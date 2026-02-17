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
        return abs(self.quantity) * self.current_price

    @property
    def risk(self) -> float:
        if self.stop_loss is None:
            return self.value * 0.02
        return abs(self.quantity) * abs(self.entry_price - self.stop_loss)

    @property
    def pnl(self) -> float:
        if self.quantity > 0:
            return self.quantity * (self.current_price - self.entry_price)
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
        return abs(self.quantity) * self.price

    @property
    def risk(self) -> float:
        if self.stop_loss is None:
            return self.value * 0.02
        return abs(self.quantity) * abs(self.price - self.stop_loss)


class RiskLimits:
    """Risk limit enforcement system."""

    def __init__(self, config: Dict):
        self.max_position_size = config.get('max_position_size', 0.05)
        self.max_portfolio_heat = config.get('max_portfolio_heat', 0.10)
        self.max_drawdown = config.get('max_drawdown', 0.15)
        self.daily_loss_limit = config.get('daily_loss_limit', 0.03)

        # New concentration/correlation guards
        self.max_symbol_exposure = config.get('max_symbol_exposure', self.max_position_size)
        self.max_correlated_exposure = config.get('max_correlated_exposure', 0.20)
        self.correlation_threshold = config.get('correlation_threshold', 0.8)

        self.equity_peak = 0
        self.daily_start_equity = 0
        self.trading_halted = False

    def _drawdown(self, current_equity: float) -> float:
        self.equity_peak = max(self.equity_peak, current_equity)
        return (self.equity_peak - current_equity) / self.equity_peak if self.equity_peak > 0 else 0

    def _symbol_exposure(self, symbol: str, open_positions: List[Position]) -> float:
        return sum(p.value for p in open_positions if p.symbol == symbol)

    def _correlated_exposure(self,
                             order: Order,
                             open_positions: List[Position],
                             correlation_map: Optional[Dict[str, Dict[str, float]]] = None) -> float:
        if not correlation_map:
            return 0.0

        order_corrs = correlation_map.get(order.symbol, {})
        correlated = 0.0
        for pos in open_positions:
            corr = abs(order_corrs.get(pos.symbol, 0.0))
            if corr >= self.correlation_threshold:
                correlated += pos.value
        return correlated

    def check_order(self,
                    order: Order,
                    current_equity: float,
                    open_positions: List[Position],
                    correlation_map: Optional[Dict[str, Dict[str, float]]] = None) -> Tuple[bool, str]:
        if self.trading_halted:
            return False, "Trading halted due to risk violation"

        position_value = order.value
        max_position_value = self.max_position_size * current_equity
        if position_value > max_position_value:
            return False, (f"Position size ${position_value:.2f} exceeds "
                           f"{self.max_position_size:.1%} limit (${max_position_value:.2f})")

        existing_symbol_exposure = self._symbol_exposure(order.symbol, open_positions)
        symbol_exposure_new = existing_symbol_exposure + position_value
        max_symbol_value = self.max_symbol_exposure * current_equity
        if symbol_exposure_new > max_symbol_value:
            return False, (f"Symbol exposure ${symbol_exposure_new:.2f} exceeds "
                           f"{self.max_symbol_exposure:.1%} limit (${max_symbol_value:.2f})")

        current_risk = sum(p.risk for p in open_positions)
        new_total_risk = current_risk + order.risk
        max_risk = self.max_portfolio_heat * current_equity
        if new_total_risk > max_risk:
            return False, (f"Portfolio heat ${new_total_risk:.2f} exceeds "
                           f"{self.max_portfolio_heat:.1%} limit (${max_risk:.2f})")

        correlated_exposure = self._correlated_exposure(order, open_positions, correlation_map)
        correlated_exposure_new = correlated_exposure + position_value
        max_corr_value = self.max_correlated_exposure * current_equity
        if correlated_exposure_new > max_corr_value:
            return False, (f"Correlated exposure ${correlated_exposure_new:.2f} exceeds "
                           f"{self.max_correlated_exposure:.1%} limit (${max_corr_value:.2f})")

        drawdown = self._drawdown(current_equity)
        if drawdown > self.max_drawdown:
            self.trading_halted = True
            return False, (f"Max drawdown {drawdown:.2%} exceeded "
                           f"(limit: {self.max_drawdown:.1%}) - HALTING ALL TRADING")

        if self.daily_start_equity > 0:
            daily_pnl = current_equity - self.daily_start_equity
            daily_loss_pct = -daily_pnl / self.daily_start_equity if daily_pnl < 0 else 0
            if daily_loss_pct > self.daily_loss_limit:
                logger.warning(f"Daily loss {daily_loss_pct:.2%} exceeds limit {self.daily_loss_limit:.1%}")
                return False, f"Daily loss limit {self.daily_loss_limit:.1%} exceeded"

        return True, "Order approved"

    def update_equity(self, current_equity: float) -> None:
        self.equity_peak = max(self.equity_peak, current_equity)
        if self.daily_start_equity == 0:
            self.daily_start_equity = current_equity

    def reset_daily(self, current_equity: float) -> None:
        self.daily_start_equity = current_equity
        logger.info(f"Daily reset: equity=${current_equity:.2f}")

    def get_current_metrics(self, current_equity: float, open_positions: List[Position]) -> Dict:
        total_position_value = sum(p.value for p in open_positions)
        total_risk = sum(p.risk for p in open_positions)
        total_pnl = sum(p.pnl for p in open_positions)

        drawdown = self._drawdown(current_equity)
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
        self.trading_halted = False
        logger.warning("Trading resumed manually")
