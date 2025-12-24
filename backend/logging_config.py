"""
Centralized logging configuration for the application.

Usage:
    from backend.logging_config import configure_logging
    configure_logging(app)

This module creates a rotating file handler and configures the root logger
based on values from `backend.config.Config`.
"""

import logging
import os
from logging.handlers import RotatingFileHandler

from config import Config


def configure_logging(app=None) -> None:
    """Configure logging for the project in an idempotent way.

    If `app` is provided, ensure `app.logger` is configured to use
    the same handlers and that propagation is disabled to avoid duplicate messages.
    """
    log_file = (
        Config.LOG_FILE
        if hasattr(Config, "LOG_FILE") and Config.LOG_FILE
        else os.path.join(os.path.dirname(__file__), "logs", "app.log")
    )
    log_dir = os.path.dirname(log_file)
    os.makedirs(log_dir, exist_ok=True)

    level = getattr(logging, Config.LOG_LEVEL.upper(), logging.INFO)

    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s [in %(pathname)s:%(lineno)d]")

    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Add a single rotating file handler if not already present for that path
    already = False
    for h in root_logger.handlers:
        if isinstance(h, RotatingFileHandler) and getattr(h, "baseFilename", None) == os.path.abspath(log_file):
            already = True
            break

    if not already:
        handler = RotatingFileHandler(log_file, maxBytes=Config.LOG_MAX_BYTES, backupCount=Config.LOG_BACKUP_COUNT)
        handler.setLevel(level)
        handler.setFormatter(formatter)
        root_logger.addHandler(handler)

    # If Flask app provided, configure its logger to use the same handlers
    if app is not None:
        app.logger.handlers = root_logger.handlers
        app.logger.setLevel(level)
        app.logger.propagate = False
