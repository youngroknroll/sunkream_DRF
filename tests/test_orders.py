import pytest

from tests.factories import ProductFactory


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

    def test_create_buy_bid(self, authenticated_client, product_size):
        response = authenticated_client.post(self.URL, {
            "product_size_id": product_size.id,
            "position": "BUY",
            "price": 300000,
        })
        assert response.status_code == 201
        assert response.json()["code"] == "OK"

    def test_create_sell_bid(self, authenticated_client, product_size):
        response = authenticated_client.post(self.URL, {
            "product_size_id": product_size.id,
            "position": "SELL",
            "price": 250000,
        })
        assert response.status_code == 201

    def test_create_bid_invalid_position(self, authenticated_client, product_size):
        response = authenticated_client.post(self.URL, {
            "product_size_id": product_size.id,
            "position": "INVALID",
            "price": 300000,
        })
        assert response.status_code == 400

    def test_create_bid_price_must_be_positive(self, authenticated_client, product_size):
        response = authenticated_client.post(self.URL, {
            "product_size_id": product_size.id,
            "position": "BUY",
            "price": 0,
        })
        assert response.status_code == 400

    def test_create_bid_product_size_not_found(self, authenticated_client):
        response = authenticated_client.post(self.URL, {
            "product_size_id": 99999,
            "position": "BUY",
            "price": 300000,
        })
        assert response.status_code == 404


@pytest.mark.django_db
class TestBidListAPI:
    URL = "/api/v1/bids/"

    def test_list_my_bids(self, authenticated_client, product_size):
        authenticated_client.post(self.URL, {
            "product_size_id": product_size.id,
            "position": "BUY",
            "price": 300000,
        })
        response = authenticated_client.get(self.URL)
        assert response.status_code == 200
        results = response.json()["data"]["results"]
        assert len(results) == 1
        assert results[0]["price"] == 300000


@pytest.mark.django_db
class TestOrderCreateAPI:
    URL = "/api/v1/orders/"

    def test_create_order_success(self, authenticated_client, user, seller, sell_bid):
        response = authenticated_client.post(self.URL, {"bidding_id": sell_bid.id})
        assert response.status_code == 201
        assert response.json()["code"] == "OK"

        user.refresh_from_db()
        seller.refresh_from_db()
        assert user.point == 1_000_000 - 300000
        assert seller.point == 1_000_000 + 300000

    def test_create_order_from_buy_bid(self, seller_client, seller, user, buy_bid):
        """BUY 입찰에 대해 판매자가 매칭하면, 입찰자=buyer, 요청자=seller"""
        response = seller_client.post(self.URL, {"bidding_id": buy_bid.id})
        assert response.status_code == 201
        assert response.json()["code"] == "OK"

        user.refresh_from_db()
        seller.refresh_from_db()
        assert user.point == 1_000_000 - 300000
        assert seller.point == 1_000_000 + 300000

    def test_create_order_already_contracted(self, authenticated_client, sell_bid):
        authenticated_client.post(self.URL, {"bidding_id": sell_bid.id})
        response = authenticated_client.post(self.URL, {"bidding_id": sell_bid.id})
        assert response.status_code == 409
        data = response.json()
        assert data["code"] == "CONFLICT"
        assert data["message"] == "Bidding already contracted."

    def test_create_order_insufficient_point(self, authenticated_client, user, sell_bid):
        user.point = 100
        user.save()
        response = authenticated_client.post(self.URL, {"bidding_id": sell_bid.id})
        assert response.status_code == 400
        data = response.json()
        assert data["code"] == "INSUFFICIENT_POINT"
        assert data["message"] == "Insufficient points."

    def test_create_order_bidding_not_found(self, authenticated_client):
        response = authenticated_client.post(self.URL, {"bidding_id": 99999})
        assert response.status_code == 404

    def test_create_order_cannot_buy_own_bid(self, authenticated_client, own_sell_bid):
        response = authenticated_client.post(self.URL, {"bidding_id": own_sell_bid.id})
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

    def test_my_orders_empty(self, authenticated_client):
        response = authenticated_client.get(self.URL)
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
