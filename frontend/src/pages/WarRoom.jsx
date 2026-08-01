/* eslint-disable react-hooks/exhaustive-deps */
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Download, BarChart3, DollarSign, FileText, Users, Building2, ShieldCheck, AlertTriangle, TrendingDown, Plus, X, Search, Beaker, Home, Loader2 } from 'lucide-react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Switch } from '../components/ui/switch';
import { Separator } from '../components/ui/separator';
import { Slider } from '../components/ui/slider';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Badge } from '../components/ui/badge';
import { BarChart, Bar, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend, ComposedChart, Line, ReferenceLine, Cell } from 'recharts';
import axios from 'axios';
import { useApp } from '../context/AppContext';
import { RegionSwitcher } from '../components/RegionSwitcher';
import { ThemeSwitcher } from '../components/ThemeSwitcher';
import { InfoTooltip } from '../components/InfoTooltip';
import { AssumptionsTable } from '../components/AssumptionsTable';
import { TPPBenchmarker } from '../components/TPPBenchmarker';
import { StrategicBrief } from '../components/StrategicBrief';
import { ValueBridge } from '../components/ValueBridge';
import { LogisticalBurdenCard } from '../components/LogisticalBurdenCard';
import { toast } from 'sonner';
import { formatLargeCurrency } from '../utils/formatters';
import { driver } from 'driver.js';
import 'driver.js/dist/driver.css';
import { HelpCircle } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || '';
const API = (BACKEND_URL && BACKEND_URL.startsWith('http')) ? `${BACKEND_URL}/api` : '/api';

export default function WarRoom() {
  const { selectedDrug, selectedRegion, calculationResults, theme, customCompetitors, setCustomCompetitors, setWarRoomSnapshot, hasSeenTour, setHasSeenTour, runTourPhaseC, setRunTourPhaseC } = useApp();
  const navigate = useNavigate();

  // Module B: Deal Architect State
  const [targetROI, setTargetROI] = useState(3.0);
  const [patientWallet, setPatientWallet] = useState(50000);
  const [papRecommendation, setPapRecommendation] = useState(null);

  // Dynamic Pricing Engine State
  const [payerSegments, setPayerSegments] = useState([]);
  const [selectedPayer, setSelectedPayer] = useState('oop');
  const [pricingModel, setPricingModel] = useState(null);

  // Module A: Competitive Thunderdome State
  const [showAdverseEventCost, setShowAdverseEventCost] = useState(true);

  // Custom Competitors State (up to 5) - managed globally via AppContext
  const [competitorSearch, setCompetitorSearch] = useState('');
  const [competitorSuggestions, setCompetitorSuggestions] = useState([]);
  const [isLoadingCompetitor, setIsLoadingCompetitor] = useState(false);
  const MAX_COMPETITORS = 5;

  // PDF Generation
  const [isGeneratingPDF, setIsGeneratingPDF] = useState(false);

  // Regional HEOR data — real ecosystem costs per region
  const [heorData, setHeorData] = useState(null);
  const [isHeorLoading, setIsHeorLoading] = useState(false);

  // Discontinuation Cliff Simulator State
  const [cliffSimEnabled, setCliffSimEnabled] = useState(false);
  const [fundedPeriods, setFundedPeriods] = useState([6]);

  // Active Tab State
  const [activeTab, setActiveTab] = useState('thunderdome');

  // The Brain: which modules apply to this drug + indication.
  // Defaults to all-on so the UI degrades gracefully without a profile.
  const applicabilityModules = calculationResults?.applicability?.modules || {};

  // If the active tab has been hidden by the applicability rules, fall back.
  useEffect(() => {
    if (activeTab === 'architect' && applicabilityModules.pap_deal_architect === false) setActiveTab('thunderdome');
    if (activeTab === 'cliff' && applicabilityModules.adherence === false) setActiveTab('thunderdome');
  }, [activeTab, applicabilityModules.pap_deal_architect, applicabilityModules.adherence]);

  // Auto-start Phase C Tour if the user hasn't seen it
  useEffect(() => {
    if (!hasSeenTour && !runTourPhaseC && calculationResults) {
      setTimeout(() => setRunTourPhaseC(true), 1000);
    }
  }, [hasSeenTour, runTourPhaseC, calculationResults, setRunTourPhaseC]);

  useEffect(() => {
    if (runTourPhaseC) {
      const driverObj = driver({
        showProgress: false,
        popoverClass: theme === 'dark' ? 'driver-popover-dark' : 'driver-popover-light',
        steps: [
          {
            element: '.tour-war-room-header',
            popover: {
              title: 'Welcome to the War Room',
              description: 'This is your tactical execution interface for high-stakes negotiations and simulations.',
              side: 'bottom',
              align: 'start'
            }
          },
          {
            element: '.tour-war-room-tabs',
            popover: {
              title: 'Combat Modules',
              description: 'Switch between the Thunderdome, Deal Architect, and Patient Bridge to access deep-dive analysis.',
              side: 'bottom',
              align: 'center'
            }
          },
          {
            element: '.tour-strategic-brief',
            popover: {
              title: 'Strategic Brief (AI Sync)',
              description: 'Get real-time market intelligence summaries synthesized from global news and regulatory filings.',
              side: 'bottom',
              align: 'center'
            }
          },
          {
            element: '.tour-competitive-thunderdome',
            popover: {
              title: 'Competitive Thunderdome',
              description: 'Model head-to-head scenarios by adding competitors and factoring in hidden adverse-event management costs.',
              side: 'top',
              align: 'center'
            }
          },
          {
            element: '.tour-generate-dossier',
            popover: {
              title: 'Global Value Dossier',
              description: 'Export all simulations and tactical findings into a boardroom-ready PDF dossier.',
              side: 'left',
              align: 'center'
            }
          }
        ],
        onDestroyStarted: () => {
          if (!driverObj.hasNextStep() || window.confirm("Finish the tour?")) {
            driverObj.destroy();
            setRunTourPhaseC(false);
            setHasSeenTour(true);
          }
        },
      });
      driverObj.drive();
    }
  }, [runTourPhaseC, setRunTourPhaseC, setHasSeenTour, theme]);

  useEffect(() => {
    // If the data is simply loading in the background, do not immediately kick them out. 
    // Wait for the context to resolve.

    // Fetch payer segments
    const fetchSegments = async () => {
      try {
        const response = await axios.get(`${API}/regions/${selectedRegion.code}/payer-segments`);
        setPayerSegments(response.data.segments || []);
      } catch (error) {
        console.error('Error fetching payer segments:', error);
      }
    };

    fetchSegments();
  }, [selectedDrug, calculationResults, navigate, selectedRegion]);

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

  // Clear stale PAP result when region changes (prevents old AED result showing for India)
  useEffect(() => {
    setPapRecommendation(null);
  }, [selectedRegion?.code]);

  // Fetch real regional HEOR costs whenever region changes
  useEffect(() => {
    if (!selectedDrug || !selectedRegion?.code) return;
    setIsHeorLoading(true);
    setHeorData(null);
    axios.get(
      `${API}/heor/regional-data?drug_name=${encodeURIComponent(selectedDrug.name)}&region_code=${selectedRegion.code}&indication=${encodeURIComponent(selectedDrug.indication || '')}`
    )
      .then(res => { setHeorData(res.data); setWarRoomSnapshot(prev => ({ ...prev, heor: res.data })); })
      .catch(() => setHeorData(null))
      .finally(() => setIsHeorLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedRegion?.code, selectedDrug?.name]);

  // Re-price custom competitors when region changes
  useEffect(() => {
    if (!selectedRegion?.code || customCompetitors.length === 0) return;
    const currentIndication = selectedDrug?.indication || '';
    customCompetitors.forEach(async (comp) => {
      try {
        const res = await axios.get(
          `${API}/competitor/analyze?competitor_name=${encodeURIComponent(comp.name)}&region_code=${selectedRegion.code}&indication=${encodeURIComponent(currentIndication)}`
        );
        setCustomCompetitors(prev => prev.map(c =>
          c.id === comp.id
            ? { ...c, baseCost: res.data.base_cost || c.baseCost, aeMgmtCost: res.data.ae_mgmt_cost || c.aeMgmtCost, isEstimated: res.data.is_estimated ?? c.isEstimated }
            : c
        ));
      } catch { /* keep existing values on failure */ }
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedRegion?.code]);

  // Search for competitors
  // Search for competitors - filters by current indication context
  const handleCompetitorSearch = async (value) => {
    setCompetitorSearch(value);
    if (value.length > 1) {
      try {
        // Pass indication to search for context-aware filtering
        const currentIndication = selectedDrug.indication || '';
        const response = await axios.get(`${API}/drugs/search?q=${value}&indication=${encodeURIComponent(currentIndication)}`);
        // Filter out already added competitors and the selected drug
        const filtered = response.data
          .filter(drug =>
            drug.name.toLowerCase() !== selectedDrug.name.toLowerCase() &&
            !customCompetitors.some(c => c.name.toLowerCase() === drug.name.toLowerCase())
          )
          .map(drug => ({
            ...drug,
            // Override indication display to match current context
            displayIndication: currentIndication || drug.indication
          }));
        setCompetitorSuggestions(filtered);
      } catch (error) {
        console.error('Competitor search error:', error);
      }
    } else {
      setCompetitorSuggestions([]);
    }
  };

  // Add a custom competitor
  const addCompetitor = async (drug) => {
    if (customCompetitors.length >= MAX_COMPETITORS) {
      toast.error(`Maximum ${MAX_COMPETITORS} competitors allowed`);
      return;
    }

    setIsLoadingCompetitor(true);
    setCompetitorSuggestions([]);
    setCompetitorSearch('');

    try {
      // Fetch competitor data (pricing and safety) with indication context
      const currentIndication = selectedDrug.indication || '';
      const response = await axios.get(
        `${API}/competitor/analyze?competitor_name=${encodeURIComponent(drug.name)}&region_code=${selectedRegion.code}&indication=${encodeURIComponent(currentIndication)}`
      );

      // Determine if off-label: the drug has a known indication that isn't the one we are researching
      const drugIndicationRaw = (drug.indication || '').toLowerCase();
      const currentIndicationRaw = currentIndication.toLowerCase();
      let isOffLabel = false;
      if (drugIndicationRaw && currentIndicationRaw && !drugIndicationRaw.includes(currentIndicationRaw) && !currentIndicationRaw.includes(drugIndicationRaw)) {
        isOffLabel = true;
      }

      const competitorData = {
        id: drug.id || drug.name.toLowerCase().replace(/\s+/g, '_'),
        name: drug.name,
        indication: currentIndication || drug.indication,
        actualApprovedIndication: drug.indication, // Keep the real one for reference
        baseCost: response.data.base_cost || 100000,
        aeMgmtCost: response.data.ae_mgmt_cost || 25000,
        aeRate: response.data.ae_rate || 0.15,
        isEstimated: response.data.is_estimated || false,
        isOffLabel: isOffLabel
      };

      setCustomCompetitors(prev => {
        const next = [...prev, competitorData];
        setWarRoomSnapshot(s => ({ ...s, thunderdome: { competitors: next } }));
        return next;
      });

      if (isOffLabel) {
        toast.warning(`Added ${drug.name} (Note: Unapproved for ${currentIndication})`, {
          style: { background: '#FEF08A', color: '#854D0E', border: '1px solid #FDE047' }
        });
      } else {
        toast.success(`Added ${drug.name} as competitor`);
      }
    } catch (error) {
      console.error('Error adding competitor:', error);

      // Determine if off-label (fallback logic)
      const currentIndication = selectedDrug.indication || '';
      const drugIndicationRaw = (drug.indication || '').toLowerCase();
      const currentIndicationRaw = currentIndication.toLowerCase();
      let isOffLabel = false;
      if (drugIndicationRaw && currentIndicationRaw && !drugIndicationRaw.includes(currentIndicationRaw) && !currentIndicationRaw.includes(drugIndicationRaw)) {
        isOffLabel = true;
      }

      // Add with default values if API fails
      const competitorData = {
        id: drug.id || drug.name.toLowerCase().replace(/\s+/g, '_'),
        name: drug.name,
        indication: currentIndication || drug.indication,
        actualApprovedIndication: drug.indication,
        baseCost: 100000,
        aeMgmtCost: 25000,
        aeRate: 0.15,
        isEstimated: true,
        isOffLabel: isOffLabel
      };
      setCustomCompetitors(prev => [...prev, competitorData]);

      if (isOffLabel) {
        toast.warning(`Added ${drug.name} (Estimated, Unapproved for ${currentIndication})`, {
          style: { background: '#FEF08A', color: '#854D0E', border: '1px solid #FDE047' }
        });
      } else {
        toast.success(`Added ${drug.name} (estimated values)`);
      }
    } finally {
      setIsLoadingCompetitor(false);
    }
  };

  // Remove a custom competitor
  const removeCompetitor = (competitorId) => {
    setCustomCompetitors(prev => prev.filter(c => c.id !== competitorId));
    toast.success('Competitor removed');
  };

  if (!selectedDrug || !calculationResults) {
    return (
      <div className="min-h-screen bg-[#1A1A1A] flex flex-col items-center justify-center text-white">
        <Loader2 className="w-12 h-12 text-blue-500 animate-spin mb-4" />
        <h2 className="text-xl font-bold tracking-widest uppercase">Initializing War Room Context...</h2>
        <p className="text-gray-400 mt-2">Loading core asset algorithms from the strategy server.</p>
        <Button onClick={() => navigate('/')} className="mt-8 bg-white/10 hover:bg-white/20">Return Home manually if stuck</Button>
      </div>
    );
  }

  // Theme-aware colors
  const textColor = theme === 'dark' ? '#E5E5E5' : '#1A1A1A';
  const mutedColor = theme === 'dark' ? '#737373' : '#6B7280';
  const borderColor = theme === 'dark' ? '#262626' : '#E5E5E5';
  const surfaceBg = theme === 'dark' ? '#121212' : '#FFFFFF';
  const cardBg = theme === 'dark' ? '#0A0A0A' : '#FAFAFA';
  const inputBg = theme === 'dark' ? '#050505' : '#F5F5F5';

  // Theme-aware CSS classes
  const textPrimary = theme === 'dark' ? 'text-white' : 'text-gray-900';
  const textSecondary = theme === 'dark' ? 'text-gray-300' : 'text-gray-700';

  // Module A: Competitive Thunderdome Data
  // Uses heorData (real regional costs) when available, falls back to calculationResults
  const getCompetitiveData = () => {
    const drugCost = heorData?.drug_base_cost ?? calculationResults.drug_cost;
    const aePerPeriod = heorData?.ae_management_cost ?? Math.round((calculationResults.commercial_brain?.drug_severe_ae_rate || 0.15) * 3 * 50000);
    const competitorBase = heorData?.standard_of_care_cost ?? calculationResults.competitor_base_cost;
    const competitorAe = calculationResults.breakdown?.adverse_event_cost ?? 0;

    const drugAeRate = calculationResults.commercial_brain?.drug_severe_ae_rate || 0.15;
    const drugAeCostValue = Math.round(drugAeRate * aePerPeriod);

    const data = [
      {
        name: selectedDrug.name,
        'Base Cost': drugCost,
        'AE Mgmt. Cost': showAdverseEventCost ? drugAeCostValue : 0,
        fill: '#008080',
        isSubject: true
      }
    ];

    data.push({
      name: selectedDrug.competitor_name || 'Standard',
      'Base Cost': competitorBase,
      'AE Mgmt. Cost': showAdverseEventCost ? (heorData ? Math.round(0.30 * aePerPeriod) : competitorAe) : 0,
      fill: '#737373',
      isDefault: true
    });

    const competitorColors = ['#E53E3E', '#F59E0B', '#8B5CF6', '#EC4899', '#06B6D4'];
    customCompetitors.forEach((comp, idx) => {
      data.push({
        name: comp.isOffLabel ? `${comp.name} [OFF-LABEL]` : comp.name,
        'Base Cost': comp.baseCost,
        'AE Mgmt. Cost': showAdverseEventCost ? comp.aeMgmtCost : 0,
        fill: competitorColors[idx % competitorColors.length],
        isCustom: true,
        fullName: comp.name
      });
    });

    return data;
  };

  // Module B: Calculate PAP
  const calculatePAP = async () => {
    try {
      const walletConverted = patientWallet / selectedRegion.conversion_rate_from_inr;
      const response = await axios.post(
        `${API}/pap/recommend?drug_id=${selectedDrug.id}&target_roi=${targetROI}&patient_wallet_monthly=${walletConverted}&region_code=${selectedRegion.code}`
      );
      const result = { ...response.data, currency: selectedRegion.currency_symbol };
      setPapRecommendation(result);
      // eslint-disable-next-line react-hooks/exhaustive-deps
      setWarRoomSnapshot(prev => ({ ...prev, dealArchitect: { papRecommendation: result, targetROI, patientWallet } }));
      toast.success('PAP recommendation calculated');
    } catch (error) {
      console.error('PAP calculation error:', error);
      toast.error('Failed to calculate PAP recommendation');
    }
  };

  // Module C: Patient Bridge Data
  const getPatientBridgeData = () => {
    const monthlyDrugCost = calculationResults.drug_cost / 12;
    const competitorMonthly = calculationResults.competitor_base_cost / 12;
    const icuSpike = calculationResults.breakdown.crash_cost;

    return {
      standard: [
        { month: 'M1', cost: competitorMonthly },
        { month: 'M2', cost: competitorMonthly },
        { month: 'M3', cost: competitorMonthly },
        { month: 'M4', cost: competitorMonthly + icuSpike }, // ICU spike
        { month: 'M5', cost: 0 },
        { month: 'M6', cost: 0 }
      ],
      innovation: [
        { month: 'M1', cost: monthlyDrugCost },
        { month: 'M2', cost: monthlyDrugCost },
        { month: 'M3', cost: monthlyDrugCost },
        { month: 'M4', cost: monthlyDrugCost },
        { month: 'M5', cost: monthlyDrugCost },
        { month: 'M6', cost: monthlyDrugCost }
      ]
    };
  };

  const bridgeData = getPatientBridgeData();
  const totalStandard = bridgeData.standard.reduce((sum, m) => sum + m.cost, 0);
  const totalInnovation = bridgeData.innovation.reduce((sum, m) => sum + m.cost, 0);

  // PDF Generation
  const handleGenerateDossier = async () => {
    setIsGeneratingPDF(true);
    try {
      const response = await axios.post(
        `${API}/dossier/generate?drug_id=${selectedDrug.id}&region_code=${selectedRegion.code}`,
        {},
        { responseType: 'blob' }
      );

      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `${selectedDrug.name}_Value_Dossier_${selectedRegion.code}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.parentNode.removeChild(link);

      toast.success('Global Value Dossier downloaded successfully');
    } catch (error) {
      console.error('PDF generation error:', error);
      toast.error('Failed to generate dossier');
    } finally {
      setIsGeneratingPDF(false);
    }
  };

  return (
    <div className="war-room min-h-screen relative">
      {/* Background gradient for depth - Dark Mode Only */}
      {theme === 'dark' && (
        <>
          <div className="fixed inset-0 bg-gradient-to-br from-[#050505] via-[#0a0a0a] to-[#050505] -z-10" />
          <div className="fixed inset-0 opacity-30 -z-10" style={{
            background: 'radial-gradient(ellipse at 30% 20%, rgba(0, 128, 128, 0.08) 0%, transparent 50%), radial-gradient(ellipse at 70% 80%, rgba(229, 62, 62, 0.05) 0%, transparent 50%)'
          }} />
        </>
      )}

      {/* Header with Glass Effect */}
      <div className="glass-surface border-b px-6 py-4 flex items-center justify-between sticky top-0 z-50" style={{ borderColor }}>
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
          <Button
            data-testid="back-to-dashboard-btn"
            variant="ghost"
            size="sm"
            onClick={() => navigate('/dashboard')}
            className="hover:bg-white/5"
            style={{ color: textColor }}
          >
            <ArrowLeft className="w-4 h-4 mr-2" />
            DASHBOARD
          </Button>
          <div className="tour-war-room-header">
            <h1 className="text-2xl font-bold font-data" style={{ color: textColor }}>WAR ROOM</h1>
            <p className="text-sm" style={{ color: mutedColor }}>Tactical Execution Modules</p>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <ThemeSwitcher />
          <RegionSwitcher />
          <button
            onClick={() => {
              setRunTourPhaseC(true);
            }}
            className="flex items-center gap-2 px-3 py-2 h-9 text-sm font-medium transition-colors rounded-sm border glass-button opacity-80 hover:opacity-100"
            style={{ color: textColor, borderColor: theme === 'dark' ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)' }}
          >
            <HelpCircle className="w-4 h-4" />
            <span className="hidden sm:inline">Tour</span>
          </button>
          <Button
            data-testid="generate-dossier-btn"
            onClick={handleGenerateDossier}
            disabled={isGeneratingPDF}
            className="tour-generate-dossier glass-button text-white font-data"
          >
            <Download className="w-4 h-4 mr-2" />
            {isGeneratingPDF ? 'GENERATING...' : 'GENERATE DOSSIER'}
          </Button>
        </div>
      </div>

      {/* Drug Context Bar */}
      <div className="border-b px-6 py-3" style={{ borderColor, background: surfaceBg }}>
        <div className="flex items-center justify-between">
          <div>
            <span className="text-xs uppercase tracking-widest mr-3" style={{ color: mutedColor }}>ASSET</span>
            <span className="font-data text-lg" style={{ color: textColor }}>{selectedDrug.name}</span>
            <span className="text-sm ml-3" style={{ color: mutedColor }}>| {selectedDrug.indication}</span>
          </div>
          <div className="flex items-center gap-6 text-sm">
            <div>
              <span className="mr-2" style={{ color: mutedColor }}>Drug Cost:</span>
              <span className="font-data" style={{ color: textColor }}>
                {selectedRegion.currency_symbol}{calculationResults.drug_cost.toLocaleString()}
              </span>
            </div>
            <div>
              <span className="mr-2" style={{ color: mutedColor }}>Liability:</span>
              <span className="font-data text-[#E53E3E]">
                {selectedRegion.currency_symbol}{calculationResults.total_liability.toLocaleString()}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content - Tabs */}
      <div className="p-6">
        <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
          <TabsList className="tour-war-room-tabs glass-card border border-white/10">
            <TabsTrigger value="thunderdome" className="font-data" data-testid="thunderdome-tab">
              <BarChart3 className="w-4 h-4 mr-2" />
              COMPETITIVE THUNDERDOME
            </TabsTrigger>
            {applicabilityModules.adherence !== false && (
              <TabsTrigger value="cliff" className="font-data" data-testid="cliff-simulator-tab">
                <TrendingDown className="w-4 h-4 mr-2" />
                DISCONTINUATION CLIFF
              </TabsTrigger>
            )}
            {applicabilityModules.pap_deal_architect !== false && (
              <TabsTrigger value="architect" className="font-data" data-testid="deal-architect-tab">
                <DollarSign className="w-4 h-4 mr-2" />
                DEAL ARCHITECT
              </TabsTrigger>
            )}
            <TabsTrigger value="tpp" className="font-data" data-testid="tpp-benchmarker-tab">
              <Beaker className="w-4 h-4 mr-2" />
              COMPARE MY TPP
            </TabsTrigger>
            <TabsTrigger value="bridge" className="font-data" data-testid="patient-bridge-tab">
              <FileText className="w-4 h-4 mr-2" />
              PATIENT BRIDGE
            </TabsTrigger>
          </TabsList>

          {/* Module A: Competitive Thunderdome */}
          <TabsContent value="thunderdome" className="space-y-6" data-testid="thunderdome-content">
            <div className="tour-strategic-brief">
              <StrategicBrief
                activeTab={activeTab}
                pricingModel={pricingModel}
                selectedPayer={selectedPayer}
                selectedDrug={selectedDrug}
                calculationResults={calculationResults}
              />
            </div>
            <Card className="tour-competitive-thunderdome glass-card overflow-hidden">
              <CardHeader className="pb-2">
                <CardTitle className={`font-data ${textPrimary}`}>
                  HEAD-TO-HEAD COST COMPARISON
                </CardTitle>
                <CardDescription className="text-muted-foreground">
                  Total cost-to-treat comparison including hidden liabilities
                </CardDescription>
              </CardHeader>
              <CardContent>
                {/* Controls Row: Add Competitor + Show Adverse-Event Cost */}
                <div className="flex flex-col md:flex-row md:items-end gap-4 mb-6 pb-4 border-b" style={{ borderColor }}>
                  {/* Add Competitor Input */}
                  <div className="flex-1 relative">
                    <Label className="text-xs uppercase tracking-widest text-muted-foreground mb-2 block">
                      Add Competitor ({customCompetitors.length}/{MAX_COMPETITORS})
                    </Label>
                    <div className="relative">
                      <Search className={`absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 ${theme === 'dark' ? 'text-gray-500' : 'text-gray-400'}`} />
                      <Input
                        data-testid="add-competitor-input"
                        type="text"
                        placeholder="Search drug to compare..."
                        value={competitorSearch}
                        onChange={(e) => handleCompetitorSearch(e.target.value)}
                        disabled={customCompetitors.length >= MAX_COMPETITORS || isLoadingCompetitor}
                        className={`pl-10 pr-4 py-2 text-sm h-9 ${theme === 'dark'
                          ? 'bg-[#050505] border-[#262626] text-white placeholder:text-gray-600'
                          : 'bg-white border-gray-300 text-gray-900 placeholder:text-gray-400'
                          }`}
                      />

                      {/* Suggestions Dropdown */}
                      {competitorSuggestions.length > 0 && (
                        <div
                          className={`absolute z-20 w-full mt-1 rounded-sm shadow-lg overflow-hidden max-h-48 overflow-y-auto ${theme === 'dark' ? 'bg-[#121212] border border-[#262626]' : 'bg-white border border-gray-200'
                            }`}
                          data-testid="competitor-suggestions-dropdown"
                        >
                          {competitorSuggestions.map((drug) => (
                            <button
                              key={drug.id}
                              data-testid={`add-competitor-${drug.id}`}
                              onClick={() => addCompetitor(drug)}
                              className={`w-full px-3 py-2 text-left transition-all border-b last:border-b-0 ${theme === 'dark'
                                ? 'hover:bg-[#008080]/20 border-[#262626]'
                                : 'hover:bg-[#008080]/10 border-gray-100'
                                }`}
                            >
                              <div className={`font-medium text-sm ${textPrimary}`}>{drug.name}</div>
                              <div className="text-xs text-muted-foreground">{drug.displayIndication || selectedDrug.indication || drug.indication}</div>
                            </button>
                          ))}
                        </div>
                      )}
                    </div>

                    {/* Added Competitors Tags */}
                    {customCompetitors.length > 0 && (
                      <div className="flex flex-wrap gap-1.5 mt-2">
                        {customCompetitors.map((comp, idx) => {
                          const colors = ['#E53E3E', '#F59E0B', '#8B5CF6', '#EC4899', '#06B6D4'];
                          const color = colors[idx % colors.length];
                          return (
                            <div
                              key={comp.id}
                              className="flex items-center gap-1.5 px-2 py-1 rounded-sm text-xs"
                              style={{ backgroundColor: `${color}20`, border: `1px solid ${color}40` }}
                              data-testid={`competitor-tag-${comp.id}`}
                            >
                              <div className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: color }} />
                              <span className={textPrimary}>
                                {comp.name}
                                {comp.isOffLabel && <span className="ml-1 text-[9px] text-yellow-600 font-bold bg-yellow-100 px-1 rounded">OFF-LABEL</span>}
                              </span>
                              <button
                                onClick={() => removeCompetitor(comp.id)}
                                className="hover:text-red-400 transition-colors"
                                data-testid={`remove-competitor-${comp.id}`}
                              >
                                <X className="w-3 h-3" />
                              </button>
                            </div>
                          );
                        })}
                      </div>
                    )}
                    {isLoadingCompetitor && (
                      <div className="text-xs text-muted-foreground mt-1">Loading...</div>
                    )}
                  </div>

                  {/* Show Adverse-Event Cost Toggle */}
                  <div className="flex items-center gap-2">
                    <Label htmlFor="adverse-event-toggle" className="text-sm font-normal text-muted-foreground cursor-pointer">
                      <InfoTooltip content="The hidden financial burden of managing serious adverse events and related hospitalization">
                        Show Adverse-Event Cost
                      </InfoTooltip>
                    </Label>
                    <Switch
                      id="adverse-event-toggle"
                      data-testid="adverse-event-cost-toggle"
                      checked={showAdverseEventCost}
                      onCheckedChange={setShowAdverseEventCost}
                    />
                  </div>
                </div>
                {/* Chart with loading overlay */}
                <div className="relative" style={{ height: '400px' }}>
                  {/* Loading/blur overlay */}
                  {isHeorLoading && (
                    <div className="absolute inset-0 z-10 flex flex-col items-center justify-center rounded"
                      style={{ backdropFilter: 'blur(6px)', background: 'rgba(5,5,5,0.6)' }}>
                      <div className="w-8 h-8 border-2 border-[#008080] border-t-transparent rounded-full animate-spin mb-3" />
                      <p className="text-xs font-data text-[#008080] uppercase tracking-widest">
                        Fetching {selectedRegion.name} regional data...
                      </p>
                    </div>
                  )}
                  <div style={{ filter: isHeorLoading ? 'blur(4px)' : 'none', height: '100%', transition: 'filter 0.3s ease' }}>
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={getCompetitiveData()}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#262626" opacity={0.3} />
                        <XAxis
                          dataKey="name"
                          stroke="#737373"
                          tick={{ fill: '#737373', fontSize: 14, fontFamily: 'JetBrains Mono' }}
                        />
                        <YAxis
                          stroke="#737373"
                          tick={{ fill: '#737373', fontSize: 12, fontFamily: 'JetBrains Mono' }}
                          tickFormatter={(value) => `${selectedRegion.currency_symbol}${(value / 1000).toFixed(0)}K`}
                        />
                        <Tooltip
                          contentStyle={{
                            background: '#121212',
                            border: '1px solid #262626',
                            borderRadius: '4px'
                          }}
                          labelStyle={{ color: '#E5E5E5', fontFamily: 'JetBrains Mono' }}
                          itemStyle={{ color: '#E5E5E5', fontFamily: 'JetBrains Mono' }}
                          formatter={(value) => `${selectedRegion.currency_symbol}${value.toLocaleString()}`}
                        />
                        <Legend
                          wrapperStyle={{ fontFamily: 'JetBrains Mono', fontSize: '12px' }}
                        />
                        <Bar dataKey="Base Cost" stackId="a" fill="#008080" radius={[0, 0, 0, 0]} />
                        <Bar
                          dataKey="AE Mgmt. Cost"
                          stackId="a"
                          fill="#E53E3E"
                          radius={[4, 4, 0, 0]}
                        />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>

                {/* Summary Table */}
                <div className="overflow-x-auto">
                  {heorData?.is_estimated && (
                    <div className="flex items-center gap-2 mb-3 text-xs text-amber-500/80">
                      <AlertTriangle className="w-3 h-3" />
                      <span>Prices estimated from {heorData.sources}. Replace with local tender/formulary data for precision.</span>
                    </div>
                  )}
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b" style={{ borderColor }}>
                        <th className={`text-left py-2 px-3 font-medium ${textPrimary}`}>Drug</th>
                        <th className={`text-right py-2 px-3 font-medium ${textPrimary}`}>Base Cost</th>
                        <th className={`text-right py-2 px-3 font-medium ${textPrimary}`}>AE Mgmt. Cost</th>
                        <th className={`text-right py-2 px-3 font-medium ${textPrimary}`}>Total</th>
                      </tr>
                    </thead>
                    <tbody>
                      {/* Subject Drug */}
                      <tr className="border-b" style={{ borderColor }}>
                        <td className="py-3 px-3">
                          <div className="flex items-center gap-2">
                            <div className="w-2 h-2 rounded-full bg-[#008080]" />
                            <span className={`font-medium ${textPrimary}`}>{selectedDrug.name}</span>
                            {heorData?.is_estimated && <span className="text-[10px] text-amber-500 border border-amber-500/50 px-1 rounded">Est.</span>}
                          </div>
                        </td>
                        <td className={`text-right py-3 px-3 font-data ${textPrimary}`}>
                          {formatLargeCurrency(heorData?.drug_base_cost ?? calculationResults.drug_cost, selectedRegion.currency_symbol)}
                        </td>
                        <td className="text-right py-3 px-3 font-data text-[#F59E0B]">
                          +{formatLargeCurrency(Math.round((calculationResults.commercial_brain?.drug_severe_ae_rate || 0.15) * (heorData?.ae_management_cost ?? 50000)), selectedRegion.currency_symbol)}
                        </td>
                        <td className="text-right py-3 px-3 font-data text-[#008080] font-bold">
                          {formatLargeCurrency((heorData?.drug_base_cost ?? calculationResults.drug_cost) + Math.round((calculationResults.commercial_brain?.drug_severe_ae_rate || 0.15) * (heorData?.ae_management_cost ?? 50000)), selectedRegion.currency_symbol)}
                        </td>
                      </tr>

                      {/* Default Competitor / SoC */}
                      <tr className="border-b" style={{ borderColor }}>
                        <td className="py-3 px-3">
                          <div className="flex items-center gap-2">
                            <div className="w-2 h-2 rounded-full bg-[#737373]" />
                            <span className={`font-medium ${textPrimary}`}>{selectedDrug.competitor_name}</span>
                            {heorData?.is_estimated && <span className="text-[10px] text-amber-500 border border-amber-500/50 px-1 rounded">Est.</span>}
                          </div>
                        </td>
                        <td className={`text-right py-3 px-3 font-data ${textPrimary}`}>
                          {formatLargeCurrency(heorData?.standard_of_care_cost ?? calculationResults.competitor_base_cost, selectedRegion.currency_symbol)}
                        </td>
                        <td className="text-right py-3 px-3 font-data text-[#E53E3E]">
                          +{formatLargeCurrency(Math.round(0.30 * (heorData?.ae_management_cost ?? calculationResults.breakdown?.adverse_event_cost ?? 45000)), selectedRegion.currency_symbol)}
                        </td>
                        <td className={`text-right py-3 px-3 font-data ${textPrimary} font-bold`}>
                          {formatLargeCurrency((heorData?.standard_of_care_cost ?? calculationResults.competitor_base_cost) + Math.round(0.30 * (heorData?.ae_management_cost ?? calculationResults.breakdown?.adverse_event_cost ?? 45000)), selectedRegion.currency_symbol)}
                        </td>
                      </tr>

                      {/* Custom Competitors */}
                      {customCompetitors.map((comp, idx) => {
                        const colors = ['#E53E3E', '#F59E0B', '#8B5CF6', '#EC4899', '#06B6D4'];
                        const color = colors[idx % colors.length];
                        const total = comp.baseCost + comp.aeMgmtCost;
                        return (
                          <tr key={comp.id} className="border-b" style={{ borderColor }}>
                            <td className="py-3 px-3">
                              <div className="flex items-center gap-2">
                                <div className="w-2 h-2 rounded-full" style={{ backgroundColor: color }} />
                                <span className={`font-medium ${textPrimary}`}>{comp.name}</span>
                                {comp.isEstimated && (
                                  <span className="text-[10px] text-amber-500 border border-amber-500/50 px-1 rounded">Est</span>
                                )}
                              </div>
                            </td>
                            <td className={`text-right py-3 px-3 font-data ${textPrimary}`}>
                              {formatLargeCurrency(comp.baseCost, selectedRegion.currency_symbol)}
                            </td>
                            <td className="text-right py-3 px-3 font-data" style={{ color }}>
                              +{formatLargeCurrency(comp.aeMgmtCost, selectedRegion.currency_symbol)}
                            </td>
                            <td className="text-right py-3 px-3 font-data font-bold" style={{ color }}>
                              {formatLargeCurrency(total, selectedRegion.currency_symbol)}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>

                {/* Value Bridge — replaces old single-line Key Insight */}
                {(() => {
                  const drugBase = heorData?.drug_base_cost ?? calculationResults.drug_cost;
                  const aeUnitCost = heorData?.ae_management_cost ?? 50000;
                  const drugAeRate = calculationResults.commercial_brain?.drug_severe_ae_rate || 0.15;
                  const competitorAeRate = 0.30; // standard SoC AE rate

                  const drugAeCost = Math.round(drugAeRate * aeUnitCost);
                  // Drug has the better primary endpoint → low treatment-failure burden (0 by default)
                  const drugRelapseCost = 0;

                  const firstCustomComp = customCompetitors.length > 0 ? customCompetitors[0] : null;

                  const competitorBase = firstCustomComp ? firstCustomComp.baseCost : (heorData?.standard_of_care_cost ?? calculationResults.competitor_base_cost);
                  const competitorAeCost = firstCustomComp ? firstCustomComp.aeMgmtCost : Math.round(competitorAeRate * aeUnitCost);
                  // Competitor: treatment-failure cost from the value-engine breakdown
                  const competitorRelapseCost = calculationResults.breakdown?.crash_cost ?? Math.round(aeUnitCost * 2.5);

                  let compName = firstCustomComp ? firstCustomComp.name : (selectedDrug.competitor_name || 'Standard of Care');
                  if (firstCustomComp && firstCustomComp.isOffLabel) {
                    compName = `${compName} [OFF-LABEL]`;
                  }

                  const vbData = {
                    value_bridge_data: {
                      competitor: {
                        name: compName,
                        base_cost: competitorBase,
                        adverse_event_cost_ae: competitorAeCost,
                        treatment_failure_cost: competitorRelapseCost,
                        total_cost: competitorBase + competitorAeCost + competitorRelapseCost,
                      },
                      our_asset: {
                        name: selectedDrug.name,
                        base_cost: drugBase,
                        adverse_event_cost_ae: drugAeCost,
                        treatment_failure_cost: drugRelapseCost,
                        total_cost: drugBase + drugAeCost + drugRelapseCost,
                      },
                    },
                    simple_value_narrative: {
                      headline: 'Free is Expensive.',
                      safety_value: `${selectedDrug.name} carries a ${Math.round(drugAeRate * 100)}% serious AE rate vs ${Math.round(competitorAeRate * 100)}% for ${selectedDrug.competitor_name || 'the comparator'}, preventing ${Math.round((competitorAeRate - drugAeRate) * 100)} severe hospitalizations per 100 patients and eliminating ${selectedRegion.currency_symbol}${(competitorAeCost - drugAeCost).toLocaleString()} in adverse-event costs per treatment period.`,
                      system_value: `By keeping patients on effective therapy, ${selectedDrug.name} eliminates the ${selectedRegion.currency_symbol}${competitorRelapseCost.toLocaleString()} treatment-failure burden carried by ${selectedDrug.competitor_name || 'the comparator'}, resulting in a net system saving of ${selectedRegion.currency_symbol}${Math.max(0, (competitorBase + competitorAeCost + competitorRelapseCost) - (drugBase + drugAeCost)).toLocaleString()} per patient per year.`,
                    },
                  };

                  return (
                    <div className="grid grid-cols-12 gap-6 items-stretch">
                      <div className="col-span-12 lg:col-span-8">
                        <ValueBridge
                          valueBridgeData={vbData}
                          currencySymbol={selectedRegion.currency_symbol}
                        />
                      </div>
                      <div className="col-span-12 lg:col-span-4">
                        <LogisticalBurdenCard
                          assetName={selectedDrug.name}
                          competitorName={selectedDrug.competitor_name}
                          logisticalData={calculationResults.commercial_brain?.logistics}
                        />
                      </div>
                    </div>
                  );
                })()}
              </CardContent>
            </Card>
          </TabsContent>

          {/* Module: Discontinuation Cliff Simulator */}
          <TabsContent value="cliff" className="space-y-6" data-testid="cliff-simulator-content">
            <StrategicBrief
              activeTab={activeTab}
              pricingModel={pricingModel}
              selectedPayer={selectedPayer}
              selectedDrug={selectedDrug}
              calculationResults={calculationResults}
            />
            <Card className="glass-card overflow-hidden">
              <CardHeader>
                <CardTitle className={`font-data ${textPrimary} flex items-center justify-between`}>
                  <div className="flex items-center gap-2">
                    <AlertTriangle className="w-5 h-5 text-[#E53E3E]" />
                    THE DISCONTINUATION CLIFF
                  </div>
                  <div className="flex items-center gap-2">
                    <Label htmlFor="cliff-toggle" className="text-sm font-normal text-muted-foreground cursor-pointer">
                      Enable Simulator
                    </Label>
                    <Switch
                      id="cliff-toggle"
                      data-testid="cliff-simulator-toggle"
                      checked={cliffSimEnabled}
                      onCheckedChange={(enabled) => {
                        setCliffSimEnabled(enabled);
                        if (enabled) {
                          // Calculate rescue cost
                          const rescueCost = Math.round(calculationResults.total_liability * 0.4);
                          toast.warning(
                            `Warning: Discontinuation at Period ${fundedPeriods[0]} triggers a ${selectedRegion.currency_symbol}${rescueCost.toLocaleString()} Deferred Cost Spike. Continuing therapy is more cost-effective.`,
                            { duration: 8000 }
                          );
                        }
                      }}
                    />
                  </div>
                </CardTitle>
                <CardDescription className="text-muted-foreground">
                  Visualize the financial cliff when treatment is discontinued prematurely
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                {/* Funded Periods Slider */}
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <Label className="text-sm text-muted-foreground">
                      <InfoTooltip content="Number of treatment periods before funding stops">
                        Funded Periods
                      </InfoTooltip>
                    </Label>
                    <span className={`font-data ${textPrimary} text-lg`}>{fundedPeriods[0]} Periods</span>
                  </div>
                  <Slider
                    data-testid="funded-periods-slider"
                    value={fundedPeriods}
                    onValueChange={(value) => {
                      setFundedPeriods(value);
                      if (cliffSimEnabled) {
                        const rescueCost = Math.round(calculationResults.total_liability * 0.4);
                        toast.warning(
                          `Warning: Discontinuation at Period ${value[0]} triggers a ${selectedRegion.currency_symbol}${rescueCost.toLocaleString()} Deferred Cost Spike. Continuing therapy is more cost-effective.`,
                          { duration: 5000 }
                        );
                      }
                    }}
                    min={1}
                    max={12}
                    step={1}
                    className="w-full"
                  />
                  <div className="flex justify-between text-xs text-muted-foreground font-data">
                    <span>1 Period</span>
                    <span>6 Periods</span>
                    <span>12 Periods</span>
                  </div>
                </div>

                {/* The Cliff Visualization */}
                <div style={{ height: '350px' }} data-testid="cliff-chart">
                  <ResponsiveContainer width="100%" height="100%">
                    <ComposedChart
                      data={(() => {
                        const stopPeriod = fundedPeriods[0];
                        const monthlyDrugCost = calculationResults.drug_cost / 12;
                        const rescueCost = Math.round(calculationResults.total_liability * 0.4);

                        const data = [];
                        for (let i = 1; i <= 12; i++) {
                          if (cliffSimEnabled) {
                            if (i <= stopPeriod) {
                              // Funded periods - normal drug cost
                              data.push({
                                period: `P${i}`,
                                treatment: monthlyDrugCost,
                                rescue: 0,
                                isStop: i === stopPeriod,
                                isFunded: true
                              });
                            } else if (i === stopPeriod + 1) {
                              // Rescue cost spike
                              data.push({
                                period: `P${i}`,
                                treatment: 0,
                                rescue: rescueCost,
                                isStop: false,
                                isRescue: true,
                                isFunded: false
                              });
                            } else {
                              // Post-discontinuation (palliation/ongoing)
                              data.push({
                                period: `P${i}`,
                                treatment: 0,
                                rescue: 0,
                                isStop: false,
                                isFunded: false
                              });
                            }
                          } else {
                            // No simulation - just show normal treatment costs
                            data.push({
                              period: `P${i}`,
                              treatment: monthlyDrugCost,
                              rescue: 0,
                              isStop: false,
                              isFunded: true
                            });
                          }
                        }
                        return data;
                      })()}
                    >
                      <CartesianGrid strokeDasharray="3 3" stroke="#262626" opacity={0.3} />
                      <XAxis
                        dataKey="period"
                        stroke="#737373"
                        tick={{ fill: '#737373', fontSize: 11, fontFamily: 'JetBrains Mono' }}
                      />
                      <YAxis
                        stroke="#737373"
                        tick={{ fill: '#737373', fontSize: 11, fontFamily: 'JetBrains Mono' }}
                        tickFormatter={(v) => `${(v / 100000).toFixed(1)}L`}
                      />
                      <Tooltip
                        contentStyle={{
                          background: '#121212',
                          border: '1px solid #262626',
                          borderRadius: '4px'
                        }}
                        labelStyle={{ color: '#E5E5E5', fontFamily: 'JetBrains Mono' }}
                        formatter={(value, name) => [
                          `${selectedRegion.currency_symbol}${value.toLocaleString()}`,
                          name === 'treatment' ? 'Treatment Cost' : 'Deferred Cost Spike'
                        ]}
                      />
                      <Legend
                        wrapperStyle={{ fontFamily: 'JetBrains Mono', fontSize: '12px' }}
                        formatter={(value) => value === 'treatment' ? 'Treatment Cost' : 'Deferred Cost Spike'}
                      />

                      {/* Treatment bars */}
                      <Bar dataKey="treatment" fill="#008080" radius={[4, 4, 0, 0]}>
                        {(() => {
                          const stopPeriod = fundedPeriods[0];
                          const cells = [];
                          for (let i = 0; i < 12; i++) {
                            if (cliffSimEnabled && i >= stopPeriod) {
                              cells.push(<Cell key={i} fill="#262626" />);
                            } else {
                              cells.push(<Cell key={i} fill="#008080" />);
                            }
                          }
                          return cells;
                        })()}
                      </Bar>

                      {/* Rescue cost bar (the cliff) */}
                      <Bar dataKey="rescue" fill="#E53E3E" radius={[4, 4, 0, 0]} />

                      {/* Funding Stop Line */}
                      {cliffSimEnabled && (
                        <ReferenceLine
                          x={`C${fundedPeriods[0]}`}
                          stroke="#F59E0B"
                          strokeWidth={2}
                          strokeDasharray="6 4"
                          label={{
                            value: 'FUNDING STOP',
                            fill: '#F59E0B',
                            fontSize: 11,
                            fontWeight: 'bold',
                            position: 'top'
                          }}
                        />
                      )}
                    </ComposedChart>
                  </ResponsiveContainer>
                </div>

                {/* Cost Breakdown */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="p-4 bg-[#008080]/10 border border-[#008080]/30 rounded-sm">
                    <div className="text-xs uppercase tracking-widest text-[#008080] mb-1">FUNDED TREATMENT</div>
                    <div className={`font-data ${textPrimary} text-xl`}>
                      {selectedRegion.currency_symbol}{Math.round((calculationResults.drug_cost / 12) * fundedPeriods[0]).toLocaleString()}
                    </div>
                    <div className="text-xs text-muted-foreground mt-1">
                      {fundedPeriods[0]} periods × {selectedRegion.currency_symbol}{Math.round(calculationResults.drug_cost / 12).toLocaleString()}
                    </div>
                  </div>

                  <div className={`p-4 rounded-sm ${cliffSimEnabled ? 'bg-[#E53E3E]/10 border border-[#E53E3E]/30' : 'bg-[#262626] border border-[#262626]'}`}>
                    <div className={`text-xs uppercase tracking-widest mb-1 ${cliffSimEnabled ? 'text-[#E53E3E]' : 'text-muted-foreground'}`}>
                      DEFERRED COST SPIKE
                    </div>
                    <div className={`font-data text-xl ${cliffSimEnabled ? 'text-[#E53E3E] font-bold' : 'text-muted-foreground'}`}>
                      {cliffSimEnabled
                        ? `${selectedRegion.currency_symbol}${Math.round(calculationResults.total_liability * 0.4).toLocaleString()}`
                        : '—'
                      }
                    </div>
                    <div className="text-xs text-muted-foreground mt-1">
                      40% of Unfunded Exposure
                    </div>
                  </div>

                  <div className={`p-4 rounded-sm ${cliffSimEnabled ? 'bg-[#F59E0B]/10 border border-[#F59E0B]/30' : 'bg-[#262626] border border-[#262626]'}`}>
                    <div className={`text-xs uppercase tracking-widest mb-1 ${cliffSimEnabled ? 'text-[#F59E0B]' : 'text-muted-foreground'}`}>
                      TOTAL WITH DISCONTINUATION
                    </div>
                    <div className={`font-data text-xl ${cliffSimEnabled ? 'text-[#F59E0B] font-bold' : 'text-muted-foreground'}`}>
                      {cliffSimEnabled
                        ? `${selectedRegion.currency_symbol}${(
                          Math.round((calculationResults.drug_cost / 12) * fundedPeriods[0]) +
                          Math.round(calculationResults.total_liability * 0.4)
                        ).toLocaleString()}`
                        : '—'
                      }
                    </div>
                    <div className="text-xs text-muted-foreground mt-1">
                      Funded + Rescue
                    </div>
                  </div>
                </div>

                {/* The Lesson */}
                <Separator className="bg-white/10" />

                <div className={`p-6 rounded-sm ${cliffSimEnabled ? 'bg-[#E53E3E]/10 border-2 border-[#E53E3E]/50' : 'bg-[#121212] border border-[#262626]'}`}>
                  <div className="flex items-start gap-4">
                    <AlertTriangle className={`w-8 h-8 flex-shrink-0 ${cliffSimEnabled ? 'text-[#E53E3E]' : 'text-muted-foreground'}`} />
                    <div>
                      <div className={`text-sm font-bold mb-2 ${cliffSimEnabled ? 'text-[#E53E3E]' : 'text-muted-foreground'}`}>
                        UNFUNDED EXPOSURE WARNING
                      </div>
                      {cliffSimEnabled ? (
                        <div className="space-y-3">
                          <p className={`text-sm ${textPrimary}`}>
                            Stopping treatment at <span className="font-data font-bold text-[#F59E0B]">Period {fundedPeriods[0]}</span> triggers
                            a <span className="font-data font-bold text-[#E53E3E]">{selectedRegion.currency_symbol}{Math.round(calculationResults.total_liability * 0.4).toLocaleString()}</span> Deferred Cost Spike.
                          </p>
                          <p className={`text-sm ${textPrimary}`}>
                            <span className="font-bold">Total Projected Liability:</span>{' '}
                            <span className="font-data text-[#F59E0B]">
                              {selectedRegion.currency_symbol}{(
                                Math.round((calculationResults.drug_cost / 12) * fundedPeriods[0]) +
                                Math.round(calculationResults.total_liability * 0.4)
                              ).toLocaleString()}
                            </span>
                          </p>
                          <p className={`text-sm ${textPrimary}`}>
                            <span className="font-bold">Full 12-Period Treatment:</span>{' '}
                            <span className="font-data text-[#008080]">
                              {selectedRegion.currency_symbol}{calculationResults.drug_cost.toLocaleString()}
                            </span>
                          </p>
                          {(Math.round((calculationResults.drug_cost / 12) * fundedPeriods[0]) + Math.round(calculationResults.total_liability * 0.4)) > calculationResults.drug_cost && (
                            <div className="mt-4 p-3 bg-[#E53E3E]/20 rounded-sm">
                              <p className={`text-sm font-bold ${textPrimary}`}>
                                Discontinuation creates <span className="text-[#E53E3E] font-data">
                                  {selectedRegion.currency_symbol}{(
                                    (Math.round((calculationResults.drug_cost / 12) * fundedPeriods[0]) + Math.round(calculationResults.total_liability * 0.4)) -
                                    calculationResults.drug_cost
                                  ).toLocaleString()} additional unfunded exposure
                                </span> vs. completing full therapy.
                              </p>
                            </div>
                          )}
                        </div>
                      ) : (
                        <p className="text-sm text-muted-foreground">
                          Enable the simulator to visualize how discontinuing treatment creates unfunded downstream exposure that exceeds the cost of continuing therapy.
                        </p>
                      )}
                    </div>
                  </div>
                </div>

                {/* Formula Reference */}
                <div className="p-4 bg-[#050505] border border-[#262626] rounded-sm">
                  <div className="text-xs uppercase tracking-widest text-muted-foreground mb-2">RISK MODEL FORMULA</div>
                  <code className="text-xs font-data text-[#00D4D4]">
                    Deferred_Cost_Spike = 40% × Unfunded_Exposure = 0.4 × {selectedRegion.currency_symbol}{calculationResults.total_liability.toLocaleString()} = {selectedRegion.currency_symbol}{Math.round(calculationResults.total_liability * 0.4).toLocaleString()}
                  </code>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Module B: Deal Architect */}
          <TabsContent value="architect" className="space-y-6" data-testid="deal-architect-content">
            <StrategicBrief
              activeTab={activeTab}
              pricingModel={pricingModel}
              selectedPayer={selectedPayer}
              selectedDrug={selectedDrug}
              calculationResults={calculationResults}
            />
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Payer Segment Selection */}
              <Card className="war-room-surface lg:col-span-3">
                <CardHeader>
                  <CardTitle className={`font-data ${textPrimary}`}>PAYER SEGMENT ANALYSIS</CardTitle>
                  <CardDescription className="text-muted-foreground">
                    Select payer type to see segment-specific pricing and advice
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                  <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                    <div>
                      <Label className="text-sm text-muted-foreground mb-2 block">Payer Segment</Label>
                      <Select value={selectedPayer} onValueChange={setSelectedPayer}>
                        <SelectTrigger
                          className={`w-full font-data ${theme === 'dark'
                            ? 'bg-[#050505] border-[#262626] text-white'
                            : 'bg-white border-gray-300 text-gray-900'
                            }`}
                          data-testid="war-room-payer-selector"
                        >
                          <SelectValue placeholder="Select Payer Type" />
                        </SelectTrigger>
                        <SelectContent className={
                          theme === 'dark'
                            ? 'bg-[#121212] border-[#262626] text-white'
                            : 'bg-white border-gray-200 text-gray-900'
                        }>
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
                    </div>

                    {pricingModel && (
                      <>
                        <div>
                          <Label className="text-sm text-muted-foreground mb-2 block">List Price/Period</Label>
                          <div className={`font-data ${textPrimary} text-xl`}>
                            {pricingModel.currency_symbol}{pricingModel.list_price_per_period?.toLocaleString()}
                          </div>
                        </div>
                        <div>
                          <Label className="text-sm text-muted-foreground mb-2 block">Annual Patient OOP</Label>
                          <div className="font-data text-[#E53E3E] text-xl">
                            {pricingModel.currency_symbol}{pricingModel.annual_oop_impact?.toLocaleString()}
                          </div>
                        </div>
                        <div>
                          <Label className="text-sm text-muted-foreground mb-2 block">Effective Monthly</Label>
                          <div className="font-data text-[#F59E0B] text-xl">
                            {pricingModel.currency_symbol}{pricingModel.effective_monthly_cost?.toLocaleString()}
                          </div>
                        </div>
                      </>
                    )}
                  </div>

                  {/* Period-Based Chart */}
                  {pricingModel && pricingModel.period_data && (
                    <div style={{ height: '250px' }}>
                      <ResponsiveContainer width="100%" height="100%">
                        <ComposedChart data={pricingModel.period_data.map(c => ({
                          name: `C${c.period}`,
                          patient: c.patient_pay,
                          insurer: c.insurer_pay,
                          govt: c.govt_pay,
                          effective: pricingModel.effective_monthly_cost,
                          isFree: c.is_free_period
                        }))}>
                          <CartesianGrid strokeDasharray="3 3" stroke="#262626" opacity={0.3} />
                          <XAxis dataKey="name" stroke="#737373" tick={{ fill: '#737373', fontSize: 11 }} />
                          <YAxis stroke="#737373" tick={{ fill: '#737373', fontSize: 11 }} tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`} />
                          <Tooltip
                            contentStyle={{ background: '#121212', border: '1px solid #262626', borderRadius: '4px' }}
                            formatter={(value) => [`${pricingModel.currency_symbol}${value.toLocaleString()}`, '']}
                          />
                          <Legend />
                          <Bar dataKey="patient" name="Patient Pays" fill="#E53E3E" radius={[2, 2, 0, 0]} />
                          {pricingModel.annual_insurer_impact > 0 && (
                            <Bar dataKey="insurer" name="Insurer Pays" fill="#3B82F6" radius={[2, 2, 0, 0]} />
                          )}
                          {pricingModel.annual_govt_impact > 0 && (
                            <Bar dataKey="govt" name="Govt Pays" fill="#10B981" radius={[2, 2, 0, 0]} />
                          )}
                          {pricingModel.effective_monthly_cost > 0 && (
                            <ReferenceLine y={pricingModel.effective_monthly_cost} stroke="#F59E0B" strokeDasharray="5 5" />
                          )}
                        </ComposedChart>
                      </ResponsiveContainer>
                    </div>
                  )}

                  {/* Deal Architect Advice */}
                  {pricingModel && (
                    <div className="p-4 bg-[#008080]/10 border border-[#008080]/30 rounded-sm">
                      <div className="text-xs uppercase tracking-widest text-[#008080] mb-2">DEAL ARCHITECT RECOMMENDATION</div>
                      <p className={`text-sm ${textPrimary}`}>{pricingModel.deal_architect_advice}</p>
                      {pricingModel.pap_scheme_applied && (
                        <Badge className="mt-2 bg-[#008080] text-white">{pricingModel.pap_scheme_applied}</Badge>
                      )}
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* Legacy PAP Calculator */}
              <Card className="glass-card overflow-hidden">
                <CardHeader>
                  <CardTitle className={`font-data ${textPrimary}`}>CUSTOM PAP CALCULATOR</CardTitle>
                  <CardDescription className="text-muted-foreground">
                    Define custom parameters for PAP recommendation
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                  <div className="space-y-2">
                    <Label htmlFor="target-roi" className="text-sm text-muted-foreground">
                      <InfoTooltip content="Target return on investment multiplier for payer value proposition">
                        Target Payer ROI
                      </InfoTooltip>
                    </Label>
                    <div className="flex items-center gap-3">
                      <Input
                        id="target-roi"
                        data-testid="target-roi-input"
                        type="number"
                        step="0.1"
                        value={targetROI}
                        onChange={(e) => setTargetROI(parseFloat(e.target.value))}
                        className={`font-data border-[#262626] ${theme === 'dark' ? 'bg-[#050505] text-white' : 'bg-white text-gray-900 border-gray-300'}`}
                      />
                      <span className="text-sm text-muted-foreground">× Return</span>
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="patient-wallet" className="text-sm text-muted-foreground">
                      <InfoTooltip content="Maximum monthly out-of-pocket capacity for patient/family">
                        Patient Monthly Wallet
                      </InfoTooltip>
                    </Label>
                    <div className="flex items-center gap-3">
                      <span className={`font-data ${textPrimary}`}>{selectedRegion.currency_symbol}</span>
                      <Input
                        id="patient-wallet"
                        data-testid="patient-wallet-input"
                        type="number"
                        step="1000"
                        min="0"
                        max="100000000"
                        value={patientWallet}
                        onChange={(e) => {
                          const val = parseFloat(e.target.value);
                          if (!isNaN(val) && val >= 0 && val <= 100000000) {
                            setPatientWallet(val);
                          }
                        }}
                        className={`font-data border-[#262626] ${theme === 'dark' ? 'bg-[#050505] text-white' : 'bg-white text-gray-900 border-gray-300'}`}
                      />
                      <span className="text-sm text-muted-foreground">/ month</span>
                    </div>
                  </div>

                  <Button
                    data-testid="calculate-pap-btn"
                    onClick={calculatePAP}
                    className="w-full bg-[#008080] hover:bg-[#008080]/90 text-white font-data"
                  >
                    CALCULATE PAP
                  </Button>
                </CardContent>
              </Card>

              {papRecommendation && (
                <Card className="war-room-surface lg:col-span-2" data-testid="pap-recommendation-result">
                  <CardHeader>
                    <CardTitle className={`font-data ${textPrimary}`}>CUSTOM PAP RESULT</CardTitle>
                    <CardDescription className="text-muted-foreground">
                      Optimized patient assistance structure
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <span className="text-sm text-muted-foreground">Headline Price</span>
                        <div className={`font-data ${textPrimary} text-lg`}>
                          {papRecommendation.currency}{papRecommendation.headline_price.toLocaleString()}
                        </div>
                      </div>
                      <div>
                        <span className="text-sm text-muted-foreground">Affordability Gap</span>
                        <div className="font-data text-[#E53E3E] text-lg">
                          {papRecommendation.currency}{papRecommendation.gap.toLocaleString()}
                        </div>
                      </div>
                    </div>
                    <div className="p-4 bg-[#008080]/10 border border-[#008080]/30 rounded-sm">
                      <div className="text-xs uppercase tracking-widest text-muted-foreground mb-2">SCHEME</div>
                      <div className="text-lg font-data text-[#008080] font-bold">
                        {papRecommendation.recommended_scheme}
                      </div>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className={`text-sm font-bold ${textPrimary}`}>Effective Price</span>
                      <span className="font-data text-[#10B981] font-bold text-xl">
                        {papRecommendation.currency}{papRecommendation.effective_price.toLocaleString()}
                      </span>
                    </div>
                  </CardContent>
                </Card>
              )}
            </div>
          </TabsContent>

          {/* Module C: Patient Bridge */}
          <TabsContent value="bridge" className="space-y-6" data-testid="patient-bridge-content">
            <StrategicBrief
              activeTab={activeTab}
              pricingModel={pricingModel}
              selectedPayer={selectedPayer}
              selectedDrug={selectedDrug}
              calculationResults={calculationResults}
            />
            <Card className="glass-card overflow-hidden">
              <CardHeader>
                <CardTitle className={`font-data ${textPrimary}`}>FINANCIAL COUNSELING: CASH FLOW COMPARISON</CardTitle>
                <CardDescription className="text-muted-foreground">
                  Volatile "Watch & Wait" vs. Predictable Innovation
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="space-y-6">
                  {/* The Gradient Slopes Chart */}
                  <div style={{ height: '350px' }} data-testid="bridge-gradient-slopes">
                    <ResponsiveContainer width="100%" height="100%">
                      <AreaChart
                        data={(() => {
                          const data = [];
                          for (let i = 0; i < 6; i++) {
                            data.push({
                              month: bridgeData.standard[i].month,
                              standard: bridgeData.standard[i].cost,
                              innovation: bridgeData.innovation[i].cost,
                              isSpike: bridgeData.standard[i].cost > 100000
                            });
                          }
                          return data;
                        })()}
                        margin={{ top: 20, right: 30, left: 20, bottom: 5 }}
                      >
                        <defs>
                          <linearGradient id="colorStandard" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#E53E3E" stopOpacity={0.8} />
                            <stop offset="95%" stopColor="#E53E3E" stopOpacity={0.1} />
                          </linearGradient>
                          <linearGradient id="colorInnovation" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#008080" stopOpacity={0.8} />
                            <stop offset="95%" stopColor="#008080" stopOpacity={0.1} />
                          </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" stroke="#262626" opacity={0.3} />
                        <XAxis dataKey="month" stroke="#737373" tick={{ fill: '#737373', fontSize: 12, fontFamily: 'JetBrains Mono' }} />
                        <YAxis
                          stroke="#737373"
                          tickFormatter={(value) => `${selectedRegion.currency_symbol}${(value / 1000).toFixed(0)}k`}
                          tick={{ fill: '#737373', fontSize: 12, fontFamily: 'JetBrains Mono' }}
                        />
                        <Tooltip
                          contentStyle={{ background: '#121212', border: '1px solid #262626', borderRadius: '4px' }}
                          labelStyle={{ color: '#E5E5E5', fontFamily: 'JetBrains Mono' }}
                          itemStyle={{ fontFamily: 'JetBrains Mono' }}
                          formatter={(value) => `${selectedRegion.currency_symbol}${value.toLocaleString()}`}
                        />
                        <Legend wrapperStyle={{ fontFamily: 'JetBrains Mono' }} />

                        <Area
                          type="monotone"
                          dataKey="standard"
                          name="Standard Care (Volatile)"
                          stroke="#E53E3E"
                          fillOpacity={1}
                          fill="url(#colorStandard)"
                          animationBegin={0}
                          animationDuration={1500}
                        />

                        <Area
                          type="monotone"
                          dataKey="innovation"
                          name={`${selectedDrug.name} (Predictable EMI)`}
                          stroke="#008080"
                          fillOpacity={1}
                          fill="url(#colorInnovation)"
                          animationBegin={500}
                          animationDuration={1500}
                        />

                        {/* Risk Pulse Animation - Highlight the M4 Spike conceptually */}
                        {bridgeData.standard.map((d) => d.cost > 100000 ? (
                          <ReferenceLine key={`spike-${d.month}`} x={d.month} stroke="#F59E0B" strokeDasharray="3 3" label={{ position: 'top', value: 'Catastrophic Risk', fill: '#F59E0B', fontSize: 12, fontFamily: 'Archivo, sans-serif' }} className="animate-pulse" />
                        ) : null)}
                      </AreaChart>
                    </ResponsiveContainer>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="p-4 bg-[#E53E3E]/10 border border-[#E53E3E]/30 rounded-sm">
                      <div className="text-xs uppercase tracking-widest text-[#E53E3E] mb-2 font-bold">Standard Care Liability</div>
                      <div className="font-data text-2xl text-white mb-1">{selectedRegion.currency_symbol}{totalStandard.toLocaleString()}</div>
                      <p className={`text-xs ${textPrimary} mt-2`}>
                        <span className="font-bold">Risk:</span> Unpredictable catastrophic costs.
                      </p>
                    </div>
                    <div className="p-4 bg-[#008080]/10 border border-[#008080]/30 rounded-sm">
                      <div className="text-xs uppercase tracking-widest text-[#008080] mb-2 font-bold">{selectedDrug.name.toUpperCase()} PREDICTABILITY</div>
                      <div className="font-data text-2xl text-white mb-1">{selectedRegion.currency_symbol}{totalInnovation.toLocaleString()}</div>
                      <p className={`text-xs ${textPrimary} mt-2`}>
                        <span className="font-bold">Benefit:</span> Flat, predictable monthly EMI.
                      </p>
                    </div>
                  </div>
                </div>

                <Separator className="bg-white/10" />

                <div className="p-6 bg-[#121212] border border-[#262626] rounded-sm transform transition-all hover:scale-[1.01] hover:shadow-[0_0_30px_rgba(0,128,128,0.15)]">
                  <div className="text-center space-y-3">
                    <div className="text-xs uppercase tracking-widest text-muted-foreground">
                      FINANCIAL ADVANTAGE
                    </div>
                    <div className={`font-data ${textPrimary} text-3xl`}>
                      {totalStandard > totalInnovation ? (
                        <>
                          <span className="text-[#10B981]">Save {selectedRegion.currency_symbol}{(totalStandard - totalInnovation).toLocaleString()}</span>
                          <p className="text-sm text-muted-foreground mt-2">over 6 months with predictable care</p>
                        </>
                      ) : (
                        <>
                          <span className="text-[#008080]">Invest {selectedRegion.currency_symbol}{(totalInnovation - totalStandard).toLocaleString()}</span>
                          <p className="text-sm text-muted-foreground mt-2">for catastrophic risk protection</p>
                        </>
                      )}
                    </div>
                  </div>
                </div>

                <Button
                  data-testid="print-counseling-sheet-btn"
                  variant="outline"
                  className={`w-full border-[#262626] ${textPrimary} hover:bg-white/10`}
                  onClick={() => window.print()}
                >
                  <FileText className="w-4 h-4 mr-2" />
                  PRINT COUNSELING SHEET
                </Button>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Module: TPP Benchmarker - Compare My TPP */}
          <TabsContent value="tpp" className="space-y-6" data-testid="tpp-benchmarker-content">
            <TPPBenchmarker
              theme={theme}
              textPrimary={textPrimary}
              textSecondary={textSecondary}
              cardBg={cardBg}
              borderColor={borderColor}
              selectedPayer={selectedPayer}
              setSelectedPayer={setSelectedPayer}
              payerSegments={payerSegments}
            />
          </TabsContent>
        </Tabs>

        {/* Assumptions & Methodology Table - Full Transparency (Hidden on TPP tab since it has its own) */}
        {activeTab !== 'tpp' && (
          <div className="mt-6">
            <AssumptionsTable calculation={calculationResults} theme={theme} />
          </div>
        )}
      </div>
    </div>
  );
}
