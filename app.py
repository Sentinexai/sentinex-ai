import streamlit as st
from alpaca_trade_api.rest import REST, TimeFrame
import pandas as pd
import numpy as np
import requests
import logging

# Setting up basic logging
logging.basicConfig(level=logging.INFO)

# ========== CONFIGURATION ==========
API_KEY = ''PKHSYF5XH92B8VFNAJFD'
SECRET_KEY = '89KOB1vOSn2c3HeGorQe6zkKa0F4tFgBjbIAisCf'
BASE_URL = 'https://paper-api.alpaca.markets'

# List of crypto tickers (modify as needed)
CRYPTO_TICKERS = [
    "BTCUSD", "ETHUSD", "SOLUSD", "DOGEUSD", "SHIBUSD", "AVAXUSD", "ADAUSD", "MATICUSD",
    "XRPUSD", "LINKUSD", "PEPEUSD", "WIFUSD", "ARBUSD", "SEIUSD", "TONUSD",
    "BNBUSD", "RNDRUSD", "INJUSD", "TIAUSD"
]

LOOKBACK = 21  # Minutes for RSI and volume calculation
RSI_BUY = 20   # RSI buy threshold
RSI_SELL = 80  # RSI sell threshold
VOL_SPIKE = 2  # x avg volume spike
CRYPTO_QTY = 0.002  # Example: 0.002 BTC ≈ $15-20 per trade

# ========== INIT ==========
api = REST(API_KEY, SECRET_KEY, BASE_URL)

st.set_page_config(page_title="Sentinex Sniper", layout="wide")
st.title("🤖 Sentinex Sniper Bot — Only A+ Trades! (Crypto Mode)")

def calculate_rsi(prices, window=14):
    """Calculate the RSI (Relative Strength Index)"""
    prices = pd.Series(prices)
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def add_rsi(bars):
    """Calculate RSI and add it to the bars DataFrame."""
    bars['rsi'] = calculate_rsi(bars['close'])
    return bars

def get_data(symbol, tf=TimeFrame.Minute, limit=LOOKBACK):
    """Fetch historical price data for the given symbol"""
    try:
        bars = api.get_bars(symbol, tf, limit=limit).df
        return bars
    except Exception as e:
        logging.error(f"Error fetching data for {symbol}: {e}")
        return None

def get_sentiment(symbol):
    """Fetch sentiment data for the given symbol from an external API"""
    sentiment_url = f"https://api.sentimentapi.com/{symbol}"
    try:
        response = requests.get(sentiment_url)
        sentiment_score = response.json().get('score', 0)  # Adjust as necessary
        return sentiment_score
    except Exception as e:
        logging.error(f"Error fetching sentiment for {symbol}: {e}")
        return 0

def confluence_signal(bars, symbol):
    """Generate a buy/sell signal based on RSI, volume spike, and sentiment"""
    if 'symbol' not in bars.columns:
        logging.error(f"Missing symbol column for {symbol}")
        return None

    bars["avg_vol"] = bars["volume"].rolling(LOOKBACK).mean()

    last = bars.iloc[-1]
    prev_high = bars["high"].max()

    # Get sentiment score using the symbol
    sentiment_score = get_sentiment(symbol)

    if (
        last["rsi"] < RSI_BUY and
        last["volume"] > VOL_SPIKE * last["avg_vol"] and
        last["close"] > prev_high * 0.99
    ):
        return "BUY"
    elif last["rsi"] > RSI_SELL:
        return "SELL"
    else:
        return None

# ========== MAIN LOGIC ==========
st.header("🔎 Scanning for A+ setups in Crypto...")

for symbol in CRYPTO_TICKERS:
    bars = get_data(symbol)
    if bars is None or len(bars) < LOOKBACK:
        st.write(f"{symbol}: No data.")
        continue
    
    # Calculate RSI
    bars = add_rsi(bars)
    bars.dropna(inplace=True)  # Ensure no NaN values

    signal = confluence_signal(bars, symbol)
    st.write(f"{symbol}: {signal or 'No trade'}")
    
    # Uncomment below for auto trading (be careful with real $)
    # if signal == "BUY":
    #     api.submit_order(symbol=symbol, qty=CRYPTO_QTY, side='buy', type='market', time_in_force='gtc')
    # elif signal == "SELL":
    #     api.submit_order(symbol=symbol, qty=CRYPTO_QTY, side='sell', type='market', time_in_force='gtc')

st.info("Simulating trades with small account size. Adjust quantities and risk settings accordingly for real trading. To go fully auto, uncomment the 'submit_order' lines.")
