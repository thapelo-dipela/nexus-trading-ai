"""
Multi-Symbol Trading Module — Support for trading multiple cryptocurrencies
Extends single-symbol trading with per-coin position tracking and margin management
"""
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, field
import config

logger = logging.getLogger(__name__)


@dataclass
class CoinPosition:
    """Individual position for a cryptocurrency"""
    symbol: str
    direction: str  # "LONG" or "SHORT"
    entry_price: float
    quantity: float
    leverage: float = 1.0  # Margin ratio: 10x = 0.1 margin ratio
    timestamp: int = 0
    pnl_usd: float = 0.0
    trade_id: str = ""
    
    def current_pnl(self, current_price: float) -> float:
        """Calculate unrealized PnL"""
        if self.direction == "LONG":
            return (current_price - self.entry_price) * self.quantity
        else:  # SHORT
            return (self.entry_price - current_price) * self.quantity
    
    def current_pnl_pct(self, current_price: float) -> float:
        """Calculate unrealized PnL percentage"""
        if self.entry_price == 0:
            return 0.0
        unrealized = self.current_pnl(current_price)
        margin_invested = (self.entry_price * self.quantity) * self.leverage  # Use leverage
        if margin_invested == 0:
            return 0.0
        return (unrealized / margin_invested) * 100


class MultiSymbolPortfolio:
    """Manage multiple active positions across different coins"""
    
    def __init__(self, portfolio_file: str = "nexus_multi_positions.json"):
        self.portfolio_file = portfolio_file
        self.positions: Dict[str, CoinPosition] = {}
        self.load_positions()
    
    def load_positions(self) -> None:
        """Load open positions from file"""
        try:
            if Path(self.portfolio_file).exists():
                with open(self.portfolio_file, 'r') as f:
                    data = json.load(f)
                    for symbol, pos_data in data.get('positions', {}).items():
                        self.positions[symbol] = CoinPosition(**pos_data)
                    logger.info(f"✅ Loaded {len(self.positions)} open positions")
            else:
                logger.info(f"📄 {self.portfolio_file} not found - starting fresh")
        except Exception as e:
            logger.error(f"❌ Failed to load positions: {e}")
            self.positions = {}
    
    def save_positions(self) -> None:
        """Save positions to file"""
        try:
            data = {
                'positions': {
                    symbol: {
                        'symbol': pos.symbol,
                        'direction': pos.direction,
                        'entry_price': pos.entry_price,
                        'quantity': pos.quantity,
                        'leverage': pos.leverage,
                        'timestamp': pos.timestamp,
                        'pnl_usd': pos.pnl_usd,
                        'trade_id': pos.trade_id
                    }
                    for symbol, pos in self.positions.items()
                }
            }
            with open(self.portfolio_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"❌ Failed to save positions: {e}")
    
    def open_position(
        self, 
        symbol: str, 
        direction: str, 
        entry_price: float, 
        quantity: float,
        leverage: float = 1.0,
        trade_id: str = ""
    ) -> bool:
        """Open a new position for a symbol"""
        if symbol in self.positions:
            logger.warning(f"⚠️ Position already open for {symbol}")
            return False
        
        import time
        position = CoinPosition(
            symbol=symbol,
            direction=direction,
            entry_price=entry_price,
            quantity=quantity,
            leverage=leverage,
            timestamp=int(time.time()),
            trade_id=trade_id
        )
        
        self.positions[symbol] = position
        self.save_positions()
        logger.info(f"✅ Opened {direction} position: {quantity} {symbol} @ ${entry_price:.2f} (leverage: {leverage}x)")
        return True
    
    def close_position(self, symbol: str, exit_price: float) -> Optional[float]:
        """Close position for a symbol and return realized PnL"""
        if symbol not in self.positions:
            logger.warning(f"⚠️ No position open for {symbol}")
            return None
        
        position = self.positions[symbol]
        pnl = position.current_pnl(exit_price)
        
        # Store realized PnL
        position.pnl_usd = pnl
        
        del self.positions[symbol]
        self.save_positions()
        
        logger.info(f"✅ Closed {position.direction} position: {symbol} @ ${exit_price:.2f}, PnL: ${pnl:+.2f}")
        return pnl
    
    def get_position(self, symbol: str) -> Optional[CoinPosition]:
        """Get position for a symbol"""
        return self.positions.get(symbol)
    
    def has_position(self, symbol: str) -> bool:
        """Check if position exists for symbol"""
        return symbol in self.positions
    
    def get_all_positions(self) -> Dict[str, CoinPosition]:
        """Get all open positions"""
        return self.positions.copy()
    
    def get_total_exposure_usd(self, current_prices: Dict[str, float]) -> float:
        """Calculate total notional exposure across all positions"""
        total = 0.0
        for symbol, position in self.positions.items():
            if symbol in current_prices:
                price = current_prices[symbol]
                notional = (position.entry_price * position.quantity) / position.leverage
                total += notional
        return total
    
    def get_portfolio_pnl(self, current_prices: Dict[str, float]) -> float:
        """Calculate total unrealized PnL across portfolio"""
        total_pnl = 0.0
        for symbol, position in self.positions.items():
            if symbol in current_prices:
                pnl = position.current_pnl(current_prices[symbol])
                total_pnl += pnl
        return total_pnl
    
    def get_portfolio_metrics(self, current_prices: Dict[str, float]) -> Dict:
        """Get comprehensive portfolio metrics"""
        positions_data = []
        total_pnl = 0.0
        total_exposure = 0.0
        
        for symbol, position in self.positions.items():
            if symbol in current_prices:
                current_price = current_prices[symbol]
                pnl = position.current_pnl(current_price)
                pnl_pct = position.current_pnl_pct(current_price)
                notional_exposure = (position.entry_price * position.quantity) / position.leverage
                
                total_pnl += pnl
                total_exposure += notional_exposure
                
                positions_data.append({
                    'symbol': symbol,
                    'direction': position.direction,
                    'entry_price': position.entry_price,
                    'current_price': current_price,
                    'quantity': position.quantity,
                    'leverage': position.leverage,
                    'notional_exposure': notional_exposure,
                    'unrealized_pnl': pnl,
                    'unrealized_pnl_pct': pnl_pct
                })
        
        return {
            'positions': positions_data,
            'total_positions': len(self.positions),
            'total_exposure_usd': total_exposure,
            'total_unrealized_pnl': total_pnl,
            'active_symbols': list(self.positions.keys())
        }


def get_margin_ratio_for_symbol(symbol: str) -> float:
    """Get margin ratio (leverage multiplier) for a symbol"""
    return config.SYMBOL_MARGIN_RATIOS.get(symbol, config.DEFAULT_MARGIN_RATIO)


def get_leverage_for_symbol(symbol: str) -> float:
    """Get leverage (X multiplier) for a symbol"""
    margin_ratio = get_margin_ratio_for_symbol(symbol)
    return 1.0 / margin_ratio if margin_ratio > 0 else 1.0


def validate_position_size(
    symbol: str,
    quantity: float,
    entry_price: float,
    portfolio_value: float
) -> tuple[bool, str]:
    """Validate if position size is acceptable"""
    margin_ratio = get_margin_ratio_for_symbol(symbol)
    notional_value = quantity * entry_price
    margin_required = notional_value * margin_ratio
    
    # Check against portfolio
    margin_used_pct = (margin_required / portfolio_value) * 100
    
    if margin_used_pct > config.MAX_POSITION_PCT:
        return False, f"Position too large: {margin_used_pct:.1f}% > {config.MAX_POSITION_PCT}%"
    
    if margin_required < config.MIN_TRADE_SIZE_USD:
        return False, f"Position too small: ${margin_required:.2f} < ${config.MIN_TRADE_SIZE_USD}"
    
    if margin_required > config.MAX_TRADE_SIZE_USD:
        return False, f"Position too large: ${margin_required:.2f} > ${config.MAX_TRADE_SIZE_USD}"
    
    return True, "✅ Position size valid"


# Example usage in main trading loop:
# portfolio = MultiSymbolPortfolio()
# 
# # Open positions across multiple coins
# portfolio.open_position("ETH", "LONG", 2500.0, 1.0, leverage=6.67)
# portfolio.open_position("SOL", "LONG", 150.0, 10.0, leverage=5.0)
#
# # Get metrics
# prices = {"ETH": 2520.0, "SOL": 155.0}
# metrics = portfolio.get_portfolio_metrics(prices)
# print(f"Total PnL: ${metrics['total_unrealized_pnl']:.2f}")
