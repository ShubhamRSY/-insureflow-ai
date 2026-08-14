import { Monitor, Moon, Sun } from 'lucide-react';
import { useTheme } from './ThemeProvider';

const OPTIONS = [
  { id: 'dark', label: 'Dark', icon: Moon },
  { id: 'light', label: 'Light', icon: Sun },
  { id: 'auto', label: 'Default', icon: Monitor },
];

export default function ThemeToggle({ compact = false }) {
  const { preference, setPreference } = useTheme();

  return (
    <div
      className="flex rounded-lg bg-surface-overlay p-0.5 ring-1 ring-white/10"
      role="group"
      aria-label="Color theme"
    >
      {OPTIONS.map((opt) => {
        const Icon = opt.icon;
        const active = preference === opt.id;
        return (
          <button
            key={opt.id}
            type="button"
            onClick={() => setPreference(opt.id)}
            title={opt.id === 'auto' ? 'Follow time of day — light 7am–7pm, dark otherwise' : opt.label}
            className={`inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs font-medium transition ${
              active ? 'bg-brand/20 text-brand-light' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Icon className="h-3.5 w-3.5" />
            {compact ? null : <span>{opt.label}</span>}
          </button>
        );
      })}
    </div>
  );
}
