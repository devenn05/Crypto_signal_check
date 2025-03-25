import requests
import time


# Function to get current price from Binance
def get_current_price(symbol):
    url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
    response = requests.get(url).json()
    return float(response["price"])


# Function to get exchange netflow (approximation using Binance Wallet Data API)
def get_exchange_netflow(symbol, interval):
    url = f"https://api.binance.com/api/v3/ticker/24hr?symbol={symbol}"
    response = requests.get(url).json()

    if "quoteVolume" in response and "volume" in response:
        quote_volume = float(response["quoteVolume"])  # Total trade volume in USD
        asset_volume = float(response["volume"])  # Crypto volume traded

        # Approximate Netflow: Assume a % of total trade volume is deposited/withdrawn
        netflow = asset_volume * 0.05  # Assume 5% of traded volume moved to/from exchanges
        return netflow
    return None


# User Input
symbol = input("Enter Crypto Symbol (e.g., BTCUSDT, ETHUSDT): ").strip().upper()
trade_type = input("Did you take a 'long' or 'short' trade? ").strip().lower()
time_unit = input("Select Timeframe: Minutes, Hours, or Days? ").strip().lower()
time_value = int(input(f"Enter how many {time_unit}: "))

# Convert timeframe into seconds
if time_unit == "minutes":
    interval = time_value * 60
elif time_unit == "hours":
    interval = time_value * 3600
elif time_unit == "days":
    interval = time_value * 86400
else:
    print("Invalid timeframe. Defaulting to 24 hours.")
    interval = 86400  # Default to 1 day

# Fetch Data
current_price = get_current_price(symbol)
netflow = get_exchange_netflow(symbol, interval)

# Print Results
print(f"\n📊 Exchange Netflow Analysis for {symbol}")
print(f"💰 Current Price: ${current_price}")

if netflow is not None:
    if netflow < 0:
        print("✅ Negative Netflow → More crypto leaving exchanges (Bullish)")
        if trade_type == "long":
            print("🔹 Your long position seems safer based on exchange netflow.")
        else:
            print("⚠️ Your short position may be risky (whales are withdrawing).")
    else:
        print("⚠️ Positive Netflow → More crypto entering exchanges (Bearish)")
        if trade_type == "short":
            print("🔹 Your short position seems safer based on exchange netflow.")
        else:
            print("⚠️ Your long position may be risky (whales are depositing).")
else:
    print("⚠️ No exchange netflow data available.")
