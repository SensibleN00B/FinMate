from datetime import date


def first_day(dt: date) -> date:
    return dt.replace(day=1)


def prev_month(first_day: date) -> date:
    return (
        first_day.replace(year=first_day.year - 1, month=12)
        if first_day.month == 1
        else first_day.replace(month=first_day.month - 1)
    )
