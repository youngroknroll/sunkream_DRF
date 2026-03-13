from rest_framework import serializers

from orders.models import Bidding, Order


class BidCreateSerializer(serializers.Serializer):
    product_size_id = serializers.IntegerField()
    position = serializers.ChoiceField(choices=Bidding.Position.choices)
    price = serializers.IntegerField(min_value=1)


class BidListSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(
        source="product_size.product.name", read_only=True
    )
    size = serializers.IntegerField(source="product_size.size.size", read_only=True)

    class Meta:
        model = Bidding
        fields = ["id", "product_name", "size", "position", "status", "price", "created_at"]


VALID_STATUS_TRANSITIONS = {
    Order.Status.INSPECTION: Order.Status.IN_TRANSIT,
    Order.Status.IN_TRANSIT: Order.Status.DELIVERED,
}


class OrderStatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Order.Status.choices)


class OrderCreateSerializer(serializers.Serializer):
    bidding_id = serializers.IntegerField()


class OrderListSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(
        source="bidding.product_size.product.name", read_only=True
    )
    size = serializers.IntegerField(
        source="bidding.product_size.size.size", read_only=True
    )

    class Meta:
        model = Order
        fields = ["id", "product_name", "size", "status", "price", "created_at"]
