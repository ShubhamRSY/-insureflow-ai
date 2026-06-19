import { useCallback, useEffect, useState } from 'react';
import { BrowserRouter, Routes, Route, Navigate, useNavigate } from 'react-router-dom';
import Layout from './components/Layout';
import LoginModal from './components/LoginModal';
import JobDrawer from './components/JobDrawer';
import Overview from './pages/Overview';
import SystemPage from './pages/System';
import InsurancePage from './pages/Insurance';
import MortgagePage from './pages/Mortgage';
import WorkflowPage from './pages/Workflow';
import SettingsPage from './pages/Settings';
import { auth, endpoints, AuthError } from './lib/api';

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
  const [drawer, setDrawer] = useState({ vertical: null, jobId: null, job: null });

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

  const loadInsuranceJobs = useCallback(async () => {
    if (!auth.isLoggedIn) return;
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
    await Promise.all([loadHealth(), loadPresets(), loadOverview(), loadInsuranceJobs(), loadMortgageJobs()]);
  }, [loadHealth, loadPresets, loadOverview, loadInsuranceJobs, loadMortgageJobs]);

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

  const openJob = async (vertical, jobId) => {
    try {
      const fetch = vertical === 'insurance' ? endpoints.insuranceJob : endpoints.mortgageJob;
      const job = await fetch(jobId);
      setDrawer({ vertical, jobId, job });
    } catch (e) {
      if (e instanceof AuthError) handleAuthError();
      else throw e;
    }
  };

  const runDemo = async (vertical, presetId) => {
    if (!auth.isLoggedIn) { setLoginOpen(true); return; }
    const res = vertical === 'insurance'
      ? await endpoints.runInsuranceDemo(presetId)
      : await endpoints.runMortgageDemo(presetId);
    navigate(vertical === 'insurance' ? '/insurance' : '/mortgage');
    await refreshAll();
    openJob(vertical, res.job_id);
  };

  const submitInsurance = async (body) => {
    const res = await endpoints.runInsurance(body);
    await loadInsuranceJobs();
    openJob('insurance', res.job_id);
  };

  const submitMortgage = async (body) => {
    const res = await endpoints.runMortgage(body);
    await loadMortgageJobs();
    openJob('mortgage', res.job_id);
  };

  return (
    <>
      <Routes>
        <Route element={<Layout health={health} pendingCount={pending.length} onRefresh={refreshAll} onLogin={() => setLoginOpen(true)} user={user} setUser={setUser} />}>
          <Route index element={<Overview overview={overview} health={health} presets={presets} onRunDemo={runDemo} onOpenJob={openJob} onLogin={() => setLoginOpen(true)} />} />
          <Route path="system" element={<SystemPage health={health} />} />
          <Route path="insurance" element={<Protected onLogin={() => setLoginOpen(true)}><InsurancePage presets={presets} jobs={insuranceJobs} onRunDemo={runDemo} onOpenJob={openJob} onSubmit={submitInsurance} /></Protected>} />
          <Route path="mortgage" element={<Protected onLogin={() => setLoginOpen(true)}><MortgagePage presets={presets} jobs={mortgageJobs} onRunDemo={runDemo} onOpenJob={openJob} onSubmit={submitMortgage} /></Protected>} />
          <Route path="workflow" element={<Protected onLogin={() => setLoginOpen(true)}><WorkflowPage pending={pending} onRefresh={loadOverview} /></Protected>} />
          <Route path="settings" element={<SettingsPage onLogin={() => setLoginOpen(true)} />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>

      <LoginModal open={loginOpen} onClose={() => setLoginOpen(false)} onSuccess={(u) => { setUser(u); refreshAll(); }} />
      <JobDrawer job={drawer.job} vertical={drawer.vertical} jobId={drawer.jobId} onClose={() => setDrawer({ vertical: null, jobId: null, job: null })} />
    </>
  );
}

export default function App() {
  return (
    <BrowserRouter basename="/dashboard">
      <AppRoutes />
    </BrowserRouter>
  );
}
