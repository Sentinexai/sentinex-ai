import pandas as pd
import numpy as np
import datetime
from alpaca_trade_api.rest import REST, TimeFrame
import time
import pytz
from scipy.stats import zscore
from functools import wraps

# ======================
# CONFIGURATION
# ======================
API_KEY = "PKHSYF5XF92B8VFNAJFD"
SECRET_KEY = "89KOB1vOSn2c3HeGorQe6zkKa0F4tFgBjbIAisCf"
BASE_URL = "https://paper-api.alpaca.markets"

# Strategy Parameters
INITIAL_CAPITAL = 5000
RISK_PER_TRADE = 0.02
STOP_LOSS_PCT = 0.015
TAKE_PROFIT_PCT = 0.03
RSI_OVERBOUGHT = 65
RSI_OVERSOLD = 35

# ======================
# ALPACA INIT
# ======================
api = REST(API_KEY, SECRET_KEY, BASE_URL)

# ======================
# CORE FUNCTIONS
# ======================
def get_sp500_symbols():
    url = 'https://datahub.io/core/s-and-p-500-companies/r/constituents.csv'
    return pd.read_csv(url)['Symbol'].tolist()

@retry(max_retries=3, delay=2)
def get_bars(symbol, timeframe=TimeFrame.Minute, limit=50):
    return api.get_bars(symbol, timeframe, limit=limit, adjustments='split').df

def calculate_volatility(bars):
    return (bars['high'] - bars['low']).mean() / bars['close'].mean()

def sort_symbols_by_opportunity(symbols):
    """Priority sorting based on liquidity, volatility, and RSI"""
    opportunities = []
    
    for symbol in symbols:
        try:
            bars = get_bars(symbol)
            if len(bars) < 20: continue
            
            # Opportunity score components
            volume_score = bars['volume'].iloc[-1] / bars['volume'].mean()
            rsi = get_rsi(bars['close'])
            rsi_score = (RSI_OVERSOLD - rsi.iloc[-1]) / (RSI_OVERSOLD - 30)  # Normalized
            volatility_score = calculate_volatility(bars)
            
            # Composite score (higher = better)
            score = (rsi_score * 0.4) + (volume_score * 0.3) + (volatility_score * 0.3)
            opportunities.append( (symbol, score) )
            
        except Exception as e:
            continue
    
    # Sort by best opportunities first
    return [x[0] for x in sorted(opportunities, key=lambda x: x[1], reverse=True)][:30]

# ======================
# ENHANCED SELLING SYSTEM
# ======================
def get_sell_signal(bars, entry_price):
    """Multi-indicator sell decision matrix"""
    # Technical indicators
    rsi = get_rsi(bars['close'])
    macd_line = bars['close'].ewm(span=12).mean() - bars['close'].ewm(span=26).mean()
    macd_signal = macd_line.ewm(span=9).mean()
    upper_band = bars['close'].rolling(20).mean() + 2*bars['close'].rolling(20).std()
    
    # Mean reversion
    returns = bars['close'].pct_change(20)
    z = zscore(returns.dropna())[-1]
    
    # Sell conditions
    conditions = {
        'rsi_overbought': rsi.iloc[-1] > RSI_OVERBOUGHT,
        'bollinger_break': bars['close'].iloc[-1] > upper_band.iloc[-1],
        'macd_crossover': macd_line.iloc[-1] < macd_signal.iloc[-1],
        'zscore_high': z > 2.0,
        'volume_spike': bars['volume'].iloc[-1] > 1.5*bars['volume'].rolling(20).mean().iloc[-1]
    }
    
    # Weighted decision
    score = sum([
        conditions['rsi_overbought'] * 0.3,
        conditions['bollinger_break'] * 0.25,
        conditions['macd_crossover'] * 0.2,
        conditions['zscore_high'] * 0.15,
        conditions['volume_spike'] * 0.1
    ])
    
    return score >= 0.6  # Trigger if weighted score > 60%

def dynamic_position_sizing(available_cash, current_price, volatility):
    """Volatility-adjusted position sizing"""
    max_risk = available_cash * RISK_PER_TRADE
    volatility_factor = 1 + (volatility * 2)  # Scale down in high volatility
    return int(max_risk / (current_price * volatility_factor))

# ======================
# EXECUTION ENGINE
# ======================
def execute_sell(symbol, qty):
    try:
        # First attempt market sell
        api.submit_order(
            symbol=symbol,
            qty=qty,
            side='sell',
            type='market',
            time_in_force='gtc'
        )
        return True
    except Exception as e:
        print(f"Market sell failed: {e}. Trying limit sell...")
        try:
            last_price = get_bars(symbol, limit=1)['close'].iloc[-1]
            api.submit_order(
                symbol=symbol,
                qty=qty,
                side='sell',
                type='limit',
                limit_price=last_price * 0.995,
                time_in_force='day'
            )
            return True
        except Exception as e2:
            print(f"Limit sell also failed: {e2}")
            return False

# ======================
# MAIN TRADING LOOP
# ======================
def trading_cycle():
    symbols = sort_symbols_by_opportunity(get_sp500_symbols())
    positions = {pos.symbol: float(pos.qty) for pos in api.list_positions()}
    account = api.get_account()
    
    # Buy Phase
    for symbol in symbols:
        if len(positions) >= 10:  # Max 10 positions
            break
            
        bars = get_bars(symbol)
        if len(bars) < 20: continue
        
        current_price = bars['close'].iloc[-1]
        volatility = calculate_volatility(bars)
        
        if get_rsi(bars['close']).iloc[-1] < RSI_OVERSOLD:
            qty = dynamic_position_sizing(float(account.cash), current_price, volatility)
            if qty > 0:
                api.submit_order(
                    symbol=symbol,
                    qty=qty,
                    side='buy',
                    type='market',
                    time_in_force='gtc',
                    order_class='bracket',
                    stop_loss={'stop_price': current_price * (1 - STOP_LOSS_PCT)},
                    take_profit={'limit_price': current_price * (1 + TAKE_PROFIT_PCT)}
                )
                print(f"Bought {qty} {symbol} @ {current_price}")
    
    # Sell Phase
    for symbol, qty in positions.items():
        bars = get_bars(symbol)
        if len(bars) < 20: continue
        
        if get_sell_signal(bars, entry_price=get_average_entry(symbol)):
            if execute_sell(symbol, qty):
                print(f"Sold {qty} {symbol}")
                # Optional: Sell covered call
                try:
                    sell_covered_call(symbol, qty)
                except Exception as e:
                    print(f"Covered call failed: {e}")

# ======================
# UTILITIES
# ======================
def get_average_entry(symbol):
    positions = api.list_positions()
    pos = next((p for p in positions if p.symbol == symbol), None)
    return float(pos.avg_entry_price) if pos else None

def sell_covered_call(symbol, qty):
    """Options income strategy"""
    chains = api.get_options_chain(symbol)
    expiry = sorted(chains.expirations)[0]  # Nearest expiry
    strike = get_bars(symbol, TimeFrame.Day, 1)['close'].iloc[-1] * 1.05  # 5% OTM
    
    api.submit_order(
        symbol=f"{symbol}{expiry}C{strike}",
        qty=qty,
        side='sell',
        type='limit',
        limit_price=api.get_latest_trade(f"{symbol}{expiry}C{strike}").price,
        time_in_force='day'
    )

# ======================
# RISK MANAGEMENT
# ======================
def risk_management():
    # Implement daily VaR calculation
    portfolio = api.list_positions()
    if not portfolio: return
    
    values = [float(pos.market_value) for pos in portfolio]
    returns = np.random.normal(0, 0.02, 1000)  # Simulated returns
    var_95 = np.percentile(returns, 5)
    
    if var_95 < -0.1:  # 10% loss threshold
        print("Risk threshold breached! Liquidating 50%")
        for pos in portfolio[:len(portfolio)//2]:
            execute_sell(pos.symbol, pos.qty)

# ======================
# MAIN LOOP
# ======================
while True:
    try:
        if datetime.datetime.now().time() < datetime.time(9,30):
            risk_management()
            time.sleep(300)  # Wait for market open
            continue
            
        trading_cycle()
        time.sleep(60)  # Run every minute during market hours
        
    except Exception as e:
        print(f"Critical error: {e}")
        time.sleep(300)

