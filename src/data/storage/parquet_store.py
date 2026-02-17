
import pandas as pd
import os
from datetime import datetime, timedelta
from pathlib import Path

class ParquetStore:
    """
    Handles storage of market data in Parquet format.
    Partition strategy: base_dir / symbol / interval / year / month / data.parquet
    """
    
    def __init__(self, base_dir: str):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _get_path(self, symbol: str, interval: str, date: datetime) -> Path:
        """Constructs the path for a specific day's data."""
        # Sanitize symbol for filesystem (e.g., BTC/USDT -> BTC_USDT)
        safe_symbol = symbol.replace('/', '_')
        year = str(date.year)
        month = f"{date.month:02d}"
        
        path = self.base_dir / safe_symbol / interval / year / month
        path.mkdir(parents=True, exist_ok=True)
        return path / f"{date.strftime('%Y-%m-%d')}.parquet"

    def save(self, df: pd.DataFrame, symbol: str, interval: str):
        """
        Saves DataFrame to Parquet, partitioned by day.
        Expects 'timestamp' column to be present.
        """
        if df.empty:
            print("No data to save.")
            return

        # Ensure timestamp is datetime
        if not pd.api.types.is_datetime64_any_dtype(df['timestamp']):
             df['timestamp'] = pd.to_datetime(df['timestamp'])

        # Group by day and save
        # This handles if the input DF spans multiple days
        grouped = df.groupby(df['timestamp'].dt.date)
        
        for date_obj, group_df in grouped:
             # Convert date_obj back to datetime for path generation
             dt = datetime.combine(date_obj, datetime.min.time())
             file_path = self._get_path(symbol, interval, dt)
             
             print(f"Saving {len(group_df)} rows to {file_path}")
             
             # If file exists, we might want to append or overwrite. 
             # For simplicity in MVP, we overwrite or robustly combine.
             # Combining is better to avoid data loss if we fetch partial days.
             if file_path.exists():
                 existing_df = pd.read_parquet(file_path)
                 combined_df = pd.concat([existing_df, group_df]).drop_duplicates(subset=['timestamp']).sort_values('timestamp')
                 combined_df.to_parquet(file_path, index=False)
             else:
                 group_df.to_parquet(file_path, index=False)

    def load(self, symbol: str, interval: str, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """
        Loads data from Parquet within the specified range.
        Optimized to read only necessary partitions.
        """
        # This is a simplified loader. In production, use a library like partitioning intent or 
        # iterate explicitly over the directory structure.
        
        all_dfs = []
        
        # Iterate through all days in range
        delta = end_date - start_date
        for i in range(delta.days + 1):
             day = start_date + timedelta(days=i)
             file_path = self._get_path(symbol, interval, day)
             
             if file_path.exists():
                 day_df = pd.read_parquet(file_path)
                 all_dfs.append(day_df)
        
        if not all_dfs:
             return pd.DataFrame()
             
        combined_df = pd.concat(all_dfs, ignore_index=True)
        
        # Filter exact timestamps
        mask = (combined_df['timestamp'] >= start_date) & (combined_df['timestamp'] <= end_date)
        return combined_df.loc[mask].sort_values('timestamp').reset_index(drop=True)
