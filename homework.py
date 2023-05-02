"""Телеграм-бот для проверки статуса домашней работы."""
import logging
import os
import sys
import time

from http import HTTPStatus
from requests import RequestException
import requests
import telegram
from dotenv import load_dotenv

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
    tokens = {
        'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
        'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID,
        'TELEGRAM_TOKEN': TELEGRAM_TOKEN}
    for token, value in tokens.items():
        if value is None:
            logger.critical(f'{token} не найден.')
            sys.exit()
    return all(tokens.values())


def send_message(bot, message):
    """Отправка сообщения в телеграм."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.debug(f'Отправлено сообщение: {message}')
    except telegram.TelegramError:
        logger.error('Сообщение не отправлено')


def get_api_answer(timestamp):
    """Получение информации от Практикума."""
    timestamp = int(time.time())
    try:
        response = requests.get(ENDPOINT,
                                headers=HEADERS,
                                params={'from_date': timestamp})
        if response.status_code != HTTPStatus.OK:
            raise AssertionError(
                f'Эндпоин недоступен. Код ответа: {response.status_code}'
            )
        try:
            return response.json()
        except ValueError:
            logger.error('Ошибка преобразования к типам данный Python')
    except RequestException:
        logger.exception(f'Ошибка при запросе к эндпоинту {ENDPOINT}')


def check_response(response):
    """Проверка на корректность переданных данных."""
    if not isinstance(response, dict):
        raise TypeError('От API пришел не словарь.')
    homework = response.get('homeworks')
    if not isinstance(homework, list):
        raise TypeError('В ответе от API нет списка.')
    return homework[0]


def parse_status(homework):
    """Получение статуса проверки домашней работы."""
    if not isinstance(homework, dict):
        raise TypeError('После проверки ответа пришел не словарь')
    try:
        homework_name = homework['homework_name']
        homework_status = homework['status']
        verdict = HOMEWORK_VERDICTS[homework_status]
        if homework_status not in HOMEWORK_VERDICTS:
            raise KeyError(f'Ошибка {homework_status}')
        elif homework_name is None:
            raise Exception('Ошибка ответа')
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'
    except KeyError as error:
        logging.error(f'Ошибка {error}')

    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        raise Exception('Ошибка в константах с токенами.')
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    last_status = ''
    while True:
        try:
            response = get_api_answer(timestamp)
            homework = check_response(response)
            if homework:
                status = parse_status(homework)
                if status != last_status:
                    send_message(bot, status)
            else:
                message = 'Статус работы без изменений'
                logger.error(message)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
            logger.error(message)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
