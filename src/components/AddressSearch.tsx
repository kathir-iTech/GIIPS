import React, { useState, useEffect, useRef, useCallback } from 'react';
import { MapPin, Loader2, Search } from 'lucide-react';

const NOMINATIM_BASE = 'https://nominatim.openstreetmap.org/search';

const TN_BBOX = '76.0,13.5,80.5,6.5';

interface NominatimResult {
  lat: string;
  lon: string;
  display_name: string;
  place_id: number;
}

interface AddressSearchProps {
  value: string;
  onChange: (data: { address: string; lat: number; lon: number }) => void;
  placeholder?: string;
}

const AddressSearch: React.FC<AddressSearchProps> = ({ value, onChange, placeholder = 'Search your location...' }) => {
  const [query, setQuery] = useState(value || '');
  const [results, setResults] = useState<NominatimResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const [selected, setSelected] = useState(false);

  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const wrapperRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (selected) return;

    if (debounceRef.current) clearTimeout(debounceRef.current);

    const trimmed = query.trim();
    if (trimmed.length < 3) {
      setResults([]);
      setOpen(false);
      return;
    }

    debounceRef.current = setTimeout(async () => {
      if (abortRef.current) abortRef.current.abort();
      const controller = new AbortController();
      abortRef.current = controller;

      setLoading(true);
      try {
        const params = new URLSearchParams({
          q: trimmed,
          format: 'json',
          limit: '7',
          countrycodes: 'in',
          viewbox: TN_BBOX,
          bounded: '1',
          addressdetails: '1',
        });

        const res = await fetch(`${NOMINATIM_BASE}?${params}`, {
          signal: controller.signal,
          headers: {
            'User-Agent': 'GIIPS-GrievancePortal/2.1 (citizen complaint submission)',
            'Accept': 'application/json',
          },
        });

        if (!res.ok) return;
        const data: NominatimResult[] = await res.json();
        setResults(data);
        setOpen(data.length > 0);
      } catch (e: any) {
        if (e.name !== 'AbortError') {
          setResults([]);
        }
      } finally {
        setLoading(false);
      }
    }, 500);

    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [query, selected]);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSelect = useCallback((result: NominatimResult) => {
    setQuery(result.display_name);
    setSelected(true);
    setOpen(false);
    onChange({
      address: result.display_name,
      lat: parseFloat(result.lat),
      lon: parseFloat(result.lon),
    });
  }, [onChange]);

  const handleInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    setQuery(e.target.value);
    setSelected(false);
  }, []);

  const handleClear = useCallback(() => {
    setQuery('');
    setSelected(false);
    setResults([]);
    setOpen(false);
    onChange({ address: '', lat: 0, lon: 0 });
  }, [onChange]);

  return (
    <div className="address-search-wrapper" ref={wrapperRef}>
      <div className="address-search-input-group">
        <Search size={16} className="address-search-icon" />
        <input
          type="text"
          className="address-search-input"
          placeholder={placeholder}
          value={query}
          onChange={handleInputChange}
          onFocus={() => { if (results.length > 0) setOpen(true); }}
        />
        {loading && <Loader2 size={16} className="address-search-spinner" />}
        {query && !loading && (
          <button className="address-search-clear" onClick={handleClear} type="button">&times;</button>
        )}
      </div>
      {open && results.length > 0 && (
        <ul className="address-suggestions">
          {results.map((r) => (
            <li key={r.place_id} className="address-suggestion-item" onClick={() => handleSelect(r)}>
              <MapPin size={14} className="address-suggestion-icon" />
              <span className="address-suggestion-text">{r.display_name}</span>
            </li>
          ))}
        </ul>
      )}
      {open && !loading && results.length === 0 && query.trim().length >= 3 && (
        <div className="address-no-results">No locations found in Tamil Nadu</div>
      )}
    </div>
  );
};

export default AddressSearch;
