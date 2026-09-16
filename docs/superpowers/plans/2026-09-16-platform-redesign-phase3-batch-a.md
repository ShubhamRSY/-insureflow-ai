# Platform Redesign Phase 3 Batch A Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Standardize the page `<h1>` size on the 7 pages that use `text-2xl` up to the app-wide majority, `text-3xl`, so every page header reads consistently.

**Architecture:** Seven single-line edits across seven files, each changing one `<h1>` element's className. No logic, no new components, no shared file touched. Small enough to be one batched implementer dispatch rather than seven separate task cycles, per the "batch small same-shape work" guidance — all seven edits are the same category of change.

**Tech Stack:** React 18, Tailwind CSS 3 (className strings only — no config/CSS file changes in this batch).

**Spec:** `docs/superpowers/specs/2026-09-16-platform-redesign-phase3-scope.md` (Batch A)

## Global Constraints

- Only the 7 files listed below — do not touch `components/LoginModal.jsx` (its `text-2xl` instances are modal-dialog `<h2>` titles, a different UI context, intentionally out of scope).
- Change only the className string on the named `<h1>` line in each file — no other edits.
- `CommercialInsurance.jsx`, `GeneralInsurance.jsx`, `HealthInsurance.jsx`, `LifeInsurance.jsx` already include `text-slate-100` in their className — keep it. `Mortgage.jsx`, `Lending.jsx`, `CommercialReference.jsx` do not have `text-slate-100` in their current className — do not add it; this batch only changes `text-2xl` to `text-3xl`, nothing else, matching each file's own current style exactly apart from that one token.
- `npm run build` and `npm test` (from `frontend/`) must pass after the change.

---

### Task 1: Bump 7 page headers from `text-2xl` to `text-3xl`

**Files:**
- Modify: `frontend/src/pages/Mortgage.jsx:42`
- Modify: `frontend/src/pages/Lending.jsx:103`
- Modify: `frontend/src/pages/CommercialInsurance.jsx:48`
- Modify: `frontend/src/pages/CommercialReference.jsx:118`
- Modify: `frontend/src/pages/GeneralInsurance.jsx:47`
- Modify: `frontend/src/pages/HealthInsurance.jsx:47`
- Modify: `frontend/src/pages/LifeInsurance.jsx:51`

**Interfaces:** None — no exports, no props, no shared code touched.

- [ ] **Step 1: Edit all 7 files**

In `frontend/src/pages/Mortgage.jsx`, line 42, replace:
```jsx
          <h1 className="text-2xl font-bold tracking-tight">Mortgage Underwriting</h1>
```
with:
```jsx
          <h1 className="text-3xl font-bold tracking-tight">Mortgage Underwriting</h1>
```

In `frontend/src/pages/Lending.jsx`, line 103, replace:
```jsx
            <h1 className="text-2xl font-bold tracking-tight">Lending Underwriting</h1>
```
with:
```jsx
            <h1 className="text-3xl font-bold tracking-tight">Lending Underwriting</h1>
```

In `frontend/src/pages/CommercialInsurance.jsx`, line 48, replace:
```jsx
              <h1 className="text-2xl font-bold tracking-tight text-slate-100">{hub.title}</h1>
```
with:
```jsx
              <h1 className="text-3xl font-bold tracking-tight text-slate-100">{hub.title}</h1>
```

In `frontend/src/pages/CommercialReference.jsx`, line 118, replace:
```jsx
            <h1 className="text-2xl font-bold tracking-tight text-slate-100">Commercial insurance notebook</h1>
```
with:
```jsx
            <h1 className="text-3xl font-bold tracking-tight text-slate-100">Commercial insurance notebook</h1>
```

In `frontend/src/pages/GeneralInsurance.jsx`, line 47, replace:
```jsx
              <h1 className="text-2xl font-bold tracking-tight text-slate-100">{hub.title}</h1>
```
with:
```jsx
              <h1 className="text-3xl font-bold tracking-tight text-slate-100">{hub.title}</h1>
```

In `frontend/src/pages/HealthInsurance.jsx`, line 47, replace:
```jsx
              <h1 className="text-2xl font-bold tracking-tight text-slate-100">{hub.title}</h1>
```
with:
```jsx
              <h1 className="text-3xl font-bold tracking-tight text-slate-100">{hub.title}</h1>
```

In `frontend/src/pages/LifeInsurance.jsx`, line 51, replace:
```jsx
              <h1 className="text-2xl font-bold tracking-tight text-slate-100">{hub.title}</h1>
```
with:
```jsx
              <h1 className="text-3xl font-bold tracking-tight text-slate-100">{hub.title}</h1>
```

- [ ] **Step 2: Verify the build**

Run: `cd frontend && npm run build`
Expected: build succeeds.

- [ ] **Step 3: Run the existing test suite**

Run: `cd frontend && npm test`
Expected: all existing tests still pass — check in particular whether any test asserts a specific className string on these headers (a snapshot or a `toHaveClass` check); if one does and fails, that's expected given this change and the test should be updated to expect `text-3xl` instead of `text-2xl`, not reverted.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/Mortgage.jsx frontend/src/pages/Lending.jsx frontend/src/pages/CommercialInsurance.jsx frontend/src/pages/CommercialReference.jsx frontend/src/pages/GeneralInsurance.jsx frontend/src/pages/HealthInsurance.jsx frontend/src/pages/LifeInsurance.jsx
git commit -m "Standardize page headers on text-3xl (app-wide majority)"
```

---

## Self-Review

**Spec coverage:** Batch A's entire scope (7 files, one edit each) is covered by this single task.

**Placeholder scan:** None — every file has its exact current line and exact replacement line.

**Type consistency:** N/A — no interfaces, no shared types.
