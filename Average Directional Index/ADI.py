#Average Directional Index

import requests
import pandas as pd

# Binance API URLs
BINANCE_SPOT_URL = "https://api.binance.com/api/v3"
BINANCE_FUTURES_URL = "https://fapi.binance.com/fapi/v1"

# Binance-supported timeframes
VALID_TIMEFRAMES = {
    "minutes": ["1m", "3m", "5m", "15m", "30m"],
    "hours": ["1h", "2h", "4h", "6h", "8h", "12h"],
    "days": ["1d", "3d"],
    "weeks": ["1w"],
    "months": ["1M"]
}


# Fetch current price
def get_current_price(symbol, market_type):
    base_url = BINANCE_FUTURES_URL if market_type == "futures" else BINANCE_SPOT_URL
    url = f"{base_url}/ticker/price?symbol={symbol.upper()}"
    response = requests.get(url).json()

    if "price" in response:
        return float(response["price"])
    else:
        raise ValueError(f"Error fetching price: {response}")


# Fetch OHLC data
def fetch_ohlc_data(symbol, interval, market_type, limit=200):
    base_url = BINANCE_FUTURES_URL if market_type == "futures" else BINANCE_SPOT_URL
    url = f"{base_url}/klines?symbol={symbol.upper()}&interval={interval}&limit={limit}"
    response = requests.get(url).json()

    if isinstance(response, dict) and "code" in response:
        raise ValueError(f"Error fetching OHLC data: {response['msg']}")

    df = pd.DataFrame(response, columns=[
        "timestamp", "open", "high", "low", "close", "volume", "close_time",
        "quote_asset_volume", "trades", "taker_buy_base_asset_volume",
        "taker_buy_quote_asset_volume", "ignore"
    ])

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


# Analyze trade and give a clear "YES" or "NO" verdict
def analyze_trade(symbol, trade_type, interval, market_type):
    try:
        current_price = get_current_price(symbol, market_type)
        print(f"\n📢 Market: {market_type.upper()} | Coin: {symbol.upper()}")
        print(f"📌 Current Price: ${current_price:.2f}")

        df = fetch_ohlc_data(symbol, interval, market_type)
        df["ADX"] = calculate_adx(df)

        latest_adx = df["ADX"].iloc[-1]
        print(f"\n📊 ADX Analysis for {symbol.upper()} on {interval}:")
        print(f"🔹 ADX Value: {latest_adx:.2f}")

        # Trend Strength
        trend_strength = "Weak" if latest_adx < 20 else "Moderate" if latest_adx < 25 else "Strong"
        print(f"💡 Trend Strength: {trend_strength}")

        # Trade Verdict
        print("\n💡 Trade Verdict:")
        if trade_type.lower() == "long":
            if latest_adx > 25:
                print("✅ YES - Safe to Long (Strong Trend Detected)")
            else:
                print("❌ NO - Risky to Long (Weak or Sideways Market)")
        elif trade_type.lower() == "short":
            if latest_adx > 25:
                print("✅ YES - Safe to Short (Strong Trend Detected)")
            else:
                print("❌ NO - Risky to Short (Weak or Sideways Market)")
        else:
            print("❌ Invalid trade type. Please enter 'long' or 'short'.")

    except Exception as e:
        print(f"❌ Error: {e}")


# Get user inputs
market_type = input("Choose Market Type (spot/futures): ").strip().lower()
if market_type not in ["spot", "futures"]:
    print("❌ Invalid market type. Choose 'spot' or 'futures'.")
    exit()

symbol = input("Enter Crypto Pair (e.g., BTCUSDT): ").strip()
trade_type = input("Enter Trade Type (Long/Short): ").strip().lower()

# Timeframe Selection
time_unit = input("Choose Timeframe Unit (Minutes, Hours, Days): ").strip().lower()

if time_unit not in VALID_TIMEFRAMES:
    print("❌ Invalid timeframe unit. Choose Minutes, Hours, or Days.")
    exit()

time_value = input(f"Enter number of {time_unit} (e.g., 5 for 5 {time_unit}): ").strip()

try:
    time_value = int(time_value)
except ValueError:
    print("❌ Invalid number. Please enter a valid integer.")
    exit()

# Convert timeframe to Binance format
interval = f"{time_value}{time_unit[0]}"  # e.g., 5m for 5 minutes, 4h for 4 hours, 1d for 1 day

# Check if timeframe is valid
if interval not in VALID_TIMEFRAMES[time_unit]:
    print(f"❌ {interval} is not a valid timeframe for {time_unit}. Supported: {', '.join(VALID_TIMEFRAMES[time_unit])}")
    exit()

# Run Analysis
analyze_trade(symbol, trade_type, interval, market_type)
