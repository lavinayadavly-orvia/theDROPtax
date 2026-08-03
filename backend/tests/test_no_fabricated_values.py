"""
Guards against the platform inventing numbers.

Each test here corresponds to a real defect found in review, where a
plausible-looking figure was manufactured and shown to the user as fact.
"""
import os
import sys
import inspect
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest


def _source_of(func):
    return inspect.getsource(func)


def test_no_generic_pap_scheme_is_auto_applied():
    """The engine halved every out-of-pocket drug by auto-applying "Buy 1 Get 1 Free".

    A scheme may only be applied when the drug record names a verified one.
    """
    import server
    src = _source_of(server.calculate_period_costs)
    # The old defect: picking a scheme purely by ranking the generic table.
    assert "min(region_paps" not in src, "A generic PAP scheme is being auto-selected again"
    assert "drug_pap_code" in src, "Scheme selection must be gated on the drug's verified code"


def test_regional_price_returns_none_when_unresolved():
    """get_regional_price used to fall back to a flat 15,000/month for anything unknown."""
    import server
    src = _source_of(server.get_regional_price)
    assert '"monthly_price": None' in src, "Unresolved prices must be None, not a default figure"


def test_pap_and_dossier_refuse_without_a_price():
    """Both endpoints previously substituted a 1,000,000 headline price."""
    import server
    for func in (server.recommend_pap, server.generate_dossier):
        src = _source_of(func)
        assert "1000000" not in src, f"{func.__name__} still has a fabricated default price"
        assert "422" in src, f"{func.__name__} must refuse rather than invent a price"


def test_value_engine_returns_none_without_inputs():
    """No primary endpoint => no fabricated event probability or liability."""
    import server
    out = server.calculate_value_engine(None, "Heart Failure", None, "IN")
    assert out["event_probability"] is None
    assert out["c_event"] is None
    assert out["total_liability"] is None
    assert out["data_incomplete"] is True


def test_seeder_does_not_invent_safety_rates():
    """The workbook has no safety data; per-category AE rates were being invented."""
    src = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "seed_from_workbook.py")).read()
    assert '"drug_severe_ae_rate": None' in src
    assert '"competitor_severe_ae_rate": None' in src
    assert not re.search(r"toxic_rate\s*=\s*0\.\d", src), "Per-category AE rates are being fabricated again"


def test_seeder_does_not_invent_prices():
    """Missing prices were being replaced with a flat 100."""
    src = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "seed_from_workbook.py")).read()
    assert "else 100.0" not in src, "Missing prices are being backfilled with a default again"
