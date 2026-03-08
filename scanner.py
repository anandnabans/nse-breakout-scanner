"""
scanner.py — NSE Breakout Scanner  [BOTH DIRECTIONS]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BULLISH BREAKOUT (above EMA20):
  ✅ Yesterday close  <=  EMA20  (was at or below the line)
  ✅ Today close       >  EMA20  (crossed above today)
  ✅ Today volume      >  Yesterday volume
  ✅ Green candle     (close > open)
  ✅ Price > 100 and Avg vol > 500K

BEARISH BREAKDOWN (below EMA20):
  ✅ Yesterday close  >=  EMA20  (was at or above the line)
  ✅ Today close       <  EMA20  (crossed below today)
  ✅ Today volume      >  Yesterday volume
  ✅ Red candle       (close < open)
  ✅ Price > 100 and Avg vol > 500K
"""

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
    # .shift(1) = exclude today from average — critical for accurate ratio
    df["avg_vol_20"] = df["volume"].rolling(20).mean().shift(1)
    df["prev_vol"]   = df["volume"].shift(1)
    df["body_ratio"] = (df["close"] - df["open"]).abs() / \
                       (df["high"] - df["low"]).replace(0, np.nan)
    df["rsi14"]      = calc_rsi(df["close"], 14)
    return df


def evaluate_signal(symbol, df):
    """
    Returns a signal dict with direction='BULLISH' or 'BEARISH', else None.
    """
    if len(df) < 25:
        return None

    df   = enrich(df)
    curr = df.iloc[-1]
    prev = df.iloc[-2]

    # NaN guard
    for val in [curr["close"], curr["open"], curr["volume"],
                curr["ema20"], prev["ema20"], prev["close"],
                curr["avg_vol_20"], curr["prev_vol"]]:
        if pd.isna(val):
            return None

    # Liquidity filter
    if curr["close"] < MIN_PRICE:
        return None
    if curr["avg_vol_20"] < MIN_AVG_VOLUME:
        return None

    ema_level = prev["ema20"]   # Yesterday's EMA = the true breakout/breakdown level

    # ── Volume must be higher than yesterday (both directions) ──
    if curr["volume"] <= curr["prev_vol"]:
        return None

    vol_ratio  = round(curr["volume"] / curr["prev_vol"], 2)
    body       = curr["body_ratio"] if not pd.isna(curr["body_ratio"]) else 0

    # ── BULLISH BREAKOUT: crossed above EMA ──────────────────────
    if prev["close"] <= ema_level and curr["close"] > ema_level and curr["close"] > curr["open"]:
        ema_break_pct = round(((curr["close"] - ema_level) / ema_level) * 100, 2)
        rank_score    = round((vol_ratio * 0.5) + (ema_break_pct * 0.3) + (body * 0.2), 4)
        return {
            "symbol":        symbol,
            "direction":     "🟢 BULLISH",
            "price":         round(curr["close"], 2),
            "ema20":         round(ema_level, 2),
            "ema_break_pct": f"+{ema_break_pct}%",
            "volume":        int(curr["volume"]),
            "prev_volume":   int(curr["prev_vol"]),
            "vol_ratio":     vol_ratio,
            "avg_vol_20":    int(curr["avg_vol_20"]),
            "body_ratio":    round(body * 100, 1),
            "rsi14":         round(curr["rsi14"], 1),
            "signal":        "BREAKOUT ABOVE EMA20",
            "rank_score":    rank_score,
        }

    # ── BEARISH BREAKDOWN: crossed below EMA ─────────────────────
    if prev["close"] >= ema_level and curr["close"] < ema_level and curr["close"] < curr["open"]:
        ema_break_pct = round(((ema_level - curr["close"]) / ema_level) * 100, 2)
        rank_score    = round((vol_ratio * 0.5) + (ema_break_pct * 0.3) + (body * 0.2), 4)
        return {
            "symbol":        symbol,
            "direction":     "🔴 BEARISH",
            "price":         round(curr["close"], 2),
            "ema20":         round(ema_level, 2),
            "ema_break_pct": f"-{ema_break_pct}%",
            "volume":        int(curr["volume"]),
            "prev_volume":   int(curr["prev_vol"]),
            "vol_ratio":     vol_ratio,
            "avg_vol_20":    int(curr["avg_vol_20"]),
            "body_ratio":    round(body * 100, 1),
            "rsi14":         round(curr["rsi14"], 1),
            "signal":        "BREAKDOWN BELOW EMA20",
            "rank_score":    rank_score,
        }

    return None


class BreakoutScanner:

    def scan(self, dataset):
        bullish = []
        bearish = []
        logger.info(f"Scanning {len(dataset)} symbols (both directions)...")

        for symbol, df in dataset.items():
            try:
                result = evaluate_signal(symbol, df)
                if result:
                    if "BULLISH" in result["direction"]:
                        bullish.append(result)
                        logger.info(f"  🟢 BULLISH: {symbol:<15} ₹{result['price']} | EMA: ₹{result['ema20']} | Break: {result['ema_break_pct']} | Vol: {result['vol_ratio']}x")
                    else:
                        bearish.append(result)
                        logger.info(f"  🔴 BEARISH: {symbol:<15} ₹{result['price']} | EMA: ₹{result['ema20']} | Break: {result['ema_break_pct']} | Vol: {result['vol_ratio']}x")
            except Exception as e:
                logger.warning(f"  ⚠ {symbol}: {e}")

        # Sort each by rank score
        bullish.sort(key=lambda x: x["rank_score"], reverse=True)
        bearish.sort(key=lambda x: x["rank_score"], reverse=True)

        logger.info(f"\nDone — 🟢 {len(bullish)} Bullish breakouts | 🔴 {len(bearish)} Bearish breakdowns")

        # Return top N from each, bullish first then bearish
        return bullish[:TOP_N_RESULTS] + bearish[:TOP_N_RESULTS]

    def to_dataframe(self, signals):
        if not signals:
            return pd.DataFrame()
        df   = pd.DataFrame(signals)
        cols = ["direction", "symbol", "price", "ema20", "ema_break_pct",
                "volume", "prev_volume", "vol_ratio", "avg_vol_20",
                "body_ratio", "rsi14", "signal", "rank_score"]
        cols = [c for c in cols if c in df.columns]
        return df[cols].reset_index(drop=True)
