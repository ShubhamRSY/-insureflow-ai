import { useState, useEffect, useRef } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { endpoints, auth } from '../lib/api';
import PasswordInput from '../components/PasswordInput';

const PLANS = [
  { id: 'free', name: 'Free', price: '$0', period: '/mo', paid: false, description: 'Try InsureFlow with 50 submissions/mo', features: ['50 submissions/mo', '1 user', 'Basic extraction & risk scoring', 'State rules'] },
  { id: 'starter', name: 'Starter', price: '$299', period: '/mo', paid: true, description: 'For small MGAs getting started', features: ['200 submissions/mo', '3 users', 'Compliance checks', 'Regulatory intelligence', '+ $2.99/submission'] },
  { id: 'pro', name: 'Pro', price: '$999', period: '/mo', paid: true, description: 'For growing underwriting teams', features: ['1,000 submissions/mo', '5 users', 'Fraud detection & reinsurance', 'API access & webhooks', '+ $1.99/submission'] },
  { id: 'enterprise', name: 'Enterprise', price: 'Custom', period: '', paid: true, description: 'For carriers and large MGAs', features: ['Unlimited submissions', 'Unlimited users', 'Everything in Pro', 'Priority support'] },
];

const EMPTY_BILLING = { card_name: '', card_number: '', card_exp: '', card_cvc: '', billing_zip: '' };

export default function SignupPage() {
  const navigate = useNavigate();
  const [step, setStep] = useState(1);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [selectedPlan, setSelectedPlan] = useState('free');
  const [result, setResult] = useState(null);
  const [accountCreated, setAccountCreated] = useState(false);
  const [checkout, setCheckout] = useState(null);
  const [billing, setBilling] = useState(EMPTY_BILLING);
  const [formData, setFormData] = useState({ company_name: '', full_name: '', username: '', email: '', password: '' });
  const busyRef = useRef(false);

  useEffect(() => {
    if (auth.isLoggedIn) {
      navigate('/', { replace: true });
    }
  }, [navigate]);

  const planMeta = PLANS.find((p) => p.id === selectedPlan) || PLANS[0];
  const isPaid = !!planMeta.paid;
  const totalSteps = isPaid ? 4 : 3;
  const successStep = isPaid ? 4 : 3;

  const updateField = (field) => (e) => {
    setFormData((prev) => ({ ...prev, [field]: e.target.value }));
  };

  const updateBilling = (field) => (e) => {
    setBilling((prev) => ({ ...prev, [field]: e.target.value }));
  };

  const handleAccountSubmit = async (e) => {
    e.preventDefault();
    if (busyRef.current) return;
    busyRef.current = true;
    setError('');
    setLoading(true);
    try {
      const body = {
        username: formData.username.trim(),
        email: formData.email.trim(),
        password: formData.password,
        company_name: formData.company_name.trim(),
        full_name: formData.full_name.trim(),
      };
      if (!body.username || !body.email || !body.password || !body.company_name) {
        throw new Error('All fields are required');
      }
      setResult(body);
      setStep(2);
    } catch (err) {
      setError(err.message);
    } finally {
      busyRef.current = false;
      setLoading(false);
    }
  };

  // Create the account on the Free plan first, so a plan choice alone never
  // grants paid entitlements. The paid subscription activates only after checkout.
  const createAccount = async () => {
    const data = await endpoints.signup({
      username: result.username,
      email: result.email,
      password: result.password,
      company_name: result.company_name,
      full_name: result.full_name,
      plan: 'free',
    });
    auth.token = data.token;
    const me = await endpoints.me();
    auth.user = me;
    setAccountCreated(true);
    setResult((prev) => ({ ...prev, api_key: data.api_key, token: data.token, org_id: data.org_id }));
    return data;
  };

  const handlePlanSubmit = async () => {
    if (busyRef.current) return;
    busyRef.current = true;
    setError('');
    setLoading(true);
    try {
      if (!accountCreated) {
        await createAccount();
      }
      if (!isPaid) {
        setStep(successStep);
        return;
      }
      const session = await endpoints.startCheckout({ tier: selectedPlan });
      setCheckout(session);
      setStep(3);
    } catch (err) {
      setError(err.message);
    } finally {
      busyRef.current = false;
      setLoading(false);
    }
  };

  const handleCheckoutSubmit = async (e) => {
    e.preventDefault();
    if (busyRef.current) return;
    busyRef.current = true;
    setError('');
    setLoading(true);
    try {
      if (!checkout?.checkout_id) {
        throw new Error('No open checkout — go back and choose a plan');
      }
      await endpoints.confirmCheckout(checkout.checkout_id, {
        card_name: billing.card_name.trim(),
        card_number: billing.card_number.replace(/\s+/g, ''),
        card_exp: billing.card_exp.trim(),
        card_cvc: billing.card_cvc.trim(),
        billing_zip: billing.billing_zip.trim(),
      });
      setStep(4);
    } catch (err) {
      setError(err.message);
    } finally {
      busyRef.current = false;
      setLoading(false);
    }
  };

  const handleCancelCheckout = async () => {
    if (busyRef.current) return;
    busyRef.current = true;
    setLoading(true);
    try {
      if (checkout?.checkout_id) {
        try { await endpoints.cancelCheckout(checkout.checkout_id); } catch { /* ignore */ }
      }
      setCheckout(null);
      setStep(2);
    } finally {
      busyRef.current = false;
      setLoading(false);
    }
  };

  const isSuccess = result && step === successStep;

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 flex items-center justify-center p-4">
      <div className="w-full max-w-lg">
        <div className="text-center mb-8">
          <Link to="/" className="text-2xl font-bold text-white hover:text-brand-light transition-colors">
            InsureFlow
          </Link>
          <p className="mt-2 text-sm text-slate-300">Create your account</p>
        </div>

        {/* Step indicators */}
        <div className="flex items-center justify-center gap-2 mb-8">
          {Array.from({ length: totalSteps }, (_, i) => i + 1).map((s) => (
            <div key={s} className="flex items-center gap-2">
              <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium transition-colors ${
                step >= s ? 'bg-brand-light text-slate-950' : 'bg-slate-600 text-white'
              }`}>{s}</div>
              {s < totalSteps && <div className={`w-12 h-0.5 ${step > s ? 'bg-brand-light' : 'bg-slate-600'}`} />}
            </div>
          ))}
        </div>

        <div className="glass-card p-8">
          {error && <p className="mb-4 rounded-xl bg-red-500/10 px-3 py-2 text-sm text-red-400">{error}</p>}

          {step === 1 && (
            <>
              <h2 className="text-xl font-bold text-white mb-1">Account Details</h2>
              <p className="text-sm text-slate-300 mb-6">Tell us about your organization</p>
              <form onSubmit={handleAccountSubmit} className="space-y-4">
                <input name="company_name" placeholder="Company / Organization name" required className="input-field" value={formData.company_name} onChange={updateField('company_name')} />
                <input name="full_name" placeholder="Your full name (optional)" className="input-field" value={formData.full_name} onChange={updateField('full_name')} />
                <input name="username" placeholder="Username" required minLength={3} className="input-field" autoComplete="username" value={formData.username} onChange={updateField('username')} />
                <input name="email" type="email" placeholder="Work email" required className="input-field" autoComplete="email" value={formData.email} onChange={updateField('email')} />
                <PasswordInput placeholder="Password (min 8 chars, upper + lower + digit + special)" autoComplete="new-password" value={formData.password} onChange={updateField('password')} />
                <button type="submit" disabled={loading} className="btn-primary w-full">
                  {loading ? 'Validating...' : 'Continue'}
                </button>
              </form>
            </>
          )}

          {step === 2 && (
            <>
              <h2 className="text-xl font-bold text-white mb-1">Choose Your Plan</h2>
              <p className="text-sm text-slate-300 mb-6">You can change plans anytime from settings. Paid plans continue to checkout.</p>
              <div className="space-y-3 mb-6">
                {PLANS.map((plan) => (
                  <button
                    key={plan.id}
                    type="button"
                    onClick={() => setSelectedPlan(plan.id)}
                    disabled={loading}
                    className={`w-full text-left p-4 rounded-xl border transition-all disabled:cursor-not-allowed disabled:opacity-60 ${
                      selectedPlan === plan.id
                        ? 'border-brand-light bg-brand-light/10'
                        : 'border-white/10 bg-white/[0.03] hover:border-white/20'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div>
                        <span className="font-medium text-white">{plan.name}</span>
                        {plan.paid && <span className="ml-2 text-[10px] uppercase tracking-wide bg-brand-light/20 text-brand-light rounded px-1.5 py-0.5">Paid</span>}
                        <span className="ml-3 text-sm text-slate-300">{plan.description}</span>
                      </div>
                      <div className="text-right shrink-0 ml-3">
                        <span className="text-lg font-bold text-white">{plan.price}</span>
                        <span className="text-sm text-slate-300">{plan.period}</span>
                      </div>
                    </div>
                    <div className="mt-2 flex flex-wrap gap-2">
                      {plan.features.map((f) => (
                        <span key={f} className="text-xs bg-white/10 text-slate-200 rounded px-2 py-0.5">{f}</span>
                      ))}
                    </div>
                  </button>
                ))}
              </div>
              <div className="flex gap-3">
                <button type="button" onClick={() => setStep(1)} disabled={loading} className="flex-1 rounded-xl border border-white/15 px-4 py-2.5 text-sm text-slate-200 hover:border-white/30 transition-colors disabled:cursor-not-allowed disabled:opacity-60">
                  Back
                </button>
                <button type="button" onClick={handlePlanSubmit} disabled={loading} className="btn-primary flex-1">
                  {loading
                    ? (isPaid ? 'Opening checkout...' : 'Creating Account...')
                    : (isPaid ? 'Continue to payment' : 'Create Account')}
                </button>
              </div>
            </>
          )}

          {step === 3 && isPaid && (
            <>
              <h2 className="text-xl font-bold text-white mb-1">Checkout</h2>
              <p className="text-sm text-slate-300 mb-4">
                {planMeta.name} plan
                {planMeta.price !== 'Custom' && <> — <span className="font-medium text-white">{planMeta.price}{planMeta.period}</span></>}
                {planMeta.price === 'Custom' && <> — our team will confirm your custom pricing after checkout.</>}
              </p>
              <form onSubmit={handleCheckoutSubmit} className="space-y-4">
                <input name="card_name" placeholder="Name on card" required className="input-field" autoComplete="cc-name" value={billing.card_name} onChange={updateBilling('card_name')} />
                <input name="card_number" placeholder="Card number" required inputMode="numeric" className="input-field" autoComplete="cc-number" value={billing.card_number} onChange={updateBilling('card_number')} />
                <div className="flex gap-3">
                  <input name="card_exp" placeholder="MM/YY" required className="input-field" autoComplete="cc-exp" value={billing.card_exp} onChange={updateBilling('card_exp')} />
                  <input name="card_cvc" placeholder="CVC" required className="input-field" autoComplete="cc-csc" value={billing.card_cvc} onChange={updateBilling('card_cvc')} />
                </div>
                <input name="billing_zip" placeholder="Billing ZIP" className="input-field" autoComplete="postal-code" value={billing.billing_zip} onChange={updateBilling('billing_zip')} />
                <p className="text-xs text-slate-400">Test/demo checkout — no real charge is processed.</p>
                <div className="flex gap-3">
                  <button type="button" onClick={handleCancelCheckout} disabled={loading} className="flex-1 rounded-xl border border-white/15 px-4 py-2.5 text-sm text-slate-200 hover:border-white/30 transition-colors disabled:cursor-not-allowed disabled:opacity-60">
                    Back
                  </button>
                  <button type="submit" disabled={loading} className="btn-primary flex-1">
                    {loading ? 'Processing payment...' : 'Pay & create account'}
                  </button>
                </div>
              </form>
            </>
          )}

          {isSuccess && (
            <div className="text-center">
              <div className="w-16 h-16 rounded-full bg-emerald-500/20 flex items-center justify-center mx-auto mb-4">
                <svg className="w-8 h-8 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              </div>
              <h2 className="text-xl font-bold text-white mb-2">Welcome to InsureFlow!</h2>
              <p className="text-sm text-slate-300 mb-6">
                Your account is ready{isPaid ? ` on the ${planMeta.name} plan` : ''}. Save your API key — it won't be shown again.
              </p>

              {result.api_key && (
                <div className="mb-6">
                  <label className="mb-1.5 block text-xs font-medium text-slate-300">API Key</label>
                  <div className="flex items-center gap-2">
                    <input
                      readOnly
                      value={result.api_key}
                      className="input-field flex-1 text-xs font-mono"
                      onClick={(e) => e.target.select()}
                    />
                    <button
                      type="button"
                      onClick={async () => {
                        try {
                          if (navigator.clipboard && window.isSecureContext) {
                            await navigator.clipboard.writeText(result.api_key);
                          } else {
                            const ta = document.createElement('textarea');
                            ta.value = result.api_key;
                            ta.style.position = 'fixed';
                            ta.style.left = '-9999px';
                            document.body.appendChild(ta);
                            ta.select();
                            document.execCommand('copy');
                            document.body.removeChild(ta);
                          }
                          // simple feedback
                          const btn = event?.currentTarget;
                          if (btn) {
                            const old = btn.textContent;
                            btn.textContent = 'Copied';
                            setTimeout(() => (btn.textContent = old), 1200);
                          }
                        } catch (e) {
                          console.error('Failed to copy API key', e);
                        }
                      }}
                      className="rounded-xl border border-white/15 px-3 py-2 text-sm text-slate-200 hover:border-brand-light hover:text-brand-light transition-colors"
                    >
                      Copy
                    </button>
                  </div>
                  <p className="mt-2 text-xs text-slate-400">Use this key for API/programmatic access. Your session is already active — you don’t need to paste this to sign in.</p>
                </div>
              )}

              <button type="button" onClick={() => navigate('/')} className="btn-primary w-full">
                Go to Dashboard
              </button>
            </div>
          )}
        </div>

        <p className="mt-6 text-center text-sm text-slate-400">
          Already have an account?{' '}
          <Link to="/" className="text-brand-light hover:underline">Sign in</Link>
        </p>
      </div>
    </div>
  );
}
