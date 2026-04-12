"""
NEXUS Trading AI — Streamlit Demo Dashboard
Reads live data from: nexus_live_decisions.json, nexus_positions.json,
                       nexus_equity_curve.json, nexus_weights.json
"""
import json
import os
import time
from datetime import datetime
from pathlib import Path

import plotly.graph_objects as go
import plotly.express as px
import streamlit as st

# ─── Page Config ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="NEXUS Trading AI",
    page_icon="⬡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─── Custom CSS ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:wght@300;400;500;600&display=swap');

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
    background-color: #060a0f;
    color: #e2e8f0;
}

/* Header */
.nexus-header {
    display: flex;
    align-items: center;
    gap: 16px;
    padding: 28px 0 8px 0;
    border-bottom: 1px solid #1a2535;
    margin-bottom: 28px;
}
.nexus-logo {
    font-family: 'Space Mono', monospace;
    font-size: 2rem;
    font-weight: 700;
    color: #00d4ff;
    letter-spacing: -2px;
    line-height: 1;
}
.nexus-sub {
    font-size: 0.78rem;
    color: #4a6080;
    letter-spacing: 3px;
    text-transform: uppercase;
    font-weight: 500;
    margin-top: 4px;
}

/* Metric cards */
.metric-card {
    background: linear-gradient(135deg, #0d1520 0%, #0a1018 100%);
    border: 1px solid #1a2535;
    border-radius: 12px;
    padding: 20px 24px;
    position: relative;
    overflow: hidden;
}
.metric-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0;
    width: 3px; height: 100%;
    background: #00d4ff;
    border-radius: 3px 0 0 3px;
}
.metric-label {
    font-size: 0.72rem;
    color: #4a6080;
    letter-spacing: 2px;
    text-transform: uppercase;
    font-weight: 500;
    margin-bottom: 8px;
}
.metric-value {
    font-family: 'Space Mono', monospace;
    font-size: 1.6rem;
    font-weight: 700;
    color: #e2e8f0;
    line-height: 1;
}
.metric-value.positive { color: #00e676; }
.metric-value.negative { color: #ff4757; }
.metric-value.accent   { color: #00d4ff; }

/* Section headers */
.section-title {
    font-family: 'Space Mono', monospace;
    font-size: 0.7rem;
    color: #00d4ff;
    letter-spacing: 3px;
    text-transform: uppercase;
    margin-bottom: 14px;
    margin-top: 4px;
}

/* Agent cards */
.agent-card {
    background: #0d1520;
    border: 1px solid #1a2535;
    border-radius: 10px;
    padding: 16px;
    margin-bottom: 10px;
}
.agent-name {
    font-family: 'Space Mono', monospace;
    font-size: 0.8rem;
    color: #00d4ff;
    font-weight: 700;
    margin-bottom: 6px;
}
.badge {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 20px;
    font-size: 0.7rem;
    font-weight: 600;
    letter-spacing: 1px;
    text-transform: uppercase;
}
.badge-buy  { background: rgba(0,230,118,0.15); color: #00e676; border: 1px solid rgba(0,230,118,0.3); }
.badge-sell { background: rgba(255,71,87,0.15);  color: #ff4757; border: 1px solid rgba(255,71,87,0.3); }
.badge-hold { background: rgba(255,193,7,0.15);  color: #ffc107; border: 1px solid rgba(255,193,7,0.3); }

/* Status dot */
.status-live {
    display: inline-block;
    width: 8px; height: 8px;
    background: #00e676;
    border-radius: 50%;
    animation: pulse 2s infinite;
    margin-right: 6px;
    vertical-align: middle;
}
@keyframes pulse {
    0%,100% { opacity: 1; box-shadow: 0 0 0 0 rgba(0,230,118,0.4); }
    50%      { opacity: 0.8; box-shadow: 0 0 0 6px rgba(0,230,118,0); }
}

/* Consensus box */
.consensus-box {
    background: linear-gradient(135deg, #0d1520, #091018);
    border: 1px solid #1a2535;
    border-radius: 12px;
    padding: 24px;
    text-align: center;
}
.consensus-direction {
    font-family: 'Space Mono', monospace;
    font-size: 2.4rem;
    font-weight: 700;
    letter-spacing: -1px;
}
.dir-buy  { color: #00e676; }
.dir-sell { color: #ff4757; }
.dir-hold { color: #ffc107; }

/* Positions table */
.pos-row {
    background: #0d1520;
    border: 1px solid #1a2535;
    border-radius: 8px;
    padding: 14px 18px;
    margin-bottom: 8px;
    display: flex;
    justify-content: space-between;
    align-items: center;
}

/* Dividers */
hr.nexus-divider {
    border: none;
    border-top: 1px solid #1a2535;
    margin: 24px 0;
}

/* Plotly chart bg */
.js-plotly-plot .plotly .bg { fill: transparent !important; }

/* Streamlit overrides */
.stApp { background-color: #060a0f; }
div[data-testid="stVerticalBlock"] > div { background: transparent; }
.stMetric { background: transparent; }
header[data-testid="stHeader"] { background: transparent; }
</style>
""", unsafe_allow_html=True)


# ─── Data Loaders ────────────────────────────────────────────────────────────
def load_json(filename: str, default=None):
    try:
        with open(filename, "r") as f:
            return json.load(f)
    except Exception:
        return default


def load_live_decisions():
    return load_json("nexus_live_decisions.json", {})


def load_equity_curve():
    return load_json("nexus_equity_curve.json", [])


def load_weights():
    return load_json("nexus_weights.json", {})


def load_positions():
    return load_json("nexus_positions.json", {})


# ─── Helpers ─────────────────────────────────────────────────────────────────
def direction_badge(direction: str) -> str:
    d = direction.upper()
    cls = {"BUY": "badge-buy", "SELL": "badge-sell"}.get(d, "badge-hold")
    return f'<span class="badge {cls}">{d}</span>'


def color_val(val: float, fmt: str = "+.2f") -> str:
    cls = "positive" if val >= 0 else "negative"
    return f'<span class="metric-value {cls}">{val:{fmt}}</span>'


def conf_bar(conf: float) -> str:
    pct = int(conf * 100)
    color = "#00e676" if pct >= 60 else "#ffc107" if pct >= 30 else "#ff4757"
    return f"""
    <div style="background:#1a2535;border-radius:4px;height:6px;width:100%;margin-top:6px">
      <div style="background:{color};border-radius:4px;height:6px;width:{pct}%"></div>
    </div>
    <div style="font-size:0.7rem;color:#4a6080;margin-top:3px">{pct}% confidence</div>
    """


# ─── Header ──────────────────────────────────────────────────────────────────
st.markdown("""
<div class="nexus-header">
  <div>
    <div class="nexus-logo">⬡ NEXUS</div>
    <div class="nexus-sub">Multi-Agent Crypto Trading System</div>
  </div>
  <div style="margin-left:auto;font-size:0.75rem;color:#4a6080;font-family:'Space Mono',monospace">
    <span class="status-live"></span>LIVE ENGINE
  </div>
</div>
""", unsafe_allow_html=True)


# ─── Auto-refresh ─────────────────────────────────────────────────────────────
refresh_rate = st.sidebar.selectbox("Auto-refresh (seconds)", [10, 30, 60, 120], index=1)
st.sidebar.markdown("---")
st.sidebar.markdown("**Data Files**")
for f in ["nexus_live_decisions.json", "nexus_equity_curve.json", "nexus_weights.json", "nexus_positions.json"]:
    exists = "✅" if Path(f).exists() else "❌"
    st.sidebar.markdown(f"{exists} `{f}`")

# Load all data
decisions   = load_live_decisions()
equity_data = load_equity_curve()
weights     = load_weights()
positions   = load_positions()

# ─── Top KPI Row ─────────────────────────────────────────────────────────────
agents_list  = decisions.get("agent_decisions", [])
consensus    = decisions.get("consensus_decision", {})
c_direction  = consensus.get("direction", "—")
c_confidence = float(consensus.get("confidence", 0.0))
timestamp    = decisions.get("timestamp", "")
cycle_num    = decisions.get("latest_cycle", "—")

# Equity stats
equity_vals = [e.get("equity", e) if isinstance(e, dict) else e for e in equity_data]
portfolio_val = equity_vals[-1] if equity_vals else 0.0
start_val     = equity_vals[0]  if equity_vals else portfolio_val
pnl_pct       = ((portfolio_val - start_val) / start_val * 100) if start_val else 0.0

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    dir_color = {"BUY": "#00e676", "SELL": "#ff4757"}.get(c_direction.upper(), "#ffc107")
    st.markdown(f"""
    <div class="metric-card">
      <div class="metric-label">Consensus</div>
      <div class="metric-value" style="color:{dir_color};font-family:'Space Mono',monospace">{c_direction}</div>
    </div>""", unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class="metric-card">
      <div class="metric-label">Confidence</div>
      <div class="metric-value accent">{c_confidence:.1%}</div>
    </div>""", unsafe_allow_html=True)

with col3:
    pnl_cls = "positive" if pnl_pct >= 0 else "negative"
    st.markdown(f"""
    <div class="metric-card">
      <div class="metric-label">Total PnL</div>
      <div class="metric-value {pnl_cls}">{pnl_pct:+.2f}%</div>
    </div>""", unsafe_allow_html=True)

with col4:
    st.markdown(f"""
    <div class="metric-card">
      <div class="metric-label">Portfolio Value</div>
      <div class="metric-value">${portfolio_val:,.0f}</div>
    </div>""", unsafe_allow_html=True)

with col5:
    agent_count = len(agents_list)
    st.markdown(f"""
    <div class="metric-card">
      <div class="metric-label">Active Agents</div>
      <div class="metric-value accent">{agent_count}</div>
    </div>""", unsafe_allow_html=True)

st.markdown("<hr class='nexus-divider'>", unsafe_allow_html=True)

# ─── Main Content ─────────────────────────────────────────────────────────────
left, right = st.columns([3, 2], gap="large")

with left:
    # ── Equity Curve ────────────────────────────────────────────────────────
    st.markdown('<div class="section-title">Equity Curve</div>', unsafe_allow_html=True)

    if equity_vals and len(equity_vals) > 1:
        timestamps = []
        for i, e in enumerate(equity_data):
            if isinstance(e, dict) and "timestamp" in e:
                try:
                    timestamps.append(datetime.fromtimestamp(e["timestamp"]))
                except Exception:
                    timestamps.append(i)
            else:
                timestamps.append(i)

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=timestamps,
            y=equity_vals,
            mode="lines",
            line=dict(color="#00d4ff", width=2),
            fill="tozeroy",
            fillcolor="rgba(0,212,255,0.06)",
            name="Portfolio Value",
            hovertemplate="$%{y:,.2f}<extra></extra>",
        ))
        fig.update_layout(
            height=280,
            margin=dict(l=0, r=0, t=8, b=0),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(13,21,32,0.5)",
            font=dict(family="Space Mono", color="#4a6080", size=10),
            xaxis=dict(showgrid=False, showline=False, color="#4a6080"),
            yaxis=dict(showgrid=True, gridcolor="#1a2535", gridwidth=1, color="#4a6080", tickprefix="$"),
            showlegend=False,
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    else:
        st.markdown("""
        <div style="background:#0d1520;border:1px dashed #1a2535;border-radius:10px;
                    padding:48px;text-align:center;color:#4a6080;font-size:0.8rem;">
          No equity curve data yet — start the trading engine to populate this chart.
        </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Agent Weight Bar Chart ───────────────────────────────────────────────
    st.markdown('<div class="section-title">Agent Weights</div>', unsafe_allow_html=True)

    if weights:
        agent_ids = list(weights.keys())
        w_vals    = [float(weights[a]) if isinstance(weights[a], (int, float))
                     else float(weights[a].get("weight", 1.0)) if isinstance(weights[a], dict)
                     else 1.0 for a in agent_ids]
        colors = ["#00d4ff" if w >= max(w_vals) else "#1a4060" for w in w_vals]
        fig2 = go.Figure(go.Bar(
            x=w_vals, y=agent_ids,
            orientation="h",
            marker_color=colors,
            hovertemplate="%{y}: %{x:.3f}<extra></extra>",
        ))
        fig2.update_layout(
            height=max(160, len(agent_ids) * 36),
            margin=dict(l=0, r=0, t=4, b=0),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(13,21,32,0.5)",
            font=dict(family="Space Mono", color="#4a6080", size=10),
            xaxis=dict(showgrid=True, gridcolor="#1a2535", color="#4a6080"),
            yaxis=dict(showgrid=False, color="#8090a0"),
            showlegend=False,
        )
        st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})
    else:
        st.markdown("""
        <div style="background:#0d1520;border:1px dashed #1a2535;border-radius:10px;
                    padding:24px;text-align:center;color:#4a6080;font-size:0.8rem;">
          No weight data yet.
        </div>""", unsafe_allow_html=True)


with right:
    # ── Consensus Decision ───────────────────────────────────────────────────
    st.markdown('<div class="section-title">Current Decision</div>', unsafe_allow_html=True)
    dir_cls = {"BUY": "dir-buy", "SELL": "dir-sell"}.get(c_direction.upper(), "dir-hold")
    conf_pct = int(c_confidence * 100)
    conf_color = "#00e676" if conf_pct >= 60 else "#ffc107" if conf_pct >= 30 else "#ff4757"
    ts_display = timestamp[:19].replace("T", " ") if timestamp else "—"

    st.markdown(f"""
    <div class="consensus-box">
      <div style="font-size:0.7rem;color:#4a6080;letter-spacing:2px;text-transform:uppercase;margin-bottom:12px">
        Cycle #{cycle_num}
      </div>
      <div class="consensus-direction {dir_cls}">{c_direction}</div>
      <div style="margin:16px 0 8px 0">
        <div style="background:#1a2535;border-radius:6px;height:8px;width:100%">
          <div style="background:{conf_color};border-radius:6px;height:8px;width:{conf_pct}%;
                      transition:width 0.5s ease"></div>
        </div>
      </div>
      <div style="font-family:'Space Mono',monospace;font-size:1.1rem;color:{conf_color};margin-bottom:4px">
        {conf_pct}% confidence
      </div>
      <div style="font-size:0.72rem;color:#4a6080;margin-top:10px">{ts_display}</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Agent Votes ──────────────────────────────────────────────────────────
    st.markdown('<div class="section-title">Agent Votes</div>', unsafe_allow_html=True)

    if agents_list:
        for agent in agents_list:
            a_id   = agent.get("agent_id", "unknown")
            a_dir  = agent.get("direction", "HOLD")
            a_conf = float(agent.get("confidence", 0))
            a_mult = float(agent.get("regime_multiplier", 1.0))
            badge  = direction_badge(a_dir)
            st.markdown(f"""
            <div class="agent-card">
              <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px">
                <div class="agent-name">{a_id}</div>
                {badge}
              </div>
              {conf_bar(a_conf)}
              <div style="font-size:0.68rem;color:#4a6080;margin-top:4px">
                regime ×{a_mult:.2f}
              </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="background:#0d1520;border:1px dashed #1a2535;border-radius:10px;
                    padding:32px;text-align:center;color:#4a6080;font-size:0.8rem;">
          No agent votes yet — engine not running.
        </div>""", unsafe_allow_html=True)

st.markdown("<hr class='nexus-divider'>", unsafe_allow_html=True)

# ─── Open Positions ───────────────────────────────────────────────────────────
st.markdown('<div class="section-title">Open Positions</div>', unsafe_allow_html=True)

pos_list = decisions.get("positions", [])
if not pos_list and isinstance(positions, dict):
    pos_list = positions.get("open_positions", [])
if not pos_list and isinstance(positions, list):
    pos_list = positions

if pos_list:
    cols = st.columns(len(pos_list) if len(pos_list) <= 4 else 4)
    for i, pos in enumerate(pos_list[:4]):
        direction   = pos.get("direction", "—")
        entry       = float(pos.get("entry_price", 0))
        current     = float(pos.get("current_price", 0))
        upnl_pct    = float(pos.get("unrealised_pnl_pct", 0))
        size        = float(pos.get("size", pos.get("size_usd", 0)))
        dir_color   = "#00e676" if direction == "BUY" else "#ff4757"
        pnl_color   = "#00e676" if upnl_pct >= 0 else "#ff4757"
        with cols[i % 4]:
            st.markdown(f"""
            <div class="metric-card" style="border-left-color:{dir_color}">
              <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">
                <span style="font-family:'Space Mono',monospace;font-size:0.75rem;color:{dir_color};font-weight:700">{direction}</span>
                <span style="font-family:'Space Mono',monospace;font-size:0.7rem;color:#4a6080">${size:,.0f}</span>
              </div>
              <div style="font-size:0.7rem;color:#4a6080;margin-bottom:2px">Entry</div>
              <div style="font-family:'Space Mono',monospace;font-size:0.9rem;color:#e2e8f0">${entry:,.2f}</div>
              <div style="font-size:0.7rem;color:#4a6080;margin-top:8px;margin-bottom:2px">Unrealised PnL</div>
              <div style="font-family:'Space Mono',monospace;font-size:1.1rem;font-weight:700;color:{pnl_color}">{upnl_pct:+.2f}%</div>
            </div>
            """, unsafe_allow_html=True)
else:
    st.markdown("""
    <div style="background:#0d1520;border:1px dashed #1a2535;border-radius:10px;
                padding:28px;text-align:center;color:#4a6080;font-size:0.8rem;">
      No open positions.
    </div>""", unsafe_allow_html=True)

# ─── Footer ───────────────────────────────────────────────────────────────────
st.markdown(f"""
<div style="margin-top:40px;padding-top:16px;border-top:1px solid #1a2535;
            display:flex;justify-content:space-between;align-items:center;
            font-size:0.68rem;color:#2a3a50;font-family:'Space Mono',monospace;">
  <span>NEXUS TRADING AI</span>
  <span>PRISM · KRAKEN · ERC-8004</span>
  <span>Auto-refresh: {refresh_rate}s</span>
</div>
""", unsafe_allow_html=True)

# ─── Auto-refresh ─────────────────────────────────────────────────────────────
time.sleep(refresh_rate)
st.rerun()
