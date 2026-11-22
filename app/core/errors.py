"""Domain errors raised by the service layer.

Services stay free of HTTP details: they raise one of these, and the handler
registered in ``app.main`` turns it into a JSON response ``{"detail": ...}``.
"""


class AppError(Exception):
    status_code = 400

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class BadRequestError(AppError):
    status_code = 400


class UnauthorizedError(AppError):
    status_code = 401


class ForbiddenError(AppError):
    status_code = 403


class NotFoundError(AppError):
    status_code = 404


class ConflictError(AppError):
    status_code = 409


class PayloadTooLargeError(AppError):
    status_code = 413


class TooManyRequestsError(AppError):
    """Asked again too soon (e.g. another sign-up code within a minute)."""

    status_code = 429


class BadGatewayError(AppError):
    """An outside service (e.g. the payment provider) failed or could not be reached."""

    status_code = 502
