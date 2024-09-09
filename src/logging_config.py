import logging.config
from pythonjsonlogger import jsonlogger
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "format": "%(asctime)s %(name) %(levelname)s %(message)s",
            "class": "pythonjsonlogger.jsonlogger.JsonFormatter",
        }
    },
    "handlers": {
        "stdout": {
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
            "formatter": "json",
        },
        'rotating_file_handler': {
            'class': 'logging.handlers.RotatingFileHandler',
            'formatter': 'json',
            'filename': 'logs/app.log',
            'maxBytes': 1024 * 1024,  # 1MB
            'backupCount': 3,  # Keep 3 backup files
        },
    },
    "loggers": {"": {"handlers": ["stdout", "rotating_file_handler"], "level": "DEBUG"}},
}


logging.config.dictConfig(LOGGING)
