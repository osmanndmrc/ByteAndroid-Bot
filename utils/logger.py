"""
Loguru setup module for console and rotating file logs.
"""

import sys
from pathlib import Path
from loguru import logger
from config.config_loader import LoggingConfig


def setup_logger(config: LoggingConfig, log_dir: str = "logs") -> None:
    """Configures Loguru logger with console and rotating file outputs."""
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    # Remove default handlers
    logger.remove()

    # Add stdout handler with colorized formatting
    console_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>"
    )
    logger.add(sys.stdout, level=config.log_level, format=console_format, colorize=True)

    # Add rotating file handler for general logs
    file_format = (
        "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}"
    )
    logger.add(
        log_path / "snapbot_{time:YYYY-MM-DD}.log",
        level=config.log_level,
        format=file_format,
        rotation=config.rotation,
        retention=config.retention,
        enqueue=True,
        backtrace=True,
        diagnose=True,
    )

    # Add dedicated error file handler
    logger.add(
        log_path / "errors_{time:YYYY-MM-DD}.log",
        level="ERROR",
        format=file_format,
        rotation=config.rotation,
        retention=config.retention,
        enqueue=True,
        backtrace=True,
        diagnose=True,
    )

    logger.info("Logger system initialized successfully.")
