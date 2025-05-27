import os
import time
import json
import logging
import datetime
import requests
import pandas as pd
import numpy as np
import pytz
from transformers import pipeline
from alpaca.trading.client import TradingClient
from alpaca.trading.enums import OrderSide, TimeInForce
from dotenv import load_dotenv

# ========== CONFIGURATION ==========

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
load_dotenv()

with open('config.json') as f:
    config = json.load(f)

ALPACA_API_KEY = os.getenv("ALPACA_API_KEY") or config["alpaca"]["api_key"]
ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY") or config["alpaca"]["secret_key"]
ALPACA_BASE_URL = config["alpaca"].get("base_url", "https://paper-api.alpaca.markets")
NEWS_API_KEY = os.getenv("NEWS_API_KEY") or config["news"].get("api_key", "")

trading_client = TradingClient(ALPACA_API_KEY, ALPACA_SECRET_KEY, paper=True)

# ========== PDT MANAGER ==========

class PDTManager:
    def __init__(self, api_client, pdt_threshold=25000):
        self.api = api_client
        self.pdt_threshold = pdt_threshold

    def is_pdt_restricted(self):
        account = self.api.get_account()
        return float(account.equity) < self.pdt_threshold

    def count_day_trades(self, days=5):
        utc = pytz.UTC
        now = datetime.datetime.now(utc)
        start_date = now - datetime.timedelta(days=days)
        orders = self.api.list_orders(
            status='filled',
            after=start_date.isoformat(),
            until=now.isoformat(),
            limit=500
        )
        symbol_day_orders = {}
        for order in orders:
            filled_at = getattr(order, 'filled_at', None) or getattr(order, 'created_at', None)
            if not filled_at:
                continue
            day = filled_at.astimezone(utc).strftime('%Y-%m-%d')
            key = (order.symbol, day)
            if key not in symbol_day_orders:
                symbol_day_orders[key] = {'buy': False, 'sell': False}
            if order.side == 'buy':
                symbol_day_orders[key]['buy'] = True
            elif order.side == 'sell':
                symbol_day_orders[key]['sell'] = True
        day_trades = sum(1 for trades in symbol_day_orders.values() if trades['buy'] and trades['sell'])
        return day_trades

    def can_day_trade(self):
        if not self.is_pdt_restricted():
            return True
        return self.count_day_trades() < 3

    def should_avoid_same_day_exit(self, symbol):
        if not self.is_pdt_restricted():
            return False
        utc = pytz.UTC
        today = datetime.datetime.now(utc).strftime('%Y-%m-%d')
        orders = self.api.list_orders(
            status='filled',
            after=today,
            until=today
        )
        for order in orders:
            if order.symbol == symbol and order.side == 'buy':
                return True
        return False

pdt_mgr = PDTManager(trading_client, config["account"]["pdt_threshold"])

# ========== NEWS SENTIMENT ==========

def get_news_headlines(symbol, max_articles=5):
    if not config["news"]["enabled"] or not NEWS_API_KEY:
        return []
    url = f"https://newsapi.org/v2/everything?q={symbol}&apiKey={NEWS_API_KEY}"
    try:
        resp = requests.get(url)
        articles = resp.json().get('articles', [])
        return [a['title'] for a in articles[:max_articles]]
    except Exception as e:
        logging.warning(f"News fetch failed for {symbol}: {e}")
        return []

sentiment_model = pipeline("sentiment-analysis") if config["sentiment"]["enabled"] else None

def get_news_sentiment(symbols):
    news_sentiment = {}
    for symbol in symbols:
        headlines = get_news_headlines(symbol)
        if sentiment_model and headlines:
            sentiments = sentiment_model(headlines)
            avg_sentiment = sum(1 if s['label']=='POSITIVE' else -1 for s in sentiments) / len(sentiments)
            news_sentiment[symbol] = avg_sentiment
    return news_sentiment

# ========== DATA FETCHING ==========

def get_sp500_symbols():
    url = 'https://datahub.io/core/s-and-p-500-companies/r/constituents.csv'
    return pd.read_csv(url)['Symbol'].tolist()

def fetch_symbol_bars(symbol, limit=50):
    # You may want to use Alpaca's data API here for real data
    # Placeholder: simulate with random walk
    prices = np.cumsum(np.random.randn(limit)) + 100
    volumes = np.random.randint(1000, 2000, size=limit)
    return {"close": prices.tolist(), "volume": volumes.tolist()}

def get_bars(symbols):
    bars_data = {}
    for symbol in symbols:
        bars_data[symbol] = fetch_symbol_bars(symbol)
    return bars_data

# ========== STRATEGY ==========

def calculate_rsi(prices, window=14):
    prices = np.array(prices)
    delta = np.diff(prices)
    up = delta.clip(min=0)
    down = -delta.clip(max=0)
    avg_gain = np.mean(up[-window:]) if len(up) >= window else 0
    avg_loss = np.mean(down[-window:]) if len(down) >= window else 1
    rs = avg_gain / avg_loss if avg_loss != 0 else 1
    return 100 - (100 / (1 + rs))

def find_opportunities(bars_data, news_sentiment):
    opportunities = {}
    for symbol, bars in bars_data.items():
        price = bars['close'][-1]
        volume = bars['volume'][-1]
        sentiment = news_sentiment.get(symbol, 0)
        if price < config['stock_selection']['max_price'] and volume > config['stock_selection']['min_volume']:
            rsi = calculate_rsi(bars['close'])
            if rsi < 35 and sentiment > 0:
                opportunities[symbol] = "buy"
    return opportunities

def position_size(cash, price):
    risk = config['risk']['risk_per_trade']
    return int((cash * risk) // price)

def should_exit(symbol, bars, sentiment):
    price = bars['close'][-1]
    if sentiment < 0 or price < np.mean(bars['close'][-5:]):
        return True
    return False

# ========== ORDER MANAGEMENT ==========

def market_is_open():
    clock = trading_client.get_clock()
    return clock.is_open

def get_positions():
    # TODO: Replace with real Alpaca positions
    return {}

def get_account():
    account = trading_client.get_account()
    return {"cash": float(account.cash)}

def place_order(symbol, qty, side, price):
    try:
        # TODO: Replace with real Alpaca order logic
        logging.info(f"Placing {side} order for {qty} shares of {symbol} at {price}")
    except Exception as e:
        logging.error(f"Order failed: {e}")

# ========== MAIN TRADING LOOP ==========

if __name__ == "__main__":
    while True:
        try:
            if not market_is_open():
                logging.info("Market closed.")
                time.sleep(60)
                continue

            symbols = get_sp500_symbols()
            bars_data = get_bars(symbols)
            news_sentiment = get_news_sentiment(symbols) if config["news"]["enabled"] else {}

            opportunities = find_opportunities(bars_data, news_sentiment)
            positions = get_positions()
            account = get_account()

            # Buy phase
            for symbol, signal in opportunities.items():
                if len(positions) >= config['risk']['max_positions']:
                    break
                if pdt_mgr.should_avoid_same_day_exit(symbol):
                    continue
                qty = position_size(account['cash'], bars_data[symbol]['close'][-1])
                if qty > 0:
                    place_order(symbol, qty, 'buy', bars_data[symbol]['close'][-1])

            # Sell phase
            for symbol, pos in positions.items():
                if should_exit(symbol, bars_data[symbol], news_sentiment.get(symbol, {})):
                    place_order(symbol, pos['qty'], 'sell', bars_data[symbol]['close'][-1])

            time.sleep(60)
        except Exception as e:
            logging.error(f"Cycle error: {e}")
            time.sleep(300)
