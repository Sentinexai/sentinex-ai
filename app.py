import streamlit as st
from alpaca_trade_api.rest import REST, TimeFrame
import pandas as pd
import numpy as np
import requests

# Configuration
API_KEY = 'YOUR_API_KEY'
SECRET_KEY = 'YOUR_SECRET_KEY'
BASE_URL = 'https://paper-api.alpaca.markets'

# Crypto and small cap tickers
CRYPTO_TICKERS = ["BTCUSD", "ETHUSD", "SOLUSD"]
SMALL_CAPS = ["NKLA", "MARA", "RIOT", "SNDL"]

LOOKBACK = 21  # RSI and volume calc
RSI_BUY = 20   # RSI buy threshold
RSI_SELL = 80  # RSI sell threshold
VOL_SPIKE = 2  # volume spike threshold

# Trade quantity for $500 sim
STOCK_QTY = 1
CRYPTO_QTY = 0.002

# Initialize Alpaca API
api = REST(API_KEY, SECRET_KEY, BASE_URL)

# Streamlit Configuration
st.set_page_config(page_title="Sentinex Sniper", layout="wide")
st.title("🤖 Sentinex Sniper Bot — Crypto & Small Caps")

# RSI calculation function
def calculate_rsi(prices, window=14):
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

# Get data function
def get_data(symbol, tf=TimeFrame.Minute, limit=LOOKBACK):
    try:
        bars = api.get_bars(symbol, tf, limit=limit).df
        return bars
    except Exception as e:
        return None

# Signal generation based on RSI and volume spike
def confluence_signal(bars, symbol):
    bars["rsi"] = calculate_rsi(bars["close"])
    bars["avg_vol"] = bars["volume"].rolling(LOOKBACK).mean()
    last = bars.iloc[-1]
    prev_high = bars["high"].max()
    
    # Get sentiment (using a placeholder for now)
    sentiment_score = 0.75  # Assume 75% positive sentiment
    
    if (
        last["rsi"] < RSI_BUY and
        last["volume"] > VOL_SPIKE * last["avg_vol"] and
        last["close"] > prev_high * 0.99 and
        sentiment_score > 0.5
    ):
        return "BUY"
    elif last["rsi"] > RSI_SELL:
        return "SELL"
    else:
        return None

# Stock Scan
st.header("🔎 Scanning for A+ setups in Small Caps...")

for symbol in SMALL_CAPS:
    bars = get_data(symbol)
    if bars is None or len(bars) < LOOKBACK:
        st.write(f"{symbol}: No data.")
        continue
    signal = confluence_signal(bars, symbol)
    st.write(f"{symbol}: {signal or 'No trade'}")
    # Uncomment for actual trading (on paper trading, this will execute a trade)
    # if signal == "BUY":
    #     api.submit_order(symbol=symbol, qty=STOCK_QTY, side='buy', type='market', time_in_force='gtc')
    # elif signal == "SELL":
    #     api.submit_order(symbol=symbol, qty=STOCK_QTY, side='sell', type='market', time_in_force='gtc')

# Crypto Scan
st.header("💎 Scanning for A+ setups in Crypto...")

for symbol in CRYPTO_TICKERS:
    bars = get_data(symbol)
    if bars is None or len(bars) < LOOKBACK:
        st.write(f"{symbol}: No data.")
        continue
    signal = confluence_signal(bars, symbol)
    st.write(f"{symbol}: {signal or 'No trade'}")
    # Uncomment for actual trading (on paper trading, this will execute a trade)
    # if signal == "BUY":
    #     api.submit_order(symbol=symbol, qty=CRYPTO_QTY, side='buy', type='market', time_in_force='gtc')
    # elif signal == "SELL":
    #     api.submit_order(symbol=symbol, qty=CRYPTO_QTY, side='sell', type='market', time_in_force='gtc')

st.info("Simulating a small account with paper trading. Modify quantity as necessary for real trading!")


