import logging
import os
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

_HERE = Path(__file__).parent.parent


class LogUtil:
    """
    日志管理类
    """
    _loggers = {}

    @classmethod
    def get_logger(cls, module_name):

        if module_name in cls._loggers:
            return cls._loggers[module_name]

        logger = logging.getLogger(module_name)
        logger.setLevel(logging.INFO)

        # 设置路径
        log_dir = _HERE / 'log'
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        if not logger.handlers:
            log_file = os.path.join(log_dir, f"{module_name}.log")

            # 每天凌晨切分
            handler = TimedRotatingFileHandler(
                log_file, when="midnight", interval=1, backupCount=30, encoding="utf-8"
            )
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)

            logger.addHandler(handler)
            # 添加控制台输出
            console = logging.StreamHandler()
            console.setFormatter(formatter)
            logger.addHandler(console)

        cls._loggers[module_name] = logger
        return logger
