from typing import Dict, Optional
import requests
import logging
import time
import pandas as pd

class CoinGeckoAPI:
    BASE_URL = "https://api.coingecko.com/api/v3"

    def __init__(self):
        self.session = requests.Session()

    def _make_request_with_backoff(self, url: str, params: dict = None, max_retries: int = 10, max_wait: int = 10):
        """Make API request with exponential backoff retry mechanism"""
        for attempt in range(max_retries):
            try:
                response = self.session.get(url, params=params)

                if response.status_code == 200:
                    return response

                if response.status_code == 429:
                    wait_time = min(2 ** attempt, max_wait)
                    logging.warning(f"Rate limited. Waiting {wait_time} seconds...")
                    time.sleep(wait_time)
                    continue

                response.raise_for_status()

            except Exception as e:
                if attempt == max_retries - 1:
                    raise

                wait_time = min(2 ** attempt, max_wait)
                logging.error(f"Attempt {attempt + 1} failed: {e}. Retrying in {wait_time} seconds...")
                time.sleep(wait_time)

        return None

    def get_price_history(self, token: str, days: int = 7) -> Optional[pd.DataFrame]:
        """Get historical price data for a token"""
        try:
            response = self._make_request_with_backoff(
                f"{self.BASE_URL}/coins/{token}/market_chart",
                params={
                    'vs_currency': 'usd',
                    'days': str(days),
                }
            )

            if not response:
                return None

            prices = response.json()['prices']
            df = pd.DataFrame(prices, columns=['timestamp', 'price'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)

            return df

        except Exception as e:
            logging.error(f"Error fetching history for {token}: {e}")
            return None
