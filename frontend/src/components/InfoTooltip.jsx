import React from 'react';
import { HelpCircle } from 'lucide-react';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from './ui/tooltip';
import { GLOSSARY } from '../lib/glossary';

// Standard InfoTooltip with custom content
export const InfoTooltip = ({ content, children, side = "top" }) => {
  return (
    <TooltipProvider delayDuration={100}>
      <Tooltip>
        <TooltipTrigger asChild>
          <span className="inline-flex items-center gap-1 cursor-help">
            {children}
            <HelpCircle className="w-3.5 h-3.5 text-muted-foreground hover:text-[#008080] transition-colors" />
          </span>
        </TooltipTrigger>
        <TooltipContent 
          side={side}
          className="max-w-sm bg-[#0A0A0A] text-white text-xs border border-[#008080]/30 shadow-lg shadow-[#008080]/10 p-3"
        >
          <p className="leading-relaxed">{content}</p>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
};

// Glossary-powered tooltip - just pass the glossary key
export const TermTooltip = ({ termKey, children, side = "top", showIcon = true }) => {
  const entry = GLOSSARY[termKey];
  
  if (!entry) {
    console.warn(`Glossary term not found: ${termKey}`);
    return <span>{children}</span>;
  }
  
  return (
    <TooltipProvider delayDuration={100}>
      <Tooltip>
        <TooltipTrigger asChild>
          <span className="inline-flex items-center gap-1 cursor-help border-b border-dotted border-muted-foreground/50 hover:border-[#008080] transition-colors">
            {children}
            {showIcon && <HelpCircle className="w-3 h-3 text-muted-foreground hover:text-[#008080] transition-colors" />}
          </span>
        </TooltipTrigger>
        <TooltipContent 
          side={side}
          className="max-w-sm bg-[#0A0A0A] text-white text-xs border border-[#008080]/30 shadow-lg shadow-[#008080]/10 p-3"
        >
          <div className="space-y-1">
            <div className="font-bold text-[#008080] text-sm">{entry.term}</div>
            <p className="leading-relaxed text-gray-300">{entry.full}</p>
          </div>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
};

// Inline tooltip for values - shows the definition when hovering over a value
export const ValueTooltip = ({ termKey, value, unit = "", side = "top" }) => {
  const entry = GLOSSARY[termKey];
  
  if (!entry) {
    return <span>{value}{unit}</span>;
  }
  
  return (
    <TooltipProvider delayDuration={100}>
      <Tooltip>
        <TooltipTrigger asChild>
          <span className="cursor-help hover:text-[#008080] transition-colors">
            {value}{unit}
          </span>
        </TooltipTrigger>
        <TooltipContent 
          side={side}
          className="max-w-sm bg-[#0A0A0A] text-white text-xs border border-[#008080]/30 shadow-lg shadow-[#008080]/10 p-3"
        >
          <div className="space-y-1">
            <div className="font-bold text-[#008080] text-sm">{entry.term}</div>
            <p className="text-gray-400 text-xs">{entry.short}</p>
            <p className="leading-relaxed text-gray-300 pt-1">{entry.full}</p>
          </div>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
};

