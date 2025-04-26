Sure! Below is the complete `app.py` code for your Streamlit application, incorporating all the necessary changes to handle the "Not Found" errors when fetching historical data for cryptocurrency tickers. This code includes improvements to filter out non-tradable assets and to make sure you're only dealing with assets that have available historical data.

### Complete `app.py` Code

```python
import streamlit as st
import pandas as pd
import numpy as np
from alpaca_trade_api.rest import REST, TimeFrame

# ========== CONFIGURATION ==========
API_KEY = 'PKHSYF5XH92B8VFNAJFD'  
SECRET_KEY = '89KOB1vOSn2c3HeGorQe6zkKa0F4tFgBjbIAisCf' 
BASE_URL = 'https://paper-api.alpaca.markets'
LOOKBACK = 21  # Number of minutes for RSI calculation
RSI_BUY = 30   # RSI buy threshold
RSI_SELL = 70  # RSI sell threshold
CRYPTO_QTY = 0.002  # Quantity for trading

# Initialize Alpaca API
api = REST(API_KEY, SECRET_KEY, BASE_URL)

# Set up the Streamlit layout
st.set_page_config(page_title="Sentinex Sniper", layout="wide")
st.title("🤖 Sentinex Sniper Bot — Only A+ Trades! (Crypto Mode)")

def calculate_rsi(prices, window=14):
    """Calculate the RSI (Relative Strength Index)"""
    prices = pd.Series(prices)
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def fetch_supported_crypto_tickers():
    """Fetch supported crypto tickers."""
    try:
        assets = api.list_assets()
        
        # Filter for tradable crypto assets
        crypto_tickers = [asset.symbol for asset in assets if asset.tradable and asset.exchange == 'CRYPTO'] 
        
        if not crypto_tickers:
            st.warning("No available cryptocurrency tickers found.")
        else:
            st.success(f"Supported available cryptocurrency tickers: {crypto_tickers}")  # Display fetched tickers
        
        return crypto_tickers
    except Exception as e:
        st.error(f"Error fetching assets: {e}")
        return []

def get_data(symbol):
    """Fetch historical price data for the given symbol."""
    try:
        # Fetch historical bars for the specified symbol using TimeFrame
        bars = api.get_bars(symbol, TimeFrame.Minute, limit=LOOKBACK).df
        
        if bars.empty:
            st.warning(f"No historical data available for {symbol}.")
        
        return bars
    except Exception as e:
        st.error(f"Error fetching data for {symbol}: {e}")  # Display error
        return None

def confluence_signal(bars):
    """Generate buy/sell signals based on RSI."""
    if bars is None or len(bars) < LOOKBACK:
        return None

    bars['rsi'] = calculate_rsi(bars['close'])
    last = bars.iloc[-1]

    if last['rsi'] < RSI_BUY:
        return "BUY"
    elif last['rsi'] > RSI_SELL:
        return "SELL"
    else:
        return "HOLD"

# ========== MAIN LOGIC ==========
st.header("🔎 Scanning for A+ setups in Crypto...")

# Fetch crypto tickers
crypto_tickers = fetch_supported_crypto_tickers()

# Iterate over the supported crypto tickers
for symbol in crypto_tickers:
    bars = get_data(symbol)
    if bars is not None:  # Only proceed if data was fetched successfully
        signal = confluence_signal(bars)
        st.write(f"{symbol}: {signal or 'No trade'}")
    else:
        st.write(f"{symbol}: No data available.")
    
    # Uncomment the following lines for live trading (after testing)
    # if signal == "BUY":
    #     api.submit_order(symbol=symbol, qty=CRYPTO_QTY, side='buy', type='market', time_in_force='gtc')
    # elif signal == "SELL":
    #     api.submit_order(symbol=symbol, qty=CRYPTO_QTY, side='sell', type='market', time_in_force='gtc')

st.info("Simulating trades with small account size. Adjust quantities and risk settings accordingly for real trading. To go fully auto, uncomment the 'submit_order' lines.")
```

### Key Changes
1. **Asset Filtering**: The `fetch_supported_crypto_tickers` function ensures it only fetches tradeable cryptocurrencies directly from the cryptocurrency exchange.
2. **Data Availability Check**: In the ticker iteration loop, we check if historical data exists before trying to generate trading signals, preventing unnecessary errors.
3. **Warning Messages**: Appropriate warning and success messages notify users when no tradable assets or available historical data is present.

### Next Steps
- **Run the App**: Deploy this updated code and observe how it operates with the filtered crypto tickers.
- **Review Permissions**: Ensure that your Alpaca account has cryptocurrency trading permissions active and check the available assets on your account.
- **Testing Live Trading**: Once you confirm that the app works as expected, you can uncomment the trading logic at the end to enable live trading.

If you encounter more issues or have additional questions, please feel free to reach out for further guidance!
