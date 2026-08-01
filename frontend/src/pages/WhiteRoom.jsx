import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, X, Swords, HelpCircle } from 'lucide-react';
import { Input } from '../components/ui/input';
import axios from 'axios';
import { useApp } from '../context/AppContext';
import { ThemeSwitcher } from '../components/ThemeSwitcher';
import { IndicationSelectDialog } from '../components/IndicationSelectDialog';
import { driver } from 'driver.js';
import 'driver.js/dist/driver.css';
import { AnalysisLoadingOverlay } from '../components/AnalysisLoadingOverlay';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || '';
const API = (BACKEND_URL && BACKEND_URL.startsWith('http')) ? `${BACKEND_URL}/api` : '/api';

export default function WhiteRoom() {
  const [searchQuery, setSearchQuery] = useState('');
  const [suggestions, setSuggestions] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [loadingDrugName, setLoadingDrugName] = useState('');
  const { setSelectedDrug, theme, selectedRegion, hasSeenTour, setHasSeenTour, runTourPhaseA, setRunTourPhaseA } = useApp();
  const navigate = useNavigate();

  // Indication selection state
  const [showIndicationDialog, setShowIndicationDialog] = useState(false);
  const [pendingDrug, setPendingDrug] = useState(null);
  const [availableIndications, setAvailableIndications] = useState([]);

  // Competitor/Rival state
  const [competitorQuery, setCompetitorQuery] = useState('');
  const [competitorSuggestions, setCompetitorSuggestions] = useState([]);
  const [selectedCompetitor, setSelectedCompetitor] = useState(null);
  const [didYouMean, setDidYouMean] = useState(null);

  // Auto-open Tour on first visit
  React.useEffect(() => {
    if (!hasSeenTour && !runTourPhaseA) {
      // Small delay to ensure DOM is ready
      setTimeout(() => setRunTourPhaseA(true), 500);
    }
  }, [hasSeenTour, runTourPhaseA, setRunTourPhaseA]);

  React.useEffect(() => {
    if (runTourPhaseA) {
      const driverObj = driver({
        showProgress: false,
        popoverClass: theme === 'dark' ? 'driver-popover-dark' : 'driver-popover-light',
        steps: [
          {
            element: '.tour-search-input',
            popover: {
              title: 'Step 1: Search & Discover',
              description: 'Enter any therapeutic asset (e.g., Semaglutide, Tirzepatide) to begin real-time strategic analysis.',
              side: 'bottom',
              align: 'start'
            }
          }
        ],
        onDestroyStarted: () => {
          if (!driverObj.hasNextStep() || window.confirm("Skip the rest of the tour?")) {
            driverObj.destroy();
            setRunTourPhaseA(false);
            setHasSeenTour(true);
          }
        },
      });
      driverObj.drive();
    }
  }, [runTourPhaseA, setRunTourPhaseA, setHasSeenTour, theme]);

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
        } else if (data && data.results) {
          setSuggestions(data.results);
          setDidYouMean(data.did_you_mean || null);
        } else {
          console.error('Search API returned unexpected data:', typeof data);
          setSuggestions([]);
          setDidYouMean(null);
        }
      } catch (error) {
        console.error('Search error:', error);
      }
    } else {
      setSuggestions([]);
      setDidYouMean(null);
    }
  };

  const handleCompetitorSearch = async (value) => {
    setCompetitorQuery(value);
    setSelectedCompetitor(null);
    if (value.length > 1) {
      try {
        const response = await axios.get(`${API}/drugs/search?q=${value}`);
        const data = response.data;
        const results = Array.isArray(data) ? data : (data?.results || []);
        setCompetitorSuggestions(results);
      } catch (error) {
        console.error('Competitor search error:', error);
      }
    } else {
      setCompetitorSuggestions([]);
    }
  };

  const handleSelectCompetitor = (drug) => {
    setSelectedCompetitor(drug);
    setCompetitorQuery(drug.name);
    setCompetitorSuggestions([]);
    toast.success(`Competitor set: ${drug.name}`);
  };

  const clearCompetitor = () => {
    setSelectedCompetitor(null);
    setCompetitorQuery('');
  };

  const handleSelectDrug = async (drugId, drugName = null, drugIndication = null) => {
    setIsLoading(true);
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
        setShowIndicationDialog(true);
        setIsLoading(false);
        setLoadingDrugName('');
        return;
      }

      // Single indication - proceed directly with analysis
      // Include competitor if selected
      let analyzeUrl = `${API}/drugs/analyze?drug_name=${encodeURIComponent(indicationsData.drug_name || drugName || drugId)}&region_code=${selectedRegion.code}`;
      if (selectedCompetitor) {
        analyzeUrl += `&competitor_name=${encodeURIComponent(selectedCompetitor.name)}`;
      }
      // Explicitly append the indication if provided by the dropdown array
      if (drugIndication && !drugIndication.includes("Click to analyze via real-time web search")) {
        analyzeUrl += `&indication=${encodeURIComponent(drugIndication)}`;
      }

      const response = await axios.post(analyzeUrl);
      setSelectedDrug(response.data);
      navigate('/dashboard');
    } catch (error) {
      console.error('Error fetching drug:', error);
      toast.error('Failed to load drug information');
      setIsLoading(false);
      setLoadingDrugName('');
    }
  };

  const handleIndicationSelect = async (selectedIndication) => {
    if (!pendingDrug) return;

    setIsLoading(true);
    setLoadingDrugName(pendingDrug.name);
    setShowIndicationDialog(false);

    try {
      // Analyze with selected indication
      // Include competitor if selected
      let analyzeUrl = `${API}/drugs/analyze?drug_name=${encodeURIComponent(pendingDrug.name)}&indication=${encodeURIComponent(selectedIndication)}&region_code=${selectedRegion.code}`;
      if (selectedCompetitor) {
        analyzeUrl += `&competitor_name=${encodeURIComponent(selectedCompetitor.name)}`;
      }

      const response = await axios.post(analyzeUrl);
      setSelectedDrug(response.data);
      setPendingDrug(null);
      setAvailableIndications([]);
      navigate('/dashboard');
    } catch (error) {
      console.error('Error analyzing drug with indication:', error);
      console.error('Raw error details:', error.response?.data || error.message);
      toast.error(`Failed to analyze: ${error.message}`);
    } finally {
      setIsLoading(false);
      setLoadingDrugName('');
    }
  };

  return (
    <div className={`min-h-screen flex items-center justify-center px-4 relative ${theme === 'dark' ? 'bg-[#050505]' : 'bg-white'}`}>
      {/* Background gradient for depth */}
      {theme === 'dark' && (
        <>
          <div className="fixed inset-0 bg-gradient-to-br from-[#050505] via-[#0a0a0a] to-[#050505] -z-10" />
          <div className="fixed inset-0 -z-10" style={{
            background: 'radial-gradient(ellipse at 50% 30%, rgba(0, 128, 128, 0.08) 0%, transparent 60%)'
          }} />
        </>
      )}

      {/* Top Right Controls */}
      <div className="absolute top-4 right-4 flex items-center gap-3">
        <button
          onClick={() => {
            setHasSeenTour(false);
            setRunTourPhaseA(true);
          }}
          className={`flex items-center gap-2 px-3 py-2 text-sm font-medium transition-colors rounded-full border ${theme === 'dark'
            ? 'bg-black/40 border-white/10 text-gray-300 hover:text-white hover:bg-white/10'
            : 'bg-white border-gray-200 text-gray-600 hover:text-gray-900 hover:bg-gray-50 shadow-sm'
            }`}
        >
          <HelpCircle className="w-4 h-4" />
          <span className="hidden sm:inline">How to Use</span>
        </button>
        <ThemeSwitcher />
      </div>

      <div className="w-full max-w-3xl space-y-8">
        <div className="text-center space-y-4">
          <h1 className={`text-5xl lg:text-6xl font-bold tracking-tight ${theme === 'dark' ? 'text-white' : 'text-gray-900'}`}>
            The DROP Tax
          </h1>
          <p className={`text-xl font-medium tracking-wide ${theme === 'dark' ? 'text-gray-300' : 'text-gray-700'}`}>
            Understanding the 4 As behind drop outs
          </p>
          <p className={`text-sm tracking-normal ${theme === 'dark' ? 'text-gray-400' : 'text-gray-500'}`}>
            The 4 As - Availability, Accessibility, and Acceptance and Adherence
          </p>
        </div>

        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (suggestions.length > 0) {
              const drug = suggestions[0];
              handleSelectDrug(drug.id, drug.name, drug.indication);
            }
          }}
          className="relative"
        >
          <div className="relative">
            <Search className={`absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 ${theme === 'dark' ? 'text-gray-500' : 'text-gray-400'}`} />
            <Input
              data-testid="drug-search-input"
              type="text"
              placeholder="Enter Brand Name..."
              value={searchQuery}
              onChange={(e) => handleSearch(e.target.value)}
              className={`tour-search-input pl-12 pr-4 py-6 text-lg border-2 rounded-sm transition-all ${theme === 'dark'
                ? 'glass-input text-white placeholder:text-gray-500 focus:border-[#008080] focus:shadow-[0_0_20px_rgba(0,128,128,0.2)]'
                : 'bg-white border-gray-200 text-gray-900 placeholder:text-gray-400 focus:border-[#008080]'
                }`}
            />
          </div>

          {suggestions.length > 0 && (
            <div
              className={`absolute z-10 w-full mt-2 rounded-sm shadow-lg overflow-hidden ${theme === 'dark' ? 'glass-card' : 'bg-white border-2 border-gray-200'
                }`}
              data-testid="search-suggestions"
            >
              {suggestions.map((drug) => (
                <button
                  key={drug.id}
                  data-testid={`drug-suggestion-${drug.id}`}
                  onClick={() => handleSelectDrug(drug.id, drug.name, drug.indication)}
                  disabled={isLoading}
                  className={`w-full px-4 py-3 text-left transition-all border-b last:border-b-0 disabled:opacity-50 ${theme === 'dark'
                    ? 'hover:bg-white/5 border-white/10'
                    : 'hover:bg-gray-50 border-gray-100'
                    }`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex-1">
                      <div className={`font-semibold ${theme === 'dark' ? 'text-white' : 'text-gray-900'}`}>{drug.name}</div>
                      <div className={`text-sm ${theme === 'dark' ? 'text-gray-400' : 'text-gray-500'}`}>{drug.indication}</div>
                    </div>
                    {drug.is_dynamic && (
                      <span className="ml-2 px-2 py-1 text-xs bg-[#008080] text-white rounded">
                        Search
                      </span>
                    )}
                  </div>
                </button>
              ))}
            </div>
          )}

          {/* "Did you mean?" suggestion banner */}
          {didYouMean && (
            <div
              className={`absolute z-20 mt-1 w-full shadow-xl rounded-lg px-4 py-2.5 cursor-pointer transition-colors ${theme === 'dark'
                ? 'glass-card border-white/10 hover:bg-white/5'
                : 'bg-white border-2 border-[#008080]/20 hover:bg-gray-50'}`}
              style={{ top: suggestions.length > 0 ? `${suggestions.length * 48 + 56}px` : '100%' }}
              onClick={() => {
                setDidYouMean(null);
                handleSearch(didYouMean);
              }}
            >
              <span className={`text-xs ${theme === 'dark' ? 'text-gray-400' : 'text-gray-500'}`}>Did you mean: </span>
              <span className="text-sm font-bold text-[#008080] hover:underline">{didYouMean}</span>
              <span className={`text-xs ${theme === 'dark' ? 'text-gray-400' : 'text-gray-500'}`}> ?</span>
            </div>
          )}
        </form>

        <div className={`text-center text-sm ${theme === 'dark' ? 'text-gray-500' : 'text-gray-500'}`}>
          <p className="mb-4">Enter any drug name to begin real-time strategic analysis</p>
          <p className={`text-xs ${theme === 'dark' ? 'text-gray-600' : 'text-gray-400'}`}>
            Powered by real-time web intelligence - no hardcoded data
          </p>
        </div>
      </div>

      {/* Indication Selection Dialog */}
      <IndicationSelectDialog
        open={showIndicationDialog}
        onOpenChange={(open) => {
          setShowIndicationDialog(open);
          if (!open) {
            setPendingDrug(null);
            setAvailableIndications([]);
          }
        }}
        drugName={pendingDrug?.name || ''}
        indications={availableIndications}
        onSelectIndication={handleIndicationSelect}
        isLoading={isLoading}
      />

      {/* Analysis Loading Overlay */}
      <AnalysisLoadingOverlay
        isVisible={isLoading}
        drugName={loadingDrugName}
      />

      {/* Driver.js popovers are appended to document body */}
    </div>
  );
}
