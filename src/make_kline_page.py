"""Generate a single self-contained HTML page with 24 candlestick charts,
one per NVDA post-earnings trading day. Mobile-friendly, hover for OHLCV.

Design:
- Uses Plotly.js from CDN (no local install needed)
- Each chart: candlestick (OHLC) on top + volume bars below
- Responsive grid: 1 col on phone, 2 on tablet, 3 on desktop
- X-axis: minute-of-day (09:30 - 16:00 ET)
- Hover shows time + O/H/L/C + volume
"""
import os
import json
import pandas as pd
import numpy as np

HERE = os.path.dirname(__file__)
ROOT = os.path.abspath(os.path.join(HERE, ".."))
DATA = os.path.join(ROOT, "data")
OUT_DIR = os.path.join(ROOT, "paper")
os.makedirs(OUT_DIR, exist_ok=True)


def load_minute():
    p = os.path.join(DATA, "exported_1m_csv", "NVDA_1m.csv")
    df = pd.read_csv(p, parse_dates=["datetime_utc"])
    df["dt_et"] = (df["datetime_utc"].dt.tz_localize("UTC")
                    .dt.tz_convert("US/Eastern").dt.tz_localize(None))
    df["date"] = df["dt_et"].dt.date
    df["hm"] = df["dt_et"].dt.strftime("%H:%M")
    df = df[(df["hm"] >= "09:30") & (df["hm"] < "16:00")].copy()
    return df[df["volume"] > 0].reset_index(drop=True)


def main():
    mins = load_minute()
    events = pd.read_csv(os.path.join(DATA, "nvda_earnings.csv"),
                          parse_dates=["earnings_date"])
    trading_dates = np.array(sorted(mins["date"].unique()))

    charts = []
    for _, ev in events.iterrows():
        ed = ev["earnings_date"].date()
        mask = trading_dates > ed
        if not mask.any():
            continue
        nd = trading_dates[mask][0]
        mask_prev = trading_dates <= ed
        if not mask_prev.any():
            continue
        pd_day = trading_dates[mask_prev][-1]
        pb = mins[mins["date"] == pd_day]
        nb = mins[mins["date"] == nd].sort_values("dt_et").reset_index(drop=True)
        if len(pb) < 10 or len(nb) < 300:
            continue
        P_prev = float(pb.iloc[-1]["close"])
        P_open = float(nb.iloc[0]["close"])
        P_close = float(nb.iloc[-1]["close"])

        overnight_pct = (P_open / P_prev - 1) * 100
        day_pct = (P_close / P_open - 1) * 100
        full_pct = (P_close / P_prev - 1) * 100

        charts.append({
            "quarter": ev["fiscal_quarter"],
            "earnings_date": str(ed),
            "next_day": str(nd),
            "P_prev": round(P_prev, 2),
            "overnight_pct": round(overnight_pct, 2),
            "day_pct": round(day_pct, 2),
            "full_pct": round(full_pct, 2),
            "eps_actual": float(ev["actual_eps"]),
            "eps_cons": float(ev["consensus_eps"]),
            "rev_actual": float(ev["actual_revenue_bn"]),
            "rev_cons": float(ev["consensus_revenue_bn"]),
            "times": nb["hm"].tolist(),
            "open":  [round(float(x), 3) for x in nb["open"].values],
            "high":  [round(float(x), 3) for x in nb["high"].values],
            "low":   [round(float(x), 3) for x in nb["low"].values],
            "close": [round(float(x), 3) for x in nb["close"].values],
            "volume": [int(x) for x in nb["volume"].values],
        })

    print(f"Built {len(charts)} charts")

    # -------- Assemble HTML --------
    html = r"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>NVDA 24次财报日分钟K线 (2020-2026)</title>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<style>
  * { box-sizing: border-box; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, "PingFang SC",
                 "Microsoft YaHei", Helvetica, Arial, sans-serif;
    margin: 0; padding: 10px;
    background: #f5f5f7;
    color: #222;
  }
  header {
    text-align: center;
    padding: 12px 10px 20px;
    background: linear-gradient(135deg, #1a237e, #3949ab);
    color: white;
    border-radius: 12px;
    margin-bottom: 15px;
  }
  header h1 {
    margin: 0 0 6px 0;
    font-size: 20px;
  }
  header p {
    margin: 4px 0 0 0;
    font-size: 13px;
    opacity: 0.9;
  }
  .summary {
    max-width: 900px;
    margin: 0 auto 18px;
    background: white;
    padding: 12px 16px;
    border-radius: 10px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
    font-size: 13px;
    line-height: 1.55;
  }
  .grid {
    display: grid;
    grid-template-columns: 1fr;
    gap: 14px;
  }
  @media (min-width: 700px) {
    .grid { grid-template-columns: repeat(2, 1fr); }
  }
  @media (min-width: 1100px) {
    .grid { grid-template-columns: repeat(3, 1fr); }
  }
  .card {
    background: white;
    border-radius: 10px;
    padding: 10px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
  }
  .meta {
    font-size: 12px;
    margin-bottom: 6px;
    line-height: 1.5;
  }
  .meta .q {
    font-weight: 600;
    font-size: 14px;
    color: #1a237e;
  }
  .meta .date { color: #555; }
  .pill {
    display: inline-block;
    padding: 2px 7px;
    border-radius: 4px;
    font-size: 11px;
    margin-right: 4px;
    font-weight: 600;
  }
  .pos { background: #e8f5e9; color: #2e7d32; }
  .neg { background: #ffebee; color: #c62828; }
  .zero { background: #eceff1; color: #546e7a; }
  .chart { width: 100%; height: 360px; }
  footer {
    text-align: center;
    font-size: 11px;
    color: #888;
    padding: 20px 10px;
  }
</style>
</head>
<body>
<header>
  <h1>NVDA 24 次财报日分钟 K 线</h1>
  <p>2020 Q1 – 2026 Q4 · 每个卡片 = 财报发布之后的第一个交易日 · 点/滑过可看 OHLC + 成交量</p>
</header>

<div class="summary">
  <b>怎么看：</b> 每张图上方是 1 分钟 K 线（红涨绿跌），下方浅灰柱是每分钟成交量。
  横轴是美东时间 09:30 到 16:00。<b>蓝色虚线</b>是前日收盘价，
  反映隔夜跳空；<b>紫色虚线</b>是 10:30（开盘 1 小时结束）。
  卡片头部的三个彩色 pill 依次是：<b>隔夜</b>、<b>开盘后全天</b>、<b>财报日总涨跌</b>。
</div>

<div class="grid" id="grid"></div>

<footer>
  数据源：1-min OHLCV · MBA 课程论文《数据分析与决策 II》NVDA 散户行为研究 side notes
</footer>

<script>
const CHARTS = __CHARTS_JSON__;

function pillClass(v) {
  if (v > 0.05) return "pos";
  if (v < -0.05) return "neg";
  return "zero";
}
function signed(v) { return (v >= 0 ? "+" : "") + v.toFixed(2) + "%"; }

const grid = document.getElementById("grid");

CHARTS.forEach((c, idx) => {
  const card = document.createElement("div");
  card.className = "card";

  // Meta header
  const meta = document.createElement("div");
  meta.className = "meta";
  meta.innerHTML = `
    <div>
      <span class="q">${c.quarter}</span>
      <span class="date">  财报 ${c.earnings_date} → 交易日 ${c.next_day}</span>
    </div>
    <div style="margin-top:3px">
      <span class="pill ${pillClass(c.overnight_pct)}">隔夜 ${signed(c.overnight_pct)}</span>
      <span class="pill ${pillClass(c.day_pct)}">日内 ${signed(c.day_pct)}</span>
      <span class="pill ${pillClass(c.full_pct)}">合计 ${signed(c.full_pct)}</span>
      <span style="font-size:11px; color:#888; margin-left:4px">
        EPS ${c.eps_actual} (预期 ${c.eps_cons}) · 营收 ${c.rev_actual}B (预期 ${c.rev_cons}B)
      </span>
    </div>
  `;
  card.appendChild(meta);

  // Chart container
  const chartDiv = document.createElement("div");
  chartDiv.className = "chart";
  chartDiv.id = "chart_" + idx;
  card.appendChild(chartDiv);

  grid.appendChild(card);

  // Build Plotly traces
  const candle = {
    x: c.times,
    open: c.open, high: c.high, low: c.low, close: c.close,
    type: "candlestick",
    name: "价格",
    increasing: { line: { color: "#d32f2f" }, fillcolor: "#ef5350" },
    decreasing: { line: { color: "#388e3c" }, fillcolor: "#66bb6a" },
    xaxis: "x", yaxis: "y",
    hovertemplate:
      "时间 %{x} ET<br>" +
      "开 $%{open:.2f}<br>" +
      "高 $%{high:.2f}<br>" +
      "低 $%{low:.2f}<br>" +
      "收 $%{close:.2f}<extra></extra>",
  };

  const volColors = c.close.map((cl, i) => cl >= c.open[i] ? "#ef9a9a" : "#a5d6a7");
  const volume = {
    x: c.times,
    y: c.volume.map(v => v / 1e6),
    type: "bar",
    name: "成交量 (M)",
    marker: { color: volColors, line: { width: 0 } },
    xaxis: "x", yaxis: "y2",
    hovertemplate: "%{x} ET<br>成交量 %{y:.2f}M 股<extra></extra>",
  };

  // Annotations: prev-close reference + 10:30 marker
  const shapes = [
    {
      type: "line", xref: "x", yref: "y",
      x0: c.times[0], x1: c.times[c.times.length - 1],
      y0: c.P_prev, y1: c.P_prev,
      line: { color: "#1976d2", dash: "dash", width: 1.2 },
    },
    {
      type: "line", xref: "x", yref: "paper",
      x0: "10:30", x1: "10:30", y0: 0, y1: 1,
      line: { color: "#8e24aa", dash: "dot", width: 1 },
    },
  ];

  const layout = {
    margin: { l: 48, r: 15, t: 8, b: 28 },
    showlegend: false,
    xaxis: {
      rangeslider: { visible: false },
      type: "category",
      tickmode: "array",
      tickvals: ["09:30", "10:30", "12:00", "13:30", "15:00", "15:59"],
      tickfont: { size: 10 },
    },
    yaxis: {
      domain: [0.28, 1],
      title: { text: "价格 (US$)", font: { size: 11 } },
      tickfont: { size: 10 },
      side: "left",
    },
    yaxis2: {
      domain: [0, 0.22],
      title: { text: "Vol (M)", font: { size: 10 } },
      tickfont: { size: 9 },
      side: "left",
    },
    shapes: shapes,
    annotations: [
      {
        x: c.times[0], y: c.P_prev, xref: "x", yref: "y",
        text: "前收 $" + c.P_prev.toFixed(2),
        showarrow: false, font: { size: 9, color: "#1976d2" },
        xanchor: "left", yanchor: "bottom",
        bgcolor: "rgba(255,255,255,0.7)",
      },
    ],
    dragmode: "pan",
  };

  Plotly.newPlot(chartDiv.id, [candle, volume], layout,
    { responsive: true, displayModeBar: false, scrollZoom: true });
});
</script>
</body>
</html>
"""

    html = html.replace("__CHARTS_JSON__", json.dumps(charts, ensure_ascii=False))

    out = os.path.join(OUT_DIR, "NVDA_24财报日K线.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    sz = os.path.getsize(out) / 1024
    print(f"Saved: {out}  ({sz:.0f} KB)")


if __name__ == "__main__":
    main()
