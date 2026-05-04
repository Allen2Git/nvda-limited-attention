"""Render a 3D scatter + OLS regression plane for the core paper regression.

Uses the 24 NVDA earnings events and fits
    r_mid_day = a + b1 * r_open_1h + b2 * r_overnight + eps
Then plots the scatter and the fitted plane in 3D, plus a 2D 'residual vs fit'
diagnostic panel, side-by-side for intuition.
"""
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401

HERE = os.path.dirname(__file__)
ROOT = os.path.abspath(os.path.join(HERE, ".."))
RES = os.path.join(ROOT, "results")
FIG = os.path.join(ROOT, "figures")
os.makedirs(FIG, exist_ok=True)

# ----- data --------------------------------------------------------
d = pd.read_csv(os.path.join(RES, "event_level.csv"),
                parse_dates=["earnings_date"])
x1 = d["r_open_1h"].values * 100         # percent
x2 = d["r_overnight"].values * 100
y = d["r_mid_day"].values * 100

# ----- OLS fit -----------------------------------------------------
X = np.column_stack([np.ones(len(d)), x1, x2])
beta, *_ = np.linalg.lstsq(X, y, rcond=None)
alpha, b1, b2 = beta
yhat = X @ beta
resid = y - yhat
ss_res = (resid ** 2).sum()
ss_tot = ((y - y.mean()) ** 2).sum()
r2 = 1 - ss_res / ss_tot

print(f"alpha = {alpha:+.3f}, b1 = {b1:+.3f}, b2 = {b2:+.3f}, R2 = {r2:.3f}")

# ----- mesh for the plane -----------------------------------------
pad = 0.5
x1_lo, x1_hi = x1.min() - pad, x1.max() + pad
x2_lo, x2_hi = x2.min() - pad, x2.max() + pad
xx1, xx2 = np.meshgrid(np.linspace(x1_lo, x1_hi, 30),
                        np.linspace(x2_lo, x2_hi, 30))
zz = alpha + b1 * xx1 + b2 * xx2

# ----- figure ------------------------------------------------------
fig = plt.figure(figsize=(14, 6))

# --- 3D panel ---
ax3d = fig.add_subplot(1, 2, 1, projection="3d")

# Regression plane (nearly flat -> translucent gray)
ax3d.plot_surface(xx1, xx2, zz, alpha=0.28, color="#888888",
                   edgecolor="#555555", linewidth=0.15, antialiased=True)

# Scatter: above-plane = red, below-plane = blue
above = resid > 0
ax3d.scatter(x1[above], x2[above], y[above], s=55, color="#e41a1c",
              edgecolor="white", linewidth=0.8, label="Above plane",
              depthshade=True)
ax3d.scatter(x1[~above], x2[~above], y[~above], s=55, color="#377eb8",
              edgecolor="white", linewidth=0.8, label="Below plane",
              depthshade=True)

# Vertical dashed segments from each point to the plane (shows residual)
for xi1, xi2, yi, yh in zip(x1, x2, y, yhat):
    ax3d.plot([xi1, xi1], [xi2, xi2], [yh, yi],
              color="gray", linestyle=":", linewidth=0.6, alpha=0.6)

ax3d.set_xlabel("r_open_1h (%)", labelpad=8)
ax3d.set_ylabel("r_overnight (%)", labelpad=8)
ax3d.set_zlabel("r_mid_day (%)", labelpad=8)
ax3d.set_title(f"Regression plane:  r_mid_day = {alpha:+.2f} {b1:+.3f} r_open_1h "
               f"{b2:+.3f} r_overnight\n"
               f"n = {len(d)} events,   R² = {r2:.3f}  (near zero -> plane is nearly flat)",
               fontsize=10, pad=10)
ax3d.view_init(elev=18, azim=-62)
ax3d.legend(loc="upper left", fontsize=8)

# --- 2D diagnostic panel: residual vs fitted ---
ax2d = fig.add_subplot(1, 2, 2)
ax2d.scatter(yhat, resid, s=55,
             c=np.where(above, "#e41a1c", "#377eb8"),
             edgecolor="white", linewidth=0.8)
ax2d.axhline(0, color="black", lw=0.8, ls="--")
ax2d.set_xlabel("Fitted value  y_hat  (predicted r_mid_day, %)")
ax2d.set_ylabel("Residual  e = y - y_hat  (%)")
ax2d.set_title("Residual vs fitted value  (how far each point deviates from the plane)",
               fontsize=10, pad=10)
ax2d.grid(alpha=0.25)

# Annotate a few extreme points
for idx in np.argsort(np.abs(resid))[-5:]:
    ax2d.annotate(d.iloc[idx]["fiscal_quarter"],
                  xy=(yhat[idx], resid[idx]),
                  xytext=(yhat[idx] + 0.15, resid[idx] + 0.15),
                  fontsize=8, color="#333")

fig.suptitle("Geometry of the core regression:  two predictors -> a plane in 3D -> plane is near flat -> beta_1 ~ beta_2 ~ 0",
             fontsize=11, y=0.98)

plt.tight_layout(rect=(0, 0, 1, 0.94))

# Use a CJK-capable font; fallback to DejaVu if 'Songti/STHeiti' not available
try:
    plt.rcParams["font.family"] = ["Arial Unicode MS", "STHeiti",
                                    "Songti SC", "Heiti SC",
                                    "Noto Sans CJK SC", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False
except Exception:
    pass

out = os.path.join(FIG, "fig7_regression_plane_3d.png")
fig.savefig(out, dpi=180, bbox_inches="tight")
plt.close(fig)
print("Saved:", out)
