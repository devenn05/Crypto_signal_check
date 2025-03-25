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
    index_value = response["data"][0]["value"]
    index_classification = response["data"][0]["value_classification"]
    return int(index_value), index_classification

# Analyze trade based on Fear & Greed Index
def analyze_trade(symbol, trade_type, interval):
    current_price = get_current_price(symbol)
    print(f"\n📢 Current Price of {symbol.upper()}: ${current_price:.2f}")

    fear_greed_value, classification = get_fear_greed_index()
    print(f"\n📊 Fear & Greed Index: {fear_greed_value} ({classification})")

    # Trade Decision
    print("\n💡 Trade Recommendation:")
    if trade_type.lower() == "long":
        if fear_greed_value < 30:
            print("✅ Safe Bet: Market is fearful, potential buying opportunity.")
        else:
            print("⚠️ Risky Bet: Market is greedy, possible overbought conditions.")
    elif trade_type.lower() == "short":
        if fear_greed_value > 70:
            print("✅ Safe Bet: Market is greedy, possible shorting opportunity.")
        else:
            print("⚠️ Risky Bet: Market is fearful, not ideal for shorting.")
    else:
        print("❌ Invalid trade type. Please enter 'long' or 'short'.")

# Get User Inputs
symbol = input("Enter Crypto Pair (e.g., BTCUSDT): ").strip()
trade_type = input("Enter Trade Type (Long/Short): ").strip()

# Timeframe Selection
time_unit = input("Choose Timeframe Unit (Minutes, Hours, Days): ").strip().lower()

if time_unit not in VALID_TIMEFRAMES:
    print("❌ Invalid timeframe unit. Please enter Minutes, Hours, or Days.")
    exit()

time_value = input(f"Enter number of {time_unit} (e.g., 5 for 5 {time_unit}): ").strip()

try:
    time_value = int(time_value)
except ValueError:
    print("❌ Invalid number. Please enter a valid integer.")
    exit()

# Match user input with Binance-supported intervals
interval = f"{time_value}{time_unit[0]}"  # e.g., 5m for 5 minutes, 4h for 4 hours, 1d for 1 day

# Check if the selected timeframe is valid
if interval not in VALID_TIMEFRAMES[time_unit]:
    print(f"❌ {interval} is not a valid timeframe for {time_unit}. Supported: {', '.join(VALID_TIMEFRAMES[time_unit])}")
    exit()

# Run Analysis
analyze_trade(symbol, trade_type, interval)
