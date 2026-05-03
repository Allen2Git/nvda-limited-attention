"""Figures for the NVDA earnings overshoot-reversal paper (null-result story)."""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

HERE = os.path.dirname(__file__)
RES = os.path.join(HERE, "..", "results")
FIG = os.path.join(HERE, "..", "figures")
os.makedirs(FIG, exist_ok=True)

evt = pd.read_csv(os.path.join(RES, "event_level.csv"), parse_dates=["earnings_date"])
placebo = pd.read_csv(os.path.join(RES, "placebo_days.csv"))
path_avg = pd.read_csv(os.path.join(RES, "intraday_path_avg.csv"))
surprise = pd.read_csv(os.path.join(RES, "surprise_split.csv"))

# =====================================================================
# FIG 1: Bar chart of mean returns across the three windows
# =====================================================================
fig, ax = plt.subplots(figsize=(8, 4.5))
means_e = [evt["r_overnight"].mean() * 100, evt["r_open_1h"].mean() * 100,
           evt["r_mid_day"].mean() * 100]
means_p = [placebo["r_overnight"].mean() * 100, placebo["r_open_1h"].mean() * 100,
           placebo["r_mid_day"].mean() * 100]
se_e = [evt["r_overnight"].std() / np.sqrt(len(evt)) * 100,
        evt["r_open_1h"].std() / np.sqrt(len(evt)) * 100,
        evt["r_mid_day"].std() / np.sqrt(len(evt)) * 100]
se_p = [placebo["r_overnight"].std() / np.sqrt(len(placebo)) * 100,
        placebo["r_open_1h"].std() / np.sqrt(len(placebo)) * 100,
        placebo["r_mid_day"].std() / np.sqrt(len(placebo)) * 100]
labels = ["Overnight\n(close -> 09:30)",
          "Open 1h\n(09:30 -> 10:30)",
          "Mid-day\n(10:30 -> 16:00)"]
x = np.arange(3)
w = 0.35
ax.bar(x - w/2, means_e, w, yerr=np.array(se_e)*1.96, capsize=5,
       label="Earnings day (n=24)", color="#e41a1c", alpha=0.85)
ax.bar(x + w/2, means_p, w, yerr=np.array(se_p)*1.96, capsize=5,
       label=f"Placebo day (n={len(placebo)})", color="#377eb8", alpha=0.65)
ax.axhline(0, color="gray", lw=0.5)
ax.set_xticks(x)
ax.set_xticklabels(labels)
ax.set_ylabel("Mean log-return (%)")
ax.set_title("Where does the earnings reaction happen?\n"
             "Overnight dominates; intraday looks like any random day")
ax.legend()
for i, v in enumerate(means_e):
    ax.text(x[i] - w/2, v + (0.15 if v > 0 else -0.25),
            f"{v:+.2f}%", ha="center", fontsize=9, fontweight="bold")
for i, v in enumerate(means_p):
    ax.text(x[i] + w/2, v + (0.15 if v > 0 else -0.25),
            f"{v:+.2f}%", ha="center", fontsize=9)
fig.tight_layout()
fig.savefig(os.path.join(FIG, "fig1_means_by_window.png"), dpi=160)
plt.close(fig)

# =====================================================================
# FIG 2: Scatter — open_1h vs mid_day (no overshoot+reversal pattern)
# =====================================================================
fig, axes = plt.subplots(1, 2, figsize=(12, 4.8))
for ax, data, title, color in zip(
    axes,
    [evt, placebo],
    [f"Earnings days (n={len(evt)})", f"Placebo days (n={len(placebo)})"],
    ["#e41a1c", "#377eb8"],
):
    x = data["r_open_1h"].values * 100
    y = data["r_mid_day"].values * 100
    ax.scatter(x, y, s=36, color=color, alpha=0.7, edgecolors="white")
    # OLS fit
    if len(data) >= 3:
        b = np.polyfit(x, y, 1)
        xg = np.linspace(x.min(), x.max(), 50)
        ax.plot(xg, b[0] * xg + b[1], color="black", lw=1.5, ls="--",
                label=f"slope = {b[0]:+.3f}")
    ax.axhline(0, color="gray", lw=0.4)
    ax.axvline(0, color="gray", lw=0.4)
    ax.set_xlabel("Opening-hour return 09:30-10:30 (%)")
    ax.set_ylabel("Mid-day return 10:30-16:00 (%)")
    ax.set_title(title)
    ax.legend(fontsize=9)
    ax.grid(alpha=0.2)
fig.suptitle("No overshoot-reversal relationship on either earnings or placebo days",
             fontsize=12)
fig.tight_layout()
fig.savefig(os.path.join(FIG, "fig2_scatter.png"), dpi=160)
plt.close(fig)

# =====================================================================
# FIG 3: Average intraday path of NVDA price on earnings days
# =====================================================================
pa = path_avg[(path_avg["m"] >= 0) & (path_avg["m"] <= 389)].copy()
fig, ax = plt.subplots(figsize=(10, 4.5))
ax.plot(pa["m"], pa["mean"] * 100, lw=2, color="#984ea3", label="Mean path")
ax.fill_between(pa["m"],
                (pa["mean"] - 1.96 * pa["se"]) * 100,
                (pa["mean"] + 1.96 * pa["se"]) * 100,
                color="#984ea3", alpha=0.2, label="95% CI")
ax.axhline(0, color="gray", lw=0.4)
for m, lbl in [(0, "09:30"), (60, "10:30"), (180, "12:30"), (390-1, "~16:00")]:
    ax.axvline(m, color="gray", lw=0.4, ls=":")
    ax.text(m, ax.get_ylim()[0], lbl, ha="center", fontsize=8, color="gray")
ax.set_xlabel("Minutes after open on post-earnings trading day")
ax.set_ylabel("Log price relative to 09:30 open (%)")
ax.set_title("Average intraday price path across 24 NVDA earnings days\n"
             "No systematic drift: prices wander but don't trend")
ax.legend()
fig.tight_layout()
fig.savefig(os.path.join(FIG, "fig3_intraday_path.png"), dpi=160)
plt.close(fig)

# =====================================================================
# FIG 4: Overnight vs full-day scatter — overnight captures most of move
# =====================================================================
fig, ax = plt.subplots(figsize=(8, 6))
x = evt["r_overnight"].values * 100
y = evt["r_full_day"].values * 100
ax.scatter(x, y, s=60, color="#e41a1c", alpha=0.75, edgecolors="white", zorder=3)
# Fit
b = np.polyfit(x, y, 1)
xg = np.linspace(x.min(), x.max(), 50)
ax.plot(xg, b[0] * xg + b[1], color="black", lw=1.5, ls="--",
        label=f"slope = {b[0]:+.2f}, R^2 = {np.corrcoef(x,y)[0,1]**2:.2f}")
ax.plot([x.min(), x.max()], [x.min(), x.max()], color="gray", lw=0.8,
        label="y = x (all move is overnight)")
ax.axhline(0, color="gray", lw=0.4)
ax.axvline(0, color="gray", lw=0.4)
ax.set_xlabel("Overnight return (close -> 09:30 open)  [%]")
ax.set_ylabel("Full-day return (close -> next close)  [%]")
ax.set_title("Overnight move predicts the full-day move almost 1-for-1\n"
             "=> pre-market institutional trading absorbs the news")
ax.legend(fontsize=10)
ax.grid(alpha=0.2)
# Annotate the AI-boom outlier
mx = evt["r_overnight"].abs().idxmax()
ax.annotate(f"{evt.loc[mx,'fiscal_quarter']}",
            xy=(x[mx], y[mx]), xytext=(x[mx]-5, y[mx]+0.5),
            fontsize=9, arrowprops=dict(arrowstyle="-", color="gray", lw=0.5))
fig.tight_layout()
fig.savefig(os.path.join(FIG, "fig4_overnight_fullday.png"), dpi=160)
plt.close(fig)

# =====================================================================
# FIG 5: Per-event return decomposition (stacked bars)
# =====================================================================
evt_sorted = evt.sort_values("earnings_date").reset_index(drop=True)
fig, ax = plt.subplots(figsize=(12, 5.5))
x_idx = np.arange(len(evt_sorted))
ov = evt_sorted["r_overnight"].values * 100
op = evt_sorted["r_open_1h"].values * 100
mid = evt_sorted["r_mid_day"].values * 100
ax.bar(x_idx, ov, color="#377eb8", label="Overnight", alpha=0.9)
ax.bar(x_idx, op, bottom=ov, color="#e41a1c", label="Open 1h", alpha=0.9)
ax.bar(x_idx, mid, bottom=ov+op, color="#4daf4a", label="Mid-day", alpha=0.9)
ax.axhline(0, color="black", lw=0.5)
ax.set_xticks(x_idx)
ax.set_xticklabels(evt_sorted["fiscal_quarter"], rotation=75, fontsize=8)
ax.set_ylabel("Log return contribution (%)")
ax.set_title("Decomposition of each earnings-day move into overnight / open-1h / mid-day")
ax.legend(loc="best", fontsize=9)
fig.tight_layout()
fig.savefig(os.path.join(FIG, "fig5_event_decomposition.png"), dpi=160)
plt.close(fig)

# =====================================================================
# FIG 6: Surprise split
# =====================================================================
fig, ax = plt.subplots(figsize=(9, 4.5))
tercile_order = ["low", "mid", "high"]
s_sorted = surprise.set_index("tercile").reindex(tercile_order).reset_index()
x = np.arange(len(s_sorted))
w = 0.22
ax.bar(x - 1.5*w, s_sorted["mean_overnight"]*100, w, label="overnight",
       color="#377eb8")
ax.bar(x - 0.5*w, s_sorted["mean_open_1h"]*100, w, label="open 1h",
       color="#e41a1c")
ax.bar(x + 0.5*w, s_sorted["mean_mid_day"]*100, w, label="mid-day",
       color="#4daf4a")
ax.bar(x + 1.5*w, s_sorted["mean_full_day"]*100, w, label="full day",
       color="#984ea3")
ax.axhline(0, color="gray", lw=0.5)
ax.set_xticks(x)
ax.set_xticklabels([f"{t}\n(n={n})" for t, n in zip(s_sorted["tercile"], s_sorted["n"])])
ax.set_ylabel("Mean log return (%)")
ax.set_xlabel("EPS surprise tercile")
ax.set_title("Returns by EPS-surprise tercile\n"
             "Pattern: mid surprises under-react, not high surprises")
ax.legend(fontsize=9)
fig.tight_layout()
fig.savefig(os.path.join(FIG, "fig6_surprise.png"), dpi=160)
plt.close(fig)

print("Saved figures:")
for f in sorted(os.listdir(FIG)):
    if f.startswith("fig"):
        print("  ", f)
