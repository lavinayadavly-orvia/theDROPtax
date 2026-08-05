"""
The first branch: what kind of problem is this drug, and what is worth fetching.

Two axes, and they are independent. Conflating them is what produced a coverage
matrix for a seven-rupee tablet.

    COST        decides whether money questions exist at all. At Rs7 a tablet
                there is no payer conversation, no assistance question and no
                negotiation, for any indication. 139 of the 161 priced molecules
                in the catalogue sit there.

    INDICATION  decides which evidence applies — endpoints, which trials count,
                what "works" means. Ramipril for hypertension and ramipril for
                high cardiovascular risk differ here and nowhere else.

Exclusivity modifies the cost axis rather than forming a third one: it explains
why a price is what it is, and whether it is about to move.

The output is a fetch plan. A settled cheap generic should render three cards
quickly; an exclusive high-cost injectable earns the full treatment. Rendering
both identically is the failure this module exists to prevent.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from core.constants import REGIONAL_CONSTANTS

# Burden bands as a share of monthly household income, not absolute currency —
# the same Rs2,000 is trivial in one market and material in another, and the
# platform serves three.
#
# Bands are deliberately order-of-magnitude. Catalogue prices mostly rest on an
# assumed once-daily dose, so a drug taken three times a day costs 3x what we
# hold; wide bands mean that error rarely moves a drug across a boundary.
COST_BANDS = [
    (0.010, "none",         "No payer conversation — bought without thought"),
    (0.050, "noticeable",   "Felt, but not a barrier"),
    (0.200, "material",     "Coverage and assistance become live questions"),
    (1.000, "heavy",        "Dominates the treatment decision"),
    (float("inf"), "catastrophic", "Exceeds monthly income — unaffordable unsupported"),
]
# Below this band, money modules are not merely low-scored — they are absent.
MONEY_BANDS = {"material", "heavy", "catastrophic"}


@dataclass
class CostGate:
    monthly_cost: Optional[float] = None
    currency: str = "INR"
    monthly_income: Optional[float] = None
    burden: Optional[float] = None            # share of monthly income
    band: Optional[str] = None
    meaning: Optional[str] = None
    money_questions_live: Optional[bool] = None
    price_is_estimated: Optional[bool] = None
    band_if_dosed_three_times_daily: Optional[str] = None
    note: Optional[str] = None


@dataclass
class Classification:
    molecule: str
    indication: Optional[str]
    cost: CostGate
    exclusivity: Optional[str] = None
    us_first_approval: Optional[str] = None
    profile: str = "unclassified"
    fetch: Dict[str, bool] = field(default_factory=dict)
    reasons: List[str] = field(default_factory=list)
    issues: List[Dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        d = self.__dict__.copy()
        d["cost"] = self.cost.__dict__.copy()
        return d


def _band(burden: Optional[float]) -> tuple[Optional[str], Optional[str]]:
    if burden is None:
        return None, None
    for ceiling, name, meaning in COST_BANDS:
        if burden < ceiling:
            return name, meaning
    return None, None


def cost_gate(monthly_cost: Optional[float], region: str = "IN",
              assumes_once_daily: bool = False,
              price_is_estimated: Optional[bool] = None) -> CostGate:
    """Does a money conversation exist for this drug?

    Returns band None when the price is unknown. That is NOT the same as
    "cheap": an unpriced drug must not have its coverage and assistance
    sections silently suppressed, so money_questions_live stays None and the
    caller surfaces it as a gap.
    """
    rc = REGIONAL_CONSTANTS.get((region or "IN").upper(), REGIONAL_CONSTANTS["IN"])
    income = rc.get("monthly_salary")
    gate = CostGate(monthly_cost=monthly_cost, currency=rc.get("currency", "INR"),
                    monthly_income=income, price_is_estimated=price_is_estimated)

    if monthly_cost is None or not income:
        gate.note = ("No price resolved — cannot say whether money questions "
                     "apply. Treated as unknown, not as inexpensive.")
        return gate

    gate.burden = round(monthly_cost / income, 4)
    gate.band, gate.meaning = _band(gate.burden)
    gate.money_questions_live = gate.band in MONEY_BANDS

    # Where a price was built by scaling a per-tablet cost to a month on an
    # assumed once-daily dose, three-times-daily dosing triples it and can move
    # the band. This keys on that specific assumption, NOT on price_is_estimated
    # generally: inclisiran's price is estimated because no verified India price
    # exists, and it is dosed twice a year — warning that it might be taken
    # three times a day is gibberish.
    if assumes_once_daily:
        worse, _ = _band(round(monthly_cost * 3 / income, 4))
        if worse and worse != gate.band:
            gate.band_if_dosed_three_times_daily = worse
            gate.note = (f"Price assumes once-daily dosing. At three times daily "
                         f"this drug reaches '{worse}', where money questions apply.")
    return gate


def classify(molecule: str, indication: Optional[str],
             monthly_cost: Optional[float], region: str = "IN",
             exclusivity: Optional[str] = None,
             us_first_approval: Optional[str] = None,
             price_is_estimated: Optional[bool] = None,
             indication_mapped: Optional[bool] = None,
             treatment_model: Optional[str] = None,
             assumes_once_daily: bool = False,
             india_competition: Optional[str] = None,
             india_us_conflict: Optional[str] = None) -> Classification:
    """Classify a (drug x indication) pair and return what to fetch for it."""
    gate = cost_gate(monthly_cost, region, assumes_once_daily, price_is_estimated)
    c = Classification(molecule=molecule, indication=indication, cost=gate,
                       exclusivity=exclusivity, us_first_approval=us_first_approval)

    money = gate.money_questions_live
    # Unknown price is treated as though money may matter. The conservative
    # direction here is to fetch and show, because hiding a coverage section
    # for a drug that turns out to be expensive is the worse failure.
    if money is None:
        money = True
        c.issues.append({"field": "price", "severity": "warning",
                         "message": "No price resolved — money sections shown "
                                    "pending a price, not suppressed."})

    if gate.band:
        c.reasons.append(
            f"Costs about {gate.burden * 100:.1f}% of monthly income — {gate.meaning.lower()}.")
    if gate.band_if_dosed_three_times_daily:
        c.reasons.append(gate.note)

    # India leads. US exclusivity is a pipeline signal — approved there means it
    # will probably arrive here — and it does NOT describe competition in this
    # market. Drugs@FDA calls tenecteplase exclusive to Genentech; Emcure sells
    # it here as Elaxim, and reporting the US position produced a false claim.
    if india_competition:
        c.reasons.append({
            "single_brand": "One Indian brand recorded — but the catalogue lists key "
                            "brands, not every brand, so treat that as a floor.",
            "few_brands": "Marketed in India by a small number of branded generics — "
                          "price competition without any exclusivity having to expire.",
            "many_brands": "Widely branded in India — price is competed down by "
                           "branded generics, not by patent expiry.",
        }[india_competition])
        if india_us_conflict:
            c.issues.append({"field": "competition", "severity": "warning",
                             "message": india_us_conflict})
    elif exclusivity is not None:
        c.reasons.append(
            "No Indian brand data. US records show "
            + {"exclusive": "no generic competition",
               "generic_few_makers": "few generic makers",
               "generic_many_makers": "many generic makers"}[exclusivity]
            + " — a pipeline signal only, which does not describe this market.")
    else:
        c.issues.append({"field": "competition", "severity": "info",
                         "message": "Competition not established in either market — "
                                    "depth not reduced on the strength of an unknown."})

    # Profile is a name for the combination, used for display, not for logic.
    # Profile names the combination for display. It reads the Indian picture
    # where we have one and falls back to the US signal only when we do not.
    contested = india_competition or {
        "exclusive": "single_brand", "generic_few_makers": "few_brands",
        "generic_many_makers": "many_brands"}.get(exclusivity)
    if money and contested == "single_brand":
        c.profile = "single_brand_high_cost"
    elif money and contested == "few_brands":
        c.profile = "concentrated_supply"
    elif money:
        c.profile = "costly_but_competed"
    elif contested == "single_brand":
        c.profile = "single_brand_low_cost"
    else:
        c.profile = "settled_generic"

    if indication_mapped is False:
        c.issues.append({"field": "indication", "severity": "info",
                         "message": f"'{indication}' is not in the therapy-area registry — "
                                    f"endpoints unavailable, other sections unaffected."})

    # A single administration given during an admission is bundled into the
    # hospitalisation claim. Coverage still applies — someone claims it — but
    # there is no recurring payment for a patient to finance or an assistance
    # programme to subsidise. Cost alone cannot see this; tenecteplase is
    # expensive AND needs none of it.
    ongoing_payment = treatment_model != "acute_single_dose"
    if not ongoing_payment:
        c.reasons.append("Given once during an admission — bundled in the "
                         "hospitalisation claim, so there is no recurring patient "
                         "payment to finance or subsidise.")

    c.fetch = {
        # Always: what the drug is and whether it works are the reason anyone came.
        "label_facts": True,
        "clinical_evidence": True,
        "brands_and_availability": True,
        # Money sections, gated by cost and by whether payment recurs.
        "coverage": bool(money),
        "assistance": bool(money) and ongoing_payment,
        "cash_flow": bool(money) and ongoing_payment,
        "price_negotiation": bool(money),
        # Competitive depth is only interesting where a contest exists.
        "competition": contested in ("single_brand", "few_brands") or bool(money),
    }
    if not money:
        c.reasons.append("Money sections omitted — at this price there is nothing "
                         "to cover, finance or negotiate.")
    return c
