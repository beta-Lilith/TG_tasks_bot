import logging
import os
import sys
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

import local_exceptions


load_dotenv()
PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
TOKENS = [
    'PRACTICUM_TOKEN',
    'TELEGRAM_TOKEN',
    'TELEGRAM_CHAT_ID',
]
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}
RETRY_PERIOD = 10 * 60
# Text messages:
LOGS_OK = 'OK'
LOGS_END = '--- end of file ---'
# func check_tokens
TOKENS_LOGS_START = 'Проверка токенов'
NO_TOKENS_LOGS = 'Потеряли токен(ы) в {missing_tokens}'
NO_TOKENS_RAISE = 'Потеряли токен(ы): {missing_tokens}'
# func send_message
MESSAGE_LOGS_START = 'Отправляем сообщение в ТГ...'
MESSAGE_SENT_LOGS = 'Сообщение успешно отправлено. {message}'
MESSAGE_NOT_SENT_LOGS = 'Ошибка {error} при отправке сообщения:\n{message}'
# func get_api_answer
API_LOGS_START = 'Проверка запроса к API'
API_BAD_REQUEST_RAISE = (
    'Сбой в запросе к API: {error}\n'
    'Отправили данные:\n'
    'url - {url}\n'
    'headers - {headers}\n'
    'params - {params}'
)
API_NOT200_RAISE = (
    'Ответ не 200, а {status_code}\n'
    'Отправили данные:\n'
    'url - {url}\n'
    'headers - {headers}\n'
    'params - {params}'
)
API_BAD_JSON_RAISE = (
    'Ошибка сервера {key}: {error}\n'
    'Отправили данные:\n'
    'url - {url}\n'
    'headers - {headers}\n'
    'params - {params}'
)
# func check_response
RESPONSE_LOGS_START = 'Проверка ответа API'
RESPONCE_NOT_DICT_RAISE = 'Ответ от API не словарь, a {type}'
RESPONSE_NO_HOMEWORKS_RAISE = 'Потеряли ключ homeworks в ответе API'
RESPONSE_HOMEWORKS_NOT_LIST_RAISE = 'Домашка это не список, a {type}'
# func parse_status
STATUS_LOGS_START = 'Проверка статуса домашней работы'
STATUS_UNKNOWN_NAME_RAISE = 'Нет ключа homework_name в домашке'
STATUS_UNKNOWN_RAISE = 'Нет ключа status в домашке'
STATUS_NOT_IN_VERDICTS_RAISE = 'Статуса {status} нет в HOMEWORK_VERDICTS'
STATUS_MESSAGE = (
    'Изменился статус проверки работы '
    '"{homework_name}". {verdict}'
)
# func main LOGS
MAIN_LOGS_START = '--- beginning of file ---'
MAIN_NO_UPDATES = 'Статус домашки не менялся'
MAIN_ERROR_MESSAGE = 'Хьюстон, у нас проблемы: {error}'


def check_tokens():
    """Переменные окружения доступны."""
    logging.debug(TOKENS_LOGS_START)
    missing_tokens = [token_name
                      for token_name in TOKENS
                      if globals()[token_name] is None]
    if missing_tokens:
        logging.critical(NO_TOKENS_LOGS.format(
            missing_tokens=missing_tokens)
        )
        raise ValueError(NO_TOKENS_RAISE.format(
            missing_tokens=missing_tokens)
        )


def send_message(bot, message):
    """Отправка сообщений в Telegram."""
    logging.debug(MESSAGE_LOGS_START)
    try:
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message)
        logging.debug(MESSAGE_SENT_LOGS.format(
            message=message)
        )
        return True
    except telegram.TelegramError as error:
        logging.exception(MESSAGE_NOT_SENT_LOGS.format(
            error=error,
            message=message)
        )
        return False


def get_api_answer(timestamp):
    """Запрос к эндпоинту API-сервиса."""
    logging.debug(API_LOGS_START)
    data_for_api = dict(
        url=ENDPOINT,
        headers=HEADERS,
        params={'from_date': timestamp},
    )
    try:
        response = requests.get(**data_for_api)
    except requests.RequestException as error:
        raise ConnectionError(API_BAD_REQUEST_RAISE.format(
            error=error,
            **data_for_api)
        )
    if response.status_code != HTTPStatus.OK:
        raise local_exceptions.Not200Error(API_NOT200_RAISE.format(
            status_code=response.status_code,
            **data_for_api)
        )
    response = response.json()
    for key in ['code', 'error']:
        if key in response:
            raise local_exceptions.APIErrorKeyError(API_BAD_JSON_RAISE.format(
                key=key,
                error=response.get(key),
                **data_for_api)
            )
    logging.debug(LOGS_OK)
    return response


def check_response(response):
    """Ответ API соответствует документации."""
    logging.debug(RESPONSE_LOGS_START)
    if not isinstance(response, dict):
        raise TypeError(RESPONCE_NOT_DICT_RAISE.format(
            type=type(response))
        )
    if 'homeworks' not in response:
        raise KeyError(RESPONSE_NO_HOMEWORKS_RAISE)
    homeworks = response['homeworks']
    if not isinstance(homeworks, list):
        raise TypeError(RESPONSE_HOMEWORKS_NOT_LIST_RAISE.format(
            type=type(homeworks))
        )
    logging.debug(LOGS_OK)
    return homeworks


def parse_status(homework):
    """Статус домашней работы."""
    logging.debug(STATUS_LOGS_START)
    if 'homework_name' not in homework:
        raise KeyError(STATUS_UNKNOWN_NAME_RAISE)
    if 'status' not in homework:
        raise KeyError(STATUS_UNKNOWN_RAISE)
    status = homework.get('status')
    if status not in HOMEWORK_VERDICTS:
        raise ValueError(STATUS_NOT_IN_VERDICTS_RAISE.format(
            status=status)
        )
    logging.debug(LOGS_OK)
    return STATUS_MESSAGE.format(
        homework_name=homework.get('homework_name'),
        verdict=HOMEWORK_VERDICTS.get(status)
    )


def main():
    """Основная логика работы бота."""
    logging.debug(MAIN_LOGS_START)
    check_tokens()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    last_message = None
    while True:
        try:
            response = get_api_answer(timestamp)
            homeworks = check_response(response)
            if not homeworks:
                logging.debug(MAIN_NO_UPDATES)
                continue
            message = parse_status(homeworks[0])
            if last_message != message and send_message(bot, message):
                last_message = message
                timestamp = response.get('current_date', timestamp)
        except Exception as error:
            error_message = MAIN_ERROR_MESSAGE.format(
                error=error)
            logging.exception(error_message)
            if (last_message != error_message
               and send_message(bot, error_message)):
                last_message = error_message
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    # Logs settings
    logging.basicConfig(
        level=logging.DEBUG,
        handlers=(
            logging.StreamHandler(stream=sys.stdout),
            logging.FileHandler(
                filename=__file__ + '.log',
                mode='w')
        ),
        format='%(asctime)s - '
               '%(levelname)s - '
               '%(name)s - '
               '%(funcName)s - '
               '%(lineno)d - '
               '%(message)s'
    )
    main()
    logging.debug(LOGS_END)
