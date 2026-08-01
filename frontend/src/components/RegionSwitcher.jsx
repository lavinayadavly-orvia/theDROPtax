import React, { useEffect } from 'react';
import { useApp } from '../context/AppContext';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || '';
const API = (BACKEND_URL && BACKEND_URL.startsWith('http')) ? `${BACKEND_URL}/api` : '/api';

export const RegionSwitcher = () => {
  const { selectedRegion, setSelectedRegion, regions, setRegions } = useApp();

  useEffect(() => {
    const fetchRegions = async () => {
      try {
        const response = await axios.get(`${API}/regions`);
        setRegions(response.data);
        if (response.data.length > 0 && !selectedRegion.name) {
          setSelectedRegion(response.data[0]);
        }
      } catch (error) {
        console.error('Error fetching regions:', error);
      }
    };
    fetchRegions();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleRegionChange = (code) => {
    const region = regions.find(r => r.code === code);
    if (region) {
      setSelectedRegion(region);
    }
  };

  return (
    <div className="flex items-center gap-2">
      <span className="text-xs uppercase tracking-widest text-muted-foreground font-data">REGION</span>
      <Select value={selectedRegion.code} onValueChange={handleRegionChange}>
        <SelectTrigger data-testid="region-switcher" className="w-[140px] border-primary/30 bg-background/50">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {regions.map((region) => (
            <SelectItem key={region.code} value={region.code} data-testid={`region-option-${region.code}`}>
              <span className="font-data">{region.currency_symbol} {region.name}</span>
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
};
