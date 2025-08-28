from decimal import Decimal
from django.conf import settings
from django.db.models import Sum

from fin_mate.models import Account, Transaction, Budget
from fin_mate.services.fx import get_rates


def month_summary(user, start, end):
    accounts_qs = Account.objects.with_balance().filter(user=user).order_by("name")
    month_tx = Transaction.objects.filter(account__user=user, date__gte=start, date__lt=end)

    currencies = {(a.currency or "").upper() for a in accounts_qs if a.currency}
    currencies |= {(row["account__currency"] or settings.FX_BASE_CURRENCY).upper()
                   for row in month_tx.values("account__currency").distinct()}
    rates = get_rates(currencies)

    base_total = Decimal("0")
    acc_labels, acc_values_base = [], []
    for a in accounts_qs:
        amount = getattr(a, "annotated_balance", Decimal("0")) or Decimal("0")
        code = (a.currency or settings.FX_BASE_CURRENCY).upper()
        rate = rates.get(code, Decimal("1"))
        v_base = (amount * rate).quantize(Decimal("0.01"))
        base_total += v_base
        acc_labels.append(a.name)
        acc_values_base.append(float(v_base))

    def sum_in_base(qs) -> Decimal:
        total = Decimal("0")
        for row in qs.values("account__currency").annotate(total=Sum("amount")):
            code = (row["account__currency"] or settings.FX_BASE_CURRENCY).upper()
            rate = rates.get(code, Decimal("1"))
            total += (row["total"] * rate).quantize(Decimal("0.01"))
        return total

    income = sum_in_base(month_tx.public().filter(type=Transaction.TransactionType.INCOME))
    expenses = sum_in_base(month_tx.filter(type=Transaction.TransactionType.EXPENSE))
    net = income - expenses

    top_cats_qs = (month_tx.filter(type=Transaction.TransactionType.EXPENSE)
    .values("category__name")
    .annotate(total=Sum("amount"))
    .order_by("-total")[:5])
    total_exp = expenses or Decimal("0")
    top_categories = [{
        "name": row["category__name"] or "—",
        "total": row["total"],
        "percent": float((row["total"] / total_exp) * 100) if total_exp else 0.0,
    } for row in top_cats_qs]

    budgets_qs = (Budget.objects.select_related("category")
                  .filter(user=user, period__year=start.year, period__month=start.month)
                  .order_by("category__name"))
    spends_map = {row["category_id"]: row["total"]
                  for row in month_tx.filter(type=Transaction.TransactionType.EXPENSE)
                  .values("category_id").annotate(total=Sum("amount"))}
    budgets = []
    for b in budgets_qs:
        spent = spends_map.get(b.category_id, Decimal("0"))
        limit = b.limit or Decimal("0")
        denom = limit if limit else Decimal("0.01")
        progress = float((spent / denom) * 100) if denom else 0.0
        budgets.append({"obj": b, "spent": spent, "progress": progress})

    recent = (
        Transaction.objects
        .filter(account__user=user)
        .public()
        .select_related("account", "category")
        .order_by("-date", "-pk")[:10]
    )

    return {
        "accounts": accounts_qs,
        "base_total": base_total,
        "total_balance": base_total,
        "accounts_chart": {"labels": acc_labels, "values": acc_values_base, "total": float(base_total)},
        "income": income, "expenses": expenses, "net": net,
        "top_categories": top_categories,
        "budgets": budgets,
        "recent": recent,
        "rates": rates,
    }
