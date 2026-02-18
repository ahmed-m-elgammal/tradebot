"""UI contract primitives for the operator-grade trading dashboard.

This module defines static structure and state contracts for building a
multi-pane live trading UI. The contract is intentionally framework-agnostic
so it can back a web, desktop, or terminal dashboard implementation.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List


class Mode(str, Enum):
    """System operating mode."""

    LIVE = "LIVE"
    PAPER = "PAPER"
    BACKTEST = "BACKTEST"


class EngineState(str, Enum):
    """Strategy engine lifecycle state."""

    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    HALTED = "HALTED"


class Zone(str, Enum):
    """Top-level persistent layout zones."""

    GLOBAL_STATUS_BAR = "global_status_bar"
    NAVIGATION_RAIL = "navigation_rail"
    MAIN_CONTENT = "main_content"
    RISK_SENTINEL_PANEL = "risk_sentinel_panel"
    EXECUTION_STRIP = "execution_strip"
    ALERTS_FEED = "alerts_feed"


class MainView(str, Enum):
    """Main content destinations."""

    COMMAND = "command"
    POSITIONS = "positions"
    ORDERS = "orders"
    STRATEGIES = "strategies"
    BACKTEST = "backtest"
    RISK = "risk"
    SYSTEM = "system"


@dataclass(frozen=True)
class DataLoop:
    """A live update loop contract."""

    name: str
    cadence: str
    update_targets: List[str]


@dataclass
class GlobalOperatorState:
    """Session-wide state that survives view changes."""

    mode: Mode = Mode.PAPER
    engine_state: EngineState = EngineState.PAUSED
    kill_switch_active: bool = False
    active_view: MainView = MainView.COMMAND
    strategy_enabled: Dict[str, bool] = field(default_factory=dict)
    risk_limits: Dict[str, float] = field(default_factory=dict)
    session_start_equity: float = 0.0
    equity_peak: float = 0.0


@dataclass
class LiveMarketState:
    """Tick/event-driven mutable live state."""

    prices: Dict[str, float] = field(default_factory=dict)
    positions: Dict[str, Dict] = field(default_factory=dict)
    order_book: Dict[str, Dict] = field(default_factory=dict)
    risk_metrics: Dict[str, float] = field(default_factory=dict)


@dataclass
class AuditState:
    """Append-only historical session logs."""

    order_history: List[Dict] = field(default_factory=list)
    alert_history: List[Dict] = field(default_factory=list)
    parameter_changes: List[Dict] = field(default_factory=list)
    risk_breaches: List[Dict] = field(default_factory=list)
    fill_tape: List[Dict] = field(default_factory=list)


def required_data_loops() -> List[DataLoop]:
    """Return the three mandatory live UI update loops."""

    return [
        DataLoop(
            name="price_tick_stream",
            cadence="100-700ms",
            update_targets=[
                "position_pnl",
                "unrealized_totals",
                "limit_trigger_distance",
                "signal_indicators",
                "exposure_gauges",
            ],
        ),
        DataLoop(
            name="portfolio_state_stream",
            cadence="1s_or_bar_close",
            update_targets=[
                "risk_metrics",
                "equity_snapshot",
                "command_kpis",
                "equity_curve",
                "risk_sentinel",
            ],
        ),
        DataLoop(
            name="order_fill_event_stream",
            cadence="event_driven",
            update_targets=[
                "execution_strip",
                "orders_view",
                "positions_view",
                "alerts_feed",
                "session_pnl",
            ],
        ),
    ]


def fixed_zones() -> List[Zone]:
    """Return zones that must remain visible across all main views."""

    return [
        Zone.GLOBAL_STATUS_BAR,
        Zone.RISK_SENTINEL_PANEL,
        Zone.ALERTS_FEED,
        Zone.EXECUTION_STRIP,
    ]
