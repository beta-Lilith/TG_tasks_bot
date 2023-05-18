class UnknownStatusError(Exception):
    """Неизвестный статус домашки."""

    ...


class UnknownNameError(Exception):
    """Неизвестное имя домашки."""

    ...


class Not200Error(Exception):
    """Не 200."""

    ...


class APIError(Exception):
    """ЛЮБОЙ ДРУГОЙ СБОЙ :'D."""

    ...
