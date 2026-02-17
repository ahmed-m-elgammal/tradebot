
import ccxt
import pandas as pd
from datetime import datetime, timedelta, timezone
from src.data.ingest.base_ingestor import BaseIngestor

class CCXTCryptoIngestor(BaseIngestor):
    """
    Ingestor for Crypto Exchanges via CCXT.
    """
    
    def __init__(self, exchange_id: str, api_key: str = None, secret: str = None):
        super().__init__(api_key)
        self.output_ohlcv = True
        self.exchange_id = exchange_id
        try:
            exchange_class = getattr(ccxt, exchange_id)
            self.exchange = exchange_class({
                'apiKey': api_key,
                'secret': secret,
                'enableRateLimit': True
            })
        except AttributeError:
             raise ValueError(f"Exchange {exchange_id} not supported by CCXT")
             
    def connect(self):
        # CCXT handles connection implicitly, but we can check if exchange is responsive
        try:
            self.exchange.load_markets()
            print(f"Connected to {self.exchange_id} successfully.")
        except Exception as e:
            print(f"Failed to connect to {self.exchange_id}: {e}")
            raise e

    def fetch_data(self, symbol: str, start_date: datetime, end_date: datetime, interval: str) -> pd.DataFrame:
        """
        Fetches OHLCV data from the exchange.
        """
        # Convert start_date to timestamp (ms) as CCXT expects
        since = int(start_date.timestamp() * 1000)
        
        limit = None # Use default limit or specific if needed
        
        all_ohlcv = []
        current_since = since
        end_timestamp = int(end_date.timestamp() * 1000)
        
        print(f"Fetching {symbol} from {self.exchange_id} starting at {start_date}...")
        
        while current_since < end_timestamp:
             try:
                ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe=interval, since=current_since, limit=1000)
                if not ohlcv:
                     print("No more data returned.")
                     break
                
                all_ohlcv.extend(ohlcv)
                
                # Check the last timestamp
                last_timestamp = ohlcv[-1][0]
                
                # If we received data up to end_date, stop
                if last_timestamp >= end_timestamp:
                     break
                
                # Move 'since' forward. 
                # Careful: fetch_ohlcv is inclusive of 'since', so we need next candle time
                # Or simply use the last timestamp + 1ms to avoid duplicates (though some overlap is safer to dedup later)
                current_since = last_timestamp + 1
             except Exception as e:
                 print(f"Error fetching data from {self.exchange_id}: {e}")
                 # For robustness, maybe retry or break
                 break

        if not all_ohlcv:
             return pd.DataFrame()
             
        # Convert to DataFrame
        # CCXT structure: [timestamp, open, high, low, close, volume]
        df = pd.DataFrame(all_ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        # Convert timestamp (ms) to datetime
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        
        # Filter strictly within requested range
        mask = (df['timestamp'] >= start_date) & (df['timestamp'] <= end_date)
        df = df.loc[mask]
        
        return df
