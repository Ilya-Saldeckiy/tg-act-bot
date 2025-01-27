from datetime import datetime
from inspect import getframeinfo
from loguru import logger


class LogLevels:
    """Уровни логирования"""
    TRACE = 'TRACE'
    DEBUG = 'DEBUG'
    INFO = 'INFO'
    SUCCESS = 'SUCCESS'
    WARNING = 'WARNING'
    ERROR = 'ERROR'
    CRITICAL = 'CRITICAL'


class Log:
    """Логирование"""

    def __init__(self, data, app, level=LogLevels.INFO, frame=None):
        logger.add(
            f"logs/{level.lower()}-{datetime.now().date()}-{app}.log",
            retention='10 days',
            rotation='1 GB',
            level=level,
        )

        if frame:
            frame_info = getframeinfo(frame)
            data = f'{data} -> Файл: {frame_info.filename}, Строка: {frame_info.lineno}'

        if str(level) == LogLevels.TRACE:
            logger.trace(data)
        elif str(level) == LogLevels.DEBUG:
            logger.debug(data)
        elif str(level) == LogLevels.SUCCESS:
            logger.success(data)
        elif str(level) == LogLevels.WARNING:
            logger.warning(data)
        elif str(level) == LogLevels.ERROR:
            logger.error(data)
        elif str(level) == LogLevels.CRITICAL:
            logger.critical(data)
        elif str(level) == LogLevels.INFO:
            logger.info(data)
