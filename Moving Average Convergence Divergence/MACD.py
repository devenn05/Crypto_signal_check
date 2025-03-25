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
    response = requests.get(f"{BINANCE_PRICE_API_URL}?symbol={symbol}")
    data = response.json()
    return float(data["price"])

def fetch_binance_ohlc(symbol, interval, market_type, limit=100):
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

def calculate_macd(df, short_window=12, long_window=26, signal_window=9):
    """Calculate MACD Indicator"""
    df["EMA12"] = df["close"].ewm(span=short_window, adjust=False).mean()
    df["EMA26"] = df["close"].ewm(span=long_window, adjust=False).mean()
    df["MACD"] = df["EMA12"] - df["EMA26"]
    df["Signal_Line"] = df["MACD"].ewm(span=signal_window, adjust=False).mean()
    return df["MACD"], df["Signal_Line"]

def evaluate_trade(symbol, market_type, trade_side, time_frame, num_periods):
    """Evaluate trade safety based on MACD indicator"""

    # Convert user timeframe input to Binance-supported intervals
    interval_mapping = {"minutes": "m", "hours": "h", "days": "d", "weeks": "w", "months": "M"}
    interval = f"{num_periods}{interval_mapping[time_frame.lower()]}"

    if interval not in VALID_TIMEFRAMES[time_frame.lower()]:
        raise ValueError(f"Invalid interval. Supported {time_frame} options: {', '.join(VALID_TIMEFRAMES[time_frame.lower()])}")

    # Fetch market data
    current_price = get_current_price(symbol)
    df = fetch_binance_ohlc(symbol, interval, market_type)
    df["MACD"], df["Signal_Line"] = calculate_macd(df)

    latest_macd = df["MACD"].iloc[-1]
    latest_signal = df["Signal_Line"].iloc[-1]

    # Trade Analysis
    if latest_macd > latest_signal:
        macd_analysis = "✅ Bullish Momentum: MACD is above Signal Line."
        verdict = "✅ YES - Safe to Long" if trade_side == "long" else "❌ NO - Risky to Short"
    else:
        macd_analysis = "⚠️ Bearish Momentum: MACD is below Signal Line."
        verdict = "✅ YES - Safe to Short" if trade_side == "short" else "❌ NO - Risky to Long"

    # Print results
    print(f"🔹 Market: {market_type.upper()} | Coin: {symbol.upper()}")
    print(f"📌 Current Price: ${current_price:.2f}")
    print(f"📊 {macd_analysis}")
    print(f"📊 Trade Verdict: {verdict}")

# Example Usage:
market_type = input("Choose market type (spot/futures): ").strip().lower()
coin = input("Enter coin (e.g., BTCUSDT): ").strip().upper()
trade_side = input("Enter trade side (long/short): ").strip().lower()
time_frame = input("Enter time frame (minutes/hours/days/weeks/months): ").strip().lower()
num_periods = int(input(f"Enter number of {time_frame}: "))

evaluate_trade(coin, market_type, trade_side, time_frame, num_periods)
