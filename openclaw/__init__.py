"""
OpenClaw: Quantum Board of Directors
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Multi-director consensus voting system powered by Groq + Llama 3.3 70B.

The Board consists of four autonomous financial personas:
  1. Alpha (The Quant) - Technical analysis
  2. Beta (The Sentiment Scout) - Social + news sentiment
  3. Gamma (The Risk Officer) - Risk management & capital preservation
  4. Delta (The Opportunist) - Capital flow & rotation signals

Board decisions determine:
  - Trade direction (BUY / SELL / HOLD)
  - Consensus level (4/4, 3/4, 2/4, HOLD)
  - Leverage (1x to 4x based on conviction)
  - Exit target (25% standard or 50% risk-on)
"""

from .engine import QuantumBoard, BoardDecision, DirectorOpinion, DirectorVote, BoardVote

__all__ = [
    "QuantumBoard",
    "BoardDecision",
    "DirectorOpinion",
    "DirectorVote",
    "BoardVote",
]
