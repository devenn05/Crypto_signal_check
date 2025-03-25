import requests

# Function to get current price
def get_current_price(symbol):
    url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
    response = requests.get(url).json()
    return float(response["price"])

# Function to get whale activity (large trades from Binance API)
def get_whale_activity(symbol):
    url = f"https://api.binance.com/api/v3/depth?symbol={symbol}&limit=500"
    response = requests.get(url).json()

    if "bids" in response and "asks" in response:
        # Extract bid (buy) and ask (sell) orders
        bids = [(float(price), float(quantity)) for price, quantity in response["bids"]]
        asks = [(float(price), float(quantity)) for price, quantity in response["asks"]]

        # Define whale trade threshold (e.g., orders > 5 BTC)
        whale_threshold = 5

        # Count whale orders
        large_buys = sum(qty for price, qty in bids if qty > whale_threshold)
        large_sells = sum(qty for price, qty in asks if qty > whale_threshold)

        return large_buys, large_sells
    return None, None

# User input
symbol = input("Enter Crypto Symbol (e.g., BTCUSDT, ETHUSDT): ").strip().upper()
trade_type = input("Did you take a 'long' or 'short' trade? ").strip().lower()

# Fetch data
current_price = get_current_price(symbol)
large_buys, large_sells = get_whale_activity(symbol)

# Print results
print(f"\n📊 Whale Activity Analysis for {symbol}")
print(f"💰 Current Price: ${current_price}")
print(f"🐋 Large Buy Orders (>5 BTC): {large_buys} BTC")
print(f"🐋 Large Sell Orders (>5 BTC): {large_sells} BTC")

# Interpretation
if large_buys is not None:
    if large_buys > large_sells:
        print("✅ More large buy orders → Bullish (Whales are accumulating)")
        if trade_type == "long":
            print("🔹 Your long position seems safer based on whale activity.")
        else:
            print("⚠️ Your short position may be risky (whales buying).")
    elif large_sells > large_buys:
        print("⚠️ More large sell orders → Bearish (Selling pressure increasing)")
        if trade_type == "short":
            print("🔹 Your short position seems safer based on whale activity.")
        else:
            print("⚠️ Your long position may be risky (whales selling).")
    else:
        print("🤔 Balanced activity → No strong whale signals detected.")
else:
    print("⚠️ No whale activity data available.")

