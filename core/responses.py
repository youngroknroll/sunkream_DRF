from rest_framework.response import Response
from rest_framework import status


def success_response(data=None, message="success", status_code=status.HTTP_200_OK):
    return Response(
        {"code": "OK", "message": message, "data": data},
        status=status_code,
    )
