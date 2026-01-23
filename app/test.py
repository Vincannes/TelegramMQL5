#!/usr/bin/env python
# #support	:Trolard Vincent
# copyright	:Vincannes
#!/usr/bin/env python
import os
import asyncio
import argparse
import configparser
from telethon import TelegramClient, events

from app.domain.message_filter import MessageFilter
from app.domain.exceptions import FailedParseMessage


# =========================
# CONFIG
# =========================

PROJECT_DIR = os.path.dirname(os.path.dirname(__file__))

config = configparser.ConfigParser()
config.optionxform = str  # conserve la casse
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
# TEST 2 : TelegramClient réel
# =========================

async def test_telegram_client():
    print("\n🧪 TEST TelegramClient (réel)\n" + "-" * 40)

    client = TelegramClient(session_name + "_test", api_id, api_hash)

    @client.on(events.NewMessage(chats=group_name))
    async def handler(event):
        print("\n📨 MESSAGE REÇU DE TELEGRAM")
        print("From :", event.sender_id)
        print("Text :", event.message.text)

        try:
            mf = MessageFilter(event.message.text)
            model = mf.parse_signal()
            print("✅ Signal détecté :", model)
        except Exception as e:
            FailedParseMessage(event.message.text, e)
            print("❌ Message ignoré")

        print("\n⛔ Fin du test Telegram (1 message)")
        await client.disconnect()

    await client.start()
    print("🟢 En attente d’un message Telegram...")
    await client.run_until_disconnected()


# =========================
# MAIN
# =========================

def main():
    parser = argparse.ArgumentParser(description="TelegramMQL5 test runner")
    parser.add_argument(
        "--mode",
        choices=["message", "telegram"],
        required=True,
        help="Test mode: 'message' to test MessageFilter, 'telegram' to test TelegramClient"
    )

    args = parser.parse_args()

    if args.mode == "message":
        test_message_filter()

    elif args.mode == "telegram":
        asyncio.run(test_telegram_client())


if __name__ == "__main__":
    main()