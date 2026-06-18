from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.tree import Tree

from insureflow.agents.supervisor import SupervisorAgent
from insureflow.audit.store import AuditStore
from insureflow.pipeline import UnderwritingPipeline

app = typer.Typer(
    name="insureflow",
    help="Autonomous agentic pipeline for commercial underwriting data ingestion & reconciliation",
)
console = Console()


@app.command()
def run(
    acord_xml: Optional[Path] = typer.Option(
        None, "--acord", "-a", help="Path to ACORD XML file"
    ),
    inspection_reports: Optional[list[Path]] = typer.Option(
        None, "--report", "-r", help="Path to inspection report(s)"
    ),
    supplemental: Optional[list[Path]] = typer.Option(
        None, "--supplemental", "-s", help="Path to supplemental document(s)"
    ),
    bundle_id: Optional[str] = typer.Option(
        None, "--bundle-id", "-b", help="Custom bundle ID"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Show detailed output"
    ),
) -> None:
    log_level = logging.INFO if verbose else logging.WARNING
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    pipeline = UnderwritingPipeline()

    with console.status("[bold green]Running InsureFlow pipeline..."):
        results = pipeline.run_from_files(
            acord_xml_path=str(acord_xml) if acord_xml else None,
            inspection_report_paths=[str(p) for p in (inspection_reports or [])],
            supplemental_paths=[str(p) for p in (supplemental or [])],
            bundle_id=bundle_id,
        )

    status_color = "green" if results["status"] == "completed" else "yellow"
    console.print(f"\n[bold]Pipeline Status:[/] [{status_color}]{results['status']}[/]")
    console.print(f"[bold]Bundle ID:[/] {results['bundle_id']}")

    recon = results.get("reconciliation", {})
    console.print(f"\n[bold]Reconciliation Summary:[/]")
    console.print(f"  Match Rate: {recon.get('match_rate', 0):.1%}")
    console.print(f"  Discrepancies: {len(recon.get('discrepancies', []))}")
    console.print(f"  Overall Status: {recon.get('overall_status', 'N/A')}")

    audit = results.get("audit_summary", {})
    console.print(f"\n[bold]Audit Summary:[/]")
    console.print(f"  Total Entries: {audit.get('total_audit_entries', 0)}")
    console.print(f"  Provenance Nodes: {audit.get('total_provenance_nodes', 0)}")
    console.print(f"  Verified Nodes: {audit.get('verified_nodes', 0)}")
    console.print(f"  Verification Rate: {audit.get('verification_rate', 0):.1%}")

    if verbose:
        synth = results.get("synthesis", {})
        console.print(f"\n[bold]Synthesis Profile:[/]")
        profile = synth.get("synthesized_profile", {})
        for key, value in profile.items():
            console.print(f"  {key}: {value}")

        discrepancies = recon.get("discrepancies", [])
        if discrepancies:
            table = Table(title="Discrepancies")
            table.add_column("Field", style="red")
            table.add_column("Source A", style="cyan")
            table.add_column("Source B", style="magenta")
            table.add_column("Severity", style="yellow")
            for d in discrepancies:
                table.add_row(
                    d.get("field_path", ""),
                    str(d.get("source_a", "")),
                    str(d.get("source_b", "")),
                    d.get("severity", ""),
                )
            console.print(table)

    console.print("\n[green]Pipeline run complete.[/]")


@app.command()
def demo() -> None:
    """Run the pipeline with built-in sample data."""
    sample_xml = """<?xml version="1.0" encoding="UTF-8"?>
<ACORD xmlns="http://www.acord.org/standards/PC_Surety/ACORD">
  <Submission>
    <NamedInsured>
      <GeneralPartyInfo>
        <NameInfo>
          <CommercialName>
            <Name>Acme Manufacturing Corp</Name>
            <DBA>Acme Industrial</DBA>
          </CommercialName>
        </NameInfo>
        <Addr1>100 Industrial Blvd</Addr1>
        <City>Chicago</City>
        <StateProvCd>IL</StateProvCd>
        <PostalCode>60601</PostalCode>
        <TaxIdentity>
          <TaxID>36-1234567</TaxID>
        </TaxIdentity>
        <BusinessType>Corporation</BusinessType>
      </GeneralPartyInfo>
    </NamedInsured>
    <Broker>
      <GeneralPartyInfo>
        <NameInfo>
          <CommercialName>
            <Name>Risk Advisors LLC</Name>
          </CommercialName>
        </NameInfo>
        <ContactName>John Smith</ContactName>
        <Email>jsmith@riskadvisors.com</Email>
      </GeneralPartyInfo>
    </Broker>
    <PolicyPeriod>
      <EffectiveDate>2026-07-01</EffectiveDate>
      <ExpirationDate>2027-07-01</ExpirationDate>
    </PolicyPeriod>
    <Coverage>
      <CoverageType>General Liability</CoverageType>
      <Limit>2000000</Limit>
      <Deductible>25000</Deductible>
      <Premium>85000</Premium>
    </Coverage>
    <Coverage>
      <CoverageType>Property</CoverageType>
      <Limit>5000000</Limit>
      <Deductible>50000</Deductible>
      <Premium>120000</Premium>
    </Coverage>
    <Risk>
      <NAICSCode>332710</NAICSCode>
      <SICCode>3499</SICCode>
      <BusinessDescription>Metal parts manufacturing</BusinessDescription>
      <ConstructionType>Masonry</ConstructionType>
      <Occupancy>Manufacturing</Occupancy>
      <ProtectionClass>4</ProtectionClass>
      <NumberOfStories>2</NumberOfStories>
      <TotalSquareFootage>85000</TotalSquareFootage>
    </Risk>
    <FinancialInfo>
      <AnnualRevenue>15000000</AnnualRevenue>
      <Payroll>4200000</Payroll>
    </FinancialInfo>
  </Submission>
</ACORD>"""

    sample_report = """# INSPECTION REPORT
## Acme Manufacturing Corp
## 100 Industrial Blvd, Chicago, IL 60601

### EXECUTIVE SUMMARY
This report summarizes the physical inspection of Acme Manufacturing Corp,
a metal fabrication facility operating at the above address.

### BUILDING CONSTRUCTION
The building is a 2-story masonry structure built in 1995.
Total square footage is approximately 85,000 sq ft.
The roof is built-up tar and gravel in fair condition.

### OCCUPANCY
The facility operates as a metal parts manufacturing plant
(NAICS 332710). Single occupancy. Operating hours 6am-6pm weekdays.

### FIRE PROTECTION
The building is fully sprinklered with a central station alarm.
Fire extinguishers are present throughout.
Protection class: 4.

### PRIOR LOSSES
One prior claim in 2023 for water damage ($15,000).
No other losses reported in the last 5 years.

### RECOMMENDATIONS
1. Upgrade roof within 2 years
2. Increase security monitoring
3. Document business continuity plan
"""

    pipeline = UnderwritingPipeline()
    with console.status("[bold green]Running demo pipeline..."):
        results = pipeline.run(
            acord_xml=sample_xml,
            inspection_reports=[sample_report],
        )

    status_color = "green" if results["status"] == "completed" else "yellow"
    console.print(f"\n[bold]Demo Pipeline Status:[/] [{status_color}]{results['status']}[/]")

    recon = results.get("reconciliation", {})
    console.print(f"\n[bold]Reconciliation:[/]")
    console.print(f"  Matched: {recon.get('matched_fields', 0)}/{recon.get('total_fields', 0)}")
    console.print(f"  Match Rate: {recon.get('match_rate', 0):.1%}")
    console.print(f"  Discrepancies: {len(recon.get('discrepancies', []))}")

    discrepancies = recon.get("discrepancies", [])
    if discrepancies:
        table = Table(title="Discrepancies Found")
        table.add_column("Field", style="red")
        table.add_column("ACORD Value", style="cyan")
        table.add_column("Report Value", style="magenta")
        table.add_column("Severity", style="yellow")
        for d in discrepancies:
            table.add_row(
                d.get("field_path", ""),
                str(d.get("structured_value", "")),
                str(d.get("unstructured_value", "")),
                d.get("severity", ""),
            )
        console.print(table)
    else:
        console.print("[green]No discrepancies found.[/]")

    audit = results.get("audit_summary", {})
    console.print(f"\n[bold]Audit Trail:[/]")
    console.print(f"  {audit.get('total_audit_entries', 0)} events logged")
    console.print(f"  {audit.get('verified_nodes', 0)}/{audit.get('total_provenance_nodes', 0)} nodes verified")
    console.print(f"  Verification Rate: {audit.get('verification_rate', 0):.1%}")

    console.print("\n[green]Demo complete![/]")


@app.command()
def audit(
    bundle_id: str = typer.Argument(..., help="Bundle ID to inspect"),
    path: Optional[Path] = typer.Option(
        None, "--path", "-p", help="Audit store path"
    ),
) -> None:
    """Inspect the audit trail for a completed pipeline run."""
    store = AuditStore(base_path=path)
    trail_data = store.load_json(bundle_id, "audit_trail.json")
    if not trail_data:
        console.print(f"[red]No audit trail found for bundle: {bundle_id}[/]")
        raise typer.Exit(1)

    console.print(f"\n[bold]Audit Trail: {bundle_id}[/]")
    entries = trail_data.get("entries", [])
    for entry in entries:
        sev = entry.get("severity", "info")
        color = {"info": "blue", "warning": "yellow", "error": "red", "critical": "red bold"}.get(sev, "white")
        console.print(f"  [{color}][{sev.upper():7s}][/] {entry.get('event', '')} - {entry.get('message', '')}")

    console.print(f"\n[bold]Total entries:[/] {len(entries)}")


@app.command()
def agents(
    acord_xml: Optional[Path] = typer.Option(
        None, "--acord", "-a", help="Path to ACORD XML file"
    ),
    json_payload: Optional[Path] = typer.Option(
        None, "--json", "-j", help="Path to JSON broker payload"
    ),
    loss_run: Optional[Path] = typer.Option(
        None, "--loss-run", "-l", help="Path to loss run document"
    ),
    inspection: Optional[Path] = typer.Option(
        None, "--report", "-r", help="Path to inspection report"
    ),
    sov_doc: Optional[Path] = typer.Option(
        None, "--sov", "-s", help="Path to schedule of values"
    ),
    detailed: bool = typer.Option(
        False, "--detailed", "-d", help="Show detailed agent findings"
    ),
) -> None:
    """Run multi-agent underwriting analysis on submission documents."""
    from insureflow.ingestion.loader import SubmissionLoader

    docs: dict[str, str | list[str] | None] = {}
    doc_labels: list[str] = []

    if acord_xml:
        docs["acord_xml"] = acord_xml.read_text(encoding="utf-8")
        doc_labels.append(f"ACORD: {acord_xml.name}")
    if json_payload:
        docs["json_payload"] = json_payload.read_text(encoding="utf-8")
        doc_labels.append(f"JSON: {json_payload.name}")
    if loss_run:
        docs["loss_run"] = loss_run.read_text(encoding="utf-8")
        doc_labels.append(f"Loss Run: {loss_run.name}")
    if inspection:
        docs["inspection_reports"] = [inspection.read_text(encoding="utf-8")]
        doc_labels.append(f"Report: {inspection.name}")
    if sov_doc:
        docs["schedule_of_values"] = sov_doc.read_text(encoding="utf-8")
        doc_labels.append(f"SOV: {sov_doc.name}")

    if not docs:
        console.print("[red]No input documents. Use --acord, --json, --loss-run, --report, or --sov[/]")
        raise typer.Exit(1)

    with console.status("[bold green]Loading submission..."):
        loader = SubmissionLoader()
        bundle = loader.load_bundle(**docs, bundle_id="agent-analysis", auto_classify=True)

    with console.status("[bold yellow]Running multi-agent analysis..."):
        supervisor = SupervisorAgent()
        memo = supervisor.analyze_submission_structured(bundle)

    decision_color = {
        "accept": "green",
        "refer": "yellow",
        "decline": "red",
    }.get(memo["decision"], "white")

    console.print(f"\n[bold]═══ UNDERWRITING MEMO ═══[/]")
    console.print(f"[bold]Bundle:[/] {memo['bundle_id']}")
    console.print(f"[bold]Insured:[/] {memo['insured_name']}")
    console.print(f"[bold]Decision:[/] [{decision_color}]{memo['decision'].upper()}[/]")
    console.print(f"[bold]Risk Score:[/] {memo['overall_risk_score']:.2f}")
    console.print(f"[bold]Risk Severity:[/] {memo['overall_risk_severity'].upper()}")

    console.print(f"\n[bold]Summary:[/]")
    console.print(f"  {memo['summary']}")

    findings = memo.get("key_findings", [])
    if findings:
        table = Table(title=f"Key Findings ({len(findings)})")
        table.add_column("Severity", style="bold")
        table.add_column("Category")
        table.add_column("Finding")
        for f in findings:
            sev_color = {"critical": "red bold", "high": "red", "moderate": "yellow", "low": "green"}
            table.add_row(
                f"[{sev_color.get(f['severity'], 'white')}]{f['severity'].upper()}[/]",
                f["category"],
                f["title"],
            )
        console.print(table)

    conditions = memo.get("conditions", [])
    if conditions:
        console.print(f"\n[bold]Conditions / Actions:[/]")
        for c in conditions:
            console.print(f"  • {c}")

    if memo.get("human_review_required"):
        console.print(f"\n[red bold]⚠ HUMAN REVIEW REQUIRED[/]")
        for reason in memo.get("human_review_reasons", []):
            console.print(f"  [red]• {reason}[/]")

    if detailed:
        agent_results = memo.get("agent_results", {})
        console.print(f"\n[bold]Agent Performance:[/]")
        for name, stats in agent_results.items():
            color = "green" if not stats.get("errors") else "red"
            console.print(f"  [{color}]{name}:[/] risk={stats['risk_score']:.2f}, "
                          f"findings={stats['findings_count']}, "
                          f"summary={stats['summary']}")
            if stats.get("errors"):
                for e in stats["errors"]:
                    console.print(f"    [red]ERROR: {e}[/]")

    console.print(f"\n[green]Multi-agent analysis complete.[/]")


@app.command("mortgage-borrowers")
def mortgage_borrowers(
    directory: Path = typer.Option(
        Path("simulated_documents/home_mortgage"),
        "--dir", "-d",
        help="Root directory containing per-borrower subfolders",
    ),
    product: str = typer.Option("auto", "--product", "-p"),
    no_llm: bool = typer.Option(False, "--no-llm", help="Disable LLM extraction"),
    detailed: bool = typer.Option(False, "--detailed"),
) -> None:
    """Process each borrower package separately (John vs Maria vs Chen, etc.)."""
    from insureflow.models.mortgage import ProductLine
    from insureflow.mortgage.bundler import discover_borrower_packages
    from insureflow.mortgage.pipeline import MortgagePipeline

    product_map = {
        "auto": None,
        "residential": ProductLine.RESIDENTIAL_MORTGAGE,
        "commercial": ProductLine.COMMERCIAL_MORTGAGE,
    }
    product_line = product_map.get(product.lower())
    packages = discover_borrower_packages(str(directory), product_line=product_line)

    console.print(f"\n[bold]Found {len(packages)} borrower package(s)[/]\n")
    pipeline = MortgagePipeline(use_llm=not no_llm)

    for pkg in packages:
        with console.status(f"[green]Processing {pkg.display_name}..."):
            result = pipeline.run_from_paths(
                pkg.paths,
                bundle_id=f"borrower-{pkg.borrower_id}",
                product_line=pkg.product_line,
                borrower_id=pkg.borrower_id,
            )
        color = {"approve": "green", "refer": "yellow", "suspend": "yellow", "deny": "red"}.get(
            result["decision"], "white"
        )
        console.print(
            f"  [{color}]{pkg.display_name:30s}[/] "
            f"{result['document_count']:3d} docs → {result['decision'].upper()} "
            f"(risk {result['risk_score']:.2f})"
        )
        if detailed and result.get("audit_paths"):
            console.print(f"    [dim]Audit: {result['audit_paths'].get('audit_trail', '')}[/]")

    console.print(f"\n[green]Per-borrower processing complete.[/]")


@app.command()
def mortgage(
    directory: Optional[Path] = typer.Option(
        None, "--dir", "-d", help="Directory of mortgage documents (recursive .txt)"
    ),
    files: Optional[list[Path]] = typer.Option(
        None, "--file", "-f", help="Individual document paths"
    ),
    product: str = typer.Option(
        "auto", "--product", "-p", help="Product line: auto, residential, commercial"
    ),
    no_llm: bool = typer.Option(False, "--no-llm", help="Disable LLM extraction"),
    detailed: bool = typer.Option(
        False, "--detailed", help="Show full document classification and compliance detail"
    ),
) -> None:
    """Process mortgage loan documents (home or commercial) with bank compliance rules."""
    from insureflow.models.mortgage import ProductLine
    from insureflow.mortgage.pipeline import MortgagePipeline

    product_map = {
        "auto": None,
        "residential": ProductLine.RESIDENTIAL_MORTGAGE,
        "commercial": ProductLine.COMMERCIAL_MORTGAGE,
    }
    product_line = product_map.get(product.lower())
    if product_line is None and product.lower() != "auto":
        console.print(f"[red]Unknown product line: {product}[/]")
        raise typer.Exit(1)

    pipeline = MortgagePipeline(use_llm=not no_llm)

    if directory:
        with console.status("[bold green]Processing mortgage documents..."):
            results = pipeline.run_from_directory(str(directory), product_line=product_line)
    elif files:
        with console.status("[bold green]Processing mortgage documents..."):
            results = pipeline.run_from_paths([str(f) for f in files], product_line=product_line)
    else:
        default_dir = Path("simulated_documents/home_mortgage")
        if not default_dir.exists():
            console.print("[red]Provide --dir or --file, or place docs in simulated_documents/home_mortgage[/]")
            raise typer.Exit(1)
        console.print(f"[dim]Using default directory: {default_dir}[/]")
        with console.status("[bold green]Processing mortgage documents..."):
            results = pipeline.run_from_directory(str(default_dir), product_line=product_line)

    decision_color = {
        "approve": "green",
        "refer": "yellow",
        "suspend": "yellow",
        "deny": "red",
    }.get(results["decision"], "white")

    console.print(f"\n[bold]═══ MORTGAGE UNDERWRITING MEMO ═══[/]")
    console.print(f"[bold]Bundle:[/] {results['bundle_id']}")
    console.print(f"[bold]Product:[/] {results['product_line']}")
    console.print(f"[bold]Borrower:[/] {results['borrower']}")
    console.print(f"[bold]Documents:[/] {results['document_count']}")
    console.print(f"[bold]Decision:[/] [{decision_color}]{results['decision'].upper()}[/]")
    console.print(f"[bold]Risk Score:[/] {results['risk_score']:.2f}")
    if results.get("dti_ratio"):
        console.print(f"[bold]DTI:[/] {results['dti_ratio']}%")
    if results.get("ltv_ratio"):
        console.print(f"[bold]LTV:[/] {results['ltv_ratio']:.1f}%")

    memo = results.get("memo", {})
    findings = memo.get("key_findings", [])
    if findings:
        table = Table(title=f"Key Findings ({len(findings)})")
        table.add_column("Severity", style="bold")
        table.add_column("Category")
        table.add_column("Finding")
        for f in findings[:10]:
            sev_color = {"critical": "red bold", "high": "red", "moderate": "yellow", "low": "green"}
            table.add_row(
                f"[{sev_color.get(f['severity'], 'white')}]{f['severity'].upper()}[/]",
                f.get("category", ""),
                f.get("title", ""),
            )
        console.print(table)

    violations = results.get("compliance_violations", [])
    if violations:
        console.print(f"\n[bold]Compliance Violations ({len(violations)}):[/]")
        for v in violations:
            color = "red" if v["severity"] == "critical" else "yellow"
            console.print(f"  [{color}]{v['rule_id']}[/] {v['message']}")

    recon = results.get("reconciliation_issues", [])
    if recon:
        console.print(f"\n[bold]Reconciliation Issues ({len(recon)}):[/]")
        for r in recon[:8]:
            console.print(f"  [{r['severity']}] {r['field_path']}: {r['value_a']} vs {r['value_b']}")

    if detailed:
        types = results.get("document_types", {})
        console.print(f"\n[bold]Document Classification:[/]")
        for dtype, count in sorted(types.items()):
            console.print(f"  {dtype}: {count}")

    if results.get("human_review_required"):
        console.print(f"\n[red bold]⚠ HUMAN REVIEW REQUIRED[/]")

    console.print(f"\n[green]Mortgage pipeline complete.[/]")


if __name__ == "__main__":
    app()
