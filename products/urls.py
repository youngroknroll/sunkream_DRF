from django.urls import path

from products.views import BrandListView, ProductDetailView, ProductListView, WishlistView

urlpatterns = [
    path("", ProductListView.as_view(), name="product-list"),
    path("brands/", BrandListView.as_view(), name="brand-list"),
    path("<int:pk>/", ProductDetailView.as_view(), name="product-detail"),
    path("<int:product_id>/wishlist/", WishlistView.as_view(), name="wishlist"),
]
