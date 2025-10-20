from dataclasses import dataclass
from datetime import date
from django.db import transaction
from fin_mate.models import Budget
from fin_mate.services.dates import prev_month


@dataclass
class CopyResult:
    created: int
    target: date
    prev: date

@transaction.atomic
def copy_month(user, target: date) -> CopyResult:
    prev = prev_month(target)

    existing = set(Budget.objects
        .filter(user=user, period__year=target.year, period__month=target.month)
        .values_list("category_id", flat=True))

    prev_rows = Budget.objects.filter(
        user=user, period__year=prev.year, period__month=prev.month
    ).values("category_id", "limit", "notes")

    to_create = [
        Budget(user=user,
               category_id=row["category_id"],
               limit=row["limit"],
               notes=row["notes"],
               period=target)
        for row in prev_rows
        if row["category_id"] not in existing
    ]
    Budget.objects.bulk_create(to_create, ignore_conflicts=True)
    return CopyResult(created=len(to_create), target=target, prev=prev)
