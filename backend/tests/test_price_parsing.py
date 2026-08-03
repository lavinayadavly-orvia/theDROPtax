"""
Workbook price parsing — units, Indian numbering, and honest gaps.

The workbook quotes prices in mixed units ("₹10–18 / tab", "~₹1.2 lakh / dose",
"Hospital only"). The platform models cost per treatment period (a month), so
these regression tests pin the normalisation and, crucially, that a price which
cannot be derived stays None rather than being invented.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from seed_from_workbook import parse_price


def test_indian_lakh_notation_is_scaled():
    """'₹1.2 lakh' must be 120,000 — not 1.2 (which rendered as ₹1 in the UI)."""
    r = parse_price("~₹1.2 lakh / dose (twice-yearly; price later reduced)")
    assert r["unit_price"] == pytest.approx(120000)
    # Twice-yearly dosing => 120000 / 6 months
    assert r["monthly"] == 20000


def test_crore_notation_is_scaled():
    assert parse_price("₹2 crore / course")["unit_price"] == pytest.approx(20000000)


def test_per_tablet_is_converted_to_a_monthly_cost():
    """A per-tab price is not a monthly price — 150 of 218 drugs are quoted this way."""
    r = parse_price("₹10–18 / tab")
    assert r["monthly"] == 420          # midpoint 14 x 30 days
    assert r["is_estimated"] is True    # once-daily dosing is an assumption
    assert "once-daily" in r["note"]


def test_per_month_is_taken_directly_and_not_flagged():
    r = parse_price("₹14,000–27,500 / month")
    assert r["monthly"] == 20750
    assert r["is_estimated"] is False


def test_per_day_is_multiplied_out():
    assert parse_price("₹100–250 / day")["monthly"] == 5250


@pytest.mark.parametrize("text", ["Hospital only", "Premium", "Specialist", "", None])
def test_non_numeric_prices_are_not_invented(text):
    """Anti-hallucination: no number in the source => no number out."""
    r = parse_price(text)
    assert r["monthly"] is None
    assert r["unit_price"] is None
    assert r["is_estimated"] is True
    assert r["note"]


def test_unknown_dosing_frequency_reports_unit_price_but_no_monthly():
    """A per-pen price with no stated frequency cannot become a monthly cost."""
    r = parse_price("₹10,000–13,000 / pen")
    assert r["unit_price"] == pytest.approx(11500)
    assert r["monthly"] is None
    assert "frequency is not stated" in r["note"]


def test_stated_frequency_drives_the_conversion():
    weekly = parse_price("₹1,000 / injection (weekly)")
    assert weekly["monthly"] == pytest.approx(4300, rel=0.01)
    quarterly = parse_price("₹9,000 / depot (3-monthly)")
    assert quarterly["monthly"] == 3000
