import logging
import sys


logging.basicConfig(
    level=logging.DEBUG,
    filename='logs_all.log',
    filemode='w',
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


def logger_for_homework():
    """Настройка логов для домашки."""
    logger = logging.getLogger('homework.py')
    logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler(stream=sys.stdout)
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger


LOGS_SETTINGS = {
    'hw_logger': logger_for_homework(),
}
