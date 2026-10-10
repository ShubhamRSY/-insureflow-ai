# AI architecture proposal — intake, extraction, triage, copilot

- Author: @ai-engineer
- Date: 2026-10-09
- Status: Proposal (T-006)
- Reviewers: @ml-engineer, @software-engineer, @model-risk, @compliance
- Depends on the field list in `deliverables/senior-underwriter/required-fields.md`

The LLM recommends. Deterministic rules and humans decide. No LLM output by itself issues a quote or a decline.

## Components

```
Submission pack (PDF, spreadsheet, email)
        │
        ▼
┌─────────────┐
│ 1. Intake   │  store object, hash, page count, doc type
└──────┬──────┘
       ▼
┌─────────────┐
│ 2. Extract  │  LLM → field, value, source span, confidence
└──────┬──────┘  one candidate per field per document
       ▼
┌─────────────┐
│ 3. Reconcile│  deterministic: null vs value, cross-doc conflict
└──────┬──────┘
       ▼
┌─────────────┐
│ 4. Triage   │  deterministic rules = appetite + authority matrix
└──────┬──────┘  output is a band, not a price
       ▼
   ┌───┴────┬─────────────┬──────────────┐
   ▼        ▼             ▼              ▼
Incomplete  Auto-quote    Refer          Decline draft
(no quote)  filed rate    human queue    human sends
            only if every
            required field
            is confirmed
┌─────────────┐
│ 5. Copilot  │  summary + draft broker note, human sends
└─────────────┘
```

| Component | Tier (per T-008) | Why |
|---|---|---|
| Intake | 3 | Storage. No decision. |
| Extraction | **2** | Only if every required field is confirmed by a human or by an exact rule before the rater sees it. If any required field can pass through unconfirmed, this is Tier 1 and I will not ship it that way. |
| Reconcile | 2 | It can block a quote. It must not invent a value. |
| Triage / auto-quote gates | **1** | Can issue a quote. Deterministic does not make it "not a model." @model-risk is right. |
| Copilot summary and draft email | 3 | Not the system of record. Not sent without a human. |
| Decline draft | 2 | Human sends, on-list reason only. |

## Human-in-the-loop

| Point | Rule |
|---|---|
| Required field | Blank stays blank. A missing loss run is not zero claims. A "no known loss" letter is a document of type `nkl_letter`, not a loss run. |
| Conflict | If ACORD, SOV, and loss runs disagree, band = Refer. The copilot shows both values and the spans. |
| Low confidence | Below the eval threshold, the field is unconfirmed. Unconfirmed required field → Incomplete, not a guess. |
| Class code | Model may suggest. It does not write the class that gets rated. |
| Auto-quote | Only when triage says the band is auto-quote **and** every gate field is confirmed. Quote at the filed rate. System does not bind. |
| Decline | Model may attach a rule id from the prohibited or knock-out list. A human sends the notice. No free-text reason. |
| Broker email | Draft only. |

## Data sent to the LLM

Page images or text of the submission documents, plus the field schema. Not: credit, criminal history, web pages, or a vendor score. Person names are on the forms; they are not features. The prompt says to ignore names for classification. @compliance and @responsible-ai still have to accept that the raw document contains them.

## Evaluation (before any shadow use)

With @senior-underwriter's gold set, once the field list is accepted:

| Metric | Fail the change if |
|---|---|
| Field accuracy on required fields | Below the bar we set with @senior-underwriter on the gold set |
| Citation | Value whose span does not contain the value |
| Hallucination | Required field filled when the document has no value |
| Null discipline | Missing loss run stored as zero losses — any one case is a stop |
| Conflict recall | Known ACORD/SOV mismatches the gold set marks, missed |
| Routing | Band disagrees with the gold label |

Tier 1 auto-quote does not go to shadow on synthetic files alone (T-008). Extraction (Tier 2) can be measured on the gold set first.

Prompt version, model version, input hash, and output are logged on the submission.

## Failure

Timeout, schema failure, or no span → that field is null and the band cannot be auto-quote. The system does not retry into a guessed value.

## Not in this proposal

A loss model, a price, an agent that walks the file without the reconcile step, and training on customer submissions.
