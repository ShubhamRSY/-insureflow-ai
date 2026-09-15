import { useEffect, useState } from 'react';
import { CheckCircle2, AlertTriangle, Info, X } from 'lucide-react';
import { toast } from '../lib/toast';

const STYLES = {
  success: { icon: CheckCircle2, className: 'border-emerald-500/20 bg-emerald-500/10 text-emerald-200', iconClassName: 'text-emerald-400' },
  error: { icon: AlertTriangle, className: 'border-red-500/20 bg-red-500/10 text-red-200', iconClassName: 'text-red-400' },
  info: { icon: Info, className: 'border-sky-500/20 bg-sky-500/10 text-sky-200', iconClassName: 'text-sky-400' },
};

const AUTO_DISMISS_MS = 6000;

export default function ToastContainer() {
  const [items, setItems] = useState([]);

  useEffect(() => toast.subscribe((item) => {
    setItems((prev) => [...prev, item]);
    setTimeout(() => {
      setItems((prev) => prev.filter((i) => i.id !== item.id));
    }, AUTO_DISMISS_MS);
  }), []);

  const dismiss = (id) => setItems((prev) => prev.filter((i) => i.id !== id));

  if (!items.length) return null;

  return (
    <div className="pointer-events-none fixed bottom-4 right-4 z-[100] flex w-full max-w-sm flex-col gap-2">
      {items.map((item) => {
        const style = STYLES[item.kind] || STYLES.info;
        const Icon = style.icon;
        return (
          <div
            key={item.id}
            role="status"
            className={`pointer-events-auto flex items-start gap-3 rounded-xl border px-4 py-3 text-sm shadow-lg backdrop-blur-md ${style.className}`}
          >
            <Icon className={`mt-0.5 h-4 w-4 shrink-0 ${style.iconClassName}`} />
            <span className="flex-1 whitespace-pre-line">{item.message}</span>
            <button type="button" onClick={() => dismiss(item.id)} className="shrink-0 rounded-lg p-0.5 opacity-60 hover:opacity-100">
              <X className="h-3.5 w-3.5" />
            </button>
          </div>
        );
      })}
    </div>
  );
}
