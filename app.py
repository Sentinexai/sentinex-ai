import pandas as pd
import numpy as np
import datetime
from alpaca_trade_api.rest import REST, TimeFrame
import time

# === CONFIGURATION ===
API_KEY = "PKHSYF5XH92B8VFNAJFD"
SECRET_KEY = "89KOB1vOSn2c3HeGorQe6zkKa0F4tFgBjbIAisCf"
BASE_URL = "https://paper-api.alpaca.markets"
MAX_POSITIONS = 10
RISK_PER_TRADE = 0.02
INITIAL_CAPITAL = 1000
TRAILING_STOP_PCT = 0.9
LOW_PRICE_MAX = 20

api = REST(API_KEY, SECRET_KEY, BASE_URL)

# === POSITION TRACKER ===
class PositionTracker:
    def __init__(self):
        self.positions = {}

    def add_position(self, symbol, buy_price, qty):
        self.positions[symbol] = {
            'buy_price': buy_price,
            'highest_price': buy_price,
            'qty': qty
        }

    def update_prices(self, current_prices):
        for symbol, data in self.positions.items():
            current_price = current_prices.get(symbol)
            if current_price and current_price > data['highest_price']:
                self.positions[symbol]['highest_price'] = current_price

    def check_trailing_stops(self, current_prices):
        sell_signals = []
        for symbol, data in self.positions.copy().items():
            current_price = current_prices.get(symbol)
            if not current_price:
                continue
            trailing_stop_price = data['highest_price'] * TRAILING_STOP_PCT
            if current_price <= trailing_stop_price:
                sell_signals.append({
                    'symbol': symbol,
                    'qty': data['qty'],
                    'reason': f"Trailing stop @ {trailing_stop_price:.2f}"
                })
                del self.positions[symbol]
        return sell_signals

tracker = PositionTracker()

# === TICKER LIST ===
def get_low_price_tickers():
    url = 'https://datahub.io/core/s-and-p-500-companies/r/constituents.csv'
    sp500 = pd.read_csv(url)['Symbol'].tolist()
    low_price_tickers = []
    for symbol in sp500:
        try:
            bars = api.get_bars(symbol, TimeFrame.Day, limit=1).df
            if not bars.empty and bars['close'].iloc[-1] <= LOW_PRICE_MAX:
                low_price_tickers.append(symbol)
        except:
            continue
    return low_price_tickers

TICKERS = get_low_price_tickers()

# === TRADING LOGIC ===
def get_rsi(prices, window=14):
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calculate_position_size(equity, price):
    risk_amount = equity * RISK_PER_TRADE
    return max(1, int(risk_amount // price))

trade_log = []
portfolio_value = [INITIAL_CAPITAL]

while True:
    try:
        equity = float(api.get_account().equity)
        positions = {pos.symbol: float(pos.qty) for pos in api.list_positions()}
        current_prices = {pos.symbol: float(pos.current_price) for pos in api.list_positions()}

        # Process trailing stops
        tracker.update_prices(current_prices)
        sell_signals = tracker.check_trailing_stops(current_prices)
        for signal in sell_signals:
            api.submit_order(
                symbol=signal['symbol'],
                qty=signal['qty'],
                side='sell',
                type='market',
                time_in_force='gtc'
            )
            print(f"SELL {signal['qty']} {signal['symbol']} - {signal['reason']}")

        # Find new buy opportunities
        for symbol in TICKERS:
            if len(positions) + len(tracker.positions) >= MAX_POSITIONS:
                break
            if symbol in positions or symbol in tracker.positions:
                continue
            
            try:
                bars = api.get_bars(symbol, TimeFrame.Minute, limit=20).df
                if bars.empty or bars['volume'].iloc[-1] < 5000:
                    continue
                
                bars['rsi'] = get_rsi(bars['close'])
                latest_close = bars['close'].iloc[-1]
                latest_rsi = bars['rsi'].iloc[-1]
                
                if latest_rsi < 30:
                    qty = calculate_position_size(equity, latest_close)
                    if qty > 0 and equity > latest_close * qty:
                        api.submit_order(
                            symbol=symbol,
                            qty=qty,
                            side='buy',
                            type='market',
                            time_in_force='gtc'
                        )
                        tracker.add_position(symbol, latest_close, qty)
                        print(f"BUY {qty} {symbol} @ {latest_close:.2f} | RSI: {latest_rsi:.2f}")
            except Exception as e:
                print(f"Error on {symbol}: {e}")

        # Update portfolio tracking
        total_value = equity + sum(float(pos.market_value) for pos in api.list_positions())
        portfolio_value.append(total_value)
        print(f"\nPortfolio: ${total_value:.2f} | Positions: {len(positions) + len(tracker.positions)}/{MAX_POSITIONS}")
        print("="*50)
        time.sleep(30)

    except Exception as e:
        print(f"Main error: {e}")
        time.sleep(60)
