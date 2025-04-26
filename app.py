import streamlit as st
from alpaca_trade_api.rest import REST, TimeFrame
import pandas as pd
import numpy as np

# ========== CONFIGURATION ==========

API_KEY = 'PKHSYF5XH92B8VFNAJFD'
SECRET_KEY = '89KOB1vOSn2c3HeGorQe6zkKa0F4tFgBjbIAisCf'
BASE_URL = 'https://paper-api.alpaca.markets'

# List of supported crypto tickers for Alpaca
CRYPTO_TICKERS = [
    "BTCUSD", "ETHUSD", "SOLUSD", "DOGEUSD", "SHIBUSD", "AVAXUSD", "ADAUSD", "MATICUSD",
    "XRPUSD", "LINKUSD", "OPUSD", "PEPEUSD", "WIFUSD", "ARBUSD", "SEIUSD", "TONUSD",
    "BNBUSD", "RNDRUSD", "INJUSD", "TIAUSD"
]

LOOKBACK = 21  # Minutes for RSI and volume calc
RSI_BUY = 30   # RSI buy threshold (oversold)
RSI_SELL = 70  # RSI sell threshold (overbought)
VOL_SPIKE = 2  # x avg volume spike

# Use small size for $500 simulation (e.g., $20-25 per trade)
CRYPTO_QTY = 0.002  # e.g., 0.002 BTC ≈ $15-20

# ========== INIT ==========

api = REST(API_KEY, SECRET_KEY, BASE_URL)

st.set_page_config(page_title="Sentinex Sniper", layout="wide")
st.title("🤖 Sentinex Sniper Bot — Crypto Only (High Potential Profits)")

# Calculate RSI
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
        return bars
    except Exception as e:
        st.error(f"Error fetching data for {symbol}: {e}")
        return None

# Confluence Signal for buy/sell
def confluence_signal(bars):
    bars["rsi"] = calculate_rsi(bars["close"])
    bars["avg_vol"] = bars["volume"].rolling(LOOKBACK).mean()
    last = bars.iloc[-1]
    prev_high = bars["high"].max()

    # Buy condition: RSI below 30 (oversold), volume spike, price breaking above previous high
    if (
        last["rsi"] < RSI_BUY and
        last["volume"] > VOL_SPIKE * last["avg_vol"] and
        last["close"] > prev_high * 1.01  # Price breaks past previous high
    ):
        return "BUY"
    # Sell condition: RSI above 70 (overbought)
    elif last["rsi"] > RSI_SELL:
        return "SELL"
    else:
        return None

# ========== MAIN LOGIC ==========

st.header("🔎 Scanning for A+ setups in Crypto...")

for symbol in CRYPTO_TICKERS:
    bars = get_data(symbol)
    if bars is None or len(bars) < LOOKBACK:
        st.write(f"{symbol}: No data or error fetching data.")
        continue

    # Analyze the data for buy/sell signals
    signal = confluence_signal(bars)
    st.write(f"{symbol}: {signal or 'No trade'}")

    # For real trading, uncomment the submit order lines below
    if signal == "BUY":
        st.write(f"📈 {symbol} - Buying signal detected. Executing buy order...")
        # Uncomment below for real auto trading
        # api.submit_order(symbol=symbol, qty=CRYPTO_QTY, side='buy', type='market', time_in_force='gtc')
    elif signal == "SELL":
        st.write(f"📉 {symbol} - Selling signal detected. Executing sell order...")
        # Uncomment below for real auto trading
        # api.submit_order(symbol=symbol, qty=CRYPTO_QTY, side='sell', type='market', time_in_force='gtc')

# Simulation info
st.info("Simulating trades with a small account size. Adjust quantities and risk settings accordingly for real trading. To go fully auto, uncomment the 'submit_order' lines.")
