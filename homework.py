"""Телеграм-бот для проверки статуса домашней работы."""
import logging
import os
import sys
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv
from requests.exceptions import RequestException

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=(
        logging.StreamHandler(sys.stdout),
    )
)

logger = logging.getLogger(__name__)


def check_tokens():
    """Проверка данных в константах."""
    tokens_are_missing = False
    for token_name in ('PRACTICUM_TOKEN',
                       'TELEGRAM_CHAT_ID',
                       'TELEGRAM_TOKEN'):
        if not globals().get(token_name):
            tokens_are_missing = True
            logger.error(f"Отсутствует {token_name}")
    if tokens_are_missing:
        logger.critical('Не найдены некоторые токены,'
                        ' программа будет завершена.')
        exit()
    logger.info("Все токены найдены.")


def send_message(bot, message):
    """Отправка сообщения в телеграм."""
    bot.send_message(TELEGRAM_CHAT_ID, message)
    logger.debug(f'Отправлено сообщение: {message}')


def get_api_answer(timestamp):
    """Получение информации от Практикума."""
    timestamp = int(time.time())
    try:
        response = requests.get(ENDPOINT,
                                headers=HEADERS,
                                params={'from_date': timestamp})
        response.raise_for_status()
        if response.status_code == HTTPStatus.OK:
            return response.json()
    except RequestException as error:
        logger.error(f'Ошибка: {error}')
    raise ValueError('Не удалось получить ответ от API')


def check_response(response):
    """Проверка на корректность переданных данных."""
    if not isinstance(response, dict):
        raise TypeError('От API пришел не словарь.')
    homework = response.get('homeworks')
    if not isinstance(homework, list):
        raise TypeError('В ответе от API нет списка.')


def parse_status(homework):
    """Получение статуса проверки домашней работы."""
    for required_key in ['homework_name', 'status']:
        if required_key not in homework:
            raise KeyError(f'Отсутствует ключ {required_key}')
    homework_name = homework['homework_name']
    homework_status = homework['status']
    if homework_status not in HOMEWORK_VERDICTS:
        raise KeyError('Отсутствует ключ status')
    verdict = HOMEWORK_VERDICTS[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    check_tokens()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    last_status = []
    while True:
        try:
            response = get_api_answer(timestamp)
            check_response(response)
            homeworks = response.get('homeworks')
            if not homeworks:
                send_message(bot, 'Статус работы без изменений')
            else:
                homework, *_ = homeworks
                status = parse_status(homework)
                if status != last_status:
                    send_message(bot, status)
        except telegram.TelegramError as error:
            logger.error(f'Сообщение не отправлено. Ошибка: {error}')
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
            logger.error(message)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
