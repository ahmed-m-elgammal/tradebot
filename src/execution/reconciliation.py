"""Reconciliation checks between expected and actual paper-trading state."""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List

from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ReconciliationResult:
    timestamp: datetime
    mismatches: List[str]
    drift_abs: float
    missing_updates: int

    @property
    def ok(self) -> bool:
        return len(self.mismatches) == 0 and self.drift_abs == 0 and self.missing_updates == 0


class ReconciliationEngine:
    """Periodic reconciliation and daily summary report generation."""

    def __init__(self, drift_tolerance: float = 1e-6):
        self.drift_tolerance = drift_tolerance
        self.daily_results: List[ReconciliationResult] = []

    def reconcile(self, expected: Dict, actual: Dict) -> ReconciliationResult:
        mismatches = []

        exp_pos = expected.get('positions', {})
        act_pos = actual.get('positions', {})
        if set(exp_pos.keys()) != set(act_pos.keys()):
            mismatches.append('position_symbol_set_mismatch')

        drift_abs = 0.0
        for sym in set(exp_pos.keys()).intersection(act_pos.keys()):
            drift_abs += abs(exp_pos[sym].get('quantity', 0.0) - act_pos[sym].get('quantity', 0.0))
            drift_abs += abs(exp_pos[sym].get('avg_entry_price', 0.0) - act_pos[sym].get('avg_entry_price', 0.0))

        if drift_abs > self.drift_tolerance:
            mismatches.append('position_drift_exceeded')

        missing_updates = max(0, int(expected.get('update_count', 0) - actual.get('update_count', 0)))
        if missing_updates > 0:
            mismatches.append('missing_updates_detected')

        result = ReconciliationResult(
            timestamp=datetime.now(timezone.utc),
            mismatches=mismatches,
            drift_abs=drift_abs,
            missing_updates=missing_updates,
        )
        self.daily_results.append(result)
        logger.info('Reconciliation run', extra={
            'ok': result.ok,
            'mismatches': mismatches,
            'drift_abs': drift_abs,
            'missing_updates': missing_updates,
        })
        return result

    def daily_summary(self) -> Dict:
        total = len(self.daily_results)
        failed = sum(1 for r in self.daily_results if not r.ok)
        summary = {
            'runs': total,
            'failed_runs': failed,
            'success_rate': (total - failed) / total if total else 1.0,
            'max_drift_abs': max((r.drift_abs for r in self.daily_results), default=0.0),
            'total_missing_updates': sum(r.missing_updates for r in self.daily_results),
        }
        logger.info('Daily reconciliation summary', extra=summary)
        return summary

    def reset_day(self) -> None:
        self.daily_results = []
