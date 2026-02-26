import factory
from django.contrib.auth import get_user_model

User = get_user_model()


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    email = factory.Sequence(lambda n: f"user{n}@example.com")
    name = factory.Faker("name")
    password = factory.PostGenerationMethodCall("set_password", "testpass123")


class BrandFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "products.Brand"

    name = factory.Sequence(lambda n: f"brand_{n}")


class SizeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "products.Size"

    size = factory.Sequence(lambda n: 250 + n * 5)


class ProductFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "products.Product"

    brand = factory.SubFactory(BrandFactory)
    name = factory.Sequence(lambda n: f"Product {n}")
    model_number = factory.Sequence(lambda n: f"MODEL-{n:04d}")
    release_price = 199000
    thumbnail_url = "https://example.com/thumb.jpg"


class ProductImageFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "products.ProductImage"

    product = factory.SubFactory(ProductFactory)
    image_url = factory.Sequence(lambda n: f"https://example.com/img_{n}.jpg")


class ProductSizeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "products.ProductSize"

    product = factory.SubFactory(ProductFactory)
    size = factory.SubFactory(SizeFactory)
