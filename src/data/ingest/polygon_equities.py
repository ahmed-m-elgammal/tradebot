
import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional
from src.data.ingest.base_ingestor import BaseIngestor

class PolygonEquitiesIngestor(BaseIngestor):
    """
    Ingestor for US Equities via Polygon.io API.
    """
    
    BASE_URL = "https://api.polygon.io"
    
    def connect(self):
        # Polygon uses API key in query params, so explicit connection isn't needed
        # but we can verify credentials here if we want.
        url = f"{self.BASE_URL}/v1/marketstatus/now?apiKey={self.api_key}"
        try:
            response = requests.get(url)
            response.raise_for_status()
            print("Connected to Polygon.io successfully.")
        except requests.exceptions.RequestException as e:
            print(f"Failed to connect to Polygon.io: {e}")
            raise e

    def fetch_data(self, symbol: str, start_date: datetime, end_date: datetime, interval: str) -> pd.DataFrame:
        """
        Fetches aggregates (bars) from Polygon.io.
        """
        # Map interval (e.g., '1m', '1d') to Polygon params
        timespan = 'minute'
        multiplier = 1
        if interval == '1d':
            timespan = 'day'
        elif interval == '1h':
            timespan = 'hour'
        elif interval == '5m':
             timespan = 'minute'
             multiplier = 5
        # Add more mappings as needed
        
        start_str = start_date.strftime('%Y-%m-%d')
        end_str = end_date.strftime('%Y-%m-%d')
        
        # Polygon API endpoint: /v2/aggs/ticker/{stocksTicker}/range/{multiplier}/{timespan}/{from}/{to}
        endpoint = f"/v2/aggs/ticker/{symbol}/range/{multiplier}/{timespan}/{start_str}/{end_str}"
        url = f"{self.BASE_URL}{endpoint}"
        
        params = {
            'apiKey': self.api_key,
            'limit': 50000, # Max limit per request
            'adjusted': 'true',
            'sort': 'asc'
        }
        
        print(f"Requesting URL: {url}")
        
        all_results = []
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            if 'results' in data:
                all_results.extend(data['results'])
            
            # Handle pagination if necessary (Polygon aggs usually return all in one go or link to next, 
            # but usually for ranges < 50k bars it's one shot. For critical path, implement next_url handling)

        except requests.exceptions.RequestException as e:
            print(f"Error fetching data for {symbol}: {e}")
            raise e

        if not all_results:
            return pd.DataFrame()
            
        # Convert to DataFrame
        df = pd.DataFrame(all_results)
        
        # Rename columns to match schema
        # Polygon returns: v (volume), vw (vwap), o (open), c (close), h (high), l (low), t (timestamp), n (transactions)
        df.rename(columns={
            'v': 'volume',
            'o': 'open',
            'c': 'close',
            'h': 'high',
            'l': 'low',
            't': 'timestamp'
        }, inplace=True)
        
        # Convert timestamp (ms) to datetime
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        
        # Select required columns
        df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
        
        return df
