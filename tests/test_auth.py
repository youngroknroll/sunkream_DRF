import pytest
from django.contrib.auth import get_user_model

User = get_user_model()

KAKAO_LOGIN_URL = "/api/v1/auth/kakao/"


@pytest.mark.django_db
class TestKakaoLoginAPI:
    def test_login_missing_token_returns_400(self, api_client):
        response = api_client.post(KAKAO_LOGIN_URL, {})
        assert response.status_code == 400

    def test_login_new_user_creates_account(self, mock_kakao_success, api_client):
        response = api_client.post(KAKAO_LOGIN_URL, {"access_token": "valid_kakao_token"})
        assert response.status_code == 200
        data = response.json()["data"]
        assert "access" in data
        assert "refresh" in data

        user = User.objects.get(kakao_id="123456789")
        assert user.email == "kakao@example.com"
        assert user.name == "KakaoUser"

    def test_login_existing_user_returns_tokens(self, mock_kakao_success, api_client):
        User.objects.create_user(
            email="kakao@example.com",
            kakao_id="123456789",
            name="OldName",
        )
        response = api_client.post(KAKAO_LOGIN_URL, {"access_token": "valid_kakao_token"})
        assert response.status_code == 200
        data = response.json()["data"]
        assert "access" in data

    def test_login_invalid_kakao_token(self, mock_kakao_fail, api_client):
        response = api_client.post(KAKAO_LOGIN_URL, {"access_token": "invalid_token"})
        assert response.status_code == 401
        assert response.json()["code"] == "UNAUTHORIZED"
