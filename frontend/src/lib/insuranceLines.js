export const INSURANCE_LINE_NAMES = {
  // Property
  commercial_property: 'Commercial Property Insurance',
  property: 'Commercial Property Insurance',
  business_interruption: 'Business Interruption (Business Income) Insurance',
  builders_risk: "Builder's Risk Insurance",
  inland_marine: 'Inland Marine Insurance',
  ocean_marine: 'Ocean Marine Insurance',
  equipment_breakdown: 'Equipment Breakdown (Boiler & Machinery) Insurance',
  flood_commercial: 'Flood Insurance (Commercial)',
  earthquake_commercial: 'Earthquake Insurance (Commercial)',
  crime: 'Crime Insurance',
  // Liability
  general_liability: 'General Liability (CGL)',
  product_liability: 'Product Liability Insurance',
  errors_and_omissions: 'Professional Liability / E&O',
  eo: 'Professional Liability / E&O',
  directors_and_officers: 'Directors & Officers (D&O) Liability',
  do: 'Directors & Officers (D&O) Liability',
  epli: 'Employment Practices Liability (EPLI)',
  fiduciary_liability: 'Fiduciary Liability Insurance',
  cyber_liability: 'Cyber Liability Insurance',
  umbrella: 'Umbrella / Excess Liability Insurance',
  pollution_liability: 'Pollution / Environmental Liability',
  liquor_liability: 'Liquor Liability Insurance',
  media_liability: 'Media Liability Insurance',
  // Workforce
  workers_comp: "Workers' Compensation Insurance",
  employers_liability: "Employer's Liability Insurance",
  group_health: 'Group Health Insurance',
  group_life: 'Group Life Insurance',
  group_disability: 'Group Disability Insurance',
  key_person: 'Key Person Insurance',
  business_overhead_expense: 'Business Overhead Expense Insurance',
  voluntary_benefits: 'Voluntary / Supplemental Benefits',
  // Auto
  commercial_auto: 'Commercial Auto Insurance',
  fleet: 'Fleet Insurance',
  hnoa: 'Hired & Non-Owned Auto (HNOA)',
  motor_truck_cargo: 'Motor Truck Cargo Insurance',
  garage_liability: 'Garage Liability Insurance',
  // Financial
  trade_credit: 'Trade Credit Insurance',
  surety_bonds: 'Surety Bonds',
  political_risk: 'Political Risk Insurance',
  // Specialty
  tech_eo_cyber: 'Technology E&O / Cyber (Industry-Specific)',
  construction: "Construction / Contractor's Insurance",
  aviation: 'Aviation Insurance',
  event_insurance: 'Event Insurance',
  intellectual_property: 'Intellectual Property Insurance',
  kidnap_ransom: 'Kidnap & Ransom (K&R) Insurance',
  terrorism: 'Terrorism Insurance',
  product_recall: 'Product Recall Insurance',
  supply_chain: 'Supply Chain Insurance',
  // Package
  business_owners_policy: "Business Owner's Policy (BOP)",
  commercial_package: 'Commercial Package Policy (CPP)',
  // Personal
  personal_homeowners: 'Personal Homeowners',
  personal_auto: 'Personal Auto',
  life: 'Life Insurance',
};

export function insuranceLineLabel(value) {
  if (!value) return '';
  const key = String(value).toLowerCase();
  return INSURANCE_LINE_NAMES[key] || String(value).replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}
