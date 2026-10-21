import logging
import os
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

# 指向 backend/ 根目录
_BACKEND_ROOT = Path(__file__).resolve().parents[2]


class LogUtil:
    """
    通用日志管理工具
    """
    _loggers = {}

    @classmethod
    def get_logger(cls, module_name: str) -> logging.Logger:
        if module_name in cls._loggers:
            return cls._loggers[module_name]

        logger = logging.getLogger(module_name)
        logger.setLevel(logging.INFO)

        # 统一输出路径为 backend/logs
        log_dir = _BACKEND_ROOT / 'logs'
        if not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)

        if not logger.handlers:
            log_file = os.path.join(log_dir, f"{module_name}.log")

            # 每天凌晨切分，保留 30 天日志
            handler = TimedRotatingFileHandler(
                log_file, when="midnight", interval=1, backupCount=30, encoding="utf-8"
            )
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)

            # 控制台标准输出
            console = logging.StreamHandler()
            console.setFormatter(formatter)
            logger.addHandler(console)

        cls._loggers[module_name] = logger
        return logger
