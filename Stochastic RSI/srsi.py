#Stochastic RSI (Advanced RSI for Reversals)
#Stoch RSI > 80 → Overbought (Sell Signal)
#Stoch RSI < 20 → Oversold (Buy Signal)


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

def calculate_stochastic_rsi(prices, rsi_period=14, stoch_rsi_period=14):
    """Calculate Stochastic RSI (Advanced RSI for Reversals)"""
    if len(prices) < rsi_period + stoch_rsi_period:
        raise ValueError("Not enough data points to calculate Stochastic RSI")

    # Calculate RSI
    deltas = np.diff(prices)
    gain = np.where(deltas > 0, deltas, 0)
    loss = np.where(deltas < 0, -deltas, 0)

    avg_gain = np.convolve(gain, np.ones(rsi_period)/rsi_period, mode='valid')
    avg_loss = np.convolve(loss, np.ones(rsi_period)/rsi_period, mode='valid')

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    # Calculate Stochastic RSI
    stoch_rsi_min = np.min(rsi[-stoch_rsi_period:])
    stoch_rsi_max = np.max(rsi[-stoch_rsi_period:])
    stoch_rsi = 100 * (rsi[-1] - stoch_rsi_min) / (stoch_rsi_max - stoch_rsi_min)

    return stoch_rsi

def evaluate_trade(symbol, market_type, trade_side, time_frame, num_periods):
    """Evaluate trade safety based on Stochastic RSI"""

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
    stoch_rsi = calculate_stochastic_rsi(prices)
    current_price = prices[-1]  # Latest price

    # Trade safety analysis
    if trade_side.lower() == "long":
        verdict = "✅ YES - Safe to Long (Stoch RSI Oversold < 20)" if stoch_rsi < 20 else "❌ NO - Risky to Long (Stoch RSI Overbought > 80)"
    elif trade_side.lower() == "short":
        verdict = "✅ YES - Safe to Short (Stoch RSI Overbought > 80)" if stoch_rsi > 80 else "❌ NO - Risky to Short (Stoch RSI Oversold < 20)"
    else:
        verdict = "❌ Invalid trade side! Choose 'long' or 'short'."

    # Print results
    print(f"🔹 Market: {market_type.upper()} | Coin: {symbol.upper()}")
    print(f"📌 Current Price: ${current_price:.2f}")
    print(f"📊 Stochastic RSI: {stoch_rsi:.2f}")
    print(f"📈 Trade Verdict: {verdict}")

# Example Usage:
market_type = input("Choose market type (spot/futures): ").strip().lower()
coin = input("Enter coin (e.g., BTCUSDT): ").strip().upper()
trade_side = input("Enter trade side (long/short): ").strip().lower()
time_frame = input("Enter time frame (minutes/hours/days): ").strip().lower()
num_periods = int(input(f"Enter number of {time_frame}: "))

evaluate_trade(coin, market_type, trade_side, time_frame, num_periods)
