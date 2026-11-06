# T-082 / P-087 + P-088 (D-170): UI check (D-065 item 3), @senior-underwriter, 2026-11-06

Verdict: APPROVE. High findings: none.

Checked: cards screenshot, what's-new screenshot, HOUSING_NOTE, HOUSING_PROGRAM branch in _match, two 2026-11-05 WHATS_NEW lines.

Criteria
- Refusals have plain reasons: PASS. "No market confirm and no send from this screen: no saved run for SUB-55x; refusing to gate on nothing" and "Account-manager check: refused, the saved extraction run for this file cannot be read" appear on every card (synthetic, as stated). Hold reasons are plain ("housing program: sprinkler answer missing (P-088; AG:62)").
- Housing card never reads as a decline: PASS. Route is senior_referral, the note says "a senior underwriter must review... the housing program and its occupants are not a reason to decline", with AG:37/AG:62 cited and the facts that drive severity listed. Carrier C is "recommendation only; the underwriter decides".
- English/Spanish parity: PASS. SUB-550 (Student housing) and SUB-551 (Vivienda subsidiada) both give senior_referral, the same HOUSING_NOTE, Carrier C. Code uses one branch and one constant for both lists. SUB-552 (cantina beside restaurant) gives the bar/liquor referral, matching the English twin.
- What's new: PASS. One line each, date, task id, decision (2026-11-05 P-087 (T-082) D-170; P-088 (T-082) D-170). The P-088 line says "Not used in any pilot until real company compliance signs", which is the right caveat.

Medium / Low (backlog, one line each)
- M1: SUB-551 card appends "; no sprinklers" and SUB-550 does not; fixtures differ on sprinklers, so the screenshot alone does not prove parity. Code does (same branch). Add one same-sprinkler pair next time.
- M2: Note says "before any market is selected" yet the same card suggests Carrier C; reword to "a suggested market is shown only for the senior underwriter to confirm".
- M3: The sprinkler-missing hold reason does not repeat "not a reason to decline"; add the phrase so a hold is not read as a decline.
- L1: Card shows the raw code "carrier_c"; show "Carrier C".
- L2: P-088 What's-new line is long (4 lines); trim.
- L3: "R2/W2 win first" ordering is only in a code comment; fine for the UI.
