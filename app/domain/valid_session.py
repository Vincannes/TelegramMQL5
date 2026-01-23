#!/usr/bin/env python
# #support	:Trolard Vincent
# copyright	:Vincannes

import qrcode
from getpass import getpass
from telethon import TelegramClient, events, errors


def _print_qr(url: str) -> None:
    """Display QR code in terminal."""
    qr = qrcode.QRCode(border=1)
    qr.add_data(url)
    qr.make(fit=True)
    qr.print_ascii(invert=True)


async def authorize(client: TelegramClient) -> None:
    """
    Authorize the Telegram client.
    If QR code login is required, prints it to terminal.
    If 2FA is required, asks for password.
    """
    if await client.is_user_authorized():
        print("✅ Already authorized, using existing session.")
        return

    try:
        # QR code login
        qr = await client.qr_login()
        print("Scan this QR code with your Telegram app:")
        _print_qr(qr.url)
        await qr.wait(timeout=120)

    except errors.SessionPasswordNeededError:
        # 2FA login
        password = getpass("Enter 2FA password: ")
        await client.sign_in(password=password)


# def _print_qr(url: str) -> None:
#     qr = qrcode.QRCode(border=1)
#     qr.add_data(url)
#     qr.make(fit=True)
#     qr.print_ascii(invert=True)
#
#
# async def authorize(client: TelegramClient) -> None:
#     if await client.is_user_authorized():
#         return
#
#     try:
#         qr = await client.qr_login()
#         _print_qr(qr.url)
#         await qr.wait(timeout=120)
#
#     except errors.SessionPasswordNeededError:
#         password = getpass("2FA password: ")
#         await client.sign_in(password=password)
#
# async def main_session() -> None:
#     client = TelegramClient(session_name, api_id, api_hash)
#     await client.connect()
#
#     try:
#         await authorize(client)
#
#         me = await client.get_me()
#         print(f"Logged in as: {me.first_name}")
#
#         await client.run_until_disconnected()
#
#     finally:
#         await client.disconnect()