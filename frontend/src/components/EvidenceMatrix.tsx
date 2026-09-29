'use client';
import React, { useState, useRef, useMemo, useEffect } from 'react';
import { Upload, FileText, CheckCircle2, XCircle, Clock, Loader2, Search, Link2 } from 'lucide-react';
import { uploadDisclosureCheck, getEvidenceGaps } from '../lib/api';import { GlassCard } from './ui/GlassCard';
import { Badge } from './ui/Badge';
import { Button } from './ui/Button';
import { InnovationPassport } from '../types';
import { useLang } from '../lib/LangContext';
import { t } from '../lib/i18n';

interface EvidenceRow {
  id: string;
  claim: string;
  evidenceType: string;
  status: 'GREEN' | 'YELLOW' | 'RED';
  sourceReference?: string;
  claimKey?: string;
  typeKey?: string;
}

interface EvidenceMatrixProps {
  initialRows?: EvidenceRow[];
  onStatusUpdate?: (itemId: string, status: string) => void;
  passportId?: string;
  passport?: InnovationPassport | null;
}

const DEFAULT_ROWS: EvidenceRow[] = [
  { id: 'ev-1', claim: '', claimKey: 'ev_demo_claim_1', evidenceType: '', typeKey: 'ev_demo_type_1', status: 'YELLOW' },
  { id: 'ev-2', claim: '', claimKey: 'ev_demo_claim_2', evidenceType: '', typeKey: 'ev_demo_type_2', status: 'RED' },
  { id: 'ev-3', claim: '', claimKey: 'ev_demo_claim_3', evidenceType: '', typeKey: 'ev_demo_type_3', status: 'GREEN' },
  { id: 'ev-4', claim: '', claimKey: 'ev_demo_claim_4', evidenceType: '', typeKey: 'ev_demo_type_4', status: 'YELLOW' },
  { id: 'ev-5', claim: '', claimKey: 'ev_demo_claim_5', evidenceType: '', typeKey: 'ev_demo_type_5', status: 'GREEN' },
];

const STATUS_UI: Record<string, { label: string; filter: string; bg: string; border: string; dot: string; text: string; icon: React.ReactNode }> = {
  GREEN: { label: 'ev_status_verified', filter: 'ev_filter_strong', bg: 'bg-emerald-100', border: 'border-emerald-300', dot: 'bg-emerald-500', text: 'text-emerald-700', icon: <CheckCircle2 className="w-3.5 h-3.5" /> },
  YELLOW: { label: 'ev_status_in_progress', filter: 'ev_filter_moderate', bg: 'bg-amber-100', border: 'border-amber-300', dot: 'bg-amber-500', text: 'text-amber-700', icon: <Clock className="w-3.5 h-3.5" /> },
  RED: { label: 'ev_status_missing', filter: 'ev_status_missing', bg: 'bg-red-100', border: 'border-red-300', dot: 'bg-red-500', text: 'text-red-700', icon: <XCircle className="w-3.5 h-3.5" /> },
};

type FilterKey = 'ALL' | 'GREEN' | 'YELLOW' | 'RED';

export default function EvidenceMatrix({ initialRows, onStatusUpdate, passportId, passport }: EvidenceMatrixProps) {
  const { lang } = useLang();
  const rowText = (r: EvidenceRow) => ({
    claim: r.claimKey ? t(r.claimKey, lang) : r.claim,
    type: r.typeKey ? t(r.typeKey, lang) : r.evidenceType,
  });
  const [rows, setRows] = useState<EvidenceRow[]>(initialRows || DEFAULT_ROWS);
  const [filter, setFilter] = useState<FilterKey>('ALL');
  const [search, setSearch] = useState('');
  const [uploadingId, setUploadingId] = useState<string | null>(null);
  const [uploadResult, setUploadResult] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const [passportRowsLoading, setPassportRowsLoading] = useState(false);
  const [linkedError, setLinkedError] = useState('');
  const fileInputRef = useRef<HTMLInputElement>(null);
  const pendingUploadId = useRef<string | null>(null);

  const statusFromEvidence = (s: string): EvidenceRow['status'] => {
    const k = (s || '').toLowerCase();
    if (k.includes('accepted')) return 'GREEN';
    if (k.includes('missing')) return 'RED';
    return 'YELLOW';
  };

  useEffect(() => {
    if (!passportId || !passport) {
      setRows(initialRows || DEFAULT_ROWS);
      setLinkedError('');
      return;
    }
    let active = true;
    setPassportRowsLoading(true);
    setLinkedError('');
    (async () => {
      try {
        const gapSummary = await getEvidenceGaps(passportId);
        if (!active) return;
        const claimRows: EvidenceRow[] = (passport.proposed_claims || []).map((c, i) => ({
          id: `claim-${i + 1}`,
          claim: c,
          evidenceType: '',
          typeKey: 'ev_type_passport_claim',
          status: 'YELLOW',
        }));
        const gapRows: EvidenceRow[] = (gapSummary.items || []).map((item) => ({
          id: item.id,
          claim: item.requirement_name || '',
          claimKey: item.requirement_name ? undefined : 'ev_type_regulatory_req',
          evidenceType: [item.expected_evidence_type, item.jurisdiction].filter(Boolean).join(' · '),
          status: statusFromEvidence(item.status),
        }));
        const merged = [...claimRows, ...gapRows];
        setRows(merged.length > 0 ? merged : DEFAULT_ROWS);
      } catch (e: any) {
        if (active) {
          setLinkedError(e.message || t('ev_sync_failed', lang));
          setRows(DEFAULT_ROWS);
        }
      } finally {
        if (active) setPassportRowsLoading(false);
      }
    })();
    return () => { active = false; };
  }, [passportId, passport, initialRows]);

  const counts = useMemo(() => ({
    ALL: rows.length,
    GREEN: rows.filter((r) => r.status === 'GREEN').length,
    YELLOW: rows.filter((r) => r.status === 'YELLOW').length,
    RED: rows.filter((r) => r.status === 'RED').length,
  }), [rows]);

  const filteredRows = rows.filter((row) => {
    if (filter !== 'ALL' && row.status !== filter) return false;
    if (search) {
      const txt = rowText(row);
      const hay = `${txt.claim} ${txt.type}`.toLowerCase();
      if (!hay.includes(search.toLowerCase())) return false;
    }
    return true;
  });

  const handleUpload = (rowId: string) => {
    pendingUploadId.current = rowId;
    fileInputRef.current?.click();
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const rowId = pendingUploadId.current || '';

    setUploadingId(rowId);
    setUploadResult(null);
    try {
      const res = await uploadDisclosureCheck(file);
      setRows((prev) => prev.map((r) => (r.id === rowId ? { ...r, status: 'YELLOW', sourceReference: file.name } : r)));
      onStatusUpdate?.(rowId, 'Uploaded');
      setUploadResult({ type: 'success', text: t('ev_upload_success', lang).replace('{file}', file.name).replace('{text}', res.extracted_text?.slice(0, 60) || t('ev_docs_scanned', lang)) });
    } catch {
      setUploadResult({ type: 'error', text: t('ev_upload_failed', lang) });
    } finally {
      setUploadingId(null);
      pendingUploadId.current = null;
      if (e.target) e.target.value = '';
    }
  };

  const cycleStatus = (rowId: string) => {
    setRows((prev) =>
      prev.map((row) => {
        if (row.id !== rowId) return row;
        const next = row.status === 'RED' ? 'YELLOW' : row.status === 'YELLOW' ? 'GREEN' : 'RED';
        onStatusUpdate?.(rowId, next);
        return { ...row, status: next as EvidenceRow['status'] };
      })
    );
  };

  const filters: { key: FilterKey; label: string; color: string }[] = [
    { key: 'ALL', label: t('ev_filter_all', lang), color: 'text-slate-600' },
    { key: 'GREEN', label: t('ev_filter_strong', lang), color: 'text-emerald-600' },
    { key: 'YELLOW', label: t('ev_filter_moderate', lang), color: 'text-amber-600' },
    { key: 'RED', label: t('ev_status_missing', lang), color: 'text-red-600' },
  ];

  return (
    <div className="space-y-5 animate-slide-up">
      {/* Linked passport banner */}
      {passport && passportId && (
        <div className="flex flex-wrap items-center gap-2 px-4 py-3 rounded-2xl bg-emerald-50/70 border border-emerald-200">
          <Link2 className="w-4 h-4 text-emerald-600" />
          <span className="text-xs text-slate-700">
            <span className="font-semibold text-slate-900">{t('ev_linked_to_passport', lang)}</span> {passport.case_title}
            <code className="ml-1.5 font-mono text-[10px] text-emerald-700">{passportId.slice(0, 8)}</code>
          </span>
          {passportRowsLoading && <Loader2 className="w-3.5 h-3.5 animate-spin text-emerald-600 ml-auto" />}
          {!passportRowsLoading && <Badge variant="success" dot className="ml-auto">{t('ev_auto_synced', lang)}</Badge>}
        </div>
      )}
      {linkedError && (
        <div className="px-4 py-2.5 rounded-xl bg-red-50 border border-red-200 text-xs text-red-700 flex items-center gap-2">
          <XCircle className="w-4 h-4 flex-shrink-0" /> {linkedError} {t('ev_showing_demo_rows', lang)}
        </div>
      )}

      {/* Summary cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {filters.map((f) => (
          <button key={f.key} onClick={() => setFilter(f.key)} className="text-left">
            <GlassCard hover padding="md" className={filter === f.key ? 'border-blue-500/40' : ''}>
              <div className="flex items-center justify-between">
                <span className={`text-[11px] font-medium uppercase tracking-wide ${f.color}`}>{f.label}</span>
                {f.key === 'GREEN' && <span className="w-2 h-2 rounded-full bg-emerald-400" />}
                {f.key === 'YELLOW' && <span className="w-2 h-2 rounded-full bg-amber-400" />}
                {f.key === 'RED' && <span className="w-2 h-2 rounded-full bg-red-400" />}
                {f.key === 'ALL' && <span className="w-2 h-2 rounded-full bg-slate-400" />}
              </div>
              <div className="text-2xl font-black text-slate-900 mt-1 font-display">{counts[f.key]}</div>
            </GlassCard>
          </button>
        ))}
      </div>

      {/* Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="relative flex-1 max-w-sm">
          <Search className="w-4 h-4 text-slate-500 absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder={t('ev_search_placeholder', lang)}
            className="w-full pl-10 pr-4 py-2.5 bg-emerald-50/70 border border-emerald-200 rounded-xl text-sm text-slate-900 placeholder-slate-500 focus:outline-none focus:border-blue-500/40"
          />
        </div>
        <Button variant="secondary" size="sm" icon={<Upload className="w-4 h-4" />}>{t('ev_upload_evidence', lang)}</Button>
      </div>

      {/* Table */}
      <GlassCard className="overflow-hidden !p-0">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-[10px] uppercase tracking-widest text-slate-500 border-b border-emerald-200">
                <th className="px-5 py-3.5 font-semibold">{t('ev_col_claim', lang)}</th>
                <th className="px-5 py-3.5 font-semibold">{t('ev_col_evidence_type', lang)}</th>
                <th className="px-5 py-3.5 font-semibold">{t('ev_col_status', lang)}</th>
                <th className="px-5 py-3.5 font-semibold">{t('ev_col_action', lang)}</th>
              </tr>
            </thead>
            <tbody>
              {filteredRows.map((row) => {
                const ui = STATUS_UI[row.status];
                const txt = rowText(row);
                return (
                  <tr key={row.id} className="border-b border-emerald-100 hover:bg-emerald-50/50 transition">
                    <td className="px-5 py-3.5 text-slate-700 font-medium">{txt.claim}</td>
                    <td className="px-5 py-3.5 text-slate-500">{txt.type}</td>
                    <td className="px-5 py-3.5">
                      <button onClick={() => cycleStatus(row.id)} className={`px-3 py-1.5 rounded-full border text-xs font-semibold inline-flex items-center gap-1.5 ${ui.bg} ${ui.border} ${ui.text} hover:opacity-80 transition`}>
                        <span className={`w-1.5 h-1.5 rounded-full ${ui.dot}`} /> {t(ui.label, lang)}
                      </button>
                    </td>
                    <td className="px-5 py-3.5">
                      {row.sourceReference ? (
                        <Badge variant="success" dot className="truncate max-w-[160px] overflow-hidden"><FileText className="w-3 h-3" /> {row.sourceReference}</Badge>
                      ) : (
                        <button onClick={() => handleUpload(row.id)} disabled={uploadingId === row.id} className="px-3 py-1.5 rounded-lg bg-emerald-50/70 hover:bg-blue-100 border border-emerald-200 hover:border-blue-500/40 text-xs text-slate-600 hover:text-blue-600 inline-flex items-center gap-1.5 transition disabled:opacity-50">
                          {uploadingId === row.id ? <Loader2 className="w-3 h-3 animate-spin" /> : <Upload className="w-3 h-3" />} {t('ev_upload', lang)}
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })}
              {filteredRows.length === 0 && (
                <tr>
                  <td colSpan={4} className="px-5 py-10 text-center text-slate-500 text-sm">
                    <Search className="w-6 h-6 mx-auto mb-2 text-slate-500" />
                    {t('ev_no_matches', lang)}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </GlassCard>

      <input ref={fileInputRef} type="file" accept=".pdf,.docx,.txt,.png,.jpg,.jpeg" className="hidden" onChange={handleFileChange} />

      {uploadResult && (
        <div className={`px-4 py-3 rounded-xl border text-xs animate-scaleIn ${uploadResult.type === 'success' ? 'bg-emerald-100 border-emerald-500/30 text-emerald-700' : 'bg-red-100 border-red-500/30 text-red-700'}`}>
          {uploadResult.text}
        </div>
      )}
    </div>
  );
}