import React from 'react';
import { Card, CardContent } from './ui/card';
import { Badge } from './ui/badge';
import { AlertTriangle, TrendingUp, DollarSign, Target, CheckCircle2 } from 'lucide-react';
import { useApp } from '../context/AppContext';

export function StrategicBrief({ activeTab, pricingModel, selectedPayer, selectedDrug, calculationResults }) {
    const { theme, selectedRegion } = useApp();

    // Guard clauses
    if (!pricingModel || !calculationResults || !selectedDrug || !selectedRegion) return null;

    // Extract necessary data points
    const drugName = selectedDrug.name;
    const regionName = selectedRegion.name;
    const competitorName = selectedDrug.competitor_name?.split(' ')[0] || 'Competitor';
    const currentYear = new Date().getFullYear(); // Assuming 2026 based on context
    const sourceYear = calculationResults.source_year || currentYear;
    const isDataStale = (currentYear - sourceYear) > 2;

    // 1. Triangulated Pricing Logic
    // Hierarchy: 1. Big 4 Reports -> 2. TPA Benchmarks -> 3. Regional Peer Proxy
    let unitCostSourceText = "TPA Benchmarks";
    if (calculationResults.data_source === 'big4') {
        unitCostSourceText = "Big 4 Reports";
    } else if (pricingModel.is_price_estimated) {
        unitCostSourceText = "Regional Peer Proxy";
    }

    // Calculate some risk metrics to show in the 'Why'
    const riskWeightedCostIndex = calculationResults.drug_cost > 0
        ? (calculationResults.total_liability / calculationResults.drug_cost).toFixed(2)
        : 0;

    // 2. Dynamic Text Assembly based on Rules

    // The Takeaway
    // E.g., First-Mover Advantage in India vs Competitor.
    const advantageType = "First-Mover Advantage"; // Could be dynamic based on more context if available
    const takeawayText = `${drugName} ${advantageType} in ${regionName} vs ${competitorName}.`;

    // The Why
    // E.g., Triangulated data (TPA Benchmarks) shows 2.5x Risk-Weighted Cost exposure in Month 4.
    const whyText = `Triangulated data (${unitCostSourceText}) shows ${riskWeightedCostIndex}x Risk-Weighted Cost exposure driven by hidden downstream liabilities.`;

    // The Action (Segment-Specific Logic)
    // Changes based on activeTab (module) OR selectedPayer
    let actionText = `Recommend strategic positioning for ${selectedPayer.replace('_', ' ').toUpperCase()}.`;
    let actionHighlight = "Action Required";

    if (activeTab === 'bridge') {
        actionText = `Focus on "Predictable EMI" to neutralize the catastrophic Month 4 spike seen in standard care.`;
        actionHighlight = "Predictable EMI";
    } else if (selectedPayer === 'cghs' || selectedPayer === 'echs' || selectedPayer === 'ayushman_bharat') {
        actionText = `Focus on "Formulary Inclusion" and "Tender Participation" as patient out-of-pocket (OOP) is zero.`;
        actionHighlight = "Formulary Focus";
    } else if (selectedPayer === 'oop') {
        actionText = `Focus on "Financial Burden" and "Adherence Risk." Highlight "Buy 1 Get 1" PAP to stabilize cash flow.`;
        actionHighlight = "Financial Burden";
    }

    // Theme support
    const textColor = theme === 'dark' ? 'text-[#E5E5E5]' : 'text-gray-900';
    const mutedColor = theme === 'dark' ? 'text-[#A3A3A3]' : 'text-gray-600';
    const highlightColor = theme === 'dark' ? 'text-[#008080]' : 'text-[#006666]';
    const borderColor = theme === 'dark' ? 'border-[#008080]/30' : 'border-[#008080]/20';
    const bgClass = theme === 'dark' ? 'bg-[#008080]/5' : 'bg-[#008080]/5';

    return (
        <Card className={`mb-6 border-l-4 border-l-[#008080] ${bgClass} ${borderColor} shadow-sm relative overflow-hidden`}>
            {/* Subtle shine effect */}
            <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-[#008080]/20 to-transparent" />

            <CardContent className="p-4 sm:p-5">
                <div className="flex flex-col md:flex-row gap-4 justify-between items-start md:items-stretch">

                    {/* Left Column: Takeaway & Why */}
                    <div className="flex-1 space-y-3">
                        <div>
                            <div className="flex items-center gap-2 mb-1">
                                <Target className={`w-4 h-4 ${highlightColor}`} />
                                <span className={`text-[10px] font-bold uppercase tracking-wider ${highlightColor}`}>Strategic Insight</span>
                            </div>
                            <h3 className={`text-base md:text-lg font-data font-semibold ${textColor} leading-tight`}>
                                {takeawayText}
                            </h3>
                        </div>

                        <div className={`text-sm ${mutedColor} leading-snug flex items-start gap-2`}>
                            <TrendingUp className="w-4 h-4 mt-0.5 opacity-70 shrink-0" />
                            <p>
                                <span className="font-semibold" style={{ color: theme === 'dark' ? '#D4D4D4' : '#4B5563' }}>The Why: </span>
                                {whyText}
                            </p>
                        </div>
                    </div>

                    {/* Middle/Right Column: Action & Meta */}
                    <div className="flex-1 md:max-w-md w-full flex flex-col justify-between pt-2 md:pt-0 border-t md:border-t-0 md:border-l border-white/10 md:pl-5">
                        <div>
                            <div className={`text-sm font-medium ${textColor} mb-2 flex items-start gap-2`}>
                                <CheckCircle2 className={`w-4 h-4 mt-0.5 ${highlightColor} shrink-0`} />
                                <span>
                                    <span className="font-semibold" style={{ color: theme === 'dark' ? '#D4D4D4' : '#4B5563' }}>Action: </span>
                                    {actionText}
                                </span>
                            </div>
                        </div>

                        <div className="flex items-center gap-2 mt-3 pt-3 border-t border-white/5">
                            <Badge variant="outline" className={`text-[10px] bg-transparent ${theme === 'dark' ? 'border-gray-700 text-gray-400' : 'border-gray-200 text-gray-500'}`}>
                                Focus: {actionHighlight}
                            </Badge>

                            <Badge variant="outline" className={`text-[10px] bg-transparent ${theme === 'dark' ? 'border-[#008080]/30 text-[#008080]' : 'border-[#008080]/20 text-[#006666]'}`}>
                                Unit Source: {unitCostSourceText}
                            </Badge>

                            {isDataStale && (
                                <Badge variant="destructive" className="text-[10px] bg-red-500/20 text-red-500 border-red-500/30 flex items-center gap-1">
                                    <AlertTriangle className="w-3 h-3" /> Data Stale ({sourceYear})
                                </Badge>
                            )}
                        </div>
                    </div>

                </div>
            </CardContent>
        </Card>
    );
}
