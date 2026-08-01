import React from 'react';
import { X, Search, Target, LayoutDashboard, Swords } from 'lucide-react';
import { useApp } from '../context/AppContext';

export const HowToUseModal = ({ open, onOpenChange }) => {
    const { theme } = useApp();

    if (!open) return null;

    return (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm custom-scrollbar">
            <div
                className={`relative w-full max-w-3xl rounded-xl shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-200 ${theme === 'dark'
                        ? 'bg-[#0a0a0a] border border-white/10 text-white shadow-[#008080]/10'
                        : 'bg-white border text-gray-900 border-gray-200'
                    }`}
            >
                {/* Header */}
                <div className={`flex items-center justify-between px-6 py-5 border-b ${theme === 'dark' ? 'border-white/10' : 'border-gray-100'}`}>
                    <div>
                        <h2 className="text-2xl font-bold tracking-tight">Welcome to The DROP Tax</h2>
                        <p className={`text-sm mt-1 ${theme === 'dark' ? 'text-gray-400' : 'text-gray-500'}`}>
                            Your Commercial Intelligence platform for Value-Based Access.
                        </p>
                    </div>
                    <button
                        onClick={() => onOpenChange(false)}
                        className={`p-2 transition-colors rounded-full ${theme === 'dark' ? 'hover:bg-white/10' : 'hover:bg-gray-100'}`}
                    >
                        <X className="w-5 h-5" />
                    </button>
                </div>

                {/* Content */}
                <div className="p-8 space-y-6">
                    <div className="grid gap-6 md:grid-cols-2">

                        {/* Step 1 */}
                        <div className={`p-5 rounded-xl border transition-all hover:shadow-lg ${theme === 'dark' ? 'bg-white/[0.02] border-white/10 hover:border-[#008080]/50' : 'bg-gray-50 border-gray-100 hover:border-[#008080]/30'}`}>
                            <div className="flex items-center gap-3 mb-3">
                                <div className="p-2.5 rounded-lg bg-[#008080]/20 text-[#008080]">
                                    <Search className="w-5 h-5" />
                                </div>
                                <h3 className="text-lg font-semibold">1. Search & Discover</h3>
                            </div>
                            <p className={`text-sm leading-relaxed ${theme === 'dark' ? 'text-gray-400' : 'text-gray-600'}`}>
                                Type any therapeutic asset (e.g., Semaglutide, Tirzepatide) into the main console.
                                Our intelligence engine will instantly locate relevant data.
                            </p>
                        </div>

                        {/* Step 2 */}
                        <div className={`p-5 rounded-xl border transition-all hover:shadow-lg ${theme === 'dark' ? 'bg-white/[0.02] border-white/10 hover:border-[#008080]/50' : 'bg-gray-50 border-gray-100 hover:border-[#008080]/30'}`}>
                            <div className="flex items-center gap-3 mb-3">
                                <div className="p-2.5 rounded-lg bg-[#008080]/20 text-[#008080]">
                                    <Target className="w-5 h-5" />
                                </div>
                                <h3 className="text-lg font-semibold">2. Select Indication</h3>
                            </div>
                            <p className={`text-sm leading-relaxed ${theme === 'dark' ? 'text-gray-400' : 'text-gray-600'}`}>
                                Choose specific disease areas (e.g., Heart Failure, Type 2 Diabetes) when prompted
                                to analyze precise, context-specific pricing and clinical data.
                            </p>
                        </div>

                        {/* Step 3 */}
                        <div className={`p-5 rounded-xl border transition-all hover:shadow-lg ${theme === 'dark' ? 'bg-white/[0.02] border-white/10 hover:border-[#008080]/50' : 'bg-gray-50 border-gray-100 hover:border-[#008080]/30'}`}>
                            <div className="flex items-center gap-3 mb-3">
                                <div className="p-2.5 rounded-lg bg-[#008080]/20 text-[#008080]">
                                    <LayoutDashboard className="w-5 h-5" />
                                </div>
                                <h3 className="text-lg font-semibold">3. Executive Dashboard</h3>
                            </div>
                            <p className={`text-sm leading-relaxed ${theme === 'dark' ? 'text-gray-400' : 'text-gray-600'}`}>
                                Review comprehensive regional pricing, access barriers, projected
                                liability exposure, and real-time threat intelligence.
                            </p>
                        </div>

                        {/* Step 4 */}
                        <div className={`p-5 rounded-xl border transition-all hover:shadow-lg ${theme === 'dark' ? 'bg-white/[0.02] border-white/10 hover:border-[#008080]/50' : 'bg-gray-50 border-gray-100 hover:border-[#008080]/30'}`}>
                            <div className="flex items-center gap-3 mb-3">
                                <div className="p-2.5 rounded-lg bg-[#008080]/20 text-[#008080]">
                                    <Swords className="w-5 h-5" />
                                </div>
                                <h3 className="text-lg font-semibold">4. Enter War Room</h3>
                            </div>
                            <p className={`text-sm leading-relaxed ${theme === 'dark' ? 'text-gray-400' : 'text-gray-600'}`}>
                                Access the strategic cockpit to simulate competitor scenarios,
                                calculate ICER metrics, and model Patient Assistance Programs (PAP).
                            </p>
                        </div>

                    </div>
                </div>

                {/* Footer */}
                <div className={`px-6 py-5 border-t flex justify-end items-center ${theme === 'dark' ? 'border-white/10 bg-black/40' : 'bg-gray-50 border-gray-100'}`}>
                    <button
                        onClick={() => onOpenChange(false)}
                        className="px-8 py-2.5 text-sm font-bold text-white transition-all rounded-md bg-[#008080] hover:bg-[#009999] hover:shadow-[0_0_15px_rgba(0,128,128,0.4)]"
                    >
                        Start Analyzing
                    </button>
                </div>
            </div>
        </div>
    );
};
