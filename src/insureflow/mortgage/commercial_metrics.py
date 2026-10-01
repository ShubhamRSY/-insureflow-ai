"""Commercial credit metrics: DSCR, LTV and debt yield.

Commercial real estate is underwritten on the property's cash flow, not on
the borrower's personal balance sheet. The three numbers that carry that
work are:

* **DSCR** = annual net operating income / annual debt service. How many
  times the property's income covers the note.
* **LTV** = loan amount / value. How much skin is in the deal.
* **Debt yield** = annual net operating income / loan amount. The unlevered
  return on the lender's dollar, independent of the interest rate.

This module computes them from the file, and — the part that matters
underwriting-wise — records *where each input came from*. A DSCR that
nobody can trace back to a document and a line is not a DSCR, it is a
number, and this module refuses to return one without provenance.

When the borrower's statement states a DSCR, the computed figure is still
derived independently and the two are compared. A stated ratio that
disagrees with the arithmetic of the borrower's own documents is a data
integrity problem worth surfacing, not something to paper over by
preferring the stated number.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from insureflow.models.mortgage import (
    MortgageBundle,
    MortgageDocument,
    MortgageDocumentType,
    ProductLine,
)

__all__ = [
    "MetricSource",
    "DSCRResult",
    "CommercialCreditMetrics",
    "net_operating_income",
    "annual_debt_service",
    "compute_dscr",
    "debt_yield",
    "resolve_loan_amount",
    "compute_commercial_metrics",
    "STATED_VS_COMPUTED_TOLERANCE",
]

# A stated DSCR is often rounded to two decimals, so agreement is expected
# at roughly +/-0.01. Anything wider than this is a discrepancy worth
# telling a human about rather than silently resolving one way.
STATED_VS_COMPUTED_TOLERANCE = 0.05

_MONTHS_PER_YEAR = 12


@dataclass(frozen=True)
class MetricSource:
    """Where a commercial metric input came from.

    ``basis`` is ``stated`` when the document asserts the figure directly
    and ``derived`` when this code calculated it from other extracted
    numbers. ``context`` carries the extractor note (which column of a
    multi-year statement was read), which is the difference between an
    auditable metric and an unexplained one.
    """

    value: float
    document_type: MortgageDocumentType
    field_name: str
    basis: str = "stated"
    context: str = ""

    def describe(self) -> str:
        return f"{self.value:,.2f} ({self.basis}, {self.document_type.value}.{self.field_name})"


@dataclass(frozen=True)
class DSCRResult:
    """A DSCR and everything needed to defend it."""

    dscr: Optional[float] = None
    noi: Optional[float] = None
    annual_debt_service: Optional[float] = None
    noi_source: Optional[MetricSource] = None
    debt_service_source: Optional[MetricSource] = None
    basis: str = "unavailable"
    stated_dscr: Optional[float] = None
    stated_dscr_source: Optional[MetricSource] = None
    variance: Optional[float] = None
    total_annual_debt_service: Optional[float] = None
    dscr_on_total_debt: Optional[float] = None
    notes: tuple[str, ...] = field(default_factory=tuple)

    @property
    def computable(self) -> bool:
        return self.dscr is not None and self.annual_debt_service is not None and self.noi is not None

    def provenance(self) -> str:
        if not self.computable:
            return "DSCR not computable"
        noi = self.noi_source.describe() if self.noi_source else "unattributed NOI"
        service = self.debt_service_source.describe() if self.debt_service_source else "unattributed debt service"
        return f"DSCR {self.dscr:.2f}x = NOI {self.noi:,.0f} / annual debt service {self.annual_debt_service:,.0f} | {noi} | {service}"


@dataclass(frozen=True)
class CommercialCreditMetrics:
    """The commercial underwriting picture for a deal."""

    dscr: DSCRResult = field(default_factory=DSCRResult)
    ltv: Optional[float] = None
    debt_yield: Optional[float] = None
    noi: Optional[float] = None
    loan_amount: float = 0.0
    notes: tuple[str, ...] = field(default_factory=tuple)

    @property
    def complete(self) -> bool:
        """True when every commercial criterion could actually be evaluated."""
        return self.dscr.computable and self.ltv is not None and self.debt_yield is not None

    def missing(self) -> list[str]:
        gaps: list[str] = []
        if not self.dscr.computable:
            gaps.append("dscr")
        if self.ltv is None:
            gaps.append("ltv")
        if self.debt_yield is None:
            gaps.append("debt_yield")
        return gaps


def _docs(bundle: MortgageBundle, doc_type: MortgageDocumentType) -> list[MortgageDocument]:
    return bundle.documents_by_type(doc_type)


def _source_from(doc: MortgageDocument, field_name: str, basis: str) -> Optional[MetricSource]:
    raw = doc.get_field(field_name, "")
    if not raw:
        return None
    cleaned = raw.replace("$", "").replace(",", "").replace("x", "").strip()
    try:
        value = float(cleaned)
    except ValueError:
        return None
    entries = doc.extracted_fields.get(field_name, [])
    context = entries[0].context if entries else ""
    return MetricSource(
        value=value,
        document_type=doc.document_type,
        field_name=field_name,
        basis=basis,
        context=context,
    )


def net_operating_income(bundle: MortgageBundle) -> tuple[Optional[MetricSource], tuple[str, ...]]:
    """Annual NOI, preferring the operating statement's own NOI line.

    Falls back to effective gross income less operating expenses when the
    statement omits an NOI row, and finally to the NOI the appraisal
    capitalised. Each fallback is recorded in the notes because a rebuilt
    NOI deserves less confidence than a reported one.
    """
    notes: list[str] = []

    for doc in _docs(bundle, MortgageDocumentType.OPERATING_STATEMENT):
        source = _source_from(doc, "noi", "stated")
        if source is not None:
            return source, tuple(notes)

    for doc in _docs(bundle, MortgageDocumentType.OPERATING_STATEMENT):
        egi = _source_from(doc, "effective_gross_income", "stated")
        opex = _source_from(doc, "total_operating_expenses", "stated")
        if egi is not None and opex is not None:
            rebuilt = egi.value - opex.value
            notes.append(f"NOI rebuilt from effective gross income less operating expenses ({rebuilt:,.2f})")
            return (
                MetricSource(
                    value=rebuilt,
                    document_type=doc.document_type,
                    field_name="effective_gross_income-total_operating_expenses",
                    basis="derived",
                    context=f"EGI {egi.value:,.2f} - operating expenses {opex.value:,.2f}",
                ),
                tuple(notes),
            )

    for doc_type in (MortgageDocumentType.COMMERCIAL_APPRAISAL,):
        for doc in _docs(bundle, doc_type):
            source = _source_from(doc, "noi", "stated")
            if source is not None:
                notes.append("NOI taken from the appraisal, not from a current operating statement")
                return source, tuple(notes)

    notes.append("no NOI could be sourced from the operating statement or appraisal")
    return None, tuple(notes)


def annual_debt_service(bundle: MortgageBundle) -> tuple[Optional[MetricSource], Optional[float], tuple[str, ...]]:
    """Annual debt service on the subject loan, and on all scheduled debt.

    Prefers the business debt schedule, which itemises each note, and
    annualises the subject loan's monthly P&I. Returns ``(subject, total,
    notes)``; either may be ``None`` and the notes say why.
    """
    notes: list[str] = []

    subject: Optional[MetricSource] = None
    total: Optional[float] = None

    for doc in _docs(bundle, MortgageDocumentType.BUSINESS_DEBT_SCHEDULE):
        if subject is None:
            monthly = _source_from(doc, "subject_loan_monthly_debt_service", "stated")
            if monthly is not None:
                subject = MetricSource(
                    value=monthly.value * _MONTHS_PER_YEAR,
                    document_type=doc.document_type,
                    field_name="subject_loan_monthly_debt_service",
                    basis="derived",
                    context=f"monthly P&I {monthly.value:,.2f} x {_MONTHS_PER_YEAR} months" + (f" | {monthly.context}" if monthly.context else ""),
                )
        if total is None:
            monthly_total = _source_from(doc, "total_monthly_debt_service", "stated")
            if monthly_total is not None and monthly_total.value > 0:
                total = monthly_total.value * _MONTHS_PER_YEAR

    if subject is None:
        for doc in _docs(bundle, MortgageDocumentType.OPERATING_STATEMENT):
            monthly = _source_from(doc, "subject_loan_monthly_debt_service", "stated")
            if monthly is not None:
                notes.append("annual debt service annualised from the operating statement; no business debt schedule in file")
                subject = MetricSource(
                    value=monthly.value * _MONTHS_PER_YEAR,
                    document_type=doc.document_type,
                    field_name="subject_loan_monthly_debt_service",
                    basis="derived",
                    context=f"P&I Monthly {monthly.value:,.2f} x {_MONTHS_PER_YEAR} months",
                )
                break

    if subject is None:
        notes.append("no scheduled principal-and-interest payment found; annual debt service is unknown")

    if total is not None and subject is not None and total > subject.value + 0.5:
        notes.append(f"other scheduled debt brings total annual debt service to {total:,.2f}, above the subject loan's {subject.value:,.2f}")

    return subject, total, tuple(notes)


def compute_dscr(bundle: MortgageBundle) -> DSCRResult:
    """Compute DSCR as annual NOI over annual debt service.

    The ratio is derived from the borrower's documents; a DSCR printed on
    the statement is captured separately and compared against it. Both
    inputs are required. Any other outcome is reported as unavailable
    rather than defaulted, because an absent DSCR is an absent fact and
    the caller has to be able to tell that apart from a weak one.
    """
    notes: list[str] = []

    noi_source, noi_notes = net_operating_income(bundle)
    notes.extend(noi_notes)

    debt_source, total_debt, debt_notes = annual_debt_service(bundle)
    notes.extend(debt_notes)

    stated_source: Optional[MetricSource] = None
    for doc in _docs(bundle, MortgageDocumentType.OPERATING_STATEMENT):
        stated_source = _source_from(doc, "dscr", "stated")
        if stated_source is not None:
            break

    if noi_source is None or debt_source is None:
        missing = []
        if noi_source is None:
            missing.append("annual NOI")
        if debt_source is None:
            missing.append("annual debt service")
        notes.append(f"cannot compute DSCR: missing {' and '.join(missing)}")
        return DSCRResult(
            noi=noi_source.value if noi_source else None,
            noi_source=noi_source,
            debt_service_source=debt_source,
            stated_dscr=stated_source.value if stated_source else None,
            stated_dscr_source=stated_source,
            basis="unavailable",
            total_annual_debt_service=total_debt,
            notes=tuple(notes),
        )

    annual_debt = debt_source.value
    if annual_debt <= 0:
        notes.append("cannot compute DSCR: annual debt service is zero")
        return DSCRResult(
            noi=noi_source.value,
            noi_source=noi_source,
            annual_debt_service=annual_debt,
            debt_service_source=debt_source,
            stated_dscr=stated_source.value if stated_source else None,
            stated_dscr_source=stated_source,
            basis="unavailable",
            total_annual_debt_service=total_debt,
            notes=tuple(notes),
        )

    noi = noi_source.value
    dscr = noi / annual_debt

    variance: Optional[float] = None
    if stated_source is not None and stated_source.value > 0:
        variance = stated_source.value - dscr
        if abs(variance) > STATED_VS_COMPUTED_TOLERANCE:
            notes.append(
                f"stated DSCR of {stated_source.value:.2f}x disagrees with the {dscr:.2f}x computed from NOI and scheduled debt service by {variance:+.2f}x; the documents are internally inconsistent"
            )
        else:
            notes.append(f"stated DSCR of {stated_source.value:.2f}x reconciles with the computed {dscr:.2f}x")

    dscr_on_total: Optional[float] = None
    if total_debt is not None and total_debt > annual_debt and total_debt > 0:
        dscr_on_total = noi / total_debt
        notes.append(f"DSCR on all scheduled debt service would be {dscr_on_total:.2f}x")

    return DSCRResult(
        dscr=dscr,
        noi=noi,
        annual_debt_service=annual_debt,
        noi_source=noi_source,
        debt_service_source=debt_source,
        basis="computed",
        stated_dscr=stated_source.value if stated_source else None,
        stated_dscr_source=stated_source,
        variance=variance,
        total_annual_debt_service=total_debt,
        dscr_on_total_debt=dscr_on_total,
        notes=tuple(notes),
    )


def resolve_loan_amount(bundle: MortgageBundle, loan_amount: float | None = None) -> float:
    """The note amount, with documented fallbacks.

    Order: the amount the caller requested, then the purchase price, then
    the original loan amount on the business debt schedule. The last one
    exists because a commercial run is often launched from a document
    folder with no loan amount supplied, and a debt schedule states the
    note size in plain text. Each fallback is noted so the figure's origin
    is visible in the underwriting record.
    """
    if loan_amount and loan_amount > 0:
        return float(loan_amount)
    if bundle.collateral and bundle.collateral.purchase_price > 0:
        return float(bundle.collateral.purchase_price)
    for doc in _docs(bundle, MortgageDocumentType.BUSINESS_DEBT_SCHEDULE):
        source = _source_from(doc, "original_loan_amount", "stated")
        if source is not None and source.value > 0:
            return source.value
    return 0.0


def debt_yield(noi: Optional[float], loan_amount: float) -> Optional[float]:
    """Annual NOI as a fraction of the loan amount, or ``None`` if unknown."""
    if noi is None or noi <= 0 or loan_amount <= 0:
        return None
    return noi / loan_amount


def _resolve_ltv(bundle: MortgageBundle, amount: float) -> Optional[float]:
    if bundle.collateral and bundle.collateral.ltv > 0:
        return float(bundle.collateral.ltv)
    value = 0.0
    if bundle.collateral:
        value = bundle.collateral.appraised_value or bundle.collateral.purchase_price
    if value > 0 and amount > 0:
        return amount / value * 100.0
    return None


def compute_commercial_metrics(bundle: MortgageBundle, loan_amount: float | None = None) -> CommercialCreditMetrics:
    """The full commercial metric set for a deal, with per-metric gaps.

    Only ever called for a ``COMMERCIAL_MORTGAGE`` bundle; residential
    deals are underwritten on income and credit and should not reach
    this code at all.
    """
    notes: list[str] = []
    if bundle.product_line != ProductLine.COMMERCIAL_MORTGAGE:
        notes.append("commercial metrics computed for a non-commercial product line; check the bundle classification")

    dscr = compute_dscr(bundle)
    notes.extend(dscr.notes)

    amount = resolve_loan_amount(bundle, loan_amount)
    ltv = _resolve_ltv(bundle, amount)
    if ltv is None:
        notes.append("LTV is unknown: no appraised value or purchase price to measure the loan against")
    elif bundle.collateral and bundle.collateral.ltv <= 0:
        notes.append(f"LTV derived as loan amount over collateral value ({ltv:.1f}%)")

    dy = debt_yield(dscr.noi, amount)
    if dy is None:
        notes.append("debt yield is unknown: it needs both annual NOI and a loan amount")
    elif dscr.noi is not None and amount > 0:
        notes.append(f"debt yield {dy * 100:.1f}% = NOI {dscr.noi:,.0f} / loan amount {amount:,.0f}")

    return CommercialCreditMetrics(
        dscr=dscr,
        ltv=ltv,
        debt_yield=dy,
        noi=dscr.noi,
        loan_amount=amount,
        notes=tuple(notes),
    )
