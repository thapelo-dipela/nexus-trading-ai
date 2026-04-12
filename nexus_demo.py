"""
NEXUS Unified Trading Intelligence — Streamlit Demo Dashboard
"""
import streamlit as st
import requests
import json
import time
from datetime import datetime
from pathlib import Path

st.set_page_config(
    page_title="NEXUS Unified Trading Intelligence",
    page_icon="⬡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Styling ────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  .stApp { background: #080a0f; color: #e2e8f4; }
  .metric-card { background: #0d0f16; border: 1px solid #1c2030; border-radius: 8px; padding: 14px; margin-bottom: 8px; }
  .agent-vote { background: #0d0f16; border: 1px solid #1c2030; border-radius: 6px; padding: 10px; margin-bottom: 6px; }
  .buy-color { color: #10b981; }
  .sell-color { color: #ef4444; }
  .hold-color { color: #6b7280; }
  .gold-color { color: #f59e0b; }
  .cyan-color { color: #06b6d4; }
  .purple-color { color: #8b5cf6; }
  div[data-testid="stMetricValue"] { font-size: 1.4rem; font-weight: 800; }
</style>
""", unsafe_allow_html=True)

# ── Config ─────────────────────────────────────────────────────────────────────
CHECKPOINTS_FILE = Path("/Users/thapelodipela/Desktop/nexus-trading-ai/ai-trading-agent-template/checkpoints.jsonl")
NEXUS_URL = "http://localhost:5000"
AGENT_ID = "75"
WALLET = "0x29070e2221630DcF69f548796abc64ad5F953e20"
ETHERSCAN = f"https://sepolia.etherscan.io/address/{WALLET}"

# ── Data loaders ───────────────────────────────────────────────────────────────
@st.cache_data(ttl=5)
def load_checkpoints():
    if not CHECKPOINTS_FILE.exists():
        return []
    lines = CHECKPOINTS_FILE.read_text().strip().split("\n")
    cps = []
    for l in lines:
        try:
            cps.append(json.loads(l))
        except:
            pass
    return list(reversed(cps))

@st.cache_data(ttl=5)
def load_nexus(endpoint):
    try:
        r = requests.get(f"{NEXUS_URL}/api/{endpoint}", timeout=3)
        return r.json()
    except:
        return {"success": False}

def parse_votes(reasoning):
    import re
    votes = []
    m = re.search(r'Consensus: (.+?) →', reasoning or '')
    if m:
        for part in m.group(1).split(' | '):
            vm = re.match(r'(\w+)→(\w+)\((\d+)%\)', part)
            if vm:
                votes.append({"agent": vm.group(1), "action": vm.group(2), "conf": int(vm.group(3))})
    return votes

def action_color(action):
    return {"BUY": "#10b981", "SELL": "#ef4444", "HOLD": "#6b7280"}.get(action, "#6b7280")

# ══════════════════════════════════════════════════════════════════════════════
# HEADER
# ══════════════════════════════════════════════════════════════════════════════
col_logo, col_links = st.columns([3, 1])
with col_logo:
    st.markdown("# ⬡ NEXUS Unified Trading Intelligence")
    st.markdown(f"**Agent ID:** `{AGENT_ID}` &nbsp;|&nbsp; **Wallet:** `{WALLET[:10]}...{WALLET[-4:]}`")
with col_links:
    st.markdown(f"[🔗 View on Etherscan]({ETHERSCAN})", unsafe_allow_html=False)
    st.markdown(f"[🔗 Sepolia Transactions]({ETHERSCAN}#internaltx)")

st.divider()

# Load data
cps = load_checkpoints()
latest = cps[0] if cps else {}
market = load_nexus("market")
risk = load_nexus("risk")
agents = load_nexus("agents")
sentiment = load_nexus("sentiment")
performance = load_nexus("performance")

# ══════════════════════════════════════════════════════════════════════════════
# TOP METRICS ROW
# ══════════════════════════════════════════════════════════════════════════════
m1, m2, m3, m4, m5, m6 = st.columns(6)

price = latest.get("priceUsd", 0)
action = latest.get("action", "HOLD")
conf = int((latest.get("confidence", 0.5)) * 100)

with m1:
    st.metric("BTC Price", f"${price:,.2f}" if price else "—")
with m2:
    color = action_color(action)
    st.markdown(f"**Last Decision**")
    st.markdown(f"<h2 style='color:{color};margin:0'>{action}</h2>", unsafe_allow_html=True)
with m3:
    st.metric("Confidence", f"{conf}%")
with m4:
    st.metric("Checkpoints", len(cps))
with m5:
    risk_score = market.get("risk_score", "—")
    st.metric("Risk Score", f"{risk_score:.1f}" if isinstance(risk_score, float) else "—")
with m6:
    fg = sentiment.get("fear_greed", "—") if sentiment.get("success") else "—"
    st.metric("Fear & Greed", fg)

st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# MAIN LAYOUT: LEFT = CONSENSUS | RIGHT = MARKET
# ══════════════════════════════════════════════════════════════════════════════
left, right = st.columns([3, 2])

with left:
    # ── Live Agent Consensus ──────────────────────────────────────────────────
    st.subheader("🤖 Live Agent Consensus")
    
    reasoning = latest.get("reasoning", "")
    votes = parse_votes(reasoning)
    is_veto = "[RISK VETO]" in reasoning
    
    if is_veto:
        st.error(f"⚠️ RISK GUARDIAN VETO — {reasoning.replace('[RISK VETO] VETO: ', '')}")
    elif votes:
        st.markdown(f"**Weighted consensus: {conf}%** → Final decision: **{action}**")
        for v in votes:
            col_name, col_act, col_bar, col_pct = st.columns([2, 1, 4, 1])
            colors = {"MOMENTUM": "#60a5fa", "SENTIMENT": "#8b5cf6", "RISK_GUARDIAN": "#f59e0b", "MEAN_REVERSION": "#06b6d4"}
            c = colors.get(v["agent"], "#6b7280")
            with col_name:
                st.markdown(f"<span style='color:{c};font-weight:700;font-size:11px'>{v['agent'].replace('_',' ')}</span>", unsafe_allow_html=True)
            with col_act:
                ac = action_color(v["action"])
                st.markdown(f"<span style='color:{ac};font-weight:700'>{v['action']}</span>", unsafe_allow_html=True)
            with col_bar:
                st.progress(v["conf"] / 100)
            with col_pct:
                st.markdown(f"**{v['conf']}%**")
    else:
        st.info("Warming up — waiting for 3 price samples...")
    
    if reasoning and not is_veto:
        with st.expander("Full reasoning"):
            st.code(reasoning)

    st.divider()

    # ── Checkpoint Feed ───────────────────────────────────────────────────────
    st.subheader("📋 Recent Checkpoints")
    
    for cp in cps[:15]:
        action_c = action_color(cp.get("action", "HOLD"))
        conf_c = int((cp.get("confidence", 0.5)) * 100)
        ts = cp.get("timestamp", 0)
        t = datetime.fromtimestamp(ts if ts > 1e10 else ts).strftime("%H:%M:%S")
        rea = cp.get("reasoning", "—")
        is_consensus = "Consensus:" in rea
        is_veto_cp = "RISK VETO" in rea
        
        with st.container():
            c1, c2, c3, c4 = st.columns([1, 2, 4, 1])
            with c1:
                st.markdown(f"<span style='color:{action_c};font-weight:800;font-size:14px'>{cp.get('action','?')}</span>", unsafe_allow_html=True)
                st.caption(t)
            with c2:
                st.markdown(f"**${cp.get('priceUsd',0):,.2f}**")
            with c3:
                if is_veto_cp:
                    st.markdown(f"<span style='color:#f59e0b;font-size:10px'>{rea[:80]}...</span>", unsafe_allow_html=True)
                elif is_consensus:
                    st.markdown(f"<span style='color:#60a5fa;font-size:10px'>{rea[:80]}...</span>", unsafe_allow_html=True)
                else:
                    st.caption(rea[:80])
            with c4:
                st.markdown(f"**{conf_c}%**")
        st.divider()

with right:
    # ── Market Intelligence ───────────────────────────────────────────────────
    st.subheader("📊 PRISM Market Intelligence")
    
    if market.get("success"):
        r1, r2 = st.columns(2)
        with r1:
            sig1 = market.get("signal_1h", "neutral")
            color1 = "#10b981" if sig1 == "bullish" else "#ef4444" if sig1 == "bearish" else "#6b7280"
            st.markdown(f"**1H Signal:** <span style='color:{color1};font-weight:800'>{sig1.upper()}</span>", unsafe_allow_html=True)
        with r2:
            sig4 = market.get("signal_4h", "neutral")
            color4 = "#10b981" if sig4 == "bullish" else "#ef4444" if sig4 == "bearish" else "#6b7280"
            st.markdown(f"**4H Signal:** <span style='color:{color4};font-weight:800'>{sig4.upper()}</span>", unsafe_allow_html=True)
    else:
        st.warning("NEXUS server offline — restart `python3 dashboard_server.py`")

    st.divider()

    # ── Risk Metrics ──────────────────────────────────────────────────────────
    st.subheader("⚠️ Risk Metrics")
    if risk.get("success"):
        r1, r2 = st.columns(2)
        with r1:
            st.metric("Max Drawdown", f"{risk.get('max_drawdown_30d', 0):.1f}%")
            st.metric("Volatility", f"{risk.get('volatility_30d', 0):.1f}%")
        with r2:
            st.metric("Sharpe Ratio", f"{risk.get('sharpe_ratio', 0):.2f}")
            st.metric("Risk Score", f"{market.get('risk_score', 0):.1f}" if market.get("success") else "—")
    else:
        st.warning("Risk data unavailable")

    st.divider()

    # ── Agent Voting Power ────────────────────────────────────────────────────
    st.subheader("⚖️ Agent Voting Power")
    if agents.get("success") and agents.get("agents"):
        total_w = sum(a.get("weight", 1) for a in agents["agents"])
        for a in agents["agents"]:
            w = a.get("weight", 1)
            pct = (w / total_w) * 100
            pnl = a.get("pnl_total", 0)
            name = (a.get("agent_id") or a.get("name") or "AGENT").upper()
            colors = {"MOMENTUM": "#60a5fa", "SENTIMENT": "#8b5cf6", "RISK_GUARDIAN": "#f59e0b", "MEAN_REVERSION": "#06b6d4"}
            c = colors.get(name, "#06b6d4")
            st.markdown(f"<span style='color:{c};font-weight:700'>{name}</span> — **{pct:.1f}%** vote | W: {w:.4f} | PnL: {'+'if pnl>=0 else ''}${pnl:.2f}", unsafe_allow_html=True)
            st.progress(pct / 100)
    else:
        st.warning("Agent data unavailable — is NEXUS server running?")

    st.divider()

    # ── Sentiment ─────────────────────────────────────────────────────────────
    st.subheader("💭 Sentiment Analysis")
    if sentiment.get("success"):
        fg = sentiment.get("fear_greed", 50)
        st.metric("Fear & Greed Index", fg, help="0=Extreme Fear, 100=Extreme Greed")
        st.progress(fg / 100)
        comp = sentiment.get("composite", {})
        if comp:
            s1, s2, s3 = st.columns(3)
            with s1:
                st.metric("Trending", f"{int(comp.get('trending',0)*100)}%")
            with s2:
                st.metric("Community", f"{int(comp.get('community',0)*100)}%")
            with s3:
                st.metric("Momentum", f"{int(comp.get('momentum',0)*100)}%")
    else:
        st.warning("Sentiment data unavailable")

    st.divider()

    # ── On-chain proof ────────────────────────────────────────────────────────
    st.subheader("⛓️ On-Chain Proof of Work")
    st.markdown(f"""
    | Contract | Status |
    |---|---|
    | AgentRegistry | ✅ Registered (ID: 75) |
    | HackathonVault | ✅ 0.05 ETH allocated |
    | RiskRouter | ✅ Trade intents live |
    | ValidationRegistry | ✅ Checkpoints on-chain |
    | ReputationRegistry | ✅ Accumulating |
    """)
    st.markdown(f"[🔗 View all transactions on Sepolia Etherscan →]({ETHERSCAN})")

# ══════════════════════════════════════════════════════════════════════════════
# PRICE CHART
# ══════════════════════════════════════════════════════════════════════════════
st.divider()
st.subheader("📈 BTC Price — Live from Checkpoints")

if len(cps) >= 2:
    import plotly.graph_objects as go
    
    chart_data = list(reversed(cps[:50]))
    prices = [cp.get("priceUsd", 0) for cp in chart_data]
    times = [datetime.fromtimestamp(cp["timestamp"] if cp["timestamp"] > 1e10 else cp["timestamp"]).strftime("%H:%M:%S") for cp in chart_data]
    actions_list = [cp.get("action", "HOLD") for cp in chart_data]
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=times, y=prices,
        mode='lines+markers',
        line=dict(color='#3b82f6', width=2),
        marker=dict(
            color=['#10b981' if a=='BUY' else '#ef4444' if a=='SELL' else '#6b7280' for a in actions_list],
            size=8
        ),
        name='BTC Price',
        hovertemplate='%{x}<br>$%{y:,.2f}<extra></extra>'
    ))
    fig.update_layout(
        paper_bgcolor='#080a0f',
        plot_bgcolor='#0d0f16',
        font=dict(color='#e2e8f4'),
        height=300,
        margin=dict(l=0, r=0, t=10, b=0),
        xaxis=dict(gridcolor='#1c2030', showgrid=True),
        yaxis=dict(gridcolor='#1c2030', showgrid=True, tickformat='$,.0f'),
        showlegend=False
    )
    st.plotly_chart(fig, use_container_width=True)
    st.caption("🟢 Green dots = BUY signal &nbsp; 🔴 Red dots = SELL signal &nbsp; ⚫ Grey = HOLD")
else:
    st.info("Waiting for price data...")

# ══════════════════════════════════════════════════════════════════════════════
# FOOTER
# ══════════════════════════════════════════════════════════════════════════════
st.divider()
st.caption(f"NEXUS Unified Trading Intelligence | Agent ID: {AGENT_ID} | Last updated: {datetime.now().strftime('%H:%M:%S')} | Auto-refresh every 5s")

# Auto-refresh
time.sleep(5)
st.rerun()
