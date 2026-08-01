import React from 'react';
import {
    BarChart,
    Bar,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    Legend,
    ReferenceLine,
    ResponsiveContainer,
    LabelList,
    Cell,
} from 'recharts';
import { TrendingDown, ShieldCheck, Activity } from 'lucide-react';
import { useApp } from '../context/AppContext';

// ─── Color tokens ────────────────────────────────────────────────────────────
const getColors = (isDark) => ({
    assetBase: '#0EA5E9',        // Accessible Teal
    competitorBase: '#94A3B8',   // Muted Silver
    adverseEvent: '#EF4444',         // Warning Red
    relapse: '#F97316',          // Orange — differentiate relapse from AE
    netSavings: '#22C55E',       // Green — savings indicator
    border: isDark ? '#27272A' : '#E4E4E7',
    surface: isDark ? '#18181B' : '#FAFAFA',
    bg: isDark ? '#09090B' : '#FFFFFF',
    textPrimary: isDark ? '#F3F4F6' : '#18181B',
    textMuted: isDark ? '#71717A' : '#52525B', // readable on light and dark
});

// Currency formatter
const fmt = (val, symbol = '') =>
    `${symbol}${Math.abs(val) >= 1000
        ? `${(Math.abs(val) / 1000).toFixed(0)}k`
        : Math.abs(val).toLocaleString()}`;

// ─── Custom Tooltip ──────────────────────────────────────────────────────────
const BridgeTooltip = ({ active, payload, label, currencySymbol, colors }) => {
    if (!active || !payload?.length) return null;
    const total = payload.reduce((s, p) => s + (p.value || 0), 0);
    return (
        <div
            style={{
                background: colors.surface,
                border: `1px solid ${colors.border}`,
                borderRadius: 6,
                padding: '12px 16px',
                fontFamily: 'JetBrains Mono, monospace',
                minWidth: 220,
                boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)'
            }}
        >
            <p style={{ color: colors.textMuted, fontSize: 11, marginBottom: 8, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                {label}
            </p>
            {payload.map((p) => (
                <div key={p.name} style={{ display: 'flex', justifyContent: 'space-between', gap: 24, marginBottom: 4 }}>
                    <span style={{ color: p.fill, fontSize: 12 }}>{p.name}</span>
                    <span style={{ color: colors.textPrimary, fontSize: 12 }}>
                        {currencySymbol}{p.value?.toLocaleString()}
                    </span>
                </div>
            ))}
            <div style={{ borderTop: `1px solid ${colors.border}`, marginTop: 8, paddingTop: 8, display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: colors.textMuted, fontSize: 12 }}>Total</span>
                <span style={{ color: colors.textPrimary, fontSize: 13, fontWeight: 700 }}>
                    {currencySymbol}{total.toLocaleString()}
                </span>
            </div>
        </div>
    );
};

// ─── Narrative Card ──────────────────────────────────────────────────────────
const NarrativeCard = ({ icon: Icon, label, value, color, colors }) => (
    <div
        style={{
            background: colors.surface,
            border: `1px solid ${colors.border}`,
            borderRadius: 8,
            padding: '20px 24px',
            flex: 1,
            minWidth: 0,
        }}
    >
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
            <div style={{ width: 28, height: 28, borderRadius: 6, background: `${color}20`, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <Icon size={14} style={{ color }} />
            </div>
            <span style={{ color: colors.textMuted, fontSize: 10, textTransform: 'uppercase', letterSpacing: '0.08em', fontFamily: 'JetBrains Mono, monospace' }}>
                {label}
            </span>
        </div>
        <p style={{ color: colors.textPrimary, fontSize: 13, lineHeight: 1.6, margin: 0 }}>
            {value}
        </p>
    </div>
);

// ─── Main Component ──────────────────────────────────────────────────────────
export function ValueBridge({ valueBridgeData, currencySymbol = '' }) {
    const { theme } = useApp();
    const isDark = theme === 'dark';
    const colors = getColors(isDark);

    // Empty state
    if (!valueBridgeData?.value_bridge_data) {
        return (
            <div style={{ background: colors.bg, border: `1px solid ${colors.border}`, borderRadius: 8, padding: 32, textAlign: 'center' }}>
                <p style={{ color: colors.textMuted, fontFamily: 'JetBrains Mono, monospace', fontSize: 13 }}>
                    Total Cost of Care data unavailable for this region / drug combination.
                </p>
            </div>
        );
    }

    const { competitor, our_asset } = valueBridgeData.value_bridge_data;
    const narrative = valueBridgeData.simple_value_narrative || {};

    // Net savings = competitor total − our asset total
    const netSavings = competitor.total_cost - our_asset.total_cost;
    const competitorTotal = competitor.total_cost;
    const assetTotal = our_asset.total_cost;

    // Build chart data — stacked bars side by side
    const chartData = [
        {
            name: competitor.name,
            'Base Cost': competitor.base_cost,
            'Adverse Event Cost': competitor.adverse_event_cost_ae,
            'Treatment Failure Cost': competitor.treatment_failure_cost,
            isCompetitor: true,
        },
        {
            name: our_asset.name,
            'Base Cost': our_asset.base_cost,
            'Adverse Event Cost': our_asset.adverse_event_cost_ae,
            'Treatment Failure Cost': our_asset.treatment_failure_cost,
            isCompetitor: false,
        },
    ];

    const yMax = Math.ceil(Math.max(competitorTotal, assetTotal) * 1.18 / 1000) * 1000;

    return (
        <div style={{ background: colors.bg, borderRadius: 12, overflow: 'hidden' }}>
            {/* ── Header ── */}
            <div style={{ padding: '20px 24px 0' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12 }}>
                    <div>
                        <h3 style={{ color: colors.textPrimary, fontFamily: 'JetBrains Mono, monospace', fontSize: 14, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.1em', margin: 0 }}>
                            Total Cost of Care — Value Bridge
                        </h3>
                        <p style={{ color: colors.textMuted, fontSize: 12, marginTop: 4, marginBottom: 0 }}>
                            Stacked true-cost comparison including adverse-event and treatment-failure costs
                        </p>
                    </div>
                    {netSavings > 0 && (
                        <div style={{ background: '#22C55E18', border: `1px solid #22C55E40`, borderRadius: 8, padding: '8px 16px', display: 'flex', alignItems: 'center', gap: 8 }}>
                            <TrendingDown size={16} style={{ color: colors.netSavings }} />
                            <span style={{ color: colors.netSavings, fontFamily: 'JetBrains Mono, monospace', fontSize: 13, fontWeight: 700 }}>
                                Net Saving: {currencySymbol}{netSavings.toLocaleString()}
                            </span>
                        </div>
                    )}
                </div>
            </div>

            {/* ── Chart ── */}
            <div style={{ height: 380, padding: '16px 8px 0' }}>
                <ResponsiveContainer width="100%" height="100%">
                    <BarChart
                        data={chartData}
                        margin={{ top: 20, right: 40, left: 10, bottom: 10 }}
                        barCategoryGap="35%"
                    >
                        <CartesianGrid strokeDasharray="3 3" stroke={colors.border} opacity={1} vertical={false} />
                        <XAxis
                            dataKey="name"
                            tick={{ fill: colors.textMuted, fontSize: 13, fontFamily: 'JetBrains Mono, monospace' }}
                            axisLine={false}
                            tickLine={false}
                        />
                        <YAxis
                            domain={[0, yMax]}
                            tickFormatter={(v) => fmt(v, currencySymbol)}
                            tick={{ fill: colors.textMuted, fontSize: 11, fontFamily: 'JetBrains Mono, monospace' }}
                            axisLine={false}
                            tickLine={false}
                            width={70}
                        />
                        <Tooltip
                            content={<BridgeTooltip currencySymbol={currencySymbol} colors={colors} />}
                            cursor={{ fill: isDark ? 'rgba(255,255,255,0.03)' : 'rgba(0,0,0,0.03)' }}
                        />
                        <Legend
                            wrapperStyle={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 11, paddingTop: 12 }}
                            formatter={(value) => <span style={{ color: colors.textMuted }}>{value}</span>}
                        />

                        {/* Net Savings connector line */}
                        {netSavings > 0 && (
                            <ReferenceLine
                                y={competitorTotal}
                                stroke={colors.netSavings}
                                strokeDasharray="6 3"
                                strokeWidth={1.5}
                                label={{
                                    value: `← Net saving ${currencySymbol}${netSavings.toLocaleString()}`,
                                    fill: colors.netSavings,
                                    fontSize: 11,
                                    fontFamily: 'JetBrains Mono, monospace',
                                    position: 'right',
                                }}
                            />
                        )}

                        {/* Base Cost — color per bar */}
                        <Bar dataKey="Base Cost" stackId="stack" fill={colors.competitorBase} radius={[0, 0, 4, 4]}>
                            {chartData.map((entry) => (
                                <Cell
                                    key={entry.name}
                                    fill={entry.isCompetitor ? colors.competitorBase : colors.assetBase}
                                />
                            ))}
                        </Bar>

                        {/* Adverse Event Cost */}
                        <Bar dataKey="Adverse Event Cost" stackId="stack" fill={colors.adverseEvent} />

                        {/* Failure/Relapse Tax */}
                        <Bar dataKey="Treatment Failure Cost" stackId="stack" fill={colors.relapse} radius={[4, 4, 0, 0]}>
                            <LabelList
                                dataKey={(entry) => entry['Base Cost'] + entry['Adverse Event Cost'] + entry['Treatment Failure Cost']}
                                position="top"
                                formatter={(v) => `${currencySymbol}${fmt(v)}`}
                                style={{ fill: colors.textPrimary, fontSize: 12, fontFamily: 'JetBrains Mono, monospace', fontWeight: 700 }}
                            />
                        </Bar>
                    </BarChart>
                </ResponsiveContainer>
            </div>

            {/* ── 3-Column Narrative Panel ── */}
            {(narrative.headline || narrative.safety_value || narrative.system_value) && (
                <div style={{ padding: '20px 24px 24px' }}>
                    <div style={{ borderTop: `1px solid ${colors.border}`, paddingTop: 20 }}>
                        {narrative.headline && (
                            <p style={{ color: colors.textPrimary, fontSize: 18, fontWeight: 700, fontFamily: 'JetBrains Mono, monospace', marginBottom: 16, marginTop: 0, letterSpacing: '-0.01em' }}>
                                "{narrative.headline}"
                            </p>
                        )}
                        <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
                            {narrative.safety_value && (
                                <NarrativeCard
                                    icon={ShieldCheck}
                                    label="Safety Value"
                                    value={narrative.safety_value}
                                    color={colors.assetBase}
                                    colors={colors}
                                />
                            )}
                            {narrative.system_value && (
                                <NarrativeCard
                                    icon={Activity}
                                    label="System Value"
                                    value={narrative.system_value}
                                    color={colors.netSavings}
                                    colors={colors}
                                />
                            )}
                            {netSavings > 0 && (
                                <NarrativeCard
                                    icon={TrendingDown}
                                    label="Net Economic Verdict"
                                    value={`At ${currencySymbol}${assetTotal.toLocaleString()} total cost vs ${currencySymbol}${competitorTotal.toLocaleString()} for the comparator — the system saves ${currencySymbol}${netSavings.toLocaleString()} per patient episode when accounting for all hidden taxes.`}
                                    color={colors.netSavings}
                                    colors={colors}
                                />
                            )}
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

