import { X, Lock, Mail } from 'lucide-react';
import { useState } from 'react';

export default function FreemiumBanner({ remaining, DAILY_LIMIT, onLogin, isLoggedIn }) {
  const [dismissed, setDismissed] = useState(false);

  if (dismissed || isLoggedIn) return null;

  return (
    <div className="relative z-50 border-b border-amber-500/20 bg-gradient-to-r from-amber-500/10 via-amber-500/5 to-transparent">
      <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-6 py-3 lg:px-8">
        <div className="flex items-center gap-3">
          <Lock className="h-4 w-4 shrink-0 text-amber-400" />
          <p className="text-sm text-slate-300">
            <span className="font-semibold text-amber-300">Free preview</span>
            {' '}&mdash;{' '}
            {remaining > 0 ? (
              <>
                You have <span className="font-mono font-bold text-white">{remaining}</span> of {DAILY_LIMIT} views left today.
                {' '}Explore the platform, then contact us for full access.
              </>
            ) : (
              <>Daily view limit reached. Contact us for full access.</>
            )}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <a
            href="mailto:shubham@ryterainc.com?subject=Rytera%20%E2%80%94%20Full%20Access%20Request"
            className="inline-flex items-center gap-1.5 rounded-lg bg-amber-500/20 px-3 py-1.5 text-xs font-semibold text-amber-200 ring-1 ring-amber-500/30 transition hover:bg-amber-500/30"
          >
            <Mail className="h-3 w-3" />
            Contact for access
          </a>
          <button
            type="button"
            onClick={() => setDismissed(true)}
            className="rounded-lg p-1 text-slate-500 transition hover:text-slate-300"
            aria-label="Dismiss"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
