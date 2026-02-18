"""Position tracking and PnL accounting for paper trading."""

from dataclasses import dataclass
from typing import Dict

from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class PositionSnapshot:
    symbol: str
    quantity: float
    avg_entry_price: float
    last_price: float

    @property
    def market_value(self) -> float:
        return self.quantity * self.last_price


class PositionTracker:
    def __init__(self):
        self.positions: Dict[str, PositionSnapshot] = {}
        self.realized_pnl: float = 0.0

    def apply_fill(self, symbol: str, side: str, quantity: float, price: float) -> None:
        pos = self.positions.get(symbol, PositionSnapshot(symbol=symbol, quantity=0.0, avg_entry_price=0.0, last_price=price))
        signed_qty = quantity if side == 'buy' else -quantity

        if pos.quantity == 0 or (pos.quantity > 0 and signed_qty > 0) or (pos.quantity < 0 and signed_qty < 0):
            new_qty = pos.quantity + signed_qty
            if new_qty != 0:
                pos.avg_entry_price = ((abs(pos.quantity) * pos.avg_entry_price) + (abs(signed_qty) * price)) / abs(new_qty)
            pos.quantity = new_qty
        else:
            # reducing or flipping position
            close_qty = min(abs(pos.quantity), abs(signed_qty))
            if pos.quantity > 0:
                self.realized_pnl += close_qty * (price - pos.avg_entry_price)
            else:
                self.realized_pnl += close_qty * (pos.avg_entry_price - price)

            residual = abs(signed_qty) - close_qty
            if residual > 0:
                pos.quantity = residual if signed_qty > 0 else -residual
                pos.avg_entry_price = price
            else:
                pos.quantity = pos.quantity + signed_qty
                if pos.quantity == 0:
                    pos.avg_entry_price = 0.0

        pos.last_price = price
        self.positions[symbol] = pos
        logger.info('Position updated', extra={
            'symbol': symbol,
            'quantity': pos.quantity,
            'avg_entry_price': pos.avg_entry_price,
            'realized_pnl': self.realized_pnl,
        })

    def mark_to_market(self, prices: Dict[str, float]) -> float:
        unrealized = 0.0
        for sym, pos in self.positions.items():
            if sym in prices:
                pos.last_price = prices[sym]
            unrealized += pos.quantity * (pos.last_price - pos.avg_entry_price)
        return unrealized

    def exposure_by_symbol(self) -> Dict[str, float]:
        return {sym: abs(pos.market_value) for sym, pos in self.positions.items()}

    def snapshot(self, prices: Dict[str, float]) -> Dict:
        unrealized = self.mark_to_market(prices)
        return {
            'realized_pnl': self.realized_pnl,
            'unrealized_pnl': unrealized,
            'positions': {sym: {'quantity': p.quantity, 'avg_entry_price': p.avg_entry_price, 'last_price': p.last_price}
                          for sym, p in self.positions.items()},
            'symbol_exposure': self.exposure_by_symbol(),
        }
