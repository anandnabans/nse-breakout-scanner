import logging
from typing import Optional
import numpy as np
import pandas as pd
from config import VOLUME_AVG_PERIOD, MIN_PRICE, MIN_AVG_VOLUME, TOP_N_RESULTS

logger = logging.getLogger(__name__)

def calc_ema(series, period):
    return series.ewm(span=period, adjust=False).mean()

def calc_rsi(series, period=14):
    delta    = series.diff()
    gain     = delta.clip(lower=0)
    loss     = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, adjust=False).mean()
    rs       = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))

def enrich(df):
    df = df.copy()
    df["ema20"]      = calc_ema(df["close"], 20)
    df["avg_vol_20"] = df["volume"].rolling(20).mean().shift(1)
    df["prev_vol"]   = df["volume"].shift(1)
    df["body_ratio"] = (df["close"] - df["open"]).abs() / (df["high"] - df["low"]).replace(0, np.nan)
    df["rsi14"]      = calc_rsi(df["close"], 14)
    return df

def evaluate_signal(symbol, df):
    if len(df) < 25:
        return None
    df   = enrich(df)
    curr = df.iloc[-1]
    prev = df.iloc[-2]
    for val in [curr["close"], curr["open"], curr["volume"],
                curr["ema20"], prev["ema20"], prev["close"],
                curr["avg_vol_20"], curr["prev_vol"]]:
        if pd.isna(val):
            return None
    if curr["close"] < MIN_PRICE:
        return None
    if curr["avg_vol_20"] < MIN_AVG_VOLUME:
        return None
    # CORE: yesterday below EMA, today above yesterday's EMA
    ema_level   = prev["ema20"]
    was_below   = prev["close"] <= ema_level
    broke_above = curr["close"] >  ema_level
    if not (was_below and broke_above):
        return None
    # Today volume > yesterday volume
    if curr["volume"] <= curr["prev_vol"]:
        return None
    # Green candle
    if curr["close"] <= curr["open"]:
        return None

    vol_ratio     = curr["volume"] / curr["prev_vol"]
    ema_break_pct = ((curr["close"] - ema_level) / ema_level) * 100
    body          = curr["body_ratio"] if not pd.isna(curr["body_ratio"]) else 0
    rank_score    = (vol_ratio * 0.5) + (ema_break_pct * 0.3) + (body * 0.2)

    return {
        "symbol":        symbol,
        "price":         round(curr["close"], 2),
        "ema20":         round(ema_level, 2),
        "ema_break_pct": round(ema_break_pct, 2),
        "volume":        int(curr["volume"]),
        "prev_volume":   int(curr["prev_vol"]),
        "vol_ratio":     round(vol_ratio, 2),
        "avg_vol_20":    int(curr["avg_vol_20"]),
        "body_ratio":    round(body * 100, 1),
        "rsi14":         round(curr["rsi14"], 1),
        "breakout":      "YES",
        "rank_score":    round(rank_score, 4),
    }

class BreakoutScanner:
    def scan(self, dataset):
        signals = []
        for symbol, df in dataset.items():
            try:
                result = evaluate_signal(symbol, df)
                if result:
                    signals.append(result)
            except Exception as e:
                logger.warning(f"{symbol}: {e}")
        signals.sort(key=lambda x: x["rank_score"], reverse=True)
        return signals[:TOP_N_RESULTS]

    def to_dataframe(self, signals):
        if not signals:
            return pd.DataFrame()
        df   = pd.DataFrame(signals)
        cols = ["symbol","price","ema20","ema_break_pct","volume","prev_volume","vol_ratio","avg_vol_20","body_ratio","rsi14","breakout","rank_score"]
        return df[[c for c in cols if c in df.columns]].reset_index(drop=True)
