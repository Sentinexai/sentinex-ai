import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from alpaca_trade_api import REST
import requests
import time
import os
from datetime import datetime

# Configuration
API_KEY = "PKHSYF5XH92B8VFNAJFD"
API_SECRET = "89KOB1vOSn2c3HeGorQe6zkKa0F4tFgBjbIAisCf"
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
            nn.Linear(32, 2)  # Output: [Long confidence, Short confidence]
        )
        
    def forward(self, x):
        out, _ = self.lstm(x)
        out, _ = self.attention(out, out, out)
        return torch.sigmoid(self.fc(out[:, -1]))

class AdvancedRiskManager:
    def __init__(self, initial_balance=10000):
        self.balance = initial_balance
        self.positions = {}  # Tracks {symbol: {'side': 'long/short', 'qty': N}}
        
    def calculate_position_size(self, current_price, atr, direction):
        risk_amount = self.balance * 0.02  # 2% risk per trade
        size = risk_amount / (atr * 3)
        max_shares = int(min(size, self.balance * 0.1) / current_price)
        return max(max_shares, 1)

class SentinexAITrader:
    def __init__(self):
        self.api = REST(API_KEY, API_SECRET, BASE_URL)
        self.sentiment = EnhancedSentimentAnalyzer()
        self.predictor = QuantumLSTM()
        self.predictor.load_state_dict(torch.load('quantum_predictor.pth'))
        self.risk_manager = AdvancedRiskManager(float(self.api.get_account().equity))
        self.symbols = self._screen_stocks()
        
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
                    bar.volume > 1000000 and
                    self.api.get_asset(asset.symbol).shortable)
        except:
            return False
    
    def get_market_data(self, symbol):
        bars = self.api.get_bars(symbol, '15Min', limit=50).df
        bars['returns'] = bars['close'].pct_change()
        bars['atr'] = (bars['high'] - bars['low']).rolling(14).mean()
        return bars.dropna()
    
    def get_news_sentiment(self, symbol):
        news = requests.get(f"https://newsapi.org/v2/everything?q={symbol}&apiKey={os.getenv('NEWS_API_KEY')}").json()
        return [article['title'] for article in news.get('articles', [])[:3]]
    
    def predict_movement(self, data):
        features = data[['open', 'high', 'low', 'close', 'volume', 'atr']].values
        tensor_data = torch.FloatTensor(features).unsqueeze(0)
        long_conf, short_conf = self.predictor(tensor_data)[0].tolist()
        return 'long' if long_conf > 0.7 else 'short' if short_conf > 0.7 else 'hold'
    
    def execute_trade(self, symbol, action, current_price, atr):
        try:
            position = self.api.get_position(symbol) if self.api.get_position(symbol) else None
            
            # Close opposite positions first
            if position:
                if (position.side == 'long' and action == 'short') or (position.side == 'short' and action == 'long'):
                    self.api.close_position(symbol)
                    print(f"Closed {position.side} position in {symbol}")

            # Calculate position size
            size = self.risk_manager.calculate_position_size(current_price, atr, action)
            
            if action == 'long':
                self.api.submit_order(
                    symbol=symbol,
                    qty=size,
                    side='buy',
                    type='limit',
                    limit_price=current_price * 0.995,
                    time_in_force='gtc'
                )
                print(f"Opened long: {size} shares of {symbol} at limit ${current_price * 0.995:.2f}")
                
            elif action == 'short':
                self.api.submit_order(
                    symbol=symbol,
                    qty=size,
                    side='sell',
                    type='limit',
                    limit_price=current_price * 1.005,
                    time_in_force='gtc'
                )
                print(f"Opened short: {size} shares of {symbol} at limit ${current_price * 1.005:.2f}")
                
        except Exception as e:
            print(f"Trade execution error: {str(e)}")

    def run(self):
        while True:
            self.symbols = self._screen_stocks()
            for symbol in self.symbols:
                try:
                    data = self.get_market_data(symbol)
                    if len(data) < 20: continue
                    
                    current_price = data['close'].iloc[-1]
                    atr = data['atr'].iloc[-1]
                    news = self.get_news_sentiment(symbol)
                    
                    # Generate predictions
                    price_action = self.predict_movement(data)
                    sentiment = np.mean([self.sentiment.analyze(h) for h in news])
                    
                    # Trading logic
                    if price_action == 'long' and sentiment > 0.6:
                        self.execute_trade(symbol, 'long', current_price, atr)
                    elif price_action == 'short' and sentiment < 0.4:
                        self.execute_trade(symbol, 'short', current_price, atr)
                        
                except Exception as e:
                    print(f"Error processing {symbol}: {str(e)}")
            
            time.sleep(300)
            self.risk_manager.balance = float(self.api.get_account().equity)

if __name__ == "__main__":
    bot = SentinexAITrader()
    print("🚀 Starting Sentinex AI Quantum Trading Bot")
    bot.run()

