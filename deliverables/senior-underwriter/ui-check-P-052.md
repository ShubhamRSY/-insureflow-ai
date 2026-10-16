# UI check P-052 / P-051 (D-098, D-065 item 3) — @senior-underwriter

Verdict: APPROVE (no High). Based on the three screenshots and the WHATS_NEW lines; code of confirm_html, _no_send_reason, _send_html not read.

Checked against D-098:
- Before confirm (SUB-990): form has senior picker, carrier, required reason, and says it sends nothing and a new run needs a new confirm. Send section shows red "No send: a senior referral needs a senior underwriter to confirm the market first." OK.
- After confirm: card shows who (UW-001 Dana Reyes, synthetic, senior), date, run hash 25d55c70, reason, and states the send still needs an approve and the typed line. Send section still blocked with a plain reason. OK.
- P-051 (SUB-991, pub beside an office): no form, plain red reason, suggested market "none". OK.
- WHATS_NEW lines for P-051 and P-052 present, dated, with D-098.

Medium / Low (backlog, one line each):
- Medium: "W1 word" and "D-057, D-060" in the refusal text are internal jargon; say "a prohibited class (bar, pub, lounge) is on the file; only a person outside this screen can handle it".
- Medium: after confirm, the send section says "Approve first ... (no logged decision by a listed underwriter)" but the approve form takes a free-typed "Underwriter id" with no hint of which ids count; add a hint or a picker.
- Low: the green confirm banner appears twice after confirm (top flash and card); keep the card only.
- Low: SUB-991 shows two near-identical red refusals (match line and Send section); keep one.
- Low: could not verify from the screenshot that the "Senior underwriter" picker lists only senior ids; confirm in code/test.
- Low: "Record decision" form stays visible on a prohibited file; harmless since no send, but a note would avoid confusion.
