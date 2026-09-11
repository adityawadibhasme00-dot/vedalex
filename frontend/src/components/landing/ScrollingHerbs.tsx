'use client';
import React, { useEffect, useState } from 'react';
import { Leaf, X, ScrollText, BookOpen } from 'lucide-react';
import { useLang } from '../../lib/LangContext';

interface Herb {
  key: string;
  en: string;
  hi: string;
  latin: string;
  color: string;
  descEn: string;
  descHi: string;
  noteEn: string;
  noteHi: string;
  facts: { en: string; hi: string }[];
}

const HERBS: Herb[] = [
  {
    key: 'tulsi',
    en: 'Tulsi', hi: 'तुलसी',
    latin: 'Ocimum sanctum',
    color: 'from-emerald-600 to-green-500',
    descEn: 'The sacred "Queen of Herbs" — adaptogen that supports immunity, respiratory health and mental calm.',
    descHi: 'हर्ब-रानी — प्रतिरोधक क्षमता, श्वसन स्वास्थ्य और मानसिक शांति का पोषक एडाप्टोजन।',
    noteEn: 'IP-SAKTI maps every botanical to its Ayurvedic Pharmacopoeia (API) monograph for Section 3(p) screening.',
    noteHi: 'IP-SAKTI हर वनस्पति को सेक्शन 3(p) जाँच हेतु आयुर्वेदिक फार्माकोपिया (API) मोनोग्राफ से जोड़ता है।',
    facts: [
      { en: 'Immunity booster', hi: 'प्रतिरोधक क्षमता' },
      { en: 'Respiratory care', hi: 'श्वसन देखभाल' },
      { en: 'Stress adaptation', hi: 'तनाव अनुकूलन' },
    ],
  },
  {
    key: 'ashwagandha',
    en: 'Ashwagandha', hi: 'अश्वगंधा',
    latin: 'Withania somnifera',
    color: 'from-amber-600 to-yellow-500',
    descEn: 'Adaptogenic root synonymous with vitality — energy, balanced stress and longevity. A TKDL-common ingredient.',
    descHi: 'शक्ति का प्रतीक एडाप्टोजेनिक मूल — ऊर्जा, तनाव संतुलन और दीर्घायु। TKDL में प्रचलित घटक।',
    noteEn: 'Common TKDL entry → novel formulation + synergistic claims raise your readiness score automatically.',
    noteHi: 'सामान्य TKDL प्रविष्टि → नवीन फॉर्मूलेशन व सहक्रियात्मक दावे स्वतः तैयारी स्कोर बढ़ाते हैं।',
    facts: [
      { en: 'Energy & stamina', hi: 'ऊर्जा व सहनशक्ति' },
      { en: 'Sleep support', hi: 'नींद सहायता' },
      { en: 'Longevity', hi: 'दीर्घायु' },
    ],
  },
  {
    key: 'brahmi',
    en: 'Brahmi', hi: 'ब्राह्मी',
    latin: 'Bacopa monnieri',
    color: 'from-teal-600 to-cyan-500',
    descEn: 'Classical Medhya (intellect) rasayana — memory, focus and cognition. Prized in classical Ayurvedic texts.',
    descHi: 'शास्त्रीय मेध्या (बुद्धि) रसायन — स्मृति, एकाग्रता और बोध। आयुर्वेदिक ग्रंथों में आदरणीय।',
    noteEn: 'Classical mention increases Section 3(p) scrutiny — narrative evidence helps overcome it.',
    noteHi: 'शास्त्रीय उल्लेख से सेक्शन 3(p) जाँच गहरी होती है — कथात्मक साक्ष्य इसमें सहायक है।',
    facts: [
      { en: 'Memory', hi: 'स्मृति' },
      { en: 'Focus', hi: 'एकाग्रता' },
      { en: 'Cognitive tonic', hi: 'बोध पोषक' },
    ],
  },
  {
    key: 'haldi',
    en: 'Haldi · Turmeric', hi: 'हल्दी',
    latin: 'Curcuma longa',
    color: 'from-orange-600 to-amber-500',
    descEn: 'The golden rhizome — curcumin-rich anti-inflammatory used in wellness, cosmetics and food.',
    descHi: 'सुनहरा प्रकंद — कर्क्यूमिन-युक्त सूजनरोधी; स्वास्थ्य, सौंदर्य और आहार में प्रयुक्त।',
    noteEn: 'A nano/liposomal curcumin delivery can cross Section 3(p) with demonstrated bioenhancement.',
    noteHi: 'नैनो/लिपोसोमल कर्क्यूमिन वितरण, बायोएन्हांसमेंट प्रदर्शन से सेक्शन 3(p) पार कर सकता है।',
    facts: [
      { en: 'Anti-inflammatory', hi: 'सूजनरोधी' },
      { en: 'Antioxidant', hi: 'एंटीऑक्सीडेंट' },
      { en: 'Golden spice', hi: 'सुनहरा मसाला' },
    ],
  },
  {
    key: 'amla',
    en: 'Amla', hi: 'आंवला',
    latin: 'Phyllanthus emblica',
    color: 'from-lime-600 to-green-500',
    descEn: 'Rasayana berry packed with Vitamin C — digestion, immunity and skin vitality.',
    descHi: 'विटामिन-C से परिपूर्ण रसायन फल — पाचन, प्रतिरोधक क्षमता और त्वचा की मजबूती।',
    noteEn: 'Priority herbal ingredient — sourcing origin data is captured in the Innovation Passport.',
    noteHi: 'प्राथमिक घटक — स्रोतक्षेत्र की जानकारी इनोवेशन पासपोर्ट में अंकित की जाती है।',
    facts: [
      { en: 'Vitamin C', hi: 'विटामिन C' },
      { en: 'Digestion', hi: 'पाचन' },
      { en: 'Skin vitality', hi: 'त्वचा ऊर्जा' },
    ],
  },
  {
    key: 'neem',
    en: 'Neem', hi: 'नीम',
    latin: 'Azadirachta indica',
    color: 'from-green-700 to-emerald-500',
    descEn: 'Purifying tree of many uses — skin, blood purification and traditional oral care.',
    descHi: 'अनेक उपयोगों वाला पवित्र वृक्ष — त्वचा, रक्त शोधन और पारंपरिक मुख देखभाल।',
    noteEn: 'Neem extracts are heavily patented — prior-art engine flags overlapping cliffs early.',
    noteHi: 'नीम के अर्क पर कई पेटेंट हैं — पूर्व-आधार इंजन अतिव्यापी क्लिफ्स पहले ही चिह्नित करता है।',
    facts: [
      { en: 'Skin care', hi: 'त्वचा देखभाल' },
      { en: 'Blood purification', hi: 'रक्त शोधन' },
      { en: 'Oral care', hi: 'मुख देखभाल' },
    ],
  },
  {
    key: 'shatavari',
    en: 'Shatavari', hi: 'शतावरी',
    latin: 'Asparagus racemosus',
    color: 'from-pink-600 to-rose-500',
    descEn: 'Women’s vitality rasayana — lactation, reproductive wellness and digestive support.',
    descHi: 'स्त्री शक्ति रसायन — स्तनपान, प्रजनन स्वास्थ्य और पाचन सहायता।',
    noteEn: 'Gynecological claims trigger FTO checks — evidence matrix scores every claim.',
    noteHi: 'स्त्री रोग संबंधी दावों पर FTO जाँच होती है — साक्ष्य मैट्रिक्स हर दावे का मूल्यांकन करता है।',
    facts: [
      { en: 'Female vitality', hi: 'स्त्री शक्ति' },
      { en: 'Digestion', hi: 'पाचन' },
      { en: 'Rasayana', hi: 'रसायन' },
    ],
  },
  {
    key: 'guduchi',
    en: 'Guduchi · Giloy', hi: 'गुडुची · गिलोय',
    latin: 'Tinospora cordifolia',
    color: 'from-violet-600 to-purple-500',
    descEn: 'Immuno-modulator celebrated in classical texts — fever care, metabolism and annual immunity.',
    descHi: 'शास्त्रों में प्रशंसित प्रतिरक्षा-नियामक — ज्वर देखभाल, चयापचय और वार्षिक प्रतिरोधक क्षमता।',
    noteEn: 'Named formulations lower novelty — combining actives with a novel process restores it.',
    noteHi: 'प्रचलित नाम से नवीनता घटती है — अभिनव प्रक्रिया से सक्रिय पदार्थ मिलाने से यह लौटती है।',
    facts: [
      { en: 'Immunity', hi: 'प्रतिरोधक क्षमता' },
      { en: 'Fever care', hi: 'ज्वर देखभाल' },
      { en: 'Metabolism', hi: 'चयापचय' },
    ],
  },
];

export default function ScrollingHerbs() {
  const { lang } = useLang();
  const Hi = (en: string, hi: string) => (lang === 'hi' ? hi : en);
  const [index, setIndex] = useState(-1);
  const [openKey, setOpenKey] = useState<string | null>(null);
  const [hint, setHint] = useState(true);

  useEffect(() => {
    let raf = 0;
    const update = () => {
      cancelAnimationFrame(raf);
      raf = requestAnimationFrame(() => {
        const doc = document.documentElement;
        const max = doc.scrollHeight - window.innerHeight;
        const p = max > 0 ? window.scrollY / max : 0;
        const idx = Math.min(HERBS.length - 1, Math.max(0, Math.floor(p * HERBS.length)));
        setIndex(idx);
      });
    };
    update();
    window.addEventListener('scroll', update, { passive: true });
    window.addEventListener('resize', update);
    const t = setTimeout(() => setHint(false), 7000);
    return () => {
      window.removeEventListener('scroll', update);
      window.removeEventListener('resize', update);
      cancelAnimationFrame(raf);
      clearTimeout(t);
    };
  }, []);

  const herb = index >= 0 ? HERBS[index] : null;
  const isLeft = index % 2 === 0;
  const open = herb ? HERBS.find((h) => h.key === openKey) || null : null;

  return (
    <>
      {/* Scroll-triggered herb layer (one at a time, alternating sides) */}
      <div className="pointer-events-none fixed inset-0 z-30" aria-hidden={open ? true : false}>
        {herb && (
          <button
            type="button"
            onClick={() => setOpenKey(openKey === herb.key ? null : herb.key)}
            className={`pointer-events-auto group absolute top-[24%] flex items-center gap-2 focus:outline-none transition-all duration-[750ms] ease-out will-change-transform ${
              isLeft ? 'left-2 sm:left-4 lg:left-8' : 'right-2 sm:right-4 lg:right-8'
            } ${openKey === herb.key ? 'scale-95 opacity-90' : 'opacity-100 hover:scale-105'}`}
          >
            <span className={`rounded-full bg-gradient-to-br ${herb.color} shadow-lg shadow-black/20 ring-2 ring-white/80 flex items-center justify-center animate-float w-12 h-12 sm:w-14 sm:h-14`}>
              <Leaf className="text-white w-6 h-6 sm:w-7 sm:h-7 drop-shadow" />
            </span>
            <span className="bg-white/95 backdrop-blur border border-slate-200 rounded-full px-3 py-1 text-[11px] font-bold text-slate-800 shadow-md shadow-slate-900/10 hidden sm:inline-flex">
              {Hi(herb.en, herb.hi)}
              <span className="text-emerald-600 ml-1.5">· {herb.latin.split(' ')[0]}</span>
            </span>
          </button>
        )}

        {/* Info panel for the active herb (same side as the herb) */}
        <div
          className={`pointer-events-auto fixed top-[30%] z-40 w-[290px] max-w-[82vw] transition-all duration-[750ms] ease-out ${
            isLeft ? 'left-2 sm:left-4 lg:left-10' : 'right-2 sm:right-4 lg:right-10'
          }`}
          style={{
            opacity: open ? 1 : 0,
            transform: open ? 'translateY(0) scale(1)' : isLeft ? 'translateY(24px) scale(0.96)' : 'translateY(24px) scale(0.96)',
            pointerEvents: open ? 'auto' : 'none',
          }}
        >
          {open && (
            <div className="rounded-2xl bg-white/95 backdrop-blur-xl border border-slate-200 shadow-2xl shadow-slate-900/20 overflow-hidden">
              <div className={`bg-gradient-to-br ${open.color} px-4 py-3 flex items-start justify-between gap-2`}>
                <div>
                  <div className="text-white font-black text-base leading-tight">{Hi(open.en, open.hi)}</div>
                  <div className="text-white/85 text-[11px] italic font-medium">{open.latin}</div>
                </div>
                <button type="button" onClick={() => setOpenKey(null)} className="text-white/85 hover:text-white bg-white/15 hover:bg-white/25 rounded-full p-1.5 transition" aria-label="Close">
                  <X className="w-3.5 h-3.5" />
                </button>
              </div>
              <div className="p-4 space-y-3">
                <p className="text-xs text-slate-600 leading-relaxed">{Hi(open.descEn, open.descHi)}</p>
                <div className="flex flex-wrap gap-1.5">
                  {open.facts.map((f, i) => (
                    <span key={i} className="px-2.5 py-1 rounded-full bg-emerald-50 border border-emerald-200 text-[10px] font-semibold text-emerald-700">
                      {Hi(f.en, f.hi)}
                    </span>
                  ))}
                </div>
                <div className="flex items-start gap-2 rounded-xl bg-violet-50 border border-violet-200 px-3 py-2.5">
                  <BookOpen className="w-3.5 h-3.5 text-violet-600 mt-0.5 flex-shrink-0" />
                  <p className="text-[10.5px] text-violet-700 leading-snug">{Hi(open.noteEn, open.noteHi)}</p>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* First-visit hint */}
      {hint && !open && (
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-40 pointer-events-none animate-fade-in-up">
          <div className="flex items-center gap-2 px-4 py-2.5 rounded-full bg-white/95 backdrop-blur border border-emerald-200 shadow-lg shadow-emerald-900/10 text-[11px] font-semibold text-emerald-800">
            <ScrollText className="w-3.5 h-3.5" />
            {Hi('Scroll — botanicals appear one at a time. Tap one for its story.', 'स्क्रॉल करें — वनस्पतियाँ एक-एक करके प्रकट होंगी। किसी पर टैप करें।')}
          </div>
        </div>
      )}
    </>
  );
}