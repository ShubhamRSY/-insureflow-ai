import { useId } from 'react';

const BOWL = 'M14 8H38a14 14 0 0 1 0 28H14ZM22 16H36a6 6 0 0 1 0 12H22Z';

// Rytera mark: an R built from three see-through layers (stem, bowl, leg) on a dark tile.
export default function BrandMark({ className = 'h-8 w-8' }) {
  const id = useId().replace(/:/g, '');
  return (
    <svg viewBox="0 0 64 64" fill="none" className={className} aria-hidden="true">
      <defs>
        <clipPath id={`s${id}`}><rect x="10" y="8" width="10" height="48" rx="5" /></clipPath>
        <clipPath id={`b${id}`}><path clipRule="evenodd" d={BOWL} /></clipPath>
      </defs>
      <rect width="64" height="64" rx="16" fill="#0e1a16" />
      <g transform="translate(32 32) scale(.82) translate(-31 -32.5)">
        <rect x="10" y="8" width="10" height="48" rx="5" fill="#b8893f" />
        <path fillRule="evenodd" d={BOWL} fill="#e6c896" />
        <path d="M33 34L47 52" stroke="#6fa8a3" strokeWidth="10" strokeLinecap="round" />
        <g fill="#0e1a16" stroke="#0e1a16" opacity=".45">
          <path fillRule="evenodd" stroke="none" d={BOWL} clipPath={`url(#s${id})`} />
          <path d="M33 34L47 52" fill="none" strokeWidth="10" strokeLinecap="round" clipPath={`url(#b${id})`} />
        </g>
      </g>
    </svg>
  );
}
