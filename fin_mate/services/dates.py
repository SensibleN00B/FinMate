from datetime import date
from django.utils import timezone

def first_day(dt: date) -> date:
    return dt.replace(day=1)

def prev_month(first_day: date) -> date:
    return first_day.replace(year=first_day.year - 1, month=12) if first_day.month == 1 \
           else first_day.replace(month=first_day.month - 1)

def month_range(dt: date) -> tuple[date, date]:
    start = first_day(dt)
    end = start.replace(year=start.year + 1, month=1) if start.month == 12 \
          else start.replace(month=start.month + 1)
    return start, end

def parse_period_or_today(period_str: str | None) -> date:
    if period_str:
        try:
            y, m = map(int, period_str.split("-")[:2])
            return date(y, m, 1)
        except Exception:
            pass
    return timezone.localdate().replace(day=1)
