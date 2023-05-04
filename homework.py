"""Телеграм-бот для проверки статуса домашней работы."""
import logging
import os
import sys
import time
import requests
import telegram

from http import HTTPStatus
from requests import RequestException
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
    if None in (PRACTICUM_TOKEN, TELEGRAM_CHAT_ID, TELEGRAM_TOKEN):
        logger.critical("Один или несколько токенов не найдены.")
        sys.exit()
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
        if response.status_code != HTTPStatus.OK:
            raise ValueError(
                f'Эндпоин недоступен. Код ответа: {response.status_code}'
            )
        return response.json()
    except RequestException:
        logger.exception(f'Ошибка при запросе к эндпоинту {ENDPOINT}')


def check_response(response):
    """Проверка на корректность переданных данных."""
    if not isinstance(response, dict):
        raise TypeError('От API пришел не словарь.')
    homework = response.get('homeworks')
    if not isinstance(homework, list):
        raise TypeError('В ответе от API нет списка.')
    return True


def parse_status(homework):
    """Получение статуса проверки домашней работы."""
    if 'homework_name' not in homework:
        raise KeyError('Отсутствует ключ homework_name')
    homework_name = homework['homework_name']
    homework_status = homework['status']
    if homework_status not in HOMEWORK_VERDICTS:
        raise KeyError('Отсутствует ключ status')
    verdict = HOMEWORK_VERDICTS[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    call_check_tokens = check_tokens()
    if call_check_tokens is False:
        raise ValueError('Ошибка в константах с токенами.')
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    last_status = ''
    while True:
        try:
            response = get_api_answer(timestamp)
            homework = check_response(response)
            if homework:
                homework = response.get('homeworks')
                if len(homework) == 0:
                    try:
                        send_message(bot, 'Статус работы без изменений')
                    except telegram.TelegramError:
                        logger.error('Сообщение не отправлено')
                else:
                    print(homework)
                    status = parse_status(*homework)
                    if status != last_status:
                        try:
                            send_message(bot, status)
                        except telegram.TelegramError:
                            logger.error('Сообщение не отправленно.')
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
