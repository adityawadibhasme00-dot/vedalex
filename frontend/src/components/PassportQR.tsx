'use client';
import React, { useEffect, useRef, useState } from 'react';
import QRCode from 'qrcode';
import { Download, Smartphone, QrCode, Check } from 'lucide-react';
import { InnovationPassport } from '../types';
import { useLang } from '../lib/LangContext';

interface PassportQRProps {
  passport: InnovationPassport;
}

export default function PassportQR({ passport }: PassportQRProps) {
  const { lang } = useLang();
  const Hi = (en: string, hi: string) => (lang === 'hi' ? hi : en);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [qr, setQr] = useState(false);
  const [downloaded, setDownloaded] = useState(false);

  const payload = JSON.stringify(
    {
      app: 'IP-SAKTI Sahayak',
      doc: 'Innovation Passport',
      id: passport.id,
      version: passport.version || 1,
      title: passport.case_title,
      ingredients: (passport.ingredients || []).map(
        (i) => `${i.raw_name} (${i.botanical_name || '—'})`
      ),
      claims: passport.proposed_claims || [],
      markets: passport.target_markets || [],
      form: `${passport.product_form} · ${passport.dosage_form}`,
      biological_resource_origin: passport.biological_resource_origin,
      issued: new Date().toISOString().slice(0, 10),
    },
    null,
    0
  );

  useEffect(() => {
    if (!canvasRef.current) return;
    QRCode.toCanvas(
      canvasRef.current,
      payload,
      { width: 168, margin: 1, errorCorrectionLevel: 'M', color: { dark: '#065F46', light: '#FFFFFF' } },
      (err: Error | null | undefined) => {
        if (err) console.error('QR generation error', err);
        else setQr(true);
      }
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [passport.id, passport.version]);

  const handleDownload = () => {
    const blob = new Blob([JSON.stringify(passport, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `innovation-passport-${(passport.id || '').slice(0, 8)}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    setDownloaded(true);
    setTimeout(() => setDownloaded(false), 2500);
  };

  return (
    <div className="flex flex-col items-center rounded-2xl bg-white border border-emerald-200 shadow-xl shadow-emerald-900/10 p-4 w-[220px]">
      <div className="flex items-center gap-2 mb-3 w-full">
        <QrCode className="w-4 h-4 text-emerald-700" />
        <span className="text-xs font-bold text-slate-900">{Hi('Scan to download passport', 'पासपोर्ट डाउनलोड करने के लिए स्कैन करें')}</span>
      </div>

      <div className="rounded-xl border-2 border-emerald-900/10 bg-white p-2">
        {qr ? (
          <canvas ref={canvasRef} className="block" />
        ) : (
          <div className="w-[168px] h-[168px] flex items-center justify-center text-[11px] text-slate-400">
            {Hi('Generating QR…', 'QR बन रहा है…')}
          </div>
        )}
      </div>

      <div className="flex items-center gap-1.5 mt-2.5 text-[10px] text-slate-500 text-center">
        <Smartphone className="w-3.5 h-3.5 text-emerald-600 flex-shrink-0" />
        {Hi(
          'Scan with any camera — passport summary opens on your device',
          'किसी भी कैमरे से स्कैन करें — पासपोर्ट सारांश आपके डिवाइस पर खुलता है'
        )}
      </div>

      <button
        type="button"
        onClick={handleDownload}
        className="mt-3 w-full inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-gradient-to-r from-emerald-700 to-emerald-600 hover:from-emerald-600 hover:to-emerald-500 text-white text-xs font-bold shadow-lg shadow-emerald-900/30 transition disabled:opacity-60"
        disabled={downloaded}
      >
        {downloaded ? (
          <>
            <Check className="w-4 h-4" /> {Hi('Passport saved!', 'पासपोर्ट सहेजा गया!')}
          </>
        ) : (
          <>
            <Download className="w-4 h-4" /> {Hi('Download .JSON', 'डाउनलोड करें')}
          </>
        )}
      </button>
    </div>
  );
}