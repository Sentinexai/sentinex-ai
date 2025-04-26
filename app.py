import os
import requests
import pandas as pd
import time

# Configuration for Alpaca API (replace with your actual keys)
API_KEY = 'PKHSYF5XH92B8VFNAJFD'
SECRET_KEY = '89KOB1vOSn2c3HeGorQe6zkKa0F4tFgBjbIAisCf'
BASE_URL = 'https://paper-api.alpaca.markets'

# Function to get historical price data
def fetch_historical_data(symbol):
    headers = {
        'PKHSYF5XH92B8VFNAJFD': API_KEY,
        '89KOB1vOSn2c3HeGorQe6zkKa0F4tFgBjbIAisCf': SECRET_KEY,
    }
    response = requests.get(f"{BASE_URL}/bars/minute?symbol={symbol}&limit=100", headers=headers)
    
    if response.status_code == 200:
        data = pd.DataFrame(response.json())
        return data
    else:
        print(f"Error fetching historical data: {response.json()}")
        return None

# Function to calculate trading indicators (e.g., RSI)
def compute_rsi(prices, period=14):
    delta = prices.diff(1)
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    
    rs = gain / loss
    return 100 - (100 / (1 + rs))

# Function to execute a trade
def execute_trade(symbol, qty, side):
    url = f"{BASE_URL}/orders"
    headers = {
        'APCA_API_KEY_ID': API_KEY,
        'APCA_API_SECRET_KEY': SECRET_KEY,
        'Content-Type': 'application/json'
    }
    order_data = {
        "symbol": symbol,
        "qty": qty,
        "side": side,
        "type": "market",
        "time_in_force": "gtc"
    }
    response = requests.post(url, json=order_data, headers=headers)
    
    if response.status_code == 200:
        print(f"Order executed: {response.json()}")
    else:
        print(f"Error executing order: {response.json()}")

# Trading function
def trading_logic():
    symbol = 'BTC/USD'  # Example cryptocurrency symbol
    data = fetch_historical_data(symbol)

    if data is not None:
        # Calculate indicators
        data['rsi'] = compute_rsi(data['close'])

        # Get last RSI value
        last_rsi = data['rsi'].iloc[-1]
        print(f"Last RSI for {symbol}: {last_rsi}")

        # Implement trading strategy based on RSI
        if last_rsi < 30:  # Buy threshold
            print(f"Buying {symbol}")
            execute_trade(symbol, qty=0.01, side='buy')  # Example quantity
        elif last_rsi > 70:  # Sell threshold
            print(f"Selling {symbol}")
            execute_trade(symbol, qty=0.01, side='sell')  # Example quantity

# Main execution loop
def main():
    while True:
        trading_logic()
        time.sleep(60)  # Run every minute; adjust as needed

if __name__ == "__main__":
    main()
