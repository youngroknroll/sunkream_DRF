from django.db import transaction
from django.db.models import Count
from rest_framework import generics, permissions, status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response

from core.responses import success_response
from orders.models import Bidding, Order
from orders.serializers import (
    BidCreateSerializer,
    BidListSerializer,
    OrderCreateSerializer,
    OrderListSerializer,
)
from products.models import ProductSize


class BidListCreateView(generics.ListCreateAPIView):
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

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = BidListSerializer(page, many=True)
            paginated = self.paginator.get_paginated_response(serializer.data)
            return success_response(data={
                "count": paginated.data["count"],
                "results": paginated.data["results"],
            })
        serializer = BidListSerializer(queryset, many=True)
        return success_response(data={"results": serializer.data})

    def create(self, request, *args, **kwargs):
        serializer = BidCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        product_size = ProductSize.objects.get(pk=serializer.validated_data["product_size_id"])
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
                return Response(
                    {"code": "CONFLICT", "message": "Bidding already contracted."},
                    status=status.HTTP_409_CONFLICT,
                )

            if bidding.user == request.user:
                raise ValidationError("Cannot match your own bid.")

            if bidding.position == Bidding.Position.SELL:
                buyer, seller = request.user, bidding.user
            else:
                buyer, seller = bidding.user, request.user

            if buyer.point < bidding.price:
                return Response(
                    {"code": "INSUFFICIENT_POINT", "message": "Insufficient points."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            buyer.point -= bidding.price
            seller.point += bidding.price
            buyer.save(update_fields=["point"])
            seller.save(update_fields=["point"])

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
        buy_orders = Order.objects.filter(buyer=user).select_related(
            "bidding__product_size__product", "bidding__product_size__size"
        )
        sell_orders = Order.objects.filter(seller=user).select_related(
            "bidding__product_size__product", "bidding__product_size__size"
        )
        active_bids = Bidding.objects.filter(
            user=user, status=Bidding.Status.ON_BIDDING
        ).select_related("product_size__product", "product_size__size")

        return success_response(data={
            "user_name": user.name,
            "user_email": user.email,
            "user_point": user.point,
            "buy_orders": OrderListSerializer(buy_orders, many=True).data,
            "sell_orders": OrderListSerializer(sell_orders, many=True).data,
            "active_bids": BidListSerializer(active_bids, many=True).data,
        })


class PriceHistoryView(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, product_id):
        from products.models import Product

        if not Product.objects.filter(pk=product_id).exists():
            raise NotFound("Product not found.")

        orders = (
            Order.objects.filter(bidding__product_size__product_id=product_id)
            .select_related("bidding__product_size__size")
            .order_by("-created_at")
        )

        order_history = [
            {
                "price": o.price,
                "size": o.bidding.product_size.size.size,
                "date": o.created_at.isoformat(),
            }
            for o in orders
        ]

        sell_bids = (
            Bidding.objects.filter(
                product_size__product_id=product_id,
                position=Bidding.Position.SELL,
                status=Bidding.Status.ON_BIDDING,
            )
            .values("price", "product_size__size__size")
            .annotate(count=Count("id"))
            .order_by("price")
        )

        buy_bids = (
            Bidding.objects.filter(
                product_size__product_id=product_id,
                position=Bidding.Position.BUY,
                status=Bidding.Status.ON_BIDDING,
            )
            .values("price", "product_size__size__size")
            .annotate(count=Count("id"))
            .order_by("-price")
        )

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
