import streamlit as st
import pandas as pd
import numpy as np
from alpaca_trade_api.rest import REST, TimeFrame

# ========== CONFIGURATION ==========
API_KEY = 'PKHSYF5XH92B8VFNAJFD'
SECRET_KEY = '89KOB1vOSn2c3HeGorQe6zkKa0F4tFgBjbIAisCf'  
BASE_URL = 'https://paper-api.alpaca.markets'
LOOKBACK = 21  # Number of minutes for RSI calculation
RSI_BUY = 30   # RSI buy threshold
RSI_SELL = 70  # RSI sell threshold
CRYPTO_QTY = 0.002  # Quantity for trading

# Initialize Alpaca API
api = REST(API_KEY, SECRET_KEY, BASE_URL)

# Set up the Streamlit layout
st.set_page_config(page_title="Sentinex Sniper", layout="wide")
st.title("🤖 Sentinex Sniper Bot — Only A+ Trades! (Crypto Mode)")

def calculate_rsi(prices, window=14):
    """Calculate the RSI (Relative Strength Index)"""
    prices = pd.Series(prices)
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def fetch_supported_crypto_tickers():
    """Fetch supported crypto tickers."""
    try:
        assets = api.list_assets()
        # Filter only tradable crypto assets by confirming tradability and the presence of 'crypto' in the symbol
        crypto_tickers = [asset.symbol for asset in assets if asset.tradable and asset.exchange and 'crypto' in asset.symbol.lower()]

        if not crypto_tickers:
            st.warning("No supported crypto tickers found.")
        else:
            st.success(f"Supported crypto tickers: {crypto_tickers}")  # Display the fetched tickers
        
        return crypto_tickers
    except Exception as e:
        st.error(f"Error fetching assets: {e}")
        return []

def get_data(symbol):
    """Fetch historical price data for the given symbol."""
    try:
        bars = api.get_bars(symbol, TimeFrame.Minute, limit=LOOKBACK).df
        
        if bars.empty:
            st.warning(f"No historical data available for {symbol}.")
        
        return bars
    except Exception as e:
        st.error(f"Error fetching data for {symbol}: {e}")  # Display error
        return None

def confluence_signal(bars):
    """Generate buy/sell signals based on RSI."""
    if bars is None or len(bars) < LOOKBACK:
        return None

    bars['rsi'] = calculate_rsi(bars['close'])
    last = bars.iloc[-1]

    if last['rsi'] < RSI_BUY:
        return "BUY"
    elif last['rsi'] > RSI_SELL:
        return "SELL"
    else:
        return "HOLD"

# ========== MAIN LOGIC ==========
st.header("🔎 Scanning for A+ setups in Crypto...")

# Fetch crypto tickers
crypto_tickers = fetch_supported_crypto_tickers()

# Iterate over the supported crypto tickers
for symbol in crypto_tickers:
    bars = get_data(symbol)
    signal = confluence_signal(bars)
    st.write(f"{symbol}: {signal or 'No trade'}")
    
    # Uncomment the following lines for live trading
    # if signal == "BUY":
    #     api.submit_order(symbol=symbol, qty=CRYPTO_QTY, side='buy', type='market', time_in_force='gtc')
    # elif signal == "SELL":
    #     api.submit_order(symbol=symbol, qty=CRYPTO_QTY, side='sell', type='market', time_in_force='gtc')

st.info("Simulating trades with small account size. Adjust quantities and risk settings accordingly for real trading.")
