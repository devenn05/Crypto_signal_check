import requests
import random

# Binance API Endpoint
BINANCE_PRICE_API_URL = "https://api.binance.com/api/v3/ticker/price"

def get_binance_price(symbol):
    """Fetch the current market price from Binance."""
    response = requests.get(f"{BINANCE_PRICE_API_URL}?symbol={symbol.upper()}")
    data = response.json()
    return float(data["price"])

def get_exchange_netflow():
    """Simulates miner activity using exchange netflow as a proxy."""
    # Simulated netflow: Negative means outflow (miners holding), Positive means inflow (miners selling)
    return random.uniform(-1000, 1000)

def evaluate_miner_activity(symbol, trade_side, timeframe, time_value):
    """Evaluate trade safety based on simulated miner activity."""
    
    # Fetch current market price
    current_price = get_binance_price(symbol)
    netflow = get_exchange_netflow()  # Simulated netflow

    # Miner Sentiment Analysis
    if netflow < 0:
        miner_sentiment = "✅ Bullish (Miners are holding)"
        safe_long = True
        safe_short = False
    else:
        miner_sentiment = "⚠️ Bearish (Miners are selling)"
        safe_long = False
        safe_short = True

    # Trade Verdict
    if trade_side == "long":
        verdict = "✅ YES - Safe to Long" if safe_long else "❌ NO - Risky to Long"
    elif trade_side == "short":
        verdict = "✅ YES - Safe to Short" if safe_short else "❌ NO - Risky to Short"
    else:
        verdict = "❌ Invalid trade side."

    # Print Results
    print(f"\n📊 Miner Activity Analysis for {symbol} ({time_value} {timeframe} timeframe)")
    print(f"💰 Current Price: ${current_price:.2f}")
    print(f"🔹 Miner Netflow: {netflow:.2f} BTC")
    print(f"📊 Sentiment: {miner_sentiment}")
    print(f"📊 Trade Verdict: {verdict}")

# User Input
symbol = input("Enter Crypto Pair (e.g., BTCUSDT): ").strip().upper()
trade_side = input("Enter Trade Side (long/short): ").strip().lower()

timeframe = input("Select Timeframe Type: minutes, hours, or days? ").strip().lower()
time_value = input(f"How many {timeframe}? ").strip()

# Validate time value
try:
    time_value = int(time_value)
except ValueError:
    print("❌ Invalid input. Please enter a valid number for timeframe.")
    exit()

# Run Analysis
evaluate_miner_activity(symbol, trade_side, timeframe, time_value)
