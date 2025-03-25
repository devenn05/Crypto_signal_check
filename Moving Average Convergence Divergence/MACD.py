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
def fetch_binance_ohlc(symbol, interval, limit=100):
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


# Calculate MACD
def calculate_macd(df, short_window=12, long_window=26, signal_window=9):
    df["EMA12"] = df["close"].ewm(span=short_window, adjust=False).mean()
    df["EMA26"] = df["close"].ewm(span=long_window, adjust=False).mean()

    df["MACD"] = df["EMA12"] - df["EMA26"]
    df["Signal_Line"] = df["MACD"].ewm(span=signal_window, adjust=False).mean()

    return df["MACD"], df["Signal_Line"]


# Analyze Trade & Provide Recommendation
def analyze_trade(symbol, trade_type, interval):
    current_price = get_current_price(symbol)
    print(f"\n📢 Current Price of {symbol.upper()}: ${current_price:.2f}")

    df = fetch_binance_ohlc(symbol, interval)
    df["MACD"], df["Signal_Line"] = calculate_macd(df)

    latest_macd = df["MACD"].iloc[-1]
    latest_signal = df["Signal_Line"].iloc[-1]

    print(f"\n📊 MACD Analysis for {symbol.upper()} on {interval}:")
    print(f"🔹 MACD: {latest_macd:.5f}")
    print(f"🔹 Signal Line: {latest_signal:.5f}")

    if latest_macd > latest_signal:
        print("✅ Bullish Momentum: MACD is above Signal Line.")
    elif latest_macd < latest_signal:
        print("⚠️ Bearish Momentum: MACD is below Signal Line.")
    else:
        print("🔸 MACD and Signal Line are equal. No strong trend.")

    # Trade Decision
    print("\n💡 Trade Recommendation:")
    if trade_type.lower() == "long":
        if latest_macd > latest_signal:
            print("✅ Safe Bet: MACD indicates bullish momentum.")
        else:
            print("⚠️ Risky Bet: MACD is below Signal Line, possible downtrend.")
    elif trade_type.lower() == "short":
        if latest_macd < latest_signal:
            print("✅ Safe Bet: MACD indicates bearish momentum.")
        else:
            print("⚠️ Risky Bet: MACD is above Signal Line, possible uptrend.")
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
