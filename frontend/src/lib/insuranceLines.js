export const INSURANCE_LINE_NAMES = {
  commercial_property: 'Property & Business Interruption',
  property: 'Property & Business Interruption',
  general_liability: 'General Liability',
  business_owners_policy: 'Business Owners Policy (BOP)',
  umbrella: 'Commercial Umbrella',
  workers_comp: "Workers' Compensation",
  directors_and_officers: 'Directors & Officers (D&O)',
  do: 'Directors & Officers (D&O)',
  trade_credit: 'Trade Credit Insurance',
  errors_and_omissions: 'Errors & Omissions (E&O)',
  eo: 'Errors & Omissions (E&O)',
  key_person: 'Key Person Insurance',
  personal_homeowners: 'Personal Homeowners',
  personal_auto: 'Personal Auto',
  life: 'Life Insurance',
};

export function insuranceLineLabel(value) {
  if (!value) return '';
  const key = String(value).toLowerCase();
  return INSURANCE_LINE_NAMES[key] || String(value).replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}
