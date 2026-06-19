import { Badge, EmptyState } from '../components/ui';
import { ClipboardCheck } from 'lucide-react';
import { endpoints } from '../lib/api';

export default function WorkflowPage({ pending, onRefresh }) {
  const handleSignOff = async (bundleId, action) => {
    const license = prompt('License number (optional):') || '';
    const notes = prompt('Notes (optional):') || '';
    try {
      await endpoints.signOff(bundleId, { action, license_number: license, notes });
      onRefresh();
    } catch (e) {
      alert(e.message);
    }
  };

  return (
    <div className="mx-auto max-w-3xl space-y-8 animate-fade-in">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">UW Sign-off Queue</h1>
        <p className="mt-1 text-slate-400">Licensed underwriter review for insurance submissions</p>
      </div>

      <div className="glass-card p-6">
        {!pending?.length ? (
          <EmptyState icon={ClipboardCheck} title="Queue empty" description="No submissions awaiting licensed UW sign-off" />
        ) : (
          <div className="space-y-4">
            {pending.map((p) => {
              const id = p.bundle_id || p.bundleId;
              return (
                <div key={id} className="rounded-xl border border-white/[0.06] bg-surface-overlay p-5">
                  <div className="flex items-center justify-between gap-4">
                    <span className="font-mono text-sm font-semibold">{id}</span>
                    <Badge status={p.state || p.status || 'pending'} />
                  </div>
                  <p className="mt-2 text-sm text-slate-400">{p.recommendation || p.decision || 'Awaiting review'}</p>
                  <div className="mt-4 flex flex-wrap gap-2">
                    <button type="button" onClick={() => handleSignOff(id, 'approve')} className="btn-primary btn-sm text-xs">Approve</button>
                    <button type="button" onClick={() => handleSignOff(id, 'refer')} className="btn-secondary text-xs">Refer</button>
                    <button type="button" onClick={() => handleSignOff(id, 'decline')} className="rounded-xl px-3 py-1.5 text-xs text-red-400 ring-1 ring-red-500/30 hover:bg-red-500/10">Decline</button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
