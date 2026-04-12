"""
NEXUS Trading AI — Streamlit Dashboard
"""
import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

API_BASE = "http://localhost:3000"
GROQ_KEY = os.getenv("GROQ_API_KEY", "")

st.set_page_config(
    page_title="NEXUS Trading AI",
    page_icon="⬡",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600&family=DM+Mono&display=swap');
html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; background-color: #FAFAF8; }
.stApp { background-color: #FAFAF8; }
section[data-testid="stSidebar"] { background-color: #F3F2EE; border-right: 1px solid rgba(0,0,0,0.07); }
[data-testid="metric-container"] { background: #FFFFFF; border: 1px solid rgba(0,0,0,0.07); border-radius: 10px; padding: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.06); }
</style>
""", unsafe_allow_html=True)

def api(path):
    try:
        r = requests.get(f"{API_BASE}{path}", timeout=8)
        return r.json()
    except:
        return None

# ── SIDEBAR ───────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⬡ NEXUS")
    st.markdown("---")
    tab = st.radio("Navigate", [
        "Dashboard",
        "Agents",
        "Positions",
        "Sentiment",
        "Risk",
        "AI Chat",
    ])
    st.markdown("---")
    strategy = st.selectbox("Active Strategy", [
        "algorithmic_quant", "trend_following", "breakout",
        "mean_reversion", "scalping", "swing", "smc",
        "position", "arbitrage", "yolo"
    ])
    st.markdown("---")
    auto_refresh = st.toggle("Auto Refresh (15s)", value=True)
    if st.button("🔄 Refresh Now"):
        st.rerun()

# ── AUTO REFRESH ──────────────────────────────────────


# ══════════════════════════════════════════════════════
# DASHBOARD TAB
# ══════════════════════════════════════════════════════
if tab == "Dashboard":
    st.markdown("## Dashboard")

    market  = api("/api/market")
    balance = api("/api/balance")
    live    = api("/api/live-decisions")

    # ── STAT CARDS ────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        price = market["price"] if market and market.get("success") else 0
        chg   = market["change_24h"] if market else 0
        st.metric("BTC Price", f"${price:,.2f}", f"{chg:+.2f}%")
    with c2:
        bal = balance["balance_usd"] if balance and balance.get("success") else 0
        st.metric("Portfolio Value", f"${bal:,.2f}")
    with c3:
        pnl = balance["total_pnl"] if balance and balance.get("success") else 0
        st.metric("Session PnL", f"${pnl:,.2f}")
    with c4:
        wr = balance["win_rate"] if balance and balance.get("success") else 0
        tr = balance["total_trades"] if balance and balance.get("success") else 0
        st.metric("Win Rate", f"{wr:.1f}%", f"{tr} trades")

    st.markdown("---")

    # ── AGENT VOTES + CONSENSUS ───────────────────────
    col_left, col_right = st.columns([2, 1])

    with col_left:
        st.markdown("#### Agent Parliament")
        if live and live.get("success"):
            decisions = live["data"].get("agent_decisions", [])
            consensus = live["data"].get("consensus_decision", {})
            cycle     = live["data"].get("latest_cycle", 0)

            if decisions:
                df = pd.DataFrame(decisions)
                df["confidence_pct"] = (df["confidence"] * 100).round(1)
                df = df[["agent_id", "direction", "confidence_pct", "reasoning"]]
                df.columns = ["Agent", "Vote", "Confidence %", "Reasoning"]

                def color_vote(val):
                    if val == "BUY":  return "color: #16A34A; font-weight: 600"
                    if val == "SELL": return "color: #DC2626; font-weight: 600"
                    return "color: #9B9B8E"

                st.dataframe(
                    df.style.map(color_vote, subset=["Vote"]),
                    width='stretch', hide_index=True
                )

            if consensus:
                dir_ = consensus.get("direction", "HOLD")
                conf = consensus.get("confidence", 0)
                color = "#16A34A" if dir_ == "BUY" else "#DC2626" if dir_ == "SELL" else "#9B9B8E"
                st.markdown(f"""
                <div style="background:#fff;border:1px solid rgba(0,0,0,0.07);border-radius:10px;padding:16px;margin-top:8px">
                    <div style="font-size:11px;color:#9B9B8E;text-transform:uppercase;letter-spacing:0.07em;margin-bottom:8px">Cycle {cycle} — Consensus</div>
                    <span style="color:{color};font-size:22px;font-weight:600">{dir_}</span>
                    <span style="color:#6B6B5E;font-size:14px;margin-left:8px">{conf*100:.1f}% confidence</span>
                </div>
                """, unsafe_allow_html=True)

    with col_right:
        st.markdown("#### Market Signals")
        if market and market.get("success"):
            sig1h = market.get("signal_1h", "—")
            sig4h = market.get("signal_4h", "—")
            risk  = market.get("risk_score", 0)
            vol   = market.get("volume_24h", 0)

            st.markdown(f"""
            <div style="background:#fff;border:1px solid rgba(0,0,0,0.07);border-radius:10px;padding:16px">
                <div style="display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid rgba(0,0,0,0.05)">
                    <span style="color:#6B6B5E;font-size:12px">Signal 1H</span>
                    <span style="font-family:'DM Mono';font-size:12px">{sig1h}</span>
                </div>
                <div style="display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid rgba(0,0,0,0.05)">
                    <span style="color:#6B6B5E;font-size:12px">Signal 4H</span>
                    <span style="font-family:'DM Mono';font-size:12px">{sig4h}</span>
                </div>
                <div style="display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid rgba(0,0,0,0.05)">
                    <span style="color:#6B6B5E;font-size:12px">Risk Score</span>
                    <span style="font-family:'DM Mono';font-size:12px;color:{'#DC2626' if risk>70 else '#D97706' if risk>40 else '#16A34A'}">{risk:.1f}</span>
                </div>
                <div style="display:flex;justify-content:space-between;padding:8px 0">
                    <span style="color:#6B6B5E;font-size:12px">Volume 24H</span>
                    <span style="font-family:'DM Mono';font-size:12px">${vol:,.0f}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

    # ── AGENT WEIGHT CHART ────────────────────────────
    st.markdown("---")
    agents_data = api("/api/agents")
    if agents_data and agents_data.get("success") and agents_data.get("agents"):
        agents = agents_data["agents"]
        st.markdown("#### Agent Voting Weights")
        fig = go.Figure(go.Bar(
            x=[a["agent_id"] for a in agents],
            y=[a["weight"] for a in agents],
            marker_color=["#D97706" if a["weight"] == max(a2["weight"] for a2 in agents) else "#ECEAE3" for a in agents],
            marker_line_color="rgba(0,0,0,0.1)",
            marker_line_width=1,
        ))
        fig.update_layout(
            paper_bgcolor="#FAFAF8", plot_bgcolor="#FAFAF8",
            height=220, margin=dict(l=0, r=0, t=10, b=0),
            xaxis=dict(showgrid=False, color="#6B6B5E"),
            yaxis=dict(showgrid=True, gridcolor="rgba(0,0,0,0.05)", color="#6B6B5E"),
            font=dict(family="DM Sans", color="#6B6B5E", size=12),
        )
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

# ══════════════════════════════════════════════════════
# AGENTS TAB
# ══════════════════════════════════════════════════════
elif tab == "Agents":
    st.markdown("## Agent Leaderboard")
    data = api("/api/agents")
    if data and data.get("success") and data.get("agents"):
        agents = data["agents"]

        # Summary metrics
        s = data.get("summary", {})
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Trades", s.get("total_trades", 0))
        c2.metric("Total Wins",   s.get("total_wins", 0))
        c3.metric("Win Rate",     f"{s.get('win_rate', 0):.1f}%")
        c4.metric("Total PnL",    f"${s.get('total_pnl', 0):,.2f}")

        st.markdown("---")

        # Agent table
        rows = []
        for a in agents:
            wins   = a.get("wins", 0)
            closed = a.get("trades_closed", 0)
            acc    = f"{wins/closed*100:.1f}%" if closed else "—"
            rows.append({
                "Agent":      a["agent_id"],
                "Weight":     round(a.get("weight", 1.0), 4),
                "Wins":       wins,
                "Losses":     a.get("losses", 0),
                "Trades":     closed,
                "Accuracy":   acc,
                "PnL":        f"${a.get('pnl_total', 0):,.2f}",
                "Status":     "⚠ Penalised" if a.get("consecutive_floor_trades", 0) >= 3 else "✓ Active",
            })

        df = pd.DataFrame(rows)
        st.dataframe(df, width='stretch', hide_index=True)

        st.markdown("---")
        st.markdown("#### PnL by Agent")
        fig = go.Figure(go.Bar(
            x=[a["agent_id"] for a in agents],
            y=[a.get("pnl_total", 0) for a in agents],
            marker_color=["#16A34A" if a.get("pnl_total", 0) >= 0 else "#DC2626" for a in agents],
            marker_line_width=0,
        ))
        fig.update_layout(
            paper_bgcolor="#FAFAF8", plot_bgcolor="#FAFAF8",
            height=260, margin=dict(l=0, r=0, t=10, b=0),
            xaxis=dict(showgrid=False, color="#6B6B5E"),
            yaxis=dict(showgrid=True, gridcolor="rgba(0,0,0,0.05)", color="#6B6B5E",
                       tickprefix="$"),
            font=dict(family="DM Sans", color="#6B6B5E", size=12),
        )
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

# ══════════════════════════════════════════════════════
# POSITIONS TAB
# ══════════════════════════════════════════════════════
elif tab == "Positions":
    st.markdown("## Positions")
    pos  = api("/api/positions")
    trd  = api("/api/trades")

    st.markdown("#### Open Positions")
    if pos and pos.get("success") and pos.get("positions"):
        rows = []
        for p in pos["positions"]:
            rows.append({
                "Pair":      p.get("pair", "—"),
                "Direction": p.get("direction", "—"),
                "Size":      f"${p.get('size_usd', 0):,.2f}",
                "Entry":     f"${p.get('entry_price', 0):,.2f}",
                "PnL":       f"${p.get('pnl_usd', 0):,.2f}",
                "Status":    p.get("status", "OPEN"),
            })
        st.dataframe(pd.DataFrame(rows), width='stretch', hide_index=True)
    else:
        st.info("No open positions")

    st.markdown("---")
    st.markdown("#### Recent Closed Trades")
    if trd and trd.get("success") and trd.get("trades"):
        rows = []
        for t in trd["trades"][-20:]:
            pnl = t.get("pnl_usd", 0)
            rows.append({
                "Pair":      t.get("pair", "—"),
                "Direction": t.get("direction", "—"),
                "PnL $":     f"${pnl:,.2f}",
                "PnL %":     f"{t.get('pnl_pct', 0):+.2f}%",
                "Strategy":  t.get("strategy", "—"),
                "Result":    "✓ Win" if pnl > 0 else "✗ Loss",
            })
        df = pd.DataFrame(rows)
        st.dataframe(df, width='stretch', hide_index=True)

        # PnL chart
        pnls = [t.get("pnl_usd", 0) for t in trd["trades"]]
        cumulative = []
        total = 0
        for p in pnls:
            total += p
            cumulative.append(total)
        fig = go.Figure(go.Scatter(
            y=cumulative, mode="lines",
            line=dict(color="#16A34A", width=1.5),
            fill="tozeroy", fillcolor="rgba(22,163,74,0.06)"
        ))
        fig.update_layout(
            paper_bgcolor="#FAFAF8", plot_bgcolor="#FAFAF8",
            height=200, margin=dict(l=0,r=0,t=10,b=0),
            title="Cumulative PnL",
            xaxis=dict(showgrid=False, color="#6B6B5E"),
            yaxis=dict(showgrid=True, gridcolor="rgba(0,0,0,0.05)",
                       color="#6B6B5E", tickprefix="$"),
            font=dict(family="DM Sans", color="#6B6B5E", size=12),
        )
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
    else:
        st.info("No closed trades yet")

# ══════════════════════════════════════════════════════
# SENTIMENT TAB
# ══════════════════════════════════════════════════════
elif tab == "Sentiment":
    st.markdown("## Market Sentiment")
    sent = api("/api/sentiment")
    mkt  = api("/api/market")

    c1, c2, c3 = st.columns(3)
    if sent and sent.get("success"):
        fg = sent.get("fear_greed")
        with c1:
            st.metric("Fear & Greed", fg or "—",
                "Extreme Fear" if fg and fg < 20 else
                "Fear" if fg and fg < 40 else
                "Greed" if fg and fg > 60 else
                "Extreme Greed" if fg and fg > 80 else "Neutral"
            )
        comp = sent.get("composite", {})
        if isinstance(comp, dict):
            with c2: st.metric("Composite Score", f"{comp.get('composite', 0):+.3f}", comp.get("label", "—"))
            with c3: st.metric("News Score", f"{comp.get('news_score', 0):+.3f}")

    if mkt and mkt.get("success"):
        st.markdown("---")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("#### PRISM Signals")
            st.markdown(f"""
            | Timeframe | Signal |
            |-----------|--------|
            | 1H | `{mkt.get('signal_1h','—')}` |
            | 4H | `{mkt.get('signal_4h','—')}` |
            | Risk Score | `{mkt.get('risk_score', '—')}` |
            """)
        with c2:
            st.markdown("#### Fear & Greed Gauge")
            if sent and sent.get("fear_greed"):
                fg = sent["fear_greed"]
                fig = go.Figure(go.Indicator(
                    mode="gauge+number",
                    value=fg,
                    gauge=dict(
                        axis=dict(range=[0, 100]),
                        bar=dict(color="#D97706"),
                        steps=[
                            dict(range=[0,25],   color="#FEE2E2"),
                            dict(range=[25,45],  color="#FEF3C7"),
                            dict(range=[45,55],  color="#F3F2EE"),
                            dict(range=[55,75],  color="#DCFCE7"),
                            dict(range=[75,100], color="#BBF7D0"),
                        ],
                    ),
                    number=dict(font=dict(color="#1A1915")),
                ))
                fig.update_layout(
                    paper_bgcolor="#FAFAF8", height=220,
                    margin=dict(l=20,r=20,t=20,b=20),
                    font=dict(family="DM Sans"),
                )
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

# ══════════════════════════════════════════════════════
# RISK TAB
# ══════════════════════════════════════════════════════
elif tab == "Risk":
    st.markdown("## Risk Metrics")
    risk   = api("/api/risk")
    equity = api("/api/equity")

    if risk and risk.get("success"):
        c1, c2, c3 = st.columns(3)
        c1.metric("Risk Score",      f"{risk.get('risk_score', 0):.1f}")
        c2.metric("ATR %",           f"{risk.get('atr_pct', 0):.2f}%")
        c3.metric("30D Volatility",  f"{risk.get('volatility_30d', 0):.1f}%")
        c1, c2, c3 = st.columns(3)
        c1.metric("Max Drawdown 30D", f"{risk.get('max_drawdown_30d', 0):.1f}%")
        c2.metric("Sharpe Ratio",     f"{risk.get('sharpe_ratio', 0):.2f}")
        c3.metric("Sortino Ratio",    f"{risk.get('sortino_ratio', 0):.2f}")

    if equity and equity.get("success") and equity.get("data"):
        st.markdown("---")
        st.markdown("#### Equity Curve")
        data = equity["data"]
        # Handle both timestamp and date formats
        x_vals = []
        y_vals = []
        for d in data:
            if isinstance(d, dict):
                y_vals.append(float(d.get("equity", 0)))
                ts = d.get("timestamp") or d.get("date", "")
                if isinstance(ts, (int, float)) and ts > 1e9:
                    x_vals.append(datetime.fromtimestamp(ts).strftime("%H:%M"))
                else:
                    x_vals.append(str(ts))
            else:
                y_vals.append(float(d))
                x_vals.append(str(len(x_vals)))
        fig = go.Figure(go.Scatter(
            x=x_vals,
            y=y_vals,
            mode="lines",
            line=dict(color="#16A34A", width=1.5),
            fill="tozeroy", fillcolor="rgba(22,163,74,0.06)",
        ))
        fig.update_layout(
            paper_bgcolor="#FAFAF8", plot_bgcolor="#FAFAF8",
            height=300, margin=dict(l=0,r=0,t=10,b=0),
            xaxis=dict(showgrid=False, color="#6B6B5E"),
            yaxis=dict(showgrid=True, gridcolor="rgba(0,0,0,0.05)",
                       color="#6B6B5E", tickprefix="$"),
            font=dict(family="DM Sans", color="#6B6B5E", size=12),
        )
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

# ══════════════════════════════════════════════════════
# AI CHAT TAB
# ══════════════════════════════════════════════════════
elif tab == "AI Chat":
    st.markdown("## Ask NEXUS")
    st.caption("Ask about agent decisions, trades, risk, or strategy performance.")

    # Init chat history
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": "Hello. I'm NEXUS. Ask me about agent decisions, trade history, or risk metrics."}
        ]

    # Display messages
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Build system context
    market  = api("/api/market")
    balance = api("/api/balance")
    live    = api("/api/live-decisions")

    price  = market["price"] if market and market.get("success") else "unknown"
    pnl    = balance["total_pnl"] if balance and balance.get("success") else "unknown"
    cycle  = live["data"]["latest_cycle"] if live and live.get("success") else "unknown"

    system_ctx = f"""You are NEXUS, an AI trading system assistant for a multi-agent crypto trading bot.
Current state:
- BTC Price: ${price}
- Session PnL: ${pnl}
- Cycle: {cycle}
- Strategy: {strategy}
Answer questions concisely and factually. Reference specific metrics when available."""

    # Suggested prompts
    if len(st.session_state.messages) == 1:
        cols = st.columns(2)
        prompts = [
            "Why did Risk Guardian veto?",
            "Which agent has highest accuracy?",
            "What is the current drawdown?",
            "Explain the latest consensus",
        ]
        for i, p in enumerate(prompts):
            if cols[i % 2].button(p, key=f"prompt_{i}"):
                st.session_state.messages.append({"role": "user", "content": p})
                st.rerun()

    # Chat input
    if prompt := st.chat_input("Ask about agents, trades, risk…"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Thinking…"):
                if not GROQ_KEY:
                    reply = "⚠️ GROQ_API_KEY not found in .env — add it to enable AI chat."
                else:
                    try:
                        r = requests.post(
                            "https://api.groq.com/openai/v1/chat/completions",
                            headers={
                                "Content-Type": "application/json",
                                "Authorization": f"Bearer {GROQ_KEY}",
                            },
                            json={
                                "model": "llama-3.3-70b-versatile",
                                "max_tokens": 400,
                                "temperature": 0.3,
                                "messages": [
                                    {"role": "system", "content": system_ctx},
                                    *[{"role": m["role"], "content": m["content"]}
                                      for m in st.session_state.messages],
                                ],
                            },
                            timeout=20,
                        )
                        reply = r.json()["choices"][0]["message"]["content"]
                    except Exception as e:
                        reply = f"NEXUS temporarily unavailable: {str(e)}"

                st.markdown(reply)
                st.session_state.messages.append({"role": "assistant", "content": reply})

