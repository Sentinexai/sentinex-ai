import pandas as pd
import numpy as np
import datetime
from alpaca_trade_api.rest import REST, TimeFrame
import time
import pytz
from functools import wraps
from alpaca.trading.client import TradingClient

# ======================
# CONFIGURATION
# ======================
API_KEY = "PKHSYF5XF92B8VFNAJFD"
SECRET_KEY = "89KOB1vOSn2c3HeGorQe6zkKa0F4tFgBjbIAisCf"
BASE_URL = "https://paper-api.alpaca.markets"

# Strategy Parameters
INITIAL_CAPITAL = 10000
RISK_PER_TRADE = 0.02  # 2% of capital per trade
STOP_LOSS_PCT = 0.015  # 1.5%
TAKE_PROFIT_PCT = 0.03  # 3%
RSI_OVERBOUGHT = 65
RSI_OVERSOLD = 35
MAX_POSITIONS = 15  # Increased capacity for smaller positions

# ======================
# ALPACA INIT
# ======================
api = REST(API_KEY, SECRET_KEY, BASE_URL)
trading_client = TradingClient(API_KEY, SECRET_KEY)

# ======================
# CORE FUNCTIONS
# ======================
def retry(max_retries=3, delay=1):
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
def get_bars(symbol, timeframe=TimeFrame.Minute, limit=50):
    return api.get_bars(symbol, timeframe, limit=limit, adjustments='split').df

def get_sp500_symbols():
    url = 'https://datahub.io/core/s-and-p-500-companies/r/constituents.csv'
    return pd.read_csv(url)['Symbol'].tolist()

def calculate_volatility(bars):
    return (bars['high'] - bars['low']).mean() / bars['close'].mean()

def get_rsi(prices, window=14):
    delta = prices.diff().fillna(0)
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(window).mean()
    avg_loss = loss.rolling(window).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def sort_symbols_by_opportunity(symbols):
    """Priority sorting with strong bias for low-price stocks"""
    opportunities = []
    
    for symbol in symbols:
        try:
            bars = get_bars(symbol)
            if bars is None or len(bars) < 20:
                continue
            
            current_price = bars['close'].iloc[-1]
            
            # Enhanced price scoring (quadratic bias for lower prices)
            price_score = (100 / current_price) ** 2  # Quadratic scaling
            
            # Other factors
            volume_score = bars['volume'].iloc[-1] / bars['volume'].mean()
            rsi = get_rsi(bars['close'])
            rsi_score = max(0, (RSI_OVERSOLD - rsi.iloc[-1]) / RSI_OVERSOLD)
            volatility_score = calculate_volatility(bars)
            
            # Composite score (60% weight to price)
            score = (price_score * 0.6) + (rsi_score * 0.2) + (volume_score * 0.1) + (volatility_score * 0.1)
            opportunities.append((symbol, score, current_price))
            
        except Exception as e:
            continue
    
    # Sort by best opportunities first, filter prices < $50
    return sorted([x for x in opportunities if x[2] < 50], 
                 key=lambda x: x[1], reverse=True)[:MAX_POSITIONS]

def dynamic_position_sizing(available_cash, current_price):
    """Aggressive quantity allocation for low-priced stocks"""
    # Base position size
    max_risk_amount = available_cash * RISK_PER_TRADE
    
    # Price-based multiplier
    if current_price < 10:
        price_multiplier = 5.0
    elif current_price < 20:
        price_multiplier = 3.0
    elif current_price < 30:
        price_multiplier = 2.0
    else:
        price_multiplier = 1.0
    
    qty = int((max_risk_amount * price_multiplier) // current_price)
    return max(1, qty)

def execute_smart_order(symbol, qty, side):
    """Hybrid order execution with price checks"""
    try:
        last_price = get_bars(symbol, limit=1)['close'].iloc[-1]
        
        if side == 'buy':
            order = api.submit_order(
                symbol=symbol,
                qty=qty,
                side='buy',
                type='limit',
                limit_price=last_price * 1.01,  # 1% above current
                time_in_force='day',
                order_class='bracket',
                stop_loss={'stop_price': last_price * (1 - STOP_LOSS_PCT)},
                take_profit={'limit_price': last_price * (1 + TAKE_PROFIT_PCT)}
            )
        else:
            order = api.submit_order(
                symbol=symbol,
                qty=qty,
                side='sell',
                type='limit',
                limit_price=last_price * 0.99,  # 1% below current
                time_in_force='day'
            )
        return order
    except Exception as e:
        print(f"Smart order failed: {e}")
        return None

# ======================
# MAIN TRADING LOGIC
# ======================
def trading_cycle():
    # Market hours check
    clock = trading_client.get_clock()
    if not clock.is_open:
        print(f"Market closed. Next open: {clock.next_open}")
        return

    # Get prioritized symbols
    opportunities = sort_symbols_by_opportunity(get_sp500_symbols())
    positions = {pos.symbol: float(pos.qty) for pos in api.list_positions()}
    account = api.get_account()
    
    # Buy Phase
    for symbol, score, price in opportunities:
        if len(positions) >= MAX_POSITIONS:
            break
            
        bars = get_bars(symbol)
        if bars is None or len(bars) < 20:
            continue
        
        current_price = bars['close'].iloc[-1]
        
        # Entry conditions
        if (get_rsi(bars['close']).iloc[-1] < RSI_OVERSOLD and 
            current_price > bars['close'].rolling(20).mean().iloc[-1]):
            
            qty = dynamic_position_sizing(float(account.cash), current_price)
            if qty > 0 and current_price < 50:  # Hard price cap
                order = execute_smart_order(symbol, qty, 'buy')
                if order:
                    print(f"Bought {qty} {symbol} @ {current_price:.2f}")
                    time.sleep(1)  # Rate limit cushion

    # Sell Phase
    for symbol, qty in positions.items():
        bars = get_bars(symbol)
        if bars is None or len(bars) < 20:
            continue
        
        current_price = bars['close'].iloc[-1]
        exit_conditions = (
            current_price >= 1.03 * get_average_entry(symbol) or  # Take quick profits
            get_rsi(bars['close']).iloc[-1] > RSI_OVERBOUGHT or
            current_price < 0.97 * bars['close'].rolling(20).mean().iloc[-1]
        )
        
        if exit_conditions:
            execute_smart_order(symbol, qty, 'sell')
            print(f"Sold {qty} {symbol} @ {current_price:.2f}")

# ======================
# UTILITIES
# ======================
def get_average_entry(symbol):
    positions = api.list_positions()
    pos = next((p for p in positions if p.symbol == symbol), None)
    return float(pos.avg_entry_price) if pos else None

# ======================
# MAIN LOOP
# ======================
if __name__ == "__main__":
    while True:
        try:
            trading_cycle()
            time.sleep(60)  # Run every minute during market hours
        except Exception as e:
            print(f"Cycle error: {e}")
            time.sleep(300)
