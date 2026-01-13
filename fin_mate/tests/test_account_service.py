import pytest
from decimal import Decimal
from fin_mate.models import Account, Transaction, Category
from fin_mate.services.account_service import create_account_with_balance

@pytest.mark.django_db
def test_create_account_no_balance(user):
    account = Account(name="Test Account", currency=Account.Currency.UAH, type=Account.Type.CASH)
    created_account = create_account_with_balance(account, user)

    assert created_account.pk is not None
    assert created_account.user == user
    assert created_account.transactions.count() == 0

@pytest.mark.django_db
def test_create_account_with_balance(user):
    account = Account(name="Rich Account", currency=Account.Currency.USD, type=Account.Type.CARD)
    balance = Decimal("100.00")
    created_account = create_account_with_balance(account, user, balance)

    assert created_account.pk is not None
    assert created_account.transactions.count() == 1
    
    txn = created_account.transactions.first()
    assert txn.amount == balance
    assert txn.type == Transaction.TransactionType.INCOME
    assert txn.description == "Initial balance"
    assert txn.category.name == "Opening balance"
    assert txn.category.is_system is True

@pytest.mark.django_db
def test_create_account_opening_balance_category_reuse(user):
    # Create category beforehand
    Category.objects.create(user=user, name="Opening balance", is_system=False)
    
    account = Account(name="Reuse Category", currency=Account.Currency.EUR)
    create_account_with_balance(account, user, Decimal("50"))

    category = Category.objects.get(user=user, name="Opening balance")
    assert category.is_system is True

