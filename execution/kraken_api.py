"""
NEXUS Kraken API Integration — Read-only trade history & performance tracking for lablab.ai competition.
Fetches trade history, calculates PnL, and formats for leaderboard submission.
"""
import logging
import json
import time
import hashlib
import hmac
import requests
from typing import Optional, List, Dict, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import base64

import config

logger = logging.getLogger(__name__)


@dataclass
class Trade:
    """Single executed trade record."""
    trade_id: str
    pair: str
    direction: str  # "buy" or "sell"
    price: float
    volume: float
    cost: float  # Price × Volume
    fee: float
    timestamp: int
    postxid: str  # Kraken post-transaction ID

    def pnl(self) -> float:
        """Return PnL for this single trade (approximate)."""
        return self.cost - self.fee


@dataclass
class PositionSnapshot:
    """Open position at a point in time."""
    pair: str
    volume: float
    avg_entry_price: float
    current_price: float
    unrealised_pnl: float
    timestamp: int


@dataclass
class PerformanceMetrics:
    """Complete performance summary for leaderboard."""
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate_pct: float
    total_pnl: float
    total_fees: float
    gross_pnl: float  # Before fees
    realised_pnl: float
    unrealised_pnl: float
    net_pnl: float  # After fees
    max_drawdown_pct: float
    sharpe_ratio: float
    best_trade: float
    worst_trade: float
    avg_win: float
    avg_loss: float
    profit_factor: float
    api_key_hash: str  # SHA256 of API key for verification
    submission_timestamp: int


class KrakenAPIClient:
    """
    Read-only Kraken API client for trade history and performance tracking.
    No execution or withdrawal access — data verification only.
    """

    def __init__(self, api_key: str, api_secret: str):
        """
        Initialize with Kraken API credentials.

        Args:
            api_key: Kraken API public key
            api_secret: Kraken API private key (base64 encoded)
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.api_url = "https://api.kraken.com"
        self.version = "0"  # API v0
        self.session = requests.Session()

    def _get_kraken_signature(self, urlpath: str, data: Dict, nonce: str) -> str:
        """
        Generate Kraken API signature for authentication.
        """
        postdata = json.dumps(data)
        encoded = (str(nonce) + postdata).encode()
        message = urlpath.encode() + hashlib.sha256(encoded).digest()

        signature = hmac.new(
            base64.b64decode(self.api_secret),
            message,
            hashlib.sha512,
        )
        sigdigest = base64.b64encode(signature.digest()).decode()
        return sigdigest

    def _kraken_request(
        self, endpoint: str, data: Optional[Dict] = None, private: bool = False
    ) -> Optional[Dict]:
        """
        Make authenticated request to Kraken API.

        Args:
            endpoint: API endpoint (e.g., "Trades")
            data: Request parameters
            private: True for private endpoints (requires auth)

        Returns:
            Response JSON or None if failed
        """
        try:
            if data is None:
                data = {}

            if private:
                # Private endpoint
                nonce = str(int(time.time() * 1000))
                data["nonce"] = nonce
                urlpath = f"/{self.version}/private/{endpoint}"

                signature = self._get_kraken_signature(urlpath, data, nonce)
                headers = {
                    "API-Sign": signature,
                    "API-Key": self.api_key,
                }

                url = self.api_url + urlpath
                response = self.session.post(url, data=data, headers=headers, timeout=10)
            else:
                # Public endpoint
                urlpath = f"/{self.version}/public/{endpoint}"
                url = self.api_url + urlpath
                response = self.session.get(url, params=data, timeout=10)

            if response.status_code != 200:
                logger.error(f"[red]Kraken API error {response.status_code}: {response.text}[/red]")
                return None

            result = response.json()

            if result.get("error"):
                logger.error(f"[red]Kraken API error: {result['error']}[/red]")
                return None

            return result.get("result")

        except Exception as e:
            logger.error(f"[red]Kraken API request failed: {e}[/red]")
            return None

    def get_closed_trades(self, hours: int = 24) -> Optional[List[Trade]]:
        """
        Fetch closed trades from the last N hours.

        Args:
            hours: Number of hours to look back (default 24)

        Returns:
            List of Trade objects or None if failed
        """
        try:
            # Fetch closed trades
            trades_data = self._kraken_request("TradesHistory", {"trades": True}, private=True)

            if not trades_data:
                logger.warning("[yellow]No trade history available[/yellow]")
                return []

            trades_dict = trades_data.get("trades", {})
            cutoff_time = int(time.time()) - (hours * 3600)

            trades = []
            for trade_id, trade_info in trades_dict.items():
                timestamp = int(trade_info.get("time", 0))

                # Only include recent trades
                if timestamp < cutoff_time:
                    continue

                pair = trade_info.get("pair", "")
                direction = "buy" if trade_info.get("type") == "buy" else "sell"
                price = float(trade_info.get("price", 0))
                volume = float(trade_info.get("vol", 0))
                cost = float(trade_info.get("cost", 0))
                fee = float(trade_info.get("fee", 0))
                postxid = trade_info.get("postxid", "")

                trades.append(
                    Trade(
                        trade_id=trade_id,
                        pair=pair,
                        direction=direction,
                        price=price,
                        volume=volume,
                        cost=cost,
                        fee=fee,
                        timestamp=timestamp,
                        postxid=postxid,
                    )
                )

            logger.info(f"[green]Fetched {len(trades)} trades from Kraken[/green]")
            return trades

        except Exception as e:
            logger.error(f"[red]Failed to get closed trades: {e}[/red]")
            return None

    def get_open_positions(self) -> Optional[Dict[str, PositionSnapshot]]:
        """
        Fetch current open positions.

        Returns:
            Dict of pair → PositionSnapshot or None if failed
        """
        try:
            positions_data = self._kraken_request("OpenPositions", {}, private=True)

            if not positions_data:
                logger.info("[dim]No open positions[/dim]")
                return {}

            positions = {}

            # Fetch current ticker prices
            ticker_data = self._kraken_request("Ticker", {"pair": config.PAIR}, private=False)

            if not ticker_data:
                logger.warning("[yellow]Could not fetch current prices[/yellow]")
                return {}

            current_price = float(ticker_data.get(list(ticker_data.keys())[0], {}).get("c", [0])[0])

            for position_id, position_info in positions_data.items():
                pair = position_info.get("pair", "")
                volume = float(position_info.get("vol", 0))
                avg_entry_price = float(position_info.get("cost", 0)) / volume if volume > 0 else 0
                unrealised_pnl = (current_price - avg_entry_price) * volume

                positions[pair] = PositionSnapshot(
                    pair=pair,
                    volume=volume,
                    avg_entry_price=avg_entry_price,
                    current_price=current_price,
                    unrealised_pnl=unrealised_pnl,
                    timestamp=int(time.time()),
                )

            logger.info(f"[green]Fetched {len(positions)} open positions[/green]")
            return positions

        except Exception as e:
            logger.error(f"[red]Failed to get open positions: {e}[/red]")
            return None

    def calculate_performance_metrics(
        self, trades: List[Trade], unrealised_pnl: float = 0.0
    ) -> Optional[PerformanceMetrics]:
        """
        Calculate comprehensive performance metrics from trade history.

        Args:
            trades: List of Trade objects
            unrealised_pnl: Current unrealised PnL from open positions

        Returns:
            PerformanceMetrics object
        """
        try:
            if not trades:
                logger.warning("[yellow]No trades to analyze[/yellow]")
                return None

            total_trades = len(trades)
            total_fees = sum(t.fee for t in trades)
            realised_pnl = sum(t.cost - t.fee for t in trades)

            # Categorize wins/losses
            trades_with_pnl = []
            for trade in trades:
                trade_pnl = trade.cost - trade.fee
                trades_with_pnl.append(trade_pnl)

            winning_trades = len([p for p in trades_with_pnl if p > 0])
            losing_trades = len([p for p in trades_with_pnl if p < 0])
            win_rate_pct = (winning_trades / total_trades * 100) if total_trades > 0 else 0.0

            # PnL metrics
            total_pnl = sum(trades_with_pnl)
            gross_pnl = sum(t.cost for t in trades)
            net_pnl = realised_pnl + unrealised_pnl

            # Best/worst trades
            best_trade = max(trades_with_pnl) if trades_with_pnl else 0.0
            worst_trade = min(trades_with_pnl) if trades_with_pnl else 0.0

            # Win/loss averages
            wins = [p for p in trades_with_pnl if p > 0]
            losses = [p for p in trades_with_pnl if p < 0]
            avg_win = sum(wins) / len(wins) if wins else 0.0
            avg_loss = abs(sum(losses) / len(losses)) if losses else 0.0

            # Profit factor
            profit_factor = avg_win / avg_loss if avg_loss > 0 else 0.0

            # Sharpe ratio (simplified)
            if len(trades_with_pnl) > 1:
                mean_pnl = sum(trades_with_pnl) / len(trades_with_pnl)
                variance = sum((p - mean_pnl) ** 2 for p in trades_with_pnl) / len(trades_with_pnl)
                std_dev = variance ** 0.5
                sharpe_ratio = (mean_pnl / std_dev) if std_dev > 0 else 0.0
            else:
                sharpe_ratio = 0.0

            # Maximum drawdown (simplified)
            cumulative = 0.0
            peak = 0.0
            max_dd = 0.0
            for pnl in trades_with_pnl:
                cumulative += pnl
                if cumulative > peak:
                    peak = cumulative
                drawdown = peak - cumulative
                if drawdown > max_dd:
                    max_dd = drawdown

            initial_capital = 1000.0  # Assumed for %-based calculation
            max_drawdown_pct = (max_dd / initial_capital * 100) if initial_capital > 0 else 0.0

            # API key hash for verification
            api_key_hash = hashlib.sha256(self.api_key.encode()).hexdigest()

            metrics = PerformanceMetrics(
                total_trades=total_trades,
                winning_trades=winning_trades,
                losing_trades=losing_trades,
                win_rate_pct=win_rate_pct,
                total_pnl=total_pnl,
                total_fees=total_fees,
                gross_pnl=gross_pnl,
                realised_pnl=realised_pnl,
                unrealised_pnl=unrealised_pnl,
                net_pnl=net_pnl,
                max_drawdown_pct=max_drawdown_pct,
                sharpe_ratio=sharpe_ratio,
                best_trade=best_trade,
                worst_trade=worst_trade,
                avg_win=avg_win,
                avg_loss=avg_loss,
                profit_factor=profit_factor,
                api_key_hash=api_key_hash,
                submission_timestamp=int(time.time()),
            )

            return metrics

        except Exception as e:
            logger.error(f"[red]Failed to calculate metrics: {e}[/red]")
            return None

    def format_leaderboard_submission(self, metrics: PerformanceMetrics) -> Dict:
        """
        Format performance metrics for lablab.ai leaderboard submission.

        Returns:
            JSON-serializable dictionary
        """
        return {
            "submission": {
                "timestamp": datetime.fromtimestamp(metrics.submission_timestamp).isoformat(),
                "api_key_hash": metrics.api_key_hash,
            },
            "performance": {
                "net_pnl": round(metrics.net_pnl, 2),
                "realised_pnl": round(metrics.realised_pnl, 2),
                "unrealised_pnl": round(metrics.unrealised_pnl, 2),
                "total_trades": metrics.total_trades,
                "winning_trades": metrics.winning_trades,
                "losing_trades": metrics.losing_trades,
                "win_rate_pct": round(metrics.win_rate_pct, 2),
            },
            "risk_metrics": {
                "max_drawdown_pct": round(metrics.max_drawdown_pct, 2),
                "sharpe_ratio": round(metrics.sharpe_ratio, 2),
                "profit_factor": round(metrics.profit_factor, 2),
            },
            "trade_details": {
                "best_trade": round(metrics.best_trade, 2),
                "worst_trade": round(metrics.worst_trade, 2),
                "avg_win": round(metrics.avg_win, 2),
                "avg_loss": round(metrics.avg_loss, 2),
            },
            "costs": {
                "total_fees": round(metrics.total_fees, 2),
            },
        }
