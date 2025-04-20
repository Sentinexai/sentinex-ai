import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
from alpaca.data.historical import CryptoHistoricalDataClient
from alpaca.data.requests import CryptoBarsRequest
from alpaca.data.timeframe import TimeFrame
from datetime import datetime, timedelta

# Discord webhook URL
WEBHOOK_URL = "https://discord.com/api/webhooks/1363368522734108772/0gES_N4GWVjPDW987hM1iwGg6eYs2fLZNa6P6up_7FC7H4etTJvPT2j_dN4CiXqaQHDV"

# Set page
st.set_page_config(page_title="Sentinex PRO", layout="wide")
st.title("📈 Sentinex PRO: BTC/USD Chart, Trades, Discord Alerts & Export")

# Client for crypto data
client = CryptoHistoricalDataClient()

# Initialize session state
if "trades" not in st.session_state:
    st.session_state["trades"] = []

# Timeframes
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

# Request setup
request_params = CryptoBarsRequest(
    symbol_or_symbols=["BTC/USD"],
    timeframe=timeframes[selected_tf],
    start=start,
    end=end
)

# Discord notification
def send_discord_alert(trade):
    message = {
        "content": f"📍 **Sentinex Trade Alert**\n**{trade['type']}** BTC/USD at `${trade['price']:,.2f}`\n🕒 {trade['time'].strftime('%Y-%m-%d %H:%M:%S UTC')}"
    }
    try:
        requests.post(WEBHOOK_URL, json=message)
    except Exception as e:
        st.error(f"Failed to send Discord alert: {e}")

# Pull data
try:
    bars = client.get_crypto_bars(request_params).df
    df = bars[bars.index.get_level_values(0) == "BTC/USD"]
    df = df.reset_index(level=0, drop=True)

    latest = df.iloc[-1]
    if st.button("💥 Simulate BUY Trade"):
        trade = {
            "time": latest.name,
            "price": latest["close"],
            "type": "BUY"
        }
        st.session_state["trades"].append(trade)
        send_discord_alert(trade)
        st.success(f"BUY trade logged at {trade['time']} | ${trade['price']:,.2f}")

    if st.button("🔻 Simulate SELL Trade"):
        trade = {
            "time": latest.name,
            "price": latest["close"],
            "type": "SELL"
        }
        st.session_state["trades"].append(trade)
        send_discord_alert(trade)
        st.warning(f"SELL trade logged at {trade['time']} | ${trade['price']:,.2f}")

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
        title="BTC/USD Chart with Simulated Trades",
        xaxis_title="Time",
        yaxis_title="Price (USD)",
        xaxis_rangeslider_visible=False
    )
    st.plotly_chart(fig, use_container_width=True)

    # Export to CSV
    if st.session_state["trades"]:
        df_trades = pd.DataFrame(st.session_state["trades"])
        csv = df_trades.to_csv(index=False).encode("utf-8")
        st.download_button("📥 Download Trade Log (CSV)", data=csv, file_name="sentinex_trades.csv", mime="text/csv")

except Exception as e:
    st.error(f"Failed to load chart data: {e}")







