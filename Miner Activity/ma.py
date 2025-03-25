import requests

def get_binance_price(symbol):
    url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol.upper()}"
    response = requests.get(url).json()
    return float(response["price"])

def get_exchange_netflow(symbol):
    """ Simulates miner activity using exchange netflow as a proxy. """
    # In real-world, we would need data from CryptoQuant or Glassnode
    # But here we simulate miner behavior with a random function for demo
    import random
    netflow = random.uniform(-1000, 1000)  # Simulated inflow/outflow in BTC
    return netflow

# Ask user for input
symbol = input("Enter coin symbol (e.g., BTCUSDT): ").upper()
trade_side = input("Is this a long or short trade? (long/short): ").strip().lower()

time_type = input("Select timeframe type: minutes, hours, or days? ").strip().lower()
time_value = int(input(f"How many {time_type}? ").strip())

# Fetch current price
current_price = get_binance_price(symbol)
print(f"\n📌 Current {symbol} Price: ${current_price}")

# Get miner activity (simulated using netflow)
netflow = get_exchange_netflow(symbol)

# Determine miner sentiment
if netflow < 0:
    miner_sentiment = "Bullish (Miners are holding)"
    trade_safe = "✅ Safe to go long" if trade_side == "long" else "⚠️ Risky for short"
else:
    miner_sentiment = "Bearish (Miners are selling)"
    trade_safe = "✅ Safe to go short" if trade_side == "short" else "⚠️ Risky for long"

# Output result
print(f"\n📊 Miner Activity Analysis for {symbol} ({time_value} {time_type} timeframe)")
print(f"🔹 Miner Sentiment: {miner_sentiment}")
print(f"💡 Trade Advice: {trade_safe}")
