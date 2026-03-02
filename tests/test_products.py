import pytest
from django.db import IntegrityError

from products.models import Wishlist
from tests.factories import (
    BrandFactory,
    ProductFactory,
    ProductImageFactory,
    ProductSizeFactory,
    SizeFactory,
    UserFactory,
)


@pytest.mark.django_db
class TestProductModels:
    def test_브랜드_문자열표현은_이름이다(self):
        brand = BrandFactory(name="Nike")
        assert str(brand) == "Nike"

    def test_상품은_브랜드를_가진다(self):
        product = ProductFactory()
        assert product.brand is not None
        assert product.brand.name.startswith("brand_")

    def test_상품이미지는_상품에_속한다(self):
        img = ProductImageFactory()
        assert img.product is not None

    def test_상품사이즈는_상품과_사이즈_조합이_유일하다(self):
        ps = ProductSizeFactory()
        with pytest.raises(IntegrityError):
            ProductSizeFactory(product=ps.product, size=ps.size)

    def test_위시리스트는_유저와_상품_조합이_유일하다(self):
        user = UserFactory()
        product = ProductFactory()
        Wishlist.objects.create(user=user, product=product)
        with pytest.raises(IntegrityError):
            Wishlist.objects.create(user=user, product=product)


@pytest.mark.django_db
class TestProductListAPI:
    def _get_results(self, response):
        return response.json()["data"]["results"]

    def test_상품목록조회_데이터가없으면_빈결과를_반환한다(self, api_client, products_api):
        response = products_api.list(api_client)
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "OK"
        assert data["data"]["results"] == []

    def test_상품목록조회_등록된상품을_반환한다(self, api_client, products_api):
        ProductFactory.create_batch(3)
        response = products_api.list(api_client)
        assert len(self._get_results(response)) == 3

    def test_상품목록조회_브랜드필터가_적용된다(self, api_client, products_api):
        brand = BrandFactory(name="Nike")
        ProductFactory(brand=brand)
        ProductFactory()  # other brand
        response = products_api.list(api_client, {"brand_id": brand.id})
        results = self._get_results(response)
        assert len(results) == 1
        assert results[0]["brand"] == "Nike"

    def test_상품목록조회_사이즈필터가_적용된다(self, api_client, products_api):
        size = SizeFactory(size=270)
        product = ProductFactory()
        ProductSizeFactory(product=product, size=size)
        ProductFactory()  # no size match
        response = products_api.list(api_client, {"size_id": size.id})
        assert len(self._get_results(response)) == 1

    def test_상품목록조회_이름검색이_적용된다(self, api_client, products_api):
        ProductFactory(name="Jordan 1 Retro")
        ProductFactory(name="Air Max 90")
        response = products_api.list(api_client, {"search": "Jordan"})
        results = self._get_results(response)
        assert len(results) == 1
        assert "Jordan" in results[0]["name"]

    def test_상품목록조회_페이지네이션이_적용된다(self, api_client, products_api):
        ProductFactory.create_batch(5)
        response = products_api.list(api_client, {"limit": 2, "offset": 0})
        data = response.json()["data"]
        assert len(data["results"]) == 2
        assert data["count"] == 5


@pytest.mark.django_db
class TestProductDetailAPI:
    def test_상품상세조회_요청에_성공한다(self, api_client, products_api):
        product = ProductFactory()
        ProductImageFactory(product=product)
        response = products_api.detail(api_client, product.id)
        assert response.status_code == 200

    def test_상품상세조회_필수필드를_포함한다(self, api_client, products_api):
        product = ProductFactory()
        ProductImageFactory(product=product)
        response = products_api.detail(api_client, product.id)
        data = response.json()["data"]
        assert data["id"] == product.id
        assert data["name"] == product.name
        assert "images" in data
        assert "wishlist_count" in data

    def test_상품상세조회_상품이없으면_404를_반환한다(self, api_client, products_api, not_found_id):
        response = products_api.detail(api_client, not_found_id)
        assert response.status_code == 404
        assert response.json()["code"] == "NOT_FOUND"


@pytest.mark.django_db
class TestBrandListAPI:
    def test_브랜드목록조회_브랜드목록을_반환한다(self, api_client, products_api):
        BrandFactory.create_batch(3)
        response = products_api.brands(api_client)
        assert response.status_code == 200
        data = response.json()["data"]
        assert len(data) == 3


@pytest.mark.django_db
class TestWishlistAPI:
    def test_위시리스트추가_인증이없으면_401을_반환한다(self, api_client, products_api, product):
        response = products_api.add_wishlist(api_client, product.id)
        assert response.status_code == 401

    def test_위시리스트추가_성공하면_201을_반환한다(self, authenticated_client, products_api, product):
        response = products_api.add_wishlist(authenticated_client, product.id)
        assert response.status_code == 201
        assert response.json()["code"] == "OK"

    def test_위시리스트추가_중복이면_409를_반환한다(
        self, authenticated_client, products_api, product, assert_api_error,
    ):
        products_api.add_wishlist(authenticated_client, product.id)
        response = products_api.add_wishlist(authenticated_client, product.id)
        assert response.status_code == 409
        assert_api_error(response, 409, "CONFLICT", "Already in wishlist.")

    def test_위시리스트삭제_성공하면_204를_반환한다(self, authenticated_client, products_api, product):
        products_api.add_wishlist(authenticated_client, product.id)
        response = products_api.remove_wishlist(authenticated_client, product.id)
        assert response.status_code == 204

    def test_위시리스트삭제_대상이없으면_404를_반환한다(self, authenticated_client, products_api, product):
        response = products_api.remove_wishlist(authenticated_client, product.id)
        assert response.status_code == 404

    def test_위시리스트추가_상품이없으면_404를_반환한다(
        self, authenticated_client, products_api, not_found_id,
    ):
        response = products_api.add_wishlist(authenticated_client, not_found_id)
        assert response.status_code == 404
