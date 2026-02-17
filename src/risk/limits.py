"""
Risk Limits

Hard and soft limit enforcement for position sizing and portfolio risk.
"""

from typing import Dict, Tuple, Optional, List
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class Position:
    """Represents an open position."""
    symbol: str
    quantity: float
    entry_price: float
    current_price: float
    stop_loss: Optional[float] = None
    
    @property
    def value(self) -> float:
        """Current position value."""
        return abs(self.quantity) * self.current_price
    
    @property
    def risk(self) -> float:
        """Amount at risk if stop loss hit."""
        if self.stop_loss is None:
            return self.value * 0.02  # Assume 2% risk if no stop
        return abs(self.quantity) * abs(self.entry_price - self.stop_loss)
    
    @property
    def pnl(self) -> float:
        """Current profit/loss."""
        if self.quantity > 0:  # Long
            return self.quantity * (self.current_price - self.entry_price)
        else:  # Short
            return abs(self.quantity) * (self.entry_price - self.current_price)


@dataclass
class Order:
    """Represents a proposed order."""
    symbol: str
    quantity: float
    price: float
    stop_loss: Optional[float] = None
    
    @property
    def value(self) -> float:
        """Order value."""
        return abs(self.quantity) * self.price
    
    @property
    def risk(self) -> float:
        """Amount at risk."""
        if self.stop_loss is None:
            return self.value * 0.02
        return abs(self.quantity) * abs(self.price - self.stop_loss)


class RiskLimits:
    """
    Risk limit enforcement system.
    
    Enforces:
    - Maximum position size per symbol
    - Maximum portfolio heat (total risk)
    - Maximum drawdown
    - Daily loss limits
    """
    
    def __init__(self, config: Dict):
        """
        Initialize risk limits.
        
        Args:
            config: Configuration dictionary with:
                - max_position_size: Max % of equity per position (e.g., 0.05 for 5%)
                - max_portfolio_heat: Max % of equity at risk (e.g., 0.10 for 10%)
                - max_drawdown: Max drawdown before halt (e.g., 0.15 for 15%)
                - daily_loss_limit: Max daily loss % (e.g., 0.03 for 3%)
        """
        self.max_position_size = config.get('max_position_size', 0.05)
        self.max_portfolio_heat = config.get('max_portfolio_heat', 0.10)
        self.max_drawdown = config.get('max_drawdown', 0.15)
        self.daily_loss_limit = config.get('daily_loss_limit', 0.03)
        
        # Track equity peak for drawdown calculation
        self.equity_peak = 0
        self.daily_start_equity = 0
        self.trading_halted = False
        
        logger.info(f"Risk Limits initialized:")
        logger.info(f"  Max position size: {self.max_position_size:.1%}")
        logger.info(f"  Max portfolio heat: {self.max_portfolio_heat:.1%}")
        logger.info(f"  Max drawdown: {self.max_drawdown:.1%}")
        logger.info(f"  Daily loss limit: {self.daily_loss_limit:.1%}")
    
    def check_order(self, 
                   order: Order,
                   current_equity: float,
                   open_positions: List[Position]) -> Tuple[bool, str]:
        """
        Check if order is within risk limits.
        
        Called BEFORE placing any order.
        
        Args:
            order: Proposed order
            current_equity: Current equity
            open_positions: List of currently open positions
            
        Returns:
            Tuple of (approved: bool, reason: str)
        """
        # Check if trading is halted
        if self.trading_halted:
            return False, "Trading halted due to risk violation"
        
        # Check position size limit
        position_value = order.value
        max_position_value = self.max_position_size * current_equity
        
        if position_value > max_position_value:
            return False, (f"Position size ${position_value:.2f} exceeds "
                          f"{self.max_position_size:.1%} limit (${max_position_value:.2f})")
        
        # Check portfolio heat (total risk)
        current_risk = sum(p.risk for p in open_positions)
        new_total_risk = current_risk + order.risk
        max_risk = self.max_portfolio_heat * current_equity
        
        if new_total_risk > max_risk:
            return False, (f"Portfolio heat ${new_total_risk:.2f} exceeds "
                          f"{self.max_portfolio_heat:.1%} limit (${max_risk:.2f})")
        
        # Check drawdown
        self.equity_peak = max(self.equity_peak, current_equity)
        drawdown = (self.equity_peak - current_equity) / self.equity_peak if self.equity_peak > 0 else 0
        
        if drawdown > self.max_drawdown:
            self.trading_halted = True
            return False, (f"Max drawdown {drawdown:.2%} exceeded "
                          f"(limit: {self.max_drawdown:.1%}) - HALTING ALL TRADING")
        
        # Check daily loss limit
        if self.daily_start_equity > 0:
            daily_pnl = current_equity - self.daily_start_equity
            daily_loss_pct = -daily_pnl / self.daily_start_equity if daily_pnl < 0 else 0
            
            if daily_loss_pct > self.daily_loss_limit:
                logger.warning(f"Daily loss {daily_loss_pct:.2%} exceeds limit "
                             f"{self.daily_loss_limit:.1%}")
                return False, f"Daily loss limit {self.daily_loss_limit:.1%} exceeded"
        
        return True, "Order approved"
    
    def update_equity(self, current_equity: float) -> None:
        """
        Update tracked equity values.
        
        Args:
            current_equity: Current equity value
        """
        self.equity_peak = max(self.equity_peak, current_equity)
        
        if self.daily_start_equity == 0:
            self.daily_start_equity = current_equity
    
    def reset_daily(self, current_equity: float) -> None:
        """
        Reset daily tracking (call at start of new trading day).
        
        Args:
            current_equity: Equity at start of day
        """
        self.daily_start_equity = current_equity
        logger.info(f"Daily reset: equity=${current_equity:.2f}")
    
    def get_current_metrics(self, current_equity: float, 
                           open_positions: List[Position]) -> Dict:
        """
        Get current risk metrics.
        
        Args:
            current_equity: Current equity
            open_positions: List of open positions
            
        Returns:
            Dictionary with current risk metrics
        """
        # Calculate metrics
        total_position_value = sum(p.value for p in open_positions)
        total_risk = sum(p.risk for p in open_positions)
        total_pnl = sum(p.pnl for p in open_positions)
        
        self.equity_peak = max(self.equity_peak, current_equity)
        drawdown = (self.equity_peak - current_equity) / self.equity_peak if self.equity_peak > 0 else 0
        
        daily_pnl = current_equity - self.daily_start_equity if self.daily_start_equity > 0 else 0
        daily_pnl_pct = daily_pnl / self.daily_start_equity if self.daily_start_equity > 0 else 0
        
        return {
            'equity': current_equity,
            'equity_peak': self.equity_peak,
            'drawdown': drawdown,
            'drawdown_pct': drawdown,
            'position_value': total_position_value,
            'position_pct': total_position_value / current_equity if current_equity > 0 else 0,
            'portfolio_heat': total_risk,
            'heat_pct': total_risk / current_equity if current_equity > 0 else 0,
            'unrealized_pnl': total_pnl,
            'daily_pnl': daily_pnl,
            'daily_pnl_pct': daily_pnl_pct,
            'num_positions': len(open_positions),
            'trading_halted': self.trading_halted
        }
    
    def resume_trading(self) -> None:
        """Resume trading after manual review."""
        self.trading_halted = False
        logger.warning("Trading resumed manually")
