from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from users.views import KakaoLoginView

urlpatterns = [
    path("kakao/", KakaoLoginView.as_view(), name="kakao-login"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
]
