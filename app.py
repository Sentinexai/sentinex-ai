import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from alpaca.data.historical import CryptoHistoricalDataClient
from alpaca.data.requests import CryptoBarsRequest
from alpaca.data.timeframe import TimeFrame
from datetime import datetime, timedelta

client = CryptoHistoricalDataClient()

st.set_page_config(page_title="Sentinex Chart", layout="wide")
st.title("📈 Live BTC/USD Chart with Trade Timeframes")

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


