import logging
import os
import json
from logging.handlers import TimedRotatingFileHandler
from logging import FileHandler, getLogger
from Config import ENV_SETTINGS

os.makedirs(ENV_SETTINGS.LOG_DIR, exist_ok=True)


class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "line_no": record.lineno,
        }
        return json.dumps(log_record)

def setupLoggerFunction(module_name):
    logger= getLogger(module_name)
    logger.setLevel(logging.DEBUG)

    logger.propagate = False

    module_log_dir = os.path.join(ENV_SETTINGS.LOG_DIR, module_name)
    os.makedirs(module_log_dir, exist_ok=True)
    current_dir = os.getcwd()

    all_log_file_path = os.path.join(current_dir, module_log_dir, "all_logs.txt")
    error_log_file_path = os.path.join(current_dir, module_log_dir, "error_logs.txt")

    all_log_file_handler = FileHandler(filename=all_log_file_path, mode="a", encoding="utf-8")
    all_log_file_handler.setLevel(logging.INFO)
    all_log_file_handler.setFormatter(JSONFormatter())

    error_log_file_handler = TimedRotatingFileHandler(filename=error_log_file_path, mode="a", encoding="utf-8")
    error_log_file_handler.setLevel(logging.ERROR)
    error_log_file_handler.setFormatter(JSONFormatter())

    logger.addHandler(all_log_file_handler)
    logger.addHandler(error_log_file_handler)

    return logger