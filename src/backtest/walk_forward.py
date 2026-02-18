"""Walk-forward validation utilities."""

from typing import List, Dict, Tuple, Optional, Callable
import copy
import pandas as pd


class WalkForwardValidator:
    """Rolling train/test backtest evaluator with optional per-fold calibration."""

    def __init__(self, backtester, train_size: int = 252, test_size: int = 63):
        self.backtester = backtester
        self.train_size = train_size
        self.test_size = test_size

    def run(
        self,
        strategy,
        data: pd.DataFrame,
        position_sizer=None,
        sizing_params=None,
        calibrator: Optional[Callable] = None,
    ) -> Tuple[List[Dict], pd.DataFrame]:
        """Run walk-forward folds and return fold metrics and summary frame."""
        fold_metrics: List[Dict] = []

        for i in range(0, len(data) - self.train_size - self.test_size + 1, self.test_size):
            train = data.iloc[i:i + self.train_size].copy()
            test = data.iloc[i + self.train_size:i + self.train_size + self.test_size].copy()
            if train.empty or test.empty:
                continue

            strategy_fold = copy.deepcopy(strategy)
            if calibrator is not None:
                calibrator(strategy_fold, train)
            elif hasattr(strategy_fold, 'fit') and callable(getattr(strategy_fold, 'fit')):
                strategy_fold.fit(train)

            results, metrics = self.backtester.run(
                strategy_fold,
                test,
                position_sizer=position_sizer,
                sizing_params=sizing_params,
            )
            fold_metrics.append({
                'fold_start': test.index.min(),
                'fold_end': test.index.max(),
                **metrics,
                'bars': len(results),
            })

        summary = pd.DataFrame(fold_metrics)
        return fold_metrics, summary
