import pytest
from django.contrib.auth import get_user_model

from tests.factories import ProductFactory, ProductSizeFactory, SizeFactory, UserFactory

User = get_user_model()


@pytest.fixture
def product_size(db):
    return ProductSizeFactory()


@pytest.fixture
def seller(db):
    return UserFactory(email="seller@example.com")


@pytest.fixture
def buyer_client(api_client, user):
    api_client.force_authenticate(user=user)
    return api_client


@pytest.mark.django_db
class TestBidCreateAPI:
    URL = "/api/v1/bids/"

    def test_create_bid_requires_auth(self, api_client, product_size):
        response = api_client.post(self.URL, {
            "product_size_id": product_size.id,
            "position": "BUY",
            "price": 300000,
        })
        assert response.status_code == 401

    def test_create_buy_bid(self, buyer_client, product_size):
        response = buyer_client.post(self.URL, {
            "product_size_id": product_size.id,
            "position": "BUY",
            "price": 300000,
        })
        assert response.status_code == 201
        assert response.json()["code"] == "OK"

    def test_create_sell_bid(self, buyer_client, product_size):
        response = buyer_client.post(self.URL, {
            "product_size_id": product_size.id,
            "position": "SELL",
            "price": 250000,
        })
        assert response.status_code == 201

    def test_create_bid_invalid_position(self, buyer_client, product_size):
        response = buyer_client.post(self.URL, {
            "product_size_id": product_size.id,
            "position": "INVALID",
            "price": 300000,
        })
        assert response.status_code == 400

    def test_create_bid_price_must_be_positive(self, buyer_client, product_size):
        response = buyer_client.post(self.URL, {
            "product_size_id": product_size.id,
            "position": "BUY",
            "price": 0,
        })
        assert response.status_code == 400

    def test_create_bid_product_size_not_found(self, buyer_client):
        response = buyer_client.post(self.URL, {
            "product_size_id": 99999,
            "position": "BUY",
            "price": 300000,
        })
        assert response.status_code == 404


@pytest.mark.django_db
class TestBidListAPI:
    URL = "/api/v1/bids/"

    def test_list_my_bids(self, buyer_client, product_size):
        buyer_client.post(self.URL, {
            "product_size_id": product_size.id,
            "position": "BUY",
            "price": 300000,
        })
        response = buyer_client.get(self.URL)
        assert response.status_code == 200
        results = response.json()["data"]["results"]
        assert len(results) == 1
        assert results[0]["price"] == 300000


@pytest.mark.django_db
class TestOrderCreateAPI:
    URL = "/api/v1/orders/"

    def _create_sell_bid(self, seller, product_size):
        from orders.models import Bidding

        return Bidding.objects.create(
            user=seller,
            product_size=product_size,
            position=Bidding.Position.SELL,
            price=300000,
        )

    def test_create_order_success(self, buyer_client, user, seller, product_size):
        bid = self._create_sell_bid(seller, product_size)
        response = buyer_client.post(self.URL, {"bidding_id": bid.id})
        assert response.status_code == 201
        assert response.json()["code"] == "OK"

        # buyer point decreased, seller point increased
        user.refresh_from_db()
        seller.refresh_from_db()
        assert user.point == 1_000_000 - 300000
        assert seller.point == 1_000_000 + 300000

    def test_create_order_from_buy_bid(self, api_client, user, seller, product_size):
        """BUY 입찰에 대해 판매자가 매칭하면, 입찰자=buyer, 요청자=seller"""
        from orders.models import Bidding

        buy_bid = Bidding.objects.create(
            user=user,
            product_size=product_size,
            position=Bidding.Position.BUY,
            price=300000,
        )
        api_client.force_authenticate(user=seller)
        response = api_client.post(self.URL, {"bidding_id": buy_bid.id})
        assert response.status_code == 201
        assert response.json()["code"] == "OK"

        user.refresh_from_db()
        seller.refresh_from_db()
        assert user.point == 1_000_000 - 300000
        assert seller.point == 1_000_000 + 300000

    def test_create_order_already_contracted(self, buyer_client, seller, product_size):
        bid = self._create_sell_bid(seller, product_size)
        buyer_client.post(self.URL, {"bidding_id": bid.id})
        response = buyer_client.post(self.URL, {"bidding_id": bid.id})
        assert response.status_code == 409
        data = response.json()
        assert data["code"] == "CONFLICT"
        assert data["message"] == "Bidding already contracted."

    def test_create_order_insufficient_point(self, buyer_client, user, seller, product_size):
        user.point = 100
        user.save()
        bid = self._create_sell_bid(seller, product_size)
        response = buyer_client.post(self.URL, {"bidding_id": bid.id})
        assert response.status_code == 400
        data = response.json()
        assert data["code"] == "INSUFFICIENT_POINT"
        assert data["message"] == "Insufficient points."

    def test_create_order_bidding_not_found(self, buyer_client):
        response = buyer_client.post(self.URL, {"bidding_id": 99999})
        assert response.status_code == 404

    def test_create_order_cannot_buy_own_bid(self, buyer_client, user, product_size):
        from orders.models import Bidding

        own_bid = Bidding.objects.create(
            user=user,
            product_size=product_size,
            position=Bidding.Position.SELL,
            price=300000,
        )
        response = buyer_client.post(self.URL, {"bidding_id": own_bid.id})
        assert response.status_code == 400
        data = response.json()
        assert data["code"] == "INVALID_PARAMETER"
        assert data["message"] == "Cannot match your own bid."


@pytest.mark.django_db
class TestMyOrdersAPI:
    URL = "/api/v1/me/orders/"

    def test_my_orders_requires_auth(self, api_client):
        response = api_client.get(self.URL)
        assert response.status_code == 401

    def test_my_orders_empty(self, buyer_client):
        response = buyer_client.get(self.URL)
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["buy_orders"] == []
        assert data["sell_orders"] == []
        assert data["active_bids"] == []


@pytest.mark.django_db
class TestPriceHistoryAPI:
    def test_price_history(self, api_client):
        product = ProductFactory()
        response = api_client.get(f"/api/v1/products/{product.id}/price-history/")
        assert response.status_code == 200
        data = response.json()["data"]
        assert "order_history" in data
        assert "sell_bids" in data
        assert "buy_bids" in data
