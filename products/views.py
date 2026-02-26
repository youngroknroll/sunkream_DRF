from django.db import IntegrityError
from django.db.models import Count
from rest_framework import generics, permissions, status
from rest_framework.exceptions import NotFound
from rest_framework.response import Response

from core.exceptions import ConflictError
from core.mixins import SuccessResponseListMixin
from core.responses import success_response
from products.models import Brand, Product, Wishlist
from products.serializers import (
    BrandSerializer,
    ProductDetailSerializer,
    ProductListSerializer,
)


class ProductListView(SuccessResponseListMixin, generics.ListAPIView):
    serializer_class = ProductListSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        qs = Product.objects.select_related("brand").all()

        brand_id = self.request.query_params.get("brand_id")
        if brand_id:
            qs = qs.filter(brand_id=brand_id)

        size_id = self.request.query_params.get("size_id")
        if size_id:
            qs = qs.filter(product_sizes__size_id=size_id)

        search = self.request.query_params.get("search")
        if search:
            qs = qs.filter(name__icontains=search)

        return qs.distinct()


class ProductDetailView(generics.RetrieveAPIView):
    serializer_class = ProductDetailSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = "pk"

    def get_queryset(self):
        return Product.objects.select_related("brand").prefetch_related("images").annotate(
            wishlist_count=Count("wishlists")
        )

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return success_response(data=serializer.data)


class BrandListView(generics.ListAPIView):
    serializer_class = BrandSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = None
    queryset = Brand.objects.all()

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return success_response(data=serializer.data)


class WishlistView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def _get_product(self, product_id):
        try:
            return Product.objects.get(pk=product_id)
        except Product.DoesNotExist:
            raise NotFound("Product not found.")

    def post(self, request, product_id):
        product = self._get_product(product_id)
        try:
            Wishlist.objects.create(user=request.user, product=product)
        except IntegrityError:
            raise ConflictError("Already in wishlist.")
        return success_response(
            message="Wishlist added.",
            status_code=status.HTTP_201_CREATED,
        )

    def delete(self, request, product_id):
        product = self._get_product(product_id)
        deleted, _ = Wishlist.objects.filter(user=request.user, product=product).delete()
        if not deleted:
            raise NotFound("Wishlist entry not found.")
        return Response(status=status.HTTP_204_NO_CONTENT)
