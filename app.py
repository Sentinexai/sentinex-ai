import streamlit as st
from alpaca_trade_api.rest import REST, TimeFrame
import pandas as pd
import numpy as np

# ========== CONFIGURATION ==========

API_KEY = 'PKHSYF5XH92B8VFNAJFD'
SECRET_KEY = '89KOB1vOSn2c3HeGorQe6zkKa0F4tFgBjbIAisCf'
BASE_URL = 'https://paper-api.alpaca.markets'

# ========== INIT ==========

api = REST(API_KEY, SECRET_KEY, BASE_URL)

st.set_page_config(page_title="Sentinex Sniper", layout="wide")
st.title("🤖 Sentinex Sniper Bot — Only A+ Trades! (Crypto Mode)")

LOOKBACK = 21  # Minutes for RSI and volume calculation
RSI_BUY = 20   # RSI buy threshold
RSI_SELL = 80  # RSI sell threshold
VOL_SPIKE = 2  # x avg volume spike

# Use small size for simulation (adjust quantity for your real account)
CRYPTO_QTY = 0.002  # e.g., 0.002 BTC ≈ $15-20

# ========== FUNCTION DEFINITIONS ==========

def calculate_rsi(prices, window=14):
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

# Get the historical data for a symbol
def get_data(symbol, tf=TimeFrame.Minute, limit=LOOKBACK):
    try:
        bars = api.get_bars(symbol, tf, limit=limit).df
        if bars.empty:
            st.write(f"Data for {symbol} is empty.")
            return None
        return bars
    except Exception as e:
        st.write(f"Error fetching data for {symbol}: {e}")
        return None

# Confluence Signal for buy/sell
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

# Fetch supported crypto tickers from Alpaca
def fetch_supported_crypto():
    try:
        assets = api.list_assets()
        crypto_assets = [asset.symbol for asset in assets if 'USD' in asset.symbol and asset.tradable]
        return crypto_assets
    except Exception as e:
        st.write(f"Error fetching assets: {e}")
        return []

# ========== MAIN LOGIC ==========

# Get supported crypto tickers
crypto_tickers = fetch_supported_crypto()

# Display available crypto tickers
st.header("💎 Scanning for A+ setups in Crypto...")

for symbol in crypto_tickers:
    bars = get_data(symbol)
    if bars is None or len(bars) < LOOKBACK:
        st.write(f"{symbol}: No data.")
        continue
    signal = confluence_signal(bars)
    st.write(f"{symbol}: {signal or 'No trade'}")
    # Uncomment below for auto trading (be cautious with real $)
    # if signal == "BUY":
    #     api.submit_order(symbol=symbol, qty=CRYPTO_QTY, side='buy', type='market', time_in_force='gtc')
    # elif signal == "SELL":
    #     api.submit_order(symbol=symbol, qty=CRYPTO_QTY, side='sell', type='market', time_in_force='gtc')

st.info("Simulating trades with small account size, adjust accordingly for real trading. To go fully auto, uncomment the 'submit_order' lines.")



