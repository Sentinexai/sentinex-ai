import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from alpaca_trade_api.rest import REST
from ta.momentum import RSIIndicator
from ta.trend import MACD
from collections import deque
import random
import time

# ===== USER PROVIDED CONFIGURATION =====
API_KEY = "PKHSYF5XH92B8VFNAJFD"
SECRET_KEY = "89KOB1vOSn2c3HeGorQe6zkKa0F4tFgBjbIAisCf"
BASE_URL = "https://paper-api.alpaca.markets"
CRYPTO_SYMBOL = 'BTC/USD'  # Alpaca's crypto format

# ===== SELF-CONTAINED ADVANCED BOT =====
class AdvancedCryptoTradingSystem:
    def __init__(self):
        self.api = REST(API_KEY, SECRET_KEY, BASE_URL)
        self.trade_history = deque(maxlen=200)
        self.learning_memory = deque(maxlen=1000)
        self.position_size = 0.01  # Risk 1% per trade
        self.current_position = None
        
    def get_market_data(self):
        """Get consolidated crypto data from Alpaca"""
        try:
            bars = self.api.get_crypto_bars(CRYPTO_SYMBOL, '15Min', limit=50).df
            return bars.reset_index()
        except Exception as e:
            st.error(f"Data Error: {str(e)}")
            return pd.DataFrame()

    def generate_synthetic_news(self):
        """Simulate news events based on price action"""
        bars = self.get_market_data()
        if len(bars) < 2:
            return 0.5  # Neutral sentiment
        
        last_change = (bars['close'].iloc[-1] - bars['close'].iloc[-2]) / bars['close'].iloc[-2]
        if abs(last_change) > 0.03:
            return 1.0 if last_change > 0 else 0.0  # Strong sentiment
        return 0.5 + random.uniform(-0.2, 0.2)  # Random noise

    def technical_analysis(self, bars):
        """Multi-indicator consensus system"""
        if len(bars) < 20:
            return 0.5  # Neutral if insufficient data
            
        rsi = RSIIndicator(bars['close']).rsi().iloc[-1]
        macd = MACD(bars['close']).macd_diff().iloc[-1]
        
        # Consensus scoring system
        rsi_score = 1 if rsi < 35 else 0 if rsi > 65 else 0.5
        macd_score = 1 if macd > 0 else 0
        return (rsi_score + macd_score) / 2

    def risk_managed_order(self, decision):
        """Smart order execution with position management"""
        current_price = self.get_market_data()['close'].iloc[-1]
        account = self.api.get_account()
        
        if decision == "buy" and not self.current_position:
            qty = (float(account.buying_power) * self.position_size) / current_price
            self.api.submit_order(
                symbol=CRYPTO_SYMBOL,
                qty=round(qty, 6),
                side='buy',
                type='market',
                time_in_force='gtc'
            )
            self.current_position = current_price
            return f"Bought {round(qty, 4)} {CRYPTO_SYMBOL}"
            
        elif decision == "sell" and self.current_position:
            positions = self.api.list_positions()
            for pos in positions:
                if pos.symbol == CRYPTO_SYMBOL.replace('/', ''):
                    self.api.submit_order(
                        symbol=CRYPTO_SYMBOL,
                        qty=pos.qty,
                        side='sell',
                        type='market',
                        time_in_force='gtc'
                    )
                    profit = (current_price - self.current_position) * float(pos.qty)
                    self.learn_from_trade(profit)
                    self.current_position = None
                    return f"Sold {pos.qty} {CRYPTO_SYMBOL} | Profit: ${profit:.2f}"
        return "No action taken"

    def learn_from_trade(self, profit):
        """Reinforcement learning from trade outcomes"""
        memory_entry = {
            'timestamp': pd.Timestamp.now(),
            'profit': profit,
            'position_size': self.position_size,
            'market_conditions': self.analyze_market_context()
        }
        self.learning_memory.append(memory_entry)
        
        # Adaptive risk management
        if profit > 0:
            self.position_size = min(0.05, self.position_size * 1.1)
        else:
            self.position_size = max(0.005, self.position_size * 0.9)

    def analyze_market_context(self):
        """Feature engineering for learning system"""
        bars = self.get_market_data()
        if len(bars) < 10:
            return {}
            
        return {
            'volatility': bars['close'].pct_change().std(),
            'trend_strength': (bars['close'].iloc[-1] - bars['close'].iloc[-10]) / bars['close'].iloc[-10],
            'volume_ratio': bars['volume'].iloc[-1] / bars['volume'].mean()
        }

    def make_decision(self):
        """Core decision-making logic"""
        bars = self.get_market_data()
        if bars.empty:
            return "hold"
            
        news_score = self.generate_synthetic_news()
        tech_score = self.technical_analysis(bars)
        
        # Consensus decision matrix
        if news_score > 0.7 and tech_score > 0.7:
            return "buy"
        elif news_score < 0.3 and tech_score < 0.3:
            return "sell"
        return "hold"

# ===== STREAMLIT INTERFACE =====
st.title("🔐 Advanced Crypto Trading System (Paper Trading)")
st.caption(f"Connected to Alpaca: {CRYPTO_SYMBOL}")

if 'trading_system' not in st.session_state:
    st

