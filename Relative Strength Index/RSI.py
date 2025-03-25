import requests
import pandas as pd

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


# Fetch OHLC data from Binance API
def fetch_binance_ohlc(symbol, interval, limit=200):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol.upper()}&interval={interval}&limit={limit}"
    response = requests.get(url)
    data = response.json()

    # Convert to DataFrame
    df = pd.DataFrame(data, columns=[
        "timestamp", "open", "high", "low", "close", "volume", "close_time",
        "quote_asset_volume", "trades", "taker_buy_base_asset_volume",
        "taker_buy_quote_asset_volume", "ignore"
    ])

    # Convert necessary columns to numeric
    df["close"] = pd.to_numeric(df["close"])

    return df[["timestamp", "close"]]


# Calculate RSI
def calculate_rsi(df, period=14):
    delta = df["close"].diff()

    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

    rs = gain / loss
    df["RSI"] = 100 - (100 / (1 + rs))

    return df["RSI"]


# Analyze Trade & Provide Recommendation
def analyze_trade(symbol, trade_type, interval):
    current_price = get_current_price(symbol)
    print(f"\n📢 Current Price of {symbol.upper()}: ${current_price:.2f}")

    df = fetch_binance_ohlc(symbol, interval)
    df["RSI"] = calculate_rsi(df)

    latest_rsi = df["RSI"].iloc[-1]

    print(f"\n📊 RSI Analysis for {symbol.upper()} on {interval}:")
    print(f"🔹 RSI Value: {latest_rsi:.2f}")

    if latest_rsi > 70:
        print("⚠️ Overbought: Possible pullback expected.")
    elif latest_rsi < 30:
        print("✅ Oversold: Possible bounce expected.")
    else:
        print("🔸 RSI is in a neutral zone.")

    # Trade Decision
    print("\n💡 Trade Recommendation:")
    if trade_type.lower() == "long":
        if latest_rsi < 30:
            print("✅ Safe Bet: RSI indicates oversold, possible upside.")
        else:
            print("⚠️ Risky Bet: RSI is high, market may pull back.")
    elif trade_type.lower() == "short":
        if latest_rsi > 70:
            print("✅ Safe Bet: RSI indicates overbought, possible downside.")
        else:
            print("⚠️ Risky Bet: RSI is low, market may bounce.")
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
