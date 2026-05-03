"""
Streamlit dashboard: NVDA earnings overshoot-reversal null result.

    streamlit run src/app.py

Tabs:
  1. Overview — story + headline null numbers + window means
  2. Regression — core regression table with 95% CI visuals
  3. Scatter — open_1h vs mid_day (and placebo comparison)
  4. Intraday path — average price path across 24 events
  5. Per-event — event-level decomposition of overnight / open / mid
  6. Raw data
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

ROOT = os.path.abspath(os.path.join(HERE, ".."))
RES = os.path.join(ROOT, "results")

st.set_page_config(page_title="NVDA 有限注意力失效", layout="wide")

# ------------------------------------------------------------------ sidebar
st.sidebar.title("NVDA 有限注意力")
st.sidebar.markdown(
    "清华-Cornell MBA · 数据分析与决策 II\n\n"
    "**研究问题**：经典的「过冲 + 反转」模式在 2020 年代的 NVDA 上还成立吗？"
)


@st.cache_data
def _load():
    evt = pd.read_csv(os.path.join(RES, "event_level.csv"),
                      parse_dates=["earnings_date", "next_day"])
    placebo = pd.read_csv(os.path.join(RES, "placebo_days.csv"))
    reg = pd.read_csv(os.path.join(RES, "regressions.csv"))
    surprise = pd.read_csv(os.path.join(RES, "surprise_split.csv"))
    path = pd.read_csv(os.path.join(RES, "intraday_path_avg.csv"))
    summary = json.load(open(os.path.join(RES, "summary.json")))
    return evt, placebo, reg, surprise, path, summary


evt, placebo, reg, surprise, path, summary = _load()

# ------------------------------------------------------------------ tabs
tabs = st.tabs([
    "① 概览",
    "② 核心回归",
    "③ 散点图",
    "④ 日内价格路径",
    "⑤ 单事件分解",
    "⑥ 原始数据",
])

# ---- Tab 1 ----
with tabs[0]:
    st.title("有限注意力假说在 NVIDIA 上失效了吗？")
    st.markdown(
        """本研究使用 2020-05 至 2026-02 共 **24 次 NVDA 财报**的 1 分钟级数据，
        检验经典的「过冲 + 反转」模式是否仍然存在。

        **关键假说**：在有限注意力假说下，财报次日 09:30–10:30 的开盘 1 小时收益
        应显著**负**预测 10:30–16:00 的盘中收益。

        **实证结果**：零关系。β₁ ≈ 0，t 值不显著，整体 R² < 0.01。

        **机制解释**：盘前交易、社交媒体、Robinhood 式 App 三项市场结构变化，
        使散户的信息时延从小时级降到了秒级。85% 的财报冲击在盘前已被完成定价。
        """
    )

    c1, c2, c3, c4 = st.columns(4)
    b_open = summary["MAIN_beta_open_1h"]
    b_over = summary["MAIN_beta_overnight"]
    c1.metric("β₁ on r_open_1h", f"{b_open['coef']:+.3f}",
              f"t={b_open['t']:+.2f}")
    c2.metric("β₂ on r_overnight", f"{b_over['coef']:+.3f}",
              f"t={b_over['t']:+.2f}")
    c3.metric("主回归 R²", f"{summary['MAIN_R2']:.3f}")
    c4.metric("财报事件数", f"{summary['n_events']}")

    # Window means bar chart
    st.subheader("三窗口平均收益（财报日 vs 非财报日）")
    windows = ["overnight", "open_1h", "mid_day"]
    fig = go.Figure()
    means_e = [evt[f"r_{w}"].mean() * 100 for w in windows]
    ses_e = [evt[f"r_{w}"].std() / np.sqrt(len(evt)) * 100 for w in windows]
    means_p = [placebo[f"r_{w}"].mean() * 100 for w in windows]
    ses_p = [placebo[f"r_{w}"].std() / np.sqrt(len(placebo)) * 100 for w in windows]
    fig.add_trace(go.Bar(
        x=windows, y=means_e,
        error_y=dict(type="data", array=np.array(ses_e) * 1.96),
        name=f"Earnings (n={len(evt)})", marker_color="#e41a1c",
        text=[f"{v:+.2f}%" for v in means_e], textposition="outside",
    ))
    fig.add_trace(go.Bar(
        x=windows, y=means_p,
        error_y=dict(type="data", array=np.array(ses_p) * 1.96),
        name=f"Placebo (n={len(placebo)})", marker_color="#377eb8",
        text=[f"{v:+.2f}%" for v in means_p], textposition="outside",
    ))
    fig.update_layout(barmode="group", height=440,
                      yaxis_title="Mean log-return (%)",
                      xaxis_title="Window")
    st.plotly_chart(fig, use_container_width=True)

# ---- Tab 2 Regression ----
with tabs[1]:
    st.header("核心回归")
    st.markdown(
        r"""$r_{mid\_day,i}=\alpha+\beta_1 r_{open\_1h,i}+\beta_2 r_{overnight,i}+\epsilon_i$

        有限注意力假说预测：$\beta_1$ 显著 **为负**（开盘过冲在盘中被反转）。"""
    )

    which = st.radio("选择回归设置",
                     ["main", "uni_open_1h", "uni_overnight", "win_30m", "placebo"],
                     horizontal=True)
    sub = reg[reg["label"] == which]
    st.dataframe(
        sub.style.format({"coef": "{:+.4f}", "se": "{:.4f}",
                          "t": "{:+.2f}", "p": "{:.3f}",
                          "r2": "{:.3f}"}),
        use_container_width=True,
    )

    # Visual forest plot for main + placebo
    st.subheader("主回归 vs Placebo 对比")
    fig = go.Figure()
    for lbl, color in [("main", "#e41a1c"), ("placebo", "#377eb8")]:
        sub2 = reg[(reg["label"] == lbl) & (reg["variable"] != "const")]
        for _, r in sub2.iterrows():
            fig.add_trace(go.Scatter(
                x=[r["coef"]], y=[f"{lbl} / {r['variable']}"],
                error_x=dict(type="data", array=[1.96 * r["se"]]),
                mode="markers", marker=dict(size=12, color=color),
                showlegend=False,
            ))
    fig.add_vline(x=0, line_color="gray", line_width=0.5)
    fig.update_layout(xaxis_title="Coef (95% CI)", height=380)
    st.plotly_chart(fig, use_container_width=True)

# ---- Tab 3 Scatter ----
with tabs[2]:
    st.header("开盘 1 小时收益 vs 盘中收益散点")
    col1, col2 = st.columns(2)
    for col, data, title, color in zip(
        [col1, col2], [evt, placebo],
        [f"财报日 (n={len(evt)})", f"Placebo 日 (n={len(placebo)})"],
        ["#e41a1c", "#377eb8"],
    ):
        x = data["r_open_1h"].values * 100
        y = data["r_mid_day"].values * 100
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=x, y=y, mode="markers",
                                 marker=dict(size=8, color=color, opacity=0.7)))
        if len(data) >= 3:
            b = np.polyfit(x, y, 1)
            xg = np.linspace(x.min(), x.max(), 40)
            fig.add_trace(go.Scatter(x=xg, y=b[0] * xg + b[1],
                                     mode="lines", line=dict(color="black", dash="dash"),
                                     name=f"slope = {b[0]:+.3f}"))
        fig.add_hline(y=0, line_color="gray", line_width=0.3)
        fig.add_vline(x=0, line_color="gray", line_width=0.3)
        fig.update_layout(xaxis_title="Open 1h ret (%)",
                          yaxis_title="Mid-day ret (%)",
                          title=title, height=430)
        col.plotly_chart(fig, use_container_width=True)

    st.subheader("隔夜收益 vs 全日收益（信息主要在盘前被吸收）")
    x = evt["r_overnight"].values * 100
    y = evt["r_full_day"].values * 100
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=x, y=y, mode="markers+text",
        marker=dict(size=10, color="#e41a1c", opacity=0.75),
        text=evt["fiscal_quarter"],
        textposition="top center", textfont=dict(size=9),
    ))
    b = np.polyfit(x, y, 1)
    xg = np.linspace(x.min(), x.max(), 40)
    fig.add_trace(go.Scatter(x=xg, y=b[0] * xg + b[1], mode="lines",
                             line=dict(color="black", dash="dash"),
                             name=f"slope = {b[0]:+.2f}  R²={np.corrcoef(x,y)[0,1]**2:.2f}"))
    fig.add_trace(go.Scatter(x=xg, y=xg, mode="lines",
                             line=dict(color="gray", width=0.8),
                             name="y = x"))
    fig.update_layout(xaxis_title="Overnight return (%)",
                      yaxis_title="Full-day return (%)", height=470)
    st.plotly_chart(fig, use_container_width=True)

# ---- Tab 4 Intraday path ----
with tabs[3]:
    st.header("日内平均价格路径（24 个财报事件平均）")
    st.markdown("横轴是次日 09:30 开盘后的分钟数，纵轴是相对开盘的 log 价格。")
    pa = path[(path["m"] >= 0) & (path["m"] <= 389)]
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=pa["m"], y=pa["mean"] * 100,
        mode="lines", line=dict(width=2.5, color="#984ea3"),
        name="Mean",
    ))
    fig.add_trace(go.Scatter(
        x=pa["m"], y=(pa["mean"] + 1.96 * pa["se"]) * 100,
        line=dict(width=0), showlegend=False, hoverinfo="skip",
    ))
    fig.add_trace(go.Scatter(
        x=pa["m"], y=(pa["mean"] - 1.96 * pa["se"]) * 100,
        fill="tonexty", fillcolor="rgba(152,78,163,0.2)",
        line=dict(width=0), name="95% CI",
    ))
    fig.add_hline(y=0, line_color="gray", line_width=0.4)
    for m, lbl in [(60, "10:30"), (180, "12:30"), (389, "16:00")]:
        fig.add_vline(x=m, line_color="gray", line_dash="dot", line_width=0.5,
                      annotation_text=lbl)
    fig.update_layout(xaxis_title="Minutes after open",
                      yaxis_title="Log price relative to 09:30 (%)",
                      height=480)
    st.plotly_chart(fig, use_container_width=True)

# ---- Tab 5 Per-event ----
with tabs[4]:
    st.header("每次财报的收益分解")
    d = evt.sort_values("earnings_date").reset_index(drop=True)
    fig = go.Figure()
    fig.add_trace(go.Bar(x=d["fiscal_quarter"],
                         y=d["r_overnight"] * 100, name="Overnight",
                         marker_color="#377eb8"))
    fig.add_trace(go.Bar(x=d["fiscal_quarter"],
                         y=d["r_open_1h"] * 100, name="Open 1h",
                         marker_color="#e41a1c"))
    fig.add_trace(go.Bar(x=d["fiscal_quarter"],
                         y=d["r_mid_day"] * 100, name="Mid-day",
                         marker_color="#4daf4a"))
    fig.update_layout(barmode="stack", height=500,
                      xaxis_title="Fiscal quarter",
                      yaxis_title="Log return (%)")
    st.plotly_chart(fig, use_container_width=True)

    st.dataframe(
        d[["earnings_date", "fiscal_quarter", "eps_surprise_pct",
           "r_overnight", "r_open_1h", "r_mid_day", "r_full_day"]]
        .style.format({"eps_surprise_pct": "{:+.1f}",
                       "r_overnight": "{:+.2%}", "r_open_1h": "{:+.2%}",
                       "r_mid_day": "{:+.2%}", "r_full_day": "{:+.2%}"}),
        use_container_width=True,
    )

# ---- Tab 6 Raw ----
with tabs[5]:
    st.header("原始数据浏览")
    which = st.radio("选择",
                     ["Event-level panel", "Placebo days", "Regressions",
                      "Surprise split", "Intraday path (avg)"])
    if which == "Event-level panel":
        st.dataframe(evt, use_container_width=True)
    elif which == "Placebo days":
        st.dataframe(placebo, use_container_width=True)
    elif which == "Regressions":
        st.dataframe(reg, use_container_width=True)
    elif which == "Surprise split":
        st.dataframe(surprise, use_container_width=True)
    else:
        st.dataframe(path, use_container_width=True)
