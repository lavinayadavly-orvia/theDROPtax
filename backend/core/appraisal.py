"""
Dynamic Evidence Appraisal Engine — PRD v1.3.0 §4.3 and §5.1.

A fixed hierarchy (RCT > PSM > cohort) is wrong because it cannot know what is
being asked. A 5-year propensity-matched registry of 45,000 patients is better
evidence for a rare safety signal than an 18-month trial of 1,561; the same
trial is better evidence for a regulatory efficacy claim. So the weights move
with the question, not the study.

    Appraisal Score(i,c) = w_shape(c)·S + w_size(c)·P + w_endpoint(c)·E
                         + w_rigor(c)·R + w_relevance(c)·A

What this engine does NOT do
---------------------------
It does not filter. The score sets ORDER and EMPHASIS; every study stays
visible, the active weight profile is returned alongside the ranking so the
user can see what drove it, and switching intent re-orders in place. A study
is never dropped because it scored low — only because it was never retrieved,
which is a different fact and is reported separately.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class Intent(str, Enum):
    """Query context c. Drives the weight profile."""
    SAFETY = "safety"
    EFFICACY = "efficacy"
    ACCESS = "access"


class Region(str, Enum):
    INDIA = "IN"
    SINGAPORE = "SG"
    UAE = "AE"


# ── §4.3 weight profiles ──────────────────────────────────────────────────
# Each profile sums to 1.0. Sourced from the PRD calibration cases, not chosen
# here; changing them changes documented behaviour and should update the PRD.
WEIGHT_PROFILES: Dict[Intent, Dict[str, float]] = {
    Intent.SAFETY:   {"shape": 0.10, "size": 0.40, "endpoint": 0.05, "rigor": 0.20, "relevance": 0.25},
    Intent.EFFICACY: {"shape": 0.30, "size": 0.10, "endpoint": 0.35, "rigor": 0.20, "relevance": 0.05},
    Intent.ACCESS:   {"shape": 0.10, "size": 0.20, "endpoint": 0.10, "rigor": 0.25, "relevance": 0.35},
}

INTENT_LABELS = {
    Intent.SAFETY:   "Safety & Rare Events",
    Intent.EFFICACY: "Primary Efficacy & Outcomes",
    Intent.ACCESS:   "Regional Market Access",
}


# ── §5.1 Ethno-geographic proximity (A) ───────────────────────────────────
# Tier 1 = 1.00 · Tier 2A = 0.75 · Tier 2B = 0.45 · Tier 3 = 0.20
PROXIMITY: Dict[Region, Dict[str, float]] = {
    Region.INDIA: {
        "south_asian": 1.00,           # India, Pakistan, Bangladesh, Sri Lanka
        "south_asian_diaspora": 0.75,  # e.g. UK Biobank South Asian subgroup
        "middle_eastern": 0.45,
        "east_asian": 0.45,
        "se_asian": 0.45,
        "western": 0.20,
        "african": 0.20,
    },
    Region.SINGAPORE: {
        "singaporean": 1.00,
        "east_asian": 0.75,
        "south_asian": 0.75,
        "se_asian": 0.45,
        "middle_eastern": 0.20,
        "western": 0.20,
        "african": 0.20,
    },
    Region.UAE: {
        "gcc_arab": 1.00,
        "mena": 0.75,
        "south_asian_expat": 0.75,
        "south_asian": 0.75,           # large UAE expat population
        "east_asian": 0.20,
        "western": 0.20,
        "african": 0.20,
    },
}
TIER3_DEFAULT = 0.20    # unknown cohort is treated as the most distant, never better


@dataclass
class Study:
    """A candidate paper. Component scores are 0-10 properties of the study.

    Scores absent from the source stay None; the engine reports the study as
    unscorable rather than substituting a value.
    """
    study_id: str
    title: str
    shape: Optional[float] = None       # S — internal validity / design controls
    exposure_years: Optional[float] = None   # raw patient-years (N x follow-up)
    endpoint: Optional[float] = None    # E — hard outcome vs surrogate
    rigor: Optional[float] = None       # R — bias control, PSM, pre-registration
    cohort: Optional[str] = None        # ethnicity/geography key for A
    # Descriptive, carried through for display
    design: Optional[str] = None
    n: Optional[int] = None
    followup_years: Optional[float] = None
    source_url: Optional[str] = None
    year: Optional[int] = None


@dataclass
class Appraisal:
    study_id: str
    title: str
    score: Optional[float]
    components: Dict[str, Optional[float]]
    weights: Dict[str, float]
    contributions: Dict[str, Optional[float]]
    proximity: float
    proximity_tier: str
    warning_badge: Optional[str]
    unscorable_reason: Optional[str] = None
    display: Dict[str, Any] = field(default_factory=dict)
    # Partial appraisal — see partial_score below. `score` stays None whenever
    # anything is missing, so the strict contract is unchanged.
    partial_score: Optional[float] = None
    scored_on: List[str] = field(default_factory=list)
    missing: List[str] = field(default_factory=list)
    weight_mass: Optional[float] = None
    basis_note: Optional[str] = None

    @property
    def effective_score(self) -> Optional[float]:
        """What to order by: the full score when we have it, else the partial."""
        return self.score if self.score is not None else self.partial_score


# A partial score is only offered when the dimensions we DID extract carry at
# least this share of the intent's weight. Below it, the surviving dimensions
# say too little about the question being asked — a paper known only by its
# endpoint is not thereby a strong paper, and ranking it would imply otherwise.
MIN_WEIGHT_MASS = 0.60


def normalise_exposure(patient_years: Optional[float]) -> Optional[float]:
    """Patient-years to 0-10, log-scaled.

    Exposure spans orders of magnitude — a few hundred patient-years to a few
    hundred thousand — so a linear scale would let one megacohort dominate every
    comparison. 100,000 patient-years maps to 10.0.
    """
    if patient_years is None or patient_years <= 0:
        return None
    return min(10.0, max(0.0, (math.log10(patient_years) / 5.0) * 10.0))


def proximity_for(region: Region, cohort: Optional[str]) -> tuple[float, str]:
    """Return (A in 0-1, tier label) per §5.1."""
    table = PROXIMITY.get(region, {})
    key = (cohort or "").strip().lower().replace(" ", "_").replace("-", "_")
    value = table.get(key, TIER3_DEFAULT)
    if value >= 1.0:
        return value, "Tier 1 — direct local match"
    if value >= 0.75:
        return value, "Tier 2A — high ethnic proxy"
    if value >= 0.45:
        return value, "Tier 2B — moderate regional proxy"
    return value, "Tier 3 — global fallback"


def warning_badge(region: Region, tier_value: float, cohort: Optional[str],
                  title: str, n: Optional[int]) -> Optional[str]:
    """§5.2 badges. Tier 1 carries no badge — there is nothing to warn about."""
    if tier_value >= 1.0:
        return None
    who = cohort or "unspecified cohort"
    size = f"N={n:,}" if n else "N not reported"
    if tier_value >= 0.45:
        return (f"⚠️ Regional Proxy Data: direct local studies for {region.value} are "
                f"unavailable. Displaying {who} ({size}; proximity weight {tier_value:.2f}).")
    return (f"⚠️ Global Evidence Fallback: no regional or ethnic subgroup studies "
            f"identified for {region.value}. Displaying {title} ({size}; "
            f"proximity weight {tier_value:.2f}).")


def appraise(study: Study, intent: Intent, region: Region) -> Appraisal:
    """Score one study under a given intent and region."""
    weights = WEIGHT_PROFILES[intent]
    A, tier = proximity_for(region, study.cohort)
    P = normalise_exposure(study.exposure_years)

    components = {
        "shape": study.shape,
        "size": P,
        "endpoint": study.endpoint,
        "rigor": study.rigor,
        "relevance": A * 10.0,      # scale proximity onto the same 0-10 basis
    }

    missing = [k for k, v in components.items() if v is None]
    badge = warning_badge(region, A, study.cohort, study.title, study.n)

    if missing:
        # Partial data is reported as partial. Treating a missing component as
        # zero would silently penalise a study for a gap in our extraction.
        #
        # But refusing to rank anything incomplete is its own failure: real
        # abstracts routinely omit follow-up duration or carry no design label,
        # and a strict rule left 23 of 25 live papers unranked. So we score over
        # the dimensions we DID read, renormalised across their weights, and say
        # exactly which ones those were. Nothing is imputed — the missing
        # dimension is absent from the arithmetic, not filled in.
        present = [k for k, v in components.items() if v is not None]
        mass = sum(weights[k] for k in present)
        partial = None
        contributions: Dict[str, Optional[float]] = {k: None for k in components}
        note = f"not scored — missing {', '.join(missing)}"
        if mass >= MIN_WEIGHT_MASS:
            contributions = {k: round(weights[k] / mass * components[k], 3)
                             for k in present}
            partial = round(sum(contributions.values()), 2)
            note = (f"partial — scored on {', '.join(present)} "
                    f"({mass * 100:.0f}% of the weight for this question); "
                    f"not found: {', '.join(missing)}")
        return Appraisal(
            study_id=study.study_id, title=study.title, score=None,
            components=components, weights=weights,
            contributions=contributions,
            proximity=A, proximity_tier=tier, warning_badge=badge,
            unscorable_reason=note,
            display=_display(study),
            partial_score=partial, scored_on=present, missing=missing,
            weight_mass=round(mass, 3), basis_note=note,
        )

    contributions = {k: round(weights[k] * components[k], 3) for k in components}
    score = round(sum(contributions.values()), 2)
    return Appraisal(
        study_id=study.study_id, title=study.title, score=score,
        components={k: round(v, 2) for k, v in components.items()},
        weights=weights, contributions=contributions,
        proximity=A, proximity_tier=tier, warning_badge=badge,
        display=_display(study),
        scored_on=list(components), missing=[], weight_mass=1.0,
        basis_note="scored on all five dimensions",
    )


def _display(s: Study) -> Dict[str, Any]:
    return {"design": s.design, "n": s.n, "followup_years": s.followup_years,
            "year": s.year, "cohort": s.cohort, "source_url": s.source_url}


def rank(studies: List[Study], intent: Intent, region: Region) -> Dict[str, Any]:
    """Order studies for a question. Nothing is removed.

    Returns the full set plus the active profile, so the interface can show
    what drove the order and let the user change it.
    """
    results = [appraise(s, intent, region) for s in studies]
    # Fully- and partially-scored studies share one ordering, because splitting
    # them would bury a strong paper whose abstract omitted its follow-up
    # beneath a weak one that happened to state everything. Each carries its
    # basis (`scored_on`, `weight_mass`) so the reader can see what the number
    # rests on.
    scored = sorted([r for r in results if r.effective_score is not None],
                    key=lambda r: r.effective_score, reverse=True)
    unscored = [r for r in results if r.effective_score is None]
    return {
        "intent": intent.value,
        "intent_label": INTENT_LABELS[intent],
        "region": region.value,
        "active_weights": WEIGHT_PROFILES[intent],
        "ranked": scored,
        "unscored": unscored,          # shown, not discarded
        "fully_scored": sum(1 for r in scored if r.score is not None),
        "partially_scored": sum(1 for r in scored if r.score is None),
        "total_considered": len(studies),
        "note": ("Order reflects the active question. Nothing is filtered out — "
                 "change the intent to re-rank the same evidence. Entries marked "
                 "partial were scored only on the dimensions their abstract "
                 "reported; missing dimensions are excluded from the arithmetic, "
                 "never imputed."),
    }


def detect_divergence(label_value: Optional[float], rwe_value: Optional[float],
                      metric: str, unit: str = "%",
                      threshold_pct: float = 15.0) -> Optional[str]:
    """§4.2 divergence callout.

    Surfaces the gap between the registered label figure and real-world
    observation instead of choosing one. Returns None when either side is
    unknown — an absent value is not a disagreement.
    """
    if label_value is None or rwe_value is None or label_value == 0:
        return None
    delta = abs(label_value - rwe_value) / abs(label_value) * 100.0
    if delta < threshold_pct:
        return None
    return (f"Label reports {label_value}{unit} {metric}; real-world evidence reports "
            f"{rwe_value}{unit} — a {delta:.0f}% relative difference. Both are shown; "
            f"neither supersedes the other.")
