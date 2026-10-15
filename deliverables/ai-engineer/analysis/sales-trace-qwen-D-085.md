# qwen/qwen3.8-27b sales misses, D-084 run (D-085 item 3)

Error analysis only. No fix. No model call.

## Summary (orchestrator, 2026-10-15)

| Cause | Files | Count |
|---|---|---|
| Format: two numbers or a label in one value; gate rejects (right number read) | 087, 091, 092, 097 (scan), 099, 100, 105 | 7 |
| Format, plus the quote drops markdown "**"; gate cannot find it (right number read) | 096, 098, 101, 103 | 4 |
| Empty | 095 | 1 |
| Conflict merge: one-sided conflict dropped by the gate | 094 | 1 |
| Scorer: a correct stored conflict scored as miss ($ and commas) | 106 | 1 |
| Wrong number chosen (payroll vs revenue) | none | 0 |

qwen read the right sales number in 11 of 14 misses; the loss is in the output format, which the gate correctly refuses. No fix in this task (D-085).

## SUB-087

- Gold: 1180000
- Model returned: [{"value": "Annual sales $1,180,000; Annual payroll $410,000", "source": "application.pdf", "quote": "Annual sales $1,180,000\nAnnual payroll $410,000", "reason": null}]
- After the gate: [{"value": null, "source": "application.pdf", "quote": null, "reason": "value not inside the cited text"}]
- Final: None, needs_review True, reason None
- Document lines:
  - application.pdf: Annual sales $1,180,000
  - application.pdf: Annual payroll $410,000
- Cause: format: the model put sales and payroll (or a label) in one value; the citation gate rejects a value that is not inside its quote. The right number was read; nothing was stored.

## SUB-091

- Gold: 720000
- Model returned: [{"value": "Annual sales $720,000; Annual payroll $198,000", "source": "application.pdf", "quote": "Annual sales $720,000 (bar 65%, food 35%)", "reason": null}]
- After the gate: [{"value": null, "source": "application.pdf", "quote": null, "reason": "value not inside the cited text"}]
- Final: None, needs_review True, reason None
- Document lines:
  - application.pdf: Annual sales $720,000 (bar 65%, food 35%)
  - application.pdf: Annual payroll $198,000
- Cause: format: the model put sales and payroll (or a label) in one value; the citation gate rejects a value that is not inside its quote. The right number was read; nothing was stored.

## SUB-092

- Gold: 14800000
- Model returned: [{"value": "Annual sales $14,800,000; Annual payroll $1,900,000", "source": "application.pdf", "quote": "Annual sales $14,800,000\nAnnual payroll $1,900,000", "reason": null}]
- After the gate: [{"value": null, "source": "application.pdf", "quote": null, "reason": "value not inside the cited text"}]
- Final: None, needs_review True, reason None
- Document lines:
  - application.pdf: Annual sales $14,800,000
  - application.pdf: Annual payroll $1,900,000
- Cause: format: the model put sales and payroll (or a label) in one value; the citation gate rejects a value that is not inside its quote. The right number was read; nothing was stored.

## SUB-094

- Gold: 1050000
- Model returned: [{"value": null, "source": null, "quote": null, "reason": null}]; conflict [[('$1,050,000', 'application.md'), ('$1,250,000', 'email.md')]]
- After the gate: [{"value": null, "source": null, "quote": null, "reason": null}]
- Final: None, needs_review True, reason None
- Document lines:
  - application.md: **Annual sales:** $1,050,000
  - application.md: **Annual payroll:** $340,000
  - email.md: Lone Oak Signworks LLC - attached app and schedule. Revenue is around 1.25 million I think, I put a number in the app but check it. Eff 2/1/2027. Shop
- Cause: conflict merge: the model reported application $1,050,000 vs email '1.25 million'; the email side failed the gate, and a conflict left with one side is dropped, so the application value was lost (pre-existing gate behaviour).

## SUB-095

- Gold: 1050000
- Model returned: [{"value": null, "source": null, "quote": "", "reason": null}]
- After the gate: [{"value": null, "source": null, "quote": null, "reason": null}]
- Final: None, needs_review True, reason None
- Document lines:
  - application.pdf: Annual sales $1,050,000
  - application.pdf: Annual payroll $340,000
- Cause: empty: the model returned no sales value although the typed application states it.

## SUB-096

- Gold: 2350000
- Model returned: [{"value": "Sales: $2,350,000; Payroll: $510,000", "source": "application.md", "quote": "Annual sales: $2,350,000 combined", "reason": null}]
- After the gate: [{"value": null, "source": "application.md", "quote": null, "reason": "quote not found in application.md"}]
- Final: None, needs_review True, reason None
- Document lines:
  - application.md: **Annual sales:** $2,350,000 combined
  - application.md: **Annual payroll:** $510,000
  - email.md: Mesquite Home and Gift Co, 3 stores in East Texas. Schedule in excel. Eff 1/1/2027. Combined sales about 2.35M. Had a couple claims this year, all on 
- Cause: format: as above, and the quote drops the markdown '**' around the label, so the gate cannot find the quote in the file. The right number was read; nothing was stored.

## SUB-097

- Gold: 1640000
- Model returned: [{"value": "Annual sales: 1,640,000; Annual payroll: 455,000", "source": "scan.jpg", "quote": "Annual sales: 1,640,000", "reason": null}]
- After the gate: [{"value": null, "source": "scan.jpg", "quote": null, "reason": "value not inside the cited text"}]
- Final: None, needs_review True, reason None
- Document lines:
  - scan.jpg: Annual sales: 1,640,000
  - scan.jpg: Avnual payroll: 455,000
- Cause: format: the model put sales and payroll (or a label) in one value; the citation gate rejects a value that is not inside its quote. The right number was read; nothing was stored. (scan source)

## SUB-098

- Gold: 1450000
- Model returned: [{"value": "Sales: $1,450,000; Payroll: $680,000", "source": "application.md", "quote": "Annual sales: $1,450,000", "reason": null}]
- After the gate: [{"value": null, "source": "application.md", "quote": null, "reason": "quote not found in application.md"}]
- Final: None, needs_review True, reason None
- Document lines:
  - application.md: **Annual sales:** $1,450,000
  - application.md: **Annual payroll:** $680,000
  - email.md: Caprock Tile and Stone Inc, Lubbock. Tile and stone install, we do residential and some light commercial. Eff 3/1/2027. Sales around 1.45M. Shop is a 
- Cause: format: as above, and the quote drops the markdown '**' around the label, so the gate cannot find the quote in the file. The right number was read; nothing was stored.

## SUB-099

- Gold: 3900000
- Model returned: [{"value": "Annual sales $3,900,000; Annual payroll $540,000", "source": "application.pdf", "quote": "Annual sales $3,900,000\nAnnual payroll $540,000", "reason": null}]
- After the gate: [{"value": null, "source": "application.pdf", "quote": null, "reason": "value not inside the cited text"}]
- Final: None, needs_review True, reason None
- Document lines:
  - application.pdf: Annual sales $3,900,000
  - application.pdf: Annual payroll $540,000
  - email.md: Brazos Paper and Janitorial Supply LLC in Waco. Renewal 1/1/2027. Clean account, no losses. Warehouse is sprinklered. Sales 3.9M. Attaching app and sc
- Cause: format: the model put sales and payroll (or a label) in one value; the citation gate rejects a value that is not inside its quote. The right number was read; nothing was stored.

## SUB-100

- Gold: 246000
- Model returned: [{"value": "Gross rents $246,000", "source": "application.pdf", "quote": "Annual sales Gross rents $246,000", "reason": null}]
- After the gate: [{"value": null, "source": "application.pdf", "quote": null, "reason": "value not inside the cited text"}]
- Final: None, needs_review True, reason None
- Document lines:
  - application.pdf: Annual sales Gross rents $246,000
- Cause: format: the value carries the label 'Gross rents'; the gate rejects it. Right number.

## SUB-101

- Gold: 720000
- Model returned: [{"value": "Sales: $720,000; Payroll: $196,000", "source": "application.md", "quote": "Annual sales: $720,000", "reason": null}]
- After the gate: [{"value": null, "source": "application.md", "quote": null, "reason": "quote not found in application.md"}]
- Final: None, needs_review True, reason None
- Document lines:
  - application.md: **Annual sales:** $720,000
  - application.md: **Annual payroll:** $196,000
  - email.md: Pappa Sal's Pizza Co, El Paso. Eff 1/1/2027. Had a grease fire in January, its on the loss run scan, sorry the scan is bad. Two deck ovens. Sales arou
- Cause: format: as above, and the quote drops the markdown '**' around the label, so the gate cannot find the quote in the file. The right number was read; nothing was stored.

## SUB-103

- Gold: 1390000
- Model returned: [{"value": "Sales: $1,390,000; Payroll: $610,000", "source": "application.md", "quote": "Annual sales: $1,390,000", "reason": null}]
- After the gate: [{"value": null, "source": "application.md", "quote": null, "reason": "quote not found in application.md"}]
- Final: None, needs_review True, reason None
- Document lines:
  - application.md: **Annual sales:** $1,390,000
  - application.md: **Annual payroll:** $610,000
- Cause: format: as above, and the quote drops the markdown '**' around the label, so the gate cannot find the quote in the file. The right number was read; nothing was stored.

## SUB-105

- Gold: 2100000
- Model returned: [{"value": "Annual sales $2,100,000; Annual payroll $620,000", "source": "application.pdf", "quote": "Annual sales $2,100,000 (food $1,550,000, bar $550,000)\nAnnual payroll $620,000", "reason": null}]
- After the gate: [{"value": null, "source": "application.pdf", "quote": null, "reason": "value not inside the cited text"}]
- Final: None, needs_review True, reason None
- Document lines:
  - application.pdf: Annual sales $2,100,000 (food $1,550,000, bar $550,000)
  - application.pdf: Annual payroll $620,000
  - email.md: Sakura Ridge Grill and Sushi LLC, Frisco, new location eff 2/1/2027. Hibachi tables and sushi bar, full bar. Revenue split is in the app. Slip claim i
- Cause: format: the model put sales and payroll (or a label) in one value; the citation gate rejects a value that is not inside its quote. The right number was read; nothing was stored.

## SUB-106

- Gold: 1520000
- Model returned: [{"value": null, "source": null, "quote": null, "reason": null}]; conflict [[('$1,520,000', 'application.pdf'), ('$1,200,000', 'email.md')]]
- After the gate: [{"value": null, "source": null, "quote": null, "reason": null}]; conflict [[('$1,520,000', 'application.pdf'), ('$1,200,000', 'email.md')]]
- Final: None, needs_review True, reason None; open conflict [[('$1,520,000', 'application.pdf'), ('$1,200,000', 'email.md')]]
- Document lines:
  - application.pdf: Annual sales $1,520,000
  - application.pdf: Annual payroll $880,000
  - email.md: Redbud Engineering Consulting LLC, Irving. Eff 4/1/2027. Revenue last year was about 1.2M per my books. Application says 1.52M, the accountant put the
- Cause: not a model error: the real conflict (application $1,520,000 vs email 1.2M) is stored; the frozen scorer cannot match the stored sides because they keep $ and commas, so it marks a miss instead of flagged.

