"""
Pydantic models for the DROP Tax Commercial Suite.

Therapy-area-agnostic: clinical fields are generic (`primary_endpoint_*`,
`secondary_endpoints`, `*_severe_ae_rate`) and driven by the Therapy Area
Registry (core/therapy_areas.py). Pricing is denominated in generic treatment
"periods" (a period = one dispensing/dosing interval).
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
import uuid


class RegionConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    code: str
    name: str
    currency: str
    currency_symbol: str
    competitor_focus: str
    strategic_focus: str
    conversion_rate_from_inr: float


class AdverseEvent(BaseModel):
    name: str
    rate: float  # 0.0 to 1.0 - serious/severe adverse-event rate
    cost: float  # Regional management/hospitalization cost


class IndicationOption(BaseModel):
    """For multi-indication drugs"""
    indication: str
    approval_date: Optional[str] = None
    is_primary: bool = False


class Endpoint(BaseModel):
    """A single clinical endpoint value (registry-defined)."""
    key: str
    label: str
    unit: str
    direction: str = "higher_better"  # or "lower_better"
    value: Optional[float] = None      # None => data unavailable (never fabricated)
    is_estimated: bool = False
    source_url: Optional[str] = None


class DataQualityIssue(BaseModel):
    field: str
    severity: str = "warning"  # info | warning | error
    message: str


class DataQuality(BaseModel):
    """Anti-hallucination envelope: what was resolved vs missing/estimated."""
    status: str = "complete"           # complete | partial | unavailable
    missing_fields: List[str] = []
    issues: List[DataQualityIssue] = []


class CoverageSetting(BaseModel):
    """Coverage + price basis for one site of care (IPD / OPD / HOME)."""
    feasible: bool = False
    coverage: str = "unknown"          # covered | partial | conditional | excluded | unknown
    price_basis: Optional[str] = None  # institutional_tender | institutional_or_retail | retail_mrp
    patient_oop_est: Optional[float] = None
    reason: Optional[str] = None


class ApplicabilityProfile(BaseModel):
    """The 'Brain' output: which modules/metrics apply to this drug+indication."""
    model_config = ConfigDict(extra="ignore")
    treatment_model: str = "unknown"   # acute_single_dose | fixed_course | chronic_ongoing | unknown
    route: str = "unknown"             # iv_bolus | iv_infusion | sc_injection | oral | unknown
    feasible_settings: List[str] = []  # subset of [IPD, OPD, HOME]
    duration_periods: Optional[int] = None
    cost_burden_ratio: Optional[float] = None
    coverage_by_setting: Dict[str, CoverageSetting] = {}
    recommended_setting: Optional[str] = None
    coverage_gap: Dict[str, Any] = {}
    financial_assistance: Dict[str, Any] = {}
    modules: Dict[str, bool] = {}
    issues: List[DataQualityIssue] = []


class DrugProfile(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    indication: str
    indications_available: Optional[List[IndicationOption]] = []
    mechanism_of_action: str
    launch_date: Optional[str] = None
    global_price_inr: float
    regulatory_status: str

    # Route / setting metadata (feeds the applicability resolver)
    route: Optional[str] = None
    care_setting: Optional[str] = None

    # Competitor info
    competitor_name: str
    competitor_price_inr: float

    # Clinical data — generic, registry-driven
    primary_endpoint_key: Optional[str] = None
    primary_endpoint_label: Optional[str] = None
    primary_endpoint_unit: Optional[str] = None
    primary_endpoint_value: Optional[float] = None
    primary_endpoint_is_estimated: bool = False
    primary_endpoint_method: Optional[str] = None
    comparator_primary_value: Optional[float] = None
    hazard_ratio: Optional[float] = None
    secondary_endpoints: Optional[List[Dict[str, Any]]] = []

    # Safety data (serious / grade-appropriate AEs, therapy-area-agnostic)
    drug_severe_ae_rate: Optional[float] = None
    competitor_severe_ae_rate: Optional[float] = None
    drug_adverse_events: Optional[List[Any]] = []
    competitor_adverse_events: Optional[List[Any]] = []

    # Data source tracking + quality
    data_sources: Optional[Dict[str, Any]] = {}
    data_quality: Optional[DataQuality] = None
    local_hero_applied: Optional[bool] = False

    # Category
    category: Optional[str] = "CardioMetabolic"
    is_estimated: Optional[bool] = False


class DrugSearchResponse(BaseModel):
    id: str
    name: str
    indication: str
    has_multiple_indications: bool = False


class DrugSuggestion(BaseModel):
    """Drug suggestion for autocomplete"""
    name: str
    indication: str


class ValueCalculation(BaseModel):
    """Value engine result — downstream clinical-event cost vs drug cost."""
    total_liability: float
    event_probability: float           # relative downstream event/failure proxy [0,1]
    c_event: float                     # expected downstream event cost
    productivity_loss_months: float
    c_prod: float
    c_adverse_events: float            # AE management cost
    breakdown: Dict[str, float]
    currency: str
    currency_symbol: str


class PAPRecommendation(BaseModel):
    target_roi: float
    patient_wallet_monthly: float
    headline_price: float
    gap: float
    recommended_scheme: str
    effective_price: float


# ── Dynamic Pricing Engine Models (period-denominated) ──────────────────────

class PeriodData(BaseModel):
    """Cost breakdown for a single treatment period (dispensing/dosing interval)."""
    period: int
    patient_pay: float
    insurer_pay: float = 0
    govt_pay: float = 0
    is_free_period: bool = False
    notes: Optional[str] = None


class PeriodBreakdown(BaseModel):
    """Compact period breakdown for pricing."""
    period: int
    patient_pay: float
    third_party_pay: float
    is_free: bool = False


class PayerSegmentInfo(BaseModel):
    """Information about a payer segment"""
    code: str
    name: str
    description: str
    copay_percent: float
    annual_cap: Optional[float] = None
    pap_eligible: bool
    pap_advice: Optional[str] = None


class PricingModel(BaseModel):
    """Complete pricing model response"""
    segment: str
    segment_code: str
    currency: str
    currency_symbol: str
    list_price_per_period: float
    period_data: List[PeriodData]
    annual_oop_impact: float
    annual_insurer_impact: float = 0
    annual_govt_impact: float = 0
    effective_monthly_cost: float
    pap_scheme_applied: Optional[str] = None
    pap_scheme_code: Optional[str] = None
    deal_architect_advice: str
    is_price_estimated: bool = False


class PricingRequest(BaseModel):
    """Request for pricing calculation"""
    drug_name: str
    region_code: str = "IN"
    payer_segment: str = "oop"
    num_periods: int = 12


class PricingCalculation(BaseModel):
    """Full pricing calculation result"""
    drug_cost: float
    total_liability: float
    currency_symbol: str
    payer_segment: str
    periods: List[PeriodBreakdown]
    annual_patient_oop: float
    annual_third_party: float
    effective_monthly: float
    pap_scheme: Optional[str] = None


class NewsItem(BaseModel):
    title: str
    description: str
    date: str
    category: str
    source_url: Optional[str] = None
