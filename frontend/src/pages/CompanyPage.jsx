import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { Building2, Globe, MapPin, Users, Briefcase, ExternalLink } from 'lucide-react';

export default function CompanyPage() {
  const { slug } = useParams();
  const [company, setCompany] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        setLoading(true);
        setError(null);
        const res = await fetch(`/api/companies/${slug}`);
        if (!res.ok) {
          throw new Error(res.status === 404 ? 'Company not found' : 'Failed to load company');
        }
        const data = await res.json();
        if (!cancelled) setCompany(data);
      } catch (e) {
        if (!cancelled) setError(e.message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, [slug]);

  if (loading) {
    return (
      <div className="mx-auto max-w-5xl px-4 py-10">
        <div className="animate-pulse">
          <div className="h-40 w-full rounded-xl bg-slate-800/60" />
          <div className="-mt-12 flex items-end gap-4 px-6">
            <div className="h-24 w-24 rounded-xl bg-slate-700" />
            <div className="mb-2 space-y-2">
              <div className="h-6 w-48 rounded bg-slate-700" />
              <div className="h-4 w-32 rounded bg-slate-800" />
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (error || !company) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-16 text-center">
        <Building2 className="mx-auto h-10 w-10 text-slate-500" />
        <h1 className="mt-4 text-xl font-semibold text-slate-200">{error || 'Company not found'}</h1>
        <p className="mt-2 text-sm text-slate-400">This company page doesn&apos;t exist or hasn&apos;t been created yet.</p>
        <Link to="/" className="btn-primary mt-6 inline-flex">Back to Overview</Link>
      </div>
    );
  }

  const specialties = Array.isArray(company.specialties)
    ? company.specialties
    : typeof company.specialties === 'string' && company.specialties.trim()
      ? company.specialties.split(',').map(s => s.trim()).filter(Boolean)
      : [];

  return (
    <div className="mx-auto max-w-6xl px-4 py-6">
      {/* Cover + header */}
      <div className="overflow-hidden rounded-xl border border-white/5 bg-gradient-to-b from-slate-800/80 to-slate-900/80">
        <div className="h-40 w-full bg-gradient-to-r from-cyan-500/10 via-sky-500/10 to-indigo-500/10" />
        <div className="relative px-6 pb-6">
          <div className="absolute -top-12 flex h-24 w-24 items-center justify-center rounded-xl border border-white/10 bg-slate-900 shadow-lg">
            {company.logo_url ? (
              <img src={company.logo_url} alt={company.name} className="h-16 w-16 rounded-lg object-contain" />
            ) : (
              <Building2 className="h-10 w-10 text-slate-400" />
            )}
          </div>
          <div className="ml-28 flex flex-wrap items-start justify-between gap-4 pt-2">
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-2xl font-semibold text-slate-100">{company.name}</h1>
                {company.is_verified && (
                  <span className="rounded-full bg-cyan-400/10 px-2 py-0.5 text-xs text-cyan-300">Verified</span>
                )}
              </div>
              <div className="mt-1 flex flex-wrap items-center gap-3 text-sm text-slate-400">
                {company.industry && <span className="flex items-center gap-1"><Briefcase className="h-3.5 w-3.5" />{company.industry}</span>}
                {company.headquarters && <span className="flex items-center gap-1"><MapPin className="h-3.5 w-3.5" />{company.headquarters}</span>}
                {company.company_size && <span className="flex items-center gap-1"><Users className="h-3.5 w-3.5" />{company.company_size} employees</span>}
              </div>
            </div>
            {company.website && (
              <a href={company.website} target="_blank" rel="noreferrer" className="btn-secondary inline-flex items-center gap-2">
                Visit website <ExternalLink className="h-4 w-4" />
              </a>
            )}
          </div>
        </div>
      </div>

      {/* Body */}
      <div className="mt-6 grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2 space-y-6">
          <div className="rounded-xl border border-white/5 bg-slate-900/60">
            <div className="border-b border-white/5 px-6 py-4">
              <h2 className="text-base font-medium text-slate-100">About</h2>
            </div>
            <div className="px-6 py-5">
              {company.about ? (
                <p className="whitespace-pre-wrap text-sm leading-relaxed text-slate-300">{company.about}</p>
              ) : (
                <p className="text-sm text-slate-500">No description added yet.</p>
              )}
              {specialties.length > 0 && (
                <div className="mt-4">
                  <p className="text-xs uppercase tracking-wide text-slate-500">Specialties</p>
                  <div className="mt-2 flex flex-wrap gap-2">
                    {specialties.map((tag) => (
                      <span key={tag} className="rounded-full border border-white/10 px-2.5 py-1 text-xs text-slate-300">{tag}</span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        <div className="space-y-6">
          <div className="rounded-xl border border-white/5 bg-slate-900/60">
            <div className="border-b border-white/5 px-6 py-4">
              <h2 className="text-base font-medium text-slate-100">Company details</h2>
            </div>
            <div className="space-y-3 px-6 py-5 text-sm">
              {company.website && (
                <div>
                  <p className="text-xs text-slate-500">Website</p>
                  <a href={company.website} target="_blank" rel="noreferrer" className="mt-1 inline-flex items-center gap-1 text-cyan-300 hover:underline">
                    <Globe className="h-3.5 w-3.5" /> {company.website.replace(/^https?:\/\//, '')}
                  </a>
                </div>
              )}
              {company.industry && (
                <div>
                  <p className="text-xs text-slate-500">Industry</p>
                  <p className="mt-1 text-slate-300">{company.industry}</p>
                </div>
              )}
              {company.company_size && (
                <div>
                  <p className="text-xs text-slate-500">Company size</p>
                  <p className="mt-1 text-slate-300">{company.company_size}</p>
                </div>
              )}
              {company.headquarters && (
                <div>
                  <p className="text-xs text-slate-500">Headquarters</p>
                  <p className="mt-1 text-slate-300">{company.headquarters}</p>
                </div>
              )}
              {!company.website && !company.industry && !company.company_size && !company.headquarters && (
                <p className="text-slate-500">No details added yet.</p>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
