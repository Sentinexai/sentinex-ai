import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import requests
import plotly.graph_objects as go
from alpaca.data.historical import CryptoHistoricalDataClient, StockHistoricalDataClient
from alpaca.data.requests import CryptoBarsRequest, StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from streamlit_autorefresh import st_autorefresh
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ===== USER CONFIG =====
CRYPTO_ASSETS = ["BTC/USD", "ETH/USD", "SOL/USD", "MATIC/USD"]
STOCK_ASSETS = ["AAPL", "TSLA", "NVDA", "SPY"]
SHEET_URL = st.secrets.get("SHEET_URL", "")  # Set your Google Sheets URL here or in Streamlit secrets
DISCORD_WEBHOOK = st.secrets.get("DISCORD_WEBHOOK", "")  # Optional: Set your Discord webhook

ALPACA_API_KEY = st.secrets.get("ALPACA_API_KEY", "")
ALPACA_API_SECRET = st.secrets.get("ALPACA_API_SECRET", "")
ALPACA_PAPER = True

# ===== PAGE CONFIG =====
st.set_page_config(page_title="Sentinex ULTRA", layout="wide")
st.title("🚀 Sentinex ULTRA AI – Automated Sniper Bot (Crypto + Stocks)")
st_autorefresh(interval=60_000, key="refresh")

# ===== SESSION STATE =====
if "holding" not in st.session_state:
    st.session_state.holding = {}
if "max_price" not in st.session_state:
    st.session_state.max_price = {}
if "realized_pnl" not in st.session_state:
    st.session_state.realized_pnl = {}
if "trade_log" not in st.session_state:
    st.session_state.trade_log = []
if "asset_mode" not in st.session_state:
    st.session_state.asset_mode = "crypto"

# ===== SHEETS SETUP =====
def get_gs_client():
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
        return gspread.authorize(creds)
    except Exception as e:
        st.error("Google Sheets connection failed: "+str(e))
        return None

def log_trade_to_sheet(trade):
    if not SHEET_URL:
        return
    gc = get_gs_client()
    if not gc:
        return
    try:
        sh = gc.open_by_url(SHEET_URL)
        ws_name = "Crypto Trades" if trade["asset_type"] == "Crypto" else "Stock Trades"
        worksheet = sh.worksheet(ws_name)
        worksheet.append_row([
            trade["time"], trade["symbol"], trade["type"], trade["price"], trade["reason"],
            trade["heat"], trade["pnl"], trade["asset_type"]
        ])
    except Exception as e:
        st.warning("Failed to log trade to Google Sheet: "+str(e))

def send_discord_alert(trade):
    if not DISCORD_WEBHOOK:
        return
    msg = {
        "content": f"📈 **{trade['symbol']} | {trade['type']}** at `${trade['price']:,.2f}`\n💥 Strategy: {trade['reason']} | Heat: {trade['heat']}\nP&L: {trade['pnl']:.2f if trade['pnl'] else 0} | {trade['asset_type']}"
    }
    try:
        requests.post(DISCORD_WEBHOOK, json=msg, timeout=3)
    except:
        pass

# ===== STRATEGY LOGIC =====
def calculate_rsi(close, period=14):
    delta = close.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_heat_score(df):
    vol_ratio = df["volume"].iloc[-1] / (df["volume"].mean() or 1)
    trend = df["close"].pct_change().rolling(5).mean().iloc[-1]
    rsi = calculate_rsi(df["close"]).iloc[-1]
    score = vol_ratio + (trend * 100) + (100 - abs(rsi - 50)) / 10
    return round(score, 2)

# ===== UI: MODE SELECTOR =====
mode = st.selectbox("Asset Type", ["Crypto", "Stocks"], key="mode")
st.session_state.asset_mode = mode.lower()

if st.session_state.asset_mode == "crypto":
    assets = CRYPTO_ASSETS
    client = CryptoHistoricalDataClient()
else:
    assets = STOCK_ASSETS
    client = StockHistoricalDataClient()

strategy = st.selectbox("Strategy", ["RSI Breakout", "MA Crossover"], key="strategy")

# ===== MAIN TRADING LOGIC LOOP =====
for symbol in assets:
    # --- Pull bars ---
    end = datetime.utcnow()
    start = end - timedelta(days=2)
    if st.session_state.asset_mode == "crypto":
        req = CryptoBarsRequest(symbol_or_symbols=[symbol], timeframe=TimeFrame.Minute, start=start, end=end)
    else:
        req = StockBarsRequest(symbol_or_symbols=[symbol], timeframe=TimeFrame.Minute, start=start, end=end)
    bars = client.get_crypto_bars(req).df if st.session_state.asset_mode == "crypto" else client.get_stock_bars(req).df
    df = bars[bars.index.get_level_values(0) == symbol].reset_index()
    if "close" not in df.columns or df.empty:
        st.warning(f"No data for {symbol}, skipping...")
        continue
    df["rsi"] = calculate_rsi(df["close"])
    df["ma"] = df["close"].rolling(14).mean()
    heat = calculate_heat_score(df)
    latest = df.iloc[-1]
    price = latest["close"]
    rsi_val = latest["rsi"]
    ma_val = latest["ma"]
    time = str(latest["timestamp"])
    should_buy = should_sell = False
    reason = ""
    # --- Strategy Logic ---
    if strategy == "RSI Breakout":
        if rsi_val < 30 and st.session_state.holding.get(symbol) is None:
            should_buy = True
            reason = "RSI < 30"
        elif rsi_val > 70 and st.session_state.holding.get(symbol) is not None:
            should_sell = True
            reason = "RSI > 70"
        if st.session_state.holding.get(symbol) is not None:
            st.session_state.max_price[symbol] = max(st.session_state.max_price.get(symbol, price), price)
            if price < st.session_state.max_price[symbol] * 0.97:
                should_sell = True
                reason = "Trailing Stop"
    elif strategy == "MA Crossover":
        prev_close = df["close"].iloc[-2]
        prev_ma = df["ma"].iloc[-2]
        if prev_close < prev_ma and price > ma_val and st.session_state.holding.get(symbol) is None:
            should_buy = True
            reason = "MA Bullish Cross"
        elif prev_close > prev_ma and price < ma_val and st.session_state.holding.get(symbol) is not None:
            should_sell = True
            reason = "MA Bearish Cross"
    # --- Execute Logic ---
    if should_buy:
        st.session_state.holding[symbol] = price
        st.session_state.max_price[symbol] = price
        trade = {
            "time": time, "price": price, "type": "BUY", "symbol": symbol,
            "reason": reason, "heat": heat, "pnl": None, "asset_type": mode
        }
        st.session_state.trade_log.append(trade)
        log_trade_to_sheet(trade)
        send_discord_alert(trade)
        st.success(f"BUY {symbol} at ${price:.2f} | {reason} | Heat: {heat}")
    elif should_sell:
        buy_price = st.session_state.holding.get(symbol)
        pnl = price - buy_price if buy_price else 0
        st.session_state.realized_pnl[symbol] = st.session_state.realized_pnl.get(symbol, 0) + pnl
        st.session_state.holding[symbol] = None
        st.session_state.max_price[symbol] = 0
        trade = {
            "time": time, "price": price, "type": "SELL", "symbol": symbol,
            "reason": reason, "heat": heat, "pnl": pnl, "asset_type": mode
        }
        st.session_state.trade_log.append(trade)
        log_trade_to_sheet(trade)
        send_discord_alert(trade)
        st.warning(f"SELL {symbol} at ${price:.2f} | P&L: ${pnl:.2f} | {reason}")

# ===== UI: P&L + LOG =====
for symbol in assets:
    st.subheader(f"📈 {symbol}")
    st.metric("Realized P&L", f"${st.session_state.realized_pnl.get(symbol, 0):,.2f}")
    if st.session_state.holding.get(symbol):
        current_price = price
        unreal = current_price - st.session_state.holding[symbol]
        st.metric("Unrealized P&L", f"${unreal:,.2f}")

st.markdown("### 📊 Trade Log")
log_df = pd.DataFrame(st.session_state.trade_log)
if not log_df.empty:
    st.dataframe(log_df.tail(15))
    csv = log_df.to_csv(index=False).encode("utf-8")
    st.download_button("📥 Download Trade Log (CSV)", data=csv, file_name="sentinex_trades.csv", mime="text/csv")

st.info("Built by Sentinex AI. Phase 2: Multi-timeframe, AI scoring, and more coming soon!")

