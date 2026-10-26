# RAG Corpus: Per-LOB Underwriting Knowledge Base

This folder holds the underwriting knowledge base embedded/indexed into a vector store (RAG) for underwriting assistance. Each product document is a full-depth underwriting guide entry — eligibility and appetite, decline criteria, submission requirements with document rationale, coverage schedule, exclusions, endorsements, limits, rating factors, underwriting focus, decline/refer authority, and regulatory notes.

Content is generated from the live catalogs in the codebase (`src/insureflow/insurance/*.py`, `package_checklist.py`) merged with category-level underwriting rules in [`scripts/rag_knowledge_base.py`](../../scripts/rag_knowledge_base.py), per-product field overrides in [`scripts/rag_product_overrides.py`](../../scripts/rag_product_overrides.py), and a per-product differentiation layer in [`scripts/rag_product_differentiation.py`](../../scripts/rag_product_differentiation.py).

Each product inherits its category's line rules, then the override layer replaces any field where the product diverges (cover, perils, exclusions, limits, rating, authority), and the differentiation layer supplies product-specific decline criteria, endorsements, and refer authority. This keeps line-wide rules consistent while ensuring no two products in a category carry identical full text, exclusions, decline criteria, endorsements, limits, rating, or refer rules.

## Structure

| LOB | Corpus | Documents dir | Entries |
|---|---|---|---|
| commercial | [commercial/RAG_CORPUS.md](commercial/RAG_CORPUS.md) | [commercial/documents/](commercial/documents/) | 59 products (property, liability, workforce, auto, financial, specialty, ART, package) |
| life | [life/RAG_CORPUS.md](life/RAG_CORPUS.md) | [life/documents/](life/documents/) | 41 products (term, whole, universal, endowment, ULIP, money-back, annuity) |
| health | [health/RAG_CORPUS.md](health/RAG_CORPUS.md) | [health/documents/](health/documents/) | 30 products (individual/family, critical illness, senior/Medicare, group, supplemental, accident, disability) |
| general | [general/RAG_CORPUS.md](general/RAG_CORPUS.md) | [general/documents/](general/documents/) | 31 products (motor, home, travel, marine, fire, liability, cyber, crop, animal, event, title, mortgage, provider) |
| personal_auto | [personal_auto/RAG_CORPUS.md](personal_auto/RAG_CORPUS.md) | [personal_auto/documents/](personal_auto/documents/) | 1 program guide + document-type checklist |
| personal_homeowners | [personal_homeowners/RAG_CORPUS.md](personal_homeowners/RAG_CORPUS.md) | [personal_homeowners/documents/](personal_homeowners/documents/) | 1 program guide + document-type checklist |

## What to use this RAG for

| Use case | RAG retrieval | Example queries |
|---|---|---|
| Submission completeness | Submission requirements + document rationale + core packet | "What documents do I need for property_bi?" / "Is ACORD 140 required for commercial property?" |
| Eligibility / appetite | Target market, eligibility, decline criteria | "Is an unprotected frame warehouse eligible for property?" / "Who is declined for workers comp?" |
| UW eligibility/requirements | Underwriting focus + eligibility + refer triggers | "What triggers inspection for car_comprehensive?" / "When does a loss ratio refer?" |
| Coverages & exclusions | Coverage schedule + exclusions + endorsements | "What is excluded on cyber liability?" / "What endorsements exist for D&O?" |
| Limits & pricing | Limits/retention + rating factors | "What is the mold sub-limit on commercial property?" / "How is personal auto rated?" |
| Authority / escalation | Decline & refer authority | "What refers to the Commercial Desk?" / "When must the Life Chief UW review?" |
| Regulatory/compliance hints | Standards + filing notes (ACORD, MIB, HIPAA, IRDAI) | "What authorizations are required for life?" / "What is state-filed for health?" |
| New underwriter onboarding | Full guide entry per product | "Teach me the submission pack and exclusions for builder's risk" |
| Agent/tool grounding | Per-product chunks for classifiers/checklists | Feed the relevant product chunk when classifying uploaded docs |

## Integration with existing RAG

- Runtime layer: `src/insureflow/rag/` (`vector_store`, `guidelines`, `rag_agent`, `embeddings`, `self_rag`). `RAGAgent` indexes `builtin_guidelines()` + `builtin_carrier_appetite_rules()` and falls back to keyword + knowledge graph.
- This corpus provides per-product underwriting guide chunks. Index each `documents/<product>.md` (split on `##` sections) into the same vector store under a collection (e.g. `lob_documentation`).
- Recommended: when the LOB/category is known (triage), bias retrieval to that folder; otherwise hybrid search across all LOBs.
- Embeddings: `src/insureflow/llm/embeddings.py` supports hashed (default, no egress) or OpenAI/sentence-transformers (optional).

## Regeneration

- Generator: [scripts/generate_rag_corpus.py](../../scripts/generate_rag_corpus.py)
- Underwriting knowledge base (category/line rules): [scripts/rag_knowledge_base.py](../../scripts/rag_knowledge_base.py)
- Per-product field overrides: [scripts/rag_product_overrides.py](../../scripts/rag_product_overrides.py)
- Per-product decline/endorsement/refer differentiation: [scripts/rag_product_differentiation.py](../../scripts/rag_product_differentiation.py)
- Regenerate from the current catalogs: `.venv/bin/python scripts/generate_rag_corpus.py`

## Notes

- Each entry reflects the real catalog fields (descriptions, required documents, coverages, ACORD forms) plus the category-level underwriting rules from the knowledge base.
- Personal lines use the `package_checklist` document-type enums; each personal LOB gets one program guide plus the document-type checklist.
- Edit `rag_knowledge_base.py` to tune market, eligibility, exclusions, limits, rating, and authority rules per LOB category, then re-run the generator.
