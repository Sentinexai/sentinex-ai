import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from alpaca_trade_api.rest import REST, TimeFrame
import time

# --- Alpaca API Credentials ---
API_KEY = "PKHSYF5XH92B8VFNAJFD"
SECRET_KEY = "89KOB1vOSn2c3HeGorQe6zkKa0F4tFgBjbIAisCf"
BASE_URL = "https://paper-api.alpaca.markets"

SYMBOL = "BTCUSD"  # Alpaca expects BTCUSD, not BTC/USD
QTY_PER_TRADE = 0.0001  # Small size for demo

SMA_FAST = 12
SMA_SLOW = 24

@st.cache_resource
def get_api():
    return REST(API_KEY, SECRET_KEY, BASE_URL)

def get_bars(symbol=SYMBOL):
    api = get_api()
    bars = api.get_crypto_bars(symbol, TimeFrame.Minute, limit=100).df
    bars = bars[bars.exchange == 'CBSE']  # Use Coinbase data only
    bars = bars.copy()
    bars['sma_fast'] = bars['close'].rolling(SMA_FAST).mean()
    bars['sma_slow'] = bars['close'].rolling(SMA_SLOW).mean()
    return bars

def get_position(symbol=SYMBOL):
    api = get_api()
    positions = api.list_positions()
    for p in positions:
        if p.symbol == symbol:
            return float(p.qty)
    return 0

def submit_order(side, qty=QTY_PER_TRADE, symbol=SYMBOL):
    api = get_api()
    try:
        api.submit_order(symbol=symbol, qty=qty, side=side, type='market', time_in_force='gtc')
        st.success(f"Order submitted: {side.upper()} {qty} {symbol}")
    except Exception as e:
        st.error(f"Order error: {e}")

def plot_chart(bars):
    fig = go.Figure(data=[go.Candlestick(
        x=bars.index,
        open=bars['open'],
        high=bars['high'],
        low=bars['low'],
        close=bars['close'],
        name='Candles'
    )])
    fig.add_trace(go.Scatter(
        x=bars.index, y=bars["sma_fast"], line=dict(color='green', width=1), name=f"SMA{SMA_FAST}"
    ))
    fig.add_trace(go.Scatter(
        x=bars.index, y=bars["sma_slow"], line=dict(color='red', width=1), name=f"SMA{SMA_SLOW}"
    ))
    st.plotly_chart(fig, use_container_width=True)

st.title("📈 Alpaca Crypto Paper Trading Bot (BTCUSD, CBSE)")
bars = get_bars()
if not bars.empty:
    plot_chart(bars)
    st.write(bars.tail(10))
else:
    st.error("No market data available. Check symbol or API limits.")

position = get_position()
st.write(f"Current BTCUSD position: {position}")

if st.button("Run Bot Step"):
    if len(bars) < SMA_SLOW + 1:
        st.warning("Not enough data for moving averages.")
    else:
        should_buy = bars['sma_fast'].iloc[-1] > bars['sma_slow'].iloc[-1]
        should_sell = bars['sma_fast'].iloc[-1] < bars['sma_slow'].iloc[-1]
        if position == 0 and should_buy:
            submit_order('buy')
        elif position > 0 and should_sell:
            submit_order('sell', qty=position)
        else:
            st.info("No trade signal.")

if st.button("Force Sell All"):
    if position > 0:
        submit_order('sell', qty=position)
    else:
        st.info("No position to sell.")

# Account info
api = get_api()
account = api.get_account()
st.write(f"Equity: ${account.equity}")
st.write(f"Buying Power: ${account.buying_power}")

