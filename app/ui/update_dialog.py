#!/usr/bin/env python
"""Boites de dialogue liees a la mise a jour automatique."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMessageBox, QProgressDialog


def show_update_available_dialog(parent, version: str, notes: str) -> bool:
    """Affiche la fenetre d'annonce de mise a jour, retourne True si l'utilisateur valide."""
    box = QMessageBox(parent)
    box.setWindowTitle("Mise à jour disponible")
    box.setIcon(QMessageBox.Information)

    text = f"Une nouvelle version ({version}) est disponible."
    if notes:
        text += f"\n\n{notes}"
    box.setText(text)

    update_btn = box.addButton("Mettre à jour", QMessageBox.AcceptRole)
    box.addButton("Plus tard", QMessageBox.RejectRole)
    box.exec()

    return box.clickedButton() == update_btn


def make_download_progress_dialog(parent) -> QProgressDialog:
    """Fenetre de progression indeterminee affichee pendant le telechargement."""
    dialog = QProgressDialog("Téléchargement de la mise à jour...", None, 0, 0, parent)
    dialog.setWindowTitle("Mise à jour en cours")
    dialog.setWindowModality(Qt.WindowModal)
    dialog.setCancelButton(None)
    dialog.setMinimumDuration(0)
    return dialog


def show_update_failed_dialog(parent, error: str) -> None:
    QMessageBox.warning(
        parent,
        "Mise à jour",
        f"La mise à jour a échoué et sera ignorée pour cette session.\n\n{error}",
    )
