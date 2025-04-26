import os
import requests
import pandas as pd
import tweepy
from nltk.sentiment import SentimentIntensityAnalyzer
from bs4 import BeautifulSoup
import numpy as np
import time

# Setup for Alpaca API
API_KEY = ' PKHSYF5XH92B8VFNAJFD'
SECRET_KEY = '89KOB1vOSn2c3HeGorQe6zkKa0F4tFgBjbIAi'
BASE_URL = 'https://paper-api.alpaca.markets'


class TradingEnvironment:
    def __init__(self, symbol, qty):
        self.symbol = symbol
        self.qty = qty
        self.state = None

    def reset(self):
        # Initial state setup can be defined here
        self.state = self.fetch_market_data()
        return self.state

    def fetch_market_data(self):
        headers = {
            ' PKHSYF5XH92B8VFNAJFD': API_KEY,
            '89KOB1vOSn2c3HeGorQe6zkKa0F4tFgBjbIAi': SECRET_KEY,
        }
        response = requests.get(f"{BASE_URL}/bars/minute?symbol={self.symbol}&limit=100", headers=headers)
        if response.status_code == 200:
            data = pd.DataFrame(response.json())
            # Compute indicators here if needed, e.g., RSI, SMA
            return data
        else:
            print(f"Error fetching data: {response.json()}")
            return None

    def step(self, action):
        # Implement action execution and return new state and reward
        # Placeholder for trading logic
        reward = self.execute_trade(action)
        self.state = self.fetch_market_data()  # Fetch new state
        return self.state, reward

    def execute_trade(self, action):
        if action == 1:  # Buy
            self.place_order('buy')
            return 1  # Reward for a successful buy
        elif action == 2:  # Sell
            self.place_order('sell')
            return -1  # Reward for a successful sell
        return 0  # Neutral reward for hold

    def place_order(self, side):
        url = f"{BASE_URL}/orders"
        order_data = {
            "symbol": self.symbol,
            "qty": self.qty,
            "side": side,
            "type": "market",
            "time_in_force": "gtc"
        }
        response = requests.post(url, json=order_data, headers={'PKHSYF5XH92B8VFNAJFD': API_KEY, '89KOB1vOSn2c3HeGorQe6zkKa0F4tFgBjbIAisCf': SECRET_KEY})
        if response.status_code == 200:
            print(f"Order executed: {response.json()}")
        else:
            print(f"Error executing order: {response.json()}")


def fetch_news_articles(url):
    articles = []
    response = requests.get(url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        for item in soup.find_all('h2'):
            article_title = item.get_text()
            articles.append(article_title)
    return articles


def fetch_tweets(query):
    # Authenticate to Twitter
    auth = tweepy.OAuth1UserHandler("TWITTER_API_KEY", "TWITTER_API_SECRET")
    api = tweepy.API(auth)
    tweets = api.search_tweets(q=query, count=100, lang='en')
    return [tweet.text for tweet in tweets]


def analyze_sentiment(texts):
    sia = SentimentIntensityAnalyzer()
    sentiment_scores = [sia.polarity_scores(text)['compound'] for text in texts]
    return np.mean(sentiment_scores)  # Average sentiment score


def compute_rsi(prices, period=14):
    delta = prices.diff(1)
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))


def make_decision(data, sentiment_score):
    # Implement your decision logic based on indicators and sentiment
    last_rsi = compute_rsi(data['close'].astype(float)).iloc[-1]
    
    if sentiment_score > 0.05 and last_rsi < 30:
        return 1  # Buy
    elif sentiment_score < -0.05 and last_rsi > 70:
        return 2  # Sell
    return 0  # Hold


def trading_logic():
    symbol = 'BTC/USD'
    qty = 0.01
    environment = TradingEnvironment(symbol, qty)
    
    while True:
        environment.reset()
        news_articles = fetch_news_articles('https://www.coindesk.com/')
        tweets = fetch_tweets("Bitcoin")
        sentiment_score = analyze_sentiment(news_articles + tweets)
        
        market_data = environment.fetch_market_data()
        action = make_decision(market_data, sentiment_score)
        
        state, reward = environment.step(action)  # Execute trade

        time.sleep(60)  # Wait before making the next decision


if __name__ == "__main__":
    trading_logic()
