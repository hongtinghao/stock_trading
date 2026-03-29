import logging
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
import sys

from stock_trading.config.settings import settings

def get_logger(name: str, console_level: int = None, file_level: int = None) -> logging.Logger:
    """
    生成一个同时写文件+控制台的 logger，配置从 settings.LOGGING_CONFIG 读取。

    Args:
        name: 通常传 __name__
        console_level: 可选，覆盖配置中的控制台级别
        file_level: 可选，覆盖配置文件中的文件级别
    """
    logger = logging.getLogger(name)
    if logger.hasHandlers():
        return logger

    # 从配置读取参数
    log_dir = settings.LOGGING_CONFIG['DIR']
    log_dir.mkdir(parents=True, exist_ok=True)

    file_path = log_dir / settings.LOGGING_CONFIG['FILE_NAME']

    # 级别（优先使用调用参数，否则用配置）
    cfg_console_level = getattr(logging, settings.LOGGING_CONFIG['CONSOLE_LEVEL'].upper(), logging.INFO)
    cfg_file_level = getattr(logging, settings.LOGGING_CONFIG['FILE_LEVEL'].upper(), logging.DEBUG)
    console_level = console_level if console_level is not None else cfg_console_level
    file_level = file_level if file_level is not None else cfg_file_level

    logger.setLevel(min(console_level, file_level))

    # 控制台 handler
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(console_level)
    console_fmt = logging.Formatter(
        fmt=settings.LOGGING_CONFIG['CONSOLE_FORMAT'],
        datefmt=settings.LOGGING_CONFIG['CONSOLE_DATE_FORMAT']
    )
    console.setFormatter(console_fmt)

    # 按天滚动的文件 handler
    file_handler = TimedRotatingFileHandler(
        filename=file_path,
        when=settings.LOGGING_CONFIG['WHEN'],
        interval=settings.LOGGING_CONFIG['INTERVAL'],
        backupCount=settings.LOGGING_CONFIG['BACKUP_COUNT'],
        encoding='utf-8'
    )
    file_handler.setLevel(file_level)
    file_fmt = logging.Formatter(fmt=settings.LOGGING_CONFIG['FILE_FORMAT'])
    file_handler.setFormatter(file_fmt)

    logger.addHandler(console)
    logger.addHandler(file_handler)
    return logger