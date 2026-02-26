from django.conf import settings
from django.db import models

from core.models import TimeStampModel


class Brand(TimeStampModel):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        db_table = "brands"

    def __str__(self):
        return self.name


class Product(TimeStampModel):
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, related_name="products")
    name = models.CharField(max_length=255)
    model_number = models.CharField(max_length=100, blank=True, default="")
    release_price = models.PositiveIntegerField(default=0)
    thumbnail_url = models.URLField(blank=True, default="")

    class Meta:
        db_table = "products"

    def __str__(self):
        return self.name


class ProductImage(TimeStampModel):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images")
    image_url = models.URLField()

    class Meta:
        db_table = "product_images"


class Size(models.Model):
    size = models.PositiveIntegerField(unique=True)

    class Meta:
        db_table = "sizes"

    def __str__(self):
        return str(self.size)


class ProductSize(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="product_sizes")
    size = models.ForeignKey(Size, on_delete=models.CASCADE, related_name="product_sizes")

    class Meta:
        db_table = "product_sizes"
        constraints = [
            models.UniqueConstraint(fields=["product", "size"], name="unique_product_size"),
        ]

    def __str__(self):
        return f"{self.product.name} - {self.size.size}"


class Wishlist(TimeStampModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="wishlists"
    )
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="wishlists")

    class Meta:
        db_table = "wishlists"
        constraints = [
            models.UniqueConstraint(fields=["user", "product"], name="unique_user_product_wish"),
        ]
