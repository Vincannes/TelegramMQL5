#!/usr/bin/env python
import os
import sys
import json
import qasync
import asyncio

from telethon import TelegramClient
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QListWidgetItem

from app import constants
from app.domain.logging import setup_logger
from app.domain.valid_session import authorize_qt
from app.domain.telegram_listener import start_listener, get_channels
from app.ui.telegram_mql_ui import MainController
from app.ui.config_windows_ui import ConfigWindow


api_id = int(constants.config["telegram"]["api_id"])
api_hash = constants.config["telegram"]["api_hash"]

logger = setup_logger(constants.LOG_FILE)


class AppController(MainController):
    def __init__(self, ui_file):
        super().__init__(ui_file)

        # Client Telegram unique
        self.client = TelegramClient(constants.SESSION_PATH, api_id, api_hash)
        self.listener_task = None
        self.group_configs = {}

        logger.info(f"Session path: {constants.SESSION_PATH}")

        # Boutons
        self.window.btnLoginQR.clicked.connect(
            lambda: asyncio.create_task(self.on_login_qr())
        )
        self.window.btnBackQR.clicked.connect(self.on_back_qr)
        self.window.btnConfigure.clicked.connect(self.open_config_window)
        self.window.btnNextFolder.clicked.connect(
            lambda: asyncio.create_task(self.on_next_folder())
        )

        # Callback sur Validate
        self.on_validate_callback = self.handle_validate
        self.window.btnConfigure.setEnabled(False)

    async def load_existing_session(self) -> bool:
        if os.path.exists(constants.SESSION_PATH) and constants.MQL_DIR_PATH:
            await self.client.connect()
            if await self.client.is_user_authorized():
                await self.fill_groups()
                return True

            await self.client.disconnect()
        return False

    async def initialize_ui(self):
        self.window.stackedWidget.setCurrentWidget(self.window.page_loading)

        # Laisse le temps à l UI de s'afficher
        await asyncio.sleep(0.1)

        if constants.MQL_DIR_PATH:
            logger.info("MQL dir: {}".format(constants.MQL_DIR_PATH))
            authorized = await self.load_existing_session()

            if authorized:
                self.window.stackedWidget.setCurrentWidget(self.window.page_groups)
                self.window.footerLog.setText("Session restored")
                return

            # dossier OK mais pas de session
            self.window.stackedWidget.setCurrentWidget(self.window.page_phone)
            return

        # Aucun dossier selectionne
        self.window.stackedWidget.setCurrentWidget(self.window.page_select_folder)

    async def fill_groups(self):
        groups = await get_channels(self.client)
        self.window.listGroups.clear()
        for key, value in groups.items():
            item = QListWidgetItem(str(key))
            item.setData(Qt.UserRole, value)
            self.window.listGroups.addItem(item)

    async def on_login_qr(self):
        self.window.lineEditPhone.setVisible(False)
        self.window.btnSendCode.setVisible(False)
        self.window.btnLoginQR.setVisible(False)
        self.window.btnBackQR.setVisible(True)

        await self.client.connect()
        try:
            qr = await self.client.qr_login()
            await authorize_qt(self.client, self.window.qrCodeLabel, qr)
            self.window.footerLog.setText("QR code scanned successfully")
            self.window.stackedWidget.setCurrentWidget(self.window.page_groups)
            self.window.footerLog.setText("")
            await self.fill_groups()

        except asyncio.TimeoutError:
            logger.info("⏰ QR code expired")
            self.window.footerLog.setText("QR code expired")
            self.reset_login_ui()
        except asyncio.CancelledError:
            self.window.footerLog.setText("QR login cancelled ")
            logger.info("QR login cancelled")
            self.reset_login_ui()

    async def handle_validate(self, group_id, group_name):
        if not group_id:
            return

        logger.info(f"Selected group: (ID: {group_id})")
        self.window.footerLog.setText(f"Selected group: (ID: {group_id})")

        # ---- UI ----
        # Lock tous les items et forcer la sélection
        for i in range(self.window.listGroups.count()):
            item = self.window.listGroups.item(i)
            item.setFlags(item.flags() & ~Qt.ItemIsEnabled)
        selected_item = self.window.listGroups.currentItem()
        if selected_item:
            self.window.listGroups.setCurrentItem(selected_item)

        # Bouton Validate devient Unvalidate
        self.window.btnValidate.setText("Unvalidate")

        # Label status
        self.window.labelStatus.setText("Listening")
        self.window.labelStatus.setText("<b>Status:</b> Listening")
        self.window.labelStatus.setVisible(True)

        # ---- Start listener task si pas déjà démarrée ----
        if not self.listener_task or self.listener_task.done():
            self.listener_task = asyncio.create_task(
                start_listener(self.client, int(group_id), group_name, self.logger_widget)
            )

    async def on_next_folder(self):
        with open(constants.SETTINGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        constants.MQL_DIR_PATH = data.get("MQL_DIR_PATH")
        authorized = await self.load_existing_session()
        if authorized:
            self.window.stackedWidget.setCurrentWidget(self.window.page_groups)
            self.window.footerLog.setText("Session restored")
        else:
            self.window.stackedWidget.setCurrentWidget(self.window.page_phone)

    def open_config_window(self):
        item = self.window.listGroups.currentItem()
        if not item:
            logger.info("Please select a group first")
            return

        # group_id = item.data(Qt.UserRole)
        group = item.text()
        config_window = ConfigWindow(group, self.window)
        config_window.exec()

    def on_back_qr(self):
        self.reset_login_ui()

    def reset_login_ui(self):
        """Réinitialise les éléments de la page login"""
        self.window.lineEditPhone.setVisible(True)
        self.window.btnSendCode.setVisible(True)
        self.window.btnLoginQR.setVisible(True)
        self.window.btnBackQR.setVisible(False)
        self.window.qrCodeLabel.clear()
        self.window.stackedWidget.setCurrentWidget(self.window.page_phone)

    def logger_widget(self, msg):
        self.window.footerLog.setText(msg)


def main():
    app = QApplication(sys.argv)

    if os.path.exists(constants.CSS_FILE):
        with open(constants.CSS_FILE, "r") as f:
            app.setStyleSheet(f.read())

    # Boucle qasync
    loop = qasync.QEventLoop(app)
    import asyncio
    asyncio.set_event_loop(loop)

    controller = AppController(constants.MAIN_UI_FILE)
    controller.show()

    # Charger session existante
    # loop.create_task(controller.load_existing_session())
    loop.create_task(controller.initialize_ui())

    with loop:
        loop.run_forever()


if __name__ == "__main__":
    main()
