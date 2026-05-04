"""Plot the actual minute-level price path of NVDA on 2024-02-22
(the day after FY24Q4 earnings released on 2024-02-21), to visually
demonstrate that the opening hour does NOT overshoot and revert."""
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(__file__)
ROOT = os.path.abspath(os.path.join(HERE, ".."))
DATA = os.path.join(ROOT, "data")
FIG = os.path.join(ROOT, "figures")
os.makedirs(FIG, exist_ok=True)

# Read NVDA 1-min data
p = os.path.join(DATA, "exported_1m_csv", "NVDA_1m.csv")
df = pd.read_csv(p, parse_dates=["datetime_utc"])
df["dt_et"] = (df["datetime_utc"].dt.tz_localize("UTC")
               .dt.tz_convert("US/Eastern").dt.tz_localize(None))
df["date"] = df["dt_et"].dt.date

# Earnings release: 2024-02-21 after close; next trading day = 2024-02-22
event_day = pd.Timestamp("2024-02-22").date()
prev_day = pd.Timestamp("2024-02-21").date()

prev_bars = df[df["date"] == prev_day].sort_values("dt_et")
next_bars = df[df["date"] == event_day].sort_values("dt_et").reset_index(drop=True)

# Time-of-day filter for regular session
next_bars["hm"] = next_bars["dt_et"].dt.strftime("%H:%M")
rth = next_bars[(next_bars["hm"] >= "09:30") & (next_bars["hm"] < "16:00")].copy()

p_prev_close = float(prev_bars.iloc[-1]["close"])
p_0930 = float(rth.iloc[0]["close"])

# Minute index from 0 to 389
rth["m"] = np.arange(len(rth))
rth["price"] = rth["close"]

# Identify key anchor times
anchors = {
    "09:30 open": 0,
    "10:30 (end open-1h)": 60,
    "12:00 lunch": 150,
    "16:00 close": 389,
}

fig, axes = plt.subplots(2, 1, figsize=(12, 8.5),
                         gridspec_kw={"height_ratios": [3, 1]})

# ---- top: minute price ----
ax = axes[0]
ax.plot(rth["m"], rth["price"], color="#333", lw=1.3)
ax.axhline(p_prev_close, color="#888", ls=":", lw=1,
           label=f"Prev close  ${p_prev_close:.2f}  (2024-02-21)")
ax.axhline(p_0930, color="#e41a1c", ls="--", lw=1,
           label=f"09:30 open  ${p_0930:.2f}  (+{(p_0930/p_prev_close-1)*100:.1f}% overnight jump)")

# Mark the open-hour window
ax.axvspan(0, 60, color="#e41a1c", alpha=0.08,
           label="09:30-10:30 open hour")

for name, m in anchors.items():
    if m < len(rth):
        ax.annotate(name, xy=(m, rth.iloc[m]["price"]),
                    xytext=(m + 5, rth.iloc[m]["price"] + 2),
                    fontsize=9, color="#333",
                    arrowprops=dict(arrowstyle="->", color="gray", lw=0.5))
        ax.plot(m, rth.iloc[m]["price"], "o", color="black", ms=6)

# Compute the range inside the open hour
open_1h = rth.iloc[:61]
ax.axhline(open_1h["price"].max(), color="#4daf4a", ls=":", lw=0.8, alpha=0.6)
ax.axhline(open_1h["price"].min(), color="#984ea3", ls=":", lw=0.8, alpha=0.6)

ax.set_xlabel("Minutes after 09:30 open")
ax.set_ylabel("NVDA price (US$)")
ax.set_title(f"NVDA price path on 2024-02-22 (post-earnings day)\n"
             f"Overnight jump: ${p_prev_close:.2f} -> ${p_0930:.2f} (+{(p_0930/p_prev_close-1)*100:.1f}%)\n"
             f"Open-1h range only: [{open_1h['price'].min():.2f}, {open_1h['price'].max():.2f}]  "
             f"= {(open_1h['price'].max()/open_1h['price'].min()-1)*100:.1f}% width")
ax.legend(loc="lower right", fontsize=9)
ax.grid(alpha=0.25)

# ---- bottom: minute volume ----
ax2 = axes[1]
ax2.bar(rth["m"], rth["volume"] / 1e6, color="#888", alpha=0.75, width=1.0)
ax2.axvspan(0, 60, color="#e41a1c", alpha=0.08)
ax2.set_xlabel("Minutes after 09:30 open")
ax2.set_ylabel("Volume (M shares / minute)")
ax2.set_title("Per-minute volume — note the open-hour spike is the retail 'wave'")
ax2.grid(alpha=0.25)

plt.tight_layout()
out = os.path.join(FIG, "fig_2024Q4_intraday_detail.png")
plt.savefig(out, dpi=170, bbox_inches="tight")
plt.close(fig)
print("Saved:", out)

# Print numerical summary for the narrative
print(f"\n--- 2024-02-22 NVDA price timeline ---")
print(f"Prev close (2024-02-21): ${p_prev_close:.2f}")
print(f"09:30 open:              ${p_0930:.2f}  (overnight jump +{(p_0930/p_prev_close-1)*100:.2f}%)")
print(f"10:30 (end of open hr):  ${rth.iloc[60]['close']:.2f}  "
      f"({(rth.iloc[60]['close']/p_0930 - 1) * 100:+.2f}% open 1h return)")
print(f"16:00 close:             ${rth.iloc[-1]['close']:.2f}  "
      f"({(rth.iloc[-1]['close']/rth.iloc[60]['close'] - 1) * 100:+.2f}% mid-day return)")
print(f"Open 1h range:           [{open_1h['price'].min():.2f}, "
      f"{open_1h['price'].max():.2f}]  "
      f"= {(open_1h['price'].max()/open_1h['price'].min()-1)*100:.2f}%")
