import pytest
from django.db import IntegrityError

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
    def test_brand_str(self):
        brand = BrandFactory(name="Nike")
        assert str(brand) == "Nike"

    def test_product_belongs_to_brand(self):
        product = ProductFactory()
        assert product.brand is not None
        assert product.brand.name.startswith("brand_")

    def test_product_image_belongs_to_product(self):
        img = ProductImageFactory()
        assert img.product is not None

    def test_product_size_unique_together(self):
        ps = ProductSizeFactory()
        with pytest.raises(IntegrityError):
            ProductSizeFactory(product=ps.product, size=ps.size)

    def test_wishlist_unique_together(self):
        from products.models import Wishlist

        user = UserFactory()
        product = ProductFactory()
        Wishlist.objects.create(user=user, product=product)
        with pytest.raises(IntegrityError):
            Wishlist.objects.create(user=user, product=product)


@pytest.mark.django_db
class TestProductListAPI:
    URL = "/api/v1/products/"

    def test_list_products_empty(self, api_client):
        response = api_client.get(self.URL)
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "OK"
        assert data["data"]["results"] == []

    def test_list_products_returns_data(self, api_client):
        ProductFactory.create_batch(3)
        response = api_client.get(self.URL)
        assert response.status_code == 200
        results = response.json()["data"]["results"]
        assert len(results) == 3

    def test_filter_by_brand(self, api_client):
        brand = BrandFactory(name="Nike")
        ProductFactory(brand=brand)
        ProductFactory()  # other brand
        response = api_client.get(self.URL, {"brand_id": brand.id})
        results = response.json()["data"]["results"]
        assert len(results) == 1
        assert results[0]["brand"] == "Nike"

    def test_filter_by_size(self, api_client):
        size = SizeFactory(size=270)
        product = ProductFactory()
        ProductSizeFactory(product=product, size=size)
        ProductFactory()  # no size match
        response = api_client.get(self.URL, {"size_id": size.id})
        results = response.json()["data"]["results"]
        assert len(results) == 1

    def test_search_by_name(self, api_client):
        ProductFactory(name="Jordan 1 Retro")
        ProductFactory(name="Air Max 90")
        response = api_client.get(self.URL, {"search": "Jordan"})
        results = response.json()["data"]["results"]
        assert len(results) == 1
        assert "Jordan" in results[0]["name"]

    def test_pagination(self, api_client):
        ProductFactory.create_batch(5)
        response = api_client.get(self.URL, {"limit": 2, "offset": 0})
        data = response.json()["data"]
        assert len(data["results"]) == 2
        assert data["count"] == 5


@pytest.mark.django_db
class TestProductDetailAPI:
    def test_get_product_detail(self, api_client):
        product = ProductFactory()
        ProductImageFactory(product=product)
        response = api_client.get(f"/api/v1/products/{product.id}/")
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["id"] == product.id
        assert data["name"] == product.name
        assert "images" in data
        assert "wishlist_count" in data

    def test_product_not_found(self, api_client):
        response = api_client.get("/api/v1/products/99999/")
        assert response.status_code == 404
        assert response.json()["code"] == "NOT_FOUND"


@pytest.mark.django_db
class TestBrandListAPI:
    def test_list_brands(self, api_client):
        BrandFactory.create_batch(3)
        response = api_client.get("/api/v1/products/brands/")
        assert response.status_code == 200
        data = response.json()["data"]
        assert len(data) == 3


@pytest.mark.django_db
class TestWishlistAPI:
    def test_add_wishlist_requires_auth(self, api_client):
        product = ProductFactory()
        response = api_client.post(f"/api/v1/products/{product.id}/wishlist/")
        assert response.status_code == 401

    def test_add_wishlist(self, authenticated_client):
        product = ProductFactory()
        response = authenticated_client.post(f"/api/v1/products/{product.id}/wishlist/")
        assert response.status_code == 201
        assert response.json()["code"] == "OK"

    def test_add_wishlist_duplicate_returns_conflict(self, authenticated_client):
        product = ProductFactory()
        authenticated_client.post(f"/api/v1/products/{product.id}/wishlist/")
        response = authenticated_client.post(f"/api/v1/products/{product.id}/wishlist/")
        assert response.status_code == 409
        data = response.json()
        assert data["code"] == "CONFLICT"
        assert data["message"] == "Already in wishlist."

    def test_remove_wishlist(self, authenticated_client):
        product = ProductFactory()
        authenticated_client.post(f"/api/v1/products/{product.id}/wishlist/")
        response = authenticated_client.delete(f"/api/v1/products/{product.id}/wishlist/")
        assert response.status_code == 204

    def test_remove_wishlist_not_exists(self, authenticated_client):
        product = ProductFactory()
        response = authenticated_client.delete(f"/api/v1/products/{product.id}/wishlist/")
        assert response.status_code == 404

    def test_add_wishlist_product_not_found(self, authenticated_client):
        response = authenticated_client.post("/api/v1/products/99999/wishlist/")
        assert response.status_code == 404
