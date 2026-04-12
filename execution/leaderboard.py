"""
NEXUS Leaderboard Integration — Submit performance to lablab.ai for competition ranking.
Fetches trade history from Kraken API and formats for submission.
"""
import logging
import json
import time
from typing import Optional
from datetime import datetime

import config
from execution.kraken_api import KrakenAPIClient

logger = logging.getLogger(__name__)


class LeaderboardManager:
    """
    Manage performance tracking and leaderboard submissions for lablab.ai competition.
    """

    def __init__(self):
        """Initialize leaderboard manager with Kraken API client."""
        self.kraken_api = KrakenAPIClient(config.KRAKEN_API_KEY, config.KRAKEN_API_SECRET)
        self.submission_file = "nexus_leaderboard_submission.json"
        self.submission_history = []
        self.load_submission_history()

    def load_submission_history(self):
        """Load previous submission history from file."""
        try:
            with open(self.submission_file, "r") as f:
                self.submission_history = json.load(f)
            logger.info(f"[green]Loaded {len(self.submission_history)} previous submissions[/green]")
        except FileNotFoundError:
            logger.info("[dim]No previous submissions file[/dim]")
            self.submission_history = []

    def save_submission(self, submission: dict):
        """Save submission to history file."""
        try:
            self.submission_history.append(submission)
            with open(self.submission_file, "w") as f:
                json.dump(self.submission_history, f, indent=2)
            logger.info(f"[green]Saved submission #{len(self.submission_history)}[/green]")
        except Exception as e:
            logger.error(f"[red]Failed to save submission: {e}[/red]")

    def fetch_and_calculate_metrics(self, hours: int = 24) -> Optional[dict]:
        """
        Fetch trade history and calculate performance metrics.

        Args:
            hours: Number of hours to look back

        Returns:
            Formatted submission dict or None
        """
        try:
            # Fetch closed trades
            trades = self.kraken_api.get_closed_trades(hours=hours)
            if not trades:
                logger.warning("[yellow]No trades found for metrics calculation[/yellow]")
                return None

            # Fetch open positions (for unrealised PnL)
            positions = self.kraken_api.get_open_positions()
            unrealised_pnl = sum(p.unrealised_pnl for p in positions.values()) if positions else 0.0

            # Calculate metrics
            metrics = self.kraken_api.calculate_performance_metrics(trades, unrealised_pnl)

            if not metrics:
                logger.error("[red]Failed to calculate metrics[/red]")
                return None

            # Format for submission
            submission = self.kraken_api.format_leaderboard_submission(metrics)

            return submission

        except Exception as e:
            logger.error(f"[red]Failed to fetch and calculate metrics: {e}[/red]")
            return None

    def submit_to_leaderboard(self) -> bool:
        """
        Submit current performance to leaderboard.

        Returns:
            True if submission successful, False otherwise
        """
        if not config.KRAKEN_SUBMISSION_ENABLED:
            logger.info("[dim]Leaderboard submission disabled[/dim]")
            return False

        try:
            # Fetch and calculate metrics
            submission = self.fetch_and_calculate_metrics(hours=24)

            if not submission:
                logger.error("[red]Could not prepare submission[/red]")
                return False

            # Save to local history
            self.save_submission(submission)

            # Log submission
            perf = submission.get("performance", {})
            risk = submission.get("risk_metrics", {})

            logger.info(
                f"[bold green]Leaderboard Submission[/bold green] @ {submission['submission']['timestamp']}\n"
                f"  Net PnL: ${perf.get('net_pnl', 0):.2f}\n"
                f"  Win Rate: {perf.get('win_rate_pct', 0):.1f}%\n"
                f"  Trades: {perf.get('total_trades', 0)}\n"
                f"  Sharpe: {risk.get('sharpe_ratio', 0):.2f}\n"
                f"  Max DD: {risk.get('max_drawdown_pct', 0):.2f}%"
            )

            # TODO: Push to lablab.ai leaderboard API endpoint
            # POST to: https://api.lablab.ai/leaderboard/nexus-trading-challenge
            # Include: submission, api_key_hash for verification

            logger.info("[blue]Ready for lablab.ai leaderboard API submission[/blue]")
            return True

        except Exception as e:
            logger.error(f"[red]Leaderboard submission failed: {e}[/red]")
            return False

    def get_current_rank(self) -> Optional[dict]:
        """
        Calculate current standing (percentage to beat, ranking among simulated competitors).

        Returns:
            Rank metrics or None
        """
        try:
            submission = self.fetch_and_calculate_metrics(hours=24)

            if not submission:
                return None

            perf = submission.get("performance", {})
            net_pnl = perf.get("net_pnl", 0)
            win_rate = perf.get("win_rate_pct", 0)
            risk = submission.get("risk_metrics", {})
            sharpe = risk.get("sharpe_ratio", 0)

            # Scoring algorithm (can be tuned)
            # Score = (net_pnl × 0.5) + (win_rate × 2) + (sharpe × 100)
            score = (net_pnl * 0.5) + (win_rate * 2) + (sharpe * 100)

            return {
                "net_pnl": net_pnl,
                "win_rate_pct": win_rate,
                "sharpe_ratio": sharpe,
                "composite_score": round(score, 2),
                "submission_count": len(self.submission_history),
                "last_submission": self.submission_history[-1]["submission"]["timestamp"]
                if self.submission_history
                else None,
            }

        except Exception as e:
            logger.error(f"[red]Failed to calculate rank: {e}[/red]")
            return None

    def leaderboard_status(self) -> str:
        """Generate human-readable leaderboard status string."""
        try:
            rank = self.get_current_rank()

            if not rank:
                return "[yellow]Unable to fetch leaderboard status[/yellow]"

            lines = [
                "[bold]NEXUS Leaderboard Status[/bold]",
                "",
                f"Net PnL: ${rank['net_pnl']:.2f}",
                f"Win Rate: {rank['win_rate_pct']:.1f}%",
                f"Sharpe Ratio: {rank['sharpe_ratio']:.2f}",
                f"Composite Score: {rank['composite_score']:.1f}",
                f"Submissions: {rank['submission_count']}",
                f"Last Submission: {rank['last_submission']}",
            ]

            return "\n".join(lines)

        except Exception as e:
            logger.error(f"[red]Failed to generate leaderboard status: {e}[/red]")
            return "[red]Error generating status[/red]"
