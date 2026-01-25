#!/usr/bin/env python
# #support	:Trolard Vincent
# copyright	:Vincannes

class PairErrors(Exception):
    def __init__(self, pairs):
        super().__init__(
            "Pair not found. Allowed pair: {}".format(" ".join(pairs))
        )

class DirectionError(Exception):
    def __init__(self, msg):
        super().__init__(
            "Order type cannot found in message : '{}'".format(msg)
        )


class PriceError(Exception):
    def __init__(self, msg):
        super().__init__(
            "Entry Price not found in message : '{}'".format(msg)
        )

class FailedParseMessage(Exception):
    def __init__(self, msg, error):
        super().__init__(
            "Falied to parse : '{}'\n{}".format(msg, error)
        )
