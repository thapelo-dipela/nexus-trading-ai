"""
NEXUS Market Data Builder — assembles complete MarketData snapshots from PRISM and Kraken.
"""
import logging
import requests
from typing import Optional, Tuple

import config
from agents.base import MarketData, Candle, PrismSignal, PrismRisk
from execution.kraken import KrakenClient

logger = logging.getLogger(__name__)
