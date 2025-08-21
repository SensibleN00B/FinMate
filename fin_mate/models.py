from django.conf import settings
from django.db import models
from django.db.models import Q, Sum
from django.utils import timezone


class Category(models.Model):
    name = models.CharField(
        max_length=63,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="categories",
        on_delete=models.CASCADE
    )
    # icon = models.CharField(
    #     max_length=63,
    #     blank=True,
    #     help_text="Optional: name of an icon class",
    # )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "name"],
                name="uniq_category_name_per_user",
            )
        ]
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name


class Account(models.Model):
    class Currency(models.TextChoices):
        UAH = "UAH", "Ukrainian Hryvnia"
        USD = "USD", "US Dollar"
        EUR = "EUR", "Euro"

    class Type(models.TextChoices):
        CASH = "CASH", "Cash"
        CARD = "CARD", "Bank Card"
        DEPOSIT = "DEPOSIT", "Deposit"
        CRYPTO = "CRYPTO", "Crypto Wallet"

    name = models.CharField(max_length=63)
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    currency = models.CharField(
        max_length=3,
        choices=Currency.choices,
        default=Currency.UAH,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="accounts",
        on_delete=models.CASCADE,
    )
    type = models.CharField(
        max_length=10,
        choices=Type.choices,
        default=Type.CASH,
    )

    def __str__(self):
        return f"{self.name} ({self.get_type_display()}) - {self.balance} {self.currency}"

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "name"],
                name="uniq_account_per_user",
            )
        ]
        verbose_name_plural = "accounts"


class Transaction(models.Model):
    class TransactionType(models.TextChoices):
        INCOME = "INCOME", "Income"
        EXPENSE = "EXPENSE", "Expense"

    amount = models.DecimalField(max_digits=12, decimal_places=2)
    type = models.CharField(choices=TransactionType.choices, max_length=10)
    account = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name="transactions"
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name="transactions"
    )
    date = models.DateTimeField(default=timezone.now, db_index=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return f"{self.get_type_display()} - {self.amount} ({self.category})"

    class Meta:
        ordering = ["-date"]


class Budget(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="budgets"
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name="budgets"
    )
    limit = models.DecimalField(max_digits=12, decimal_places=2)
    month = models.DateField()
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.category.name} • {self.month:%Y-%m} • {self.limit}"

    class Meta:
        ordering = ["-month", "category__name"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "category", "month"],
                name="uniq_user_category_month"
            ),
            models.CheckConstraint(
                check=Q(limit__gt=0),
                name="budget_limit_gt_than_zero"
            )
        ]
        verbose_name_plural = "budgets"

    @property
    def spent_amount(self):
        start = self.month.replace(day=1)
        if start.month == 12:
            end = start.replace(year=start.year + 1, month=1)
        else:
            end = start.replace(month=start.month + 1)

        aggregation = Transaction.objects.filter(
            user_account=self.user,
            category=self.category,
            type=Transaction.TransactionType.EXPENSE,
            date__gte=start,
            date__lt=end,
        ).aggregate(total=Sum("amount"))

        return aggregation["total"] or 0

    @property
    def progress(self):
        if not self.limit:
            return 0.0
        return float(self.spent_amount / self.limit * 100)


