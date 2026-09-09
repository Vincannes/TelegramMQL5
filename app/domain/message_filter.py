#!/usr/bin/env python
# #support	:Trolard Vincent
# copyright	:Vincannes

import re
import unicodedata

from app import constants
from app.domain.exceptions import PairErrors, PriceError, DirectionError
from app.domain.model.order_model import OrderModel

FLAGS = re.IGNORECASE


class MessageFilter(object):

    TEMPLATE_REGEX = constants.DEFAULT_FIELDS

    def __init__(self, text):
        self._text = self.normalize_text(text.lower())
        self._pairs = [s.strip() for s in self.TEMPLATE_REGEX.get(constants.SYMBOL_KEY_FIELD, "").split(",")]
        self._pairs_mapping = {}
        for m in self.TEMPLATE_REGEX.get(constants.CUST_SYMBOL_KEY_FIELD, "").split(","):
            if "=" in m:
                k, v = m.split("=")
                self._pairs_mapping[k.strip().lower()] = v.strip().lower()

    @property
    def text(self):
        return self._text

    def normalize_text(self, text: str) -> str:
        text = text.replace("\n", " ").replace("\r", " ")

        # 1. Unicode normalization (separating accents)
        text = unicodedata.normalize("NFD", text)

        # 2. Removal of accents
        text = "".join(
            c for c in text
            if unicodedata.category(c) != "Mn"
        )

        # 3. Convert to lowercase (optional but recommended)
        text = text.lower()

        # 4. Removal of unauthorized characters
        #    We keep letters, numbers, spaces, and .
        text = re.sub(r"[^a-z0-9\s\.,]", " ", text)

        # 5. Cleaning of multiple spaces
        text = re.sub(r"\s+", " ", text).strip()

        # 6. Decimal comma -> decimal point (4625,5 -> 4625.5). Only a comma
        #    glued between digits and followed by at most two digits counts as
        #    a decimal: "4,625" (three digits) is a thousands separator and
        #    falls through to the removal below, like every other comma.
        text = re.sub(r"(?<=\d),(?=\d{1,2}(?!\d))", ".", text)
        text = text.replace(",", "")
        return text

    def _get_order_type(self):
        buy_kws = [kw.strip() for kw in self.TEMPLATE_REGEX.get(constants.BUY_KEY_FIELD, "").split(",") if kw.strip()]
        sell_kws = [kw.strip() for kw in self.TEMPLATE_REGEX.get(constants.SELL_KEY_FIELD, "").split(",") if kw.strip()]

        if buy_kws:
            pattern = r"\b(" + "|".join(map(re.escape, buy_kws)) + r")\b"
            if re.search(pattern, self._text, FLAGS):
                return OrderModel.ORDER_TYPE_BUY

        if sell_kws:
            pattern = r"\b(" + "|".join(map(re.escape, sell_kws)) + r")\b"
            if re.search(pattern, self._text, FLAGS):
                return OrderModel.ORDER_TYPE_SELL

        return None

    def _get_pair(self):
        if not self._pairs:
            return None
        pattern = r"\b(" + "|".join(map(re.escape, self._pairs)) + r")\b"
        m = re.search(pattern, self._text, FLAGS)
        if not m:
            return None
        pair = m.group(0)
        return pair

    def _get_entry(self):
        keywords = [kw.strip() for kw in self.TEMPLATE_REGEX.get(constants.ENTRY_KEY_FIELD, "").split(",")]
        if not keywords:
            return None
        pattern = r"\b(" + "|".join(map(re.escape, keywords)) + r")\b\s*(?:[:\-]|at)?\s*([\d.,]+)"
        m = re.search(pattern, self._text, FLAGS)
        return m.group(2) if m else None

    def _get_stop(self):
        keywords = [kw.strip() for kw in self.TEMPLATE_REGEX.get(constants.SL_KEY_FIELD, "").split(",")]
        if not keywords:
            return None
        pattern = r"\b(" + "|".join(map(re.escape, keywords)) + r")\b\s*(?:[:\-]|at)?\s*([\d.,]+)"
        m = re.search(pattern, self._text, FLAGS)
        return m.group(2) if m else None

    def _is_breakeven(self):
        keywords = [kw.strip() for kw in self.TEMPLATE_REGEX.get(constants.BE_KEY_FIELD, "").split(",") if kw.strip()]
        if not keywords:
            return False
        pattern = r"\b(" + "|".join(map(re.escape, keywords)) + r")\b"
        return bool(re.search(pattern, self._text, FLAGS))

    def _is_close(self):
        keywords = [kw.strip() for kw in self.TEMPLATE_REGEX.get(constants.CLOSE_KEY_FIELD, "").split(",") if kw.strip()]
        if not keywords:
            return False
        pattern = r"\b(" + "|".join(map(re.escape, keywords)) + r")\b"
        return bool(re.search(pattern, self._text, FLAGS))

    def _get_profits(self):
        keywords = [kw.strip() for kw in self.TEMPLATE_REGEX.get(constants.TP_KEY_FIELD, "").split(",") if kw.strip()]
        if not keywords:
            return []
        # \d{0,2} lets an index glued to the keyword (tp1, tp2, tp3) match
        # without being captured as the price. The \b after keeps "tp 4220"
        # (space-separated price) intact instead of eating its digits.
        #
        # The price group grabs every number that follows the keyword, so a
        # single keyword like "tps 4060.0 4067.0" yields both targets. NUMBER
        # accepts a dot decimal (4060.0) or a comma decimal (4842,62) but stops
        # before a field-separator comma (the one in "4067.0 , date") because
        # that comma is not followed by a digit. Each number is then split out.
        number = r"\d[\d.]*(?:,\d+)?"
        pattern = (
            r"\b(" + "|".join(map(re.escape, keywords)) +
            r")\d{0,2}\b\s*(?:[:\-]|at)?\s*((?:" + number + r"[\s,]*)+)"
        )
        profits = []
        for m in re.finditer(pattern, self._text, FLAGS):
            profits += re.findall(number, m.group(2))
        return profits

    def parse_signal(self):
        # Close message: a close keyword is an explicit instruction, so it is
        # checked before the direction. "close the sell on gold" must close the
        # position, not be read as a new Sell order.
        if self._is_close():
            # Pair is optional. When absent, MQL5 closes every position/order
            # opened by this EA.
            pair = self._get_pair()
            if pair and pair in self._pairs_mapping.keys():
                pair = self._pairs_mapping.get(pair, pair)
            return OrderModel(
                order_type=None,
                pair=pair,
                price=None,
                stop=None,
                profits=[],
                action=OrderModel.ACTION_CLOSE,
            )

        order_type = self._get_order_type()

        # BreakEven message: BE keyword present and no buy/sell direction.
        # Only a pair is needed to target the open position(s) on MQL5.
        if order_type is None and self._is_breakeven():
            # Pair is optional for a BreakEven message. When absent, MQL5
            # applies it to every open position of this EA.
            pair = self._get_pair()
            if pair and pair in self._pairs_mapping.keys():
                pair = self._pairs_mapping.get(pair, pair)
            return OrderModel(
                order_type=None,
                pair=pair,
                price=None,
                stop=None,
                profits=[],
                action=OrderModel.ACTION_BREAKEVEN,
            )

        if order_type is None:
            raise DirectionError(self._text)

        pair = self._get_pair()
        if not pair:
            raise PairErrors(self._pairs)

        if pair in self._pairs_mapping.keys():
            pair = self._pairs_mapping.get(pair, pair)

        price = self._get_entry()
        if not price:
            raise PriceError(self._text)

        stop = self._get_stop()
        profits = self._get_profits()
        return OrderModel(
            order_type=order_type,
            pair=pair,
            price=price,
            stop=stop,
            profits=profits,
        )


if __name__ == "__main__":
    txt1 = "📊 Achat : XAUUSD !" \
        "🎯 Prix d’entrée : 4822" \
        "⛔️ Stop : 4812,62" \
        "🚀 TP 1 : 4842,62" \
        "🚀 TakeProfit : 4962,62"\
        "🚀 Take Profit : 4892,62"\
        "🚀 TProfit : 4852,62"

    txt = "XAUUSD BUY NOW 4409"\
        "❌‼️ STOP LOSS 4394"\
        "✔️ 1/ Take Profit 4415"\
        "✔️ 2/ Take Profit 4425"\
        "✔️ 3/ Take Profit 4460"\
        "✔️ 4/ Take Profit OPEN"

    txt2 = "EURJPY sell 4409" \
          "❌Sl 4394" \
          "✔️ 1TP 4415" \
          "✔️ 2 Take Profit 4425" \
          "✔️ 3 Profit 4460" \
          "✔️ 4 Take Profit 4 OPEN"

    txt3 = "$ETH LONG TRADE "\
    "ENTRY: 2935 "\
    "TARGETS: 2990 - 3090 "\
    "STOPLOSS: 2895"

    txt4 = "ETH LONG TRADE " \
           "ENTRY at 2935 " \
           "TARGETS: 2990 - 3090 " \
           "STOPLOSS: 2895"

    txt5 = "buy gold at 4931 sl at 4886.5 tp at 4955"

    data = {
        "Buy Keyword": "buy, achat, long, achete",
        "Sell Keyword": "sell, vente, short, vends",
        "Entry Price Keyword": "Entry zone, at, now, prix d entree, sell, buy, entry",
        "Stop Loss Keyword": "stop loss, stop-loss, sl, sl @, STOPLOSS, Stop",
        "Take Profit Keyword": "take profit, TProfit, take-profit, tp, TakeProfit, TARGETS, - , TP 1 : , TP 4 : , TP 2 : , TP 3 : ",
        "Symbol Keyword": "GOLD, BTC, EURUSD, USDJPY, XAUUSD, EURJPY, ETH",
        "Custom Symbol Matchs": "GOLD=XAUUSD, BTC=BTCUSD"
    }
    MessageFilter.TEMPLATE_REGEX = data
    for i in [txt, txt1, txt2, txt3, txt4, txt5]:
        print()
        print(i)
        message = MessageFilter(i)
        model = message.parse_signal()
        print(model)

    # import json, os
    # from datetime import datetime
    # signal = model.to_dict()
    # signal["lot"] = 0.01
    # signal["comment"] = "TelegramSignal"
    # signal["date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # filename = "signal.json"
    #
    # if os.path.exists(filename):
    #     with open(filename, "r", encoding="utf-8") as f:
    #         try:
    #             signals = json.load(f)
    #             if not isinstance(signals, list):
    #                 signals = []
    #         except json.JSONDecodeError:
    #             signals = []
    # else:
    #     signals = []
    #
    # signal["index"] = len(signals) + 1
    # signals.append(signal)
    # with open(filename, "w", encoding="utf-8") as f:
    #     json.dump(signals, f, indent=4)
