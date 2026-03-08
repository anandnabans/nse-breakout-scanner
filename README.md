# 🚀 NSE Breakout Scanner

Scans all NSE stocks daily for **EMA20 breakouts with volume confirmation**.

## Signal Conditions
| # | Condition | Logic |
|---|-----------|-------|
| 1 | EMA20 Breakout | Yesterday close ≤ EMA20 **AND** Today close > EMA20 |
| 2 | Volume Up | Today volume > Yesterday volume |
| 3 | Green Candle | Today close > Today open |
| 4 | Liquidity | Price > ₹100 AND Avg Vol 20d > 500K |

## Auto Schedule
Runs every **weekday at 3:15 PM IST** via GitHub Actions.
Results sent to **Telegram**.

## Setup Telegram Alerts
Add these secrets in GitHub → Settings → Secrets → Actions:
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

## Run Manually
```bash
python3 main.py
```
Or trigger from GitHub Actions → Run workflow button.
