import React, { useRef } from 'react';
import { useReactToPrint } from 'react-to-print';
import { X, Download, ShieldCheck, BarChart2, AlertCircle } from 'lucide-react';
import { Button } from './ui/button';
import {
    ResponsiveContainer,
    BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
    ReferenceLine,
    ComposedChart,
} from 'recharts';
import { useApp } from '../context/AppContext';

// ─── Light-mode palette (PDF-optimised) ─────────────────────────────────────
const LIGHT = {
    bg: '#FFFFFF',
    pageBg: '#F3F4F6',
    text: '#111827',
    muted: '#6B7280',
    border: '#E5E7EB',
    accent: '#1D4ED8',
    teal: '#0F766E',
    red: '#DC2626',
    amber: '#D97706',
    grid: '#F3F4F6',
    barAsset: '#0F766E',
    barCompetitor: '#DC2626',
    barBase: '#1D4ED8',
    barAdverseEvent: '#D97706',
    barFailure: '#7C3AED',
    barSubsidy: '#0F766E',
    barPatient: '#DC2626',
    notRun: '#F9FAFB',
    notRunBorder: '#E5E7EB',
    notRunText: '#9CA3AF',
};

// ─── "Not Run" placeholder ────────────────────────────────────────────────────
function NotRunBlock() {
    return (
        <div
            className="flex items-center gap-3 px-5 py-4 rounded"
            style={{ background: LIGHT.notRun, border: `1px dashed ${LIGHT.notRunBorder}` }}
        >
            <AlertCircle className="w-4 h-4 shrink-0" style={{ color: LIGHT.notRunText }} />
            <p className="text-sm italic" style={{ color: LIGHT.notRunText }}>
                Analysis not run by the user.
            </p>
        </div>
    );
}

// ─── Section wrapper ─────────────────────────────────────────────────────────
function ReportSection({ number, title, icon: Icon, children, notRun = false }) {
    return (
        <section className="chart-section space-y-4">
            <div className="flex items-center gap-3 pb-2" style={{ borderBottom: `1px solid ${LIGHT.border}` }}>
                {Icon && <Icon className="w-4 h-4 shrink-0" style={{ color: LIGHT.accent }} />}
                <span className="font-mono text-xs font-bold uppercase tracking-widest" style={{ color: LIGHT.accent }}>
                    {number}.
                </span>
                <h2 className="font-serif text-base font-bold" style={{ color: LIGHT.text }}>{title}</h2>
            </div>
            {notRun ? <NotRunBlock /> : children}
        </section>
    );
}

// ─── Value Bridge chart ───────────────────────────────────────────────────────
function ReportValueBridge({ data, currencySymbol }) {
    return (
        <div style={{ width: '100%', height: 280 }}>
            <ResponsiveContainer width="100%" height={280}>
                <BarChart data={data} margin={{ top: 8, right: 24, left: 24, bottom: 8 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke={LIGHT.grid} />
                    <XAxis dataKey="category" tick={{ fill: LIGHT.text, fontSize: 12 }} />
                    <YAxis tickFormatter={v => `${currencySymbol}${(v / 1000).toFixed(0)}k`} tick={{ fill: LIGHT.muted, fontSize: 11 }} />
                    <Tooltip formatter={(v, name) => [`${currencySymbol}${v.toLocaleString('en-US')}`, name]}
                        contentStyle={{ background: LIGHT.bg, border: `1px solid ${LIGHT.border}`, color: LIGHT.text }} />
                    <Legend wrapperStyle={{ color: LIGHT.text, fontSize: 12 }} />
                    <Bar isAnimationActive={false} dataKey="base_cost" name="Base Cost" stackId="a" fill={LIGHT.barBase} />
                    <Bar isAnimationActive={false} dataKey="adverse_event_cost" name="Adverse Event Cost" stackId="a" fill={LIGHT.barAdverseEvent} />
                    <Bar isAnimationActive={false} dataKey="treatment_failure_cost" name="Treatment Failure Cost" stackId="a" fill={LIGHT.barFailure} radius={[4, 4, 0, 0]} />
                </BarChart>
            </ResponsiveContainer>
        </div>
    );
}

// ─── Patient Cash Flow chart ──────────────────────────────────────────────────
function ReportCashFlow({ data, currencySymbol }) {
    const periods = data?.periods || [];
    const avgPays = periods.length ? periods.reduce((s, c) => s + (c.patient_pay || 0), 0) / periods.length : 0;
    return (
        <div style={{ width: '100%', height: 260 }}>
            <ResponsiveContainer width="100%" height={260}>
                <ComposedChart data={periods} margin={{ top: 8, right: 24, left: 24, bottom: 8 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke={LIGHT.grid} />
                    <XAxis dataKey="period" tick={{ fill: LIGHT.text, fontSize: 12 }} />
                    <YAxis tickFormatter={v => `${currencySymbol}${(v / 1000).toFixed(0)}k`} tick={{ fill: LIGHT.muted, fontSize: 11 }} />
                    <Tooltip formatter={(v, name) => [`${currencySymbol}${v.toLocaleString('en-US')}`, name]}
                        contentStyle={{ background: LIGHT.bg, border: `1px solid ${LIGHT.border}`, color: LIGHT.text }} />
                    <Legend wrapperStyle={{ color: LIGHT.text, fontSize: 12 }} />
                    <Bar isAnimationActive={false} dataKey="subsidy" name="Manufacturer Subsidy" fill={LIGHT.barSubsidy} />
                    <Bar isAnimationActive={false} dataKey="patient_pay" name="Patient Pays" fill={LIGHT.barPatient} radius={[4, 4, 0, 0]} />
                    {avgPays > 0 && (
                        <ReferenceLine y={avgPays} stroke={LIGHT.teal} strokeDasharray="6 3"
                            label={{ value: 'Effective Avg', position: 'insideTopRight', fill: LIGHT.teal, fontSize: 11 }} />
                    )}
                </ComposedChart>
            </ResponsiveContainer>
        </div>
    );
}

// ─── Competitor Thunderdome table ─────────────────────────────────────────────
function ThunderdomeSection({ competitors, currencySymbol }) {
    return (
        <div className="overflow-x-auto">
            <table className="w-full text-sm border-collapse">
                <thead>
                    <tr style={{ borderBottom: `2px solid ${LIGHT.border}` }}>
                        <th className="text-left py-2 pr-4 font-semibold" style={{ color: LIGHT.text }}>Competitor</th>
                        <th className="text-right py-2 pr-4 font-semibold" style={{ color: LIGHT.text }}>Base Cost</th>
                        <th className="text-right py-2 pr-4 font-semibold" style={{ color: LIGHT.text }}>AE Mgmt Cost</th>
                        <th className="text-left py-2 font-semibold" style={{ color: LIGHT.text }}>Status</th>
                    </tr>
                </thead>
                <tbody>
                    {competitors.map((comp, i) => (
                        <tr key={i} style={{ borderBottom: `1px solid ${LIGHT.border}` }}>
                            <td className="py-2 pr-4 font-medium" style={{ color: LIGHT.text }}>{comp.name}</td>
                            <td className="py-2 pr-4 text-right font-mono" style={{ color: LIGHT.text }}>
                                {currencySymbol}{(comp.baseCost || 0).toLocaleString('en-US')}
                            </td>
                            <td className="py-2 pr-4 text-right font-mono" style={{ color: LIGHT.amber }}>
                                {currencySymbol}{(comp.aeMgmtCost || 0).toLocaleString('en-US')}
                            </td>
                            <td className="py-2">
                                {comp.isOffLabel
                                    ? <span className="text-xs px-2 py-0.5 rounded-full font-medium" style={{ background: '#FEF9C3', color: '#854D0E' }}>Off-Label</span>
                                    : <span className="text-xs px-2 py-0.5 rounded-full font-medium" style={{ background: '#D1FAE5', color: '#065F46' }}>Approved</span>
                                }
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}

// ─── PAP / Deal Architect summary ────────────────────────────────────────────
function DealArchitectSection({ data, currencySymbol }) {
    const pap = data.papRecommendation;
    if (!pap) return <NotRunBlock />;
    return (
        <div className="space-y-3">
            <div className="grid grid-cols-3 gap-3">
                {[
                    { label: 'PAP Scheme', value: pap.recommended_scheme || 'N/A' },
                    { label: 'Target ROI', value: `${data.targetROI}x` },
                    { label: 'Patient Wallet', value: `${currencySymbol}${(data.patientWallet || 0).toLocaleString('en-US')}/mo` },
                ].map(({ label, value }) => (
                    <div key={label} className="p-3 rounded" style={{ background: LIGHT.grid, border: `1px solid ${LIGHT.border}` }}>
                        <div className="text-xs uppercase tracking-wider mb-1" style={{ color: LIGHT.muted }}>{label}</div>
                        <div className="text-sm font-bold" style={{ color: LIGHT.text }}>{value}</div>
                    </div>
                ))}
            </div>
            {pap.rationale && (
                <p className="text-sm leading-relaxed" style={{ color: LIGHT.muted }}>{pap.rationale}</p>
            )}
        </div>
    );
}

// ─── Main Component ───────────────────────────────────────────────────────────
export default function IntelligenceReport({ onClose, selectedDrug, selectedRegion, calculationResults, pricingModel }) {
    const componentRef = useRef();
    const { warRoomSnapshot } = useApp();

    const handlePrint = useReactToPrint({
        contentRef: componentRef,
        documentTitle: `${selectedDrug?.name || 'Asset'}_Intelligence_Report`,
        onBeforeGetContent: () => new Promise((resolve) => setTimeout(resolve, 500)),
    });

    if (!selectedDrug) return null;

    const calcRes = calculationResults || {};
    const brain = calcRes.commercial_brain || {};
    const currencySymbol = selectedRegion?.currency_symbol || '₹';
    const dateStr = new Date().toLocaleDateString('en-IN', { year: 'numeric', month: 'long', day: 'numeric' });

    // Build value bridge data
    const valueBridgeData = [
        {
            category: selectedDrug.competitor_name || 'SoC',
            base_cost: calcRes.competitor_base_cost || 0,
            adverse_event_cost: brain.c_adverse_events || 0,
            treatment_failure_cost: brain.c_prod || 0,
        },
        {
            category: selectedDrug.name,
            base_cost: calcRes.drug_cost || 0,
            adverse_event_cost: brain.c_adverse_events ? Math.round(brain.c_adverse_events * 0.2) : 0,
            treatment_failure_cost: 0,
        },
    ];

    const cashFlowData = { pap_scheme: pricingModel?.pap_scheme_applied || 'Standard', periods: pricingModel?.period_data || [] };

    // Determine which sections have data
    const hasCalcData = !!calculationResults && !!calculationResults.drug_cost;
    const hasCashFlow = (pricingModel?.period_data?.length || 0) > 0;
    const hasThunderdome = (warRoomSnapshot?.thunderdome?.competitors?.length || 0) > 0;
    const hasDealArchitect = !!warRoomSnapshot?.dealArchitect;
    const hasTPP = !!warRoomSnapshot?.tppBenchmarker;
    const hasCliff = !!warRoomSnapshot?.cliff;
    const hasHEOR = !!warRoomSnapshot?.heor;

    return (
        <div className="fixed inset-0 z-[100] flex flex-col overflow-hidden" style={{ background: LIGHT.pageBg }}>
            {/* Sticky header */}
            <div className="bg-white border-b px-6 py-4 flex items-center justify-between shadow-sm z-10 shrink-0"
                style={{ borderColor: LIGHT.border }}>
                <div className="flex items-center gap-4">
                    <Button variant="ghost" size="sm" onClick={onClose} className="text-gray-500 hover:text-gray-900 hover:bg-gray-100">
                        <X className="w-5 h-5 mr-2" />Close Report
                    </Button>
                    <div className="hidden sm:block">
                        <h1 className="text-lg font-serif font-bold" style={{ color: LIGHT.text }}>Intelligence Report</h1>
                        <p className="text-xs uppercase tracking-wider" style={{ color: LIGHT.muted }}>{selectedDrug.name}</p>
                    </div>
                </div>
                <Button onClick={() => handlePrint()} className="text-white font-medium shadow-sm" style={{ background: LIGHT.accent }}>
                    <Download className="w-4 h-4 mr-2" />Download PDF
                </Button>
            </div>

            {/* Scrollable document */}
            <div className="flex-1 overflow-y-auto w-full p-4 sm:p-8 md:p-12 print:p-0">
                <div
                    ref={componentRef}
                    className="max-w-4xl mx-auto shadow-xl min-h-[1056px] p-10 md:p-16 print:shadow-none print:max-w-none print:w-full print:p-0 flex flex-col gap-10"
                    style={{ background: LIGHT.bg, color: LIGHT.text }}
                >
                    <style type="text/css" media="print">{`
                        @page { size: auto; margin: 15mm; }
                        .chart-section { page-break-inside: avoid; }
                        body { -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }
                    `}</style>

                    {/* ── Document Header ─────────────────── */}
                    <header style={{ borderBottom: `2px solid ${LIGHT.text}`, paddingBottom: '1.5rem' }}>
                        <div className="flex justify-between items-end mb-4">
                            <div>
                                <div className="font-serif text-4xl font-black tracking-tight leading-none mb-2" style={{ color: LIGHT.text }}>
                                    {selectedDrug.name}
                                </div>
                                <div className="text-lg font-medium" style={{ color: LIGHT.muted }}>{selectedDrug.indication}</div>
                            </div>
                            <div className="text-right">
                                <div className="text-sm font-bold uppercase tracking-widest mb-1" style={{ color: LIGHT.accent }}>The DROP Tax Intelligence</div>
                                <div className="text-sm" style={{ color: LIGHT.muted }}>{dateStr} | {selectedRegion?.name}</div>
                            </div>
                        </div>
                        <div className="grid grid-cols-3 gap-4 mt-6 pt-4" style={{ borderTop: `1px solid ${LIGHT.border}` }}>
                            {[
                                { label: 'Comparator', value: selectedDrug.competitor_name || 'Standard of Care' },
                                { label: 'Region', value: selectedRegion?.name },
                                { label: 'List Price / Period', value: `${currencySymbol}${calcRes.drug_cost != null ? calcRes.drug_cost.toLocaleString('en-US') : 'N/A'}` },
                            ].map(({ label, value }) => (
                                <div key={label}>
                                    <div className="text-xs uppercase tracking-wider mb-1" style={{ color: LIGHT.muted }}>{label}</div>
                                    <div className="text-sm font-medium" style={{ color: LIGHT.text }}>{value}</div>
                                </div>
                            ))}
                        </div>
                    </header>

                    {/* ── Section 1: Executive Summary ──── */}
                    <ReportSection number="1" title="Executive Summary" icon={ShieldCheck}>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-x-12 gap-y-6">
                            <article>
                                <h3 className="text-xs font-bold uppercase tracking-wider mb-2" style={{ color: LIGHT.text }}>Epidemiology &amp; Market Sizing</h3>
                                <p className="text-sm leading-relaxed" style={{ color: LIGHT.muted }}>
                                    {selectedDrug.epidemiology
                                        ? `In ${selectedRegion?.name}, the annual incidence of ${(selectedDrug.indication || '').toLowerCase()} is estimated at ${selectedDrug.epidemiology.base_incidence?.toLocaleString() || 'N/A'} patients. Addressable population: ~${selectedDrug.epidemiology.addressable_population?.toLocaleString() || 'N/A'} patients/year.`
                                        : 'Epidemiology data not available for this indication. Market sizing uses standard published incidence estimates.'}
                                </p>
                            </article>
                            <article>
                                <h3 className="text-xs font-bold uppercase tracking-wider mb-2" style={{ color: LIGHT.text }}>Logistical Burden &amp; QoL Impact</h3>
                                <p className="text-sm leading-relaxed" style={{ color: LIGHT.muted }}>
                                    {brain.logistics?.objective_insight || `${selectedDrug.name} offers a differentiated treatment profile. Refer to prescribing information for full logistical and quality-of-life comparative data.`}
                                </p>
                            </article>
                            <article>
                                <h3 className="text-xs font-bold uppercase tracking-wider mb-2" style={{ color: LIGHT.text }}>Value Narrative (Total Cost of Care)</h3>
                                <p className="text-sm leading-relaxed" style={{ color: LIGHT.muted }}>
                                    {calcRes.analysis?.recommendation?.message || `${selectedDrug.name} presents a calculated Risk-Weighted Cost Index of ${calcRes.drug_cost > 0 ? (calcRes.total_liability / calcRes.drug_cost).toFixed(2) : 'N/A'}x versus the standard of care.`}
                                </p>
                            </article>
                            <article>
                                <h3 className="text-xs font-bold uppercase tracking-wider mb-2" style={{ color: LIGHT.text }}>Strategic Pricing Overview</h3>
                                <p className="text-sm leading-relaxed" style={{ color: LIGHT.muted }}>
                                    {pricingModel
                                        ? `Under the current payer scenario, the effective monthly patient exposure is ${currencySymbol}${pricingModel.effective_monthly_cost?.toLocaleString() || 'N/A'} with PAP scheme: ${pricingModel.pap_scheme_applied || 'Standard'}.`
                                        : 'Pricing model not calculated for this session.'}
                                </p>
                            </article>
                        </div>
                    </ReportSection>

                    {/* ── Section 2: Total Cost of Care (Value Bridge) ── */}
                    <ReportSection number="2" title="Total Cost of Care — Value Bridge" icon={BarChart2} notRun={!hasCalcData}>
                        <p className="text-xs mb-4" style={{ color: LIGHT.muted }}>
                            Stacked breakdown: Acquisition + Adverse Event Cost + Treatment Failure Cost across both assets
                        </p>
                        <ReportValueBridge data={valueBridgeData} currencySymbol={currencySymbol} />
                        <div className="mt-4 grid grid-cols-2 gap-4">
                            {[
                                { label: 'Asset Acquisition Cost', value: `${currencySymbol}${(calcRes.drug_cost || 0).toLocaleString('en-US')}`, color: LIGHT.text },
                                { label: 'Competitor Unfunded Exposure', value: `${currencySymbol}${(calcRes.total_liability || 0).toLocaleString('en-US')}`, color: LIGHT.red },
                            ].map(({ label, value, color }) => (
                                <div key={label} className="p-3 rounded" style={{ background: LIGHT.grid, border: `1px solid ${LIGHT.border}` }}>
                                    <div className="text-xs uppercase tracking-wider mb-1" style={{ color: LIGHT.muted }}>{label}</div>
                                    <div className="text-base font-bold font-mono" style={{ color }}>{value}</div>
                                </div>
                            ))}
                        </div>
                    </ReportSection>

                    {/* ── Section 3: Patient Cash Flow ── */}
                    <ReportSection number="3" title="Treatment Period Economics — Patient Cash Flow" notRun={!hasCashFlow}>
                        {hasCashFlow && (
                            <>
                                <p className="text-xs mb-4" style={{ color: LIGHT.muted }}>
                                    Patient cash flows per period under the applied PAP scheme: <strong>{cashFlowData.pap_scheme}</strong>
                                </p>
                                <ReportCashFlow data={cashFlowData} currencySymbol={currencySymbol} />
                            </>
                        )}
                    </ReportSection>

                    {/* ── Section 4: Competitive Thunderdome ── */}
                    <ReportSection number="4" title="Competitive Thunderdome — Head-to-Head" notRun={!hasThunderdome}>
                        {hasThunderdome && (
                            <ThunderdomeSection
                                competitors={warRoomSnapshot.thunderdome.competitors}
                                currencySymbol={currencySymbol}
                            />
                        )}
                    </ReportSection>

                    {/* ── Section 5: Deal Architect / PAP ── */}
                    <ReportSection number="5" title="Deal Architect — PAP Recommendation" notRun={!hasDealArchitect}>
                        {hasDealArchitect && (
                            <DealArchitectSection data={warRoomSnapshot.dealArchitect} currencySymbol={currencySymbol} />
                        )}
                    </ReportSection>

                    {/* ── Section 6: TPP Benchmarker ── */}
                    <ReportSection number="6" title="TPP Benchmarker — Clinical Profile Comparison" notRun={!hasTPP}>
                        {hasTPP && (
                            <p className="text-sm leading-relaxed" style={{ color: LIGHT.muted }}>
                                {JSON.stringify(warRoomSnapshot.tppBenchmarker, null, 2)}
                            </p>
                        )}
                    </ReportSection>

                    {/* ── Section 7: Regional HEOR / Patient Bridge ── */}
                    <ReportSection number="7" title="Regional HEOR &amp; Patient Bridge" notRun={!hasHEOR}>
                        {hasHEOR && (
                            <div className="grid grid-cols-2 gap-4">
                                {[
                                    { label: 'Drug Base Cost', value: `${currencySymbol}${(warRoomSnapshot.heor.drug_base_cost || 0).toLocaleString('en-US')}` },
                                    { label: 'AE Management Cost', value: `${currencySymbol}${(warRoomSnapshot.heor.ae_management_cost || 0).toLocaleString('en-US')}` },
                                    { label: 'Standard of Care Cost', value: `${currencySymbol}${(warRoomSnapshot.heor.standard_of_care_cost || 0).toLocaleString('en-US')}` },
                                    { label: 'Region', value: selectedRegion?.name },
                                ].map(({ label, value }) => (
                                    <div key={label} className="p-3 rounded" style={{ background: LIGHT.grid, border: `1px solid ${LIGHT.border}` }}>
                                        <div className="text-xs uppercase tracking-wider mb-1" style={{ color: LIGHT.muted }}>{label}</div>
                                        <div className="text-sm font-bold" style={{ color: LIGHT.text }}>{value}</div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </ReportSection>

                    {/* ── Section 8: Methodology & Assumptions ── */}
                    <ReportSection number="8" title="Methodology & Assumptions" icon={AlertCircle}>
                        <div className="space-y-6">
                            {calcRes.calculation_transparency?.inputs && (
                                <div>
                                    <h3 className="text-xs font-bold uppercase tracking-wider mb-3" style={{ color: LIGHT.text }}>Clinical & Financial Inputs</h3>
                                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                        {Object.entries(calcRes.calculation_transparency.inputs).map(([key, input]) => (
                                            <div key={key} className="p-3 rounded border" style={{ background: LIGHT.bg, borderColor: LIGHT.border }}>
                                                <div className="flex justify-between items-start mb-1">
                                                    <span className="text-[10px] font-bold uppercase tracking-tighter" style={{ color: LIGHT.muted }}>
                                                        {key.replace(/_/g, ' ')}
                                                    </span>
                                                    {input.is_estimated && (
                                                        <span className="text-[9px] px-1.5 py-0.5 rounded bg-amber-100 text-amber-800 font-bold uppercase">Estimated</span>
                                                    )}
                                                </div>
                                                <div className="text-sm font-bold mb-1" style={{ color: LIGHT.text }}>
                                                    {typeof input.value === 'number' && key.includes('rate')
                                                        ? `${(input.value * 100).toFixed(1)}%`
                                                        : input.value?.toLocaleString() || 'N/A'}
                                                    {key.includes('months') ? ' months' : ''}
                                                </div>
                                                <div className="text-[10px] italic leading-tight" style={{ color: LIGHT.muted }}>
                                                    Source: {input.source || 'General Standard of Care'} ({input.method})
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {calcRes.calculation_transparency?.formulas && (
                                <div>
                                    <h3 className="text-xs font-bold uppercase tracking-wider mb-3" style={{ color: LIGHT.text }}>Core Calculation Formulas</h3>
                                    <div className="space-y-2">
                                        {Object.entries(calcRes.calculation_transparency.formulas).map(([key, formula]) => (
                                            <div key={key} className="p-3 rounded" style={{ background: LIGHT.grid }}>
                                                <div className="flex items-center gap-2 mb-1">
                                                    <span className="font-mono text-[10px] font-bold px-1.5 py-0.5 bg-white border rounded" style={{ color: LIGHT.accent }}>{key.toUpperCase()}</span>
                                                    <span className="text-[11px] font-bold" style={{ color: LIGHT.text }}>{formula.description}</span>
                                                </div>
                                                <div className="font-mono text-xs p-2 bg-white/50 rounded border border-dashed border-gray-300" style={{ color: LIGHT.accent }}>
                                                    {formula.formula}
                                                </div>
                                                <div className="text-[9px] mt-1 font-mono uppercase tracking-tighter" style={{ color: LIGHT.muted }}>
                                                    Current Branch: {formula.inputs}
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}

                            <p className="text-[10px] leading-relaxed italic" style={{ color: LIGHT.muted }}>
                                <strong>Disclaimer:</strong> This report is generated using a combination of live web-crawled clinical data and predefined regional economic factors. Costs are estimates based on standard dosing schedules and may vary by specific patient weight or localized hospital procurement prices.
                            </p>
                        </div>
                    </ReportSection>

                    {/* ── Footer ── */}
                    <footer className="mt-12 pt-4 text-center" style={{ borderTop: `1px solid ${LIGHT.border}` }}>
                        <p className="text-xs" style={{ color: LIGHT.muted }}>
                            Generated by The DROP Tax Intelligence | Strictly Confidential | Internal Strategy Eyes Only
                        </p>
                    </footer>
                </div>
            </div>
        </div>
    );
}
