#Volume Profile (Order Flow Confirmation)
#High volume at price level → Strong support/resistance
#Low volume at price level → Weak zone (Price moves easily)

import requests
import numpy as np
from collections import defaultdict

# Binance API endpoints
BINANCE_SPOT_API_URL = "https://api.binance.com/api/v3/klines"
BINANCE_FUTURES_API_URL = "https://fapi.binance.com/fapi/v1/klines"

def get_historical_data(symbol, interval, market_type, limit=200):
    """Fetch historical price & volume data from Spot or Futures Market"""
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

    # Extract closing prices and volumes
    prices = [float(candle[4]) for candle in data]  # Closing prices
    volumes = [float(candle[5]) for candle in data]  # Trading volumes

    return prices, volumes

def calculate_volume_profile(prices, volumes, num_bins=10):
    """Calculate Volume Profile (Order Flow Confirmation)"""
    price_min, price_max = min(prices), max(prices)
    price_bins = np.linspace(price_min, price_max, num_bins + 1)  # Create price bins

    volume_profile = defaultdict(float)

    for price, volume in zip(prices, volumes):
        for i in range(num_bins):
            if price_bins[i] <= price < price_bins[i + 1]:
                volume_profile[price_bins[i]] += volume
                break

    # Find strong and weak price zones
    max_volume = max(volume_profile.values())
    strong_zones = {level: vol for level, vol in volume_profile.items() if vol >= max_volume * 0.7}  # High-volume (Strong S/R)
    weak_zones = {level: vol for level, vol in volume_profile.items() if vol < max_volume * 0.3}   # Low-volume (Weak zone)

    return strong_zones, weak_zones, price_bins

def evaluate_trade(symbol, market_type, trade_side, time_frame, num_periods):
    """Evaluate trade safety based on Volume Profile"""

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
    prices, volumes = get_historical_data(symbol, interval, market_type)
    strong_zones, weak_zones, price_bins = calculate_volume_profile(prices, volumes)
    current_price = prices[-1]  # Latest price

    # Trade safety analysis
    if trade_side.lower() == "long":
        if any(level <= current_price <= level + (price_bins[1] - price_bins[0]) for level in strong_zones):
            verdict = "✅ YES - Safe to Long (High Volume Support Zone)"
        elif any(level <= current_price <= level + (price_bins[1] - price_bins[0]) for level in weak_zones):
            verdict = "❌ NO - Risky to Long (Low Volume Weak Zone)"
        else:
            verdict = "❌ NO - Risky (No strong support nearby)"

    elif trade_side.lower() == "short":
        if any(level <= current_price <= level + (price_bins[1] - price_bins[0]) for level in strong_zones):
            verdict = "❌ NO - Risky to Short (Strong Support Below)"
        elif any(level <= current_price <= level + (price_bins[1] - price_bins[0]) for level in weak_zones):
            verdict = "✅ YES - Safe to Short (Weak Zone, Price Moves Easily)"
        else:
            verdict = "✅ YES - Safe to Short (No strong support nearby)"

    else:
        verdict = "❌ Invalid trade side! Choose 'long' or 'short'."

    # Print results
    print(f"🔹 Market: {market_type.upper()} | Coin: {symbol.upper()}")
    print(f"📌 Current Price: ${current_price:.2f}")
    print(f"📊 Volume Profile: {len(strong_zones)} Strong Zones, {len(weak_zones)} Weak Zones")
    print(f"📈 Trade Verdict: {verdict}")

# Example Usage:
market_type = input("Choose market type (spot/futures): ").strip().lower()
coin = input("Enter coin (e.g., BTCUSDT): ").strip().upper()
trade_side = input("Enter trade side (long/short): ").strip().lower()
time_frame = input("Enter time frame (minutes/hours/days): ").strip().lower()
num_periods = int(input(f"Enter number of {time_frame}: "))

evaluate_trade(coin, market_type, trade_side, time_frame, num_periods)
