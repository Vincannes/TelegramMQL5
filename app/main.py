#!/usr/bin/env python
# #support	:Trolard Vincent
# copyright	:Vincannes
import os
import json
import configparser
from datetime import datetime

from telethon import TelegramClient, events

from app.domain.exceptions import FailedParseMessage
from app.domain.message_filter import MessageFilter

# =========================
# CONFIG
# =========================

PROJECT_DIR = os.path.dirname(os.path.dirname(__file__))

config = configparser.ConfigParser()
config.read(os.path.join(PROJECT_DIR, "app", "config", "config.ini"))

MQL_FILE_DIR = config["paths"]["mql_file_dir"]
api_id = int(config["telegram"]["api_id"])
api_hash = config["telegram"]["api_hash"]
session_name = config["telegram"]["session_name"]
filename = os.path.join(MQL_FILE_DIR, "signals.json")
log_file = os.path.join(PROJECT_DIR, "logs", "telegram_log.txt")
pair_mapping = dict(config["pair_mapping"])

client = TelegramClient(session_name, api_id, api_hash)
MessageFilter.PAIRS = [p.strip() for p in config["trading"]["pairs"].split(",")]
MessageFilter.PAIRS_MAPPING = pair_mapping

# =========================
# PROCESS
# =========================


@client.on(events.NewMessage(chats=config["telegram"]["group_name"]))
async def handler(event):
    if event.message.text:
        log_line = f"[{event.message.date}] {event.sender_id}: {event.message.text}\n"
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(log_line)

        print("📩 New message logged : '{}'".format(event.message.text))
        model = None
        try:
            message = MessageFilter(event.message.text)
            model = message.parse_signal()
            print(model)
        except Exception as e:
            FailedParseMessage(event.message.text, e)

        if model:
            signal = model.to_dict()
            signal["lot"] = float(config["mql"]["default_lot"])
            signal["comment"] = config["mql"]["comment"]
            signal["date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
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
            print(f"✅ Signal write dans {filename}")


client.start()
print("🟢 Listening...")
client.run_until_disconnected()

