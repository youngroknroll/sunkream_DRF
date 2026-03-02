import pytest


@pytest.mark.django_db
class TestBidCreateAPI:
    def test_입찰생성_인증이없으면_401을_반환한다(self, api_client, bids_api, bid_data):
        response = bids_api.create(api_client, bid_data)
        assert response.status_code == 401

    def test_입찰생성_구매입찰을_생성한다(self, authenticated_client, bids_api, bid_data):
        response = bids_api.create(authenticated_client, bid_data)
        assert response.status_code == 201
        assert response.json()["code"] == "OK"

    def test_입찰생성_판매입찰을_생성한다(self, authenticated_client, bids_api, make_bid_data):
        response = bids_api.create(authenticated_client, make_bid_data(position="SELL", price=250000))
        assert response.status_code == 201

    def test_입찰생성_position이_유효하지않으면_400을_반환한다(self, authenticated_client, bids_api, make_bid_data):
        response = bids_api.create(authenticated_client, make_bid_data(position="INVALID"))
        assert response.status_code == 400

    def test_입찰생성_가격이_0이하면_400을_반환한다(self, authenticated_client, bids_api, make_bid_data):
        response = bids_api.create(authenticated_client, make_bid_data(price=0))
        assert response.status_code == 400

    def test_입찰생성_상품사이즈가_없으면_404를_반환한다(
        self, authenticated_client, bids_api, make_bid_data, not_found_id,
    ):
        response = bids_api.create(authenticated_client, make_bid_data(product_size_id=not_found_id))
        assert response.status_code == 404


@pytest.mark.django_db
class TestBidListAPI:
    def test_내입찰조회_내가입찰한_목록을_반환한다(self, authenticated_client, bids_api, buy_bid):
        response = bids_api.list_my(authenticated_client)
        assert response.status_code == 200
        results = response.json()["data"]["results"]
        assert len(results) == 1
        assert results[0]["price"] == buy_bid.price


@pytest.mark.django_db
class TestOrderCreateAPI:
    def _assert_points_transferred(self, buyer, seller, price):
        buyer.refresh_from_db()
        seller.refresh_from_db()
        assert buyer.point == 1_000_000 - price
        assert seller.point == 1_000_000 + price

    def test_주문생성_판매입찰매칭시_201을_반환한다(self, authenticated_client, orders_api, sell_bid):
        response = orders_api.create(authenticated_client, sell_bid.id)
        assert response.status_code == 201
        assert response.json()["code"] == "OK"

    def test_주문생성_판매입찰매칭시_포인트가_이전된다(
        self, authenticated_client, orders_api, user, seller, sell_bid,
    ):
        orders_api.create(authenticated_client, sell_bid.id)
        self._assert_points_transferred(user, seller, 300000)

    def test_주문생성_구매입찰매칭시_201을_반환한다(self, seller_client, orders_api, buy_bid):
        """BUY 입찰에 대해 판매자가 매칭하면, 입찰자=buyer, 요청자=seller"""
        response = orders_api.create(seller_client, buy_bid.id)
        assert response.status_code == 201
        assert response.json()["code"] == "OK"

    def test_주문생성_구매입찰매칭시_포인트가_이전된다(self, seller_client, orders_api, seller, user, buy_bid):
        orders_api.create(seller_client, buy_bid.id)
        self._assert_points_transferred(user, seller, 300000)

    def test_주문생성_이미체결된입찰이면_409를_반환한다(
        self, authenticated_client, orders_api, contracted_sell_bid, assert_api_error,
    ):
        response = orders_api.create(authenticated_client, contracted_sell_bid.id)
        assert_api_error(response, 409, "CONFLICT", "Bidding already contracted.")

    def test_주문생성_포인트가_부족하면_400을_반환한다(
        self, authenticated_client, orders_api, user, sell_bid, assert_api_error,
    ):
        user.point = 100
        user.save()
        response = orders_api.create(authenticated_client, sell_bid.id)
        assert_api_error(response, 400, "INSUFFICIENT_POINT", "Insufficient points.")

    def test_주문생성_입찰이_없으면_404를_반환한다(self, authenticated_client, orders_api, not_found_id):
        response = orders_api.create(authenticated_client, not_found_id)
        assert response.status_code == 404

    def test_주문생성_내입찰은_매칭할수없다(
        self, authenticated_client, orders_api, own_sell_bid, assert_api_error,
    ):
        response = orders_api.create(authenticated_client, own_sell_bid.id)
        assert_api_error(response, 400, "INVALID_PARAMETER", "Cannot match your own bid.")


@pytest.mark.django_db
class TestMyOrdersAPI:
    def test_내주문조회_인증이없으면_401을_반환한다(self, api_client, me_api):
        response = me_api.orders(api_client)
        assert response.status_code == 401

    def test_내주문조회_데이터가없으면_빈목록을_반환한다(self, authenticated_client, me_api):
        response = me_api.orders(authenticated_client)
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["buy_orders"] == []
        assert data["sell_orders"] == []
        assert data["active_bids"] == []


@pytest.mark.django_db
class TestPriceHistoryAPI:
    def test_시세히스토리조회_요청에_성공한다(self, api_client, products_api, product):
        response = products_api.price_history(api_client, product.id)
        assert response.status_code == 200

    def test_시세히스토리조회_필수섹션을_포함한다(self, api_client, products_api, product):
        response = products_api.price_history(api_client, product.id)
        data = response.json()["data"]
        assert "order_history" in data
        assert "sell_bids" in data
        assert "buy_bids" in data
