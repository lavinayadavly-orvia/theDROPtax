// Therapy Area Registry (frontend mirror of backend/core/therapy_areas.py).
// Single source of truth for which endpoints/metrics apply to each indication.
// Keep in sync with the backend registry.

export const INDICATION_REGISTRY = {
  // ── CVD — Cardiology & Lipidology ──
  'cardiovascular risk reduction': {
    category: 'CVD', indication: 'Cardiovascular Risk Reduction',
    aliases: ['cv risk reduction', 'mace reduction', 'cardiovascular outcomes', 'ascvd risk reduction',
      'secondary prevention', 'post-pci', 'acute coronary syndrome', 'acs', 'antiplatelet',
      'stroke prevention', 'atrial fibrillation', 'thromboembolism', 'anticoagul', 'antithrombotic'],
    primaryEndpoint: { key: 'mace_hr', label: '3-pt MACE Risk Reduction', unit: 'HR', direction: 'lower_better',
      definition: 'Hazard ratio for 3-point Major Adverse Cardiovascular Events (CV death, MI, stroke). HR<1 means fewer events.' },
    secondaryEndpoints: [
      { key: 'cv_mortality_hr', label: 'CV Mortality HR', unit: 'HR' },
      { key: 'nnt', label: 'Number Needed to Treat', unit: 'patients' },
    ],
    safetyLabel: 'Serious AEs', hazardRatioLabel: 'MACE HR',
    treatmentModel: 'chronic_ongoing', routeDefault: 'sc_injection',
    placeholder: 'e.g., Cardiovascular Risk Reduction',
  },
  'heart failure': {
    category: 'CVD', indication: 'Heart Failure',
    aliases: ['hfref', 'hfpef', 'chronic heart failure', 'cardiac failure', 'heart-failure'],
    primaryEndpoint: { key: 'hf_event_hr', label: 'CV-death / HF-hospitalisation HR', unit: 'HR', direction: 'lower_better',
      definition: 'Hazard ratio for the composite of cardiovascular death or heart-failure hospitalisation.' },
    secondaryEndpoints: [
      { key: 'kccq', label: 'KCCQ Score Change', unit: 'points' },
      { key: 'ntprobnp', label: 'NT-proBNP Change', unit: '%' },
    ],
    safetyLabel: 'Serious AEs', hazardRatioLabel: 'HF-event HR',
    treatmentModel: 'chronic_ongoing', routeDefault: 'oral',
    placeholder: 'e.g., Heart Failure',
  },
  'hypercholesterolemia': {
    category: 'CVD', indication: 'Hypercholesterolemia / Dyslipidemia',
    aliases: ['dyslipidemia', 'dyslipidaemia', 'high cholesterol', 'ldl lowering', 'hyperlipidemia',
      'ascvd', 'familial hypercholesterolemia', 'high ldl', 'hypertriglyceridemia', 'triglyceride', 'statin', 'lipid'],
    primaryEndpoint: { key: 'ldl_reduction', label: 'LDL-C Reduction', unit: '%', direction: 'lower_better',
      definition: 'Percentage reduction in LDL cholesterol vs baseline.' },
    secondaryEndpoints: [
      { key: 'apob', label: 'ApoB Reduction', unit: '%' },
      { key: 'lpa', label: 'Lp(a) Reduction', unit: '%' },
    ],
    safetyLabel: 'Serious AEs', hazardRatioLabel: 'MACE HR',
    treatmentModel: 'chronic_ongoing', routeDefault: 'oral',
    placeholder: 'e.g., Hypercholesterolemia',
  },
  'hypertension': {
    category: 'CVD', indication: 'Hypertension',
    aliases: ['high blood pressure', 'resistant hypertension', 'htn', 'hypertensive', 'antihypertensive', 'controlled hypotension'],
    primaryEndpoint: { key: 'sbp_reduction', label: 'Systolic BP Reduction', unit: 'mmHg', direction: 'lower_better',
      definition: 'Absolute reduction in systolic blood pressure vs comparator.' },
    secondaryEndpoints: [
      { key: 'dbp_reduction', label: 'Diastolic BP Reduction', unit: 'mmHg' },
      { key: 'bp_control_rate', label: 'BP Control Rate', unit: '%' },
    ],
    safetyLabel: 'Serious AEs', hazardRatioLabel: 'CV-event HR',
    treatmentModel: 'chronic_ongoing', routeDefault: 'oral',
    placeholder: 'e.g., Hypertension',
  },

  // ── CVS — Cerebrovascular & Acute Vascular ──
  'acute ischemic stroke': {
    category: 'CVS', indication: 'Acute Ischemic Stroke',
    aliases: ['ischemic stroke', 'ischaemic stroke', 'acute stroke', 'thrombolysis stroke'],
    primaryEndpoint: { key: 'functional_independence', label: 'Functional Independence (mRS 0–2)', unit: '%', direction: 'higher_better',
      definition: 'Proportion achieving modified Rankin Scale 0–2 (functional independence) at 90 days.' },
    secondaryEndpoints: [
      { key: 'recanalization', label: 'Recanalisation Rate', unit: '%' },
    ],
    safetyLabel: 'Symptomatic ICH', hazardRatioLabel: 'Poor-outcome HR',
    treatmentModel: 'acute_single_dose', routeDefault: 'iv_bolus',
    placeholder: 'e.g., Acute Ischemic Stroke',
  },
  'acute myocardial infarction': {
    category: 'CVS', indication: 'Acute Myocardial Infarction',
    aliases: ['stemi', 'acute mi', 'heart attack', 'myocardial infarction'],
    primaryEndpoint: { key: 'reperfusion', label: 'Reperfusion / TIMI-3 Flow', unit: '%', direction: 'higher_better',
      definition: 'Proportion achieving successful reperfusion (TIMI grade 3 flow).' },
    secondaryEndpoints: [
      { key: 'mortality_90d', label: '90-day Mortality', unit: '%' },
    ],
    safetyLabel: 'Major bleeding', hazardRatioLabel: 'Mortality HR',
    treatmentModel: 'acute_single_dose', routeDefault: 'iv_bolus',
    placeholder: 'e.g., Acute Myocardial Infarction',
  },

  // ── Metabolic — Endocrinology ──
  'chronic weight management': {
    category: 'Metabolic', indication: 'Chronic Weight Management',
    aliases: ['obesity', 'weight management', 'weight loss', 'overweight'],
    primaryEndpoint: { key: 'weight_reduction', label: 'Mean Body-Weight Reduction', unit: '%', direction: 'higher_better',
      definition: 'Mean percentage body-weight reduction vs baseline.' },
    secondaryEndpoints: [
      { key: 'responder_10', label: '≥10% Weight-loss Responders', unit: '%' },
      { key: 'waist', label: 'Waist Circumference Change', unit: 'cm' },
    ],
    safetyLabel: 'Serious / GI AEs', hazardRatioLabel: null,
    treatmentModel: 'chronic_ongoing', routeDefault: 'sc_injection',
    placeholder: 'e.g., Chronic Weight Management (Obesity)',
  },
  'type 2 diabetes': {
    category: 'Metabolic', indication: 'Type 2 Diabetes',
    aliases: ['t2dm', 't2d', 'diabetes mellitus type 2', 'diabetes', 'glycaemic', 'glycemic',
      'insulin', 'prandial insulin', 'basal insulin', 'hyperglyc'],
    primaryEndpoint: { key: 'hba1c_reduction', label: 'HbA1c Reduction', unit: '%', direction: 'lower_better',
      definition: 'Absolute HbA1c reduction (percentage points) vs baseline.' },
    secondaryEndpoints: [
      { key: 'hba1c_target', label: '% Achieving HbA1c <7%', unit: '%' },
      { key: 'weight', label: 'Weight Change', unit: 'kg' },
    ],
    safetyLabel: 'Serious / GI AEs', hazardRatioLabel: null,
    treatmentModel: 'chronic_ongoing', routeDefault: 'oral',
    placeholder: 'e.g., Type 2 Diabetes',
  },

  // ── Women's Health — Gynecology ──
  'vasomotor symptoms': {
    category: "Women's Health", indication: 'Vasomotor Symptoms',
    aliases: ['vms', 'menopause', 'menopausal hot flashes', 'hot flushes'],
    primaryEndpoint: { key: 'vms_frequency', label: 'VMS Frequency Reduction', unit: '%', direction: 'lower_better',
      definition: 'Percentage reduction in frequency of moderate-to-severe vasomotor symptoms.' },
    secondaryEndpoints: [
      { key: 'vms_severity', label: 'VMS Severity Reduction', unit: '%' },
    ],
    safetyLabel: 'Serious AEs', hazardRatioLabel: null,
    treatmentModel: 'chronic_ongoing', routeDefault: 'oral',
    placeholder: 'e.g., Vasomotor Symptoms (Menopause)',
  },
  'osteoporosis': {
    category: "Women's Health", indication: 'Osteoporosis',
    aliases: ['postmenopausal osteoporosis', 'bone loss', 'fracture prevention', 'osteopenia', 'bone mineral density', 'vitamin d deficiency'],
    primaryEndpoint: { key: 'vertebral_fracture_hr', label: 'Vertebral-Fracture Risk Reduction', unit: 'HR', direction: 'lower_better',
      definition: 'Hazard ratio for new vertebral fracture vs comparator.' },
    secondaryEndpoints: [
      { key: 'bmd_spine', label: 'BMD Change (Spine)', unit: '%' },
      { key: 'bmd_hip', label: 'BMD Change (Hip)', unit: '%' },
    ],
    safetyLabel: 'Serious AEs', hazardRatioLabel: 'Fracture HR',
    treatmentModel: 'fixed_course', routeDefault: 'sc_injection',
    placeholder: 'e.g., Osteoporosis',
  },
  'endometriosis': {
    category: "Women's Health", indication: 'Endometriosis',
    aliases: ['endometriosis-associated pain', 'pelvic pain endometriosis'],
    primaryEndpoint: { key: 'dysmenorrhea_responder', label: 'Dysmenorrhoea Responder Rate', unit: '%', direction: 'higher_better',
      definition: 'Responder rate for menstrual pelvic pain (dysmenorrhoea).' },
    secondaryEndpoints: [
      { key: 'nmpp', label: 'Non-menstrual Pelvic Pain Responder', unit: '%' },
    ],
    safetyLabel: 'BMD loss (GnRH antagonists)', hazardRatioLabel: null,
    treatmentModel: 'fixed_course', routeDefault: 'oral',
    placeholder: 'e.g., Endometriosis',
  },
  'uterine fibroids': {
    category: "Women's Health", indication: 'Uterine Fibroids',
    aliases: ['uterine leiomyoma', 'fibroids', 'myoma'],
    primaryEndpoint: { key: 'mbl_responder', label: 'Menstrual Blood-Loss Responder (<80 mL & ≥50% ↓)', unit: '%', direction: 'higher_better',
      definition: 'Proportion achieving menstrual blood loss <80 mL AND ≥50% reduction from baseline.' },
    secondaryEndpoints: [
      { key: 'amenorrhea', label: 'Amenorrhoea Rate', unit: '%' },
    ],
    safetyLabel: 'BMD loss', hazardRatioLabel: null,
    treatmentModel: 'fixed_course', routeDefault: 'oral',
    placeholder: 'e.g., Uterine Fibroids',
  },
  'heavy menstrual bleeding': {
    category: "Women's Health", indication: 'Heavy Menstrual Bleeding (Menorrhagia)',
    aliases: ['menorrhagia', 'hmb', 'abnormal uterine bleeding', 'heavy periods',
      'dysfunctional uterine bleeding', 'postpartum haemorrhage', 'postpartum hemorrhage'],
    primaryEndpoint: { key: 'mbl_reduction', label: 'Menstrual Blood-Loss Reduction (alkaline-hematin)', unit: '%', direction: 'lower_better',
      definition: 'Percentage reduction in objectively-measured menstrual blood loss (alkaline-hematin method).' },
    secondaryEndpoints: [
      { key: 'hemoglobin', label: 'Haemoglobin / Ferritin Improvement', unit: 'g/dL' },
    ],
    safetyLabel: 'Serious AEs', hazardRatioLabel: null,
    treatmentModel: 'chronic_ongoing', routeDefault: 'oral',
    placeholder: 'e.g., Heavy Menstrual Bleeding',
  },
};

// Build alias index once
const ALIAS_INDEX = {};
Object.entries(INDICATION_REGISTRY).forEach(([key, entry]) => {
  ALIAS_INDEX[key] = key;
  ALIAS_INDEX[entry.indication.toLowerCase()] = key;
  (entry.aliases || []).forEach((a) => { ALIAS_INDEX[a.toLowerCase()] = key; });
});

// Resolve a free-text indication to its registry entry (exact, alias, substring). Null if unknown.
export function resolveIndication(indication) {
  if (!indication) return null;
  const key = indication.trim().toLowerCase();
  if (ALIAS_INDEX[key]) return INDICATION_REGISTRY[ALIAS_INDEX[key]];
  let best = null, bestLen = 0;
  Object.entries(ALIAS_INDEX).forEach(([alias, canonical]) => {
    if (key.includes(alias) && alias.length > bestLen) { best = canonical; bestLen = alias.length; }
  });
  return best ? INDICATION_REGISTRY[best] : null;
}

// Resolve by category as a fallback when indication isn't recognised.
export function entryForCategory(category) {
  const c = (category || '').toLowerCase();
  return Object.values(INDICATION_REGISTRY).find((e) => e.category.toLowerCase() === c) || null;
}

// Convenience: get the endpoint set for a drug (by indication, else category).
export function getEndpointsForDrug(drug) {
  if (!drug) return null;
  return resolveIndication(drug.indication) || entryForCategory(drug.category);
}
