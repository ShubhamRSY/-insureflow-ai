import { useCallback, useEffect, useState } from 'react';
import { BrowserRouter, Routes, Route, Navigate, Link, useNavigate, useParams } from 'react-router-dom';
import { StateProvider } from './lib/useStateContext';
import Layout from './components/Layout';
import LoginModal from './components/LoginModal';
import SignupPage from './pages/SignupPage';
import JobDrawer from './components/JobDrawer';
import FreemiumBanner from './components/FreemiumBanner';
import Overview from './pages/Overview';
import SsoCallback from './pages/SsoCallback';
import SystemPage from './pages/System';
import InsurancePage from './pages/Insurance';
import CommercialInsuranceHub from './pages/CommercialInsurance';
import CommercialReference from './pages/CommercialReference';
import CommercialLinePage from './pages/CommercialLine';
import LifeInsuranceHub from './pages/LifeInsurance';
import LifeLinePage from './pages/LifeLine';
import HealthInsuranceHub from './pages/HealthInsurance';
import HealthLinePage from './pages/HealthLine';
import GeneralInsuranceHub from './pages/GeneralInsurance';
import GeneralLinePage from './pages/GeneralLine';
import InsuranceSegmentPage from './pages/InsuranceSegment';
import MortgagePage from './pages/Mortgage';
import LendingPage from './pages/Lending';
import WorkflowPage from './pages/Workflow';
import UWWorkbench from './pages/UWWorkbench';
import UWDashboard from './pages/UWDashboard';
import SettingsPage from './pages/Settings';
import RegulatoryReviewPage from './pages/RegulatoryReview';
import BrokerStatusPage from './pages/BrokerStatus';
import AuthorityMatrix from './pages/AuthorityMatrix';
import MarketAdmin from './pages/MarketAdmin';
import RenewalDashboard from './pages/RenewalDashboard';
import RegistryPage from './pages/Registry';
import QueuePage from './pages/Queue';
import OverrideAnalyticsPage from './pages/OverrideAnalytics';
import EvalTrendsPage from './pages/EvalTrends';
import PortfolioPage from './pages/Portfolio';
import IntegrationsPage from './pages/Integrations';
import WebhooksPage from './pages/Webhooks';
import InsuranceJobDetail from './pages/InsuranceJobDetail';
import PilotPage from './pages/Pilot';
import IssuancePage from './pages/Issuance';
import MonitoringPage from './pages/Monitoring';
import ProducerCommsPage from './pages/ProducerComms';
import LineUnderwriting from './pages/LineUnderwriting';
import StaffUnderwriting from './pages/StaffUnderwriting';
import RatemakingPage from './pages/Ratemaking';
import BusinessKPIsPage from './pages/BusinessKPIs';
import PriorDecisionsPage from './pages/PriorDecisions';
import ErrorBoundary from './components/ErrorBoundary';
import { auth, endpoints, AuthError } from './lib/api';
import { useFreemium } from './lib/useFreemium';

function Protected({ children, onLogin }) {
  if (!auth.isLoggedIn) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-center">
        <p className="text-lg text-slate-300">Authentication required</p>
        <button type="button" onClick={onLogin} className="btn-primary mt-4">Sign In</button>
      </div>
    );
  }
  return children;
}

// In-app landing for disabled or unknown routes. Stays inside the dashboard
// (no redirect to the marketing site, no silent history replacement), so the
// browser Back button keeps working predictably.
function PlaceholderPage({ title, message }) {
  return (
    <div className="flex flex-col items-center justify-center py-24 text-center">
      <p className="text-lg text-slate-200">{title}</p>
      <p className="mt-1 max-w-md text-sm text-slate-400">{message}</p>
      <Link to="/" className="btn-primary mt-6">Back to Overview</Link>
    </div>
  );
}

function AppRoutes() {
  const navigate = useNavigate();
  const [user, setUser] = useState(auth.user);
  const [loginOpen, setLoginOpen] = useState(false);
  const [health, setHealth] = useState(null);
  const [presets, setPresets] = useState(null);
  const [overview, setOverview] = useState(null);
  const [insuranceJobs, setInsuranceJobs] = useState([]);
  const [mortgageJobs, setMortgageJobs] = useState([]);
  const [pending, setPending] = useState([]);
  const [marketCycle, setMarketCycle] = useState(null);
  const [queueStats, setQueueStats] = useState(null);
  const [authorityData, setAuthorityData] = useState(null);
  const [lendingDemoResult, setLendingDemoResult] = useState(null);
  const [drawer, setDrawer] = useState({ vertical: null, jobId: null, job: null });
  const [welcomeMessage, setWelcomeMessage] = useState('');
  const { remaining, isLimited, trackView, DAILY_LIMIT } = useFreemium(auth.isLoggedIn);

  const loadHealth = useCallback(async () => {
    try { setHealth(await endpoints.diagnostics()); } catch { /* ignore */ }
  }, []);

  const loadPresets = useCallback(async () => {
    try { setPresets(await endpoints.presets()); } catch { /* ignore */ }
  }, []);

  const handleAuthError = useCallback(() => {
    auth.wipeSession();
    setUser(null);
    setLoginOpen(true);
    setDrawer({ vertical: null, jobId: null, job: null });
  }, []);

  const loadOverview = useCallback(async () => {
    if (!auth.isLoggedIn) return;
    try {
      const data = await endpoints.overview();
      setOverview(data);
      setPending(data.pending || []);
    } catch (e) {
      if (e instanceof AuthError) handleAuthError();
    }
  }, [handleAuthError]);

  const loadMarketCycle = useCallback(async () => {
    if (!auth.isLoggedIn) return;
    try { setMarketCycle(await endpoints.marketCycle()); }
    catch { /* ignore */ }
  }, []);

  const loadQueueStats = useCallback(async () => {
    if (!auth.isLoggedIn) return;
    try { setQueueStats(await endpoints.submissionQueue()); }
    catch { /* ignore */ }
  }, []);

  const loadAuthority = useCallback(async () => {
    if (!auth.isLoggedIn) return;
    try { setAuthorityData(await endpoints.authorityMatrix()); }
    catch { /* ignore */ }
  }, []);

  const loadInsuranceJobs = useCallback(async () => {
    try {
      const { jobs } = await endpoints.insuranceJobs();
      const rows = await Promise.all(
        (jobs || []).map(async (id) => {
          try { return { id, job: await endpoints.insuranceJob(id) }; }
          catch (e) {
            if (e instanceof AuthError) throw e;
            return { id, job: { status: 'unknown' } };
          }
        }),
      );
      setInsuranceJobs(rows);
    } catch (e) {
      if (e instanceof AuthError) handleAuthError();
    }
  }, [handleAuthError]);

  const loadMortgageJobs = useCallback(async () => {
    if (!auth.isLoggedIn) return;
    try {
      const { jobs } = await endpoints.mortgageJobs();
      const rows = await Promise.all(
        (jobs || []).map(async (id) => {
          try { return { id, job: await endpoints.mortgageJob(id) }; }
          catch (e) {
            if (e instanceof AuthError) throw e;
            return { id, job: { status: 'unknown' } };
          }
        }),
      );
      setMortgageJobs(rows);
    } catch (e) {
      if (e instanceof AuthError) handleAuthError();
    }
  }, [handleAuthError]);

  const refreshAll = useCallback(async () => {
    await Promise.all([loadHealth(), loadPresets(), loadOverview(), loadInsuranceJobs(), loadMortgageJobs(), loadMarketCycle(), loadQueueStats(), loadAuthority()]);
  }, [loadHealth, loadPresets, loadOverview, loadInsuranceJobs, loadMortgageJobs, loadMarketCycle, loadQueueStats, loadAuthority]);

  useEffect(() => {
    endpoints.authStatus().then((s) => {
      if (s.setup_required) {
        auth.wipeSession();
        setUser(null);
      }
    }).catch(() => {});
  }, []);

  useEffect(() => {
    refreshAll();
    if (auth.isLoggedIn) {
      endpoints.me().then(setUser).catch((e) => {
        auth.clear();
        setUser(null);
        if (e instanceof AuthError) setLoginOpen(true);
      });
    }
    const iv = setInterval(loadHealth, 60000);
    return () => clearInterval(iv);
  }, [refreshAll, loadHealth]);

  useEffect(() => {
    if (!drawer.jobId || drawer.job?.status !== 'processing') return;
    const iv = setInterval(async () => {
      try {
        const fetch = drawer.vertical === 'insurance' ? endpoints.insuranceJob : endpoints.mortgageJob;
        const job = await fetch(drawer.jobId);
        setDrawer((d) => ({ ...d, job }));
        if (job.status !== 'processing') refreshAll();
      } catch (e) {
        if (e instanceof AuthError) {
          handleAuthError();
        }
      }
    }, 3000);
    return () => clearInterval(iv);
  }, [drawer.jobId, drawer.vertical, drawer.job?.status, refreshAll, handleAuthError]);

  const openJob = async (vertical, jobId, bundleId) => {
    const actualJobId = bundleId
      ? (insuranceJobs.find(r => r.job?.results?.bundle_id === bundleId)?.id || jobId)
      : jobId;
    if (vertical === 'insurance') {
      navigate(`/insurance/${actualJobId}`);
      return;
    }
    try {
      const job = await endpoints.mortgageJob(actualJobId);
      setDrawer({ vertical, jobId: actualJobId, job });
    } catch (e) {
      if (e instanceof AuthError) handleAuthError();
      else throw e;
    }
  };

  const runDemo = async (vertical, presetId) => {
    if (!auth.isLoggedIn) { setLoginOpen(true); return; }
    if (isLimited) { setLoginOpen(true); return; }
    try {
      if (vertical === 'lending') {
        const res = await endpoints.runLendingDemo(presetId);
        setLendingDemoResult(res);
        navigate('/');
        return;
      }
      const res = vertical === 'insurance'
        ? await endpoints.runInsuranceDemo(presetId)
        : await endpoints.runMortgageDemo(presetId);
      if (!res?.job_id) throw new Error('Sample run did not return a job id');
      await refreshAll();
      if (vertical === 'insurance') {
        navigate(`/insurance/${res.job_id}`);
      } else {
        navigate('/');
        openJob('mortgage', res.job_id);
      }
    } catch (e) {
      if (e instanceof AuthError) handleAuthError();
      throw e;
    }
  };

  const submitInsurance = async (body) => {
    try {
      if (body._jobId) {
        navigate(`/insurance/${body._jobId}`);
        return;
      }
      const res = await endpoints.runInsurance(body);
      await loadInsuranceJobs();
      navigate(`/insurance/${res.job_id}`);
    } catch (e) {
      if (e instanceof AuthError) handleAuthError();
      throw e;
    }
  };

  const deleteInsuranceJob = async (jobId) => {
    setInsuranceJobs((prev) => prev.filter((r) => r.id !== jobId));
    try {
      await endpoints.deleteJob(jobId);
    } catch (e) {
      if (e instanceof AuthError) {
        handleAuthError();
        return;
      }
      await loadInsuranceJobs();
      throw e;
    }
  };

  const deleteAllInsuranceJobs = async (ids) => {
    const list = ids?.length ? ids : insuranceJobs.map((r) => r.id);
    setInsuranceJobs((prev) => prev.filter((r) => !list.includes(r.id)));
    try {
      await Promise.all(list.map((id) => endpoints.deleteJob(id).catch(() => {})));
      await loadInsuranceJobs();
    } catch (e) {
      if (e instanceof AuthError) handleAuthError();
      else {
        await loadInsuranceJobs();
        throw e;
      }
    }
  };

  const submitMortgage = async (body) => {
    const res = await endpoints.runMortgage(body);
    await loadMortgageJobs();
    openJob('mortgage', res.job_id);
  };

  const runMortgageConnect = async (jobId) => {
    await refreshAll();
    openJob('mortgage', jobId);
  };

  return (
    <>
      <FreemiumBanner remaining={remaining} DAILY_LIMIT={DAILY_LIMIT} onLogin={() => setLoginOpen(true)} isLoggedIn={auth.isLoggedIn} />
      <Routes>
        <Route path="broker/status/:token" element={<BrokerStatusPage />} />
        <Route path="signup" element={<SignupPage />} />
        <Route path="sso/callback" element={<SsoCallback />} />
          <Route element={<Layout health={health} pendingCount={pending.length} onRefresh={refreshAll} onLogin={() => setLoginOpen(true)} user={user} setUser={setUser} isLimited={isLimited} welcomeMessage={welcomeMessage} onDismissWelcome={() => setWelcomeMessage('')} />}>
          <Route index element={<Overview overview={overview} health={health} presets={presets} onRunDemo={runDemo} onOpenJob={openJob} onLogin={() => setLoginOpen(true)} marketCycle={marketCycle} queueStats={queueStats} insuranceJobs={insuranceJobs} isLimited={isLimited} remaining={remaining} trackView={trackView} />} />
          <Route path="system" element={<SystemPage health={health} />} />
          <Route path="reference/commercial" element={<Protected onLogin={() => setLoginOpen(true)}><CommercialReference /></Protected>} />
          <Route path="reference" element={<Navigate to="/reference/commercial" replace />} />
          <Route path="insurance/commercial/guides" element={<Navigate to="/reference/commercial" replace />} />
          <Route path="insurance/commercial/:lobSlug" element={<Protected onLogin={() => setLoginOpen(true)}><CommercialLinePage presets={presets} onRunDemo={runDemo} onSubmit={submitInsurance} /></Protected>} />
          <Route path="insurance/commercial" element={<Protected onLogin={() => setLoginOpen(true)}><CommercialInsuranceHub presets={presets} onRunDemo={runDemo} onSubmit={submitInsurance} jobs={insuranceJobs} onDeleteJob={deleteInsuranceJob} onDeleteAllJobs={deleteAllInsuranceJobs} /></Protected>} />
          <Route path="insurance/life/:lobSlug" element={<Protected onLogin={() => setLoginOpen(true)}><LifeLinePage presets={presets} onRunDemo={runDemo} onSubmit={submitInsurance} /></Protected>} />
          <Route path="insurance/life" element={<Protected onLogin={() => setLoginOpen(true)}><LifeInsuranceHub presets={presets} onRunDemo={runDemo} onSubmit={submitInsurance} jobs={insuranceJobs} onDeleteJob={deleteInsuranceJob} onDeleteAllJobs={deleteAllInsuranceJobs} /></Protected>} />
          <Route path="insurance/health/:lobSlug" element={<Protected onLogin={() => setLoginOpen(true)}><HealthLinePage presets={presets} onRunDemo={runDemo} onSubmit={submitInsurance} /></Protected>} />
          <Route path="insurance/health" element={<Protected onLogin={() => setLoginOpen(true)}><HealthInsuranceHub presets={presets} onRunDemo={runDemo} onSubmit={submitInsurance} jobs={insuranceJobs} onDeleteJob={deleteInsuranceJob} onDeleteAllJobs={deleteAllInsuranceJobs} /></Protected>} />
          <Route path="insurance/general/:lobSlug" element={<Protected onLogin={() => setLoginOpen(true)}><GeneralLinePage presets={presets} onRunDemo={runDemo} onSubmit={submitInsurance} /></Protected>} />
          <Route path="insurance/general" element={<Protected onLogin={() => setLoginOpen(true)}><GeneralInsuranceHub presets={presets} onRunDemo={runDemo} onSubmit={submitInsurance} jobs={insuranceJobs} onDeleteJob={deleteInsuranceJob} onDeleteAllJobs={deleteAllInsuranceJobs} /></Protected>} />
          <Route path="insurance/sections/:sectionId" element={<Protected onLogin={() => setLoginOpen(true)}><InsuranceSegmentPage /></Protected>} />
          <Route path="insurance/:jobId" element={<Protected onLogin={() => setLoginOpen(true)}><InsuranceJobDetail onDeleted={loadInsuranceJobs} onDeleteJob={deleteInsuranceJob} /></Protected>} />
          <Route path="insurance" element={<Protected onLogin={() => setLoginOpen(true)}><InsurancePage presets={presets} jobs={insuranceJobs} onRunDemo={runDemo} onOpenJob={openJob} onSubmit={submitInsurance} onRefresh={loadInsuranceJobs} onDeleteJob={deleteInsuranceJob} onDeleteAllJobs={deleteAllInsuranceJobs} /></Protected>} />
          <Route path="line-uw" element={<Protected onLogin={() => setLoginOpen(true)}><LineUnderwriting /></Protected>} />
          <Route path="staff-uw" element={<Protected onLogin={() => setLoginOpen(true)}><StaffUnderwriting /></Protected>} />
          <Route path="pilot" element={<Protected onLogin={() => setLoginOpen(true)}><PilotPage /></Protected>} />
          <Route path="mortgage" element={<PlaceholderPage title="Mortgage is coming soon" message="Rytera currently underwrites insurance lines. Mortgage decisioning will open here." />} />
          <Route path="lending" element={<PlaceholderPage title="Lending is coming soon" message="Rytera currently underwrites insurance lines. Lending decisioning will open here." />} />
          <Route path="workflow" element={<Protected onLogin={() => setLoginOpen(true)}><WorkflowPage pending={pending} onRefresh={loadOverview} onOpenJob={openJob} authorityData={authorityData} /></Protected>} />
          <Route path="uw-workbench" element={<Protected onLogin={() => setLoginOpen(true)}><UWWorkbench onOpenJob={openJob} authorityData={authorityData} onRefresh={refreshAll} /></Protected>} />
          <Route path="uw-dashboard" element={<Protected onLogin={() => setLoginOpen(true)}><UWDashboard onOpenJob={openJob} /></Protected>} />
          <Route path="prior-decisions" element={<Protected onLogin={() => setLoginOpen(true)}><PriorDecisionsPage /></Protected>} />
          <Route path="issuance" element={<Protected onLogin={() => setLoginOpen(true)}><IssuancePage /></Protected>} />
          <Route path="producer-comms" element={<Protected onLogin={() => setLoginOpen(true)}><ProducerCommsPage /></Protected>} />
          <Route path="monitoring" element={<Protected onLogin={() => setLoginOpen(true)}><MonitoringPage /></Protected>} />
          <Route path="renewals" element={<Protected onLogin={() => setLoginOpen(true)}><RenewalDashboard /></Protected>} />
          <Route path="overrides" element={<Protected onLogin={() => setLoginOpen(true)}><OverrideAnalyticsPage /></Protected>} />
          <Route path="business-kpis" element={<Protected onLogin={() => setLoginOpen(true)}><BusinessKPIsPage /></Protected>} />
          <Route path="eval-trends" element={<Protected onLogin={() => setLoginOpen(true)}><EvalTrendsPage /></Protected>} />
          <Route path="portfolio" element={<Protected onLogin={() => setLoginOpen(true)}><PortfolioPage /></Protected>} />
          <Route path="ratemaking" element={<Protected onLogin={() => setLoginOpen(true)}><RatemakingPage /></Protected>} />
          <Route path="queue" element={<Protected onLogin={() => setLoginOpen(true)}><QueuePage queueStats={queueStats} insuranceJobs={insuranceJobs} onOpenJob={openJob} onRefresh={loadQueueStats} /></Protected>} />
          <Route path="registry" element={<Protected onLogin={() => setLoginOpen(true)}><RegistryPage /></Protected>} />
          <Route path="integrations" element={<Protected onLogin={() => setLoginOpen(true)}><IntegrationsPage /></Protected>} />
          <Route path="integrations/:sourceId" element={<Protected onLogin={() => setLoginOpen(true)}><IntegrationsPage /></Protected>} />
          <Route path="webhooks" element={<Protected onLogin={() => setLoginOpen(true)}><WebhooksPage /></Protected>} />
          <Route path="authority" element={<Protected onLogin={() => setLoginOpen(true)}><AuthorityMatrix /></Protected>} />
          <Route path="market" element={<Protected onLogin={() => setLoginOpen(true)}><MarketAdmin /></Protected>} />
          <Route path="regulatory-review" element={<Protected onLogin={() => setLoginOpen(true)}><RegulatoryReviewPage /></Protected>} />
          <Route path="settings" element={<SettingsPage onLogin={() => setLoginOpen(true)} />} />
          <Route path="*" element={<PlaceholderPage title="Page not found" message="That dashboard page doesn't exist. Head back to the Overview to keep working." />} />
        </Route>
      </Routes>

      <LoginModal open={loginOpen} onClose={() => setLoginOpen(false)} onSuccess={(u) => {
        setUser(u);
        refreshAll();
        const h = new Date().getHours();
        const greet = h < 12 ? 'Good morning' : h < 17 ? 'Good afternoon' : 'Good evening';
        setWelcomeMessage(`${greet}, ${u.username || 'there'}! Make sure you've selected the right states before proceeding — our servers are USA-based.`);
        setTimeout(() => setWelcomeMessage(''), 8000);
      }} />
      <ErrorBoundary resetKey={drawer.jobId || 'closed'}>
        <JobDrawer job={drawer.job} vertical={drawer.vertical} jobId={drawer.jobId} onClose={() => setDrawer({ vertical: null, jobId: null, job: null })} />
      </ErrorBoundary>
    </>
  );
}

export default function App() {
  return (
    <StateProvider>
      <BrowserRouter basename="/dashboard">
        <AppRoutes />
      </BrowserRouter>
    </StateProvider>
  );
}
