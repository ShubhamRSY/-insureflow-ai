# Platform redesign — "Ledger, not glow"

Approved direction: [mockups](https://claude.ai/artifact/7FsScjJkWmu3vDn8cEDcxa) (Overview, Queue, Life Insurance line-detail).

## Why

Current UI (`frontend/`) is a generic dark-SaaS look: indigo/purple gradients, glassmorphism (`glass-card`), mesh-gradient backgrounds, ALL-CAPS tracking-wide labels. It doesn't say anything specific about underwriting. New direction leans into the subject matter: underwriting is about writing/certifying a risk — hairline structure instead of blur/glow, a serif with gravitas for headlines, monospace reserved for the numbers the product claims to trace (policy numbers, rates, scores, IDs).

An earlier audit (5 parallel agents across all ~45 pages, see conversation history) found the *current* design system already has drift: hand-rolled markup duplicating `StatCard`/`Badge`/`EmptyState`, inconsistent header sizes, inconsistent table density. That cleanup is superseded by this redesign — pages get the new tokens/components in the same pass rather than being fixed twice.

## Design tokens

Colors (dark theme; a light-theme mapping can follow the same pattern the current `index.css` uses):

| Token | Hex | Use |
|---|---|---|
| `ink` | `#0B0E14` | page background |
| `rail` | `#090B10` | icon rail background (darkest) |
| `slate` | `#12161F` | nav panel / raised surface |
| `slate2` | `#171C26` | cards, table header bg |
| `rule` | `#262C38` | hairline borders |
| `rule-soft` | `#1D2330` | table row dividers |
| `bone` | `#E7E9EE` | primary text |
| `muted` | `#8B93A3` | secondary text |
| `muted2` | `#5B6472` | tertiary text, "catalog"/inactive tags |
| `brass` | `#C79A46` | **the one accent** — primary buttons, active nav, decision moments only |
| `verdigris` | `#3E8E82` | secondary accent — "live"/approved/success |
| `risk-red` | `#C0524A` | hot/high-risk |
| `risk-amber` | `#C98A3A` | warm/medium-risk |

Principles: numbers earn monospace, prose doesn't. One accent (brass), spent only on decisions/active states — don't reuse it for category tagging (mockup review caught this: dropped a third ad-hoc blue and stopped using brass for the "mortgage" demo tag). Hairlines over shadows/blur — no `backdrop-blur`, no glow, no mesh gradients. Sentence case labels, not ALL-CAPS. No arrow glyphs appended to buttons.

Type: **Source Serif 4** (Google Fonts) for display/headlines, **IBM Plex Sans** for UI/body, **IBM Plex Mono** for numbers/IDs/rates only.

## Sidebar restructure

Current (`Layout.jsx`): single 272px column, accordion sections, gradient active-state, collapses to a 64px icon-only rail via a toggle.

New: two-tier, always both visible —
- **Rail** (60px, `rail` bg): one icon per top-level nav group (Overview, System, Insurance, Reference, Mortgage & Lending, UW Operations, Post-Decision, Analytics, Governance, Integrations, Account), brand mark at top. Active group = brass icon + brass-tinted bg square.
- **Nav panel** (198px, `slate` bg): shows the active group's children as a flat list (title in Source Serif 4 at top, health pill + user block pinned at bottom). Clicking a different rail icon swaps which group's children the panel shows — this needs local state (`activeGroup`) independent of the route-derived active *item* within that group.

This replaces the accordion (`openGroups` state, chevron expand/collapse) entirely — every group is always "reachable" from the rail, only one group's children render at a time.

## Component mapping (old → new)

| Old class/pattern | New |
|---|---|
| `.glass-card` (blur + shadow) | `.card` — `slate2` bg, 1px `rule` border, 8px radius, no blur/shadow |
| `.btn-primary` (gradient) | flat `brass` bg, `ink` text |
| `.nav-link` / `.nav-link-active` (gradient wash) | rail item (icon, brass-tinted bg when active) + nav-panel item (brass text + brass-tinted bg when active) |
| ALL-CAPS `text-xs uppercase tracking-wider` labels | sentence case, `muted`/`muted2` color, no `uppercase` |
| Hand-rolled stat tiles (Queue.jsx etc.) | `StatCard`, restyled to new tokens — **and now actually used**, closing the audit findings from the earlier pass |
| Hand-rolled status pills / color-map functions | `Badge`/`PriorityBadge`, restyled to new tokens |
| Mesh-gradient hero background | flat `ink`, no `bg-mesh`/`hero-glow` |

## Rollout phases

1. **Global tokens** — `tailwind.config.js` colors/fontFamily, `index.css` CSS custom properties (`--ry-*`) and `@layer components` classes (`.card`, `.btn-primary`, `.btn-secondary`, `.badge`), Google Fonts `<link>`. This is the one place that cascades to every page automatically via existing Tailwind/CSS-var indirection.
2. **`Layout.jsx` sidebar rewrite** — rail + nav panel, real routing/active-state logic, replacing the accordion.
3. **Page-by-page sweep** — apply new component usage per page, batched by nav section (reusing the priority order from the earlier audit: header sizes → Badge/EmptyState adoption in Insurance hub + line-detail pages → StatCard adoption app-wide → UWDashboard.jsx deep clean → misc structural fixes), now targeting the new tokens instead of the old ones.

Each phase is independently reviewable/testable (existing Vitest suite + manual check in the dev server) before moving to the next.
