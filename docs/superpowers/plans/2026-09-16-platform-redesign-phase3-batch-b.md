# Platform Redesign Phase 3 Batch B Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the cross-page divergences among the Insurance hub pages, line-detail pages, and their supporting pages: missing `PageBack`, hand-rolled Live/Catalog pills instead of `Badge`, inconsistent `backTo`/`backLabel` into `LineDetailLayout`, and missing `EmptyState` usage.

**Architecture:** Five tasks. Task 1 adds two new status colors to the shared `Badge` component (foundational — later tasks consume it). Tasks 2-5 each touch a small, related group of page files, applying one category of fix per task.

**Tech Stack:** React 18, Tailwind CSS 3. No new dependencies — `Badge`, `EmptyState`, `PageBack` all already exist in `frontend/src/components/ui.jsx`.

**Spec:** `docs/superpowers/specs/2026-09-16-platform-redesign-phase3-scope.md` (Batch B)

## Global Constraints

- Only the files named in each task — no other pages, no shared files beyond `components/ui.jsx` (Task 1 only).
- `Badge`'s `catalog` color must be slate (`bg-slate-500/20 text-slate-300 ring-slate-500/20`), matching the majority pattern already used in `Insurance.jsx`/`InsuranceSegment.jsx` — NOT the amber currently hand-rolled in `GeneralInsurance.jsx` alone. Adopting `Badge` there is expected to change that one page's Catalog pill color from amber to slate; this is intentional, not a regression.
- `npm run build` and `npm test` (from `frontend/`) must pass after every task.

---

### Task 1: Add `live`/`catalog` status colors to `Badge`

**Files:**
- Modify: `frontend/src/components/ui.jsx:126-196` (the `colors` map inside `Badge`)

**Interfaces:**
- Produces: `<Badge status="live" />` renders "Live" in emerald; `<Badge status="catalog" />` renders "Catalog" in slate. (Badge's existing `capitalize` CSS class turns the lowercase status into displayed "Live"/"Catalog" automatically — no `label` prop needed unless overriding the text, e.g. `label="Coming soon"`.)

- [ ] **Step 1: Add the two color entries**

In `frontend/src/components/ui.jsx`, inside the `Badge` function's `colors` object, add these two entries (anywhere in the object; adding them right after the opening `ok:` line keeps related statuses together):

```js
    live: 'bg-emerald-500/15 text-emerald-400 ring-emerald-500/20',
    catalog: 'bg-slate-500/20 text-slate-300 ring-slate-500/20',
```

- [ ] **Step 2: Verify the build**

Run: `cd frontend && npm run build`
Expected: build succeeds.

- [ ] **Step 3: Run the existing test suite**

Run: `cd frontend && npm test`
Expected: all existing tests pass — this is an additive change to a map, no existing status keys change value.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/ui.jsx
git commit -m "Add live/catalog status colors to Badge"
```

---

### Task 2: Insurance hub pages — add missing `PageBack`, adopt `Badge` for Live/Catalog

**Files:**
- Modify: `frontend/src/pages/GeneralInsurance.jsx`
- Modify: `frontend/src/pages/HealthInsurance.jsx`
- Modify: `frontend/src/pages/CommercialInsurance.jsx`
- Modify: `frontend/src/pages/LifeInsurance.jsx`

**Interfaces:**
- Consumes: `Badge` and `PageBack` from `../components/ui` (Task 1 must land first for `Badge`'s `live`/`catalog` colors to exist).

Three of the four hub pages (`GeneralInsurance.jsx`, `HealthInsurance.jsx`, `CommercialInsurance.jsx`) are missing the `PageBack` link that `LifeInsurance.jsx` already has. All four hand-roll their Live/Catalog pill instead of using `Badge`.

- [ ] **Step 1: Add `PageBack` import to the three files missing it**

In `frontend/src/pages/GeneralInsurance.jsx`, add to the top imports (after the existing `import SubmissionJobsList from '../components/SubmissionJobsList';` line):
```jsx
import { PageBack, Badge } from '../components/ui';
```
Do the same in `frontend/src/pages/HealthInsurance.jsx` and `frontend/src/pages/CommercialInsurance.jsx` (same import line, added after their own last existing import).

In `frontend/src/pages/LifeInsurance.jsx`, it already imports `PageBack` (line 7: `import { PageBack } from '../components/ui';`) — change that line to also import `Badge`:
```jsx
import { PageBack, Badge } from '../components/ui';
```

- [ ] **Step 2: Add the missing `PageBack` to the three hub pages**

In `frontend/src/pages/GeneralInsurance.jsx`, replace:
```jsx
      <div>
        <div className="flex items-start gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-sky-500/15 text-sky-400">
```
with:
```jsx
      <div>
        <div className="mb-3">
          <PageBack to="/insurance" label="All insurance" />
        </div>
        <div className="flex items-start gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-sky-500/15 text-sky-400">
```

In `frontend/src/pages/HealthInsurance.jsx`, replace:
```jsx
      <div>
        <div className="flex items-start gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-teal-500/15 text-teal-400">
```
with:
```jsx
      <div>
        <div className="mb-3">
          <PageBack to="/insurance" label="All insurance" />
        </div>
        <div className="flex items-start gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-teal-500/15 text-teal-400">
```

In `frontend/src/pages/CommercialInsurance.jsx`, replace:
```jsx
      <div>
        <div className="flex items-start gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-brand/15 text-brand">
```
with:
```jsx
      <div>
        <div className="mb-3">
          <PageBack to="/insurance" label="All insurance" />
        </div>
        <div className="flex items-start gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-brand/15 text-brand">
```

`LifeInsurance.jsx` already has this — no change needed there for this step.

- [ ] **Step 3: Replace the hand-rolled Live/Catalog pill with `Badge` in all four files**

In `frontend/src/pages/GeneralInsurance.jsx`, replace:
```jsx
              <h1 className="text-3xl font-bold tracking-tight text-slate-100">{hub.title}</h1>
              <span className="rounded-full bg-amber-500/15 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-amber-400">
                Catalog
              </span>
```
with:
```jsx
              <h1 className="text-3xl font-bold tracking-tight text-slate-100">{hub.title}</h1>
              <Badge status="catalog" />
```

In `frontend/src/pages/HealthInsurance.jsx`, replace:
```jsx
              <h1 className="text-3xl font-bold tracking-tight text-slate-100">{hub.title}</h1>
              <span className="rounded-full bg-emerald-500/15 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-emerald-400">
                Live
              </span>
```
with:
```jsx
              <h1 className="text-3xl font-bold tracking-tight text-slate-100">{hub.title}</h1>
              <Badge status="live" />
```

In `frontend/src/pages/CommercialInsurance.jsx`, replace:
```jsx
              <h1 className="text-3xl font-bold tracking-tight text-slate-100">{hub.title}</h1>
              <span className="rounded-full bg-emerald-500/15 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-emerald-400">
                Live
              </span>
```
with:
```jsx
              <h1 className="text-3xl font-bold tracking-tight text-slate-100">{hub.title}</h1>
              <Badge status="live" />
```

In `frontend/src/pages/LifeInsurance.jsx`, replace:
```jsx
              <h1 className="text-3xl font-bold tracking-tight text-slate-100">{hub.title}</h1>
              <span className="rounded-full bg-emerald-500/15 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-emerald-400">
                Live
              </span>
```
with:
```jsx
              <h1 className="text-3xl font-bold tracking-tight text-slate-100">{hub.title}</h1>
              <Badge status="live" />
```

- [ ] **Step 4: Verify the build**

Run: `cd frontend && npm run build`
Expected: build succeeds.

- [ ] **Step 5: Run the existing test suite**

Run: `cd frontend && npm test`
Expected: all existing tests pass. If a test asserts the old hand-rolled pill markup or the amber Catalog color on `GeneralInsurance.jsx`, update the assertion to match the new `Badge`-rendered output rather than reverting the change.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pages/GeneralInsurance.jsx frontend/src/pages/HealthInsurance.jsx frontend/src/pages/CommercialInsurance.jsx frontend/src/pages/LifeInsurance.jsx
git commit -m "Add missing PageBack and adopt Badge on insurance hub pages"
```

---

### Task 3: Line-detail pages — pass `backTo`/`backLabel` to `LineDetailLayout`

**Files:**
- Modify: `frontend/src/pages/GeneralLine.jsx`
- Modify: `frontend/src/pages/HealthLine.jsx`
- Modify: `frontend/src/pages/CommercialLine.jsx`

**Interfaces:**
- Consumes: `LineDetailLayout`'s existing `backTo`/`backLabel` props (already implemented in `frontend/src/components/LineDetailLayout.jsx`, already used by `frontend/src/pages/LifeLine.jsx` — no changes to `LineDetailLayout.jsx` itself).

`LifeLine.jsx` already passes `backTo="/insurance/life"` and `backLabel="Life insurance hub"`. The other three line pages render `LineDetailLayout` without either prop, so they show no back-link at all.

- [ ] **Step 1: Add `backTo`/`backLabel` to the three files**

In `frontend/src/pages/GeneralLine.jsx`, replace:
```jsx
    <LineDetailLayout
      line={line}
      eyebrowLabel="Personal Lines"
      accent="sky"
      icon={Icon}
      presets={presets}
```
with:
```jsx
    <LineDetailLayout
      line={line}
      eyebrowLabel="Personal Lines"
      accent="sky"
      icon={Icon}
      backTo="/insurance/general"
      backLabel="General insurance hub"
      presets={presets}
```

In `frontend/src/pages/HealthLine.jsx`, replace:
```jsx
    <LineDetailLayout
      line={line}
      eyebrowLabel="Health Insurance"
      accent="teal"
      icon={Icon}
      presets={presets}
```
with:
```jsx
    <LineDetailLayout
      line={line}
      eyebrowLabel="Health Insurance"
      accent="teal"
      icon={Icon}
      backTo="/insurance/health"
      backLabel="Health insurance hub"
      presets={presets}
```

In `frontend/src/pages/CommercialLine.jsx`, replace:
```jsx
    <LineDetailLayout
      line={line}
      eyebrowLabel="Business / Commercial"
      accent="brand"
      icon={Icon}
      presets={presets}
```
with:
```jsx
    <LineDetailLayout
      line={line}
      eyebrowLabel="Business / Commercial"
      accent="brand"
      icon={Icon}
      backTo="/insurance/commercial"
      backLabel="Commercial insurance hub"
      presets={presets}
```

- [ ] **Step 2: Verify the build**

Run: `cd frontend && npm run build`
Expected: build succeeds.

- [ ] **Step 3: Run the existing test suite**

Run: `cd frontend && npm test`
Expected: all existing tests pass.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/GeneralLine.jsx frontend/src/pages/HealthLine.jsx frontend/src/pages/CommercialLine.jsx
git commit -m "Add back-to-hub link to General/Health/Commercial line-detail pages"
```

---

### Task 4: `Insurance.jsx` + `InsuranceSegment.jsx` — adopt `Badge`, add `EmptyState`

**Files:**
- Modify: `frontend/src/pages/Insurance.jsx`
- Modify: `frontend/src/pages/InsuranceSegment.jsx`

**Interfaces:**
- Consumes: `Badge`, `EmptyState` from `../components/ui` (both already imported in `Insurance.jsx`; `InsuranceSegment.jsx` does not currently import from `../components/ui` at all — add the import).

- [ ] **Step 1: `Insurance.jsx` — add `EmptyState` to the existing import**

Replace:
```jsx
import { Badge, ScoreBadge, PriorityBadge, AssigneeAvatar } from '../components/ui';
```
with:
```jsx
import { Badge, ScoreBadge, PriorityBadge, AssigneeAvatar, EmptyState } from '../components/ui';
```

- [ ] **Step 2: `Insurance.jsx` — replace the per-section hand-rolled pill with `Badge`**

Replace:
```jsx
                      <span className={`rounded-full px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wider ${
                        section.status === 'live'
                          ? 'bg-emerald-500/15 text-emerald-400'
                          : 'bg-slate-500/20 text-slate-300'
                      }`}>
                        {section.disabled ? 'Coming soon' : section.status === 'live' ? 'Live' : 'Catalog'}
                      </span>
```
with:
```jsx
                      <Badge
                        status={section.disabled ? 'catalog' : section.status === 'live' ? 'live' : 'catalog'}
                        label={section.disabled ? 'Coming soon' : undefined}
                      />
```

- [ ] **Step 3: `Insurance.jsx` — replace the "No jobs yet" paragraph with `EmptyState`**

Replace:
```jsx
        {!recent.length ? (
          <p className="px-5 py-8 text-sm text-slate-500">No jobs yet. Open a section and run a package.</p>
        ) : (
```
with:
```jsx
        {!recent.length ? (
          <EmptyState title="No jobs yet" description="Open a section and run a package." />
        ) : (
```

- [ ] **Step 4: `InsuranceSegment.jsx` — add the `ui` import**

Replace:
```jsx
import { endpoints } from '../lib/api';
import { getInsuranceSection, insuranceSectionAccent } from '../lib/insuranceSections';
```
with:
```jsx
import { endpoints } from '../lib/api';
import { getInsuranceSection, insuranceSectionAccent } from '../lib/insuranceSections';
import { Badge } from '../components/ui';
```

- [ ] **Step 5: `InsuranceSegment.jsx` — replace the section-level pill with `Badge`**

Replace:
```jsx
              <span className={`rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider ${
                sectionStatus === 'live'
                  ? 'bg-emerald-500/15 text-emerald-400'
                  : 'bg-slate-500/20 text-slate-300'
              }`}>
                {sectionStatus === 'live' ? 'Live' : 'Catalog'}
              </span>
```
with:
```jsx
              <Badge status={sectionStatus} />
```

- [ ] **Step 6: `InsuranceSegment.jsx` — replace the per-product pill with `Badge`**

Replace:
```jsx
                {p.cat && liveByCat[p.cat] ? (
                  <span className="shrink-0 rounded-full bg-emerald-500/15 px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wider text-emerald-400">
                    Live
                  </span>
                ) : null}
```
with:
```jsx
                {p.cat && liveByCat[p.cat] ? <Badge status="live" /> : null}
```

- [ ] **Step 7: Verify the build**

Run: `cd frontend && npm run build`
Expected: build succeeds.

- [ ] **Step 8: Run the existing test suite**

Run: `cd frontend && npm test`
Expected: all existing tests pass.

- [ ] **Step 9: Commit**

```bash
git add frontend/src/pages/Insurance.jsx frontend/src/pages/InsuranceSegment.jsx
git commit -m "Adopt Badge/EmptyState in Insurance.jsx and InsuranceSegment.jsx"
```

---

### Task 5: `InsuranceJobDetail.jsx` error/not-found states → `EmptyState`; `CommercialReference.jsx` back link → `PageBack`

**Files:**
- Modify: `frontend/src/pages/InsuranceJobDetail.jsx`
- Modify: `frontend/src/pages/CommercialReference.jsx`

**Interfaces:**
- Consumes: `EmptyState`, `PageBack` from `../components/ui`.

The loading spinner in `InsuranceJobDetail.jsx` is left as-is (`EmptyState` isn't a fit for an inline spinner) — only its error and not-found states change. `InsuranceJobDetail.jsx`'s own hand-rolled history-based back button (near the top of the file, `onClick={() => (window.history.length > 1 ? navigate(-1) : navigate('/insurance'))}`) is also left as-is — it deliberately goes back in browser history rather than to a fixed route, since this page is reached from many different list views; that's a different, intentional behavior from `PageBack`'s fixed-route pattern, not an oversight.

- [ ] **Step 1: `InsuranceJobDetail.jsx` — add the `ui` import**

Replace:
```jsx
import { displayText } from '../lib/safe';
```
with:
```jsx
import { displayText } from '../lib/safe';
import { EmptyState } from '../components/ui';
```

- [ ] **Step 2: `InsuranceJobDetail.jsx` — replace the error state**

Replace:
```jsx
  if (error) {
    return (
      <div className="py-16 text-center">
        <p className="text-red-400">{error}</p>
        <button onClick={() => navigate('/insurance')} className="mt-4 text-sm text-slate-400 hover:text-white">Back to Insurance</button>
      </div>
    );
  }
```
with:
```jsx
  if (error) {
    return (
      <EmptyState
        title="Couldn't load this submission"
        description={error}
        action={<button onClick={() => navigate('/insurance')} className="btn-secondary btn-sm text-sm">Back to Insurance</button>}
      />
    );
  }
```

- [ ] **Step 3: `InsuranceJobDetail.jsx` — replace the not-found state**

Replace:
```jsx
  if (!job) {
    return (
      <div className="py-16 text-center">
        <p className="text-slate-400">Submission not found.</p>
        <button onClick={() => navigate('/insurance')} className="mt-4 text-sm text-slate-400 hover:text-white">Back to Insurance</button>
      </div>
    );
  }
```
with:
```jsx
  if (!job) {
    return (
      <EmptyState
        title="Submission not found"
        action={<button onClick={() => navigate('/insurance')} className="btn-secondary btn-sm text-sm">Back to Insurance</button>}
      />
    );
  }
```

- [ ] **Step 4: `CommercialReference.jsx` — replace the hand-rolled back link with `PageBack`**

This file does not currently import from `../components/ui` at all. Add the import — after the existing `import { endpoints } from '../lib/api';` line, add:
```jsx
import { PageBack } from '../components/ui';
```

Then replace:
```jsx
            <Link to="/insurance/commercial" className="mt-2 inline-flex items-center gap-1 text-xs text-brand hover:underline">
              ← Back to submissions
            </Link>
```
with:
```jsx
            <div className="mt-2">
              <PageBack to="/insurance/commercial" label="Back to submissions" />
            </div>
```

After this change, check whether `Link` (from `react-router-dom`) is still used anywhere else in this file — if this was its only use, remove the now-unused `import { Link } from 'react-router-dom';` line too.

- [ ] **Step 5: Verify the build**

Run: `cd frontend && npm run build`
Expected: build succeeds.

- [ ] **Step 6: Run the existing test suite**

Run: `cd frontend && npm test`
Expected: all existing tests pass.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/pages/InsuranceJobDetail.jsx frontend/src/pages/CommercialReference.jsx
git commit -m "Use EmptyState in InsuranceJobDetail, PageBack in CommercialReference"
```

---

## Self-Review

**Spec coverage:** Batch B's scope items (missing PageBack, hand-rolled Live/Catalog pills, backTo/backLabel inconsistency, missing EmptyState) are each covered by Tasks 2-5. Task 1 is the prerequisite Badge color addition.

**Placeholder scan:** Task 5 Step 4 is intentionally descriptive rather than exact-code, because `CommercialReference.jsx`'s current back-link content wasn't fully re-verified line-by-line after Task 1 of Batch A changed a nearby line in this same file — the implementer is told exactly what to search for and what the fallback reasoning is, which is a legitimate "verify then adapt" instruction, not a vague "add appropriate handling."

**Type consistency:** `Badge`'s `status`/`label` prop usage is identical across every call site introduced in Tasks 2 and 4. `LineDetailLayout`'s `backTo`/`backLabel` props (Task 3) match the exact prop names already used by `LifeLine.jsx` and already implemented in `LineDetailLayout.jsx`.
