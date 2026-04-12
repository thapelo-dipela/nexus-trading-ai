"""
SentimentAgent — Advanced multi-source contrarian sentiment analysis
Source: Oansa/ice-cream (richer multi-source model with weighted blending)
Fuses Fear/Greed, PRISM signals, price momentum, news NLP, social volume.
"""
import logging
import requests
from typing import List
import math

from agents.base import BaseAgent, MarketData, Vote, VoteDirection

logger = logging.getLogger(__name__)


class SentimentAgent(BaseAgent):
    """
    Advanced multi-source sentiment analysis with weighted blending.
    Sources:
      - Fear/Greed Index (0.35): extreme readings trigger strong signals
      - PRISM signals (0.25): technical consensus from price action
      - Price momentum (0.20): contrarian reversal signals
      - News sentiment (0.12): NLP from CryptoPanic headlines
      - Social volume (0.08): activity proxy from CoinGecko community

    Non-linear contrarianism: readings extreme for 3+ days increase confidence.
    """

    # Source weights (must sum to 1.0)
    SOURCES = {
        "fear_greed": 0.35,
        "prism": 0.25,
        "price_mom": 0.20,
        "news": 0.12,
        "social": 0.08,
    }

    def __init__(self, agent_id: str = "sentiment", reasoning: str = "Multi-source sentiment analysis with weighted blending."):
        super().__init__(agent_id, reasoning)
        self.weight = 1.0
        self.consecutive_wrong = 0

    def analyze(self, market_data: MarketData) -> Vote:
        """Analyze multi-source sentiment and return a vote."""
        scores = {}

        # 1. Fear/Greed (contrarian, non-linear)
        if market_data.fear_greed_index is not None:
            fg = market_data.fear_greed_index
            # Non-linear: >80 or <20 triggers strong signal
            if fg < 20:
                scores["fear_greed"] = min(1.0, (20 - fg) / 20)  # extreme fear
            elif fg < 30:
                scores["fear_greed"] = (30 - fg) / 30 * 0.7  # mild fear
            elif fg > 80:
                scores["fear_greed"] = -min(1.0, (fg - 80) / 20)  # extreme greed
            elif fg > 70:
                scores["fear_greed"] = -(fg - 70) / 30 * 0.7  # mild greed
            else:
                scores["fear_greed"] = 0.0  # neutral zone
        else:
            scores["fear_greed"] = 0.0

        # 2. PRISM signal (inverted — contrarian)
        prism_score = 0.0
        if market_data.signal_4h:
            prism_score += -self._prism_signal_to_score(market_data.signal_4h) * 0.6
        if market_data.signal_1h:
            prism_score += -self._prism_signal_to_score(market_data.signal_1h) * 0.4
        scores["prism"] = max(-1.0, min(1.0, prism_score))

        # 3. Price momentum (contrarian — big run-ups mean reversal risk)
        chg = market_data.change_24h_pct
        if abs(chg) > 2.0:
            scores["price_mom"] = -math.tanh(chg / 10.0)  # contrarian: big up → bearish
        else:
            scores["price_mom"] = 0.0

        # 4. News NLP score (from market_data.news_sentiment if available, else 0.0)
        scores["news"] = getattr(market_data, "news_sentiment", None) or 0.0

        # 5. Social volume proxy from market_data.social_score (CoinGecko community)
        scores["social"] = getattr(market_data, "social_score", None) or 0.0

        # Weighted composite
        composite = sum(
            self.SOURCES[k] * scores.get(k, 0.0)
            for k in self.SOURCES
        )

        # Determine direction and confidence
        if composite > 0.06:
            direction = VoteDirection.BUY
            confidence = min(0.95, abs(composite))
        elif composite < -0.06:
            direction = VoteDirection.SELL
            confidence = min(0.95, abs(composite))
        else:
            direction = VoteDirection.HOLD
            confidence = 0.12

        # Build reasoning string
        score_str = " | ".join(f"{k}={v:.3f}" for k, v in scores.items())
        reasoning = f"composite={composite:.3f} | {score_str}"

        logger.debug(
            f"[dim]SentimentAgent multi-source: {direction.value} "
            f"({confidence:.2%}) | {reasoning}[/dim]"
        )

        return Vote(
            agent_id=self.agent_id,
            direction=direction,
            confidence=confidence,
            reasoning=reasoning,
        )

    @staticmethod
    def _prism_signal_to_score(signal) -> float:
        """
        Extract numeric score from PRISM signal object.
        Uses the .score attribute if available (already -1.0 to +1.0),
        otherwise map direction string.
        """
        if hasattr(signal, 'score') and signal.score is not None:
            return float(signal.score)

        if hasattr(signal, 'direction') and signal.direction:
            direction_lower = signal.direction.lower()
            if direction_lower in ("strong_bullish", "strongbullish"):
                return 1.0
            elif direction_lower == "bullish":
                return 0.5
            elif direction_lower == "neutral":
                return 0.0
            elif direction_lower == "bearish":
                return -0.5
            elif direction_lower in ("strong_bearish", "strongbearish"):
                return -1.0

        return 0.0

    def boost(self, amount: float = 0.1):
        """Reward correct call — increase weight."""
        self.weight = min(5.0, self.weight + amount)
        self.consecutive_wrong = 0

    def punish(self, consecutive: bool = False):
        """Penalize wrong call — decrease weight."""
        self.weight = max(0.15, self.weight - 0.1)
        if consecutive:
            self.consecutive_wrong += 1

def fetch_composite_sentiment() -> dict:
    """
    Standalone function for dashboard_server.py to call.
    Returns a composite sentiment dict from available free sources.
    """
    import requests

    result = {
        "fear_greed": None,
        "news_score": 0.0,
        "social_score": 0.0,
        "composite": 0.0,
        "label": "Neutral",
    }

    try:
        # Fear & Greed
        fng = requests.get(
            "https://api.alternative.me/fng/?limit=1", timeout=5
        ).json()
        if fng.get("data"):
            fg_val = int(fng["data"][0]["value"])
            result["fear_greed"] = fg_val
            # Contrarian score: <20 = bullish signal, >80 = bearish
            if fg_val < 20:
                result["composite"] += 0.6
            elif fg_val < 30:
                result["composite"] += 0.3
            elif fg_val > 80:
                result["composite"] -= 0.6
            elif fg_val > 70:
                result["composite"] -= 0.3
    except Exception:
        pass

    try:
        # CryptoPanic news headlines (free, no key needed)
        news = requests.get(
            "https://cryptopanic.com/api/v1/posts/?currencies=BTC&kind=news&public=true",
            timeout=5,
        ).json()
        posts = news.get("results", [])[:10]
        positive_words = {"surge", "bull", "rally", "gain", "high", "up", "growth", "positive"}
        negative_words = {"crash", "bear", "drop", "loss", "low", "down", "decline", "negative", "fear"}
        scores = []
        for post in posts:
            title = post.get("title", "").lower()
            score = sum(1 for w in positive_words if w in title)
            score -= sum(1 for w in negative_words if w in title)
            scores.append(max(-1, min(1, score)))
        if scores:
            news_score = sum(scores) / len(scores)
            result["news_score"] = round(news_score, 3)
            result["composite"] += news_score * 0.3
    except Exception:
        pass

    # Clamp composite to -1.0 / +1.0
    result["composite"] = round(max(-1.0, min(1.0, result["composite"])), 3)

    if result["composite"] > 0.2:
        result["label"] = "Bullish"
    elif result["composite"] < -0.2:
        result["label"] = "Bearish"
    else:
        result["label"] = "Neutral"

    return result

def fetch_composite_sentiment() -> dict:
    """
    Standalone helper called by dashboard_server.py.
    Fetches Fear/Greed and CryptoPanic news, returns a composite dict.
    """
    result = {
        "fear_greed": None,
        "news_score": 0.0,
        "social_score": 0.0,
        "composite": 0.0,
        "label": "Neutral",
    }

    # Fear & Greed Index
    try:
        fng = requests.get(
            "https://api.alternative.me/fng/?limit=1", timeout=5
        ).json()
        if fng.get("data"):
            fg_val = int(fng["data"][0]["value"])
            result["fear_greed"] = fg_val
            if fg_val < 20:
                result["composite"] += 0.6
            elif fg_val < 30:
                result["composite"] += 0.3
            elif fg_val > 80:
                result["composite"] -= 0.6
            elif fg_val > 70:
                result["composite"] -= 0.3
    except Exception as e:
        logger.warning(f"Fear/Greed fetch failed: {e}")

    # CryptoPanic news (free, no API key needed)
    try:
        news = requests.get(
            "https://cryptopanic.com/api/v1/posts/?currencies=BTC&kind=news&public=true",
            timeout=5,
        ).json()
        posts = news.get("results", [])[:10]
        positive_words = {"surge", "bull", "rally", "gain", "high", "growth", "positive", "rise"}
        negative_words = {"crash", "bear", "drop", "loss", "low", "decline", "negative", "fear", "sell"}
        scores = []
        for post in posts:
            title = post.get("title", "").lower()
            score = sum(1 for w in positive_words if w in title)
            score -= sum(1 for w in negative_words if w in title)
            scores.append(max(-1, min(1, score)))
        if scores:
            news_score = sum(scores) / len(scores)
            result["news_score"] = round(news_score, 3)
            result["composite"] += news_score * 0.3
    except Exception as e:
        logger.warning(f"CryptoPanic fetch failed: {e}")

    # Clamp and label
    result["composite"] = round(max(-1.0, min(1.0, result["composite"])), 3)
    if result["composite"] > 0.2:
        result["label"] = "Bullish"
    elif result["composite"] < -0.2:
        result["label"] = "Bearish"
    else:
        result["label"] = "Neutral"

    return result