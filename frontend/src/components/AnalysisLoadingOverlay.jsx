import React, { useState, useEffect } from 'react';
import { Loader2, Search, Database, Brain, BarChart3, CheckCircle } from 'lucide-react';

const ANALYSIS_STAGES = [
  { id: 'search', label: 'Searching databases...', icon: Search, duration: 1500 },
  { id: 'clinical', label: 'Extracting clinical endpoints...', icon: Database, duration: 2000 },
  { id: 'competitor', label: 'Analyzing competitor landscape...', icon: Brain, duration: 1500 },
  { id: 'calculate', label: 'Computing liability model...', icon: BarChart3, duration: 1000 },
  { id: 'complete', label: 'Analysis complete', icon: CheckCircle, duration: 500 }
];

export function AnalysisLoadingOverlay({ isVisible, drugName = 'drug' }) {
  const [currentStage, setCurrentStage] = useState(0);
  const [progress, setProgress] = useState(0);
  
  useEffect(() => {
    if (!isVisible) {
      setCurrentStage(0);
      setProgress(0);
      return;
    }
    
    let stageIndex = 0;
    let progressValue = 0;
    
    const advanceStage = () => {
      if (stageIndex < ANALYSIS_STAGES.length - 1) {
        stageIndex++;
        setCurrentStage(stageIndex);
      }
    };
    
    const progressInterval = setInterval(() => {
      progressValue += 2;
      setProgress(Math.min(progressValue, 95));
    }, 100);
    
    const stageTimers = ANALYSIS_STAGES.slice(0, -1).map((stage, idx) => {
      const delay = ANALYSIS_STAGES.slice(0, idx + 1).reduce((acc, s) => acc + s.duration, 0);
      return setTimeout(advanceStage, delay);
    });
    
    return () => {
      clearInterval(progressInterval);
      stageTimers.forEach(t => clearTimeout(t));
    };
  }, [isVisible]);
  
  if (!isVisible) return null;
  
  const CurrentIcon = ANALYSIS_STAGES[currentStage]?.icon || Search;
  
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm">
      <div className="glass-card p-8 rounded-lg max-w-md w-full mx-4 space-y-6">
        {/* Drug name */}
        <div className="text-center">
          <h2 className="text-2xl font-bold text-white mb-2">Analyzing {drugName}</h2>
          <p className="text-sm text-gray-400">Real-time web intelligence in progress</p>
        </div>
        
        {/* Progress bar */}
        <div className="space-y-2">
          <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
            <div 
              className="h-full bg-gradient-to-r from-[#008080] to-[#00A0A0] transition-all duration-300 ease-out"
              style={{ width: `${progress}%` }}
            />
          </div>
          <div className="flex justify-between text-xs text-gray-500">
            <span>{progress}%</span>
            <span>~5-10 seconds</span>
          </div>
        </div>
        
        {/* Current stage */}
        <div className="flex items-center justify-center gap-3 py-4">
          <div className="relative">
            <CurrentIcon className="w-6 h-6 text-[#008080]" />
            <Loader2 className="w-10 h-10 text-[#008080]/30 animate-spin absolute -top-2 -left-2" />
          </div>
          <span className="text-white font-medium">
            {ANALYSIS_STAGES[currentStage]?.label}
          </span>
        </div>
        
        {/* Stage indicators */}
        <div className="flex justify-center gap-2">
          {ANALYSIS_STAGES.slice(0, -1).map((stage, idx) => (
            <div 
              key={stage.id}
              className={`w-2 h-2 rounded-full transition-colors duration-300 ${
                idx <= currentStage ? 'bg-[#008080]' : 'bg-gray-700'
              }`}
            />
          ))}
        </div>
        
        {/* Info text */}
        <p className="text-xs text-center text-gray-500">
          Querying clinical trials, FDA labels, and market data...
        </p>
      </div>
    </div>
  );
}
