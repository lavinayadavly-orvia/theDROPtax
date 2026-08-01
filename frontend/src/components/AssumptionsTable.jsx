import React, { useState } from 'react';
import { ChevronDown, ChevronUp, Info, ExternalLink, AlertTriangle, CheckCircle } from 'lucide-react';
import { Badge } from './ui/badge';
import { Button } from './ui/button';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from './ui/collapsible';

export function AssumptionsTable({ calculation, theme }) {
  const [isOpen, setIsOpen] = useState(false);
  
  if (!calculation) return null;
  
  const textColor = theme === 'dark' ? '#E5E5E5' : '#1A1A1A';
  const mutedColor = theme === 'dark' ? '#737373' : '#6B7280';
  const borderColor = theme === 'dark' ? '#262626' : '#E5E5E5';
  const surfaceBg = theme === 'dark' ? '#121212' : '#FFFFFF';
  
  const transparency = calculation.calculation_transparency || {};
  const inputs = transparency.inputs || {};
  const formulas = transparency.formulas || {};
  const commercialBrain = calculation.commercial_brain || {};
  
  const NA = 'Data unavailable';
  const fmtMoney = (v) => (v == null ? NA : calculation.currency_symbol + v.toLocaleString());

  // Build the assumptions data (registry-driven labels; never fabricated values)
  const assumptionRows = [
    {
      label: inputs.primary_endpoint?.label || commercialBrain.primary_endpoint_label || 'Primary Endpoint',
      value: inputs.primary_endpoint?.value != null
        ? `${inputs.primary_endpoint.value} ${inputs.primary_endpoint.unit || ''}`.trim()
        : NA,
      source: inputs.primary_endpoint?.source,
      method: inputs.primary_endpoint?.method || 'Not resolved',
      isEstimated: inputs.primary_endpoint?.is_estimated || inputs.primary_endpoint?.value == null,
      confidence: commercialBrain.clinical_confidence
    },
    {
      label: 'Hazard Ratio (HR)',
      value: commercialBrain.hazard_ratio != null ? commercialBrain.hazard_ratio.toFixed(2) : NA,
      source: inputs.primary_endpoint?.source,
      method: 'Clinical Trial Publication',
      isEstimated: commercialBrain.hazard_ratio == null,
      confidence: commercialBrain.hazard_ratio != null ? 0.8 : 0
    },
    {
      label: 'Competitor Serious AE Rate',
      value: commercialBrain.competitor_severe_ae_rate != null
        ? `${(commercialBrain.competitor_severe_ae_rate * 100).toFixed(0)}%`
        : NA,
      source: inputs.competitor_ae_rate?.source,
      method: inputs.competitor_ae_rate?.method || 'Not resolved',
      isEstimated: commercialBrain.competitor_ae_is_estimated,
      confidence: commercialBrain.competitor_severe_ae_rate == null ? 0 : (commercialBrain.competitor_ae_is_estimated ? 0.3 : 0.8)
    },
    {
      label: 'Drug Serious AE Rate',
      value: commercialBrain.drug_severe_ae_rate != null
        ? `${(commercialBrain.drug_severe_ae_rate * 100).toFixed(0)}%`
        : NA,
      source: inputs.drug_ae_rate?.source,
      method: inputs.drug_ae_rate?.method || 'Not resolved',
      isEstimated: commercialBrain.drug_ae_is_estimated,
      confidence: commercialBrain.drug_severe_ae_rate == null ? 0 : (commercialBrain.drug_ae_is_estimated ? 0.3 : 0.8)
    }
  ];

  // Formula explanations (therapy-area-agnostic value engine)
  const formulaRows = [
    {
      metric: 'Event Probability',
      formula: formulas.event_probability?.formula || 'registry_normalised(primary_endpoint)',
      result: commercialBrain.event_probability != null ? commercialBrain.event_probability.toFixed(2) : NA,
      description: formulas.event_probability?.description || 'Downstream event / treatment-failure proxy'
    },
    {
      metric: 'Event Cost',
      formula: formulas.c_event?.formula || 'event_probability × regional_event_cost',
      result: fmtMoney(commercialBrain.c_event),
      description: formulas.c_event?.description || `Expected cost of a ${(commercialBrain.event_label || 'downstream event').toLowerCase()}`
    },
    {
      metric: 'Adverse-Event Cost',
      formula: formulas.c_adverse_events?.formula || 'AE_rate × 3 × AE_cost',
      result: fmtMoney(commercialBrain.c_adverse_events),
      description: formulas.c_adverse_events?.description || 'AE management cost differential'
    },
    {
      metric: 'Productivity Loss',
      formula: formulas.c_prod?.formula || 'monthly_income × productivity_loss_months',
      result: fmtMoney(commercialBrain.c_prod),
      description: formulas.c_prod?.description || 'Lost productivity attributable to downstream events'
    }
  ];

  const ConfidenceIndicator = ({ confidence }) => {
    const level = confidence >= 0.7 ? 'high' : confidence >= 0.4 ? 'medium' : 'low';
    const colors = {
      high: 'text-emerald-500',
      medium: 'text-amber-500',
      low: 'text-red-400'
    };
    const labels = {
      high: 'High',
      medium: 'Medium',
      low: 'Low'
    };
    
    return (
      <span className={`text-xs font-data ${colors[level]}`}>
        {labels[level]} ({(confidence * 100).toFixed(0)}%)
      </span>
    );
  };

  return (
    <Collapsible open={isOpen} onOpenChange={setIsOpen} className="w-full">
      <CollapsibleTrigger asChild>
        <Button 
          variant="ghost" 
          className="w-full justify-between p-4 h-auto glass-card hover:bg-white/5"
          style={{ borderColor: borderColor }}
          data-testid="assumptions-toggle"
        >
          <div className="flex items-center gap-2">
            <Info className="h-4 w-4" style={{ color: mutedColor }} />
            <span className="text-sm font-medium" style={{ color: textColor }}>
              CALCULATION ASSUMPTIONS & METHODOLOGY
            </span>
            {(commercialBrain.data_incomplete || commercialBrain.competitor_ae_is_estimated) && (
              <Badge variant="outline" className="text-xs border-amber-500 text-amber-500">
                {commercialBrain.data_incomplete ? 'Incomplete Data' : 'Contains Estimates'}
              </Badge>
            )}
          </div>
          {isOpen ? (
            <ChevronUp className="h-4 w-4" style={{ color: mutedColor }} />
          ) : (
            <ChevronDown className="h-4 w-4" style={{ color: mutedColor }} />
          )}
        </Button>
      </CollapsibleTrigger>
      
      <CollapsibleContent className="mt-2">
        <div className="glass-card p-4 space-y-4" style={{ borderColor: borderColor }}>
          {/* Input Assumptions Table */}
          <div>
            <div className="text-xs uppercase tracking-widest mb-3" style={{ color: mutedColor }}>
              DATA INPUTS & SOURCES
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm" data-testid="assumptions-inputs-table">
                <thead>
                  <tr style={{ borderBottom: `1px solid ${borderColor}` }}>
                    <th className="text-left py-2 px-3 font-medium" style={{ color: mutedColor }}>Parameter</th>
                    <th className="text-left py-2 px-3 font-medium" style={{ color: mutedColor }}>Value</th>
                    <th className="text-left py-2 px-3 font-medium" style={{ color: mutedColor }}>Method</th>
                    <th className="text-left py-2 px-3 font-medium" style={{ color: mutedColor }}>Status</th>
                    <th className="text-left py-2 px-3 font-medium" style={{ color: mutedColor }}>Confidence</th>
                  </tr>
                </thead>
                <tbody>
                  {assumptionRows.map((row, idx) => (
                    <tr 
                      key={idx} 
                      style={{ borderBottom: `1px solid ${borderColor}` }}
                      className="hover:bg-white/5"
                    >
                      <td className="py-2 px-3 font-data" style={{ color: textColor }}>{row.label}</td>
                      <td className="py-2 px-3 font-data font-bold" style={{ color: '#14B8A6' }}>
                        {row.value}
                      </td>
                      <td className="py-2 px-3 text-xs" style={{ color: mutedColor }}>
                        <div className="flex items-center gap-1">
                          {row.method}
                          {row.source && (
                            <a 
                              href={row.source} 
                              target="_blank" 
                              rel="noopener noreferrer"
                              className="hover:text-cyan-400"
                            >
                              <ExternalLink className="h-3 w-3" />
                            </a>
                          )}
                        </div>
                      </td>
                      <td className="py-2 px-3">
                        {row.isEstimated ? (
                          <Badge variant="outline" className="text-xs border-amber-500 text-amber-500">
                            <AlertTriangle className="h-3 w-3 mr-1" />
                            Estimated
                          </Badge>
                        ) : row.value !== '-' && row.value !== 'Not Available' ? (
                          <Badge variant="outline" className="text-xs border-emerald-500 text-emerald-500">
                            <CheckCircle className="h-3 w-3 mr-1" />
                            Verified
                          </Badge>
                        ) : (
                          <span className="text-xs" style={{ color: mutedColor }}>-</span>
                        )}
                      </td>
                      <td className="py-2 px-3">
                        <ConfidenceIndicator confidence={row.confidence || 0} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
          
          {/* Calculation Formulas Table */}
          <div>
            <div className="text-xs uppercase tracking-widest mb-3" style={{ color: mutedColor }}>
              LIABILITY CALCULATIONS
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm" data-testid="assumptions-formulas-table">
                <thead>
                  <tr style={{ borderBottom: `1px solid ${borderColor}` }}>
                    <th className="text-left py-2 px-3 font-medium" style={{ color: mutedColor }}>Metric</th>
                    <th className="text-left py-2 px-3 font-medium" style={{ color: mutedColor }}>Formula</th>
                    <th className="text-left py-2 px-3 font-medium" style={{ color: mutedColor }}>Result</th>
                    <th className="text-left py-2 px-3 font-medium" style={{ color: mutedColor }}>Description</th>
                  </tr>
                </thead>
                <tbody>
                  {formulaRows.map((row, idx) => (
                    <tr 
                      key={idx} 
                      style={{ borderBottom: `1px solid ${borderColor}` }}
                      className="hover:bg-white/5"
                    >
                      <td className="py-2 px-3 font-data font-bold" style={{ color: textColor }}>{row.metric}</td>
                      <td className="py-2 px-3 font-mono text-xs" style={{ color: '#14B8A6' }}>
                        {row.formula}
                      </td>
                      <td className="py-2 px-3 font-data font-bold" style={{ color: '#F87171' }}>
                        {row.result}
                      </td>
                      <td className="py-2 px-3 text-xs" style={{ color: mutedColor }}>
                        {row.description}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
          
          {/* Total Liability */}
          <div 
            className="flex justify-between items-center p-3 rounded-sm mt-4"
            style={{ backgroundColor: theme === 'dark' ? '#1A1A1A' : '#F5F5F5' }}
          >
            <span className="font-medium" style={{ color: textColor }}>TOTAL UNFUNDED EXPOSURE</span>
            <span className="font-data text-xl font-bold text-[#F87171]">
              {calculation.currency_symbol}{calculation.total_liability?.toLocaleString() || 0}
            </span>
          </div>
          
          {/* Disclaimer */}
          <div className="text-xs p-3 rounded-sm" style={{ backgroundColor: theme === 'dark' ? '#0A0A0A' : '#F9F9F9', color: mutedColor }}>
            <strong>Note:</strong> Values marked as "Estimated" are derived using fallback methods when primary data sources are unavailable. 
            Confidence scores reflect data source reliability. Regional cost parameters are based on healthcare cost indices for the selected region.
          </div>
        </div>
      </CollapsibleContent>
    </Collapsible>
  );
}
