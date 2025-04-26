import streamlit as st
from alpaca_trade_api.rest import REST, TimeFrame
import pandas as pd
import numpy as np

# ========== CONFIGURATION ==========

API_KEY = 'PKHSYF5XH92B8VFNAJFD'  # Replace with your API Key
SECRET_KEY = '89KOB1vOSn2c3HeGorQe6zkKa0F4tFgBjbIAisCf'  # Replace with your Secret Key
BASE_URL = 'https://paper-api.alpaca.markets'

# Define the crypto tickers supported by Alpaca
CRYPTO_TICKERS = [
    "BTCUSD", "ETHUSD", "SOLUSD", "DOGEUSD", "SHIBUSD", "AVAXUSD", "ADAUSD", "MATICUSD",
    "XRPUSD", "LINKUSD", "OPUSD", "PEPEUSD", "WIFUSD", "ARBUSD", "SEIUSD", "TONUSD",
    "BNBUSD", "RNDRUSD", "INJUSD", "TIAUSD"
]

LOOKBACK = 21  # Number of minutes for RSI and volume calc
RSI_BUY = 30   # RSI threshold for buy signal
RSI_SELL = 70  # RSI threshold for sell signal
VOL_SPIKE = 2  # Volume spike threshold (2x average volume)

# Use small size for paper trading simulation (adjust accordingly)
CRYPTO_QTY = 0.002  # For example, 0.002 BTC ≈ $15-20

# ========== INIT ==========

api = REST(API_KEY, SECRET_KEY, BASE_URL)

st.set_page_config(page_title="Sentinex Sniper", layout="wide")
st.title("🤖 Sentinex Sniper Bot — Crypto Mode (High Profit Trades)")

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
        return None

# Confluence Signal for buy/sell based on RSI and volume
def confluence_signal(bars):
    bars["rsi"] = calculate_rsi(bars["close"])
    bars["avg_vol"] = bars["volume"].rolling(LOOKBACK).mean()
    last = bars.iloc[-1]
    if last["rsi"] < RSI_BUY and last["volume"] > VOL_SPIKE * last["avg_vol"]:
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
    signal = confluence_signal(bars)
    st.write(f"{symbol}: {signal or 'No trade'}")
    
    # Perform auto trading (uncomment below to enable real trading)
    if signal == "BUY":
        try:
            api.submit_order(
                symbol=symbol,
                qty=CRYPTO_QTY,
                side='buy',
                type='market',
                time_in_force='gtc'
            )
            st.write(f"{symbol}: BUY order placed.")
        except Exception as e:
            st.write(f"Error placing BUY order for {symbol}: {str(e)}")
    elif signal == "SELL":
        try:
            api.submit_order(
                symbol=symbol,
                qty=CRYPTO_QTY,
                side='sell',
                type='market',
                time_in_force='gtc'
            )
            st.write(f"{symbol}: SELL order placed.")
        except Exception as e:
            st.write(f"Error placing SELL order for {symbol}: {str(e)}")

st.info("Simulating trades with small account size. Adjust quantities and risk settings accordingly for real trading.")

