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
def analyze_trade(symbol, trade_type, interval):
    current_price = get_current_price(symbol)
    print(f"\n📢 Current Price of {symbol.upper()}: ${current_price:.2f}")

    fear_greed_value, classification = get_fear_greed_index()
    print(f"\n📊 Fear & Greed Index: {fear_greed_value} ({classification})")

    # Trade Decision Based on New Interpretation
    print("\n💡 Trade Recommendation:")
    if fear_greed_value <= 25:
        print("✅ Extreme Fear: Possible BUY opportunity (Long recommended).")
    elif fear_greed_value >= 75:
        print("⚠️ Extreme Greed: Possible SELL signal (Short recommended).")
    else:
        print("🔶 Neutral Market: Proceed with caution.")

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
