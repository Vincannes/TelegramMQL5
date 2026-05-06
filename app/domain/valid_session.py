#!/usr/bin/env python
# #support	:Trolard Vincent
# copyright	:Vincannes

import qrcode
from io import BytesIO
from getpass import getpass

from PySide6.QtGui import QPixmap, Qt
from telethon import TelegramClient, errors

from app.domain.logging import setup_logger

logger = setup_logger()


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
        logger.info("✅ Already authorized, using existing session.")
        return

    try:
        # QR code login
        qr = await client.qr_login()
        logger.info("Scan this QR code with your Telegram app:")
        _print_qr(qr.url)
        await qr.wait(timeout=120)

    except errors.SessionPasswordNeededError:
        # 2FA login
        password = getpass("Enter 2FA password: ")
        await client.sign_in(password=password)


async def authorize_qt(client: TelegramClient, qr_label, qr=None):
    """
    Autorise le client Telegram et affiche le QR dans le QLabel si nécessaire.
    qr: un QR déjà généré, sinon il sera créé.
    """
    if await client.is_user_authorized():
        logger.info("✅ Already authorized, using existing session.")
        return

    try:
        if qr is None:
            qr = await client.qr_login()
            logger.info("Scan this QR code with your Telegram app:")
        show_qr_in_label(qr_label, qr.url)
        await qr.wait(timeout=120)
        logger.info("✅ QR code scanned successfully!")

    except errors.SessionPasswordNeededError:
        password = getpass("Enter 2FA password: ")
        await client.sign_in(password=password)


async def _authorize_qt(client: TelegramClient, qr_label):
    """
    Autorise le client Telegram et affiche le QR dans le QLabel si nécessaire.
    """
    if await client.is_user_authorized():
        logger.info("✅ Already authorized, using existing session.")
        return

    try:
        qr = await client.qr_login()
        logger.info("Scan this QR code with your Telegram app:")

        show_qr_in_label(qr_label, qr.url)
        await qr.wait(timeout=120)
        logger.info("✅ QR code scanned successfully!")

    except errors.SessionPasswordNeededError:
        password = getpass("Enter 2FA password: ")
        await client.sign_in(password=password)


def show_qr_in_label(label, qr_url: str):
    """
    Génère un QR code à partir de l'URL et l'affiche dans un QLabel.
    """
    qr = qrcode.QRCode(border=2)
    qr.add_data(qr_url)

    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    buffer = BytesIO()
    img.save(buffer, format="PNG")
    pixmap = QPixmap()
    pixmap.loadFromData(buffer.getvalue(), "PNG")

    size = label.minimumSize()
    w = size.width() if size.width() > 0 else 220
    h = size.height() if size.height() > 0 else 220
    pixmap = pixmap.scaled(w, h, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)

    label.setPixmap(pixmap)
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    label.setVisible(True)
