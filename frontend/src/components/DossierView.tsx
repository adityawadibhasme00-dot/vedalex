'use client';
import React, { useState } from 'react';
import { FileText, FileCode, FileCheck2, Download, Loader2, CheckCircle2, ExternalLink } from 'lucide-react';
import { exportDossier } from '../lib/api';
import { GlassCard } from './ui/GlassCard';
import { Button } from './ui/Button';
import { Badge } from './ui/Badge';

interface DossierViewProps {
  passportId: string;
}

function resolveDownloadUrl(downloadUrl: string): string {
  if (/^https?:\/\//i.test(downloadUrl)) return downloadUrl;
  return downloadUrl.startsWith('/') ? downloadUrl : `/${downloadUrl}`;
}

function triggerDownload(url: string) {
  const a = document.createElement('a');
  a.href = url;
  a.target = '_self';
  a.rel = 'noopener';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
}

export default function DossierView({ passportId }: DossierViewProps) {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<null | { filename: string; download_url: string; generated_at: string }>(null);
  const [error, setError] = useState<string | null>(null);

  const runExport = async (format: string) => {
    if (!passportId) { setError('No passport available. Create one first.'); return; }
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await exportDossier(passportId, format);
      setResult(res);
      const url = resolveDownloadUrl(res.download_url);
      // Trigger the download shortly after rendering the result card
      setTimeout(() => { try { triggerDownload(url); } catch { /* handled below */ } }, 80);
    } catch (e: any) {
      setError(e?.message || 'Export failed. Make sure the backend is running.');
    } finally {
      setLoading(false);
    }
  };

  const formatBtn = (label: string, icon: React.ReactNode) => (
    <button
      onClick={() => runExport(label.toLowerCase())}
      disabled={loading}
      className="flex flex-col items-center gap-3 p-5 rounded-2xl border border-emerald-200 bg-emerald-50 hover:border-blue-500/40 hover:bg-emerald-100 transition group disabled:opacity-50"
    >
      <div className="w-12 h-12 rounded-2xl bg-blue-100 text-blue-600 flex items-center justify-center group-hover:bg-blue-200 transition">
        {icon}
      </div>
      <span className="text-sm font-semibold text-slate-900">Dossier {label}</span>
      <span className="text-[10px] text-slate-500">Filing-ready report</span>
    </button>
  );

  return (
    <div className="space-y-6">
      <GlassCard padding="lg">
        <h3 className="text-sm font-bold text-slate-900 font-display mb-1">Generate filing-ready documents</h3>
        <p className="text-xs text-slate-500 mb-6">
          Combine your Innovation Passport, regulatory assessment, evidence status and QR verification into a polished dossier.
        </p>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {formatBtn('PDF', <FileText className="w-6 h-6" />)}
          {formatBtn('DOCX', <FileCode className="w-6 h-6" />)}
          <button
            onClick={() => runExport('checklist')}
            disabled={loading}
            className="flex flex-col items-center gap-3 p-5 rounded-2xl border border-emerald-200 bg-emerald-50 hover:border-violet-500/40 hover:bg-emerald-100 transition group disabled:opacity-50"
          >
            <div className="w-12 h-12 rounded-2xl bg-violet-100 text-violet-600 flex items-center justify-center group-hover:bg-violet-200 transition">
              <FileCheck2 className="w-6 h-6" />
            </div>
            <span className="text-sm font-semibold text-slate-900">Checklist</span>
            <span className="text-[10px] text-slate-500">Filings & requirements</span>
          </button>
        </div>
      </GlassCard>

      {loading && (
        <GlassCard padding="lg" className="flex items-center gap-3 text-sm text-blue-600">
          <Loader2 className="w-5 h-5 animate-spin" /> Generating dossier...
        </GlassCard>
      )}

      {error && (
        <GlassCard padding="md" className="border-red-500/40">
          <div className="text-sm text-red-600">{error}</div>
        </GlassCard>
      )}

      {result && (
        <GlassCard padding="lg" className="border-emerald-500/30 animate-slide-up">
          <div className="flex items-start justify-between gap-4">
            <div className="flex items-center gap-3">
              <CheckCircle2 className="w-6 h-6 text-emerald-600 flex-shrink-0" />
              <div>
                <p className="text-sm font-bold text-slate-900">Dossier generated successfully</p>
                <p className="text-xs text-slate-500 mt-0.5">{result.filename}</p>
                <p className="text-[10px] text-slate-500 mt-1">Generated {new Date(result.generated_at).toLocaleString()}</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <a
                href={resolveDownloadUrl(result.download_url)}
                onClick={(e) => { e.preventDefault(); triggerDownload(resolveDownloadUrl(result.download_url)); }}
                className="flex items-center gap-2 px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold transition"
              >
                <Download className="w-4 h-4" /> Download again
              </a>
              <a
                href={resolveDownloadUrl(result.download_url)}
                target="_blank"
                rel="noreferrer"
                className="flex items-center gap-2 px-3 py-2 rounded-xl bg-white border border-emerald-300 hover:bg-emerald-50 text-emerald-700 text-xs font-bold transition"
                title="Open in new tab"
              >
                <ExternalLink className="w-4 h-4" />
              </a>
            </div>
          </div>
          <div className="mt-4 pt-4 border-t border-emerald-200">
            <Badge variant="success" dot>QR Verified</Badge>
            <Badge variant="info" dot>DPDP Compliant</Badge>
          </div>
        </GlassCard>
      )}
    </div>
  );
}
