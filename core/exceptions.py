from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.views import exception_handler

ERROR_CODE_MAP = {
    status.HTTP_400_BAD_REQUEST: "INVALID_PARAMETER",
    status.HTTP_401_UNAUTHORIZED: "UNAUTHORIZED",
    status.HTTP_403_FORBIDDEN: "FORBIDDEN",
    status.HTTP_404_NOT_FOUND: "NOT_FOUND",
    status.HTTP_409_CONFLICT: "CONFLICT",
}


class ConflictError(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "Resource conflict."
    default_code = "conflict"


class ForbiddenError(APIException):
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = "Permission denied."
    default_code = "forbidden"


class InsufficientPointError(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Insufficient points."
    default_code = "insufficient_point"


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is None:
        return response

    error_code = "INSUFFICIENT_POINT" if isinstance(exc, InsufficientPointError) else ERROR_CODE_MAP.get(response.status_code, "ERROR")
    data = response.data

    if isinstance(data, list):
        detail = data[0]
    elif isinstance(data, dict) and "detail" in data:
        detail = data["detail"]
    elif isinstance(data, dict):
        first_errors = next(iter(data.values()))
        detail = first_errors[0] if isinstance(first_errors, list) else str(first_errors)
    else:
        detail = str(data)

    response.data = {"code": error_code, "message": str(detail)}

    return response
