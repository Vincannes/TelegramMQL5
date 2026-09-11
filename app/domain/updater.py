#!/usr/bin/env python
"""Auto-update via GitHub Releases: check, download and apply a new build."""
import json
import os
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Optional

from packaging.version import parse as parse_version

from app import constants
from app.domain.logging import setup_logger

logger = setup_logger(constants.LOG_FILE)

GITHUB_API_LATEST_RELEASE = (
    f"https://api.github.com/repos/{constants.GITHUB_REPO}/releases/latest"
)
USER_AGENT = "TelegramToMQL-Updater"


@dataclass
class UpdateInfo:
    version: str
    download_url: str
    notes: str


def check_for_update() -> Optional[UpdateInfo]:
    """Interroge l'API GitHub Releases. Bloquant : a lancer hors du thread UI."""
    request = urllib.request.Request(
        GITHUB_API_LATEST_RELEASE,
        headers={"User-Agent": USER_AGENT, "Accept": "application/vnd.github+json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        logger.warning(f"Update check failed: {exc}")
        return None

    remote_version = data.get("tag_name", "").lstrip("vV")
    if not remote_version:
        return None

    try:
        if parse_version(remote_version) <= parse_version(constants.APP_VERSION):
            return None
    except Exception as exc:
        logger.warning(f"Invalid version comparison ({remote_version}): {exc}")
        return None

    exe_asset = next(
        (a for a in data.get("assets", []) if a.get("name", "").lower().endswith(".exe")),
        None,
    )
    if not exe_asset:
        logger.warning("Latest release has no .exe asset")
        return None

    return UpdateInfo(
        version=remote_version,
        download_url=exe_asset["browser_download_url"],
        notes=(data.get("body") or "").strip(),
    )


def download_update(download_url: str) -> str:
    """Telecharge le nouvel exe dans un fichier temporaire et retourne son chemin."""
    request = urllib.request.Request(download_url, headers={"User-Agent": USER_AGENT})
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".exe", prefix="TelegramToMQL_update_")
    with urllib.request.urlopen(request, timeout=60) as response, os.fdopen(tmp_fd, "wb") as tmp_file:
        while True:
            chunk = response.read(65536)
            if not chunk:
                break
            tmp_file.write(chunk)
    return tmp_path


def apply_update_and_restart(new_exe_path: str) -> None:
    """
    Genere un script qui attend la fermeture du process courant, remplace
    l'exe actuel par le nouveau puis relance l'application. A appeler juste
    avant de fermer l'app (QApplication.quit()) ; ne fait rien hors build gele.
    """
    if not getattr(sys, "frozen", False):
        logger.warning("apply_update_and_restart ignored: not a frozen build")
        return

    current_exe = sys.executable
    pid = os.getpid()
    updater_script = os.path.join(tempfile.gettempdir(), "telegram_mql_update.bat")

    script_content = (
        "@echo off\n"
        ":wait_loop\n"
        f'tasklist /FI "PID eq {pid}" 2^>NUL | find "{pid}" >NUL\n'
        "if not errorlevel 1 (\n"
        "    timeout /t 1 /nobreak >NUL\n"
        "    goto wait_loop\n"
        ")\n"
        f'move /Y "{new_exe_path}" "{current_exe}" >NUL\n'
        f'start "" "{current_exe}"\n'
        'del "%~f0"\n'
    )
    with open(updater_script, "w", encoding="utf-8") as f:
        f.write(script_content)

    subprocess.Popen(
        ["cmd", "/c", updater_script],
        creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
        close_fds=True,
    )
