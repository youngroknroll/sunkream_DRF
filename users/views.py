import requests
from django.contrib.auth import get_user_model
from rest_framework import permissions
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from core.responses import success_response
from users.serializers import KakaoLoginSerializer

User = get_user_model()

KAKAO_USER_INFO_URL = "https://kapi.kakao.com/v2/user/me"


class KakaoLoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = KakaoLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        kakao_token = serializer.validated_data["access_token"]

        kakao_response = requests.get(
            KAKAO_USER_INFO_URL,
            headers={"Authorization": f"Bearer {kakao_token}"},
            timeout=5,
        )

        if kakao_response.status_code != 200:
            raise AuthenticationFailed("Invalid Kakao token.")

        kakao_data = kakao_response.json()
        kakao_id = str(kakao_data["id"])
        kakao_account = kakao_data.get("kakao_account", {})
        email = kakao_account.get("email", f"{kakao_id}@kakao.user")
        nickname = kakao_account.get("profile", {}).get("nickname", "")

        user, created = User.objects.get_or_create(
            kakao_id=kakao_id,
            defaults={"email": email, "name": nickname},
        )

        refresh = RefreshToken.for_user(user)

        return success_response(data={
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "is_new_user": created,
        })
