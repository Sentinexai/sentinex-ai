import streamlit as st
from alpaca_trade_api.rest import REST, TimeFrame
import pandas as pd
import numpy as np
import time

# ========== CONFIGURATION ==========
API_KEY = 'PKHSYF5XH92B8VFNAJFD'
SECRET_KEY = '89KOB1vOSn2c3HeGorQe6zkKa0F4tFgBjbIAisCf'
BASE_URL = 'https://paper-api.alpaca.markets'

# ========== INIT ==========
api = REST(API_KEY, SECRET_KEY, BASE_URL)

st.set_page_config(page_title="Sentinex Sniper", layout="wide")
st.title("🤖 Sentinex Sniper Bot — Only A+ Trades! (Crypto Mode)")

# Calculate RSI
def calculate_rsi(prices, window=14):
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

# Get the historical data for a symbol
def get_data(symbol, tf=TimeFrame.Minute, limit=21):
    try:
        bars = api.get_bars(symbol, tf, limit=limit).df
        if bars.empty:
            st.error(f"Data is empty for {symbol}. Skipping.")
            return None
        return bars
    except Exception as e:
        st.error(f"Error fetching data for {symbol}: {str(e)}")
        return None

# Confluence Signal for buy/sell
def confluence_signal(bars):
    bars["rsi"] = calculate_rsi(bars["close"])
    bars["avg_vol"] = bars["volume"].rolling(21).mean()
    last = bars.iloc[-1]
    prev_high = bars["high"].max()
    if (
        last["rsi"] < 20 and
        last["volume"] > 2 * last["avg_vol"] and
        last["close"] > prev_high * 0.99
    ):
        return "BUY"
    elif last["rsi"] > 80:
        return "SELL"
    else:
        return None

# Fetch available crypto assets from Alpaca
def fetch_supported_crypto():
    try:
        assets = api.list_assets()
        crypto_assets = [asset.symbol for asset in assets if asset.type == 'crypto']
        return crypto_assets
    except Exception as e:
        st.error(f"Error fetching assets: {str(e)}")
        return []

# ========== MAIN LOGIC ==========
st.header("🔎 Scanning for A+ setups in Crypto...")

# Fetch supported crypto tickers from Alpaca
crypto_tickers = fetch_supported_crypto()
st.write(f"Found {len(crypto_tickers)} supported crypto tickers: {crypto_tickers}")

# Loop over available cryptos
for symbol in crypto_tickers:
    bars = get_data(symbol)
    if bars is None or len(bars) < 21:
        st.write(f"{symbol}: No data or error fetching data.")
        continue
    signal = confluence_signal(bars)
    st.write(f"{symbol}: {signal or 'No trade'}")
    # UNCOMMENT below for auto trading (be careful with real $)
    # if signal == "BUY":
    #     api.submit_order(symbol=symbol, qty=0.002, side='buy', type='market', time_in_force='gtc')
    # elif signal == "SELL":
    #     api.submit_order(symbol=symbol, qty=0.002, side='sell', type='market', time_in_force='gtc')

st.info("Simulating trades with small account size. Adjust accordingly for real trading. \nTo go fully auto, uncomment the 'submit_order' lines.")






