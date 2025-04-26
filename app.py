import streamlit as st
from alpaca_trade_api.rest import REST, TimeFrame
import pandas as pd
import numpy as np
import time

# ========== CONFIGURATION ==========

API_KEY = 'PKHSYF5XH92B8VFNAJFD'
SECRET_KEY = '89KOB1vOSn2c3HeGorQe6zkKa0F4tFgBjbIAisCf'
BASE_URL = 'https://paper-api.alpaca.markets'

# Crypto tickers for scanning
CRYPTO_TICKERS = [
    "BTCUSD", "ETHUSD", "SOLUSD", "DOGEUSD", "SHIBUSD", "AVAXUSD", "ADAUSD", "MATICUSD",
    "XRPUSD", "LINKUSD", "PEPEUSD", "WIFUSD", "ARBUSD", "SEIUSD", "TONUSD", "BNBUSD", "RNDRUSD", "INJUSD", "TIAUSD"
]

LOOKBACK = 21  # Minutes for RSI and volume calc
RSI_BUY = 20   # RSI buy threshold
RSI_SELL = 80  # RSI sell threshold
VOL_SPIKE = 2  # x avg volume spike

CRYPTO_QTY = 0.002  # Quantity for each crypto trade (adjust size based on your preference)

# ========== INIT ==========

api = REST(API_KEY, SECRET_KEY, BASE_URL)

st.set_page_config(page_title="Sentinex Sniper Bot", layout="wide")
st.title("🤖 Sentinex Sniper Bot — Only A+ Trades! (Crypto Mode)")

# ========== DATA FETCHING ==========

# Function to fetch data for supported cryptos dynamically from Alpaca
def fetch_supported_crypto():
    try:
        assets = api.list_assets()
        crypto_assets = [asset.symbol for asset in assets if asset.asset_class == 'crypto']
        return crypto_assets
    except Exception as e:
        st.error(f"Error fetching assets: {str(e)}")
        return []

# Get the historical data for a symbol
def get_data(symbol, tf=TimeFrame.Minute, limit=LOOKBACK):
    try:
        bars = api.get_bars(symbol, tf, limit=limit).df
        return bars
    except Exception as e:
        st.error(f"Error fetching data for {symbol}: {str(e)}")
        return None

# Calculate RSI for the price data
def calculate_rsi(prices, window=14):
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

# Confluence Signal for Buy/Sell
def confluence_signal(bars):
    bars["rsi"] = calculate_rsi(bars["close"])
    bars["avg_vol"] = bars["volume"].rolling(LOOKBACK).mean()
    last = bars.iloc[-1]
    prev_high = bars["high"].max()
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

# Fetch supported crypto tickers dynamically from Alpaca
crypto_tickers = fetch_supported_crypto()

if len(crypto_tickers) == 0:
    st.warning("No supported crypto tickers found. Check your Alpaca API configuration.")
else:
    for symbol in crypto_tickers:
        bars = get_data(symbol)
        if bars is None or len(bars) < LOOKBACK:
            st.write(f"{symbol}: No data or error fetching data.")
            continue

        signal = confluence_signal(bars)
        st.write(f"{symbol}: {signal or 'No trade'}")
        
        # Uncomment below for live trading (auto buy/sell)
        # if signal == "BUY":
        #     api.submit_order(symbol=symbol, qty=CRYPTO_QTY, side='buy', type='market', time_in_force='gtc')
        # elif signal == "SELL":
        #     api.submit_order(symbol=symbol, qty=CRYPTO_QTY, side='sell', type='market', time_in_force='gtc')

st.info("Simulating trades with small account size. Adjust quantities and risk settings accordingly for real trading. \nTo go fully auto, uncomment the 'submit_order' lines.")
