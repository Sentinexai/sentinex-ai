import streamlit as st
from alpaca_trade_api.rest import REST, TimeFrame
import pandas as pd
import numpy as np

# ========== CONFIGURATION ==========

API_KEY = 'PKHSYF5XH92B8VFNAJFD'
SECRET_KEY = '89KOB1vOSn2c3HeGorQe6zkKa0F4tFgBjbIAisCf'
BASE_URL = 'https://paper-api.alpaca.markets'

# Small Cap Stocks with price filter (change based on your needs)
# Stocks in the $10-$20 range (adjust if necessary)
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

# Use small size for $500 simulation (e.g., $20-25 per trade)
STOCK_QTY = 1
CRYPTO_QTY = 0.002  # e.g., 0.002 BTC ≈ $15-20

# ========== INIT ==========

api = REST(API_KEY, SECRET_KEY, BASE_URL)

st.set_page_config(page_title="Sentinex Sniper", layout="wide")
st.title("🤖 Sentinex Sniper Bot — Only A+ Trades! (Crypto & Small Caps)")

# Filter small-cap stocks based on price range: $10 to $20
def filter_small_caps():
    stock_data = []
    for symbol in SMALL_CAPS:
        bars = get_data(symbol)
        if bars is not None and len(bars) > LOOKBACK:
            current_price = bars.iloc[-1]["close"]
            if 10 <= current_price <= 20:
                stock_data.append(symbol)
    return stock_data

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

# ========== MAIN LOGIC ==========

# Filter small-cap stocks within price range of $10-$20
small_cap_stocks = filter_small_caps()
st.header("🔎 Scanning for A+ setups in Small Caps...")

for symbol in small_cap_stocks:
    bars = get_data(symbol)
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
    bars = get_data(symbol)
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

st.info("Simulating trades with small account size, adjust accordingly for real trading. \nTo go fully auto, uncomment the 'submit_order' lines.")



