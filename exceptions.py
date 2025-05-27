
class MissingEnvironmentVariableError(Exception):
    """Исключение при отсутствии обязательных переменных окружения."""

    def __init__(self, missing):
        message = f'Отсутствуют обязательные переменные окружения: {", ".join(missing)}'
        super().__init__(message)
        self.missing = missing


class InvalidResponseCodeError(Exception):
    """Исключение при неверном коде ответа API."""

    pass
