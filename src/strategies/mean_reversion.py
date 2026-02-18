"""
Mean Reversion Trading Strategy

Simple mean reversion strategy using Bollinger Bands and RSI.
"""

import pandas as pd
from typing import Dict, Optional
import logging

from src.strategies.base_strategy import BaseStrategy
from src.features.technical_indicators import TechnicalIndicators

logger = logging.getLogger(__name__)


class MeanReversionStrategy(BaseStrategy):
    """Mean reversion strategy using Bollinger Bands and RSI."""

    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)

        self.bb_window = self.config.get('bollinger_window', 20)
        self.bb_std = self.config.get('bollinger_std', 2.0)
        self.rsi_window = self.config.get('rsi_window', 14)
        self.rsi_oversold = self.config.get('rsi_oversold', 30)
        self.rsi_overbought = self.config.get('rsi_overbought', 70)

        self.long_only = self.config.get('long_only', True)
        self.stop_loss_pct = self.config.get('stop_loss_pct', 0.05)
        self.max_bars_in_trade = self.config.get('max_bars_in_trade', 0)
        self.atr_stop_mult = self.config.get('atr_stop_mult', 0.0)
        self.volatility_kill_switch = self.config.get('volatility_kill_switch', 0.0)

    def fit(self, train_df: pd.DataFrame) -> None:
        """Calibrate lightweight thresholds using training data in walk-forward."""
        if train_df.empty or 'close' not in train_df.columns:
            return
        ret_std = float(train_df['close'].pct_change().std())
        if ret_std > 0:
            # conservative dynamic stop calibration bounded by config default envelope
            calibrated = min(0.10, max(0.01, ret_std * 6.0))
            self.stop_loss_pct = calibrated

    def _get_stop_price(self, row: pd.Series, entry_price: float, side: int) -> float:
        fixed_stop = entry_price * (1 - self.stop_loss_pct) if side == 1 else entry_price * (1 + self.stop_loss_pct)
        if self.atr_stop_mult > 0 and 'atr' in row and pd.notna(row['atr']):
            atr_stop = entry_price - self.atr_stop_mult * row['atr'] if side == 1 else entry_price + self.atr_stop_mult * row['atr']
            return max(fixed_stop, atr_stop) if side == 1 else min(fixed_stop, atr_stop)
        return fixed_stop

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()

        indicators = TechnicalIndicators(validate_lookahead=False)
        if 'bb_upper' not in df.columns:
            df = indicators.add_bollinger_bands(df, window=self.bb_window, std=self.bb_std)
        if 'rsi' not in df.columns:
            df = indicators.add_rsi(df, window=self.rsi_window)
        if 'atr' not in df.columns:
            df = indicators.add_atr(df)

        buy_condition = (df['close'] < df['bb_lower']) & (df['rsi'] < self.rsi_oversold)
        sell_condition = (df['close'] > df['bb_upper']) & (df['rsi'] > self.rsi_overbought)

        signals = []
        current_position = 0
        entry_price = None
        stop_price = None
        bars_in_trade = 0

        for idx, row in df.iterrows():
            if self.volatility_kill_switch > 0 and pd.notna(row.get('atr')) and row['close'] > 0:
                atr_pct = row['atr'] / row['close']
                if atr_pct >= self.volatility_kill_switch:
                    current_position = 0
                    entry_price = None
                    stop_price = None
                    bars_in_trade = 0
                    signals.append(0)
                    continue

            exit_now = False
            if current_position != 0:
                bars_in_trade += 1
                if current_position == 1:
                    mean_exit = (row['close'] > row['bb_middle']) or (row['rsi'] > self.rsi_overbought)
                    stop_exit = stop_price is not None and row['close'] <= stop_price
                    timeout_exit = self.max_bars_in_trade > 0 and bars_in_trade >= self.max_bars_in_trade
                    exit_now = mean_exit or stop_exit or timeout_exit
                else:
                    mean_exit = (row['close'] < row['bb_middle']) or (row['rsi'] < self.rsi_oversold)
                    stop_exit = stop_price is not None and row['close'] >= stop_price
                    timeout_exit = self.max_bars_in_trade > 0 and bars_in_trade >= self.max_bars_in_trade
                    exit_now = mean_exit or stop_exit or timeout_exit

            if exit_now:
                current_position = 0
                entry_price = None
                stop_price = None
                bars_in_trade = 0

            if current_position == 0:
                if bool(buy_condition.loc[idx]):
                    current_position = 1
                    entry_price = float(row['close'])
                    stop_price = self._get_stop_price(row, entry_price, side=1)
                    bars_in_trade = 0
                elif (not self.long_only) and bool(sell_condition.loc[idx]):
                    current_position = -1
                    entry_price = float(row['close'])
                    stop_price = self._get_stop_price(row, entry_price, side=-1)
                    bars_in_trade = 0

            signals.append(current_position)

        df['signal'] = pd.Series(signals, index=df.index, dtype=int)

        self.validate_signals(df)
        self.log_strategy_stats(df)
        return df

    def get_signal_description(self, row: pd.Series) -> str:
        if row['signal'] == 1:
            return (f"BUY: Price ({row['close']:.2f}) below lower BB ({row['bb_lower']:.2f}), "
                    f"RSI ({row['rsi']:.1f}) oversold (< {self.rsi_oversold})")
        if row['signal'] == -1:
            return (f"SELL: Price ({row['close']:.2f}) above upper BB ({row['bb_upper']:.2f}), "
                    f"RSI ({row['rsi']:.1f}) overbought (> {self.rsi_overbought})")
        if 'bb_middle' in row and 'rsi' in row:
            return f"FLAT: Price near mean ({row['bb_middle']:.2f}), RSI neutral ({row['rsi']:.1f})"
        return "FLAT: No signal"

    def get_entry_price_targets(self, row: pd.Series) -> Dict:
        if row['signal'] == 1:
            return {
                'entry': row['close'],
                'stop_loss': row['bb_lower'] * 0.98,
                'take_profit': row['bb_middle'],
                'risk_reward': abs((row['bb_middle'] - row['close']) /
                                   (row['close'] - row['bb_lower'] * 0.98))
            }
        if row['signal'] == -1:
            return {
                'entry': row['close'],
                'stop_loss': row['bb_upper'] * 1.02,
                'take_profit': row['bb_middle'],
                'risk_reward': abs((row['close'] - row['bb_middle']) /
                                   (row['bb_upper'] * 1.02 - row['close']))
            }
        return {}
