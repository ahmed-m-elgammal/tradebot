from src.ui.dashboard_contract import (
    EngineState,
    GlobalOperatorState,
    MainView,
    Mode,
    Zone,
    fixed_zones,
    required_data_loops,
)


def test_required_data_loops_contract():
    loops = required_data_loops()

    assert len(loops) == 3
    assert {loop.name for loop in loops} == {
        "price_tick_stream",
        "portfolio_state_stream",
        "order_fill_event_stream",
    }

    cadence_map = {loop.name: loop.cadence for loop in loops}
    assert cadence_map["price_tick_stream"] == "100-700ms"
    assert cadence_map["portfolio_state_stream"] == "1s_or_bar_close"
    assert cadence_map["order_fill_event_stream"] == "event_driven"


def test_fixed_zone_visibility_contract():
    zones = fixed_zones()

    assert Zone.GLOBAL_STATUS_BAR in zones
    assert Zone.RISK_SENTINEL_PANEL in zones
    assert Zone.ALERTS_FEED in zones
    assert Zone.EXECUTION_STRIP in zones


def test_global_operator_state_defaults():
    state = GlobalOperatorState()

    assert state.mode == Mode.PAPER
    assert state.engine_state == EngineState.PAUSED
    assert state.kill_switch_active is False
    assert state.active_view == MainView.COMMAND
    assert state.session_start_equity == 0.0
    assert state.equity_peak == 0.0
