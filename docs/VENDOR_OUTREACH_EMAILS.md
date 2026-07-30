# Vendor sandbox outreach emails

Copy/adapt these when requesting sandbox credentials.

---

## LexisNexis — CLUE Commercial

**Subject:** Sandbox API access request — Rytera underwriting platform (CLUE)

Hello,

We are Rytera (ryterainc.com), an AI underwriting platform running a **shadow pilot** with [Carrier/MGA Name].

We need **sandbox / UAT** access to CLUE Commercial so our oracle agent can verify loss history without inventing clean results.

Please advise on:
1. Sandbox base URL and auth method (API key / OAuth)
2. Test FEINs / named insureds we can query
3. Rate limits and data retention terms
4. Timeline and commercial contact for production cutover

Technical contact: [you@rytera…]  
Security / DPA materials available on request.

Thank you.

---

## Verisk — A-PLUS Property

**Subject:** Sandbox API access — A-PLUS for Rytera commercial UW pilot

Hello,

Requesting **sandbox credentials** for A-PLUS property loss history for our multi-agent underwriting platform (Rytera).

We will call your REST API from our integration gateway with:
- Named insured + property address + tax ID
- Years-back typically 5–7

Please send sandbox URL, API key issuance process, and sample request/response docs.

---

## Guidewire / PAS UAT

**Subject:** UAT PolicyCenter REST access for Rytera shadow-to-bind pilot

Hello,

We need a **UAT** Guidewire PolicyCenter (or Duck Creek / BriteCore) endpoint to:
1. Submit quote jobs from AI-indicated premiums
2. Bind only after licensed UW sign-off in Rytera (or keep bind in your PAS during shadow)

Please share UAT base URL, auth, and sample `/jobs` + `/policies/bind` contracts.

Until then we remain in **shadow mode** (analyze + UW review; bind disabled).
