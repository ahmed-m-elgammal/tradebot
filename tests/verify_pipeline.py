
import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
from pathlib import Path
import shutil

# Add src to path
sys.path.append(os.path.join(os.getcwd(), 'src'))
sys.path.append(os.getcwd())

from src.data.ingest.validator import DataValidator
from src.data.storage.data_lake import DataLake
from src.data.quality.gap_detector import GapDetector
from src.data.quality.staleness_monitor import StalenessMonitor
from src.data.quality.outlier_detector import OutlierDetector

def create_mock_data(start_date, end_date, freq='1min'):
    dates = pd.date_range(start=start_date, end=end_date, freq=freq)
    n = len(dates)
    
    # Random walk price
    price = 100 + np.cumsum(np.random.randn(n))
    
    df = pd.DataFrame({
        'timestamp': dates,
        'open': price,
        'high': price + 0.1,
        'low': price - 0.1,
        'close': price + 0.05,
        'volume': np.random.randint(100, 1000, n).astype(float)
    })
    return df

def run_verification():
    print("=== Starting Phase 1.1 Core Data Pipeline Verification ===")
    
    # Setup test env
    if os.path.exists("test_data_lake"):
        shutil.rmtree("test_data_lake")
    
    data_lake = DataLake("test_data_lake")
    validator = DataValidator()
    
    # 1. Simulate Ingestion & Validation
    print("\n[Test 1] Ingestion & Validation")
    start = datetime.now(timezone.utc) - timedelta(hours=2)
    end = datetime.now(timezone.utc)
    
    df_mock = create_mock_data(start, end)
    
    try:
        validator.validate(df_mock)
        print("✅ Validation passed for valid mock data.")
    except Exception as e:
        print(f"❌ Validation FAILED: {e}")
        return

    # 2. Storage (Parquet)
    print("\n[Test 2] Storage (Parquet)")
    symbol = "TEST_BTC_USDT"
    data_lake.get_raw_store().save(df_mock, symbol, "1m")
    
    # Read back
    df_read = data_lake.get_raw_store().load(symbol, "1m", start, end)
    
    if len(df_mock) == len(df_read):
        print(f"✅ Storage Read/Write successful. Rows: {len(df_read)}")
    else:
        print(f"❌ Storage Mismatch! Wrote {len(df_mock)}, Read {len(df_read)}")
        return

    # 3. Quality Checks: Gap Detection
    print("\n[Test 3] Gap Detection")
    # Introduce a gap
    df_gap = df_mock.copy()
    df_gap = df_gap.drop(df_gap.index[10:20]) # Drop 10 mins
    
    gaps = GapDetector().detect_gaps(df_gap, "1m")
    if len(gaps) > 0:
        print(f"✅ Gap detection successful. Found {len(gaps)} gaps.")
        print(f"   Gap details: {gaps[0]}")
    else:
        print("❌ Gap detection FAILED. Expected gaps but found none.")

    # 4. Quality Checks: Staleness
    print("\n[Test 4] Staleness Monitor")
    stale_df = df_mock.copy()
    # Make it old
    stale_df['timestamp'] = stale_df['timestamp'] - timedelta(hours=5)
    
    staleness = StalenessMonitor().check_staleness(stale_df, threshold_minutes=15)
    if staleness > 15:
        print(f"✅ Staleness detection successful. Delay: {staleness:.2f} mins")
    else:
        print(f"❌ Staleness detection FAILED. Delay: {staleness:.2f}")

    # 5. Quality Checks: Outliers
    print("\n[Test 5] Outlier Detection")
    outlier_df = df_mock.copy()
    # Inject outlier
    outlier_df.loc[50, 'close'] = outlier_df.loc[50, 'close'] * 1.5 # 50% jump
    
    outliers = OutlierDetector().detect_outliers(outlier_df, method='pct_change', threshold=0.2)
    if not outliers.empty:
         print(f"✅ Outlier detection successful. Found {len(outliers)} outliers.")
    else:
         print("❌ Outlier detection FAILED.")
         
    print("\n=== Verification Complete ===")
    
    # Cleanup
    if os.path.exists("test_data_lake"):
        shutil.rmtree("test_data_lake")

if __name__ == "__main__":
    run_verification()
