
from pathlib import Path
from src.data.storage.parquet_store import ParquetStore

class DataLake:
    """
    Manages the Data Lake structure with separation of concerns:
    - Raw: Immutable, exactly as ingested (validated but raw)
    - Processed: Cleaned, gaps filled, adjusted
    """
    
    def __init__(self, base_dir: str):
        self.base_dir = Path(base_dir)
        self.raw_dir = self.base_dir / "raw"
        self.processed_dir = self.base_dir / "processed"
        
        self.raw_store = ParquetStore(str(self.raw_dir))
        self.processed_store = ParquetStore(str(self.processed_dir))

    def get_raw_store(self) -> ParquetStore:
        return self.raw_store
        
    def get_processed_store(self) -> ParquetStore:
        return self.processed_store
