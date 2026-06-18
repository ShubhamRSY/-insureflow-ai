from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from insureflow.models.mortgage import ProductLine

# Category folders shared at package root (not borrower-specific)
SHARED_CATEGORY_DIRS = frozenset({
    "assets", "credit_debt", "credit_dept", "income", "legal", "property",
    "debt_legal", "due_diligence", "entity_financials", "property_performance",
})

# Map shared-doc filename tokens → borrower package id
FILENAME_BORROWER_HINTS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"john.?thompson|thompson.*john", re.I), "thompson_john_sarah"),
    (re.compile(r"sarah.?thompson", re.I), "thompson_john_sarah"),
    (re.compile(r"david.?chen|karen.?chen|chen_david|chen_joint", re.I), "chen_david_karen"),
    (re.compile(r"marcus.?johnson|imani.?johnson|johnson_marcus", re.I), "johnson_marcus_imani"),
    (re.compile(r"maria.?rodriguez|rodriguez_maria", re.I), "rodriguez_maria"),
    (re.compile(r"lisa.?patel|patel_lisa", re.I), "patel_lisa"),
    (re.compile(r"james.?wilson|wilson_james", re.I), "wilson_james"),
    (re.compile(r"thompson_commercial|tcp_llc", re.I), "thompson_commercial_properties"),
    (re.compile(r"midwest.?medical|medical_plaza", re.I), "midwest_medical_plaza"),
    (re.compile(r"oak.?street|sullivan", re.I), "oak_street_retail"),
    (re.compile(r"riverbend|self_storage|tom_thomas", re.I), "riverbend_self_storage"),
]


@dataclass
class BorrowerPackage:
    borrower_id: str
    display_name: str
    product_line: ProductLine
    paths: list[str] = field(default_factory=list)

    @property
    def document_count(self) -> int:
        return len(self.paths)


def _slug_to_display(slug: str) -> str:
    return slug.replace("_", " ").title()


def _infer_borrower_from_path(path: str) -> str | None:
    parts = Path(path).parts
    for part in reversed(parts):
        lower = part.lower()
        if lower in SHARED_CATEGORY_DIRS:
            continue
        if lower.endswith(".txt"):
            continue
        # borrower folder e.g. chen_david_karen
        if "_" in lower and lower not in ("home_mortgage", "commercial_mortgage", "simulated_documents"):
            if lower not in SHARED_CATEGORY_DIRS:
                return lower
    return None


def _infer_borrower_from_filename(path: str) -> str | None:
    name = Path(path).name
    for pattern, borrower_id in FILENAME_BORROWER_HINTS:
        if pattern.search(name):
            return borrower_id
    return None


def discover_borrower_packages(
    directory: str,
    product_line: ProductLine | None = None,
) -> list[BorrowerPackage]:
    """Split a mortgage document directory into per-borrower loan packages."""
    root = Path(directory)
    if not root.is_dir():
        raise FileNotFoundError(f"Directory not found: {directory}")

    inferred_product = product_line or (
        ProductLine.COMMERCIAL_MORTGAGE if "commercial_mortgage" in str(root).lower()
        else ProductLine.RESIDENTIAL_MORTGAGE
    )

    packages: dict[str, BorrowerPackage] = {}

    for txt_path in sorted(root.rglob("*.txt")):
        path_str = str(txt_path)
        borrower_id = _infer_borrower_from_path(path_str) or _infer_borrower_from_filename(path_str)

        if not borrower_id:
            # Generic shared doc — assign via filename hints or default bucket
            borrower_id = _infer_borrower_from_filename(path_str) or "unassigned"

        if borrower_id not in packages:
            packages[borrower_id] = BorrowerPackage(
                borrower_id=borrower_id,
                display_name=_slug_to_display(borrower_id),
                product_line=inferred_product,
            )
        packages[borrower_id].paths.append(path_str)

    # Drop empty unassigned if other packages exist
    if "unassigned" in packages and len(packages) > 1:
        unassigned = packages.pop("unassigned")
        # Try to attach unassigned docs to best filename match only packages
        for path in unassigned.paths:
            bid = _infer_borrower_from_filename(path)
            if bid and bid in packages:
                packages[bid].paths.append(path)
            elif "thompson_john_sarah" in packages:
                packages["thompson_john_sarah"].paths.append(path)

    return sorted(packages.values(), key=lambda p: p.borrower_id)
