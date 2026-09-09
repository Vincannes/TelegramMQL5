#!/usr/bin/env python
# #support	:Trolard Vincent
# copyright	:Vincannes

def to_float(value):
    return float(value.replace(",", "."))


class OrderModel(object):

    ORDER_TYPE_NONE = 0
    ORDER_TYPE_BUY = 1
    ORDER_TYPE_SELL = 2

    ACTION_OPEN = "open"
    ACTION_BREAKEVEN = "breakeven"
    ACTION_CLOSE = "close"

    def __init__(self, order_type, pair, price, stop, profits, action=ACTION_OPEN):
        self._order_type = order_type
        self._pair = pair
        self._price = price
        self._stop = stop
        self._profits = profits
        self._action = action

    @property
    def action(self):
        return self._action

    @property
    def is_breakeven(self):
        return self._action == self.ACTION_BREAKEVEN

    @property
    def is_close(self):
        return self._action == self.ACTION_CLOSE

    @property
    def pair(self):
        if not self._pair:
            return ""
        return self._pair.upper()

    @property
    def order_type(self):
        return self._order_type

    @property
    def price(self):
        return to_float(self._price)

    @property
    def stop(self):
        return to_float(self._stop)

    @property
    def profits(self):
        # TP1 is the closest target to the entry price: ascending for a Buy,
        # descending for a Sell.
        values = [to_float(i) for i in self._profits]
        return sorted(values, reverse=self._order_type == self.ORDER_TYPE_SELL)

    def to_dict(self):
        if self.is_close:
            # No pair -> MQL5 closes every position/order opened by this EA.
            return {
                "action": self.ACTION_CLOSE,
                "symbol": self.pair,
            }
        if self.is_breakeven:
            return {
                "action": self.ACTION_BREAKEVEN,
                "symbol": self.pair,
            }
        return {
            "action": self.ACTION_OPEN,
            "symbol": self.pair,
            "type": self.order_type,
            "entry": self.price,
            "sl": self.stop,
            "tp": self.profits,
        }

    def __str__(self):
        if self.is_close:
            target = self.pair if self.pair else "ALL open positions"
            return "Close : '{}' (close trades)".format(target)

        if self.is_breakeven:
            target = self.pair if self.pair else "ALL open positions"
            return "BreakEven : '{}' (move SL to entry)".format(target)

        dir_str = "None"
        if self.order_type == self.ORDER_TYPE_BUY:
            dir_str = "Buy"
        if self.order_type == self.ORDER_TYPE_SELL:
            dir_str = "Sell"

        profits_str = ""
        if self.profits:
            for i, prof in enumerate(self.profits):
                i += 1
                profits_str += "TP {} : {}\n".format(str(i), prof)

        return "{} : '{}' at {}\nSL: {}\n{}".format(
            dir_str,
            self.pair,
            self.price,
            self.stop,
            profits_str,
        )
