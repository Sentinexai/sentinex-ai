import alpaca_trade_api as tradeapi

API_KEY = "PKT8EXDCQYZ3G5ZAUQ35"
SECRET_KEY = "2mhc4bkAp1sZTkWApcNMhxMPci9rXPuTeG3ZLGdO"
BASE_URL = "https://paper-api.alpaca.markets"

api = tradeapi.REST(API_KEY, SECRET_KEY, BASE_URL, api_version='v2')

def get_account_info():
    account = api.get_account()
    return {
        "buying_power": account.buying_power,
        "cash": account.cash,
        "portfolio_value": account.portfolio_value,
        "status": account.status
    }

def place_test_trade(symbol="AAPL", qty=1, side="buy"):
    try:
        order = api.submit_order(
            symbol=symbol,
            qty=qty,
            side=side,
            type='market',
            time_in_force='gtc'
        )
        return f"Trade executed: {side.upper()} {qty} {symbol}"
    except Exception as e:
        return f"Trade failed: {e}"

