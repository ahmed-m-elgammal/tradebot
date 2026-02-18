"""Paper-trading order lifecycle manager."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional, List
from datetime import datetime, timezone
import uuid

from src.utils.logger import get_logger

logger = get_logger(__name__)


class OrderState(str, Enum):
    CREATED = 'created'
    SUBMITTED = 'submitted'
    PARTIALLY_FILLED = 'partially_filled'
    FILLED = 'filled'
    CANCELED = 'canceled'
    REJECTED = 'rejected'


class RejectReason(str, Enum):
    KILL_SWITCH = 'kill_switch_enabled'
    MAX_LOSS_CIRCUIT_BREAKER = 'max_loss_circuit_breaker'
    RISK_CHECK_FAILED = 'risk_check_failed'
    INVALID_ORDER = 'invalid_order'
    EXCHANGE_REJECTED = 'exchange_rejected'


@dataclass
class PaperOrder:
    symbol: str
    side: str  # buy/sell
    quantity: float
    order_type: str = 'market'  # market/limit
    limit_price: Optional[float] = None
    sector: Optional[str] = None
    cluster: Optional[str] = None
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: OrderState = OrderState.CREATED
    filled_quantity: float = 0.0
    avg_fill_price: float = 0.0
    reject_reason: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class OrderManager:
    """Tracks order lifecycle and enforces pre-submission controls."""

    def __init__(self, risk_limits=None, max_daily_loss_abs: float = 0.0):
        self.risk_limits = risk_limits
        self.max_daily_loss_abs = max_daily_loss_abs
        self.kill_switch = False

        self.orders: Dict[str, PaperOrder] = {}
        self.rejection_counters: Dict[str, int] = {reason.value: 0 for reason in RejectReason}
        self.failure_counters: Dict[str, int] = {'exchange_failures': 0, 'unknown_failures': 0}
        self.state_counts: Dict[str, int] = {state.value: 0 for state in OrderState}
        self._daily_realized_pnl = 0.0

    def set_kill_switch(self, enabled: bool) -> None:
        self.kill_switch = enabled

    def update_daily_realized_pnl(self, realized_pnl: float) -> None:
        self._daily_realized_pnl = realized_pnl

    def _validate_order(self, order: PaperOrder) -> Optional[RejectReason]:
        if order.quantity <= 0:
            return RejectReason.INVALID_ORDER
        if order.order_type == 'limit' and (order.limit_price is None or order.limit_price <= 0):
            return RejectReason.INVALID_ORDER
        if order.side not in ('buy', 'sell'):
            return RejectReason.INVALID_ORDER
        return None

    def _mark_rejected(self, order: PaperOrder, reason: RejectReason) -> PaperOrder:
        order.status = OrderState.REJECTED
        order.reject_reason = reason.value
        order.updated_at = datetime.now(timezone.utc)
        self.orders[order.id] = order
        self.rejection_counters[reason.value] += 1
        self.state_counts[OrderState.REJECTED.value] += 1
        logger.warning('Order rejected', extra={
            'order_id': order.id,
            'symbol': order.symbol,
            'reason': reason.value,
            'status': order.status.value,
        })
        return order

    def submit_order(self, order: PaperOrder, current_equity: Optional[float] = None, open_positions: Optional[List] = None):
        open_positions = open_positions or []

        if self.kill_switch:
            return self._mark_rejected(order, RejectReason.KILL_SWITCH)

        if self.max_daily_loss_abs > 0 and self._daily_realized_pnl <= -abs(self.max_daily_loss_abs):
            return self._mark_rejected(order, RejectReason.MAX_LOSS_CIRCUIT_BREAKER)

        invalid_reason = self._validate_order(order)
        if invalid_reason is not None:
            return self._mark_rejected(order, invalid_reason)

        if self.risk_limits is not None and current_equity is not None:
            from src.risk.limits import Order as RiskOrder
            risk_order = RiskOrder(
                symbol=order.symbol,
                quantity=order.quantity if order.side == 'buy' else -order.quantity,
                price=order.limit_price if order.limit_price else 1.0,
                sector=order.sector,
                cluster=order.cluster,
            )
            approved, reason = self.risk_limits.check_order(risk_order, current_equity=current_equity, open_positions=open_positions)
            if not approved:
                logger.warning('Risk check rejected order', extra={'order_id': order.id, 'reason': reason})
                return self._mark_rejected(order, RejectReason.RISK_CHECK_FAILED)

        order.status = OrderState.SUBMITTED
        order.updated_at = datetime.now(timezone.utc)
        self.orders[order.id] = order
        self.state_counts[OrderState.SUBMITTED.value] += 1
        logger.info('Order submitted', extra={'order_id': order.id, 'symbol': order.symbol, 'status': order.status.value})
        return order

    def apply_fill(self, order_id: str, fill_qty: float, fill_price: float) -> PaperOrder:
        order = self.orders[order_id]
        fill_qty = max(0.0, min(fill_qty, order.quantity - order.filled_quantity))

        new_total_qty = order.filled_quantity + fill_qty
        if new_total_qty > 0:
            order.avg_fill_price = (
                (order.avg_fill_price * order.filled_quantity) + (fill_price * fill_qty)
            ) / new_total_qty
        order.filled_quantity = new_total_qty

        if order.filled_quantity == 0:
            order.status = OrderState.SUBMITTED
        elif order.filled_quantity < order.quantity:
            order.status = OrderState.PARTIALLY_FILLED
            self.state_counts[OrderState.PARTIALLY_FILLED.value] += 1
        else:
            order.status = OrderState.FILLED
            self.state_counts[OrderState.FILLED.value] += 1

        order.updated_at = datetime.now(timezone.utc)
        logger.info('Order fill update', extra={
            'order_id': order.id,
            'symbol': order.symbol,
            'filled_quantity': order.filled_quantity,
            'avg_fill_price': order.avg_fill_price,
            'status': order.status.value,
        })
        return order

    def cancel_order(self, order_id: str) -> PaperOrder:
        order = self.orders[order_id]
        order.status = OrderState.CANCELED
        order.updated_at = datetime.now(timezone.utc)
        self.state_counts[OrderState.CANCELED.value] += 1
        logger.info('Order canceled', extra={'order_id': order.id, 'symbol': order.symbol, 'status': order.status.value})
        return order

    def get_telemetry(self) -> Dict:
        return {
            'rejections': dict(self.rejection_counters),
            'failures': dict(self.failure_counters),
            'state_counts': dict(self.state_counts),
            'orders_total': len(self.orders),
        }
