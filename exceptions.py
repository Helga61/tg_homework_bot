class StatusCodeError(Exception):
    """Код ответа сервера не 200."""

    pass


class RequestExceptionError(Exception):
    """Ошибка в запросе."""

    pass


class NotTokenError(Exception):
    """Ошибка токена."""

    pass


class NotCheckHomeworkError(Exception):
    """Список проверяемых работ пуст."""

    pass
