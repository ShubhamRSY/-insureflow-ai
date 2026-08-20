import { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { endpoints, auth } from '../lib/api';
import PasswordInput from '../components/PasswordInput';

const PLANS = [
  { id: 'free', name: 'Free', price: '$0', period: '/mo', description: 'Try InsureFlow with 50 submissions/mo', features: ['50 submissions/mo', '1 user', 'Basic extraction & risk scoring', 'State rules'] },
  { id: 'starter', name: 'Starter', price: '$299', period: '/mo', description: 'For small MGAs getting started', features: ['200 submissions/mo', '3 users', 'Compliance checks', 'Regulatory intelligence', '+ $2.99/submission'] },
  { id: 'pro', name: 'Pro', price: '$999', period: '/mo', description: 'For growing underwriting teams', features: ['1,000 submissions/mo', '5 users', 'Fraud detection & reinsurance', 'API access & webhooks', '+ $1.99/submission'] },
  { id: 'enterprise', name: 'Enterprise', price: 'Custom', period: '', description: 'For carriers and large MGAs', features: ['Unlimited submissions', 'Unlimited users', 'Everything in Pro', 'Priority support'] },
];

export default function SignupPage() {
  const navigate = useNavigate();
  const [step, setStep] = useState(1);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [selectedPlan, setSelectedPlan] = useState('free');
  const [result, setResult] = useState(null);

  useEffect(() => {
    if (auth.isLoggedIn) {
      navigate('/dashboard', { replace: true });
    }
  }, [navigate]);

  const handleAccountSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const fd = new FormData(e.target);
      const body = {
        username: String(fd.get('username') || '').trim(),
        email: String(fd.get('email') || '').trim(),
        password: String(fd.get('password') || ''),
        company_name: String(fd.get('company_name') || '').trim(),
        full_name: String(fd.get('full_name') || '').trim(),
        plan: selectedPlan,
      };
      if (!body.username || !body.email || !body.password || !body.company_name) {
        throw new Error('All fields are required');
      }
      setResult(body);
      setStep(2);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleConfirm = async () => {
    setError('');
    setLoading(true);
    try {
      const data = await endpoints.signup({
        username: result.username,
        email: result.email,
        password: result.password,
        company_name: result.company_name,
        full_name: result.full_name,
        plan: selectedPlan,
      });
      auth.token = data.token;
      const me = await endpoints.me();
      auth.user = me;
      setResult({ ...result, api_key: data.api_key, token: data.token });
      setStep(3);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 flex items-center justify-center p-4">
      <div className="w-full max-w-lg">
        <div className="text-center mb-8">
          <Link to="/dashboard" className="text-2xl font-bold text-white hover:text-brand-light transition-colors">
            InsureFlow
          </Link>
          <p className="mt-2 text-slate-400">Create your account</p>
        </div>

        {/* Step indicators */}
        <div className="flex items-center justify-center gap-2 mb-8">
          {[1, 2, 3].map((s) => (
            <div key={s} className="flex items-center gap-2">
              <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium transition-colors ${
                step >= s ? 'bg-brand-light text-slate-950' : 'bg-slate-800 text-slate-500'
              }`}>{s}</div>
              {s < 3 && <div className={`w-12 h-0.5 ${step > s ? 'bg-brand-light' : 'bg-slate-800'}`} />}
            </div>
          ))}
        </div>

        <div className="glass-card p-8">
          {error && <p className="mb-4 rounded-xl bg-red-500/10 px-3 py-2 text-sm text-red-400">{error}</p>}

          {step === 1 && (
            <>
              <h2 className="text-xl font-bold text-white mb-1">Account Details</h2>
              <p className="text-sm text-slate-400 mb-6">Tell us about your organization</p>
              <form onSubmit={handleAccountSubmit} className="space-y-4">
                <input name="company_name" placeholder="Company / Organization name" required className="input-field" />
                <input name="full_name" placeholder="Your full name (optional)" className="input-field" />
                <input name="username" placeholder="Username" required minLength={3} className="input-field" autoComplete="username" />
                <input name="email" type="email" placeholder="Work email" required className="input-field" autoComplete="email" />
                <PasswordInput placeholder="Password (min 8 chars, upper + lower + digit + special)" autoComplete="new-password" />
                <button type="submit" disabled={loading} className="btn-primary w-full">
                  {loading ? 'Validating...' : 'Continue'}
                </button>
              </form>
            </>
          )}

          {step === 2 && (
            <>
              <h2 className="text-xl font-bold text-white mb-1">Choose Your Plan</h2>
              <p className="text-sm text-slate-400 mb-6">You can change plans anytime from settings</p>
              <div className="space-y-3 mb-6">
                {PLANS.map((plan) => (
                  <button
                    key={plan.id}
                    type="button"
                    onClick={() => setSelectedPlan(plan.id)}
                    className={`w-full text-left p-4 rounded-xl border transition-all ${
                      selectedPlan === plan.id
                        ? 'border-brand-light bg-brand-light/10'
                        : 'border-slate-700 bg-slate-800/50 hover:border-slate-600'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div>
                        <span className="font-medium text-white">{plan.name}</span>
                        <span className="ml-3 text-sm text-slate-400">{plan.description}</span>
                      </div>
                      <div className="text-right">
                        <span className="text-lg font-bold text-white">{plan.price}</span>
                        <span className="text-sm text-slate-400">{plan.period}</span>
                      </div>
                    </div>
                    <div className="mt-2 flex flex-wrap gap-2">
                      {plan.features.map((f) => (
                        <span key={f} className="text-xs bg-slate-800 text-slate-400 rounded px-2 py-0.5">{f}</span>
                      ))}
                    </div>
                  </button>
                ))}
              </div>
              <div className="flex gap-3">
                <button type="button" onClick={() => setStep(1)} className="flex-1 rounded-xl border border-slate-700 px-4 py-2.5 text-sm text-slate-300 hover:border-slate-500 transition-colors">
                  Back
                </button>
                <button type="button" onClick={handleConfirm} disabled={loading} className="btn-primary flex-1">
                  {loading ? 'Creating Account...' : 'Create Account'}
                </button>
              </div>
            </>
          )}

          {step === 3 && result && (
            <div className="text-center">
              <div className="w-16 h-16 rounded-full bg-emerald-500/20 flex items-center justify-center mx-auto mb-4">
                <svg className="w-8 h-8 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              </div>
              <h2 className="text-xl font-bold text-white mb-2">Welcome to InsureFlow!</h2>
              <p className="text-sm text-slate-400 mb-6">Your account is ready. Save your API key — it won't be shown again.</p>

              {result.api_key && (
                <div className="mb-6">
                  <label className="mb-1.5 block text-xs font-medium text-slate-400">API Key</label>
                  <div className="flex items-center gap-2">
                    <input
                      readOnly
                      value={result.api_key}
                      className="input-field flex-1 text-xs font-mono"
                      onClick={(e) => e.target.select()}
                    />
                    <button
                      type="button"
                      onClick={() => navigator.clipboard.writeText(result.api_key)}
                      className="rounded-xl border border-slate-700 px-3 py-2 text-sm text-slate-300 hover:border-brand-light hover:text-brand-light transition-colors"
                    >
                      Copy
                    </button>
                  </div>
                </div>
              )}

              <button type="button" onClick={() => navigate('/dashboard')} className="btn-primary w-full">
                Go to Dashboard
              </button>
            </div>
          )}
        </div>

        <p className="mt-6 text-center text-sm text-slate-500">
          Already have an account?{' '}
          <Link to="/dashboard" className="text-brand-light hover:underline">Sign in</Link>
        </p>
      </div>
    </div>
  );
}
