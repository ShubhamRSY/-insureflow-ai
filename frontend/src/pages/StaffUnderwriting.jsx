import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  BookOpen, ClipboardCheck, GraduationCap, LineChart, RefreshCw, Scale, Search,
  ArrowRight, TrendingUp,
} from 'lucide-react';
import { Badge, EmptyState } from '../components/ui';
import { endpoints } from '../lib/api';

const TABS = [
  { id: 'overview', label: 'Overview', icon: Search },
  { id: 'market_research', label: 'Market', icon: Search },
  { id: 'coverage_development', label: 'Coverages', icon: Scale },
  { id: 'experience', label: 'Experience', icon: TrendingUp },
  { id: 'rating_reviews', label: 'Rating plans', icon: LineChart },
  { id: 'guides', label: 'UW guides', icon: BookOpen },
  { id: 'audits', label: 'UW audits', icon: ClipboardCheck },
  { id: 'training', label: 'Training', icon: GraduationCap },
];

export default function StaffUnderwriting() {
  const [tab, setTab] = useState('overview');
  const [overview, setOverview] = useState(null);
  const [items, setItems] = useState([]);
  const [experience, setExperience] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);

  const [researchForm, setResearchForm] = useState({ title: '', topic: 'product_mix', summary: '', recommendation: '' });
  const [guideForm, setGuideForm] = useState({ title: '', line_of_business: 'commercial_property', body: '', status: 'draft', version: '1.0' });
  const [auditForm, setAuditForm] = useState({ office: 'Southwest Regional', scope: 'Documentation, classification, rating, selection vs guide', files_reviewed: 12, findings: '' });
  const [trainForm, setTrainForm] = useState({ title: '', topic: 'technical_insurance', audience: 'line_uw', outline: '' });
  const [expForm, setExpForm] = useState({
    line_of_business: 'commercial_property',
    class_of_business: 'light manufacturing',
    territory: 'TX',
    earned_premium: 2500000,
    incurred_losses: 1750000,
    industry_loss_ratio: 0.65,
  });
  const [rateForm, setRateForm] = useState({
    line_of_business: 'commercial_property',
    advisory_org: 'ISO',
    summary: '',
    loss_cost_change_pct: 2.5,
    expense_load_pct: 28,
    profit_load_pct: 5,
    action: 'revise',
  });
  const [covForm, setCovForm] = useState({ title: '', change_type: 'endorsement', description: '' });

  const loadOverview = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      setOverview(await endpoints.staffOverview());
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  const loadSection = useCallback(async (section) => {
    if (section === 'overview' || section === 'experience') return;
    setLoading(true);
    setError('');
    try {
      const res = await endpoints.staffSection(section);
      setItems(res.items || []);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadOverview(); }, [loadOverview]);
  useEffect(() => { loadSection(tab); }, [tab, loadSection]);

  const refresh = async () => {
    await loadOverview();
    await loadSection(tab);
  };

  const run = async (fn) => {
    setSaving(true);
    setError('');
    try {
      await fn();
      await refresh();
    } catch (e) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="mx-auto max-w-6xl space-y-8 animate-fade-in">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-[10px] font-bold uppercase tracking-widest text-violet-400">Staff underwriter</p>
          <h1 className="mt-1 text-3xl font-bold tracking-tight">Home-office desk</h1>
          <p className="mt-1 max-w-2xl text-slate-400">
            Research markets, develop coverages, evaluate experience, revise rating plans, formulate policy, author guides, audit line files, and train line underwriters.
          </p>
        </div>
        <div className="flex gap-2">
          <Link to="/market" className="btn-secondary btn-sm text-xs">Market cycle <ArrowRight className="h-3.5 w-3.5" /></Link>
          <button type="button" onClick={refresh} className="btn-secondary btn-sm text-xs">
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} /> Refresh
          </button>
        </div>
      </div>

      {error && <div className="rounded-xl bg-red-500/10 px-4 py-3 text-sm text-red-300">{error}</div>}

      <div className="flex flex-wrap gap-2">
        {TABS.map((t) => {
          const Icon = t.icon;
          return (
            <button
              key={t.id}
              type="button"
              onClick={() => setTab(t.id)}
              className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold ${tab === t.id ? 'bg-brand/20 text-brand-light' : 'bg-white/5 text-slate-400 hover:text-slate-200'}`}
            >
              <Icon className="h-3.5 w-3.5" /> {t.label}
            </button>
          );
        })}
      </div>

      {tab === 'overview' && overview && (
        <div className="space-y-6">
          <div className="grid gap-3 sm:grid-cols-3 lg:grid-cols-4">
            {Object.entries(overview.counts || {}).map(([k, v]) => (
              <div key={k} className="glass-card px-4 py-3">
                <p className="text-[10px] uppercase tracking-wider text-slate-500">{k.replace(/_/g, ' ')}</p>
                <p className="mt-1 text-2xl font-bold">{v}</p>
              </div>
            ))}
          </div>
          <div className="glass-card p-5">
            <h2 className="font-semibold">Staff underwriting tasks</h2>
            <ul className="mt-3 grid gap-2 sm:grid-cols-2">
              {(overview.tasks || []).map((t) => (
                <li key={t} className="rounded-lg bg-surface-overlay px-3 py-2 text-sm text-slate-300">{t}</li>
              ))}
            </ul>
          </div>
        </div>
      )}

      {tab === 'market_research' && (
        <div className="grid gap-6 lg:grid-cols-2">
          <form className="glass-card space-y-3 p-5" onSubmit={(e) => { e.preventDefault(); run(() => endpoints.staffMarketResearch(researchForm).then(() => setResearchForm({ title: '', topic: 'product_mix', summary: '', recommendation: '' }))); }}>
            <h2 className="font-semibold">Research the market</h2>
            <input className="input w-full" placeholder="Title" required value={researchForm.title} onChange={(e) => setResearchForm({ ...researchForm, title: e.target.value })} />
            <select className="input w-full" value={researchForm.topic} onChange={(e) => setResearchForm({ ...researchForm, topic: e.target.value })}>
              <option value="target_market">Target market</option>
              <option value="state_expansion">State expansion</option>
              <option value="product_mix">Product mix</option>
              <option value="premium_volume">Premium volume</option>
              <option value="other">Other</option>
            </select>
            <textarea className="input min-h-[80px] w-full" placeholder="Summary" required value={researchForm.summary} onChange={(e) => setResearchForm({ ...researchForm, summary: e.target.value })} />
            <textarea className="input min-h-[60px] w-full" placeholder="Recommendation" value={researchForm.recommendation} onChange={(e) => setResearchForm({ ...researchForm, recommendation: e.target.value })} />
            <button type="submit" disabled={saving} className="btn-primary text-sm">Save research note</button>
          </form>
          <ItemList items={items} empty="No market research notes yet" />
        </div>
      )}

      {tab === 'coverage_development' && (
        <div className="grid gap-6 lg:grid-cols-2">
          <form className="glass-card space-y-3 p-5" onSubmit={(e) => { e.preventDefault(); run(() => endpoints.staffCoverageDev(covForm).then(() => setCovForm({ title: '', change_type: 'endorsement', description: '' }))); }}>
            <h2 className="font-semibold">Develop coverages</h2>
            <input className="input w-full" placeholder="Title" required value={covForm.title} onChange={(e) => setCovForm({ ...covForm, title: e.target.value })} />
            <select className="input w-full" value={covForm.change_type} onChange={(e) => setCovForm({ ...covForm, change_type: e.target.value })}>
              <option value="form_mod">Form modification</option>
              <option value="endorsement">Endorsement</option>
              <option value="regulatory">Regulatory</option>
              <option value="association">Association / ISO committee</option>
            </select>
            <textarea className="input min-h-[100px] w-full" placeholder="Description" required value={covForm.description} onChange={(e) => setCovForm({ ...covForm, description: e.target.value })} />
            <button type="submit" disabled={saving} className="btn-primary text-sm">Propose coverage change</button>
          </form>
          <ItemList items={items} empty="No coverage development items" />
        </div>
      )}

      {tab === 'experience' && (
        <div className="grid gap-6 lg:grid-cols-2">
          <form className="glass-card space-y-3 p-5" onSubmit={async (e) => {
            e.preventDefault();
            setSaving(true);
            setError('');
            try {
              setExperience(await endpoints.staffExperience(expForm));
            } catch (err) {
              setError(err.message);
            } finally {
              setSaving(false);
            }
          }}>
            <h2 className="font-semibold">Evaluate underwriting experience</h2>
            <input className="input w-full" placeholder="Line of business" value={expForm.line_of_business} onChange={(e) => setExpForm({ ...expForm, line_of_business: e.target.value })} />
            <input className="input w-full" placeholder="Class" value={expForm.class_of_business} onChange={(e) => setExpForm({ ...expForm, class_of_business: e.target.value })} />
            <input className="input w-full" placeholder="Territory" value={expForm.territory} onChange={(e) => setExpForm({ ...expForm, territory: e.target.value })} />
            <div className="grid grid-cols-2 gap-2">
              <input className="input" type="number" placeholder="Earned premium" value={expForm.earned_premium} onChange={(e) => setExpForm({ ...expForm, earned_premium: Number(e.target.value) })} />
              <input className="input" type="number" placeholder="Incurred losses" value={expForm.incurred_losses} onChange={(e) => setExpForm({ ...expForm, incurred_losses: Number(e.target.value) })} />
            </div>
            <button type="submit" disabled={saving} className="btn-primary text-sm">Analyze experience</button>
          </form>
          {experience ? (
            <div className="glass-card space-y-3 p-5">
              <Badge>{experience.strategy}</Badge>
              <p className="text-2xl font-bold">LR {(experience.loss_ratio * 100).toFixed(1)}%</p>
              <p className="text-sm text-slate-400">Industry {(experience.industry_loss_ratio * 100).toFixed(1)}% · Δ {(experience.delta_vs_industry * 100).toFixed(1)} pts</p>
              <p className="text-sm text-slate-300">{experience.narrative}</p>
            </div>
          ) : (
            <EmptyState icon={TrendingUp} title="Run an experience slice" description="Compare book loss ratio to industry by line, class, and territory." />
          )}
        </div>
      )}

      {tab === 'rating_reviews' && (
        <div className="grid gap-6 lg:grid-cols-2">
          <form className="glass-card space-y-3 p-5" onSubmit={(e) => { e.preventDefault(); run(() => endpoints.staffRatingPlans(rateForm)); }}>
            <h2 className="font-semibold">Review rating plans</h2>
            <p className="text-xs text-slate-500">Combine ISO / AAIS / NCCI loss costs with expense and profit loads.</p>
            <input className="input w-full" placeholder="Line of business" value={rateForm.line_of_business} onChange={(e) => setRateForm({ ...rateForm, line_of_business: e.target.value })} />
            <select className="input w-full" value={rateForm.advisory_org} onChange={(e) => setRateForm({ ...rateForm, advisory_org: e.target.value })}>
              <option value="ISO">ISO</option>
              <option value="AAIS">AAIS</option>
              <option value="NCCI">NCCI</option>
              <option value="independent">Independent</option>
            </select>
            <textarea className="input min-h-[70px] w-full" placeholder="Summary" required value={rateForm.summary} onChange={(e) => setRateForm({ ...rateForm, summary: e.target.value })} />
            <div className="grid grid-cols-3 gap-2">
              <input className="input" type="number" step="0.1" title="Loss cost Δ%" value={rateForm.loss_cost_change_pct} onChange={(e) => setRateForm({ ...rateForm, loss_cost_change_pct: Number(e.target.value) })} />
              <input className="input" type="number" step="0.1" title="Expense %" value={rateForm.expense_load_pct} onChange={(e) => setRateForm({ ...rateForm, expense_load_pct: Number(e.target.value) })} />
              <input className="input" type="number" step="0.1" title="Profit %" value={rateForm.profit_load_pct} onChange={(e) => setRateForm({ ...rateForm, profit_load_pct: Number(e.target.value) })} />
            </div>
            <button type="submit" disabled={saving} className="btn-primary text-sm">Record rating review</button>
          </form>
          <ItemList items={items} empty="No rating plan reviews" />
        </div>
      )}

      {tab === 'guides' && (
        <div className="grid gap-6 lg:grid-cols-2">
          <form className="glass-card space-y-3 p-5" onSubmit={(e) => { e.preventDefault(); run(() => endpoints.staffGuides(guideForm).then(() => setGuideForm({ title: '', line_of_business: 'commercial_property', body: '', status: 'draft', version: '1.0' }))); }}>
            <h2 className="font-semibold">Develop underwriting guides</h2>
            <input className="input w-full" placeholder="Title" required value={guideForm.title} onChange={(e) => setGuideForm({ ...guideForm, title: e.target.value })} />
            <input className="input w-full" placeholder="Line of business" value={guideForm.line_of_business} onChange={(e) => setGuideForm({ ...guideForm, line_of_business: e.target.value })} />
            <textarea className="input min-h-[120px] w-full" placeholder="Guide body" required value={guideForm.body} onChange={(e) => setGuideForm({ ...guideForm, body: e.target.value })} />
            <div className="grid grid-cols-2 gap-2">
              <select className="input" value={guideForm.status} onChange={(e) => setGuideForm({ ...guideForm, status: e.target.value })}>
                <option value="draft">Draft</option>
                <option value="published">Published</option>
                <option value="archived">Archived</option>
              </select>
              <input className="input" placeholder="Version" value={guideForm.version} onChange={(e) => setGuideForm({ ...guideForm, version: e.target.value })} />
            </div>
            <button type="submit" disabled={saving} className="btn-primary text-sm">Publish / save guide</button>
          </form>
          <ItemList items={items} empty="No guides yet" />
        </div>
      )}

      {tab === 'audits' && (
        <div className="grid gap-6 lg:grid-cols-2">
          <form className="glass-card space-y-3 p-5" onSubmit={(e) => {
            e.preventDefault();
            const findings = auditForm.findings
              ? auditForm.findings.split('\n').filter(Boolean).map((line) => ({ severity: 'minor', category: 'documentation', detail: line }))
              : [];
            run(() => endpoints.staffAudits({
              office: auditForm.office,
              scope: auditForm.scope,
              files_reviewed: Number(auditForm.files_reviewed) || 0,
              findings,
            }));
          }}>
            <h2 className="font-semibold">Conduct underwriting audit</h2>
            <p className="text-xs text-slate-500">Visit branch files for documentation, classification, rating, and selection vs guide.</p>
            <input className="input w-full" placeholder="Office" value={auditForm.office} onChange={(e) => setAuditForm({ ...auditForm, office: e.target.value })} />
            <input className="input w-full" type="number" placeholder="Files reviewed" value={auditForm.files_reviewed} onChange={(e) => setAuditForm({ ...auditForm, files_reviewed: e.target.value })} />
            <textarea className="input min-h-[60px] w-full" placeholder="Scope" value={auditForm.scope} onChange={(e) => setAuditForm({ ...auditForm, scope: e.target.value })} />
            <textarea className="input min-h-[80px] w-full" placeholder="Findings (one per line)" value={auditForm.findings} onChange={(e) => setAuditForm({ ...auditForm, findings: e.target.value })} />
            <button type="submit" disabled={saving} className="btn-primary text-sm">Record audit</button>
          </form>
          <ItemList items={items} empty="No underwriting audits yet" />
        </div>
      )}

      {tab === 'training' && (
        <div className="grid gap-6 lg:grid-cols-2">
          <form className="glass-card space-y-3 p-5" onSubmit={(e) => { e.preventDefault(); run(() => endpoints.staffTraining(trainForm).then(() => setTrainForm({ title: '', topic: 'technical_insurance', audience: 'line_uw', outline: '' }))); }}>
            <h2 className="font-semibold">Education & training</h2>
            <input className="input w-full" placeholder="Module title" required value={trainForm.title} onChange={(e) => setTrainForm({ ...trainForm, title: e.target.value })} />
            <select className="input w-full" value={trainForm.audience} onChange={(e) => setTrainForm({ ...trainForm, audience: e.target.value })}>
              <option value="line_uw">Line underwriters</option>
              <option value="producers">Producers</option>
              <option value="all">All</option>
            </select>
            <textarea className="input min-h-[100px] w-full" placeholder="Outline" required value={trainForm.outline} onChange={(e) => setTrainForm({ ...trainForm, outline: e.target.value })} />
            <button type="submit" disabled={saving} className="btn-primary text-sm">Add training module</button>
          </form>
          <ItemList items={items} empty="No training modules" />
        </div>
      )}
    </div>
  );
}

function ItemList({ items, empty }) {
  if (!items?.length) {
    return <EmptyState icon={BookOpen} title={empty} description="New items appear after you save." />;
  }
  return (
    <div className="space-y-2">
      {items.slice().reverse().map((item) => {
        const key = item.note_id || item.item_id || item.review_id || item.guide_id || item.audit_id || item.module_id || item.policy_id || JSON.stringify(item).slice(0, 40);
        const title = item.title || item.office || item.line_of_business || key;
        return (
          <div key={key} className="glass-card px-4 py-3">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-sm font-medium">{title}</span>
              {item.status && <Badge>{item.status}</Badge>}
              {item.topic && <Badge>{item.topic}</Badge>}
              {item.advisory_org && <Badge>{item.advisory_org}</Badge>}
              {typeof item.compliant_pct === 'number' && <Badge>{item.compliant_pct}% compliant</Badge>}
            </div>
            <p className="mt-1 text-xs text-slate-500 line-clamp-3">
              {item.summary || item.description || item.body || item.outline || item.scope || ''}
            </p>
          </div>
        );
      })}
    </div>
  );
}
