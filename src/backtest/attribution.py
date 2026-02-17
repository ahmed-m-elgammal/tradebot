"""
P&L Attribution Analysis

Breakdown and analysis of profit/loss sources.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class Trade:
    """Individual trade record."""
    timestamp: pd.Timestamp
    symbol: str
    side: str  # 'BUY' or 'SELL'
    quantity: float
    entry_price: float
    exit_price: Optional[float] = None
    exit_timestamp: Optional[pd.Timestamp] = None
    commission: float = 0.0
    slippage: float = 0.0
    
    @property
    def is_closed(self) -> bool:
        """Check if trade is closed."""
        return self.exit_price is not None
    
    @property
    def pnl(self) -> float:
        """Calculate P&L for closed trade."""
        if not self.is_closed:
            return 0.0
        
        if self.side == 'BUY':
            gross_pnl = self.quantity * (self.exit_price - self.entry_price)
        else:  # SELL
            gross_pnl = self.quantity * (self.entry_price - self.exit_price)
        
        # Subtract costs
        net_pnl = gross_pnl - self.commission - self.slippage
        return net_pnl
    
    @property
    def return_pct(self) -> float:
        """Return as percentage."""
        if not self.is_closed or self.entry_price == 0:
            return 0.0
        
        return self.pnl / (self.quantity * self.entry_price)
    
    @property
    def holding_period(self) -> Optional[pd.Timedelta]:
        """Time held."""
        if not self.is_closed:
            return None
        return self.exit_timestamp - self.timestamp


class AttributionAnalyzer:
    """
    Analyze P&L attribution across different dimensions.
    
    Breaks down performance by:
    - Time period (daily, weekly, monthly)
    - Symbol
    - Strategy
    - Long vs short
    - Cost components (commission, slippage)
    """
    
    def __init__(self):
        """Initialize analyzer."""
        self.trades: List[Trade] = []
    
    def add_trade(self, trade: Trade):
        """Add trade to analysis."""
        self.trades.append(trade)
        logger.debug(f"Added trade: {trade.symbol} {trade.side} @ {trade.entry_price}")
    
    def analyze_by_time(self, frequency: str = 'D') -> pd.DataFrame:
        """
        Analyze P&L by time period.
        
        Args:
            frequency: Pandas frequency string ('D', 'W', 'M')
            
        Returns:
            DataFrame with P&L by period
        """
        if not self.trades:
            return pd.DataFrame()
        
        closed_trades = [t for t in self.trades if t.is_closed]
        if not closed_trades:
            return pd.DataFrame()
        
        # Create DataFrame
        df = pd.DataFrame([
            {
                'timestamp': t.exit_timestamp,
                'pnl': t.pnl,
                'return_pct': t.return_pct,
                'commission': t.commission,
                'slippage': t.slippage
            }
            for t in closed_trades
        ])
        
        # Group by period
        df.set_index('timestamp', inplace=True)
        grouped = df.groupby(pd.Grouper(freq=frequency)).agg({
            'pnl': ['sum', 'count', 'mean'],
            'return_pct': 'mean',
            'commission': 'sum',
            'slippage': 'sum'
        })
        
        # Flatten column names
        grouped.columns = ['_'.join(col).strip() for col in grouped.columns.values]
        grouped.rename(columns={
            'pnl_sum': 'total_pnl',
            'pnl_count': 'num_trades',
            'pnl_mean': 'avg_pnl',
            'return_pct_mean': 'avg_return_pct',
            'commission_sum': 'total_commission',
            'slippage_sum': 'total_slippage'
        }, inplace=True)
        
        # Add cumulative P&L
        grouped['cumulative_pnl'] = grouped['total_pnl'].cumsum()
        
        return grouped
    
    def analyze_by_symbol(self) -> pd.DataFrame:
        """
        Analyze P&L by symbol.
        
        Returns:
            DataFrame with P&L by symbol
        """
        closed_trades = [t for t in self.trades if t.is_closed]
        if not closed_trades:
            return pd.DataFrame()
        
        # Group by symbol
        symbol_data = {}
        for trade in closed_trades:
            if trade.symbol not in symbol_data:
                symbol_data[trade.symbol] = {
                    'pnl': [],
                    'return_pct': [],
                    'num_trades': 0,
                    'commission': 0,
                    'slippage': 0
                }
            
            symbol_data[trade.symbol]['pnl'].append(trade.pnl)
            symbol_data[trade.symbol]['return_pct'].append(trade.return_pct)
            symbol_data[trade.symbol]['num_trades'] += 1
            symbol_data[trade.symbol]['commission'] += trade.commission
            symbol_data[trade.symbol]['slippage'] += trade.slippage
        
        # Create DataFrame
        rows = []
        for symbol, data in symbol_data.items():
            rows.append({
                'symbol': symbol,
                'total_pnl': sum(data['pnl']),
                'avg_pnl': np.mean(data['pnl']),
                'avg_return_pct': np.mean(data['return_pct']),
                'num_trades': data['num_trades'],
                'win_rate': sum(1 for p in data['pnl'] if p > 0) / len(data['pnl']),
                'total_commission': data['commission'],
                'total_slippage': data['slippage']
            })
        
        df = pd.DataFrame(rows)
        df.sort_values('total_pnl', ascending=False, inplace=True)
        return df
    
    def analyze_by_direction(self) -> Dict:
        """
        Analyze P&L by long vs short.
        
        Returns:
            Dictionary with stats for longs and shorts
        """
        closed_trades = [t for t in self.trades if t.is_closed]
        
        longs = [t for t in closed_trades if t.side == 'BUY']
        shorts = [t for t in closed_trades if t.side == 'SELL']
        
        def calc_stats(trades):
            if not trades:
                return {
                    'num_trades': 0,
                    'total_pnl': 0,
                    'avg_pnl': 0,
                    'win_rate': 0,
                    'avg_winner': 0,
                    'avg_loser': 0
                }
            
            pnls = [t.pnl for t in trades]
            winners = [p for p in pnls if p > 0]
            losers = [p for p in pnls if p < 0]
            
            return {
                'num_trades': len(trades),
                'total_pnl': sum(pnls),
                'avg_pnl': np.mean(pnls),
                'win_rate': len(winners) / len(pnls) if pnls else 0,
                'avg_winner': np.mean(winners) if winners else 0,
                'avg_loser': np.mean(losers) if losers else 0
            }
        
        return {
            'long': calc_stats(longs),
            'short': calc_stats(shorts),
            'total': calc_stats(closed_trades)
        }
    
    def analyze_costs(self) -> Dict:
        """
        Analyze cost breakdown.
        
        Returns:
            Dictionary with cost analysis
        """
        closed_trades = [t for t in self.trades if t.is_closed]
        
        if not closed_trades:
            return {
                'total_commission': 0,
                'total_slippage': 0,
                'total_costs': 0,
                'gross_pnl': 0,
                'net_pnl': 0,
                'cost_ratio': 0
            }
        
        total_commission = sum(t.commission for t in closed_trades)
        total_slippage = sum(t.slippage for t in closed_trades)
        total_costs = total_commission + total_slippage
        
        # Calculate gross P&L (before costs)
        gross_pnl = sum(t.pnl + t.commission + t.slippage for t in closed_trades)
        net_pnl = sum(t.pnl for t in closed_trades)
        
        return {
            'total_commission': total_commission,
            'total_slippage': total_slippage,
            'total_costs': total_costs,
            'gross_pnl': gross_pnl,
            'net_pnl': net_pnl,
            'cost_ratio': total_costs / abs(gross_pnl) if gross_pnl != 0 else 0,
            'commission_pct': total_commission / total_costs if total_costs > 0 else 0,
            'slippage_pct': total_slippage / total_costs if total_costs > 0 else 0
        }
    
    def get_summary(self) -> Dict:
        """
        Get comprehensive attribution summary.
        
        Returns:
            Dictionary with full attribution breakdown
        """
        closed_trades = [t for t in self.trades if t.is_closed]
        
        if not closed_trades:
            logger.warning("No closed trades to analyze")
            return {
                'num_trades': 0,
                'total_pnl': 0,
                'by_direction': {},
                'by_costs': {},
                'top_symbols': []
            }
        
        summary = {
            'num_trades': len(closed_trades),
            'num_open': len(self.trades) - len(closed_trades),
            'total_pnl': sum(t.pnl for t in closed_trades),
            'avg_pnl_per_trade': np.mean([t.pnl for t in closed_trades]),
            'by_direction': self.analyze_by_direction(),
            'by_costs': self.analyze_costs(),
        }
        
        # Top/bottom symbols
        by_symbol = self.analyze_by_symbol()
        if not by_symbol.empty:
            summary['top_symbols'] = by_symbol.head(5).to_dict('records')
            summary['bottom_symbols'] = by_symbol.tail(5).to_dict('records')
        
        return summary
    
    def generate_report(self) -> str:
        """
        Generate human-readable attribution report.
        
        Returns:
            Formatted report string
        """
        summary = self.get_summary()
        
        report = []
        report.append("=" * 70)
        report.append("P&L ATTRIBUTION REPORT")
        report.append("=" * 70)
        
        # Overall stats
        report.append(f"\nTotal Trades: {summary['num_trades']}")
        report.append(f"Open Positions: {summary.get('num_open', 0)}")
        report.append(f"Total P&L: ${summary['total_pnl']:.2f}")
        report.append(f"Average P&L per Trade: ${summary.get('avg_pnl_per_trade', 0):.2f}")
        
        # Direction breakdown
        if 'by_direction' in summary:
            report.append("\n" + "-" * 70)
            report.append("BY DIRECTION")
            report.append("-" * 70)
            
            for direction in ['long', 'short', 'total']:
                stats = summary['by_direction'].get(direction, {})
                report.append(f"\n{direction.upper()}:")
                report.append(f"  Trades: {stats.get('num_trades', 0)}")
                report.append(f"  Total P&L: ${stats.get('total_pnl', 0):.2f}")
                report.append(f"  Win Rate: {stats.get('win_rate', 0):.1%}")
                report.append(f"  Avg Winner: ${stats.get('avg_winner', 0):.2f}")
                report.append(f"  Avg Loser: ${stats.get('avg_loser', 0):.2f}")
        
        # Cost breakdown
        if 'by_costs' in summary:
            costs = summary['by_costs']
            report.append("\n" + "-" * 70)
            report.append("COST BREAKDOWN")
            report.append("-" * 70)
            report.append(f"Commission: ${costs.get('total_commission', 0):.2f} ({costs.get('commission_pct', 0):.1%})")
            report.append(f"Slippage: ${costs.get('total_slippage', 0):.2f} ({costs.get('slippage_pct', 0):.1%})")
            report.append(f"Total Costs: ${costs.get('total_costs', 0):.2f}")
            report.append(f"Cost Ratio: {costs.get('cost_ratio', 0):.2%} of gross P&L")
            report.append(f"Gross P&L: ${costs.get('gross_pnl', 0):.2f}")
            report.append(f"Net P&L: ${costs.get('net_pnl', 0):.2f}")
        
        # Top symbols
        if 'top_symbols' in summary and summary['top_symbols']:
            report.append("\n" + "-" * 70)
            report.append("TOP SYMBOLS (by P&L)")
            report.append("-" * 70)
            for sym in summary['top_symbols']:
                report.append(f"{sym['symbol']}: ${sym['total_pnl']:.2f} ({sym['num_trades']} trades, {sym['win_rate']:.1%} win rate)")
        
        report.append("\n" + "=" * 70)
        
        return "\n".join(report)
