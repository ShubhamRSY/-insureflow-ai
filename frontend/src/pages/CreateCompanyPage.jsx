import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Building2, Globe, Briefcase, MapPin, Hash, FileText } from 'lucide-react';

const ORG_SIZES = [
  '1-10 employees',
  '11-50 employees',
  '51-200 employees',
  '201-500 employees',
  '501-1000 employees',
  '1001-5000 employees',
  '5001-10000 employees',
  '10000+ employees',
];

const ORG_TYPES = [
  'Privately Held',
  'Public Company',
  'Partnership',
  'Government Agency',
  'Nonprofit',
  'Sole Proprietorship',
  'Self-Owned',
];

function slugify(name) {
  return name
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
}

export default function CreateCompanyPage() {
  const navigate = useNavigate();
  const [form, setForm] = useState({
    name: 'Rytera AI',
    slug: 'rytera-ai',
    slugEdited: true,
    website: '',
    industry: 'Insurance',
    company_size: '',
    organization_type: 'Privately Held',
    headquarters: '',
    about: '',
    specialties: 'AI, Insurance, InsurTech',
  });
  const [logoPreview, setLogoPreview] = useState('/brand/rytera-logo.png');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  function handleNameChange(e) {
    const name = e.target.value;
    setForm((prev) => ({
      ...prev,
      name,
      slug: prev.slugEdited ? prev.slug : slugify(name),
    }));
  }

  function handleSlugChange(e) {
    setForm((prev) => ({
      ...prev,
      slug: slugify(e.target.value),
      slugEdited: true,
    }));
  }

  function handleChange(e) {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError('');
    
    if (!form.name.trim()) return setError('Organization name is required');
    if (!form.slug.trim()) return setError('LinkedIn address is required');
    if (!form.industry.trim()) return setError('Industry is required');
    if (!form.company_size) return setError('Organization size is required');
    if (!form.organization_type) return setError('Organization type is required');
    
    setSubmitting(true);
    try {
      const payload = {
        name: form.name.trim(),
        slug: form.slug.trim(),
        website: form.website.trim() || null,
        industry: form.industry.trim(),
        company_size: form.company_size,
        organization_type: form.organization_type,
        headquarters: form.headquarters.trim() || null,
        about: form.about.trim() || 'Rytera AI is building intelligent insurance infrastructure with AI-powered underwriting, risk analysis, and automation.',
        specialties: form.specialties.trim() || null,
        logo_url: logoPreview || null,
      };
      
      const res = await fetch('/api/companies', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || 'Failed to create company page');
      }
      
      const company = await res.json();
      navigate(`/company/${company.slug}`);
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="mx-auto max-w-3xl px-4 py-8">
      <div className="mb-8">
        <h1 className="text-2xl font-semibold text-slate-100">Create a Company Page</h1>
        <p className="mt-1 text-sm text-slate-400">Tell us about your organization to create your LinkedIn-style company page.</p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="rounded-xl border border-white/5 bg-slate-900/60">
          <div className="border-b border-white/5 px-6 py-4">
            <h2 className="flex items-center gap-2 text-base font-medium text-slate-100"><Building2 className="h-4 w-4" />Page details</h2>
          </div>
          <div className="space-y-5 px-6 py-5">
            <div>
              <label className="mb-1.5 block text-sm font-medium text-slate-200">
                Name <span className="text-red-400">*</span>
              </label>
              <p className="mb-2 text-xs text-slate-500">Add your organization&apos;s name</p>
              <input
                type="text"
                name="name"
                value={form.name}
                onChange={handleNameChange}
                className="w-full rounded-lg border border-white/10 bg-slate-900/60 px-3 py-2 text-sm text-slate-100 focus:border-cyan-400/50 focus:outline-none focus:ring-1 focus:ring-cyan-400/30"
                required
              />
            </div>

            <div>
              <label className="mb-1.5 block text-sm font-medium text-slate-200">
                LinkedIn Page Public URL <span className="text-red-400">*</span>
              </label>
              <p className="mb-2 text-xs text-slate-500">Add your unique LinkedIn address</p>
              <div className="flex items-center rounded-lg border border-white/10 bg-slate-900/60 focus-within:border-cyan-400/50 focus-within:ring-1 focus-within:ring-cyan-400/30">
                <span className="flex items-center gap-1 px-3 text-sm text-slate-500">
                  <Hash className="h-3.5 w-3.5" />
                  linkedin.com/company/
                </span>
                <input
                  type="text"
                  value={form.slug}
                  onChange={handleSlugChange}
                  className="flex-1 bg-transparent px-1 py-2 text-sm text-slate-100 focus:outline-none"
                  required
                />
              </div>
              <p className="mt-1.5 text-xs text-slate-500">Preview: linkedin.com/company/{form.slug}</p>
            </div>

            <div>
              <label className="mb-1.5 block text-sm font-medium text-slate-200">Logo</label>
              <div className="flex items-center gap-4">
                <div className="flex h-20 w-20 items-center justify-center rounded-xl border border-white/10 bg-slate-900/60 overflow-hidden">
                  <img src={logoPreview} alt="Logo preview" className="h-full w-full object-contain" />
                </div>
                <div>
                  <p className="text-sm text-slate-300">Rytera AI logo</p>
                  <p className="text-xs text-slate-500">Using brand/rytera-logo.png</p>
                </div>
              </div>
            </div>

            <div>
              <label className="mb-1.5 block text-sm font-medium text-slate-200">Website</label>
              <p className="mb-2 text-xs text-slate-500">Begin with http://, https:// or www.</p>
              <div className="relative">
                <Globe className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
                <input
                  type="url"
                  name="website"
                  value={form.website}
                  onChange={handleChange}
                  placeholder="https://"
                  className="w-full rounded-lg border border-white/10 bg-slate-900/60 py-2 pl-9 pr-3 text-sm text-slate-100 placeholder:text-slate-600 focus:border-cyan-400/50 focus:outline-none focus:ring-1 focus:ring-cyan-400/30"
                />
              </div>
            </div>
          </div>
        </div>

        <div className="rounded-xl border border-white/5 bg-slate-900/60">
          <div className="border-b border-white/5 px-6 py-4">
            <h2 className="flex items-center gap-2 text-base font-medium text-slate-100"><Briefcase className="h-4 w-4" />Company info</h2>
          </div>
          <div className="space-y-5 px-6 py-5">
            <div>
              <label className="mb-1.5 block text-sm font-medium text-slate-200">
                Industry <span className="text-red-400">*</span>
              </label>
              <p className="mb-2 text-xs text-slate-500">ex: Information Services</p>
              <input
                type="text"
                name="industry"
                value={form.industry}
                onChange={handleChange}
                className="w-full rounded-lg border border-white/10 bg-slate-900/60 px-3 py-2 text-sm text-slate-100 focus:border-cyan-400/50 focus:outline-none focus:ring-1 focus:ring-cyan-400/30"
                required
              />
            </div>

            <div>
              <label className="mb-1.5 block text-sm font-medium text-slate-200">
                Organization size <span className="text-red-400">*</span>
              </label>
              <p className="mb-2 text-xs text-slate-500">Required</p>
              <select
                name="company_size"
                value={form.company_size}
                onChange={handleChange}
                className="w-full rounded-lg border border-white/10 bg-slate-900/60 px-3 py-2 text-sm text-slate-100 focus:border-cyan-400/50 focus:outline-none focus:ring-1 focus:ring-cyan-400/30"
                required
              >
                <option value="" disabled>Select size</option>
                {ORG_SIZES.map((size) => (
                  <option key={size} value={size}>{size}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="mb-1.5 block text-sm font-medium text-slate-200">
                Organization type <span className="text-red-400">*</span>
              </label>
              <p className="mb-2 text-xs text-slate-500">Required</p>
              <select
                name="organization_type"
                value={form.organization_type}
                onChange={handleChange}
                className="w-full rounded-lg border border-white/10 bg-slate-900/60 px-3 py-2 text-sm text-slate-100 focus:border-cyan-400/50 focus:outline-none focus:ring-1 focus:ring-cyan-400/30"
                required
              >
                {ORG_TYPES.map((type) => (
                  <option key={type} value={type}>{type}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="mb-1.5 block text-sm font-medium text-slate-200">Headquarters</label>
              <div className="relative">
                <MapPin className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
                <input
                  type="text"
                  name="headquarters"
                  value={form.headquarters}
                  onChange={handleChange}
                  placeholder="e.g. San Francisco, CA"
                  className="w-full rounded-lg border border-white/10 bg-slate-900/60 py-2 pl-9 pr-3 text-sm text-slate-100 placeholder:text-slate-600 focus:border-cyan-400/50 focus:outline-none focus:ring-1 focus:ring-cyan-400/30"
                />
              </div>
            </div>

            <div>
              <label className="mb-1.5 block text-sm font-medium text-slate-200">About</label>
              <div className="relative">
                <FileText className="absolute left-3 top-3 h-4 w-4 text-slate-500" />
                <textarea
                  name="about"
                  value={form.about}
                  onChange={handleChange}
                  rows={4}
                  className="w-full rounded-lg border border-white/10 bg-slate-900/60 py-2 pl-9 pr-3 text-sm text-slate-100 placeholder:text-slate-600 focus:border-cyan-400/50 focus:outline-none focus:ring-1 focus:ring-cyan-400/30"
                />
              </div>
            </div>

            <div>
              <label className="mb-1.5 block text-sm font-medium text-slate-200">Specialties</label>
              <p className="mb-2 text-xs text-slate-500">Separate with commas</p>
              <input
                type="text"
                name="specialties"
                value={form.specialties}
                onChange={handleChange}
                className="w-full rounded-lg border border-white/10 bg-slate-900/60 px-3 py-2 text-sm text-slate-100 focus:border-cyan-400/50 focus:outline-none focus:ring-1 focus:ring-cyan-400/30"
              />
            </div>
          </div>
        </div>

        {error && (
          <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-2 text-sm text-red-400">
            {error}
          </div>
        )}

        <div className="flex items-center justify-end gap-3">
          <button type="button" onClick={() => navigate(-1)} className="btn-secondary">
            Cancel
          </button>
          <button type="submit" disabled={submitting} className="btn-primary">
            {submitting ? 'Creating...' : 'Create page'}
          </button>
        </div>
      </form>
    </div>
  );
}
