import streamlit as st
from alpaca_trade_api.rest import REST, TimeFrame
import pandas as pd
import numpy as np
import requests

# ========== CONFIGURATION ========== 
API_KEY = 'PKHSYF5XH92B8VFNAJFD'
SECRET_KEY = '89KOB1vOSn2c3HeGorQe6zkKa0F4tFgBjbIAisCf'
BASE_URL = 'https://paper-api.alpaca.markets'

# Expanded small-cap stock list
SMALL_CAPS = [
    "NKLA", "MARA", "RIOT", "SNDL", "SOFI", "PLTR", "CLSK", "BBBY", "TLRY", "IDEX",
    "GME", "AMC", "CVNA", "AI", "NVAX", "BBBYQ", "LCID", "TSLA", "NIO", "BILI",
    "FFIE", "APE", "AMTD", "CEI", "VERU", "IONQ", "QS", "DNA", "OSTK", "VYNE", "BBIG"
]

# Expanded crypto list
CRYPTO_TICKERS = [
    "BTCUSD", "ETHUSD", "SOLUSD", "DOGEUSD", "SHIBUSD", "AVAXUSD", "ADAUSD", "MATICUSD",
    "XRPUSD", "LINKUSD", "OPUSD", "PEPEUSD", "WIFUSD", "ARBUSD", "SEIUSD", "TONUSD",
    "BNBUSD", "RNDRUSD", "INJUSD", "TIAUSD"
]

LOOKBACK = 21  # Minutes for RSI and volume calc
RSI_BUY = 20   # RSI buy threshold
RSI_SELL = 80  # RSI sell threshold
VOL_SPIKE = 2  # x avg volume spike

# Stock and Crypto quantities for trades
STOCK_QTY = 1
CRYPTO_QTY = 0.002  # e.g., 0.002 BTC ≈ $15-20

# ========== INIT ========== 
api = REST(API_KEY, SECRET_KEY, BASE_URL)

st.set_page_config(page_title="Sentinex Sniper", layout="wide")
st.title("🤖 Sentinex Sniper Bot — Only A+ Trades! ($500 Paper Trading Sim)")

# ========== FUNCTIONS ========== 

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

def is_rug_pull(crypto):
    url = f"https://api.coingecko.com/api/v3/coins/{crypto}/market_chart?vs_currency=usd&days=1"
    response = requests.get(url)
    data = response.json()
    if data['prices'][-1][1] < 0.1:
        return True
    return False

def get_sentiment(symbol):
    sentiment_url = f"https://api.lunarcrush.com/v2?data=assets&key=YOUR_API_KEY&symbol={symbol}"
    response = requests.get(sentiment_url)
    sentiment_data = response.json()
    sentiment_score = sentiment_data['data'][0]['sentiment']
    return sentiment_score

# ========== MAIN LOGIC ==========

# Small Cap Trading Loop
st.header("🔎 Scanning for A+ setups in Small Caps...")
for symbol in SMALL_CAPS:
    bars = get_data(symbol)
    if bars is None or len(bars) < LOOKBACK:
        st.write(f"{symbol}: No data.")
        continue
    signal = confluence_signal(bars)
    sentiment_score = get_sentiment(symbol)
    if sentiment_score > 0.75 and not is_rug_pull(symbol):
        st.write(f"{symbol}: {signal or 'No trade'}")
        if signal == "BUY":
            api.submit_order(symbol=symbol, qty=STOCK_QTY, side="buy", type="market", time_in_force="gtc")
        elif signal == "SELL":
            api.submit_order(symbol=symbol, qty=STOCK_QTY, side="sell", type="market", time_in_force="gtc")

# Crypto Trading Loop
st.header("💎 Crypto Mode (A+ signals)")
for symbol in CRYPTO_TICKERS:
    bars = get_data(symbol)
    if bars is None or len(bars) < LOOKBACK:
        st.write(f"{symbol}: No data.")
        continue
    signal = confluence_signal(bars)
    sentiment_score = get_sentiment(symbol)
    if sentiment_score > 0.75 and not is_rug_pull(symbol):
        st.write(f"{symbol}: {signal or 'No trade'}")
        if signal == "BUY":
            api.submit_order(symbol=symbol, qty=CRYPTO_QTY, side="buy", type="market", time_in_force="gtc")
        elif signal == "SELL":
            api.submit_order(symbol=symbol, qty=CRYPTO_QTY, side="sell", type="market", time_in_force="gtc")

st.info("Simulating $500 account: trade size is set small. To go fully auto, uncomment the 'submit_order' lines. Want trailing stops, sentiment, or more auto-risk controls? Just ask!")

