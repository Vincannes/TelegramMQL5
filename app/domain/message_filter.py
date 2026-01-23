#!/usr/bin/env python
# #support	:Trolard Vincent
# copyright	:Vincannes

import re
import unicodedata

from app.domain.exceptions import PairErrors, PriceError, DirectionError
from app.domain.model.order_model import OrderModel

FLAGS = re.IGNORECASE


class MessageFilter(object):

    PAIRS = []
    PAIRS_MAPPING = {}

    def __init__(self, text):
        self._text = self.normalize_text(text.lower())

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
        return text

    def _get_order_type(self):
        value = re.search(
            r"\b(buy|sell|achat|vente|long|short)\b",
            self._text, FLAGS
        )
        if not value:
            return None
        group = value.group(0)
        return group

    def _get_pair(self):
        pairs_pattern = r"\b(" + "|".join(map(re.escape, self.PAIRS)) + r")\b"
        value = re.search(pairs_pattern, self._text, FLAGS)
        if not value:
            return None
        group = value.group(0)
        return group

    def _get_entry(self):
        entry_pattern = r"\b(prix\s*d(?:['’]|\s)?entree|entry|price|buy|sell)\b(?:\s+now)?\s*[:\-]?\s*([\d.,]+)"
        pattern = re.compile(
            entry_pattern,
            FLAGS
        )
        m = pattern.search(self._text)
        if not m:
            return None
        return m.group(2)

    def _get_stop(self):
        value = re.search(
            r"\b(sl|stop\s*loss|stop)\s*[:\-]?\s*([\d.,]+)",
            self._text, FLAGS
        )
        if not value:
            return None
        return value.group(2)

    def _get_profits(self):
        value = re.finditer(
            r"\b(tp\s*\d*|take\s*profit|profit|target|targets)\s*[:\-]?\s*([\d.,]+)",
            self._text, FLAGS
        )
        if not value:
            return None
        return [v.group(2) for v in value]

    def parse_signal(self):
        direction = self._get_order_type()
        if not direction:
            raise DirectionError(self._text)

        pair = self._get_pair()
        if not pair:
            raise PairErrors(self.PAIRS)

        if pair in self.PAIRS_MAPPING.keys():
            print("ici", pair)
            pair = self.PAIRS_MAPPING.get(pair, pair)

        price = self._get_entry()
        if not price:
            raise PriceError(self._text)

        stop = self._get_stop()
        profits = self._get_profits()
        return OrderModel(
            direction=direction,
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

    message = MessageFilter(txt1)
    model = message.parse_signal()
    print(model)

    import json, os
    from datetime import datetime
    signal = model.to_dict()
    signal["lot"] = 0.01
    signal["comment"] = "TelegramSignal"
    signal["date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    filename = "signal.json"

    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            try:
                signals = json.load(f)
                if not isinstance(signals, list):
                    signals = []
            except json.JSONDecodeError:
                signals = []
    else:
        signals = []

    signal["index"] = len(signals) + 1
    signals.append(signal)
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(signals, f, indent=4)
