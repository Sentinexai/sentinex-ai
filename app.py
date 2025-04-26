import streamlit as st
import pandas as pd
import plotly.graph_objs as go
import alpaca_trade_api as tradeapi
import requests
from transformers import pipeline

# --- Alpaca Paper Trading Credentials ---
API_KEY = "PKHSYF5XH92B8VFNAJFD"
SECRET_KEY = "89KOB1vOSn2c3HeGorQe6zkKa0F4tFgBjbIAisCf"
BASE_URL = "https://paper-api.alpaca.markets"

# --- News API (for demonstration, limited requests) ---
NEWS_API_KEY = "demo"  # Replace with your NewsAPI.org key for production

# --- Initialize Alpaca API ---
api = tradeapi.REST(API_KEY, SECRET_KEY, BASE_URL, api_version='v2')

# --- Sentiment Analysis Pipeline ---
@st.cache_resource
def get_sentiment_analyzer():
    return pipeline("sentiment-analysis", model="ProsusAI/finbert")

sentiment_analyzer = get_sentiment_analyzer()

# --- Get Latest Market Data ---
def get_latest_bar(symbol):
    barset = api.get_barset(symbol, 'minute', limit=5)
    bars = barset[symbol]
    df = pd.DataFrame([{
        'time': bar.t,
        'open': bar.o,
        'high': bar.h,
        'low': bar.l,
        'close': bar.c,
        'volume': bar.v
    } for bar in bars])
    return df

# --- Get Latest News ---
def get_latest_news(symbol):
    url = f"https://newsapi.org/v2/everything?q={symbol}&apiKey={NEWS_API_KEY}&sortBy=publishedAt&language=en"
    response = requests.get(url)
    articles = response.json().get("articles", [])
    return articles[:5]

# --- Trade Signal Logic ---
def should_trade(latest_news, bars):
    for article in latest_news:
        sentiment = sentiment_analyzer(article["title"])[0]
        if sentiment["label"] == "positive" and bars['close'].iloc[-1] > bars['open'].iloc[-1]:
            return "buy"
        if sentiment["label"] == "negative" and bars['close'].iloc[-1] < bars['open'].iloc[-1]:
            return "sell"
    return "hold"

# --- Trade Execution ---
def execute_trade(symbol, side, qty=1):
    try:
        api.submit_order(
            symbol=symbol,
            qty=qty,
            side=side,
            type="market",
            time_in_force="gtc"
        )
        st.success(f"Executed {side.upper()} order for {symbol} ({qty} shares)")
    except Exception as e:
        st.error(f"Trade execution failed: {e}")

# --- Streamlit UI ---
st.title("🚀 Advanced Alpaca Trading Bot (Paper Trading)")
symbol = st.text_input("Enter symbol", value="AAPL")

if st.button("Run Bot"):
    with st.spinner("Fetching data and analyzing..."):
        bars = get_latest_bar(symbol)
        news = get_latest_news(symbol)
        signal = should_trade(news, bars)
        st.write(f"**Trade Signal:** `{signal.upper()}`")
        if signal in ["buy", "sell"]:
            execute_trade(symbol, signal)
        # Candlestick chart
        fig = go.Figure(data=[go.Candlestick(
            x=bars['time'],
            open=bars['open'],
            high=bars['high'],
            low=bars['low'],
            close=bars['close']
        )])
        st.plotly_chart(fig)
        # News headlines
        st.subheader("Latest News")
        for article in news:
            st.write(f"**{article['title']}**")
            st.write(article['description'])

# --- Account Info ---
if st.checkbox("Show Account Info"):
    account = api.get_account()
    st.write(f"Account Number: {account.account_number}")
    st.write(f"Buying Power: {account.buying_power}")
    st.write(f"Portfolio Value: {account.portfolio_value}")

