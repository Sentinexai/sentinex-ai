import logging
from core.data import DataManager
from core.strategy import Strategy
from core.order import OrderManager
from core.pdt_manager import PDTManager

class Trader:
    def __init__(self, config):
        self.config = config
        self.data = DataManager(config)
        self.strategy = Strategy(config)
        self.order_mgr = OrderManager(config)
        self.pdt_mgr = PDTManager(self.order_mgr.api, config['account']['pdt_threshold'])

    def run_trading_cycle(self):
        if not self.order_mgr.market_is_open():
            logging.info("Market closed.")
            return

        symbols = self.data.get_symbols()
        bars_data = self.data.get_bars(symbols)
        news_sentiment = self.data.get_news_sentiment(symbols) if self.config['news']['enabled'] else {}

        opportunities = self.strategy.find_opportunities(bars_data, news_sentiment)
        positions = self.order_mgr.get_positions()
        account = self.order_mgr.get_account()

        # Buy phase
        for symbol, signal in opportunities.items():
            if len(positions) >= self.config['risk']['max_positions']:
                break
            if self.pdt_mgr.should_avoid_same_day_exit(symbol):
                continue
            qty = self.strategy.position_size(account['cash'], bars_data[symbol]['close'][-1])
            if qty > 0:
                self.order_mgr.place_order(symbol, qty, 'buy', bars_data[symbol]['close'][-1])

        # Sell phase
        for symbol, pos in positions.items():
            if self.strategy.should_exit(symbol, bars_data[symbol], news_sentiment.get(symbol, {})):
                self.order_mgr.place_order(symbol, pos['qty'], 'sell', bars_data[symbol]['close'][-1])
