import { RadialBar, RadialBarChart, PolarAngleAxis } from 'recharts';

// Circular progress-ring score gauge. Same red/amber/emerald band cuts as
// ui.jsx's ScoreBadge so a score reads the same color as a ring here or a
// pill in a table elsewhere in the app.
//
// direction="risk" (default): high value = worse, ring goes green→red as it
// fills — use for risk/severity scores.
// direction="quality": high value = better, ring goes red→green as it fills
// — use for guideline/appetite-fit scores.
function bandColor(pct) {
  if (pct >= 66) return '#f87171'; // red-400
  if (pct >= 33) return '#fbbf24'; // amber-400
  return '#34d399'; // emerald-400
}

export default function ScoreGauge({
  value = 0,
  max = 100,
  label,
  sublabel,
  size = 108,
  direction = 'risk',
  displayValue,
}) {
  const safeValue = Number.isFinite(Number(value)) ? Number(value) : 0;
  const pct = Math.max(0, Math.min(100, (safeValue / (max || 100)) * 100));
  const bandPct = direction === 'quality' ? 100 - pct : pct;
  const color = bandColor(bandPct);
  const data = [{ value: pct, fill: color }];
  const shown = displayValue ?? Math.round(safeValue);

  return (
    <div className="flex flex-col items-center" style={{ width: size }}>
      <div className="relative" style={{ width: size, height: size }}>
        <RadialBarChart
          width={size}
          height={size}
          cx="50%"
          cy="50%"
          innerRadius="72%"
          outerRadius="100%"
          barSize={Math.max(6, size * 0.11)}
          data={data}
          startAngle={90}
          endAngle={-270}
        >
          <PolarAngleAxis type="number" domain={[0, 100]} tick={false} axisLine={false} />
          <RadialBar background={{ fill: 'rgba(255,255,255,0.07)' }} dataKey="value" cornerRadius={size} clockWise isAnimationActive />
        </RadialBarChart>
        <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-2xl font-bold leading-none" style={{ color }}>{shown}</span>
          {max !== 100 && <span className="mt-0.5 text-[9px] text-slate-500">/ {max}</span>}
        </div>
      </div>
      {label && <p className="mt-1.5 text-center text-[10px] font-bold uppercase tracking-widest text-slate-400">{label}</p>}
      {sublabel && <p className="text-center text-[10px] text-slate-500">{sublabel}</p>}
    </div>
  );
}
