import React from 'react';
import { ResponsiveContainer, ComposedChart, CartesianGrid, XAxis, YAxis, Tooltip, Legend, Bar, ReferenceLine } from 'recharts';
import { Card, CardContent } from './ui/card';
import { Separator } from './ui/separator';
import { InfoTooltip } from './InfoTooltip';

export default function PatientCashFlow({ pricingModel, currencySymbol, theme = 'dark' }) {
    if (!pricingModel || !pricingModel.period_data) return null;

    const cycleChartData = pricingModel.period_data.map(c => ({
        name: `C${c.cycle}`,
        cycle: c.cycle,
        patient: c.patient_pay,
        insurer: c.insurer_pay,
        govt: c.govt_pay,
        effective: pricingModel.effective_monthly_cost,
        isFree: c.is_free_period
    }));

    const textColor = theme === 'dark' ? '#E5E5E5' : '#1A1A1A';
    const mutedColor = theme === 'dark' ? '#737373' : '#6B7280';
    const surfaceBg = theme === 'dark' ? '#121212' : '#FFFFFF';
    const borderColor = theme === 'dark' ? '#262626' : '#E5E5E5';
    const effectiveAvgColor = theme === 'dark' ? '#FFFFFF' : '#1A1A1A';

    return (
        <div className="space-y-6">
            {/* Header with Tooltip for clarity */}
            <div className="flex items-center gap-2 mb-2">
                <h3 className="text-xs font-bold uppercase tracking-widest" style={{ color: mutedColor }}>
                    Cycle View: Patient Cash Flow
                </h3>
                {pricingModel.effective_monthly_cost > 0 && (
                    <InfoTooltip content="Effective Avg: The average amount the patient actually pays out-of-pocket per treatment cycle, considering any financial assistance or free doses." />
                )}
            </div>

            <div style={{ height: '220px' }} data-testid="cycle-cost-chart">
                <ResponsiveContainer width="100%" height="100%">
                    <ComposedChart data={cycleChartData.slice(0, 6)}>
                        <CartesianGrid strokeDasharray="3 3" stroke={borderColor} opacity={0.3} />
                        <XAxis dataKey="name" stroke={mutedColor} tick={{ fill: mutedColor, fontSize: 11 }} />
                        <YAxis stroke={mutedColor} tick={{ fill: mutedColor, fontSize: 10 }} tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`} />
                        <Tooltip
                            contentStyle={{ background: surfaceBg, border: `1px solid ${borderColor}`, borderRadius: '4px' }}
                            labelStyle={{ color: textColor, fontFamily: 'JetBrains Mono' }}
                            formatter={(value, name) => [`${currencySymbol || pricingModel.currency_symbol || '$'}${value.toLocaleString()}`, name]}
                        />
                        <Legend />
                        <Bar dataKey="patient" stackId="a" name="Patient Pays" fill="#F87171" radius={[0, 0, 0, 0]} />
                        <Bar dataKey="subsidy" stackId="a" name="Manufacturer Subsidy" fill="#008080" fillOpacity={0.6} radius={[2, 2, 0, 0]} />
                        {pricingModel.annual_insurer_impact > 0 && (
                            <Bar dataKey="insurer" stackId="a" name="Insurer Pays" fill="#60A5FA" fillOpacity={0.4} radius={[2, 2, 0, 0]} />
                        )}
                        {pricingModel.annual_govt_impact > 0 && (
                            <Bar dataKey="govt" stackId="a" name="Govt Pays" fill="#34D399" radius={[2, 2, 0, 0]} />
                        )}
                        {pricingModel.effective_monthly_cost > 0 && (
                            <ReferenceLine
                                y={pricingModel.effective_monthly_cost}
                                stroke={effectiveAvgColor}
                                strokeWidth={2}
                                strokeDasharray="6 4"
                                label={{ value: 'Effective Avg', fill: effectiveAvgColor, fontSize: 10, fontWeight: 'bold' }}
                            />
                        )}
                    </ComposedChart>
                </ResponsiveContainer>
            </div>

            <Card className={`${theme === 'dark' ? 'glass-card' : 'bg-gray-50 border border-gray-200'} overflow-hidden`} data-testid="pricing-summary-card">
                <CardContent className="p-4 space-y-3 relative">
                    {theme === 'dark' && <div className="glass-gradient absolute inset-0 pointer-events-none" />}
                    <div className="relative z-10 space-y-3">
                        <div className="flex justify-between items-center">
                            <span className={`text-xs ${theme === 'dark' ? 'text-muted-foreground' : 'text-gray-500'}`}>Annual Patient OOP</span>
                            <span className="font-data text-[#F87171] font-bold" style={{ fontSize: '1.1rem' }}>
                                {currencySymbol || pricingModel.currency_symbol || '$'}{pricingModel.annual_oop_impact?.toLocaleString()}
                            </span>
                        </div>
                        {pricingModel.annual_insurer_impact > 0 && (
                            <>
                                <Separator style={{ backgroundColor: borderColor }} />
                                <div className="flex justify-between items-center">
                                    <span className={`text-xs ${theme === 'dark' ? 'text-muted-foreground' : 'text-gray-500'}`}>Payer Burden / Year</span>
                                    <span className="font-data text-[#60A5FA] font-bold">
                                        {currencySymbol || pricingModel.currency_symbol || '$'}{pricingModel.annual_insurer_impact?.toLocaleString()}
                                    </span>
                                </div>
                            </>
                        )}
                        {pricingModel.pap_scheme_applied && (
                            <div className="mt-2 pt-2 border-t" style={{ borderColor }}>
                                <div className="text-xs font-medium text-[#008080]">
                                    {pricingModel.pap_scheme_applied} model active
                                </div>
                            </div>
                        )}
                    </div>
                </CardContent>
            </Card>
        </div>
    );
}
