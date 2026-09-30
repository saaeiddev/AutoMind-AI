from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from core.paths import ensure_directories


def configure_logging() -> logging.Logger:
    paths = ensure_directories()
    logger = logging.getLogger("automind")
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler = RotatingFileHandler(
        paths.logs / "automind.log",
        maxBytes=2_000_000,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    logger.info("AutoMind AI logging initialized")
    return logger
