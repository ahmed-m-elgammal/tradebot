"""Execution model abstractions for backtesting."""

from dataclasses import dataclass
import numpy as np


@dataclass
class FillResult:
    fill_ratio: float
    fee_multiplier: float


class ExecutionModel:
    """Simple execution model supporting market/limit orders and partial fills."""

    def __init__(self, limit_fill_sensitivity: float = 4.0):
        self.limit_fill_sensitivity = limit_fill_sensitivity

    def simulate_fill(
        self,
        order_size: float,
        order_type: str = 'market',
        book_depth: float = 1.0,
        volatility: float = 0.0,
    ) -> FillResult:
        abs_size = abs(order_size)
        if abs_size <= 0:
            return FillResult(fill_ratio=0.0, fee_multiplier=1.0)

        if order_type == 'market':
            # Market always fills but incurs higher impact under higher vol.
            return FillResult(fill_ratio=1.0, fee_multiplier=1.0 + min(2.0, volatility * 20.0))

        # Limit: queue/depth and volatility reduce fill probability.
        depth_factor = min(1.0, book_depth / max(abs_size, 1e-9))
        vol_penalty = float(np.exp(-self.limit_fill_sensitivity * max(0.0, volatility)))
        fill_ratio = float(np.clip(depth_factor * vol_penalty, 0.0, 1.0))

        # Better fees when passive (limit), but partial fill risk.
        fee_multiplier = 0.7
        return FillResult(fill_ratio=fill_ratio, fee_multiplier=fee_multiplier)
