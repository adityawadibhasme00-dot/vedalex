'use client';

import React, { useState } from 'react';
import { dispatchExpertHandoff } from '../lib/api';
import { ShieldCheck, UserCheck, X, FileText, Check, AlertCircle } from 'lucide-react';
import { useLang } from '../lib/LangContext';
import { t } from '../lib/i18n';

interface ExpertHandoffModalProps {
  isOpen: boolean;
  onClose: () => void;
  passportId: string;
  initialExpertType?: string;
}

const EXPERT_TYPE_OPTIONS = [
  { value: 'Registered Patent Agent', label: 'Registered Patent Agent (Indian Patent Office / Section 3(p) Specialist)' },
  { value: 'AYUSH Regulatory Consultant', label: 'AYUSH Regulatory Consultant (Drugs & Cosmetics Act / FSSAI 2022)' },
  { value: 'Export Compliance Consultant', label: 'US FDA & Health Canada Export Regulatory Consultant' },
];

const ESCALATION_TO_EXPERT: Record<string, string> = {
  ip_attorney: 'Registered Patent Agent',
  regulatory_expert: 'AYUSH Regulatory Consultant',
  nba: 'AYUSH Regulatory Consultant',
  tkdl: 'Registered Patent Agent',
};

export default function ExpertHandoffModal({
  isOpen,
  onClose,
  passportId,
  initialExpertType
}: ExpertHandoffModalProps) {
  const { lang } = useLang();
  const [userName, setUserName] = useState('Dr. Rajesh Vaidya');
  const [userEmail, setUserEmail] = useState('rajesh.vaidya@ayurstartup.in');
  const [expertType, setExpertType] = useState(
    (initialExpertType && ESCALATION_TO_EXPERT[initialExpertType]) || 'Registered Patent Agent'
  );
  const [dpdpConsent, setDpdpConsent] = useState(true);
  const [liabilityAck, setLiabilityAck] = useState(true);
  const [isLoading, setIsLoading] = useState(false);
  const [successResponse, setSuccessResponse] = useState<any>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    try {
      const res = await dispatchExpertHandoff({
        passport_id: passportId,
        expert_type: expertType,
        user_name: userName,
        user_email: userEmail,
        explicit_dpdp_consent: dpdpConsent,
        liability_boundary_acknowledged: liabilityAck
      });
      setSuccessResponse(res);
    } catch (err) {
      alert(t('expert_error', lang));
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-fade-in">
      <div className="glass-panel max-w-xl w-full rounded-2xl p-6 border border-emerald-500/40 shadow-2xl">
        {/* Header */}
        <div className="flex items-start justify-between pb-4 border-b border-emerald-200">
          <div className="flex items-center space-x-3">
            <div className="p-2.5 rounded-xl bg-emerald-100 text-emerald-600">
              <UserCheck className="w-5 h-5" />
            </div>
            <div>
              <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-600">
                {t('expert_escalation_pathway', lang)}
              </span>
              <h3 className="text-lg font-bold text-slate-900 font-display">
                {t('expert_bridge_title', lang)}
              </h3>
            </div>
          </div>
          <button onClick={onClose} className="p-1.5 rounded-lg text-slate-500 hover:text-slate-900 hover:bg-emerald-50 transition">
            <X className="w-5 h-5" />
          </button>
        </div>

        {successResponse ? (
          <div className="py-6 space-y-4 text-center">
            <div className="w-12 h-12 rounded-full bg-emerald-100 text-emerald-600 flex items-center justify-center mx-auto">
              <Check className="w-6 h-6" />
            </div>
            <h4 className="text-base font-bold text-slate-900">{t('expert_success_heading', lang)}</h4>
            <p className="text-xs text-slate-600 max-w-md mx-auto">{successResponse.message}</p>
            <div className="p-3 rounded-xl bg-emerald-50/70 border border-emerald-200 text-xs text-left font-mono space-y-1">
              <div><strong className="text-slate-500">{t('expert_ticket_id', lang)}</strong> {successResponse.ticket_id}</div>
              <div><strong className="text-slate-500">{t('expert_assigned_hub', lang)}</strong> {successResponse.assigned_facilitation_center}</div>
              <div><strong className="text-slate-500">{t('expert_dpdp_hash', lang)}</strong> {successResponse.consent_audit_hash.slice(0, 16)}...</div>
              <div><strong className="text-slate-500">{t('expert_sla', lang)}</strong> {t('expert_sla_value', lang)}</div>
            </div>
            <button
              onClick={onClose}
              className="px-6 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-xs transition"
            >
              {t('expert_close_window', lang)}
            </button>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4 my-4 text-xs">
            <div>
              <label className="text-slate-500 font-medium block mb-1">{t('expert_select_track', lang)}</label>
              <select
                value={expertType}
                onChange={(e) => setExpertType(e.target.value)}
                className="w-full bg-emerald-50/70 border border-emerald-200 rounded-xl p-2.5 text-slate-800 focus:outline-none focus:border-emerald-500"
              >
                {EXPERT_TYPE_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
              </select>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-slate-500 font-medium block mb-1">{t('expert_contact_name', lang)}</label>
                <input
                  type="text"
                  value={userName}
                  onChange={(e) => setUserName(e.target.value)}
                  className="w-full bg-emerald-50/70 border border-emerald-200 rounded-xl p-2.5 text-slate-800 focus:outline-none focus:border-emerald-500"
                  required
                />
              </div>
              <div>
                <label className="text-slate-500 font-medium block mb-1">{t('expert_contact_email', lang)}</label>
                <input
                  type="email"
                  value={userEmail}
                  onChange={(e) => setUserEmail(e.target.value)}
                  className="w-full bg-emerald-50/70 border border-emerald-200 rounded-xl p-2.5 text-slate-800 focus:outline-none focus:border-emerald-500"
                  required
                />
              </div>
            </div>

            {/* Mandatory Compliance Checkboxes */}
            <div className="p-3.5 rounded-xl bg-emerald-50/70 border border-emerald-200 space-y-2.5">
              <label className="flex items-start space-x-2.5 cursor-pointer">
                <input
                  type="checkbox"
                  checked={dpdpConsent}
                  onChange={(e) => setDpdpConsent(e.target.checked)}
                  className="mt-0.5 rounded border-slate-700 text-emerald-600 focus:ring-emerald-500"
                  required
                />
                <span className="text-[11px] text-slate-700">
                  <strong>{t('expert_dpdp_label', lang)}</strong> {t('expert_dpdp_body', lang)}
                </span>
              </label>

              <label className="flex items-start space-x-2.5 cursor-pointer">
                <input
                  type="checkbox"
                  checked={liabilityAck}
                  onChange={(e) => setLiabilityAck(e.target.checked)}
                  className="mt-0.5 rounded border-slate-700 text-emerald-600 focus:ring-emerald-500"
                  required
                />
                <span className="text-[11px] text-slate-700">
                  <strong>{t('expert_liability_label', lang)}</strong> {t('expert_liability_body', lang)}
                </span>
              </label>
            </div>

            <button
              type="submit"
              disabled={isLoading || !dpdpConsent || !liabilityAck}
              className="w-full py-2.5 rounded-xl bg-gradient-to-r from-emerald-600 to-emerald-500 hover:from-emerald-500 text-white font-semibold text-xs shadow-lg transition disabled:opacity-50"
            >
              {isLoading ? t('expert_dispatching', lang) : t('expert_submit', lang)}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
