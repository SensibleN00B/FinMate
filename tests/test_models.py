from django.contrib.auth import get_user_model
from django.test import TestCase
from fin_mate.models import Transaction, Account, Category


class TransactionModelTest(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="testuser", password="password123"
        )
        self.category = Category.objects.create(name="Groceries", user=self.user)
        self.account = Account.objects.create(
            name="Main Account",
            balance=1000.00,
            currency=Account.Currency.USD,
            user=self.user,
            type=Account.Type.CARD,
        )

    def test_transaction_creation(self):
        transaction = Transaction.objects.create(
            amount=200.00,
            type=Transaction.TransactionType.INCOME,
            category=self.category,
            account=self.account,
            description="Salary",
        )
        self.assertEqual(transaction.amount, 200.00)
        self.assertEqual(transaction.type, Transaction.TransactionType.INCOME)
        self.assertEqual(transaction.category, self.category)
        self.assertEqual(transaction.account, self.account)
        self.assertEqual(transaction.description, "Salary")

    def test_transaction_str_representation(self):
        transaction = Transaction.objects.create(
            amount=150.50,
            type=Transaction.TransactionType.EXPENSE,
            category=self.category,
            account=self.account,
            description="Dinner",
        )
        expected_str = f"{transaction.get_type_display()} - {transaction.amount} ({transaction.category})"
        self.assertEqual(str(transaction), expected_str)

    def test_transaction_default_date(self):
        transaction = Transaction.objects.create(
            amount=50.00,
            type=Transaction.TransactionType.EXPENSE,
            category=self.category,
            account=self.account,
        )
        self.assertIsNotNone(transaction.date)

    def test_transaction_ordering(self):
        t1 = Transaction.objects.create(
            amount=100.00,
            type=Transaction.TransactionType.INCOME,
            category=self.category,
            account=self.account,
        )
        t2 = Transaction.objects.create(
            amount=200.00,
            type=Transaction.TransactionType.EXPENSE,
            category=self.category,
            account=self.account,
        )
        transactions = list(Transaction.objects.all())
        self.assertEqual(transactions, [t2, t1])
