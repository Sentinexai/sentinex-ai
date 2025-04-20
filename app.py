import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
import numpy as np
from datetime import datetime, timedelta
from alpaca.data.historical import CryptoHistoricalDataClient
from alpaca.data.requests import CryptoBarsRequest
from alpaca.data.timeframe import TimeFrame
from streamlit_autorefresh import st_autorefresh

# Discord webhook
WEBHOOK_URL = "https://discord.com/api/webhooks/1363368522734108772/0gES_N4GWVjPDW987hM1iwGg6eYs2fLZNa6P6up_7FC7H4etTJvPT2j_dN4CiXqaQHDV"

# Refresh every 60 seconds
st_autorefresh(interval=60000, key="auto_refresh")

# Page setup
st.set_page_config(page_title="Sentinex AUTO", layout="wide")
st.title("🤖 Sentinex Auto RSI Bot — BTC/USD (60s refresh)")

client = CryptoHistoricalDataClient()

if "trades" not in st.session_state:
    st.session_state["trades"] = []

def calculate_rsi(close, period=14):
    delta = close.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def send_discord_alert(trade):
    msg = {
        "content": f"📍 **Sentinex AUTO Trade**\n**{trade['type']}** BTC/USD at `${trade['price']:,.2f}`\n🕒 {trade['time'].strftime('%Y-%m-%d %H:%M:%S UTC')}`"
    }
    try:
        requests.post(WEBHOOK_URL, json=msg)
    except Exception as e:
        st.error(f"Discord alert failed: {e}")

# Get data
end = datetime.utcnow()
start = end - timedelta(days=1)
params = CryptoBarsRequest(symbol_or_symbols=["BTC/USD"], timeframe=TimeFrame.Minute, start=start, end=end)
bars = client.get_crypto_bars(params).df
df = bars[bars.index.get_level_values(0) == "BTC/USD"]
df = df.reset_index(level=0, drop=True)
df["rsi"] = calculate_rsi(df["close"])

# Strategy Logic
latest = df.iloc[-1]
rsi_value = latest["rsi"]

should_buy = rsi_value < 30
should_sell = rsi_value > 70

# Place trade based on condition
if should_buy:
    trade = {"time": latest.name, "price": latest["close"], "type": "BUY"}
    st.session_state["trades"].append(trade)
    send_discord_alert(trade)
    st.success(f"AUTO BUY at ${trade['price']:,.2f} | RSI: {rsi_value:.2f}")

elif should_sell:
    trade = {"time": latest.name, "price": latest["close"], "type": "SELL"}
    st.session_state["trades"].append(trade)
    send_discord_alert(trade)
    st.warning(f"AUTO SELL at ${trade['price']:,.2f} | RSI: {rsi_value:.2f}")

# Chart
fig = go.Figure()
fig.add_trace(go.Candlestick(
    x=df.index,
    open=df["open"],
    high=df["high"],
    low=df["low"],
    close=df["close"],
    name="BTC/USD"
))

for trade in st.session_state["trades"]:
    fig.add_trace(go.Scatter(
        x=[trade["time"]],
        y=[trade["price"]],
        mode="markers+text",
        marker=dict(
            color="green" if trade["type"] == "BUY" else "red",
            size=10,
            symbol="arrow-up" if trade["type"] == "BUY" else "arrow-down"
        ),
        text=[trade["type"]],
        textposition="top center",
        name=trade["type"]
    ))

fig.update_layout(
    title="BTC/USD Chart with Auto Trades",
    xaxis_title="Time",
    yaxis_title="Price (USD)",
    xaxis_rangeslider_visible=False
)
st.plotly_chart(fig, use_container_width=True)
