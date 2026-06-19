import { useState } from 'react';
import { CONNECTOR_BRANDS } from '../lib/connectorBrands';

export default function ConnectorLogo({ sourceId, name, size = 40 }) {
  const brand = CONNECTOR_BRANDS[sourceId] || {};
  const [failed, setFailed] = useState(false);
  const px = `${size}px`;

  if (brand.slug && !failed) {
    return (
      <img
        src={`https://cdn.simpleicons.org/${brand.slug}/${brand.color || 'white'}`}
        alt={`${name} logo`}
        width={size}
        height={size}
        className="object-contain"
        loading="lazy"
        onError={() => setFailed(true)}
      />
    );
  }

  const initials = brand.initials || (name || '?').slice(0, 2).toUpperCase();
  const bg = brand.bg ? `#${brand.bg}` : 'rgb(30 41 59)';

  return (
    <div
      className="flex items-center justify-center rounded-lg text-xs font-bold tracking-tight text-white shadow-inner"
      style={{ width: px, height: px, backgroundColor: bg, color: brand.color ? `#${brand.color}` : '#fff' }}
      aria-hidden
    >
      {initials}
    </div>
  );
}
