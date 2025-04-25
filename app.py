import streamlit as st
from alpaca_trade_api.rest import REST, TimeFrame
import pandas as pd
import numpy as np

# ========== CONFIGURATION ==========
API_KEY = 'PKHSYF5XH92B8VFNAJFD'
SECRET_KEY = '89KOB1vOSn2c3HeGorQe6zkKa0F4tFgBjbIAisCf'
BASE_URL = 'https://paper-api.alpaca.markets'

SMALL_CAPS = ["NKLA", "MARA", "RIOT", "SNDL", "SOFI", "PLTR", "CLSK", "BBBY", "TLRY", "IDEX"]
CRYPTO_TICKERS = ["BTCUSD", "ETHUSD", "SOLUSD", "DOGEUSD"]

LOOKBACK = 21  # Minutes for RSI and volume calc
RSI_BUY = 20   # RSI buy threshold
RSI_SELL = 80  # RSI sell threshold
VOL_SPIKE = 2  # x avg volume spike

# ========== INIT ==========
api = REST(API_KEY, SECRET_KEY, BASE_URL)

st.set_page_config(page_title="Sentinex Sniper", layout="wide")
st.title("🤖 Sentinex Sniper Bot — Only A+ Trades!")

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
        return None

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
st.header("🔎 Scanning for A+ setups...")

for symbol in SMALL_CAPS:
    bars = get_data(symbol)
    if bars is None or len(bars) < LOOKBACK:
        st.write(f"{symbol}: No data.")
        continue
    signal = confluence_signal(bars)
    st.write(f"{symbol}: {signal or 'No trade'}")
    # To auto-trade, uncomment:
    # if signal == "BUY":
    #     api.submit_order(symbol=symbol, qty=1, side='buy', type='market', time_in_force='gtc')
    # elif signal == "SELL":
    #     api.submit_order(symbol=symbol, qty=1, side='sell', type='market', time_in_force='gtc')

st.header("💎 Crypto Mode (A+ signals)")
for symbol in CRYPTO_TICKERS:
    bars = get_data(symbol)
    if bars is None or len(bars) < LOOKBACK:
        st.write(f"{symbol}: No data.")
        continue
    signal = confluence_signal(bars)
    st.write(f"{symbol}: {signal or 'No trade'}")
    # To auto-trade, uncomment:
    # if signal == "BUY":
    #     api.submit_order(symbol=symbol, qty=0.01, side='buy', type='market', time_in_force='gtc')
    # elif signal == "SELL":
    #     api.submit_order(symbol=symbol, qty=0.01, side='sell', type='market', time_in_force='gtc')

st.info("Sniper mode: **Only the best confluence signals will trigger trades!** To enable auto-trading, uncomment the submit_order lines in the code. For trailing stop and position management, just say the word!")


