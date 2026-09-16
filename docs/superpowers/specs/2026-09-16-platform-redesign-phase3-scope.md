# Platform redesign Phase 3 — page-by-page component adoption

Extends: [2026-09-16-platform-redesign-design.md](2026-09-16-platform-redesign-design.md) (tokens/sidebar, phases 1-2, merged).

## Why a separate scope doc

Phase 1-2 repointed global tokens and rewrote the sidebar shell without touching any page. Every page already renders in the new brass/ink/serif system as a side effect. What's left is the drift documented in the original 5-agent audit (see conversation history): pages that hand-roll markup instead of reusing `StatCard`/`Badge`/`EmptyState`/`Tabs`, inconsistent header sizes, missing empty states, one worst-offender file. Phase 1-2 fixed the shared components those pages *should* be using — Phase 3 is getting the pages to actually use them.

45 pages is too large for one plan. Decomposed into 6 batches, each independently plannable/testable, in priority order:

## Batches

**A. Header size normalization** — 7 *page* files use `text-2xl` for their page `<h1>` where 29 use `text-3xl` (confirmed majority by direct count). Standardize the 7 minority files up: `Mortgage.jsx`, `Lending.jsx`, `CommercialInsurance.jsx`, `CommercialReference.jsx`, `GeneralInsurance.jsx`, `HealthInsurance.jsx`, `LifeInsurance.jsx`. (`components/LoginModal.jsx` also matched the original grep but its `text-2xl` instances are `<h2>` modal-dialog titles — First-time Setup, Create Account, Reset Password, Welcome back — a different UI context than a page header; excluded from this batch, left as-is.) Smallest, safest batch — one category of edit repeated across 7 files, no logic changes. Also resolves the hub-vs-line-detail header mismatch the audit found (hub pages currently `text-2xl`, `LineDetailLayout.jsx` already `text-3xl`) as a side effect.

**B. Insurance hub + line-detail consistency** — cross-page divergences the audit found among the 4 hub pages (`GeneralInsurance`/`HealthInsurance`/`LifeInsurance`/`CommercialInsurance`) and 4 line-detail pages (`GeneralLine`/`HealthLine`/`LifeLine`/`CommercialLine`): missing `PageBack` on 3 of 4 hubs, hand-rolled Live/Catalog pills duplicated 6× instead of `Badge`, inconsistent `backTo`/`backLabel` passed to `LineDetailLayout`, missing `EmptyState` for "no jobs"/error states in `Insurance.jsx`/`InsuranceSegment.jsx`/`InsuranceJobDetail.jsx` (3 different hand-rolled give-up states in one file).

**C. `StatCard` adoption app-wide** — the single most repeated pattern in the audit. Hand-rolled stat tiles in `Queue.jsx`, `EvalTrends.jsx` (2 spots), `Issuance.jsx`, `ProducerComms.jsx`, `Registry.jsx`, `RegulatoryReview.jsx`, `StaffUnderwriting.jsx`, `AuthorityMatrix.jsx` (tier cards), `LineUnderwriting.jsx` (capability cards), plus the duplicated product-card markup shared between `Mortgage.jsx`/`Lending.jsx`.

**D. `Badge`/`PriorityBadge` adoption + filter-pills→`Tabs`** — ad-hoc color-mapping functions and hand-rolled pills: `Integrations.jsx` kind pills, `Settings.jsx` `ROLE_BADGE` map, `System.jsx`, `UWDashboard.jsx` `SEVERITY_COLORS`/`STATUS_STYLES`, `RenewalDashboard.jsx` `deltaColor`, `BusinessKPIs.jsx`, `MarketAdmin.jsx` phase color (also fixes a stray `text-green-400` vs the app's `text-emerald-400`), `AuthorityMatrix.jsx` tier/co-sign badges mixed inconsistently in one table. Filter-pill buttons in `Webhooks.jsx`/`ProducerComms.jsx`/`Registry.jsx` reimplement the `Tabs` component instead of using it.

**E. `UWDashboard.jsx` deep clean** — the audit's worst-offender file: doesn't import `components/ui` at all, defines its own `MetricCard` duplicating `StatCard`, raw `bg-slate-800/50` panels instead of `.glass-card` (6 spots), `max-w-[1600px]` instead of the `max-w-6xl` norm, submission-row styling matching nothing else in the app, hand-rolled empty states. Big enough and divergent enough to deserve its own focused pass rather than folding into batch C/D.

**F. Misc structural** — page-width drift (`Overview.jsx` `max-w-7xl`, `MarketAdmin.jsx` `max-w-4xl` → `max-w-6xl`), duplicated inline danger/success button styles in `Workflow.jsx`/`UWWorkbench.jsx` (add `.btn-danger`/`.btn-success` next to `.btn-primary`/`.btn-secondary`), table header density split two ways (`px-6 py-3 text-xs` vs `px-3 py-2 text-[10px]`, pick one), `Pilot.jsx`'s loading state drops the whole header instead of keeping it visible like every other page.

## Process

Each batch gets its own implementation plan (`docs/superpowers/plans/`), executed via subagent-driven-development in its own worktree, same as Phase 1-2: per-task review, final whole-branch review, merge to main, report rulings and any parked findings before moving to the next batch.
