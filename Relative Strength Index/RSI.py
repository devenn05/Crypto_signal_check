import requests
import pandas as pd

# Binance API Endpoints
BINANCE_SPOT_API_URL = "https://api.binance.com/api/v3/klines"
BINANCE_FUTURES_API_URL = "https://fapi.binance.com/fapi/v1/klines"
BINANCE_PRICE_API_URL = "https://api.binance.com/api/v3/ticker/price"

# Binance Supported Timeframes
VALID_TIMEFRAMES = {
    "minutes": ["1m", "3m", "5m", "15m", "30m"],
    "hours": ["1h", "2h", "4h", "6h", "8h", "12h"],
    "days": ["1d", "3d"],
    "weeks": ["1w"],
    "months": ["1M"]
}

def get_current_price(symbol):
    """Fetch current price from Binance"""
    response = requests.get(f"{BINANCE_PRICE_API_URL}?symbol={symbol.upper()}")
    data = response.json()
    return float(data["price"])

def fetch_binance_ohlc(symbol, interval, market_type, limit=200):
    """Fetch historical OHLC data from Binance Spot or Futures market"""
    api_url = BINANCE_FUTURES_API_URL if market_type == "futures" else BINANCE_SPOT_API_URL

    params = {"symbol": symbol.upper(), "interval": interval, "limit": limit}
    response = requests.get(api_url, params=params)
    data = response.json()

    if "code" in data:
        raise Exception(f"Error fetching data: {data['msg']}")

    # Convert data to DataFrame
    df = pd.DataFrame(data, columns=[
        "timestamp", "open", "high", "low", "close", "volume", "close_time",
        "quote_asset_volume", "trades", "taker_buy_base_asset_volume",
        "taker_buy_quote_asset_volume", "ignore"
    ])

    df["close"] = pd.to_numeric(df["close"])
    return df[["timestamp", "close"]]

def calculate_rsi(df, period=14):
    """Calculate Relative Strength Index (RSI)"""
    delta = df["close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

    rs = gain / loss
    df["RSI"] = 100 - (100 / (1 + rs))
    return df["RSI"]

def evaluate_trade(symbol, market_type, trade_side, time_frame, num_periods):
    """Evaluate trade safety using RSI Indicator"""

    # Convert user timeframe input to Binance-supported intervals
    interval_mapping = {"minutes": "m", "hours": "h", "days": "d", "weeks": "w", "months": "M"}
    interval = f"{num_periods}{interval_mapping[time_frame.lower()]}"

    if interval not in VALID_TIMEFRAMES[time_frame.lower()]:
        raise ValueError(f"Invalid interval. Supported {time_frame} options: {', '.join(VALID_TIMEFRAMES[time_frame.lower()])}")

    # Fetch market data
    current_price = get_current_price(symbol)
    df = fetch_binance_ohlc(symbol, interval, market_type)

    # Calculate RSI
    df["RSI"] = calculate_rsi(df)
    latest_rsi = df["RSI"].iloc[-1]

    # RSI Analysis
    if latest_rsi > 70:
        rsi_analysis = "⚠️ Overbought: Possible pullback expected."
        safe_long = False
        safe_short = True
    elif latest_rsi < 30:
        rsi_analysis = "✅ Oversold: Possible bounce expected."
        safe_long = True
        safe_short = False
    else:
        rsi_analysis = "🔸 Neutral RSI: No clear trend."
        safe_long = False
        safe_short = False

    # Trade Verdict
    if trade_side == "long":
        verdict = "✅ YES - Safe to Long" if safe_long else "❌ NO - Risky to Long"
    elif trade_side == "short":
        verdict = "✅ YES - Safe to Short" if safe_short else "❌ NO - Risky to Short"
    else:
        verdict = "❌ Invalid trade side."

    # Print results
    print(f"🔹 Market: {market_type.upper()} | Coin: {symbol.upper()}")
    print(f"📌 Current Price: ${current_price:.2f}")
    print(f"📊 RSI: {latest_rsi:.2f}")
    print(f"📊 {rsi_analysis}")
    print(f"📊 Trade Verdict: {verdict}")

# Example Usage:
market_type = input("Choose market type (spot/futures): ").strip().lower()
coin = input("Enter coin (e.g., BTCUSDT): ").strip().upper()
trade_side = input("Enter trade side (long/short): ").strip().lower()
time_frame = input("Enter time frame (minutes/hours/days/weeks/months): ").strip().lower()
num_periods = int(input(f"Enter number of {time_frame}: "))

evaluate_trade(coin, market_type, trade_side, time_frame, num_periods)
