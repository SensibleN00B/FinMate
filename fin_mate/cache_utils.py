from decimal import Decimal

from django.core.cache import cache

from fin_mate.models import Account

BALANCE_CACHE_TIME = 1800


def get_account_balance(account_id: int) -> Decimal:
    key = f"account:{account_id}:balance"
    value = cache.get(key=key)

    if value is not None:
        return value
    balance = (
        Account.objects.with_balance()
        .filter(pk=account_id)
        .values_list("annotated_balance", flat=True)
        .first()
    ) or Decimal("0.00")
    cache.set(key, balance, BALANCE_CACHE_TIME)

    return balance
