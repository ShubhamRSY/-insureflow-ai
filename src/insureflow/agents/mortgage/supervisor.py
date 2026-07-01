from __future__ import annotations

import json
import logging

from insureflow.llm.client import LLMClient
from insureflow.models.mortgage import (
    MortgageAgentResult,
    MortgageBundle,
    MortgageDecision,
    MortgageDocumentType,
    MortgageFinding,
    MortgageMemo,
    ProductLine,
)

logger = logging.getLogger(__name__)


def _parse_llm_json_findings(raw: str, category: str) -> list[MortgageFinding]:
    try:
        cleaned = raw.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()
        data = json.loads(cleaned)
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            items = data.get("findings", [])
        else:
            items = []
        return [
            MortgageFinding(
                title=item.get("title", "LLM finding"),
                description=item.get("description", ""),
                severity=item.get("severity", "moderate"),
                category=category,
            )
            for item in items
        ]
    except (json.JSONDecodeError, TypeError):
        pass
    return []


def _collect_doc_text(
    bundle: MortgageBundle, *doc_types: MortgageDocumentType, max_chars: int = 12000
) -> str:
    parts: list[str] = []
    for dt in doc_types:
        for d in bundle.documents_by_type(dt):
            label = dt.value.upper()
            parts.append(f"--- {label} ({d.document_id}) ---\n{d.raw_text[:3000]}")
    combined = "\n\n".join(parts)
    return combined[:max_chars]


class MortgageIncomeAgent:
    agent_name = "IncomeAnalystAgent"

    def analyze(self, bundle: MortgageBundle) -> MortgageAgentResult:
        llm = LLMClient(model_tier="cheap")
        findings: list[MortgageFinding] = []

        doc_text = _collect_doc_text(
            bundle,
            MortgageDocumentType.W2,
            MortgageDocumentType.TAX_RETURN_1040,
            MortgageDocumentType.PAY_STUB,
            MortgageDocumentType.SCHEDULE_C,
        )
        if doc_text.strip():
            system_prompt = (
                "You are a senior mortgage income underwriter. "
                "Analyze income documents for risks, inconsistencies, and stability concerns. "
                "Respond with a JSON array of findings. "
                'Each finding: {"title": str, "description": str, "severity": "low"|"moderate"|"high"|"critical"}.'
            )
            user_prompt = f"Income documents to analyze:\n\n{doc_text[:8000]}"
            try:
                raw = llm.complete(system_prompt=system_prompt, user_prompt=user_prompt)
                findings.extend(_parse_llm_json_findings(raw, "income"))
            except Exception as exc:
                logger.warning("LLM income analysis failed: %s", exc)

        if not bundle.income:
            findings.append(
                MortgageFinding(
                    title="Missing income documentation",
                    description="No qualifying income could be calculated from loan package",
                    severity="critical",
                    category="income",
                )
            )
            return MortgageAgentResult(
                agent_name=self.agent_name,
                findings=findings,
                risk_score=0.9,
                summary="Income verification failed",
            )

        if bundle.income.self_employment_income > 0:
            findings.append(
                MortgageFinding(
                    title="Self-employment income present",
                    description=f"Schedule C / business income ${bundle.income.self_employment_income:,.0f} requires 2-year averaging",
                    severity="moderate",
                    category="income",
                )
            )

        for issue in bundle.reconciliation_issues:
            if issue.rule_id == "W2_1040_WAGE_MATCH":
                findings.append(
                    MortgageFinding(
                        title="W-2 / tax return wage mismatch",
                        description=f"{issue.value_a} vs {issue.value_b}",
                        severity="high",
                        category="income",
                        document_refs=[issue.source_a, issue.source_b],
                    )
                )

        risk = 0.3 if not findings else 0.6
        return MortgageAgentResult(
            agent_name=self.agent_name,
            findings=findings,
            risk_score=risk,
            summary=f"Qualifying income: ${bundle.income.adjusted_gross_income or bundle.income.total_income:,.0f}/yr",
        )


class MortgageCreditAgent:
    agent_name = "CreditAnalystAgent"

    def analyze(self, bundle: MortgageBundle) -> MortgageAgentResult:
        llm = LLMClient(model_tier="cheap")
        findings: list[MortgageFinding] = []

        doc_text = _collect_doc_text(
            bundle,
            MortgageDocumentType.CREDIT_REPORT,
            MortgageDocumentType.CREDIT_CARD_STATEMENT,
            MortgageDocumentType.AUTO_LOAN_STATEMENT,
            MortgageDocumentType.STUDENT_LOAN_STATEMENT,
        )
        if doc_text.strip():
            system_prompt = (
                "You are a senior mortgage credit analyst. "
                "Review credit documents for risks, derogatory marks, high utilization, and payment history issues. "
                "Respond with a JSON array of findings. "
                'Each finding: {"title": str, "description": str, "severity": "low"|"moderate"|"high"|"critical"}.'
            )
            user_prompt = f"Credit documents to analyze:\n\n{doc_text[:8000]}"
            try:
                raw = llm.complete(system_prompt=system_prompt, user_prompt=user_prompt)
                findings.extend(_parse_llm_json_findings(raw, "credit"))
            except Exception as exc:
                logger.warning("LLM credit analysis failed: %s", exc)

        if not bundle.credit:
            findings.append(
                MortgageFinding(
                    title="No credit report",
                    description="Credit profile unavailable",
                    severity="critical",
                    category="credit",
                )
            )
            return MortgageAgentResult(
                agent_name=self.agent_name,
                findings=findings,
                risk_score=0.85,
                summary="Credit analysis incomplete",
            )

        score = bundle.credit.credit_score
        if not score:
            findings.append(
                MortgageFinding(
                    title="Credit score not extracted",
                    description="Credit report present but qualifying score could not be parsed — manual review",
                    severity="moderate",
                    category="credit",
                )
            )
        elif score >= 740:
            findings.append(
                MortgageFinding(
                    title="Strong credit score",
                    description=f"Score {score}",
                    severity="low",
                    category="credit",
                )
            )
        elif score >= 680:
            findings.append(
                MortgageFinding(
                    title="Acceptable credit score",
                    description=f"Score {score}",
                    severity="low",
                    category="credit",
                )
            )
        elif score >= 620:
            findings.append(
                MortgageFinding(
                    title="Marginal credit score",
                    description=f"Score {score} — near minimum",
                    severity="moderate",
                    category="credit",
                )
            )
        else:
            findings.append(
                MortgageFinding(
                    title="Below minimum credit score",
                    description=f"Score {score}",
                    severity="critical",
                    category="credit",
                )
            )

        for flag in bundle.credit.derogatory_flags:
            findings.append(
                MortgageFinding(
                    title="Credit risk flag",
                    description=flag,
                    severity="moderate",
                    category="credit",
                )
            )

        risk = max(0.2, 1.0 - (score / 850)) if score else 0.8
        return MortgageAgentResult(
            agent_name=self.agent_name,
            findings=findings,
            risk_score=risk,
            summary=f"Credit score: {score}, utilization: {bundle.credit.utilization_rate}%",
        )


class MortgageAssetAgent:
    agent_name = "AssetAnalystAgent"

    def analyze(self, bundle: MortgageBundle) -> MortgageAgentResult:
        llm = LLMClient(model_tier="cheap")
        findings: list[MortgageFinding] = []

        doc_text = _collect_doc_text(
            bundle,
            MortgageDocumentType.BANK_STATEMENT,
            MortgageDocumentType.INVESTMENT_STATEMENT,
            MortgageDocumentType.RETIREMENT_401K,
        )
        if doc_text.strip():
            system_prompt = (
                "You are a senior mortgage asset and reserves analyst. "
                "Review bank and investment statements for sufficient liquidity, large deposits, and seasoning concerns. "
                "Respond with a JSON array of findings. "
                'Each finding: {"title": str, "description": str, "severity": "low"|"moderate"|"high"|"critical"}.'
            )
            user_prompt = f"Asset documents to analyze:\n\n{doc_text[:8000]}"
            try:
                raw = llm.complete(system_prompt=system_prompt, user_prompt=user_prompt)
                findings.extend(_parse_llm_json_findings(raw, "assets"))
            except Exception as exc:
                logger.warning("LLM asset analysis failed: %s", exc)

        if not bundle.assets:
            findings.append(
                MortgageFinding(
                    title="No asset verification",
                    description="Bank statements not found",
                    severity="high",
                    category="assets",
                )
            )
            return MortgageAgentResult(
                agent_name=self.agent_name,
                findings=findings,
                risk_score=0.7,
                summary="Asset verification incomplete",
            )

        if bundle.assets.gift_funds > 0:
            findings.append(
                MortgageFinding(
                    title="Gift funds identified",
                    description=f"${bundle.assets.gift_funds:,.0f} — verify source and seasoning",
                    severity="moderate",
                    category="assets",
                )
            )

        reserves = bundle.assets.total_liquid_assets
        severity = "low" if reserves >= 20000 else "moderate" if reserves >= 5000 else "high"
        findings.append(
            MortgageFinding(
                title="Liquid reserves",
                description=f"${reserves:,.0f} across {len(bundle.assets.accounts)} account(s)",
                severity=severity,
                category="assets",
            )
        )

        return MortgageAgentResult(
            agent_name=self.agent_name,
            findings=findings,
            risk_score=0.3 if reserves >= 20000 else 0.6,
            summary=f"Total liquid assets: ${reserves:,.0f}",
        )


class MortgageCollateralAgent:
    agent_name = "CollateralAnalystAgent"

    def analyze(self, bundle: MortgageBundle) -> MortgageAgentResult:
        llm = LLMClient(model_tier="cheap")
        findings: list[MortgageFinding] = []

        doc_text = _collect_doc_text(
            bundle,
            MortgageDocumentType.RESIDENTIAL_APPRAISAL,
            MortgageDocumentType.COMMERCIAL_APPRAISAL,
            MortgageDocumentType.PURCHASE_AGREEMENT,
            MortgageDocumentType.RENT_ROLL,
        )
        if doc_text.strip():
            system_prompt = (
                "You are a senior mortgage collateral appraiser. "
                "Review appraisal and property documents for valuation concerns, condition issues, and market risks. "
                "Respond with a JSON array of findings. "
                'Each finding: {"title": str, "description": str, "severity": "low"|"moderate"|"high"|"critical"}.'
            )
            user_prompt = f"Collateral documents to analyze:\n\n{doc_text[:8000]}"
            try:
                raw = llm.complete(system_prompt=system_prompt, user_prompt=user_prompt)
                findings.extend(_parse_llm_json_findings(raw, "collateral"))
            except Exception as exc:
                logger.warning("LLM collateral analysis failed: %s", exc)

        if not bundle.collateral:
            if bundle.product_line == ProductLine.COMMERCIAL_MORTGAGE:
                rent_rolls = bundle.documents_by_type(MortgageDocumentType.RENT_ROLL)
                if rent_rolls:
                    rr = rent_rolls[0]
                    findings.append(
                        MortgageFinding(
                            title="Commercial rent roll parsed",
                            description=f"{rr.get_field('unit_count')} units, ${rr.get_float('total_monthly_rent'):,.0f}/mo rent",
                            severity="low",
                            category="collateral",
                        )
                    )
                    return MortgageAgentResult(
                        agent_name=self.agent_name,
                        findings=findings,
                        risk_score=0.4,
                        summary="Commercial collateral from rent roll",
                    )
            findings.append(
                MortgageFinding(
                    title="No collateral data",
                    description="Appraisal or purchase agreement missing",
                    severity="high",
                    category="collateral",
                )
            )
            return MortgageAgentResult(
                agent_name=self.agent_name,
                findings=findings,
                risk_score=0.75,
                summary="Collateral analysis incomplete",
            )

        if bundle.collateral.ltv > 80:
            findings.append(
                MortgageFinding(
                    title="High LTV",
                    description=f"LTV {bundle.collateral.ltv:.1f}% — PMI or additional down payment required",
                    severity="moderate",
                    category="collateral",
                )
            )

        return MortgageAgentResult(
            agent_name=self.agent_name,
            findings=findings,
            risk_score=0.35,
            summary=f"Appraised: ${bundle.collateral.appraised_value:,.0f}, LTV: {bundle.collateral.ltv:.1f}%",
        )


class MortgageFraudDetectionAgent:
    agent_name = "FraudDetectionAgent"

    def analyze(self, bundle: MortgageBundle) -> MortgageAgentResult:
        findings: list[MortgageFinding] = []

        # 1. Income inconsistency: W-2 vs 1040 wage discrepancy > 10%
        for issue in bundle.reconciliation_issues:
            if issue.rule_id == "W2_1040_WAGE_MATCH":
                try:
                    v_a = float(issue.value_a.replace("$", "").replace(",", ""))
                    v_b = float(issue.value_b.replace("$", "").replace(",", ""))
                    if v_a > 0:
                        pct = abs(v_a - v_b) / v_a * 100
                        if pct > 10:
                            findings.append(
                                MortgageFinding(
                                    title="W-2 / 1040 wage discrepancy > 10%",
                                    description=f"{pct:.1f}% difference: ${v_a:,.0f} vs ${v_b:,.0f}",
                                    severity="high",
                                    category="fraud",
                                    document_refs=[issue.source_a, issue.source_b],
                                )
                            )
                except (ValueError, TypeError):
                    pass

        # 2. Address mismatches across borrower documents
        if bundle.borrowers:
            addresses = {b.address for b in bundle.borrowers if b.address}
            if len(addresses) > 1:
                findings.append(
                    MortgageFinding(
                        title="Address mismatch across borrowers",
                        description=f"Multiple addresses found: {', '.join(addresses)}",
                        severity="high",
                        category="fraud",
                    )
                )

        # 3. Large gift funds >= $25k
        if bundle.assets and bundle.assets.gift_funds >= 25000:
            findings.append(
                MortgageFinding(
                    title="Large gift funds detected",
                    description=f"${bundle.assets.gift_funds:,.0f} in gift funds — verify source, donor relationship, and seasoning",
                    severity="high",
                    category="fraud",
                )
            )

        # 4. Missing key underwriting documents
        missing_map = {
            MortgageDocumentType.W2: "W-2",
            MortgageDocumentType.TAX_RETURN_1040: "Tax Return (1040)",
            MortgageDocumentType.CREDIT_REPORT: "Credit Report",
        }
        missing_docs = [
            name for dt, name in missing_map.items() if not bundle.documents_by_type(dt)
        ]
        if missing_docs:
            findings.append(
                MortgageFinding(
                    title="Missing critical underwriting documents",
                    description=", ".join(missing_docs),
                    severity="high" if len(missing_docs) >= 2 else "moderate",
                    category="fraud",
                )
            )

        # 5. Suspicious bank statement patterns (rule-based heuristic)
        if bundle.assets and bundle.assets.accounts:
            large_round_deposits = 0
            for acct in bundle.assets.accounts:
                if isinstance(acct, dict):
                    for deposit in acct.get("recent_deposits", []):
                        try:
                            amt = float(str(deposit).replace("$", "").replace(",", ""))
                            if amt >= 5000 and amt % 1000 == 0:
                                large_round_deposits += 1
                        except (ValueError, TypeError):
                            pass
            if large_round_deposits >= 3:
                findings.append(
                    MortgageFinding(
                        title="Suspicious round-number deposits",
                        description=f"{large_round_deposits} round deposits >= $5,000 — possible structured deposits",
                        severity="high",
                        category="fraud",
                    )
                )

        # 6. LLM fraud analysis on all documents
        llm_findings = self._llm_fraud_analysis(bundle)
        findings.extend(llm_findings)

        risk = min(
            1.0, len([f for f in findings if f.severity in ("high", "critical")]) * 0.2 + 0.1
        )
        return MortgageAgentResult(
            agent_name=self.agent_name,
            findings=findings,
            risk_score=round(risk, 3),
            summary=f"Fraud analysis: {len(findings)} red flag(s) detected",
        )

    def _llm_fraud_analysis(self, bundle: MortgageBundle) -> list[MortgageFinding]:
        try:
            all_texts = "\n\n".join(
                f"--- {d.document_type.value.upper()} ({d.document_id}) ---\n{d.raw_text[:2000]}"
                for d in bundle.documents[:10]
            )
            if not all_texts.strip():
                return []

            llm = LLMClient(model_tier="cheap")
            system_prompt = (
                "You are a forensic mortgage fraud analyst. "
                "Examine the document texts for fraud indicators including: "
                "income inconsistencies, suspicious bank activity (round numbers, rapid turnover), "
                "employment red flags, stale or altered documents, identity concerns, "
                "and address mismatches. "
                "Respond with a JSON array of findings. "
                'Each finding: {"title": str, "description": str, "severity": "low"|"moderate"|"high"|"critical"}.'
            )
            user_prompt = f"Loan documents to analyze for fraud:\n\n{all_texts[:10000]}"
            raw = llm.complete(system_prompt=system_prompt, user_prompt=user_prompt)
            return _parse_llm_json_findings(raw, "fraud")
        except Exception as exc:
            logger.warning("LLM fraud analysis failed: %s", exc)
            return []


class MortgageDecisionAgent:
    agent_name = "MortgageDecisionAgent"

    def decide(
        self,
        bundle: MortgageBundle,
        agent_results: list[MortgageAgentResult],
    ) -> MortgageMemo:
        all_findings: list[MortgageFinding] = []
        for ar in agent_results:
            all_findings.extend(ar.findings)

        critical = [f for f in all_findings if f.severity == "critical"]
        high = [f for f in all_findings if f.severity == "high"]
        fraud_critical = [
            f for f in all_findings if f.category == "fraud" and f.severity == "critical"
        ]
        fraud_high = [f for f in all_findings if f.category == "fraud" and f.severity == "high"]
        critical_violations = [v for v in bundle.compliance_violations if v.severity == "critical"]

        if critical or critical_violations or fraud_critical:
            decision = MortgageDecision.DENY
        elif high or len(bundle.reconciliation_issues) >= 2 or fraud_high:
            decision = MortgageDecision.SUSPEND
        elif bundle.reconciliation_issues or bundle.compliance_violations:
            decision = MortgageDecision.REFER
        else:
            decision = MortgageDecision.APPROVE

        risk_scores = [ar.risk_score for ar in agent_results]
        overall_risk = sum(risk_scores) / len(risk_scores) if risk_scores else 0.5

        dti = None
        if bundle.credit and bundle.income:
            monthly = (bundle.income.adjusted_gross_income or bundle.income.total_income) / 12
            if monthly > 0:
                dti = round(bundle.credit.total_monthly_payment / monthly * 100, 1)

        borrower = bundle.borrowers[0].full_name if bundle.borrowers else "Unknown"
        conditions: list[str] = []
        if bundle.reconciliation_issues:
            conditions.append("Resolve cross-document reconciliation issues before closing")
        for v in bundle.compliance_violations:
            if v.severity in ("high", "critical"):
                conditions.append(v.message)

        return MortgageMemo(
            bundle_id=bundle.bundle_id,
            product_line=bundle.product_line,
            borrower_name=borrower,
            decision=decision,
            risk_score=round(overall_risk, 3),
            dti_ratio=dti,
            ltv_ratio=bundle.collateral.ltv if bundle.collateral else None,
            summary=f"Decision: {decision.value.upper()} | {len(all_findings)} findings | {len(bundle.compliance_violations)} compliance checks",
            key_findings=sorted(
                all_findings,
                key=lambda f: {"critical": 0, "high": 1, "moderate": 2, "low": 3}.get(
                    f.severity, 4
                ),
            )[:10],
            reconciliation_issues=bundle.reconciliation_issues,
            compliance_violations=bundle.compliance_violations,
            conditions=conditions,
            human_review_required=decision
            in (MortgageDecision.REFER, MortgageDecision.SUSPEND, MortgageDecision.DENY),
        )


class MortgageSupervisorAgent:
    def __init__(self) -> None:
        self.income = MortgageIncomeAgent()
        self.credit = MortgageCreditAgent()
        self.assets = MortgageAssetAgent()
        self.collateral = MortgageCollateralAgent()
        self.fraud = MortgageFraudDetectionAgent()
        self.decision = MortgageDecisionAgent()

    def analyze(self, bundle: MortgageBundle) -> MortgageMemo:
        results = [
            self.income.analyze(bundle),
            self.credit.analyze(bundle),
            self.assets.analyze(bundle),
            self.collateral.analyze(bundle),
            self.fraud.analyze(bundle),
        ]
        return self.decision.decide(bundle, results)
