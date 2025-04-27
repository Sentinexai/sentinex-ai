import streamlit as st
from alpaca_trade_api.rest import REST, TimeFrame
import pandas as pd
import numpy as np
import time

# API credentials
API_KEY = "PKHSYF5XH92B8VFNAJFD"
SECRET_KEY = "89KOB1vOSn2c3HeGorQe6zkKa0F4tFgBjbIAisCf"
BASE_URL = "https://paper-api.alpaca.markets"

api = REST(API_KEY, SECRET_KEY, BASE_URL)

st.title("🤖 Sentinex Crypto Sniper")

CRYPTO_TICKERS = ["BTCUSD", "ETHUSD", "SOLUSD", "DOGEUSD", "AVAXUSD"]

# RSI calculation function
def calc_rsi(series, period=14):
    delta = series.diff(1).dropna()
    gain = delta.clip(lower=0).rolling(window=period).mean()
    loss = -delta.clip(upper=0).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def get_crypto_data(symbol):
    bars = api.get_crypto_bars(symbol, TimeFrame.Minute, limit=30).df
    bars['rsi'] = calc_rsi(bars['close'])
    return bars

# Automated Trading Logic
trade_qty = {"BTCUSD": 0.001, "ETHUSD": 0.005, "SOLUSD": 0.1, "DOGEUSD": 50, "AVAXUSD": 0.2}

if st.button("Run Sniper Bot 🚀"):
    for symbol in CRYPTO_TICKERS:
        data = get_crypto_data(symbol)
        latest_rsi = data['rsi'].iloc[-1]
        latest_close = data['close'].iloc[-1]

        positions = api.list_positions()
        current_qty = sum(float(pos.qty) for pos in positions if pos.symbol == symbol)

        if latest_rsi < 30 and current_qty == 0:
            api.submit_order(symbol=symbol, qty=trade_qty[symbol], side='buy', type='market', time_in_force='gtc')
            st.success(f"✅ Bought {trade_qty[symbol]} {symbol} @ {latest_close:.2f}, RSI: {latest_rsi:.2f}")
        elif latest_rsi > 70 and current_qty > 0:
            api.submit_order(symbol=symbol, qty=current_qty, side='sell', type='market', time_in_force='gtc')
            st.info(f"🔴 Sold {current_qty} {symbol} @ {latest_close:.2f}, RSI: {latest_rsi:.2f}")
        else:
            st.write(f"No trade for {symbol} (RSI: {latest_rsi:.2f})")

        time.sleep(1)  # Avoid hitting API limits

    st.balloons()

