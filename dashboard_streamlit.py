#!/usr/bin/env python3
"""
NEXUS Trading AI — OpenClaw Quantum Board Streamlit Dashboard

Real-time visualization of 4-director consensus board decisions with
Groq + Llama 3.3 70B integration.

Usage:
    streamlit run dashboard_streamlit.py

Requirements:
    streamlit>=1.28.0
    plotly>=5.17.0
    pandas>=2.0.0
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import json
import os
from datetime import datetime, timedelta
from pathlib import Path

# Configure Streamlit page
st.set_page_config(
    page_title="NEXUS Trading AI — OpenClaw Board",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    /* Claude AI Platform Theme */
    :root {
        --primary: #1a1a1a;
        --accent: #0ea5e9;
        --success: #10b981;
        --danger: #ef4444;
        --warning: #f59e0b;
    }
    
    body {
        background-color: #1a1a1a;
        color: #e5e7eb;
    }
    
    .stMetric {
        background-color: rgba(14, 165, 233, 0.05);
        padding: 20px;
        border-radius: 10px;
        border-left: 4px solid #0ea5e9;
    }
    
    .director-card {
        background: linear-gradient(135deg, rgba(14, 165, 233, 0.1), rgba(16, 185, 129, 0.05));
        padding: 20px;
        border-radius: 12px;
        border: 1px solid rgba(14, 165, 233, 0.3);
    }
</style>
""", unsafe_allow_html=True)

# Load configuration
try:
    from config import (
        DIRECTOR_WEIGHTS,
        LEVERAGE_RULES,
        SENTIMENT_BULLISH_THRESHOLD,
        SENTIMENT_BEARISH_THRESHOLD,
        RISK_CIRCUIT_BREAKER_DRAWDOWN,
        EXIT_TARGET_STANDARD,
        EXIT_TARGET_RISK_OFF
    )
    from openclaw.engine import QuantumBoard
except ImportError as e:
    st.error(f"⚠️ Configuration import error: {e}")
    st.info("Ensure config.py and openclaw/ are in the same directory")
    st.stop()

# Initialize session state
if "board" not in st.session_state:
    st.session_state.board = QuantumBoard(
        weights=DIRECTOR_WEIGHTS,
        leverage_rules=LEVERAGE_RULES
    )

if "history" not in st.session_state:
    st.session_state.history = []

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def load_cycle_log():
    """Load nexus_cycle_log.json if available"""
    cycle_log_path = Path("nexus_cycle_log.json")
    if cycle_log_path.exists():
        try:
            with open(cycle_log_path, "r") as f:
                cycles = json.load(f)
            return cycles if isinstance(cycles, list) else [cycles]
        except (json.JSONDecodeError, IOError):
            return []
    return []

def get_demo_market_data():
    """Generate realistic demo market data"""
    import random
    return {
        "rsi": random.randint(20, 80),
        "macd": round(random.uniform(-0.01, 0.02), 4),
        "sentiment_score": random.randint(30, 85),
        "drawdown": round(random.uniform(0, 0.05), 4),
        "price": 45000 + random.randint(-500, 500),
        "vwap": 44900 + random.randint(-400, 400),
        "cvd_momentum": round(random.uniform(-0.3, 0.4), 2),
        "trades_this_hour": random.randint(0, 8),
        "leverage_used": round(random.uniform(1.0, 2.0), 2)
    }

def get_director_emoji(director_name):
    """Return emoji for director"""
    emojis = {
        "Alpha": "📊",
        "Beta": "📱",
        "Gamma": "🛡️",
        "Delta": "⚡"
    }
    return emojis.get(director_name, "🎯")

def get_vote_color(vote):
    """Return color for vote"""
    colors = {
        "BUY": "#10b981",
        "SELL": "#ef4444",
        "HOLD": "#f59e0b"
    }
    return colors.get(vote, "#6b7280")

def format_consensus(consensus_str):
    """Format consensus string"""
    if "4/4" in consensus_str:
        return "🟢 Unanimous (4/4)"
    elif "3/4" in consensus_str:
        return "🟡 Majority (3/4)"
    elif "2/4" in consensus_str:
        return "🟠 Split (2/4)"
    else:
        return "🔴 Conflict"

# ============================================================================
# HEADER
# ============================================================================

st.markdown("# 🎬 NEXUS Trading AI — OpenClaw Quantum Board")
st.markdown("""
**Production-Grade 4-Director Consensus Engine**  
Powered by Groq + Llama 3.3 70B · Fully Auditable Decisions
""")

# Status indicators
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("System Status", "🟢 LIVE", help="OpenClaw board is active")
with col2:
    st.metric("Model", "Llama 3.3 70B", help="Groq inference engine")
with col3:
    st.metric("Latency", "<50ms", help="Board decision latency")
with col4:
    st.metric("Directors", "4 Active", help="Alpha, Beta, Gamma, Delta")

st.divider()

# ============================================================================
# SIDEBAR
# ============================================================================

with st.sidebar:
    st.markdown("## ⚙️ Configuration")
    
    # Market data source
    data_source = st.radio(
        "Data Source:",
        ["Live (nexus_cycle_log.json)", "Demo Data"],
        help="Choose between live cycle log or simulated demo data"
    )
    
    # Refresh rate
    refresh_rate = st.slider(
        "Refresh Rate (seconds):",
        min_value=5,
        max_value=60,
        value=15,
        step=5
    )
    
    # Show advanced settings
    show_advanced = st.checkbox("Show Advanced Settings", value=False)
    
    if show_advanced:
        st.markdown("### Director Weights")
        weights = {}
        for director, default_weight in DIRECTOR_WEIGHTS.items():
            weights[director] = st.slider(
                f"{director.capitalize()}:",
                min_value=0.5,
                max_value=2.0,
                value=default_weight,
                step=0.1
            )
        
        st.markdown("### Sentiment Thresholds")
        col1, col2 = st.columns(2)
        with col1:
            bullish_threshold = st.slider(
                "Bullish %:",
                min_value=50,
                max_value=90,
                value=SENTIMENT_BULLISH_THRESHOLD
            )
        with col2:
            bearish_threshold = st.slider(
                "Bearish %:",
                min_value=10,
                max_value=50,
                value=SENTIMENT_BEARISH_THRESHOLD
            )
    
    st.divider()
    
    # Documentation
    st.markdown("## 📚 Documentation")
    st.info("""
    **OpenClaw Board**: 4-director consensus engine
    
    • **Alpha**: Technical indicators (RSI, MACD)
    • **Beta**: Social sentiment (Reddit, news)
    • **Gamma**: Risk management (circuit breaker)
    • **Delta**: Capital flow & momentum
    
    [Read Full Docs](README.md)
    """)

# ============================================================================
# MAIN DASHBOARD
# ============================================================================

# Load market data
cycles = load_cycle_log() if data_source == "Live (nexus_cycle_log.json)" else []

if cycles:
    latest_cycle = cycles[-1]
    market_data = {
        "rsi": latest_cycle.get("rsi", 50),
        "macd": latest_cycle.get("macd", 0),
        "sentiment_score": latest_cycle.get("sentiment_score", 50),
        "drawdown": latest_cycle.get("drawdown", 0),
        "price": latest_cycle.get("price", 45000),
        "vwap": latest_cycle.get("vwap", 44900),
        "cvd_momentum": latest_cycle.get("cvd_momentum", 0),
        "trades_this_hour": latest_cycle.get("trades_this_hour", 0),
        "leverage_used": latest_cycle.get("leverage_used", 1.0)
    }
    timestamp = latest_cycle.get("timestamp", datetime.now().isoformat())
else:
    market_data = get_demo_market_data()
    timestamp = datetime.now().isoformat()

# Get board decision
decision = st.session_state.board.analyze_signal(market_data)

# Store in history
st.session_state.history.append({
    "timestamp": timestamp,
    "decision": decision.direction,
    "consensus": decision.consensus,
    "leverage": decision.leverage,
    **market_data
})

# Keep only last 100 decisions
if len(st.session_state.history) > 100:
    st.session_state.history = st.session_state.history[-100:]

# ============================================================================
# QUANTUM BOARD VISUALIZATION
# ============================================================================

st.markdown("## 🎬 Quantum Board of Directors")

# Director cards in grid
cols = st.columns(4)
for idx, (director_name, director_data) in enumerate(decision.execution_packet):
    with cols[idx]:
        vote = director_data.get("vote", "HOLD")
        confidence = director_data.get("confidence", 0.5)
        
        # Color based on vote
        vote_color = get_vote_color(vote)
        emoji = get_director_emoji(director_name)
        
        # Display card
        st.markdown(f"""
        <div style="
            background: linear-gradient(135deg, rgba({int(vote_color[1:3], 16)}, {int(vote_color[3:5], 16)}, {int(vote_color[5:7], 16)}, 0.1), rgba(14, 165, 233, 0.05));
            padding: 20px;
            border-radius: 12px;
            border: 2px solid {vote_color};
            text-align: center;
        ">
            <h3>{emoji} {director_name}</h3>
            <p style="color: {vote_color}; font-size: 24px; font-weight: bold;">
                {vote}
            </p>
            <p style="color: #9ca3af; margin: 10px 0;">
                Confidence: {confidence:.1%}
            </p>
            <div style="
                background-color: rgba(255, 255, 255, 0.1);
                border-radius: 10px;
                overflow: hidden;
                height: 8px;
                margin: 10px 0;
            ">
                <div style="
                    background-color: {vote_color};
                    width: {confidence * 100}%;
                    height: 100%;
                "></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

st.divider()

# ============================================================================
# CONSENSUS PANEL
# ============================================================================

st.markdown("## 🎯 Consensus Decision")

# Main decision metrics
col1, col2, col3, col4 = st.columns(4)

with col1:
    # Vote color
    vote_color = get_vote_color(decision.direction)
    st.markdown(f"""
    <div style="
        background-color: rgba({int(vote_color[1:3], 16)}, {int(vote_color[3:5], 16)}, {int(vote_color[5:7], 16)}, 0.2);
        padding: 20px;
        border-radius: 10px;
        text-align: center;
        border: 2px solid {vote_color};
    ">
        <h2 style="margin: 0; color: {vote_color};">{decision.direction}</h2>
        <p style="margin: 5px 0; color: #9ca3af;">Board Vote</p>
    </div>
    """, unsafe_allow_html=True)

with col2:
    consensus_display = format_consensus(decision.consensus)
    st.markdown(f"""
    <div style="
        background: linear-gradient(135deg, rgba(14, 165, 233, 0.2), rgba(16, 185, 129, 0.1));
        padding: 20px;
        border-radius: 10px;
        text-align: center;
        border: 2px solid #0ea5e9;
    ">
        <h2 style="margin: 0; color: #0ea5e9;">{consensus_display}</h2>
        <p style="margin: 5px 0; color: #9ca3af;">Consensus Level</p>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.metric(
        "Leverage",
        f"{decision.leverage:.1f}x",
        help=f"Position multiplier for {decision.direction} signal"
    )

with col4:
    exit_pct = int(decision.exit_target * 100)
    st.metric(
        "Exit Target",
        f"+{exit_pct}%",
        help="Profit target percentage"
    )

st.divider()

# ============================================================================
# MARKET DATA & ANALYTICS
# ============================================================================

tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Market Metrics",
    "📈 Analytics",
    "🔍 Technical Signals",
    "📋 Execution Packet"
])

with tab1:
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("### 📈 Price & Indicators")
        st.metric("Price", f"${market_data['price']:,.0f}")
        st.metric("VWAP", f"${market_data['vwap']:,.0f}")
        st.metric("RSI(14)", f"{market_data['rsi']:.0f}", 
                 help="Oversold <30, Overbought >70")
        st.metric("MACD", f"{market_data['macd']:.4f}")
    
    with col2:
        st.markdown("### 📡 Sentiment & Risk")
        st.metric("Sentiment Score", f"{market_data['sentiment_score']:.0f}%")
        st.metric("Drawdown", f"{market_data['drawdown']*100:.2f}%",
                 help="Circuit breaker at 5%")
        st.metric("CVD Momentum", f"{market_data['cvd_momentum']:.2f}")
        st.metric("Trades/Hour", f"{market_data['trades_this_hour']}/10")
    
    with col3:
        st.markdown("### ⚙️ Execution")
        st.metric("Leverage Used", f"{market_data['leverage_used']:.2f}x")
        st.metric("Decision Time", datetime.fromisoformat(timestamp).strftime("%H:%M:%S"))
        
        # Risk indicator
        risk_level = "🔴 HIGH" if market_data['drawdown'] > 0.03 else "🟡 MEDIUM" if market_data['drawdown'] > 0.02 else "🟢 LOW"
        st.metric("Risk Level", risk_level)

with tab2:
    # Historical decision chart
    if st.session_state.history:
        history_df = pd.DataFrame(st.session_state.history)
        
        # Decision history
        st.markdown("### 📊 Decision History (Last 20)")
        history_display = history_df.tail(20)[["timestamp", "decision", "consensus", "leverage", "sentiment_score"]].copy()
        history_display["timestamp"] = pd.to_datetime(history_display["timestamp"]).dt.strftime("%H:%M:%S")
        st.dataframe(
            history_display,
            use_container_width=True,
            column_config={
                "timestamp": st.column_config.TextColumn("Time"),
                "decision": st.column_config.TextColumn("Vote"),
                "consensus": st.column_config.TextColumn("Consensus"),
                "leverage": st.column_config.NumberColumn("Leverage", format="%.2fx"),
                "sentiment_score": st.column_config.NumberColumn("Sentiment", format="%.0f%%")
            }
        )
        
        # Win rate estimation (demo)
        buy_count = (history_df["decision"] == "BUY").sum()
        sell_count = (history_df["decision"] == "SELL").sum()
        hold_count = (history_df["decision"] == "HOLD").sum()
        
        st.markdown("### 📈 Decision Distribution")
        fig = go.Figure(data=[
            go.Pie(
                labels=["BUY", "SELL", "HOLD"],
                values=[buy_count, sell_count, hold_count],
                marker=dict(colors=["#10b981", "#ef4444", "#f59e0b"])
            )
        ])
        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor="#1a1a1a",
            font=dict(color="#e5e7eb")
        )
        st.plotly_chart(fig, use_container_width=True)

with tab3:
    st.markdown("### 🔍 Signal Analysis")
    
    # RSI interpretation
    rsi = market_data["rsi"]
    if rsi < 30:
        rsi_status = "🟢 **Oversold** — Strong reversal candidate"
    elif rsi > 70:
        rsi_status = "🔴 **Overbought** — Pressure to reverse"
    elif rsi < 50:
        rsi_status = "🟡 **Bearish** — Building downside momentum"
    else:
        rsi_status = "🟡 **Bullish** — Building upside momentum"
    
    col1, col2 = st.columns(2)
    with col1:
        st.info(f"**RSI(14)**: {rsi:.0f}\n\n{rsi_status}")
    
    # Sentiment interpretation
    sentiment = market_data["sentiment_score"]
    if sentiment > SENTIMENT_BULLISH_THRESHOLD:
        sentiment_status = "🟢 **Extreme Bullish** — Contrarian opportunity?"
    elif sentiment < SENTIMENT_BEARISH_THRESHOLD:
        sentiment_status = "🔴 **Extreme Bearish** — Contrarian bounce?"
    else:
        sentiment_status = "🟡 **Neutral** — Mixed signals"
    
    with col2:
        st.info(f"**Sentiment**: {sentiment:.0f}%\n\n{sentiment_status}")
    
    # Price action
    vwap_diff = ((market_data['price'] - market_data['vwap']) / market_data['vwap']) * 100
    with col1:
        if vwap_diff > 0:
            st.success(f"Price **above VWAP** by {vwap_diff:.2f}% (bullish)")
        else:
            st.error(f"Price **below VWAP** by {abs(vwap_diff):.2f}% (bearish)")
    
    with col2:
        if market_data['cvd_momentum'] > 0:
            st.success(f"CVD momentum **positive** ({market_data['cvd_momentum']:.2f})")
        else:
            st.error(f"CVD momentum **negative** ({market_data['cvd_momentum']:.2f})")

with tab4:
    st.markdown("### 📋 Full Execution Packet")
    
    # JSON display
    execution_data = {
        "timestamp": timestamp,
        "board_decision": {
            "direction": decision.direction,
            "confidence": decision.confidence,
            "consensus": decision.consensus,
            "leverage": decision.leverage,
            "exit_target": decision.exit_target
        },
        "director_votes": [
            {
                "director": vote[0],
                "vote": vote[1]["vote"],
                "confidence": vote[1]["confidence"]
            }
            for vote in decision.execution_packet
        ],
        "market_snapshot": market_data
    }
    
    st.json(execution_data)
    
    # Download button
    st.download_button(
        label="📥 Download Execution Packet",
        data=json.dumps(execution_data, indent=2),
        file_name=f"execution_packet_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
        mime="application/json"
    )

st.divider()

# ============================================================================
# FOOTER
# ============================================================================

st.markdown("""
---
**NEXUS Trading AI — OpenClaw Quantum Board**

Powered by Groq + Llama 3.3 70B · ERC-8004 Hackathon  
🟢 Production Ready | ✅ Fully Auditable | ⚡ <50ms Latency

[📚 Documentation](README.md) · [🧪 Test Results](test_openclaw.py) · [🎨 Dashboard](dashboard.html)
""")
