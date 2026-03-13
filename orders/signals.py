from django.db.models.signals import pre_delete
from django.dispatch import receiver

from orders.models import Bidding
from products.models import Product


@receiver(pre_delete, sender=Product)
def cancel_active_bids_on_product_delete(sender, instance, **kwargs):
    Bidding.objects.filter(
        product_size__product=instance,
        status=Bidding.Status.ON_BIDDING,
    ).update(status=Bidding.Status.CANCELLED)
