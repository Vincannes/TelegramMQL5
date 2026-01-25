#!/usr/bin/env python
# -*- coding: utf-8 -*-
# support : Trolard Vincent
# copyright : Vincannes

import os
import json
import asyncio
from datetime import datetime
from telethon import TelegramClient, events

from app import constants
from app.domain.logging import setup_logger
from app.domain.exceptions import FailedParseMessage
from app.domain.message_filter import MessageFilter

client_lock = asyncio.Lock()


def get_regex_values():
    if not os.path.exists(constants.JSON_DATA_FILE):
        return
    with open(constants.JSON_DATA_FILE, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            data = {}
    return data


async def get_channels(client):
    channels = {}
    async for dialog in client.iter_dialogs():
        channels[dialog.name] = dialog.id
    return {k: channels[k] for k in sorted(channels.keys())}

DATA = get_regex_values()
logger = setup_logger(log_file=constants.LOG_FILE)


async def start_listener(client: TelegramClient, group_id: int, group_name: str, post_action=False):
    """
    Start listening to a specific Telegram group and process incoming messages.
    """

    @client.on(events.NewMessage(chats=group_id))
    async def handler(event):
        if not event.message.text:
            return

        logger.info(
            "New message | sender=%s | text=%s",
            event.sender_id,
            event.message.text
        )

        model = None
        MessageFilter.TEMPLATE_REGEX = DATA.get(group_name) if DATA else constants.DEFAULT_FIELDS
        logger.info("Group name: %s" % group_name)
        logger.info(MessageFilter.TEMPLATE_REGEX)
        try:
            message = MessageFilter(event.message.text)
            model = message.parse_signal()

            logger.info("Message successfully parsed")
            logger.debug("Parsed model: %s", model)

        except Exception as e:
            err = FailedParseMessage(event.message.text, e)

            logger.warning(
                "Message parsing failed | text=%s",
                event.message.text
            )
            logger.exception(err)
            if post_action:
                post_action(
                    f"Message parsing failed.."
                )
            return

        if not model:
            logger.warning("Message not recognized (no signal detected)")
            return

        signal = model.to_dict()
        signal["date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        async with client_lock:
            if os.path.exists(constants.SIGNALS_FILENAME):
                try:
                    with open(constants.SIGNALS_FILENAME, "r", encoding="utf-8") as f:
                        signals = json.load(f)
                        if not isinstance(signals, list):
                            signals = []
                except json.JSONDecodeError:
                    logger.error("Invalid JSON in signals file, resetting")
                    signals = []
            else:
                signals = []

            signal["index"] = len(signals) + 1
            signals.append(signal)

            with open(constants.SIGNALS_FILENAME, "w", encoding="utf-8") as f:
                json.dump(signals, f, indent=4)

        logger.info(
            "Signal saved | index=%s | file=%s",
            signal["index"],
            constants.SIGNALS_FILENAME
        )
        if post_action:
            post_action(
                f"Signal saved for Symbol={signal['symbol']}"
            )

    logger.info("Listening to Telegram group ID %s", group_id)
    await client.run_until_disconnected()
    logger.info("Disconnected from Telegram")


