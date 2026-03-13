from rest_framework import serializers
from rest_framework.exceptions import NotFound

from products.models import Brand, Product, ProductImage, ProductSize, Size


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


class ProductCreateSerializer(serializers.Serializer):
    brand_id = serializers.IntegerField()
    name = serializers.CharField(max_length=255)
    model_number = serializers.CharField(max_length=100, required=False, default="")
    release_price = serializers.IntegerField(min_value=0, required=False, default=0)
    thumbnail_url = serializers.URLField(required=False, default="")
    sizes = serializers.ListField(child=serializers.IntegerField(), required=False, default=[])

    def validate_brand_id(self, value):
        if not Brand.objects.filter(pk=value).exists():
            raise NotFound("Brand not found.")
        return value

    def validate_sizes(self, value):
        if value:
            existing = set(Size.objects.filter(size__in=value).values_list("size", flat=True))
            missing = set(value) - existing
            if missing:
                raise serializers.ValidationError(f"Sizes not found: {sorted(missing)}")
        return value


class ProductUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255, required=False)
    model_number = serializers.CharField(max_length=100, required=False)
    release_price = serializers.IntegerField(min_value=0, required=False)
    thumbnail_url = serializers.URLField(required=False, allow_blank=True)


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
