import { useEffect, useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import {
  AlertCircle, Umbrella, Car, Home, Plane,
  Ship, Flame, Scale, Cpu, Leaf, Dog, Calendar, Landmark, Building2,
} from 'lucide-react';
import { endpoints } from '../lib/api';
import { defaultCommercialSelection } from '../lib/commercialTaxonomy';
import LineDetailLayout from '../components/LineDetailLayout';

const LOB_ICONS = {
  car_tp: Car,
  car_comprehensive: Car,
  tw_tp: Car,
  tw_comprehensive: Car,
  cv_tp: Car,
  cv_comprehensive: Car,
  home_structure: Home,
  home_contents: Home,
  home_comprehensive: Home,
  travel_domestic: Plane,
  travel_international: Plane,
  marine_cargo: Ship,
  marine_hull: Ship,
  fire_residential: Flame,
  fire_commercial: Flame,
  professional_indemnity_gi: Scale,
  public_liability_gi: Scale,
  product_liability_gi: Scale,
  cyber_data_breach: Cpu,
  cyber_ransomware: Cpu,
  crop_yield: Leaf,
  crop_weather: Leaf,
  livestock_cattle: Dog,
  pet_insurance: Dog,
  wedding_insurance: Calendar,
  concert_event_insurance: Calendar,
  title_insurance_gi: Landmark,
  mortgage_insurance_gi: Landmark,
  insurer_psu: Building2,
  insurer_private: Building2,
  reinsurance_treaty: Building2,
};

export default function GeneralLinePage({ presets, onRunDemo, onSubmit }) {
  const { lobSlug } = useParams();
  const [line, setLine] = useState(null);
  const [error, setError] = useState('');
  const [selection, setSelection] = useState(null);

  useEffect(() => {
    let cancelled = false;
    setLine(null);
    setError('');
    setSelection(null);
    endpoints.generalInsuranceLine(lobSlug)
      .then((d) => { if (!cancelled) setLine(d); })
      .catch((e) => { if (!cancelled) setError(e.message || 'Line not found'); });
    return () => { cancelled = true; };
  }, [lobSlug]);

  const lineTaxonomy = useMemo(() => {
    if (!line) return [];
    return [{
      id: line.category_id || 'general',
      name: line.short_name || line.name,
      products: [{
        id: line.id,
        name: line.name,
        slug: line.slug,
        insurance_line: line.insurance_line,
        checklist_lob: line.checklist_lob,
        coverages: line.coverages || [],
      }],
    }];
  }, [line]);

  useEffect(() => {
    if (!lineTaxonomy.length) return;
    setSelection(defaultCommercialSelection(lineTaxonomy));
  }, [lineTaxonomy]);

  if (error) {
    return (
      <div className="mx-auto max-w-3xl py-16 text-center">
        <AlertCircle className="mx-auto h-8 w-8 text-red-400" />
        <p className="mt-3 text-red-400">{error}</p>
        <Link to="/insurance/general" className="mt-4 inline-block text-sm text-brand hover:underline">
          Back to general hub
        </Link>
      </div>
    );
  }

  if (!line) {
    return (
      <div className="flex justify-center py-24">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-brand border-t-transparent" />
      </div>
    );
  }

  const Icon = LOB_ICONS[line.id] || Umbrella;

  return (
    <LineDetailLayout
      line={line}
      eyebrowLabel="Personal Lines"
      accent="sky"
      icon={Icon}
      presets={presets}
      lineTaxonomy={lineTaxonomy}
      selection={selection}
      onSelectionChange={setSelection}
      onRunDemo={onRunDemo}
      onSubmit={onSubmit}
      extraRunSelectorProps={{ isGeneralProductPicker: true }}
    />
  );
}
