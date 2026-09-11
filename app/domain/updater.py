#!/usr/bin/env python
"""Auto-update via GitHub Releases: check, download and apply a new build."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Optional

FINISH_UPDATE_FLAG = "--finish-update"

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


def launch_downloaded_exe(exe_path: str, install_target: Optional[str] = None) -> None:
    """Launches the freshly downloaded exe directly.

    When install_target is given, the new process is told (via a CLI flag) to
    copy itself over that path once it starts, so the originally installed
    exe gets updated too, in-process and with proper retries/logging instead
    of an external wait/move .bat script.
    """
    args = [exe_path]
    if install_target:
        args += [FINISH_UPDATE_FLAG, install_target]
    subprocess.Popen(
        args,
        creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
        close_fds=True,
    )


def get_pending_install_target(argv) -> Optional[str]:
    """Returns the target path to self-install to, if argv carries the flag."""
    if FINISH_UPDATE_FLAG in argv:
        idx = argv.index(FINISH_UPDATE_FLAG)
        if idx + 1 < len(argv):
            return argv[idx + 1]
    return None


def install_self_over(target_path: str) -> None:
    """Copies the currently running exe over target_path.

    Blocking: the original exe stays locked for a moment after the old
    process exits, so this retries for up to ~30s. Run in a background
    thread/executor, never on the UI thread. No-op outside a frozen build.
    """
    if not getattr(sys, "frozen", False):
        logger.warning("install_self_over ignored: not a frozen build")
        return

    source = sys.executable
    if os.path.abspath(source) == os.path.abspath(target_path):
        return

    for attempt in range(1, 31):
        try:
            shutil.copy2(source, target_path)
            logger.info(f"Update installed to {target_path}")
            return
        except OSError as exc:
            logger.info(f"Install retry {attempt}/30 for {target_path}: {exc}")
            time.sleep(1)

    logger.warning(f"Failed to install update to {target_path} after retries")
