/** Short hover explanations for controls across the dashboard. */
export const UI_HINTS = {
  llmExtraction:
    'Uses AI to read PDFs and scans, extract fields, and classify document types. Off = faster rule-based parsing only.',
  blockIrrelevant:
    'Blocks the run when files look unrelated to underwriting (e.g. personal photos). Irrelevant files are removed before the pipeline starts.',
  lineOfBusiness:
    'Tags the submission with the correct product so checklist, triage, and rating use the right rules.',
  commercialCategory:
    'Top-level commercial line (Property, Liability, Workforce, etc.). Pick the section that matches the submission.',
  commercialProduct:
    'Specific insurance product within the category — drives checklist, LOB-scoped ML, and rating path.',
  commercialCoverage:
    'Coverage part within the product (e.g. Building, BPP) so triage and memo are not misaligned with the request.',
  insuranceCompany:
    'Pick the writing company this file is for — your appointed panel. Rytera does not invent a market appointment. Rating still uses the loaded rate book.',
  uwValidatePremium:
    'Your indicated annual premium after UW judgment. Saved separately from AI output for override tracking.',
  uwValidateLimit:
    'Policy limit you are willing to bind. Must align with submission SOV / application limits.',
  uwValidateDeductible:
    'Retention you require on this risk. Affects indicated rate and conditions.',
  runPipeline:
    'Runs intake → parse → verify → score → price → UW memo for the uploaded package.',
  runSample:
    'Runs a built-in demo package through the full pipeline — no upload needed.',
  tabFiles: 'Upload broker PDFs, ACORD, loss runs, and other documents from your computer.',
  tabConnect: 'Pull documents from connected sources (email, storage, demo folders) into a draft bundle.',
  tabSample: 'Run a pre-loaded demo case for the selected product line.',
  removeIrrelevant: 'Remove files flagged as unrelated to underwriting before you run.',
  clearFiles: 'Remove all uploaded files from the list.',
  splitFolders: 'Treat each top-level folder as a separate borrower when importing a directory.',
  complexSubmission: 'Flags manuscript or unusual risks that may need staff UW review or custom forms.',
  requiresCoSign: 'Requires a second licensed underwriter to co-sign before bind on this authority rule.',
  connectPullAll: 'Pull demo or configured documents from every source in this category into one bundle.',
};
