"""
Literature & RWE agent.

The agent's job is to read what a paper states and nothing more. Most of these
tests are about what it must REFUSE to produce: a sample size it did not find,
a design it does not recognise, a population it cannot identify. Those gaps
flow into the appraisal engine as "unscorable", which is honest, rather than as
zero, which would libel the study.

No test here touches the network — retrieval is exercised through an injected
fetch so the suite stays deterministic.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from core.appraisal import Intent, Region, appraise, rank
from core.literature import (
    build_query, classify_design, detect_cohort, extract_enrollment,
    extract_followup_years, parse_record, provenance, score_endpoint,
    score_rigor, search, to_study,
)


# A realistic Europe PMC record, shaped exactly as the live API returns one.
ORION_RECORD = {
    "id": "32302303", "pmid": "32302303", "source": "MED", "pubYear": "2020",
    "title": "Two Phase 3 Trials of Inclisiran in Patients with Elevated LDL Cholesterol",
    "journalInfo": {"journal": {"title": "The New England Journal of Medicine"}},
    "pubTypeList": {"pubType": ["Randomized Controlled Trial", "Multicenter Study",
                                "Journal Article"]},
    "citedByCount": 1284, "isOpenAccess": "Y", "doi": "10.1056/NEJMoa1912387",
    "abstractText": (
        "In two double-blind, placebo-controlled trials we randomized 1561 patients "
        "with atherosclerotic cardiovascular disease. Participants in the United States "
        "and Europe received inclisiran or placebo. The primary end point was the "
        "percentage change in LDL cholesterol from baseline to day 510. Follow-up of "
        "1.5 years was completed. Inclisiran reduced LDL-C by 52%."
    ),
}

REGISTRY_RECORD = {
    "id": "40000001", "pmid": "40000001", "source": "MED", "pubYear": "2025",
    "title": "Five-year outcomes in an Indian multi-centre cohort",
    "journalInfo": {"journal": {"title": "Indian Heart Journal"}},
    "pubTypeList": {"pubType": ["Observational Study", "Multicenter Study"]},
    "citedByCount": 12, "isOpenAccess": "N",
    "abstractText": (
        "We conducted a propensity-score matched analysis of 45000 patients across "
        "Indian centres. Median follow-up was 5 years. All-cause mortality was the "
        "primary outcome."
    ),
}

THIN_RECORD = {
    "id": "999", "pmid": "999", "source": "MED", "pubYear": "2024",
    "title": "A commentary on lipid lowering",
    "pubTypeList": {"pubType": ["Editorial"]},
    "abstractText": "Lipid lowering remains important for population health.",
}


# ── Refusal to invent ─────────────────────────────────────────────────────

def test_missing_sample_size_is_none_not_a_guess():
    assert extract_enrollment("No numbers appear in this abstract.").value is None
    assert extract_enrollment(None).value is None


def test_missing_followup_is_none():
    assert extract_followup_years("A study of some patients.").value is None


def test_unrecognised_design_scores_none_not_a_default():
    """An unknown publication type must not be handed a middling score."""
    assert classify_design(["Some Novel Genre"]).value is None
    assert classify_design([]).value is None


def test_genre_labels_do_not_set_design():
    """'Review' and 'Editorial' describe the article, not its internal validity."""
    assert classify_design(["Review"]).value is None
    assert classify_design(["Editorial", "Comment"]).value is None


def test_abstract_with_no_method_claims_has_no_rigor_score():
    """A thin abstract has not earned a rigour score."""
    assert score_rigor("We looked at some patients and report results.").value is None


def test_unidentifiable_population_is_none():
    assert detect_cohort("A study of adults with high cholesterol.").value is None


def test_thin_record_is_all_gaps_and_still_parses():
    p = parse_record(THIN_RECORD)
    assert p.shape.value is None and p.n.value is None
    assert "design" in p.extraction_gaps and "sample size" in p.extraction_gaps
    assert p.title and p.source_url          # provenance survives regardless


# ── Every value carries its sentence ──────────────────────────────────────

def test_extracted_values_carry_the_sentence_they_came_from():
    p = parse_record(ORION_RECORD)
    for ex in (p.n, p.followup_years, p.endpoint, p.rigor, p.cohort):
        if ex.value is not None:
            assert ex.quote, "an extracted value must carry its source sentence"


def test_provenance_omits_what_was_not_extracted():
    prov = provenance(parse_record(THIN_RECORD))
    assert prov["source_url"] and prov["retrieved"]
    assert "sample_size" not in prov["evidence"]
    assert "sample size" in prov["not_extracted"]


# ── Reading what is stated ────────────────────────────────────────────────

def test_reads_enrollment_and_followup_from_a_real_abstract():
    p = parse_record(ORION_RECORD)
    assert p.n.value == 1561
    assert p.followup_years.value == pytest.approx(1.5, abs=0.01)


def test_design_takes_the_highest_validity_type_present():
    p = parse_record(ORION_RECORD)
    assert p.shape.value == 9.5                       # RCT beats Multicenter (7.0)
    assert "Randomised controlled trial" in p.design_label


def test_hard_outcome_outscores_surrogate():
    hard = score_endpoint("The primary outcome was all-cause mortality.")
    surrogate = score_endpoint("The primary end point was change in LDL cholesterol.")
    assert hard.value > surrogate.value


def test_a_paper_reporting_both_is_scored_on_the_hard_outcome():
    both = score_endpoint("We measured LDL cholesterol and adjudicated mortality.")
    assert both.value == 10.0


def test_rigor_rewards_stated_methods_and_penalises_weak_ones():
    strong = score_rigor("A double-blind, placebo-controlled, multicentre trial.")
    weak = score_rigor("A retrospective single-centre unadjusted review.")
    assert strong.value > weak.value


def test_south_asian_is_matched_before_generic_asian():
    """Pattern order decides the proximity tier — specificity must win."""
    assert detect_cohort("An Indian multi-centre cohort").value == "south_asian"
    assert detect_cohort("A Han Chinese population").value == "east_asian"


# ── Handoff to the appraisal engine ───────────────────────────────────────

def test_exposure_is_patient_years():
    s = to_study(parse_record(ORION_RECORD))
    assert s.exposure_years == pytest.approx(1561 * 1.5, abs=1)


def test_exposure_is_none_when_either_factor_is_missing():
    """N without follow-up is not patient-years, and must not be treated as such."""
    rec = dict(ORION_RECORD)
    rec["abstractText"] = "We randomized 1561 patients with elevated cholesterol."
    s = to_study(parse_record(rec))
    assert s.n == 1561 and s.followup_years is None and s.exposure_years is None


def test_a_gap_makes_a_study_unscorable_not_zero_scored():
    """The contract that keeps extraction failures from libelling a study."""
    a = appraise(to_study(parse_record(THIN_RECORD)), Intent.EFFICACY, Region.INDIA)
    assert a.score is None and a.unscorable_reason


def test_unknown_population_lands_in_tier3_never_better():
    rec = dict(ORION_RECORD)
    rec["title"] = "A trial of inclisiran"
    rec["abstractText"] = "We randomized 1561 patients. Follow-up was 1.5 years."
    a = appraise(to_study(parse_record(rec)), Intent.SAFETY, Region.INDIA)
    assert a.proximity == 0.20 and "Tier 3" in a.proximity_tier


def test_indian_registry_leads_an_india_access_query():
    """End to end: two real-shaped records, ranked for regional access."""
    studies = [to_study(parse_record(r)) for r in (ORION_RECORD, REGISTRY_RECORD)]
    out = rank(studies, Intent.ACCESS, Region.INDIA)
    assert out["ranked"][0].study_id == "40000001"


def test_hard_endpoint_observational_study_can_beat_a_surrogate_endpoint_rct():
    """The anti-blanket-hierarchy behaviour, on real records.

    ORION is a randomised trial, but its endpoint is LDL-C — a surrogate. The
    registry is observational and reports all-cause mortality. Under efficacy
    weighting, endpoint hardness carries 0.35 against design's 0.30, so the
    registry leads. "RCT beats observational" is exactly the blanket rule this
    engine exists to refuse.
    """
    studies = [to_study(parse_record(r)) for r in (ORION_RECORD, REGISTRY_RECORD)]
    out = rank(studies, Intent.EFFICACY, Region.INDIA)
    assert out["ranked"][0].study_id == "40000001"
    assert out["ranked"][0].components["endpoint"] == 10.0
    assert out["ranked"][1].components["endpoint"] == 6.0


def test_with_endpoint_held_equal_the_randomised_design_leads_on_efficacy():
    """Isolating design: give the registry a surrogate endpoint too, and the
    trial's internal validity is what decides the efficacy ordering."""
    surrogate_registry = dict(REGISTRY_RECORD)
    surrogate_registry["abstractText"] = (
        "We conducted a propensity-score matched analysis of 45000 patients across "
        "Indian centres. Median follow-up was 5 years. The primary outcome was the "
        "percentage change in LDL cholesterol."
    )
    studies = [to_study(parse_record(r)) for r in (ORION_RECORD, surrogate_registry)]
    ranked = rank(studies, Intent.EFFICACY, Region.INDIA)["ranked"]
    assert [r.components["endpoint"] for r in ranked] == [6.0, 6.0]   # like for like
    assert ranked[0].study_id == "32302303"


# ── Retrieval ─────────────────────────────────────────────────────────────

def test_query_restricts_to_indexed_records_with_abstracts():
    q = build_query("Inclisiran", "Hypercholesterolemia", since_year=2023)
    assert "HAS_ABSTRACT:Y" in q and "SRC:MED" in q and "2023-01-01" in q
    assert '"Inclisiran"' in q


def test_search_uses_the_injected_fetch_and_never_the_network():
    calls = []

    def fake_fetch(url, timeout=30):
        calls.append(url)
        return {"resultList": {"result": [ORION_RECORD]}}

    out = search("Inclisiran", "Hypercholesterolemia", fetch=fake_fetch)
    assert len(out) == 1 and calls and "europepmc" in calls[0]


def test_search_tolerates_an_empty_result_set():
    out = search("Nonexistentmolecule", fetch=lambda url, timeout=30: {})
    assert out == []


# ── Citation count is shown, not scored ───────────────────────────────────

def test_citation_count_is_carried_but_never_enters_the_score():
    """A well-cited paper is surfaced as well-cited. It does not become better
    evidence — the five dimensions are calibrated and a sixth would break them."""
    low = dict(ORION_RECORD, citedByCount=0)
    high = dict(ORION_RECORD, citedByCount=99999)
    a = appraise(to_study(parse_record(low)), Intent.EFFICACY, Region.INDIA)
    b = appraise(to_study(parse_record(high)), Intent.EFFICACY, Region.INDIA)
    assert a.score == b.score
    assert provenance(parse_record(high))["cited_by"] == 99999


# ── Structured-abstract markup ────────────────────────────────────────────

def test_html_headings_are_stripped_before_extraction():
    """Europe PMC serves structured abstracts as HTML. Left in, the section
    heading glues onto the sentence and ships inside the provenance quote."""
    from core.literature import strip_markup
    out = strip_markup("<h4>Methods and results</h4>We analyzed 32 patients.")
    assert "<h4>" not in out and "Methods and results" in out


def test_markup_does_not_leak_into_a_provenance_quote():
    rec = dict(ORION_RECORD)
    rec["abstractText"] = ("<h4>Methods</h4>We randomized 1561 patients. "
                           "<h4>Results</h4>Follow-up was 1.5 years.")
    p = parse_record(rec)
    assert p.n.value == 1561
    assert "<" not in (p.n.quote or ""), "provenance quote must not carry markup"


def test_two_digit_sample_sizes_are_read():
    """Requiring three digits silently dropped every study under 100 — a
    32-patient switch cohort is a real sample size."""
    assert extract_enrollment("We retrospectively analyzed 32 patients.").value == 32


def test_stray_small_numerals_are_still_rejected():
    """The >= 10 floor is what keeps arm labels out, not the digit count."""
    assert extract_enrollment("Patients received 2 doses of the drug.").value is None


def test_week_scale_followup_is_read():
    v = extract_followup_years("After 24 weeks of follow-up, LDL-C fell.").value
    assert v == pytest.approx(24 / 52, abs=0.01)


# ── Authors, journal, population, funding: the four that matter ───────────

AUTHORED = {
    "id": "40884558", "pmid": "40884558", "source": "MED", "pubYear": "2026",
    "title": "Inclisiran-based treatment strategy in hypercholesterolaemia",
    "journalInfo": {"journal": {"title": "European heart journal"}},
    "pubTypeList": {"pubType": ["Journal Article"]},
    "authorList": {"author": [
        {"fullName": "Landmesser U", "authorAffiliationDetailsList": {
            "authorAffiliation": [{"affiliation": "Deutsches Herzzentrum, Berlin, Germany"}]}},
        {"fullName": "Laufs U"}, {"fullName": "Schatz U"}]},
    "grantsList": {"grant": [{"agency": "Novartis Pharma"}]},
    "abstractText": ("In this double-blind, placebo-controlled study we randomized "
                     "898 patients. LDL cholesterol fell at 12 months."),
}

INDIAN_TEXT = dict(AUTHORED, id="1", pmid="1",
                   title="Inclisiran in Indian patients with ASCVD",
                   authorList={"author": [{"fullName": "A B", "authorAffiliationDetailsList": {
                       "authorAffiliation": [{"affiliation": "Dept of Cardiology, Boston, USA"}]}}]})


def test_authors_are_extracted():
    """They were not extracted at all before — a straight omission."""
    p = parse_record(AUTHORED)
    assert p.authors["count"] == 3
    assert p.authors["first"] == "Landmesser U"
    assert p.authors["senior"] == "Schatz U"


def test_journal_is_captured():
    assert parse_record(AUTHORED).journal == "European heart journal"


def test_design_falls_back_to_the_abstract_when_pubtype_is_uninformative():
    """'Journal Article' says nothing about internal validity, but the abstract
    describes the design plainly. Reading both lifted coverage from ~5/25 to 14/25."""
    p = parse_record(AUTHORED)
    assert p.shape.value == 9.5
    assert "from text" in p.design_label


def test_a_recognised_pubtype_still_wins_over_the_text():
    rec = dict(AUTHORED, pubTypeList={"pubType": ["Observational Study"]})
    p = parse_record(rec)
    assert "Publication type" in p.design_label


def test_population_falls_back_to_affiliation_and_is_marked_a_proxy():
    """Affiliation says where the authors work, not who was enrolled."""
    rec = dict(AUTHORED, title="Inclisiran outcomes")
    rec["abstractText"] = "We randomized 898 patients and measured LDL cholesterol."
    p = parse_record(rec)
    assert p.cohort.value == "western"
    assert p.cohort_is_proxy is True
    assert "not stated enrolment" in p.cohort.quote


def test_a_stated_population_beats_the_affiliation_proxy():
    """Indian patients studied by a Boston department are an Indian cohort."""
    p = parse_record(INDIAN_TEXT)
    assert p.cohort.value == "south_asian"
    assert p.cohort_is_proxy is False


def test_funding_is_captured_where_declared():
    p = parse_record(AUTHORED)
    assert p.funding.value == ["Novartis Pharma"]


def test_no_funding_declared_is_not_an_empty_claim():
    p = parse_record(THIN_RECORD)
    assert p.funding.value is None
    assert "funding" not in provenance(p)["evidence"]


def test_a_record_with_no_authors_or_journal_still_parses():
    p = parse_record(THIN_RECORD)
    assert p.authors["count"] is None and p.journal is None
    assert p.source_url
