"""
NEXUS Agents — register and export all trading agents.
"""
from agents.base import BaseAgent
from agents.momentum import MomentumAgent
from agents.sentiment import SentimentAgent
from agents.risk_guardian import RiskGuardianAgent
from agents.mean_reversion import MeanReversionAgent
from agents.orderflow import OrderFlowAgent
from agents.llm_reasoner import LLMReasonerAgent
from agents.yolo import YOLOAgent

__all__ = [
    "BaseAgent",
    "MomentumAgent",
    "SentimentAgent",
    "RiskGuardianAgent",
    "MeanReversionAgent",
    "OrderFlowAgent",
    "LLMReasonerAgent",
    "YOLOAgent",
]


def create_default_agents(anthropic_api_key: str = "") -> list[BaseAgent]:
    """
    Create and return all default trading agents.
    LLMReasonerAgent is always LAST — it reads other agents' votes.
    """
    agents = [
        OrderFlowAgent(),
        MomentumAgent(reasoning="Blends local technical analysis with PRISM multi-timeframe signals."),
        SentimentAgent(reasoning="Multi-source contrarian sentiment analysis with weighted blending."),
        RiskGuardianAgent(reasoning="Hard veto triggers and volatility-scaled signal."),
        MeanReversionAgent(reasoning="Mean reversion strategy based on RSI, Bollinger Bands, and SMA."),
    ]
    
    # LLMReasonerAgent is optional and runs LAST
    if anthropic_api_key:
        agents.append(LLMReasonerAgent(anthropic_api_key))
    
    return agents
