from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Optional

import typer
from rich.console import Console
from rich.table import Table

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
    acord_xml: Optional[Path] = typer.Option(None, "--acord", "-a", help="Path to ACORD XML file"),
    inspection_reports: Optional[list[Path]] = typer.Option(
        None, "--report", "-r", help="Path to inspection report(s)"
    ),
    supplemental: Optional[list[Path]] = typer.Option(
        None, "--supplemental", "-s", help="Path to supplemental document(s)"
    ),
    bundle_id: Optional[str] = typer.Option(None, "--bundle-id", "-b", help="Custom bundle ID"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed output"),
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
    console.print("\n[bold]Reconciliation Summary:[/]")
    console.print(f"  Match Rate: {recon.get('match_rate', 0):.1%}")
    console.print(f"  Discrepancies: {len(recon.get('discrepancies', []))}")
    console.print(f"  Overall Status: {recon.get('overall_status', 'N/A')}")

    audit = results.get("audit_summary", {})
    console.print("\n[bold]Audit Summary:[/]")
    console.print(f"  Total Entries: {audit.get('total_audit_entries', 0)}")
    console.print(f"  Provenance Nodes: {audit.get('total_provenance_nodes', 0)}")
    console.print(f"  Verified Nodes: {audit.get('verified_nodes', 0)}")
    console.print(f"  Verification Rate: {audit.get('verification_rate', 0):.1%}")

    if verbose:
        synth = results.get("synthesis", {})
        console.print("\n[bold]Synthesis Profile:[/]")
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
    console.print("\n[bold]Reconciliation:[/]")
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
    console.print("\n[bold]Audit Trail:[/]")
    console.print(f"  {audit.get('total_audit_entries', 0)} events logged")
    console.print(
        f"  {audit.get('verified_nodes', 0)}/{audit.get('total_provenance_nodes', 0)} nodes verified"
    )
    console.print(f"  Verification Rate: {audit.get('verification_rate', 0):.1%}")

    console.print("\n[green]Demo complete![/]")


@app.command()
def audit(
    bundle_id: str = typer.Argument(..., help="Bundle ID to inspect"),
    path: Optional[Path] = typer.Option(None, "--path", "-p", help="Audit store path"),
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
        color = {"info": "blue", "warning": "yellow", "error": "red", "critical": "red bold"}.get(
            sev, "white"
        )
        console.print(
            f"  [{color}][{sev.upper():7s}][/] {entry.get('event', '')} - {entry.get('message', '')}"
        )

    console.print(f"\n[bold]Total entries:[/] {len(entries)}")


@app.command()
def agents(
    acord_xml: Optional[Path] = typer.Option(None, "--acord", "-a", help="Path to ACORD XML file"),
    json_payload: Optional[Path] = typer.Option(
        None, "--json", "-j", help="Path to JSON broker payload"
    ),
    loss_run: Optional[Path] = typer.Option(
        None, "--loss-run", "-l", help="Path to loss run document"
    ),
    inspection: Optional[Path] = typer.Option(
        None, "--report", "-r", help="Path to inspection report"
    ),
    sov_doc: Optional[Path] = typer.Option(None, "--sov", "-s", help="Path to schedule of values"),
    detailed: bool = typer.Option(False, "--detailed", "-d", help="Show detailed agent findings"),
) -> None:
    """Run multi-agent underwriting analysis on submission documents."""
    from insureflow.ingestion.loader import SubmissionLoader

    docs: dict[str, Any] = {}
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
        console.print(
            "[red]No input documents. Use --acord, --json, --loss-run, --report, or --sov[/]"
        )
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

    console.print("\n[bold]═══ UNDERWRITING MEMO ═══[/]")
    console.print(f"[bold]Bundle:[/] {memo['bundle_id']}")
    console.print(f"[bold]Insured:[/] {memo['insured_name']}")
    console.print(f"[bold]Decision:[/] [{decision_color}]{memo['decision'].upper()}[/]")
    console.print(f"[bold]Risk Score:[/] {memo['overall_risk_score']:.2f}")
    console.print(f"[bold]Risk Severity:[/] {memo['overall_risk_severity'].upper()}")

    console.print("\n[bold]Summary:[/]")
    console.print(f"  {memo['summary']}")

    findings = memo.get("key_findings", [])
    if findings:
        table = Table(title=f"Key Findings ({len(findings)})")
        table.add_column("Severity", style="bold")
        table.add_column("Category")
        table.add_column("Finding")
        for f in findings:
            sev_color = {
                "critical": "red bold",
                "high": "red",
                "moderate": "yellow",
                "low": "green",
            }
            table.add_row(
                f"[{sev_color.get(f['severity'], 'white')}]{f['severity'].upper()}[/]",
                f["category"],
                f["title"],
            )
        console.print(table)

    conditions = memo.get("conditions", [])
    if conditions:
        console.print("\n[bold]Conditions / Actions:[/]")
        for c in conditions:
            console.print(f"  • {c}")

    if memo.get("human_review_required"):
        console.print("\n[red bold]⚠ HUMAN REVIEW REQUIRED[/]")
        for reason in memo.get("human_review_reasons", []):
            console.print(f"  [red]• {reason}[/]")

    if detailed:
        agent_results = memo.get("agent_results", {})
        console.print("\n[bold]Agent Performance:[/]")
        for name, stats in agent_results.items():
            color = "green" if not stats.get("errors") else "red"
            console.print(
                f"  [{color}]{name}:[/] risk={stats['risk_score']:.2f}, "
                f"findings={stats['findings_count']}, "
                f"summary={stats['summary']}"
            )
            if stats.get("errors"):
                for e in stats["errors"]:
                    console.print(f"    [red]ERROR: {e}[/]")

    console.print("\n[green]Multi-agent analysis complete.[/]")


@app.command("mortgage-borrowers")
def mortgage_borrowers(
    directory: Path = typer.Option(
        Path("simulated_documents/home_mortgage"),
        "--dir",
        "-d",
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

    console.print("\n[green]Per-borrower processing complete.[/]")


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
            console.print(
                "[red]Provide --dir or --file, or place docs in simulated_documents/home_mortgage[/]"
            )
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

    console.print("\n[bold]═══ MORTGAGE UNDERWRITING MEMO ═══[/]")
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
            sev_color = {
                "critical": "red bold",
                "high": "red",
                "moderate": "yellow",
                "low": "green",
            }
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
            console.print(
                f"  [{r['severity']}] {r['field_path']}: {r['value_a']} vs {r['value_b']}"
            )

    if detailed:
        types = results.get("document_types", {})
        console.print("\n[bold]Document Classification:[/]")
        for dtype, count in sorted(types.items()):
            console.print(f"  {dtype}: {count}")

    if results.get("human_review_required"):
        console.print("\n[red bold]⚠ HUMAN REVIEW REQUIRED[/]")

    console.print("\n[green]Mortgage pipeline complete.[/]")


@app.command("serve")
def serve(
    port: int = typer.Option(8002, "--port", "-p", help="Port (8000/8001 often taken)"),
    host: str = typer.Option("127.0.0.1", "--host", help="Bind host"),
    reload: bool = typer.Option(True, "--reload/--no-reload", help="Auto-reload on code changes"),
) -> None:
    """Start the InsureFlow API + web dashboard (use insureflow.api, not llm.main)."""
    import uvicorn

    console.print(f"\n[bold green]InsureFlow API[/] → http://{host}:{port}")
    console.print(f"[bold]Dashboard[/]      → http://{host}:{port}/dashboard")
    console.print(f"[bold]Diagnostics[/]   → http://{host}:{port}/system/diagnostics")
    console.print("[dim]Stop with Ctrl+C[/]\n")
    uvicorn.run(
        "insureflow.api:app",
        host=host,
        port=port,
        reload=reload,
    )


@app.command("auth-reset")
def auth_reset(
    port: int = typer.Option(8002, "--port", "-p", help="API port"),
) -> None:
    """Clear ALL dashboard login accounts on the running server + browser session hint."""
    import urllib.error
    import urllib.request

    url = f"http://127.0.0.1:{port}/auth/reset"
    try:
        req = urllib.request.Request(url, method="POST")
        with urllib.request.urlopen(req, timeout=5) as resp:
            import json

            data = json.loads(resp.read().decode())
        console.print(f"[green]Server: cleared {data.get('users_removed', 0)} user(s).[/]")
    except urllib.error.URLError as exc:
        console.print(f"[red]Could not reach API on port {port}:[/] {exc}")
        console.print("[yellow]Start the server first:[/] python cli.py serve --port 8002")
        raise typer.Exit(1) from exc
    console.print("[bold green]Done.[/] Open in browser to wipe saved login too:")
    console.print(
        f"  [link=http://127.0.0.1:{port}/auth/reset]http://127.0.0.1:{port}/auth/reset[/]"
    )


@app.command("e2e")
def e2e(
    port: int = typer.Option(8002, "--port", "-p"),
    in_process: bool = typer.Option(
        False, "--in-process", help="Run via TestClient (no live server)"
    ),
    fast: bool = typer.Option(False, "--fast", help="Skip connector pull tests"),
    no_browser: bool = typer.Option(False, "--no-browser", help="Skip Playwright UI tests"),
    no_celery: bool = typer.Option(False, "--no-celery", help="Skip Celery worker test"),
    use_llm: bool = typer.Option(False, "--use-llm"),
    timeout: int = typer.Option(360, "--timeout", help="Job poll timeout seconds"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Run end-to-end tests across auth, connectors, insurance, mortgage, and infra."""
    from insureflow.e2e.runner import run_inprocess, run_live

    kwargs = {
        "use_llm": use_llm,
        "test_connectors": not fast,
        "test_browser": not no_browser,
        "test_celery": not no_celery,
        "job_timeout": timeout,
    }
    report = (
        run_inprocess(**kwargs)
        if in_process
        else run_live(base_url=f"http://127.0.0.1:{port}", **kwargs)
    )

    if json_output:
        console.print_json(json.dumps(report, indent=2))
    else:
        for row in report["results"]:
            mark = "[green]PASS[/]" if row["passed"] else "[red]FAIL[/]"
            console.print(f"  {mark} {row['name']}: {row.get('detail', '')}")
        color = "green bold" if report["success"] else "red bold"
        console.print(f"\n[{color}]{report['passed']}/{report['total']} passed[/]")
    if not report["success"]:
        raise typer.Exit(1)


@app.command()
def doctor(
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    from insureflow.health.diagnostics import CheckStatus, SystemDiagnostics

    report = SystemDiagnostics(project_root=Path.cwd()).run_all()

    if json_output:
        console.print_json(json.dumps(report, indent=2))
        return

    overall_colors = {
        "healthy": "green bold",
        "degraded": "yellow bold",
        "missing": "red bold",
        "error": "red bold",
    }
    color = overall_colors.get(report["overall"], "white")
    console.print("\n[bold]InsureFlow System Doctor[/]")
    console.print(f"Overall: [{color}]{report['overall'].upper()}[/]")
    console.print(f"LLM mode: [bold]{report['llm_mode']}[/]")
    s = report["summary"]
    console.print(
        f"Checks: {s['ok']} ok · {s['degraded']} degraded · {s['missing']} missing · {s['error']} error\n"
    )

    table = Table(show_header=True, header_style="bold")
    table.add_column("Component")
    table.add_column("Status")
    table.add_column("Message")
    status_style = {
        CheckStatus.OK.value: "green",
        CheckStatus.DEGRADED.value: "yellow",
        CheckStatus.MISSING.value: "red",
        CheckStatus.ERROR.value: "red bold",
    }
    for check in report["checks"]:
        st = check["status"]
        table.add_row(
            check["component"],
            f"[{status_style.get(st, 'white')}]{st.upper()}[/]",
            check["message"],
        )
    console.print(table)

    if report["llm_mode"] == "deterministic_fallback":
        console.print("\n[yellow]Tip:[/] Add LLM_API_KEY to .env for full ReAct agent reasoning.")
        console.print("     cp .env.example .env  →  edit LLM_API_KEY=sk-...")
    console.print("\n[dim]Web UI: python cli.py serve --port 8002  →  /dashboard[/]\n")


# ── Lending ─────────────────────────────────────────────────────────────

lending_app = typer.Typer(help="Lending product underwriting for business & consumer loans.")


@lending_app.command("underwrite")
def lending_underwrite(
    product: str = typer.Argument(
        ...,
        help="Product type: business_term_loan, business_loc, cre, construction, sba_7a, sba_504, equipment, invoice, personal_term, personal_loc, auto, boat, heloc, secured, unsecured",
    ),
    amount: float = typer.Option(..., "--amount", "-a", help="Requested loan amount"),
    term: int = typer.Option(12, "--term", "-t", help="Loan term in months"),
    purpose: str = typer.Option("other", "--purpose", "-p", help="Loan purpose"),
    business_name: str = typer.Option(
        "", "--business", "-b", help="Business name (for business loans)"
    ),
    industry: str = typer.Option("", "--industry", "-i", help="Industry (for business loans)"),
    revenue: float = typer.Option(0.0, "--revenue", "-r", help="Annual revenue (business)"),
    net_income: float = typer.Option(0.0, "--net-income", "-ni", help="Net income (business)"),
    ebitda: float = typer.Option(0.0, "--ebitda", "-e", help="EBITDA (business)"),
    debt_service: float = typer.Option(
        0.0, "--debt-service", "-ds", help="Annual debt service (business)"
    ),
    total_assets: float = typer.Option(0.0, "--total-assets", "-ta", help="Total assets"),
    total_liabilities: float = typer.Option(
        0.0, "--total-liabilities", "-tl", help="Total liabilities"
    ),
    current_assets: float = typer.Option(0.0, "--current-assets", "-ca", help="Current assets"),
    current_liabilities: float = typer.Option(
        0.0, "--current-liabilities", "-cl", help="Current liabilities"
    ),
    collateral_value: float = typer.Option(
        0.0, "--collateral", "-c", help="Total collateral value"
    ),
    years_in_business: float = typer.Option(0.0, "--years", "-y", help="Years in business"),
    first_name: str = typer.Option("", "--first-name", "-fn", help="First name (consumer loans)"),
    last_name: str = typer.Option("", "--last-name", "-ln", help="Last name (consumer loans)"),
    credit_score: int = typer.Option(
        0, "--credit-score", "-cs", help="Credit score (consumer loans)"
    ),
    annual_income: float = typer.Option(0.0, "--income", "-inc", help="Annual income (consumer)"),
    monthly_debt: float = typer.Option(
        0.0, "--monthly-debt", "-md", help="Total monthly debt (consumer)"
    ),
    employment_years: float = typer.Option(
        0.0, "--emp-years", "-ey", help="Years at current employer"
    ),
    bankruptcies: int = typer.Option(0, "--bankruptcies", help="Bankruptcies in last 7 years"),
    foreclosures: int = typer.Option(0, "--foreclosures", help="Foreclosures in last 7 years"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """Run the lending underwriting pipeline for business or consumer loan applications."""
    from insureflow.lending import LendingPipeline
    from insureflow.lending.models import (
        BusinessFinancialData,
        BusinessLoanApplication,
        ConsumerFinancialData,
        ConsumerLoanApplication,
        LoanProductType,
        LoanPurpose,
    )

    product_map: dict[str, LoanProductType] = {
        "business_term_loan": LoanProductType.BUSINESS_TERM_LOAN,
        "business_loc": LoanProductType.BUSINESS_LINE_OF_CREDIT,
        "cre": LoanProductType.COMMERCIAL_REAL_ESTATE,
        "construction": LoanProductType.CONSTRUCTION_LOAN,
        "sba_7a": LoanProductType.SBA_7A,
        "sba_504": LoanProductType.SBA_504,
        "equipment": LoanProductType.EQUIPMENT_FINANCING,
        "invoice": LoanProductType.INVOICE_FINANCING,
        "personal_term": LoanProductType.PERSONAL_TERM_LOAN,
        "personal_loc": LoanProductType.PERSONAL_LINE_OF_CREDIT,
        "auto": LoanProductType.AUTO_LOAN,
        "boat": LoanProductType.BOAT_LOAN,
        "heloc": LoanProductType.HOME_EQUITY_LINE,
        "secured": LoanProductType.SECURED_PERSONAL,
        "unsecured": LoanProductType.UNSECURED_PERSONAL,
    }

    purpose_map: dict[str, LoanPurpose] = {
        "working_capital": LoanPurpose.WORKING_CAPITAL,
        "refinance": LoanPurpose.DEBT_REFINANCE,
        "equipment": LoanPurpose.EQUIPMENT_PURCHASE,
        "real_estate": LoanPurpose.REAL_ESTATE_PURCHASE,
        "construction": LoanPurpose.CONSTRUCTION,
        "expansion": LoanPurpose.BUSINESS_EXPANSION,
        "inventory": LoanPurpose.INVENTORY_FINANCING,
        "acquisition": LoanPurpose.ACQUISITION,
        "auto": LoanPurpose.AUTO_PURCHASE,
        "boat": LoanPurpose.BOAT_PURCHASE,
        "home_improvement": LoanPurpose.HOME_IMPROVEMENT,
        "debt_consolidation": LoanPurpose.DEBT_CONSOLIDATION,
        "education": LoanPurpose.EDUCATION,
        "medical": LoanPurpose.MEDICAL,
        "other": LoanPurpose.OTHER,
    }

    pt = product_map.get(product)
    if pt is None:
        console.print(f"[red]Unknown product: {product}. Options: {', '.join(product_map)}[/]")
        raise typer.Exit(1)

    purp = purpose_map.get(purpose, LoanPurpose.OTHER)
    is_business = pt.value.startswith(
        ("business_", "commercial_", "construction_", "sba_", "equipment_", "invoice_")
    )

    with console.status("[bold green]Running lending underwriting..."):
        if is_business:
            app: BusinessLoanApplication | ConsumerLoanApplication = BusinessLoanApplication(
                business_name=business_name or "Unnamed Business",
                industry=industry,
                years_in_business=years_in_business,
                product_type=pt,
                loan_purpose=purp,
                requested_amount=amount,
                requested_term_months=term,
                financials=[
                    BusinessFinancialData(
                        annual_revenue=revenue,
                        net_income=net_income,
                        ebitda=ebitda,
                        debt_service=debt_service,
                        total_assets=total_assets,
                        total_liabilities=total_liabilities,
                        current_assets=current_assets,
                        current_liabilities=current_liabilities,
                    )
                ],
                collateral=[Collateral(estimated_value=collateral_value, description="General collateral")]
                if collateral_value > 0
                else [],
            )
        else:
            app = ConsumerLoanApplication(
                first_name=first_name or "Applicant",
                last_name=last_name or "Unknown",
                product_type=pt,
                loan_purpose=purp,
                requested_amount=amount,
                requested_term_months=term,
                financial_data=ConsumerFinancialData(
                    annual_income=annual_income,
                    total_monthly_debt=monthly_debt,
                    credit_score=credit_score,
                    employment_years=employment_years,
                    bankruptcies_last_7_years=bankruptcies,
                    foreclosures_last_7_years=foreclosures,
                ),
            )

        pipeline = LendingPipeline()
        result = pipeline.run(app)

    if json_output:
        console.print_json(json.dumps(result.model_dump(mode="json"), indent=2))
        return

    decision_color = (
        "green" if result.decision.value in ("approved", "approved_with_conditions") else "red"
    )
    console.print(f"\n[bold]Lending Underwriting Result[/] — {app.application_id}")
    console.print(f"  Product:      [bold]{result.product_type.value}[/]")
    console.print(f"  Decision:     [{decision_color}]{result.decision.value.upper()}[/]")
    console.print(f"  Risk Score:   {result.risk_score:.0f}/100 ({result.risk_rating})")
    console.print(f"  Requested:    ${result.requested_amount:,.0f}")
    if result.approved_amount:
        console.print(f"  Approved:     ${result.approved_amount:,.0f}")
    if result.approved_rate:
        console.print(f"  Rate:         {result.approved_rate:.2f}%")
    if result.conditions:
        console.print(f"  Conditions:   {len(result.conditions)}")
        for c in result.conditions[:5]:
            console.print(f"    • {c}")
        if len(result.conditions) > 5:
            console.print(f"    ... and {len(result.conditions) - 5} more")
    if result.human_review_required:
        console.print(
            f"  [yellow]Human Review Required:[/] {', '.join(result.human_review_reasons)}"
        )
    if result.compliance_violations:
        console.print(
            f"  [yellow]Compliance:[/] {len(result.compliance_violations)} rule(s) evaluated"
        )
    if result.document_count:
        console.print(f"  Documents:    {result.document_count}")


# ── Model Registry ──────────────────────────────────────────────────────

registry_app = typer.Typer(help="Model component registry for compliance team review.")


@registry_app.command("list")
def registry_list(
    component: str = typer.Argument(
        "prompt", help="Component type: prompt, llm_config, compliance_rule, agent_logic"
    ),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    from insureflow.registry import ComponentType, RegistryService

    reg = RegistryService()
    ct = ComponentType(component)
    entries = reg.list_versions(ct)

    if json_output:
        data = [e.model_dump(mode="json") for e in entries]
        console.print_json(json.dumps(data, indent=2))
        return

    if not entries:
        console.print(f"[yellow]No entries for {component}.[/]")
        return

    table = Table(title=f"{component.upper()}s")
    table.add_column("ID")
    table.add_column("Version")
    table.add_column("Status")
    table.add_column("Key")
    table.add_column("Description")
    table.add_column("Updated")

    status_colors = {
        "approved": "green",
        "review": "yellow",
        "draft": "blue",
        "rejected": "red",
        "superseded": "dim",
    }

    for e in entries:
        key = ""
        if hasattr(e, "prompt_key") and e.prompt_key:
            key = e.prompt_key
        elif hasattr(e, "model_tier") and e.model_tier:
            key = e.model_tier
        elif hasattr(e, "agent_type") and e.agent_type:
            key = e.agent_type

        color = status_colors.get(e.status.value, "white")
        table.add_row(
            e.entry_id[:12],
            e.version_label,
            f"[{color}]{e.status.value}[/]",
            key,
            e.description[:40],
            e.updated_at.strftime("%Y-%m-%d %H:%M"),
        )

    console.print(table)
    console.print(f"\n[dim]{len(entries)} version(s)[/]")


@registry_app.command("diff")
def registry_diff(
    component: str = typer.Argument(
        ..., help="Component type: prompt, llm_config, compliance_rule, agent_logic"
    ),
    id_a: str = typer.Argument(..., help="First (newer) entry ID"),
    id_b: str = typer.Argument(..., help="Second (older) entry ID"),
) -> None:
    from insureflow.registry import RegistryService

    reg = RegistryService()
    diff = reg.compute_diff(id_a, id_b)

    if "error" in diff:
        console.print(f"[red]{diff['error']}[/]")
        raise typer.Exit(1)

    console.print(f"[bold]Diff:[/] {diff.get('from_version')} → {diff.get('to_version')}")
    console.print(f"[bold]Component:[/] {diff.get('component_type', component)}")
    console.print(
        f"[bold]Key:[/] {diff.get('prompt_key') or diff.get('model_tier') or diff.get('agent_type', '')}"
    )

    if diff.get("hash_changed"):
        console.print("\n[red]⚠ Content hash changed[/]")
        console.print(f"  From: {diff.get('from_hash')}")
        console.print(f"  To:   {diff.get('to_hash')}")

    if diff.get("text_changed"):
        console.print("\n[yellow]✎ Prompt text changed[/]")

    if diff.get("changes"):
        console.print("\n[yellow]✎ Configuration changes:[/]")
        for field, change in diff["changes"].items():
            console.print(f"  {field}: [red]{change['from']}[/] → [green]{change['to']}[/]")

    if diff.get("added"):
        console.print(f"\n[green]+ Added rules:[/] {', '.join(diff['added'])}")
    if diff.get("removed"):
        console.print(f"\n[red]- Removed rules:[/] {', '.join(diff['removed'])}")
    if diff.get("changed"):
        console.print(f"\n[yellow]~ Changed rules:[/] {', '.join(diff['changed'])}")


@registry_app.command("show")
def registry_show(
    entry_id: str = typer.Argument(..., help="Entry ID"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    from insureflow.registry import RegistryService

    reg = RegistryService()
    entry = reg.get(entry_id)
    if not entry:
        console.print(f"[red]Entry not found: {entry_id}[/]")
        raise typer.Exit(1)

    if json_output:
        console.print_json(json.dumps(entry.model_dump(mode="json"), indent=2))
        return

    console.print(f"[bold]Entry:[/] {entry.entry_id}")
    console.print(f"[bold]Type:[/] {entry.component_type.value}")
    console.print(f"[bold]Version:[/] {entry.version_label}")
    console.print(f"[bold]Status:[/] {entry.status.value}")
    console.print(f"[bold]Description:[/] {entry.description}")
    console.print(f"[bold]Change Notes:[/] {entry.change_notes or '(none)'}")
    console.print(f"[bold]Created:[/] {entry.created_by or 'unknown'} @ {entry.created_at}")
    console.print(f"[bold]Updated:[/] {entry.updated_at}")

    from insureflow.registry.models import (
        AgentLogicVersion,
        ComplianceRuleVersion,
        LLMConfigVersion,
        PromptVersion,
    )

    if isinstance(entry, PromptVersion) and entry.prompt_key:
        console.print(f"[bold]Prompt Key:[/] {entry.prompt_key}")
    if isinstance(entry, LLMConfigVersion) and entry.model_tier:
        console.print(f"[bold]Model Tier:[/] {entry.model_tier}")
        console.print(f"[bold]Model:[/] {entry.provider}/{entry.model_name}")
        console.print(f"[bold]Temperature:[/] {entry.temperature}")
    if isinstance(entry, AgentLogicVersion) and entry.agent_type:
        console.print(f"[bold]Agent Type:[/] {entry.agent_type}")
        console.print(f"[bold]Source:[/] {entry.source_file}")
    if isinstance(entry, ComplianceRuleVersion) and entry.rules_snapshot:
        console.print(f"[bold]Rules:[/] {len(entry.rules_snapshot)} rule(s)")

    if entry.review_comments:
        console.print(f"\n[bold]Review Comments ({len(entry.review_comments)}):[/]")
        for c in entry.review_comments:
            console.print(f"  [{c.reviewer}] {c.comment} @ {c.created_at}")


@registry_app.command("create")
def registry_create(
    component: str = typer.Argument(..., help="Component type"),
    key: str = typer.Option(
        "", "--key", "-k", help="Component key (prompt_key, model_tier, agent_type)"
    ),
    description: str = typer.Option("", "--desc", "-d", help="Description"),
    notes: str = typer.Option("", "--notes", "-n", help="Change notes"),
    version: str = typer.Option("1.0.0", "--version", "-v", help="Version label"),
    creator: str = typer.Option("cli", "--creator", "-c", help="Created by"),
) -> None:
    from insureflow.registry import ComponentType, RegistryService
    from insureflow.registry.models import (
        AgentLogicVersion,
        ComplianceRuleVersion,
        LLMConfigVersion,
        PromptVersion,
    )

    reg = RegistryService()
    ct = ComponentType(component)
    entry: PromptVersion | LLMConfigVersion | ComplianceRuleVersion | AgentLogicVersion

    if ct == ComponentType.PROMPT:
        from insureflow.agents.prompts import SYSTEM_PROMPTS

        prompt_text = SYSTEM_PROMPTS.get(key, "")
        if not prompt_text:
            console.print(
                f"[red]Unknown prompt key: {key}. Available: {', '.join(SYSTEM_PROMPTS.keys())}[/]"
            )
            raise typer.Exit(1)
        entry = PromptVersion(
            component_type=ct,
            version_label=version,
            created_by=creator,
            description=description or f"Draft {key} prompt",
            change_notes=notes,
            prompt_key=key,
            prompt_text=prompt_text,
        )
    elif ct == ComponentType.LLM_CONFIG:
        entry = LLMConfigVersion(
            component_type=ct,
            version_label=version,
            created_by=creator,
            description=description or f"Draft {key} LLM config",
            change_notes=notes,
            model_tier=key,
        )
    elif ct == ComponentType.COMPLIANCE_RULE:
        from insureflow.mortgage.compliance import BANK_RULES

        rules = {}
        for rule in BANK_RULES:
            rules[rule.rule_id] = {
                "name": rule.name,
                "severity": rule.severity,
                "product_lines": [p.value for p in rule.product_lines],
            }
        entry = ComplianceRuleVersion(
            component_type=ct,
            version_label=version,
            created_by=creator,
            description=description or "Draft compliance rules",
            change_notes=notes,
            rules_snapshot=rules,
        )
    elif ct == ComponentType.AGENT_LOGIC:
        entry = AgentLogicVersion(
            component_type=ct,
            version_label=version,
            created_by=creator,
            description=description or f"Draft {key} agent logic",
            change_notes=notes,
            agent_type=key,
        )
    else:
        console.print(f"[red]Unsupported component type: {component}[/]")
        raise typer.Exit(1)

    reg.create(entry)
    console.print(
        f"[green]Created {component} version [bold]{entry.entry_id[:12]}[/] ({version})[/]"
    )


@registry_app.command("submit")
def registry_submit(
    entry_id: str = typer.Argument(..., help="Entry ID to submit for review"),
) -> None:
    from insureflow.registry import RegistryService

    reg = RegistryService()
    entry = reg.submit_for_review(entry_id)
    if not entry:
        console.print(f"[red]Could not submit {entry_id} — not found or not in DRAFT status[/]")
        raise typer.Exit(1)
    console.print(f"[yellow]Submitted [bold]{entry_id[:12]}[/] for review (status → review)[/]")


@registry_app.command("approve")
def registry_approve(
    entry_id: str = typer.Argument(..., help="Entry ID to approve"),
    reviewer: str = typer.Option("cli-user", "--reviewer", "-r", help="Reviewer name"),
    comment: str = typer.Option("", "--comment", "-c", help="Review comment"),
) -> None:
    from insureflow.registry import RegistryService

    reg = RegistryService()
    entry = reg.get(entry_id)
    if not entry:
        console.print(f"[red]Entry not found: {entry_id}[/]")
        raise typer.Exit(1)

    old_active = reg.get_active_version(entry.component_type)
    if old_active:
        old_label = old_active.version_label
    else:
        old_label = "(none)"

    entry = reg.approve(entry_id, reviewer=reviewer, comment=comment)
    if not entry:
        console.print("[red]Could not approve — not in REVIEW status[/]")
        raise typer.Exit(1)

    console.print(f"[green]✓ Approved [bold]{entry_id[:12]}[/] ({entry.version_label})[/]")
    console.print(f"  Superseded: {old_label}")
    console.print(f"  Reviewer: {reviewer}")
    if comment:
        console.print(f"  Comment: {comment}")


@registry_app.command("reject")
def registry_reject(
    entry_id: str = typer.Argument(..., help="Entry ID to reject"),
    reviewer: str = typer.Option("cli-user", "--reviewer", "-r", help="Reviewer name"),
    comment: str = typer.Option("", "--comment", "-c", help="Review comment"),
) -> None:
    from insureflow.registry import RegistryService

    reg = RegistryService()
    entry = reg.reject(entry_id, reviewer=reviewer, comment=comment)
    if not entry:
        console.print("[red]Could not reject — not found or not in REVIEW status[/]")
        raise typer.Exit(1)
    console.print(f"[red]✗ Rejected [bold]{entry_id[:12]}[/][/]")
    if comment:
        console.print(f"  Comment: {comment}")


@registry_app.command("snapshot")
def registry_snapshot(
    bundle_id: str = typer.Option("", "--bundle", "-b", help="Associated bundle ID"),
    show: bool = typer.Option(False, "--show", "-s", help="Show latest snapshots"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    from insureflow.registry import RegistryService

    reg = RegistryService()

    if show:
        snapshots = reg.list_snapshots()
        if not snapshots:
            console.print("[yellow]No snapshots found.[/]")
            return
        if json_output:
            data = [s.model_dump(mode="json") for s in snapshots]
            console.print_json(json.dumps(data, indent=2))
            return
        table = Table(title="Snapshots")
        table.add_column("ID")
        table.add_column("Generated")
        table.add_column("Prompts")
        table.add_column("LLM Configs")
        table.add_column("Rules")
        table.add_column("Agent Logic")
        table.add_column("Bundle")
        for s in snapshots:
            table.add_row(
                s.snapshot_id[:12],
                s.generated_at.strftime("%Y-%m-%d %H:%M"),
                str(len(s.prompts)),
                str(len(s.llm_configs)),
                str(len(s.compliance_rules)),
                str(len(s.agent_logic)),
                s.bundle_id[:20] or "-",
            )
        console.print(table)
        return

    snapshot = reg.take_snapshot(bundle_id=bundle_id)
    console.print(f"[green]Snapshot taken: [bold]{snapshot.snapshot_id}[/][/]")
    console.print(f"  Prompts: {len(snapshot.prompts)} active")
    console.print(f"  LLM Configs: {len(snapshot.llm_configs)} active")
    console.print(f"  Compliance Rules: {len(snapshot.compliance_rules)} active")
    console.print(f"  Agent Logic: {len(snapshot.agent_logic)} active")
    if bundle_id:
        console.print(f"  Bundle: {bundle_id}")


@registry_app.command("bootstrap")
def registry_bootstrap(
    creator: str = typer.Option("system", "--creator", "-c", help="Creator label"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be created"),
) -> None:
    from insureflow.agents.prompts import SYSTEM_PROMPTS
    from insureflow.mortgage.compliance import BANK_RULES
    from insureflow.registry import RegistryService

    if dry_run:
        console.print("[bold]Would create:[/]")
        for key in SYSTEM_PROMPTS:
            console.print(f"  Prompt: {key}")
        for tier in ("cheap", "expensive", "default"):
            console.print(f"  LLM Config: {tier}")
        console.print(f"  Compliance Rules: {len(BANK_RULES)} rules")
        for agent_type in (
            "compliance_agent",
            "loss_run_analyst",
            "fraud_detection",
            "uw_decision",
            "risk_analyst",
        ):
            console.print(f"  Agent Logic: {agent_type}")
        return

    reg = RegistryService()
    entries = reg.bootstrap(created_by=creator)
    console.print(f"[green]Bootstrapped {len(entries)} approved version(s) from current code[/]")
    for e in entries:
        key = (
            getattr(e, "prompt_key", None)
            or getattr(e, "model_tier", None)
            or getattr(e, "agent_type", None)
            or ""
        )
        console.print(
            f"  ✓ {e.component_type.value:18s} {key:20s} → {e.entry_id[:12]} ({e.version_label})"
        )


@registry_app.command("context")
def registry_context(
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    from insureflow.registry import RegistryService

    reg = RegistryService()
    ctx = reg.version_context()

    if json_output:
        console.print_json(json.dumps(ctx, indent=2))
        return

    console.print("[bold]Active Version Context[/]\n")
    console.print("[underline]Prompts:[/]")
    for key, info in ctx.get("prompts", {}).items():
        console.print(
            f"  {key:20s} {info['version']:8s} {info['entry_id'][:12]} hash={info['hash']}"
        )
    console.print()
    console.print("[underline]LLM Configs:[/]")
    for tier, info in ctx.get("llm_configs", {}).items():
        console.print(f"  {tier:20s} {info['version']:8s} {info['model']}")
    console.print()
    console.print("[underline]Compliance Rules:[/]")
    for rid in ctx.get("compliance_rules", []):
        console.print(f"  {rid[:12]}")
    console.print()
    console.print("[underline]Agent Logic:[/]")
    for agent, info in ctx.get("agent_logic", {}).items():
        console.print(f"  {agent:20s} {info['version']:8s} {info['source_file']}")


app.add_typer(registry_app, name="registry", help="Model version registry & compliance review")
app.add_typer(
    lending_app, name="lending", help="Lending underwriting for business & consumer loan products"
)


# ── Document Analytics ───────────────────────────────────────────────────


@app.command("doc-stats")
def doc_stats(
    vertical: str = typer.Option("", "--vertical", "-v", help="Filter: insurance, mortgage"),
    distribution: bool = typer.Option(
        False, "--distribution", "-d", help="Show distribution instead of summary"
    ),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """Show average documents per application across pipeline runs."""
    from insureflow.analytics.documents import DocumentAnalyticsEngine

    engine = DocumentAnalyticsEngine()

    if distribution:
        dist = engine.distribution(vertical=vertical)
        if json_output:
            console.print_json(json.dumps(dist, indent=2))
            return
        table = Table(title=f"Document Count Distribution ({vertical or 'all'})")
        table.add_column("Bucket")
        table.add_column("Applications")
        for bucket, count in dist.items():
            table.add_row(bucket, str(count))
        console.print(table)
        return

    summary = engine.summary(vertical=vertical)

    if json_output:
        console.print_json(json.dumps(summary, indent=2))
        return

    console.print(f"\n[bold]Document Analytics[/] ({summary['vertical']})")
    console.print(f"  Total applications:      {summary['total_applications']}")
    console.print(f"  Total documents:         {summary['total_documents_processed']}")
    console.print(f"  [green]Avg docs/application:   {summary['avg_documents_per_application']}[/]")
    console.print(f"  Median:                  {summary['median_documents']}")
    console.print(f"  P95:                     {summary['p95_documents']}")
    console.print(f"  Min:                     {summary['min_documents']}")
    console.print(f"  Max:                     {summary['max_documents']}")
    console.print(f"  With human review:       {summary['applications_with_review']}")
    console.print(f"  Without review:          {summary['applications_without_review']}")
    console.print()

    if summary["by_vertical"]:
        console.print("[underline]By vertical:[/]")
        for v, stats in summary["by_vertical"].items():
            console.print(
                f"  {v:15s} {stats['avg']:>8.1f} avg ({stats['min']}-{stats['max']})  n={stats['count']}"
            )

    if summary["by_decision"]:
        console.print("[underline]By decision:[/]")
        for decision, count in sorted(summary["by_decision"].items()):
            console.print(f"  {decision:15s} {count}")


if __name__ == "__main__":
    app()
