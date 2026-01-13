import pytest
from accounts.models import User
from fin_mate.models import Account, Category

@pytest.fixture
def user(db):
    return User.objects.create_user(username="testuser", email="test@example.com", password="password")

@pytest.fixture
def category(db, user):
    return Category.objects.create(user=user, name="Food", is_system=False)

@pytest.fixture
def account(db, user):
    return Account.objects.create(user=user, name="Main Card", currency=Account.Currency.UAH)
