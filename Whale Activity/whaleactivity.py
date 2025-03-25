import requests

# Binance API Endpoints
BINANCE_PRICE_API_URL = "https://api.binance.com/api/v3/ticker/price"
BINANCE_ORDER_BOOK_API_URL = "https://api.binance.com/api/v3/depth"

# Whale Trade Threshold (adjustable)
WHALE_TRADE_THRESHOLD = 5  # Orders greater than 5 BTC/ETH/etc.

def get_current_price(symbol):
    """Fetch the current market price from Binance."""
    response = requests.get(f"{BINANCE_PRICE_API_URL}?symbol={symbol.upper()}")
    data = response.json()
    return float(data["price"])

def get_whale_activity(symbol):
    """Fetch whale activity from Binance order book (large buy/sell orders)."""
    response = requests.get(f"{BINANCE_ORDER_BOOK_API_URL}?symbol={symbol.upper()}&limit=500")
    data = response.json()

    if "bids" in data and "asks" in data:
        # Extract bid (buy) and ask (sell) orders
        bids = [(float(price), float(quantity)) for price, quantity in data["bids"]]
        asks = [(float(price), float(quantity)) for price, quantity in data["asks"]]

        # Count whale trades (orders exceeding threshold)
        large_buys = sum(qty for price, qty in bids if qty > WHALE_TRADE_THRESHOLD)
        large_sells = sum(qty for price, qty in asks if qty > WHALE_TRADE_THRESHOLD)

        return large_buys, large_sells
    return None, None

def evaluate_whale_trade(symbol, trade_side):
    """Evaluate trade safety based on whale buy/sell pressure."""
    
    # Fetch market data
    current_price = get_current_price(symbol)
    large_buys, large_sells = get_whale_activity(symbol)

    if large_buys is None:
        print(f"⚠️ Error fetching whale activity for {symbol}.")
        return

    # Whale Activity Analysis
    if large_buys > large_sells:
        whale_analysis = "✅ Bullish: Whales are accumulating."
        safe_long = True
        safe_short = False
    elif large_sells > large_buys:
        whale_analysis = "⚠️ Bearish: Whales are selling aggressively."
        safe_long = False
        safe_short = True
    else:
        whale_analysis = "🤔 Neutral: No strong whale signals detected."
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
    print(f"\n📊 Whale Activity Analysis for {symbol}")
    print(f"💰 Current Price: ${current_price:.2f}")
    print(f"🐋 Large Buy Orders (>5 BTC): {large_buys} BTC")
    print(f"🐋 Large Sell Orders (>5 BTC): {large_sells} BTC")
    print(f"📊 {whale_analysis}")
    print(f"📊 Trade Verdict: {verdict}")

# Example Usage:
coin = input("Enter Crypto Pair (e.g., BTCUSDT): ").strip().upper()
trade_side = input("Enter Trade Side (long/short): ").strip().lower()

evaluate_whale_trade(coin, trade_side)
