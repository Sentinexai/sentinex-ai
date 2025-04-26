import alpaca_trade_api as tradeapi
import pandas as pd
import time

# Set your API keys and endpoint
API_KEY = 'PKHSYF5XH92B8VFNAJFD'
SECRET_KEY = '89KOB1vOSn2c3HeGorQe6zkKa0F4tFgBjbIAisCf'
BASE_URL = 'https://paper-api.alpaca.markets'  # for paper trading

# Initialize Alpaca API client
api = tradeapi.REST(API_KEY, SECRET_KEY, BASE_URL, api_version='v2')

# List of supported crypto tickers from Alpaca (use your own)
CRYPTO_TICKERS = ['BTCUSD', 'ETHUSD', 'SOLUSD', 'DOGEUSD', 'SHIBUSD']

# Function to fetch market data for a given crypto ticker
def get_crypto_data(ticker):
    try:
        bars = api.get_barset(ticker, 'minute', limit=1000)  # Get 1000 minutes of historical data
        df = bars[ticker]
        df['time'] = df.index
        df = df[['time', 'open', 'high', 'low', 'close', 'volume']]
        return df
    except Exception as e:
        print(f"Error fetching data for {ticker}: {e}")
        return None

# Main logic for scanning crypto data
def scan_crypto():
    for ticker in CRYPTO_TICKERS:
        print(f"Scanning for {ticker}...")
        data = get_crypto_data(ticker)
        if data is not None:
            print(f"Latest data for {ticker}:")
            print(data.tail())  # Display the last few rows of data
        else:
            print(f"No data available for {ticker}")

# Run the scan
if __name__ == "__main__":
    scan_crypto()
