import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from alpaca.data.historical import CryptoHistoricalDataClient
from alpaca.data.requests import CryptoBarsRequest
from alpaca.data.timeframe import TimeFrame
from datetime import datetime, timedelta

st.set_page_config(page_title="Sentinex BTC Chart", layout="wide")
st.title("📈 Live BTC/USD Chart with Trade Timeframes")

client = CryptoHistoricalDataClient()

timeframes = {
    "1 Minute": TimeFrame.Minute,
    "5 Minutes": TimeFrame(5, "Minute"),
    "15 Minutes": TimeFrame(15, "Minute"),
    "1 Hour": TimeFrame.Hour,
    "1 Day": TimeFrame.Day
}

selected_tf = st.selectbox("Choose Timeframe", list(timeframes.keys()))

end = datetime.utcnow()
start = end - timedelta(days=1)

request_params = CryptoBarsRequest(
    symbol_or_symbols=["BTC/USD"],
    timeframe=timeframes[selected_tf],
    start=start,
    end=end
)

try:
    bars = client.get_crypto_bars(request_params).df
    df = bars[bars.index.get_level_values(0) == "BTC/USD"]

    fig = go.Figure(data=[go.Candlestick(
        x=df.index.get_level_values(1),
        open=df["open"],
        high=df["high"],
        low=df["low"],
        close=df["close"]
    )])

    fig.update_layout(
        title=f"BTC/USD - {selected_tf} Chart",
        xaxis_title="Time",
        yaxis_title="Price (USD)",
        xaxis_rangeslider_visible=False
    )

    st.plotly_chart(fig, use_container_width=True)
except Exception as e:
    st.error(f"Failed to load chart data: {e}")

