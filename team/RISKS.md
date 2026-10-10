# Risks & Issues

| ID | Risk / issue | Likelihood | Impact | Owner | Mitigation | Status |
|---|---|---|---|---|---|---|
| R-001 | LLM extraction errors lead to wrong underwriting decisions | Medium | High | @ai-engineer | Citations, confidence thresholds, human review, evals | Open |
| R-002 | Model uses proxies for protected classes | Medium | High | @responsible-ai | Proxy review, fairness testing before launch | Open |
| R-003 | Third-party data not permitted for underwriting use | Medium | High | @compliance | Data-use review (T-012) before any feature is built. v1 ban on credit and external consumer data recorded in the regulatory register. | Open |
| R-004 | A "no known loss" letter is stored as a valued loss run | Low | High | @ai-engineer | `prepare.extract` nulls that field. Still open until T-015 reviewers accept it. | Open |
| R-005 | Auto-quote rules ship as guidelines and skip validation | — | — | @model-risk | Moot. D-004 removed auto-quote. Score and match are Tier 2 only while a human decides. | Closed |
| R-006 | Writing entity, pilot states, and rate manual were unknown | — | — | @compliance | Closed for v1 by D-004: agency, Texas, placeholders A/B/C, no rate manual. Reopen when the real panel is named. | Closed |
| R-007 | Habitational labeled target while auto-quote was forbidden | — | — | @head-of-underwriting | Moot. Auto-quote cancelled. Habitational is a Carrier C recommendation only. | Closed |
| R-008 | Artisan contractors auto-quoted inside a band whose planning LR fails permissible | — | — | @head-of-underwriting | Moot. D-004 cancelled auto-quote. | Closed |
| R-010 | Missing-info request is sent with no person checking it | Low | Medium | @ai-engineer | D-007 and D-008: drafts sit in simulation/pending-approval/. approve() accepts only the user. SUB-002, SUB-005, and SUB-011 through SUB-015 were sent only after the user typed approve. | Mitigating |
| R-011 | Hazard score or carrier match is used to bind or to train on approvals | Medium | High | @actuary | T-023 and the framing forbid it. @model-risk tiers both as Tier 2 only while a human decides. | Open |
| R-012 | Completeness request misses class-specific facts (fryer, sprinklers) | Low | Medium | @ai-engineer | Restaurant drafts ask the five industry items, and a later file that already states them is not asked again. | Mitigating |
| R-013 | Address conflicts kept only in the producer email, then overwritten | Low | High | @data-engineer | Closed. Conflicts are JSON with both values, sources, and resolution. A resolved row is kept after the live files agree. SUB-003 keeps 55 vs 550 and 8,000 vs 14,000. | Closed |
| R-009 | Headline metrics ignore loss quality | Medium | Medium | @actuary | D-004 metrics stand. @actuary will block a score trained on approvals. Not a veto of the pipeline. | Open |
| R-014 | A high score on one run is treated as proof | Medium | High | @model-risk | D-020. The same files that scored clean can come back empty on a later run. SUB-051, SUB-053, SUB-055, SUB-059, SUB-061, SUB-073, and SUB-075 did that on 2026-10-10. Not a production approval. | Open |
