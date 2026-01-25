#!/usr/bin/env python
# #support	:Trolard Vincent
# copyright	:Vincannes

import logging
import os
from logging.handlers import RotatingFileHandler

from app import constants


def setup_logger(
    log_file: str = constants.LOG_FILE,
    level=logging.INFO
) -> logging.Logger:
    name = "TelegramMQL5"
    log_dir = os.path.dirname(name)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)

    logger = logging.getLogger(name)
    logger.setLevel(level)

    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # ===== File handler (rotation) =====
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=5 * 1024 * 1024,  # 5 MB
        backupCount=3,
        encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(level)

    # ===== Console handler =====
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(level)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger
