class MissingEnvironmentVariableError(Exception):
    """Исключение при отсутствии обязательных переменных окружения."""


class InvalidResponseCodeError(Exception):
    """Исключение при неверном коде ответа API."""
