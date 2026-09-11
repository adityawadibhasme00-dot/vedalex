'use client';

import React, { useState } from 'react';
import { dispatchExpertHandoff } from '../lib/api';
import { ShieldCheck, UserCheck, X, FileText, Check, AlertCircle } from 'lucide-react';

interface ExpertHandoffModalProps {
  isOpen: boolean;
  onClose: () => void;
  passportId: string;
}

export default function ExpertHandoffModal({
  isOpen,
  onClose,
  passportId
}: ExpertHandoffModalProps) {
  const [userName, setUserName] = useState('Dr. Rajesh Vaidya');
  const [userEmail, setUserEmail] = useState('rajesh.vaidya@ayurstartup.in');
  const [expertType, setExpertType] = useState('Registered Patent Agent');
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
      alert('Failed to dispatch expert handoff');
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
                Section 7.3.2 Escalation Pathway
              </span>
              <h3 className="text-lg font-bold text-slate-900 font-display">
                Certified Expert Handoff Bridge
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
            <h4 className="text-base font-bold text-slate-900">Case Successfully Queued for Dispatch</h4>
            <p className="text-xs text-slate-600 max-w-md mx-auto">{successResponse.message}</p>
            <div className="p-3 rounded-xl bg-emerald-50/70 border border-emerald-200 text-xs text-left font-mono space-y-1">
              <div><strong className="text-slate-500">Ticket ID:</strong> {successResponse.ticket_id}</div>
              <div><strong className="text-slate-500">Assigned Hub:</strong> {successResponse.assigned_facilitation_center}</div>
              <div><strong className="text-slate-500">DPDP Consent Hash:</strong> {successResponse.consent_audit_hash.slice(0, 16)}...</div>
              <div><strong className="text-slate-500">SLA Response:</strong> 48 Hours</div>
            </div>
            <button
              onClick={onClose}
              className="px-6 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-xs transition"
            >
              Close Window
            </button>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4 my-4 text-xs">
            <div>
              <label className="text-slate-500 font-medium block mb-1">Select Professional Expert Track:</label>
              <select
                value={expertType}
                onChange={(e) => setExpertType(e.target.value)}
                className="w-full bg-emerald-50/70 border border-emerald-200 rounded-xl p-2.5 text-slate-800 focus:outline-none focus:border-emerald-500"
              >
                <option value="Registered Patent Agent">Registered Patent Agent (Indian Patent Office / Section 3(p) Specialist)</option>
                <option value="AYUSH Regulatory Consultant">AYUSH Regulatory Consultant (Drugs & Cosmetics Act / FSSAI 2022)</option>
                <option value="Export Compliance Consultant">US FDA & Health Canada Export Regulatory Consultant</option>
              </select>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-slate-500 font-medium block mb-1">Contact Name:</label>
                <input
                  type="text"
                  value={userName}
                  onChange={(e) => setUserName(e.target.value)}
                  className="w-full bg-emerald-50/70 border border-emerald-200 rounded-xl p-2.5 text-slate-800 focus:outline-none focus:border-emerald-500"
                  required
                />
              </div>
              <div>
                <label className="text-slate-500 font-medium block mb-1">Contact Email:</label>
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
                  <strong>DPDP Act 2023 Consent:</strong> I give explicit consent to share this Innovation Passport and extracted laboratory documents with registered IP Facilitation Center professionals for triage review.
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
                  <strong>Liability Boundary Acknowledgment:</strong> I understand that IP-SAKTI AI provides structured first-pass triage and evidence gap assessment; certified professionals provide formal liability-bearing legal/regulatory opinions.
                </span>
              </label>
            </div>

            <button
              type="submit"
              disabled={isLoading || !dpdpConsent || !liabilityAck}
              className="w-full py-2.5 rounded-xl bg-gradient-to-r from-emerald-600 to-emerald-500 hover:from-emerald-500 text-white font-semibold text-xs shadow-lg transition disabled:opacity-50"
            >
              {isLoading ? 'Dispatching to Facilitation Queue...' : 'Submit Case to Certified Expert'}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
