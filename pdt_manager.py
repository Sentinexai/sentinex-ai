import datetime
import pytz

class PDTManager:
    def __init__(self, api_client, pdt_threshold=25000):
        self.api = api_client
        self.pdt_threshold = pdt_threshold

    def is_pdt_restricted(self):
        account = self.api.get_account()
        return float(account.equity) < self.pdt_threshold

    def count_day_trades(self, days=5):
        utc = pytz.UTC
        now = datetime.datetime.now(utc)
        start_date = now - datetime.timedelta(days=days)
        orders = self.api.list_orders(
            status='filled',
            after=start_date.isoformat(),
            until=now.isoformat(),
            limit=500
        )
        symbol_day_orders = {}
        for order in orders:
            filled_at = order.filled_at if hasattr(order, 'filled_at') else order.created_at
            if not filled_at:
                continue
            day = filled_at.astimezone(utc).strftime('%Y-%m-%d')
            key = (order.symbol, day)
            if key not in symbol_day_orders:
                symbol_day_orders[key] = {'buy': False, 'sell': False}
            if order.side == 'buy':
                symbol_day_orders[key]['buy'] = True
            elif order.side == 'sell':
                symbol_day_orders[key]['sell'] = True
        day_trades = sum(1 for trades in symbol_day_orders.values() if trades['buy'] and trades['sell'])
        return day_trades

    def can_day_trade(self):
        if not self.is_pdt_restricted():
            return True
        return self.count_day_trades() < 3

    def should_avoid_same_day_exit(self, symbol):
        if not self.is_pdt_restricted():
            return False

        utc = pytz.UTC
        today = datetime.datetime.now(utc).strftime('%Y-%m-%d')
        orders = self.api.list_orders(
            status='filled',
            after=today,
            until=today
        )
        for order in orders:
            if order.symbol == symbol and order.side == 'buy':
                return True
        return False
