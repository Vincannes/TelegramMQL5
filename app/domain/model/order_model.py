#!/usr/bin/env python
# #support	:Trolard Vincent
# copyright	:Vincannes

def to_float(value):
    return float(value.replace(",", "."))


class OrderModel(object):

    ORDER_TYPE_NONE = 0
    ORDER_TYPE_BUY = 1
    ORDER_TYPE_SELL = 2

    def __init__(self, order_type, pair, price, stop, profits):
        self._order_type = order_type
        self._pair = pair
        self._price = price
        self._stop = stop
        self._profits = profits

    @property
    def pair(self):
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
        return sorted([to_float(i) for i in self._profits])

    def to_dict(self):
        return {
            "symbol": self.pair,
            "type": self.order_type,
            "entry": self.price,
            "sl": self.stop,
            "tp": self.profits,
        }

    def __str__(self):
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
