from rest_framework import serializers

from products.models import Brand, Product, ProductImage


class BrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = ["id", "name"]


class ProductListSerializer(serializers.ModelSerializer):
    brand = serializers.CharField(source="brand.name", read_only=True)

    class Meta:
        model = Product
        fields = ["id", "brand", "name", "thumbnail_url", "release_price"]


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ["id", "image_url"]


class ProductDetailSerializer(serializers.ModelSerializer):
    brand = serializers.CharField(source="brand.name", read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)
    wishlist_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Product
        fields = [
            "id",
            "brand",
            "name",
            "model_number",
            "release_price",
            "thumbnail_url",
            "images",
            "wishlist_count",
        ]
