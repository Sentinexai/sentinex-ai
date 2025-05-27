import numpy as np

class Strategy:
    def __init__(self, config):
        self.config = config

    def find_opportunities(self, bars_data, news_sentiment):
        opportunities = {}
        for symbol, bars in bars_data.items():
            price = bars['close'][-1]
            volume = bars['volume'][-1]
            sentiment = news_sentiment.get(symbol, 0)
            # Example: combine technical and sentiment
            if price < self.config['stock_selection']['max_price'] and volume > self.config['stock_selection']['min_volume']:
                rsi = self.calculate_rsi(bars['close'])
                if rsi < 35 and sentiment > 0:
                    opportunities[symbol] = "buy"
        return opportunities

    def calculate_rsi(self, prices, window=14):
        prices = np.array(prices)
        delta = np.diff(prices)
        up = delta.clip(min=0)
        down = -delta.clip(max=0)
        avg_gain = np.mean(up[-window:]) if len(up) >= window else 0
        avg_loss = np.mean(down[-window:]) if len(down) >= window else 1  # avoid zero division
        rs = avg_gain / avg_loss if avg_loss != 0 else 1
        return 100 - (100 / (1 + rs))

    def position_size(self, cash, price):
        risk = self.config['risk']['risk_per_trade']
        return int((cash * risk) // price)

    def should_exit(self, symbol, bars, sentiment):
        price = bars['close'][-1]
        if sentiment < 0 or price < np.mean(bars['close'][-5:]):
            return True
        return False
