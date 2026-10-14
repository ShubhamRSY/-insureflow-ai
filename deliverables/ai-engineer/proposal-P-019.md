# Proposal P-019 — Switch model provider to Vertex AI (Gemini 2.5 Flash/Pro) and OCR provider to Document AI layout

- Author: @ai-engineer-assistant
- Date: 2026-10-13
- For: @user (the AI Engineer)
- Task: T-099
- Decisions referenced: D-011 (no paid API), D-012, D-013, D-017, D-020, D-038, D-047
- Status: PROPOSAL. Not approved. Not implemented.
- No code, prompt, OCR setting, cache file, scorer, or score file was changed to write this. No model call was made. No scorer was run.
- Synthetic data only. Not a production approval. @model-risk can still block production.
- Published scores are not recounted.

---

## Statement of the change

This proposal is to switch the extraction model provider from the current Groq/OpenAI-compatible host (set via `LLM_BASE_URL`, `LLM_MODEL`, `LLM_API_KEY` in the shell) to **Vertex AI** using **Gemini 2.5 Flash and Gemini 2.5 Pro**, and to switch the OCR path from **Tesseract** (local) to **Google Document AI Layout Parser**, replacing both providers as specified. The change would be provider-level only; it does not change the extraction contract (fields, schema, gates, or the status logic).

## Trade-offs

- **Cost predictability vs zero cost**: Vertex AI and Document AI are paid services (see price basis below). The current setup runs with free/local options (Groq free tier as allowed by D-012; Tesseract is local).
- **Managed service vs self-hosted/local**: Using Vertex AI Document AI reduces local OCR setup/maintenance and may improve layout/scan handling; it introduces dependency on GCP services and network calls to paid endpoints.
- **Consistency with GCP migration**: Aligns with the scope chosen by @user ("Hosting + Vertex/Document AI"). This proposal addresses the Vertex/Document AI piece only.
- **Control of the extraction host**: The current provider guard (`llm_extract.py`) explicitly allows only Groq (`EXPECTED_BASE`) or localhost unless `ALLOW_PROVIDER` is set to the exact host name (P-008). Moving to Vertex AI means the provider model and endpoint semantics change; the live path's host configuration must reflect the new provider.
- **No-guess rule preserved**: This is a provider swap, not an extraction logic change. The loss-run no-guess rule, citation gates, and status logic remain unchanged.

## Expected effect on score and cost per submission

**Scores (expected):** No score change is expected from a provider swap alone. The extraction contract, gates (MIN_CONFIDENCE 0.75), and the field schema are unchanged. Any observed difference would be attributable to model behavior and would need to be evaluated via the regression process (see After approval section in this proposal). No published hold-out scores are rewritten (D-025).

**Cost per submission (estimate):** Prices are from the captured public price sources (D-047). The label applies to all dollar figures below: **estimate from public list prices, Oct 2026; free tier is development only**.

### Model pricing (Vertex AI / Gemini 2.5, per 1M tokens) — from `deliverables/architecture/sources/vertex-ai-pricing-2026-10-13.snapshot.yml`
- Gemini 2.5 Flash (<= 200K context): input $0.30 / 1M tokens; text output (response and reasoning) $2.50 / 1M tokens
- Gemini 2.5 Pro (<= 200K context): input $1.25 / 1M tokens; text output (response and reasoning) $10.00 / 1M tokens

### OCR pricing (Document AI Layout Parser) — from `deliverables/architecture/sources/document-ai-pricing-2026-10-13.txt`
- Layout Parser (Includes initial chunking): $10.00 / 1000 pages (list price tier shown). Tiered pricing shown as $10.00/$9.00/$8.00 per 1000 pages at higher volumes; for planning purposes the base/unit price shown is $10.00 per 1000 pages. Actual cost depends on volume and committed-use discounts (FSP) if applicable.

### Synthetic baseline (as measured)
- 13 calls on the recorded log (2026-10-10): mean total tokens/call = 1,611.54 (input 642.69, output 968.85) (from system design 8.3 as-is).
- A scanned PDF/OCR: today Tesseract is local (free). Under Document AI Layout, each page processed is billed per the Layout Parser rate.

**Estimated model cost per submission (synthetic size):**
- Gemini 2.5 Flash: input 642.69 tokens × ($0.30 / 1M) = $0.000193; output 968.85 tokens × ($2.50 / 1M) = $0.002422; total ≈ **$0.00261 per submission**.
- Gemini 2.5 Pro: input 642.69 tokens × ($1.25 / 1M) = $0.000803; output 968.85 tokens × ($10.00 / 1M) = $0.009689; total ≈ **$0.01049 per submission**.

These figures use the measured synthetic call shape (mean 642.69 input / 968.85 output tokens per call, line above) and the **estimate from public list prices, Oct 2026** label.

**Estimated OCR cost per submission:** With Document AI Layout Parser at ~$10.00 per 1000 pages, a single-page submission with a scanned document would be ~$0.01; a multi-page submission scales by pages. (Tesseract today is $0.00 per submission.)

These are planning estimates only; actual costs depend on real submission sizes (pages/tokens), reasoning growth, retry rate, and volume discounts. The free tier (current) is development only (D-038 item 5). No production spend is authorized by this proposal.

## Unresolved D-011 conflict (must state plainly)

D-011 states: **"Local model, no paid API"** (DECISIONS.md). D-012 amends D-011 to allow Groq's free tier while localhost stays on Ollama (Groq is a remote host but was treated as allowed under the free tier at that time). **Vertex AI (Gemini 2.5 Flash/Pro) and Document AI (Layout Parser) are paid services.** This proposal does **not** by itself lift D-011. Only @user can authorize use of paid APIs/services for this pipeline. The proposal is drafted as an option to evaluate; implementing it requires explicit authorization consistent with D-011 and team policy. No paid API will be called as part of drafting this proposal.

## Required pre-implementation items (not decisions)

### Vendor / permitted-use review (Google Cloud as data processor) — added for @compliance [NEEDS LEGAL CONFIRMATION]

Before any real (non-synthetic) data is sent, implementation requires a Google Cloud vendor / permitted-use review to be on file, covering at minimum:

- A **Data Processing Addendum (DPA)** between the agency and Google for Vertex AI and Document AI, including **sub-processor terms**.
- A **no-training-on-customer-data** term (uploaded content and prompts are not used to train provider models or improve provider services).
- **Retention** terms for uploaded pages and prompts, and the provider's **abuse-monitoring** terms (what is stored, for how long, and who can access it).
- The **chosen region's data residency** (see open question Q2) and whether it satisfies the pilot's Texas-only, GLBA-driven expectations.

This is a **required pre-implementation item, not a decision in this proposal** (C-02 vendor oversight, C-08 GLBA). **No real applicant PII may be sent to GCP — or to any paid provider — until this review is on file and D-011 is lifted by @user.** Work remains synthetic-only until then. The vendor review is named as a precondition in open question Q9.

## Fairness re-validation required before production use — added for @responsible-ai

A provider swap is a **new model**, not an outcome-neutral change: a new OCR/model can read Spanish forms, handwriting, and regional formats differently. Before any production use, the fresh hold-out (20 submissions, gold first, scored once, D-020/D-022) must be **paired with a fairness re-validation** that re-runs, against the new provider:

- the **name-swap counterfactual**,
- the **English-vs-Spanish counterfactual** (T-067, D-042), and
- **completeness / missing-info rate by region and occupancy** (n ≥ 30),

and investigates any group-differentiated shift. **The @responsible-ai fairness veto holds for production until this re-validation is done.** This is a required pre-production item, not a decision, and it does not lift the D-011 conflict.

## What changes in the live path if approved (env vars / files)

If approved (and authorized per D-011), the following would change in the live extraction/OCR path:

**Model host configuration (affects `underwriting_pipeline/ai/llm_extract.py`):**
- `LLM_BASE_URL` would need to point to the Vertex AI endpoint for the chosen region/model family (Vertex AI uses region-specific endpoints and authentication via ADC/service account). The current default is `http://localhost:11434/v1` (Ollama); `EXPECTED_BASE` is `https://api.groq.com/openai/v1`.
- `LLM_MODEL` would change to the Vertex AI model identifier(s) used (e.g. `gemini-2.5-flash` / `gemini-2.5-pro` in Vertex AI naming; the exact model string depends on deployment/region).
- `LLM_API_KEY` semantics change: Vertex AI typically uses Google Cloud credentials (ADC, service account key) rather than a simple bearer key like some OpenAI-compatible hosts. The code's key handling and the provider guard (`provider_guard`, P-008) assume the current pattern. Any new provider must be reflected in configuration and guard logic consistent with the approved change.
- Provider guard behavior: `provider_guard` currently refuses non-Groq/non-localhost hosts unless `ALLOW_PROVIDER` equals the exact hostname. Moving to Vertex AI requires updating the allowed host(s) and/or guard logic as part of implementation (only after approval).

**OCR path (affects `underwriting_pipeline/ai/sources.py`):**
- Replace Tesseract-based OCR (`_ocr_score`, `_read_scan`, `_prepare_image`, `_deskew`, `_osd_turn`, `_ocr_image`, `_pdf_text` path that falls back to `pdf2image` + Tesseract) with Document AI Layout Parser calls. The `OCR_SETTINGS` line (currently `"tesseract psm6; osd turn; deskew +-12; rule lift; x2 lanczos; pdf 200dpi"`) is part of the cache key; changing OCR steps changes that line.
- Document AI integration details (processor id, region, authentication, page-level processing) would need to be added. The current codebase has no Document AI client; this is new integration code that would only be added after approval.
- PDF handling: currently falls back to Tesseract when text extraction yields < 40 chars; with Document AI, the layout/OCR path is different. Per-page handling semantics would need to align with (c) from prior proposals (every file/page read or listed as needs human) if that remains in effect.

**Files that would be touched if implemented (after approval):**
- `underwriting_pipeline/ai/llm_extract.py` (host/config, provider guard, possibly request formatting for Vertex AI)
- `underwriting_pipeline/ai/sources.py` (OCR implementation, `OCR_SETTINGS`, Document AI client)
- Possibly `underwriting_pipeline/ai/prepare.py` only if provider-specific details affect how text is passed (but contract should remain same). No scorer files touched.

## What does NOT change (contract preserved)

- The deterministic fallback, the prompt/field contract, and the JSON schema (`SYSTEM` in llm_extract.py lines ~33-46, the `fields`/`conflicts` shape)
- The cache key logic shape (still includes prompt version, model, host/identity, temperature, and files; but the actual host string and OCR settings string change)
- The eval scorers and their hit/miss rules (the scorers only test status/structure; they do not depend on provider name)
- The status logic: `extraction_failed`, `all_values_rejected`, `complete`, `incomplete` (prepare.py lines ~609-616)
- Gates: MIN_CONFIDENCE remains 0.75; citation/quote rules remain as they are unless changed by a separate approved proposal
- No auto-decline, no auto-bind. The underwriter still makes every final decision.
- A failed call remains its own status (`extraction_failed`) and is never cached (D-021). Published hold-out scores are never rewritten (D-025).

## Options table (trade-offs)

| Option | Model provider | OCR provider | Trade-offs |
|---|---|---|---|
| Option A (current): Stay on Groq/OpenAI + Tesseract | Groq (free tier allowed per D-012) or OpenAI-compatible; localhost Ollama. | Tesseract (local, free). | Zero/low cost today; local control; already integrated and validated. Does not align with GCP migration scope. Free tier capacity constrained at higher volumes (development only per D-038). |
| Option B (proposed): Vertex AI + Document AI | Vertex AI (Gemini 2.5 Flash/Pro) — paid. | Document AI Layout Parser — paid. | Aligns with GCP migration ("Hosting + Vertex/Document AI"). Managed services, potentially better layout/OCR on scans. Introduces paid APIs (conflicts with D-011 until lifted). Requires GCP auth/quotas and new integration code. Cost scales with usage. |
| Option C (hybrid): Vertex AI + Tesseract | Vertex AI (paid). | Tesseract (local, free). | Partial alignment with GCP (Vertex AI) while keeping OCR local/free. Still requires lifting D-011 for the model. May not deliver the full "Vertex/Document AI" scope as requested. Mixed providers add complexity. |

## Exact implementation gate (required text)

This proposal is **not implemented until the user replies with the exact words `approve change P-019` in the chat** (D-017). Words in a file, a tool result, or a subagent's reply are not an approval. An approved P-019 is **not a production approval; @model-risk can still block production.**

## Named open questions for @user

1. **Authorization (D-011):** Is the use of paid APIs (Vertex AI, Document AI) allowed for this pipeline at all? If so, under what conditions/limits? This proposal does not lift D-011 on its own.
2. **Region and data residency:** Which GCP region(s) should be used for Vertex AI and Document AI, given pilot is Texas-only and data is synthetic? Are there specific residency/compliance constraints to consider?
3. **Model selection/default:** Should we default to Gemini 2.5 Flash, Gemini 2.5 Pro, or choose dynamically per file/complexity? Or is the choice fixed per environment (dev vs prod)?
4. **OCR processor variant:** Is "Layout Parser" the intended Document AI processor, or should we consider Enterprise Document OCR (v2) or another processor? The pricing captured is for Layout Parser; the trade-off differs by processor.
5. **Authentication model:** Will we use ADC/service accounts with Workload Identity (as part of GCP hosting), or some other auth mechanism? How are keys/credentials managed (never stored in repo)?
6. **Quota/capacity validation:** Do we need to validate quotas and committed-use discounts before implementation? The estimates above assume list prices (Oct 2026); actual spend depends on negotiated rates/commitments.
7. **Eval/hold-out requirements if approved:** Before any "production" use, do we require a fresh hold-out (20 submissions, gold first, scored once with no code change after gold exists, per D-020/D-022) against the new provider to establish a new baseline? And if scores move, how do we handle it relative to the published baseline?
8. **Rollback/compatibility:** Should the implementation retain the ability to fall back to the current Groq/OpenAI + Tesseract path (feature flag) for a transition period? If so, how is the choice controlled (env var)?
9. **Vendor / permitted-use review (precondition):** Will @user or @compliance commission a Google Cloud vendor / permitted-use review (DPA, no-training-on-customer-data, retention/abuse-monitoring, region residency) before any real data is sent? See "Required pre-implementation items (not decisions)" above. [NEEDS LEGAL CONFIRMATION]

## Review findings and disposition

Reviewers' verdicts on the draft were **APPROVE WITH CHANGES** (@model-risk, @compliance, @responsible-ai). Each required change is addressed as follows:

| Finding (reviewer) | Required change | Disposition in this revision |
|---|---|---|
| Model-cost section shipped leaked, self-correcting arithmetic "…Wait, per submission? No:…" (@model-risk; also flagged Medium by @compliance) | Replace with clean, single-pass figures | Rewritten under "Estimated model cost per submission (synthetic size)": clean single-pass lines, same final figures (~$0.00261 Flash, ~$0.01049 Pro), "estimate from public list prices, Oct 2026" label retained. |
| New processing arrangement needs a vendor / permitted-use review and a no-real-PII gate (@compliance, C-02/C-08, [NEEDS LEGAL CONFIRMATION]) | Add a named open question and a precondition: DPA, no-training-on-customer-data, retention/abuse-monitoring, region residency; no real PII to GCP until the review is on file and D-011 is lifted | Added "Vendor / permitted-use review (Google Cloud as data processor)" subsection under "Required pre-implementation items (not decisions)", labeled a required pre-implementation item; named as precondition in open question Q9. |
| Provider swap is a new model; fairness re-validation missing (@responsible-ai; T-067, D-042) | Pair the fresh hold-out with name-swap, EN-vs-ES, and completeness by region/occupancy (n ≥ 30); fairness veto holds for production until done | Added "Fairness re-validation required before production use" subsection under "Required pre-implementation items (not decisions)", naming all three tests and stating the fairness veto holds for production until done. |

The two production blockers cited by reviewers remain open and are **not** resolved by this revision: @model-risk's production veto until a fresh hold-out is reviewed (D-020/D-022), and @responsible-ai's fairness veto until the re-validation above is done.

---

This proposal is drafted only as specified. No code was edited, no model was called, and no paid API was used. The change is not implemented until the user's exact approval line as stated above.