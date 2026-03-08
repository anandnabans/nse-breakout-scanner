import time, logging
import pandas as pd
from tvDatafeed import TvDatafeed, Interval
from config import TV_USERNAME, TV_PASSWORD, TV_EXCHANGE, TV_LOOKBACK_BARS, NSE_SYMBOLS

logger = logging.getLogger(__name__)

class DataFetcher:
    def __init__(self, delay=0.5):
        self.delay = delay
        self.tv    = TvDatafeed(TV_USERNAME, TV_PASSWORD) if TV_USERNAME else TvDatafeed()

    def fetch_symbol(self, symbol):
        try:
            df = self.tv.get_hist(symbol=symbol, exchange=TV_EXCHANGE,
                                  interval=Interval.in_daily, n_bars=TV_LOOKBACK_BARS)
            if df is None or df.empty:
                return None
            df.columns = [c.lower() for c in df.columns]
            required = {"open","high","low","close","volume"}
            if not required.issubset(df.columns):
                return None
            df = df.dropna(subset=["open","high","low","close"]).sort_index()
            return df if len(df) >= 25 else None
        except Exception as e:
            logger.warning(f"[{symbol}] {e}")
            return None

    def fetch_all(self, symbols=None):
        symbols = symbols or NSE_SYMBOLS
        dataset = {}
        total   = len(symbols)
        print(f"\nFetching data for {total} NSE stocks from TradingView...")
        for i, symbol in enumerate(symbols, 1):
            df = self.fetch_symbol(symbol)
            if df is not None:
                dataset[symbol] = df
            if i % 20 == 0 or i == total:
                print(f"  {i}/{total} fetched — {len(dataset)} valid so far")
            time.sleep(self.delay)
        print(f"Done: {len(dataset)}/{total} stocks loaded.\n")
        return dataset
