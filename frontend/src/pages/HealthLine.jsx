import { useEffect, useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { AlertCircle, Stethoscope, HeartPulse, Users, Activity } from 'lucide-react';
import { endpoints } from '../lib/api';
import { defaultCommercialSelection } from '../lib/commercialTaxonomy';
import LineDetailLayout from '../components/LineDetailLayout';

const LOB_ICONS = {
  individual_basic: HeartPulse,
  family_floater_standard: Users,
  critical_illness_standalone: Activity,
  senior_standard: Stethoscope,
  group_employer_mediclaim: Users,
};

export default function HealthLinePage({ presets, onRunDemo, onSubmit }) {
  const { lobSlug } = useParams();
  const [line, setLine] = useState(null);
  const [error, setError] = useState('');
  const [selection, setSelection] = useState(null);

  useEffect(() => {
    let cancelled = false;
    setLine(null);
    setError('');
    setSelection(null);
    endpoints.healthInsuranceLine(lobSlug)
      .then((d) => { if (!cancelled) setLine(d); })
      .catch((e) => { if (!cancelled) setError(e.message || 'Line not found'); });
    return () => { cancelled = true; };
  }, [lobSlug]);

  const lineTaxonomy = useMemo(() => {
    if (!line) return [];
    return [{
      id: line.category_id || 'health',
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
        <Link to="/insurance/health" className="mt-4 inline-block text-sm text-brand hover:underline">
          Back to health hub
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

  const Icon = LOB_ICONS[line.id] || Stethoscope;

  return (
    <LineDetailLayout
      line={line}
      eyebrowLabel="Health Insurance"
      accent="teal"
      icon={Icon}
      presets={presets}
      lineTaxonomy={lineTaxonomy}
      selection={selection}
      onSelectionChange={setSelection}
      onRunDemo={onRunDemo}
      onSubmit={onSubmit}
      extraRunSelectorProps={{ isHealthProductPicker: true }}
    />
  );
}
