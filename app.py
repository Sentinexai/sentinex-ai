import streamlit as st
import pandas as pd
import numpy as np
import datetime
from alpaca_trade_api.rest import REST, TimeFrame
import time
import pytz
from functools import wraps

# API Configuration
API_KEY = "PKHSYF5XF92B8VFNAJFD"
SECRET_KEY = "89KOB1vOSn2c3HeGorQe6zkKa0F4tFgBjbIAisCf"
BASE_URL = "https://paper-api.alpaca.markets"

api = REST(API_KEY, SECRET_KEY, BASE_URL)

# Strategy Parameters
RISK_PER_TRADE = 0.02
MAX_PORTFOLIO_SIZE = 5000
STOP_LOSS_PCT = 0.015
TAKE_PROFIT_PCT = 0.03
RSI_WINDOW = 14
EMA_WINDOW = 50
SYMBOL_LIMIT = 30  # Reduced from 50 to stay under rate limits
REQUEST_DELAY = 0.3  # 300ms between symbols

# Initialize variables
trade_log = []
performance_history = []

def retry(max_retries=3, delay=1):
    """Exponential backoff retry decorator"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    print(f"Retry {retries+1}/{max_retries}: {str(e)}")
                    time.sleep(delay * (2 ** retries))
                    retries += 1
            return None
        return wrapper
    return decorator

@retry(max_retries=3, delay=2)
def get_bars_safe(symbol):
    """Safe data fetching with rate limits"""
    return api.get_bars(
        symbol,
        TimeFrame.Minute,
        limit=50,
        adjustments='split'  # Critical for free data access
    ).df

def get_sp500():
    """Fetch S&P 500 symbols with caching"""
    url = 'https://datahub.io/core/s-and-p-500-companies/r/constituents.csv'
    return pd.read_csv(url)['Symbol'].tolist()

def filter_symbols():
    """Filter symbols by liquidity"""
    symbols = []
    for symbol in get_sp500()[:SYMBOL_LIMIT]:  # Limit symbols
        try:
            bars = get_bars_safe(symbol)
            if not bars.empty and bars['volume'].mean() > 500_000:
                symbols.append(symbol)
        except:
            continue
        time.sleep(REQUEST_DELAY)
    return symbols

TICKERS = filter_symbols()

def get_rsi(prices, window=14):
    """Robust RSI calculation"""
    delta = prices.diff().fillna(0)
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(window).mean()
    avg_loss = loss.rolling(window).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def manage_risk():
    """Dynamic risk adjustment"""
    global RISK_PER_TRADE
    if len(performance_history) > 10:
        win_rate = sum(performance_history[-10:])/10
        RISK_PER_TRADE = np.clip(
            RISK_PER_TRADE * (1.1 if win_rate > 0.6 else 0.9),
            0.01, 0.05
        )

def execute_trade(symbol, side, qty):
    """Safe order execution"""
    try:
        api.submit_order(
            symbol=symbol,
            qty=qty,
            side=side,
            type='market',
            time_in_force='gtc',
            order_class='bracket',
            stop_loss={'stop_price': round(qty * STOP_LOSS_PCT, 2)},
            take_profit={'limit_price': round(qty * TAKE_PROFIT_PCT, 2)}
        )
        return True
    except Exception as e:
        print(f"Order failed for {symbol}: {str(e)}")
        return False

while True:
    try:
        account = api.get_account()
        positions = api.list_positions()
        used_capital = sum(float(pos.market_value) for pos in positions)
        available_cash = min(MAX_PORTFOLIO_SIZE - used_capital, float(account.cash))
        
        manage_risk()
        
        for symbol in TICKERS:
            try:
                bars = get_bars_safe(symbol)
                if bars is None or len(bars) < 20:
                    continue
                
                current_price = bars['close'].iloc[-1]
                if current_price < 5 or bars['volume'].iloc[-1] < 10_000:
                    continue
                
                # Calculate indicators
                bars['rsi'] = get_rsi(bars['close'])
                bars['ema50'] = bars['close'].ewm(span=EMA_WINDOW).mean()
                latest_rsi = bars['rsi'].iloc[-1]
                
                # Position management
                position = next((p for p in positions if p.symbol == symbol), None)
                position_qty = float(position.qty) if position else 0
                
                # Entry logic
                if not position_qty and available_cash > 100:
                    if current_price > bars['ema50'].iloc[-1] and latest_rsi < 40:
                        volatility = (bars['high'].iloc[-1] - bars['low'].iloc[-1])/current_price
                        max_risk = available_cash * RISK_PER_TRADE
                        qty = int(max_risk / (current_price * (1 + volatility)))
                        
                        if qty > 0 and execute_trade(symbol, 'buy', qty):
                            trade_log.append({
                                'symbol': symbol,
                                'side': 'buy',
                                'price': current_price,
                                'time': datetime.datetime.now(pytz.UTC),
                                'qty': qty
                            })
                            available_cash -= qty * current_price
                
                # Exit logic
                elif position_qty > 0:
                    if latest_rsi > 60 or current_price < bars['ema50'].iloc[-1]:
                        if execute_trade(symbol, 'sell', position_qty):
                            entry = next((t for t in reversed(trade_log) 
                                       if t['symbol'] == symbol and t['side'] == 'buy'), None)
                            if entry:
                                pnl = (current_price - entry['price']) * position_qty
                                performance_history.append(1 if pnl > 0 else 0)
            
            except Exception as e:
                print(f"Symbol {symbol} error: {str(e)}")
            finally:
                time.sleep(REQUEST_DELAY)
        
        print(f"Cycle complete. Cash: ${available_cash:.2f}")
        time.sleep(60)
        
    except Exception as e:
        print(f"Main loop error: {str(e)}")
        time.sleep(60)
