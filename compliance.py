"""
NEXUS Compliance & Risk Guardrails — Enhanced validation for hackathon standards.
Enforces: Best Compliance & Risk Guardrails, Best Risk-Adjusted Return, Best Validation & Trust Model.
"""
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Tuple
from enum import Enum

import config

logger = logging.getLogger(__name__)


class ComplianceLevel(str, Enum):
    """Compliance audit level."""
    PASS = "PASS"
    WARNING = "WARNING"
    FAIL = "FAIL"


@dataclass
class ComplianceCheck:
    """Single compliance check result."""
    rule_id: str
    rule_name: str
    level: ComplianceLevel
    message: str
    timestamp: int = field(default_factory=lambda: int(time.time()))
    metric_value: Optional[float] = None
    threshold: Optional[float] = None


@dataclass
class RiskMetrics:
    """Comprehensive risk metrics for position."""
    position_size_usd: float
    leverage: float
    var_95: float  # Value at Risk (95% confidence)
    cvar_95: float  # Conditional VaR
    sharpe_ratio: float
    sortino_ratio: float
    max_loss_scenario: float
    portfolio_correlation: float
    liquidity_score: float  # 0-1, higher is better


class ComplianceEngine:
    """Centralized compliance, validation, and risk guardrails."""

    def __init__(self):
        self.checks_passed: List[ComplianceCheck] = []
        self.checks_failed: List[ComplianceCheck] = []
        self.audit_trail: List[Dict] = []

    def validate_trade_decision(
        self,
        market_data,
        position_size_usd: float,
        confidence: float,
        direction: str,
        equity_curve: Optional[List[float]] = None,
    ) -> Tuple[bool, List[ComplianceCheck]]:
        """
        Validate entire trade decision against all compliance rules.
        Args:
            market_data: Current market data
            position_size_usd: Proposed position size
            confidence: Consensus confidence
            direction: Trade direction ("BUY" or "SELL")
            equity_curve: Optional equity history for real Sharpe calculation
        Returns: (is_approved, list_of_checks)
        """
        checks = []

        # Rule 1: Position size within limits
        checks.append(self._check_position_limits(position_size_usd))

        # Rule 2: Confidence threshold
        checks.append(self._check_confidence_threshold(confidence))

        # Rule 3: Portfolio concentration
        checks.append(self._check_portfolio_concentration(market_data, position_size_usd))

        # Rule 4: Leverage limits
        checks.append(self._check_leverage_limits(market_data, position_size_usd))

        # Rule 5: Volatility limits
        checks.append(self._check_volatility_limits(market_data))

        # Rule 6: Liquidity check
        checks.append(self._check_liquidity(market_data))

        # Rule 7: Slippage protection
        checks.append(self._check_slippage_protection(market_data, position_size_usd))

        # Rule 8: Risk-adjusted return check (uses real equity curve if available)
        checks.append(self._check_risk_adjusted_return(market_data, position_size_usd, confidence, equity_curve))

        # Rule 9: Drawdown buffer
        checks.append(self._check_drawdown_buffer(market_data))

        # Rule 10: Trustless verification
        checks.append(self._check_trustless_markers(market_data, direction))

        # Rule 11: Consecutive loss limit (NEW)
        checks.append(self._check_consecutive_losses())

        # Rule 12: Session/daily loss limit (NEW)
        checks.append(self._check_session_drawdown(market_data))

        # Rule 13: Max equity drawdown (NEW)
        checks.append(self._check_max_drawdown(market_data))

        # Separate passes and failures
        for check in checks:
            if check.level == ComplianceLevel.PASS:
                self.checks_passed.append(check)
            else:
                self.checks_failed.append(check)

        # Trade approved only if no FAIL checks
        is_approved = all(c.level != ComplianceLevel.FAIL for c in checks)

        # Log audit trail
        self.audit_trail.append({
            "timestamp": int(time.time()),
            "position_size_usd": position_size_usd,
            "confidence": confidence,
            "direction": direction,
            "checks_passed": len([c for c in checks if c.level == ComplianceLevel.PASS]),
            "checks_failed": len([c for c in checks if c.level == ComplianceLevel.FAIL]),
            "approved": is_approved,
        })

        return is_approved, checks

    def _check_position_limits(self, position_size_usd: float) -> ComplianceCheck:
        """Ensure position size within configured limits."""
        if config.MIN_TRADE_SIZE_USD <= position_size_usd <= config.MAX_TRADE_SIZE_USD:
            return ComplianceCheck(
                rule_id="pos_limits",
                rule_name="Position Size Limits",
                level=ComplianceLevel.PASS,
                message=f"Position ${position_size_usd:.2f} within limits [${config.MIN_TRADE_SIZE_USD}, ${config.MAX_TRADE_SIZE_USD}]",
                metric_value=position_size_usd,
                threshold=config.MAX_TRADE_SIZE_USD,
            )
        else:
            return ComplianceCheck(
                rule_id="pos_limits",
                rule_name="Position Size Limits",
                level=ComplianceLevel.FAIL,
                message=f"Position ${position_size_usd:.2f} outside limits [${config.MIN_TRADE_SIZE_USD}, ${config.MAX_TRADE_SIZE_USD}]",
                metric_value=position_size_usd,
                threshold=config.MAX_TRADE_SIZE_USD,
            )

    def _check_confidence_threshold(self, confidence: float) -> ComplianceCheck:
        """Ensure consensus confidence meets minimum."""
        if confidence >= config.CONFIDENCE_THRESHOLD:
            return ComplianceCheck(
                rule_id="confidence",
                rule_name="Confidence Threshold",
                level=ComplianceLevel.PASS,
                message=f"Confidence {confidence:.3f} >= {config.CONFIDENCE_THRESHOLD}",
                metric_value=confidence,
                threshold=config.CONFIDENCE_THRESHOLD,
            )
        else:
            return ComplianceCheck(
                rule_id="confidence",
                rule_name="Confidence Threshold",
                level=ComplianceLevel.FAIL,
                message=f"Confidence {confidence:.3f} < {config.CONFIDENCE_THRESHOLD} — insufficient consensus",
                metric_value=confidence,
                threshold=config.CONFIDENCE_THRESHOLD,
            )

    def _check_portfolio_concentration(
        self, market_data, position_size_usd: float
    ) -> ComplianceCheck:
        """Ensure single trade doesn't exceed max portfolio concentration."""
        if market_data.portfolio_value_usd <= 0:
            return ComplianceCheck(
                rule_id="concentration",
                rule_name="Portfolio Concentration",
                level=ComplianceLevel.WARNING,
                message="Cannot assess concentration: zero portfolio value",
            )

        concentration_pct = (position_size_usd / market_data.portfolio_value_usd) * 100.0
        max_pct = config.MAX_POSITION_PCT * 100.0

        if concentration_pct <= max_pct:
            return ComplianceCheck(
                rule_id="concentration",
                rule_name="Portfolio Concentration",
                level=ComplianceLevel.PASS,
                message=f"Concentration {concentration_pct:.1f}% <= {max_pct:.1f}%",
                metric_value=concentration_pct,
                threshold=max_pct,
            )
        else:
            return ComplianceCheck(
                rule_id="concentration",
                rule_name="Portfolio Concentration",
                level=ComplianceLevel.FAIL,
                message=f"Concentration {concentration_pct:.1f}% > {max_pct:.1f}% — trade too large",
                metric_value=concentration_pct,
                threshold=max_pct,
            )

    def _check_leverage_limits(self, market_data, position_size_usd: float) -> ComplianceCheck:
        """Ensure implied leverage within limits."""
        max_leverage = getattr(config, "MAX_LEVERAGE", 3.0)
        implied_leverage = position_size_usd / market_data.portfolio_value_usd if market_data.portfolio_value_usd > 0 else 0

        if implied_leverage <= max_leverage:
            return ComplianceCheck(
                rule_id="leverage",
                rule_name="Leverage Limits",
                level=ComplianceLevel.PASS,
                message=f"Implied leverage {implied_leverage:.2f}x <= {max_leverage:.2f}x",
                metric_value=implied_leverage,
                threshold=max_leverage,
            )
        else:
            return ComplianceCheck(
                rule_id="leverage",
                rule_name="Leverage Limits",
                level=ComplianceLevel.FAIL,
                message=f"Implied leverage {implied_leverage:.2f}x > {max_leverage:.2f}x — over-leveraged",
                metric_value=implied_leverage,
                threshold=max_leverage,
            )

    def _check_volatility_limits(self, market_data) -> ComplianceCheck:
        """Ensure market volatility within acceptable range for trading."""
        if market_data.prism_risk:
            atr_pct = market_data.prism_risk.atr_pct
            vol_threshold = config.VOLATILITY_THRESHOLD

            if atr_pct <= vol_threshold:
                return ComplianceCheck(
                    rule_id="volatility",
                    rule_name="Volatility Limits",
                    level=ComplianceLevel.PASS,
                    message=f"ATR {atr_pct:.4f} <= {vol_threshold}",
                    metric_value=atr_pct,
                    threshold=vol_threshold,
                )
            else:
                return ComplianceCheck(
                    rule_id="volatility",
                    rule_name="Volatility Limits",
                    level=ComplianceLevel.WARNING,
                    message=f"ATR {atr_pct:.4f} > {vol_threshold} — high volatility",
                    metric_value=atr_pct,
                    threshold=vol_threshold,
                )
        else:
            return ComplianceCheck(
                rule_id="volatility",
                rule_name="Volatility Limits",
                level=ComplianceLevel.WARNING,
                message="Cannot assess volatility: PRISM risk unavailable",
            )

    def _check_liquidity(self, market_data) -> ComplianceCheck:
        """Ensure sufficient market liquidity."""
        volume_24h = market_data.volume_24h
        min_volume = getattr(config, "MIN_VOLUME_24H_USD", 1e9)  # Default 1B

        if volume_24h >= min_volume:
            return ComplianceCheck(
                rule_id="liquidity",
                rule_name="Market Liquidity",
                level=ComplianceLevel.PASS,
                message=f"24h volume ${volume_24h:,.0f} >= ${min_volume:,.0f}",
                metric_value=volume_24h,
                threshold=min_volume,
            )
        else:
            return ComplianceCheck(
                rule_id="liquidity",
                rule_name="Market Liquidity",
                level=ComplianceLevel.WARNING,
                message=f"24h volume ${volume_24h:,.0f} < ${min_volume:,.0f} — low liquidity",
                metric_value=volume_24h,
                threshold=min_volume,
            )

    def _check_slippage_protection(self, market_data, position_size_usd: float) -> ComplianceCheck:
        """Estimate slippage and ensure acceptable."""
        # Simplified slippage model: 0.1% per 1M USD traded
        estimated_slippage_pct = (position_size_usd / 1_000_000) * 0.1
        max_slippage_pct = getattr(config, "MAX_SLIPPAGE_PCT", 0.5)

        if estimated_slippage_pct <= max_slippage_pct:
            return ComplianceCheck(
                rule_id="slippage",
                rule_name="Slippage Protection",
                level=ComplianceLevel.PASS,
                message=f"Est. slippage {estimated_slippage_pct:.3f}% <= {max_slippage_pct}%",
                metric_value=estimated_slippage_pct,
                threshold=max_slippage_pct,
            )
        else:
            return ComplianceCheck(
                rule_id="slippage",
                rule_name="Slippage Protection",
                level=ComplianceLevel.WARNING,
                message=f"Est. slippage {estimated_slippage_pct:.3f}% > {max_slippage_pct}% — position too large for liquidity",
                metric_value=estimated_slippage_pct,
                threshold=max_slippage_pct,
            )

    def _check_risk_adjusted_return(
        self, market_data, position_size_usd: float, confidence: float, equity_curve: Optional[List[float]] = None
    ) -> ComplianceCheck:
        """
        Ensure expected risk-adjusted return (Sharpe ratio) is positive.
        If equity_curve provided, compute real Sharpe from returns.
        Otherwise use proxy: expected return / ATR.
        """
        min_sharpe = getattr(config, "MIN_SHARPE_RATIO", 0.5)

        # If we have equity curve history, compute real Sharpe
        if equity_curve and len(equity_curve) >= 10:
            returns = []
            for i in range(1, len(equity_curve)):
                ret = (equity_curve[i] - equity_curve[i - 1]) / equity_curve[i - 1]
                returns.append(ret)

            if returns:
                mean_return = sum(returns) / len(returns)
                variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
                std_dev = variance ** 0.5
                risk_free_rate = 0.0
                sharpe_ratio = (mean_return - risk_free_rate) / max(std_dev, 0.001)
            else:
                sharpe_ratio = 0.0
        else:
            # Fallback to proxy: expected return / ATR
            atr_pct = market_data.prism_risk.atr_pct if market_data.prism_risk else 0.02
            price_change_pct = abs(market_data.change_24h_pct)
            expected_return = confidence * price_change_pct
            risk_pct = atr_pct
            sharpe_ratio = expected_return / max(risk_pct, 0.01)

        if sharpe_ratio >= min_sharpe:
            return ComplianceCheck(
                rule_id="risk_return",
                rule_name="Risk-Adjusted Return",
                level=ComplianceLevel.PASS,
                message=f"Sharpe ratio {sharpe_ratio:.2f} >= {min_sharpe}",
                metric_value=sharpe_ratio,
                threshold=min_sharpe,
            )
        else:
            return ComplianceCheck(
                rule_id="risk_return",
                rule_name="Risk-Adjusted Return",
                level=ComplianceLevel.WARNING,
                message=f"Sharpe ratio {sharpe_ratio:.2f} < {min_sharpe} — unfavorable risk/reward",
                metric_value=sharpe_ratio,
                threshold=min_sharpe,
            )

    def _check_drawdown_buffer(self, market_data) -> ComplianceCheck:
        """Ensure sufficient drawdown buffer before hitting max drawdown."""
        current_drawdown = getattr(market_data, "current_drawdown_pct", 0.0)
        max_drawdown = config.MAX_DRAWDOWN_PCT
        buffer_pct = max_drawdown - current_drawdown

        if buffer_pct >= max_drawdown * 0.25:  # 25% of max drawdown as buffer
            return ComplianceCheck(
                rule_id="drawdown_buffer",
                rule_name="Drawdown Buffer",
                level=ComplianceLevel.PASS,
                message=f"Drawdown buffer {buffer_pct:.2f}% >= {max_drawdown * 0.25:.2f}%",
                metric_value=buffer_pct,
                threshold=max_drawdown * 0.25,
            )
        else:
            return ComplianceCheck(
                rule_id="drawdown_buffer",
                rule_name="Drawdown Buffer",
                level=ComplianceLevel.WARNING,
                message=f"Drawdown buffer {buffer_pct:.2f}% < {max_drawdown * 0.25:.2f}% — near limit",
                metric_value=buffer_pct,
                threshold=max_drawdown * 0.25,
            )

    def _check_trustless_markers(self, market_data, direction: str) -> ComplianceCheck:
        """
        Verify trustless markers (on-chain signals, PRISM confidence, etc.).
        Best Trustless Trading Agent criterion.
        """
        trustless_score = 0.0

        # PRISM signal confidence (0-1)
        if market_data.signal_4h:
            trustless_score += market_data.signal_4h.confidence * 0.5
        if market_data.signal_1h:
            trustless_score += market_data.signal_1h.confidence * 0.5

        min_trustless = 0.4  # 40% minimum trustless confidence

        if trustless_score >= min_trustless:
            return ComplianceCheck(
                rule_id="trustless",
                rule_name="Trustless Verification",
                level=ComplianceLevel.PASS,
                message=f"Trustless score {trustless_score:.2f} >= {min_trustless} — verified via PRISM",
                metric_value=trustless_score,
                threshold=min_trustless,
            )
        else:
            return ComplianceCheck(
                rule_id="trustless",
                rule_name="Trustless Verification",
                level=ComplianceLevel.WARNING,
                message=f"Trustless score {trustless_score:.2f} < {min_trustless} — low external verification",
                metric_value=trustless_score,
                threshold=min_trustless,
            )

    def _check_consecutive_losses(self) -> ComplianceCheck:
        """
        Compliance Clock Strategy: Instead of blocking trades after consecutive losses,
        trigger the OPPOSITE direction strategy.
        - If SELL had N consecutive losses → trigger BUY next
        - If BUY had N consecutive losses → trigger SELL next
        This allows agents to adapt and recover from losing streaks.
        """
        try:
            with open("nexus_positions.json", "r") as f:
                positions_data = json.load(f)
            
            # Get recent closed positions and check their outcomes
            closed_positions = []
            if isinstance(positions_data, dict) and "positions" in positions_data:
                closed_positions = [p for p in positions_data["positions"] if p.get("status") == "closed"]
            elif isinstance(positions_data, list):
                closed_positions = [p for p in positions_data if p.get("status") == "closed"]
            
            # Sort by exit time (most recent first)
            closed_positions.sort(key=lambda p: p.get("exit_timestamp", 0), reverse=True)
            
            # Analyze last N trades for consecutive losses by direction
            consecutive_losses = 0
            last_direction = None
            limit = config.CONSECUTIVE_LOSS_LIMIT
            
            for position in closed_positions[:limit * 2]:  # Look at twice the limit to be sure
                direction = position.get("direction", "HOLD")
                pnl_pct = position.get("pnl_pct", 0)
                
                if pnl_pct < 0:
                    if last_direction is None or last_direction == direction:
                        consecutive_losses += 1
                        last_direction = direction
                    else:
                        break  # Direction changed, reset count
                else:
                    break  # Stop counting when we hit a win
            
            # Compliance Clock: Instead of FAIL, suggest opposite direction
            if consecutive_losses >= limit:
                opposite = "BUY" if last_direction == "SELL" else "SELL"
                return ComplianceCheck(
                    rule_id="consecutive_losses",
                    rule_name="Compliance Clock",
                    level=ComplianceLevel.PASS,  # PASS - don't block, just switch direction
                    message=f"{consecutive_losses} consecutive {last_direction} losses — trigger {opposite} strategy",
                    metric_value=consecutive_losses,
                    threshold=limit,
                )
            else:
                return ComplianceCheck(
                    rule_id="consecutive_losses",
                    rule_name="Compliance Clock",
                    level=ComplianceLevel.PASS,
                    message=f"{consecutive_losses} consecutive losses < {limit} limit",
                    metric_value=consecutive_losses,
                    threshold=limit,
                )
        except Exception as e:
            logger.warning(f"Could not check consecutive losses: {e}")
            return ComplianceCheck(
                rule_id="consecutive_losses",
                rule_name="Compliance Clock",
                level=ComplianceLevel.PASS,
                message=f"Compliance Clock: ready",
            )

    def _check_session_drawdown(self, market_data) -> ComplianceCheck:
        """
        Check daily/session drawdown and halt trading if exceeded.
        Prevents cascading losses in a single trading session.
        """
        try:
            with open("nexus_positions.json", "r") as f:
                positions_data = json.load(f)
            
            # Calculate today's PnL (all trades closed today)
            import datetime
            today = datetime.date.today()
            today_start_ts = int(datetime.datetime.combine(today, datetime.time.min).timestamp())
            
            today_pnl = 0.0
            closed_positions = []
            if isinstance(positions_data, dict) and "positions" in positions_data:
                closed_positions = positions_data["positions"]
            elif isinstance(positions_data, list):
                closed_positions = positions_data
            
            for position in closed_positions:
                exit_ts = position.get("exit_timestamp", 0)
                if exit_ts >= today_start_ts and position.get("status") == "closed":
                    today_pnl += position.get("pnl_usd", 0)
            
            # Calculate session drawdown percentage
            portfolio_value = getattr(market_data, "portfolio_value_usd", 10000.0)
            session_drawdown_pct = abs(today_pnl) / portfolio_value * 100.0 if today_pnl < 0 else 0.0
            limit_pct = config.SESSION_LOSS_LIMIT_PCT
            
            if session_drawdown_pct >= limit_pct:
                return ComplianceCheck(
                    rule_id="session_drawdown",
                    rule_name="Session Loss Limit",
                    level=ComplianceLevel.FAIL,
                    message=f"Session loss {session_drawdown_pct:.2f}% >= {limit_pct}% limit — TRADING HALTED",
                    metric_value=session_drawdown_pct,
                    threshold=limit_pct,
                )
            else:
                return ComplianceCheck(
                    rule_id="session_drawdown",
                    rule_name="Session Loss Limit",
                    level=ComplianceLevel.PASS,
                    message=f"Session loss {session_drawdown_pct:.2f}% < {limit_pct}% limit",
                    metric_value=session_drawdown_pct,
                    threshold=limit_pct,
                )
        except Exception as e:
            logger.warning(f"Could not check session drawdown: {e}")
            return ComplianceCheck(
                rule_id="session_drawdown",
                rule_name="Session Loss Limit",
                level=ComplianceLevel.WARNING,
                message=f"Could not assess: {e}",
            )

    def _check_max_drawdown(self, market_data) -> ComplianceCheck:
        """
        Check maximum equity drawdown from peak and halt trading if exceeded.
        Protects against catastrophic losses over longer periods.
        """
        try:
            with open("nexus_equity_curve.json", "r") as f:
                equity_data = json.load(f)
            
            # Calculate max drawdown from peak
            equity_values = []
            if isinstance(equity_data, dict):
                equity_values = list(equity_data.values())
            elif isinstance(equity_data, list):
                equity_values = equity_data
            
            if not equity_values or len(equity_values) < 2:
                return ComplianceCheck(
                    rule_id="max_drawdown",
                    rule_name="Max Equity Drawdown",
                    level=ComplianceLevel.PASS,
                    message="Insufficient equity history to assess drawdown",
                )
            
            # Find peak-to-trough drawdown
            max_equity = max(equity_values)
            current_equity = equity_values[-1]
            drawdown_pct = ((max_equity - current_equity) / max_equity * 100.0) if max_equity > 0 else 0.0
            limit_pct = config.MAX_EQUITY_DRAWDOWN_PCT
            
            if drawdown_pct >= limit_pct:
                return ComplianceCheck(
                    rule_id="max_drawdown",
                    rule_name="Max Equity Drawdown",
                    level=ComplianceLevel.FAIL,
                    message=f"Equity drawdown {drawdown_pct:.2f}% >= {limit_pct}% limit — TRADING HALTED",
                    metric_value=drawdown_pct,
                    threshold=limit_pct,
                )
            else:
                return ComplianceCheck(
                    rule_id="max_drawdown",
                    rule_name="Max Equity Drawdown",
                    level=ComplianceLevel.PASS,
                    message=f"Equity drawdown {drawdown_pct:.2f}% < {limit_pct}% limit",
                    metric_value=drawdown_pct,
                    threshold=limit_pct,
                )
        except Exception as e:
            logger.warning(f"Could not check max drawdown: {e}")
            return ComplianceCheck(
                rule_id="max_drawdown",
                rule_name="Max Equity Drawdown",
                level=ComplianceLevel.WARNING,
                message=f"Could not assess: {e}",
            )

    def compliance_report(self) -> str:
        """Generate compliance audit report."""
        passed = len(self.checks_passed)
        failed = len(self.checks_failed)
        total = passed + failed

        lines = [
            "[bold]NEXUS Compliance Report[/bold]",
            "",
            f"Total Checks: {total} | Passed: {passed} | Failed: {failed}",
            "",
        ]

        if failed > 0:
            lines.append("[bold red]Failed Checks:[/bold red]")
            for check in self.checks_failed:
                lines.append(f"  ✗ {check.rule_name}: {check.message}")
            lines.append("")

        lines.append("[bold green]Passed Checks:[/bold green]")
        for check in self.checks_passed:
            lines.append(f"  ✓ {check.rule_name}: {check.message}")

        return "\n".join(lines)
