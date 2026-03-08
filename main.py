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
        print("  No Telegram credentials — skipping alert")
        return
    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat, "text": message},
            timeout=10
        )
        if resp.status_code == 200:
            print("  Telegram alert sent ✅")
        else:
            print(f"  Telegram failed: {resp.text}")
    except Exception as e:
        print(f"  Telegram error: {e}")

def format_telegram_message(signals, total_scanned, above_ema_list):
    date_str  = datetime.now().strftime("%d %b %Y %H:%M IST")
    lines     = []

    lines.append(f"🚀 NSE BREAKOUT SCANNER")
    lines.append(f"📅 {date_str}")
    lines.append(f"📊 Scanned: {total_scanned} stocks")
    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━")

    if signals:
        lines.append(f"✅ BREAKOUT SIGNALS: {len(signals)}")
        lines.append("")
        for i, s in enumerate(signals, 1):
            lines.append(
                f"#{i} {s['symbol']}\n"
                f"   💰 ₹{s['price']}  |  EMA20: ₹{s['ema20']}\n"
                f"   📈 Break: +{s['ema_break_pct']}%\n"
                f"   🔥 Vol Ratio: {s['vol_ratio']}×\n"
                f"   📉 RSI: {s['rsi14']}"
            )
            lines.append("")
    else:
        lines.append("❌ No genuine EMA20 breakouts today")
        lines.append("")
        if above_ema_list:
            lines.append(f"📈 Stocks above EMA20 ({len(above_ema_list)}):")
            lines.append(", ".join(above_ema_list[:10]))
            if len(above_ema_list) > 10:
                lines.append(f"...and {len(above_ema_list)-10} more")

    lines.append("")
    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append("Conditions: Close>EMA20 | Was below EMA yesterday | Green candle | Today vol > Yest vol")
    return "\n".join(lines)

def run_scan():
    setup_logging()
    from config import NSE_SYMBOLS, OUTPUT_DIR
    from data_fetcher import DataFetcher
    from scanner import BreakoutScanner
    from tvDatafeed import TvDatafeed, Interval

    print("=" * 65)
    print(f"  NSE BREAKOUT SCANNER  |  {datetime.now():%d %b %Y %H:%M IST}")
    print(f"  Close > EMA20 (prev)  |  Today Vol > Yesterday Vol")
    print("=" * 65)

    fetcher  = DataFetcher(delay=0.4)
    dataset  = fetcher.fetch_all(NSE_SYMBOLS)

    # Track stocks above EMA for Telegram summary
    above_ema_list = []
    for symbol, df in dataset.items():
        try:
            df2 = df.copy()
            df2['ema20'] = df2['close'].ewm(span=20, adjust=False).mean()
            curr = df2.iloc[-1]
            prev = df2.iloc[-2]
            if curr['close'] > prev['ema20']:
                above_ema_list.append(symbol)
        except:
            pass

    scanner  = BreakoutScanner()
    signals  = scanner.scan(dataset)
    df_out   = scanner.to_dataframe(signals)

    print("\n" + "=" * 65)
    print(f"  Stocks above EMA20: {len(above_ema_list)} → {', '.join(above_ema_list)}")
    print("=" * 65)

    if df_out.empty:
        print("\n  No genuine EMA20 breakout signals found today.")
        print("  (Needs: fresh crossover + vol up + green candle)")
    else:
        print(f"\n  BREAKOUT SIGNALS FOUND: {len(signals)}")
        print("=" * 65)
        print(df_out.to_string(index=False))
        Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
        ts      = datetime.now().strftime("%Y%m%d_%H%M%S")
        csvpath = f"{OUTPUT_DIR}/breakout_{ts}.csv"
        df_out.to_csv(csvpath, index=False)
        print(f"\n  Saved: {csvpath}")

    print("=" * 65)

    msg = format_telegram_message(signals, len(dataset), above_ema_list)
    print("\n--- TELEGRAM MESSAGE PREVIEW ---")
    print(msg)
    print("--------------------------------\n")
    send_telegram(msg)
    return signals

if __name__ == "__main__":
    run_scan()
