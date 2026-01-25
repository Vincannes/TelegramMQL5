import os
import json


from PySide6.QtWidgets import QDialog, QFormLayout, QLabel, QLineEdit, QHBoxLayout, QPushButton, QVBoxLayout, QTextEdit
from PySide6.QtCore import Qt

from app import constants
from app.domain.message_filter import MessageFilter


class ConfigWindow(QDialog):
    FIELDS = constants.DEFAULT_FIELDS_UI

    def __init__(self, group, parent=None):
        super().__init__(parent)
        self._group = group
        self.setWindowTitle("Channel Configuration")
        self.setFixedSize(800, 700)  # Taille fixe

        if parent:
            geo = parent.geometry()
            self.move(
                geo.x() + (geo.width() - self.width()) // 2,
                geo.y() + (geo.height() - self.height()) // 2
            )

        self.layout = QVBoxLayout(self)

        form = QFormLayout()

        self.inputs = {}
        for label, values in self.FIELDS.items():
            key = values[0]
            exemple = values[1]
            line_edit = QLineEdit(exemple)
            form.addRow(label + ":", line_edit)
            self.inputs[key] = line_edit

        self.layout.addLayout(form)

        button_layout = QHBoxLayout()
        self.btnReset = QPushButton("Reset")
        self.btnReset.clicked.connect(self.on_reset)
        button_layout.addWidget(self.btnReset)

        button_layout.addStretch()  # espace ENTRE Reset et Save

        self.btnSave = QPushButton("Save")
        self.btnSave.clicked.connect(self.on_save)
        button_layout.addWidget(self.btnSave)

        self.layout.addLayout(button_layout)

        # =========================
        # TEST MESSAGE SECTION
        # =========================
        test_label = QLabel("Test Message")
        test_label.setStyleSheet("font-weight: bold;")

        self.test_input = QTextEdit()
        self.test_input.setPlaceholderText("Past here your Telegram message to test...")

        self.btn_test = QPushButton("Test")
        self.btn_test.clicked.connect(self.on_test_message)

        self.test_log = QTextEdit()
        self.test_log.setReadOnly(True)
        self.test_log.setPlaceholderText("Logs...")

        self.layout.addWidget(test_label)
        self.layout.addWidget(self.test_input)
        self.layout.addWidget(self.btn_test)
        self.layout.addWidget(self.test_log)

        self.saved_data = {}
        self.load_values()

    def load_values(self):
        if not os.path.exists(constants.JSON_DATA_FILE):
            return
        with open(constants.JSON_DATA_FILE, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                data = {}

        if self._group in data and isinstance(data[self._group], dict):
            for key, (label_text, default_value) in self.FIELDS.items():
                if key in data[self._group]:
                    self.inputs[label_text].setText(str(data[self._group][key]))

    def on_reset(self):
        for label_text, line_edit in self.inputs.items():
            matching_key = None
            for key, (field_label, default) in self.FIELDS.items():
                if field_label == label_text:
                    matching_key = key
                    break
            if matching_key:
                default_value = self.FIELDS[matching_key][1]
                line_edit.setText(default_value)

    def on_save(self):
        for key, line_edit in self.inputs.items():
            self.saved_data[key] = line_edit.text().strip()

        if os.path.exists(constants.JSON_DATA_FILE):
            with open(constants.JSON_DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = {}

        if self._group not in data:
            data[self._group] = {}

        for label_text, line_edit in self.inputs.items():
            matching_key = None
            for key, (field_label, default_value) in self.FIELDS.items():
                if field_label == label_text:
                    matching_key = key
                    break

            if matching_key:
                data[self._group][matching_key] = line_edit.text()

        with open(constants.JSON_DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        self.accept()

    def get_current_config(self):
        config = {}
        for label_text, line_edit in self.inputs.items():
            for key, (field_label, _) in self.FIELDS.items():
                if field_label == label_text:
                    config[key] = line_edit.text()
                    break
        return config

    def on_test_message(self):
        self.test_log.clear()
        text = self.test_input.toPlainText().strip()

        if not text:
            self.test_log.append("❌ No input message provided for testing.")
            return

        config = self.get_current_config()
        try:
            MessageFilter.TEMPLATE_REGEX = config
            message = MessageFilter(text)
            model = message.parse_signal()

            if model:
                self.test_log.append("✅ Message successfully recognized")
                self.test_log.append("\n--- Result ---")
                self.test_log.append(str(model))
            else:
                self.test_log.append("⚠️ Message not recognized (no signal detected)")

        except Exception as e:
            self.test_log.append("❌ Parsing error occurred:")
            self.test_log.append(str(e))
