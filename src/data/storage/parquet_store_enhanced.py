"""
Enhanced Parquet Store with Compression and Metadata

Integrated with configuration and logging.
"""

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from pathlib import Path
from typing import Optional, Dict
import hashlib
import json
from datetime import datetime
import sys
sys.path.insert(0, 'c:\\Users\\A-Dev\\Desktop\\Trading Bot')

from src.config import get_config
from src.utils.logger import get_logger
from src.utils.exceptions import StorageError

logger = get_logger(__name__)


class EnhancedParquetStore:
    """
    Enhanced Parquet storage with compression and metadata tracking.
    
    Features:
    - Snappy compression
    - Schema validation
    - Metadata tracking (checksum, last_updated)
    - Optimized loading with filters
    """
    
    def __init__(self, base_path: str = "data/parquet"):
        """
        Initialize enhanced parquet store.
        
        Args:
            base_path: Base directory for parquet files
        """
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        
        # Load config
        config = get_config()
        self.compression = config.data.storage.compression
        self.validate_schema = config.data.storage.validate_schema
        self.track_metadata = config.data.storage.metadata_tracking
        
        # Define expected schema
        self.expected_schema = pa.schema([
            ('timestamp', pa.timestamp('ms')),
            ('open', pa.float64()),
            ('high', pa.float64()),
            ('low', pa.float64()),
            ('close', pa.float64()),
            ('volume', pa.float64())
        ])
        
        logger.info( "Enhanced Parquet Store initialized", extra={
            'base_path': str(self.base_path),
            'compression': self.compression,
            'validate_schema': self.validate_schema
        })
    
    def save(self, df: pd.DataFrame, symbol: str, timeframe: str) -> None:
        """
        Save DataFrame with compression and metadata.
        
        Args:
            df: DataFrame to save
            symbol: Trading symbol
            timeframe: Timeframe (1m, 5m, etc.)
        """
        try:
            # Create filename
            safe_symbol = symbol.replace('/', '_')
            filepath = self.base_path / f"{safe_symbol}_{timeframe}.parquet"
            
            # Validate schema if enabled
            if self.validate_schema:
                table = pa.Table.from_pandas(df[['timestamp', 'open', 'high', 'low', 'close', 'volume']])
                expected_cols = {field.name for field in self.expected_schema}
                actual_cols = set(table.column_names)
                
                if not expected_cols.issubset(actual_cols):
                    missing = expected_cols - actual_cols
                    raise StorageError(f"Missing required columns: {missing}")
            
            # Save with compression
            df.to_parquet(
                filepath,
                engine='pyarrow',
                compression=self.compression,
                index=False
            )
            
            # Track metadata if enabled
            if self.track_metadata:
                metadata = {
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'rows': len(df),
                    'last_updated': datetime.utcnow().isoformat(),
                    'checksum': self._calculate_checksum(df),
                    'start': df['timestamp'].min().isoformat(),
                    'end': df['timestamp'].max().isoformat()
                }
                
                metadata_file = filepath.with_suffix('.json')
                with open(metadata_file, 'w') as f:
                    json.dump(metadata, f, indent=2)
            
            logger.info(f"Saved {len(df)} rows to parquet", extra={
                'symbol': symbol,
                'timeframe': timeframe,
                'rows': len(df),
                'file': str(filepath),
                'size_mb': filepath.stat().st_size / 1024 / 1024
            })
            
        except Exception as e:
            logger.error(f"Failed to save parquet file", extra={
                'symbol': symbol,
                'timeframe': timeframe,
                'error': str(e)
            })
            raise StorageError(f"Failed to save: {e}") from e
    
    def load(self, symbol: str, timeframe: str, 
             start: Optional[datetime] = None,
             end: Optional[datetime] = None) -> pd.DataFrame:
        """
        Load DataFrame with optional filtering.
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe
            start: Optional start date
            end: Optional end date
            
        Returns:
            Loaded DataFrame
        """
        try:
            safe_symbol = symbol.replace('/', '_')
            filepath = self.base_path / f"{safe_symbol}_{timeframe}.parquet"
            
            if not filepath.exists():
                raise StorageError(f"File not found: {filepath}")
            
            # Load with optional filters (using PyArrow for efficiency)
            if start or end:
                table = pq.read_table(filepath)
                df = table.to_pandas()
                
                if start:
                    df = df[df['timestamp'] >= start]
                if end:
                    df = df[df['timestamp'] <= end]
            else:
                df = pd.read_parquet(filepath)
            
            logger.info(f"Loaded {len(df)} rows from parquet", extra={
                'symbol': symbol,
                'timeframe': timeframe,
                'rows': len(df),
                'file': str(filepath)
            })
            
            return df
            
        except Exception as e:
            logger.error(f"Failed to load parquet file", extra={
                'symbol': symbol,
                'timeframe': timeframe,
                'error': str(e)
            })
            raise StorageError(f"Failed to load: {e}") from e
    
    def _calculate_checksum(self, df: pd.DataFrame) -> str:
        """Calculate MD5 checksum of DataFrame."""
        return hashlib.md5(pd.util.hash_pandas_object(df).values).hexdigest()
    
    def get_metadata(self, symbol: str, timeframe: str) -> Optional[Dict]:
        """Get metadata for a stored file."""
        safe_symbol = symbol.replace('/', '_')
        metadata_file = self.base_path / f"{safe_symbol}_{timeframe}.json"
        
        if metadata_file.exists():
            with open(metadata_file) as f:
                return json.load(f)
        return None
