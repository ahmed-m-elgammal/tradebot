"""
Mean Reversion Trading Strategy

Simple mean reversion strategy using Bollinger Bands and RSI.

Entry Logic:
- BUY when price < lower Bollinger Band AND RSI < oversold threshold
- Optional SELL when price > upper Bollinger Band AND RSI > overbought threshold

Exit Logic:
- Exit long when price > middle Bollinger Band OR RSI > overbought
- Exit short when price < middle Bollinger Band OR RSI < oversold
- Optional emergency stop loss and max-bars-in-trade timeout
"""

import pandas as pd
from typing import Dict, Optional
import logging

from src.strategies.base_strategy import BaseStrategy
from src.features.technical_indicators import TechnicalIndicators

logger = logging.getLogger(__name__)


class MeanReversionStrategy(BaseStrategy):
    """
    Mean reversion strategy using Bollinger Bands and RSI.

    This strategy assumes that extreme price movements are temporary
    and price will revert to the mean.

    Configuration:
        - bollinger_window: Moving average window for Bollinger Bands (default: 20)
        - bollinger_std: Standard deviations for bands (default: 2.0)
        - rsi_window: RSI calculation window (default: 14)
        - rsi_oversold: RSI oversold threshold (default: 30)
        - rsi_overbought: RSI overbought threshold (default: 70)
        - long_only: If True, disable short entries (default: True)
        - stop_loss_pct: Emergency stop loss threshold (default: 0.05)
        - max_bars_in_trade: Time stop in bars (default: 0 disables)
    """

    def __init__(self, config: Optional[Dict] = None):
        """Initialize mean reversion strategy."""
        super().__init__(config)

        # Bollinger Band parameters
        self.bb_window = self.config.get('bollinger_window', 20)
        self.bb_std = self.config.get('bollinger_std', 2.0)

        # RSI parameters
        self.rsi_window = self.config.get('rsi_window', 14)
        self.rsi_oversold = self.config.get('rsi_oversold', 30)
        self.rsi_overbought = self.config.get('rsi_overbought', 70)

        # Lifecycle/risk behavior
        self.long_only = self.config.get('long_only', True)
        self.stop_loss_pct = self.config.get('stop_loss_pct', 0.05)
        self.max_bars_in_trade = self.config.get('max_bars_in_trade', 0)

        logger.info(f"Initialized {self.name} with:")
        logger.info(f"  Bollinger: window={self.bb_window}, std={self.bb_std}")
        logger.info(f"  RSI: window={self.rsi_window}, oversold={self.rsi_oversold}, overbought={self.rsi_overbought}")
        logger.info(f"  long_only={self.long_only}, stop_loss_pct={self.stop_loss_pct}, max_bars_in_trade={self.max_bars_in_trade}")

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Generate deterministic position state using entry/exit transitions.

        Returns:
            DataFrame with 'signal' column:
            - 1: Long
            - -1: Short
            - 0: Flat
        """
        df = df.copy()

        indicators = TechnicalIndicators(validate_lookahead=False)
        if 'bb_upper' not in df.columns:
            df = indicators.add_bollinger_bands(df, window=self.bb_window, std=self.bb_std)
        if 'rsi' not in df.columns:
            df = indicators.add_rsi(df, window=self.rsi_window)

        buy_condition = (df['close'] < df['bb_lower']) & (df['rsi'] < self.rsi_oversold)
        sell_condition = (df['close'] > df['bb_upper']) & (df['rsi'] > self.rsi_overbought)

        signals = []
        current_position = 0
        entry_price = None
        bars_in_trade = 0

        for idx, row in df.iterrows():
            exit_now = False

            if current_position != 0:
                bars_in_trade += 1

                if current_position == 1:
                    mean_exit = (row['close'] > row['bb_middle']) or (row['rsi'] > self.rsi_overbought)
                    stop_exit = entry_price is not None and row['close'] <= entry_price * (1 - self.stop_loss_pct)
                    timeout_exit = self.max_bars_in_trade > 0 and bars_in_trade >= self.max_bars_in_trade
                    exit_now = mean_exit or stop_exit or timeout_exit
                else:
                    mean_exit = (row['close'] < row['bb_middle']) or (row['rsi'] < self.rsi_oversold)
                    stop_exit = entry_price is not None and row['close'] >= entry_price * (1 + self.stop_loss_pct)
                    timeout_exit = self.max_bars_in_trade > 0 and bars_in_trade >= self.max_bars_in_trade
                    exit_now = mean_exit or stop_exit or timeout_exit

            if exit_now:
                current_position = 0
                entry_price = None
                bars_in_trade = 0

            if current_position == 0:
                if buy_condition.loc[idx]:
                    current_position = 1
                    entry_price = row['close']
                    bars_in_trade = 0
                elif (not self.long_only) and sell_condition.loc[idx]:
                    current_position = -1
                    entry_price = row['close']
                    bars_in_trade = 0

            signals.append(current_position)

        df['signal'] = pd.Series(signals, index=df.index, dtype=int)

        self.validate_signals(df)
        self.log_strategy_stats(df)
        return df

    def get_signal_description(self, row: pd.Series) -> str:
        """Get detailed description of signal."""
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
        """Get suggested entry prices and targets."""
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
