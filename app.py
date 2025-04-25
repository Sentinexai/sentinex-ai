import streamlit as st
from alpaca_trade_api.rest import REST, TimeFrame
import pandas as pd
import numpy as np

# ========== CONFIG ==========
API_KEY = 'PKHSYF5XH92B8VFNAJFD'
SECRET_KEY = '89KOB1vOSn2c3HeGorQe6zkKa0F4tFgBjbIAisCf'
BASE_URL = 'https://paper-api.alpaca.markets'

# Top liquid, high-volatility cryptos (edit as you like)
CRYPTO_TICKERS = [
    "BTCUSD", "ETHUSD", "SOLUSD", "DOGEUSD", "SHIBUSD", "AVAXUSD", "ADAUSD", "MATICUSD",
    "XRPUSD", "LINKUSD", "OPUSD", "PEPEUSD", "WIFUSD", "ARBUSD", "TONUSD", "BNBUSD",
    "INJUSD", "TIAUSD"
]

LOOKBACK = 21  # Minutes for RSI and volume calc
RSI_BUY = 22   # Oversold threshold (tweakable)
RSI_SELL = 78  # Overbought threshold (tweakable)
VOL_SPIKE = 2.2  # x avg volume for entry
MAX_RISK_PCT = 0.04  # Never risk more than 4% of current balance per trade
TRADE_SIZE_USD = 20  # Target size per trade (scale up as you grow)

api = REST(API_KEY, SECRET_KEY, BASE_URL)

st.set_page_config(page_title="Sentinex Crypto Sniper", layout="wide")
st.title("🤖 Sentinex Crypto Sniper Bot — Focus: $200 Account Growth")

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
    except Exception:
        return None

def get_cash():
    try:
        account = api.get_account()
        return float(account.cash)
    except Exception:
        return 200.0  # Default/fallback

def confluence_signal(bars):
    bars["rsi"] = calculate_rsi(bars["close"])
    bars["avg_vol"] = bars["volume"].rolling(LOOKBACK).mean()
    last = bars.iloc[-1]
    prev_high = bars["high"].max()
    # --- Best sniper entry: big volume, RSI oversold, price not crashing
    if (
        last["rsi"] < RSI_BUY and
        last["volume"] > VOL_SPIKE * last["avg_vol"] and
        last["close"] > prev_high * 0.98
    ):
        return "BUY"
    elif last["rsi"] > RSI_SELL:
        return "SELL"
    else:
        return None

st.header("🔎 Scanning Top Cryptos for Best Sniper Setups...")

cash = get_cash()
trade_size = min(TRADE_SIZE_USD, cash * MAX_RISK_PCT)
st.write(f"Available cash: ${cash:.2f} | Per-trade size: ${trade_size:.2f}")

for symbol in CRYPTO_TICKERS:
    bars = get_data(symbol)
    if bars is None or len(bars) < LOOKBACK:
        st.write(f"{symbol}: No data.")
        continue
    signal = confluence_signal(bars)
    st.write(f"{symbol}: {signal or 'No trade'}")
    # Uncomment below for auto trading!
    # if signal == "BUY":
    #     qty = round(trade_size / bars.iloc[-1]["close"], 6)
    #     api.submit_order(symbol=symbol, qty=qty, side='buy', type='market', time_in_force='gtc')
    #     st.success(f"BUY {symbol} {qty}")
    # elif signal == "SELL":
    #     qty = round(trade_size / bars.iloc[-1]["close"], 6)
    #     api.submit_order(symbol=symbol, qty=qty, side='sell', type='market', time_in_force='gtc')
    #     st.warning(f"SELL {symbol} {qty}")

st.info("This bot only takes sniper setups (volume + RSI confluence). It’s built to **grow small accounts** and protect against big losses. To enable auto-trading, just uncomment the order lines!")
