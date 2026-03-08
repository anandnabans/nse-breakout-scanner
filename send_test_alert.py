import requests, os

token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
chat  = os.environ.get("TELEGRAM_CHAT_ID", "")

# Read from config if env not set
if not token:
    import subprocess
    result = subprocess.run(['gh','secret','list','--repo','anandnabans/nse-breakout-scanner'], capture_output=True, text=True)
    print("Secrets:", result.stdout)

msg = """
📊 NSE SCANNER — Thursday 05 Mar 2026
(Friday Mar 6 data pending — market data 1-day lag in guest mode)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📈 STOCKS ABOVE EMA20 (16 stocks)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ RELIANCE   ₹1404.80  EMA: ₹1404.33  ← Fresh crossover + Green
✅ DMART      ₹3875.80  EMA: ₹3837.15  ← Fresh crossover + Green

⚡ Also above EMA (already were above, not fresh):
TITAN, SUNPHARMA, DIVISLAB, HINDALCO
DRREDDY, COALINDIA, APOLLOHOSP
ZYDUSLIFE, POLYCAB, PFC, BEL
TATAPOWER, CGPOWER, ASTRAL

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
❌ GENUINE BREAKOUTS (all 4 conditions): NONE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Conditions: Close > EMA20 | Was below EMA yesterday | Green candle | Today vol > Yesterday vol

⚠️ Friday Mar 6 candle not yet available (need TradingView login)
🕒 Scanner auto-runs every weekday at 3:15 PM IST
"""

if token and chat:
    resp = requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
        json={"chat_id": chat, "text": msg}, timeout=10)
    print("Sent!" if resp.status_code == 200 else f"Failed: {resp.text}")
else:
    print("No token/chat — will send via GitHub Actions")
    print(msg)
