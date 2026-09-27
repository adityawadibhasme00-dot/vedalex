'use client';

import React from 'react';
import clsx from 'clsx';
import { Download, Mail, Phone, UserRound } from 'lucide-react';

interface HumanEscalationProps {
  /** The query that triggered escalation — included in the export + email. */
  query?: string;
  /** Turn-level trace to export alongside the query. */
  log?: Array<Record<string, unknown>>;
  name?: string;
  email?: string;
  phone?: string;
  /** Called with the export payload instead of triggering a download. */
  onExport?: (payload: {
    query?: string;
    log: Array<Record<string, unknown>>;
    exportedAt: string;
  }) => void;
  className?: string;
}

/**
 * Human IP facilitator contact card + query-log export
 * (Master Prompt v7.0.0, Component 12). Rendered whenever the guardrails
 * abstain/escalate so a stuck user always has a real person to reach.
 */
export function HumanEscalation({
  query,
  log = [],
  name = 'Aditya Sharma (Compliance Lead)',
  email = 'grievance@ipsakti.in',
  phone,
  onExport,
  className,
}: HumanEscalationProps) {
  const handleExport = () => {
    const payload = {
      query,
      log,
      exportedAt: new Date().toISOString(),
    };
    if (onExport) {
      onExport(payload);
      return;
    }
    try {
      const blob = new Blob([JSON.stringify(payload, null, 2)], {
        type: 'application/json',
      });
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = 'ipsakti-escalation-log.json';
      anchor.click();
      URL.revokeObjectURL(url);
    } catch {
      // jsdom / restricted environments — export unavailable.
    }
  };

  const mailto = `mailto:${email}?subject=${encodeURIComponent(
    'IP-SAKTI — IP facilitator request'
  )}&body=${encodeURIComponent(query ? `Query: ${query}` : '')}`;

  return (
    <section
      aria-label="Human IP facilitator escalation"
      className={clsx(
        'rounded-2xl border border-amber-200 bg-amber-50/70 p-4',
        className
      )}
    >
      <header className="flex items-center gap-2 mb-3">
        <UserRound className="w-4 h-4 text-amber-700" aria-hidden="true" />
        <h3 className="text-sm font-bold text-slate-800">
          Human IP Facilitator
        </h3>
        <span className="ml-auto text-[10px] font-semibold uppercase tracking-wider text-amber-700 bg-amber-100 rounded-full px-2 py-0.5">
          Escalation path
        </span>
      </header>

      <dl className="space-y-1.5 text-xs text-slate-700 mb-4">
        <div className="flex gap-2">
          <dt className="font-semibold text-slate-500 w-16">Name</dt>
          <dd>{name}</dd>
        </div>
        <div className="flex gap-2">
          <dt className="font-semibold text-slate-500 w-16">Email</dt>
          <dd className="break-all">{email}</dd>
        </div>
        {phone && (
          <div className="flex gap-2">
            <dt className="font-semibold text-slate-500 w-16">Phone</dt>
            <dd>{phone}</dd>
          </div>
        )}
      </dl>

      <div className="flex flex-wrap gap-2">
        <a
          href={mailto}
          className="inline-flex items-center gap-1.5 rounded-xl bg-emerald-700 hover:bg-emerald-600 text-white text-xs font-semibold px-3 py-2 transition"
        >
          <Mail className="w-3.5 h-3.5" aria-hidden="true" />
          Email facilitator
        </a>
        {phone && (
          <a
            href={`tel:${phone.replace(/[^+\d]/g, '')}`}
            className="inline-flex items-center gap-1.5 rounded-xl bg-white hover:bg-slate-50 text-slate-700 border border-slate-200 text-xs font-semibold px-3 py-2 transition"
          >
            <Phone className="w-3.5 h-3.5" aria-hidden="true" />
            Call
          </a>
        )}
        <button
          type="button"
          onClick={handleExport}
          className="inline-flex items-center gap-1.5 rounded-xl bg-white hover:bg-slate-50 text-slate-700 border border-slate-200 text-xs font-semibold px-3 py-2 transition"
        >
          <Download className="w-3.5 h-3.5" aria-hidden="true" />
          Export query log
        </button>
      </div>

      {query && (
        <p className="mt-3 text-[11px] text-slate-500 border-t border-amber-200 pt-2">
          Escalated query: <span className="text-slate-700">“{query}”</span>
        </p>
      )}
    </section>
  );
}

export default HumanEscalation;
