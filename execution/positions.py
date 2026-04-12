"""
NEXUS Position Manager — track open positions and close with stop-loss/take-profit logic.
"""
import json
import logging
import time
from dataclasses import dataclass, asdict
from typing import Optional, Dict, List
from enum import Enum

import config

logger = logging.getLogger(__name__)


class ExitReason(Enum):
    """Why a position was closed."""
    TAKE_PROFIT = "take_profit"
    STOP_LOSS = "stop_loss"
    TIME_BASED = "time_based"
    MANUAL = "manual"


@dataclass
class Position:
    """Open or closed position record."""
    trade_id: str
    direction: str  # "BUY" or "SELL"
    entry_price: float
    volume: float
    entry_timestamp: int
    exit_price: Optional[float] = None
    exit_timestamp: Optional[int] = None
    exit_reason: Optional[str] = None  # ExitReason enum value
    pnl_usd: float = 0.0
    pnl_pct: float = 0.0
    status: str = "open"  # "open" or "closed"
    entry_confidence: float = 0.0  # consensus confidence at entry

    def to_dict(self):
        """Serialize for JSON storage."""
        return asdict(self)

    def is_open(self) -> bool:
        """True if position is currently open."""
        return self.status == "open"

    def unrealised_pnl(self, current_price: float) -> float:
        """Calculate unrealised PnL at current price."""
        if self.direction == "BUY":
            price_change = current_price - self.entry_price
        else:  # SELL
            price_change = self.entry_price - current_price
        return price_change * self.volume

    def unrealised_pnl_pct(self, current_price: float) -> float:
        """Unrealised PnL as percentage."""
        if self.entry_price == 0:
            return 0.0
        unrealised = self.unrealised_pnl(current_price)
        entry_notional = self.entry_price * self.volume
        return (unrealised / entry_notional * 100) if entry_notional > 0 else 0.0


class PositionManager:
    """Manage open/closed positions with exit logic."""

    def __init__(self, positions_file: str = config.POSITIONS_FILE):
        self.positions_file = positions_file
        self.positions: Dict[str, Position] = {}
        self.closed_positions: List[Position] = []
        self.load_positions()

    def load_positions(self):
        """Load position history from disk."""
        try:
            with open(self.positions_file, "r") as f:
                data = json.load(f)
                for pos_dict in data:
                    pos = Position(**pos_dict)
                    if pos.is_open():
                        self.positions[pos.trade_id] = pos
                    else:
                        self.closed_positions.append(pos)
            logger.info(f"[green]Loaded {len(self.positions)} open positions[/green]")
        except FileNotFoundError:
            logger.info("[dim]No existing positions file; starting fresh[/dim]")

    def save_positions(self):
        """Persist all positions to disk."""
        try:
            all_positions = list(self.positions.values()) + self.closed_positions
            with open(self.positions_file, "w") as f:
                json.dump([p.to_dict() for p in all_positions], f, indent=2)
        except Exception as e:
            logger.error(f"[red]Failed to save positions: {e}[/red]")

    def open_position(
        self,
        trade_id: str,
        direction: str,
        entry_price: float,
        volume: float,
        entry_confidence: float = 0.0,
    ) -> Position:
        """Open a new position."""
        position = Position(
            trade_id=trade_id,
            direction=direction,
            entry_price=entry_price,
            volume=volume,
            entry_timestamp=int(time.time()),
            status="open",
            entry_confidence=entry_confidence,
        )
        self.positions[trade_id] = position
        self.save_positions()
        logger.info(
            f"[cyan]Position opened[/cyan]: {direction} {volume:.4f} @ ${entry_price:.2f}"
        )
        return position

    def close_position(
        self,
        trade_id: str,
        exit_price: float,
        exit_reason: str = ExitReason.MANUAL.value,
    ) -> Optional[Position]:
        """Close an open position. Returns the closed position or None if not found."""
        if trade_id not in self.positions:
            logger.warning(f"[yellow]Position {trade_id} not found[/yellow]")
            return None

        position = self.positions.pop(trade_id)
        position.exit_price = exit_price
        position.exit_timestamp = int(time.time())
        position.exit_reason = exit_reason
        position.status = "closed"

        # Compute realised PnL
        if position.direction == "BUY":
            price_change = exit_price - position.entry_price
        else:  # SELL
            price_change = position.entry_price - exit_price

        position.pnl_usd = price_change * position.volume
        position.pnl_pct = (price_change / position.entry_price * 100) if position.entry_price > 0 else 0.0

        self.closed_positions.append(position)
        self.save_positions()

        status_color = "[green]✓" if position.pnl_usd >= 0 else "[red]✗"
        logger.info(
            f"{status_color}[/] Position closed ({exit_reason}): "
            f"{position.direction} {position.volume:.4f} @ ${exit_price:.2f} → "
            f"${position.pnl_usd:.2f} ({position.pnl_pct:+.2f}%)"
        )
        return position

    def check_exits(self, current_price: float) -> List[Position]:
        """
        Check all open positions for stop-loss / take-profit hits.
        Returns: list of positions that should be closed (but does NOT close them).
        """
        positions_to_close = []

        for trade_id, position in self.positions.items():
            unrealised_pnl_pct = position.unrealised_pnl_pct(current_price)

            # Check take-profit
            if unrealised_pnl_pct >= config.TAKE_PROFIT_PCT:
                logger.info(
                    f"[bold green]TAKE-PROFIT HIT[/bold green] ({trade_id}): "
                    f"{unrealised_pnl_pct:.2f}% at ${current_price:.2f}"
                )
                positions_to_close.append(position)
                continue

            # Check stop-loss
            if unrealised_pnl_pct <= -config.STOP_LOSS_PCT:
                logger.info(
                    f"[bold red]STOP-LOSS HIT[/bold red] ({trade_id}): "
                    f"{unrealised_pnl_pct:.2f}% at ${current_price:.2f}"
                )
                positions_to_close.append(position)
                continue

            # Check time-based exit (e.g., hold max 24 hours)
            age_seconds = int(time.time()) - position.entry_timestamp
            max_hold_seconds = config.MAX_HOLD_TIME_MINUTES * 60
            if age_seconds > max_hold_seconds:
                logger.info(
                    f"[bold yellow]TIME-BASED EXIT[/bold yellow] ({trade_id}): "
                    f"held {age_seconds}s, limit {max_hold_seconds}s"
                )
                positions_to_close.append(position)

        return positions_to_close

    def get_open_positions_value(self, current_price: float) -> float:
        """Sum of all open position notionals at current price."""
        total = 0.0
        for position in self.positions.values():
            total += position.volume * current_price  # Simplified notional value
        return total

    def has_open_position(self) -> bool:
        """
        Check if there is any open position.
        """
        return len(self.positions) > 0

    def get_total_unrealised_pnl(self, current_price: float) -> float:
        """Sum of all unrealised PnL."""
        total = 0.0
        for position in self.positions.values():
            total += position.unrealised_pnl(current_price)
        return total

    def get_total_realised_pnl(self) -> float:
        """Sum of all closed positions' PnL."""
        return sum(p.pnl_usd for p in self.closed_positions)

    def portfolio_equity_curve_add(self, cash: float, current_price: float, timestamp: int):
        """
        Record total portfolio value for later YieldOptimizer analysis.
        Equity = cash + unrealised positions + realised PnL.
        """
        unrealised = self.get_total_unrealised_pnl(current_price)
        realised = self.get_total_realised_pnl()
        total_equity = cash + unrealised + realised

        # Append to equity curve file
        try:
            equity_file = config.EQUITY_CURVE_FILE
            entries = []
            try:
                with open(equity_file, "r") as f:
                    entries = json.load(f)
            except FileNotFoundError:
                pass

            entries.append({
                "timestamp": timestamp,
                "equity": total_equity,
                "cash": cash,
                "unrealised_pnl": unrealised,
                "realised_pnl": realised,
            })

            with open(equity_file, "w") as f:
                json.dump(entries, f, indent=2)
        except Exception as e:
            logger.error(f"[red]Failed to write equity curve: {e}[/red]")

    def positions_summary(self, current_price: float) -> str:
        """Generate positions summary."""
        if not self.positions:
            return "[dim]No open positions[/dim]"

        total_unrealised = self.get_total_unrealised_pnl(current_price)
        total_unrealised_color = "[green]+" if total_unrealised >= 0 else "[red]"

        lines = [
            f"\n[bold]Open Positions ({len(self.positions)})[/bold]",
            f"Total unrealised PnL: {total_unrealised_color}${total_unrealised:.2f}[/]",
            "",
        ]

        for trade_id, pos in self.positions.items():
            unrealised = pos.unrealised_pnl(current_price)
            unrealised_pct = pos.unrealised_pnl_pct(current_price)
            age_min = (int(time.time()) - pos.entry_timestamp) // 60
            color = "[green]+" if unrealised >= 0 else "[red]"
            lines.append(
                f"  {trade_id}: {pos.direction} {pos.volume:.4f} @ ${pos.entry_price:.2f} "
                f"→ {color}${unrealised:.2f}[/] ({unrealised_pct:+.2f}%) age={age_min}min"
            )

        return "\n".join(lines)
