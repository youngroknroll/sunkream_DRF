from django.conf import settings
from django.db import models

from core.models import TimeStampModel


class Bidding(TimeStampModel):
    class Status(models.TextChoices):
        ON_BIDDING = "ON_BIDDING", "On Bidding"
        CONTRACTED = "CONTRACTED", "Contracted"

    class Position(models.TextChoices):
        BUY = "BUY", "Buy"
        SELL = "SELL", "Sell"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="bids"
    )
    product_size = models.ForeignKey(
        "products.ProductSize", on_delete=models.CASCADE, related_name="bids"
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.ON_BIDDING
    )
    position = models.CharField(max_length=10, choices=Position.choices)
    price = models.PositiveIntegerField()

    class Meta:
        db_table = "biddings"

    def __str__(self):
        return f"{self.user.email} - {self.position} {self.price}"


class Order(TimeStampModel):
    class Status(models.TextChoices):
        INSPECTION = "INSPECTION", "Inspection"
        IN_TRANSIT = "IN_TRANSIT", "In Transit"
        DELIVERED = "DELIVERED", "Delivered"

    bidding = models.OneToOneField(Bidding, on_delete=models.CASCADE, related_name="order")
    buyer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="buy_orders"
    )
    seller = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sell_orders"
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.INSPECTION
    )
    price = models.PositiveIntegerField()

    class Meta:
        db_table = "orders"

    def __str__(self):
        return f"Order #{self.id} - {self.price}"
