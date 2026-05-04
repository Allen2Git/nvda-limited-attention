"""Generate two WeChat-article cover figures.

Figure A: Title-hierarchy pyramid comparison (Investment Bank vs Big Tech)
- Visually shows that "VP" sits mid-stack in IB but near-top in Big Tech
- Uses English labels only (VM has no CJK fonts)

Figure B: NVDA 2024-02-22 intraday price path (for the story article cover)
- Shows the overnight jump + intraday continuation (no overshoot)
- Compact 16:9 composition for WeChat header image
"""
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Polygon

HERE = os.path.dirname(__file__)
ROOT = os.path.abspath(os.path.join(HERE, ".."))
DATA = os.path.join(ROOT, "data")
FIG = os.path.join(ROOT, "figures")
os.makedirs(FIG, exist_ok=True)


# =============================================================
# Figure A — Title Pyramid: Investment Bank vs Big Tech
# =============================================================
def draw_pyramid(ax, levels, title, palette, vp_index,
                 headcount_annotations):
    """Draw a trapezoidal pyramid. Each level is a trapezoid.
    levels: list of (label, sub_label) top-to-bottom
    vp_index: which level is 'VP' (0-indexed, highlighted)
    """
    n = len(levels)
    # Pyramid geometry (top narrow -> bottom wide)
    top_half_w = 0.9
    bot_half_w = 3.2
    level_h = 0.85
    total_h = n * level_h
    y0 = 0.5  # baseline

    for i, (label, sub) in enumerate(levels):
        # i=0 is top
        y_top = y0 + total_h - i * level_h
        y_bot = y_top - level_h
        # Linear interpolation of half-widths
        frac_top = (i) / n
        frac_bot = (i + 1) / n
        half_top = top_half_w + (bot_half_w - top_half_w) * frac_top
        half_bot = top_half_w + (bot_half_w - top_half_w) * frac_bot

        xs = [-half_top, half_top, half_bot, -half_bot]
        ys = [y_top, y_top, y_bot, y_bot]
        color = palette[i]
        edge = "#222"
        lw = 2.2 if i == vp_index else 0.9
        poly = Polygon(list(zip(xs, ys)), closed=True,
                       facecolor=color, edgecolor=edge, linewidth=lw,
                       alpha=0.92 if i == vp_index else 0.78)
        ax.add_patch(poly)

        y_mid = (y_top + y_bot) / 2
        # Label
        fw = "bold" if i == vp_index else "semibold"
        ax.text(0, y_mid + 0.08, label, ha="center", va="center",
                fontsize=12.5, fontweight=fw, color="#111")
        ax.text(0, y_mid - 0.19, sub, ha="center", va="center",
                fontsize=8.6, color="#333", style="italic")

        # Headcount annotation on the right
        hc = headcount_annotations[i]
        if hc:
            ax.annotate(hc,
                        xy=(half_bot + 0.1, y_mid),
                        xytext=(half_bot + 0.6, y_mid),
                        fontsize=8.5, color="#555", va="center",
                        arrowprops=dict(arrowstyle="-", color="#999",
                                        lw=0.6))

    # Arrow highlighting the VP level
    y_vp = y0 + total_h - vp_index * level_h - level_h / 2
    frac = (vp_index + 0.5) / n
    half_vp = top_half_w + (bot_half_w - top_half_w) * frac
    ax.annotate("VP HERE",
                xy=(-half_vp - 0.05, y_vp),
                xytext=(-half_vp - 1.7, y_vp),
                fontsize=10, fontweight="bold", color="#c0392b",
                va="center",
                arrowprops=dict(arrowstyle="->", color="#c0392b",
                                lw=1.8))

    ax.set_title(title, fontsize=14, fontweight="bold", pad=10)
    ax.set_xlim(-5.2, 5.2)
    ax.set_ylim(0, total_h + 1.0)
    ax.set_aspect("equal")
    ax.axis("off")


def make_pyramid_figure():
    fig, axes = plt.subplots(1, 2, figsize=(14, 8))

    # ---------- LEFT: Investment Bank ----------
    ib_levels = [
        ("Partner / Group Head", "Top of pyramid"),
        ("Managing Director (MD)", "REAL executive"),
        ("Executive Director (ED)", "Senior middle"),
        ("Vice President (VP)", "MIDDLE manager"),
        ("Associate", "3-6 yrs in"),
        ("Analyst", "New hire, 0-3 yrs"),
    ]
    # Color: top is deep gold (power), VP is red (highlight),
    # bottom fades to blue-grey
    ib_palette = [
        "#b8860b",   # Partner - dark goldenrod
        "#daa520",   # MD - goldenrod
        "#e8c468",   # ED - lighter gold
        "#e57373",   # VP - red (highlighted!)
        "#8fa9c4",   # Associate
        "#b8c9d9",   # Analyst
    ]
    ib_hc = [
        "~50 (globally)",
        "~2,500 (globally)",
        "~5,000",
        "~12,000  <-- BIG pool",
        "~15,000",
        "~20,000 new grads/yr",
    ]
    draw_pyramid(axes[0], ib_levels, "Investment Bank\n(Goldman Sachs,"
                                     " Morgan Stanley, JPM)",
                 ib_palette, vp_index=3, headcount_annotations=ib_hc)

    # ---------- RIGHT: Big Tech ----------
    tech_levels = [
        ("CEO", "1 person"),
        ("SVP / EVP", "C-suite"),
        ("Vice President (VP)", "REAL executive"),
        ("Senior Director / Director", "Upper mgmt"),
        ("Senior Manager / Manager", "Middle mgmt"),
        ("IC / Engineer / PM", "Individual contributor"),
    ]
    tech_palette = [
        "#4a148c",
        "#6a1b9a",
        "#e57373",   # VP highlight (same red)
        "#81c784",
        "#aed581",
        "#c5e1a5",
    ]
    tech_hc = [
        "1",
        "~20-40",
        "~100-300 (globally)",
        "~2,000",
        "~15,000",
        "~150,000+",
    ]
    draw_pyramid(axes[1], tech_levels, "Big Tech\n(Google, Meta,"
                                       " Microsoft)",
                 tech_palette, vp_index=2, headcount_annotations=tech_hc)

    # Super-title
    fig.suptitle("Same title, different worlds — where \"VP\" actually sits",
                 fontsize=16, fontweight="bold", y=0.99)

    # Footer comparison
    fig.text(0.5, 0.03,
             "Goldman Sachs VP  =  MIDDLE manager  (~12,000 of them)"
             "      vs      "
             "Google VP  =  top-tier executive  (~100-300 of them)",
             ha="center", fontsize=11, color="#c0392b",
             fontweight="bold")

    plt.tight_layout(rect=(0, 0.05, 1, 0.96))

    out = os.path.join(FIG, "cover_title_pyramid.png")
    fig.savefig(out, dpi=200, bbox_inches="tight",
                facecolor="white")
    plt.close(fig)
    print("Saved:", out)


# =============================================================
# Figure B — NVDA 2024-02-22 story cover
# =============================================================
def make_story_cover():
    # Load minute data
    p = os.path.join(DATA, "exported_1m_csv", "NVDA_1m.csv")
    df = pd.read_csv(p, parse_dates=["datetime_utc"])
    df["dt_et"] = (df["datetime_utc"].dt.tz_localize("UTC")
                    .dt.tz_convert("US/Eastern").dt.tz_localize(None))
    df["date"] = df["dt_et"].dt.date

    event_day = pd.Timestamp("2024-02-22").date()
    prev_day = pd.Timestamp("2024-02-21").date()

    prev_bars = df[df["date"] == prev_day].sort_values("dt_et")
    next_bars = df[df["date"] == event_day].sort_values(
        "dt_et").reset_index(drop=True)
    next_bars["hm"] = next_bars["dt_et"].dt.strftime("%H:%M")
    rth = next_bars[(next_bars["hm"] >= "09:30")
                     & (next_bars["hm"] < "16:00")].copy()

    p_prev_close = float(prev_bars.iloc[-1]["close"])
    p_0930 = float(rth.iloc[0]["close"])
    p_1030 = float(rth.iloc[60]["close"])
    p_close = float(rth.iloc[-1]["close"])

    rth = rth.reset_index(drop=True)
    rth["m"] = np.arange(len(rth))

    # Cover aspect: 16:9 wide for WeChat header
    fig, ax = plt.subplots(figsize=(14, 7))

    # --- build a phantom "timeline" spanning prev close (-60) to close (389)
    # so the overnight jump is visible
    x_prev = np.linspace(-60, -1, 60)
    y_prev = np.full_like(x_prev, p_prev_close)  # flat at prev close (visual)
    ax.plot(x_prev, y_prev, color="#999", lw=1.4, alpha=0.7)

    # Overnight gap (dashed)
    ax.plot([-1, 0], [p_prev_close, p_0930], color="#e41a1c",
            lw=2.2, ls="--", alpha=0.85)

    # Intraday path (solid)
    ax.plot(rth["m"], rth["close"], color="#1f2937", lw=1.7)

    # Shade the open-1h window
    ax.axvspan(0, 60, color="#e41a1c", alpha=0.08)

    # Key reference lines
    ax.axhline(p_prev_close, color="#888", lw=0.8, ls=":")
    ax.axhline(p_0930, color="#e41a1c", lw=0.8, ls=":", alpha=0.6)

    # Key points with big markers
    pts = [
        (-1, p_prev_close, "Feb 21\nclose\n$735.94", "#555"),
        (0, p_0930, f"09:30 open\n${p_0930:.2f}\n(+1.24% overnight)", "#e41a1c"),
        (60, p_1030, f"10:30\n${p_1030:.2f}\n(+4.47% open-1h)", "#2e7d32"),
        (389, p_close, f"16:00 close\n${p_close:.2f}\n(+0.80% mid-day)", "#1565c0"),
    ]
    for x, y, label, col in pts:
        ax.plot(x, y, "o", color=col, ms=11, markeredgecolor="white",
                mew=1.8, zorder=5)
        # Place text labels smartly
        xtext = x + 12
        ytext = y + 3
        if x > 300:
            xtext = x - 8
            ha = "right"
        else:
            ha = "left"
        ax.annotate(label, xy=(x, y), xytext=(xtext, ytext),
                    fontsize=10, color=col, fontweight="bold",
                    ha=ha, va="bottom",
                    bbox=dict(boxstyle="round,pad=0.35",
                              fc="white", ec=col, lw=1.2, alpha=0.95))

    # Big annotation in the middle
    ax.text(200, 755,
            "No \"overshoot-then-revert\" pattern\n"
            "price continues drifting up through the whole day",
            fontsize=13, fontweight="bold", color="#c0392b",
            ha="center", va="center",
            bbox=dict(boxstyle="round,pad=0.8", fc="#fff5f5",
                      ec="#c0392b", lw=1.3))

    # Labels
    ax.set_xlabel("Minutes (negative = Feb 21 after-hours proxy, "
                  "0 = Feb 22 09:30 ET open)", fontsize=10)
    ax.set_ylabel("NVDA price (US$)", fontsize=11)
    ax.set_title("A retail investor's 24 hours: NVIDIA Feb 22, 2024 "
                 "(post-earnings day)",
                 fontsize=16, fontweight="bold", pad=12)

    ax.set_xlim(-75, 410)
    ax.grid(alpha=0.25)

    # Watermark footer
    fig.text(0.99, 0.01,
             "Source: 1-min OHLC data  ·  MBA course paper side-notes",
             ha="right", fontsize=8, color="#999", style="italic")

    plt.tight_layout()
    out = os.path.join(FIG, "cover_story_feb22.png")
    fig.savefig(out, dpi=200, bbox_inches="tight",
                facecolor="white")
    plt.close(fig)
    print("Saved:", out)


if __name__ == "__main__":
    make_pyramid_figure()
    make_story_cover()
