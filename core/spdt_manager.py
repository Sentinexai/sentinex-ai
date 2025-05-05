"""PDT rule compliance manager"""
import datetime

class PDTManager:
    def __init__(self, api_client, pdt_threshold=25000):
        self.api = api_client
        self.pdt_threshold = pdt_threshold
        
    def is_pdt_restricted(self):
        """Check if account is under PDT threshold."""
        account = self.api.get_account()
        return float(account.equity) < self.pdt_threshold
    
    def count_day_trades(self, days=5):
        """Count day trades in the last specified days."""
        end_date = datetime.datetime.now()
        start_date = end_date - datetime.timedelta(days=days)
        start_str = start_date.strftime('%Y-%m-%d')
        end_str = end_date.strftime('%Y-%m-%d')
        
        orders = self.api.list_orders(
            status='closed',
            after=start_str,
            until=end_str,
            limit=500
        )
        
        # Group by symbol and day to identify day trades
        day_trades = 0
        symbol_day_orders = {}
        
        for order in orders:
            key = (order.symbol, order.created_at.strftime('%Y-%m-%d'))
            if key not in symbol_day_orders:
                symbol_day_orders[key] = {'buy': False, 'sell': False}
            if order.side == 'buy':
                symbol_day_orders[key]['buy'] = True
            else:  # sell
                symbol_day_orders[key]['sell'] = True
        
        # Count day trades
        for trades in symbol_day_orders.values():
            if trades['buy'] and trades['sell']:
                day_trades += 1
                
        return day_trades
    
    def can_day_trade(self):
        """Check if day trading is allowed under PDT rules."""
        if not self.is_pdt_restricted():
            return True
        return self.count_day_trades() < 3
    
    def should_avoid_same_day_exit(self, symbol):
        """Check if we should avoid selling a symbol today (PDT rule)."""
        if not self.is_pdt_restricted():
            return False
            
        today = datetime.datetime.now().strftime('%Y-%m-%d')
        orders = self.api.list_orders(
            status='all',
            after=today,
            until=today
        )
        
        for order in orders:
            if order.symbol == symbol and order.side == 'buy':
                # Already bought this symbol today, avoid selling (day trade)
                return True
                
        return False
