import streamlit as st
import pandas as pd
from alpaca_trade_api.rest import REST, TimeFrame

# ========== CONFIGURATION ==========

API_KEY = 'PKHSYF5XH92B8VFNAJFD'
SECRET_KEY = '89KOB1vOSn2c3HeGorQe6zkKa0F4tFgBjbIAisCf'
BASE_URL = 'https://paper-api.alpaca.markets'

LOOKBACK = 21  # Number of minutes for RSI and volume calculations
RSI_BUY = 20   # RSI buy threshold
RSI_SELL = 80  # RSI sell threshold
VOL_SPIKE = 2   # Volume spike threshold
STOCK_QTY = 1   # Stock quantity for trading

# ========== INIT ==========

api = REST(API_KEY, SECRET_KEY, BASE_URL)

st.set_page_config(page_title="Sentinex Sniper", layout="wide")
st.title("🤖 Sentinex Sniper Bot — Only A+ Trades! (Crypto Mode)")

# Fetch supported crypto tickers
def fetch_supported_crypto():
    try:
        assets = api.list_assets()
        crypto_assets = [asset.symbol for asset in assets if asset.asset_class == 'crypto']
        return crypto_assets
    except Exception as e:
        st.error(f"Error fetching assets: {e}")
        return []

# Calculate RSI
def calculate_rsi(prices, window=14):
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

# Get data for a symbol
def get_data(symbol, tf=TimeFrame.Minute, limit=LOOKBACK):
    try:
        bars = api.get_bars(symbol, tf, limit=limit).df
        return bars
    except Exception as e:
        st.error(f"Error fetching data for {symbol}: {e}")
        return None

# Confluence signal logic for buy/sell decision
def confluence_signal(bars):
    if bars is None or len(bars) < LOOKBACK:
        return None
    bars["rsi"] = calculate_rsi(bars["close"])
    bars["avg_vol"] = bars["volume"].rolling(LOOKBACK).mean()
    last = bars.iloc[-1]
    
    # Check if data contains expected columns
    if "symbol" not in last or "rsi" not in last or "volume" not in last:
        st.warning("Missing necessary columns in the data.")
        return None

    prev_high = bars["high"].max()
    if last["rsi"] < RSI_BUY and last["volume"] > VOL_SPIKE * last["avg_vol"] and last["close"] > prev_high * 0.99:
        return "BUY"
    elif last["rsi"] > RSI_SELL:
        return "SELL"
    else:
        return None

# ========== MAIN LOGIC ==========

# Fetch supported cryptos
crypto_tickers = fetch_supported_crypto()

# Check and display available tickers
st.write(f"Found {len(crypto_tickers)} supported crypto tickers.")
st.write(f"Crypto Tickers: {crypto_tickers}")

# Scan for A+ setups
for symbol in crypto_tickers:
    bars = get_data(symbol)
    if bars is None or len(bars) < LOOKBACK:
        st.write(f"{symbol}: No data.")
        continue
    signal = confluence_signal(bars)
    st.write(f"{symbol}: {signal or 'No trade'}")

    # Uncomment below for auto trading (be careful with real $)
    # if signal == "BUY":
    #     api.submit_order(symbol=symbol, qty=STOCK_QTY, side='buy', type='market', time_in_force='gtc')
    # elif signal == "SELL":
    #     api.submit_order(symbol=symbol, qty=STOCK_QTY, side='sell', type='market', time_in_force='gtc')

st.info("Simulating trades with small account size. Adjust quantities and risk settings accordingly for real trading. To go fully auto, uncomment the 'submit_order' lines.")

