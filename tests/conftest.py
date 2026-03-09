from unittest.mock import patch

import pytest
import requests
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from orders.models import Order
from tests.factories import BiddingFactory, ProductFactory, ProductSizeFactory, UserFactory

User = get_user_model()
NOT_FOUND_ID = 99999
VALID_KAKAO_ACCESS_TOKEN = "valid_kakao_token"
INVALID_KAKAO_ACCESS_TOKEN = "invalid_token"
KAKAO_LOGIN_URL = "/api/v1/auth/kakao/"
TOKEN_REFRESH_URL = "/api/v1/auth/token/refresh/"
BIDS_URL = "/api/v1/bids/"
ORDERS_URL = "/api/v1/orders/"
MY_ORDERS_URL = "/api/v1/me/orders/"
PRODUCTS_URL = "/api/v1/products/"
BRANDS_URL = "/api/v1/products/brands/"

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
def make_bid_data(product_size):
    def _build(**overrides):
        data = {
            "product_size_id": product_size.id,
            "position": "BUY",
            "price": 300000,
        }
        data.update(overrides)
        return data

    return _build


@pytest.fixture
def not_found_id():
    return NOT_FOUND_ID


@pytest.fixture
def kakao_access_token():
    return VALID_KAKAO_ACCESS_TOKEN


@pytest.fixture
def invalid_kakao_access_token():
    return INVALID_KAKAO_ACCESS_TOKEN


@pytest.fixture
def make_kakao_login_payload():
    def _build(access_token=None):
        if access_token is None:
            return {}
        return {"access_token": access_token}

    return _build


@pytest.fixture
def bid_data(make_bid_data):
    return make_bid_data()


@pytest.fixture
def make_order_payload():
    def _build(bidding_id):
        return {"bidding_id": bidding_id}

    return _build


@pytest.fixture
def assert_api_error():
    def _assert(response, status, code, message=None):
        assert response.status_code == status
        data = response.json()
        assert data["code"] == code
        if message is not None:
            assert data["message"] == message

    return _assert


@pytest.fixture
def auth_api():
    class AuthAPI:
        kakao_login_url = KAKAO_LOGIN_URL
        token_refresh_url = TOKEN_REFRESH_URL

        def kakao_login(self, client, payload):
            return client.post(self.kakao_login_url, payload)

        def token_refresh(self, client, refresh_token):
            return client.post(self.token_refresh_url, {"refresh": refresh_token})

    return AuthAPI()


@pytest.fixture
def bids_api():
    class BidsAPI:
        bids_url = BIDS_URL

        def create(self, client, payload):
            return client.post(self.bids_url, payload)

        def list_my(self, client):
            return client.get(self.bids_url)

    return BidsAPI()


@pytest.fixture
def orders_api(make_order_payload):
    class OrdersAPI:
        orders_url = ORDERS_URL

        def create(self, client, bidding_id):
            return client.post(self.orders_url, make_order_payload(bidding_id))

    return OrdersAPI()


@pytest.fixture
def me_api():
    class MeAPI:
        my_orders_url = MY_ORDERS_URL

        def orders(self, client):
            return client.get(self.my_orders_url)

    return MeAPI()


@pytest.fixture
def products_api():
    class ProductsAPI:
        products_url = PRODUCTS_URL
        brands_url = BRANDS_URL

        def list(self, client, params=None):
            return client.get(self.products_url, params)

        def detail(self, client, product_id):
            return client.get(f"{self.products_url}{product_id}/")

        def price_history(self, client, product_id):
            return client.get(f"{self.products_url}{product_id}/price-history/")

        def brands(self, client):
            return client.get(self.brands_url)

        def add_wishlist(self, client, product_id):
            return client.post(f"{self.products_url}{product_id}/wishlist/")

        def remove_wishlist(self, client, product_id):
            return client.delete(f"{self.products_url}{product_id}/wishlist/")

    return ProductsAPI()


@pytest.fixture
def product(db):
    return ProductFactory()


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
def contracted_sell_bid(user, seller, sell_bid):
    sell_bid.status = "CONTRACTED"
    sell_bid.save(update_fields=["status"])
    Order.objects.create(
        bidding=sell_bid, buyer=user, seller=seller, price=sell_bid.price,
    )
    return sell_bid


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
def mock_kakao_network_error():
    with patch(
        "users.views.requests.get",
        side_effect=requests.ConnectionError("Connection refused"),
    ):
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
