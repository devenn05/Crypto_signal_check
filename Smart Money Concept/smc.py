#Smart Money Concept

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

    # Extract open, high, low, and closing prices
    opens = [float(candle[1]) for candle in data]
    highs = [float(candle[2]) for candle in data]
    lows = [float(candle[3]) for candle in data]
    closes = [float(candle[4]) for candle in data]

    return opens, highs, lows, closes


def detect_bos(highs, lows):
    """Detect Break of Structure (BOS) & Change of Character (CHoCH)"""
    if highs[-1] > highs[-2] and lows[-1] > lows[-2]:
        return "BULLISH BOS (Uptrend, Safe Long)"
    elif highs[-1] < highs[-2] and lows[-1] < lows[-2]:
        return "BEARISH BOS (Downtrend, Safe Short)"
    return "NO BOS (Unclear Trend)"


def detect_order_blocks(opens, highs, lows, closes):
    """Identify Order Blocks (Demand & Supply Zones)"""
    bullish_ob = min(lows[-5:])  # Recent lowest low (Demand)
    bearish_ob = max(highs[-5:])  # Recent highest high (Supply)

    return bullish_ob, bearish_ob


def detect_liquidity_grabs(highs, lows, closes):
    """Identify Stop Hunts (Liquidity Grabs)"""
    recent_high = max(highs[-5:])
    recent_low = min(lows[-5:])
    last_close = closes[-1]

    if last_close > recent_high:
        return "BUY LIQUIDITY GRAB (Possible Short)"
    elif last_close < recent_low:
        return "SELL LIQUIDITY GRAB (Possible Long)"
    return "NO LIQUIDITY GRAB"


def evaluate_trade(symbol, market_type, trade_side, time_frame, num_periods):
    """Evaluate trade safety using SMC Concepts"""

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
    opens, highs, lows, closes = get_historical_data(symbol, interval, market_type)
    bos_signal = detect_bos(highs, lows)
    bullish_ob, bearish_ob = detect_order_blocks(opens, highs, lows, closes)
    liquidity_grab = detect_liquidity_grabs(highs, lows, closes)
    current_price = closes[-1]  # Latest price

    # Trade Safety Analysis
    if trade_side.lower() == "long":
        if liquidity_grab == "SELL LIQUIDITY GRAB" or current_price >= bullish_ob * 0.98:
            verdict = "✅ YES - Safe to Long (Liquidity Grab or Demand Zone)"
        elif liquidity_grab == "BUY LIQUIDITY GRAB" or current_price <= bearish_ob * 1.02:
            verdict = "❌ NO - Risky to Long (Near Supply Zone)"
        else:
            verdict = f"⚠️ Check BOS: {bos_signal}"

    elif trade_side.lower() == "short":
        if liquidity_grab == "BUY LIQUIDITY GRAB" or current_price <= bearish_ob * 1.02:
            verdict = "✅ YES - Safe to Short (Liquidity Grab or Supply Zone)"
        elif liquidity_grab == "SELL LIQUIDITY GRAB" or current_price >= bullish_ob * 0.98:
            verdict = "❌ NO - Risky to Short (Near Demand Zone)"
        else:
            verdict = f"⚠️ Check BOS: {bos_signal}"

    else:
        verdict = "❌ Invalid trade side! Choose 'long' or 'short'."

    # Print Results
    print(f"🔹 Market: {market_type.upper()} | Coin: {symbol.upper()}")
    print(f"📌 Current Price: ${current_price:.2f}")
    print(f"📊 Bullish Order Block: ${bullish_ob:.2f} | Bearish Order Block: ${bearish_ob:.2f}")
    print(f"⚡ Liquidity Grab: {liquidity_grab}")
    print(f"📈 Trade Verdict: {verdict}")


# Example Usage:
market_type = input("Choose market type (spot/futures): ").strip().lower()
coin = input("Enter coin (e.g., BTCUSDT): ").strip().upper()
trade_side = input("Enter trade side (long/short): ").strip().lower()
time_frame = input("Enter time frame (minutes/hours/days): ").strip().lower()
num_periods = int(input(f"Enter number of {time_frame}: "))

evaluate_trade(coin, market_type, trade_side, time_frame, num_periods)
