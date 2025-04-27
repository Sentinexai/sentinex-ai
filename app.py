import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from alpaca_trade_api import REST
import requests
import time
import os
import streamlit as st
from datetime import datetime
from tenacity import retry, stop_after_attempt, wait_fixed

# Configuration from Streamlit Secrets
API_KEY = st.secrets["ALPACA_KEY"]
API_SECRET = st.secrets["ALPACA_SECRET"]
BASE_URL = "https://paper-api.alpaca.markets"

class EnhancedSentimentAnalyzer:
    def __init__(self):
        self.tokenizer = AutoTokenizer.from_pretrained("ProsusAI/finbert")
        self.model = AutoModelForSequenceClassification.from_pretrained("ProsusAI/finbert")
        
    def analyze(self, text):
        inputs = self.tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
        outputs = self.model(**inputs)
        return torch.softmax(outputs.logits, dim=1)[0, 1].item()

class QuantumLSTM(nn.Module):
    def __init__(self, input_size=6, hidden_size=64):
        super().__init__()
        self.lstm = nn.LSTM(input_size, hidden_size, batch_first=True)
        self.attention = nn.MultiheadAttention(hidden_size, 4)
        self.fc = nn.Sequential(
            nn.Linear(hidden_size, 32),
            nn.ReLU(),
            nn.Linear(32, 3)  # [Long, Short, Hold]
        )
        
    def forward(self, x):
        out, _ = self.lstm(x)
        out, _ = self.attention(out, out, out)
        return torch.softmax(self.fc(out[:, -1]), dim=1)

class AdvancedRiskManager:
    def __init__(self, initial_balance=10000):
        self.balance = initial_balance
        self.positions = {}
        
    def calculate_position_size(self, current_price, atr):
        risk_amount = self.balance * 0.02
        size = risk_amount / (atr * 3)
        return min(int(size / current_price), int(self.balance * 0.1 / current_price))

class SentinexAITrader:
    def __init__(self):
        self.api = REST(API_KEY, API_SECRET, BASE_URL)
        self.sentiment = EnhancedSentimentAnalyzer()
        self.predictor = QuantumLSTM()
        self._load_model()
        self.risk_manager = AdvancedRiskManager(float(self.api.get_account().equity))
        self.symbols = self._screen_stocks()
        
    def _load_model(self):
        try:
            self.predictor.load_state_dict(
                torch.load('quantum_predictor.pth', map_location='cpu'),
                strict=False
            )
            st.success("Model loaded successfully")
        except Exception as e:
            st.warning(f"Model load failed: {str(e)}. Initializing new model...")
            torch.save(self.predictor.state_dict(), 'quantum_predictor.pth')
        
    def _screen_stocks(self):
        assets = self.api.list_assets(status='active')
        return [
            asset.symbol for asset in assets
            if self._is_eligible(asset)
        ]
        
    def _is_eligible(self, asset):
        try:
            bar = self.api.get_latest_bar(asset.symbol)
            return (asset.tradable and 
                    bar.close < 10 and 
                    bar.volume > 1_000_000 and
                    self.api.get_asset(asset.symbol).shortable)
        except Exception:
            return False
    
    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
    def get_market_data(self, symbol):
        bars = self.api.get_bars(symbol, '15Min', limit=50).df
        bars['returns'] = bars['close'].pct_change()
        bars['atr'] = (bars['high'] - bars['low']).rolling(14).mean()
        return bars.dropna()
    
    def get_news_sentiment(self, symbol):
        try:
            news = requests.get(
                "https://newsapi.org/v2/everything",
                params={
                    "q": symbol,
                    "apiKey": st.secrets["NEWS_API_KEY"],
                    "pageSize": 3
                },
                timeout=5
            ).json()
            return [article['title'] for article in news.get('articles', [])]
        except Exception as e:
            st.error(f"News API error: {str(e)}")
            return []
    
    def predict_movement(self, data):
        features = data[['open', 'high', 'low', 'close', 'volume', 'atr']].values
        tensor_data = torch.FloatTensor(features).unsqueeze(0)
        with torch.no_grad():
            probs = self.predictor(tensor_data)[0].numpy()
        return np.argmax(probs)  # 0=Long, 1=Short, 2=Hold
    
    def execute_trade(self, symbol, action, current_price, atr):
        try:
            position = self.api.get_position(symbol)
            if position:
                if (position.side == 'long' and action == 1) or (position.side == 'short' and action == 0):
                    self.api.close_position(symbol)
                    st.info(f"Closed {position.side} position in {symbol}")

            if action in [0, 1]:  # Only trade if not Hold
                size = self.risk_manager.calculate_position_size(current_price, atr)
                if size > 0:
                    order_type = 'limit'
                    limit_price = current_price * 0.995 if action == 0 else current_price * 1.005
                    
                    self.api.submit_order(
                        symbol=symbol,
                        qty=size,
                        side='buy' if action == 0 else 'sell',
                        type=order_type,
                        limit_price=limit_price,
                        time_in_force='gtc'
                    )
                    st.success(f"Opened {'long' if action == 0 else 'short'} position in {symbol}")
        except Exception as e:
            st.error(f"Trade execution error: {str(e)}")

    def run(self):
        while True:
            self.symbols = self._screen_stocks()
            for symbol in self.symbols:
                try:
                    data = self.get_market_data(symbol)
                    if len(data) < 20:
                        continue
                        
                    current_price = data['close'].iloc[-1]
                    atr = data['atr'].iloc[-1]
                    news = self.get_news_sentiment(symbol)
                    
                    # Generate predictions
                    action = self.predict_movement(data)
                    sentiment = np.mean([self.sentiment.analyze(h) for h in news]) if news else 0.5
                    
                    # Trading logic
                    if action == 0 and sentiment > 0.6:  # Long
                        self.execute_trade(symbol, 0, current_price, atr)
                    elif action == 1 and sentiment < 0.4:  # Short
                        self.execute_trade(symbol, 1, current_price, atr)
                        
                except Exception as e:
                    st.error(f"Error processing {symbol}: {str(e)}")
            
            time.sleep(300)
            self.risk_manager.balance = float(self.api.get_account().equity)

if __name__ == "__main__":
    st.title("Sentinex AI Trading Bot")
    bot = SentinexAITrader()
    bot.run()

