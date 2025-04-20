import streamlit as st
st.set_page_config(page_title="Sentinex ULTRA AI", layout="wide")

import pandas as pd
import plotly.graph_objects as go
import requests
import numpy as np
from datetime import datetime, timedelta
from alpaca.data.historical import CryptoHistoricalDataClient
from alpaca.data.requests import CryptoBarsRequest
from alpaca.data.timeframe import TimeFrame
from streamlit_autorefresh import st_autorefresh

# ============ CONFIG ============ #
ASSETS = ["BTC/USD", "ETH/USD", "SOL/USD", "MATIC/USD"]
STRATEGY = "RSI_BREAKOUT"
DISCORD_WEBHOOK = "https://discord.com/api/webhooks/..."  # replace with your webhook

# ============ STATE INIT ============ #
st_autorefresh(interval=60000, key="refresh")
client = CryptoHistoricalDataClient()

if "trade_log" not in st.session_state:
    st.session_state.trade_log = []
if "holding" not in st.session_state:
    st.session_state.holding = {symbol: None for symbol in ASSETS}
if "max_price" not in st.session_state:
    st.session_state.max_price = {symbol: 0 for symbol in ASSETS}
if "realized_pnl" not in st.session_state:
    st.session_state.realized_pnl = {symbol: 0 for symbol in ASSETS}

# ============ STRATEGY HELPERS ============ #
def calculate_rsi(close, period=14):
    delta = close.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def calculate_heat_score(df):
    vol_ratio = df["volume"].iloc[-1] / df["volume"].mean()
    trend = df["close"].pct_change().rolling(5).mean().iloc[-1]
    rsi = calculate_rsi(df["close"]).iloc[-1]
    score = vol_ratio + (trend * 100) + (100 - abs(rsi - 50)) / 10
    return round(score, 2)

def send_discord_alert(trade):
    try:
        msg = {
            "content": f"ðŸ“ˆ **{trade['symbol']} | {trade['type']}** at `${trade['price']:,.2f}`\nðŸ’¥ Strategy: {trade['reason']} | Heat Score: {trade['heat']}`"
        }
        requests.post(DISCORD_WEBHOOK, json=msg)
    except:
        pass

# ============ DASHBOARD ============ #
st.title("ðŸš€ Sentinex ULTRA AI â€“ Automated Crypto Sniper Bot")

for symbol in ASSETS:
    end = datetime.utcnow()
    start = end - timedelta(days=1)
    request = CryptoBarsRequest(symbol_or_symbols=[symbol], timeframe=TimeFrame.Minute, start=start, end=end)
    bars = client.get_crypto_bars(request).df
    df = bars[bars.index.get_level_values(0) == symbol].reset_index()
    df["rsi"] = calculate_rsi(df["close"])
    heat = calculate_heat_score(df)

    latest = df.iloc[-1]
    price = latest["close"]
    rsi_val = latest["rsi"]
    time = latest["timestamp"]

    should_buy = should_sell = False
    reason = ""

    # RSI BREAKOUT STRATEGY
    if STRATEGY == "RSI_BREAKOUT":
        if rsi_val < 30 and st.session_state.holding[symbol] is None:
            should_buy = True
            reason = "RSI < 30"
        elif rsi_val > 70 and st.session_state.holding[symbol] is not None:
            should_sell = True
            reason = "RSI > 70"

        if st.session_state.holding[symbol] is not None:
            st.session_state.max_price[symbol] = max(st.session_state.max_price[symbol], price)
            if price < st.session_state.max_price[symbol] * 0.97:
                should_sell = True
                reason = "Trailing Stop"

    if should_buy:
        st.session_state.holding[symbol] = price
        st.session_state.max_price[symbol] = price
        trade = {"time": time, "price": price, "type": "BUY", "symbol": symbol, "reason": reason, "heat": heat}
        st.session_state.trade_log.append(trade)
        send_discord_alert(trade)
        st.success(f"BUY {symbol} at ${price:.2f} | Reason: {reason} | Heat Score: {heat}")

    elif should_sell:
        buy_price = st.session_state.holding[symbol]
        pnl = price - buy_price
        st.session_state.realized_pnl[symbol] += pnl
        st.session_state.holding[symbol] = None
        st.session_state.max_price[symbol] = 0
        trade = {"time": time, "price": price, "type": "SELL", "symbol": symbol, "reason": reason, "heat": heat}
        st.session_state.trade_log.append(trade)
        send_discord_alert(trade)
        st.warning(f"SELL {symbol} at ${price:.2f} | P&L: ${pnl:.2f} | Reason: {reason}")

# ============ UI DISPLAY ============ #
for symbol in ASSETS:
    st.subheader(f"ðŸ“ˆ {symbol}")
    st.metric("Realized P&L", f"${st.session_state.realized_pnl[symbol]:,.2f}")
    if st.session_state.holding[symbol]:
        current_price = df["close"].iloc[-1]
        unreal = current_price - st.session_state.holding[symbol]
        st.metric("Unrealized P&L", f"${unreal:,.2f}")

st.markdown("### ðŸ“Š Trade Log")
log_df = pd.DataFrame(st.session_state.trade_log)
if not log_df.empty:
    st.dataframe(log_df.tail(15))
    csv = log_df.to_csv(index=False).encode("utf-8")
    st.download_button("ðŸ“¥ Download Trade Log (CSV)", data=csv, file_name="sentinex_trades.csv", mime="text/csv")
