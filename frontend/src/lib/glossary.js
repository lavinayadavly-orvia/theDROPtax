// Glossary of CFO-Ready Financial & Clinical Terms for the DROP Tax platform.
// Therapy-area-agnostic: clinical endpoint definitions come from the Therapy
// Area Registry (lib/therapyAreas.js); this file covers the economic model +
// generic clinical concepts.

export const GLOSSARY = {
  // Primary Liability Terms
  unfundedExposure: {
    term: "Unfunded Exposure",
    short: "Hidden liability risk if therapy fails",
    full: "The estimated cost the patient or family bears for downstream complications if the therapy fails or becomes unaffordable. Calculated as (Probability of a downstream event) × (Cost of that event)."
  },

  totalLiability: {
    term: "Total Liability",
    short: "Complete downstream risk exposure",
    full: "The sum of all potential downstream costs associated with treatment failure: the expected clinical-event cost, lost productivity, and adverse-event management. Formula: (Event Probability × Event Cost) + (Productivity Loss × Wage) + Adverse-Event Cost."
  },

  // Probability & Risk Terms
  eventProbability: {
    term: "Event Probability",
    short: "Downstream event / failure proxy",
    full: "A relative proxy (0–1) for the likelihood of a downstream clinical event or treatment failure, derived from the indication's primary endpoint via the Therapy Area Registry. Higher endpoint efficacy → lower event probability. Not a raw event rate — a normalised comparator for the value model."
  },

  riskWeightedCostIndex: {
    term: "Risk-Weighted Cost Index",
    short: "Liability-adjusted cost ratio",
    full: "The ratio of total downstream liability to base drug cost. Values >1.0x indicate significant hidden costs beyond the list price."
  },

  // Cost Components
  eventCost: {
    term: "Event Cost",
    short: "Expected downstream event cost",
    full: "Expected cost of the therapy-area-specific downstream event (e.g. a cardiovascular event, stroke disability, or fracture). Calculated as regional event cost × event probability."
  },

  adverseEventCost: {
    term: "Adverse-Event Cost",
    short: "AE management cost",
    full: "Expected cost of managing serious adverse events relative to the comparator. Formula: (Comparator serious-AE rate × 3 × regional AE management cost). Reported only when a real AE rate is available."
  },

  productivityLoss: {
    term: "Productivity Loss",
    short: "Lost productivity cost",
    full: "Economic cost of lost work during a treatment gap or downstream event, scaled by the event probability and regional monthly income."
  },

  // Safety
  safetyRate: {
    term: "Serious AE Rate",
    short: "Serious adverse-event frequency",
    full: "Proportion of patients experiencing serious/severe adverse events. Reported only when sourced — otherwise shown as 'Data unavailable', never estimated silently."
  },

  // Clinical Endpoints (generic; specifics come from the registry)
  primaryEndpoint: {
    term: "Primary Endpoint",
    short: "The key efficacy measure for this indication",
    full: "The indication-specific primary efficacy endpoint that drives the value model — e.g. MACE hazard ratio (CV risk), % body-weight reduction (obesity), functional independence (stroke), or fracture risk reduction (osteoporosis). Defined per indication in the Therapy Area Registry."
  },

  hazardRatio: {
    term: "Hazard Ratio (HR)",
    short: "Relative risk vs comparator",
    full: "The ratio of event hazard between treatment and control arms. HR < 1.0 means the treatment reduces risk. HR = 0.80 means a 20% relative risk reduction. Used across cardiovascular, stroke, and bone-health endpoints."
  },

  notAvailable: {
    term: "Data Unavailable",
    short: "No sourced value — manual input required",
    full: "The value could not be resolved from a reliable source. The platform does not fabricate a number — enter it manually or verify against the label / trial publication."
  },

  // Pricing Terms
  effectivePatientCost: {
    term: "Effective Patient Cost",
    short: "Actual out-of-pocket cost",
    full: "The real cost to the patient after assistance programmes, co-pay support, and insurance adjustments. Varies by site of care (IPD / OPD / home)."
  },

  listPrice: {
    term: "List Price",
    short: "Published headline price",
    full: "The official price per treatment period before discounts, schemes, or assistance. Differs from the retail MRP paid at home versus the institutional/tender price used in hospital."
  },

  papScheme: {
    term: "Patient Assistance Programme",
    short: "Financial-assistance programme",
    full: "Free or discounted drug programmes offered by manufacturers. Only relevant when a real out-of-pocket coverage gap exists at the recommended site of care."
  },

  // Coverage / site-of-care
  coverageBySetting: {
    term: "Coverage by Setting",
    short: "IPD vs OPD vs Home coverage",
    full: "The same drug reimburses and prices differently by where it is given: IPD (inpatient) is usually bundled into the hospitalization claim; OPD follow-up is often conditional; home/retail is typically self-pay at full MRP — frequently far more expensive."
  },

  coverageGap: {
    term: "Coverage Gap",
    short: "Out-of-pocket jump for uncovered settings",
    full: "The difference in patient out-of-pocket cost between a covered setting and an excluded one (usually home/retail). A large gap is the primary trigger for financial assistance."
  },

  // Competitor Terms
  competitorBaseCost: {
    term: "Competitor Base Cost",
    short: "Standard of Care price",
    full: "The baseline cost of the current standard treatment, used as a benchmark to demonstrate the value proposition of the new therapy."
  },

  // Discontinuation Terms
  productivityLossMonths: {
    term: "Productivity Loss (months)",
    short: "Months lost to a downstream event",
    full: "Proxy months of productivity lost to a downstream clinical event or early discontinuation, scaled by the event probability."
  },

  discontinuationCliff: {
    term: "Discontinuation Cliff",
    short: "Financial risk of stopping early",
    full: "The spike in downstream costs when therapy is discontinued prematurely — 'saving' on drug cost often increases total cost of care due to avoidable events."
  },

  rescueCost: {
    term: "Rescue Cost",
    short: "Emergency intervention expense",
    full: "The cost of managing a patient after early discontinuation or a downstream event — emergency care and hospitalisation. Formula: a fraction of Total Liability."
  },

  // Source & Data Terms
  localHero: {
    term: "Local Hero",
    short: "Regional data priority",
    full: "Regional Centres of Excellence (e.g. AIIMS, Medanta in India) whose data is prioritised over global sources, ensuring locally relevant clinical evidence."
  },

  dataTier: {
    term: "Data Tier",
    short: "Source reliability level",
    full: "Trust hierarchy for data sources. Tier 1: FDA/EMA/NEJM/Lancet (highest); Tier 2: specialty society guidelines (ACC/AHA, ESC, ADA/EASD, NAMS, ASBMR) + PubMed; Tier 3: news sources."
  },

  confidence: {
    term: "Confidence",
    short: "Data reliability score",
    full: "How reliable the extracted data is. High (80%+): primary sources. Medium (40–80%): secondary sources. Low (<40%): estimated or derived — flagged accordingly."
  }
};

// Helper function to get tooltip content
export const getTooltip = (key) => {
  const entry = GLOSSARY[key];
  if (!entry) return null;
  return { term: entry.term, content: entry.full };
};

// Helper to get short definition
export const getShortDef = (key) => {
  const entry = GLOSSARY[key];
  return entry?.short || '';
};
