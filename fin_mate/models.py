from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Case, DecimalField, F, Q, Sum, Value, When
from django.db.models.functions import Coalesce
from django.utils import timezone


class Category(models.Model):
    name = models.CharField(
        max_length=63,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name="categories", on_delete=models.CASCADE
    )
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


class Transaction(models.Model):
    class TransactionType(models.TextChoices):
        INCOME = "INCOME", "Income"
        EXPENSE = "EXPENSE", "Expense"

    amount = models.DecimalField(max_digits=12, decimal_places=2)
    type = models.CharField(choices=TransactionType.choices, max_length=10)
    account = models.ForeignKey(
        "Account", on_delete=models.CASCADE, related_name="transactions"
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name="transactions",
    )
    date = models.DateField(default=timezone.localdate, db_index=True)
    description = models.TextField(blank=True)
    tags = models.ManyToManyField(
        "Tag", through="TransactionTag", related_name="transactions", blank=True
    )

    def __str__(self):
        return f"{self.get_type_display()} - {self.amount} ({self.category})"

    def clean(self):
        if self.account.user_id != self.category.user_id:
            raise ValidationError("Account and Category must belong to the same user.")

    class Meta:
        ordering = ["-date"]
        indexes = [
            models.Index(fields=["account", "date"]),
            models.Index(fields=["category", "date"]),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(amount__gt=0), name="transaction_gt_zero"
            )
        ]


class AccountQuerySet(models.QuerySet):
    def with_balance(self):
        signed = Case(
            When(
                transactions__type=Transaction.TransactionType.INCOME,
                then=F("transactions__amount"),
            ),
            When(
                transactions__type=Transaction.TransactionType.EXPENSE,
                then=-F("transactions__amount"),
            ),
            default=Value(0),
            output_field=DecimalField(max_digits=12, decimal_places=2),
        )
        return self.annotate(
            annotated_balance=Coalesce(
                Sum(signed),
                Value(0),
                output_field=DecimalField(max_digits=12, decimal_places=2),
            )
        )


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
    objects = AccountQuerySet.as_manager()
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
        return f"{self.name} ({self.get_type_display()}) - {self.currency}"

    @property
    def balance(self):
        from fin_mate.cache_utils import get_account_balance

        return get_account_balance(self.pk)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "name"],
                name="uniq_account_per_user",
            )
        ]
        verbose_name_plural = "accounts"


class Budget(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="budgets"
    )
    category = models.ForeignKey(
        Category, on_delete=models.CASCADE, related_name="budgets"
    )
    limit = models.DecimalField(max_digits=12, decimal_places=2)
    period = models.DateField()
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.category.name} • {self.period:%Y-%m} • {self.limit}"

    class Meta:
        ordering = ["-period", "category__name"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "category", "period"], name="uniq_user_category_period"
            ),
            models.CheckConstraint(check=Q(limit__gt=0), name="budget_limit_gt_zero"),
        ]
        verbose_name_plural = "budgets"

    @property
    def spent_amount(self):
        start = self.period.replace(day=1)
        if start.month == 12:
            end = start.replace(year=start.year + 1, month=1)
        else:
            end = start.replace(month=start.month + 1)

        aggregation = Transaction.objects.filter(
            account__user=self.user,
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


class Tag(models.Model):
    class Color(models.TextChoices):
        PRIMARY = "primary", "Blue"
        SECONDARY = "secondary", "Gray"
        SUCCESS = "success", "Green"
        DANGER = "danger", "Red"
        WARNING = "warning", "Yellow"
        INFO = "info", "Cyan"
        DARK = "dark", "Dark"
        LIGHT = "light", "Light"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    name = models.CharField(max_length=32)
    color = models.CharField(
        max_length=10,
        choices=Color.choices,
        default=Color.SECONDARY,
        blank=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "name"], name="uniq_tag_name_per_user")
        ]
        ordering = ["name"]

    def __str__(self):
        return self.name


class TransactionTag(models.Model):
    transaction = models.ForeignKey(Transaction, on_delete=models.CASCADE)
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE)
    added_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["transaction", "tag"],
                name="uniq_tag_per_transaction",
            )
        ]
        indexes = [
            models.Index(fields=["transaction"]),
            models.Index(fields=["tag"]),
        ]

    def __str__(self) -> str:
        return f"{self.transaction_id} • {self.tag.name}"
