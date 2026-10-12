# 10-minute manager demo

Synthetic data only. Nothing on this page binds coverage or declines an applicant. Carrier A, B, and C are placeholders.

Use one submission so the page opens in seconds: Frio Paper Wholesale LLC, SUB-009. It is already packaged and quoted.

## 0:00 — What you are looking at

Sanger & Altgelt prepares small commercial submissions for a carrier panel. The system reads the file, cites what it found, and recommends a carrier. An underwriter approves, edits, or declines. The system does not bind.

## 1:00 — The file that arrived

Open `simulation/inbox/SUB-009/`.

- `application.md` is the application.
- `email.md` is the producer's note.
- `schedule.csv` is the building schedule.
- `loss-runs.md` is valued through 2026-08-31, with zero claims in 5 years.

The insured is Frio Paper Wholesale LLC, light wholesale, at 1800 Factor St, San Antonio.

## 2:30 — Open the workbench

From the project folder, in a terminal that already has the model settings:

```bash
python underwriting_pipeline/app/workbench.py --serve SUB-009
```

Open http://127.0.0.1:8765 . Leave the terminal running. The first load calls the model for this one submission.

## 4:00 — Walk the page

On the SUB-009 article, show these in order:

1. The files the submission came in with.
2. The extracted fields. Each row has a value, a confidence, a source file, and the cited text.
3. Conflicts. This one should have none. If a later demo has two addresses, both stay on the page and neither is picked.
4. Missing items. This one should have none.
5. The point score and the reason codes. Say out loud that the number is not a premium.
6. The carrier match. This one recommends Carrier A. Say out loud that the match is a recommendation.

## 7:00 — Record a decision

In the form on that article:

- Underwriter id: your initials, or `UW-DEMO`
- Action: `approve`
- Reason: `Demo. Wholesale, clean loss runs, Carrier A recommendation.`

Click **Record decision**. The page reloads. The counts at the top go up by one approval. Nothing is bound. Nothing is sent by that click.

The line is appended to `deliverables/software-engineer/decisions.jsonl`. Edits and declines require a reason. Those two actions are the corrections we can count later.

## 8:30 — What already went to the carrier

Show `simulation/to-carrier/SUB-009.md`. The top line is `Sent-by: user`. The body says nothing was declined and nothing was bound.

Show `simulation/from-carrier/SUB-009-carrier-a.md`. Carrier A's fictional quote is premium 6100 and deductible 2500. It is not a bind.

## 9:30 — Close

The underwriter still decides. A quote is not a binder. Bars, nightclubs, and fireworks are no-match, and we do not email a decline. Stop the terminal with Control-C when you are done.
