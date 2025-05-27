import pandas as pd
import requests
from transformers import pipeline

class DataManager:
    def __init__(self, config):
        self.config = config
        self.sentiment_model = pipeline("sentiment-analysis") if config['sentiment']['enabled'] else None

    def get_symbols(self):
        url = 'https://datahub.io/core/s-and-p-500-companies/r/constituents.csv'
        return pd.read_csv(url)['Symbol'].tolist()

    def get_bars(self, symbols):
        # Fetch historical bars for all symbols (implement batching for efficiency)
        bars_data = {}
        for symbol in symbols:
            # Fetch data from Alpaca or other provider
            bars_data[symbol] = self.fetch_symbol_bars(symbol)
        return bars_data

    def get_news_sentiment(self, symbols):
        news_sentiment = {}
        for symbol in symbols:
            headlines = self.fetch_news(symbol)
            if self.sentiment_model and headlines:
                sentiments = self.sentiment_model(headlines)
                avg_sentiment = sum(1 if s['label']=='POSITIVE' else -1 for s in sentiments) / len(sentiments)
                news_sentiment[symbol] = avg_sentiment
        return news_sentiment

    def fetch_symbol_bars(self, symbol):
        # TODO: Implement Alpaca or Yahoo Finance data fetch here
        # Placeholder example:
        return {"close": [100, 101, 102], "volume": [1000, 1100, 1200]}

    def fetch_news(self, symbol):
        api_key = self.config['news']['api_key']
        url = f"https://newsapi.org/v2/everything?q={symbol}&apiKey={api_key}"
        try:
            resp = requests.get(url)
            articles = resp.json().get('articles', [])
            return [a['title'] for a in articles[:5]]
        except Exception:
            return []
