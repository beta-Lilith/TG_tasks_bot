import os
from dotenv import load_dotenv
import requests
import time
import telegram
import sys
import local_exceptions
import logging

# Ниже объяснение что это
# from logs_settings import LOGS_SETTINGS


load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

RETRY_PERIOD = 10 * 60

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}
# Очень захотелось реализовать идею хранить все настройки для логов в одном
# файле и потом их импортировать в код.
# Понимаю, что код в том файле весь будет исполнятся, сидела думала над идеей
# нэйм равно мэйн, но ведь я хочу видеть логи со всего проекта
# тоже.. Интересно мнение на этот счет

# Однако, чтобы пройти пайтест приходится оставлять идею в комментариях.
# Поэтому логи в коде начинаются с HW_LOGGER.

# HW_LOGGER = LOGS_SETTINGS.get('hw_logger')

logging.basicConfig(
    level=logging.DEBUG,
    filename='logs_all.log',
    filemode='w',
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

HW_LOGGER = logging.getLogger('homework.py')
HW_LOGGER.setLevel(logging.DEBUG)
handler = logging.StreamHandler(stream=sys.stdout)
formatter = logging.Formatter(
    '%(asctime)s - %(levelname)s - %(message)s'
)
handler.setFormatter(formatter)
HW_LOGGER.addHandler(handler)


def check_tokens():
    """Переменные окружения доступны."""
    HW_LOGGER.debug(
        'Проверка токенов')

    tokens = (PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID)
    for token in tokens:
        if token is None:
            HW_LOGGER.critical(
                f'Нет токена в {token}')
            raise ValueError(
                'Потеряли токен')
    HW_LOGGER.debug('OK')
    return True


def send_message(bot, message):
    """Отправка сообщений в Telegram."""
    HW_LOGGER.debug(
        'Отправляем сообщение в ТГ...')

    try:
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message)
        HW_LOGGER.debug(
            'Сообщение успешно отправлено')
    except telegram.TelegramError:
        HW_LOGGER.error(
            'Ошибка при отправке сообщения')


def get_api_answer(timestamp):
    """Запрос к эндпоинту API-сервиса."""
    HW_LOGGER.debug(
        'Проверка запроса к API')

    if 'Authorization' not in HEADERS:
        HW_LOGGER.error(
            'Нет ключа Authorization в HEADERS')
        raise KeyError(
            'Забыли как авторизовываться, скоро вспомним')

    try:
        data_for_api = {
            'url': ENDPOINT,
            'headers': HEADERS,
            'params': {'from_date': timestamp},
        }
    except NameError:
        HW_LOGGER.error(
            'Данные для запроса к API не верны')
        raise NameError(
            'Потеряли данные, скоро найдем')

    try:
        response = requests.get(**data_for_api)
        if response.status_code != 200:
            HW_LOGGER.error(
                'Страница недоступна')
            raise local_exceptions.Not200Error(
                'Страница отвечает с кодом отличным от 200')
    except Exception as error:
        HW_LOGGER.error(
            f'ЛЮБОЙ ДРУГОЙ СБОЙ: {error}')
        raise local_exceptions.APIError(
            f'ЛЮБОЙ ДРУГОЙ СБОЙ: {error}')

    HW_LOGGER.debug('OK')
    return response.json()


def check_response(response):
    """Ответ API соответствует документации."""
    HW_LOGGER.debug(
        'Проверка ответа API')

    if not isinstance(response, dict):
        HW_LOGGER.error(
            'Ответ от API не словарь')
        raise TypeError(
            'Ответ от API не словарь')

    main_keys = [
        'homeworks',
        'current_date',
    ]
    for key in main_keys:
        if key not in response:
            HW_LOGGER.error(
                f'Нет ключа {key} в ответе API')
            raise KeyError(
                f'Потеряли ключ {key} в ответе API')

    homeworks = response.get('homeworks')

    if not isinstance(homeworks, list):
        HW_LOGGER.error(
            'Домашка это не список')
        raise TypeError(
            'Домашка это не список')

    HW_LOGGER.debug('OK')
    return homeworks


def parse_status(homework):
    """Статус домашней работы."""
    HW_LOGGER.debug(
        'Проверка статуса домашней работы')

    # Воюю с пайтестом, мне кажется логичнее эту часть прописать в функции выше
    # проверяем же, что документации соответствует ответ ответа
    try:
        homework_keys = [
            'id',
            'status',
            'homework_name',
            'reviewer_comment',
            'date_updated',
            'lesson_name',
        ]
        for key in homework_keys:
            if key not in homework:
                HW_LOGGER.error(
                    f'Нет ключа {key} в homeworks')
                raise KeyError(
                    f'Потеряли ключ {key} у домашки, ищем')
    except Exception:
        key == []
        if key in homework:
            HW_LOGGER.debug(
                'Домашек еще не отправляли на проверку')

    verdict_keys = [
        'approved',
        'reviewing',
        'rejected',
    ]
    for key in verdict_keys:
        if key not in HOMEWORK_VERDICTS:
            HW_LOGGER.error(
                f'Нет ключа {key} в HOMEWORK_VERDICTS')
            raise KeyError(
                f'Потеряли ключ {key}, скоро найдем')

    homework_name = homework.get('homework_name')
    status = homework.get('status')

    if homework_name not in homework.values():
        HW_LOGGER.error(
            f'Странное имя у работы: {homework_name}, нам такого не задавали!')
        raise local_exceptions.UnknownNameError(
            'Неизвестное имя у работы')

    if status not in HOMEWORK_VERDICTS.keys():
        HW_LOGGER.error(
            f'Непонятный статус у работы: {status}, срочно писать всем!!1!')
        raise local_exceptions.UnknownStatusError(
            f'Неизвестный статус у работы: {status}')

    verdict = HOMEWORK_VERDICTS.get(status)
    message = f'Изменился статус проверки работы "{homework_name}". {verdict}'

    HW_LOGGER.debug('OK')
    return message


def main():
    """Основная логика работы бота."""
    HW_LOGGER.debug(
        '--- beggining of file ---')

    if not check_tokens():
        sys.exit()

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
                HW_LOGGER.debug(
                    'Новых домашек/ошибок нет')
                continue

            message = parse_status(homeworks[0])

            if last_message is not message and error_message:
                send_message(bot, message)
                last_message = message
                timestamp = int(time.time())
            else:
                HW_LOGGER.debug(
                    'Это мы уже отправляли')

        except (
            local_exceptions.APIError,
            local_exceptions.UnknownNameError,
            local_exceptions.UnknownStatusError,
            local_exceptions.Not200Error,
            TypeError,
            KeyError,
            NameError,
        ) as error:

            if last_message is not error_message:
                error_message = f'Ошибка!! {error}'
                send_message(bot, error_message)
                last_message = error_message
                timestamp = int(time.time())
            else:
                HW_LOGGER.debug(
                    'Сообщение об ошибке уже отправляли')

        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
    HW_LOGGER.debug(
        '--- end of file ---')
