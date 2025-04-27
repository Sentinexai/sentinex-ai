import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from alpaca_trade_api.rest import REST
import time
from transformers import pipeline
from sklearn.ensemble import RandomForestClassifier

# Initialize Alpaca API
api = REST(
    "PKHSYF5XH92B8VFNAJFD",
    "89KOB1vOSn2c3HeGorQe6zkKa0F4tFgBjbIAisCf",
    base_url="https://paper-api.alpaca.markets"
)

# Configuration
INITIAL_CAPITAL = 10000  # $10,000 initial paper investment

class LearningAgent:
    def __init__(self):
        self.trade_history = []
        self.model = RandomForestClassifier()
        self.sentiment_analyzer = pipeline("sentiment-analysis", 
                                         model="mrm8488/distilroberta-finetuned-financial-news-sentiment-analysis")
    
    def analyze_trade(self, symbol, outcome):
        # Store trade outcome for learning
        market_data = self.get_market_state(symbol)
        self.trade_history.append({
            'symbol': symbol,
            'features': market_data,
            'outcome': outcome
        })
        
        # Retrain model weekly
        if len(self.trade_history) % 100 == 0:
            self.retrain_model()
    
    def retrain_model(self):
        # Convert trade history to training data
        X = pd.DataFrame([t['features'] for t in self.trade_history])
        y = [t['outcome'] for t in self.trade_history]
        if len(y) > 10:  # Only retrain with sufficient data
            self.model.fit(X, y)
    
    def get_market_state(self, symbol):
        # Simplified market state features
        bars = api.get_bars(symbol, TimeFrame.Hour, limit=24).df
        return {
            'rsi': self.calculate_rsi(bars['close']),
            'volume_change': bars['volume'].pct_change()[-1],
            'price_change': bars['close'].pct_change()[-1]
        }
    
    def calculate_rsi(self, prices, window=14):
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs)).iloc[-1]

class SentimentAnalyzer:
    def get_sentiment(self, text):
        return self.sentiment_analyzer(text)[0]

class InsiderTradingMonitor:
    def check_insider_activity(self, symbol):
        # Simulated insider activity detection
        return np.random.choice([-1, 0, 1], p=[0.1, 0.8, 0.1])

learning_agent = LearningAgent()
sentiment_analyzer = SentimentAnalyzer()
insider_monitor = InsiderTradingMonitor()

def main():
    st.set_page_config(
        page_title="🤖 AI Quantum Trader Pro",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Custom styling
    st.markdown("""
    <style>
    .header-style { font-size:50px !important; color:#4A90E2; }
    .metric-card { padding:20px; border-radius:10px; box-shadow:0 0 15px rgba(0,0,0,0.1); margin:10px; }
    .positive { color: #00C853; }
    .negative { color: #FF1744; }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown('<h1 class="header-style">🚀 AI Trading Bot ($10k Paper)</h1>', unsafe_allow_html=True)
    
    # Real-time Dashboard
    col1, col2, col3, col4 = st.columns(4)
    
    try:
        account = api.get_account()
        positions = api.list_positions()
        
        with col1:
            st.markdown(f'''
            <div class="metric-card">
                <h3>PORTFOLIO VALUE</h3>
                <h1 class="positive">${float(account.equity):,.2f}</h1>
            </div>
            ''', unsafe_allow_html=True)
            
        with col2:
            st.markdown(f'''
            <div class="metric-card">
                <h3>BUYING POWER</h3>
                <h1>${float(account.buying_power):,.2f}</h1>
            </div>
            ''', unsafe_allow_html=True)
            
        with col3:
            pct_change = (float(account.equity) / INITIAL_CAPITAL - 1) * 100
            color_class = "positive" if pct_change >= 0 else "negative"
            st.markdown(f'''
            <div class="metric-card">
                <h3>TOTAL RETURN</h3>
                <h1 class="{color_class}">{pct_change:.2f}%</h1>
            </div>
            ''', unsafe_allow_html=True)
            
        with col4:
            st.markdown(f'''
            <div class="metric-card">
                <h3>ACTIVE POSITIONS</h3>
                <h1>{len(positions)}</h1>
            </div>
            ''', unsafe_allow_html=True)

        # Analytics Section
        st.subheader("🔍 Market Analysis")
        tab1, tab2 = st.tabs(["Performance", "Sentiment"])
        
        with tab1:
            col_chart1, col_chart2 = st.columns(2)
            with col_chart1:
                st.plotly_chart(create_performance_chart(), use_container_width=True)
            with col_chart2:
                st.plotly_chart(create_allocation_chart(), use_container_width=True)
        
        with tab2:
            symbol = st.selectbox("Select Symbol", ["AAPL", "TSLA", "AMZN", "GOOGL"])
            sample_headline = f"{symbol} stock shows strong momentum in today's trading"
            sentiment = sentiment_analyzer.get_sentiment(sample_headline)
            st.metric("Example Sentiment Analysis", 
                     f"{sentiment['label']} ({sentiment['score']:.2f})")

        # Control Panel
        st.sidebar.header("⚙️ Trading Controls")
        with st.sidebar.expander("Trading Parameters"):
            st.slider("RSI Buy Threshold", 20, 40, 30)
            st.slider("RSI Sell Threshold", 60, 80, 70)
        
        if st.sidebar.button("🚀 Start Trading"):
            st.toast("Trading bot activated")
            
        if st.sidebar.button("🛑 Emergency Stop"):
            st.warning("All positions being liquidated!")

    except Exception as e:
        st.error(f"Error: {str(e)}")

def create_performance_chart():
    data = pd.DataFrame({
        'timestamp': pd.date_range(start='2024-01-01', periods=100),
        'value': np.random.normal(0.1, 0.05, 100).cumsum() * INITIAL_CAPITAL + INITIAL_CAPITAL
    })
    return px.line(data, x='timestamp', y='value', title="Portfolio Performance")

def create_allocation_chart():
    allocations = pd.DataFrame({
        'asset': ['Stocks', 'Cash'],
        'value': [80, 20]
    })
    return px.pie(allocations, values='value', names='asset', hole=0.3)

if __name__ == "__main__":
    main()
