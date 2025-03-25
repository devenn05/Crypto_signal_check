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
    df["high"] = pd.to_numeric(df["high"])
    df["low"] = pd.to_numeric(df["low"])
    df["close"] = pd.to_numeric(df["close"])

    return df[["timestamp", "high", "low", "close"]]


# Calculate ADX
def calculate_adx(df, period=14):
    df["+DM"] = df["high"].diff()
    df["-DM"] = df["low"].diff()

    df["+DM"] = df["+DM"].where((df["+DM"] > df["-DM"]) & (df["+DM"] > 0), 0)
    df["-DM"] = df["-DM"].where((df["-DM"] > df["+DM"]) & (df["-DM"] > 0), 0)

    tr1 = df["high"] - df["low"]
    tr2 = abs(df["high"] - df["close"].shift(1))
    tr3 = abs(df["low"] - df["close"].shift(1))
    df["TR"] = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    df["+DI"] = 100 * (df["+DM"].rolling(period).sum() / df["TR"].rolling(period).sum())
    df["-DI"] = 100 * (df["-DM"].rolling(period).sum() / df["TR"].rolling(period).sum())

    df["DX"] = 100 * abs(df["+DI"] - df["-DI"]) / (df["+DI"] + df["-DI"])
    df["ADX"] = df["DX"].rolling(period).mean()

    return df["ADX"]


# Analyze Trade & Provide Recommendation
def analyze_trade(symbol, trade_type, interval):
    current_price = get_current_price(symbol)
    print(f"\n📢 Current Price of {symbol.upper()}: ${current_price:.2f}")

    df = fetch_binance_ohlc(symbol, interval)
    df["ADX"] = calculate_adx(df)

    latest_adx = df["ADX"].iloc[-1]

    print(f"\n📊 ADX Analysis for {symbol.upper()} on {interval}:")
    print(f"🔹 ADX Value: {latest_adx:.2f}")

    if latest_adx > 25:
        print("✅ Strong Trend Detected")
    elif latest_adx < 20:
        print("⚠️ Weak Trend - Market is Sideways")
    else:
        print("🔸 Moderate Trend Strength")

    # Trade Decision
    print("\n💡 Trade Recommendation:")
    if trade_type.lower() == "long":
        if latest_adx > 25:
            print("✅ Safe Bet: Strong trend supports a LONG trade.")
        else:
            print("⚠️ Risky Bet: Weak trend, market may be ranging.")
    elif trade_type.lower() == "short":
        if latest_adx > 25:
            print("✅ Safe Bet: Strong trend supports a SHORT trade.")
        else:
            print("⚠️ Risky Bet: Weak trend, market may be ranging.")
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
