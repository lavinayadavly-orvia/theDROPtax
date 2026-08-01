import React, { useState } from 'react';
import { X, Briefcase, Stethoscope, FileText, Zap, Loader2, Activity } from 'lucide-react';

/**
 * StrategicModal — Premium dual-lens War Room Intelligence Briefing
 *
 * Props:
 *   open         {boolean}   — controls visibility
 *   onClose      {function}  — close handler
 *   briefing     {object}    — JSON payload from /strategic-briefing/generate
 *   isLoading    {boolean}   — show skeleton while fetching
 *   onLaunchWarRoom {function} — navigate to /war-room
 */
export function StrategicModal({ open, onClose, briefing, isLoading = false, onLaunchWarRoom }) {
    const [lens, setLens] = useState('boardroom'); // 'boardroom' | 'msl'

    if (!open) return null;

    const meta = briefing?.meta;
    const insights = briefing?.strategic_briefing || [];

    return (
        /* ── Overlay ── */
        <div
            className="fixed inset-0 z-[9999] flex items-center justify-center p-4"
            style={{ backdropFilter: 'blur(16px)', backgroundColor: 'rgba(0,0,0,0.72)' }}
            onClick={onClose}
        >
            <div
                className="relative w-full max-w-3xl max-h-[90vh] flex flex-col rounded-sm overflow-hidden"
                style={{
                    background: '#09090B',
                    border: '1px solid rgba(255,255,255,0.1)',
                    borderTop: '2px solid #0EA5E9',
                    boxShadow: '0 32px 80px rgba(0,0,0,0.8)',
                }}
                onClick={e => e.stopPropagation()}
            >

                {/* ── Header ── */}
                <header className="flex-shrink-0 px-6 pt-5 pb-4" style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
                    <div className="flex items-start justify-between gap-4">
                        <div className="flex-1 min-w-0">
                            {/* Eyebrow */}
                            <div className="text-[10px] font-mono uppercase tracking-[0.25em] mb-1"
                                style={{ color: 'rgba(0,200,200,0.7)' }}>
                                WAR ROOM INTELLIGENCE BRIEFING
                            </div>
                            {/* Subtitle */}
                            <div className="text-sm" style={{ color: 'rgba(200,210,220,0.65)', fontFamily: 'JetBrains Mono, monospace' }}>
                                {isLoading ? 'Generating briefing…' : `Strategic Analysis · ${meta?.drug_name || '—'} · ${meta?.indication || ''}`}
                            </div>

                            {/* Hero Metrics Bar — fully dynamic from backend schema */}
                            {!isLoading && meta?.hero_metrics && (
                                <div className="flex flex-wrap gap-3 mt-3">
                                    {/* Primary metric — always shown, always critical color */}
                                    {meta.hero_metrics.primary_metric_label && (
                                        <MetricPill
                                            label={meta.hero_metrics.primary_metric_label}
                                            value={meta.hero_metrics.primary_metric_value || '—'}
                                            color="crimson"
                                        />
                                    )}
                                    {/* Secondary metric — shown when GPT-4 provides it */}
                                    {meta.hero_metrics.secondary_metric_label && (
                                        <MetricPill
                                            label={meta.hero_metrics.secondary_metric_label}
                                            value={meta.hero_metrics.secondary_metric_value || '—'}
                                            color="amber"
                                        />
                                    )}
                                    {/* Legacy fallback keys (rule-based path) */}
                                    {!meta.hero_metrics.secondary_metric_label && meta.hero_metrics.risk_weighted_index && (
                                        <MetricPill
                                            label="Risk Index"
                                            value={meta.hero_metrics.risk_weighted_index}
                                            color="amber"
                                        />
                                    )}
                                    {meta.hero_metrics.list_price && (
                                        <MetricPill
                                            label="List Price"
                                            value={meta.hero_metrics.list_price}
                                            color="teal"
                                        />
                                    )}
                                    {meta.hero_metrics.pap_monthly_oop && (
                                        <MetricPill
                                            label="PAP OOP"
                                            value={meta.hero_metrics.pap_monthly_oop}
                                            color="green"
                                        />
                                    )}
                                </div>
                            )}

                        </div>

                        {/* Close Button */}
                        <button
                            onClick={onClose}
                            className="flex-shrink-0 rounded-full w-9 h-9 flex items-center justify-center transition-all duration-200"
                            style={{
                                background: 'rgba(255,255,255,0.06)',
                                border: '1px solid rgba(255,255,255,0.1)',
                            }}
                            onMouseEnter={e => {
                                e.currentTarget.style.background = 'rgba(220,38,38,0.25)';
                                e.currentTarget.style.borderColor = 'rgba(220,38,38,0.5)';
                                e.currentTarget.style.boxShadow = '0 0 12px rgba(220,38,38,0.3)';
                            }}
                            onMouseLeave={e => {
                                e.currentTarget.style.background = 'rgba(255,255,255,0.06)';
                                e.currentTarget.style.borderColor = 'rgba(255,255,255,0.1)';
                                e.currentTarget.style.boxShadow = 'none';
                            }}
                            aria-label="Close"
                        >
                            <X className="w-4 h-4" style={{ color: 'rgba(200,200,200,0.8)' }} />
                        </button>
                    </div>

                    {/* ── Lens Toggle ── */}
                    {!isLoading && (
                        <div className="flex mt-4">
                            <div
                                className="inline-flex rounded-full p-0.5"
                                style={{ background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.08)' }}
                            >
                                <LensButton
                                    active={lens === 'boardroom'}
                                    onClick={() => setLens('boardroom')}
                                    icon={<Briefcase className="w-3.5 h-3.5" />}
                                    label="Executive Boardroom"
                                />
                                <LensButton
                                    active={lens === 'msl'}
                                    onClick={() => setLens('msl')}
                                    icon={<Stethoscope className="w-3.5 h-3.5" />}
                                    label="MSL Field Nuggets"
                                />
                            </div>
                            <div className="ml-3 flex items-center text-[10px]" style={{ color: 'rgba(150,160,170,0.6)' }}>
                                {lens === 'boardroom' ? 'C-Suite financial & strategic view' : 'Clinical talking points for prescribers'}
                            </div>
                        </div>
                    )}
                </header>

                {/* ── Scrollable Body ── */}
                <div
                    className="flex-1 overflow-y-auto px-6 py-4 space-y-3 strategic-modal-scroll"
                >
                    {isLoading ? (
                        <div className="flex flex-col items-center justify-center py-16 gap-4">
                            <Loader2 className="w-8 h-8 animate-spin" style={{ color: 'rgba(0,180,180,0.7)' }} />
                            <div className="text-sm" style={{ color: 'rgba(150,160,170,0.7)', fontFamily: 'JetBrains Mono, monospace' }}>
                                Web Sweep AI generating briefing…
                            </div>
                            <div className="flex gap-1 mt-1">
                                {[0, 1, 2, 3, 4, 5, 6].map(i => (
                                    <div
                                        key={i}
                                        className="h-1 rounded-full animate-pulse"
                                        style={{
                                            width: `${24 + Math.sin(i) * 8}px`,
                                            background: 'rgba(0,180,180,0.35)',
                                            animationDelay: `${i * 120}ms`
                                        }}
                                    />
                                ))}
                            </div>
                        </div>
                    ) : insights.length === 0 ? (
                        <div className="text-center py-12 text-sm" style={{ color: 'rgba(150,160,170,0.6)' }}>
                            No insights generated. Please run an asset analysis first.
                        </div>
                    ) : (
                        insights.map((insight, idx) => (
                            <InsightCard
                                key={insight.id}
                                number={idx + 1}
                                icon={insight.icon}
                                category={insight.category}
                                text={lens === 'boardroom' ? insight.boardroom_view : insight.msl_view}
                                lens={lens}
                                isHighlight={idx === 2} // insight_3 often the financial liability — highlight it
                            />
                        ))
                    )}
                </div>

                {/* ── Pinned Footer ── */}
                <footer
                    className="flex-shrink-0 px-6 py-4 flex items-center justify-between gap-3"
                    style={{ borderTop: '1px solid rgba(255,255,255,0.06)', background: 'rgba(5,8,16,0.6)' }}
                >
                    <div className="text-[10px]" style={{ color: 'rgba(120,130,145,0.55)', fontFamily: 'JetBrains Mono, monospace' }}>
                        Powered by Real-Time Web Intelligence · No Hardcoded Data
                    </div>
                    <div className="flex items-center gap-2 flex-shrink-0">
                        {/* Ghost: Dismiss */}
                        <button
                            onClick={onClose}
                            className="px-4 py-2 rounded-sm text-xs font-mono transition-all duration-200"
                            style={{
                                color: 'rgba(180,185,195,0.7)',
                                border: '1px solid rgba(255,255,255,0.1)',
                                background: 'transparent',
                            }}
                            onMouseEnter={e => { e.currentTarget.style.background = 'rgba(255,255,255,0.05)'; }}
                            onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; }}
                        >
                            Dismiss Insight
                        </button>

                        {/* Outline: Export MSL Brief */}
                        <button
                            disabled={lens !== 'msl'}
                            className="px-4 py-2 rounded-sm text-xs font-mono transition-all duration-200 flex items-center gap-1.5"
                            style={{
                                color: lens === 'msl' ? 'rgba(0,200,200,0.85)' : 'rgba(100,110,120,0.4)',
                                border: `1px solid ${lens === 'msl' ? 'rgba(0,200,200,0.3)' : 'rgba(100,110,120,0.2)'}`,
                                background: 'transparent',
                                cursor: lens === 'msl' ? 'pointer' : 'not-allowed',
                            }}
                            onMouseEnter={e => { if (lens === 'msl') e.currentTarget.style.background = 'rgba(0,200,200,0.07)'; }}
                            onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; }}
                            title={lens !== 'msl' ? 'Switch to MSL Lens to export' : 'Export MSL Brief as PDF'}
                            onClick={() => lens === 'msl' && window.print()}
                        >
                            <FileText className="w-3 h-3" />
                            Export MSL Brief
                        </button>

                        {/* Primary: Launch War Room */}
                        <button
                            onClick={() => { onClose(); onLaunchWarRoom?.(); }}
                            className="px-5 py-2 rounded-sm text-xs font-mono font-semibold transition-all duration-200 flex items-center gap-1.5"
                            style={{
                                background: 'linear-gradient(135deg, rgba(0,120,160,0.85), rgba(0,160,180,0.85))',
                                border: '1px solid rgba(0,200,200,0.35)',
                                color: '#fff',
                                boxShadow: '0 0 20px rgba(0,160,180,0.25)',
                            }}
                            onMouseEnter={e => { e.currentTarget.style.boxShadow = '0 0 30px rgba(0,160,180,0.5)'; }}
                            onMouseLeave={e => { e.currentTarget.style.boxShadow = '0 0 20px rgba(0,160,180,0.25)'; }}
                        >
                            <Zap className="w-3 h-3" />
                            Launch War Room
                        </button>
                    </div>
                </footer>
            </div>
        </div>
    );
}

/* ── Sub-components ─────────────────────────────────────────────────── */

function MetricPill({ label, value, color }) {
    const colors = {
        crimson: { val: 'rgba(220,60,60,0.95)', bg: 'rgba(220,40,40,0.08)', border: 'rgba(220,60,60,0.2)' },
        amber: { val: 'rgba(245,158,11,0.95)', bg: 'rgba(245,158,11,0.08)', border: 'rgba(245,158,11,0.2)' },
        teal: { val: 'rgba(0,200,200,0.9)', bg: 'rgba(0,180,180,0.07)', border: 'rgba(0,200,200,0.2)' },
        green: { val: 'rgba(52,211,153,0.9)', bg: 'rgba(52,211,153,0.07)', border: 'rgba(52,211,153,0.2)' },
    };
    const c = colors[color] || colors.teal;
    return (
        <div
            className="flex items-center gap-2 px-3 py-1.5 rounded-sm"
            style={{ background: c.bg, border: `1px solid ${c.border}` }}
        >
            <span className="text-[9px] uppercase tracking-widest" style={{ color: 'rgba(160,170,180,0.65)' }}>{label}</span>
            <span className="text-sm font-mono font-bold" style={{ color: c.val, textShadow: `0 0 12px ${c.val}` }}>{value}</span>
        </div>
    );
}

function LensButton({ active, onClick, icon, label }) {
    return (
        <button
            onClick={onClick}
            className="flex items-center gap-1.5 px-4 py-2 rounded-full text-xs font-mono transition-all duration-200"
            style={{
                background: active ? 'rgba(0,160,180,0.2)' : 'transparent',
                color: active ? 'rgba(0,215,215,0.95)' : 'rgba(140,150,165,0.6)',
                border: active ? '1px solid rgba(0,200,200,0.25)' : '1px solid transparent',
                boxShadow: active ? '0 0 16px rgba(0,180,180,0.2)' : 'none',
            }}
        >
            {icon}
            {label}
        </button>
    );
}

function InsightCard({ number, icon, category, text, lens, isHighlight }) {
    const isMsl = lens === 'msl';
    return (
        <div
            className="rounded-sm px-5 py-4 transition-all duration-300"
            style={{
                background: '#18181B',
                border: '1px solid rgba(255, 255, 255, 0.1)',
                borderLeft: isHighlight
                    ? (isMsl ? '4px solid #F59E0B' : '4px solid #0EA5E9')
                    : '4px solid rgba(255,255,255,0.1)',
            }}
        >
            <div className="flex items-start gap-3">
                {/* Number + Icon Badge */}
                <div className="flex-shrink-0 flex flex-col items-center gap-1.5 mt-0.5">
                    {icon ? (
                        <span className="text-base leading-none" title="Insight Category Icon">
                            {icon}
                        </span>
                    ) : (
                        <Activity
                            className="w-4 h-4"
                            style={{ color: '#0EA5E9' }}
                            strokeWidth={2.5}
                        />
                    )}
                    <span
                        className="text-[9px] font-mono"
                        style={{ color: 'rgba(120,130,145,0.5)' }}
                    >
                        {String(number).padStart(2, '0')}
                    </span>
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0">
                    <div
                        className="text-[10px] font-mono uppercase tracking-widest mb-1.5"
                        style={{ color: isMsl ? 'rgba(0,200,160,0.7)' : 'rgba(0,190,200,0.7)' }}
                    >
                        {category}
                    </div>
                    <p
                        className="text-base font-medium leading-[1.6]"
                        style={{
                            color: '#F3F4F6',
                            fontFamily: "'Inter', -apple-system, sans-serif",
                        }}
                        dangerouslySetInnerHTML={{ __html: highlightMetrics(text, isMsl) }}
                    />
                </div>
            </div>
        </div>
    );
}

/**
 * Highlight financial metrics (₹ amounts, % values, multipliers, HEOR terms)
 * with coloured spans for the boardroom lens.
 */
function highlightMetrics(text, isMsl) {
    if (!text) return '';
    if (isMsl) {
        // MSL: highlight quoted strings and key clinical terms in a bright, legible teal. Note: #0EA5E9 is Tailwind's sky-500.
        return text
            .replace(/(['"])(.*?)\1/g, '<span style="color:#0EA5E9;font-weight:600">$1$2$1</span>')
            .replace(/\b(HR|MACE|LDL|HbA1c|BMD|VMS|mRS|ICER|QoL|AE|OOP|PAP|PMJAY|CGHS|QALY|HEOR)\b/g,
                '<span style="color:#0EA5E9;font-style:italic">$1</span>');
    }
    // Boardroom: Use solid, high-contrast colors without blurry text-shadows for better readability.
    // Strict requirement: Highlight purely with Teal (#0EA5E9) and Amber (#F59E0B)
    return text
        .replace(/(₹[\d,]+(?:\/\w+)?)/g,
            '<span style="color:#F59E0B;font-family:\'JetBrains Mono\',monospace;font-weight:700">$1</span>')
        .replace(/(\d+\.\d+x)/g,
            '<span style="color:#F59E0B;font-family:\'JetBrains Mono\',monospace;font-weight:700">$1</span>')
        .replace(/(\d+(?:\.\d+)?%)/g,
            '<span style="color:#F59E0B;font-family:\'JetBrains Mono\',monospace;font-weight:700">$1</span>')
        .replace(/\b(HR|MACE|LDL|HbA1c|BMD|VMS|mRS|ICER|QoL|AE|OOP|PAP|PMJAY|CGHS|QALY|HEOR|CDSCO)\b/g,
            '<span style="color:#0EA5E9;font-style:italic;font-weight:600">$1</span>');
}
