"""Cross-ticker pre/post-market volume share analysis.

We have 1-min bars for NVDA, AMZN, TXN (covering 2015-2026). For each
ticker, compute:
  - Average daily volume share by session (pre / rth / after) on normal days
  - On the ticker's own earnings days (if we have earnings list) OR
    on "high-vol" days (top-5% daily RTH volume) as event proxy

This lets us contrast how concentrated the three stocks are in different
sessions: NVDA (AI king), AMZN (mega-cap), TXN (mature semi).
"""
import os
import sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(__file__)
ROOT = os.path.abspath(os.path.join(HERE, ".."))
DATA = os.path.join(ROOT, "data")
RES = os.path.join(ROOT, "results")
FIG = os.path.join(ROOT, "figures")
os.makedirs(RES, exist_ok=True)
os.makedirs(FIG, exist_ok=True)

TICKERS = ["NVDA", "AMZN", "TXN"]
TICKER_LABELS = {
    "NVDA": "NVDA\n(AI accelerator)",
    "AMZN": "AMZN\n(Mega-cap tech)",
    "TXN":  "TXN\n(Mature semi)",
}
TICKER_COLORS = {"NVDA": "#76b900", "AMZN": "#ff9900", "TXN": "#c8102e"}


def load_ticker(tk):
    p = os.path.join(DATA, "exported_1m_csv", f"{tk}_1m.csv")
    df = pd.read_csv(p, parse_dates=["datetime_utc"])
    df["dt_et"] = (df["datetime_utc"].dt.tz_localize("UTC")
                    .dt.tz_convert("US/Eastern").dt.tz_localize(None))
    df["date"] = df["dt_et"].dt.date
    df["hm"] = df["dt_et"].dt.strftime("%H:%M")

    def cls(hm):
        if hm < "09:30":
            return "pre"
        if hm < "16:00":
            return "rth"
        if hm < "20:00":
            return "after"
        return "off"
    df["session"] = df["hm"].apply(cls)
    df = df[df["session"] != "off"]
    df = df[df["volume"] > 0].reset_index(drop=True)
    return df


def session_share(df):
    piv = (df.groupby(["date", "session"])["volume"]
             .sum().unstack(fill_value=0))
    for c in ["pre", "rth", "after"]:
        if c not in piv.columns:
            piv[c] = 0
    piv = piv[piv["rth"] > 0].copy()
    piv["total"] = piv["pre"] + piv["rth"] + piv["after"]
    for c in ["pre", "rth", "after"]:
        piv[f"{c}_share"] = piv[c] / piv["total"]
    return piv.reset_index()


def high_vol_days(daily_df, top_pct=0.05):
    """Proxy for event days: top-N% of trading days by RTH volume."""
    threshold = daily_df["rth"].quantile(1 - top_pct)
    return daily_df[daily_df["rth"] >= threshold]


def open1h_share_of_rth(df):
    """For each trading date, compute open-1h (09:30-10:30) share of RTH."""
    o = df[(df["hm"] >= "09:30") & (df["hm"] < "10:30")]
    o_v = o.groupby("date")["volume"].sum()
    r = df[df["session"] == "rth"]
    r_v = r.groupby("date")["volume"].sum()
    return (o_v / r_v * 100).dropna()


def main():
    overall = []
    event_proxy = []
    open1h_rows = []

    for tk in TICKERS:
        print(f"\n### Loading {tk} ...")
        df = load_ticker(tk)
        print(f"  {len(df):,} rows, {df['date'].min()} -> {df['date'].max()}")

        daily = session_share(df)
        print(f"  {len(daily)} trading days")

        # ---- Overall averages ----
        for c in ["pre", "rth", "after"]:
            overall.append({
                "ticker": tk,
                "session": c,
                "mean_share": daily[f"{c}_share"].mean() * 100,
                "median_share": daily[f"{c}_share"].median() * 100,
            })

        # ---- Event-proxy (top 5% RTH volume days) ----
        hv = high_vol_days(daily, top_pct=0.05)
        print(f"  top-5% volume day threshold: n={len(hv)}")
        for c in ["pre", "rth", "after"]:
            event_proxy.append({
                "ticker": tk,
                "session": c,
                "mean_share": hv[f"{c}_share"].mean() * 100,
                "n": len(hv),
            })

        # ---- Open-1h as share of RTH ----
        o1h = open1h_share_of_rth(df)
        open1h_rows.append({
            "ticker": tk,
            "normal_open1h_of_rth_mean": o1h.mean(),
            "normal_open1h_of_rth_median": o1h.median(),
            "highvol_open1h_of_rth_mean": o1h.loc[
                o1h.index.isin(hv["date"])].mean(),
        })

    overall_df = pd.DataFrame(overall)
    event_df = pd.DataFrame(event_proxy)
    o1h_df = pd.DataFrame(open1h_rows)

    print("\n=== Normal-day volume share by ticker ===")
    print(overall_df.pivot(index="ticker", columns="session",
                            values="mean_share").round(2))
    print("\n=== Event-proxy day (top 5% RTH volume) share ===")
    print(event_df.pivot(index="ticker", columns="session",
                          values="mean_share").round(2))
    print("\n=== Open-1h as share of RTH ===")
    print(o1h_df.round(2))

    overall_df.to_csv(os.path.join(RES, "cross_ticker_sessions_normal.csv"),
                       index=False)
    event_df.to_csv(os.path.join(RES, "cross_ticker_sessions_highvol.csv"),
                     index=False)

    # ---------- Figure ----------
    fig, axes = plt.subplots(1, 3, figsize=(16, 6))

    # ==== Panel 1: Normal day session breakdown ====
    ax = axes[0]
    tickers = TICKERS
    pre = [overall_df[(overall_df["ticker"] == t)
                       & (overall_df["session"] == "pre")][
        "mean_share"].iloc[0] for t in tickers]
    rth = [overall_df[(overall_df["ticker"] == t)
                       & (overall_df["session"] == "rth")][
        "mean_share"].iloc[0] for t in tickers]
    aft = [overall_df[(overall_df["ticker"] == t)
                       & (overall_df["session"] == "after")][
        "mean_share"].iloc[0] for t in tickers]

    x = np.arange(len(tickers))
    ax.bar(x, pre, label="Pre 04:00-09:30",
           color="#ffb74d", edgecolor="white")
    ax.bar(x, rth, bottom=pre, label="RTH 09:30-16:00",
           color="#4fc3f7", edgecolor="white")
    ax.bar(x, aft, bottom=np.array(pre) + np.array(rth),
           label="After 16:00-20:00",
           color="#9575cd", edgecolor="white")
    for i, (p, r, a) in enumerate(zip(pre, rth, aft)):
        ax.text(i, p/2, f"{p:.1f}%", ha="center", va="center",
                fontweight="bold", color="white", fontsize=10)
        ax.text(i, p + r/2, f"{r:.1f}%", ha="center", va="center",
                fontweight="bold", color="white", fontsize=11)
        ax.text(i, p + r + a/2, f"{a:.1f}%", ha="center", va="center",
                fontweight="bold", color="white", fontsize=10)
    ax.set_xticks(x)
    ax.set_xticklabels([TICKER_LABELS[t] for t in tickers], fontsize=10)
    ax.set_ylabel("Volume share (%)")
    ax.set_title("Normal-day volume by session", fontsize=12, pad=8)
    ax.legend(fontsize=8, loc="lower right")
    ax.set_ylim(0, 105)
    ax.grid(alpha=0.25, axis="y")

    # ==== Panel 2: Event-day (top 5% vol) ====
    ax = axes[1]
    pre = [event_df[(event_df["ticker"] == t)
                     & (event_df["session"] == "pre")][
        "mean_share"].iloc[0] for t in tickers]
    rth = [event_df[(event_df["ticker"] == t)
                     & (event_df["session"] == "rth")][
        "mean_share"].iloc[0] for t in tickers]
    aft = [event_df[(event_df["ticker"] == t)
                     & (event_df["session"] == "after")][
        "mean_share"].iloc[0] for t in tickers]
    ax.bar(x, pre, label="Pre",
           color="#ffb74d", edgecolor="white")
    ax.bar(x, rth, bottom=pre, label="RTH",
           color="#4fc3f7", edgecolor="white")
    ax.bar(x, aft, bottom=np.array(pre) + np.array(rth),
           label="After",
           color="#9575cd", edgecolor="white")
    for i, (p, r, a) in enumerate(zip(pre, rth, aft)):
        ax.text(i, p/2, f"{p:.1f}%", ha="center", va="center",
                fontweight="bold", color="white", fontsize=10)
        ax.text(i, p + r/2, f"{r:.1f}%", ha="center", va="center",
                fontweight="bold", color="white", fontsize=11)
        ax.text(i, p + r + a/2, f"{a:.1f}%", ha="center", va="center",
                fontweight="bold", color="white", fontsize=10)
    ax.set_xticks(x)
    ax.set_xticklabels([TICKER_LABELS[t] for t in tickers], fontsize=10)
    ax.set_ylabel("Volume share (%)")
    ax.set_title("High-event day (top-5% RTH vol) by session",
                 fontsize=12, pad=8)
    ax.legend(fontsize=8, loc="lower right")
    ax.set_ylim(0, 105)
    ax.grid(alpha=0.25, axis="y")

    # ==== Panel 3: Pre+After combined (the "ETH share") ====
    ax = axes[2]
    labels = ["Normal day", "High-event day"]
    eth_normal = [pre_ + aft_ for pre_, aft_ in zip(
        [overall_df[(overall_df["ticker"] == t) & (overall_df["session"] == "pre")]
         ["mean_share"].iloc[0] for t in tickers],
        [overall_df[(overall_df["ticker"] == t) & (overall_df["session"] == "after")]
         ["mean_share"].iloc[0] for t in tickers],
    )]
    eth_event = [pre_ + aft_ for pre_, aft_ in zip(
        [event_df[(event_df["ticker"] == t) & (event_df["session"] == "pre")]
         ["mean_share"].iloc[0] for t in tickers],
        [event_df[(event_df["ticker"] == t) & (event_df["session"] == "after")]
         ["mean_share"].iloc[0] for t in tickers],
    )]
    width = 0.28
    for i, tk in enumerate(tickers):
        offset = (i - 1) * width
        ax.bar([0 + offset, 1 + offset], [eth_normal[i], eth_event[i]],
               width, color=TICKER_COLORS[tk], label=tk, edgecolor="white")
        # labels
        ax.text(0 + offset, eth_normal[i] + 0.15,
                f"{eth_normal[i]:.1f}%", ha="center", fontsize=9,
                fontweight="bold")
        ax.text(1 + offset, eth_event[i] + 0.15,
                f"{eth_event[i]:.1f}%", ha="center", fontsize=9,
                fontweight="bold")
    ax.set_xticks([0, 1])
    ax.set_xticklabels(labels, fontsize=11)
    ax.set_ylabel("Pre + After share (%)")
    ax.set_title("Extended-hours share: normal vs event day",
                 fontsize=12, pad=8)
    ax.legend(fontsize=9)
    ax.grid(alpha=0.25, axis="y")
    ax.set_ylim(0, max(eth_event) + 3)

    fig.suptitle("Where does volume happen in 3 tech names?"
                 "  (1-min data, 2015-2026)",
                 fontsize=13, fontweight="bold", y=1.00)
    plt.tight_layout()
    out = os.path.join(FIG, "fig_cross_ticker_volume.png")
    fig.savefig(out, dpi=180, bbox_inches="tight")
    plt.close(fig)
    print(f"\nSaved figure: {out}")


if __name__ == "__main__":
    main()
