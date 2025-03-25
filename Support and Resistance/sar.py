#support and resistance
import requests
import numpy as np

# Binance API Endpoints
BINANCE_SPOT_API_URL = "https://api.binance.com/api/v3/klines"
BINANCE_FUTURES_API_URL = "https://fapi.binance.com/fapi/v1/klines"


def get_historical_data(symbol, interval, market_type, limit=100):
    """Fetch historical price data from Spot or Futures Market"""
    api_url = BINANCE_FUTURES_API_URL if market_type == "futures" else BINANCE_SPOT_API_URL

    params = {
        "symbol": symbol.upper(),
        "interval": interval,
        "limit": limit
    }
    response = requests.get(api_url, params=params)
    data = response.json()

    if "code" in data:
        raise Exception(f"Error fetching data: {data['msg']}")

    # Extract high, low, and closing prices
    highs = [float(candle[2]) for candle in data]
    lows = [float(candle[3]) for candle in data]
    closes = [float(candle[4]) for candle in data]

    return highs, lows, closes


def find_support_resistance(highs, lows):
    """Identify Key Support & Resistance Levels"""
    support = min(lows)  # Lowest low = Strongest Support
    resistance = max(highs)  # Highest high = Strongest Resistance

    return support, resistance


def evaluate_trade(symbol, market_type, trade_side, time_frame, num_periods):
    """Evaluate trade safety using Support & Resistance"""

    # Timeframe Mapping for Binance API
    interval_mapping = {
        "minutes": f"{num_periods}m",
        "hours": f"{num_periods}h",
        "days": f"{num_periods}d"
    }

    if time_frame.lower() not in interval_mapping:
        raise ValueError("Invalid time frame. Choose from minutes, hours, or days.")

    interval = interval_mapping[time_frame.lower()]

    # Fetch Market Data (Spot or Futures)
    highs, lows, closes = get_historical_data(symbol, interval, market_type)
    support, resistance = find_support_resistance(highs, lows)
    current_price = closes[-1]  # Latest price

    # Trade Safety Analysis
    if trade_side.lower() == "long":
        if current_price <= support * 1.02:  # Price close to support (Safe Long)
            verdict = "✅ YES - Safe to Long (Near Strong Support)"
        elif current_price >= resistance * 0.98:  # Price close to resistance (Risky Long)
            verdict = "❌ NO - Risky to Long (Near Strong Resistance)"
        else:
            verdict = "❌ NO - Risky to Long (No Support Nearby)"

    elif trade_side.lower() == "short":
        if current_price >= resistance * 0.98:  # Price close to resistance (Safe Short)
            verdict = "✅ YES - Safe to Short (Near Strong Resistance)"
        elif current_price <= support * 1.02:  # Price close to support (Risky Short)
            verdict = "❌ NO - Risky to Short (Near Strong Support)"
        else:
            verdict = "✅ YES - Safe to Short (No Support Nearby)"

    else:
        verdict = "❌ Invalid trade side! Choose 'long' or 'short'."

    # Print Results
    print(f"🔹 Market: {market_type.upper()} | Coin: {symbol.upper()}")
    print(f"📌 Current Price: ${current_price:.2f}")
    print(f"📊 Support Level: ${support:.2f} | Resistance Level: ${resistance:.2f}")
    print(f"📈 Trade Verdict: {verdict}")


# Example Usage:
market_type = input("Choose market type (spot/futures): ").strip().lower()
coin = input("Enter coin (e.g., BTCUSDT): ").strip().upper()
trade_side = input("Enter trade side (long/short): ").strip().lower()
time_frame = input("Enter time frame (minutes/hours/days): ").strip().lower()
num_periods = int(input(f"Enter number of {time_frame}: "))

evaluate_trade(coin, market_type, trade_side, time_frame, num_periods)
