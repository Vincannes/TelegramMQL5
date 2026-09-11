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
    """Queries the GitHub Releases API. Blocking: run outside the UI thread."""
    request = urllib.request.Request(
        GITHUB_API_LATEST_RELEASE,
        headers={"User-Agent": USER_AGENT, "Accept": "application/vnd.github+json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            logger.info("No GitHub release published yet")
        else:
            logger.warning(f"Update check failed: {exc}")
        return None
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
    """Downloads the new exe to a temporary file and returns its path.

    Raises if the download is incomplete, so a corrupted exe never gets
    installed and relaunched.
    """
    request = urllib.request.Request(download_url, headers={"User-Agent": USER_AGENT})
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".exe", prefix="TelegramToMQL_update_")
    try:
        with urllib.request.urlopen(request, timeout=60) as response, os.fdopen(tmp_fd, "wb") as tmp_file:
            expected_size = response.headers.get("Content-Length")
            downloaded = 0
            while True:
                chunk = response.read(65536)
                if not chunk:
                    break
                tmp_file.write(chunk)
                downloaded += len(chunk)

        if expected_size and downloaded != int(expected_size):
            raise IOError(
                f"Incomplete download: got {downloaded} bytes, expected {expected_size}"
            )
    except Exception:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise

    return tmp_path


def apply_update_and_restart(new_exe_path: str) -> None:
    """
    Generates a script that waits for the current process to exit, replaces
    the current exe with the new one, then relaunches the application. Call
    this right before closing the app (QApplication.quit()); it is a no-op
    outside a frozen build.
    """
    if not getattr(sys, "frozen", False):
        logger.warning("apply_update_and_restart ignored: not a frozen build")
        return

    current_exe = sys.executable
    updater_script = os.path.join(tempfile.gettempdir(), "telegram_mql_update.bat")
    update_log = os.path.join(tempfile.gettempdir(), "telegram_mql_update.log")

    # The old exe stays locked for a moment after the process exits (PyInstaller
    # onefile has a bootloader parent process), so retry the move instead of
    # trying to track PIDs, which is fragile and was leaving nothing launched.
    script_content = (
        "@echo off\n"
        "setlocal\n"
        f'set "NEWEXE={new_exe_path}"\n'
        f'set "TARGET={current_exe}"\n'
        f'set "LOG={update_log}"\n'
        "set /a tries=0\n"
        ":retry\n"
        "set /a tries+=1\n"
        'move /Y "%NEWEXE%" "%TARGET%" >NUL 2>>"%LOG%"\n'
        "if errorlevel 1 (\n"
        "    if %tries% GEQ 30 (\n"
        '        echo Update failed after 30 retries, giving up. >>"%LOG%"\n'
        "        goto launch\n"
        "    )\n"
        "    timeout /t 1 /nobreak >NUL\n"
        "    goto retry\n"
        ")\n"
        ":launch\n"
        "timeout /t 2 /nobreak >NUL\n"
        'start "" "%TARGET%"\n'
        'del "%~f0"\n'
    )
    with open(updater_script, "w", encoding="utf-8") as f:
        f.write(script_content)

    subprocess.Popen(
        ["cmd", "/c", updater_script],
        creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
        close_fds=True,
    )
