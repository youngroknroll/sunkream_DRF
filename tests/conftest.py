import pytest
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(
        email="test@example.com",
        password="testpass123",
        name="Test User",
    )


@pytest.fixture
def api_client():
    from rest_framework.test import APIClient

    return APIClient()


@pytest.fixture
def authenticated_client(api_client, user):
    api_client.force_authenticate(user=user)
    return api_client
