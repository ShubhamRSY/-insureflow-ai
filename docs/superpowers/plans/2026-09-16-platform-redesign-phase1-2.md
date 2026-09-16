# Platform Redesign Phase 1+2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Re-theme the whole Rytera dashboard app to the "Ledger, not glow" visual direction (global color/type tokens) and replace the sidebar's single accordion column with a two-tier icon-rail + nav-panel layout — without touching any of the ~45 page files in `frontend/src/pages/`.

**Architecture:** Phase 1 repoints existing global indirection points (Tailwind `theme.colors`, CSS custom properties in `index.css`, the shared `@layer components` classes like `.glass-card`/`.btn-primary`) so every page re-themes automatically, since they all already consume these tokens/classes rather than hardcoded colors. Phase 2 rewrites `Layout.jsx`'s sidebar only; no other component or page changes. Page-level component adoption (StatCard/Badge/EmptyState cleanup, per the earlier audit) is out of scope for this plan — it's a separate, much larger effort batched by nav section, to start after this plan lands.

**Tech Stack:** React 18, Tailwind CSS 3, Vite 6, Vitest 4 + @testing-library/react, lucide-react icons (already a dependency — no new packages).

**Spec:** `docs/superpowers/specs/2026-09-16-platform-redesign-design.md`

## Global Constraints

- No new npm dependencies — lucide-react already provides every icon this plan needs (`Shield`, `LayoutDashboard`, `Activity`, `Library`, `Home`, `Briefcase`, `FileCheck`, `BarChart3`, `ShieldCheck`, `Cable`, `Settings`, `Wallet`, `HandCoins`, `ChevronDown`, `ChevronRight`, `Menu`, `X`, `RefreshCw`, `Lock`, `LogOut`, `AlertTriangle` are all imported already in `frontend/src/components/Layout.jsx`).
- Do not touch any file under `frontend/src/pages/` in this plan — that's Phase 3, a separate follow-up.
- One accent color (`brand`/brass, `#C79A46`) is spent only on primary buttons and active nav state — do not introduce a second bright accent.
- Fonts load via the existing Google Fonts `<link>` pattern in `frontend/index.html` (no self-hosting, no new build step).
- `npm run build` (from `frontend/`) must succeed after every task — it is the fastest signal that Tailwind config / CSS changes are syntactically valid.
- `npm test` (`vitest run`, from `frontend/`) must pass after every task.

---

### Task 1: Swap typography (Source Serif 4 / IBM Plex Sans / IBM Plex Mono)

**Files:**
- Modify: `frontend/index.html:13`
- Modify: `frontend/tailwind.config.js:6-9`

**Interfaces:**
- Produces: Tailwind classes `font-sans` (IBM Plex Sans), `font-display` (Source Serif 4), `font-mono` (IBM Plex Mono) — used unchanged by name in every existing page, so no page edits needed.

- [ ] **Step 1: Replace the Google Fonts link**

In `frontend/index.html`, replace line 13:

```html
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700;1,9..40,400&family=Syne:wght@600;700;800&display=swap" rel="stylesheet" />
```

with:

```html
<link href="https://fonts.googleapis.com/css2?family=Source+Serif+4:opsz,wght@8..60,500;8..60,600;8..60,700&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet" />
```

- [ ] **Step 2: Update the Tailwind font family config**

In `frontend/tailwind.config.js`, replace lines 6-9:

```js
      fontFamily: {
        sans: ['"DM Sans"', 'system-ui', 'sans-serif'],
        display: ['"Syne"', '"DM Sans"', 'system-ui', 'sans-serif'],
      },
```

with:

```js
      fontFamily: {
        sans: ['"IBM Plex Sans"', 'system-ui', 'sans-serif'],
        display: ['"Source Serif 4"', 'Georgia', 'serif'],
        mono: ['"IBM Plex Mono"', 'ui-monospace', 'monospace'],
      },
```

- [ ] **Step 3: Verify the build**

Run: `cd frontend && npm run build`
Expected: build succeeds with no errors.

- [ ] **Step 4: Run the existing test suite**

Run: `cd frontend && npm test`
Expected: all existing tests still pass (font changes don't touch any tested logic).

- [ ] **Step 5: Commit**

```bash
git add frontend/index.html frontend/tailwind.config.js
git commit -m "Swap platform typography to Source Serif 4 / IBM Plex Sans / IBM Plex Mono"
```

---

### Task 2: Repoint the brand color token to brass

**Files:**
- Modify: `frontend/tailwind.config.js:31-35`

**Interfaces:**
- Produces: Tailwind classes `bg-brand`, `text-brand`, `text-brand-light`, `from-brand`, `to-brand`, `shadow-brand-glow` etc. all resolve to the new brass palette — used unchanged by every page's buttons/active-states/links.

- [ ] **Step 1: Replace the brand color values**

In `frontend/tailwind.config.js`, replace lines 31-35:

```js
        brand: {
          DEFAULT: '#5b8def',
          light: '#8bb0f7',
          glow: 'rgba(91, 141, 239, 0.28)',
        },
```

with:

```js
        brand: {
          DEFAULT: '#C79A46',
          light: '#dcb15f',
          glow: 'rgba(199, 154, 70, 0.28)',
        },
```

- [ ] **Step 2: Add the verdigris and risk color tokens**

In the same `colors` object, immediately after the `brand` block (still inside `theme.extend.colors`), add:

```js
        verdigris: {
          DEFAULT: '#3E8E82',
          soft: 'rgba(62, 142, 130, 0.14)',
        },
        risk: {
          red: '#C0524A',
          'red-soft': 'rgba(192, 82, 74, 0.14)',
          amber: '#C98A3A',
          'amber-soft': 'rgba(201, 138, 58, 0.14)',
        },
```

These are additive — nothing currently references `verdigris`/`risk` classes, so this step alone changes no rendered output. They exist so Phase 3 page work has the tokens ready (`bg-verdigris-soft text-verdigris`, `text-risk-red`, etc.) without touching this config again.

- [ ] **Step 3: Verify the build**

Run: `cd frontend && npm run build`
Expected: build succeeds.

- [ ] **Step 4: Run the existing test suite**

Run: `cd frontend && npm test`
Expected: all existing tests still pass.

- [ ] **Step 5: Commit**

```bash
git add frontend/tailwind.config.js
git commit -m "Repoint brand color token to brass, add verdigris/risk tokens"
```

---

### Task 3: Flatten surfaces — repoint CSS variables, drop blur/glow/mesh, flatten shared component classes

**Files:**
- Modify: `frontend/src/index.css:5-21` (dark theme CSS variables)
- Modify: `frontend/src/index.css:62-72` (`.glass-card`, `.btn-primary`, `.btn-secondary`)

**Interfaces:**
- Produces: `bg-surface`, `bg-surface-raised`, `bg-surface-overlay`, `bg-surface-hover`, `bg-mesh`, `bg-hero-glow`, `shadow-card`, `shadow-glow`, `.glass-card`, `.btn-primary`, `.btn-secondary` all repointed — used unchanged by every page.

- [ ] **Step 1: Repoint the dark-theme CSS custom properties**

In `frontend/src/index.css`, replace lines 5-21:

```css
:root,
html.theme-dark {
  color-scheme: dark;
  --ry-surface: 16 20 31;
  --ry-raised: 22 29 44;
  --ry-overlay: 28 37 56;
  --ry-hover: 36 48 68;
  --ry-fg: 241 245 249;
  --ry-glow: 0 0 40px rgba(91, 141, 239, 0.15);
  --ry-card-shadow: 0 1px 0 rgba(255, 255, 255, 0.04) inset, 0 8px 32px rgba(0, 0, 0, 0.4);
  --ry-mesh: radial-gradient(at 20% 20%, rgba(91, 141, 239, 0.18) 0, transparent 50%),
    radial-gradient(at 80% 0%, rgba(56, 189, 248, 0.1) 0, transparent 45%),
    radial-gradient(at 50% 100%, rgba(52, 211, 153, 0.06) 0, transparent 50%);
  --ry-hero: radial-gradient(ellipse 80% 60% at 50% -10%, rgba(91, 141, 239, 0.28), transparent 55%),
    radial-gradient(ellipse 50% 40% at 90% 20%, rgba(56, 189, 248, 0.12), transparent 50%),
    linear-gradient(180deg, #12182a 0%, #10141f 100%);
}
```

with:

```css
:root,
html.theme-dark {
  color-scheme: dark;
  --ry-surface: 11 14 20;
  --ry-raised: 18 22 31;
  --ry-overlay: 23 28 38;
  --ry-hover: 29 35 48;
  --ry-fg: 231 233 238;
  --ry-glow: none;
  --ry-card-shadow: 0 0 0 1px rgba(255, 255, 255, 0.06);
  --ry-mesh: none;
  --ry-hero: linear-gradient(180deg, #0b0e14 0%, #0b0e14 100%);
}
```

This drops the mesh/glow gradients (flat `ink` background everywhere `bg-mesh`/`bg-hero-glow` is used) and turns `shadow-card` into a 1px hairline instead of a blurred drop shadow. Leave `html.theme-light` (lines 23-38 in the original file) untouched — light theme is out of scope for this plan per the spec.

- [ ] **Step 2: Flatten `.glass-card`, `.btn-primary`, `.btn-secondary`**

In `frontend/src/index.css`, replace lines 62-72:

```css
  .glass-card {
    @apply rounded-2xl border border-white/[0.08] bg-surface-raised/85 backdrop-blur-xl shadow-card;
  }

  .btn-primary {
    @apply inline-flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-brand to-indigo-500 px-4 py-2.5 text-sm font-semibold text-white shadow-glow transition hover:brightness-110 disabled:opacity-50;
  }

  .btn-secondary {
    @apply inline-flex items-center justify-center gap-2 rounded-xl border border-white/15 bg-surface-overlay px-4 py-2.5 text-sm font-medium text-slate-100 transition hover:bg-surface-hover;
  }
```

with:

```css
  .glass-card {
    @apply rounded-lg border border-white/[0.08] bg-surface-raised shadow-card;
  }

  .btn-primary {
    @apply inline-flex items-center justify-center gap-2 rounded-lg bg-brand px-4 py-2.5 text-sm font-semibold text-surface transition hover:brightness-110 disabled:opacity-50;
  }

  .btn-secondary {
    @apply inline-flex items-center justify-center gap-2 rounded-lg border border-white/15 bg-surface-overlay px-4 py-2.5 text-sm font-medium text-slate-100 transition hover:bg-surface-hover;
  }
```

`text-surface` on `.btn-primary` reuses the same repointed `--ry-surface` variable (now `ink`, `#0B0E14`) as the button's text color, giving dark text on the brass background for contrast — no new color token needed.

- [ ] **Step 3: Verify the build**

Run: `cd frontend && npm run build`
Expected: build succeeds.

- [ ] **Step 4: Run the existing test suite**

Run: `cd frontend && npm test`
Expected: all existing tests still pass — none of them assert on rendered colors/shadows.

- [ ] **Step 5: Manual visual check**

Run: `cd frontend && npm run dev`, open the app, navigate to the Overview page. Confirm: background is flat near-black (no mesh gradient), cards have a visible hairline border and no blur, primary buttons are solid brass with dark text.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/index.css
git commit -m "Flatten surfaces: drop mesh/glow/blur, hairline cards, brass buttons"
```

---

### Task 4: Extract rail nav data and the active-group derivation logic

**Files:**
- Create: `frontend/src/lib/railNav.js`
- Create: `frontend/src/lib/railNav.test.js`

**Interfaces:**
- Consumes: `INSURANCE_NAV_CHILDREN` from `frontend/src/lib/insuranceSections.js` (already exported, already imported by `Layout.jsx` today).
- Produces:
  - `RAIL_GROUPS`: `Array<{ id: string, label: string, items: Array<{ to: string, label: string, tag?: 'Live'|'Catalog', badge?: boolean }> , scrollItems?: boolean }>`
  - `deriveActiveGroupId(pathname: string, groups = RAIL_GROUPS): string` — pure function, returns the `id` of the group whose `items` contains the longest `to` prefix match for `pathname`, or `'home'` if none match.

- [ ] **Step 1: Write the failing test**

Create `frontend/src/lib/railNav.test.js`:

```js
import { describe, it, expect } from 'vitest';
import { RAIL_GROUPS, deriveActiveGroupId } from './railNav';

describe('RAIL_GROUPS', () => {
  it('has a home group with Overview and System health', () => {
    const home = RAIL_GROUPS.find((g) => g.id === 'home');
    expect(home).toBeDefined();
    expect(home.items.map((i) => i.to)).toEqual(['/', '/system']);
  });

  it('every group has a non-empty items array', () => {
    RAIL_GROUPS.forEach((g) => {
      expect(g.items.length).toBeGreaterThan(0);
    });
  });

  it('every group id is unique', () => {
    const ids = RAIL_GROUPS.map((g) => g.id);
    expect(new Set(ids).size).toBe(ids.length);
  });
});

describe('deriveActiveGroupId', () => {
  it('matches the queue page to uw-operations', () => {
    expect(deriveActiveGroupId('/queue')).toBe('uw-operations');
  });

  it('matches a nested insurance route to the insurance group', () => {
    expect(deriveActiveGroupId('/insurance/life')).toBe('insurance');
  });

  it('falls back to home for an unmatched path', () => {
    expect(deriveActiveGroupId('/some/unknown/path')).toBe('home');
  });

  it('falls back to home for the root path', () => {
    expect(deriveActiveGroupId('/')).toBe('home');
  });

  it('picks the longest prefix match when two groups could both match', () => {
    const groups = [
      { id: 'short', items: [{ to: '/a', label: 'A' }] },
      { id: 'long', items: [{ to: '/a/b', label: 'AB' }] },
    ];
    expect(deriveActiveGroupId('/a/b/c', groups)).toBe('long');
  });
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd frontend && npx vitest run src/lib/railNav.test.js`
Expected: FAIL — `railNav.js` does not exist yet.

- [ ] **Step 3: Write `railNav.js`**

Create `frontend/src/lib/railNav.js`:

```js
import { INSURANCE_NAV_CHILDREN } from './insuranceSections';

export const RAIL_GROUPS = [
  {
    id: 'home',
    label: 'Home',
    items: [
      { to: '/', label: 'Overview' },
      { to: '/system', label: 'System health' },
    ],
  },
  {
    id: 'insurance',
    label: 'Insurance',
    scrollItems: true,
    items: INSURANCE_NAV_CHILDREN,
  },
  {
    id: 'reference',
    label: 'Reference',
    items: [{ to: '/reference/commercial', label: 'Commercial insurance' }],
  },
  {
    id: 'mortgage-lending',
    label: 'Mortgage & lending',
    items: [
      { to: '/mortgage', label: 'Mortgage', tag: 'Live' },
      { to: '/lending', label: 'Lending', tag: 'Live' },
    ],
  },
  {
    id: 'uw-operations',
    label: 'UW operations',
    items: [
      { to: '/uw-workbench', label: 'UW workbench' },
      { to: '/uw-dashboard', label: 'UW dashboard' },
      { to: '/workflow', label: 'UW sign-off' },
      { to: '/queue', label: 'Queue', badge: true },
      { to: '/line-uw', label: 'Line UW desk' },
      { to: '/staff-uw', label: 'Staff UW desk' },
      { to: '/prior-decisions', label: 'Prior decisions' },
    ],
  },
  {
    id: 'post-decision',
    label: 'Post-decision',
    items: [
      { to: '/issuance', label: 'Issuance' },
      { to: '/monitoring', label: 'Policy monitoring' },
      { to: '/producer-comms', label: 'Producer comms' },
    ],
  },
  {
    id: 'analytics',
    label: 'Analytics',
    items: [
      { to: '/renewals', label: 'Renewals' },
      { to: '/overrides', label: 'Override analytics' },
      { to: '/business-kpis', label: 'ROI & KPIs' },
      { to: '/eval-trends', label: 'Eval trends' },
      { to: '/portfolio', label: 'Portfolio' },
      { to: '/authority', label: 'Authority matrix' },
      { to: '/market', label: 'Market cycle' },
    ],
  },
  {
    id: 'governance',
    label: 'Governance',
    items: [
      { to: '/pilot', label: 'Pilot lab' },
      { to: '/registry', label: 'Model registry' },
      { to: '/regulatory-review', label: 'Regulatory review' },
      { to: '/webhooks', label: 'Webhooks' },
    ],
  },
  {
    id: 'integrations',
    label: 'Integrations',
    scrollItems: true,
    items: [
      { to: '/integrations/google-drive', label: 'Google Drive' },
      { to: '/integrations/sharepoint', label: 'SharePoint / OneDrive' },
      { to: '/integrations/s3-bucket', label: 'AWS S3' },
      { to: '/integrations/azure-blob', label: 'Azure Blob Storage' },
      { to: '/integrations/box', label: 'Box Enterprise' },
      { to: '/integrations/email-inbox', label: 'Email inbox' },
      { to: '/integrations/outlook-inbox', label: 'Outlook / Microsoft 365' },
      { to: '/integrations/server-folder', label: 'Server directory' },
      { to: '/integrations/sftp', label: 'SFTP / broker portal' },
      { to: '/integrations/ivans-download', label: 'IVANS download' },
      { to: '/integrations/acord-al3', label: 'ACORD AL3 / XML hub' },
      { to: '/integrations/guidewire-policycenter', label: 'Guidewire PolicyCenter' },
      { to: '/integrations/duck-creek', label: 'Duck Creek policy' },
      { to: '/integrations/majesco-policy', label: 'Majesco policy' },
      { to: '/integrations/applied-epic', label: 'Applied Epic (Vertafore)' },
      { to: '/integrations/hawksoft', label: 'HawkSoft AMS' },
      { to: '/integrations/salesforce-crm', label: 'Salesforce' },
      { to: '/integrations/verisk-iso', label: 'Verisk / ISO' },
      { to: '/integrations/corelogic', label: 'CoreLogic / Cotality' },
      { to: '/integrations/bold-penguin', label: 'Bold Penguin' },
      { to: '/integrations/docusign', label: 'DocuSign' },
      { to: '/integrations/microsoft-teams', label: 'Microsoft Teams' },
      { to: '/integrations/slack-intake', label: 'Slack' },
      { to: '/integrations/snowflake', label: 'Snowflake' },
    ],
  },
  {
    id: 'account',
    label: 'Account',
    items: [
      { to: '/ratemaking', label: 'Ratemaking & pricing' },
      { to: '/settings', label: 'Settings' },
    ],
  },
];

export function deriveActiveGroupId(pathname, groups = RAIL_GROUPS) {
  let bestId = 'home';
  let bestLength = -1;
  groups.forEach((group) => {
    group.items.forEach((item) => {
      const isRoot = item.to === '/';
      const matches = isRoot ? pathname === '/' : pathname.startsWith(item.to);
      if (matches && item.to.length > bestLength) {
        bestLength = item.to.length;
        bestId = group.id;
      }
    });
  });
  return bestId;
}
```

The exact integration list is copied from the current `Layout.jsx` nav array (`children` of the `/integrations` item) so no sub-route or label changes — only the data's home moves from an inline literal to this module.

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd frontend && npx vitest run src/lib/railNav.test.js`
Expected: PASS, all 8 tests green.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/railNav.js frontend/src/lib/railNav.test.js
git commit -m "Add rail nav data and active-group derivation for the sidebar redesign"
```

---

### Task 5: Rewrite `Layout.jsx` sidebar as a two-tier icon rail + nav panel

**Files:**
- Modify: `frontend/src/components/Layout.jsx` (full sidebar section, roughly lines 1-17 imports and 192-428 the `<aside>` block plus related state/handlers)

**Interfaces:**
- Consumes: `RAIL_GROUPS`, `deriveActiveGroupId` from `frontend/src/lib/railNav.js` (Task 4).
- Consumes existing props unchanged: `health`, `pendingCount`, `onRefresh`, `onLogin`, `user`, `setUser`, `isLimited`, `welcomeMessage`, `onDismissWelcome`.
- Removes: `sidebarCollapsed` state and its toggle button (the two-tier rail is already maximally compact — no further collapse mode). Removes `openGroups` state and the accordion chevron toggle (every group is always reachable via its rail icon instead).

- [ ] **Step 1: Replace the imports**

In `frontend/src/components/Layout.jsx`, replace lines 1-16:

```js
import { NavLink, Outlet, useNavigate, useLocation } from 'react-router-dom';
import {
  LayoutDashboard, Shield, Home, Activity, Settings, LogOut, RefreshCw, Menu, X,
  BarChart3, Wallet, FileCheck, Briefcase, ChevronDown, ChevronRight, Plus,
  ShieldCheck, Library, Lock, Cable, HandCoins, AlertTriangle,
} from 'lucide-react';
import { useState } from 'react';
import { auth } from '../lib/api';
import { INSURANCE_SECTIONS, INSURANCE_NAV_CHILDREN, insuranceSectionAccent } from '../lib/insuranceSections';
import { displayText } from '../lib/safe';
import { useStateContext } from '../lib/useStateContext';
import ThemeToggle from './ThemeToggle';
import StateSelector from './StateSelector';
import ErrorBoundary from './ErrorBoundary';
import OperatingModeBanner from './OperatingModeBanner';
import ToastContainer from './Toast';
```

with:

```js
import { NavLink, Outlet, useNavigate, useLocation } from 'react-router-dom';
import {
  Shield, Home, Settings, LogOut, RefreshCw, Menu, X,
  BarChart3, FileCheck, Briefcase, ShieldCheck, Library, Lock, Cable, AlertTriangle, LayoutDashboard,
} from 'lucide-react';
import { useEffect, useState } from 'react';
import { auth } from '../lib/api';
import { RAIL_GROUPS, deriveActiveGroupId } from '../lib/railNav';
import { displayText } from '../lib/safe';
import { useStateContext } from '../lib/useStateContext';
import ThemeToggle from './ThemeToggle';
import StateSelector from './StateSelector';
import ErrorBoundary from './ErrorBoundary';
import OperatingModeBanner from './OperatingModeBanner';
import ToastContainer from './Toast';

const GROUP_ICONS = {
  home: LayoutDashboard,
  insurance: Shield,
  reference: Library,
  'mortgage-lending': Home,
  'uw-operations': Briefcase,
  'post-decision': FileCheck,
  analytics: BarChart3,
  governance: ShieldCheck,
  integrations: Cable,
  account: Settings,
};
```

`ChevronDown`/`ChevronRight`/`Plus` drop out (no accordion left to expand/collapse, no "coming soon" plus-marker in this pass); `HandCoins`/`Wallet`/`Activity` drop out (individual leaf items no longer carry their own icon — only the 10 rail groups do, via `GROUP_ICONS`, and `Activity`'s only use — the old flat "System Health" top-level item — is now folded into the `home` group alongside Overview, both under the `LayoutDashboard` group icon); `INSURANCE_SECTIONS`/`insuranceSectionAccent` drop out (that per-line accent-color styling on nav labels is part of the old accordion look — the new nav panel uses a flat `Live`/`Catalog` tag instead, matching the mockup).

`CRUMBS` and `crumbsFor` (original lines 146-190) are untouched — the breadcrumb logic doesn't depend on the sidebar's internal structure.

- [ ] **Step 2: Replace the component's state and remove the old `renderNavItem` function**

Replace the function signature through the start of the render (original lines 192-212):

```js
export default function Layout({ health, pendingCount, onRefresh, onLogin, user, setUser, isLimited, welcomeMessage, onDismissWelcome }) {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [openGroups, setOpenGroups] = useState(() => {
    const init = {};
    nav.forEach((item) => { if (item.children && item.defaultOpen) init[item.to] = true; });
    return init;
  });
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const { selectedState } = useStateContext();
  const crumbs = crumbsFor(pathname);

  const logout = () => {
    auth.clear();
    setUser(null);
    navigate('/system');
  };

  const toggleGroup = (to) => setOpenGroups((g) => ({ ...g, [to]: !g[to] }));
```

with:

```js
export default function Layout({ health, pendingCount, onRefresh, onLogin, user, setUser, isLimited, welcomeMessage, onDismissWelcome }) {
  const [mobileOpen, setMobileOpen] = useState(false);
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const { selectedState } = useStateContext();
  const crumbs = crumbsFor(pathname);

  const [activeGroupId, setActiveGroupId] = useState(() => deriveActiveGroupId(pathname));
  useEffect(() => {
    setActiveGroupId(deriveActiveGroupId(pathname));
  }, [pathname]);
  const activeGroup = RAIL_GROUPS.find((g) => g.id === activeGroupId) || RAIL_GROUPS[0];

  const logout = () => {
    auth.clear();
    setUser(null);
    navigate('/system');
  };
```

- [ ] **Step 3: Delete the old `renderNavItem` function**

Delete the entire `renderNavItem` function (original lines 213-367, everything between the `toggleGroup` line removed above and the `return (` that starts the JSX) — it rendered the old flat/accordion nav array, which no longer exists.

- [ ] **Step 4: Replace the `<aside>` sidebar block**

Replace the whole `<aside className="fixed inset-y-0 left-0 ...">...</aside>` block (original lines 371-428) with:

```jsx
      <aside className={`fixed inset-y-0 left-0 z-50 flex lg:translate-x-0 ${mobileOpen ? 'translate-x-0' : '-translate-x-full'}`}>
        <div className="flex w-[60px] shrink-0 flex-col items-center border-r border-white/[0.06] bg-[rgb(9,11,16)] py-4">
          <button type="button" onClick={() => navigate('/')} className="mb-4 flex h-8 w-8 items-center justify-center rounded-lg border border-brand text-brand">
            <Shield className="h-4 w-4" />
          </button>
          <nav className="flex flex-1 flex-col items-center gap-1 overflow-y-auto">
            {RAIL_GROUPS.map((group) => {
              const Icon = GROUP_ICONS[group.id];
              const isActive = group.id === activeGroupId;
              return (
                <button
                  key={group.id}
                  type="button"
                  title={group.label}
                  onClick={() => setActiveGroupId(group.id)}
                  className={`flex h-9 w-9 items-center justify-center rounded-lg transition ${
                    isActive ? 'bg-brand/[0.14] text-brand' : 'text-slate-500 hover:bg-white/[0.05] hover:text-slate-300'
                  }`}
                >
                  <Icon className="h-[17px] w-[17px]" />
                </button>
              );
            })}
          </nav>
        </div>

        <div className="flex w-[198px] shrink-0 flex-col border-r border-white/[0.06] bg-surface-raised/95 backdrop-blur-xl">
          <div className="border-b border-white/[0.06] px-4 py-[19px]">
            <p className="font-display text-base font-semibold">{activeGroup.label}</p>
          </div>
          <div className="flex-1 space-y-0.5 overflow-y-auto p-2">
            {activeGroup.items.map((item) => {
              const isProtected = item.to !== '/' && item.to !== '/system' && !user;
              return (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.to === '/'}
                  onClick={() => setMobileOpen(false)}
                  className={({ isActive }) => `nav-link ${isActive ? 'nav-link-active' : ''}`}
                >
                  <span className="flex-1">{item.label}</span>
                  {item.tag && (
                    <span className={`rounded px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wide ${
                      item.tag === 'Live' ? 'text-verdigris' : 'text-slate-500'
                    }`}>
                      {item.tag}
                    </span>
                  )}
                  {item.badge && pendingCount > 0 && (
                    <span className="rounded-full bg-risk-red/20 px-2 py-0.5 text-[10px] font-bold text-risk-red">
                      {pendingCount}
                    </span>
                  )}
                  {isProtected && <Lock className="h-3 w-3 shrink-0 text-slate-600" />}
                </NavLink>
              );
            })}
          </div>
          <div className="border-t border-white/[0.06] p-3.5">
            {health && (
              <div className="mb-2.5 flex items-center gap-2 text-[11.5px] text-slate-400">
                <span className={`h-1.5 w-1.5 rounded-full ${health.overall === 'healthy' ? 'bg-verdigris' : health.overall === 'degraded' ? 'bg-risk-amber' : 'bg-risk-red'}`} />
                {displayText(health.overall)} · {displayText(health.llm_mode)}
              </div>
            )}
            {user ? (
              <div className="flex items-center gap-2">
                <div className="keep-white flex h-[26px] w-[26px] items-center justify-center rounded-full bg-brand text-[10.5px] font-bold text-surface">
                  {displayText(user.username)?.slice(0, 2).toUpperCase()}
                </div>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-[12.5px] font-medium">{displayText(user.username)}</p>
                  <p className="truncate text-[10px] text-slate-500">{displayText(user.role)}</p>
                </div>
                <button type="button" onClick={logout} className="rounded-lg p-1 text-slate-500 hover:bg-white/5 hover:text-slate-300">
                  <LogOut className="h-3.5 w-3.5" />
                </button>
              </div>
            ) : (
              <button type="button" onClick={onLogin} className="btn-primary w-full text-xs">Sign in</button>
            )}
          </div>
        </div>
      </aside>
```

Note: `mobileOpen && <div ... onClick={() => setMobileOpen(false)} />` (the mobile backdrop, original line 430) and the `<X>` mobile-close button that was inside the old brand header both go away with the old single-column header block — mobile close now happens by tapping the backdrop or any nav-panel link. Keep the backdrop `<div>` as-is right after the `</aside>` closing tag.

- [ ] **Step 5: Update the main content offset margin**

The `<div className="flex min-w-0 flex-1 flex-col ...">` wrapper (original line 433) currently reads:

```jsx
      <div className={`flex min-w-0 flex-1 flex-col transition-all duration-300 ${sidebarCollapsed ? 'lg:ml-[64px]' : 'lg:ml-[272px]'}`}>
```

Replace with a fixed margin (no more collapsed/expanded toggle — the two-tier sidebar is always 60px + 198px = 258px):

```jsx
      <div className="flex min-w-0 flex-1 flex-col lg:ml-[258px]">
```

- [ ] **Step 6: Remove the now-unused sidebar-collapse toggle button in the topbar**

In the `<header>` block, remove this button (it toggled `sidebarCollapsed`, which no longer exists):

```jsx
            <button
              type="button"
              className="hidden rounded-lg p-2 text-slate-500 hover:bg-white/5 hover:text-slate-300 lg:block"
              onClick={() => setSidebarCollapsed((v) => !v)}
              title={sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            >
              <Menu className="h-5 w-5" />
            </button>
```

Leave the mobile hamburger button (`className="rounded-lg p-2 lg:hidden"`, `onClick={() => setMobileOpen(true)}`) in place — that one still applies.

- [ ] **Step 7: Remove the now-dead accordion CSS**

In `frontend/src/index.css`, the `.nav-link`/`.nav-link-active` rules (lines 96-102) are still used by the new nav-panel items — keep those. No CSS deletion needed for this task; the accordion-specific chevron/scrollbar styling was all inline Tailwind classes in the deleted JSX, not shared CSS.

- [ ] **Step 8: Run the existing test suite**

Run: `cd frontend && npm test`
Expected: all existing tests pass. (No test currently imports `Layout.jsx` directly, so this confirms nothing else broke.)

- [ ] **Step 9: Verify the build**

Run: `cd frontend && npm run build`
Expected: build succeeds with no unused-import warnings for anything still referenced (double check `ChevronDown`, `ChevronRight`, `Plus`, `HandCoins`, `INSURANCE_SECTIONS`, `insuranceSectionAccent` are fully removed from the file, not just from the import line).

- [ ] **Step 10: Manual check in the dev server**

Run: `cd frontend && npm run dev`. Confirm:
- The rail shows all 10 group icons plus the brand mark; clicking each one swaps the panel's title and item list without navigating.
- Clicking a nav-panel item navigates and highlights that item.
- Reloading on `/queue` opens with "UW operations" already focused in the panel and "Queue" highlighted.
- The mobile hamburger still opens/closes the sidebar below the `lg` breakpoint.

- [ ] **Step 11: Commit**

```bash
git add frontend/src/components/Layout.jsx
git commit -m "Rewrite sidebar as two-tier icon rail + nav panel"
```

---

## Self-Review

**Spec coverage:** Design tokens (colors, type) → Tasks 1-3. Sidebar restructure (rail + panel, real routing) → Tasks 4-5. Component mapping table (`.glass-card`→`.card`-equivalent, `.btn-primary` flat brass, nav-link gradient→flat) → Task 3 (shared classes) and Task 5 (nav-link usage in the new panel already resolves through the untouched `.nav-link`/`.nav-link-active` classes, which read `brand`/`surface` tokens that Tasks 2-3 already repointed — no separate edit needed there). Page-by-page sweep (StatCard/Badge/EmptyState adoption) is explicitly out of scope for this plan, called out in Global Constraints and the Goal — matches the spec's phase 3 boundary.

**Placeholder scan:** No TBD/TODO markers; every step has literal code, not a description of code.

**Type consistency:** `RAIL_GROUPS` shape (`{id, label, items: [{to, label, tag?, badge?}], scrollItems?}`) defined in Task 4 is consumed with the exact same field names in Task 5 (`group.id`, `group.label`, `group.items`, `item.to`, `item.label`, `item.tag`, `item.badge`, `group.scrollItems`). `deriveActiveGroupId(pathname, groups)` signature matches its test calls and its one call site in Task 5.

---

## Out of scope (follow-up plans)

Phase 3 — page-by-page component adoption, batched by nav section (Overview/UW Ops → Analytics → Insurance lines → Post-Decision/Governance → Integrations/Account, per the earlier audit's priority order) — is a separate, much larger effort and should get its own plan(s) once this one is merged and the new tokens exist for pages to adopt.
