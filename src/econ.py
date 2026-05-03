"""
Lightweight econometrics helpers (numpy only, no statsmodels dependency).

Provides:
  ols(y, X)                     -> dict with beta, se (HC1), t, p, r2, n
  format_table(result, names)   -> pandas DataFrame coefficient table
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from math import erf, sqrt


def _p_from_t(t: float, df: int) -> float:
    """Two-sided p-value using normal approximation (fine for df>=30)."""
    # Normal CDF
    z = abs(t)
    # erfc-based two-sided p
    return 2 * (1 - 0.5 * (1 + erf(z / sqrt(2))))


def ols(y: np.ndarray, X: np.ndarray) -> dict:
    """OLS with HC1 heteroskedasticity-robust standard errors.

    X should already include a constant column if desired.
    """
    y = np.asarray(y, dtype=float).reshape(-1)
    X = np.asarray(X, dtype=float)
    n, k = X.shape
    XtX_inv = np.linalg.pinv(X.T @ X)
    beta = XtX_inv @ X.T @ y
    resid = y - X @ beta
    # HC1
    S = (X * resid[:, None]).T @ (X * resid[:, None])
    dof = max(n - k, 1)
    V_hc1 = (n / dof) * XtX_inv @ S @ XtX_inv
    se = np.sqrt(np.maximum(np.diag(V_hc1), 0))
    t = np.where(se > 0, beta / se, 0.0)
    p = np.array([_p_from_t(ti, dof) for ti in t])
    # R^2
    ss_res = float(np.sum(resid ** 2))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else float("nan")
    return dict(beta=beta, se=se, t=t, p=p, r2=r2, n=n, k=k, resid=resid)


def format_table(res: dict, names: list[str]) -> pd.DataFrame:
    stars = []
    for pv in res["p"]:
        if pv < 0.01:
            stars.append("***")
        elif pv < 0.05:
            stars.append("**")
        elif pv < 0.1:
            stars.append("*")
        else:
            stars.append("")
    return pd.DataFrame({
        "variable": names,
        "coef": res["beta"],
        "se(HC1)": res["se"],
        "t": res["t"],
        "p": res["p"],
        "sig": stars,
    })
