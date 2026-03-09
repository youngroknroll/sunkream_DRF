import pytest
from django.contrib.auth import get_user_model

from tests.factories import UserFactory

User = get_user_model()


@pytest.mark.django_db
class TestKakaoLoginAPI:
    def test_카카오로그인_토큰이_없으면_400을_반환한다(self, api_client, auth_api, make_kakao_login_payload):
        response = auth_api.kakao_login(api_client, make_kakao_login_payload())
        assert response.status_code == 400

    def test_카카오로그인_신규유저면_토큰을_반환한다(
        self, mock_kakao_success, api_client, auth_api, make_kakao_login_payload, kakao_access_token,
    ):
        response = auth_api.kakao_login(api_client, make_kakao_login_payload(kakao_access_token))
        assert response.status_code == 200
        data = response.json()["data"]
        assert "access" in data
        assert "refresh" in data

    def test_카카오로그인_신규유저면_계정을_생성한다(
        self, mock_kakao_success, api_client, auth_api, make_kakao_login_payload, kakao_access_token,
    ):
        auth_api.kakao_login(api_client, make_kakao_login_payload(kakao_access_token))

        user = User.objects.get(kakao_id="123456789")
        assert user.email == "kakao@example.com"
        assert user.name == "KakaoUser"

    def test_카카오로그인_기존유저면_토큰을_반환한다(
        self, mock_kakao_success, api_client, auth_api, make_kakao_login_payload, kakao_access_token,
    ):
        UserFactory(email="kakao@example.com", kakao_id="123456789", name="OldName")
        response = auth_api.kakao_login(api_client, make_kakao_login_payload(kakao_access_token))
        assert response.status_code == 200
        data = response.json()["data"]
        assert "access" in data

    def test_카카오로그인_이메일이_같은_기존유저가_있으면_카카오_계정을_연동한다(
        self, mock_kakao_success, api_client, auth_api, make_kakao_login_payload, kakao_access_token,
    ):
        existing = UserFactory(email="kakao@example.com", kakao_id=None)
        response = auth_api.kakao_login(api_client, make_kakao_login_payload(kakao_access_token))

        assert response.status_code == 200
        existing.refresh_from_db()
        assert existing.kakao_id == "123456789"
        assert response.json()["data"]["is_new_user"] is False

    def test_카카오로그인_이메일이_다른_카카오계정에_연결되어있으면_409를_반환한다(
        self, mock_kakao_success, api_client, auth_api, make_kakao_login_payload, kakao_access_token,
        assert_api_error,
    ):
        UserFactory(email="kakao@example.com", kakao_id="999999")
        response = auth_api.kakao_login(api_client, make_kakao_login_payload(kakao_access_token))

        assert_api_error(response, 409, "CONFLICT")

    def test_카카오로그인_유효하지않은_토큰이면_401을_반환한다(
        self, mock_kakao_fail, api_client, auth_api, make_kakao_login_payload, invalid_kakao_access_token,
    ):
        response = auth_api.kakao_login(api_client, make_kakao_login_payload(invalid_kakao_access_token))
        assert response.status_code == 401
        assert response.json()["code"] == "UNAUTHORIZED"

    def test_카카오로그인_네트워크오류면_401을_반환한다(
        self, mock_kakao_network_error, api_client, auth_api, make_kakao_login_payload, kakao_access_token,
    ):
        response = auth_api.kakao_login(api_client, make_kakao_login_payload(kakao_access_token))
        assert response.status_code == 401
        assert response.json()["code"] == "UNAUTHORIZED"


@pytest.mark.django_db
class TestTokenRefreshAPI:
    def test_토큰갱신_유효한_리프레시토큰이면_새_액세스토큰을_반환한다(
        self, mock_kakao_success, api_client, auth_api, make_kakao_login_payload, kakao_access_token,
    ):
        login_response = auth_api.kakao_login(api_client, make_kakao_login_payload(kakao_access_token))
        refresh_token = login_response.json()["data"]["refresh"]

        response = auth_api.token_refresh(api_client, refresh_token)
        assert response.status_code == 200
        assert "access" in response.json()

    def test_토큰갱신_유효하지않은_리프레시토큰이면_401을_반환한다(
        self, api_client, auth_api,
    ):
        response = auth_api.token_refresh(api_client, "invalid-refresh-token")
        assert response.status_code == 401
