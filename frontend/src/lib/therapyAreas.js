// Therapy Area Registry (frontend mirror of backend/core/therapy_areas.py).
// Single source of truth for which endpoints/metrics apply to each indication.
//
// GENERATED from the backend registry — do not hand-edit. To change an
// indication, edit backend/core/therapy_areas.py and regenerate.

export const INDICATION_REGISTRY = {
  'cardiovascular risk reduction': {
    category: 'CVD', indication: 'Cardiovascular Risk Reduction',
    aliases: ['cv risk reduction', 'mace reduction', 'cardiovascular outcomes', 'ascvd risk reduction', 'secondary prevention', 'secondary stroke prevention', 'post-pci', 'acute coronary syndrome', 'acs', 'antiplatelet'],
    primaryEndpoint: { key: 'mace_hr', label: '3-pt MACE Risk Reduction', unit: 'HR', direction: 'lower_better',
      definition: 'Hazard ratio for 3-point Major Adverse Cardiovascular Events (CV death, MI, stroke) vs comparator. HR<1 means fewer events; a 30% relative risk reduction is treated as maximal benefit for scoring.' },
    secondaryEndpoints: [
      { key: 'cv_mortality_hr', label: 'CV Mortality HR', unit: 'HR' },
      { key: 'acm_hr', label: 'All-cause Mortality HR', unit: 'HR' },
      { key: 'nnt', label: 'Number Needed to Treat', unit: 'patients' },
    ],
    safetyLabel: 'Serious AEs', hazardRatioLabel: 'MACE HR',
    treatmentModel: 'chronic_ongoing', routeDefault: 'sc_injection',
    placeholder: 'e.g., Cardiovascular Risk Reduction',
  },
  'heart failure': {
    category: 'CVD', indication: 'Heart Failure',
    aliases: ['hfref', 'hfpef', 'chronic heart failure', 'cardiac failure', 'heart-failure', 'refractory edema', 'refractory oedema'],
    primaryEndpoint: { key: 'hf_event_hr', label: 'CV-death / HF-hospitalisation HR', unit: 'HR', direction: 'lower_better',
      definition: 'Hazard ratio for the composite of cardiovascular death or heart-failure hospitalisation vs comparator.' },
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
    aliases: ['dyslipidemia', 'dyslipidaemia', 'high cholesterol', 'ldl lowering', 'hyperlipidemia', 'ascvd', 'familial hypercholesterolemia', 'high ldl', 'hypertriglyceridemia', 'triglyceride', 'statin', 'lipid'],
    primaryEndpoint: { key: 'ldl_reduction', label: 'LDL-C Reduction', unit: '%', direction: 'lower_better',
      definition: 'Percentage reduction in LDL cholesterol vs baseline; ~55% is treated as maximal for scoring.' },
    secondaryEndpoints: [
      { key: 'apob', label: 'ApoB Reduction', unit: '%' },
      { key: 'lpa', label: 'Lp(a) Reduction', unit: '%' },
      { key: 'mace_hr', label: 'MACE HR', unit: 'HR' },
    ],
    safetyLabel: 'Serious AEs', hazardRatioLabel: 'MACE HR',
    treatmentModel: 'chronic_ongoing', routeDefault: 'oral',
    placeholder: 'e.g., Hypercholesterolemia / Dyslipidemia',
  },
  'hypertension': {
    category: 'CVD', indication: 'Hypertension',
    aliases: ['high blood pressure', 'resistant hypertension', 'htn', 'hypertensive', 'antihypertensive', 'controlled hypotension'],
    primaryEndpoint: { key: 'sbp_reduction', label: 'Systolic BP Reduction', unit: 'mmHg', direction: 'lower_better',
      definition: 'Absolute reduction in systolic blood pressure vs comparator; ~20 mmHg treated as maximal for scoring.' },
    secondaryEndpoints: [
      { key: 'dbp_reduction', label: 'Diastolic BP Reduction', unit: 'mmHg' },
      { key: 'bp_control_rate', label: 'BP Control Rate', unit: '%' },
    ],
    safetyLabel: 'Serious AEs', hazardRatioLabel: 'CV-event HR',
    treatmentModel: 'chronic_ongoing', routeDefault: 'oral',
    placeholder: 'e.g., Hypertension',
  },
  'chronic stable angina': {
    category: 'CVD', indication: 'Chronic Stable Angina',
    aliases: ['angina', 'angina pectoris', 'antianginal', 'stable angina', 'anginal prophylaxis'],
    primaryEndpoint: { key: 'angina_frequency', label: 'Angina Frequency Reduction', unit: '%', direction: 'lower_better',
      definition: 'Percentage reduction in weekly angina episodes vs baseline; ~50% treated as maximal for scoring.' },
    secondaryEndpoints: [
      { key: 'ett', label: 'Exercise Tolerance Time', unit: 'sec' },
      { key: 'gtn_use', label: 'Short-acting Nitrate Use', unit: '%' },
    ],
    safetyLabel: 'Serious AEs', hazardRatioLabel: 'Ischaemic-event HR',
    treatmentModel: 'chronic_ongoing', routeDefault: 'oral',
    placeholder: 'e.g., Chronic Stable Angina',
  },
  'arrhythmia': {
    category: 'CVD', indication: 'Cardiac Arrhythmia (Rhythm Control)',
    aliases: ['arrhythmias', 'ventricular arrhythmia', 'atrial flutter', 'sinus rhythm', 'supraventricular', 'svt', 'tachycardia', 'vt/vf', 'antiarrhythmic'],
    primaryEndpoint: { key: 'sinus_rhythm', label: 'Sinus-Rhythm Maintenance', unit: '%', direction: 'higher_better',
      definition: 'Proportion maintaining sinus rhythm (or free of arrhythmia recurrence) at follow-up.' },
    secondaryEndpoints: [
      { key: 'recurrence_hr', label: 'Arrhythmia Recurrence HR', unit: 'HR' },
      { key: 'hosp_rate', label: 'Cardiovascular Hospitalisation', unit: '%' },
    ],
    safetyLabel: 'Proarrhythmia / serious AEs', hazardRatioLabel: 'Recurrence HR',
    treatmentModel: 'chronic_ongoing', routeDefault: 'oral',
    placeholder: 'e.g., Cardiac Arrhythmia (Rhythm Control)',
  },
  'venous thromboembolism': {
    category: 'CVD', indication: 'Thromboembolism Prevention (AF / VTE)',
    aliases: ['vte', 'non-valvular af', 'deep vein thrombosis', 'dvt', 'pulmonary embolism', 'anticoagulation', 'anticoagulant', 'mechanical heart valve', 'valve prosthesis', 'thromboprophylaxis', 'antithrombotic'],
    primaryEndpoint: { key: 'stroke_se_hr', label: 'Stroke / Systemic-Embolism HR', unit: 'HR', direction: 'lower_better',
      definition: 'Hazard ratio for stroke or systemic embolism (AF) or recurrent VTE vs comparator.' },
    secondaryEndpoints: [
      { key: 'vte_recurrence', label: 'VTE Recurrence HR', unit: 'HR' },
      { key: 'acm_hr', label: 'All-cause Mortality HR', unit: 'HR' },
    ],
    safetyLabel: 'Major bleeding', hazardRatioLabel: 'Stroke/SE HR',
    treatmentModel: 'chronic_ongoing', routeDefault: 'oral',
    placeholder: 'e.g., Thromboembolism Prevention (AF / VTE)',
  },
  'gout': {
    category: 'Metabolic', indication: 'Gout / Hyperuricaemia',
    aliases: ['hyperuricemia', 'hyperuricaemia', 'chronic gout', 'gout flare', 'urate', 'anti-gout', 'urate stones'],
    primaryEndpoint: { key: 'urate_target', label: 'Serum Urate <6 mg/dL Attainment', unit: '%', direction: 'higher_better',
      definition: 'Proportion achieving the guideline serum-urate target of <6 mg/dL.' },
    secondaryEndpoints: [
      { key: 'flare_rate', label: 'Gout Flare Rate Reduction', unit: '%' },
      { key: 'tophus', label: 'Tophus Resolution', unit: '%' },
    ],
    safetyLabel: 'Serious AEs', hazardRatioLabel: null,
    treatmentModel: 'chronic_ongoing', routeDefault: 'oral',
    placeholder: 'e.g., Gout / Hyperuricaemia',
  },
  'hypothyroidism': {
    category: 'Metabolic', indication: 'Hypothyroidism',
    aliases: ['thyroid replacement', 'goiter', 'goitre', 'tsh suppression', 'myxedema', 'myxoedema', 'underactive thyroid'],
    primaryEndpoint: { key: 'tsh_normalisation', label: 'TSH Normalisation', unit: '%', direction: 'higher_better',
      definition: 'Proportion achieving a TSH level within the reference range on replacement therapy.' },
    secondaryEndpoints: [
      { key: 'free_t4', label: 'Free T4 Normalisation', unit: '%' },
      { key: 'symptom_score', label: 'Symptom Score Improvement', unit: '%' },
    ],
    safetyLabel: 'Serious AEs', hazardRatioLabel: null,
    treatmentModel: 'chronic_ongoing', routeDefault: 'oral',
    placeholder: 'e.g., Hypothyroidism',
  },
  'hyperthyroidism': {
    category: 'Metabolic', indication: 'Hyperthyroidism',
    aliases: ['antithyroid', 'graves', 'toxic goiter', 'toxic goitre', 'thyrotoxicosis', 'overactive thyroid'],
    primaryEndpoint: { key: 'euthyroid_rate', label: 'Biochemical Euthyroidism', unit: '%', direction: 'higher_better',
      definition: 'Proportion achieving normal thyroid function on antithyroid therapy.' },
    secondaryEndpoints: [
      { key: 'remission_rate', label: 'Remission Rate', unit: '%' },
      { key: 'relapse_rate', label: 'Relapse Rate', unit: '%' },
    ],
    safetyLabel: 'Agranulocytosis / hepatotoxicity', hazardRatioLabel: null,
    treatmentModel: 'fixed_course', routeDefault: 'oral',
    placeholder: 'e.g., Hyperthyroidism',
  },
  'mineral and bone disorder': {
    category: 'Metabolic', indication: 'Mineral & Bone Disorder (CKD-MBD / Hypoparathyroidism)',
    aliases: ['renal osteodystrophy', 'hypoparathyroidism', 'rickets', 'ckd-mbd', 'active vitamin d'],
    primaryEndpoint: { key: 'pth_control', label: 'PTH / Calcium Control', unit: '%', direction: 'higher_better',
      definition: 'Proportion achieving target parathyroid hormone and serum calcium levels.' },
    secondaryEndpoints: [
      { key: 'serum_calcium', label: 'Serum Calcium Normalisation', unit: '%' },
    ],
    safetyLabel: 'Hypercalcaemia', hazardRatioLabel: null,
    treatmentModel: 'chronic_ongoing', routeDefault: 'oral',
    placeholder: 'e.g., Mineral & Bone Disorder (CKD-MBD / Hypoparathyroidism)',
  },
  'contraception': {
    category: 'Women\'s Health', indication: 'Contraception',
    aliases: ['contraceptive', 'emergency contraception', 'family planning', 'cycle regulation', 'long-acting contraception', 'oral contraceptive'],
    primaryEndpoint: { key: 'pearl_index', label: 'Pearl Index', unit: 'per 100 woman-years', direction: 'lower_better',
      definition: 'Pregnancies per 100 woman-years of use. Lower is better; ~9 (typical-use failure) is treated as the worst end of the scale.' },
    secondaryEndpoints: [
      { key: 'continuation_rate', label: '12-month Continuation Rate', unit: '%' },
      { key: 'cycle_control', label: 'Cycle Control', unit: '%' },
    ],
    safetyLabel: 'Serious AEs (VTE risk)', hazardRatioLabel: null,
    treatmentModel: 'chronic_ongoing', routeDefault: 'oral',
    placeholder: 'e.g., Contraception',
  },
  'infertility': {
    category: 'Women\'s Health', indication: 'Infertility / Assisted Reproduction',
    aliases: ['ovarian stimulation', 'controlled ovarian stimulation', 'ivf', 'iui', 'art', 'ovulation trigger', 'ovulation induction', 'luteal support', 'anovulation', 'anovulatory infertility', 'premature lh surge', 'endometrial preparation'],
    primaryEndpoint: { key: 'clinical_pregnancy_rate', label: 'Clinical Pregnancy Rate per Cycle', unit: '%', direction: 'higher_better',
      definition: 'Proportion of treatment cycles resulting in a clinically confirmed pregnancy.' },
    secondaryEndpoints: [
      { key: 'live_birth_rate', label: 'Live Birth Rate', unit: '%' },
      { key: 'oocytes_retrieved', label: 'Oocytes Retrieved', unit: 'count' },
    ],
    safetyLabel: 'Ovarian hyperstimulation (OHSS)', hazardRatioLabel: null,
    treatmentModel: 'fixed_course', routeDefault: 'sc_injection',
    placeholder: 'e.g., Infertility / Assisted Reproduction',
  },
  'polycystic ovary syndrome': {
    category: 'Women\'s Health', indication: 'Polycystic Ovary Syndrome (PCOS)',
    aliases: ['pcos', 'hirsutism', 'anti-androgen', 'acne/hirsutism', 'pmdd'],
    primaryEndpoint: { key: 'ovulation_rate', label: 'Ovulation / Menstrual Regularity Rate', unit: '%', direction: 'higher_better',
      definition: 'Proportion achieving ovulation or regular menstrual cycles.' },
    secondaryEndpoints: [
      { key: 'hirsutism_score', label: 'Hirsutism Score Improvement', unit: '%' },
      { key: 'androgen_level', label: 'Free Androgen Index', unit: '%' },
    ],
    safetyLabel: 'Serious AEs', hazardRatioLabel: null,
    treatmentModel: 'chronic_ongoing', routeDefault: 'oral',
    placeholder: 'e.g., Polycystic Ovary Syndrome (PCOS)',
  },
  'hyperprolactinaemia': {
    category: 'Women\'s Health', indication: 'Hyperprolactinaemia',
    aliases: ['hyperprolactinemia', 'prolactin', 'lactation suppression', 'galactagogue', 'stimulation of lactation', 'dopamine agonist'],
    primaryEndpoint: { key: 'prolactin_normalisation', label: 'Prolactin Normalisation', unit: '%', direction: 'higher_better',
      definition: 'Proportion achieving normal serum prolactin on therapy.' },
    secondaryEndpoints: [
      { key: 'menses_restored', label: 'Restoration of Menses / Ovulation', unit: '%' },
    ],
    safetyLabel: 'Serious AEs', hazardRatioLabel: null,
    treatmentModel: 'chronic_ongoing', routeDefault: 'oral',
    placeholder: 'e.g., Hyperprolactinaemia',
  },
  'medical termination of pregnancy': {
    category: 'Women\'s Health', indication: 'Medical Termination of Pregnancy',
    aliases: ['medical abortion', 'termination of pregnancy', 'abortion', 'antiprogestin'],
    primaryEndpoint: { key: 'complete_abortion', label: 'Complete Abortion Rate', unit: '%', direction: 'higher_better',
      definition: 'Proportion achieving complete uterine evacuation without surgical intervention.' },
    secondaryEndpoints: [
      { key: 'surgical_intervention', label: 'Surgical Intervention Required', unit: '%' },
    ],
    safetyLabel: 'Haemorrhage / infection', hazardRatioLabel: null,
    treatmentModel: 'acute_single_dose', routeDefault: 'oral',
    placeholder: 'e.g., Medical Termination of Pregnancy',
  },
  'recurrent pregnancy loss': {
    category: 'Women\'s Health', indication: 'Recurrent Pregnancy Loss / Preterm Birth Prevention',
    aliases: ['recurrent miscarriage', 'threatened miscarriage', 'prevention of recurrent miscarriage', 'progestogen', 'luteal phase support'],
    primaryEndpoint: { key: 'live_birth_rate', label: 'Live Birth Rate', unit: '%', direction: 'higher_better',
      definition: 'Proportion achieving a live birth with prophylactic progestogen therapy.' },
    secondaryEndpoints: [
      { key: 'miscarriage_rate', label: 'Miscarriage Rate', unit: '%' },
    ],
    safetyLabel: 'Serious AEs', hazardRatioLabel: null,
    treatmentModel: 'fixed_course', routeDefault: 'oral',
    placeholder: 'e.g., Recurrent Pregnancy Loss / Preterm Birth Prevention',
  },
  'rh alloimmunisation prophylaxis': {
    category: 'Women\'s Health', indication: 'Rh(D) Alloimmunisation Prophylaxis',
    aliases: ['rh prophylaxis', 'anti-d', 'rho immunoglobulin', 'alloimmunization', 'alloimmunisation'],
    primaryEndpoint: { key: 'sensitisation_prevented', label: 'Sensitisation Prevention Rate', unit: '%', direction: 'higher_better',
      definition: 'Proportion of Rh-negative mothers protected from Rh(D) alloimmunisation.' },
    secondaryEndpoints: [
      { key: 'hdfn_rate', label: 'Haemolytic Disease of Newborn', unit: '%' },
    ],
    safetyLabel: 'Serious AEs', hazardRatioLabel: null,
    treatmentModel: 'acute_single_dose', routeDefault: 'sc_injection',
    placeholder: 'e.g., Rh(D) Alloimmunisation Prophylaxis',
  },
  'vulvovaginal candidiasis': {
    category: 'Women\'s Health', indication: 'Vulvovaginal Candidiasis',
    aliases: ['vaginal candidiasis', 'vulvovaginal antifungal', 'thrush', 'vaginal antifungal'],
    primaryEndpoint: { key: 'mycological_cure', label: 'Mycological Cure Rate', unit: '%', direction: 'higher_better',
      definition: 'Proportion with negative culture at test-of-cure.' },
    secondaryEndpoints: [
      { key: 'symptom_resolution', label: 'Symptom Resolution', unit: '%' },
      { key: 'recurrence_rate', label: 'Recurrence Rate', unit: '%' },
    ],
    safetyLabel: 'Serious AEs', hazardRatioLabel: null,
    treatmentModel: 'fixed_course', routeDefault: 'oral',
    placeholder: 'e.g., Vulvovaginal Candidiasis',
  },
  'pulmonary arterial hypertension': {
    category: 'CVD', indication: 'Pulmonary Arterial Hypertension',
    aliases: ['pah', 'cteph', 'pulmonary hypertension', 'chronic thromboembolic ph'],
    primaryEndpoint: { key: 'six_min_walk', label: '6-Minute Walk Distance Improvement', unit: 'm', direction: 'higher_better',
      definition: 'Increase in six-minute walk distance from baseline — the standard PAH functional endpoint.' },
    secondaryEndpoints: [
      { key: 'who_fc', label: 'WHO Functional Class Improvement', unit: '%' },
      { key: 'clinical_worsening', label: 'Time to Clinical Worsening HR', unit: 'HR' },
    ],
    safetyLabel: 'Serious AEs (hypotension)', hazardRatioLabel: 'Clinical-worsening HR',
    treatmentModel: 'chronic_ongoing', routeDefault: 'oral',
    placeholder: 'e.g., Pulmonary Arterial Hypertension',
  },
  'peripheral arterial disease': {
    category: 'CVD', indication: 'Peripheral Arterial Disease',
    aliases: ['pad', 'intermittent claudication', 'claudication', 'peripheral vascular disease'],
    primaryEndpoint: { key: 'walking_distance', label: 'Pain-Free Walking Distance Improvement', unit: '%', direction: 'higher_better',
      definition: 'Percentage improvement in maximal or pain-free walking distance.' },
    secondaryEndpoints: [
      { key: 'abi', label: 'Ankle-Brachial Index', unit: '%' },
    ],
    safetyLabel: 'Serious AEs', hazardRatioLabel: 'Limb-event HR',
    treatmentModel: 'chronic_ongoing', routeDefault: 'oral',
    placeholder: 'e.g., Peripheral Arterial Disease',
  },
  'cerebral vasospasm': {
    category: 'CVS', indication: 'Cerebral Vasospasm (post-Subarachnoid Haemorrhage)',
    aliases: ['vasospasm', 'subarachnoid hemorrhage', 'subarachnoid haemorrhage', 'sah'],
    primaryEndpoint: { key: 'favourable_outcome', label: 'Favourable Neurological Outcome', unit: '%', direction: 'higher_better',
      definition: 'Proportion achieving a favourable neurological outcome (e.g. GOS 4-5) after subarachnoid haemorrhage.' },
    secondaryEndpoints: [
      { key: 'delayed_ischaemia', label: 'Delayed Cerebral Ischaemia', unit: '%' },
    ],
    safetyLabel: 'Hypotension', hazardRatioLabel: 'Poor-outcome HR',
    treatmentModel: 'fixed_course', routeDefault: 'oral',
    placeholder: 'e.g., Cerebral Vasospasm (post-Subarachnoid Haemorrhage)',
  },
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
  'chronic weight management': {
    category: 'Metabolic', indication: 'Chronic Weight Management',
    aliases: ['obesity', 'weight management', 'weight loss', 'overweight'],
    primaryEndpoint: { key: 'weight_reduction', label: 'Mean Body-Weight Reduction', unit: '%', direction: 'higher_better',
      definition: 'Mean percentage body-weight reduction vs baseline; ~20% treated as maximal for scoring.' },
    secondaryEndpoints: [
      { key: 'responder_5', label: '≥5% Weight-loss Responders', unit: '%' },
      { key: 'responder_10', label: '≥10% Weight-loss Responders', unit: '%' },
      { key: 'waist', label: 'Waist Circumference Change', unit: 'cm' },
    ],
    safetyLabel: 'Serious / GI AEs', hazardRatioLabel: null,
    treatmentModel: 'chronic_ongoing', routeDefault: 'sc_injection',
    placeholder: 'e.g., Chronic Weight Management',
  },
  'type 2 diabetes': {
    category: 'Metabolic', indication: 'Type 2 Diabetes',
    aliases: ['t2dm', 't2d', 'diabetes mellitus type 2', 'diabetes', 'glycaemic', 'glycemic', 'insulin', 'prandial insulin', 'basal insulin', 'hyperglyc'],
    primaryEndpoint: { key: 'hba1c_reduction', label: 'HbA1c Reduction', unit: '%', direction: 'lower_better',
      definition: 'Absolute HbA1c reduction (percentage points) vs baseline; ~2.0 points treated as maximal for scoring.' },
    secondaryEndpoints: [
      { key: 'fpg', label: 'Fasting Plasma Glucose', unit: '%' },
      { key: 'hba1c_target', label: '% Achieving HbA1c <7%', unit: '%' },
      { key: 'weight', label: 'Weight Change', unit: 'kg' },
    ],
    safetyLabel: 'Serious / GI AEs', hazardRatioLabel: null,
    treatmentModel: 'chronic_ongoing', routeDefault: 'oral',
    placeholder: 'e.g., Type 2 Diabetes',
  },
  'vasomotor symptoms': {
    category: 'Women\'s Health', indication: 'Vasomotor Symptoms',
    aliases: ['vms', 'menopause', 'menopausal hot flashes', 'hot flushes', 'menopausal symptoms', 'menopausal hrt', 'hormone replacement', 'atrophic vaginitis', 'hypoestrogenism'],
    primaryEndpoint: { key: 'vms_frequency', label: 'VMS Frequency Reduction', unit: '%', direction: 'lower_better',
      definition: 'Percentage reduction in frequency of moderate-to-severe vasomotor symptoms vs baseline.' },
    secondaryEndpoints: [
      { key: 'vms_severity', label: 'VMS Severity Reduction', unit: '%' },
      { key: 'sleep', label: 'Sleep Disturbance Improvement', unit: '%' },
    ],
    safetyLabel: 'Serious AEs', hazardRatioLabel: null,
    treatmentModel: 'chronic_ongoing', routeDefault: 'oral',
    placeholder: 'e.g., Vasomotor Symptoms',
  },
  'osteoporosis': {
    category: 'Women\'s Health', indication: 'Osteoporosis',
    aliases: ['postmenopausal osteoporosis', 'bone loss', 'fracture prevention', 'osteopenia', 'bone mineral density', 'vitamin d deficiency'],
    primaryEndpoint: { key: 'vertebral_fracture_hr', label: 'Vertebral-Fracture Risk Reduction', unit: 'HR', direction: 'lower_better',
      definition: 'Hazard ratio for new vertebral fracture vs comparator; ~60% relative risk reduction treated as maximal.' },
    secondaryEndpoints: [
      { key: 'bmd_spine', label: 'BMD Change (Spine)', unit: '%' },
      { key: 'bmd_hip', label: 'BMD Change (Hip)', unit: '%' },
      { key: 'nonvert_fracture', label: 'Non-vertebral Fracture RRR', unit: 'HR' },
    ],
    safetyLabel: 'Serious AEs', hazardRatioLabel: 'Fracture HR',
    treatmentModel: 'fixed_course', routeDefault: 'sc_injection',
    placeholder: 'e.g., Osteoporosis',
  },
  'endometriosis': {
    category: 'Women\'s Health', indication: 'Endometriosis',
    aliases: ['endometriosis-associated pain', 'pelvic pain endometriosis'],
    primaryEndpoint: { key: 'dysmenorrhea_responder', label: 'Dysmenorrhoea Responder Rate', unit: '%', direction: 'higher_better',
      definition: 'Proportion of responders for menstrual pelvic pain (dysmenorrhoea) with reduced/stable rescue analgesic use.' },
    secondaryEndpoints: [
      { key: 'nmpp', label: 'Non-menstrual Pelvic Pain Responder', unit: '%' },
      { key: 'analgesic_use', label: 'Analgesic Use Reduction', unit: '%' },
    ],
    safetyLabel: 'BMD loss (GnRH antagonists)', hazardRatioLabel: null,
    treatmentModel: 'fixed_course', routeDefault: 'oral',
    placeholder: 'e.g., Endometriosis',
  },
  'uterine fibroids': {
    category: 'Women\'s Health', indication: 'Uterine Fibroids',
    aliases: ['uterine leiomyoma', 'uterine fibroid', 'fibroids', 'myoma', 'fibroid symptoms'],
    primaryEndpoint: { key: 'mbl_responder', label: 'Menstrual Blood-Loss Responder (<80 mL & ≥50% ↓)', unit: '%', direction: 'higher_better',
      definition: 'Proportion achieving menstrual blood loss <80 mL AND ≥50% reduction from baseline (alkaline-hematin).' },
    secondaryEndpoints: [
      { key: 'amenorrhea', label: 'Amenorrhoea Rate', unit: '%' },
      { key: 'hemoglobin', label: 'Haemoglobin Improvement', unit: 'g/dL' },
    ],
    safetyLabel: 'BMD loss', hazardRatioLabel: null,
    treatmentModel: 'fixed_course', routeDefault: 'oral',
    placeholder: 'e.g., Uterine Fibroids',
  },
  'postpartum haemorrhage': {
    category: 'Women\'s Health', indication: 'Postpartum Haemorrhage (Prevention & Treatment)',
    aliases: ['pph', 'postpartum hemorrhage', 'uterine atony', 'uterotonic', 'uterine involution', 'refractory pph'],
    primaryEndpoint: { key: 'pph_reduction', label: 'PPH Incidence Reduction (blood loss ≥500 mL)', unit: '%', direction: 'lower_better',
      definition: 'Relative reduction in the proportion of women with postpartum blood loss ≥500 mL.' },
    secondaryEndpoints: [
      { key: 'mean_blood_loss', label: 'Mean Blood Loss', unit: 'mL' },
      { key: 'transfusion_rate', label: 'Transfusion Rate', unit: '%' },
    ],
    safetyLabel: 'Serious AEs', hazardRatioLabel: 'Haemorrhage HR',
    treatmentModel: 'acute_single_dose', routeDefault: 'iv_bolus',
    placeholder: 'e.g., Postpartum Haemorrhage (Prevention & Treatment)',
  },
  'preterm labour': {
    category: 'Women\'s Health', indication: 'Preterm Labour (Tocolysis)',
    aliases: ['tocolysis', 'tocolytic', 'threatened preterm labor', 'threatened preterm labour', 'preterm birth', 'suppression of preterm labor'],
    primaryEndpoint: { key: 'delay_48h', label: 'Birth Delayed ≥48 h', unit: '%', direction: 'higher_better',
      definition: 'Proportion of women undelivered 48 hours after starting tocolysis — the window for antenatal steroids and transfer.' },
    secondaryEndpoints: [
      { key: 'delay_7d', label: 'Birth Delayed ≥7 days', unit: '%' },
      { key: 'nicu_admission', label: 'NICU Admission', unit: '%' },
    ],
    safetyLabel: 'Serious maternal AEs', hazardRatioLabel: 'Preterm-birth HR',
    treatmentModel: 'fixed_course', routeDefault: 'iv_infusion',
    placeholder: 'e.g., Preterm Labour (Tocolysis)',
  },
  'labour induction': {
    category: 'Women\'s Health', indication: 'Labour Induction & Cervical Ripening',
    aliases: ['induction of labor', 'induction of labour', 'cervical ripening', 'cervical priming', 'augmentation of labor', 'augmentation of labour'],
    primaryEndpoint: { key: 'vaginal_delivery_24h', label: 'Vaginal Delivery within 24 h', unit: '%', direction: 'higher_better',
      definition: 'Proportion achieving vaginal delivery within 24 hours of induction.' },
    secondaryEndpoints: [
      { key: 'caesarean_rate', label: 'Caesarean Section Rate', unit: '%' },
      { key: 'time_to_delivery', label: 'Induction-to-Delivery Interval', unit: 'hours' },
    ],
    safetyLabel: 'Uterine hyperstimulation', hazardRatioLabel: 'Caesarean HR',
    treatmentModel: 'acute_single_dose', routeDefault: 'iv_infusion',
    placeholder: 'e.g., Labour Induction & Cervical Ripening',
  },
  'iron deficiency anaemia': {
    category: 'Women\'s Health', indication: 'Iron-Deficiency Anaemia (Pregnancy & Postpartum)',
    aliases: ['iron-deficiency anemia', 'iron deficiency anemia', 'antianemic', 'anaemia', 'megaloblastic anemia', 'neural-tube-defect prevention', 'iron deficiency'],
    primaryEndpoint: { key: 'hb_increase', label: 'Haemoglobin Increase', unit: 'g/dL', direction: 'higher_better',
      definition: 'Mean rise in haemoglobin from baseline; ~3 g/dL treated as maximal correction for scoring.' },
    secondaryEndpoints: [
      { key: 'ferritin', label: 'Ferritin Repletion', unit: 'ng/mL' },
      { key: 'transfusion_avoided', label: 'Transfusion Avoidance', unit: '%' },
    ],
    safetyLabel: 'Serious AEs', hazardRatioLabel: null,
    treatmentModel: 'fixed_course', routeDefault: 'oral',
    placeholder: 'e.g., Iron-Deficiency Anaemia (Pregnancy & Postpartum)',
  },
  'pre-eclampsia': {
    category: 'Women\'s Health', indication: 'Pre-eclampsia / Eclampsia',
    aliases: ['eclampsia', 'severe pre-eclampsia', 'seizure prophylaxis', 'pre-eclamptic'],
    primaryEndpoint: { key: 'eclampsia_hr', label: 'Eclamptic Seizure Risk Reduction', unit: 'HR', direction: 'lower_better',
      definition: 'Hazard ratio for eclamptic seizure vs comparator or placebo.' },
    secondaryEndpoints: [
      { key: 'maternal_mortality', label: 'Maternal Mortality', unit: '%' },
    ],
    safetyLabel: 'Serious maternal AEs', hazardRatioLabel: 'Seizure HR',
    treatmentModel: 'acute_single_dose', routeDefault: 'iv_infusion',
    placeholder: 'e.g., Pre-eclampsia / Eclampsia',
  },
  'fetal lung maturation': {
    category: 'Women\'s Health', indication: 'Fetal Lung Maturation (Antenatal Corticosteroid)',
    aliases: ['antenatal corticosteroid', 'fetal lung maturity', 'respiratory distress syndrome prophylaxis'],
    primaryEndpoint: { key: 'rds_hr', label: 'Neonatal RDS Risk Reduction', unit: 'HR', direction: 'lower_better',
      definition: 'Hazard ratio for neonatal respiratory distress syndrome after antenatal corticosteroid.' },
    secondaryEndpoints: [
      { key: 'neonatal_mortality', label: 'Neonatal Mortality', unit: '%' },
    ],
    safetyLabel: 'Serious AEs', hazardRatioLabel: 'RDS HR',
    treatmentModel: 'acute_single_dose', routeDefault: 'sc_injection',
    placeholder: 'e.g., Fetal Lung Maturation (Antenatal Corticosteroid)',
  },
  'heavy menstrual bleeding': {
    category: 'Women\'s Health', indication: 'Heavy Menstrual Bleeding (Menorrhagia)',
    aliases: ['menorrhagia', 'hmb', 'abnormal uterine bleeding', 'heavy periods', 'dysfunctional uterine bleeding', 'postpartum haemorrhage', 'postpartum hemorrhage'],
    primaryEndpoint: { key: 'mbl_reduction', label: 'Menstrual Blood-Loss Reduction (alkaline-hematin)', unit: '%', direction: 'lower_better',
      definition: 'Percentage reduction in objectively-measured menstrual blood loss (alkaline-hematin method) vs baseline.' },
    secondaryEndpoints: [
      { key: 'hemoglobin', label: 'Haemoglobin / Ferritin Improvement', unit: 'g/dL' },
      { key: 'amenorrhea', label: 'Amenorrhoea Rate', unit: '%' },
    ],
    safetyLabel: 'Serious AEs', hazardRatioLabel: null,
    treatmentModel: 'chronic_ongoing', routeDefault: 'oral',
    placeholder: 'e.g., Heavy Menstrual Bleeding (Menorrhagia)',
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
