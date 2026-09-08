import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { AlertTriangle, CheckCircle2, Shield } from 'lucide-react';
import { endpoints } from '../lib/api';

/**
 * Global honesty banner: shadow vs ready, bind allowed, indication posture.
 * Sourced from the same pilot sandbox status as Pilot Lab.
 */
export default function OperatingModeBanner() {
  const [status, setStatus] = useState(null);

  useEffect(() => {
    let cancelled = false;
    endpoints
      .pilotSandboxStatus()
      .then((res) => {
        if (!cancelled) setStatus(res);
      })
      .catch(() => {
        if (!cancelled) setStatus(null);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (!status) return null;

  const shadow = Boolean(status.shadow_mode);
  const bindAllowed = Boolean(status.bind_allowed);
  const readyMode = Boolean(status.ready_mode);
  const cutover = status.bind_cutover || {};
  const book = cutover.carrier_book || {};
  const customerBook = Boolean(book.is_customer_book);

  let tone = 'amber';
  let Icon = AlertTriangle;
  let title = 'Indication mode';
  let detail = 'Quotes are indications — not a carrier bind.';

  if (shadow) {
    tone = 'amber';
    Icon = AlertTriangle;
    title = 'Shadow mode — bind off';
    detail = 'Underwriting runs for review only. No policy will be bound in the PAS.';
  } else if (readyMode && bindAllowed && customerBook) {
    tone = 'emerald';
    Icon = CheckCircle2;
    title = 'Ready mode — bind allowed';
    detail = 'Customer rate book loaded. Bind still requires licensed UW sign-off and open subjectivities cleared.';
  } else if (readyMode && bindAllowed) {
    tone = 'sky';
    Icon = Shield;
    title = 'Ready mode — indication / PAS bind gated';
    detail = customerBook
      ? 'Bind path available after UW sign-off.'
      : 'Pilot/synthetic rate book in use — premiums are indications until a customer filed book is imported.';
  } else if (readyMode && !bindAllowed) {
    tone = 'amber';
    Icon = AlertTriangle;
    title = 'Ready mode — PAS credentials needed';
    detail = 'Operating mode is ready, but bind stays off until a live Guidewire/BriteCore URL + key is configured.';
  }

  const tones = {
    amber: 'border-amber-500/25 bg-amber-500/10 text-amber-100',
    emerald: 'border-emerald-500/25 bg-emerald-500/10 text-emerald-100',
    sky: 'border-sky-500/25 bg-sky-500/10 text-sky-100',
  };
  const iconTone = {
    amber: 'text-amber-400',
    emerald: 'text-emerald-400',
    sky: 'text-sky-400',
  };

  return (
    <div className={`mb-4 flex flex-wrap items-start gap-3 rounded-xl border px-4 py-3 text-sm ${tones[tone]}`}>
      <Icon className={`mt-0.5 h-4 w-4 shrink-0 ${iconTone[tone]}`} />
      <div className="min-w-0 flex-1">
        <p className="font-semibold text-white">{title}</p>
        <p className="mt-0.5 text-xs opacity-90">{detail}</p>
      </div>
      <Link to="/pilot" className="shrink-0 text-xs font-medium text-white/80 underline-offset-2 hover:underline">
        Pilot Lab
      </Link>
    </div>
  );
}
