from __future__ import annotations
from decimal import Decimal
from datetime import timedelta
from typing import Iterable

import requests
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone


def _key(d) -> str:
    return f"fxrates:{d.isoformat()}"


def _fetch_nbu(date_):
    """
    Returns a dict {'USD': Decimal(..), ...} for a date from the NBU.
    API: https://bank.gov.ua/NBUStatService/v1/statdirectory/exchange?date=YYYYMMDD&json
    """
    url = f"https://bank.gov.ua/NBUStatService/v1/statdirectory/exchange?date={date_.strftime('%Y%m%d')}&json"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        data = r.json()
    except Exception:
        return {}

    out = {}
    for row in data:
        cc = (row.get("cc") or "").upper()
        rate = row.get("rate")
        if cc and rate is not None:
            try:
                out[cc] = Decimal(str(rate))
            except Exception:
                pass
    return out


def get_rates(codes: Iterable[str]) -> dict[str, Decimal]:
    """
    Gets rates for the required codes (and the base one), caches the result to FX_CACHE_SECONDS.
    Fallback: yesterday's cache → settings.CURRENCY_RATES.
    """
    codes = {c.upper() for c in codes if c}
    today = timezone.localdate()

    rates = cache.get(_key(today))
    if not rates:
        rates = _fetch_nbu(today)
        if not rates:
            y = today - timedelta(days=1)
            rates = cache.get(_key(y), {})
        if rates:
            cache.set(_key(today), rates, settings.FX_CACHE_SECONDS)

    rates = dict(rates)
    rates[settings.FX_BASE_CURRENCY] = Decimal("1")

    for c in codes:
        if c not in rates and c in settings.CURRENCY_RATES:
            rates[c] = Decimal(str(settings.CURRENCY_RATES[c]))

    need = codes | {settings.FX_BASE_CURRENCY}
    return {c: rates[c] for c in need if c in rates}
