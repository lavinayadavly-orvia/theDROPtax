import React from 'react';

export function LogisticalBurdenSnippet({ assetName, competitorName, logisticalData }) {
    if (!logisticalData) return null;

    const { our_asset, competitor } = logisticalData;

    return (
        <div className="space-y-3 mt-6" data-testid="logistical-burden-snippet">
            <div className="text-xs uppercase tracking-widest text-[#9CA3AF] mb-2">LOGISTICAL PROFILES</div>
            <div className="bg-[#111827] border border-[#27272A] rounded-sm p-3">
                {/* Asset Row */}
                <div className="flex items-center gap-2 mb-3">
                    <div className="w-2 h-2 rounded-full bg-[#008080]" />
                    <span className="text-sm font-medium text-[#F3F4F6] truncate max-w-[120px]" title={assetName}>
                        {assetName}:
                    </span>
                    <span className="ml-auto border border-[#008080]/30 text-[#008080] rounded px-1.5 py-0.5 whitespace-nowrap text-xs bg-[#008080]/5">
                        {our_asset.route} {our_asset.regimen}
                    </span>
                    <span className="text-[#9CA3AF] text-xs whitespace-nowrap">({our_asset.setting})</span>
                </div>

                {/* Competitor Row */}
                <div className="flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full bg-slate-500" />
                    <span className="text-sm font-medium text-[#F3F4F6] truncate max-w-[120px]" title={competitorName || 'Competitor'}>
                        {competitorName || 'Competitor'}:
                    </span>
                    <span className="ml-auto border border-slate-500/30 text-slate-400 rounded px-1.5 py-0.5 whitespace-nowrap text-xs bg-slate-500/5">
                        {competitor.route} {competitor.regimen}
                    </span>
                    <span className="text-[#9CA3AF] text-xs whitespace-nowrap">({competitor.setting})</span>
                </div>
            </div>
        </div>
    );
}
