import { useEffect, useState } from 'react';
import { auth, endpoints } from '../lib/api';

export default function SsoCallback() {
  const [error, setError] = useState('');

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const code = params.get('code') || '';
    const state = params.get('state') || '';
    if (!code) {
      setError('Missing authorization code from the identity provider.');
      return;
    }
    endpoints.ssoCallback({ code, state })
      .then(async (r) => {
        if (!r.access_token) {
          setError(r.error || 'SSO did not issue a session.');
          return;
        }
        auth.token = r.access_token;
        const me = await endpoints.me();
        auth.user = me;
        window.location.replace('/dashboard/');
      })
      .catch((e) => setError(e.message || String(e)));
  }, []);

  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center px-6 text-center">
      {error ? (
        <>
          <p className="text-lg text-red-300">{error}</p>
          <a href="/dashboard/" className="btn-primary mt-4">Back to sign in</a>
        </>
      ) : (
        <p className="text-slate-300">Signing you in…</p>
      )}
    </div>
  );
}
