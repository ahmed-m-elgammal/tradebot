"""
Position Sizing Module

Methods for calculating position sizes based on risk management principles.
"""

import numpy as np
from typing import Optional, Dict
import logging

logger = logging.getLogger(__name__)


class PositionSizer:
    """
    Position sizing calculator with multiple methods.
    
    Methods:
    - Kelly Criterion: Optimal sizing based on win rate and payoff ratio
    - Fixed Fractional: Simple percentage of equity per trade
    - Volatility-based: Adjust size based on recent volatility
    """
    
    def __init__(self, default_method: str = 'fixed_fractional'):
        """
        Initialize position sizer.
        
        Args:
            default_method: Default sizing method to use
        """
        self.default_method = default_method
        
    def kelly_sizing(self, 
                    win_rate: float,
                    avg_win: float,
                    avg_loss: float,
                    equity: float,
                    safety_factor: float = 0.5,
                    max_risk: float = 0.02) -> float:
        """
        Kelly Criterion position sizing.
        
        Formula: f = (p/a) - ((1-p)/b)
        Where:
        - f = fraction of equity to risk
        - p = win rate
        - a = average loss (as positive number)
        - b = average win
        
        We apply a safety factor (typically 0.5) to reduce risk of ruin.
        
        Args:
            win_rate: Historical win rate (0-1, e.g., 0.55 for 55%)
            avg_win: Average winning trade return (e.g., 0.02 for 2%)
            avg_loss: Average losing trade return (as positive, e.g., 0.015 for 1.5%)
            equity: Current portfolio equity
            safety_factor: Multiplier to reduce Kelly fraction (0-1)
            max_risk: Maximum allowed risk per trade
            
        Returns:
            Position size in dollars
        """
        if win_rate <= 0 or win_rate >= 1:
            logger.warning(f"Invalid win_rate: {win_rate}, using fixed fractional")
            return self.fixed_fractional(equity, risk_per_trade=0.01)
            
        if avg_win <= 0 or avg_loss <= 0:
            logger.warning(f"Invalid avg_win/avg_loss, using fixed fractional")
            return self.fixed_fractional(equity, risk_per_trade=0.01)
        
        # Calculate Kelly fraction
        kelly = (win_rate / avg_loss) - ((1 - win_rate) / avg_win)
        
        # Apply safety factor
        kelly_fraction = max(0, kelly * safety_factor)
        
        # Cap at max risk
        kelly_fraction = min(kelly_fraction, max_risk)
        
        # Calculate position size
        position_size = kelly_fraction * equity
        
        logger.debug(f"Kelly sizing: win_rate={win_rate:.2%}, kelly={kelly:.3f}, "
                    f"safe_kelly={kelly_fraction:.3f}, position=${position_size:.2f}")
        
        return position_size
    
    def fixed_fractional(self, 
                        equity: float,
                        risk_per_trade: float = 0.01) -> float:
        """
        Simple fixed fractional position sizing.
        
        Risk a fixed percentage of equity on each trade.
        
        Args:
            equity: Current portfolio equity
            risk_per_trade: Fraction of equity to risk (e.g., 0.01 for 1%)
            
        Returns:
            Position size in dollars
        """
        if risk_per_trade <= 0 or risk_per_trade > 0.1:
            logger.warning(f"risk_per_trade {risk_per_trade} out of range [0, 0.1], using 0.01")
            risk_per_trade = 0.01
            
        position_size = equity * risk_per_trade
        
        logger.debug(f"Fixed fractional: equity=${equity:.2f}, risk={risk_per_trade:.2%}, "
                    f"position=${position_size:.2f}")
        
        return position_size
    
    def volatility_based(self,
                        equity: float,
                        volatility: float,
                        target_volatility: float = 0.02,
                        base_risk: float = 0.01) -> float:
        """
        Adjust position size based on volatility.
        
        Increase position size when volatility is low,
        decrease when volatility is high.
        
        Args:
            equity: Current portfolio equity
            volatility: Recent volatility (std dev of returns)
            target_volatility: Target volatility level
            base_risk: Base risk percentage
            
        Returns:
            Position size in dollars
        """
        if volatility <= 0:
            logger.warning(f"Invalid volatility: {volatility}, using fixed fractional")
            return self.fixed_fractional(equity, risk_per_trade=base_risk)
            
        # Adjust risk based on volatility
        # If volatility is high, reduce position; if low, increase
        vol_adjustment = target_volatility / volatility
        adjusted_risk = base_risk * vol_adjustment
        
        # Cap adjustment between 0.5x and 2x base risk
        adjusted_risk = np.clip(adjusted_risk, base_risk * 0.5, base_risk * 2.0)
        
        position_size = equity * adjusted_risk
        
        logger.debug(f"Volatility-based: vol={volatility:.3f}, target={target_volatility:.3f}, "
                    f"adj_risk={adjusted_risk:.3%}, position=${position_size:.2f}")
        
        return position_size
    
    def calculate_position(self,
                          signal: int,
                          equity: float,
                          method: Optional[str] = None,
                          **kwargs) -> float:
        """
        Calculate position size for a given signal.
        
        Args:
            signal: Trading signal (-1, 0, 1)
            equity: Current equity
            method: Sizing method ('kelly', 'fixed_fractional', 'volatility_based')
            **kwargs: Method-specific parameters
            
        Returns:
            Position size in dollars (0 if signal is 0)
        """
        if signal == 0:
            return 0.0
            
        method = method or self.default_method
        
        if method == 'kelly':
            required_params = ['win_rate', 'avg_win', 'avg_loss']
            if not all(p in kwargs for p in required_params):
                logger.warning(f"Kelly method requires {required_params}, using fixed fractional")
                return self.fixed_fractional(equity)
            return self.kelly_sizing(equity=equity, **kwargs)
            
        elif method == 'volatility_based':
            if 'volatility' not in kwargs:
                logger.warning("Volatility method requires 'volatility', using fixed fractional")
                return self.fixed_fractional(equity)
            return self.volatility_based(equity=equity, **kwargs)
            
        else:  # fixed_fractional (default)
            return self.fixed_fractional(equity=equity, **kwargs)
    
    def calculate_shares(self,
                        position_size: float,
                        entry_price: float,
                        stop_loss: Optional[float] = None,
                        risk_amount: Optional[float] = None) -> Dict:
        """
        Convert position size in dollars to number of shares.
        
        If stop_loss is provided, adjusts shares to risk exactly risk_amount.
        
        Args:
            position_size: Position size in dollars
            entry_price: Entry price per share
            stop_loss: Stop loss price (optional)
            risk_amount: Amount willing to risk in dollars (optional)
            
        Returns:
            Dictionary with shares, position_value, and risk info
        """
        if entry_price <= 0:
            raise ValueError(f"Invalid entry_price: {entry_price}")
            
        if stop_loss is not None and risk_amount is not None:
            # Calculate shares based on risk
            risk_per_share = abs(entry_price - stop_loss)
            if risk_per_share > 0:
                shares = risk_amount / risk_per_share
            else:
                shares = position_size / entry_price
        else:
            # Simple calculation based on position size
            shares = position_size / entry_price
            
        # Round down to nearest whole share
        shares = int(shares)
        
        actual_position_value = shares * entry_price
        
        result = {
            'shares': shares,
            'entry_price': entry_price,
            'position_value': actual_position_value,
        }
        
        if stop_loss is not None:
            result['stop_loss'] = stop_loss
            result['risk_per_share'] = abs(entry_price - stop_loss)
            result['total_risk'] = shares * result['risk_per_share']
            
        return result
