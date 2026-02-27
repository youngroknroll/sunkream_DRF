from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from tests.factories import BiddingFactory, ProductSizeFactory, UserFactory

User = get_user_model()

_MOCK_KAKAO_USER_INFO = {
    "id": 123456789,
    "kakao_account": {
        "email": "kakao@example.com",
        "profile": {
            "nickname": "KakaoUser",
        },
    },
}


@pytest.fixture
def user(db):
    return User.objects.create_user(
        email="test@example.com",
        password="testpass123",
        name="Test User",
    )


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def authenticated_client(api_client, user):
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def seller(db):
    return UserFactory(email="seller@example.com")


@pytest.fixture
def seller_client(seller):
    client = APIClient()
    client.force_authenticate(user=seller)
    return client


@pytest.fixture
def product_size(db):
    return ProductSizeFactory()


@pytest.fixture
def sell_bid(seller, product_size):
    return BiddingFactory(user=seller, product_size=product_size, position="SELL")


@pytest.fixture
def buy_bid(user, product_size):
    return BiddingFactory(user=user, product_size=product_size, position="BUY")


@pytest.fixture
def own_sell_bid(user, product_size):
    return BiddingFactory(user=user, product_size=product_size, position="SELL")


@pytest.fixture
def mock_kakao_success():
    def _handler(url, **kwargs):
        class MockResponse:
            status_code = 200

            def json(self):
                return _MOCK_KAKAO_USER_INFO

        return MockResponse()

    with patch("users.views.requests.get", side_effect=_handler):
        yield


@pytest.fixture
def mock_kakao_fail():
    def _handler(url, **kwargs):
        class MockResponse:
            status_code = 401

            def json(self):
                return {"msg": "this access token does not exist", "code": -401}

        return MockResponse()

    with patch("users.views.requests.get", side_effect=_handler):
        yield
