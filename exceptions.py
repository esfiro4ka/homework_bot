class NoMessageException(Exception):
    """Сбой при отправке сообщения в Telegram."""


class NegativeStatusCodeException(Exception):
    """API возвращает код, отличный от 200."""


class JSONDecodeException(Exception):
    """Ошибка преобразования JSON."""


class APIErrorException(Exception):
    """Ошибка при запросе к основному API."""


class NoHomeworkException(Exception):
    """Нет домашнего задания за выбранный период."""


class NoHomeworkStatusException(Exception):
    """У домашнего задания нет статуса."""


class UnknownHomeworkStatusException(Exception):
    """Статус домашнего задания неизвестен."""
