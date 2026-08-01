import React, { useState, useEffect, useRef } from 'react';
import { Search, FlaskConical, DollarSign, Activity, ChevronRight, AlertTriangle, ChevronDown, ChevronUp, Info, Beaker, Percent, ExternalLink, CheckCircle, Users, Building2, ShieldCheck } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from './ui/card';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Badge } from './ui/badge';
import { Separator } from './ui/separator';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { Slider } from './ui/slider';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from './ui/tooltip';
import axios from 'axios';
import { useApp } from '../context/AppContext';
import { toast } from 'sonner';
import { getEndpointsForDrug, resolveIndication } from '../lib/therapyAreas';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || '';
const API = (BACKEND_URL && BACKEND_URL.startsWith('http')) ? `${BACKEND_URL}/api` : '/api';

// Subsidy schemes with their effective cycle ratios
const SUBSIDY_SCHEMES = [
  { id: 'none', name: 'No Subsidy', cyclesPaid: 12, totalCycles: 12 },
  { id: 'bogo', name: 'Buy 1 Get 1 Free', cyclesPaid: 6, totalCycles: 12 },
  { id: '8of12', name: '8 of 12 Paid', cyclesPaid: 8, totalCycles: 12 },
  { id: '6of12', name: '6 of 12 Paid', cyclesPaid: 6, totalCycles: 12 },
  { id: 'cap3', name: '3-Cycle Cap', cyclesPaid: 3, totalCycles: 12 },
];

// Comorbidity chips for patient profile (CardioMetabolic / Women's Health)
const COMORBIDITY_OPTIONS = [
  { id: 'renal', label: 'Renal Impairment', contraindications: ['nephrotoxic'] },
  { id: 'cardiac', label: 'Cardiac Disease', contraindications: ['cardiotoxic', 'qt_prolongation'] },
  { id: 'hepatic', label: 'Hepatic Impairment', contraindications: ['hepatotoxic'] },
  { id: 'diabetes', label: 'Diabetes', contraindications: ['hyperglycemia'] },
  { id: 'bleeding_risk', label: 'Bleeding Risk', contraindications: ['anticoagulant'] },
];

// Methodology Section Component - Shows calculation assumptions and formulas
function MethodologySection({
  userAsset,
  competitorAsset,
  subsidyScheme,
  discountPercent,
  totalCycles,
  populationScale,
  effectiveUserPrice,
  effectiveCompPrice,
  currencySymbol,
  theme,
  textPrimary,
  textSecondary,
  borderColor
}) {
  const [isExpanded, setIsExpanded] = useState(false);

  const scheme = SUBSIDY_SCHEMES.find(s => s.id === subsidyScheme);
  const subsidyFactor = scheme ? (scheme.cyclesPaid / scheme.totalCycles) : 1;
  const discountFactor = 1 - (discountPercent / 100);

  // Data inputs with sources
  const dataInputs = [
    {
      parameter: 'Your Asset Primary Endpoint',
      value: userAsset.mPFS ? `${userAsset.mPFS} months` : 'Not entered',
      method: 'User input',
      status: userAsset.mPFS ? 'Entered' : 'Pending',
      confidence: userAsset.mPFS ? 'User-defined' : '-'
    },
    {
      parameter: 'Your Asset Secondary Endpoint',
      value: userAsset.mOS ? `${userAsset.mOS} months` : 'Not entered',
      method: 'User input',
      status: userAsset.mOS ? 'Entered' : 'Pending',
      confidence: userAsset.mOS ? 'User-defined' : '-'
    },
    {
      parameter: 'Your Asset Serious AE Rate',
      value: userAsset.aeRate ? `${userAsset.aeRate}%` : 'Not entered',
      method: 'User input',
      status: userAsset.aeRate ? 'Entered' : 'Pending',
      confidence: userAsset.aeRate ? 'User-defined' : '-'
    },
    {
      parameter: 'Your Asset Market Price',
      value: userAsset.marketPrice ? `${currencySymbol}${parseFloat(userAsset.marketPrice).toLocaleString()}` : 'Not entered',
      method: 'User input',
      status: userAsset.marketPrice ? 'Entered' : 'Pending',
      confidence: userAsset.marketPrice ? 'User-defined' : '-'
    },
    {
      parameter: 'Competitor Primary Endpoint',
      value: competitorAsset.mPFS ? `${competitorAsset.mPFS} months` : 'Not entered',
      method: competitorAsset.name ? 'Search prefill / User edit' : 'User input',
      status: competitorAsset.mPFS ? 'Entered' : 'Pending',
      confidence: competitorAsset.mPFS ? 'User-defined' : '-'
    },
    {
      parameter: 'Competitor Secondary Endpoint',
      value: competitorAsset.mOS ? `${competitorAsset.mOS} months` : 'Not entered',
      method: competitorAsset.name ? 'Search prefill / User edit' : 'User input',
      status: competitorAsset.mOS ? 'Entered' : 'Pending',
      confidence: competitorAsset.mOS ? 'User-defined' : '-'
    },
    {
      parameter: 'Competitor Serious AE Rate',
      value: competitorAsset.aeRate ? `${competitorAsset.aeRate}%` : 'Not entered',
      method: competitorAsset.name ? 'Search prefill / User edit' : 'User input',
      status: competitorAsset.aeRate ? 'Entered' : 'Pending',
      confidence: competitorAsset.aeRate ? 'User-defined' : '-'
    },
    {
      parameter: 'Competitor Market Price',
      value: competitorAsset.marketPrice ? `${currencySymbol}${parseFloat(competitorAsset.marketPrice).toLocaleString()}` : 'Not entered',
      method: competitorAsset.name ? 'Search prefill / User edit' : 'User input',
      status: competitorAsset.marketPrice ? 'Entered' : 'Pending',
      confidence: competitorAsset.marketPrice ? 'User-defined' : '-'
    },
  ];

  // Pricing calculations with formulas
  const pricingCalculations = [
    {
      metric: 'Subsidy Factor',
      formula: `${scheme?.cyclesPaid || 12} / ${scheme?.totalCycles || 12}`,
      result: subsidyFactor.toFixed(2),
      description: `${scheme?.name || 'No Subsidy'} - cycles paid / total cycles`
    },
    {
      metric: 'Discount Factor',
      formula: `1 - (${discountPercent}% / 100)`,
      result: discountFactor.toFixed(2),
      description: `Negotiated discount applied on top of subsidy`
    },
    {
      metric: 'Your Asset Effective Price',
      formula: `market_price × subsidy_factor × discount_factor`,
      result: `${currencySymbol}${effectiveUserPrice.toLocaleString()}`,
      description: `${currencySymbol}${parseFloat(userAsset.marketPrice || 0).toLocaleString()} × ${subsidyFactor.toFixed(2)} × ${discountFactor.toFixed(2)}`
    },
    {
      metric: 'Competitor Effective Price',
      formula: `market_price × subsidy_factor × discount_factor`,
      result: `${currencySymbol}${effectiveCompPrice.toLocaleString()}`,
      description: `${currencySymbol}${parseFloat(competitorAsset.marketPrice || 0).toLocaleString()} × ${subsidyFactor.toFixed(2)} × ${discountFactor.toFixed(2)}`
    },
    {
      metric: 'Your Asset Total Exposure',
      formula: `effective_price × periods × population`,
      result: `${currencySymbol}${(effectiveUserPrice * totalCycles * populationScale).toLocaleString()}`,
      description: `${currencySymbol}${effectiveUserPrice.toLocaleString()} × ${totalCycles} periods × ${populationScale.toLocaleString()} patients`
    },
    {
      metric: 'Competitor Total Exposure',
      formula: `effective_price × periods × population`,
      result: `${currencySymbol}${(effectiveCompPrice * totalCycles * populationScale).toLocaleString()}`,
      description: `${currencySymbol}${effectiveCompPrice.toLocaleString()} × ${totalCycles} periods × ${populationScale.toLocaleString()} patients`
    },
  ];

  return (
    <Card className="glass-card overflow-hidden" style={{ borderColor }}>
      <CardHeader
        className="pb-3 cursor-pointer flex flex-row items-center justify-between"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <CardTitle className={`font-data text-sm ${textPrimary} flex items-center gap-2`}>
          <Info className="w-4 h-4 text-muted-foreground" />
          <span className="underline">CALCULATION ASSUMPTIONS & METHODOLOGY</span>
        </CardTitle>
        {isExpanded ? (
          <ChevronUp className="w-4 h-4 text-muted-foreground" />
        ) : (
          <ChevronDown className="w-4 h-4 text-muted-foreground" />
        )}
      </CardHeader>

      {isExpanded && (
        <CardContent className="space-y-6">
          {/* DATA INPUTS & SOURCES */}
          <div>
            <h4 className={`text-xs uppercase tracking-widest ${textSecondary} mb-3`}>DATA INPUTS & SOURCES</h4>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b" style={{ borderColor }}>
                    <th className={`text-left py-2 px-3 font-medium ${textPrimary}`}>Parameter</th>
                    <th className={`text-left py-2 px-3 font-medium text-[#008080]`}>Value</th>
                    <th className={`text-left py-2 px-3 font-medium ${textPrimary}`}>Method</th>
                    <th className={`text-left py-2 px-3 font-medium ${textPrimary}`}>Status</th>
                    <th className={`text-left py-2 px-3 font-medium ${textPrimary}`}>Confidence</th>
                  </tr>
                </thead>
                <tbody>
                  {dataInputs.map((input, idx) => (
                    <tr key={idx} className="border-b" style={{ borderColor }}>
                      <td className={`py-2 px-3 ${textSecondary}`}>{input.parameter}</td>
                      <td className="py-2 px-3 font-data text-[#008080]">{input.value}</td>
                      <td className={`py-2 px-3 ${textSecondary} text-xs`}>{input.method}</td>
                      <td className="py-2 px-3">
                        {input.status === 'Entered' ? (
                          <Badge variant="outline" className="text-xs border-[#008080] text-[#008080]">
                            <CheckCircle className="w-3 h-3 mr-1" />
                            Entered
                          </Badge>
                        ) : (
                          <Badge variant="outline" className="text-xs border-yellow-500 text-yellow-500">
                            Pending
                          </Badge>
                        )}
                      </td>
                      <td className={`py-2 px-3 text-xs ${input.confidence === 'User-defined' ? 'text-[#008080]' : textSecondary}`}>
                        {input.confidence}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <Separator className="bg-white/10" />

          {/* PRICING CALCULATIONS */}
          <div>
            <h4 className={`text-xs uppercase tracking-widest ${textSecondary} mb-3`}>PRICING CALCULATIONS</h4>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b" style={{ borderColor }}>
                    <th className={`text-left py-2 px-3 font-medium ${textPrimary}`}>Metric</th>
                    <th className={`text-left py-2 px-3 font-medium text-[#008080]`}>Formula</th>
                    <th className={`text-left py-2 px-3 font-medium text-[#008080]`}>Result</th>
                    <th className={`text-left py-2 px-3 font-medium ${textPrimary}`}>Description</th>
                  </tr>
                </thead>
                <tbody>
                  {pricingCalculations.map((calc, idx) => (
                    <tr key={idx} className="border-b" style={{ borderColor }}>
                      <td className={`py-2 px-3 ${textSecondary}`}>{calc.metric}</td>
                      <td className="py-2 px-3 font-mono text-xs text-[#008080]">{calc.formula}</td>
                      <td className="py-2 px-3 font-data text-[#008080]">{calc.result}</td>
                      <td className={`py-2 px-3 text-xs ${textSecondary}`}>{calc.description}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <Separator className="bg-white/10" />

          {/* TOTAL EXPOSURE DIFFERENCE */}
          <div className={`p-4 rounded-sm ${exposureDiff > 0 ? 'bg-[#E53E3E]/10 border border-[#E53E3E]/30' : 'bg-[#008080]/10 border border-[#008080]/30'}`}>
            <div className="flex justify-between items-center">
              <div>
                <h4 className={`text-xs uppercase tracking-widest ${textSecondary} mb-1`}>TOTAL EXPOSURE DIFFERENCE</h4>
                <p className={`text-xs ${textSecondary}`}>
                  {exposureDiff > 0
                    ? `Your Asset costs ${currencySymbol}${Math.abs(exposureDiff).toLocaleString()} MORE than Competitor`
                    : `Your Asset costs ${currencySymbol}${Math.abs(exposureDiff).toLocaleString()} LESS than Competitor`
                  }
                </p>
              </div>
              <div className={`font-data text-2xl font-bold ${exposureDiff > 0 ? 'text-[#E53E3E]' : 'text-[#008080]'}`}>
                {exposureDiff > 0 ? '+' : '-'}{currencySymbol}{Math.abs(exposureDiff).toLocaleString()}
              </div>
            </div>
          </div>

          {/* Note */}
          <p className={`text-xs ${textSecondary} italic`}>
            Note: All values in this comparison are user-editable. Prefilled values from search are estimates and should be verified against official sources.
            Effective prices include both subsidy scheme ({scheme?.name || 'No Subsidy'}) and negotiated discount ({discountPercent}%).
          </p>
        </CardContent>
      )}
    </Card>
  );
}

// Editable Input Component with optional source tooltip
// source prop: plain string OR { label: string, url: string }
function EditableInput({ value, onChange, placeholder, label, prefix, suffix, className, dataTestId, theme, source, onSourceClear }) {
  const [localValue, setLocalValue] = useState(value ?? '');
  const [showTooltip, setShowTooltip] = useState(false);
  const inputRef = useRef(null);

  useEffect(() => {
    setLocalValue(value ?? '');
  }, [value]);

  const handleChange = (e) => {
    const val = e.target.value;
    setLocalValue(val);
    onChange(val);
    // Clear source when user edits the value
    if (onSourceClear) onSourceClear();
  };

  const handleFocus = () => {
    if (inputRef.current) {
      inputRef.current.select();
    }
  };

  // Normalise source to { label, url | null }
  const srcLabel = source
    ? (typeof source === 'object' ? source.label : source)
    : null;
  const srcUrl = source && typeof source === 'object' ? source.url : null;

  return (
    <div className="relative">
      <div className="flex items-center gap-2 mb-2">
        <Label className="text-xs uppercase tracking-widest text-muted-foreground">{label}</Label>
        {srcLabel && (
          <div
            className="relative"
            onMouseEnter={() => setShowTooltip(true)}
            onMouseLeave={() => setShowTooltip(false)}
          >
            <Info className="w-3 h-3 text-[#008080] cursor-help" />
            {showTooltip && (
              <div className={`absolute z-50 left-0 top-5 px-3 py-2 rounded-sm shadow-lg text-xs whitespace-nowrap ${theme === 'dark' ? 'bg-[#1a1a1a] border border-[#333] text-white' : 'bg-white border border-gray-200 text-gray-900'}`}>
                <div className="font-medium text-[#008080] mb-1">Data Source</div>
                {srcUrl ? (
                  <a
                    href={srcUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-[#008080] underline hover:text-teal-400 transition-colors flex items-center gap-1"
                    onClick={e => e.stopPropagation()}
                  >
                    {srcLabel}
                    <ExternalLink className="w-3 h-3 inline" />
                  </a>
                ) : (
                  <div>{srcLabel}</div>
                )}
              </div>
            )}
          </div>
        )}
      </div>
      <div className="relative">
        {prefix && <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground">{prefix}</span>}
        <Input
          ref={inputRef}
          data-testid={dataTestId}
          type="text"
          value={localValue}
          onChange={handleChange}
          onFocus={handleFocus}
          placeholder={placeholder}
          className={`${prefix ? 'pl-8' : ''} ${suffix ? 'pr-16' : ''} ${className} ${theme === 'dark' ? 'bg-[#050505] border-[#262626] text-white placeholder:text-gray-600' : 'bg-white border-gray-300 text-gray-900 placeholder:text-gray-400'} ${srcLabel ? 'border-[#008080]/50' : ''}`}
        />
        {suffix && <span className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground text-sm">{suffix}</span>}
      </div>
    </div>
  );
}

// Regulatory override options
const REGULATORY_OPTIONS = [
  { value: 'AI Auto-Detect', label: '✨ AI Auto-Detect', isDefault: true },
  { value: 'Approved (Commercial Launch)', label: '✅ Approved (Commercial Launch)', isDefault: false },
  { value: 'Pending / Named-Patient Access', label: '⏳ Pending / Named-Patient Access', isDefault: false },
  { value: 'Unapproved / Compassionate Use Only', label: '❌ Unapproved / Compassionate Use Only', isDefault: false },
];

// Asset Card Component - used for both Your Asset and Competitor
function AssetCard({
  title,
  subtitle,
  icon: Icon,
  iconColor,
  data,
  onDataChange,
  effectivePrice,
  theme,
  textPrimary,
  textSecondary,
  cardBg,
  borderColor,
  currencySymbol,
  isSearchable = false,
  onSearch,
  suggestions = [],
  onSelectSuggestion,
  sources = {},  // NEW: Data sources for each field
  onClearSource, // NEW: Callback to clear source when user edits
  isLoading = false, // NEW: Show loading indicator while web sweep fetches
  subsidyScheme = null,
  discountPercent = 0,
  comorbidities = [],
  totalCycles = 12,
  populationScale = 1000,
  selectedPayer = 'oop',
  regulatoryOverride = 'AI Auto-Detect',
  onRegulatoryChange,
  adherencePct = 100, // Default 100% adherence
  onAdherenceChange,
  endpoints = null, // Therapy Area Registry entry — drives clinical endpoint labels
}) {
  // Registry-driven endpoint labels (fall back to generic if indication unknown)
  const pe = endpoints?.primaryEndpoint;
  const se0 = endpoints?.secondaryEndpoints?.[0];
  const primaryLabel = pe ? `${pe.label}${pe.unit ? ` (${pe.unit})` : ''}` : 'Primary Endpoint';
  const primarySuffix = pe?.unit || '';
  const secondaryLabel = se0 ? `${se0.label}${se0.unit ? ` (${se0.unit})` : ''}` : 'Secondary Endpoint';
  const secondarySuffix = se0?.unit || '';
  const safetyLabel = endpoints?.safetyLabel ? `${endpoints.safetyLabel} Rate` : 'Serious AE Rate';

  // Compute Comorbidity Penalty for AE Rate
  const baseAeRate = parseFloat(data.aeRate) || 0;
  const comorbidityPenalty = comorbidities.length * 2;
  const effectiveAeRate = baseAeRate > 0 ? baseAeRate + comorbidityPenalty : 0;

  // Compute Cost for 1 Patient (Effective Price * Total Cycles) + the new Adherence Waste Penalty
  const baseCostPerPatient = effectivePrice * totalCycles;
  const nonComplianceRatio = 1 - (adherencePct / 100);
  const nonCompliancePenalty = baseCostPerPatient * nonComplianceRatio;
  const costPerPatient = baseCostPerPatient + nonCompliancePenalty;

  return (
    <Card className="glass-card overflow-hidden" style={{ borderColor }}>
      <CardHeader className="pb-3 border-b" style={{ borderColor }}>
        <CardTitle className={`font-data text-sm ${textPrimary} flex items-center gap-2`}>
          <Icon className="w-4 h-4" style={{ color: iconColor }} />
          {title}
          {isLoading && (
            <span className="flex items-center gap-1 text-[10px] font-normal normal-case tracking-normal ml-1">
              <span className="inline-block w-1.5 h-1.5 rounded-full bg-[#008080] animate-bounce" style={{ animationDelay: '0ms' }} />
              <span className="inline-block w-1.5 h-1.5 rounded-full bg-[#008080] animate-bounce" style={{ animationDelay: '150ms' }} />
              <span className="inline-block w-1.5 h-1.5 rounded-full bg-[#008080] animate-bounce" style={{ animationDelay: '300ms' }} />
              <span className="text-[#008080]">Web Sweep</span>
            </span>
          )}
        </CardTitle>
        <CardDescription className="text-muted-foreground">
          {subtitle}
        </CardDescription>
      </CardHeader>
      <CardContent className="pt-4 space-y-4">
        {/* Asset Name - Editable or Searchable */}
        {isSearchable ? (
          <div className="relative">
            <div className="flex items-center gap-2 mb-2">
              <Label className="text-xs uppercase tracking-widest text-muted-foreground">Search Competitor</Label>
              {sources.name && (
                <div className="relative group">
                  <Info className="w-3 h-3 text-[#008080] cursor-help" />
                  <div className={`absolute z-50 left-0 top-5 px-3 py-2 rounded-sm shadow-lg text-xs whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity ${theme === 'dark' ? 'bg-[#1a1a1a] border border-[#333] text-white' : 'bg-white border border-gray-200 text-gray-900'}`}>
                    <div className="font-medium text-[#008080] mb-1">Data Source</div>
                    {typeof sources.name === 'object' && sources.name.url ? (
                      <a href={sources.name.url} target="_blank" rel="noopener noreferrer"
                        className="text-[#008080] underline hover:text-teal-400 flex items-center gap-1"
                        onClick={e => e.stopPropagation()}>
                        {sources.name.label}<ExternalLink className="w-3 h-3 inline" />
                      </a>
                    ) : (
                      <div>{typeof sources.name === 'object' ? sources.name.label : sources.name}</div>
                    )}
                  </div>
                </div>
              )}

            </div>
            <div className="relative">
              <Search className={`absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 ${theme === 'dark' ? 'text-gray-500' : 'text-gray-400'}`} />
              <Input
                data-testid="competitor-search-tpp"
                type="text"
                placeholder="Search drug name..."
                value={data.name || ''}
                onChange={(e) => {
                  onDataChange({ ...data, name: e.target.value });
                  if (onSearch) onSearch(e.target.value);
                  if (onClearSource) onClearSource('name');
                }}
                className={`pl-10 ${theme === 'dark' ? 'bg-[#050505] border-[#262626] text-white placeholder:text-gray-600' : 'bg-white border-gray-300 text-gray-900 placeholder:text-gray-400'} ${sources.name ? 'border-[#008080]/50' : ''}`}
              />
            </div>
            {suggestions.length > 0 && (
              <div className={`absolute z-20 w-full mt-1 rounded-sm shadow-lg overflow-hidden max-h-48 overflow-y-auto ${theme === 'dark' ? 'bg-[#121212] border border-[#262626]' : 'bg-white border border-gray-200'}`}>
                {suggestions.map((drug, idx) => (
                  <button
                    key={idx}
                    onClick={() => onSelectSuggestion(drug)}
                    className={`w-full px-3 py-2 text-left transition-all border-b last:border-b-0 ${theme === 'dark' ? 'hover:bg-[#008080]/20 border-[#262626]' : 'hover:bg-teal-50 border-gray-100'}`}
                  >
                    <div className={`font-medium text-sm ${textPrimary}`}>{drug.name}</div>
                    <div className="text-xs text-muted-foreground">{drug.indication}</div>
                  </button>
                ))}
              </div>
            )}
          </div>
        ) : (
          <EditableInput
            label="Asset Name"
            value={data.name}
            onChange={(val) => onDataChange({ ...data, name: val })}
            placeholder="Enter drug name"
            dataTestId="user-asset-name-input"
            theme={theme}
            source={sources.name}
            onSourceClear={() => onClearSource && onClearSource('name')}
          />
        )}

        {/* Indication - Always Editable */}
        <EditableInput
          label="Indication"
          value={data.indication}
          onChange={(val) => onDataChange({ ...data, indication: val })}
          placeholder={endpoints?.placeholder || 'e.g., Heart Failure, Type 2 Diabetes'}
          dataTestId={`${isSearchable ? 'competitor' : 'user'}-indication-input`}
          theme={theme}
          source={sources.indication}
          onSourceClear={() => onClearSource && onClearSource('indication')}
        />

        {/* LOCAL REGULATORY STATUS override */}
        <div className="space-y-2">
          <Label className="text-xs uppercase tracking-widest text-muted-foreground">
            Local Regulatory Status
          </Label>
          <Select
            value={regulatoryOverride}
            onValueChange={(val) => onRegulatoryChange && onRegulatoryChange(val)}
          >
            <SelectTrigger
              data-testid={`${isSearchable ? 'competitor' : 'user'}-regulatory-select`}
              className={`h-9 text-sm border ${theme === 'dark'
                ? 'bg-[#050505] border-[#262626] hover:border-[#404040]'
                : 'bg-white border-gray-300 hover:border-gray-400'
                } transition-colors`}
              style={{
                color: regulatoryOverride === 'AI Auto-Detect' ? '#A1A1AA' : '#F3F4F6',
                borderColor: regulatoryOverride !== 'AI Auto-Detect'
                  ? `${iconColor}80`
                  : undefined,
              }}
            >
              <SelectValue />
            </SelectTrigger>
            <SelectContent
              className={theme === 'dark'
                ? 'bg-[#121212] border-[#262626] text-white'
                : 'bg-white border-gray-200'
              }
            >
              {REGULATORY_OPTIONS.map((opt) => {
                const isAuto = opt.value === 'AI Auto-Detect';
                const label = isAuto ? `✨ AI Auto-Detect (${data.regulatoryStatus || 'Pending...'})` : opt.label;
                return (
                  <SelectItem
                    key={opt.value}
                    value={opt.value}
                    className={`text-sm cursor-pointer ${theme === 'dark'
                      ? 'hover:bg-white/5 focus:bg-white/5'
                      : 'hover:bg-gray-50 focus:bg-gray-50'
                      }`}
                    style={{
                      color: opt.isDefault
                        ? '#A1A1AA'
                        : theme === 'dark' ? '#F3F4F6' : '#1A1A1A',
                    }}
                  >
                    {label}
                  </SelectItem>
                )
              })}
            </SelectContent>
          </Select>
          {regulatoryOverride !== 'AI Auto-Detect' && (
            <p className="text-[10px]" style={{ color: iconColor }}>
              🔒 Manual override active. User entered information is treated as 'Truth'.
            </p>
          )}
        </div>

        <Separator className="bg-white/10" />

        {/* Clinical Endpoints */}
        <div className="space-y-3">
          <Label className="text-xs uppercase tracking-widest" style={{ color: iconColor }}>Clinical Endpoints</Label>

          <EditableInput
            label={primaryLabel}
            value={data.mPFS}
            onChange={(val) => onDataChange({ ...data, mPFS: val })}
            placeholder="—"
            suffix={primarySuffix}
            dataTestId={`${isSearchable ? 'competitor' : 'user'}-primary-endpoint-input`}
            theme={theme}
            source={sources.mPFS}
            onSourceClear={() => onClearSource && onClearSource('mPFS')}
          />

          <EditableInput
            label={secondaryLabel}
            value={data.mOS}
            onChange={(val) => onDataChange({ ...data, mOS: val })}
            placeholder="—"
            suffix={secondarySuffix}
            dataTestId={`${isSearchable ? 'competitor' : 'user'}-secondary-endpoint-input`}
            theme={theme}
            source={sources.mOS}
            onSourceClear={() => onClearSource && onClearSource('mOS')}
          />

          <EditableInput
            label={safetyLabel}
            value={effectiveAeRate > 0 ? effectiveAeRate.toString() : data.aeRate}
            onChange={(val) => {
              const numericVal = parseFloat(val);
              if (!isNaN(numericVal)) {
                // Subtract penalty before saving so the base value remains untainted
                onDataChange({ ...data, aeRate: (numericVal - comorbidityPenalty).toString() });
              } else {
                onDataChange({ ...data, aeRate: val });
              }
            }}
            placeholder="e.g., 15"
            suffix="%"
            dataTestId={`${isSearchable ? 'competitor' : 'user'}-ae-input`}
            theme={theme}
            source={sources.aeRate}
            onSourceClear={() => onClearSource && onClearSource('aeRate')}
          />
          {comorbidityPenalty > 0 && (
            <div className="text-[10px] text-amber-500 mt-1 flex justify-end">
              Includes +{comorbidityPenalty}% Comorbidity Risk Multiplier
            </div>
          )}

          {/* Adherence Slider */}
          <div className="pt-2">
            <div className="flex justify-between items-center mb-2">
              <Label className="text-xs uppercase tracking-widest" style={{ color: iconColor }}>Patient Adherence</Label>
              <span className="font-data font-bold text-sm" style={{ color: iconColor }}>{adherencePct}%</span>
            </div>
            <Slider
              value={[adherencePct]}
              onValueChange={(vals) => onAdherenceChange && onAdherenceChange(vals[0])}
              max={100}
              min={20}
              step={5}
              className="py-2"
              data-testid={`${isSearchable ? 'competitor' : 'user'}-adherence-slider`}
            />
            {adherencePct < 100 && (
              <div className="text-[10px] text-[#E53E3E] mt-1 text-right">
                {100 - adherencePct}% Non-Compliance Penalty Applies
              </div>
            )}
          </div>
        </div>

        <Separator className="bg-white/10" />

        {/* Financial Parameters */}
        <div className="space-y-3">
          <Label className="text-xs uppercase tracking-widest text-[#F59E0B]">Financial Parameters</Label>

          <EditableInput
            label="Market Price / Period"
            value={data.marketPrice}
            onChange={(val) => onDataChange({ ...data, marketPrice: val })}
            placeholder="e.g., 350000"
            prefix={currencySymbol}
            dataTestId={`${isSearchable ? 'competitor' : 'user'}-price-input`}
            theme={theme}
            source={sources.marketPrice}
            onSourceClear={() => onClearSource && onClearSource('marketPrice')}
          />

          <div className="p-3 rounded-sm border" style={{ background: `${iconColor}10`, borderColor: `${iconColor}30` }}>
            <div className="flex justify-between items-start mb-2">
              <span className="text-xs text-muted-foreground font-medium">Effective Price/Period</span>
              <div className="text-right">
                <span className="font-data font-bold text-lg" style={{ color: iconColor }}>
                  {currencySymbol}{effectivePrice.toLocaleString()}
                </span>
                {data.marketPrice && effectivePrice < parseFloat(data.marketPrice) && (
                  <div className="text-[10px] text-muted-foreground line-through decoration-[#E53E3E]/50">
                    {currencySymbol}{parseFloat(data.marketPrice).toLocaleString()}
                  </div>
                )}
              </div>
            </div>
            {/* Detailed Breakdown */}
            {(discountPercent > 0 || (subsidyScheme && subsidyScheme !== 'none')) && (
              <div className="mt-2 pt-2 border-t border-dashed space-y-1" style={{ borderColor: `${iconColor}30` }}>
                {discountPercent > 0 && (
                  <div className="flex justify-between text-[10px]">
                    <span className="text-muted-foreground">Negotiated Discount:</span>
                    <span className="font-data font-medium" style={{ color: iconColor }}>-{discountPercent}%</span>
                  </div>
                )}
                {subsidyScheme && subsidyScheme !== 'none' && (
                  <div className="flex justify-between text-[10px]">
                    <span className="text-muted-foreground">Subsidy Applied:</span>
                    <span className="font-data font-medium" style={{ color: iconColor }}>{subsidyScheme}</span>
                  </div>
                )}
              </div>
            )}
          </div>

          <div className="p-4 rounded-sm border mt-3" style={{ background: `${iconColor}10`, borderColor: `${iconColor}50` }}>
            <div className="flex flex-col gap-1">
              <span className="text-xs uppercase tracking-widest font-bold" style={{ color: iconColor }}>Cost for 1 Patient</span>
              <span className="font-data font-bold text-3xl tracking-tight" style={{ color: iconColor }}>
                {currencySymbol}{costPerPatient.toLocaleString()}
              </span>
              <span className="text-[10px] text-muted-foreground">
                Based on {totalCycles} treatment periods {adherencePct < 100 ? `(+ waste penalty)` : ''}
              </span>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export function TPPBenchmarker({ theme, textPrimary, textSecondary, cardBg, borderColor, selectedPayer, setSelectedPayer, payerSegments }) {
  const {
    selectedDrug,
    selectedRegion,
    calculationResults,
    assetRegulatoryOverride,
    setAssetRegulatoryOverride,
    competitorRegulatoryOverride,
    setCompetitorRegulatoryOverride,
  } = useApp();

  // User's Asset (Left Pane) State - Fully Editable
  const [userAsset, setUserAsset] = useState({
    name: selectedDrug?.name || '',
    indication: selectedDrug?.indication || '',
    mPFS: '',
    mOS: '',
    aeRate: '',
    marketPrice: '',
    regulatoryStatus: 'Approved (Commercial Launch)',
    adherencePct: 100,
  });

  // User Asset Sources (for tooltips)
  const [userSources, setUserSources] = useState({});

  // Loading state while fetching user asset data via web sweep
  const [isUserAssetLoading, setIsUserAssetLoading] = useState(false);

  // Competitor Asset (Right Pane) State - Fully Editable
  const [competitorAsset, setCompetitorAsset] = useState({
    name: '',
    indication: '',
    mPFS: '',
    mOS: '',
    aeRate: '',
    marketPrice: '',
    regulatoryStatus: 'Pending...',
    adherencePct: 100,
  });

  // Competitor Data Sources (for hover tooltips)
  const [competitorSources, setCompetitorSources] = useState({});

  // Search state for competitor
  const [competitorSuggestions, setCompetitorSuggestions] = useState([]);

  // Assumption Drawer State
  const [drawerOpen, setDrawerOpen] = useState(true);
  const [subsidyScheme, setSubsidyScheme] = useState('none');
  const [discountPercent, setDiscountPercent] = useState(0);
  const [totalCycles, setTotalCycles] = useState(12);
  const [populationScale, setPopulationScale] = useState(1000);

  // Comorbidity State
  const [selectedComorbidities, setSelectedComorbidities] = useState([]);
  const [contraindictionAlerts, setContraindictionAlerts] = useState([]);

  // Epidemiology Tooltip Logic
  const epidemiology = selectedDrug?.epidemiology || calculationResults?.epidemiology;
  let popTooltipContent = null;
  let popTooltipColorClass = "";

  if (epidemiology) {
    const { addressable_population, sources } = epidemiology;
    const captureRate = (populationScale / addressable_population) * 100;

    if (captureRate <= 90) {
      popTooltipColorClass = "text-[#008080] border-[#008080]/30";
      popTooltipContent = `Capturing ~${Math.round(captureRate)}% of annual addressable ${selectedDrug?.indication || 'indication'} incidence in ${selectedRegion?.name || 'region'} (${addressable_population.toLocaleString()}). Source: ${sources}`;
    } else if (captureRate <= 100) {
      popTooltipColorClass = "text-[#F59E0B] border-[#F59E0B]/50";
      popTooltipContent = `Capturing ~${Math.round(captureRate)}% of annual addressable ${selectedDrug?.indication || 'indication'} incidence in ${selectedRegion?.name || 'region'} (${addressable_population.toLocaleString()}). Source: ${sources}`;
    } else {
      popTooltipColorClass = "text-[#E53E3E] border-[#E53E3E]/50";
      popTooltipContent = `Exceeds annual ${selectedDrug?.indication || 'indication'} incidence in ${selectedRegion?.name || 'region'} (Max: ~${addressable_population.toLocaleString()}). Model is capturing prevalence/backlog. Source: ${sources}`;
    }
  }

  // Market baseline values (triangulated 2026 data)
  const marketBaselines = {
    IN: { price: 350000, source: 'NPPA 2026', year: 2026 },
    SG: { price: 12000, source: 'MOH Singapore 2026', year: 2026 },
    AE: { price: 35000, source: 'DOH UAE 2026', year: 2026 },
  };

  const currentBaseline = marketBaselines[selectedRegion?.code] || marketBaselines.IN;

  // Initialize user asset from selected drug — prefill from context, then
  // trigger web sweep for any missing clinical fields (mPFS, mOS, aeRate)
  useEffect(() => {
    if (!selectedDrug) return;

    const brain = calculationResults?.commercial_brain;
    const hasPFS = brain?.primary_endpoint_value != null;
    const secVal = brain?.secondary_endpoints?.[0]?.value;
    const hasOS = secVal != null;
    const hasAE = brain?.drug_severe_ae_rate != null && brain?.drug_severe_ae_rate > 0;
    const allPresent = hasPFS && hasOS && hasAE;

    // Step 1: Immediately prefill whatever we have from context
    const contextSource = `Web Intelligence via search — ${selectedDrug.name}`;
    setUserAsset(prev => ({
      ...prev,
      name: selectedDrug.name || '',
      indication: selectedDrug.indication || '',
      mPFS: hasPFS ? brain.primary_endpoint_value.toString() : '',
      mOS: hasOS ? secVal.toString() : '',
      aeRate: hasAE ? (brain.drug_severe_ae_rate * 100).toFixed(0) : '',
      marketPrice: calculationResults?.drug_cost?.toString() || currentBaseline.price.toString(),
    }));
    setUserSources({
      name: contextSource,
      indication: contextSource,
      mPFS: hasPFS ? contextSource : null,
      mOS: hasOS ? contextSource : null,
      aeRate: hasAE ? contextSource : null,
      marketPrice: calculationResults?.drug_cost
        ? `${currentBaseline.source} (${currentBaseline.year})`
        : null,
    });

    // Step 2: If any clinical fields are missing, fetch via web sweep AI
    if (allPresent) return;

    const fetchUserAssetViaWebSweep = async () => {
      setIsUserAssetLoading(true);
      try {
        const response = await axios.get(
          `${API}/competitor/analyze?competitor_name=${encodeURIComponent(selectedDrug.name)}&region_code=${selectedRegion?.code || 'IN'}&indication=${encodeURIComponent(selectedDrug.indication || '')}`
        );

        const sourceUrl = response.data.source_url || null;
        const sweepLabel = response.data.source_label || response.data.source || `Web Intelligence — ${selectedDrug.name}`;
        const priceUrl = response.data.price_url || null;
        const priceLabel = response.data.price_source || `${currentBaseline.source} (${currentBaseline.year})`;

        const mkSrc = (label, url) => url ? { label, url } : label;

        setUserAsset(prev => ({
          ...prev,
          mPFS: !hasPFS && response.data.primary_endpoint_value != null
            ? response.data.primary_endpoint_value.toString()
            : prev.mPFS,
          mOS: prev.mOS,
          aeRate: !hasAE && response.data.severe_ae_rate != null
            ? (response.data.severe_ae_rate * 100).toFixed(0)
            : prev.aeRate,
          marketPrice: !calculationResults?.drug_cost && response.data.base_cost
            ? response.data.base_cost.toString()
            : prev.marketPrice,
          regulatoryStatus: response.data.regulatory_status || prev.regulatoryStatus || 'Approved (Commercial Launch)',
        }));

        setUserSources(prev => ({
          ...prev,
          mPFS: !hasPFS && response.data.primary_endpoint_value != null ? mkSrc(sweepLabel, sourceUrl) : prev.mPFS,
          mOS: prev.mOS,
          aeRate: !hasAE && response.data.severe_ae_rate != null ? mkSrc(sweepLabel, sourceUrl) : prev.aeRate,
          marketPrice: !calculationResults?.drug_cost && response.data.base_cost
            ? mkSrc(priceLabel, priceUrl)
            : prev.marketPrice,
        }));

        toast.success(`Prefilled ${selectedDrug.name} clinical data — hover ⓘ icons for clickable sources`, { duration: 4000 });
      } catch (err) {
        console.warn('[TPP] Web sweep prefill for user asset failed:', err);
        // Silently fail — user can fill fields manually
      } finally {
        setIsUserAssetLoading(false);
      }
    };

    fetchUserAssetViaWebSweep();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedDrug?.name, selectedDrug?.indication, selectedRegion?.code]);

  // ── Re-price both assets whenever the region or payer changes ──────────────
  // The initial prefill uses calculationResults.drug_cost which is stale after
  // a region or payer switch. This effect fetches the real ecosystem-adjusted price.
  useEffect(() => {
    if (!selectedDrug || !selectedRegion?.code || !selectedPayer) return;

    const reprice = async () => {
      try {
        // Re-price user's asset
        const userRes = await axios.get(
          `${API}/pricing/${encodeURIComponent(selectedDrug.name)}?region_code=${selectedRegion.code}&payer_segment=${selectedPayer}`
        );
        const userListPrice = userRes.data.pricing_model?.list_price_per_period;
        if (userListPrice != null) {
          const priceSource = `${currentBaseline.source} (${currentBaseline.year})`;
          setUserAsset(prev => ({ ...prev, marketPrice: userListPrice.toString() }));
          setUserSources(prev => ({ ...prev, marketPrice: priceSource }));
        }
      } catch (err) {
        // Silently fall back to baseline
        setUserAsset(prev => ({ ...prev, marketPrice: currentBaseline.price.toString() }));
      }

      // Re-price competitor if one is already selected
      if (competitorAsset.name) {
        try {
          const compRes = await axios.get(
            `${API}/pricing/${encodeURIComponent(competitorAsset.name)}?region_code=${selectedRegion.code}&payer_segment=${selectedPayer}`
          );
          const compListPrice = compRes.data.pricing_model?.list_price_per_period;
          if (compListPrice != null) {
            const priceSource = `${currentBaseline.source} (${currentBaseline.year})`;
            setCompetitorAsset(prev => ({ ...prev, marketPrice: compListPrice.toString() }));
            setCompetitorSources(prev => ({ ...prev, marketPrice: priceSource }));
          }
        } catch (err) {
          // Silently ignore
        }
      }
    };

    reprice();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedRegion?.code, selectedPayer]);

  // Clear user source when field is edited
  const clearUserSource = (field) => {
    setUserSources(prev => ({ ...prev, [field]: null }));
  };

  // Clear competitor source when field is edited
  const clearCompetitorSource = (field) => {
    setCompetitorSources(prev => ({ ...prev, [field]: null }));
  };

  // Search for competitor
  const handleCompetitorSearch = async (value) => {
    if (value.length > 1) {
      try {
        const response = await axios.get(`${API}/drugs/search?q=${value}&indication=${encodeURIComponent(selectedDrug?.indication || '')}`);
        const filtered = response.data.filter(d => d.name.toLowerCase() !== selectedDrug?.name?.toLowerCase());
        setCompetitorSuggestions(filtered);
      } catch (error) {
        console.error('Search error:', error);
      }
    } else {
      setCompetitorSuggestions([]);
    }
  };

  // Select competitor and prefill data (but keep editable)
  const selectCompetitor = async (drug) => {
    setCompetitorSuggestions([]);

    // Prefill with drug info immediately
    setCompetitorAsset(prev => ({
      ...prev,
      name: drug.name,
      indication: selectedDrug?.indication || drug.indication,
    }));

    try {
      // Fetch competitor analysis to prefill values
      const response = await axios.get(
        `${API}/competitor/analyze?competitor_name=${encodeURIComponent(drug.name)}&region_code=${selectedRegion?.code}&indication=${encodeURIComponent(selectedDrug?.indication || '')}`
      );

      const sourceUrl = response.data.source_url || null;
      const sourceLabel = response.data.source_label || response.data.source || `Web Intelligence — ${drug.name}`;
      const priceUrl = response.data.price_url || null;
      const priceLabel = response.data.price_source || `${currentBaseline.source} (${currentBaseline.year})`;

      const mkSrc = (label, url) => url ? { label, url } : label;

      setCompetitorAsset({
        name: drug.name,
        indication: selectedDrug?.indication || drug.indication,
        mPFS: response.data.primary_endpoint_value?.toString() || '',
        mOS: '',
        aeRate: response.data.severe_ae_rate ? (response.data.severe_ae_rate * 100).toFixed(0) : '',
        marketPrice: response.data.base_cost?.toString() || '',
        regulatoryStatus: response.data.regulatory_status || 'Pending / Named-Patient Access',
        adherencePct: 100,
      });

      // Set data sources for tooltips
      setCompetitorSources({
        name: mkSrc(sourceLabel, sourceUrl),
        indication: mkSrc(sourceLabel, sourceUrl),
        mPFS: response.data.primary_endpoint_value != null ? mkSrc(sourceLabel, sourceUrl) : null,
        mOS: null,
        aeRate: response.data.severe_ae_rate != null ? mkSrc(sourceLabel, sourceUrl) : null,
        marketPrice: response.data.base_cost ? mkSrc(priceLabel, priceUrl) : null,
      });

      toast.success(`Prefilled ${drug.name} data — hover ⓘ icons for clickable sources`);
    } catch (error) {
      console.error('Error fetching competitor:', error);
      toast.info('Using estimated values - all fields are editable');
      const estimateSource = `Estimate based on ${currentBaseline.source}`;
      setCompetitorAsset(prev => ({
        ...prev,
        marketPrice: (currentBaseline.price * 0.5).toString(),
        aeRate: '15',
        regulatoryStatus: 'Pending / Named-Patient Access',
      }));
      setCompetitorSources({
        name: null,
        indication: null,
        mPFS: null,
        mOS: null,
        aeRate: estimateSource,
        marketPrice: estimateSource,
      });
    }
  };

  // Calculate effective price based on payer, subsidy, and discount
  const calculateEffectivePrice = (basePrice, isUserAsset = true) => {
    let price = parseFloat(basePrice) || 0;

    // 1. Payer Coverage Adjustments
    // The backend now provides the `effective_monthly_cost` or `list_price_per_period`.
    // However, the TPP Benchmarker allows users to dynamically slide subsidies BEFORE hitting the API again.
    // For now, we apply the raw discount & subsidy to the base price since payer logic happens server-side.

    // 2. Subsidy Scheme Adjustment
    const scheme = SUBSIDY_SCHEMES.find(s => s.id === subsidyScheme);
    const subsidyFactor = scheme ? scheme.cyclesPaid / scheme.totalCycles : 1;

    // 3. Additional Discount percentage negotiated
    const discountFactor = 1 - (discountPercent / 100);

    return Math.round(price * subsidyFactor * discountFactor);
  };

  // Calculate clinical delta
  const calculateClinicalDelta = () => {
    const userPFS = parseFloat(userAsset.mPFS) || 0;
    const compPFS = parseFloat(competitorAsset.mPFS) || 0;
    if (userPFS === 0 && compPFS === 0) return null;
    return userPFS - compPFS;
  };

  // Calculate OS delta
  const calculateOSDelta = () => {
    const userOS = parseFloat(userAsset.mOS) || 0;
    const compOS = parseFloat(competitorAsset.mOS) || 0;
    if (userOS === 0 && compOS === 0) return null;
    return userOS - compOS;
  };

  // Calculate non-compliance penalty based on adherence
  const getNonCompliancePenalty = (assetObj, basePrice) => {
    // BEWARE DOUBLE PENALTY:
    // If discontinuation cliff is modeled elsewhere in assumptions (e.g. dropOff > 0),
    // we should be careful. Here, we calculate purely the waste/re-administration cost
    // of non-adherence as a standalone penalty.
    const nonComplianceRatio = 1 - ((assetObj.adherencePct || 100) / 100);
    // Non-compliance penalty: Cost * nonComplianceRatio * totalCycles * population
    return calculateEffectivePrice(basePrice) * nonComplianceRatio * totalCycles * populationScale;
  };

  // Calculate financial exposure difference
  const calculateExposureDiff = () => {
    const userEffective = calculateEffectivePrice(userAsset.marketPrice);
    const compEffective = calculateEffectivePrice(competitorAsset.marketPrice);

    const userBaseExposure = userEffective * totalCycles * populationScale;
    const compBaseExposure = compEffective * totalCycles * populationScale;

    const userPenalty = getNonCompliancePenalty(userAsset, userAsset.marketPrice);
    const compPenalty = getNonCompliancePenalty(competitorAsset, competitorAsset.marketPrice);

    return (userBaseExposure + userPenalty) - (compBaseExposure + compPenalty);
  };

  // Check for contraindication alerts
  useEffect(() => {
    const alerts = [];
    selectedComorbidities.forEach(comorbId => {
      const comorb = COMORBIDITY_OPTIONS.find(c => c.id === comorbId);
      if (comorb) {
        const userDrugLower = (userAsset.name || '').toLowerCase();
        if (comorbId === 'renal' && (userDrugLower.includes('sacubitril') || userDrugLower.includes('entresto') || userDrugLower.includes('vymada'))) {
          alerts.push({ type: 'warning', message: 'Monitor renal function and potassium with sacubitril/valsartan' });
        }
        if (comorbId === 'bleeding_risk' && (userDrugLower.includes('tenecteplase') || userDrugLower.includes('alteplase') || userDrugLower.includes('metalyse'))) {
          alerts.push({ type: 'warning', message: 'Thrombolytics contraindicated with active bleeding / high bleeding risk' });
        }
      }
    });
    setContraindictionAlerts(alerts);
  }, [selectedComorbidities, userAsset.name]);

  // Generate executive summary text
  const generateSummary = () => {
    if (!competitorAsset.name) {
      return "Enter competitor details or search for a drug to generate comparison summary.";
    }

    const delta = calculateClinicalDelta();
    const epLabel = endpointSpec?.primaryEndpoint?.label || 'primary endpoint';
    const epUnit = endpointSpec?.primaryEndpoint?.unit || '';
    const deltaText = delta !== null
      ? `${delta > 0 ? '+' : ''}${delta.toFixed(1)} ${epUnit} ${epLabel} delta`
      : 'clinical data pending';

    const exposureDiff = calculateExposureDiff();
    const exposureText = exposureDiff !== 0
      ? `${selectedRegion?.currency_symbol}${Math.abs(exposureDiff).toLocaleString()} ${exposureDiff > 0 ? 'higher' : 'lower'} total exposure`
      : 'financial impact calculation pending';

    return `Comparing ${userAsset.name || 'Your Asset'} against ${competitorAsset.name} for ${userAsset.indication || 'indication'} in ${selectedRegion?.name || 'region'}. Clinical delta: ${deltaText}. Financial impact: ${exposureText}.`;
  };

  const effectiveUserPrice = calculateEffectivePrice(userAsset.marketPrice);
  const effectiveCompPrice = calculateEffectivePrice(competitorAsset.marketPrice);
  const currencySymbol = selectedRegion?.currency_symbol || '₹';

  // Therapy Area Registry entry — drives the clinical endpoint labels shown in both panes
  const endpointSpec = getEndpointsForDrug(selectedDrug)
    || resolveIndication(userAsset.indication)
    || resolveIndication(competitorAsset.indication);

  // Get current scheme definition for display
  const scheme = SUBSIDY_SCHEMES.find(s => s.id === subsidyScheme);

  return (
    <div className="space-y-6">
      {/* Executive Summary Box (Header) */}
      <Card className="glass-card overflow-hidden border-[#008080]/30" style={{ background: `linear-gradient(135deg, ${cardBg} 0%, rgba(0,128,128,0.1) 100%)` }}>
        <CardContent className="py-4">
          <div className="flex items-start gap-4">
            <div className="p-2 rounded-sm bg-[#008080]/20">
              <Beaker className="w-5 h-5 text-[#008080]" />
            </div>
            <div className="flex-1">
              <h3 className={`font-data text-sm uppercase tracking-widest mb-2 ${textPrimary}`}>THE BRIEF</h3>
              <p className={`text-sm ${textSecondary}`}>{generateSummary()}</p>
              <div className="flex items-center gap-4 mt-3 text-xs text-muted-foreground">
                <span>Cost Source: {currentBaseline.source} ({currentBaseline.year})</span>
                <span>|</span>
                <span>All fields are editable</span>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Main Comparison Layout */}
      <div className="flex gap-6">
        {/* Left + Right Comparison Panes */}
        <div className={`flex-1 grid grid-cols-2 gap-6 transition-all`}>

          {/* LEFT PANE: User's Asset - Fully Editable */}
          <AssetCard
            title="YOUR ASSET"
            subtitle={isUserAssetLoading ? 'Fetching via Web Sweep AI…' : 'All fields are editable'}
            icon={FlaskConical}
            iconColor="#008080"
            data={userAsset}
            onDataChange={setUserAsset}
            effectivePrice={effectiveUserPrice}
            theme={theme}
            textPrimary={textPrimary}
            textSecondary={textSecondary}
            cardBg={cardBg}
            borderColor={borderColor}
            currencySymbol={currencySymbol}
            sources={userSources}
            onClearSource={clearUserSource}
            isLoading={isUserAssetLoading}
            subsidyScheme={subsidyScheme && scheme ? scheme.name : null}
            discountPercent={discountPercent}
            comorbidities={selectedComorbidities}
            totalCycles={totalCycles}
            populationScale={populationScale}
            selectedPayer={selectedPayer}
            regulatoryOverride={assetRegulatoryOverride}
            onRegulatoryChange={setAssetRegulatoryOverride}
            adherencePct={userAsset.adherencePct}
            onAdherenceChange={(val) => setUserAsset(prev => ({ ...prev, adherencePct: val }))}
            endpoints={endpointSpec}
          />

          {/* RIGHT PANE: Competitor Asset - Searchable + Editable */}
          <AssetCard
            title="COMPETITOR"
            subtitle="Search to prefill, then edit any field"
            icon={Activity}
            iconColor="#E53E3E"
            data={competitorAsset}
            onDataChange={setCompetitorAsset}
            effectivePrice={effectiveCompPrice}
            theme={theme}
            textPrimary={textPrimary}
            textSecondary={textSecondary}
            cardBg={cardBg}
            borderColor={borderColor}
            currencySymbol={currencySymbol}
            isSearchable={true}
            onSearch={handleCompetitorSearch}
            suggestions={competitorSuggestions}
            onSelectSuggestion={selectCompetitor}
            sources={competitorSources}
            onClearSource={clearCompetitorSource}
            subsidyScheme={subsidyScheme && scheme ? scheme.name : null}
            discountPercent={discountPercent}
            comorbidities={selectedComorbidities}
            totalCycles={totalCycles}
            populationScale={populationScale}
            selectedPayer={selectedPayer}
            regulatoryOverride={competitorRegulatoryOverride}
            onRegulatoryChange={setCompetitorRegulatoryOverride}
            adherencePct={competitorAsset.adherencePct}
            onAdherenceChange={(val) => setCompetitorAsset(prev => ({ ...prev, adherencePct: val }))}
            endpoints={endpointSpec}
          />
        </div>

        {/* ASSUMPTION DRAWER (Right Sidebar) */}
        <div className={`transition-all ${drawerOpen ? 'w-72' : 'w-10'}`}>
          <Card className="glass-card h-full overflow-hidden" style={{ borderColor }}>
            <CardHeader
              className="pb-2 cursor-pointer flex flex-row items-center justify-between"
              onClick={() => setDrawerOpen(!drawerOpen)}
            >
              {drawerOpen ? (
                <>
                  <CardTitle className={`font-data text-xs ${textPrimary}`}>ASSUMPTIONS</CardTitle>
                  <ChevronRight className="w-4 h-4 text-muted-foreground" />
                </>
              ) : (
                <ChevronDown className="w-4 h-4 text-muted-foreground mx-auto" />
              )}
            </CardHeader>

            {drawerOpen && (
              <CardContent className="space-y-4">
                {/* Payer Segment (Passed from WarRoom parent) */}
                {payerSegments && payerSegments.length > 0 && selectedPayer && setSelectedPayer && (
                  <>
                    <div>
                      <Label className="text-xs uppercase tracking-widest text-muted-foreground mb-2 block">Payer Segment</Label>
                      <Select value={selectedPayer} onValueChange={setSelectedPayer}>
                        <SelectTrigger className={`w-full text-sm font-data ${theme === 'dark' ? 'bg-[#050505] border-[#262626] text-white' : 'bg-white border-gray-300 text-gray-900'}`}>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent className={theme === 'dark' ? 'bg-[#121212] border-[#262626] text-white' : 'bg-white border-gray-200 text-gray-900'}>
                          {payerSegments.map((seg) => (
                            <SelectItem key={seg.code} value={seg.code} className={theme === 'dark' ? 'text-white' : 'text-gray-900'}>
                              <div className="flex items-center gap-2">
                                {seg.code === 'oop' ? <Users className="w-4 h-4" /> :
                                  seg.code.includes('insurance') ? <Building2 className="w-4 h-4" /> :
                                    <ShieldCheck className="w-4 h-4" />}
                                <span>{seg.name}</span>
                              </div>
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <div className="text-[10px] text-muted-foreground mt-1">
                        Select payer to reflect adjusted pricing
                      </div>
                    </div>
                    <Separator className="bg-white/10" />
                  </>
                )}

                {/* Subsidy Scheme */}
                <div>
                  <Label className="text-xs uppercase tracking-widest text-muted-foreground mb-2 block">Subsidy Scheme</Label>
                  <Select value={subsidyScheme} onValueChange={setSubsidyScheme}>
                    <SelectTrigger data-testid="subsidy-scheme-select" className={`w-full text-sm ${theme === 'dark' ? 'bg-[#050505] border-[#262626] text-white' : 'bg-white border-gray-300 text-gray-900'}`}>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent className={theme === 'dark' ? 'bg-[#121212] border-[#262626] text-white' : 'bg-white border-gray-200 text-gray-900'}>
                      {SUBSIDY_SCHEMES.map(scheme => (
                        <SelectItem key={scheme.id} value={scheme.id} className={theme === 'dark' ? 'text-white' : 'text-gray-900'}>
                          {scheme.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <div className="text-xs text-muted-foreground mt-1">
                    {SUBSIDY_SCHEMES.find(s => s.id === subsidyScheme)?.cyclesPaid} of {SUBSIDY_SCHEMES.find(s => s.id === subsidyScheme)?.totalCycles} cycles paid
                  </div>
                </div>

                <Separator className="bg-white/10" />

                {/* Discount Percentage - NEW */}
                <div>
                  <Label className="text-xs uppercase tracking-widest text-muted-foreground mb-2 block flex items-center gap-2">
                    <Percent className="w-3 h-3" />
                    Discount: {discountPercent}%
                  </Label>
                  <Slider
                    data-testid="discount-slider"
                    value={[discountPercent]}
                    onValueChange={([val]) => setDiscountPercent(val)}
                    min={0}
                    max={50}
                    step={1}
                    className="mt-2"
                  />
                  <div className="text-xs text-muted-foreground mt-1">
                    Additional negotiated discount on top of subsidy
                  </div>
                </div>

                <Separator className="bg-white/10" />

                {/* Total Cycles */}
                <div>
                  <div className="flex items-center gap-2 mb-2">
                    <Label className="text-xs uppercase tracking-widest text-muted-foreground">
                      Treatment Duration: {totalCycles} cycles
                    </Label>
                    <TooltipProvider>
                      <Tooltip delayDuration={300}>
                        <TooltipTrigger asChild>
                          <Info className="w-3.5 h-3.5 text-muted-foreground hover:text-white cursor-help transition-colors" />
                        </TooltipTrigger>
                        <TooltipContent side="left" className="w-64 p-3 bg-slate-900 border-slate-700 text-xs">
                          <p className="font-semibold text-slate-200 mb-1">Treatment Duration</p>
                          <p className="text-slate-400">
                            A treatment period is one dispensing/dosing interval (e.g. a month of therapy). Dosing frequency varies by asset (daily oral, weekly injection, etc.).
                          </p>
                          <p className="text-slate-400 mt-1">
                            Ensure your period count maps to the total intended duration to prevent cost over- or under-estimation.
                          </p>
                        </TooltipContent>
                      </Tooltip>
                    </TooltipProvider>
                  </div>
                  <Slider
                    data-testid="cycles-slider"
                    value={[totalCycles]}
                    onValueChange={([val]) => setTotalCycles(val)}
                    min={1}
                    max={24}
                    step={1}
                    className="mt-2"
                  />
                </div>

                <Separator className="bg-white/10" />

                {/* Population Scale */}
                <div>
                  <Label className="text-xs uppercase tracking-widest text-muted-foreground mb-2 block">
                    Population: {populationScale.toLocaleString()} patients
                  </Label>
                  <Slider
                    data-testid="population-slider"
                    value={[populationScale]}
                    onValueChange={([val]) => setPopulationScale(val)}
                    min={100}
                    max={10000}
                    step={100}
                    className="mt-2"
                    tooltipContent={popTooltipContent}
                    tooltipColorClass={popTooltipColorClass}
                  />
                </div>

                <Separator className="bg-white/10" />

                {/* Comorbidity Chips */}
                <div>
                  <Label className="text-xs uppercase tracking-widest text-muted-foreground mb-2 block">Patient Comorbidities</Label>
                  <div className="flex flex-wrap gap-1">
                    {COMORBIDITY_OPTIONS.map(comorb => (
                      <Badge
                        key={comorb.id}
                        variant={selectedComorbidities.includes(comorb.id) ? 'default' : 'outline'}
                        className={`cursor-pointer text-xs ${selectedComorbidities.includes(comorb.id) ? 'bg-[#008080] text-white' : ''}`}
                        onClick={() => {
                          setSelectedComorbidities(prev =>
                            prev.includes(comorb.id)
                              ? prev.filter(id => id !== comorb.id)
                              : [...prev, comorb.id]
                          );
                        }}
                      >
                        {comorb.label}
                      </Badge>
                    ))}
                  </div>
                </div>

                {/* Contraindication Alerts */}
                {contraindictionAlerts.length > 0 && (
                  <div className="p-3 rounded-sm bg-[#F59E0B]/10 border border-[#F59E0B]/30">
                    <div className="flex items-center gap-2 mb-2">
                      <AlertTriangle className="w-4 h-4 text-[#F59E0B]" />
                      <span className="text-xs font-bold text-[#F59E0B]">ALERTS</span>
                    </div>
                    {contraindictionAlerts.map((alert, idx) => (
                      <p key={idx} className="text-xs text-muted-foreground">{alert.message}</p>
                    ))}
                  </div>
                )}
              </CardContent>
            )}
          </Card>
        </div>
      </div>

      {/* Comparison Results Grid */}
      {(userAsset.name || competitorAsset.name) && (
        <Card className="glass-card overflow-hidden" style={{ borderColor }}>
          <CardHeader className="pb-3">
            <CardTitle className={`font-data text-sm ${textPrimary}`}>HEAD-TO-HEAD COMPARISON</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b" style={{ borderColor }}>
                    <th className={`text-left py-2 px-3 font-medium ${textPrimary}`}>Metric</th>
                    <th className={`text-right py-2 px-3 font-medium text-[#008080]`}>{userAsset.name || 'Your Asset'}</th>
                    <th className={`text-right py-2 px-3 font-medium text-[#E53E3E]`}>{competitorAsset.name || 'Competitor'}</th>
                    <th className={`text-right py-2 px-3 font-medium ${textPrimary}`}>Delta</th>
                  </tr>
                </thead>
                <tbody>
                  <tr className="border-b" style={{ borderColor }}>
                    <td className={`py-3 px-3 ${textSecondary}`}>{endpointSpec?.primaryEndpoint?.label || 'Primary Endpoint'}</td>
                    <td className={`text-right py-3 px-3 font-data ${textPrimary}`}>{userAsset.mPFS || 'N/A'} {endpointSpec?.primaryEndpoint?.unit || ''}</td>
                    <td className={`text-right py-3 px-3 font-data ${textPrimary}`}>{competitorAsset.mPFS || 'N/A'} {endpointSpec?.primaryEndpoint?.unit || ''}</td>
                    <td className={`text-right py-3 px-3 font-data font-bold ${calculateClinicalDelta() !== null ? (calculateClinicalDelta() > 0 ? 'text-[#008080]' : 'text-[#E53E3E]') : textPrimary}`}>
                      {calculateClinicalDelta() !== null ? `${calculateClinicalDelta() > 0 ? '+' : ''}${calculateClinicalDelta().toFixed(1)} ${endpointSpec?.primaryEndpoint?.unit || ''}` : 'N/A'}
                    </td>
                  </tr>
                  {endpointSpec?.secondaryEndpoints?.[0] && (
                  <tr className="border-b" style={{ borderColor }}>
                    <td className={`py-3 px-3 ${textSecondary}`}>{endpointSpec.secondaryEndpoints[0].label}</td>
                    <td className={`text-right py-3 px-3 font-data ${textPrimary}`}>{userAsset.mOS || 'N/A'} {endpointSpec.secondaryEndpoints[0].unit || ''}</td>
                    <td className={`text-right py-3 px-3 font-data ${textPrimary}`}>{competitorAsset.mOS || 'N/A'} {endpointSpec.secondaryEndpoints[0].unit || ''}</td>
                    <td className={`text-right py-3 px-3 font-data font-bold ${calculateOSDelta() !== null ? (calculateOSDelta() > 0 ? 'text-[#008080]' : 'text-[#E53E3E]') : textPrimary}`}>
                      {calculateOSDelta() !== null ? `${calculateOSDelta() > 0 ? '+' : ''}${calculateOSDelta().toFixed(1)} ${endpointSpec.secondaryEndpoints[0].unit || ''}` : 'N/A'}
                    </td>
                  </tr>
                  )}
                  <tr className="border-b" style={{ borderColor }}>
                    <td className={`py-3 px-3 ${textSecondary}`}>{endpointSpec?.safetyLabel ? `${endpointSpec.safetyLabel} Rate` : 'Serious AE Rate'}</td>
                    <td className={`text-right py-3 px-3 font-data ${textPrimary}`}>{userAsset.aeRate || 'N/A'}%</td>
                    <td className={`text-right py-3 px-3 font-data ${textPrimary}`}>{competitorAsset.aeRate || 'N/A'}%</td>
                    <td className={`text-right py-3 px-3 font-data ${textPrimary}`}>
                      {userAsset.aeRate && competitorAsset.aeRate
                        ? `${(parseFloat(userAsset.aeRate) - parseFloat(competitorAsset.aeRate)) > 0 ? '+' : ''}${(parseFloat(userAsset.aeRate) - parseFloat(competitorAsset.aeRate)).toFixed(0)}%`
                        : '-'}
                    </td>
                  </tr>
                  <tr className="border-b" style={{ borderColor }}>
                    <td className={`py-3 px-3 ${textSecondary}`}>Effective Price/Period</td>
                    <td className={`text-right py-3 px-3 font-data text-[#008080]`}>{currencySymbol}{effectiveUserPrice.toLocaleString()}</td>
                    <td className={`text-right py-3 px-3 font-data text-[#E53E3E]`}>{currencySymbol}{effectiveCompPrice.toLocaleString()}</td>
                    <td className={`text-right py-3 px-3 font-data font-bold ${effectiveUserPrice > effectiveCompPrice ? 'text-[#E53E3E]' : 'text-[#008080]'}`}>
                      {currencySymbol}{Math.abs(effectiveUserPrice - effectiveCompPrice).toLocaleString()}
                    </td>
                  </tr>
                  <tr>
                    <td className={`py-3 px-3 font-bold ${textPrimary}`}>Total Exposure ({populationScale.toLocaleString()} pts)</td>
                    <td className={`text-right py-3 px-3 font-data font-bold text-[#008080]`}>
                      {currencySymbol}{(effectiveUserPrice * totalCycles * populationScale).toLocaleString()}
                    </td>
                    <td className={`text-right py-3 px-3 font-data font-bold text-[#E53E3E]`}>
                      {currencySymbol}{(effectiveCompPrice * totalCycles * populationScale).toLocaleString()}
                    </td>
                    <td className={`text-right py-3 px-3 font-data font-bold ${calculateExposureDiff() > 0 ? 'text-[#E53E3E]' : 'text-[#008080]'}`}>
                      {currencySymbol}{Math.abs(calculateExposureDiff()).toLocaleString()}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}

      {/* CALCULATION ASSUMPTIONS & METHODOLOGY - Collapsible Section */}
      {(userAsset.name || competitorAsset.name) && (
        <MethodologySection
          userAsset={userAsset}
          competitorAsset={competitorAsset}
          subsidyScheme={subsidyScheme}
          discountPercent={discountPercent}
          totalCycles={totalCycles}
          populationScale={populationScale}
          effectiveUserPrice={effectiveUserPrice}
          effectiveCompPrice={effectiveCompPrice}
          currencySymbol={currencySymbol}
          theme={theme}
          textPrimary={textPrimary}
          textSecondary={textSecondary}
          borderColor={borderColor}
        />
      )}
    </div>
  );
}

export default TPPBenchmarker;
