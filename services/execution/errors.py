from __future__ import annotations


class ExecutionError(Exception):
    pass


class ConfigError(ExecutionError):
    pass


class PositionModeMismatchError(ExecutionError):
    pass


class ExchangeParamValidationError(ExecutionError):
    pass


class OrderRejectedError(ExecutionError):
    pass


class RateLimitError(ExecutionError):
    pass


class TemporaryNetworkError(ExecutionError):
    pass
