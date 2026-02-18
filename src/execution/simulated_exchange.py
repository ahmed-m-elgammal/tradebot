"""Simulated exchange for paper-trading with depth-aware fills."""

import random
import time
from typing import Dict

from src.utils.logger import get_logger
from src.execution.order_manager import PaperOrder

logger = get_logger(__name__)


class SimulatedExchange:
    """Applies synthetic fill logic and tracks latency histograms."""

    def __init__(self, seed: int = 42):
        self.rng = random.Random(seed)
        self.fill_latency_ms: list[float] = []
        self.fill_events = 0

    def _record_latency(self, started: float) -> None:
        latency = (time.perf_counter() - started) * 1000.0
        self.fill_latency_ms.append(latency)

    def _latency_histogram(self) -> Dict[str, int]:
        bins = {'lt1ms': 0, '1to5ms': 0, '5to20ms': 0, '20ms_plus': 0}
        for lat in self.fill_latency_ms:
            if lat < 1:
                bins['lt1ms'] += 1
            elif lat < 5:
                bins['1to5ms'] += 1
            elif lat < 20:
                bins['5to20ms'] += 1
            else:
                bins['20ms_plus'] += 1
        return bins

    def execute(self, order: PaperOrder, market_price: float, book_depth: float = 1.0, volatility: float = 0.0) -> Dict:
        """Execute order and return fill payload with possible partial fill."""
        started = time.perf_counter()

        if order.order_type == 'market':
            fill_ratio = 1.0
            slippage = min(0.01, max(0.0, volatility * 0.5))
            fill_price = market_price * (1 + slippage if order.side == 'buy' else 1 - slippage)
        else:
            if order.limit_price is None:
                fill_ratio = 0.0
                fill_price = market_price
            else:
                price_ok = market_price <= order.limit_price if order.side == 'buy' else market_price >= order.limit_price
                if not price_ok:
                    fill_ratio = 0.0
                else:
                    depth_factor = min(1.0, max(0.0, book_depth / max(order.quantity, 1e-9)))
                    vol_penalty = max(0.05, 1.0 - volatility * 5.0)
                    jitter = self.rng.uniform(0.85, 1.0)
                    fill_ratio = max(0.0, min(1.0, depth_factor * vol_penalty * jitter))
                fill_price = order.limit_price

        filled_qty = order.quantity * fill_ratio
        self.fill_events += 1
        self._record_latency(started)

        payload = {
            'order_id': order.id,
            'filled_qty': filled_qty,
            'fill_price': fill_price,
            'fill_ratio': fill_ratio,
            'status': 'filled' if fill_ratio >= 0.999 else ('partially_filled' if fill_ratio > 0 else 'unfilled'),
        }
        logger.info('Simulated fill', extra={**payload, 'order_type': order.order_type, 'symbol': order.symbol})
        return payload

    def get_metrics(self) -> Dict:
        return {
            'fill_events': self.fill_events,
            'latency_histogram': self._latency_histogram(),
            'avg_latency_ms': (sum(self.fill_latency_ms) / len(self.fill_latency_ms)) if self.fill_latency_ms else 0.0,
        }
