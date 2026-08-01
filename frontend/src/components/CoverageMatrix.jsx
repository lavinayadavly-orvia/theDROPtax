import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Badge } from './ui/badge';
import { Building2, Stethoscope, Home, AlertTriangle } from 'lucide-react';

// Site-of-care coverage & price matrix.
// The SAME drug reimburses and prices differently by where it is administered:
//   IPD  → bundled in the hospitalization claim (usually covered, tender price)
//   OPD  → day-care / OPD drug list dependent (often conditional or excluded)
//   HOME → self-administered retail at full MRP (usually excluded, costs more)
const SETTINGS = [
  { key: 'IPD', label: 'In-Patient (IPD)', icon: Building2, hint: 'Admitted / day-care administration' },
  { key: 'OPD', label: 'Out-Patient (OPD)', icon: Stethoscope, hint: 'Follow-up visit after discharge' },
  { key: 'HOME', label: 'Home / Retail', icon: Home, hint: 'Self-administered, bought at pharmacy' },
];

const COVERAGE_STYLES = {
  covered: { cls: 'border-emerald-500 text-emerald-500', label: 'Covered' },
  partial: { cls: 'border-teal-500 text-teal-500', label: 'Partial' },
  conditional: { cls: 'border-amber-500 text-amber-500', label: 'Conditional' },
  excluded: { cls: 'border-red-500 text-red-500', label: 'Excluded' },
  unknown: { cls: 'border-gray-500 text-gray-400', label: 'Unknown' },
  'n/a': { cls: 'border-gray-700 text-gray-500', label: 'Not applicable' },
};

const PRICE_BASIS_LABEL = {
  institutional_tender: 'Institutional / tender price',
  institutional_or_retail: 'Institutional or retail',
  retail_mrp: 'Retail MRP (full price)',
};

export default function CoverageMatrix({ applicability, currencySymbol = '₹', theme, textPrimary, textSecondary, borderColor }) {
  if (!applicability?.coverage_by_setting) return null;

  const { coverage_by_setting: cov, coverage_gap: gap, recommended_setting, financial_assistance: fa } = applicability;

  return (
    <Card className="glass-card overflow-hidden" style={{ borderColor }} data-testid="coverage-matrix">
      <CardHeader className="pb-3 border-b" style={{ borderColor }}>
        <CardTitle className={`font-data text-sm ${textPrimary} flex items-center gap-2`}>
          <Building2 className="w-4 h-4 text-[#008080]" />
          COVERAGE &amp; PRICE BY SITE OF CARE
        </CardTitle>
        <p className={`text-xs ${textSecondary} mt-1`}>
          The same drug reimburses and prices differently depending on where it is given.
        </p>
      </CardHeader>
      <CardContent className="pt-4">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b" style={{ borderColor }}>
                <th className={`text-left py-2 px-3 font-medium ${textPrimary}`}>Setting</th>
                <th className={`text-left py-2 px-3 font-medium ${textPrimary}`}>Coverage</th>
                <th className={`text-left py-2 px-3 font-medium ${textPrimary}`}>Price basis</th>
                <th className={`text-right py-2 px-3 font-medium ${textPrimary}`}>Est. patient OOP</th>
              </tr>
            </thead>
            <tbody>
              {SETTINGS.map(({ key, label, icon: Icon, hint }) => {
                const c = cov[key] || {};
                const style = COVERAGE_STYLES[c.coverage] || COVERAGE_STYLES.unknown;
                const isRecommended = recommended_setting === key;
                return (
                  <tr key={key} className="border-b" style={{ borderColor, opacity: c.feasible ? 1 : 0.45 }}
                      data-testid={`coverage-row-${key}`}>
                    <td className={`py-3 px-3 ${textSecondary}`}>
                      <div className="flex items-center gap-2">
                        <Icon className="w-4 h-4" />
                        <div>
                          <div className={textPrimary}>{label}</div>
                          <div className="text-[10px] text-muted-foreground">{hint}</div>
                        </div>
                        {isRecommended && (
                          <Badge variant="outline" className="text-[10px] border-[#008080] text-[#008080] ml-1">
                            Expected
                          </Badge>
                        )}
                      </div>
                    </td>
                    <td className="py-3 px-3">
                      {c.feasible ? (
                        <Badge variant="outline" className={`text-xs ${style.cls}`}>{style.label}</Badge>
                      ) : (
                        <span className="text-xs text-muted-foreground">Not feasible for this route</span>
                      )}
                    </td>
                    <td className={`py-3 px-3 text-xs ${textSecondary}`}>
                      {c.feasible ? (PRICE_BASIS_LABEL[c.price_basis] || '—') : '—'}
                    </td>
                    <td className={`py-3 px-3 text-right font-data ${textPrimary}`}>
                      {c.feasible && c.patient_oop_est != null
                        ? `${currencySymbol}${c.patient_oop_est.toLocaleString()}`
                        : <span className="text-muted-foreground text-xs">—</span>}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* Coverage gap callout — the driver of financial assistance */}
        {gap?.exists && (
          <div className="mt-4 p-3 rounded-sm border border-amber-500/40 bg-amber-500/10" data-testid="coverage-gap">
            <div className="flex items-start gap-2">
              <AlertTriangle className="w-4 h-4 text-amber-500 mt-0.5 shrink-0" />
              <div>
                <div className="text-xs font-medium text-amber-500 mb-1">
                  Coverage gap at {gap.worst_setting === 'HOME' ? 'home / retail' : 'out-patient'} setting
                </div>
                <p className={`text-xs ${textSecondary}`}>
                  {gap.note}
                  {gap.oop_jump_vs_covered != null && (
                    <> Patient pays approximately{' '}
                      <span className="font-data text-amber-500">
                        {currencySymbol}{Math.abs(gap.oop_jump_vs_covered).toLocaleString()}
                      </span>{' '}more than in the covered setting.</>
                  )}
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Financial assistance verdict */}
        <div className="mt-3 flex items-start gap-2 text-xs">
          <span className={textSecondary}>Financial assistance:</span>
          {fa?.relevant ? (
            <Badge variant="outline" className="text-xs border-[#008080] text-[#008080]">
              {fa.tier === 'full_pap' ? 'Full PAP recommended' : 'Co-pay support recommended'}
            </Badge>
          ) : (
            <Badge variant="outline" className="text-xs border-gray-500 text-gray-400">Not required</Badge>
          )}
        </div>
        {fa?.reason && <p className={`text-[11px] ${textSecondary} mt-1`}>{fa.reason}</p>}
      </CardContent>
    </Card>
  );
}
