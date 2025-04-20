
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from alpaca.data.historical import CryptoHistoricalDataClient
from alpaca.data.requests import CryptoBarsRequest
from alpaca.data.timeframe import TimeFrame
from datetime import datetime, timedelta

# Setup page
st.set_page_config(page_title="Sentinex BTC Chart + Trade Markers", layout="wide")
st.title("📈 Live BTC/USD Chart with Trade Timeframes + Simulated Trades")

# Alpaca crypto client (no API key needed for crypto)
client = CryptoHistoricalDataClient()

# Trade memory
if "trades" not in st.session_state:
    st.session_state["trades"] = []

# Timeframe selector
timeframes = {
    "1 Minute": TimeFrame.Minute,
    "5 Minutes": TimeFrame(5, "Minute"),
    "15 Minutes": TimeFrame(15, "Minute"),
    "1 Hour": TimeFrame.Hour,
    "1 Day": TimeFrame.Day
}
selected_tf = st.selectbox("Choose Timeframe", list(timeframes.keys()))

# Time range
end = datetime.utcnow()
start = end - timedelta(days=1)

# Data request
request_params = CryptoBarsRequest(
    symbol_or_symbols=["BTC/USD"],
    timeframe=timeframes[selected_tf],
    start=start,
    end=end
)

# Fetch and display
try:
    bars = client.get_crypto_bars(request_params).df
    df = bars[bars.index.get_level_values(0) == "BTC/USD"]
    df = df.reset_index(level=0, drop=True)

    # Simulate trade button
    if st.button("💥 Simulate Buy Trade"):
        latest = df.iloc[-1]
        trade = {
            "time": latest.name,
            "price": latest["close"]
        }
        st.session_state["trades"].append(trade)
        st.success(f"Trade logged at {trade['time']} | Price: ${trade['price']:,.2f}")

    # Chart
    fig = go.Figure()

    # Candlestick chart
    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df["open"],
        high=df["high"],
        low=df["low"],
        close=df["close"],
        name="BTC/USD"
    ))

    # Overlay trades
    for trade in st.session_state["trades"]:
        fig.add_trace(go.Scatter(
            x=[trade["time"]],
            y=[trade["price"]],
            mode="markers+text",
            marker=dict(color="green", size=10, symbol="arrow-up"),
            text=["BUY"],
            textposition="top center",
            name="Buy Marker"
        ))

    fig.update_layout(
        title="BTC/USD Chart with Simulated Trades",
        xaxis_title="Time",
        yaxis_title="Price (USD)",
        xaxis_rangeslider_visible=False
    )

    st.plotly_chart(fig, use_container_width=True)
except Exception as e:
    st.error(f"Failed to load chart data: {e}")

