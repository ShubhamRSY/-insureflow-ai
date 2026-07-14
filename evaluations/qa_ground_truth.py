"""Ground-truth Q&A pairs for eval (field checks + UW guideline RAG).

Complements `golden_dataset.py` (submission cases) with explicit question/answer
items so we can report: "N cases, M ground-truth questions."
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from evaluations.golden_dataset import GoldenCase, golden_dataset


@dataclass
class GroundTruthQuestion:
    question_id: str
    case_id: str
    question: str
    expected_answer: str
    category: str  # field_extraction | decision | guideline_rag | mortgage
    field_key: str = ""
    source: str = "golden_dataset"


FIELD_QUESTION_TEMPLATES: list[tuple[str, str, str]] = [
    # (field_attr, question template with {name}, category)
    ("expected_insured_name", "What is the named insured for case '{name}'?", "field_extraction"),
    ("expected_construction", "What construction type is stated for '{name}'?", "field_extraction"),
    ("expected_occupancy", "What occupancy class applies to '{name}'?", "field_extraction"),
    ("expected_protection_class", "What ISO protection class is recorded for '{name}'?", "field_extraction"),
    ("expected_square_footage", "What is the total square footage for '{name}'?", "field_extraction"),
    ("expected_stories", "How many stories does the primary building have for '{name}'?", "field_extraction"),
    ("expected_naics", "What NAICS code is on the submission for '{name}'?", "field_extraction"),
    ("expected_revenue", "What annual revenue is declared for '{name}'?", "field_extraction"),
    ("expected_payroll", "What payroll amount is declared for '{name}'?", "field_extraction"),
    ("expected_coverage_count", "How many coverages are present on the ACORD for '{name}'?", "field_extraction"),
    ("expected_location_count", "How many locations are on the submission for '{name}'?", "field_extraction"),
]


GUIDELINE_QA: list[dict[str, str]] = [
    {
        "question_id": "gl-naics-001",
        "question": "Which NAICS industries are excluded from standard carrier appetite?",
        "expected_answer": "Casinos (7211), logging (1133), mining support (2131), rail (4821), postal (4911), military (9211)",
        "category": "guideline_rag",
    },
    {
        "question_id": "gl-pc-001",
        "question": "What protection class threshold typically requires sprinkler or monitoring upgrades?",
        "expected_answer": "Protection class 5–6 and worse; PC 7–10 have stricter TIV limits",
        "category": "guideline_rag",
    },
    {
        "question_id": "gl-mfg-001",
        "question": "When are automatic sprinklers required for manufacturing occupancy?",
        "expected_answer": "Buildings over 10,000 sq ft require automatic sprinklers",
        "category": "guideline_rag",
    },
    {
        "question_id": "gl-masonry-001",
        "question": "What is the maximum per-building TIV for masonry construction under guidelines?",
        "expected_answer": "$10,000,000 per building; no more than 6 stories without engineered fire suppression review",
        "category": "guideline_rag",
    },
    {
        "question_id": "gl-docs-001",
        "question": "What documents are required for new business when TIV exceeds $2,000,000?",
        "expected_answer": "ACORD, 5-year loss runs, 3-year financials, SOV, and inspection report",
        "category": "guideline_rag",
    },
    {
        "question_id": "gl-cancel-001",
        "question": "How does prior carrier cancellation within 3 years affect appetite?",
        "expected_answer": "Cancelled or non-renewed within 3 years is ineligible for standard appetite",
        "category": "guideline_rag",
    },
    {
        "question_id": "gl-hotwork-001",
        "question": "What additional controls apply to welding or combustible dust manufacturing?",
        "expected_answer": "Hot-work limits, dust collection safeguards, increased protection standards",
        "category": "guideline_rag",
    },
    {
        "question_id": "gl-nonprofit-001",
        "question": "Are large non-profits eligible for standard appetite?",
        "expected_answer": "Non-profits with revenue exceeding $10M require specialized underwriting; not standard appetite",
        "category": "guideline_rag",
    },
]


def field_questions_from_case(case: GoldenCase) -> list[GroundTruthQuestion]:
    out: list[GroundTruthQuestion] = []
    for attr, template, category in FIELD_QUESTION_TEMPLATES:
        value = getattr(case, attr, None)
        if value is None or value == "":
            continue
        qid = f"{case.name}:{attr}"
        out.append(
            GroundTruthQuestion(
                question_id=qid,
                case_id=case.name,
                question=template.format(name=case.name),
                expected_answer=str(value),
                category=category,
                field_key=attr.replace("expected_", ""),
                source="golden_dataset",
            )
        )
    return out


def mortgage_ground_truth_questions() -> list[GroundTruthQuestion]:
    import json
    from pathlib import Path

    path = Path(__file__).resolve().parent.parent / "tests" / "golden_mortgage_outcomes.json"
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    out: list[GroundTruthQuestion] = []
    for b in data.get("borrowers", []):
        bid = b["id"]
        out.append(
            GroundTruthQuestion(
                question_id=f"mtg:{bid}:decision",
                case_id=bid,
                question=f"What is the expected underwriting decision for mortgage package '{bid}'?",
                expected_answer=str(b.get("expected_decision", "")),
                category="mortgage",
                field_key="decision",
                source="golden_mortgage_outcomes.json",
            )
        )
        if "expected_dti_range" in b:
            lo, hi = b["expected_dti_range"]
            out.append(
                GroundTruthQuestion(
                    question_id=f"mtg:{bid}:dti",
                    case_id=bid,
                    question=f"What DTI range is expected for '{bid}'?",
                    expected_answer=f"{lo}-{hi}",
                    category="mortgage",
                    field_key="dti",
                    source="golden_mortgage_outcomes.json",
                )
            )
        if "expected_ltv_range" in b:
            lo, hi = b["expected_ltv_range"]
            out.append(
                GroundTruthQuestion(
                    question_id=f"mtg:{bid}:ltv",
                    case_id=bid,
                    question=f"What LTV range is expected for '{bid}'?",
                    expected_answer=f"{lo}-{hi}",
                    category="mortgage",
                    field_key="ltv",
                    source="golden_mortgage_outcomes.json",
                )
            )
    return out


def guideline_ground_truth_questions() -> list[GroundTruthQuestion]:
    return [
        GroundTruthQuestion(
            question_id=q["question_id"],
            case_id="guidelines",
            question=q["question"],
            expected_answer=q["expected_answer"],
            category=q["category"],
            source="guideline_qa",
        )
        for q in GUIDELINE_QA
    ]


def all_ground_truth_questions() -> list[GroundTruthQuestion]:
    qs: list[GroundTruthQuestion] = []
    for case in golden_dataset():
        qs.extend(field_questions_from_case(case))
    qs.extend(mortgage_ground_truth_questions())
    qs.extend(guideline_ground_truth_questions())
    return qs


def ground_truth_inventory() -> dict[str, Any]:
    """Machine-readable inventory for interviews / dashboards / reports."""
    cases = golden_dataset()
    field_qs = [q for c in cases for q in field_questions_from_case(c)]
    mtg_qs = mortgage_ground_truth_questions()
    gl_qs = guideline_ground_truth_questions()
    all_qs = field_qs + mtg_qs + gl_qs

    mtg_borrowers = len({q.case_id for q in mtg_qs})

    return {
        "maintained": True,
        "locations": {
            "insurance_golden_cases": "evaluations/golden_dataset.py",
            "mortgage_golden_outcomes": "tests/golden_mortgage_outcomes.json",
            "guideline_qa": "evaluations/qa_ground_truth.py",
            "hitl_reviews": "evaluations/hitl_rubrics.py",
        },
        "insurance": {
            "golden_cases": len(cases),
            "case_names": [c.name for c in cases],
            "ground_truth_fields_per_case": [
                "insured_name",
                "construction",
                "occupancy",
                "protection_class",
                "square_footage",
                "stories",
                "naics",
                "revenue",
                "payroll",
                "coverage_count",
                "location_count",
            ],
            "field_level_questions": len(field_qs),
        },
        "mortgage": {
            "golden_borrower_packages": mtg_borrowers,
            "ground_truth_questions": len(mtg_qs),
        },
        "guideline_rag": {
            "ground_truth_questions": len(gl_qs),
        },
        "totals": {
            "golden_cases_and_packages": len(cases) + mtg_borrowers,
            "ground_truth_questions": len(all_qs),
            "by_category": {
                "field_extraction": sum(1 for q in all_qs if q.category == "field_extraction"),
                "mortgage": sum(1 for q in all_qs if q.category == "mortgage"),
                "guideline_rag": sum(1 for q in all_qs if q.category == "guideline_rag"),
            },
        },
        "retrieved_context": {
            "mode": "hybrid_rag_plus_knowledge_graph",
            "vector_rag": {
                "corpus": "builtin underwriting guidelines (carrier appetite, construction, PC, occupancy)",
                "store": "InMemoryVectorStore (char-n-gram) or PgVectorStore when DATABASE_URL set",
                "used_in_eval": "Ragas retrieved_contexts = guideline chunks",
            },
            "knowledge_graph": {
                "module": "insureflow.rag.knowledge_graph",
                "node_types": ["construction", "occupancy", "naics", "protection", "hazard", "control", "guideline"],
                "used_in_eval": "Ragas retrieved_contexts also include KG neighborhood facts",
            },
        },
        "interview_summary": (
            f"Yes — maintained gold sets: {len(cases)} insurance ACORD cases "
            f"({len(field_qs)} field ground-truth questions), "
            f"{mtg_borrowers} mortgage borrower packages ({len(mtg_qs)} questions), "
            f"and {len(gl_qs)} underwriting-guideline RAG Q&As — "
            f"{len(all_qs)} ground-truth questions total. "
            "Retrieved context for eval is hybrid: vector guideline RAG + underwriting knowledge graph."
        ),
    }


if __name__ == "__main__":
    import json

    print(json.dumps(ground_truth_inventory(), indent=2))
