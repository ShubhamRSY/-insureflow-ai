from __future__ import annotations

from insureflow.models.mortgage import (
    AssetSummary,
    BorrowerProfile,
    CollateralSummary,
    CreditSummary,
    IncomeSummary,
    MortgageBundle,
    MortgageBundleStatus,
    MortgageDocument,
    MortgageDocumentType,
    ProductLine,
    ReconciliationIssue,
)


class MortgageReconciliationEngine:
    """Cross-document validation for mortgage loan packages."""

    WAGE_TOLERANCE_PCT = 0.05

    def reconcile(self, bundle: MortgageBundle) -> MortgageBundle:
        issues: list[ReconciliationIssue] = []

        w2s = bundle.documents_by_type(MortgageDocumentType.W2)
        tax_returns = bundle.documents_by_type(MortgageDocumentType.TAX_RETURN_1040)
        credit_reports = bundle.documents_by_type(MortgageDocumentType.CREDIT_REPORT)
        appraisals = bundle.documents_by_type(MortgageDocumentType.RESIDENTIAL_APPRAISAL)
        purchases = bundle.documents_by_type(MortgageDocumentType.PURCHASE_AGREEMENT)
        gifts = bundle.documents_by_type(MortgageDocumentType.GIFT_LETTER)
        bank_stmts = bundle.documents_by_type(MortgageDocumentType.BANK_STATEMENT)

        # W-2 Box 1 total vs 1040 wages (joint returns: sum all W-2s)
        w2_total = self._sum_latest_w2_wages(w2s)
        for tr in tax_returns:
            tr_wages = tr.get_float("wages_line1") or tr.get_float("total_income")
            if w2_total and tr_wages:
                diff_pct = abs(w2_total - tr_wages) / max(w2_total, 1)
                if diff_pct > self.WAGE_TOLERANCE_PCT:
                    issues.append(
                        ReconciliationIssue(
                            field_path="income.wages",
                            source_a=f"W-2 total ({len(w2s)} forms)",
                            source_b=tr.source_path or "1040",
                            value_a=f"${w2_total:,.0f}",
                            value_b=f"${tr_wages:,.0f}",
                            severity="high" if diff_pct > 0.10 else "warning",
                            rule_id="W2_1040_WAGE_MATCH",
                        )
                    )

        # Appraisal vs purchase price
        for appr in appraisals:
            appr_val = appr.get_float("appraised_value")
            for pa in purchases:
                price = pa.get_float("purchase_price")
                if appr_val and price:
                    diff_pct = abs(appr_val - price) / price
                    if diff_pct > 0.05:
                        issues.append(
                            ReconciliationIssue(
                                field_path="collateral.appraised_vs_purchase",
                                source_a=appr.source_path or "Appraisal",
                                source_b=pa.source_path or "Purchase Agreement",
                                value_a=f"${appr_val:,.0f}",
                                value_b=f"${price:,.0f}",
                                severity="warning",
                                rule_id="APPRAISAL_PURCHASE_VARIANCE",
                            )
                        )

        # Credit report name vs W-2 employee name (primary borrower only)
        for cr in credit_reports:
            cr_name = cr.get_field("borrower_name").lower().strip()
            cr_first = cr_name.split()[0] if cr_name else ""
            for w2 in w2s:
                w2_name = w2.get_field("employee_name").lower().strip()
                w2_first = w2_name.split()[0] if w2_name else ""
                if not cr_first or not w2_first:
                    continue
                # Joint loan: only validate W-2s that belong to the primary borrower on the credit report
                if cr_first not in w2_name and w2_first != cr_first:
                    continue
                if cr_first not in w2_name:
                    issues.append(
                        ReconciliationIssue(
                            field_path="identity.borrower_name",
                            source_a=cr.source_path or "Credit Report",
                            source_b=w2.source_path or "W-2",
                            value_a=cr.get_field("borrower_name"),
                            value_b=w2.get_field("employee_name"),
                            severity="high",
                            rule_id="IDENTITY_NAME_MISMATCH",
                        )
                    )

        # Gift letter amount should appear as deposit pattern (flag if large gift)
        for gift in gifts:
            amount = gift.get_float("gift_amount")
            if amount >= 10000:
                issues.append(
                    ReconciliationIssue(
                        field_path="assets.gift_verification",
                        source_a=gift.source_path or "Gift Letter",
                        source_b="Bank Statements",
                        value_a=f"${amount:,.0f}",
                        value_b="Verify wire/deposit in bank statements",
                        severity="warning",
                        rule_id="GIFT_SOURCE_VERIFICATION",
                    )
                )

        bundle.reconciliation_issues = issues
        bundle.status = MortgageBundleStatus.RECONCILED
        return bundle

    def build_summaries(self, bundle: MortgageBundle) -> MortgageBundle:
        bundle.borrowers = self._extract_borrowers(bundle)
        bundle.income = self._build_income(bundle)
        bundle.credit = self._build_credit(bundle)
        bundle.assets = self._build_assets(bundle)
        bundle.collateral = self._build_collateral(bundle)
        return bundle

    def _sum_latest_w2_wages(self, w2s: list[MortgageDocument]) -> float:
        """Sum the highest Box-1 wages per employee (handles multi-year W-2 packages)."""
        by_employee: dict[str, float] = {}
        for w2 in w2s:
            name = (w2.get_field("employee_name") or "").strip().lower()
            wages = w2.get_float("wages_box1")
            if name and wages:
                by_employee[name] = max(by_employee.get(name, 0.0), wages)
        return sum(by_employee.values())

    def _extract_borrowers(self, bundle: MortgageBundle) -> list[BorrowerProfile]:
        borrowers: list[BorrowerProfile] = []
        seen: set[str] = set()

        for doc in bundle.documents:
            name = (
                doc.get_field("borrower_name")
                or doc.get_field("employee_name")
                or doc.get_field("primary_taxpayer")
                or doc.get_field("account_holder")
            )
            if name and name.lower() not in seen:
                seen.add(name.lower())
                borrowers.append(
                    BorrowerProfile(
                        full_name=name,
                        employer=doc.get_field("employer_name"),
                        address=doc.get_field("property_address") or doc.get_field("address"),
                    )
                )
        return borrowers

    def _build_income(self, bundle: MortgageBundle) -> IncomeSummary | None:
        wages = 0.0
        self_emp = 0.0
        total = 0.0
        agi = 0.0
        sources: list[str] = []

        w2_docs = bundle.documents_by_type(MortgageDocumentType.W2)
        if w2_docs:
            wages = self._sum_latest_w2_wages(w2_docs)
            sources.extend(w2.source_path or "W-2" for w2 in w2_docs if w2.get_float("wages_box1"))

        for tr in bundle.documents_by_type(MortgageDocumentType.TAX_RETURN_1040):
            total = max(total, tr.get_float("total_income"))
            agi = max(agi, tr.get_float("adjusted_gross_income"))
            self_emp = max(self_emp, tr.get_float("business_income"))
            sources.append(tr.source_path or "1040")

        if not wages and not total:
            return None
        return IncomeSummary(
            annual_wages=wages or total,
            self_employment_income=self_emp,
            total_income=total or wages + self_emp,
            adjusted_gross_income=agi or total,
            sources=sources,
        )

    def _build_credit(self, bundle: MortgageBundle) -> CreditSummary | None:
        reports = bundle.documents_by_type(MortgageDocumentType.CREDIT_REPORT)
        if not reports:
            return None
        cr = reports[0]
        score = int(cr.get_float("credit_score"))
        flags: list[str] = []
        util = cr.get_float("utilization_rate")
        if util > 30:
            flags.append(f"High utilization ({util}%)")
        if score and score < 620:
            flags.append(f"Below minimum credit score ({score})")
        return CreditSummary(
            bureau=cr.get_field("bureau"),
            credit_score=score,
            total_balance=cr.get_float("total_balance"),
            total_monthly_payment=cr.get_float("total_monthly_payment"),
            utilization_rate=util,
            open_accounts=int(cr.get_float("open_accounts")),
            derogatory_flags=flags,
        )

    def _build_assets(self, bundle: MortgageBundle) -> AssetSummary | None:
        total = 0.0
        accounts: list[dict] = []
        gift_total = 0.0

        for stmt in bundle.documents_by_type(MortgageDocumentType.BANK_STATEMENT):
            bal = stmt.get_float("ending_balance")
            if bal:
                total += bal
                accounts.append({"source": stmt.source_path, "balance": bal, "type": "bank"})

        for gift in bundle.documents_by_type(MortgageDocumentType.GIFT_LETTER):
            gift_total += gift.get_float("gift_amount")

        if not total and not gift_total:
            return None
        return AssetSummary(total_liquid_assets=total, accounts=accounts, gift_funds=gift_total)

    def _build_collateral(self, bundle: MortgageBundle) -> CollateralSummary | None:
        appr_val = 0.0
        price = 0.0
        address = ""

        for appr in bundle.documents_by_type(MortgageDocumentType.RESIDENTIAL_APPRAISAL):
            appr_val = max(appr_val, appr.get_float("appraised_value"))
            address = appr.get_field("property_address") or address

        for appr in bundle.documents_by_type(MortgageDocumentType.COMMERCIAL_APPRAISAL):
            appr_val = max(appr_val, appr.get_float("appraised_value"))
            address = appr.get_field("property_address") or address

        for pa in bundle.documents_by_type(MortgageDocumentType.PURCHASE_AGREEMENT):
            price = max(price, pa.get_float("purchase_price"))
            address = pa.get_field("property_address") or address

        if not appr_val and not price:
            return None
        collateral_value = appr_val or price
        ltv = (price / collateral_value * 100) if collateral_value and price else 0.0
        return CollateralSummary(
            property_address=address,
            appraised_value=appr_val,
            purchase_price=price,
            ltv=ltv,
        )
