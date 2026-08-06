# Risk Selection Doctrine: Book Balance & Selection Standards

This document records how InsureFlow operationalizes the classical
underwriting principles of **risk selection**, **homogeneity vs. volume**, and
**selection expense**. The implementation lives in
`src/insureflow/underwriting/selection.py` and is applied per submission by
`src/insureflow/agents/selection_standards_agent.py`.

## The doctrine

1. **Selection is the heart of underwriting.** Every submission must be
   classified and accepted, referred, or declined against the carrier's
   current appetite *and* its current book posture.
2. **Balance volume against homogeneity.** An insurer prices against the law
   of large numbers: a loss ratio is only predictable once enough *similar*
   risks are pooled. A few risks — even good ones — cannot be priced to a
   predictable outcome. Conversely, volume bought by abandoning homogeneity
   destroys predictability just as surely as a thin book does.
3. **Classify every risk.** Standard, preferred, and substandard classes carry
   different rates (see the life manual's `underwriting_class_factors` for the
   pricing side). Substandard risks are admitted *only* when their higher
   premium loadings are expected to offset their higher loss ratio — and only
   when the book is large enough to absorb them.
4. **Selection expense is real.** Strict selection (APS, paramedical exams,
   deep loss-run review) costs money per risk. For a thin book or a small
   premium, evidence cost can exceed the margin it protects.

## How the model works

The engine derives three quantities from the written book:

- **Size score** `1 - exp(-N / reference_size)` — how many policies support the
  law of averages.
- **Homogeneity** `1 - avg(premium_CV, TIV_CV) / cv_cap` — how uniform the book
  is. High coefficient of variation means a mixed, unpredictable book.
- **Predictability** `size * (0.5 + 0.5 * homogeneity)` — predictability is
  *bounded by volume*: homogeneity can scale the size-driven ceiling but cannot
  create predictability from nothing.

The predictability score selects the **selection standards tier**:

| Tier | Predictability | Candidate gate |
|------|----------------|----------------|
| `strict` | < 0.30 | preferred/standard only; substandard → refer or decline |
| `balanced` | 0.30–0.60 | substandard admitted **conditionally** (loading + evidence) |
| `broad` | > 0.60 | substandard admitted on the filed rate |

Selection expense is priced as `cost_per_risk(tier) * policy_count` against
book premium, and per-candidate against candidate premium. When the ratio
exceeds the guideline (5% of book premium, or 30% of the candidate's premium),
the agent flags that evidence requirements are eroding margin.

## Substandard loading is wired into pricing

The doctrine's "a policy covering them would have a higher premium rate" is not
left as advice. When the selection gate admits a **substandard** candidate
(`ACCEPT` or `CONDITIONAL_ACCEPT`), it computes a rate loading
`clamp((risk_score - 0.5) * 100, min 15%, max 50%)` — e.g. a risk score of 0.70
gets a 20% loading. The agent surfaces it as `suggested_premium_modification`,
and the pipeline merges it into `memo.recommendation` before the rating stage,
so the commercial quote carries a `uw_schedule_modification` component and the
summary exposes `selection_loading_pct`. Referred/declined risks are never
loaded. "Too great or too unpredictable" (score ≥ 0.85, or substandard on a
strict book) is rejected rather than priced.

## Intra-class dispersion

The text notes that "in each class there are good risks and poor risks relative
to the rest of the class." Every written policy now records its `risk_score`,
and the book snapshot buckets policies by class (preferred < 0.40,
standard < 0.65, else substandard) and computes the coefficient of variation of
risk scores within each band (`intra_class_cv`, `class_dispersion`). When
dispersion exceeds the guideline (0.15) the agent flags **class purity eroded**
— weaker risks are riding on the class average rate and should be re-rated or
reclassified.

## Experience-rating feedback loop

The doctrine closes with the Underwriter's Goal: *the insurer must compare the
actual losses of each hypothetical pool with the expected losses it priced* and
let that experience steer selection. This is implemented as a per-class
feedback loop:

- Every `PortfolioPolicy` records its realized loss experience
  (`incurred_loss`, `experience_periods`) and is flagged
  `loss_data_available` once losses are reported (via
  `PortfolioStore.record_loss_development`). Policies with no reported
  experience do not enter the loop.
- `compute_book_experience` buckets the observed policies by class
  (preferred / standard / substandard), computes the realized loss ratio
  (incurred ÷ earned premium) against the class's **expected** loss ratio
  from `SelectionStandardsConfig.expected_loss_ratio_by_class`, and blends the
  deviation toward expectation by **limited-fluctuation credibility**
  `Z = sqrt(N / credibility_full_policies)` (default: full credibility at
  30 policies). Below `min_observed_policies_for_feedback` (5), a class is not
  trusted and cannot move the book.
- The credibility-scaled **penalty factor**
  `P = 1 + Z * (actual/expected − 1)` (clamped to 0.6–1.6) drives two levers:

  | Experience | Penalty | Effect |
  |-----------|---------|--------|
  | worse than expected | P > 1 | selection thresholds **raised** (`apply_experience_to_config` tightens `strict_threshold`/`balanced_threshold`, so a broad book can demote to balanced or strict) and the candidate's substandard loading is **scaled up** by the class penalty |
  | better than expected | P < 1 | thresholds **lowered** (a book can promote toward broad) and substandard loadings scale down toward the base |
  | no / too little data | P = 1 | loop inert — config unchanged |

- The penalty is premium-weighted across credible classes for the book posture,
  so one thin class's volatile loss ratio cannot swing the whole book.
- The agent surfaces the feedback as an `Experience feedback:` finding
  (worse = HIGH, better = LOW, too-little-data = LOW) and the pipeline summary
  exposes the full `BookExperience` under `selection_experience`.

Combined with the substandard loading section above, this is the full circle:
selection admits or rejects, pricing loads what is admitted, and realized
losses feed back to tighten or relax the gate for the next submission.

## Financial function: producer experience

The doctrine's financial function acknowledges the underwriter/agent tension: the
underwriter is judged on the **quality** of production, the agent on **quantity**,
and a producer whose submissions consistently produce above-average claims may
lose the relationship. `ProducerExperienceAgent` operationalizes this:

- Every `PortfolioPolicy` carries its `producer_name` (the producing
  broker/agent from `SubmissionBundle.structured.broker.broker_name`, recorded at
  bind).
- `compute_producer_experience` groups reported-loss policies by producer and
  compares each producer's realized loss ratio to the **premium-weighted
  expectation of the classes they submitted** (the same
  `expected_loss_ratio_by_class` used by the book loop), blended by the same
  limited-fluctuation credibility.
- A producer running worse than expected (`penalty > 1.05`, credible) triggers a
  **HIGH** finding: *"submissions running above-average claims — relationship at
  risk"* — with coaching to **pre-screen against carrier appetite** before
  submitting. Better-than-expected producers get a LOW acknowledgment; producers
  with too little reported experience get a LOW "cannot rate yet" note.
- An aggregate **"Producer book quality"** finding (MODERATE) lists every
  credible at-risk producer in the book, the portfolio-level termination-risk
  signal.
- The agent runs in the portfolio stage (stage 7) alongside concentration and
  selection standards, defers in funnel mode, re-runs via
  `deep_dive(include=["producer_experience", ...])`, and surfaces in the summary
  under `producer_experience`.

The pre-screening half of the doctrine ("the agent knows a company will not
accept a certain class and should not submit it") is enforced at the front door
by `AppetiteFilterAgent` and coached into producers flagged by this agent.

## Pipeline integration

- The `SelectionStandardsAgent` and `ProducerExperienceAgent` run in the
  portfolio stage (stage 7) of `InsurancePipeline.run()` for commercial lines,
  alongside concentration analysis, using `memo.overall_risk_score` as the
  candidate risk score.
- Findings are appended to the memo; critical/high findings trigger human
  review.
- In funnel mode the stage is deferred and re-runs on demand via
  `POST /pipeline/{bundle_id}/deep-dive` (`include=["selection_standards", ...]`),
  the same as oracles/portfolio/reinsurance.
- Results surface in the pipeline summary under `selection_standards`
  (book snapshot, tier, gate action, rationale, warnings).

## Tuning

All thresholds live in `SelectionStandardsConfig`:
`reference_size`, `cv_cap`, `strict_threshold`, `balanced_threshold`,
per-tier `*_expense_per_risk`, `max_selection_expense_ratio`,
`max_candidate_expense_ratio`, `min_volume_for_law_of_averages`, `target_size`,
`min_substandard_loading`, `max_substandard_loading`, `max_intra_class_cv`,
plus the experience-loop knobs `expected_loss_ratio_by_class`,
`credibility_full_policies`, `min_observed_policies_for_feedback`, and
`experience_threshold_sensitivity`.
Tests in `tests/test_selection_standards.py` document the expected behavior at
each tier, for the expense flags, for the substandard loading, for intra-class
dispersion, and for the experience-rating feedback loop (credibility scaling,
tier tightening/relaxation, and loading scaling by class penalty).
`tests/test_producer_experience.py` covers the financial function — producer
grouping, expectation blending across classes, and the at-risk findings.
