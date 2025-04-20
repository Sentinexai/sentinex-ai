import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from datetime import datetime, timedelta

API_KEY = "PKLDL1CN0ATYYGPULLXK"
SECRET_KEY = "JZm7RcmNUb9k4OPhqRu2OOuUPVSRpwqrbf7NRs1M"

client = StockHistoricalDataClient(API_KEY, SECRET_KEY)

st.set_page_config(page_title="Sentinex Chart", layout="wide")
st.title("📈 Live AAPL Chart with Trade Timeframes")

from alpaca.data.timeframe import TimeFrame

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

request_params = StockBarsRequest(
    symbol_or_symbols=["BTC/USD"],
    timeframe=timeframes[selected_tf],
    start=start,
    end=end
)

try:
    bars = client.get_stock_bars(request_params).df
    df = bars[bars.index.get_level_values(0) == "AAPL"]

    fig = go.Figure(data=[go.Candlestick(
        x=df.index.get_level_values(1),
        open=df["open"],
        high=df["high"],
        low=df["low"],
        close=df["close"]
    )])

    fig.update_layout(
        title=f"AAPL - {selected_tf} Chart",
        xaxis_title="Time",
        yaxis_title="Price",
        xaxis_rangeslider_visible=False
    )

    st.plotly_chart(fig, use_container_width=True)
except Exception as e:
    st.error(f"Failed to load chart data: {e}")


