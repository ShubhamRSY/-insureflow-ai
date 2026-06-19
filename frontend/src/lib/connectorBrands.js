/** Brand marks for insurance connector tiles (Simple Icons CDN + fallbacks). */

export const CATEGORY_SECTIONS = [
  {
    id: 'Demo Packages',
    title: 'Sample submissions',
    subtitle: 'Pre-loaded broker packages for testing',
    icon: 'package',
  },
  {
    id: 'Document Storage',
    title: 'Cloud & document storage',
    subtitle: 'Pull ACORD, loss runs, and SOV from your file platforms',
    icon: 'cloud',
  },
  {
    id: 'Submission Intake',
    title: 'Submission intake',
    subtitle: 'Email, SFTP, and broker portal feeds',
    icon: 'inbox',
  },
  {
    id: 'Industry Exchange',
    title: 'Industry exchange',
    subtitle: 'IVANS, ACORD AL3, and carrier message hubs',
    icon: 'exchange',
  },
  {
    id: 'Policy Admin',
    title: 'Policy administration',
    subtitle: 'Guidewire, Duck Creek, Majesco policy systems',
    icon: 'policy',
  },
  {
    id: 'Agency Management',
    title: 'Agency management',
    subtitle: 'Applied Epic, HawkSoft, and wholesale AMS',
    icon: 'agency',
  },
  {
    id: 'CRM / Distribution',
    title: 'CRM & distribution',
    subtitle: 'Salesforce broker opportunities and distribution CRM',
    icon: 'crm',
  },
  {
    id: 'Rating & Loss Data',
    title: 'Rating & loss data',
    subtitle: 'Verisk ISO, CoreLogic property analytics',
    icon: 'data',
  },
  {
    id: 'eSignature',
    title: 'eSignature',
    subtitle: 'Signed applications and broker attestations',
    icon: 'signature',
  },
  {
    id: 'Collaboration',
    title: 'Collaboration',
    subtitle: 'Teams and Slack UW intake channels',
    icon: 'messaging',
  },
  {
    id: 'Data Warehouse',
    title: 'Data warehouse',
    subtitle: 'Historical loss and exposure from Snowflake',
    icon: 'warehouse',
  },
];

export const CONNECTOR_BRANDS = {
  'pacific-coast': { initials: 'PC', color: '0ea5e9', bg: '0369a1' },
  northwind: { initials: 'NW', color: '38bdf8', bg: '1d4ed8' },
  'server-folder': { initials: 'FS', color: '94a3b8', bg: '334155' },
  'google-drive': { slug: 'googledrive', color: '4285F4' },
  sharepoint: { slug: 'microsoftsharepoint', color: '0078D4' },
  's3-bucket': { slug: 'amazonaws', color: 'FF9900' },
  'azure-blob': { slug: 'microsoftazure', color: '0078D4' },
  box: { slug: 'box', color: '0061D5' },
  'email-inbox': { slug: 'gmail', color: 'EA4335' },
  sftp: { slug: 'openssh', color: 'FFFFFF' },
  'ivans-download': { initials: 'IV', color: 'FFFFFF', bg: '1e40af' },
  'acord-al3': { initials: 'AC', color: 'FFFFFF', bg: 'b45309' },
  'guidewire-policycenter': { initials: 'GW', color: 'FFFFFF', bg: '003366' },
  'duck-creek': { initials: 'DC', color: 'FFFFFF', bg: '059669' },
  'majesco-policy': { initials: 'MJ', color: 'FFFFFF', bg: '7c3aed' },
  'applied-epic': { initials: 'EP', color: 'FFFFFF', bg: 'dc2626' },
  hawksoft: { initials: 'HS', color: 'FFFFFF', bg: '0891b2' },
  'salesforce-crm': { slug: 'salesforce', color: '00A1E0' },
  'verisk-iso': { initials: 'VR', color: 'FFFFFF', bg: '991b1b' },
  corelogic: { initials: 'CL', color: 'FFFFFF', bg: '4338ca' },
  docusign: { slug: 'docusign', color: 'FFCC22' },
  'microsoft-teams': { slug: 'microsoftteams', color: '6264A7' },
  'slack-intake': { slug: 'slack', color: 'FFFFFF' },
  snowflake: { slug: 'snowflake', color: '29B5E8' },
};

export function groupSourcesByCategory(sources) {
  const map = new Map();
  for (const src of sources || []) {
    const cat = src.category || 'Other';
    if (!map.has(cat)) map.set(cat, []);
    map.get(cat).push(src);
  }
  const ordered = [];
  for (const section of CATEGORY_SECTIONS) {
    const items = map.get(section.id);
    if (items?.length) ordered.push({ ...section, sources: items });
    map.delete(section.id);
  }
  for (const [id, items] of map.entries()) {
    ordered.push({ id, title: id, subtitle: '', icon: 'cloud', sources: items });
  }
  return ordered;
}
