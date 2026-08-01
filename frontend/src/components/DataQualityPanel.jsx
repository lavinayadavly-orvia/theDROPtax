import React from 'react';
import { Card, CardContent } from './ui/card';
import { Badge } from './ui/badge';
import { AlertTriangle, AlertCircle, Info, CheckCircle2 } from 'lucide-react';

// Anti-hallucination surface: shows exactly what could NOT be resolved, so the
// user never mistakes a missing value for a computed one.
const SEVERITY = {
  error: { icon: AlertCircle, cls: 'text-red-500', border: 'border-red-500/40', bg: 'bg-red-500/10', label: 'Blocking' },
  warning: { icon: AlertTriangle, cls: 'text-amber-500', border: 'border-amber-500/40', bg: 'bg-amber-500/10', label: 'Needs input' },
  info: { icon: Info, cls: 'text-sky-400', border: 'border-sky-400/40', bg: 'bg-sky-400/10', label: 'Note' },
};

const STATUS = {
  complete: { cls: 'border-emerald-500 text-emerald-500', label: 'All data resolved' },
  partial: { cls: 'border-amber-500 text-amber-500', label: 'Partial data' },
  unavailable: { cls: 'border-red-500 text-red-500', label: 'Key data unavailable' },
};

export default function DataQualityPanel({ dataQuality, extraIssues = [], textSecondary = 'text-muted-foreground', borderColor }) {
  const issues = [...(dataQuality?.issues || []), ...extraIssues];
  const status = dataQuality?.status || (issues.length ? 'partial' : 'complete');

  // Nothing to report — show a compact confirmation rather than a scary empty box
  if (!issues.length && status === 'complete') {
    return (
      <div className="flex items-center gap-2 text-xs" data-testid="data-quality-ok">
        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
        <span className={textSecondary}>All model inputs resolved from sources.</span>
      </div>
    );
  }

  const statusStyle = STATUS[status] || STATUS.partial;

  return (
    <Card className="glass-card overflow-hidden" style={{ borderColor }} data-testid="data-quality-panel">
      <CardContent className="py-4 space-y-3">
        <div className="flex items-center justify-between">
          <div className="text-xs uppercase tracking-widest text-muted-foreground">Data Quality</div>
          <Badge variant="outline" className={`text-xs ${statusStyle.cls}`} data-testid="data-quality-status">
            {statusStyle.label}
          </Badge>
        </div>

        <p className={`text-xs ${textSecondary}`}>
          Values below could not be resolved from a reliable source. The platform does not estimate them —
          enter them manually or verify against the label / trial publication.
        </p>

        <div className="space-y-2">
          {issues.map((issue, idx) => {
            const sev = SEVERITY[issue.severity] || SEVERITY.warning;
            const Icon = sev.icon;
            return (
              <div key={idx} className={`flex items-start gap-2 p-2 rounded-sm border ${sev.border} ${sev.bg}`}
                   data-testid={`data-issue-${issue.field}`}>
                <Icon className={`w-3.5 h-3.5 mt-0.5 shrink-0 ${sev.cls}`} />
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <span className={`text-xs font-medium ${sev.cls}`}>{issue.field}</span>
                    <span className="text-[10px] text-muted-foreground uppercase tracking-wider">{sev.label}</span>
                  </div>
                  <p className={`text-xs ${textSecondary} mt-0.5`}>{issue.message}</p>
                </div>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}
