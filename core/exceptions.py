from rest_framework.views import exception_handler
from rest_framework import status

ERROR_CODE_MAP = {
    status.HTTP_400_BAD_REQUEST: "INVALID_PARAMETER",
    status.HTTP_401_UNAUTHORIZED: "UNAUTHORIZED",
    status.HTTP_403_FORBIDDEN: "FORBIDDEN",
    status.HTTP_404_NOT_FOUND: "NOT_FOUND",
    status.HTTP_409_CONFLICT: "CONFLICT",
}


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is None:
        return response

    error_code = ERROR_CODE_MAP.get(response.status_code, "ERROR")

    if isinstance(response.data, dict):
        detail = response.data.get("detail", str(response.data))
    elif isinstance(response.data, list):
        detail = response.data[0] if response.data else "An error occurred."
    else:
        detail = str(response.data)

    response.data = {
        "code": error_code,
        "message": str(detail),
    }

    return response
