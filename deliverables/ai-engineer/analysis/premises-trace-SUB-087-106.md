# Premises, name and operations trace — typed files, T-093 rerun (D-082 item 3)

Error analysis only. No fix. Replies from the T-093 rerun cache (commit 9e725e3, openai/gpt-oss-120b); no model call.

## Summary (orchestrator, 2026-10-14; analysis only, no fix)

| File | Field | Cleared by | What happened |
|---|---|---|---|
| SUB-089 | premises | model | Model put the value in a conflict: the one address vs all three schedule addresses joined. The gate kept no conflict (the joined side has no matching quote), so nothing was left. P-005 did not fire (no labelled second location). |
| SUB-092 | premises | model + agreeing-merge | Model reported a conflict: full address vs street only ("9901 Industrial Park Rd" from the schedule). `prepare.agrees()` does not treat street-only as the same address, so it stays an open conflict and the field is empty. |
| SUB-099 | premises | model + agreeing-merge | Same: full vs street only (from the schedule CSV). |
| SUB-103 | premises | model + agreeing-merge | Same: full vs street only (from the schedule xlsx). |
| SUB-098 | premises | scorer | Extracted correctly as "4102 Mesquite Bend Rd, Lubbock, TX 79424 (shop and yard)"; the frozen scorer needs an exact match, so the trailing note counts as a miss. Address check ok. |
| SUB-098 | named_insured | model + agreeing-merge | Model reported "&" vs "and" as a conflict; `agrees()` does not merge them. |
| SUB-098 | operations | model + agreeing-merge | Model reported the application line vs the email's paraphrase as a conflict. |

None of P-001 (ZIP rule), P-002 (validation) or P-005 (locations) cleared a value on these files. The common cause is the model reporting a conflict between a full value and a shorter form of the same value, and the agreeing-merge not reconciling them. Any fix is a prompt or merge change and needs a P-###.

## SUB-089

### premises_address

- Gold: 2215 Bayou Crest Dr, Houston, TX 77063
- In the documents: application.md: **Premises address:** 2215 Bayou Crest Dr, Houston, TX 77063 (main); see schedule for 2 more; loss-runs.md: Claim 1: date of loss 2026-01-18 | carrier Pecan Ridge (FICTIONAL) | cause: water damage, 2215 Bayou Crest | paid $22,400 | open reserve $0 | status closed; schedule.xlsx: 1	2215 Bayou Crest Dr	Houston	77063	2100000	Masonry	1974	16400	No
- Model returned: [{"value": null, "source": "", "quote": ""}]; conflict sides [["2215 Bayou Crest Dr, Houston, TX 77063", "2215 Bayou Crest Dr, Houston, TX 77063; 880 Kirby Meadow Ln, Houston, TX 77098; 3150 Galveston Oaks Ct, Pasadena, TX 77504"]]
- After the gate (accept_field): [{"value": null, "reason": null, "needs_review": true}]
- Rules on the way: none changed it
- Final: None, address_check None, needs_review True

## SUB-092

### premises_address

- Gold: 9901 Industrial Park Rd, Laredo, TX 78045
- In the documents: application.pdf: Premises address 9901 Industrial Park Rd, Laredo, TX 78045; schedule.xlsx: 1	9901 Industrial Park Rd	Laredo	78045	7400000	Tilt-wall concrete	2009	182000	ESFR
- Model returned: [{"value": null, "source": "", "quote": ""}]; conflict sides [["9901 Industrial Park Rd, Laredo, TX 78045", "9901 Industrial Park Rd"]]
- After the gate (accept_field): [{"value": null, "reason": null, "needs_review": true}]; conflicts kept [["9901 Industrial Park Rd, Laredo, TX 78045", "9901 Industrial Park Rd"]]
- Rules on the way: none changed it
- Final: None, address_check None, needs_review True; open conflict [["9901 Industrial Park Rd, Laredo, TX 78045", "9901 Industrial Park Rd"]]

## SUB-098

### premises_address

- Gold: 4102 Mesquite Bend Rd, Lubbock, TX 79424
- In the documents: application.md: **Premises address:** 4102 Mesquite Bend Rd, Lubbock, TX 79424 (shop and yard)
- Model returned: [{"value": "4102 Mesquite Bend Rd, Lubbock, TX 79424 (shop and yard)", "source": "application.md", "quote": "4102 Mesquite Bend Rd, Lubbock, TX 79424 (shop and yard)"}]
- After the gate (accept_field): [{"value": "4102 Mesquite Bend Rd, Lubbock, TX 79424 (shop and yard)", "reason": null, "needs_review": false}]
- Rules on the way: none changed it
- Final: '4102 Mesquite Bend Rd, Lubbock, TX 79424 (shop and yard)', address_check 'ok', needs_review False

### named_insured

- Gold: Caprock Tile & Stone Inc
- In the documents: application.md: **Named insured (legal name):** Caprock Tile & Stone Inc; loss-runs.md: Named insured: Caprock Tile & Stone Inc
- Model returned: [{"value": null, "source": null, "quote": null}]; conflict sides [["Caprock Tile & Stone Inc", "Caprock Tile & Stone Inc", "Caprock Tile and Stone Inc"]]
- After the gate (accept_field): [{"value": null, "reason": null, "needs_review": true}]; conflicts kept [["Caprock Tile & Stone Inc", "Caprock Tile & Stone Inc", "Caprock Tile and Stone Inc"]]
- Rules on the way: none changed it
- Final: None, address_check None, needs_review True; open conflict [["Caprock Tile & Stone Inc", "Caprock Tile & Stone Inc", "Caprock Tile and Stone Inc"]]

### operations

- Gold: tile, stone and marble installation
- In the documents: application.md: **Operations:** Tile, stone and marble installation, residential and light commercial, subcontract labor used
- Model returned: [{"value": null, "source": null, "quote": null}]; conflict sides [["Tile, stone and marble installation, residential and light commercial, subcontract labor used", "Tile and stone install, we do residential and some light commercial."]]
- After the gate (accept_field): [{"value": null, "reason": null, "needs_review": true}]; conflicts kept [["Tile, stone and marble installation, residential and light commercial, subcontract labor used", "Tile and stone install, we do residential and some light commercial."]]
- Rules on the way: none changed it
- Final: None, address_check None, needs_review True; open conflict [["Tile, stone and marble installation, residential and light commercial, subcontract labor used", "Tile and stone install, we do residential and some light commercial."]]

## SUB-099

### premises_address

- Gold: 1800 Hewitt Dr, Waco, TX 76705
- In the documents: application.pdf: Premises address 1800 Hewitt Dr, Waco, TX 76705
- Model returned: [{"value": null, "source": "", "quote": ""}]; conflict sides [["1800 Hewitt Dr, Waco, TX 76705", "1800 Hewitt Dr"]]
- After the gate (accept_field): [{"value": null, "reason": null, "needs_review": true}]; conflicts kept [["1800 Hewitt Dr, Waco, TX 76705", "1800 Hewitt Dr"]]
- Rules on the way: none changed it
- Final: None, address_check None, needs_review True; open conflict [["1800 Hewitt Dr, Waco, TX 76705", "1800 Hewitt Dr"]]

## SUB-103

### premises_address

- Gold: 2950 Rose Hill Rd, Tyler, TX 75703
- In the documents: application.md: **Premises address:** 2950 Rose Hill Rd, Tyler, TX 75703; schedule.xlsx: 1	2950 Rose Hill Rd	Tyler	75703	780000	Metal	1997	22000	Partial, shop area only
- Model returned: [{"value": null, "source": "", "quote": ""}]; conflict sides [["2950 Rose Hill Rd, Tyler, TX 75703", "2950 Rose Hill Rd"]]
- After the gate (accept_field): [{"value": null, "reason": null, "needs_review": true}]; conflicts kept [["2950 Rose Hill Rd, Tyler, TX 75703", "2950 Rose Hill Rd"]]
- Rules on the way: none changed it
- Final: None, address_check None, needs_review True; open conflict [["2950 Rose Hill Rd, Tyler, TX 75703", "2950 Rose Hill Rd"]]

