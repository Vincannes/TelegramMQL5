#!/usr/bin/env python
# #support : Trolard Vincent
# copyright : Vincannes

import os
import configparser
from telethon import TelegramClient, events

from app.domain.message_filter import MessageFilter
from app.domain.exceptions import FailedParseMessage


# =========================
# CONFIG
# =========================

PROJECT_DIR = os.path.dirname(os.path.dirname(__file__))

config = configparser.ConfigParser()
config.optionxform = str  # preserve case
config.read(os.path.join(PROJECT_DIR, "app", "config", "myconfig.ini"))

api_id = int(config["telegram"]["api_id"])
api_hash = config["telegram"]["api_hash"]
session_name = config["telegram"]["session_name"]
group_name = config["telegram"]["group_name"]

MessageFilter.PAIRS = [p.strip() for p in config["trading"]["pairs"].split(",")]
MessageFilter.PAIRS_MAPPING = dict(config["pair_mapping"])


# =========================
# TEST 1 : MessageFilter
# =========================

def test_message_filter():
    print("\nTEST MessageFilter (manual)")
    print("-" * 50)
    print("Paste the Telegram message you want to test.")
    print("Finish with an empty line to start parsing.\n")

    lines = []
    while True:
        line = input()
        if line.strip() == "":
            break
        lines.append(line)

    text = "\n".join(lines)

    if not text.strip():
        print("⚠️ No message provided")
        return

    print("\nMESSAGE ENTERED")
    print("-" * 50)
    print(text)

    print("\nPARSING..")
    print("-" * 50)

    try:
        mf = MessageFilter(text)
        model = mf.parse_signal()
        print("SIGNAL PARSED SUCCESSFULLY\n")
        print(model)
    except Exception as e:
        FailedParseMessage(text, e)
        print("FAILED TO PARSE THE MESSAGE\n")
        print(e)

# =========================
# MAIN
# =========================

def main():
    test_message_filter()

if __name__ == "__main__":
    main()
