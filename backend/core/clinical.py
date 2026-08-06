"""
The clinical section — does it work, is it safe, and does that apply here.

The commercial half of this platform was built first and the clinical half sat
at one molecule out of 218, so a medical affairs user typing a drug got a price
table and nothing about the drug. This assembles the other half.

Three sources, kept apart on purpose
------------------------------------
    LABEL       what a regulator approved. Immutable, quotable, and the thing
                a written response is defended with.
    INDIA       what CDSCO approved it FOR here, which can differ from the FDA
                label — a different indication is a different claim.
    LITERATURE  what has been published since, which is where a drug's real
                profile lives and where the label is silent.

They are never merged. Where they disagree that is the finding, not a problem
to resolve — §4.2 of the criteria. A label figure and a real-world figure are
shown side by side with the difference named.

No scores are shown
-------------------
Papers are ordered for the question being asked and the reason is given in
words. "8.6 versus 7.62" implies a precision that regex-scraped abstracts
cannot support, and a composite number hides which dimension moved. The
ordering machinery still runs; only its arithmetic stays out of the output.

What is missing is stated
-------------------------
An endpoint we could not extract is reported as not extracted, never as absent
from the study, and never as zero. A paper we could not score is listed with
what was missing. "Weak" and "unchecked" must not render the same.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from core.appraisal import Intent, Region, rank
from core.literature import parse_record, search, to_study
from core.therapy_areas import resolve_indication
from core.verified_facts import VERIFIED_FACTS

# What each question is for, in the words a user would use.
QUESTIONS = [
    (Intent.EFFICACY, "Does it work", "efficacy"),
    (Intent.SAFETY, "Is it safe", "safety"),
    (Intent.ACCESS, "Does it apply to Indian patients", "applicability"),
]
# Papers shown per question. The rest stay retrievable but off the page —
# ordering is a reading aid, not a filter, so the count of what is not shown
# is always reported.
SHOWN_PER_QUESTION = 4


@dataclass
class Paper:
    title: str
    journal: Optional[str]
    year: Optional[int]
    design: Optional[str]
    n: Optional[int]
    population: Optional[str]
    population_is_proxy: bool
    applies_to_india: str
    design_evidence: Optional[str]
    endpoint_quote: Optional[str]
    cited_by: Optional[int]
    url: Optional[str]
    why_here: str
    not_extracted: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__.copy()


def _why_here(appraisal, paper) -> str:
    """The reason this paper is where it is, in the domain's own terms.

    Written from the dimensions that actually moved it rather than from the
    score, so a reader can disagree with the reasoning instead of the number.
    """
    bits = []
    c = appraisal.components
    if c.get("endpoint") == 10.0:
        bits.append("reports a hard clinical outcome")
    elif c.get("endpoint") == 6.0:
        bits.append("reports a surrogate measure")
    if paper.n.value:
        bits.append(f"N={paper.n.value:,}")
    if paper.followup_years.value:
        bits.append(f"{paper.followup_years.value:g} year follow-up")
    # Where the population came from an author affiliation rather than the
    # text, say so. An Indian author group publishing a global meta-analysis
    # is not an Indian study, and "studied in the target population" would be
    # a much stronger claim than the evidence supports.
    if paper.cohort_is_proxy:
        bits.append("authors based in the target region — population not stated")
    elif appraisal.proximity >= 1.0:
        bits.append("studied in the target population")
    elif appraisal.proximity <= 0.20:
        bits.append("population distant from India")
    if paper.rigor.quote:
        bits.append(paper.rigor.quote.replace("Methods stated: ", ""))
    if appraisal.score is None and appraisal.partial_score is not None:
        bits.append(f"ranked on {len(appraisal.scored_on)} of 5 dimensions")
    return "; ".join(bits) or "no dimension could be established"


def label_baseline(molecule: str) -> Dict[str, Any]:
    """What the regulator approved, with the sentence it was read from.

    Returns found=False rather than an empty shell when we hold nothing — a
    missing label is a gap in our verification, not an absence of label.
    """
    entry = VERIFIED_FACTS.get((molecule or "").strip().lower())
    if not entry:
        return {"found": False,
                "note": (f"No verified label facts held for {molecule}. "
                         f"verify_from_dailymed.py checked 50 innovators; only "
                         f"inclisiran was persisted, so this is a gap in our "
                         f"records rather than in the label.")}
    facts = entry.get("facts", {})
    out = {"found": True, "molecule": entry.get("molecule"), "facts": {}}
    for key, f in facts.items():
        if not isinstance(f, dict):
            continue
        out["facts"][key] = {
            "value": f.get("value"),
            "source": f.get("source_name"),
            "url": f.get("source_url"),
            "retrieved": f.get("retrieved"),
            "quote": f.get("quote"),
        }
    return out


def india_indication(approval: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """What CDSCO approved it for here. A different indication is a different claim."""
    if not approval or not approval.get("found"):
        return {"found": False,
                "note": (approval or {}).get("note",
                         "Not found in the CDSCO registers.")}
    return {
        "found": True,
        "first_approval": approval.get("first_approval_date"),
        "indications": approval.get("india_indications", []),
        "only_as_combination": approval.get("only_as_combination"),
        "source": approval.get("source_name"),
        "url": approval.get("source_url"),
    }


def evidence_for(molecule: str, indication: Optional[str],
                 region: Region = Region.INDIA,
                 fetch=None, page_size: int = 25,
                 since_year: Optional[int] = 2015) -> Dict[str, Any]:
    """Retrieve once, then order the same papers for each question.

    The same set is re-ranked rather than re-fetched, because the point is that
    one body of evidence answers different questions differently — re-querying
    per question would hide that.
    """
    kwargs = {"page_size": page_size, "since_year": since_year}
    if fetch is not None:
        kwargs["fetch"] = fetch
    records = search(molecule, indication, **kwargs)
    papers = [parse_record(r) for r in records]
    by_id = {p.study_id: p for p in papers}
    studies = [to_study(p) for p in papers]

    views = {}
    for intent, question, key in QUESTIONS:
        out = rank(studies, intent, region)
        shown = []
        for a in out["ranked"][:SHOWN_PER_QUESTION]:
            p = by_id.get(a.study_id)
            if not p:
                continue
            shown.append(Paper(
                title=p.title,
                journal=p.journal,
                year=p.year,
                design=p.design_label or None,
                design_evidence=p.shape.quote,
                n=p.n.value,
                population=p.cohort.value,
                population_is_proxy=p.cohort_is_proxy,
                applies_to_india=a.proximity_tier,
                endpoint_quote=p.endpoint.quote,
                cited_by=p.cited_by,
                url=p.source_url,
                why_here=_why_here(a, p),
                not_extracted=p.extraction_gaps,
            ).to_dict())
        views[key] = {
            "question": question,
            "papers": shown,
            "retrieved": out["total_considered"],
            "ordered": len(out["ranked"]),
            "not_orderable": len(out["unscored"]),
            "not_shown": max(0, len(out["ranked"]) - len(shown)),
            "note": ("Ordered for this question. Nothing is filtered out — the "
                     "same papers reorder when the question changes."),
        }

    # Indian evidence is called out because it is the reason a 500-patient
    # local study can matter more here than a 5,000-patient foreign one.
    # Only papers whose TEXT names the population — an affiliation proxy is
    # not an Indian study and must not be counted as one.
    local = [p.title for p in papers
             if p.cohort.value == "south_asian" and not p.cohort_is_proxy]
    proxy = [p.title for p in papers
             if p.cohort.value == "south_asian" and p.cohort_is_proxy]
    return {
        "views": views,
        "papers_retrieved": len(papers),
        "indian_papers": local,
        "indian_authors_only": proxy,
        "source_name": "Europe PMC",
    }


def clinical_section(drug: Dict[str, Any], indication: Optional[str] = None,
                     approval: Optional[Dict[str, Any]] = None,
                     region: Region = Region.INDIA,
                     fetch=None) -> Dict[str, Any]:
    """The whole clinical half for one (drug x indication)."""
    molecule = (drug.get("name") or "").split("+")[0].strip()
    indication = indication or drug.get("primary_indication")
    entry = resolve_indication(indication)

    endpoints = None
    if entry:
        endpoints = {
            "primary": entry["primary_endpoint"]["label"],
            "unit": entry["primary_endpoint"].get("unit"),
            "direction": entry["primary_endpoint"].get("direction"),
            "definition": entry["primary_endpoint"].get("definition"),
            "secondary": [s["label"] for s in entry.get("secondary_endpoints", [])],
            "safety": entry.get("safety_label"),
        }

    section = {
        "molecule": drug.get("name"),
        "indication": indication,
        "indication_in_registry": bool(entry),
        "what_matters_here": endpoints,
        "label": label_baseline(molecule),
        "india_approval": india_indication(approval),
        "evidence": evidence_for(molecule, indication, region, fetch=fetch),
        "gaps": [],
    }

    if not entry:
        section["gaps"].append(
            f"'{indication}' is not in the therapy-area registry, so there is no "
            f"agreed primary endpoint to read the evidence against.")
    if not section["label"]["found"]:
        section["gaps"].append(section["label"]["note"])
    if not section["india_approval"]["found"]:
        section["gaps"].append(
            "No CDSCO approval record — which is not evidence it is unapproved here.")
    if not section["evidence"]["indian_papers"]:
        section["gaps"].append(
            "No paper in this set reports an Indian population. Everything shown "
            "is a proxy, and the applicability tier on each paper says how close.")
    return section
