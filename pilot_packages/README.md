# Pilot packages

Drop **redacted** carrier/MGA/broker submissions here for shadow underwriting.

## Layout

```
pilot_packages/
  <partner_name>/
    <submission_id>/
      acord.xml          # required
      loss_run.md        # strongly recommended
      sov.md             # strongly recommended
      inspection.md      # optional
      supplemental/      # optional extra docs
      meta.json          # optional metadata
```

## Quick start

```bash
# Seed demo packages from built-in realworld scenarios
PYTHONPATH=src python cli.py pilot seed

# List
PYTHONPATH=src python cli.py pilot list

# Run one (shadow mode — bind disabled)
PYTHONPATH=src python cli.py pilot run --partner demo --submission coastal_fl_appetite_decline

# Run all
PYTHONPATH=src python cli.py pilot run --all
```

## meta.json example

```json
{
  "insured_name": "Acme Distributors Inc",
  "expected_decision": "refer",
  "notes": "Redacted 2025 renewal — UW previously referred for loss ratio"
}
```

## Rules

- Remove FEINs / SSNs / personal emails before drop (or rely on Rytera redaction)
- Prefer ACORD XML over scanned PDFs when available
- Shadow mode is ON until live Guidewire credentials are configured
