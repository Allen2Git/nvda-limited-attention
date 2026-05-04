"""Window sensitivity: test overshoot-reversal at 10min / 30min / 1h / 2h.

For each window W in {10m, 30m, 1h, 2h}, construct:
    r_open_W   = log(P_{0930+W} / P_0930)            # 'overshoot window'
    r_rest_W   = log(P_1600 / P_{0930+W})            # 'reversal window'

Then estimate:
    r_rest_W = alpha + beta_1 * r_open_W + beta_2 * r_overnight + eps

If the classical overshoot-reversal pattern holds for ANY of these windows,
beta_1 should come out significantly NEGATIVE.  If beta_1 is near zero for
all four windows, we have stronger evidence that the result is not just a
1-hour-window artifact.
"""
from __future__ import annotations
import os
import sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(__file__)
sys.path.insert(0, HERE)
from econ import ols  # noqa

ROOT = os.path.abspath(os.path.join(HERE, ".."))
DATA = os.path.join(ROOT, "data")
RES = os.path.join(ROOT, "results")
FIG = os.path.join(ROOT, "figures")
os.makedirs(RES, exist_ok=True)
os.makedirs(FIG, exist_ok=True)


def load_minute():
    p = os.path.join(DATA, "exported_1m_csv", "NVDA_1m.csv")
    df = pd.read_csv(p, parse_dates=["datetime_utc"])
    df["dt_et"] = (df["datetime_utc"].dt.tz_localize("UTC")
                    .dt.tz_convert("US/Eastern").dt.tz_localize(None))
    df["date"] = df["dt_et"].dt.date
    df["hm"] = df["dt_et"].dt.strftime("%H:%M")
    df = df[(df["hm"] >= "09:30") & (df["hm"] < "16:00")].copy()
    return df[df["volume"] > 0].reset_index(drop=True)


# Window specs: (label, end-of-open-window hm)
WINDOWS = [
    ("10m", "09:40"),
    ("30m", "10:00"),
    ("1h",  "10:30"),
    ("2h",  "11:30"),
]


def build(mins, events):
    trading_dates = np.array(sorted(mins["date"].unique()))
    rows = []
    for _, ev in events.iterrows():
        ed = ev["earnings_date"].date()
        m = trading_dates > ed
        if not m.any():
            continue
        nd = trading_dates[m][0]
        mp = trading_dates <= ed
        if not mp.any():
            continue
        pd_day = trading_dates[mp][-1]
        pb = mins[mins["date"] == pd_day]
        nb = mins[mins["date"] == nd]
        if len(pb) < 10 or len(nb) < 300:
            continue
        P_prev = float(pb.iloc[-1]["close"])
        P_0930 = float(nb.iloc[0]["close"])
        P_1600 = float(nb.iloc[-1]["close"])

        def cat(hm):
            s = nb[nb["hm"] == hm]
            return float(s.iloc[0]["close"]) if len(s) else np.nan

        r = {
            "earnings_date": pd.Timestamp(ed),
            "r_overnight": np.log(P_0930 / P_prev),
        }
        for label, hm_end in WINDOWS:
            P_end = cat(hm_end)
            if np.isnan(P_end):
                r[f"r_open_{label}"] = np.nan
                r[f"r_rest_{label}"] = np.nan
            else:
                r[f"r_open_{label}"] = np.log(P_end / P_0930)
                r[f"r_rest_{label}"] = np.log(P_1600 / P_end)
        rows.append(r)
    return pd.DataFrame(rows)


def run(df, y, xs):
    sub = df.dropna(subset=[y, *xs]).copy()
    y_v = sub[y].values
    X = np.column_stack([np.ones(len(sub))] + [sub[c].values for c in xs])
    r = ols(y_v, X)
    return r, len(sub)


def main():
    print("Loading minute data...")
    mins = load_minute()
    events = pd.read_csv(os.path.join(DATA, "nvda_earnings.csv"),
                          parse_dates=["earnings_date"])
    df = build(mins, events)
    df.to_csv(os.path.join(RES, "window_panel.csv"), index=False)
    print(f"  built {len(df)} events with 4 window variants\n")

    # ---- One regression per window ----
    results = []
    for label, _ in WINDOWS:
        y = f"r_rest_{label}"
        xs = (f"r_open_{label}", "r_overnight")
        r, n = run(df, y, xs)
        results.append({
            "window": label,
            "n": n,
            "beta_open": float(r["beta"][1]),
            "se_open":   float(r["se"][1]),
            "t_open":    float(r["t"][1]),
            "p_open":    float(r["p"][1]),
            "beta_overnight": float(r["beta"][2]),
            "se_overnight":   float(r["se"][2]),
            "t_overnight":    float(r["t"][2]),
            "p_overnight":    float(r["p"][2]),
            "r2": float(r["r2"]),
        })
        # Mean and std of each component for descriptive layer
        mean_open = df[f"r_open_{label}"].mean() * 100
        mean_rest = df[f"r_rest_{label}"].mean() * 100
        std_open = df[f"r_open_{label}"].std() * 100
        std_rest = df[f"r_rest_{label}"].std() * 100
        print(f"--- window={label}, n={n} ---")
        print(f"  mean r_open_{label}  = {mean_open:+.3f}%  (sd {std_open:.2f}%)")
        print(f"  mean r_rest_{label}  = {mean_rest:+.3f}%  (sd {std_rest:.2f}%)")
        print(f"  beta_open      = {r['beta'][1]:+.4f}  "
              f"se={r['se'][1]:.4f}  t={r['t'][1]:+.2f}  p={r['p'][1]:.3f}")
        print(f"  beta_overnight = {r['beta'][2]:+.4f}  "
              f"se={r['se'][2]:.4f}  t={r['t'][2]:+.2f}  p={r['p'][2]:.3f}")
        print(f"  R^2 = {r['r2']:.4f}\n")

    res_df = pd.DataFrame(results)
    res_df.to_csv(os.path.join(RES, "window_sensitivity.csv"), index=False)

    # ---- Plot ----
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))

    # LEFT: beta_1 with 95% CI
    ax = axes[0]
    x = np.arange(len(results))
    beta = [r["beta_open"] for r in results]
    se = [r["se_open"] for r in results]
    ci = [1.96 * s for s in se]
    labels = [r["window"] for r in results]
    ax.errorbar(x, beta, yerr=ci, fmt="o", color="#1f77b4", ms=10,
                capsize=8, capthick=2, lw=2, ecolor="#5a8db8")
    ax.axhline(0, color="#333", lw=1, ls="--")
    # predicted direction reminder
    ax.axhspan(-1.0, 0, color="#2e7d32", alpha=0.06)
    ax.text(0.5, -0.42, "expected zone if overshoot-reversal holds\n(beta_1 < 0)",
            fontsize=9, color="#2e7d32", ha="left", style="italic")
    for xi, yi, ni in zip(x, beta, [r["n"] for r in results]):
        ax.annotate(f"{yi:+.3f}\n(n={ni})", xy=(xi, yi),
                    xytext=(xi + 0.08, yi + 0.04), fontsize=9)
    ax.set_xticks(x)
    ax.set_xticklabels([f"open-{l}\n(rest = to 16:00)" for l in labels],
                        fontsize=10)
    ax.set_ylabel("beta_1  (slope on r_open_W)")
    ax.set_title("Overshoot coefficient across 4 window widths\n"
                 "(error bars = 95% CI, HC1 robust)", fontsize=11)
    ax.set_ylim(-0.7, 0.7)
    ax.grid(alpha=0.25)

    # RIGHT: mean returns by window
    ax = axes[1]
    width = 0.35
    means_open = [df[f"r_open_{r['window']}"].mean() * 100 for r in results]
    means_rest = [df[f"r_rest_{r['window']}"].mean() * 100 for r in results]
    se_open = [df[f"r_open_{r['window']}"].std() * 100 / np.sqrt(r["n"])
               for r in results]
    se_rest = [df[f"r_rest_{r['window']}"].std() * 100 / np.sqrt(r["n"])
               for r in results]
    ax.bar(x - width/2, means_open, width, yerr=se_open,
           color="#e57373", label="r_open_W  (open window)",
           capsize=4, edgecolor="white")
    ax.bar(x + width/2, means_rest, width, yerr=se_rest,
           color="#64b5f6", label="r_rest_W  (rest of day)",
           capsize=4, edgecolor="white")
    ax.axhline(0, color="black", lw=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel("Mean return (%)  across 24 events")
    ax.set_title("Mean return in each window\n"
                 "If overshoot-reversal holds, bars should have opposite signs",
                 fontsize=11)
    ax.legend(loc="upper left", fontsize=9)
    ax.grid(alpha=0.25, axis="y")

    fig.suptitle("Window sensitivity: does the window choice change the verdict?",
                 fontsize=13, fontweight="bold", y=1.00)
    plt.tight_layout()
    out = os.path.join(FIG, "fig_window_sensitivity.png")
    fig.savefig(out, dpi=180, bbox_inches="tight")
    plt.close(fig)
    print(f"\nSaved figure: {out}")
    print(f"Saved table:  {os.path.join(RES, 'window_sensitivity.csv')}")


if __name__ == "__main__":
    main()
