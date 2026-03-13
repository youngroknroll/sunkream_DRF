from django.urls import path

from orders.views import (
    BidCancelView,
    BidListCreateView,
    MyOrdersView,
    OrderCreateView,
    OrderStatusUpdateView,
    PriceHistoryView,
)

urlpatterns = [
    path("bids/", BidListCreateView.as_view(), name="bid-list-create"),
    path("bids/<int:bid_id>/", BidCancelView.as_view(), name="bid-cancel"),
    path("orders/", OrderCreateView.as_view(), name="order-create"),
    path("orders/<int:order_id>/status/", OrderStatusUpdateView.as_view(), name="order-status-update"),
    path("me/orders/", MyOrdersView.as_view(), name="my-orders"),
    path(
        "products/<int:product_id>/price-history/",
        PriceHistoryView.as_view(),
        name="price-history",
    ),
]
