import streamlit as st
from alpaca_trade_api.rest import REST, TimeFrame
import pandas as pd
import numpy as np
import requests
import time
from requests.exceptions import ConnectionError, Timeout, RequestException

# ========== CONFIGURATION ==========
API_KEY = 'PKHSYF5XH92B8VFNAJFD'
SECRET_KEY = '89KOB1vOSn2c3HeGorQe6zkKa0F4tFgBjbIAisCf'
BASE_URL = 'https://paper-api.alpaca.markets'

# Expanded small cap list (update as you like)
SMALL_CAPS = [
    "NKLA", "MARA", "RIOT", "SNDL", "SOFI", "PLTR", "CLSK", "BBBY", "TLRY", "IDEX",
    "GME", "AMC", "CVNA", "AI", "NVAX", "BBBYQ", "LCID", "TSLA", "NIO", "BILI",
    "FFIE", "APE", "AMTD", "CEI", "VERU", "IONQ", "QS", "DNA", "OSTK", "VYNE", "BBIG"
]

# Expanded crypto list (update as you like)
CRYPTO_TICKERS = [
    "BTCUSD", "ETHUSD", "SOLUSD", "DOGEUSD", "SHIBUSD", "AVAXUSD", "ADAUSD", "MATICUSD",
    "XRPUSD", "LINKUSD", "OPUSD", "PEPEUSD", "WIFUSD", "ARBUSD", "SEIUSD", "TONUSD",
    "BNBUSD", "RNDRUSD", "INJUSD", "TIAUSD"
]

LOOKBACK = 21  # Minutes for RSI and volume calc
RSI_BUY = 20   # RSI buy threshold
RSI_SELL = 80  # RSI sell threshold
VOL_SPIKE = 2  # x avg volume spike

# Use small size for simulation (e.g., $20-25 per trade)
STOCK_QTY = 1
CRYPTO_QTY = 0.002  # e.g., 0.002 BTC ≈ $15-20

# ========== INIT ==========
api = REST(API_KEY, SECRET_KEY, BASE_URL)

st.set_page_config(page_title="Sentinex Sniper", layout="wide")
st.title("🤖 Sentinex Sniper Bot — Only A+ Trades! ($500 Paper Trading Sim)")

def calculate_rsi(prices, window=14):
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def get_data(symbol, tf=TimeFrame.Minute, limit=LOOKBACK):
    try:
        bars = api.get_bars(symbol, tf, limit=limit).df
        return bars
    except Exception as e:
        st.error(f"Error fetching data for {symbol}: {e}")
        return None

def get_sentiment(symbol):
    sentiment_url = f'https://api.sentimentanalysis.com/{symbol}'  # Replace with actual sentiment API URL
    try:
        response = requests.get(sentiment_url)
        response.raise_for_status()  # Check for any HTTP errors
        sentiment_score = response.json().get('score', 0)
        return sentiment_score
    except (ConnectionError, Timeout) as e:
        st.error(f"Network error: {e}")
    except RequestException as e:
        st.error(f"Request error: {e}")
    return 0  # Return default score if there's an issue

def confluence_signal(bars):
    bars["rsi"] = calculate_rsi(bars["close"])
    bars["avg_vol"] = bars["volume"].rolling(LOOKBACK).mean()
    last = bars.iloc[-1]
    prev_high = bars["high"].max()
    sentiment_score = get_sentiment(last["symbol"])
    
    if (
        last["rsi"] < RSI_BUY and
        last["volume"] > VOL_SPIKE * last["avg_vol"] and
        last["close"] > prev_high * 0.99 and
        sentiment_score > 0  # Sentiment must be positive
    ):
        return "BUY"
    elif last["rsi"] > RSI_SELL:
        return "SELL"
    else:
        return None

def get_data_with_retry(symbol, retries=3, delay=5):
    for _ in range(retries):
        bars = get_data(symbol)
        if bars is not None:
            return bars
        st.write(f"Retrying data for {symbol}...")
        time.sleep(delay)
    return None

# ========== MAIN LOGIC ==========
st.header("🔎 Scanning for A+ setups in Small Caps...")

for symbol in SMALL_CAPS:
    bars = get_data_with_retry(symbol)
    if bars is None or len(bars) < LOOKBACK:
        st.write(f"{symbol}: No data.")
        continue
    signal = confluence_signal(bars)
    st.write(f"{symbol}: {signal or 'No trade'}")
    # UNCOMMENT below for auto trading (be careful with real $)
    # if signal == "BUY":
    #     api.submit_order(symbol=symbol, qty=STOCK_QTY, side='buy', type='market', time_in_force='gtc')
    # elif signal == "SELL":
    #     api.submit_order(symbol=symbol, qty=STOCK_QTY, side='sell', type='market', time_in_force='gtc')

st.header("💎 Crypto Mode (A+ signals)")

for symbol in CRYPTO_TICKERS:
    bars = get_data_with_retry(symbol)
    if bars is None or len(bars) < LOOKBACK:
        st.write(f"{symbol}: No data.")
        continue
    signal = confluence_signal(bars)
    st.write(f"{symbol}: {signal or 'No trade'}")
    # UNCOMMENT below for auto trading (be careful with real $)
    # if signal == "BUY":
    #     api.submit_order(symbol=symbol, qty=CRYPTO_QTY, side='buy', type='market', time_in_force='gtc')
    # elif signal == "SELL":
    #     api.submit_order(symbol=symbol, qty=CRYPTO_QTY, side='sell', type='market', time_in_force='gtc')

st.info("Simulating trades for $500 account with small position sizes. To go fully auto, uncomment the 'submit_order' lines.\nWant to improve with trailing stops, sentiment, or more? Let me know!")

