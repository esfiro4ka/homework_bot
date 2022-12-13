import logging
import os
import sys
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

from exceptions import (APIErrorException, NegativeStatusCodeException,
                        NoHomeworkException, NoHomeworkStatusException,
                        NoMessageException, UnknownHomeworkStatusException)

load_dotenv()


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(sys.stdout)
logger.addHandler(handler)
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
handler.setFormatter(formatter)

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
PAYLOAD = {'from_date': int(time.time())}

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Проверяет доступность переменных окружения."""
    tokens = [TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, PRACTICUM_TOKEN]
    return all(tokens)


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.debug('Удачная отправка сообщения в Telegram.')
    except Exception:
        logger.error('Сбой при отправке сообщения в Telegram.')
        raise NoMessageException('Сбой при отправке сообщения в Telegram.')


def get_api_answer(timestamp):
    """Делает запрос к эндпоинту API-сервиса."""
    try:
        homework_statuses = requests.get(ENDPOINT,
                                         headers=HEADERS,
                                         params=PAYLOAD)
        if homework_statuses.status_code == HTTPStatus.OK:
            homework = homework_statuses.json()
            return homework
        else:
            raise NegativeStatusCodeException('Код API, отличный от 200.')
    except Exception as error:
        raise APIErrorException(f'Ошибка при запросе к API: {error}.')


def check_response(response):
    """Проверяет ответ API на соответствие документации."""
    if not isinstance(response, dict):
        raise TypeError('Ответ API должен быть словарем!')
    if 'homeworks' not in response:
        raise TypeError('В ответе API нет ключа "homeworks"!')
    if not isinstance(response['homeworks'], list):
        raise TypeError('В ответе под ключом "homeworks" должен быть список!')
    if response['homeworks'][0]['status'] not in HOMEWORK_VERDICTS.keys():
        raise TypeError('В ответе API отсутствуют ожидаемые ключи!')


def parse_status(homework):
    """Извлекает из информации о конкретной домашней работе ее статус."""
    homework_name = homework.get('homework_name')
    if not homework_name:
        raise NoHomeworkException('Нет домашнего задания за выбранный период.')
    status = homework.get('status')
    if not status:
        raise NoHomeworkStatusException('У домашнего задания нет статуса.')
    try:
        verdict = HOMEWORK_VERDICTS[status]
    except KeyError:
        raise UnknownHomeworkStatusException('Статус задания неизвестен.')
    message = f'Изменился статус проверки работы "{homework_name}". {verdict}'
    return message


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        message = ('Отсутствуют переменные окружения.')
        logger.critical(message)
        sys.exit(message)
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    status = ''
    while True:
        try:
            timestamp = int(time.time())
            response = get_api_answer(timestamp)
            check_response(response)
            current_status = status
            status = parse_status(response.get('homeworks')[0])
            if current_status != status:
                send_message(bot, status)
            else:
                logger.debug('В ответе API нет новых статусов')
        except Exception as error:
            message = f'Сбой в работе программы: {error}.'
            logger.error(message)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
