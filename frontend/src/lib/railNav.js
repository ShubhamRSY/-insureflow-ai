import { INSURANCE_NAV_CHILDREN } from './insuranceSections';

export const RAIL_GROUPS = [
  {
    id: 'home',
    label: 'Home',
    items: [
      { to: '/', label: 'Overview' },
      { to: '/system', label: 'System health' },
    ],
  },
  {
    id: 'insurance',
    label: 'Insurance',
    scrollItems: true,
    items: INSURANCE_NAV_CHILDREN,
  },
  {
    id: 'reference',
    label: 'Reference',
    items: [{ to: '/reference/commercial', label: 'Commercial insurance' }],
  },
  {
    id: 'mortgage-lending',
    label: 'Mortgage & lending',
    items: [
      { to: '/mortgage', label: 'Mortgage', tag: 'Live' },
      { to: '/lending', label: 'Lending', tag: 'Live' },
    ],
  },
  {
    id: 'uw-operations',
    label: 'UW operations',
    items: [
      { to: '/uw-workbench', label: 'UW workbench' },
      { to: '/uw-dashboard', label: 'UW dashboard' },
      { to: '/workflow', label: 'UW sign-off' },
      { to: '/queue', label: 'Queue', badge: true },
      { to: '/line-uw', label: 'Line UW desk' },
      { to: '/staff-uw', label: 'Staff UW desk' },
      { to: '/prior-decisions', label: 'Prior decisions' },
    ],
  },
  {
    id: 'post-decision',
    label: 'Post-decision',
    items: [
      { to: '/issuance', label: 'Issuance' },
      { to: '/monitoring', label: 'Policy monitoring' },
      { to: '/producer-comms', label: 'Producer comms' },
    ],
  },
  {
    id: 'analytics',
    label: 'Analytics',
    items: [
      { to: '/renewals', label: 'Renewals' },
      { to: '/overrides', label: 'Override analytics' },
      { to: '/business-kpis', label: 'ROI & KPIs' },
      { to: '/eval-trends', label: 'Eval trends' },
      { to: '/portfolio', label: 'Portfolio' },
      { to: '/authority', label: 'Authority matrix' },
      { to: '/market', label: 'Market cycle' },
    ],
  },
  {
    id: 'governance',
    label: 'Governance',
    items: [
      { to: '/pilot', label: 'Pilot lab' },
      { to: '/registry', label: 'Model registry' },
      { to: '/regulatory-review', label: 'Regulatory review' },
      { to: '/webhooks', label: 'Webhooks' },
    ],
  },
  {
    id: 'integrations',
    label: 'Integrations',
    scrollItems: true,
    items: [
      { to: '/integrations/google-drive', label: 'Google Drive' },
      { to: '/integrations/sharepoint', label: 'SharePoint / OneDrive' },
      { to: '/integrations/s3-bucket', label: 'AWS S3' },
      { to: '/integrations/azure-blob', label: 'Azure Blob Storage' },
      { to: '/integrations/box', label: 'Box Enterprise' },
      { to: '/integrations/email-inbox', label: 'Email inbox' },
      { to: '/integrations/outlook-inbox', label: 'Outlook / Microsoft 365' },
      { to: '/integrations/server-folder', label: 'Server directory' },
      { to: '/integrations/sftp', label: 'SFTP / broker portal' },
      { to: '/integrations/ivans-download', label: 'IVANS download' },
      { to: '/integrations/acord-al3', label: 'ACORD AL3 / XML hub' },
      { to: '/integrations/guidewire-policycenter', label: 'Guidewire PolicyCenter' },
      { to: '/integrations/duck-creek', label: 'Duck Creek policy' },
      { to: '/integrations/majesco-policy', label: 'Majesco policy' },
      { to: '/integrations/applied-epic', label: 'Applied Epic (Vertafore)' },
      { to: '/integrations/hawksoft', label: 'HawkSoft AMS' },
      { to: '/integrations/salesforce-crm', label: 'Salesforce' },
      { to: '/integrations/verisk-iso', label: 'Verisk / ISO' },
      { to: '/integrations/corelogic', label: 'CoreLogic / Cotality' },
      { to: '/integrations/bold-penguin', label: 'Bold Penguin' },
      { to: '/integrations/docusign', label: 'DocuSign' },
      { to: '/integrations/microsoft-teams', label: 'Microsoft Teams' },
      { to: '/integrations/slack-intake', label: 'Slack' },
      { to: '/integrations/snowflake', label: 'Snowflake' },
    ],
  },
  {
    id: 'account',
    label: 'Account',
    items: [
      { to: '/ratemaking', label: 'Ratemaking & pricing' },
      { to: '/settings', label: 'Settings' },
    ],
  },
];

export function deriveActiveGroupId(pathname, groups = RAIL_GROUPS) {
  let bestId = 'home';
  let bestLength = -1;
  groups.forEach((group) => {
    group.items.forEach((item) => {
      const isRoot = item.to === '/';
      const matches = isRoot ? pathname === '/' : pathname.startsWith(item.to);
      if (matches && item.to.length > bestLength) {
        bestLength = item.to.length;
        bestId = group.id;
      }
    });
  });
  return bestId;
}
