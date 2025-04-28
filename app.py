import streamlit as st
import pandas as pd
import numpy as np
import datetime
from alpaca_trade_api.rest import REST, TimeFrame
import time
import requests

API_KEY = "PKHSYF5XH92B8VFNAJFD"
SECRET_KEY = "89KOB1vOSn2c3HeGorQe6zkKa0F4tFgBjbIAisCf"
BASE_URL = "https://paper-api.alpaca.markets"
api = REST(API_KEY, SECRET_KEY, BASE_URL)

# Download S&P 500 tickers live
def get_sp500():
    url = 'https://datahub.io/core/s-and-p-500-companies/r/constituents.csv'
    df = pd.read_csv(url)
    return df['Symbol'].tolist()

TICKERS = get_sp500()

def get_rsi(prices, window=14):
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

trade_log = []
win = 0
loss = 0
MAX_PORTFOLIO_SIZE = 5000  # $5,000 total portfolio size
RISK_PER_TRADE = 0.05  # Risk 5% per trade

while True:
    try:
        # Get current account balance and positions
        account = api.get_account()
        cash = float(account.cash)
        positions = api.list_positions()
        
        # Calculate available buying power
        used_capital = sum(float(pos.market_value) for pos in positions)
        available_cash = min(MAX_PORTFOLIO_SIZE - used_capital, cash)
        
        for symbol in TICKERS:
            try:
                bars = api.get_bars(symbol, TimeFrame.Minute, limit=20).df
                if bars.empty or bars['volume'].iloc[-1] < 5000 or bars['close'].iloc[-1] < 5:
                    continue
                
                current_price = bars['close'].iloc[-1]
                bars['rsi'] = get_rsi(bars['close'])
                latest_rsi = bars['rsi'].iloc[-1]
                
                # Check existing position
                position_qty = 0
                for pos in positions:
                    if pos.symbol == symbol:
                        position_qty = float(pos.qty)
                        break
                
                # Dynamic position sizing
                if latest_rsi < 45 and position_qty == 0 and available_cash > 0:
                    max_risk_amount = available_cash * RISK_PER_TRADE
                    qty = int(max_risk_amount // current_price)
                    
                    if qty > 0:
                        api.submit_order(
                            symbol=symbol,
                            qty=qty,
                            side='buy',
                            type='market',
                            time_in_force='gtc'
                        )
                        trade_log.append((symbol, "BUY", current_price, datetime.datetime.now(), qty))
                        print(f"BUY {qty} {symbol} @ {current_price:.2f} | RSI: {latest_rsi:.2f}")
                        available_cash -= qty * current_price
                
                elif latest_rsi > 55 and position_qty > 0:
                    api.submit_order(
                        symbol=symbol,
                        qty=position_qty,
                        side='sell',
                        type='market',
                        time_in_force='gtc'
                    )
                    sell_price = bars['close'].iloc[-1]
                    
                    # Calculate P&L
                    for log in reversed(trade_log):
                        if log[0] == symbol and log[1] == "BUY":
                            buy_price = log[2]
                            shares_bought = log[4]
                            break
                    
                    pnl = (sell_price - buy_price) * shares_bought
                    if pnl > 0:
                        win += 1
                    else:
                        loss += 1
                    
                    trade_log.append((symbol, "SELL", sell_price, datetime.datetime.now(), pnl))
                    print(f"SELL {position_qty} {symbol} @ {sell_price:.2f} | P&L: {pnl:.2f}")
                    print(f"Wins: {win}, Losses: {loss}, W/L Ratio: {(win/(win+loss)):.2f}")
            
            except Exception as e:
                print(f"Error on {symbol}: {e}")
        
        print(f"Total Trades: {len(trade_log)}, Wins: {win}, Losses: {loss}, W/L Ratio: {(win/(win+loss)) if (win+loss)>0 else 0:.2f}")
        time.sleep(60)
    
    except Exception as e:
        print(f"Main loop error: {e}")
        time.sleep(60)

