import React from 'react';
import { Scale } from 'lucide-react'; // Using Scale as a neutral balance icon

export function LogisticalBurdenCard({ assetName, competitorName, logisticalData }) {
    if (!logisticalData) return null;

    const { our_asset, competitor, objective_insight } = logisticalData;

    return (
        <div className="flex flex-col h-full bg-[#111827] border border-[#27272A] rounded-sm overflow-hidden" data-testid="logistical-burden-card">

            {/* Header */}
            <div className="p-4 border-b border-[#27272A]">
                <h3 className="text-sm font-data font-bold tracking-widest text-[#F3F4F6] uppercase">
                    LOGISTICAL BURDEN & QoL
                </h3>
            </div>

            {/* Top Section (The Split) */}
            <div className="flex flex-1 relative">
                {/* Left Side: Asset */}
                <div className="flex-1 p-5 border-r border-[#27272A] flex flex-col justify-center gap-4">
                    <div className="flex items-center gap-2">
                        <div className="w-2.5 h-2.5 rounded-full bg-[#008080]" />
                        <span className="font-data font-bold text-[#F3F4F6] text-lg">{assetName}</span>
                    </div>

                    <div className="space-y-3">
                        <div>
                            <div className="text-[10px] uppercase tracking-wider text-[#9CA3AF] mb-1">REGIMEN & ROUTE</div>
                            <div className="font-medium text-[#F3F4F6]">
                                {our_asset.route} <span className="text-[#008080] ml-1">{our_asset.regimen}</span>
                            </div>
                        </div>

                        <div>
                            <div className="text-[10px] uppercase tracking-wider text-[#9CA3AF] mb-1">CARE SETTING</div>
                            <div className="font-medium text-[#F3F4F6]">{our_asset.setting}</div>
                        </div>
                    </div>
                </div>

                {/* Right Side: Competitor */}
                <div className="flex-1 p-5 flex flex-col justify-center gap-4">
                    <div className="flex items-center gap-2">
                        <div className="w-2.5 h-2.5 rounded-full bg-slate-500" />
                        <span className="font-data font-bold text-[#F3F4F6] text-lg">{competitorName || 'Competitor'}</span>
                    </div>

                    <div className="space-y-3">
                        <div>
                            <div className="text-[10px] uppercase tracking-wider text-[#9CA3AF] mb-1">REGIMEN & ROUTE</div>
                            <div className="font-medium text-[#F3F4F6]">
                                {competitor.route} <span className="text-slate-400 ml-1">{competitor.regimen}</span>
                            </div>
                        </div>

                        <div>
                            <div className="text-[10px] uppercase tracking-wider text-[#9CA3AF] mb-1">CARE SETTING</div>
                            <div className="font-medium text-[#F3F4F6]">{competitor.setting}</div>
                        </div>
                    </div>
                </div>
            </div>

            {/* Bottom Section (The Insight Footer) */}
            <div className="bg-[#0B0F19] p-4 border-t border-[#27272A] flex gap-3 items-start">
                <Scale className="w-5 h-5 text-[#9CA3AF] shrink-0 mt-0.5" />
                <p className="text-sm text-[#9CA3AF] italic leading-relaxed">
                    {objective_insight}
                </p>
            </div>

        </div>
    );
}
