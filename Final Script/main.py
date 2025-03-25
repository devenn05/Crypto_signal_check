import requests
import pandas as pd
import numpy as np
from collections import defaultdict
import random

# Binance API configurations
BINANCE_SPOT_URL = "https://api.binance.com/api/v3"
BINANCE_FUTURES_URL = "https://fapi.binance.com/fapi/v1"
BINANCE_PRICE_API_URL = "https://api.binance.com/api/v3/ticker/price"
BINANCE_ORDER_BOOK_API_URL = "https://api.binance.com/api/v3/depth"
WHALE_TRADE_THRESHOLD = 5  # Orders greater than 5 BTC/ETH/etc.

VALID_TIMEFRAMES = {
    "minutes": ["1m", "3m", "5m", "15m", "30m"],
    "hours": ["1h", "2h", "4h", "6h", "8h", "12h"],
    "days": ["1d", "3d"],
    "weeks": ["1w"],
    "months": ["1M"]
}


def get_current_price(symbol, market_type):
    base_url = BINANCE_FUTURES_URL if market_type == "futures" else BINANCE_SPOT_URL
    url = f"{base_url}/ticker/price?symbol={symbol.upper()}"
    response = requests.get(url).json()
    return float(response["price"])


def fetch_ohlc_data(symbol, interval, market_type, limit=200):
    base_url = BINANCE_FUTURES_URL if market_type == "futures" else BINANCE_SPOT_URL
    url = f"{base_url}/klines?symbol={symbol.upper()}&interval={interval}&limit={limit}"
    response = requests.get(url).json()

    df = pd.DataFrame(response, columns=[
        "timestamp", "open", "high", "low", "close", "volume", "close_time",
        "quote_asset_volume", "trades", "taker_buy_base_asset_volume",
        "taker_buy_quote_asset_volume", "ignore"
    ])

    # Convert all numeric columns to float
    numeric_cols = ["open", "high", "low", "close", "volume",
                    "quote_asset_volume", "taker_buy_base_asset_volume",
                    "taker_buy_quote_asset_volume"]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col])

    return df


# 1. Average Directional Index (ADX)
def adx_verdict(df, trade_type):
    df["+DM"] = df["high"].diff()
    df["-DM"] = df["low"].diff()
    df["+DM"] = df["+DM"].where((df["+DM"] > df["-DM"]) & (df["+DM"] > 0), 0)
    df["-DM"] = df["-DM"].where((df["-DM"] > df["+DM"]) & (df["-DM"] > 0), 0)

    tr1 = df["high"] - df["low"]
    tr2 = abs(df["high"] - df["close"].shift(1))
    tr3 = abs(df["low"] - df["close"].shift(1))
    df["TR"] = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    period = 14
    df["+DI"] = 100 * (df["+DM"].rolling(period).sum() / df["TR"].rolling(period).sum())
    df["-DI"] = 100 * (df["-DM"].rolling(period).sum() / df["TR"].rolling(period).sum())
    df["DX"] = 100 * abs(df["+DI"] - df["-DI"]) / (df["+DI"] + df["-DI"])
    df["ADX"] = df["DX"].rolling(period).mean()

    latest_adx = df["ADX"].iloc[-1]
    if latest_adx > 25:
        return "yes" if trade_type in ["long", "short"] else "no"
    return "no"


# 2. EMA (Moving Averages)
def ema_verdict(df, trade_type):
    short_ma = df["close"].ewm(span=50, adjust=False).mean().iloc[-1]
    long_ma = df["close"].ewm(span=200, adjust=False).mean().iloc[-1]

    if trade_type == "long":
        return "yes" if short_ma > long_ma else "no"
    else:  # short
        return "yes" if short_ma < long_ma else "no"


# 3. Exchange Net Flow
def netflow_verdict(symbol, market_type, trade_type):
    api_url = BINANCE_FUTURES_URL if market_type == "futures" else BINANCE_SPOT_URL
    response = requests.get(f"{api_url}/ticker/24hr?symbol={symbol.upper()}").json()
    quote_volume = float(response["quoteVolume"])
    asset_volume = float(response["volume"])
    netflow = asset_volume * 0.05  # Approximation

    if netflow < 0:
        return "yes" if trade_type == "long" else "no"
    else:
        return "yes" if trade_type == "short" else "no"


# 4. Market Sentiment (Fear & Greed)
def sentiment_verdict(trade_type):
    try:
        url = "https://api.alternative.me/fng/"
        response = requests.get(url).json()
        index_value = int(response["data"][0]["value"])

        if index_value <= 25:
            return "yes" if trade_type == "long" else "no"
        elif index_value >= 75:
            return "yes" if trade_type == "short" else "no"
    except:
        pass
    return "no"


# 5. Miner Activity
def miner_verdict():
    netflow = random.uniform(-1000, 1000)  # Simulated netflow
    return "yes" if netflow < 0 else "no"  # Simplified for demo


# 6. MACD
def macd_verdict(df, trade_type):
    df["EMA12"] = df["close"].ewm(span=12, adjust=False).mean()
    df["EMA26"] = df["close"].ewm(span=26, adjust=False).mean()
    df["MACD"] = df["EMA12"] - df["EMA26"]
    df["Signal_Line"] = df["MACD"].ewm(span=9, adjust=False).mean()

    latest_macd = df["MACD"].iloc[-1]
    latest_signal = df["Signal_Line"].iloc[-1]

    if latest_macd > latest_signal:
        return "yes" if trade_type == "long" else "no"
    else:
        return "yes" if trade_type == "short" else "no"


# 7. Order Flow Confirmation (Volume Profile)
def volume_profile_verdict(df, trade_type):
    try:
        num_bins = 10
        price_min, price_max = df["close"].min(), df["close"].max()
        price_bins = np.linspace(price_min, price_max, num_bins + 1)

        volume_profile = defaultdict(float)
        for _, row in df.iterrows():
            price = row["close"]
            volume = row["volume"]
            for i in range(num_bins):
                if price_bins[i] <= price < price_bins[i + 1]:
                    volume_profile[price_bins[i]] += float(volume)
                    break

        max_volume = max(volume_profile.values())
        strong_zones = {level: vol for level, vol in volume_profile.items() if vol >= max_volume * 0.7}
        current_price = df["close"].iloc[-1]

        if trade_type == "long":
            near_strong_zone = any(level <= current_price <= level + (price_bins[1] - price_bins[0])
                                   for level in strong_zones)
            return "yes" if near_strong_zone else "no"
        else:  # short
            near_weak_zone = not any(level <= current_price <= level + (price_bins[1] - price_bins[0])
                                     for level in strong_zones)
            return "yes" if near_weak_zone else "no"
    except:
        return "no"


# 8. Relative Strength Index (RSI)
def rsi_verdict(df, trade_type):
    try:
        period = 14
        delta = df["close"].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))

        latest_rsi = rsi.iloc[-1]
        if latest_rsi < 30:
            return "yes" if trade_type == "long" else "no"
        elif latest_rsi > 70:
            return "yes" if trade_type == "short" else "no"
    except:
        pass
    return "no"


# 9. Smart Money Concept
def smc_verdict(df, trade_type):
    try:
        highs = df["high"].values[-5:]
        lows = df["low"].values[-5:]
        closes = df["close"].values[-5:]

        # Break of Structure detection
        if highs[-1] > highs[-2] and lows[-1] > lows[-2]:
            bos_signal = "bullish"
        elif highs[-1] < highs[-2] and lows[-1] < lows[-2]:
            bos_signal = "bearish"
        else:
            bos_signal = "neutral"

        # Order blocks
        bullish_ob = min(lows)
        bearish_ob = max(highs)
        current_price = closes[-1]

        if trade_type == "long":
            if bos_signal == "bullish" or current_price >= bullish_ob * 0.98:
                return "yes"
        else:  # short
            if bos_signal == "bearish" or current_price <= bearish_ob * 1.02:
                return "yes"
    except:
        pass
    return "no"


# 10. Whale Activity
def whale_verdict(symbol, trade_type):
    try:
        response = requests.get(f"{BINANCE_ORDER_BOOK_API_URL}?symbol={symbol.upper()}&limit=500").json()
        bids = [(float(price), float(qty)) for price, qty in response["bids"]]
        asks = [(float(price), float(qty)) for price, qty in response["asks"]]

        large_buys = sum(qty for price, qty in bids if qty > WHALE_TRADE_THRESHOLD)
        large_sells = sum(qty for price, qty in asks if qty > WHALE_TRADE_THRESHOLD)

        if large_buys > large_sells:
            return "yes" if trade_type == "long" else "no"
        elif large_sells > large_buys:
            return "yes" if trade_type == "short" else "no"
    except:
        pass
    return "no"


# 11. Stochastic RSI
def stoch_rsi_verdict(df, trade_type):
    try:
        # Calculate RSI
        period = 14
        delta = df["close"].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))

        # Calculate Stochastic RSI
        stoch_period = 14
        stoch_rsi_min = rsi.rolling(stoch_period).min()
        stoch_rsi_max = rsi.rolling(stoch_period).max()
        stoch_rsi = 100 * (rsi - stoch_rsi_min) / (stoch_rsi_max - stoch_rsi_min)

        latest_stoch_rsi = stoch_rsi.iloc[-1]
        if latest_stoch_rsi < 20:
            return "yes" if trade_type == "long" else "no"
        elif latest_stoch_rsi > 80:
            return "yes" if trade_type == "short" else "no"
    except:
        pass
    return "no"


# 12. Support and Resistance
# Add these helper functions near the top with your other utility functions
def get_historical_data(symbol, interval, market_type, limit=100):
    """Fetch historical price data from Spot or Futures Market"""
    base_url = BINANCE_FUTURES_URL if market_type == "futures" else BINANCE_SPOT_URL
    url = f"{base_url}/klines"

    params = {
        "symbol": symbol.upper(),
        "interval": interval,
        "limit": limit
    }
    response = requests.get(url, params=params)
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


# Replace the existing support_resistance_verdict function with this:
def support_resistance_verdict(df, trade_type):
    """Enhanced Support/Resistance Analysis with Detailed Verdict"""
    try:
        # Get data from DataFrame (to maintain compatibility)
        highs = df["high"].values
        lows = df["low"].values
        closes = df["close"].values

        support, resistance = find_support_resistance(highs, lows)
        current_price = closes[-1]  # Latest price

        # Trade Safety Analysis
        if trade_type == "long":
            if current_price <= support * 1.02:  # Price close to support (Safe Long)
                return "yes"
            elif current_price >= resistance * 0.98:  # Price close to resistance (Risky Long)
                return "no"
            else:
                return "no"  # Neutral zone

        elif trade_type == "short":
            if current_price >= resistance * 0.98:  # Price close to resistance (Safe Short)
                return "yes"
            elif current_price <= support * 1.02:  # Price close to support (Risky Short)
                return "no"
            else:
                return "no"  # Neutral zone

    except Exception as e:
        print(f"Support/Resistance Error: {str(e)}")
        return "no"


def get_final_verdict(verdicts):
    yes_count = sum(1 for v in verdicts.values() if v == "yes")
    return "yes" if yes_count >= 6 else "no"  # Majority wins


def main():
    print("=== Crypto Trading Analysis Dashboard ===")

    # Get user inputs
    market_type = input("Choose Market Type (spot/futures): ").strip().lower()
    if market_type not in ["spot", "futures"]:
        print("Invalid market type. Choose 'spot' or 'futures'.")
        return

    symbol = input("Enter Crypto Pair (e.g., BTCUSDT): ").strip().upper()
    trade_type = input("Enter Trade Type (long/short): ").strip().lower()
    if trade_type not in ["long", "short"]:
        print("Invalid trade type. Choose 'long' or 'short'.")
        return

    time_unit = input("Choose Timeframe Unit (minutes/hours/days): ").strip().lower()
    if time_unit not in ["minutes", "hours", "days"]:
        print("Invalid timeframe unit. Choose minutes, hours, or days.")
        return

    time_value = input(f"Enter number of {time_unit} (e.g., 5 for 5 {time_unit}): ").strip()
    try:
        time_value = int(time_value)
    except ValueError:
        print("Invalid number. Please enter a valid integer.")
        return

    interval = f"{time_value}{time_unit[0]}"
    if interval not in VALID_TIMEFRAMES[time_unit]:
        print(f"Invalid timeframe. Supported: {', '.join(VALID_TIMEFRAMES[time_unit])}")
        return

    # Fetch data once
    try:
        df = fetch_ohlc_data(symbol, interval, market_type)
        current_price = get_current_price(symbol, market_type)
        print(f"\nCurrent {symbol} Price: ${current_price:.2f} | Timeframe: {interval}")
    except Exception as e:
        print(f"Error fetching data: {e}")
        return

    # Get all verdicts
    verdicts = {
        "ADX": adx_verdict(df.copy(), trade_type),
        "EMA": ema_verdict(df.copy(), trade_type),
        "Exchange Net Flow": netflow_verdict(symbol, market_type, trade_type),
        "Market Sentiment": sentiment_verdict(trade_type),
        "Miner Activity": miner_verdict(),
        "MACD": macd_verdict(df.copy(), trade_type),
        "Volume Profile": volume_profile_verdict(df.copy(), trade_type),
        "RSI": rsi_verdict(df.copy(), trade_type),
        "Smart Money": smc_verdict(df.copy(), trade_type),
        "Whale Activity": whale_verdict(symbol, trade_type),
        "Stochastic RSI": stoch_rsi_verdict(df.copy(), trade_type),
        "Support/Resistance": support_resistance_verdict(df.copy(), trade_type)
    }

    # Display results
    print("\n=== Analysis Results ===")
    for indicator, verdict in verdicts.items():
        print(f"{indicator: <20}: {verdict.upper()}")

    final_verdict = get_final_verdict(verdicts)
    print(f"\n=== FINAL VERDICT: {final_verdict.upper()} ===")


if __name__ == "__main__":
    main()
