"""
Position Sizing Module

Methods for calculating position sizes based on risk management principles.
"""

import numpy as np
from typing import Optional, Dict
import logging

logger = logging.getLogger(__name__)


class PositionSizer:
    """Position sizing calculator with multiple methods."""

    def __init__(self, default_method: str = 'fixed_fractional'):
        self.default_method = default_method

    def kelly_sizing(self,
                     win_rate: float,
                     avg_win: float,
                     avg_loss: float,
                     equity: float,
                     safety_factor: float = 0.5,
                     max_risk: float = 0.02) -> float:
        if win_rate <= 0 or win_rate >= 1:
            logger.warning(f"Invalid win_rate: {win_rate}, using fixed fractional")
            return self.fixed_fractional(equity, risk_per_trade=0.01)

        if avg_win <= 0 or avg_loss <= 0:
            logger.warning("Invalid avg_win/avg_loss, using fixed fractional")
            return self.fixed_fractional(equity, risk_per_trade=0.01)

        kelly = (win_rate / avg_loss) - ((1 - win_rate) / avg_win)
        kelly_fraction = max(0, kelly * safety_factor)
        kelly_fraction = min(kelly_fraction, max_risk)
        position_size = kelly_fraction * equity

        logger.debug(f"Kelly sizing: win_rate={win_rate:.2%}, kelly={kelly:.3f}, "
                     f"safe_kelly={kelly_fraction:.3f}, position=${position_size:.2f}")
        return position_size

    def fixed_fractional(self, equity: float, risk_per_trade: float = 0.01) -> float:
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
        if volatility <= 0:
            logger.warning(f"Invalid volatility: {volatility}, using fixed fractional")
            return self.fixed_fractional(equity, risk_per_trade=base_risk)

        vol_adjustment = target_volatility / volatility
        adjusted_risk = base_risk * vol_adjustment
        adjusted_risk = np.clip(adjusted_risk, base_risk * 0.5, base_risk * 2.0)

        position_size = equity * adjusted_risk
        logger.debug(f"Volatility-based: vol={volatility:.3f}, target={target_volatility:.3f}, "
                     f"adj_risk={adjusted_risk:.3%}, position=${position_size:.2f}")
        return position_size

    @staticmethod
    def drawdown_scale(current_drawdown: float) -> float:
        """Drawdown-aware risk scaling."""
        if current_drawdown < 0.05:
            return 1.0
        if current_drawdown < 0.10:
            return 0.6
        return 0.3

    def calculate_position(self,
                           signal: int,
                           equity: float,
                           method: Optional[str] = None,
                           current_drawdown: float = 0.0,
                           **kwargs) -> float:
        if signal == 0:
            return 0.0

        method = method or self.default_method

        if method == 'kelly':
            required_params = ['win_rate', 'avg_win', 'avg_loss']
            if not all(p in kwargs for p in required_params):
                logger.warning(f"Kelly method requires {required_params}, using fixed fractional")
                base_size = self.fixed_fractional(equity)
            else:
                base_size = self.kelly_sizing(equity=equity, **kwargs)
        elif method == 'volatility_based':
            if 'volatility' not in kwargs:
                logger.warning("Volatility method requires 'volatility', using fixed fractional")
                base_size = self.fixed_fractional(equity)
            else:
                base_size = self.volatility_based(equity=equity, **kwargs)
        else:
            base_size = self.fixed_fractional(equity=equity, **kwargs)

        scale = self.drawdown_scale(max(0.0, current_drawdown))
        return base_size * scale

    def calculate_shares(self,
                         position_size: float,
                         entry_price: float,
                         stop_loss: Optional[float] = None,
                         risk_amount: Optional[float] = None) -> Dict:
        if entry_price <= 0:
            raise ValueError(f"Invalid entry_price: {entry_price}")

        if stop_loss is not None and risk_amount is not None:
            risk_per_share = abs(entry_price - stop_loss)
            if risk_per_share > 0:
                shares = risk_amount / risk_per_share
            else:
                shares = position_size / entry_price
        else:
            shares = position_size / entry_price

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
