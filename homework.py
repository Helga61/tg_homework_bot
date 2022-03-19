import json
import logging
import os
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv
from requests.exceptions import RequestException

from exceptions import NotTokenError, RequestExceptionError, StatusCodeError

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
TOKENS = ['PRACTICUM_TOKEN', 'TELEGRAM_TOKEN', 'TELEGRAM_CHAT_ID']

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logging.basicConfig(
    level=logging.DEBUG,
    filename='journal.log',
    filemode='w',
    format='%(asctime)s - %(levelname)s - %(message)s - %(name)s'
)
logger = logging.getLogger(__name__)
logger.addHandler(
    logging.StreamHandler()
)


def send_message(bot, message):
    """Отправляет сообщение в Телеграмм."""
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logger.info('Сообщение отправлено')
    except telegram.TelegramError as telegram_error:
        logger.error(
            f'Сообщение не отправлено: {telegram_error}')


def get_api_answer(current_timestamp):
    """Отправляет запрос к API."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        response = requests.get(url=ENDPOINT, headers=HEADERS, params=params)
        if response.status_code != HTTPStatus.OK:
            logger.error(f'Ресурс недоступен, ответ {response.status_code}')
            raise StatusCodeError(
                f'Ресурс недоступен, ответ {response.status_code}'
            )
        return response.json()
    except RequestException as error:
        logger.error(f'ошибка подключения {error}')
        raise RequestExceptionError(f'ошибка подключения {error}')
    except json.JSONDecodeError as value_error:
        logger.error(f'Код ответа API (ValueError): {value_error}')
        raise json.JSONDecodeError(
            f'Код ответа API (ValueError): {value_error}'
        )


def check_response(response):
    """Проверяет данные ответа API."""
    if type(response) is not dict:
        logger.error('Неверный тип данных')
        raise TypeError('Неверный тип данных')
    if 'homeworks' not in response:
        logger.error('Отсутствует ожидаемый ключ "homeworks"')
        raise KeyError('Отсутствует ожидаемый ключ "homeworks"')
    if 'current_date' not in response:
        logger.error('Отсутствует ожидаемый ключ "current_date"')
        raise KeyError('Отсутствует ожидаемый ключ "current_date"')
    homeworks = response['homeworks']
    if type(homeworks) is not list:
        logger.error(
            'Неверный тип данных: ключ "homeworks" '
            'должен содержать список'
        )
        raise TypeError(
            'Неверный тип данных: ключ "homeworks" '
            'должен содержать список'
        )
    return homeworks


def parse_status(homework):
    """Отслеживание статуса домашней работы."""
    if 'homework_name' not in homework:
        logger.error('Отсутствует ожидаемый ключ "homework_name"')
        raise KeyError('Отсутствует ожидаемый ключ "homework_name"')
    homework_name = homework.get('homework_name')
    if homework_name is None or homework_name == '':
        logger.error('Отсутствует название работы')
        raise ValueError('Отсутствует название работы')
    homework_status = homework.get('status')
    if homework_status not in HOMEWORK_STATUSES:
        logger.error('Неизвестный статус работы')
        raise KeyError('Неизвестный статус работы')
    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверка наличия токенов."""
    tokens_bool = True
    for name in TOKENS:
        if globals()[name] is None:
            logger.critical(f'Не найден токен {name}')
            tokens_bool = False
    return tokens_bool


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logger.critical('Проверьте наличие всех токенов')
        raise NotTokenError('Проверьте наличие всех токенов')
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    status_homework = None
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            current_status = homeworks[0].get('status')
            if len(homeworks) == 0:
                logger.info('Работа пока не принята на проверку')
            if status_homework != current_status:
                send_message(bot, parse_status(homeworks[0]))
                status_homework = current_status
            else:
                logger.debug('Пока без изменений')
            current_timestamp = response['current_date']
            time.sleep(RETRY_TIME)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
