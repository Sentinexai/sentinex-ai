import logging
from alpaca.trading.client import TradingClient

class OrderManager:
    def __init__(self, config):
        self.api = TradingClient(
            api_key=config['alpaca']['api_key'],
            secret_key=config['alpaca']['secret_key'],
            paper=True
        )

    def market_is_open(self):
        clock = self.api.get_clock()
        return clock.is_open

    def get_positions(self):
        # TODO: Return current positions as a dict
        # Example placeholder:
        return {}

    def get_account(self):
        account = self.api.get_account()
        return {"cash": float(account.cash)}

    def place_order(self, symbol, qty, side, price):
        try:
            # TODO: Place order logic here using Alpaca API
            logging.info(f"Placing {side} order for {qty} shares of {symbol} at {price}")
        except Exception as e:
            logging.error(f"Order failed: {e}")
