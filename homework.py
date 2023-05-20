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
NO_TOKENS_LOGS = 'Нет токена в {name}'
NO_TOKENS_RAISE = 'Потеряли токен(ы), проверь логи.'
# func send_message
MESSAGE_LOGS_START = 'Отправляем сообщение в ТГ...'
MESSAGE_SENT_LOGS = 'Сообщение успешно отправлено. {message}'
MESSAGE_NOT_SENT_LOGS = 'Ошибка при отправке сообщения: {error}'
# func get_api_answer
API_LOGS_START = 'Проверка запроса к API'
API_BAD_REQUEST_RAISE = ('Сбой в запросе к API: {error}. '
                         'Отправили данные: {data_for_api}')
API_NOT200_RAISE = ('Ответ не 200, а {status_code}. '
                    'Отправили данные: {data_for_api}')
API_BAD_JSON_RAISE = ('Ошибка сервера {code}: {error}. '
                      'Отправили данные: {data_for_api}')
# func check_response
RESPONSE_LOGS_START = 'Проверка ответа API'
RESPONCE_NOT_DICT_RAISE = 'Ответ от API не словарь, a {type}'
RESPONSE_NO_HOMEWORKS_RAISE = 'Потеряли ключ homeworks в ответе API'
RESPONSE_HOMEWORKS_NOT_LIST_RAISE = 'Домашка это не список, a {type}'
# func parse_status
STATUS_LOGS_START = 'Проверка статуса домашней работы'
STATUS_UNKNOWN_NAME_RAISE = 'Неизвестное имя у работы: {homework_name}'
STATUS_UNKNOWN_RAISE = 'Неизвестный статус у работы: {status}'
STATUS_NOT_IN_VERDICTS_RAISE = 'Статуса {status} нет в HOMEWORK_VERDICTS'
STATUS_MESSAGE = ('Изменился статус проверки работы '
                  '"{homework_name}". {verdict}')
# func main LOGS
MAIN_LOGS_START = '--- beginning of file ---'
MAIN_NO_UPDATES = 'Новых домашек/ошибок нет'
MAIN_MESSAGE_NOT_SENT = 'Не получилось отправить сообщение в ТГ: {error}'
MAIN_MESSAGE_NO_UPDATES = 'Это мы уже отправляли'
MAIN_ERROR_MESSAGE = 'Хьюстон, у нас проблемы: {error}'
MAIN_ERROR_MESSAGE_NOT_SENT = ('Не получилось отправить сообщение '
                               'об ошибке в ТГ: {error}')
MAIN_ERROR_MESSAGE_NO_UPDATES = 'Сообщение об ошибке уже отправляли'


def check_tokens():
    """Переменные окружения доступны."""
    logging.debug(TOKENS_LOGS_START)

    TOKENS = {
        'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
        'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
        'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID,
    }
    for name, token in TOKENS.items():
        if token is None:
            logging.critical(NO_TOKENS_LOGS.format(
                name=name)
            )
    for token in TOKENS.values():
        if token is None:
            raise ValueError(NO_TOKENS_RAISE)

    logging.debug(LOGS_OK)


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
    except telegram.TelegramError as error:
        logging.exception(MESSAGE_NOT_SENT_LOGS.format(
            error=error)
        )


def get_api_answer(timestamp):
    """Запрос к эндпоинту API-сервиса."""
    logging.debug(API_LOGS_START)

    data_for_api = {
        'url': ENDPOINT,
        'headers': HEADERS,
        'params': {'from_date': timestamp},
    }
    try:
        response = requests.get(**data_for_api)
    except requests.RequestException as error:
        raise local_exceptions.APIError(API_BAD_REQUEST_RAISE.format(
            error=error,
            data_for_api=data_for_api)
        )
    if response.status_code != HTTPStatus.OK:
        raise requests.HTTPError(API_NOT200_RAISE.format(
            status_code=response.status_code,
            data_for_api=data_for_api)
        )
    response = response.json()
    if 'code' in response or 'error' in response:
        raise requests.HTTPError(API_BAD_JSON_RAISE.format(
            code=response.get('code'),
            error=response.get('error'),
            data_for_api=data_for_api)
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

    homeworks = response.get('homeworks')

    if not isinstance(homeworks, list):
        raise TypeError(RESPONSE_HOMEWORKS_NOT_LIST_RAISE.format(
            type=type(homeworks))
        )

    logging.debug(LOGS_OK)
    return homeworks


def parse_status(homework):
    """Статус домашней работы."""
    logging.debug(STATUS_LOGS_START)

    homework_name = homework.get('homework_name')
    status = homework.get('status')

    if homework_name not in homework.values():
        raise KeyError(STATUS_UNKNOWN_NAME_RAISE.format(
            homework_name=homework_name)
        )
    if status not in homework.values():
        raise KeyError(STATUS_UNKNOWN_RAISE.format(
            status=status)
        )
    if status not in HOMEWORK_VERDICTS:
        raise KeyError(STATUS_NOT_IN_VERDICTS_RAISE.format(
            status=status)
        )

    verdict = HOMEWORK_VERDICTS.get(status)
    message = STATUS_MESSAGE.format(
        homework_name=homework_name,
        verdict=verdict)

    logging.debug(LOGS_OK)
    return message


def main():  # noqa C901
    """Основная логика работы бота."""
    logging.debug(MAIN_LOGS_START)

    check_tokens()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    # timestamp = 0
    last_message = None
    error_message = 'error'

    while True:

        try:

            response = get_api_answer(timestamp)
            homeworks = check_response(response)

            if not homeworks:
                logging.debug(MAIN_NO_UPDATES)
                continue

            message = parse_status(homeworks[0])

            if last_message is not message and error_message:
                try:
                    send_message(bot, message)
                    last_message = message
                    timestamp = response.get('current_date', timestamp)
                except Exception as error:
                    logging.exception(MAIN_MESSAGE_NOT_SENT.format(
                        error=error)
                    )
            else:
                logging.debug(MAIN_MESSAGE_NO_UPDATES)

        except Exception as error:

            if last_message is not error_message:
                error_message = MAIN_ERROR_MESSAGE.format(
                    error=error)
                logging.exception(error_message)
                try:
                    send_message(bot, error_message)
                    last_message = error_message
                except Exception as error:
                    logging.exception(MAIN_ERROR_MESSAGE_NOT_SENT.format(
                        error=error)
                    )
            else:
                logging.debug(MAIN_ERROR_MESSAGE_NO_UPDATES)

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
               '%(message)s - '
               '%(name)s - '
               '%(funcName)s - '
               '%(lineno)d'
    )
    main()
    logging.debug(LOGS_END)
