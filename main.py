import requests
import pandas as pd
import numpy as np
from collections import defaultdict
import random
from flask import Flask, request, jsonify
from flask_cors import CORS
import os

# Initialize Flask app
app = Flask(__name__)
CORS(app)

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


# ----------------------
# Core Analysis Functions (Keep all existing logic)
# ----------------------

#Formatting Prices

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

    numeric_cols = ["open", "high", "low", "close", "volume",
                    "quote_asset_volume", "taker_buy_base_asset_volume",
                    "taker_buy_quote_asset_volume"]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col])

    return df


def format_price(price):
    """Improved price formatting with comprehensive error handling"""
    try:
        # Convert to float (handles strings, numpy types, etc.)
        price = float(price)
        
        # Handle zero and NaN cases
        if price == 0 or pd.isna(price):
            return "0.00"
            
        abs_price = abs(price)
        
        # Determine formatting based on magnitude
        if abs_price < 0.000001:  # Extremely small values (0.00000089 -> 0.00000089)
            formatted = f"{price:.8f}"
        elif abs_price < 0.0001:   # Very small values (0.000234 -> 0.000234)
            formatted = f"{price:.6f}"
        elif abs_price < 1:        # Small values (0.00456 -> 0.0046)
            formatted = f"{price:.4f}"
        elif abs_price < 1000:     # Normal values (123.456 -> 123.46)
            formatted = f"{price:.2f}"
        else:                      # Large values (123456 -> 123456)
            formatted = f"{price:.0f}"
            
        # Clean up trailing zeros and decimal point if needed
        if '.' in formatted:
            formatted = formatted.rstrip('0').rstrip('.')
        return formatted
        
    except (ValueError, TypeError):
        return str(price)  # Fallback for non-convertible values


# 1. ADX Indicator (Corrected)
def adx_verdict(df, trade_type):
    try:
        df = df.copy()
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

        latest_adx = float(df["ADX"].iloc[-1]) if not pd.isna(df["ADX"].iloc[-1]) else 0
        latest_plus_di = float(df["+DI"].iloc[-1]) if not pd.isna(df["+DI"].iloc[-1]) else 0
        latest_minus_di = float(df["-DI"].iloc[-1]) if not pd.isna(df["-DI"].iloc[-1]) else 0

        verdict = "no"
        explanation = f"ADX: {format_price(latest_adx)} (Weak Trend)"
        if latest_adx > 25:
            verdict = "yes"
            explanation = f"ADX: {format_price(latest_adx)} (Strong Trend)"
            if trade_type == "long" and latest_plus_di > latest_minus_di:
                explanation += f" | +DI({format_price(latest_plus_di)}) > -DI({format_price(latest_minus_di)})"
            elif trade_type == "short" and latest_minus_di > latest_plus_di:
                explanation += f" | -DI({format_price(latest_minus_di)}) > +DI({format_price(latest_plus_di)})"

        return {"verdict": verdict, "explanation": explanation}
    except Exception as e:
        return {"verdict": "no", "explanation": f"ADX Error: {str(e)}"}


# 2. EMA Indicator (Corrected)
def ema_verdict(df, trade_type):
    try:
        df = df.copy()
        short_ma = float(df["close"].ewm(span=50, adjust=False).mean().iloc[-1])
        long_ma = float(df["close"].ewm(span=200, adjust=False).mean().iloc[-1])

        verdict = "no"
        explanation = f"EMA50: {format_price(short_ma)}, EMA200: {format_price(long_ma)}"

        if trade_type == "long":
            if short_ma > long_ma:
                verdict = "yes"
                explanation += " (Bullish Crossover)"
            else:
                explanation += " (No Bullish Crossover)"
        else:  # short
            if short_ma < long_ma:
                verdict = "yes"
                explanation += " (Bearish Crossover)"
            else:
                explanation += " (No Bearish Crossover)"

        return {"verdict": verdict, "explanation": explanation}
    except Exception as e:
        return {"verdict": "no", "explanation": f"EMA Error: {str(e)}"}


# 3. Exchange Net Flow (Corrected)
def netflow_verdict(symbol, market_type, trade_type):
    try:
        api_url = BINANCE_FUTURES_URL if market_type == "futures" else BINANCE_SPOT_URL
        response = requests.get(f"{api_url}/ticker/24hr?symbol={symbol.upper()}").json()
        quote_volume = float(response.get("quoteVolume", 0))
        asset_volume = float(response.get("volume", 0))
        netflow = asset_volume * 0.05  # Approximation

        verdict = "no"
        explanation = f"24h Vol: {format_price(asset_volume)} | Flow: {'+' if netflow >= 0 else ''}{format_price(netflow)}"
        if netflow < 0:
            if trade_type == "long":
                verdict = "yes"
                explanation += " (Outflow favors longs)"
        else:
            if trade_type == "short":
                verdict = "yes"
                explanation += " (Inflow favors shorts)"

        return {"verdict": verdict, "explanation": explanation}
    except Exception as e:
        return {"verdict": "no", "explanation": f"Flow Error: {str(e)}"}


# 4. Market Sentiment (Corrected)
def sentiment_verdict(trade_type):
    try:
        url = "https://api.alternative.me/fng/"
        response = requests.get(url).json()
        index_value = int(response["data"][0]["value"])

        verdict = "no"
        explanation = f"F&G Index: {index_value} - "

        if index_value <= 25:
            explanation += "Extreme Fear"
            if trade_type == "long":
                verdict = "yes"
        elif index_value >= 75:
            explanation += "Extreme Greed"
            if trade_type == "short":
                verdict = "yes"
        else:
            explanation += "Neutral"

        return {"verdict": verdict, "explanation": explanation}
    except Exception as e:
        return {"verdict": "no", "explanation": f"Sentiment Error: {str(e)}"}


# 5. Miner Activity (Corrected)
def miner_verdict():
    try:
        netflow = random.uniform(-1000, 1000)  # Simulated netflow
        verdict = "no"
        explanation = f"Miner Flow: {format_price(netflow)}"

        if netflow < 0:
            verdict = "yes"
            explanation += " (Miners holding)"
        else:
            explanation += " (Miners selling)"

        return {"verdict": verdict, "explanation": explanation}
    except Exception as e:
        return {"verdict": "no", "explanation": f"Miner Error: {str(e)}"}


# 6. MACD (Corrected)
def macd_verdict(df, trade_type):
    try:
        df = df.copy()
        df["EMA12"] = df["close"].ewm(span=12, adjust=False).mean()
        df["EMA26"] = df["close"].ewm(span=26, adjust=False).mean()
        df["MACD"] = df["EMA12"] - df["EMA26"]
        df["Signal_Line"] = df["MACD"].ewm(span=9, adjust=False).mean()

        latest_macd = float(df["MACD"].iloc[-1]) if not pd.isna(df["MACD"].iloc[-1]) else 0
        latest_signal = float(df["Signal_Line"].iloc[-1]) if not pd.isna(df["Signal_Line"].iloc[-1]) else 0

        verdict = "no"
        explanation = f"MACD: {format_price(latest_macd)}, Signal: {format_price(latest_signal)}"

        if latest_macd > latest_signal:
            if trade_type == "long":
                verdict = "yes"
                explanation += " (Bullish Crossover)"
            else:
                explanation += " (Bullish but trade mismatch)"
        else:
            if trade_type == "short":
                verdict = "yes"
                explanation += " (Bearish Crossover)"
            else:
                explanation += " (Bearish but trade mismatch)"

        return {"verdict": verdict, "explanation": explanation}
    except Exception as e:
        return {"verdict": "no", "explanation": f"MACD Error: {str(e)}"}


# 7. Volume Profile (Corrected)
def volume_profile_verdict(df, trade_type):
    try:
        df = df.copy()
        num_bins = 10
        price_min, price_max = float(df["close"].min()), float(df["close"].max())
        price_bins = np.linspace(price_min, price_max, num_bins + 1)

        volume_profile = defaultdict(float)
        for _, row in df.iterrows():
            price = float(row["close"])
            volume = float(row["volume"])
            for i in range(num_bins):
                if price_bins[i] <= price < price_bins[i + 1]:
                    volume_profile[price_bins[i]] += volume
                    break

        max_volume = max(volume_profile.values()) if volume_profile else 0
        strong_zones = {level: vol for level, vol in volume_profile.items() if vol >= max_volume * 0.7}
        current_price = float(df["close"].iloc[-1]) if not pd.isna(df["close"].iloc[-1]) else 0

        verdict = "no"
        explanation = f"Strong Zones: {len(strong_zones)} | Current Price: {format_price(current_price)}"

        if trade_type == "long":
            near_strong_zone = any(level <= current_price <= level + (price_bins[1] - price_bins[0])
                               for level in strong_zones)
            if near_strong_zone:
                verdict = "yes"
                explanation += " (Near support)"
            else:
                explanation += " (No strong support)"
        else:  # short
            near_weak_zone = not any(level <= current_price <= level + (price_bins[1] - price_bins[0])
                                 for level in strong_zones)
            if near_weak_zone:
                verdict = "yes"
                explanation += " (No strong resistance)"
            else:
                explanation += " (Near resistance)"

        return {"verdict": verdict, "explanation": explanation}
    except Exception as e:
        return {"verdict": "no", "explanation": f"Volume Error: {str(e)}"}


# 8. RSI (Corrected)
def rsi_verdict(df, trade_type):
    try:
        df = df.copy()
        period = 14
        delta = df["close"].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))

        latest_rsi = float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else 50

        verdict = "no"
        explanation = f"RSI: {format_price(latest_rsi)}"

        if latest_rsi < 30:
            explanation += " (Oversold)"
            if trade_type == "long":
                verdict = "yes"
        elif latest_rsi > 70:
            explanation += " (Overbought)"
            if trade_type == "short":
                verdict = "yes"
        else:
            explanation += " (Neutral)"

        return {"verdict": verdict, "explanation": explanation}
    except Exception as e:
        return {"verdict": "no", "explanation": f"RSI Error: {str(e)}"}


# 9. Smart Money Concept (Corrected)
def smc_verdict(df, trade_type):
    try:
        df = df.copy()
        highs = [float(x) for x in df["high"].values[-5:]]
        lows = [float(x) for x in df["low"].values[-5:]]
        closes = [float(x) for x in df["close"].values[-5:]]

        # Break of Structure detection
        if highs[-1] > highs[-2] and lows[-1] > lows[-2]:
            bos_signal = "bullish"
        elif highs[-1] < highs[-2] and lows[-1] < lows[-2]:
            bos_signal = "bearish"
        else:
            bos_signal = "neutral"

        # Order blocks
        bullish_ob = min(lows) if lows else 0
        bearish_ob = max(highs) if highs else 0
        current_price = closes[-1] if closes else 0

        verdict = "no"
        explanation = f"BoS: {bos_signal} | Bullish OB: {format_price(bullish_ob)} | Bearish OB: {format_price(bearish_ob)}"

        if trade_type == "long":
            if bos_signal == "bullish" or current_price >= bullish_ob * 0.98:
                verdict = "yes"
                explanation += " (Bullish confirmation)"
        else:  # short
            if bos_signal == "bearish" or current_price <= bearish_ob * 1.02:
                verdict = "yes"
                explanation += " (Bearish confirmation)"

        return {"verdict": verdict, "explanation": explanation}
    except Exception as e:
        return {"verdict": "no", "explanation": f"SMC Error: {str(e)}"}


# 10. Whale Activity (Corrected)
def whale_verdict(symbol, trade_type):
    try:
        response = requests.get(f"{BINANCE_ORDER_BOOK_API_URL}?symbol={symbol.upper()}&limit=500").json()
        bids = [(float(price), float(qty)) for price, qty in response.get("bids", [])]
        asks = [(float(price), float(qty)) for price, qty in response.get("asks", [])]

        large_buys = sum(qty for price, qty in bids if qty > WHALE_TRADE_THRESHOLD)
        large_sells = sum(qty for price, qty in asks if qty > WHALE_TRADE_THRESHOLD)

        verdict = "no"
        explanation = f"Whale Buys: {format_price(large_buys)} | Whale Sells: {format_price(large_sells)}"

        if large_buys > large_sells * 1.5:  # 50% more buys than sells
            if trade_type == "long":
                verdict = "yes"
                explanation += " (Strong buying pressure)"
        elif large_sells > large_buys * 1.5:
            if trade_type == "short":
                verdict = "yes"
                explanation += " (Strong selling pressure)"

        return {"verdict": verdict, "explanation": explanation}
    except Exception as e:
        return {"verdict": "no", "explanation": f"Whale Error: {str(e)}"}


# 11. Stochastic RSI (Corrected)
def stoch_rsi_verdict(df, trade_type):
    try:
        df = df.copy()
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

        latest_stoch_rsi = float(stoch_rsi.iloc[-1]) if not pd.isna(stoch_rsi.iloc[-1]) else 50

        verdict = "no"
        explanation = f"StochRSI: {format_price(latest_stoch_rsi)}"

        if latest_stoch_rsi < 20:
            explanation += " (Oversold)"
            if trade_type == "long":
                verdict = "yes"
        elif latest_stoch_rsi > 80:
            explanation += " (Overbought)"
            if trade_type == "short":
                verdict = "yes"
        else:
            explanation += " (Neutral)"

        return {"verdict": verdict, "explanation": explanation}
    except Exception as e:
        return {"verdict": "no", "explanation": f"StochRSI Error: {str(e)}"}


# 12. Support/Resistance (Corrected)
def support_resistance_verdict(df, trade_type):
    try:
        df = df.copy()
        # Get significant levels
        highs = [float(x) for x in df["high"].values[-50:]]  # Last 50 periods
        lows = [float(x) for x in df["low"].values[-50:]]

        # Find key levels using clustering
        levels = []
        for _ in range(3):  # Find top 3 levels
            if not highs or not lows:
                break
            resistance = max(highs)
            support = min(lows)
            levels.extend([support, resistance])
            
            # Remove values near these levels
            highs = [h for h in highs if not (resistance * 0.99 <= h <= resistance * 1.01)]
            lows = [l for l in lows if not (support * 0.99 <= l <= support * 1.01)]

        # Sort and remove duplicates
        levels = sorted(list(set(levels)))
        current_price = float(df["close"].iloc[-1]) if not pd.isna(df["close"].iloc[-1]) else 0

        # Find nearest levels
        supports = [l for l in levels if l < current_price]
        resistances = [l for l in levels if l > current_price]
        nearest_support = max(supports) if supports else None
        nearest_resistance = min(resistances) if resistances else None

        verdict = "no"
        explanation = f"Levels: S[{', '.join(format_price(s) for s in supports)}] | "
        explanation += f"R[{', '.join(format_price(r) for r in resistances)}] | "
        explanation += f"Current: {format_price(current_price)}"

        if trade_type == "long":
            if nearest_support and (current_price <= nearest_support * 1.02):
                verdict = "yes"
                explanation += f" (Near strong support at {format_price(nearest_support)})"
            elif nearest_resistance and (current_price >= nearest_resistance * 0.98):
                explanation += f" (Approaching resistance at {format_price(nearest_resistance)})"
            else:
                explanation += " (Between levels)"
        else:  # short
            if nearest_resistance and (current_price >= nearest_resistance * 0.98):
                verdict = "yes"
                explanation += f" (Near strong resistance at {format_price(nearest_resistance)})"
            elif nearest_support and (current_price <= nearest_support * 1.02):
                explanation += f" (Approaching support at {format_price(nearest_support)})"
            else:
                explanation += " (Between levels)"

        return {"verdict": verdict, "explanation": explanation}
    except Exception as e:
        return {"verdict": "no", "explanation": f"S/R Error: {str(e)}"}


def get_final_verdict(verdicts):
    yes_indicators = [indicator for indicator, data in verdicts.items() if data["verdict"] == "yes"]
    no_indicators = [indicator for indicator, data in verdicts.items() if data["verdict"] == "no"]
    confidence_level = len(yes_indicators)

    if confidence_level >= 9:
        confidence = "✅ EXTREME CONFIDENCE"
        emoji = "🚀🚀🚀"
    elif confidence_level >= 7:
        confidence = "👍 HIGH CONFIDENCE"
        emoji = "🚀🚀"
    elif confidence_level >= 6:
        confidence = "🟢 SOLID"
        emoji = "🚀"
    elif confidence_level >= 4:
        confidence = "⚠️ CAUTION"
        emoji = "⚠️"
    else:
        confidence = "🔴 CONFIRM LOSS"
        emoji = "🛑"

    return {
        "verdict": "yes" if confidence_level >= 6 else "no",
        "score": f"{confidence_level}/12",
        "confidence": confidence,
        "emoji": emoji,
        "yes_indicators": yes_indicators,
        "no_indicators": no_indicators,
        "confidence_level": confidence_level
    }

def get_trading_advice(final_verdict, trade_type):
    advice = ""
    confidence_level = final_verdict["confidence_level"]
    
    if confidence_level >= 9:
        advice = f"  {final_verdict['emoji']} STRONG SIGNAL! Consider aggressive position sizing"
    elif confidence_level >= 7:
        advice = f"  {final_verdict['emoji']} Good opportunity, standard position recommended"
    elif confidence_level >= 6:
        advice = f"  {final_verdict['emoji']} Decent setup, consider smaller position"
    elif confidence_level >= 4:
        advice = "  ⚠️ Marginal setup - wait for confirmation"
    else:
        advice = "  🚫 Avoid this trade - too many red flags"
    
    return advice

def get_better_alternatives(final_verdict, trade_type):
    alternatives = []
    confidence_level = final_verdict["confidence_level"]
    
    if confidence_level >= 7:
        if trade_type == "long":
            alternatives.append("Consider scaling in at key support levels")
        else:
            alternatives.append("Consider scaling in at key resistance levels")
    elif confidence_level >= 4:
        alternatives.append("Wait for stronger confirmation signals")
        alternatives.append(f"Check lower timeframes for better {'long' if trade_type == 'long' else 'short'} entry")
    else:
        alternatives.append("Consider waiting for market conditions to improve")
        alternatives.append(f"Look for opposite {'short' if trade_type == 'long' else 'long'} opportunities")
    
    if trade_type == "long":
        alternatives.append("Watch for bullish reversal patterns")
    else:
        alternatives.append("Watch for bearish continuation patterns")
    
    return alternatives

def get_quick_summary(results):
    """Generate a concise summary of the analysis results"""
    try:
        summary = (
            f"• Current Price: ${format_price(results.get('current_price', 0))}\n"
            f"• Timeframe: {results.get('timeframe', 'N/A')}\n"
            f"• Trade Type: {results.get('trade_type', '').upper()}\n"
            f"• Confidence Score: {results.get('final_verdict', {}).get('score', '0/12')} "
            f"({results.get('final_verdict', {}).get('confidence', 'N/A')})"
        )
        
                
        return summary
    except Exception as e:
        return f"Summary Error: {str(e)}"

def display_final_verdict(final, trade_type):
    print("\n" + "=" * 60)

    if final["verdict"] == "yes":
        print(f"{final['emoji']} {'FINAL VERDICT: GO ' + trade_type.upper() + '!':^50} {final['emoji']}")
        print(f"{'🔥 ' + final['confidence'] + ' 🔥':^60}")
    else:
        print(f"{final['emoji']} {'FINAL VERDICT: AVOID ' + trade_type.upper():^50} {final['emoji']}")
        print(f"{'❌ ' + final['confidence'] + ' ❌':^60}")

    print("=" * 60)
    print(f"📊 SCORE: {final['score']} indicators agree")
    print("\n🔍 BREAKDOWN:")
    print(f"✅ {len(final['yes_indicators'])} Supporting:")
    print("   " + ", ".join(final['yes_indicators']))
    print(f"\n❌ {len(final['no_indicators'])} Against:")
    print("   " + ", ".join(final['no_indicators']))

    # Trading advice based on confidence level
    print("\n💡 PRO TRADER ADVICE:")
    if final["confidence_level"] >= 9:
        print(f"  {final['emoji']} STRONG SIGNAL! Consider aggressive position sizing")
    elif final["confidence_level"] >= 7:
        print(f"  {final['emoji']} Good opportunity, standard position recommended")
    elif final["confidence_level"] >= 6:
        print(f"  {final['emoji']} Decent setup, consider smaller position")
    elif final["confidence_level"] >= 4:
        print(f"  ⚠️ Marginal setup - wait for confirmation")
    else:
        print(f"  🚫 Avoid this trade - too many red flags")

    print("=" * 60)


def display_indicator_results(verdicts, symbol, current_price, timeframe):
    """Display formatted indicator results with proper price formatting"""
    try:
        output = []
        output.append(f"\n📈 {symbol} INDICATOR RESULTS 📉")
        output.append(f"💰 Current Price: ${format_price(current_price)} | ⏳ Timeframe: {timeframe}\n")

        # Indicator icons mapping
        INDICATOR_ICONS = {
            "ADX": "📶", "EMA": "📉📈", "Exchange Net Flow": "💸",
            "Market Sentiment": "😨😊", "Miner Activity": "⛏️", "MACD": "✖️",
            "Volume Profile": "📊", "RSI": "🔽🔼", "Smart Money": "🐋",
            "Whale Activity": "🐳", "Stochastic RSI": "🔄", "Support/Resistance": "⏹️"
        }

        # Process each indicator
        for indicator, data in verdicts.items():
            icon = INDICATOR_ICONS.get(indicator, "▪️")
            verdict_emoji = "✅" if data.get("verdict") == "yes" else "❌"
            
            output.append(f"{icon} {indicator}:")
            output.append(f"   → {data.get('explanation', 'No data')}")
            output.append(f"   → VERDICT: {verdict_emoji} {data.get('verdict', 'N/A').upper()}\n")

        output.append("=" * 60)
        return "\n".join(output)
    except Exception as e:
        return f"Error displaying results: {str(e)}"
def check_coin_availability(symbol, market_type):
    """Check if trading data exists for the given symbol"""
    try:
        base_url = BINANCE_FUTURES_URL if market_type == "futures" else BINANCE_SPOT_URL
        url = f"{base_url}/ticker/price?symbol={symbol.upper()}"
        response = requests.get(url)

        if response.status_code == 200:
            return True
        elif response.status_code == 400:
            error_msg = response.json().get('msg', '')
            if "Invalid symbol" in error_msg:
                return False
        return False
    except Exception:
        return False

def calculate_target_prices(df, current_price, trade_type):
    """Calculate target prices based on technical levels"""
    targets = {}
    
    # Calculate recent volatility (ATR)
    atr = calculate_atr(df)
    
    # Support/Resistance levels
    support, resistance = calculate_support_resistance(df)
    
    if trade_type == "long":
        # Conservative target (1x ATR)
        targets['conservative'] = current_price + atr
        # Moderate target (2x ATR)
        targets['moderate'] = current_price + (2 * atr)
        # Aggressive target (next resistance)
        targets['aggressive'] = resistance if resistance > current_price else current_price + (3 * atr)
        # Stop loss
        targets['stop_loss'] = max(support, current_price - (2 * atr))
    else:  # short
        # Conservative target (1x ATR)
        targets['conservative'] = current_price - atr
        # Moderate target (2x ATR)
        targets['moderate'] = current_price - (2 * atr)
        # Aggressive target (next support)
        targets['aggressive'] = support if support < current_price else current_price - (3 * atr)
        # Stop loss
        targets['stop_loss'] = min(resistance, current_price + (2 * atr))
    
    return targets

def calculate_atr(df, period=14):
    """Calculate Average True Range"""
    high_low = df['high'] - df['low']
    high_close = abs(df['high'] - df['close'].shift())
    low_close = abs(df['low'] - df['close'].shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    return tr.rolling(period).mean().iloc[-1]

def calculate_support_resistance(df, lookback=50):
    """Identify key support and resistance levels"""
    recent_data = df.iloc[-lookback:]
    support = recent_data['low'].min()
    resistance = recent_data['high'].max()
    return support, resistance

# ----------------------
# Results Formatting Functions
# ----------------------

def format_console_output(results):
    """Convert analysis results to beautiful console-style text with proper formatting"""
    try:
        output = []
        
        # 1. Header with price info
        output.append(f"\n📈 {results.get('symbol', '')} Analysis Results 📉")
        output.append(f"💰 Current Price: ${format_price(results.get('current_price', 0))} | "
                    f"⏳ Timeframe: {results.get('timeframe', 'N/A')}\n")

        # 2. Indicator results with icons
        icons = {
            "ADX": "📶", "EMA": "📉📈", "Exchange Net Flow": "💸",
            "Market Sentiment": "😨😊", "Miner Activity": "⛏️", "MACD": "✖️",
            "Volume Profile": "📊", "RSI": "🔽🔼", "Smart Money": "🐋",
            "Whale Activity": "🐳", "Stochastic RSI": "🔄", "Support/Resistance": "⏹️"
        }

        for name, data in results.get('verdicts', {}).items():
            output.append(f"{icons.get(name, '▪️')} {name}:")
            output.append(f"   → {data.get('explanation', 'No data available')}")
            output.append(f"   → VERDICT: {'✅ YES' if data.get('verdict') == 'yes' else '❌ NO'}\n")

        # 3. Final verdict section
        final_verdict = results.get('final_verdict', {})
        output.append("=" * 60)
        verdict_text = "GO " if final_verdict.get('verdict') == 'yes' else 'AVOID '
        output.append(
            f"\n{final_verdict.get('emoji', '')} "
            f"FINAL VERDICT: {verdict_text}{results.get('trade_type', '').upper()}! "
            f"{final_verdict.get('emoji', '')}"
        )
        output.append(f"{'🔥 ' + final_verdict.get('confidence', '') + ' 🔥':^60}")
        output.append("=" * 60)
        output.append(f"📊 SCORE: {final_verdict.get('score', '0/12')} indicators agree")

        # 4. Breakdown of supporting/contrary indicators
        output.append("\n🔍 BREAKDOWN:")
        output.append(f"✅ {len(final_verdict.get('yes_indicators', []))} Supporting:")
        output.append("   " + ", ".join(final_verdict.get('yes_indicators', ['None'])))
        output.append(f"\n❌ {len(final_verdict.get('no_indicators', []))} Against:")
        output.append("   " + ", ".join(final_verdict.get('no_indicators', ['None'])))

        # 5. Trading advice
        output.append("\n💡 PRO TRADER ADVICE:")
        output.append(get_trading_advice(final_verdict, results.get('trade_type', '')))

        # 6. Price targets if available
        if 'structured_data' in results and 'targets' in results['structured_data']:
            targets = results['structured_data']['targets']
            current_price = float(results.get('current_price', 0))
            output.append("\n🎯 PRICE TARGETS:")
            output.append(f"• Current Price: ${format_price(current_price)}")
            
            if results.get('trade_type') == 'long':
                output.append(
                    f"➤ Conservative: ${format_price(targets.get('conservative', 0))} "
                    f"(+{format_price(targets.get('conservative', 0) - current_price)})"
                )
                output.append(
                    f"➤ Moderate: ${format_price(targets.get('moderate', 0))} "
                    f"(+{format_price(targets.get('moderate', 0) - current_price)})"
                )
                output.append(
                    f"➤ Aggressive: ${format_price(targets.get('aggressive', 0))} "
                    f"(+{format_price(targets.get('aggressive', 0) - current_price)})"
                )
                output.append(
                    f"⛔ Stop Loss: ${format_price(targets.get('stop_loss', 0))} "
                    f"(-{format_price(current_price - targets.get('stop_loss', 0))})"
                )
            else:
                output.append(
                    f"➤ Conservative: ${format_price(targets.get('conservative', 0))} "
                    f"(-{format_price(current_price - targets.get('conservative', 0))})"
                )
                output.append(
                    f"➤ Moderate: ${format_price(targets.get('moderate', 0))} "
                    f"(-{format_price(current_price - targets.get('moderate', 0))})"
                )
                output.append(
                    f"➤ Aggressive: ${format_price(targets.get('aggressive', 0))} "
                    f"(-{format_price(current_price - targets.get('aggressive', 0))})"
                )
                output.append(
                    f"⛔ Stop Loss: ${format_price(targets.get('stop_loss', 0))} "
                    f"(+{format_price(targets.get('stop_loss', 0) - current_price)})"
                )

        # 7. Quick summary
        output.append("\n📝 QUICK SUMMARY:")
        output.append(get_quick_summary(results))

        # 8. Better alternatives
        output.append("\n🔄 BETTER ALTERNATIVES:")
        alternatives = get_better_alternatives(final_verdict, results.get('trade_type', ''))
        for alt in alternatives:
            output.append(f"- {alt}")

        output.append("=" * 60)
        output.append("💎 Remember: No indicator is perfect - always manage risk!")
        output.append("=" * 60)

        return "\n".join(output)
    except Exception as e:
        return f"Error formatting output: {str(e)}"


# ----------------------
# API Endpoint
# ----------------------

@app.route('/analyze', methods=['POST'])
def api_analyze():
    try:
        params = request.json

        # Validate inputs
        required_fields = ['market_type', 'symbol', 'trade_type', 'time_unit', 'time_value']
        for field in required_fields:
            if field not in params:
                return jsonify({'error': f'Missing required field: {field}'}), 400

        # Check if coin exists
        if not check_coin_availability(params['symbol'], params['market_type']):
            return jsonify({'error': 'Invalid coin pair. Please check the symbol and market type.'}), 400

        # Get current price
        current_price = get_current_price(params['symbol'], params['market_type'])
        
        # Fetch OHLC data
        df = fetch_ohlc_data(
            params['symbol'],
            f"{params['time_value']}{params['time_unit'][0]}",
            params['market_type']
        )

        # Calculate price targets
        targets = calculate_target_prices(df, current_price, params['trade_type'])

        # Run all indicator analyses
        verdicts = {
            "ADX": adx_verdict(df.copy(), params['trade_type']),
            "EMA": ema_verdict(df.copy(), params['trade_type']),
            "Exchange Net Flow": netflow_verdict(params['symbol'], params['market_type'], params['trade_type']),
            "Market Sentiment": sentiment_verdict(params['trade_type']),
            "Miner Activity": miner_verdict(),
            "MACD": macd_verdict(df.copy(), params['trade_type']),
            "Volume Profile": volume_profile_verdict(df.copy(), params['trade_type']),
            "RSI": rsi_verdict(df.copy(), params['trade_type']),
            "Smart Money": smc_verdict(df.copy(), params['trade_type']),
            "Whale Activity": whale_verdict(params['symbol'], params['trade_type']),
            "Stochastic RSI": stoch_rsi_verdict(df.copy(), params['trade_type']),
            "Support/Resistance": support_resistance_verdict(df.copy(), params['trade_type'])
        }

        # Get final verdict
        final_verdict = get_final_verdict(verdicts)

        # Prepare complete results
        results = {
            'symbol': params['symbol'],
            'market_type': params['market_type'],
            'trade_type': params['trade_type'],
            'timeframe': f"{params['time_value']}{params['time_unit'][0]}",
            'current_price': current_price,
            'verdicts': verdicts,
            'final_verdict': final_verdict,
            'structured_data': {
                'indicators': verdicts,
                'final_verdict': final_verdict,
                'price': current_price,
                'targets': targets
            }
        }

        return jsonify({
            'console_output': format_console_output(results),
            'structured_data': results['structured_data']
        })

    except Exception as e:
        if "single positional indexer is out-of-bounds" in str(e):
            return jsonify({'error': 'Invalid coin pair or timeframe. Please check your inputs.'}), 400
        return jsonify({'error': str(e)}), 500
# ----------------------
# CLI Entry Point (Keeps original functionality)
# ----------------------

def main():
    print("=== Crypto Trading Analysis Dashboard ===")

    # Get user inputs
    market_type = input("Choose Market Type (spot/futures): ").strip().lower()
    symbol = input("Enter Crypto Pair (e.g., BTCUSDT): ").strip().upper()
    trade_type = input("Enter Trade Type (long/short): ").strip().lower()
    time_unit = input("Choose Timeframe Unit (minutes/hours/days): ").strip().lower()
    time_value = input(f"Enter number of {time_unit}: ").strip()

    try:
        # Run analysis
        df = fetch_ohlc_data(
            symbol,
            f"{time_value}{time_unit[0]}",
            market_type
        )

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

        final = get_final_verdict(verdicts)

        # Format and print results
        results = {
            'symbol': symbol,
            'market_type': market_type,
            'trade_type': trade_type,
            'timeframe': f"{time_value}{time_unit[0]}",
            'current_price': get_current_price(symbol, market_type),
            'verdicts': verdicts,
            'final_verdict': final
        }

        print(format_console_output(results))

    except Exception as e:
        print(f"\n❌ Error: {str(e)}")


if __name__ == '__main__':
    if os.environ.get('WEB_MODE'):
        app.run(debug=True, port=5000)
    else:
        main()