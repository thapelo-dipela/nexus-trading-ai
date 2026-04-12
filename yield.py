"""
NEXUS Yield Optimizer — Maximizes risk-adjusted returns and portfolio yield.
Addresses: Best Yield / Portfolio Agent, Best Risk-Adjusted Return.
"""
import logging
import math
from typing import Optional, List, Tuple, Dict
from dataclasses import dataclass

import numpy as np

import config

logger = logging.getLogger(__name__)


@dataclass
class PortfolioMetrics:
    """Comprehensive portfolio performance metrics."""
    total_return_pct: float
    annualized_return_pct: float
    volatility_pct: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown_pct: float
    calmar_ratio: float
    win_rate_pct: float
    profit_factor: float  # Gross profit / gross loss
    consecutive_wins: int
    consecutive_losses: int


class YieldOptimizer:
    """
    Portfolio yield optimization engine.
    Maximizes risk-adjusted returns via:
    - Kelly Criterion for position sizing
    - Sortino ratio optimization
    - Drawdown minimization
    - Volatility targeting
    """

    def __init__(self):
        self.trade_history: List[Dict] = []
        self.peak_portfolio_value = 0.0

    def record_trade(self, direction: str, entry_price: float, exit_price: float, volume: float):
        """Record a completed trade."""
        pnl = (exit_price - entry_price) * volume if direction == "BUY" else (entry_price - exit_price) * volume
        self.trade_history.append({
            "direction": direction,
            "entry_price": entry_price,
            "exit_price": exit_price,
            "volume": volume,
            "pnl": pnl,
        })

    def compute_kelly_position_size(
        self,
        win_rate: float,
        avg_win: float,
        avg_loss: float,
        portfolio_value: float,
    ) -> float:
        """
        Compute optimal position size using Kelly Criterion.
        Maximizes long-term geometric growth.

        Kelly% = (win_rate × avg_win - (1 - win_rate) × avg_loss) / avg_win
        Position = Kelly% × portfolio_value
        """
        if avg_win <= 0 or avg_loss <= 0:
            return config.MIN_TRADE_SIZE_USD

        kelly_pct = (win_rate * avg_win - (1 - win_rate) * avg_loss) / avg_win

        # Apply safety factor (use 25% of Kelly to reduce bust risk)
        kelly_safety = kelly_pct * 0.25

        # Clamp between limits
        position = kelly_safety * portfolio_value
        return max(config.MIN_TRADE_SIZE_USD, min(config.MAX_TRADE_SIZE_USD, position))

    def compute_sharpe_ratio(
        self,
        returns: List[float],
        risk_free_rate: float = 0.02,
    ) -> float:
        """
        Compute Sharpe ratio.
        (mean_return - risk_free_rate) / std_dev
        """
        if len(returns) < 2:
            return 0.0

        mean_return = np.mean(returns)
        std_dev = np.std(returns)

        if std_dev == 0:
            return 0.0

        return (mean_return - risk_free_rate) / std_dev

    def compute_sortino_ratio(
        self,
        returns: List[float],
        risk_free_rate: float = 0.02,
    ) -> float:
        """
        Compute Sortino ratio (only penalizes downside volatility).
        (mean_return - risk_free_rate) / downside_std_dev
        """
        if len(returns) < 2:
            return 0.0

        mean_return = np.mean(returns)

        # Downside deviation: only negative returns
        downside_returns = [r for r in returns if r < 0]
        if not downside_returns:
            downside_std = 0.0
        else:
            downside_std = np.std(downside_returns)

        if downside_std == 0:
            return 0.0

        return (mean_return - risk_free_rate) / downside_std

    def compute_calmar_ratio(
        self,
        returns: List[float],
        max_drawdown_pct: float,
    ) -> float:
        """
        Compute Calmar ratio (return / max drawdown).
        Higher is better (return with lower drawdown).
        """
        if max_drawdown_pct == 0 or len(returns) == 0:
            return 0.0

        total_return = np.sum(returns)
        return total_return / max_drawdown_pct

    def compute_max_drawdown(self, equity_curve: List[float]) -> Tuple[float, int, int]:
        """
        Compute maximum drawdown percentage and when it occurred.
        Returns: (max_drawdown_pct, start_idx, end_idx)
        """
        if len(equity_curve) < 2:
            return 0.0, 0, 0

        peak = equity_curve[0]
        max_dd = 0.0
        peak_idx = 0
        trough_idx = 0

        for i, value in enumerate(equity_curve):
            if value > peak:
                peak = value
                peak_idx = i

            dd = (peak - value) / peak * 100.0
            if dd > max_dd:
                max_dd = dd
                trough_idx = i

        return max_dd, peak_idx, trough_idx

    def compute_portfolio_metrics(
        self,
        equity_curve: List[float],
    ) -> PortfolioMetrics:
        """
        Compute comprehensive portfolio metrics.
        Assumes equity_curve is daily NAV snapshots.
        """
        if len(equity_curve) < 2:
            return PortfolioMetrics(
                total_return_pct=0.0,
                annualized_return_pct=0.0,
                volatility_pct=0.0,
                sharpe_ratio=0.0,
                sortino_ratio=0.0,
                max_drawdown_pct=0.0,
                calmar_ratio=0.0,
                win_rate_pct=0.0,
                profit_factor=0.0,
                consecutive_wins=0,
                consecutive_losses=0,
            )

        # Returns (daily)
        returns = np.diff(equity_curve) / equity_curve[:-1]

        # Total and annualized return
        total_return = (equity_curve[-1] - equity_curve[0]) / equity_curve[0]
        trading_days = len(equity_curve)
        annualized = (1 + total_return) ** (252.0 / trading_days) - 1

        # Volatility
        volatility = np.std(returns) * np.sqrt(252)

        # Sharpe and Sortino
        sharpe = self.compute_sharpe_ratio(returns.tolist())
        sortino = self.compute_sortino_ratio(returns.tolist())

        # Max drawdown
        max_dd, _, _ = self.compute_max_drawdown(equity_curve)

        # Calmar
        calmar = self.compute_calmar_ratio(returns.tolist(), max_dd)

        # Win rate
        wins = len([r for r in returns if r > 0])
        win_rate = wins / len(returns) * 100.0

        # Profit factor
        gross_profit = sum([r for r in returns if r > 0])
        gross_loss = abs(sum([r for r in returns if r < 0]))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else gross_profit

        # Consecutive wins/losses
        consecutive_wins = 0
        consecutive_losses = 0
        current_wins = 0
        current_losses = 0

        for r in returns:
            if r > 0:
                current_wins += 1
                current_losses = 0
                consecutive_wins = max(consecutive_wins, current_wins)
            elif r < 0:
                current_losses += 1
                current_wins = 0
                consecutive_losses = max(consecutive_losses, current_losses)

        return PortfolioMetrics(
            total_return_pct=total_return * 100.0,
            annualized_return_pct=annualized * 100.0,
            volatility_pct=volatility * 100.0,
            sharpe_ratio=sharpe,
            sortino_ratio=sortino,
            max_drawdown_pct=max_dd,
            calmar_ratio=calmar,
            win_rate_pct=win_rate,
            profit_factor=profit_factor,
            consecutive_wins=consecutive_wins,
            consecutive_losses=consecutive_losses,
        )

    def volatility_target_position_size(
        self,
        portfolio_value: float,
        current_volatility_pct: float,
        target_volatility_pct: float = 10.0,
    ) -> float:
        """
        Scale position size to maintain target portfolio volatility.
        Higher vol → smaller positions; lower vol → larger positions.
        """
        if current_volatility_pct <= 0:
            return config.MIN_TRADE_SIZE_USD

        volatility_ratio = target_volatility_pct / current_volatility_pct

        # Base position scaled by vol ratio
        base_position = portfolio_value * 0.01  # 1% base
        scaled = base_position * volatility_ratio

        return max(config.MIN_TRADE_SIZE_USD, min(config.MAX_TRADE_SIZE_USD, scaled))

    def diversification_score(
        self,
        agent_votes: List,
        market_data,
    ) -> float:
        """
        Compute diversification score (0-1).
        Higher when agents have diverse opinions (reduced herd risk).
        """
        if len(agent_votes) < 2:
            return 0.5

        # Count votes by direction
        buy_votes = sum(1 for v in agent_votes if v.direction.value == "BUY")
        sell_votes = sum(1 for v in agent_votes if v.direction.value == "SELL")
        hold_votes = sum(1 for v in agent_votes if v.direction.value == "HOLD")

        total = len(agent_votes)

        # Entropy-based diversity (higher entropy = more diverse)
        votes_dist = np.array([buy_votes, sell_votes, hold_votes]) / total

        # Filter out zero probabilities
        votes_dist = votes_dist[votes_dist > 0]

        if len(votes_dist) == 0:
            return 0.0

        entropy = -np.sum(votes_dist * np.log2(votes_dist + 1e-9))
        max_entropy = np.log2(len(votes_dist))

        # Normalize to 0-1
        normalized_entropy = entropy / max_entropy if max_entropy > 0 else 0

        return min(1.0, normalized_entropy)

    def portfolio_stress_test(
        self,
        portfolio_value: float,
        market_data,
        scenarios: Optional[Dict[str, float]] = None,
    ) -> Dict[str, float]:
        """
        Stress test portfolio against various market scenarios.
        Returns estimated portfolio value under each scenario.

        Default scenarios:
        - flash_crash: -20% sudden move
        - vix_spike: volatility +50%
        - liquidity_crunch: bid-ask spread widens
        """
        if scenarios is None:
            scenarios = {
                "flash_crash": -20.0,
                "sharp_rally": 15.0,
                "vix_spike": -10.0,  # Volatility increase reduces portfolio
            }

        results = {}

        for scenario_name, scenario_impact_pct in scenarios.items():
            impact = portfolio_value * (scenario_impact_pct / 100.0)
            stressed_value = portfolio_value + impact

            results[scenario_name] = stressed_value

        return results

    def yield_optimization_report(self, equity_curve: List[float]) -> str:
        """Generate yield optimization report."""
        metrics = self.compute_portfolio_metrics(equity_curve)

        lines = [
            "[bold]NEXUS Yield Optimization Report[/bold]",
            "",
            "[bold green]Returns[/bold green]",
            f"  Total Return: {metrics.total_return_pct:.2f}%",
            f"  Annualized Return: {metrics.annualized_return_pct:.2f}%",
            "",
            "[bold green]Risk Metrics[/bold green]",
            f"  Volatility: {metrics.volatility_pct:.2f}%",
            f"  Max Drawdown: {metrics.max_drawdown_pct:.2f}%",
            "",
            "[bold green]Risk-Adjusted Returns[/bold green]",
            f"  Sharpe Ratio: {metrics.sharpe_ratio:.2f}",
            f"  Sortino Ratio: {metrics.sortino_ratio:.2f}",
            f"  Calmar Ratio: {metrics.calmar_ratio:.2f}",
            "",
            "[bold green]Win Statistics[/bold green]",
            f"  Win Rate: {metrics.win_rate_pct:.1f}%",
            f"  Profit Factor: {metrics.profit_factor:.2f}",
            f"  Consecutive Wins: {metrics.consecutive_wins}",
            f"  Consecutive Losses: {metrics.consecutive_losses}",
        ]

        return "\n".join(lines)
