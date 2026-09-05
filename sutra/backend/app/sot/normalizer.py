"""
sot/normalizer.py — Canonical form for numbers, units, currency, dates.
The grounding check in validation/grounding.py is only as good as this file.
"""
from __future__ import annotations
import re
from app.core.schemas import Quantity, DateSpan


# Indian number system
_CRORE  = 10_000_000
_LAKH   = 100_000
_THOUSAND = 1_000

_CURRENCY_MAP = {
    'rs': 'INR', 'rs.': 'INR', 'inr': 'INR',
    'rupee': 'INR', 'rupees': 'INR',
    '$': 'USD', 'usd': 'USD',
    '€': 'EUR', 'eur': 'EUR',
    '£': 'GBP', 'gbp': 'GBP',
}

_CRORE_RE  = re.compile(r'([\d,\.]+)\s*crore', re.IGNORECASE)
_LAKH_RE   = re.compile(r'([\d,\.]+)\s*lakh', re.IGNORECASE)
_PERCENT_RE = re.compile(r'([\d,\.]+)\s*%')
_NUM_RE     = re.compile(r'[\d,]+(?:\.\d+)?')


def _parse_float(s: str) -> float:
    return float(s.replace(',', ''))


def normalize_number(raw: str) -> Quantity | None:
    """
    Convert a raw numeric string to a Quantity with canonical value.
    Handles Indian system (lakh, crore), percentage, plain numbers.
    """
    raw = raw.strip()
    m = _CRORE_RE.search(raw)
    if m:
        val = _parse_float(m.group(1)) * _CRORE
        return Quantity(value=val, unit='INR_base', raw=raw, scale=_CRORE)
    m = _LAKH_RE.search(raw)
    if m:
        val = _parse_float(m.group(1)) * _LAKH
        return Quantity(value=val, unit='INR_base', raw=raw, scale=_LAKH)
    m = _PERCENT_RE.search(raw)
    if m:
        val = _parse_float(m.group(1))
        return Quantity(value=val, unit='percent', raw=raw, scale=1.0)
    m = _NUM_RE.search(raw)
    if m:
        val = _parse_float(m.group())
        return Quantity(value=val, unit='', raw=raw, scale=1.0)
    return None


def normalize_date(raw: str, doc_date: str | None = None) -> DateSpan | None:
    """
    Map a raw date string to an ISO DateSpan.
    Basic implementation; extend with dateparser for production.
    """
    # Try ISO format directly
    iso_re = re.compile(r'(\d{4})(?:-(\d{2})(?:-(\d{2}))?)?')
    m = iso_re.search(raw)
    if m:
        year = m.group(1)
        month = m.group(2)
        day = m.group(3)
        if day:
            iso = f'{year}-{month}-{day}'
            gran = 'day'
        elif month:
            iso = f'{year}-{month}'
            gran = 'month'
        else:
            iso = year
            gran = 'year'
        return DateSpan(iso_start=iso, granularity=gran, raw=raw)
    return None
