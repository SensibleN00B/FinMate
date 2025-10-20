from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from fin_mate.models import Category, Transaction

CACHE_KEY = "account:{id}:balance"

DEFAULT_CATEGORIES = [
    "Food",
    "Transport",
    "Salary",
    "Entertainment",
    "Health",
    "Clothing",
    "Investment",
    "Donations",
    "Insurance",
    "Home & Renovation",
    "Digital Goods",
    "Utilities",
    "Beauty",
    "Sport",
]


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_default_categories(sender, instance, created, **kwargs):
    if not created:
        return
    categories = [
        Category(user=instance, name=category) for category in DEFAULT_CATEGORIES
    ]
    with transaction.atomic():
        Category.objects.bulk_create(categories, ignore_conflicts=True)


def _invalidate_account_cache(account_id: int | None):
    if account_id:
        cache.delete(CACHE_KEY.format(id=account_id))


@receiver(pre_save, sender=Transaction)
def remember_old_account(sender, instance: Transaction, **kwargs):
    if instance.pk:
        try:
            instance._old_account_id = (
                Transaction.objects.only("account_id").get(pk=instance.pk).account_id
            )
        except Transaction.DoesNotExist:
            instance._old_account_id = None


@receiver(post_save, sender=Transaction)
def invalidate_after_save(sender, instance: Transaction, **kwargs):
    _invalidate_account_cache(instance.account_id)
    old_id = getattr(instance, "_old_account_id", None)
    if old_id and old_id != instance.account_id:
        _invalidate_account_cache(old_id)


@receiver(post_delete, sender=Transaction)
def invalidate_after_delete(sender, instance: Transaction, **kwargs):
    _invalidate_account_cache(instance.account_id)
