from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from accounts.models import User
from fin_mate.models import Account, Category, Transaction

def create_account_with_balance(account: Account, user: User, starting_balance: Decimal | None = None) -> Account:
    """
    Saves the account and optionally creates an initial balance transaction.
    """
    if starting_balance is None:
        starting_balance = Decimal("0")

    with transaction.atomic():
        account.user = user
        account.save()

        if starting_balance > 0:
            opening_category, _ = Category.objects.get_or_create(
                user=user,
                name="Opening balance",
                defaults={"is_system": True},
            )
            # Ensure it is system (in case it existed but wasn't system)
            if not opening_category.is_system:
                opening_category.is_system = True
                opening_category.save(update_fields=["is_system"])

            Transaction.objects.create(
                amount=starting_balance,
                type=Transaction.TransactionType.INCOME,
                account=account,
                category=opening_category,
                date=timezone.localdate(),
                description="Initial balance",
            )
            
    return account
