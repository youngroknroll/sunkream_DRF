from django.urls import path

from orders.views import BidListCreateView, MyOrdersView, OrderCreateView, PriceHistoryView

urlpatterns = [
    path("bids/", BidListCreateView.as_view(), name="bid-list-create"),
    path("orders/", OrderCreateView.as_view(), name="order-create"),
    path("me/orders/", MyOrdersView.as_view(), name="my-orders"),
    path(
        "products/<int:product_id>/price-history/",
        PriceHistoryView.as_view(),
        name="price-history",
    ),
]
