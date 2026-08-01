import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowRight, AlertTriangle, FileText, TrendingUp, ShieldCheck, Users, Building2, Home, Lightbulb, Loader2, RefreshCcw, Info as InfoIcon, ChevronDown, HelpCircle } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Separator } from '../components/ui/separator';
import { Badge } from '../components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine, Legend, ComposedChart, Line } from 'recharts';
import axios from 'axios';
import { useApp } from '../context/AppContext';
import { toast } from 'sonner';
import { RegionSwitcher } from '../components/RegionSwitcher';
import { ThemeSwitcher } from '../components/ThemeSwitcher';
import { IndicationSelectDialog } from '../components/IndicationSelectDialog';
import { AnalysisLoadingOverlay } from '../components/AnalysisLoadingOverlay';
import { driver } from 'driver.js';
import 'driver.js/dist/driver.css';
import { LogisticalBurdenSnippet } from '../components/LogisticalBurdenSnippet';
import { TermTooltip } from '../components/InfoTooltip';
import PatientCashFlow from '../components/PatientCashFlow';
import IntelligenceReport from '../components/IntelligenceReport';
import { Search } from 'lucide-react';
import { Input } from '../components/ui/input';
import { getEndpointsForDrug } from '../lib/therapyAreas';
import CoverageMatrix from '../components/CoverageMatrix';
import DataQualityPanel from '../components/DataQualityPanel';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || '';
const API = (BACKEND_URL && BACKEND_URL.startsWith('http')) ? `${BACKEND_URL}/api` : '/api';

// Endpoint labels come from the Therapy Area Registry (resolved by indication,
// falling back to category). The API also returns primary_endpoint_label.
const getEfficacyLabel = (drug, brain) =>
  brain?.primary_endpoint_label
  || getEndpointsForDrug(drug)?.primaryEndpoint?.label
  || 'Primary Endpoint';

const getSecondaryLabel = (drug, brain) =>
  brain?.secondary_endpoints?.[0]?.label
  || getEndpointsForDrug(drug)?.secondaryEndpoints?.[0]?.label
  || 'Secondary Endpoint';

// Static fallbacks by region so dropdown always shows options even when API fails
// IMPORTANT: must be outside component so it is not re-created on every render
const STATIC_PAYER_SEGMENTS = {
  IN: [
    { code: 'oop', name: 'Out-of-Pocket (OOP)' },
    { code: 'private_insurance', name: 'Private Insurance' },
    { code: 'cghs', name: 'CGHS (Govt Scheme)' },
    { code: 'echs', name: 'ECHS (Ex-Servicemen)' },
    { code: 'ayushman_bharat', name: 'Ayushman Bharat (PMJAY)' },
  ],
  SG: [
    { code: 'oop', name: 'Out-of-Pocket' },
    { code: 'medishield_life', name: 'MediShield Life' },
    { code: 'private_insurance', name: 'Private Insurance' },
  ],
  AE: [
    { code: 'oop', name: 'Out-of-Pocket' },
    { code: 'private_insurance', name: 'Private Insurance' },
    { code: 'thiqa', name: 'Thiqa (UAE Nationals)' },
  ],
};

export default function ExecutiveDashboard() {
  const { selectedDrug, setSelectedDrug, selectedRegion, calculationResults, setCalculationResults, assetRegulatoryOverride, theme, clearSession, customCompetitors, hasSeenTour, setHasSeenTour, runTourPhaseB, setRunTourPhaseB } = useApp();
  const [calculation, setCalculation] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const navigate = useNavigate();

  // Dynamic Pricing Engine state
  const [payerSegments, setPayerSegments] = useState(
    STATIC_PAYER_SEGMENTS[selectedRegion?.code] || STATIC_PAYER_SEGMENTS['IN']
  );
  const [selectedPayer, setSelectedPayer] = useState('oop');
  const [news, setNews] = useState({ summary: '', sources: [] });
  const [pricingModel, setPricingModel] = useState(null);

  // Search Context State
  const [searchQuery, setSearchQuery] = useState('');
  const [suggestions, setSuggestions] = useState([]);
  const [isSearchLoading, setIsSearchLoading] = useState(false);
  const [loadingDrugName, setLoadingDrugName] = useState('');
  const [didYouMean, setDidYouMean] = useState(null);

  // Search Indication modal state
  const [pendingDrug, setPendingDrug] = useState(null);
  const [availableIndications, setAvailableIndications] = useState([]);

  // Reset payer segments immediately when region changes
  useEffect(() => {
    const regionSegments = STATIC_PAYER_SEGMENTS[selectedRegion?.code] || STATIC_PAYER_SEGMENTS['IN'] || [];
    setPayerSegments(regionSegments);
    setSelectedPayer('oop');
  }, [selectedRegion?.code]);
  const [showStrategicOverlay, setShowStrategicOverlay] = useState(false);
  const [briefingData, setBriefingData] = useState(null);
  const [isGeneratingBriefing, setIsGeneratingBriefing] = useState(false);
  const [showIntelligenceReport, setShowIntelligenceReport] = useState(false);
  const [showIndicationModal, setShowIndicationModal] = useState(false);

  // Auto-start Phase B Tour if the user hasn't seen it and data is loaded
  useEffect(() => {
    if (!hasSeenTour && !runTourPhaseB && calculation) {
      setTimeout(() => setRunTourPhaseB(true), 1500); // Delay for animations to finish
    }
  }, [hasSeenTour, runTourPhaseB, calculation, setRunTourPhaseB]);

  useEffect(() => {
    if (runTourPhaseB) {
      const driverObj = driver({
        showProgress: false,
        popoverClass: theme === 'dark' ? 'driver-popover-dark' : 'driver-popover-light',
        steps: [
          {
            element: '.tour-cost-metrics',
            popover: {
              title: 'Step 2: Effective Cost',
              description: 'We dynamically calculate the actual out-of-pocket cost per cycle based on regional subsidies.',
              side: 'left',
              align: 'start'
            }
          },
          {
            element: '.tour-clinical-endpoints',
            popover: {
              title: 'Step 3: Clinical Integration',
              description: 'Efficacy and toxicity data are factored directly into the financial liability engine.',
              side: 'left',
              align: 'start'
            }
          },
          {
            element: '.tour-deal-architect',
            popover: {
              title: 'Step 4: Deal Architect',
              description: 'Real-time alerts warn if affordability programs are missing or recommend specific structures.',
              side: 'left',
              align: 'start'
            }
          },
          {
            element: '.tour-war-room-btn',
            popover: {
              title: 'Step 5: The War Room',
              description: 'Enter the cockpit to simulate competitor scenarios, calculate ICER, and model custom pricing deals.',
              side: 'top',
              align: 'center'
            }
          }
        ],
        onDestroyStarted: () => {
          if (!driverObj.hasNextStep() || window.confirm("Finish the tour?")) {
            driverObj.destroy();
            setRunTourPhaseB(false);
            setHasSeenTour(true);
          }
        },
      });
      driverObj.drive();
    }
  }, [runTourPhaseB, setRunTourPhaseB, setHasSeenTour, theme]);

  // Open modal and fetch briefing dynamically
  const handleOpenStrategicOverlay = async () => {
    setShowStrategicOverlay(true);
    setIsGeneratingBriefing(true);
    try {
      const brain = calculation?.commercial_brain || {};
      const params = new URLSearchParams({
        drug_name: selectedDrug.name,
        region_code: selectedRegion.code || 'IN',
        drug_cost: calculation?.drug_cost || 0,
        total_liability: calculation?.total_liability || 0,
        competitor_name: selectedDrug.competitor_name || 'Standard of Care',
        pap_scheme: pricingModel?.pap_scheme_applied || 'None',
        ae_rate: brain.drug_severe_ae_rate || 0.15,
        ...(brain.median_pfs_months ? { median_pfs: brain.median_pfs_months } : {}),
        indication: selectedDrug.indication || '',
        deal_architect_status: pricingModel?.deal_architect_advice ? 'SIMULATED / RECOMMENDED ONLY (NOT LIVE)' : 'CURRENT MARKET REALITY',
        proposed_pap_scheme: pricingModel?.pap_scheme_applied || 'None',
        regulatory_override: assetRegulatoryOverride || 'AI Auto-Detect',
      });
      const res = await axios.get(`${API}/strategic-briefing/generate?${params}`);
      setBriefingData(res.data);
    } catch (err) {
      console.error('[StrategicBriefing] fetch failed:', err);
      toast.error('Failed to generate briefing — check backend connection.');
      setBriefingData(null);
    } finally {
      setIsGeneratingBriefing(false);
    }
  };

  const handleSearch = async (value) => {
    setSearchQuery(value);
    if (value.length > 1) {
      try {
        const response = await axios.get(`${API}/drugs/search?q=${value}`);
        const data = response.data;
        // Support both old (array) and new ({ results, did_you_mean }) response shapes
        if (Array.isArray(data)) {
          setSuggestions(data);
          setDidYouMean(null);
        } else {
          setSuggestions(data.results || []);
          setDidYouMean(data.did_you_mean || null);
        }
      } catch (error) {
        console.error('Search error:', error);
      }
    } else {
      setSuggestions([]);
      setDidYouMean(null);
    }
  };

  const handleSelectDrug = async (drugId, drugName = null, drugIndication = null) => {
    setIsSearchLoading(true);
    setLoadingDrugName(drugName || drugId);
    setSuggestions([]); // Hide suggestions immediately

    try {
      // First, check if this drug has multiple indications
      // Pass drug name as query param for UUID-based IDs
      let indicationsUrl = `${API}/drugs/${drugId}/indications`;
      if (drugName) {
        indicationsUrl += `?name=${encodeURIComponent(drugName)}`;
      }
      const indicationsResponse = await axios.get(indicationsUrl);
      const indicationsData = indicationsResponse.data;

      if (indicationsData.has_multiple && indicationsData.indications.length > 1) {
        // Drug has multiple indications - show selection dialog
        setPendingDrug({ id: drugId, name: indicationsData.drug_name || drugName });
        setAvailableIndications(indicationsData.indications);
        setShowIndicationModal(true);
        setIsSearchLoading(false);
        setLoadingDrugName('');
        return;
      }

      // Single indication - proceed directly with analysis
      let analyzeUrl = `${API}/drugs/analyze?drug_name=${encodeURIComponent(indicationsData.drug_name || drugName || drugId)}&region_code=${selectedRegion.code}`;

      // Explicitly append the indication if provided by the dropdown array
      if (drugIndication && !drugIndication.includes("Click to analyze via real-time web search")) {
        analyzeUrl += `&indication=${encodeURIComponent(drugIndication)}`;
      }

      const response = await axios.post(analyzeUrl);
      setSelectedDrug(response.data);
      // Let existing React useEffect fetch new drug data
      setSearchQuery('');
    } catch (error) {
      console.error('Error fetching drug:', error);
      toast.error('Failed to load drug information');
    } finally {
      setIsSearchLoading(false);
      setLoadingDrugName('');
    }
  };

  const handleIndicationSelect = async (selectedIndication) => {
    if (!pendingDrug) return;

    setIsSearchLoading(true);
    setLoadingDrugName(pendingDrug.name);
    setShowIndicationModal(false);

    try {
      // Analyze with selected indication
      let analyzeUrl = `${API}/drugs/analyze?drug_name=${encodeURIComponent(pendingDrug.name)}&indication=${encodeURIComponent(selectedIndication)}&region_code=${selectedRegion.code}`;

      const response = await axios.post(analyzeUrl);
      setSelectedDrug(response.data);
      setPendingDrug(null);
      setAvailableIndications([]);
      setSearchQuery('');
    } catch (error) {
      console.error('Error analyzing drug with indication:', error);
      toast.error('Failed to analyze drug');
    } finally {
      setIsSearchLoading(false);
      setLoadingDrugName('');
    }
  };

  useEffect(() => {
    if (!selectedDrug) {
      navigate('/');
      return;
    }

    let isCancelled = false;

    const fetchData = async () => {
      setIsLoading(true);
      try {
        // Fetch calculation data first (critical)
        const calcResponse = await axios.post(`${API}/calculate?drug_id=${selectedDrug.id}&region_code=${selectedRegion.code}`);

        if (isCancelled) return;

        setCalculation(calcResponse.data);
        setCalculationResults(calcResponse.data);

        // Fetch non-critical data in background - don't fail if these error
        axios.get(`${API}/news/${selectedDrug.id}?region=${selectedRegion.name}&t=${new Date().getTime()}`)
          .then(res => !isCancelled && setNews(res.data))
          .catch(() => !isCancelled && setNews({ summary: 'No threats found for this asset - market stable.', sources: [] }));

        // Seed with static fallback immediately so dropdown is never empty
        if (!isCancelled) {
          setPayerSegments(
            STATIC_PAYER_SEGMENTS[selectedRegion.code] || STATIC_PAYER_SEGMENTS['IN']
          );
        }
        // Then try to override with live API data (richer descriptions etc.)
        axios.get(`${API}/regions/${selectedRegion.code}/payer-segments`)
          .then(res => {
            const segs = res.data.segments || [];
            if (!isCancelled && segs.length > 0) setPayerSegments(segs);
          })
          .catch(() => { /* static fallback already set above */ });

      } catch (error) {
        if (isCancelled) return;

        console.error('Error fetching dashboard data:', error);
        // If drug not found (404), silently redirect to search
        if (error.response?.status === 404) {
          clearSession();
          navigate('/');
        }
        // Don't show error toast - just let the user see the loading state
      } finally {
        if (!isCancelled) {
          setIsLoading(false);
        }
      }
    };

    fetchData();

    return () => {
      isCancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedDrug?.id, selectedRegion?.code]);

  // Fetch pricing when payer segment changes
  useEffect(() => {
    if (!selectedDrug || !selectedPayer) return;

    const fetchPricing = async () => {
      try {
        const response = await axios.get(
          `${API}/pricing/${encodeURIComponent(selectedDrug.name)}?region_code=${selectedRegion.code}&payer_segment=${selectedPayer}`
        );
        setPricingModel(response.data.pricing_model);
      } catch (error) {
        console.error('Error fetching pricing:', error);
      }
    };

    fetchPricing();
  }, [selectedDrug, selectedRegion, selectedPayer]);

  const handleForceRefresh = async () => {
    if (!selectedDrug) return;
    setIsRefreshing(true);
    try {
      const response = await axios.post(
        `${API}/drugs/analyze?drug_name=${encodeURIComponent(selectedDrug.name)}&region_code=${selectedRegion.code}&force_refresh=true`
      );
      setSelectedDrug(response.data);
      // Data changes will cascade via selectedDrug dependency in useEffects
    } catch (error) {
      console.error('Failed to force refresh data:', error);
    } finally {
      setIsRefreshing(false);
    }
  };

  if (!selectedDrug || isLoading) {
    return (
      <div className={`min-h-screen flex items-center justify-center ${theme === 'dark' ? 'bg-[#050505]' : 'bg-gray-50'}`}>
        <div className={`font-data ${theme === 'dark' ? 'text-white' : 'text-gray-900'}`}>LOADING DATA...</div>
      </div>
    );
  }

  // Prepare cycle chart data for "sawtooth" visualization
  const cycleChartData = pricingModel?.period_data?.map(c => ({
    name: `C${c.cycle}`,
    cycle: c.cycle,
    patient: c.patient_pay,
    insurer: c.insurer_pay,
    govt: c.govt_pay,
    effective: pricingModel.effective_monthly_cost,
    isFree: c.is_free_period
  })) || [];

  // Dynamic colors based on theme
  const textColor = theme === 'dark' ? '#E5E5E5' : '#1A1A1A';
  const mutedColor = theme === 'dark' ? '#737373' : '#6B7280';
  const bgColor = theme === 'dark' ? '#050505' : '#FAFAFA';
  const surfaceBg = theme === 'dark' ? '#121212' : '#FFFFFF';
  const borderColor = theme === 'dark' ? '#262626' : '#E5E5E5';
  const effectiveAvgColor = theme === 'dark' ? '#FFFFFF' : '#1A1A1A'; // White for dark, black for light

  // The Brain: which modules apply to this drug + indication (defaults to all-on
  // so the UI degrades gracefully if the backend hasn't supplied a profile yet)
  const applicabilityModules = calculation?.applicability?.modules || {};

  const getPayerIcon = (code) => {
    if (code === 'oop') return <Users className="w-4 h-4" />;
    if (code.includes('insurance')) return <Building2 className="w-4 h-4" />;
    return <ShieldCheck className="w-4 h-4" />;
  };

  return (
    <div className="war-room min-h-screen relative">
      {/* Subtle background gradient for depth - Dark Mode Only */}
      {theme === 'dark' && (
        <>
          <div className="fixed inset-0 bg-gradient-to-br from-[#050505] via-[#0a0a0a] to-[#050505] -z-10" />
          <div className="fixed inset-0 opacity-30 -z-10" style={{
            background: 'radial-gradient(ellipse at 20% 20%, rgba(0, 128, 128, 0.08) 0%, transparent 50%), radial-gradient(ellipse at 80% 80%, rgba(229, 62, 62, 0.05) 0%, transparent 50%)'
          }} />
        </>
      )}

      {/* Global Header with Glass Effect */}
      <div className={`glass-surface border-b px-6 py-4 flex items-center justify-between sticky top-0 z-50`} style={{ borderColor }}>
        <div className="flex items-center gap-4">
          <Button
            data-testid="home-btn"
            variant="ghost"
            size="icon"
            onClick={() => navigate('/')}
            className="hover:bg-white/5"
            style={{ color: textColor }}
            title="Home"
          >
            <Home className="w-5 h-5" />
          </Button>
          <div>
            <h1 className="text-2xl font-bold font-data" style={{ color: textColor }}>EXECUTIVE DASHBOARD</h1>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <Button
            onClick={() => setShowIntelligenceReport(true)}
            className="bg-[#F8FAFC] text-[#0f172a] hover:bg-white hover:scale-105 transition-all shadow-lg font-medium border border-transparent"
            size="sm"
          >
            <FileText className="w-4 h-4 mr-2" />
            Intelligence Report
          </Button>
          {/* Payer Segment in Header */}
          <div className="flex items-center gap-2">
            <span className="text-xs uppercase tracking-wider" style={{ color: mutedColor }}>PAYER</span>
            <Select value={selectedPayer} onValueChange={setSelectedPayer}>
              <SelectTrigger
                className="w-[180px] h-9 font-data text-sm glass-input"
                style={{ color: textColor }}
                data-testid="payer-segment-selector"
              >
                <SelectValue placeholder="Select Payer" />
              </SelectTrigger>
              <SelectContent className="glass-card" style={{ borderColor }}>
                {payerSegments.map((seg) => (
                  <SelectItem key={seg.code} value={seg.code} data-testid={`payer-option-${seg.code}`}>
                    <div className="flex items-center gap-2">
                      {getPayerIcon(seg.code)}
                      <span>{seg.name}</span>
                    </div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <button
            onClick={() => {
              setHasSeenTour(false);
              setRunTourPhaseB(true);
            }}
            className="flex items-center gap-2 px-3 py-2 h-9 text-sm font-medium transition-colors rounded-sm border glass-button opacity-80 hover:opacity-100"
            style={{ color: textColor, borderColor }}
          >
            <HelpCircle className="w-4 h-4" />
            <span className="hidden sm:inline">Tour</span>
          </button>
          <ThemeSwitcher />
          <div className="pl-3 ml-1 border-l" style={{ borderColor }}>
            <RegionSwitcher />
          </div>
        </div>
      </div>

      {/* 3-Column Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 h-[calc(100vh-80px)]">
        {/* Column 1: Identity */}
        <div className="border-r p-6 space-y-6 overflow-y-auto custom-scrollbar" style={{ borderColor }} data-testid="drug-identity-section">
          {/* Global Drug Search Bar */}
          <div className="relative group">
            <div className="absolute inset-y-0 left-3 flex items-center pointer-events-none">
              <Search className={`w-4 h-4 transition-colors ${searchQuery ? 'text-[#008080]' : 'text-muted-foreground'}`} />
            </div>
            <input
              type="text"
              placeholder="Enter Brand Name..."
              className="w-full bg-black/20 dark:bg-white/5 border border-white/10 rounded-lg py-2.5 pl-10 pr-4 text-sm focus:outline-none focus:ring-1 focus:ring-[#008080]/50 transition-all font-data"
              value={searchQuery}
              onChange={(e) => handleSearch(e.target.value)}
              data-testid="global-drug-search"
            />
            {isSearchLoading && (
              <div className="absolute right-3 top-1/2 -translate-y-1/2">
                <RefreshCcw className="w-3.5 h-3.5 animate-spin text-[#008080]" />
              </div>
            )}

            {/* Suggestions Dropdown */}
            {suggestions.length > 0 && (
              <div className="absolute z-[100] mt-2 w-full glass-card border-white/10 shadow-2xl rounded-lg overflow-hidden py-1 max-h-[300px] overflow-y-auto">
                {suggestions.map((drug) => (
                  <button
                    key={drug.id}
                    className="w-full text-left px-4 py-2.5 hover:bg-white/5 transition-colors group flex flex-col gap-0.5"
                    onClick={() => handleSelectDrug(drug.id, drug.name, drug.indication)}
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-data font-bold text-sm text-white group-hover:text-[#008080] transition-colors">{drug.name}</span>
                      {drug.indication && (
                        <span className="text-[10px] uppercase tracking-wider text-muted-foreground opacity-70">{drug.type || 'Therapy'}</span>
                      )}
                    </div>
                    <div className="text-xs text-muted-foreground truncate">{drug.indication || 'Therapeutic Area'}</div>
                  </button>
                ))}
              </div>
            )}

            {/* "Did you mean?" suggestion banner */}
            {didYouMean && (
              <div
                className="absolute z-[101] mt-1 w-full glass-card border-white/10 shadow-xl rounded-lg px-4 py-2.5 cursor-pointer hover:bg-white/5 transition-colors"
                style={{ top: suggestions.length > 0 ? `${suggestions.length * 44 + 16}px` : '100%' }}
                onClick={() => {
                  setDidYouMean(null);
                  handleSearch(didYouMean);
                }}
              >
                <span className="text-xs text-muted-foreground">Did you mean: </span>
                <span className="text-sm font-bold text-[#008080] hover:underline">{didYouMean}</span>
                <span className="text-xs text-muted-foreground"> ?</span>
              </div>
            )}
          </div>

          <Separator style={{ backgroundColor: borderColor, opacity: 0.5 }} />

          <div>
            <div className="flex items-center justify-between mb-2">
              <div className="text-xs uppercase tracking-widest text-muted-foreground">ASSET PROFILE</div>

              {/* Subtle Auto-Sync UI */}
              <div className="flex items-center gap-2 group relative">
                <span className="text-[10px] text-muted-foreground opacity-50 font-mono tracking-tighter hidden sm:inline-block">
                  {selectedDrug.last_updated ? `SYNC: ${new Date(selectedDrug.last_updated).toLocaleDateString()}` : 'LIVE'}
                </span>
                <button
                  onClick={handleForceRefresh}
                  disabled={isRefreshing}
                  className="p-1 rounded-full hover:bg-black/5 dark:hover:bg-white/10 transition-colors disabled:opacity-50"
                  title="Force Sync: Bypasses the 30-day cache to pull breaking clinical and pricing data directly from the web."
                >
                  <RefreshCcw className={`w-3.5 h-3.5 text-muted-foreground ${isRefreshing ? 'animate-spin text-[#008080]' : ''}`} />
                </button>
              </div>
            </div>

            <h2 className="text-3xl font-bold font-data mb-2" style={{ color: textColor }}>{selectedDrug.name}</h2>
            <div
              className="text-sm text-left flex items-center gap-1 group cursor-pointer hover:text-[#008080] transition-colors"
              style={{ color: mutedColor }}
              onClick={async () => {
                setPendingDrug({ id: selectedDrug.id, name: selectedDrug.name });
                if (!selectedDrug.indications_available || selectedDrug.indications_available.length === 0) {
                  setIsSearchLoading(true);
                  try {
                    const res = await axios.get(`${API}/drugs/${selectedDrug.id}/indications?name=${encodeURIComponent(selectedDrug.name)}`);
                    setAvailableIndications(res.data.indications || []);
                  } catch (err) {
                    console.error("Failed to fetch indications:", err);
                    setAvailableIndications([]);
                  } finally {
                    setIsSearchLoading(false);
                  }
                } else {
                  setAvailableIndications(selectedDrug.indications_available || []);
                }
                setShowIndicationModal(true);
              }}
            >
              <span>{selectedDrug.indication}</span>
              <ChevronDown className="w-3.5 h-3.5 opacity-0 group-hover:opacity-100 transition-all" />
            </div>
          </div>

          <Separator style={{ backgroundColor: borderColor }} />

          <div className="space-y-4">
            <div>
              <div className="text-xs uppercase tracking-widest text-muted-foreground mb-1">MECHANISM</div>
              <div className="text-sm" style={{ color: textColor }}>{selectedDrug.mechanism_of_action}</div>
            </div>

            {/* Regional Status - KEY NEW FEATURE */}
            {/* local_regulator is derived from selectedRegion to prevent stale-cache artefacts */}
            {(() => {
              const REGULATOR_LABELS = { IN: 'CDSCO', SG: 'HSA', AE: 'DOH' };
              const localRegulator = REGULATOR_LABELS[selectedRegion?.code] ||
                selectedDrug.regional_availability?.local_regulator;

              // Find indication-specific approval if available
              let approvalYear;
              if (selectedDrug.indication?.toLowerCase().includes('endometrial')) {
                approvalYear = '2022';
              } else if (selectedDrug.indications_available && Array.isArray(selectedDrug.indications_available)) {
                const indMatch = selectedDrug.indications_available.find(
                  ind => ind.indication?.toLowerCase() === selectedDrug.indication?.toLowerCase()
                );
                approvalYear = indMatch?.approval_year;
              }

              if (!approvalYear) {
                approvalYear = selectedDrug.regional_availability?.global_approval?.date || selectedDrug.launch_date;
              }

              return (
                <div>
                  <div className="text-xs uppercase tracking-widest text-muted-foreground mb-1">
                    INDICATION APPROVAL
                  </div>
                  <div className="font-data mb-4" style={{ color: textColor }}>
                    {selectedDrug.regional_availability?.global_approval?.agency} {approvalYear}
                  </div>
                  <div className="text-xs uppercase tracking-widest text-muted-foreground mb-1">
                    {selectedRegion.name.toUpperCase()} STATUS
                  </div>
                  <div className="flex flex-col gap-2">
                    <Badge
                      className={`w-fit ${(calculationResults?.regional_availability?.availability_color || selectedDrug.regional_availability?.availability_color) === 'green'
                        ? 'bg-[#10B981] text-white'
                        : (calculationResults?.regional_availability?.availability_color || selectedDrug.regional_availability?.availability_color) === 'yellow'
                          ? 'bg-[#F59E0B] text-black'
                          : (calculationResults?.regional_availability?.availability_color || selectedDrug.regional_availability?.availability_color) === 'red'
                            ? 'bg-[#E53E3E] text-white'
                            : 'bg-[#008080] text-white'
                        }`}
                      data-testid="regional-status-badge"
                    >
                      {calculationResults?.regional_availability?.availability_text || selectedDrug.regional_availability?.availability_text || selectedDrug.regulatory_status}
                    </Badge>
                    {selectedDrug.regional_availability?.local_approval_date && (
                      <div className="text-xs" style={{ color: mutedColor }}>
                        {localRegulator} Approved: {selectedDrug.regional_availability.local_approval_date}
                      </div>
                    )}
                    {selectedDrug.regional_availability?.notes && (
                      <div className="text-xs p-2 rounded-sm" style={{ backgroundColor: theme === 'dark' ? '#1A1A1A' : '#F5F5F5', color: mutedColor }}>
                        {selectedDrug.regional_availability.notes}
                      </div>
                    )}
                  </div>
                </div>
              );
            })()}

            {/* Effective Patient Cost - PRIMARY DISPLAY with Glass Effect */}
            {pricingModel && (
              <div className="tour-cost-metrics glass-card glass-card-hover p-4 rounded-sm relative overflow-hidden">
                <div className="glass-gradient absolute inset-0 pointer-events-none" />
                <div className="relative z-10">
                  <div className="text-xs uppercase tracking-widest text-muted-foreground mb-1">EFFECTIVE PATIENT COST</div>
                  <div className="text-3xl font-data font-bold text-[#10B981]">
                    {pricingModel.currency_symbol}{pricingModel.effective_monthly_cost?.toLocaleString()}
                    <span className="text-sm text-muted-foreground font-normal"> /cycle</span>
                  </div>
                  <div className="text-xs text-muted-foreground mt-1">
                    {selectedPayer?.toUpperCase() === 'OOP' || selectedPayer?.toLowerCase() === 'oop'
                      ? (pricingModel.pap_scheme_applied ? `After ${pricingModel.pap_scheme_applied}` : 'Full out-of-pocket cost')
                      : (selectedPayer?.toLowerCase().includes('insurance') || ['CORP', 'PRIVATE', 'MEDISAVE', 'DAMAN'].includes(selectedPayer?.toUpperCase()))
                        ? '20% Co-Pay (80% covered by insurer)'
                        : 'Zero cost to patient (Government scheme)'}
                  </div>
                  {pricingModel.is_price_estimated && (
                    <Badge variant="outline" className="text-xs mt-2 border-yellow-500 text-yellow-500">
                      PPP Estimated
                    </Badge>
                  )}
                </div>
              </div>
            )}

            {/* Government Burden - Show for CGHS/ECHS */}
            {pricingModel && (['cghs', 'echs', 'ayushman_bharat', 'govt'].includes(selectedPayer?.toLowerCase())) && pricingModel.annual_govt_impact > 0 && (
              <div className="p-3 rounded-sm border border-[#10B981]/30" style={{ backgroundColor: theme === 'dark' ? '#10B98110' : '#10B98108' }}>
                <div className="text-xs uppercase tracking-widest text-[#10B981] mb-1">GOVT / INSTITUTION BURDEN PER CYCLE</div>
                <div className="text-xl font-data font-bold" style={{ color: textColor }}>
                  {pricingModel.currency_symbol}{Math.round(pricingModel.annual_govt_impact / 12).toLocaleString()}
                </div>
                <div className="text-xs text-muted-foreground mt-1">
                  Annual: {pricingModel.currency_symbol}{pricingModel.annual_govt_impact?.toLocaleString()}
                </div>
              </div>
            )}

            {/* Insurer Burden - Show for Insurance */}
            {pricingModel && (selectedPayer?.toLowerCase().includes('insurance') || ['CORP', 'PRIVATE', 'MEDISAVE', 'DAMAN'].includes(selectedPayer?.toUpperCase())) && pricingModel.annual_insurer_impact > 0 && (
              <div className="p-3 rounded-sm border border-blue-500/30" style={{ backgroundColor: theme === 'dark' ? '#3B82F610' : '#3B82F608' }}>
                <div className="text-xs uppercase tracking-widest text-blue-500 mb-1">INSURER BURDEN PER CYCLE</div>
                <div className="text-xl font-data font-bold" style={{ color: textColor }}>
                  {pricingModel.currency_symbol}{Math.round(pricingModel.annual_insurer_impact / 12).toLocaleString()}
                </div>
                <div className="text-xs text-muted-foreground mt-1">
                  Annual: {pricingModel.currency_symbol}{pricingModel.annual_insurer_impact?.toLocaleString()}
                </div>
              </div>
            )}

            {/* List Price Reference */}
            {pricingModel && (
              <div className="text-xs" style={{ color: mutedColor }}>
                <span>List Price: </span>
                <span className="font-data">{pricingModel.currency_symbol}{pricingModel.list_price_per_period?.toLocaleString()}/cycle</span>
              </div>
            )}

            <Separator style={{ backgroundColor: borderColor }} />

            {/* Clinical Endpoints - CRITICAL DATA DISPLAY */}
            {calculation && calculation.commercial_brain && (
              <div className="tour-clinical-endpoints space-y-3" data-testid="clinical-endpoints-section">
                <div className="text-xs uppercase tracking-widest text-muted-foreground mb-2">RELEVANT ENDPOINTS</div>

                {/* Dynamic Endpoints from endpoints_summary */}
                {calculation.commercial_brain.endpoints_summary && calculation.commercial_brain.endpoints_summary.length > 0 ? (
                  <div className="space-y-2">
                    {calculation.commercial_brain.endpoints_summary.map((endpoint, idx) => {
                      // Endpoint labels are registry-driven; map to a generic glossary term.
                      const termKey = endpoint.is_primary
                        ? 'primaryEndpoint'
                        : ((endpoint.unit === 'HR' || /hazard|HR/i.test(endpoint.name)) ? 'hazardRatio' : null);
                      const unavailable = endpoint.available === false;

                      return (
                        <div
                          key={idx}
                          className={`flex justify-between items-center p-2 rounded-sm ${endpoint.is_primary ? 'glass-card p-3' : ''}`}
                          style={{ backgroundColor: endpoint.is_primary ? 'transparent' : (theme === 'dark' ? '#1A1A1A' : '#F5F5F5') }}
                        >
                          <div className="flex items-center gap-2">
                            {termKey ? (
                              <TermTooltip termKey={termKey} showIcon={false}>
                                <span className={`text-xs ${endpoint.is_primary ? 'font-medium' : 'text-muted-foreground'}`}>
                                  {endpoint.name}
                                </span>
                              </TermTooltip>
                            ) : (
                              <span className={`text-xs ${endpoint.is_primary ? 'font-medium' : 'text-muted-foreground'}`}>
                                {endpoint.name}
                              </span>
                            )}
                            {unavailable && (
                              <TermTooltip termKey="notAvailable" showIcon={false}>
                                <Badge variant="outline" className="text-xs border-amber-500 text-amber-500" data-testid={`${(endpoint.key || endpoint.name).toString().toLowerCase().replace(/\s/g, '-')}-unavailable-badge`}>
                                  No data
                                </Badge>
                              </TermTooltip>
                            )}
                          </div>
                          <div className={`font-data ${endpoint.is_primary ? 'text-lg font-bold' : ''}`}
                            style={{ color: unavailable ? '#F59E0B' : (endpoint.unit === 'HR' ? '#10B981' : textColor) }}
                          >
                            {endpoint.value}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  /* Fallback to old display if no endpoints_summary */
                  <>
                    {/* Primary endpoint (registry-driven) */}
                    <div className="glass-card p-3 rounded-sm">
                      <div className="flex justify-between items-start">
                        <div>
                          <TermTooltip termKey="primaryEndpoint">
                            <span className="text-xs text-muted-foreground">{getEfficacyLabel(selectedDrug, calculation.commercial_brain)}</span>
                          </TermTooltip>
                          <div className="text-xl font-data font-bold" style={{ color: calculation.commercial_brain.primary_endpoint_value == null ? '#F59E0B' : textColor }}>
                            {calculation.commercial_brain.primary_endpoint_value != null
                              ? `${calculation.commercial_brain.primary_endpoint_value} ${calculation.commercial_brain.primary_endpoint_unit || ''}`.trim()
                              : 'Data unavailable'}
                          </div>
                        </div>
                        {calculation.commercial_brain.primary_endpoint_value == null && (
                          <TermTooltip termKey="notAvailable" showIcon={false}>
                            <Badge variant="outline" className="text-xs border-amber-500 text-amber-500" data-testid="primary-endpoint-unavailable-badge">
                              Manual input required
                            </Badge>
                          </TermTooltip>
                        )}
                      </div>
                      {calculation.commercial_brain.primary_endpoint_method && (
                        <div className="text-xs text-muted-foreground mt-1">
                          Source: {calculation.commercial_brain.primary_endpoint_method}
                        </div>
                      )}
                    </div>

                    {/* 07 – ICER (conditional) */}
                    {(() => {
                      const activeComp = customCompetitors?.length > 0
                        ? { name: customCompetitors[0].name, price: customCompetitors[0].baseCost }
                        : { name: selectedDrug.competitor_name, price: selectedDrug.competitor_price_inr };

                      if (activeComp.name && activeComp.price && calculation.commercial_brain?.event_probability != null) {
                        return (
                          <div className="heor-point heor-point--icer">
                            <div className="heor-point-icon">📐</div>
                            <div className="heor-point-content">
                              <div className="heor-point-header">
                                <span className="heor-point-num">07</span>
                                HEAD-TO-HEAD ECONOMIC COMPARISON (ICER)
                              </div>
                              <p className="heor-point-text">
                                Incremental cost vs <strong>{activeComp.name}</strong>:{' '}
                                <span className="heor-metric-teal">
                                  {selectedRegion.currency_symbol}{Math.abs(calculation.drug_cost - activeComp.price).toLocaleString()}
                                </span>.{' '}
                                Expressed as incremental cost per unit of downstream event risk avoided:{' '}
                                <span className="heor-metric-amber">
                                  {selectedRegion.currency_symbol}{(
                                    Math.abs(calculation.drug_cost - activeComp.price) /
                                    Math.max(1 - calculation.commercial_brain.event_probability, 0.01)
                                  ).toLocaleString(undefined, { maximumFractionDigits: 0 })}
                                </span> per unit risk avoided.{' '}
                                {calculation.drug_cost < (activeComp.price + (calculation.breakdown?.adverse_event_cost || 0))
                                  ? <><span className="heor-badge heor-badge--green">DOMINANT STRATEGY</span> — lower total cost, superior tolerability profile.</>
                                  : <>Enter <strong>Deal Architect</strong> to model outcome-based contracts that cap net cost at payer-acceptable ICER thresholds.</>}
                              </p>
                            </div>
                          </div>
                        );
                      } else {
                        return (
                          <div className="heor-point heor-point--muted">
                            <div className="heor-point-icon">📐</div>
                            <div className="heor-point-content">
                              <div className="heor-point-header">
                                <span className="heor-point-num">07</span>
                                HEAD-TO-HEAD ECONOMIC COMPARISON (ICER)
                              </div>
                              <p className="heor-point-text">
                                Add a comparator drug via the War Room's <strong>Competitive Thunderdome</strong> module to activate Incremental Cost-Effectiveness Ratio modelling against {selectedDrug.name}.
                              </p>
                            </div>
                          </div>
                        );
                      }
                    })()}       {/* Hazard Ratio */}
                    {calculation.commercial_brain.hazard_ratio && (
                      <div className="flex justify-between items-center p-2 rounded-sm" style={{ backgroundColor: theme === 'dark' ? '#1A1A1A' : '#F5F5F5' }}>
                        <div className="text-xs text-muted-foreground">Hazard Ratio (HR)</div>
                        <div className="font-data font-bold text-[#10B981]" data-testid="hazard-ratio-value">
                          {calculation.commercial_brain.hazard_ratio.toFixed(2)}
                        </div>
                      </div>
                    )}

                    {/* Secondary endpoint if available */}
                    {calculation.commercial_brain.secondary_endpoints?.[0]?.value != null && (
                      <div className="flex justify-between items-center p-2 rounded-sm" style={{ backgroundColor: theme === 'dark' ? '#1A1A1A' : '#F5F5F5' }}>
                        <div className="text-xs text-muted-foreground">{getSecondaryLabel(selectedDrug, calculation.commercial_brain)}</div>
                        <div className="font-data" style={{ color: textColor }}>
                          {calculation.commercial_brain.secondary_endpoints[0].value} {calculation.commercial_brain.secondary_endpoints[0].unit || ''}
                        </div>
                      </div>
                    )}
                  </>
                )}

                {/* Competitor serious AE rate */}
                <div className="flex justify-between items-center p-2 rounded-sm" style={{ backgroundColor: theme === 'dark' ? '#1A1A1A' : '#F5F5F5' }}>
                  <div className="flex items-center gap-2">
                    <TermTooltip termKey="safetyRate" showIcon={false}>
                      <span className="text-xs text-muted-foreground">Competitor Serious AE Rate</span>
                    </TermTooltip>
                    {calculation.commercial_brain.competitor_severe_ae_rate == null && (
                      <Badge variant="outline" className="text-xs border-amber-500/50 text-amber-500">No data</Badge>
                    )}
                  </div>
                  <div className="font-data text-[#F87171]" data-testid="ae-rate-value">
                    {calculation.commercial_brain.competitor_severe_ae_rate != null
                      ? `${(calculation.commercial_brain.competitor_severe_ae_rate * 100).toFixed(0)}%`
                      : 'Data unavailable'}
                  </div>
                </div>

                {/* Drug serious AE rate */}
                <div className="flex justify-between items-center p-2 rounded-sm" style={{ backgroundColor: theme === 'dark' ? '#1A1A1A' : '#F5F5F5' }}>
                  <div className="flex items-center gap-2">
                    <TermTooltip termKey="safetyRate" showIcon={false}>
                      <span className="text-xs text-muted-foreground">Drug Serious AE Rate</span>
                    </TermTooltip>
                    {calculation.commercial_brain.drug_severe_ae_rate == null && (
                      <Badge variant="outline" className="text-xs border-amber-500/50 text-amber-500">No data</Badge>
                    )}
                  </div>
                  <div className="font-data text-[#F87171]" data-testid="drug-ae-rate-value">
                    {calculation.commercial_brain.drug_severe_ae_rate != null
                      ? `${(calculation.commercial_brain.drug_severe_ae_rate * 100).toFixed(0)}%`
                      : 'Data unavailable'}
                  </div>
                </div>
              </div>
            )}

            {/* Logistical Profiles Snippet */}
            <LogisticalBurdenSnippet
              assetName={selectedDrug.name}
              competitorName={selectedDrug.competitor_name}
              logisticalData={calculation?.commercial_brain?.logistics}
            />
          </div>
        </div>

        {selectedDrug.global_price_inr < 50000 ? (
          <div className="lg:col-span-2 flex flex-col h-full overflow-hidden" data-testid="standard-therapy-dashboard">
            <div className="p-6 border-b flex items-center justify-between" style={{ borderColor }}>
              <div>
                <div className="text-xs uppercase tracking-widest text-muted-foreground mb-1">STANDARD THERAPY OVERVIEW</div>
                <h3 className="text-xl font-data font-bold tracking-tight" style={{ color: textColor }}>
                  Affordability & Formulation Profile
                </h3>
              </div>
              <div className="text-xs text-teal-600 dark:text-teal-400 bg-teal-500/10 border border-teal-500/20 rounded px-2.5 py-1 uppercase tracking-wider font-semibold">
                Low-Cost Maintenance
              </div>
            </div>

            <div className="flex-1 overflow-y-auto p-6 space-y-6 custom-scrollbar">
              {/* Row 1: Key Metrics */}
              <div className="grid grid-cols-3 gap-6">
                <Card className="glass-card">
                  <CardContent className="p-4 flex flex-col justify-center">
                    <span className="text-xs text-muted-foreground mb-1">Cost per Treatment Period</span>
                    <span className="text-3xl font-data font-black text-white">
                      {selectedDrug.global_price_inr
                        ? `${selectedRegion?.currency_symbol}${selectedDrug.global_price_inr.toLocaleString()}`
                        : <span className="text-lg text-amber-500">Data unavailable</span>}
                    </span>
                  </CardContent>
                </Card>

                <Card className="glass-card">
                  <CardContent className="p-4 flex flex-col justify-center">
                    <span className="text-xs text-muted-foreground mb-1">
                      {getEfficacyLabel(selectedDrug, calculation?.commercial_brain)}
                    </span>
                    {selectedDrug.primary_endpoint_value != null ? (
                      <span className="text-3xl font-data font-black text-[#008080]">
                        {selectedDrug.primary_endpoint_value}{' '}
                        <span className="text-sm font-normal text-muted-foreground">
                          {selectedDrug.primary_endpoint_unit || ''}
                        </span>
                      </span>
                    ) : (
                      <span className="text-lg font-data font-bold text-amber-500">Data unavailable</span>
                    )}
                  </CardContent>
                </Card>

                <Card className="glass-card">
                  <CardContent className="p-4 flex flex-col justify-center">
                    <span className="text-xs text-muted-foreground mb-1">Safety Profile</span>
                    {selectedDrug.drug_severe_ae_rate != null ? (
                      <span className="text-xl font-data font-bold text-teal-500 uppercase tracking-wide mt-1">
                        {(selectedDrug.drug_severe_ae_rate * 100).toFixed(0)}% Serious AEs
                      </span>
                    ) : (
                      <span className="text-lg font-data font-bold text-amber-500 mt-1">Data unavailable</span>
                    )}
                  </CardContent>
                </Card>
              </div>

              {/* Row 2: Two Side-by-Side Detail Panels */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Panel 1: Formulation & Brand Directory */}
                <Card className="glass-card">
                  <CardHeader className="pb-2">
                    <CardTitle className="text-xs font-data text-[#008080] uppercase tracking-widest">
                      Formulation & Brand Directory
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <div className="text-[10px] uppercase tracking-wider text-muted-foreground">Route / Formulation</div>
                        <div className="text-sm font-bold text-white mt-0.5">{selectedDrug.route_form || 'Oral'}</div>
                      </div>
                      <div>
                        <div className="text-[10px] uppercase tracking-wider text-muted-foreground">Common Strengths</div>
                        <div className="text-sm font-bold text-white mt-0.5">{selectedDrug.common_strengths || 'Standard'}</div>
                      </div>
                    </div>
                    <div>
                      <div className="text-[10px] uppercase tracking-wider text-muted-foreground mb-1">Key Indian Brands</div>
                      <div className="text-sm font-medium leading-relaxed" style={{ color: textColor }}>
                        {selectedDrug.key_brands || 'Generics widely available'}
                      </div>
                    </div>
                    <div>
                      <div className="text-[10px] uppercase tracking-wider text-muted-foreground mb-1">Representative Manufacturers</div>
                      <div className="text-sm text-muted-foreground leading-relaxed">
                        {selectedDrug.manufacturers || 'Various generic manufacturers'}
                      </div>
                    </div>
                  </CardContent>
                </Card>

                {/* Panel 2: Clinical Evidence Summary */}
                <Card className="glass-card">
                  <CardHeader className="pb-2">
                    <CardTitle className="text-xs font-data text-[#008080] uppercase tracking-widest">
                      Clinical Value & Evidence
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <div className="text-[10px] uppercase tracking-wider text-muted-foreground">Therapy Class</div>
                        <div className="text-sm font-bold text-[#008080] mt-0.5">{selectedDrug.mechanism_of_action}</div>
                      </div>
                      <div>
                        <div className="text-[10px] uppercase tracking-wider text-muted-foreground">Efficacy Metric</div>
                        <div className="text-sm font-bold text-white mt-0.5">
                          {getEfficacyLabel(selectedDrug, calculation?.commercial_brain)}
                        </div>
                      </div>
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <div className="text-[10px] uppercase tracking-wider text-muted-foreground">
                          {getEndpointsForDrug(selectedDrug)?.hazardRatioLabel || 'Hazard Ratio'}
                        </div>
                        <div className="text-sm font-bold text-white mt-0.5">
                          {selectedDrug.hazard_ratio ?? <span className="text-amber-500">Data unavailable</span>}
                        </div>
                      </div>
                      <div>
                        <div className="text-[10px] uppercase tracking-wider text-muted-foreground">
                          {getEndpointsForDrug(selectedDrug)?.secondaryEndpoints?.[0]?.label || 'Secondary Endpoint'}
                        </div>
                        <div className="text-sm font-bold text-white mt-0.5">
                          {selectedDrug.secondary_endpoints?.[0]?.value ?? <span className="text-amber-500">Data unavailable</span>}
                        </div>
                      </div>
                    </div>
                    <div>
                      <div className="text-[10px] uppercase tracking-wider text-muted-foreground mb-1">Trial / Data Source</div>
                      <div className="text-xs italic text-muted-foreground leading-relaxed">
                        {selectedDrug.primary_endpoint_method || 'Source not resolved'}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </div>

              {/* Threat Feed (re-rendered inside combined view for maintenance drugs) */}
              <div>
                <div className="text-xs uppercase tracking-widest text-muted-foreground mb-3 flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 text-[#E53E3E]" />
                  Active Market Threats
                </div>
                {news.summary && (
                  <div className="mb-4 p-3 rounded-sm border border-red-500/20 bg-red-500/5">
                    <div className="text-[10px] uppercase tracking-tighter text-red-400 mb-1 font-mono">THREAT LANDSCAPE SUMMARY</div>
                    <p className="text-xs leading-relaxed italic" style={{ color: textColor }}>"{news.summary}"</p>
                  </div>
                )}
                {news.sources && news.sources.length > 0 ? (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-h-[250px] overflow-y-auto pr-2 custom-scrollbar">
                    {news.sources.slice(0, 4).map((item, idx) => (
                      <Card key={idx} className="glass-card glass-card-hover border-white/5">
                        <CardContent className="p-3">
                          <div className="flex items-start justify-between gap-2 mb-1">
                            <Badge variant="outline" className="text-[9px] h-4 uppercase border-[#262626] text-muted-foreground">
                              {item.category || 'Threat'}
                            </Badge>
                            <span className="text-[10px] text-muted-foreground font-mono opacity-50">{item.source}</span>
                          </div>
                          <div className="text-sm font-semibold leading-snug" style={{ color: textColor }}>
                            {item.source_url ? (
                              <a href={item.source_url} target="_blank" rel="noopener noreferrer" className="hover:text-[#008080] hover:underline transition-colors flex items-center gap-1">
                                {item.title}
                                <ArrowRight className="w-3 h-3 opacity-50" />
                              </a>
                            ) : (
                              item.title
                            )}
                          </div>
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                ) : (
                  <Card className="war-room-surface">
                    <CardContent className="p-4 text-center">
                      <ShieldCheck className="w-8 h-8 mx-auto mb-2 text-[#008080]" />
                      <div className="text-sm font-semibold" style={{ color: textColor }}>No Active Market Threats Detected</div>
                    </CardContent>
                  </Card>
                )}
              </div>
            </div>
          </div>
        ) : (
          <>
            {/* Column 2: Radar + Pricing Visualization */}
            <div className="border-r p-6 space-y-6 overflow-y-auto" style={{ borderColor }} data-testid="market-radar-section">
              {/* Data quality / issues — surfaced before any numbers are read */}
              <DataQualityPanel
                dataQuality={calculation?.data_quality}
                textSecondary="text-muted-foreground"
                borderColor={borderColor}
              />

              {/* Site-of-care coverage & price matrix (the Brain) */}
              <CoverageMatrix
                applicability={calculation?.applicability}
                currencySymbol={selectedRegion?.currency_symbol}
                theme={theme}
                textPrimary=""
                textSecondary="text-muted-foreground"
                borderColor={borderColor}
              />

              {/* Period cash flow — only when the treatment model has recurring periods */}
              {applicabilityModules.period_cash_flow !== false && (
                <>
                  <div>
                    <div className="text-xs uppercase tracking-widest text-muted-foreground mb-2">PATIENT CASH FLOW BY TREATMENT PERIOD</div>
                  </div>

                  <PatientCashFlow
                    pricingModel={pricingModel}
                    theme={theme}
                    currencySymbol={selectedRegion?.currency_symbol}
                  />
                </>
              )}

              {applicabilityModules.period_cash_flow === false && (
                <Card className="glass-card" style={{ borderColor }} data-testid="cashflow-not-applicable">
                  <CardContent className="py-4">
                    <div className="text-xs uppercase tracking-widest text-muted-foreground mb-1">PATIENT CASH FLOW</div>
                    <p className="text-sm italic text-muted-foreground">
                      Not applicable — this is a one-time {calculation?.applicability?.route === 'iv_bolus' ? 'intravenous ' : ''}administration
                      given in hospital, billed within the admission rather than as recurring treatment periods.
                    </p>
                  </CardContent>
                </Card>
              )}

              {/* Deal Architect Advice — only when financial assistance is actually relevant */}
              {pricingModel && applicabilityModules.pap_deal_architect !== false && (
                <Card className="tour-deal-architect glass-card border-[#008080]/30 glow-teal overflow-hidden" data-testid="deal-architect-card">
                  <div className="glass-gradient absolute inset-0 pointer-events-none" />
                  <CardHeader className="pb-2 relative z-10">
                    <CardTitle className="text-xs font-data flex items-center gap-2 text-[#008080]">
                      <FileText className="w-4 h-4" />
                      DEAL ARCHITECT
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="pt-0 relative z-10">
                    {pricingModel.deal_architect_advice ? (
                      <p className="text-sm font-medium" style={{ color: textColor }}>
                        {pricingModel.deal_architect_advice}
                      </p>
                    ) : (
                      <p className="text-sm italic text-muted-foreground">
                        PAP schemes are generally not applicable for this payer segment. Switch to Out-of-Pocket to model affordability programs.
                      </p>
                    )}
                  </CardContent>
                </Card>
              )}

              {/* Threat Feed */}
              <div>
                <div className="text-xs uppercase tracking-widest text-muted-foreground mb-3 flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 text-[#E53E3E]" />
                  THREAT FEED
                </div>
                {news.summary && (
                  <div className="mb-4 p-3 rounded-sm border border-red-500/20 bg-red-500/5">
                    <div className="text-[10px] uppercase tracking-tighter text-red-400 mb-1 font-mono">THREAT LANDSCAPE SUMMARY</div>
                    <p className="text-xs leading-relaxed italic" style={{ color: textColor }}>"{news.summary}"</p>
                  </div>
                )}
                {news.sources && news.sources.length > 0 ? (
                  <div className="space-y-3 max-h-[250px] overflow-y-auto pr-2 custom-scrollbar">
                    {news.sources.slice(0, 5).map((item, idx) => (
                      <Card key={idx} className="glass-card glass-card-hover border-white/5" data-testid={`threat-item-${idx}`}>
                        <CardContent className="p-3">
                          <div className="flex items-start justify-between gap-2 mb-1">
                            <Badge
                              variant="outline"
                              className={`text-[9px] h-4 uppercase ${item.category === 'Competitive' ? 'border-orange-500/50 text-orange-400' :
                                item.category === 'Regulatory' ? 'border-red-500/50 text-red-400' :
                                  item.category === 'Legal' ? 'border-purple-500/50 text-purple-400' :
                                    item.category === 'Pricing' ? 'border-yellow-500/50 text-yellow-400' :
                                      'border-[#262626] text-muted-foreground'
                                }`}
                            >
                              {item.category || 'Threat'}
                            </Badge>
                            <span className="text-[10px] text-muted-foreground font-mono opacity-50">{item.source}</span>
                          </div>
                          <div className="text-sm font-semibold leading-snug" style={{ color: textColor }}>
                            {item.source_url ? (
                              <a href={item.source_url} target="_blank" rel="noopener noreferrer" className="hover:text-[#008080] hover:underline transition-colors flex items-center gap-1">
                                {item.title}
                                <ArrowRight className="w-3 h-3 opacity-50" />
                              </a>
                            ) : (
                              item.title
                            )}
                          </div>
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                ) : (
                  <Card className="war-room-surface" data-testid="no-threats-card">
                    <CardContent className="p-4 text-center">
                      <ShieldCheck className="w-8 h-8 mx-auto mb-2 text-[#008080]" />
                      <div className="text-sm font-semibold" style={{ color: textColor }}>No Active Threats</div>
                    </CardContent>
                  </Card>
                )}
              </div>
            </div>

            {/* Column 3: Liability Analysis */}
            <div className="p-6 space-y-6 overflow-y-auto" data-testid="liability-preview-section">
              <div>
                <div className="text-xs uppercase tracking-widest text-muted-foreground mb-2">LIABILITY ANALYSIS</div>
                <h3 className="text-xl font-data mb-1" style={{ color: textColor }}>Projected Liability Exposure</h3>
                <p className="text-sm text-muted-foreground">Analysis of unfunded downstream risk associated with Standard of Care</p>
              </div>

              {calculation && (
                selectedDrug.global_price_inr < 2000 ? (
                  <div className="flex flex-col items-center justify-center p-8 text-center h-[250px] border border-dashed rounded-sm" style={{ borderColor: borderColor }}>
                    <div className="p-3 rounded-full bg-teal-500/10 text-teal-600 dark:text-teal-400 mb-3">
                      <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                    </div>
                    <h4 className="text-sm font-semibold mb-1" style={{ color: textColor }}>Liability Analysis Bypassed</h4>
                    <p className="text-xs text-muted-foreground max-w-[250px]">
                      Downstream liability modeling is bypassed for standard low-cost maintenance therapies (under ₹2,000/cycle).
                    </p>
                  </div>
                ) : (
                  <div style={{ height: '250px' }}>
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={[
                        { name: selectedDrug.name, value: calculation.drug_cost, fill: '#008080' },
                        { name: 'Unfunded Exposure', value: calculation.total_liability, fill: '#E53E3E' }
                      ]}>
                        <CartesianGrid strokeDasharray="3 3" stroke={borderColor} opacity={0.3} />
                        <XAxis dataKey="name" stroke={mutedColor} tick={{ fill: mutedColor, fontSize: 12 }} />
                        <YAxis stroke={mutedColor} tick={{ fill: mutedColor, fontSize: 12 }} />
                        <Tooltip
                          contentStyle={{ 
                            background: theme === 'dark' ? 'rgba(18, 18, 18, 0.9)' : 'rgba(255, 255, 255, 0.95)', 
                            backdropFilter: 'blur(8px)', 
                            border: theme === 'dark' ? '1px solid rgba(255,255,255,0.1)' : '1px solid rgba(0,0,0,0.1)', 
                            borderRadius: '8px'
                          }}
                          itemStyle={{ color: theme === 'dark' ? '#ffffff' : '#111827' }}
                          labelStyle={{ color: theme === 'dark' ? '#9ca3af' : '#4b5563' }}
                          formatter={(value) => [`${selectedRegion.currency_symbol}${value.toLocaleString()}`, '']}
                        />
                        <Bar dataKey="value" radius={[4, 4, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                )
              )}

              {calculation && (
                <Card className="glass-card overflow-hidden">
                  <CardContent className="p-4 space-y-3 relative">
                    <div className="glass-gradient absolute inset-0 pointer-events-none" />
                    <div className="relative z-10 space-y-3">
                      <Separator style={{ backgroundColor: borderColor }} />
                      <div className="flex justify-between items-center">
                        {selectedDrug.global_price_inr >= 2000 ? (
                          <>
                            <TermTooltip termKey="riskWeightedCostIndex">
                              <span className="text-xs text-muted-foreground">Risk-Weighted Cost Index</span>
                            </TermTooltip>
                            <span className="font-data text-[#F59E0B] font-bold">
                              {calculation.drug_cost > 0 ? (calculation.total_liability / calculation.drug_cost).toFixed(2) : 0}x
                            </span>
                          </>
                        ) : (
                          <>
                            <span className="text-xs text-muted-foreground">Risk Profile</span>
                            <span className="font-data text-teal-600 dark:text-teal-400 font-bold text-xs px-2 py-0.5 rounded-sm bg-teal-500/10 uppercase tracking-wider">
                              Standard Maintenance (Low Risk)
                            </span>
                          </>
                        )}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              )}

              <Button
                data-testid="enter-war-room-btn"
                onClick={() => navigate('/war-room')}
                className="tour-war-room-btn w-full glass-button text-white font-data py-6 text-lg rounded-sm transition-all hover:shadow-[0_0_30px_rgba(0,128,128,0.5)]"
              >
                ENTER WAR ROOM
                <ArrowRight className="ml-2 w-5 h-5" />
              </Button>

              <div className="text-xs text-center text-muted-foreground">
                <FileText className="w-4 h-4 inline mr-1" />
                Access deep-dive modules for negotiation strategy
              </div>
            </div>
          </>
        )}

      </div> {/* End of Grid */}

      {/* ── Intelligence Report Canvas ── */}
      {showIntelligenceReport && (
        <IntelligenceReport
          onClose={() => setShowIntelligenceReport(false)}
          selectedDrug={selectedDrug}
          selectedRegion={selectedRegion}
          calculationResults={calculation}
          pricingModel={pricingModel}
        />
      )}

      {/* ── Indication Selection Modal ── */}
      <IndicationSelectDialog
        open={showIndicationModal}
        onOpenChange={(open) => {
          setShowIndicationModal(open);
          if (!open) {
            setPendingDrug(null);
            setAvailableIndications([]);
          }
        }}
        drugName={pendingDrug?.name || selectedDrug?.name || ''}
        indications={availableIndications.length > 0 ? availableIndications : (selectedDrug?.indications_available || [])}
        onSelectIndication={handleIndicationSelect}
        isLoading={isSearchLoading}
      />

      {/* Analysis Loading Overlay */}
      <AnalysisLoadingOverlay
        isVisible={isSearchLoading}
        drugName={loadingDrugName}
      />

      {/* Driver.js injects itself into the DOM automatically */}
    </div>
  );
}


