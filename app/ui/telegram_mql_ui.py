#!/usr/bin/env python
# #support	:Trolard Vincent
# copyright	:Vincannes

import json
import asyncio
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QFile, Qt
from PySide6.QtWidgets import QFileDialog

from app import constants

class MainController(object):
    def __init__(self, ui_file):
        # Load UI
        ui_file = QFile(ui_file)
        ui_file.open(QFile.ReadOnly)

        loader = QUiLoader()
        self.window = loader.load(ui_file)
        ui_file.close()

        if not self.window:
            raise RuntimeError("Failed to load UI")

        self.groups_locked = False
        self.on_validate_callback = None

        # ----- INITIAL STATE -----
        self.window.stackedWidget.setCurrentIndex(0)
        self.reset_login_view()

        # ----- SIGNALS -----
        # pseudo code
        self.window.btnSelectFolder.clicked.connect(self.select_folder)

        self.window.btnLoginQR.clicked.connect(self.show_qr_code)
        self.window.btnBackQR.clicked.connect(self.back_from_qr)

        self.window.btnSendCode.clicked.connect(self.on_send_code)
        self.window.btnValidate.clicked.connect(self.on_validate_group)

        self.window.btnLoginCode.clicked.connect(self.go_to_groups)

    # ================= LOGIN =================

    def show_qr_code(self):
        # Show QR + Back
        self.window.qrCodeLabel.setVisible(True)
        self.window.btnBackQR.setVisible(True)

        # Hide phone login
        self.window.lineEditPhone.setVisible(False)
        self.window.btnSendCode.setVisible(False)
        self.window.btnLoginQR.setVisible(False)

    def back_from_qr(self):
        self.reset_login_view()

    def reset_login_view(self):
        # ----- Cacher QR -----
        self.window.qrCodeLabel.setVisible(False)
        # ----- Cacher code login -----
        self.window.labelEnterCode.setVisible(False)
        self.window.lineEditCode.setVisible(False)
        self.window.btnLoginCode.setVisible(False)
        # ----- Cacher back QR/code -----
        self.window.btnBackQR.setVisible(False)

        # ----- Montrer telephone login -----
        self.window.lineEditPhone.setVisible(True)
        self.window.btnSendCode.setVisible(True)
        self.window.btnLoginQR.setVisible(True)

    def on_send_code(self):
        phone = self.window.lineEditPhone.text().strip()
        if not phone:
            return
        self.show_code_login()

    def show_code_login(self):
        # Hide phone login
        self.window.lineEditPhone.setVisible(False)
        self.window.btnSendCode.setVisible(False)
        self.window.btnLoginQR.setVisible(False)

        # Hide QR if it was visible
        self.window.qrCodeLabel.setVisible(False)
        self.window.btnBackQR.setVisible(False)

        # Show code login widgets
        self.window.labelEnterCode.setVisible(True)
        self.window.lineEditCode.setVisible(True)
        self.window.btnLoginCode.setVisible(True)

        # Show Back button (reuse btnBackQR)
        self.window.btnBackQR.setVisible(True)

    def back_from_qr(self):
        self.reset_login_view()

    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(
            parent=self.window,
            caption="Select the MQL5 folder",
            options=QFileDialog.ShowDirsOnly
        )
        if folder:
            self.window.labelSelectedFolder.setText(folder)
            with open(constants.SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump({"MQL_DIR_PATH": folder}, f, indent=4, ensure_ascii=False)

    # ================= NAVIGATION =================
    def go_to_groups(self):
        self.window.stackedWidget.setCurrentIndex(1)

    def go_to_login(self):
        self.window.stackedWidget.setCurrentIndex(0)
        self.reset_login_view()

    # ================= GROUP =================
    def on_validate_group(self):
        if not self.groups_locked:
            # LOCK all items
            selected_item = self.window.listGroups.currentItem()

            for i in range(self.window.listGroups.count()):
                item = self.window.listGroups.item(i)
                item.setFlags(item.flags() & ~Qt.ItemIsSelectable & ~Qt.ItemIsEnabled)

            selected_item.setFlags(selected_item.flags() | Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            self.window.listGroups.setCurrentItem(selected_item)

            self.window.btnValidate.setText("Unvalidate")
            self.window.titleGroups.setText("Select a group: {}".format(selected_item.text()))
            self.groups_locked = True
            self.window.labelStatus.setVisible(True)
            self.window.btnConfigure.setEnabled(True)

            group_id = selected_item.data(Qt.UserRole)
            group_name = selected_item.text()
            if self.on_validate_callback:
                asyncio.create_task(self.on_validate_callback(group_id, group_name))

        else:
            # UNLOCK all items
            for i in range(self.window.listGroups.count()):
                item = self.window.listGroups.item(i)
                item.setFlags(item.flags() | Qt.ItemIsSelectable | Qt.ItemIsEnabled)

            self.window.btnConfigure.setEnabled(False)
            self.window.titleGroups.setText("Select a group:")
            self.window.btnValidate.setText("Validate")
            self.groups_locked = False
            self.window.labelStatus.setVisible(False)

    def show(self):
        self.window.show()

