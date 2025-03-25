import requests

# Binance API endpoints
BINANCE_SPOT_API_URL = "https://api.binance.com/api/v3/ticker/24hr"
BINANCE_FUTURES_API_URL = "https://fapi.binance.com/fapi/v1/ticker/24hr"
BINANCE_PRICE_API_URL = "https://api.binance.com/api/v3/ticker/price"

def get_current_price(symbol):
    """Fetch current price from Binance"""
    response = requests.get(f"{BINANCE_PRICE_API_URL}?symbol={symbol}")
    data = response.json()
    return float(data["price"])

def get_exchange_netflow(symbol, market_type):
    """Fetch exchange netflow approximation (based on volume)"""
    api_url = BINANCE_FUTURES_API_URL if market_type == "futures" else BINANCE_SPOT_API_URL
    response = requests.get(f"{api_url}?symbol={symbol}")
    data = response.json()

    if "code" in data:
        raise Exception(f"Error fetching data: {data['msg']}")

    quote_volume = float(data["quoteVolume"])  # Total trade volume in USD
    asset_volume = float(data["volume"])  # Crypto volume traded

    # Approximate Netflow: Assume 5% of traded volume moved to/from exchanges
    netflow = asset_volume * 0.05
    return netflow

def evaluate_trade(symbol, market_type, trade_side, time_frame, num_periods):
    """Evaluate trade safety based on exchange netflow"""

    # Convert timeframe to seconds (for reference)
    interval_mapping = {"minutes": 60, "hours": 3600, "days": 86400}
    if time_frame.lower() not in interval_mapping:
        raise ValueError("Invalid time frame. Choose from minutes, hours, or days.")

    interval = num_periods * interval_mapping[time_frame.lower()]

    # Fetch market data
    current_price = get_current_price(symbol)
    netflow = get_exchange_netflow(symbol, market_type)

    # Trade safety analysis
    if netflow < 0:
        netflow_analysis = "✅ Negative Netflow → More crypto leaving exchanges (Bullish)"
        verdict = "✅ YES - Safe to Long" if trade_side == "long" else "❌ NO - Risky to Short"
    else:
        netflow_analysis = "⚠️ Positive Netflow → More crypto entering exchanges (Bearish)"
        verdict = "✅ YES - Safe to Short" if trade_side == "short" else "❌ NO - Risky to Long"

    # Print results
    print(f"🔹 Market: {market_type.upper()} | Coin: {symbol.upper()}")
    print(f"📌 Current Price: ${current_price:.2f}")
    print(f"📊 {netflow_analysis}")
    print(f"📊 Trade Verdict: {verdict}")

# Example Usage:
market_type = input("Choose market type (spot/futures): ").strip().lower()
coin = input("Enter coin (e.g., BTCUSDT): ").strip().upper()
trade_side = input("Enter trade side (long/short): ").strip().lower()
time_frame = input("Enter time frame (minutes/hours/days): ").strip().lower()
num_periods = int(input(f"Enter number of {time_frame}: "))

evaluate_trade(coin, market_type, trade_side, time_frame, num_periods)
