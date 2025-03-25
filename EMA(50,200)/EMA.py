#EMA FOR TREND CONFIRMATION - MAs: 50-day, 100-day, 200-day

import requests
import numpy as np

# Binance API endpoints
BINANCE_SPOT_API_URL = "https://api.binance.com/api/v3/klines"
BINANCE_FUTURES_API_URL = "https://fapi.binance.com/fapi/v1/klines"

def get_historical_data(symbol, interval, market_type, limit=200):
    """Fetch historical price data from Spot or Futures Market"""
    api_url = BINANCE_FUTURES_API_URL if market_type == "futures" else BINANCE_SPOT_API_URL

    params = {
        "symbol": symbol.upper(),
        "interval": interval,
        "limit": limit
    }
    response = requests.get(api_url, params=params)
    data = response.json()

    if "code" in data:  # Error handling for invalid API response
        raise Exception(f"Error fetching data: {data['msg']}")

    return [float(candle[4]) for candle in data]  # Closing prices

def calculate_moving_averages(prices, short_window=50, long_window=200):
    """Calculate moving averages for trend detection"""
    short_ma = np.mean(prices[-short_window:])  # Short-term MA (50-period)
    long_ma = np.mean(prices[-long_window:])  # Long-term MA (200-period)
    return short_ma, long_ma

def evaluate_trade(symbol, market_type, trade_side, time_frame, num_periods):
    """Evaluate trade safety based on moving averages"""

    # Map user input to Binance API intervals
    interval_mapping = {
        "minutes": f"{num_periods}m",
        "hours": f"{num_periods}h",
        "days": f"{num_periods}d"
    }

    if time_frame.lower() not in interval_mapping:
        raise ValueError("Invalid time frame. Choose from minutes, hours, or days.")

    interval = interval_mapping[time_frame.lower()]

    # Fetch market data (Spot or Futures)
    prices = get_historical_data(symbol, interval, market_type)
    short_ma, long_ma = calculate_moving_averages(prices)
    current_price = prices[-1]  # Latest price

    # Trade safety analysis
    if trade_side.lower() == "long":
        verdict = "✅ YES - Safe to Long (Golden Cross detected)" if short_ma > long_ma else "❌ NO - Risky to Long (Death Cross detected)"
    elif trade_side.lower() == "short":
        verdict = "✅ YES - Safe to Short (Death Cross detected)" if short_ma < long_ma else "❌ NO - Risky to Short (Golden Cross detected)"
    else:
        verdict = "❌ Invalid trade side! Choose 'long' or 'short'."

    # Print results
    print(f"🔹 Market: {market_type.upper()} | Coin: {symbol.upper()}")
    print(f"📌 Current Price: ${current_price:.2f}")
    print(f"📈 Moving Averages: 50-MA: {short_ma:.2f}, 200-MA: {long_ma:.2f}")
    print(f"📊 Trade Verdict: {verdict}")

# Example Usage:
market_type = input("Choose market type (spot/futures): ").strip().lower()
coin = input("Enter coin (e.g., BTCUSDT): ").strip().upper()
trade_side = input("Enter trade side (long/short): ").strip().lower()
time_frame = input("Enter time frame (minutes/hours/days): ").strip().lower()
num_periods = int(input(f"Enter number of {time_frame}: "))

evaluate_trade(coin, market_type, trade_side, time_frame, num_periods)
