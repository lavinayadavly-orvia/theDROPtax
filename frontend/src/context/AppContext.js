import React, { createContext, useContext, useState, useEffect } from 'react';

const AppContext = createContext();

// Storage keys
const STORAGE_KEYS = {
  DRUG: 'droptax-selected-drug',
  REGION: 'droptax-selected-region',
  CALCULATION: 'droptax-calculation-results',
  THEME: 'droptax-theme',
  LAST_PATH: 'droptax-last-path',
  TOUR_SEEN: 'droptax-tour-seen'
};

export const useApp = () => {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error('useApp must be used within AppProvider');
  }
  return context;
};

// Helper to safely parse JSON from localStorage
const getStoredValue = (key, defaultValue) => {
  if (typeof window === 'undefined') return defaultValue;
  try {
    const stored = localStorage.getItem(key);
    return stored ? JSON.parse(stored) : defaultValue;
  } catch (e) {
    console.warn(`Failed to parse ${key} from localStorage:`, e);
    return defaultValue;
  }
};

export const AppProvider = ({ children }) => {
  // Restore state from localStorage on initial load
  const [selectedDrug, setSelectedDrugState] = useState(() =>
    getStoredValue(STORAGE_KEYS.DRUG, null)
  );

  const [selectedRegion, setSelectedRegionState] = useState(() =>
    getStoredValue(STORAGE_KEYS.REGION, {
      code: 'IN',
      currency_symbol: '₹',
      conversion_rate_from_inr: 1.0,
      name: 'India',
      currency: 'INR'
    })
  );

  const [calculationResults, setCalculationResultsState] = useState(() =>
    getStoredValue(STORAGE_KEYS.CALCULATION, null)
  );

  const [regions, setRegions] = useState([]);

  // Regulatory override state — persisted across dashboard/war-room navigation
  const [assetRegulatoryOverride, setAssetRegulatoryOverride] = useState('AI Auto-Detect');
  const [competitorRegulatoryOverride, setCompetitorRegulatoryOverride] = useState('AI Auto-Detect');

  // Shared competitors state (between War Room and Executive Dashboard features)
  const [customCompetitors, setCustomCompetitors] = useState([]);

  // War Room module results — session only (not persisted)
  // Each key is null until the user runs that module
  const [warRoomSnapshot, setWarRoomSnapshot] = useState({
    thunderdome: null,   // set when competitors are added / chart renders
    dealArchitect: null, // set when PAP recommendation is generated
    tppBenchmarker: null,// set when TPP comparison loads
    cliff: null,         // set when Discontinuation Cliff is enabled
    heor: null,          // set when HEOR regional data loads
  });

  // Theme state - default to dark (the "war room" aesthetic)
  const [theme, setTheme] = useState(() => {
    if (typeof window !== 'undefined') {
      return localStorage.getItem(STORAGE_KEYS.THEME) || 'dark';
    }
    return 'dark';
  });

  // Tour State Management
  const [hasSeenTour, setHasSeenTourState] = useState(() =>
    getStoredValue(STORAGE_KEYS.TOUR_SEEN, false)
  );
  const [runTourPhaseA, setRunTourPhaseA] = useState(false);
  const [runTourPhaseB, setRunTourPhaseB] = useState(false);
  const [runTourPhaseC, setRunTourPhaseC] = useState(false);

  // Wrapped setters that persist to localStorage
  const setSelectedDrug = (drug) => {
    setSelectedDrugState(drug);
    if (drug) {
      localStorage.setItem(STORAGE_KEYS.DRUG, JSON.stringify(drug));
    } else {
      localStorage.removeItem(STORAGE_KEYS.DRUG);
    }
  };

  const setSelectedRegion = (region) => {
    setSelectedRegionState(region);
    localStorage.setItem(STORAGE_KEYS.REGION, JSON.stringify(region));
  };

  const setCalculationResults = (results) => {
    setCalculationResultsState(results);
    if (results) {
      localStorage.setItem(STORAGE_KEYS.CALCULATION, JSON.stringify(results));
    } else {
      localStorage.removeItem(STORAGE_KEYS.CALCULATION);
    }
  };

  // Track last visited path for restoration
  const setLastPath = (path) => {
    localStorage.setItem(STORAGE_KEYS.LAST_PATH, path);
  };

  const getLastPath = () => {
    return localStorage.getItem(STORAGE_KEYS.LAST_PATH) || '/';
  };

  // Clear all session data (for explicit logout/reset)
  const clearSession = () => {
    setSelectedDrugState(null);
    setCalculationResultsState(null);
    localStorage.removeItem(STORAGE_KEYS.DRUG);
    localStorage.removeItem(STORAGE_KEYS.CALCULATION);
    localStorage.removeItem(STORAGE_KEYS.LAST_PATH);
  };

  // Apply theme to document
  useEffect(() => {
    const root = document.documentElement;
    if (theme === 'dark') {
      root.classList.add('dark');
    } else {
      root.classList.remove('dark');
    }
    localStorage.setItem(STORAGE_KEYS.THEME, theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme(prev => prev === 'dark' ? 'light' : 'dark');
  };

  const setHasSeenTour = (value) => {
    setHasSeenTourState(value);
    localStorage.setItem(STORAGE_KEYS.TOUR_SEEN, JSON.stringify(value));
  };

  const value = {
    selectedDrug,
    setSelectedDrug,
    selectedRegion,
    setSelectedRegion,
    calculationResults,
    setCalculationResults,
    regions,
    setRegions,
    theme,
    setTheme,
    toggleTheme,
    setLastPath,
    getLastPath,
    clearSession,
    assetRegulatoryOverride,
    setAssetRegulatoryOverride,
    competitorRegulatoryOverride,
    setCompetitorRegulatoryOverride,
    customCompetitors,
    setCustomCompetitors,
    warRoomSnapshot,
    setWarRoomSnapshot,
    hasSeenTour,
    setHasSeenTour,
    runTourPhaseA,
    setRunTourPhaseA,
    runTourPhaseB,
    setRunTourPhaseB,
    runTourPhaseC,
    setRunTourPhaseC
  };

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
};
