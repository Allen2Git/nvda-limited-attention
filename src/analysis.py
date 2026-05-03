"""
NVDA earnings overshoot & reversal analysis.

Core research question: is the retail-driven opening surge on the trading
day AFTER an NVDA earnings release systematically followed by an intraday
reversal?  If so, the opening hour price is an emotion signal, not a
fundamental repricing.

Data: 1-minute tick-aggregated NVDA bars (2020-2026) from
      data/exported_1m_csv/NVDA_1m.csv
Events: data/nvda_earnings.csv (24 post-close earnings, 2020-05 to 2026-02)

For each earnings event i, we construct on the POST-earnings trading day:
  P_prev_close : prior session close (15:59 ET of earnings day)
  P_0930       : first-minute close in 09:30 ET session
  P_1030       : close at 10:30 ET (end of first trading hour)
  P_1600       : session close (15:59 ET)

Returns:
  r_overnight = ln(P_0930 / P_prev_close)   (institution-dominated)
  r_open_1h   = ln(P_1030 / P_0930)         (retail-dominated, post-earnings)
  r_mid_day   = ln(P_1600 / P_1030)         (balanced, rational pricing)

Core regression:
  r_mid_day_i = alpha + beta_1 * r_open_1h_i + beta_2 * r_overnight_i + eps

Asymmetry hypothesis:
  - beta_1 should be significantly NEGATIVE (opening-hour overshoot)
  - beta_2 should be ~ 0 or slightly positive (overnight is informative)

Outputs:
  results/event_level.csv    one row per earnings, all variables
  results/regressions.csv    coefficient tables (main + controls + placebo)
  results/surprise_split.csv by EPS-surprise tercile
  results/summary.json       headline numbers
"""
from __future__ import annotations
import json
import os
import sys
from math import erf, sqrt

import numpy as np
import pandas as pd

HERE = os.path.dirname(__file__)
sys.path.insert(0, HERE)
from econ import ols  # noqa: E402

ROOT = os.path.abspath(os.path.join(HERE, ".."))
DATA = os.path.join(ROOT, "data")
RES = os.path.join(ROOT, "results")
os.makedirs(RES, exist_ok=True)


# ---------------------------------------------------------------------------
def load_minute(ticker: str = "NVDA") -> pd.DataFrame:
    """Load 1-minute bars, convert to US/Eastern, keep regular session."""
    p = os.path.join(DATA, "exported_1m_csv", f"{ticker}_1m.csv")
    df = pd.read_csv(p, parse_dates=["datetime_utc"])
    df["dt_et"] = (
        df["datetime_utc"].dt.tz_localize("UTC").dt.tz_convert("US/Eastern")
        .dt.tz_localize(None)
    )
    df["date"] = df["dt_et"].dt.date
    df["hm"] = df["dt_et"].dt.strftime("%H:%M")
    # regular session 09:30-15:59
    df = df[(df["hm"] >= "09:30") & (df["hm"] < "16:00")].copy()
    df = df[df["volume"] > 0].reset_index(drop=True)
    return df


# ---------------------------------------------------------------------------
def build_event_panel(mins: pd.DataFrame, events: pd.DataFrame) -> pd.DataFrame:
    """For each earnings date (post-close release), identify the NEXT trading
    day and compute the four price anchors + three returns on that day.

    Also compute extended windows for robustness (30min, 2h, 3h).
    """
    # distinct trading dates sorted
    trading_dates = np.array(sorted(mins["date"].unique()))

    rows = []
    for _, ev in events.iterrows():
        ed = ev["earnings_date"].date()
        # next trading date strictly after earnings date
        mask = trading_dates > ed
        if not mask.any():
            continue
        next_day = trading_dates[mask][0]
        # prior trading date (the earnings day itself, since it was BEFORE close)
        mask_prev = trading_dates <= ed
        if not mask_prev.any():
            continue
        prev_day = trading_dates[mask_prev][-1]
        # earnings is AFTER close of prev_day, so P_prev_close = last minute of prev_day
        prev_bars = mins[mins["date"] == prev_day]
        next_bars = mins[mins["date"] == next_day]
        if len(prev_bars) < 10 or len(next_bars) < 300:
            continue
        P_prev_close = float(prev_bars.iloc[-1]["close"])

        # Anchor minutes on the next day (US/Eastern)
        def close_at(hm: str):
            s = next_bars[next_bars["hm"] == hm]
            return float(s.iloc[0]["close"]) if len(s) else np.nan

        P_0930 = float(next_bars.iloc[0]["close"])   # first minute close
        P_1000 = close_at("10:00")
        P_1030 = close_at("10:30")
        P_1100 = close_at("11:00")
        P_1200 = close_at("12:00")
        P_1300 = close_at("13:00")
        P_1530 = close_at("15:30")
        P_1600 = float(next_bars.iloc[-1]["close"])  # last minute close

        # Volume-weighted average within opening hour (liquidity proxy)
        open1h = next_bars[(next_bars["hm"] >= "09:30") & (next_bars["hm"] < "10:30")]
        open1h_vol = float(open1h["volume"].sum())
        full_day_vol = float(next_bars["volume"].sum())
        open1h_share = open1h_vol / full_day_vol if full_day_vol > 0 else np.nan

        rows.append({
            "earnings_date": pd.Timestamp(ed),
            "fiscal_quarter": ev["fiscal_quarter"],
            "next_day": pd.Timestamp(next_day),
            "P_prev_close": P_prev_close,
            "P_0930": P_0930,
            "P_1030": P_1030,
            "P_1600": P_1600,
            # Core returns
            "r_overnight": np.log(P_0930 / P_prev_close),
            "r_open_1h": np.log(P_1030 / P_0930),
            "r_mid_day": np.log(P_1600 / P_1030),
            "r_full_day": np.log(P_1600 / P_prev_close),
            # Window variants
            "r_open_30m": np.log(P_1000 / P_0930) if not np.isnan(P_1000) else np.nan,
            "r_open_2h":  (np.log(close_at("11:30") / P_0930)
                           if not np.isnan(close_at("11:30")) else np.nan),
            "r_aft_2h":   (np.log(P_1600 / close_at("14:00"))
                           if not np.isnan(close_at("14:00")) else np.nan),
            # Liquidity
            "open1h_share": open1h_share,
            "next_day_volume": full_day_vol,
            # Surprises
            "eps_surprise_pct": (ev["actual_eps"] - ev["consensus_eps"]) / ev["consensus_eps"] * 100,
            "rev_surprise_pct": (ev["actual_revenue_bn"] - ev["consensus_revenue_bn"]) / ev["consensus_revenue_bn"] * 100,
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
def run_regression(df: pd.DataFrame,
                   y_col: str = "r_mid_day",
                   x_cols: tuple = ("r_open_1h", "r_overnight"),
                   label: str = "main") -> dict:
    """OLS with HC1 SE; returns coef table + r^2 + n."""
    sub = df.dropna(subset=[y_col, *x_cols]).copy()
    y = sub[y_col].values
    X = np.column_stack([np.ones(len(sub))] + [sub[c].values for c in x_cols])
    r = ols(y, X)
    rows = [{"label": label, "variable": "const", "coef": float(r["beta"][0]),
             "se": float(r["se"][0]), "t": float(r["t"][0]), "p": float(r["p"][0])}]
    for i, c in enumerate(x_cols, 1):
        rows.append({"label": label, "variable": c,
                     "coef": float(r["beta"][i]),
                     "se": float(r["se"][i]),
                     "t": float(r["t"][i]),
                     "p": float(r["p"][i])})
    return {"rows": rows, "r2": float(r["r2"]), "n": int(r["n"])}


# ---------------------------------------------------------------------------
def build_placebo(mins: pd.DataFrame, events: pd.DataFrame,
                  n_placebo_per_event: int = 3,
                  seed: int = 42) -> pd.DataFrame:
    """For each earnings event, randomly pick `n_placebo_per_event` trading days
    that are NOT in [-5, +5] days around any earnings.  Compute the same
    intraday variables on those placebo days."""
    rng = np.random.default_rng(seed)
    trading_dates = np.array(sorted(mins["date"].unique()))
    earn_dates = pd.to_datetime(events["earnings_date"]).dt.date.values
    # Trading dates within ±5 days of any earnings
    blackout = set()
    for ed in earn_dates:
        for k in range(-5, 6):
            d = pd.Timestamp(ed) + pd.Timedelta(days=k)
            if d.date() in trading_dates:
                blackout.add(d.date())
    candidates = [d for d in trading_dates if d not in blackout]
    rows = []
    for _, ev in events.iterrows():
        # pick placebo days within ±60 days of the real event for comparability
        ed = ev["earnings_date"].date()
        window = [d for d in candidates if
                  abs((pd.Timestamp(d) - pd.Timestamp(ed)).days) <= 60]
        if not window:
            continue
        picks = rng.choice(window, size=min(n_placebo_per_event, len(window)),
                           replace=False)
        for d in picks:
            bars = mins[mins["date"] == d]
            prev_mask = trading_dates < d
            if not prev_mask.any() or len(bars) < 300:
                continue
            prev_day = trading_dates[prev_mask][-1]
            prev_bars = mins[mins["date"] == prev_day]
            if len(prev_bars) < 10:
                continue

            def c_at(hm):
                s = bars[bars["hm"] == hm]
                return float(s.iloc[0]["close"]) if len(s) else np.nan

            P_prev = float(prev_bars.iloc[-1]["close"])
            P_0930 = float(bars.iloc[0]["close"])
            P_1030 = c_at("10:30")
            P_1600 = float(bars.iloc[-1]["close"])
            if np.isnan(P_1030):
                continue
            rows.append({
                "pseudo_earnings_date": ev["earnings_date"],
                "placebo_date": pd.Timestamp(d),
                "r_overnight": np.log(P_0930 / P_prev),
                "r_open_1h": np.log(P_1030 / P_0930),
                "r_mid_day": np.log(P_1600 / P_1030),
            })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
def intraday_price_path(mins: pd.DataFrame, events: pd.DataFrame) -> pd.DataFrame:
    """Event-time aligned minute-level log price relative to P_0930.

    Returns one row per (event, minute-of-day) with pct from open.
    """
    trading_dates = np.array(sorted(mins["date"].unique()))
    rows = []
    for _, ev in events.iterrows():
        ed = ev["earnings_date"].date()
        mask = trading_dates > ed
        if not mask.any():
            continue
        next_day = trading_dates[mask][0]
        bars = mins[mins["date"] == next_day].sort_values("dt_et").reset_index(drop=True)
        if len(bars) < 300:
            continue
        P0 = float(bars.iloc[0]["close"])
        for i, row in bars.iterrows():
            minute = row["dt_et"].hour * 60 + row["dt_et"].minute
            # minutes from 09:30 open
            m = minute - (9 * 60 + 30)
            rows.append({
                "earnings_date": pd.Timestamp(ed),
                "m": m,
                "log_rel": np.log(row["close"] / P0),
            })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
def main():
    print("Loading 1-minute NVDA bars...")
    mins = load_minute("NVDA")
    print(f"  {len(mins):,} minute rows, {mins['date'].nunique()} trading days")

    events = pd.read_csv(os.path.join(DATA, "nvda_earnings.csv"),
                         parse_dates=["earnings_date"])
    print(f"  {len(events)} earnings events")

    # Event-level panel
    df = build_event_panel(mins, events)
    df.to_csv(os.path.join(RES, "event_level.csv"), index=False)
    print(f"Saved results/event_level.csv  ({len(df)} rows)")

    # ---- Core regression ----
    print("\n=== Core regression ===")
    main_res = run_regression(df, "r_mid_day", ("r_open_1h", "r_overnight"), "main")
    # Also run univariate versions for comparison
    uni_open = run_regression(df, "r_mid_day", ("r_open_1h",), "uni_open_1h")
    uni_over = run_regression(df, "r_mid_day", ("r_overnight",), "uni_overnight")

    # ---- Window sensitivity ----
    print("\n=== Window sensitivity ===")
    win30 = run_regression(df.dropna(subset=["r_open_30m"]),
                           "r_mid_day", ("r_open_30m", "r_overnight"),
                           "win_30m")

    # ---- Placebo ----
    print("\n=== Placebo on non-earnings days ===")
    placebo = build_placebo(mins, events, n_placebo_per_event=3)
    placebo.to_csv(os.path.join(RES, "placebo_days.csv"), index=False)
    if len(placebo) >= 10:
        pres = run_regression(placebo, "r_mid_day", ("r_open_1h", "r_overnight"),
                              "placebo")
    else:
        pres = {"rows": [], "r2": np.nan, "n": 0}

    # ---- Surprise split ----
    print("\n=== Surprise-based split ===")
    df_s = df.dropna(subset=["eps_surprise_pct"])
    # terciles
    q1, q2 = df_s["eps_surprise_pct"].quantile([1 / 3, 2 / 3])
    def tercile(v):
        return "low" if v <= q1 else ("mid" if v <= q2 else "high")
    df_s["eps_tercile"] = df_s["eps_surprise_pct"].apply(tercile)
    surprise_rows = []
    for t, g in df_s.groupby("eps_tercile"):
        if len(g) < 4:
            continue
        surprise_rows.append({
            "tercile": t, "n": len(g),
            "mean_overnight": float(g["r_overnight"].mean()),
            "mean_open_1h": float(g["r_open_1h"].mean()),
            "mean_mid_day": float(g["r_mid_day"].mean()),
            "mean_full_day": float(g["r_full_day"].mean()),
            "corr_open_mid": float(g["r_open_1h"].corr(g["r_mid_day"])),
        })
    surprise_df = pd.DataFrame(surprise_rows)
    surprise_df.to_csv(os.path.join(RES, "surprise_split.csv"), index=False)
    print(surprise_df.to_string(index=False))

    # ---- Combine all regression rows ----
    all_reg = pd.DataFrame(
        main_res["rows"] + uni_open["rows"] + uni_over["rows"]
        + win30["rows"] + pres["rows"]
    )
    # annotate n and r2 per label
    meta = {
        "main": (main_res["n"], main_res["r2"]),
        "uni_open_1h": (uni_open["n"], uni_open["r2"]),
        "uni_overnight": (uni_over["n"], uni_over["r2"]),
        "win_30m": (win30["n"], win30["r2"]),
        "placebo": (pres["n"], pres["r2"]),
    }
    all_reg["n"] = all_reg["label"].map(lambda x: meta[x][0])
    all_reg["r2"] = all_reg["label"].map(lambda x: meta[x][1])
    all_reg.to_csv(os.path.join(RES, "regressions.csv"), index=False)
    print("\nAll regressions saved.")

    # ---- Intraday price path ----
    path = intraday_price_path(mins, events)
    path.to_csv(os.path.join(RES, "intraday_path.csv"), index=False)
    # averaged
    avg = path.groupby("m")["log_rel"].agg(["mean", "std", "count"]).reset_index()
    avg["se"] = avg["std"] / np.sqrt(avg["count"])
    avg.to_csv(os.path.join(RES, "intraday_path_avg.csv"), index=False)

    # ---- Summary ----
    def pick(label, var):
        sub = all_reg[(all_reg["label"] == label) & (all_reg["variable"] == var)]
        if not len(sub):
            return None
        r = sub.iloc[0]
        return {"coef": round(float(r["coef"]), 4),
                "se": round(float(r["se"]), 4),
                "t": round(float(r["t"]), 2),
                "p": round(float(r["p"]), 4)}
    summary = {
        "n_events": int(len(df)),
        "date_range": [str(df["earnings_date"].min().date()),
                       str(df["earnings_date"].max().date())],
        "MAIN_beta_open_1h": pick("main", "r_open_1h"),
        "MAIN_beta_overnight": pick("main", "r_overnight"),
        "MAIN_R2": round(main_res["r2"], 4),
        "univar_open_1h_beta": pick("uni_open_1h", "r_open_1h"),
        "univar_overnight_beta": pick("uni_overnight", "r_overnight"),
        "win30_beta_open_30m": pick("win_30m", "r_open_30m"),
        "placebo_beta_open_1h": pick("placebo", "r_open_1h"),
        "placebo_n": pres["n"],
        "surprise_split_by_tercile": surprise_df.to_dict(orient="records"),
    }
    with open(os.path.join(RES, "summary.json"), "w") as f:
        json.dump(summary, f, indent=2, default=str)
    print("\n=== Summary ===")
    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()
