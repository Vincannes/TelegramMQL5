#!/usr/bin/env python
# support   : Trolard Vincent
# copyright : Vincannes

import os
import sys
import json
import configparser
from pathlib import Path


def resource_path(relative_path: str) -> str:
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


# === FICHIERS UI / CONFIG ===
CONFIG_INI_FILE = resource_path("config/config.ini")
MAIN_UI_FILE = resource_path("ui/telegram_mql_ui.ui")
CSS_FILE = resource_path("ui/style.css")

# === CONFIG ===
config = configparser.ConfigParser()

if not os.path.exists(CONFIG_INI_FILE):
    raise FileNotFoundError(f"Config file not found: {CONFIG_INI_FILE}")

config.read(CONFIG_INI_FILE, encoding="utf-8")

# === TELEGRAM ===
API_ID = int(config["telegram"]["api_id"])
API_HASH = config["telegram"]["api_hash"]


# === LOGS (ecriture EXTERNE à l exe) ===
APPDATA_DIR = Path(os.getenv("APPDATA")) / "TelegramMQL"
LOG_DIR = APPDATA_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

LOG_FILE = LOG_DIR / "telegram_log.log"
JSON_DATA_FILE = LOG_DIR / "data.json"

# === SESSION ===
SESSION_NAME = "telegram_session.session"
SESSION_PATH = LOG_DIR / SESSION_NAME

# === MQL ===
SETTINGS_FILE = LOG_DIR / "settings.json"
if not os.path.exists(SETTINGS_FILE):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump({"MQL_DIR_PATH": None}, f, indent=4, ensure_ascii=False)

with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
    data = json.load(f)

MQL_DIR_PATH = data.get("MQL_DIR_PATH", "")
SIGNALS_FILENAME = None
if MQL_DIR_PATH:
    SIGNALS_FILENAME = os.path.join(MQL_DIR_PATH, "Files", "signals.json")


# === KEYWORDS ===
ORDER_KEY = "OrderTypeKeyword"
ENTRY_KEY = "EntryPriceKeyword"
SL_KEY = "StopLossKeyword"
TP_KEY = "TakeProfitKeyword"
SYMBOL_KEY = "SymbolKeyword"
CUST_SYMBOL_KEY = "CustomSymbolMatchs"

ORDER_KEY_FIELD = "Order Type Keyword"
ENTRY_KEY_FIELD = "Entry Price Keyword"
SL_KEY_FIELD = "Stop Loss Keyword"
TP_KEY_FIELD = "Take Profit Keyword"
SYMBOL_KEY_FIELD = "Symbol Keyword"
CUST_SYMBOL_KEY_FIELD = "Custom Symbol Matchs"

ORDER_VALUE = "buy, sell, achat, vente, long, short"
ENTRY_VALUE = "Entry zone, at, now, prix d entree, sell, buy, entry"
SL_VALUE = "stop loss, stop-loss, sl, sl @, STOPLOSS, Stop"
TP_VALUE = "take profit, TProfit, take-profit, tp, TakeProfit, TARGET"
SYMBOL_VALUE = "GOLD, BTC, EURUSD, USDJPY, XAUUSD, EURJPY, ETH"
CUST_SYMBOL_VALUE = "GOLD=XAUUSD, BTC=BTCUSD"

DEFAULT_FIELDS = {
    ORDER_KEY_FIELD: ORDER_VALUE,
    ENTRY_KEY_FIELD: ENTRY_VALUE,
    SL_KEY_FIELD: SL_VALUE,
    TP_KEY_FIELD: TP_VALUE,
    SYMBOL_KEY_FIELD: SYMBOL_VALUE,
    CUST_SYMBOL_KEY_FIELD: CUST_SYMBOL_VALUE,
}

DEFAULT_FIELDS_UI = {
    ORDER_KEY_FIELD: (ORDER_KEY, ORDER_VALUE),
    ENTRY_KEY_FIELD: (ENTRY_KEY, ENTRY_VALUE),
    SL_KEY_FIELD: (SL_KEY, SL_VALUE),
    TP_KEY_FIELD: (TP_KEY, TP_VALUE),
    SYMBOL_KEY_FIELD: (SYMBOL_KEY, SYMBOL_VALUE),
    CUST_SYMBOL_KEY_FIELD: (CUST_SYMBOL_KEY, CUST_SYMBOL_VALUE),
}
