import React from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from './ui/dialog';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { useApp } from '../context/AppContext';
import { FlaskConical, CheckCircle2 } from 'lucide-react';

export function IndicationSelectDialog({
  open,
  onOpenChange,
  drugName,
  indications = [],
  onSelectIndication,
  isLoading = false
}) {
  const { theme } = useApp();

  const bgColor = theme === 'dark' ? '#121212' : '#FFFFFF';
  const textColor = theme === 'dark' ? '#E5E5E5' : '#1A1A1A';
  const borderColor = theme === 'dark' ? '#262626' : '#E5E5E5';
  const hoverBg = theme === 'dark' ? '#1A1A1A' : '#F5F5F5';

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        data-testid="indication-select-dialog"
        className="sm:max-w-md"
        style={{
          backgroundColor: bgColor,
          borderColor: borderColor,
          color: textColor
        }}
      >
        <DialogHeader>
          <DialogTitle
            className="flex items-center gap-2 font-data"
            style={{ color: textColor }}
          >
            <FlaskConical className="w-5 h-5 text-[#008080]" />
            SELECT INDICATION
          </DialogTitle>
          <DialogDescription className="text-muted-foreground">
            <span className="font-semibold" style={{ color: '#008080' }}>{drugName}</span> is approved for multiple indications. Select one to proceed with analysis.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-2 mt-4 max-h-[60vh] overflow-y-auto pr-2" data-testid="indication-options">
          {indications.map((ind, idx) => (
            <button
              key={idx}
              data-testid={`indication-option-${idx}`}
              onClick={() => onSelectIndication(ind.indication)}
              disabled={isLoading}
              className="w-full p-4 rounded-sm border-2 text-left transition-all hover:border-[#008080] disabled:opacity-50 disabled:cursor-not-allowed"
              style={{
                borderColor: ind.is_primary ? '#008080' : borderColor,
                backgroundColor: 'transparent'
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.backgroundColor = hoverBg;
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.backgroundColor = 'transparent';
              }}
            >
              <div className="flex items-center justify-between">
                <div>
                  <div className="font-semibold font-data" style={{ color: textColor }}>
                    {ind.indication}
                  </div>
                  {ind.approval_date && (
                    <div className="text-xs text-muted-foreground mt-1">
                      Approved: {ind.approval_date}
                    </div>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  {ind.is_primary && (
                    <Badge className="bg-[#008080] text-white text-xs">
                      <CheckCircle2 className="w-3 h-3 mr-1" />
                      Primary
                    </Badge>
                  )}
                </div>
              </div>
            </button>
          ))}
        </div>

        <div className="mt-4 text-center">
          <Button
            variant="ghost"
            onClick={() => onOpenChange(false)}
            disabled={isLoading}
            className="text-muted-foreground hover:text-foreground"
            data-testid="indication-cancel-btn"
          >
            Cancel
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
