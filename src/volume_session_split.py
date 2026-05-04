"""Split NVDA 1-min data by session (pre / rth / after) and compute
volume shares — for normal days and for earnings-day chains.

Session definitions (ET):
  Pre-Market   : 04:00 - 09:30
  Regular (RTH): 09:30 - 16:00
  After-Hours  : 16:00 - 20:00

For each earnings event, the "earnings chain" = after-hours of earnings day
  + pre-market of next day + RTH of next day + after-hours of next day.
This is the full 17-hour information-absorption cycle.
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


def load_all_sessions():
    """Load 1-min bars INCLUDING pre-market and after-hours."""
    p = os.path.join(DATA, "exported_1m_csv", "NVDA_1m.csv")
    df = pd.read_csv(p, parse_dates=["datetime_utc"])
    df["dt_et"] = (df["datetime_utc"].dt.tz_localize("UTC")
                    .dt.tz_convert("US/Eastern").dt.tz_localize(None))
    df["date"] = df["dt_et"].dt.date
    df["hm"] = df["dt_et"].dt.strftime("%H:%M")

    # Session classification
    def classify(hm):
        if hm < "09:30":
            return "pre"
        elif hm < "16:00":
            return "rth"
        elif hm < "20:00":
            return "after"
        return "off"

    df["session"] = df["hm"].apply(classify)
    df = df[df["session"] != "off"]
    df = df[df["volume"] > 0].reset_index(drop=True)
    return df


def session_share_by_day(df):
    """Per-trading-day volume share by session."""
    piv = (df.groupby(["date", "session"])["volume"]
             .sum().unstack(fill_value=0))
    # keep only rows with any RTH data (valid trading day)
    piv = piv[piv.get("rth", 0) > 0].copy()
    for c in ["pre", "rth", "after"]:
        if c not in piv.columns:
            piv[c] = 0
    piv["total"] = piv["pre"] + piv["rth"] + piv["after"]
    for c in ["pre", "rth", "after"]:
        piv[f"{c}_share"] = piv[c] / piv["total"]
    return piv.reset_index()


def earnings_chain_analysis(df, events):
    """For each earnings event, compute volume in each of:
       - E.afternoon (12:00-16:00 of earnings day)  [context]
       - E.after (16:00-20:00 of earnings day)      [post-release absorption]
       - N.pre   (04:00-09:30 of next day)          [pre-market]
       - N.rth   (09:30-16:00 of next day)          [official]
       - N.after (16:00-20:00 of next day)          [continuation]
    """
    all_dates = np.array(sorted(df["date"].unique()))
    rows = []
    for _, ev in events.iterrows():
        ed = ev["earnings_date"].date()
        m = all_dates > ed
        if not m.any():
            continue
        nd = all_dates[m][0]
        mp = all_dates <= ed
        if not mp.any():
            continue
        pd_day = all_dates[mp][-1]

        pb = df[df["date"] == pd_day]
        nb = df[df["date"] == nd]

        # Earnings day after-hours
        e_after = pb[(pb["session"] == "after")]
        # Earnings day RTH afternoon (for context)
        e_pm = pb[(pb["session"] == "rth") & (pb["hm"] >= "13:00")]
        # Next day sessions
        n_pre = nb[nb["session"] == "pre"]
        n_rth = nb[nb["session"] == "rth"]
        n_after = nb[nb["session"] == "after"]
        # Next day open 1h (subset of RTH)
        n_open1h = nb[(nb["hm"] >= "09:30") & (nb["hm"] < "10:30")]

        rows.append({
            "fiscal_quarter": ev["fiscal_quarter"],
            "earnings_date": pd.Timestamp(ed),
            "next_day": pd.Timestamp(nd),
            "e_pm_vol":   float(e_pm["volume"].sum()),
            "e_after_vol": float(e_after["volume"].sum()),
            "n_pre_vol":   float(n_pre["volume"].sum()),
            "n_open1h_vol": float(n_open1h["volume"].sum()),
            "n_rth_vol":   float(n_rth["volume"].sum()),
            "n_after_vol": float(n_after["volume"].sum()),
        })
    return pd.DataFrame(rows)


def main():
    print("Loading 1-min bars (all sessions)...")
    df = load_all_sessions()
    print(f"  {len(df):,} rows, dates {df['date'].min()} -> {df['date'].max()}")
    print(f"  Session counts (1-min bars): {df['session'].value_counts().to_dict()}")

    # -----------------------------------------------------------
    # A) Overall: average session share on NORMAL days
    # -----------------------------------------------------------
    events = pd.read_csv(os.path.join(DATA, "nvda_earnings.csv"),
                          parse_dates=["earnings_date"])
    earn_dates = set(pd.to_datetime(events["earnings_date"]).dt.date.values)
    # Exclude earnings day and next day from "normal" sample
    blackout = set()
    for ed in earn_dates:
        for k in range(-1, 3):
            blackout.add(ed + pd.Timedelta(days=k).to_pytimedelta()
                          if False else (pd.Timestamp(ed) + pd.Timedelta(days=k)).date())

    daily = session_share_by_day(df)
    daily["is_earnings_chain"] = daily["date"].isin(blackout)
    normal = daily[~daily["is_earnings_chain"]]
    earnings_chain = daily[daily["is_earnings_chain"]]

    print("\n=== (A) Average per-day volume share ===")
    print("Normal trading days (n={}):".format(len(normal)))
    for c in ["pre", "rth", "after"]:
        m = normal[f"{c}_share"].mean() * 100
        med = normal[f"{c}_share"].median() * 100
        print(f"  {c:<6} mean={m:5.2f}%  median={med:5.2f}%")

    print("\nEarnings-chain days (n={}):".format(len(earnings_chain)))
    for c in ["pre", "rth", "after"]:
        m = earnings_chain[f"{c}_share"].mean() * 100
        med = earnings_chain[f"{c}_share"].median() * 100
        print(f"  {c:<6} mean={m:5.2f}%  median={med:5.2f}%")

    # -----------------------------------------------------------
    # B) Earnings chain deep dive: 5-bucket split
    # -----------------------------------------------------------
    ec = earnings_chain_analysis(df, events)
    ec["total_chain"] = (ec["e_after_vol"] + ec["n_pre_vol"]
                          + ec["n_rth_vol"] + ec["n_after_vol"])
    for c in ["e_after", "n_pre", "n_open1h", "n_rth", "n_after"]:
        ec[f"{c}_share"] = ec[f"{c}_vol"] / ec["total_chain"] * 100

    # Summary
    print("\n=== (B) Earnings-chain volume breakdown (24 events) ===")
    print("Share of total 17-hour chain volume by phase:")
    for c, label in [
        ("e_after",  "Earnings day after-hours 16:00-20:00"),
        ("n_pre",    "Next day pre-market      04:00-09:30"),
        ("n_rth",    "Next day regular hours   09:30-16:00  [WHOLE day]"),
        ("n_open1h", "  ... of which open-1h   09:30-10:30  [subset]"),
        ("n_after",  "Next day after-hours     16:00-20:00"),
    ]:
        share = ec[f"{c}_share"]
        print(f"  {label:<50} mean={share.mean():5.2f}%  "
              f"median={share.median():5.2f}%  sd={share.std():4.2f}%")

    ec.to_csv(os.path.join(RES, "earnings_chain_volume.csv"), index=False)

    # -----------------------------------------------------------
    # C) Figure: two panels
    # -----------------------------------------------------------
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    # LEFT: normal vs earnings-chain comparison (stacked bars)
    ax = axes[0]
    labels = ["Normal day\n(n={:,})".format(len(normal)),
              "Earnings-chain day\n(n={})".format(len(earnings_chain))]
    pre_vals   = [normal["pre_share"].mean() * 100,
                   earnings_chain["pre_share"].mean() * 100]
    rth_vals   = [normal["rth_share"].mean() * 100,
                   earnings_chain["rth_share"].mean() * 100]
    after_vals = [normal["after_share"].mean() * 100,
                   earnings_chain["after_share"].mean() * 100]

    x = np.arange(len(labels))
    bar1 = ax.bar(x, pre_vals, label="Pre-market 04:00-09:30",
                   color="#ffb74d", edgecolor="white")
    bar2 = ax.bar(x, rth_vals, bottom=pre_vals, label="Regular 09:30-16:00",
                   color="#4fc3f7", edgecolor="white")
    bar3 = ax.bar(x, after_vals, bottom=np.array(pre_vals)+np.array(rth_vals),
                   label="After-hours 16:00-20:00",
                   color="#9575cd", edgecolor="white")

    for i, (p, r, a) in enumerate(zip(pre_vals, rth_vals, after_vals)):
        ax.text(i, p/2, f"{p:.1f}%", ha="center", va="center",
                fontweight="bold", color="white", fontsize=11)
        ax.text(i, p + r/2, f"{r:.1f}%", ha="center", va="center",
                fontweight="bold", color="white", fontsize=11)
        ax.text(i, p + r + a/2, f"{a:.1f}%", ha="center", va="center",
                fontweight="bold", color="white", fontsize=11)

    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=11)
    ax.set_ylabel("Volume share (%)", fontsize=11)
    ax.set_title("NVDA daily volume share by session\n"
                 "(2020-2026, averaged per day)",
                 fontsize=12, pad=10)
    ax.legend(loc="lower right", fontsize=9)
    ax.set_ylim(0, 105)
    ax.grid(alpha=0.25, axis="y")

    # RIGHT: earnings-chain 5-phase breakdown
    ax = axes[1]
    phase_labels = [
        "E-day\nafter-hours\n16:00-20:00",
        "N-day\npre-market\n04:00-09:30",
        "N-day\nopen-1h\n09:30-10:30",
        "N-day\nRTH-rest\n10:30-16:00",
        "N-day\nafter-hours\n16:00-20:00",
    ]
    phase_cols = [
        ec["e_after_share"].mean(),
        ec["n_pre_share"].mean(),
        ec["n_open1h_share"].mean(),
        (ec["n_rth_share"] - ec["n_open1h_share"]).mean(),  # rest of RTH
        ec["n_after_share"].mean(),
    ]
    phase_sds = [
        ec["e_after_share"].std(),
        ec["n_pre_share"].std(),
        ec["n_open1h_share"].std(),
        (ec["n_rth_share"] - ec["n_open1h_share"]).std(),
        ec["n_after_share"].std(),
    ]
    colors = ["#9575cd", "#ffb74d", "#ef5350", "#4fc3f7", "#9575cd"]
    xp = np.arange(len(phase_labels))
    ax.bar(xp, phase_cols, yerr=phase_sds, color=colors,
           edgecolor="white", capsize=6)
    for i, (v, sd) in enumerate(zip(phase_cols, phase_sds)):
        ax.text(i, v + sd + 1, f"{v:.1f}%", ha="center", fontweight="bold",
                fontsize=11, color="#222")

    ax.set_xticks(xp)
    ax.set_xticklabels(phase_labels, fontsize=9)
    ax.set_ylabel("Share of earnings-chain volume (%)", fontsize=11)
    ax.set_title("Earnings-chain volume breakdown\n"
                 "(each event's 17-hour cycle = 100%; mean ± 1 sd across 24 events)",
                 fontsize=12, pad=10)
    ax.set_ylim(0, max(phase_cols) + max(phase_sds) + 8)
    ax.grid(alpha=0.25, axis="y")

    # Add annotation: open-1h is part of RTH
    ax.annotate("open-1h + RTH-rest\n= full RTH",
                xy=(2.5, phase_cols[2] + phase_cols[3] + 3),
                xytext=(2.5, max(phase_cols) + max(phase_sds) + 3),
                fontsize=9, color="#555", ha="center",
                arrowprops=dict(arrowstyle="-[, widthB=2.5", color="#999"))

    fig.suptitle("Where does NVDA volume happen?  Normal days vs earnings days",
                 fontsize=13, fontweight="bold", y=1.00)
    plt.tight_layout()
    out = os.path.join(FIG, "fig_volume_session_split.png")
    fig.savefig(out, dpi=180, bbox_inches="tight")
    plt.close(fig)
    print(f"\nSaved: {out}")

    # -----------------------------------------------------------
    # D) Earnings events detail (per-event breakdown)
    # -----------------------------------------------------------
    print("\n=== (D) Per-event snapshot (selected) ===")
    show = ec[["fiscal_quarter", "e_after_share", "n_pre_share",
               "n_open1h_share", "n_rth_share", "n_after_share"]].copy()
    for c in show.columns:
        if c.endswith("_share"):
            show[c] = show[c].round(1)
    print(show.to_string(index=False))


if __name__ == "__main__":
    main()
