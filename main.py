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
        print("  No Telegram credentials — skipping")
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

def format_telegram_message(signals, total_scanned):
    date_str = datetime.now().strftime("%d %b %Y %H:%M IST")

    bullish  = [s for s in signals if "BULLISH" in s["direction"]]
    bearish  = [s for s in signals if "BEARISH" in s["direction"]]

    lines = []
    lines.append(f"🚀 NSE EMA20 SCANNER")
    lines.append(f"📅 {date_str}")
    lines.append(f"📊 Scanned: {total_scanned} stocks")
    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━")

    # Bullish section
    if bullish:
        lines.append(f"🟢 BREAKOUT ABOVE EMA20 ({len(bullish)})")
        lines.append("")
        for i, s in enumerate(bullish, 1):
            lines.append(
                f"#{i} {s['symbol']}\n"
                f"   💰 ₹{s['price']}  |  EMA20: ₹{s['ema20']}\n"
                f"   📈 Above EMA by: {s['ema_break_pct']}\n"
                f"   🔥 Vol Ratio: {s['vol_ratio']}×  |  RSI: {s['rsi14']}"
            )
            lines.append("")
    else:
        lines.append("🟢 BREAKOUT ABOVE EMA20: None today")
        lines.append("")

    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━")

    # Bearish section
    if bearish:
        lines.append(f"🔴 BREAKDOWN BELOW EMA20 ({len(bearish)})")
        lines.append("")
        for i, s in enumerate(bearish, 1):
            lines.append(
                f"#{i} {s['symbol']}\n"
                f"   💰 ₹{s['price']}  |  EMA20: ₹{s['ema20']}\n"
                f"   📉 Below EMA by: {s['ema_break_pct']}\n"
                f"   🔥 Vol Ratio: {s['vol_ratio']}×  |  RSI: {s['rsi14']}"
            )
            lines.append("")
    else:
        lines.append("🔴 BREAKDOWN BELOW EMA20: None today")
        lines.append("")

    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append("✅ Conditions (both): Fresh EMA20 cross | Today vol > Yest vol | Candle confirms direction")

    return "\n".join(lines)

def run_scan():
    setup_logging()
    from config import NSE_SYMBOLS, OUTPUT_DIR
    from data_fetcher import DataFetcher
    from scanner import BreakoutScanner

    print("=" * 65)
    print(f"  NSE EMA20 SCANNER  |  {datetime.now():%d %b %Y %H:%M IST}")
    print(f"  🟢 Breakout Above EMA20  |  🔴 Breakdown Below EMA20")
    print("=" * 65)

    fetcher  = DataFetcher(delay=0.4)
    dataset  = fetcher.fetch_all(NSE_SYMBOLS)

    scanner  = BreakoutScanner()
    signals  = scanner.scan(dataset)
    df_out   = scanner.to_dataframe(signals)

    bullish  = [s for s in signals if "BULLISH" in s["direction"]]
    bearish  = [s for s in signals if "BEARISH" in s["direction"]]

    print("\n" + "=" * 65)
    print(f"  🟢 BULLISH BREAKOUTS: {len(bullish)}  |  🔴 BEARISH BREAKDOWNS: {len(bearish)}")
    print("=" * 65)

    if df_out.empty:
        print("\n  No signals found today.")
    else:
        print(df_out.to_string(index=False))
        Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
        ts      = datetime.now().strftime("%Y%m%d_%H%M%S")
        csvpath = f"{OUTPUT_DIR}/signals_{ts}.csv"
        df_out.to_csv(csvpath, index=False)
        print(f"\n  Saved: {csvpath}")

    print("=" * 65)

    msg = format_telegram_message(signals, len(dataset))
    print("\n--- TELEGRAM PREVIEW ---")
    print(msg)
    print("------------------------\n")
    send_telegram(msg)
    return signals

if __name__ == "__main__":
    run_scan()
