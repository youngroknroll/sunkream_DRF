from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.db.models import Count, F
from rest_framework import generics, permissions, status
from rest_framework.exceptions import NotFound, ValidationError

from core.exceptions import ConflictError, ForbiddenError, InsufficientPointError
from core.mixins import SuccessResponseListMixin
from core.responses import success_response
from orders.models import Bidding, Order
from orders.serializers import (
    BidCreateSerializer,
    BidListSerializer,
    OrderCreateSerializer,
    OrderListSerializer,
    OrderStatusUpdateSerializer,
    VALID_STATUS_TRANSITIONS,
)
from products.models import Product, ProductSize

User = get_user_model()


class BidListCreateView(SuccessResponseListMixin, generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return BidCreateSerializer
        return BidListSerializer

    def get_queryset(self):
        return (
            Bidding.objects.filter(user=self.request.user)
            .select_related("product_size__product", "product_size__size")
            .order_by("-created_at")
        )

    def create(self, request, *args, **kwargs):
        serializer = BidCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            product_size = ProductSize.objects.get(
                pk=serializer.validated_data["product_size_id"]
            )
        except ProductSize.DoesNotExist:
            raise NotFound("Product size not found.")
        Bidding.objects.create(
            user=request.user,
            product_size=product_size,
            position=serializer.validated_data["position"],
            price=serializer.validated_data["price"],
        )
        return success_response(
            message="Bid created.",
            status_code=status.HTTP_201_CREATED,
        )


class OrderCreateView(generics.CreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = OrderCreateSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        bidding_id = serializer.validated_data["bidding_id"]

        with transaction.atomic():
            try:
                bidding = Bidding.objects.select_for_update().get(pk=bidding_id)
            except Bidding.DoesNotExist:
                raise NotFound("Bidding not found.")

            if bidding.status == Bidding.Status.CONTRACTED:
                raise ConflictError("Bidding already contracted.")

            if bidding.user == request.user:
                raise ValidationError("Cannot match your own bid.")

            if bidding.position == Bidding.Position.SELL:
                buyer, seller = request.user, bidding.user
            else:
                buyer, seller = bidding.user, request.user

            try:
                User.objects.filter(pk=buyer.pk).update(
                    point=F("point") - bidding.price
                )
                User.objects.filter(pk=seller.pk).update(
                    point=F("point") + bidding.price
                )
            except IntegrityError:
                raise InsufficientPointError()

            bidding.status = Bidding.Status.CONTRACTED
            bidding.save(update_fields=["status"])

            Order.objects.create(
                bidding=bidding,
                buyer=buyer,
                seller=seller,
                price=bidding.price,
            )

        return success_response(
            message="Order created.",
            status_code=status.HTTP_201_CREATED,
        )


class MyOrdersView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        buy_orders = (
            Order.objects.filter(buyer=user)
            .select_related("bidding__product_size__product", "bidding__product_size__size")
            .order_by("-created_at")[:100]
        )
        sell_orders = (
            Order.objects.filter(seller=user)
            .select_related("bidding__product_size__product", "bidding__product_size__size")
            .order_by("-created_at")[:100]
        )
        active_bids = (
            Bidding.objects.filter(user=user, status=Bidding.Status.ON_BIDDING)
            .select_related("product_size__product", "product_size__size")
            .order_by("-created_at")[:100]
        )

        return success_response(data={
            "user_name": user.name,
            "user_email": user.email,
            "user_point": user.point,
            "buy_orders": OrderListSerializer(buy_orders, many=True).data,
            "sell_orders": OrderListSerializer(sell_orders, many=True).data,
            "active_bids": BidListSerializer(active_bids, many=True).data,
        })


class OrderStatusUpdateView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, order_id):
        with transaction.atomic():
            try:
                order = Order.objects.select_for_update().get(pk=order_id)
            except Order.DoesNotExist:
                raise NotFound("Order not found.")

            if order.seller != request.user:
                raise ForbiddenError("Only the seller can update order status.")

            serializer = OrderStatusUpdateSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            new_status = serializer.validated_data["status"]

            if VALID_STATUS_TRANSITIONS.get(order.status) != new_status:
                raise ValidationError("Invalid status transition.")

            order.status = new_status
            order.save(update_fields=["status"])

        return success_response(data={"id": order.id, "status": order.status}, message="Order status updated.")


class BidCancelView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, bid_id):
        with transaction.atomic():
            try:
                bidding = (
                    Bidding.objects
                    .select_for_update()
                    .get(pk=bid_id, user=request.user)
                )
            except Bidding.DoesNotExist:
                raise NotFound("Bidding not found.")

            if bidding.status != Bidding.Status.ON_BIDDING:
                raise ConflictError("Only active bids can be cancelled.")

            bidding.status = Bidding.Status.CANCELLED
            bidding.save(update_fields=["status"])

        return success_response(message="Bid cancelled.")


class PriceHistoryView(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]

    def _bid_aggregates(self, product_id, position, order):
        return (
            Bidding.objects.filter(
                product_size__product_id=product_id,
                position=position,
                status=Bidding.Status.ON_BIDDING,
            )
            .values("price", "product_size__size__size")
            .annotate(count=Count("id"))
            .order_by(order)
        )

    def get(self, request, product_id):
        if not Product.objects.filter(pk=product_id).exists():
            raise NotFound("Product not found.")

        orders = (
            Order.objects.filter(bidding__product_size__product_id=product_id)
            .select_related("bidding__product_size__size")
            .order_by("-created_at")[:100]
        )

        order_history = [
            {
                "price": o.price,
                "size": o.bidding.product_size.size.size,
                "date": o.created_at.isoformat(),
            }
            for o in orders
        ]

        sell_bids = self._bid_aggregates(product_id, Bidding.Position.SELL, "price")
        buy_bids  = self._bid_aggregates(product_id, Bidding.Position.BUY, "-price")

        return success_response(data={
            "order_history": order_history,
            "sell_bids": [
                {"price": b["price"], "size": b["product_size__size__size"], "count": b["count"]}
                for b in sell_bids
            ],
            "buy_bids": [
                {"price": b["price"], "size": b["product_size__size__size"], "count": b["count"]}
                for b in buy_bids
            ],
        })
