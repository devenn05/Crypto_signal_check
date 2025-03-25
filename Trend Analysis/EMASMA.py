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


# Calculate EMA
def calculate_ema(df, period=50):
    return df["close"].ewm(span=period, adjust=False).mean()


# Analyze Trend & Determine Trade Safety
def analyze_trade(symbol, trade_type, interval):
    df = fetch_binance_ohlc(symbol, interval)
    df["EMA_50"] = calculate_ema(df, 50)
    df["EMA_200"] = calculate_ema(df, 200)

    latest_close = df["close"].iloc[-1]
    ema_50 = df["EMA_50"].iloc[-1]
    ema_200 = df["EMA_200"].iloc[-1]

    print(f"\n📊 Trend Analysis for {symbol.upper()} on {interval}:")
    if latest_close > ema_200:
        print("✅ Price is above the 200 EMA → Long-term uptrend.")
    else:
        print("⚠️ Price is below the 200 EMA → Long-term downtrend.")

    if ema_50 > ema_200:
        print("🔥 50 EMA is above 200 EMA → Golden Cross (Bullish).")
    elif ema_50 < ema_200:
        print("⚠️ 50 EMA is below 200 EMA → Death Cross (Bearish).")

    # Decision Making Based on Trade Type
    print("\n💡 Trade Recommendation:")
    if trade_type.lower() == "long":
        if latest_close > ema_200 and ema_50 > ema_200:
            print("✅ Safe Bet: The trend supports a LONG position.")
        else:
            print("⚠️ Risky Bet: The trend does NOT support a LONG position.")
    elif trade_type.lower() == "short":
        if latest_close < ema_200 and ema_50 < ema_200:
            print("✅ Safe Bet: The trend supports a SHORT position.")
        else:
            print("⚠️ Risky Bet: The trend does NOT support a SHORT position.")
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
