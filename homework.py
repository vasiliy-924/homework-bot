import logging
import os
import sys
import time
from http import HTTPStatus

import requests
from dotenv import load_dotenv
from telebot import TeleBot

from exceptions import (
    InvalidResponseCodeError,
    MissingEnvironmentVariableError
)

logging.basicConfig(
    level=logging.DEBUG,
    format=(
        '%(asctime)s - [%(levelname)s] - '
        '%(funcName)s:%(lineno)d - %(message)s'
    ),
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(
            f'{__file__}.log',
            encoding='utf-8'
        )
    ]
)
logger = logging.getLogger(__name__)

load_dotenv()
PRACTICUM_TOKEN = os.getenv('PRACTICUM_SECRET_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_SECRET_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_USER_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens() -> bool:
    """Проверяет доступность переменных окружения."""
    tokens = {
        'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
        'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
        'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID
    }
    missing = [name for name, value in tokens.items() if not value]

    if missing:
        logger.critical(
            'Отсутствуют обязательные переменные окружения: %s',
            ', '.join(missing)
        )
        raise MissingEnvironmentVariableError(missing)


def send_message(bot: TeleBot, message: str) -> bool:
    """Отправляет сообщение в Telegram-чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except Exception as error:
        logger.error(f'Ошибка при отправке сообщения: {error}')
        return False
    logger.debug(f'Сообщение отправлено: {message}')
    return True


def get_api_answer(timestamp: int) -> dict:
    """Выполняет запрос к API Яндекс.Практикума."""
    request_params = {
        'url': ENDPOINT,
        'headers': HEADERS,
        'params': {'from_date': timestamp}
    }

    logger.info(
        'Запрос к API: {url} с заголовками {headers} и параметрами {params}'
        .format(**request_params)
    )

    try:
        response = requests.get(**request_params)

    except requests.exceptions.RequestException as error:
        raise ConnectionError(
            (
                'Ошибка подключения к API: {error}. '
                'URL: {url}, заголовки: {headers}, параметры: {params}'
            ).format(error=error, **request_params)
        ) from error

    if response.status_code != HTTPStatus.OK:
        raise InvalidResponseCodeError(
            'Неверный код ответа API: {}. Причина: {}. Текст: {}'
            .format(
                response.status_code,
                response.reason,
                response.text
            )
        )

    return response.json()


def check_response(response: dict) -> list:
    """Проверяет корректность ответа API."""
    if not isinstance(response, dict):
        raise TypeError('Ответ API не является словарем')
    if 'homeworks' not in response:
        raise KeyError('Отсутствует обязательный ключ homeworks в ответе API')
    homeworks = response['homeworks']
    if not isinstance(homeworks, list):
        raise TypeError('homeworks не является списком')
    return homeworks


def parse_status(homework: dict) -> str:
    """Извлекает статус конкретной домашней работы."""
    homework_name = homework.get('homework_name')
    status = homework.get('status')

    if not homework_name:
        raise KeyError('Отсутствует ключ homework_name')
    if status not in HOMEWORK_VERDICTS:
        raise ValueError(f'Неожиданный статус домашней работы: {status}')

    verdict = HOMEWORK_VERDICTS[status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main() -> None:
    """Основная логика работы бота."""
    try:
        check_tokens()
    except MissingEnvironmentVariableError as error:
        sys.exit(
            'Программа принудительно остановлена: {}'.format(error)
        )

    bot = TeleBot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    last_message = ''

    while True:
        try:
            response = get_api_answer(timestamp)
            homeworks = check_response(response)

            if not homeworks:
                logger.debug('Нет новых статусов')
                continue

            homework = homeworks[0]
            message = parse_status(homework)

            if message != last_message and send_message(bot, message):
                last_message = message
                timestamp = response.get('current_date', timestamp)

        except Exception as error:
            message = 'Сбой в работе программы: {}'.format(error)
            logger.exception(message)
            if message != last_message and send_message(bot, message):
                last_message = message

        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
