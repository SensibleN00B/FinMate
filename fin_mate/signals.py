from django.conf import settings
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from fin_mate.models import Category

DEFAULT_CATEGORIES = [
    "Food", "Transport", "Salary", "Entertainment", "Health",
    "Clothing", "Investment", "Donations", "Insurance",
    "Home & Renovation", "Digital Goods", "Utilities",
    "Beauty", "Sport",
]


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_default_categories(sender, instance, created, **kwargs):
    if not created:
        return
    categories = [Category(user=instance, name=category) for category in DEFAULT_CATEGORIES]
    with transaction.atomic():
        Category.objects.bulk_create(categories, ignore_conflicts=True)
