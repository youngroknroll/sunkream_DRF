import pytest


@pytest.mark.django_db
class TestCommonResponseFormat:
    def test_404오류는_공통에러형식을_반환한다(self, api_client, products_api, not_found_id):
        response = products_api.detail(api_client, not_found_id)
        assert response.status_code == 404
        data = response.json()
        assert data["code"] == "NOT_FOUND"
        assert "message" in data

    def test_미인증요청은_공통에러형식을_반환한다(self, api_client, me_api):
        response = me_api.orders(api_client)
        assert response.status_code == 401
        data = response.json()
        assert data["code"] == "UNAUTHORIZED"
        assert "message" in data
