import os, sys, logging
from datetime import datetime
from pathlib import Path
import pandas as pd

def setup_logging():
    Path("logs").mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(message)s",
        handlers=[
            logging.FileHandler(f"logs/scanner_{datetime.now():%Y%m%d}.log"),
            logging.StreamHandler(sys.stdout),
        ]
    )

def send_telegram(message):
    import requests
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat  = os.environ.get("TELEGRAM_CHAT_ID", "")
    if not token or not chat:
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat, "text": message},
            timeout=10
        )
        print("  Telegram alert sent ✅")
    except Exception as e:
        print(f"  Telegram failed: {e}")

def format_telegram_message(signals):
    if not signals:
        return "📭 NSE Scanner: No EMA20 breakout signals today."
    
    date_str = datetime.now().strftime("%d %b %Y")
    lines = [f"🚀 NSE BREAKOUT SCANNER — {date_str}", ""]
    
    for i, s in enumerate(signals, 1):
        lines.append(
            f"#{i} {s['symbol']}\n"
            f"   💰 ₹{s['price']}  |  EMA20: ₹{s['ema20']}\n"
            f"   📈 Break: +{s['ema_break_pct']}%\n"
            f"   🔥 Vol Ratio: {s['vol_ratio']}×  (today vs yesterday)\n"
            f"   📊 RSI: {s['rsi14']}"
        )
        lines.append("")
    
    lines.append("✅ All passed: Close > EMA20 | Today Vol > Yest Vol | Green candle")
    return "\n".join(lines)

def run_scan():
    setup_logging()
    from config import NSE_SYMBOLS, OUTPUT_DIR
    from data_fetcher import DataFetcher
    from scanner import BreakoutScanner

    print("=" * 65)
    print(f"  NSE BREAKOUT SCANNER  |  {datetime.now():%d %b %Y %H:%M IST}")
    print(f"  Close > EMA20 (prev)  |  Today Vol > Yesterday Vol")
    print("=" * 65)

    fetcher  = DataFetcher(delay=0.4)
    dataset  = fetcher.fetch_all(NSE_SYMBOLS)

    scanner  = BreakoutScanner()
    signals  = scanner.scan(dataset)
    df       = scanner.to_dataframe(signals)

    print("\n" + "=" * 65)
    if df.empty:
        print("  No EMA20 breakout signals found today.")
        print("  (Normal on flat/bearish days — scanner is working correctly)")
    else:
        print(f"  BREAKOUT SIGNALS FOUND: {len(signals)}")
        print("=" * 65)
        print(df.to_string(index=False))

        Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
        ts      = datetime.now().strftime("%Y%m%d_%H%M%S")
        csvpath = f"{OUTPUT_DIR}/breakout_{ts}.csv"
        df.to_csv(csvpath, index=False)
        print(f"\n  Saved: {csvpath}")

    print("=" * 65)

    # Send to Telegram (works both locally and in GitHub Actions)
    msg = format_telegram_message(signals)
    send_telegram(msg)

    return signals

if __name__ == "__main__":
    run_scan()
