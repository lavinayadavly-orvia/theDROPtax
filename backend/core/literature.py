"""
Literature & Real-World Evidence agent.

The appraisal engine can rank evidence but had nothing to rank: clinical
endpoints existed for one molecule out of 218, taken from a label. This module
is the retrieval half — it finds real papers, reads what they actually state,
and hands Study objects to core.appraisal.

Source
------
Europe PMC REST API (ebi.ac.uk/europepmc), which indexes MEDLINE/PubMed plus
preprints and agency reports. No API key. Chosen over the PubMed E-utilities
because its `pubType` field carries MEDLINE's own publication-type vocabulary —
"Randomized Controlled Trial", "Observational Study", "Multicenter Study" — so
study design is read from the record rather than guessed at from prose.

What is extracted, and what is not
----------------------------------
Every extractor returns (value, quote) and returns (None, None) when the value
is not explicitly stated. Nothing is inferred from context, and no dimension has
a default. That matters because of how the appraisal engine treats gaps: a
missing component makes a study *unscorable*, not zero-scored, so a paper is
never penalised for something our regex failed to find. An abstract that never
reports its sample size yields exposure=None and the study is listed as "not
scored — missing size", which is the truth.

The quote is the sentence the number came from. A figure without the sentence
that produced it is not verifiable, and this platform does not ship unverifiable
figures.

Citation count and recency are carried for display but deliberately kept OUT of
the score. The five scoring dimensions are calibrated against worked cases; a
sixth would silently invalidate that calibration. A heavily-cited paper is
surfaced as heavily-cited — it does not thereby become better evidence.
"""
from __future__ import annotations

import json
import re
import ssl
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

from core.appraisal import Study

ENDPOINT = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
ARTICLE_URL = "https://europepmc.org/article/{source}/{ident}"
USER_AGENT = "DropTax/1.0 (clinical intelligence platform; +https://github.com/lavinayadavly-orvia/theDROPtax)"


# ── Design (S) ────────────────────────────────────────────────────────────
# Mapped from MEDLINE publication types as returned by Europe PMC. These are
# internal-validity scores, NOT a ranking of usefulness: the whole point of the
# appraisal engine is that a low-S registry can outrank a high-S trial once the
# question is long-term safety. An unrecognised type scores None.
DESIGN_SHAPE: Dict[str, Tuple[float, str]] = {
    "randomized controlled trial": (9.5, "Randomised controlled trial"),
    "clinical trial, phase iv": (8.5, "Phase IV trial"),
    "clinical trial, phase iii": (9.0, "Phase III trial"),
    "clinical trial, phase ii": (8.0, "Phase II trial"),
    "clinical trial": (8.0, "Clinical trial"),
    "pragmatic clinical trial": (8.0, "Pragmatic trial"),
    "meta-analysis": (8.5, "Meta-analysis"),
    "systematic review": (8.0, "Systematic review"),
    "observational study": (6.0, "Observational study"),
    "comparative study": (6.5, "Comparative study"),
    "multicenter study": (7.0, "Multicentre study"),
}
# Types that describe the article's genre rather than a study. On their own they
# tell us nothing about internal validity, so they never set S.
NON_STUDY_TYPES = {"review", "editorial", "comment", "letter", "news",
                   "case reports", "published erratum", "preprint"}

# ── Endpoint hardness (E) ─────────────────────────────────────────────────
# A hard clinical outcome is something that happened to a patient. A surrogate
# is a measurement that predicts it. Both are legitimate; they are not equal
# evidence for a claim of clinical benefit.
HARD_ENDPOINT_TERMS = [
    "all-cause mortality", "cardiovascular death", "cv death", "mortality",
    "major adverse cardiovascular", "mace", "myocardial infarction",
    "stroke", "hospitalisation", "hospitalization", "revascularisation",
    "revascularization", "fracture", "amputation", "dialysis",
    "end-stage renal", "survival", "cardiovascular events",
]
SURROGATE_TERMS = [
    "ldl-c", "ldl cholesterol", "apob", "apolipoprotein", "lp(a)",
    "hba1c", "glycated haemoglobin", "glycated hemoglobin", "blood pressure",
    "body weight", "bone mineral density", "bmd", "egfr", "biomarker",
    "cholesterol", "triglyceride", "waist circumference",
]
HARD_ENDPOINT_SCORE = 10.0
SURROGATE_ENDPOINT_SCORE = 6.0

# ── Methodological rigour (R) ─────────────────────────────────────────────
# Each marker must be stated in the text. Rigour is built up from what the
# paper claims about its own methods, never assumed from its design label.
RIGOR_MARKERS: List[Tuple[str, float, str]] = [
    (r"\bdouble[- ]blind", 2.5, "double-blind"),
    (r"\bplacebo[- ]controlled", 2.0, "placebo-controlled"),
    (r"\bpropensity[- ](?:score[- ])?match", 2.5, "propensity-score matched"),
    (r"\bintention[- ]to[- ]treat", 1.5, "intention-to-treat"),
    (r"\bpre[- ]?(?:registered|specified)", 1.5, "pre-specified"),
    (r"\bmulti[- ]?(?:centre|center)", 1.0, "multicentre"),
    (r"\bactive[- ]comparator", 1.5, "active comparator"),
    (r"\bsingle[- ](?:centre|center)", -1.0, "single-centre"),
    (r"\bretrospective", -1.0, "retrospective"),
    (r"\bunadjusted", -1.5, "unadjusted"),
]
RIGOR_BASELINE = 5.0

# ── Population (A) ────────────────────────────────────────────────────────
# Maps free text onto the cohort keys core.appraisal.PROXIMITY expects. Order
# matters: the most specific pattern must win, so "South Asian" is tested
# before "Asian". A cohort we cannot identify stays None, and the appraisal
# engine then applies Tier 3 — the most distant tier, never the benefit of the
# doubt.
COHORT_PATTERNS: List[Tuple[str, str]] = [
    (r"\bsouth asian\b|\bindian\b|\bindia\b|\bpakistan|\bbangladesh|\bsri lank", "south_asian"),
    (r"\buk biobank\b.*\bsouth asian|\bsouth asian\b.*\bdiaspora|\bbritish south asian", "south_asian_diaspora"),
    (r"\bsingapor", "singaporean"),
    (r"\bchinese\b|\bjapan|\bkorea|\btaiwan|\beast asian\b|\bhan\b", "east_asian"),
    (r"\bthai\b|\bindonesi|\bmalaysi|\bphilippin|\bvietnam|\bsoutheast asian\b|\bse asian\b", "se_asian"),
    (r"\bemirat|\bsaudi|\bqatar|\bkuwait|\bbahrain|\boman\b|\bgcc\b|\bgulf coop", "gcc_arab"),
    (r"\bmiddle east|\bmena\b|\bnorth africa|\begypt|\bjordan|\blebanon", "mena"),
    (r"\beuropean\b|\bcaucasian\b|\bwhite\b|\bunited states\b|\bus\b|\bamerican\b|\bgerman|\bfrench|\bnordic|\bdanish|\bswedish", "western"),
    (r"\bafrican\b|\bnigeria|\bkenya|\bghana|\bsouth africa", "african"),
]


@dataclass
class Extracted:
    """A value plus the sentence it was read from. No quote, no value."""
    value: Optional[Any] = None
    quote: Optional[str] = None

    def __bool__(self) -> bool:
        return self.value is not None


@dataclass
class Paper:
    """A retrieved record, with provenance and whatever could be extracted."""
    study_id: str
    title: str
    year: Optional[int]
    journal: Optional[str]
    source_url: str
    pmid: Optional[str] = None
    doi: Optional[str] = None
    retrieved: str = field(default_factory=lambda: date.today().isoformat())
    pub_types: List[str] = field(default_factory=list)
    design_label: Optional[str] = None
    cited_by: Optional[int] = None
    open_access: bool = False
    abstract: Optional[str] = None
    # extracted, each carrying its own quote
    n: Extracted = field(default_factory=Extracted)
    followup_years: Extracted = field(default_factory=Extracted)
    endpoint: Extracted = field(default_factory=Extracted)
    rigor: Extracted = field(default_factory=Extracted)
    shape: Extracted = field(default_factory=Extracted)
    cohort: Extracted = field(default_factory=Extracted)
    extraction_gaps: List[str] = field(default_factory=list)


def strip_markup(text: Optional[str]) -> Optional[str]:
    """Europe PMC returns structured abstracts with HTML section headings
    ("<h4>Methods and results</h4>"). Left in place they corrupt the provenance
    quote and glue headings onto the sentences we match against.
    """
    if not text:
        return text
    text = re.sub(r"<h\d[^>]*>([^<]*)</h\d>", r" \1. ", text)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _sentence_containing(text: str, match_start: int) -> str:
    """The sentence a match sits in — this becomes the provenance quote."""
    start = max(text.rfind(". ", 0, match_start) + 2, 0)
    end = text.find(". ", match_start)
    end = len(text) if end == -1 else end + 1
    return re.sub(r"\s+", " ", text[start:end]).strip()[:400]


# ── Extractors ────────────────────────────────────────────────────────────

def classify_design(pub_types: List[str]) -> Extracted:
    """Highest-validity design named by the record's own publication types.

    Genre labels ("Review", "Editorial") are ignored rather than scored: an
    article being a review says nothing about internal validity.
    """
    best: Optional[Tuple[float, str]] = None
    for pt in pub_types or []:
        key = pt.strip().lower()
        if key in NON_STUDY_TYPES:
            continue
        hit = DESIGN_SHAPE.get(key)
        if hit and (best is None or hit[0] > best[0]):
            best = hit
    if best is None:
        return Extracted()
    return Extracted(best[0], f"Publication type: {best[1]}")


def extract_enrollment(text: Optional[str]) -> Extracted:
    """Sample size, only where the text states one."""
    if not text:
        return Extracted()
    # Digit count is not constrained here: a 32-patient switch cohort is a real
    # sample size, and requiring three digits silently dropped every study
    # under 100. The >= 10 floor below is what filters out arm labels and
    # stray numerals.
    patterns = [
        r"\b[Nn]\s*=\s*([\d,]{2,12})\b",
        r"\b([\d,]{2,12})\s+(?:patients|participants|subjects|adults|women|individuals)\b",
        r"\benroll(?:ed|ing)\s+([\d,]{2,12})\b",
        r"\brandomi[sz]ed\s+([\d,]{2,12})\b",
        r"\banaly[sz]ed\s+([\d,]{2,12})\b",
    ]
    for pat in patterns:
        m = re.search(pat, text)
        if m:
            try:
                value = int(m.group(1).replace(",", ""))
            except ValueError:
                continue
            # A "sample size" under 10 is almost always a subgroup count or an
            # arm label caught by accident, not the study's N.
            if value >= 10:
                return Extracted(value, _sentence_containing(text, m.start()))
    return Extracted()


def extract_followup_years(text: Optional[str]) -> Extracted:
    """Follow-up duration in years, only where stated."""
    if not text:
        return Extracted()
    patterns = [
        (r"(\d+(?:\.\d+)?)\s*[- ]?year(?:s)?\s+(?:of\s+)?follow[- ]?up", 1.0),
        (r"follow[- ]?up\s+(?:of|was|period)?\s*(?:approximately\s*)?(\d+(?:\.\d+)?)\s*years?", 1.0),
        (r"(\d+(?:\.\d+)?)\s*[- ]?month(?:s)?\s+(?:of\s+)?follow[- ]?up", 1 / 12),
        (r"follow[- ]?up\s+(?:of|was|period)?\s*(?:approximately\s*)?(\d+(?:\.\d+)?)\s*months?", 1 / 12),
        (r"(\d+(?:\.\d+)?)\s*[- ]?week(?:s)?\s+(?:of\s+)?follow[- ]?up", 1 / 52),
        (r"follow[- ]?up\s+(?:of|was|period)?\s*(?:approximately\s*)?(\d+(?:\.\d+)?)\s*weeks?", 1 / 52),
        (r"over\s+(\d+(?:\.\d+)?)\s*years?", 1.0),
        (r"over\s+(\d+(?:\.\d+)?)\s*months?", 1 / 12),
        (r"\bat\s+(?:\d+,\s*)*(\d+)\s+months\b", 1 / 12),   # "at 3, 6, and 9 months"
        (r"\b(\d+(?:\.\d+)?)\s*[- ]?year\b", 1.0),
        (r"\bday\s+(\d{3,4})\b", 1 / 365),
    ]
    for pat, factor in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            try:
                value = float(m.group(1)) * factor
            except ValueError:
                continue
            if 0 < value <= 30:
                return Extracted(round(value, 2), _sentence_containing(text, m.start()))
    return Extracted()


def score_endpoint(text: Optional[str]) -> Extracted:
    """Hard clinical outcome vs surrogate biomarker.

    A paper reporting both is scored on the hard outcome — that is the claim it
    is in a position to support.
    """
    if not text:
        return Extracted()
    low = text.lower()
    for term in HARD_ENDPOINT_TERMS:
        i = low.find(term)
        if i != -1:
            return Extracted(HARD_ENDPOINT_SCORE,
                             _sentence_containing(text, i))
    for term in SURROGATE_TERMS:
        i = low.find(term)
        if i != -1:
            return Extracted(SURROGATE_ENDPOINT_SCORE,
                             _sentence_containing(text, i))
    return Extracted()


def score_rigor(text: Optional[str]) -> Extracted:
    """Rigour from method claims the paper actually makes.

    Returns None when the text names no methodological feature at all — an
    abstract too thin to describe its methods has not earned a middling score.
    """
    if not text:
        return Extracted()
    found: List[str] = []
    total = RIGOR_BASELINE
    for pat, delta, label in RIGOR_MARKERS:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            total += delta
            found.append(label)
    if not found:
        return Extracted()
    return Extracted(max(0.0, min(10.0, total)),
                     "Methods stated: " + ", ".join(found))


def detect_cohort(text: Optional[str]) -> Extracted:
    """Population key for the proximity weight, or None if unidentifiable."""
    if not text:
        return Extracted()
    for pat, key in COHORT_PATTERNS:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return Extracted(key, _sentence_containing(text, m.start()))
    return Extracted()


# ── Retrieval ─────────────────────────────────────────────────────────────

def build_query(molecule: str, indication: Optional[str] = None,
                since_year: Optional[int] = None) -> str:
    """Europe PMC query for a molecule.

    Restricted to MEDLINE/PMC journal content with an abstract, because a record
    with no abstract yields no extractable evidence — it would arrive as a row
    of nulls and add noise without adding information.
    """
    parts = [f'"{molecule}"']
    if indication:
        parts.append(f'AND ("{indication}" OR TITLE:"{molecule}")')
    parts.append("AND (SRC:MED OR SRC:PMC)")
    parts.append("AND HAS_ABSTRACT:Y")
    if since_year:
        parts.append(f"AND (FIRST_PDATE:[{since_year}-01-01 TO 3000-12-31])")
    return " ".join(parts)


def _http_get_json(url: str, timeout: int = 30) -> Dict[str, Any]:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout,
                                context=ssl.create_default_context()) as r:
        return json.loads(r.read())


def search(molecule: str, indication: Optional[str] = None,
           page_size: int = 25, since_year: Optional[int] = None,
           fetch=_http_get_json) -> List[Dict[str, Any]]:
    """Raw Europe PMC records. `fetch` is injectable so tests never hit the network."""
    query = build_query(molecule, indication, since_year)
    url = (f"{ENDPOINT}?query={urllib.parse.quote(query)}"
           f"&format=json&pageSize={page_size}&resultType=core")
    payload = fetch(url)
    return payload.get("resultList", {}).get("result", []) or []


def parse_record(rec: Dict[str, Any]) -> Paper:
    """Turn one Europe PMC record into a Paper, extracting only what is stated."""
    pub_types = (rec.get("pubTypeList") or {}).get("pubType") or []
    if isinstance(pub_types, str):
        pub_types = [pub_types]
    abstract = strip_markup(rec.get("abstractText"))
    title = strip_markup(rec.get("title")) or "(untitled)"
    # Population is often named in the title rather than the abstract body
    haystack = f"{title}. {abstract or ''}"

    source = rec.get("source") or "MED"
    ident = rec.get("id") or rec.get("pmid") or ""
    journal = ((rec.get("journalInfo") or {}).get("journal") or {}).get("title")

    year = None
    try:
        year = int(str(rec.get("pubYear"))[:4])
    except (TypeError, ValueError):
        pass

    paper = Paper(
        study_id=str(rec.get("pmid") or ident or title[:40]),
        title=title,
        year=year,
        journal=journal,
        source_url=ARTICLE_URL.format(source=source, ident=ident),
        pmid=rec.get("pmid"),
        doi=rec.get("doi"),
        pub_types=pub_types,
        cited_by=rec.get("citedByCount"),
        open_access=str(rec.get("isOpenAccess", "N")).upper() == "Y",
        abstract=abstract,
    )
    paper.shape = classify_design(pub_types)
    paper.design_label = paper.shape.quote
    paper.n = extract_enrollment(abstract)
    paper.followup_years = extract_followup_years(abstract)
    paper.endpoint = score_endpoint(abstract)
    paper.rigor = score_rigor(abstract)
    paper.cohort = detect_cohort(haystack)

    # Record what could not be read, so the gap is visible rather than implied
    for name, ex in (("design", paper.shape), ("sample size", paper.n),
                     ("follow-up", paper.followup_years),
                     ("endpoint", paper.endpoint), ("methods", paper.rigor),
                     ("population", paper.cohort)):
        if not ex:
            paper.extraction_gaps.append(name)
    return paper


def to_study(paper: Paper) -> Study:
    """Paper -> Study for the appraisal engine.

    Exposure is patient-years: N x follow-up. If either is missing the product
    is unknown, so exposure stays None and the engine reports the study as
    unscorable on size rather than inventing a denominator.
    """
    exposure = None
    if paper.n.value is not None and paper.followup_years.value is not None:
        exposure = paper.n.value * paper.followup_years.value
    return Study(
        study_id=paper.study_id,
        title=paper.title,
        shape=paper.shape.value,
        exposure_years=exposure,
        endpoint=paper.endpoint.value,
        rigor=paper.rigor.value,
        cohort=paper.cohort.value,
        design=paper.design_label,
        n=paper.n.value,
        followup_years=paper.followup_years.value,
        source_url=paper.source_url,
        year=paper.year,
    )


def provenance(paper: Paper) -> Dict[str, Any]:
    """Every extracted figure with the sentence it came from."""
    return {
        "source_name": paper.journal or "Europe PMC",
        "source_url": paper.source_url,
        "retrieved": paper.retrieved,
        "pmid": paper.pmid,
        "doi": paper.doi,
        "evidence": {
            k: {"value": ex.value, "quote": ex.quote}
            for k, ex in (("design", paper.shape), ("sample_size", paper.n),
                          ("followup_years", paper.followup_years),
                          ("endpoint", paper.endpoint), ("rigor", paper.rigor),
                          ("population", paper.cohort))
            if ex
        },
        "not_extracted": paper.extraction_gaps,
        "cited_by": paper.cited_by,
        "open_access": paper.open_access,
    }
