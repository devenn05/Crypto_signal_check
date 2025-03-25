import requests

# Binance API-supported timeframes
VALID_TIMEFRAMES = {
    "minutes": ["1m", "3m", "5m", "15m", "30m"],
    "hours": ["1h", "2h", "4h", "6h", "8h", "12h"],
    "days": ["1d", "3d"],
    "weeks": ["1w"],
    "months": ["1M"]
}

# Fetch current price from Binance API
def get_current_price(symbol):
    url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol.upper()}"
    response = requests.get(url).json()
    return float(response["price"])

# Fetch Fear & Greed Index
def get_fear_greed_index():
    url = "https://api.alternative.me/fng/"
    response = requests.get(url).json()
    index_value = int(response["data"][0]["value"])
    classification = response["data"][0]["value_classification"]
    return index_value, classification

# Analyze trade based on Fear & Greed Index
def analyze_trade(symbol, trade_type):
    current_price = get_current_price(symbol)
    fear_greed_value, classification = get_fear_greed_index()

    print(f"\n📢 Current Price of {symbol.upper()}: ${current_price:.2f}")
    print(f"📊 Fear & Greed Index: {fear_greed_value} ({classification})")

    # Trade Decision Based on Index
    if fear_greed_value <= 25:
        sentiment = "🟢 Extreme Fear → Potential Buy Zone"
        verdict = "✅ YES - Safe to Long" if trade_type == "long" else "❌ NO - Risky to Short"
    elif fear_greed_value >= 75:
        sentiment = "🔴 Extreme Greed → Potential Sell Zone"
        verdict = "✅ YES - Safe to Short" if trade_type == "short" else "❌ NO - Risky to Long"
    else:
        sentiment = "🟡 Neutral Market → Proceed with Caution"
        verdict = "⚠️ No Strong Signal - Trade Carefully"

    # Print Final Analysis
    print(f"\n💡 Market Sentiment: {sentiment}")
    print(f"📌 Trade Verdict: {verdict}")

# Get User Inputs
symbol = input("Enter Crypto Pair (e.g., BTCUSDT): ").strip()
trade_type = input("Enter Trade Type (Long/Short): ").strip().lower()

# Run Analysis
analyze_trade(symbol, trade_type)
