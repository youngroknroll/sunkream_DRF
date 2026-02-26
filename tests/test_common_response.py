import pytest
from rest_framework.test import APIClient


@pytest.mark.django_db
class TestCommonResponseFormat:
    def test_404_returns_unified_error_format(self, api_client):
        response = api_client.get("/api/v1/products/99999/")
        assert response.status_code == 404
        data = response.json()
        assert data["code"] == "NOT_FOUND"
        assert "message" in data

    def test_unauthenticated_returns_unified_error(self, api_client):
        response = api_client.get("/api/v1/me/orders/")
        assert response.status_code == 401
        data = response.json()
        assert data["code"] == "UNAUTHORIZED"
        assert "message" in data
