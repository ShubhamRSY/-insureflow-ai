import { useState, useMemo } from 'react';
import {
  FileText, MapPin, CheckCircle2, AlertTriangle, XCircle, Eye,
  ChevronDown, ChevronRight, ExternalLink, Copy, Search,
} from 'lucide-react';
import { asBBox, asList, displayText, safeLower } from '../lib/safe';

const VERIFICATION_COLORS = {
  verified: { bg: 'bg-emerald-500/10', text: 'text-emerald-400', border: 'border-emerald-500/20', icon: CheckCircle2 },
  contradicted: { bg: 'bg-red-500/10', text: 'text-red-400', border: 'border-red-500/20', icon: XCircle },
  partially_verified: { bg: 'bg-amber-500/10', text: 'text-amber-400', border: 'border-amber-500/20', icon: AlertTriangle },
  ambiguous: { bg: 'bg-sky-500/10', text: 'text-sky-400', border: 'border-sky-500/20', icon: AlertTriangle },
  unverified: { bg: 'bg-slate-500/10', text: 'text-slate-400', border: 'border-slate-500/20', icon: Eye },
};

const CRITICAL_FIELDS = new Set([
  'premium', 'adjusted_premium', 'estimated_premium', 'total_premium',
  'limit', 'deductible', 'coverage_limit', 'sublimit',
  'payroll', 'total_insured_value', 'tiv', 'revenue',
  'loss_history', 'loss_runs', 'experience_mod',
]);

function nodeCount(nodes) {
  if (Array.isArray(nodes)) return nodes.length;
  if (nodes && typeof nodes === 'object') return Object.keys(nodes).length;
  const n = Number(nodes);
  return Number.isFinite(n) ? n : 0;
}

function CopyButton({ text }) {
  const [copied, setCopied] = useState(false);
  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch { /* ignore */ }
  };
  return (
    <button
      type="button"
      onClick={handleCopy}
      className="p-0.5 rounded hover:bg-white/10 transition-colors"
      title="Copy value"
    >
      <Copy size={10} className={copied ? 'text-emerald-400' : 'text-slate-600'} />
    </button>
  );
}

function SourceBadge({ pageNumber, bbox, sourceRef, sourceText, extractionMethod }) {
  if (!pageNumber && !sourceRef && !sourceText) {
    return (
      <span className="inline-flex items-center gap-1 text-[10px] px-1.5 py-0.5 rounded bg-slate-700/50 text-slate-500">
        No source
      </span>
    );
  }

  return (
    <div className="flex items-center gap-1.5 flex-wrap">
      {pageNumber != null && (
        <button
          type="button"
          className="inline-flex items-center gap-1 text-[10px] px-1.5 py-0.5 rounded bg-sky-500/10 text-sky-300 border border-sky-500/20 hover:bg-sky-500/20 transition-colors"
          title={asBBox(bbox) ? `Page ${pageNumber}, region [${asBBox(bbox).map((b) => b.toFixed(2)).join(', ')}]` : `Page ${pageNumber}`}
        >
          <FileText size={9} />
          p. {pageNumber}
          {bbox && <MapPin size={8} className="opacity-60" />}
        </button>
      )}
      {extractionMethod && (
        <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-700/50 text-slate-400 uppercase">
          {displayText(extractionMethod)}
        </span>
      )}
    </div>
  );
}

function FieldRow({ field, isExpanded, onToggle, onJumpToPage }) {
  const fieldName = displayText(field.field_name || field.name);
  const value = field.value ?? '';
  const confidence = field.confidence;
  const pageNumber = field.page_number;
  const bbox = field.bbox;
  const sourceRef = field.source_ref || '';
  const context = field.context || '';
  const extractionMethod = field.extraction_method || '';
  const verificationStatus = displayText(field.verification_status);
  const sourceText = field.source_text || '';
  const isCritical = CRITICAL_FIELDS.has(safeLower(fieldName));

  const vStyle = VERIFICATION_COLORS[verificationStatus] || VERIFICATION_COLORS.unverified;
  const VIcon = vStyle.icon;

  return (
    <div className={`border rounded-lg transition-all ${vStyle.border} ${isExpanded ? vStyle.bg : 'bg-transparent hover:bg-slate-800/30'}`}>
      <button
        type="button"
        onClick={onToggle}
        className="w-full text-left px-3 py-2 flex items-center gap-2"
      >
        {isExpanded ? <ChevronDown size={12} className="text-slate-500 shrink-0" /> : <ChevronRight size={12} className="text-slate-500 shrink-0" />}

        <span className="text-xs text-slate-400 w-36 shrink-0 truncate" title={fieldName}>
          {fieldName}
          {isCritical && <span className="text-red-400 ml-1">*</span>}
        </span>

        <span className="text-sm font-mono text-white flex-1 truncate">
          {displayText(value)}
        </span>

        <CopyButton text={displayText(value)} />

        {confidence != null && (
          <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded ${
            confidence >= 0.9 ? 'text-emerald-400 bg-emerald-500/10' :
            confidence >= 0.7 ? 'text-amber-400 bg-amber-500/10' :
            'text-red-400 bg-red-500/10'
          }`}>
            {(confidence * 100).toFixed(0)}%
          </span>
        )}

        {verificationStatus && (
          <span className={`inline-flex items-center gap-1 text-[10px] px-1.5 py-0.5 rounded ${vStyle.bg} ${vStyle.text}`}>
            <VIcon size={9} />
            {verificationStatus.replace(/_/g, ' ')}
          </span>
        )}

        {pageNumber != null && (
          <button
            type="button"
            onClick={(e) => { e.stopPropagation(); onJumpToPage(pageNumber, bbox); }}
            className="p-1 rounded hover:bg-white/10 transition-colors"
            title={`Jump to page ${pageNumber}`}
          >
            <ExternalLink size={11} className="text-sky-400" />
          </button>
        )}
      </button>

      {isExpanded && (
        <div className="px-3 pb-2.5 space-y-1.5 ml-5">
          <div className="flex items-center gap-2">
            <SourceBadge
              pageNumber={pageNumber}
              bbox={bbox}
              sourceRef={sourceRef}
              sourceText={sourceText}
              extractionMethod={extractionMethod}
            />
          </div>

          {sourceText && (
            <div className="rounded bg-black/30 px-2.5 py-1.5 text-[11px] text-slate-300 italic border-l-2 border-sky-500/30">
              "{displayText(sourceText)}"
            </div>
          )}

          {context && (
            <p className="text-[10px] text-slate-500">
              Source: {displayText(context)}
            </p>
          )}

          {sourceRef && (
            <p className="text-[10px] text-slate-600 font-mono">
              {sourceRef}
            </p>
          )}

          {asBBox(bbox) && (
            <p className="text-[10px] text-slate-600 font-mono">
              Bbox: [{asBBox(bbox).map((b) => b.toFixed(3)).join(', ')}]
            </p>
          )}
        </div>
      )}
    </div>
  );
}

function ProvenanceGroup({ title, fields, icon: Icon, color, onJumpToPage }) {
  const [expanded, setExpanded] = useState(false);
  const [expandedField, setExpandedField] = useState(null);

  if (!fields || fields.length === 0) return null;

  return (
    <div className="space-y-1.5">
      <button
        type="button"
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-2 w-full text-left group"
      >
        {expanded ? <ChevronDown size={14} className="text-slate-500" /> : <ChevronRight size={14} className="text-slate-500" />}
        <Icon size={14} className={color} />
        <span className="text-sm font-medium text-slate-300">{title}</span>
        <span className="text-[10px] text-slate-500 ml-1">({fields.length})</span>
        <div className="flex-1" />
        <div className="flex items-center gap-1">
          {fields.filter((f) => f.page_number).length > 0 && (
            <span className="text-[10px] text-sky-400 bg-sky-500/10 px-1.5 py-0.5 rounded">
              {fields.filter((f) => f.page_number).length} cited
            </span>
          )}
          {fields.filter((f) => f.verification_status === 'contradicted').length > 0 && (
            <span className="text-[10px] text-red-400 bg-red-500/10 px-1.5 py-0.5 rounded">
              {fields.filter((f) => f.verification_status === 'contradicted').length} conflicts
            </span>
          )}
        </div>
      </button>

      {expanded && (
        <div className="space-y-1 ml-4">
          {fields.map((field, i) => {
            const key = `${field.field_name || i}`;
            return (
              <FieldRow
                key={key}
                field={field}
                isExpanded={expandedField === key}
                onToggle={() => setExpandedField(expandedField === key ? null : key)}
                onJumpToPage={onJumpToPage}
              />
            );
          })}
        </div>
      )}
    </div>
  );
}

export default function ProvenancePanel({ job, onJumpToPage }) {
  const [searchQuery, setSearchQuery] = useState('');
  const [showAll, setShowAll] = useState(false);

  const results = job?.results || {};
  const memo = results.memo || {};
  const extractedFields = (results.extracted_fields && typeof results.extracted_fields === 'object')
    ? results.extracted_fields
    : {};
  const provenance = results.provenance || {};
  const verification = results.verification || {};
  const citationIssues = asList(verification.citation_issues);

  const allFields = useMemo(() => {
    const fields = [];

    Object.entries(extractedFields).forEach(([key, val]) => {
      if (val && typeof val === 'object' && !Array.isArray(val)) {
        fields.push({
          field_name: key,
          value: val.value ?? val,
          confidence: val.confidence,
          page_number: val.page_number,
          bbox: val.bbox,
          source_ref: val.source_ref,
          context: val.context,
          extraction_method: val.extraction_method,
          verification_status: val.verification_status,
          source_text: val.source_text,
          group: 'extracted',
        });
      } else if (val !== null && val !== undefined) {
        fields.push({
          field_name: key,
          value: val,
          group: 'extracted',
        });
      }
    });

    if (Array.isArray(memo.findings)) {
      memo.findings.forEach((f, i) => {
        fields.push({
          field_name: f.field_path || `finding_${i}`,
          value: f.recommended_value || f.source_value || f.description || '',
          confidence: f.confidence,
          context: f.evidence?.join(' | ') || '',
          group: 'findings',
          verification_status: f.verification_status,
        });
      });
    }

    return fields;
  }, [extractedFields, memo]);

  const filteredFields = useMemo(() => {
    if (!searchQuery) return allFields;
    const q = searchQuery.toLowerCase();
    return allFields.filter((f) =>
      safeLower(f.field_name).includes(q) ||
      displayText(f.value).toLowerCase().includes(q)
    );
  }, [allFields, searchQuery]);

  const groupedFields = useMemo(() => {
    const groups = {
      critical: [],
      financial: [],
      coverage: [],
      party: [],
      compliance: [],
      other: [],
    };

    filteredFields.forEach((f) => {
      const name = safeLower(f.field_name);
      if (CRITICAL_FIELDS.has(name)) {
        groups.critical.push(f);
      } else if (name.includes('premium') || name.includes('rate') || name.includes('cost') || name.includes('fee') || name.includes('tax')) {
        groups.financial.push(f);
      } else if (name.includes('coverage') || name.includes('limit') || name.includes('deductible') || name.includes('exclusion')) {
        groups.coverage.push(f);
      } else if (name.includes('insured') || name.includes('applicant') || name.includes('producer') || name.includes('carrier')) {
        groups.party.push(f);
      } else if (name.includes('compliance') || name.includes('regulatory') || name.includes('state_fund') || name.includes('diligent')) {
        groups.compliance.push(f);
      } else {
        groups.other.push(f);
      }
    });

    return groups;
  }, [filteredFields]);

  const citationCount = allFields.filter((f) => f.page_number).length;
  const verifiedCount = allFields.filter((f) => f.verification_status === 'verified').length;
  const conflictCount = allFields.filter((f) => f.verification_status === 'contradicted').length;

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <MapPin size={16} className="text-brand" />
          <h3 className="text-sm font-semibold text-white">Source Provenance</h3>
        </div>
        <div className="flex items-center gap-2 text-[10px]">
          <span className="text-sky-400 bg-sky-500/10 px-2 py-0.5 rounded">{citationCount} cited</span>
          <span className="text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded">{verifiedCount} verified</span>
          {conflictCount > 0 && (
            <span className="text-red-400 bg-red-500/10 px-2 py-0.5 rounded">{conflictCount} conflicts</span>
          )}
        </div>
      </div>

      {/* Search */}
      <div className="relative">
        <Search size={12} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-500" />
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Search fields..."
          className="w-full pl-7 pr-3 py-1.5 rounded-lg bg-slate-800/50 border border-slate-700/50 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-brand/50"
        />
      </div>

      {/* Citation issues */}
      {citationIssues.length > 0 && (
        <div className="rounded-lg bg-red-500/5 border border-red-500/20 p-3">
          <p className="text-xs font-medium text-red-400 mb-1.5 flex items-center gap-1.5">
            <AlertTriangle size={12} />
            {citationIssues.length} citation issue(s) detected
          </p>
          {citationIssues.slice(0, 5).map((issue, i) => (
            <div key={i} className="text-[10px] text-red-300/70 ml-5">
              {displayText(issue.message || `${displayText(issue.field_name)}: ${displayText(issue.code)}`)}
              {issue.page_number && <span className="text-sky-400 ml-1">(p. {issue.page_number})</span>}
            </div>
          ))}
        </div>
      )}

      {/* Provenance record summary */}
      {provenance.record_id && (
        <div className="rounded-lg bg-slate-800/30 border border-slate-700/30 p-2.5 text-[10px] text-slate-500 font-mono">
          Record: {displayText(provenance.record_id)} · {nodeCount(provenance.nodes)} nodes
        </div>
      )}

      {/* Field groups */}
      <div className="space-y-3">
        <ProvenanceGroup
          title="Critical Financial Fields"
          fields={groupedFields.critical}
          icon={AlertTriangle}
          color="text-red-400"
          onJumpToPage={onJumpToPage}
        />
        <ProvenanceGroup
          title="Financial"
          fields={groupedFields.financial}
          icon={FileText}
          color="text-amber-400"
          onJumpToPage={onJumpToPage}
        />
        <ProvenanceGroup
          title="Coverage"
          fields={groupedFields.coverage}
          icon={FileText}
          color="text-sky-400"
          onJumpToPage={onJumpToPage}
        />
        <ProvenanceGroup
          title="Parties"
          fields={groupedFields.party}
          icon={FileText}
          color="text-violet-400"
          onJumpToPage={onJumpToPage}
        />
        <ProvenanceGroup
          title="Compliance"
          fields={groupedFields.compliance}
          icon={CheckCircle2}
          color="text-emerald-400"
          onJumpToPage={onJumpToPage}
        />
        <ProvenanceGroup
          title="Other Fields"
          fields={groupedFields.other}
          icon={FileText}
          color="text-slate-400"
          onJumpToPage={onJumpToPage}
        />
      </div>

      {allFields.length === 0 && (
        <div className="text-center py-8 text-slate-500">
          <MapPin size={24} className="mx-auto mb-2 opacity-50" />
          <p className="text-xs">No extracted fields with provenance data</p>
        </div>
      )}
    </div>
  );
}
