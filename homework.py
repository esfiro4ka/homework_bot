import logging
import os
import sys
import time
from http import HTTPStatus
from json import JSONDecodeError

import requests
import telegram
from dotenv import load_dotenv

from exceptions import (APIErrorException, JSONDecodeException,
                        NegativeStatusCodeException, NoHomeworkException,
                        NoHomeworkStatusException, NoMessageException,
                        UnknownHomeworkStatusException)

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

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

HOMEWORKS_KEY = 'homeworks'
CURRENT_DATE_KEY = 'current_date'


def check_tokens():
    """Проверяет доступность переменных окружения."""
    return all((TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, PRACTICUM_TOKEN))


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
                                         params={'from_date': timestamp})
        if homework_statuses.status_code == HTTPStatus.OK:
            return homework_statuses.json()
        raise NegativeStatusCodeException('Код API, отличный от 200.')
    except JSONDecodeError:
        raise JSONDecodeException('Ошибка преобразования JSON.')
    except Exception as error:
        raise APIErrorException(f'Ошибка при запросе к API: {error}.')


def check_response(response):
    """Проверяет ответ API на соответствие документации."""
    if not isinstance(response, dict):
        raise TypeError('Ответ API должен быть словарем!')
    if HOMEWORKS_KEY not in response:
        raise TypeError('В ответе API нет ключа "homeworks"!')
    if not isinstance(response.get(HOMEWORKS_KEY), list):
        raise TypeError('В ответе под ключом "homeworks" должен быть список!')
    if CURRENT_DATE_KEY not in response:
        raise TypeError('В ответе API нет ключа "current_date"!')


def parse_status(homework):
    """Извлекает из информации о конкретной домашней работе ее статус."""
    homework_name = homework.get('homework_name')
    if not homework_name:
        raise NoHomeworkException('Нет домашнего задания за выбранный период.')
    status = homework.get('status')
    if not status:
        raise NoHomeworkStatusException('У домашнего задания нет статуса.')
    verdict = HOMEWORK_VERDICTS.get(status)
    if not verdict:
        raise UnknownHomeworkStatusException('Статус задания неизвестен.')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        message = 'Отсутствуют переменные окружения.'
        logger.critical(message)
        sys.exit(message)
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    status = ''
    timestamp = int(time.time())
    while True:
        try:
            response = get_api_answer(timestamp)
            check_response(response)
            timestamp = response.get(CURRENT_DATE_KEY)
            current_status = status
            status = parse_status(response.get(HOMEWORKS_KEY)[0])
            if current_status != status:
                send_message(bot, status)
            else:
                logger.debug('В ответе API нет новых статусов')
        except Exception as error:
            message = f'Сбой в работе программы: {error}.'
            logger.error(message)
            send_message(bot, message)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
