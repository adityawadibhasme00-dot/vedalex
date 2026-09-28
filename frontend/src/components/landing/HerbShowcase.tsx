'use client';
import React, { useEffect, useRef, useState } from 'react';
import { Leaf, BookOpen, ChevronDown } from 'lucide-react';
import { useLang } from '../../lib/LangContext';

interface HerbEntry {
  key: string;
  en: string;
  hi: string;
  latin: string;
  image: string;
  accent: string;
  accentBg: string;
  accentBorder: string;
  descEn: string;
  descHi: string;
  usesEn: string[];
  usesHi: string[];
  patentNoteEn: string;
  patentNoteHi: string;
}

const HERBS: HerbEntry[] = [
  {
    key: 'tulsi',
    en: 'Tulsi',
    hi: 'तुलसी',
    latin: 'Ocimum sanctum',
    image: 'https://images.unsplash.com/photo-1615485500704-8e990f9900f7?w=800&q=80&auto=format',
    accent: 'from-emerald-700 to-green-500',
    accentBg: 'bg-emerald-50',
    accentBorder: 'border-emerald-300',
    descEn: 'The sacred "Queen of Herbs" — a powerful adaptogen revered for boosting immunity, respiratory health and mental clarity.',
    descHi: 'पवित्र "हर्ब्स की रानी" — शक्तिशाली एडाप्टोजन जो प्रतिरोधक क्षमता, श्वसन स्वास्थ्य और मानसिक स्पष्टता को बढ़ाता है।',
    usesEn: ['Immunity booster', 'Respiratory wellness', 'Stress relief', 'Antioxidant rich'],
    usesHi: ['प्रतिरोधक क्षमता', 'श्वसन स्वास्थ्य', 'तनाव निवारण', 'एंटीऑक्सीडेंट'],
    patentNoteEn: 'IP-SAKTI maps Tulsi to its Ayurvedic Pharmacopoeia (API) monograph for Section 3(p) screening — every claim is traced to a verified botanical source.',
    patentNoteHi: 'IP-SAKTI तुलसी को सेक्शन 3(p) जाँच हेतु आयुर्वेदिक फार्माकोपिया (API) मोनोग्राफ से जोड़ता है — हर दावा सत्यापित वनस्पति स्रोत से जुड़ा है।',
  },
  {
    key: 'ashwagandha',
    en: 'Ashwagandha',
    hi: 'अश्वगंधा',
    latin: 'Withania somnifera',
    image: 'https://images.unsplash.com/photo-1611241893603-3c359704e0ee?w=800&q=80&auto=format',
    accent: 'from-amber-700 to-yellow-500',
    accentBg: 'bg-amber-50',
    accentBorder: 'border-amber-300',
    descEn: 'The "Strength of a Horse" root — premier adaptogen for sustained energy, balanced cortisol and deep restorative sleep.',
    descHi: '"घोड़े की ताकत" वाली जड़ — निरंतर ऊर्जा, संतुलित कोर्टिसोल और गहरी नींद के लिए प्रमुख एडाप्टोजन।',
    usesEn: ['Energy & stamina', 'Sleep support', 'Cortisol balance', 'Muscle recovery'],
    usesHi: ['ऊर्जा व सहनशक्ति', 'नींद सहायता', 'कोर्टिसोल संतुलन', 'मांसपेशी रिकवरी'],
    patentNoteEn: 'Common TKDL entry — novel formulation + synergistic claims raise your patent readiness score automatically.',
    patentNoteHi: 'सामान्य TKDL प्रविष्टि — नवीन फॉर्मूलेशन और सहक्रियात्मक दावे स्वतः तैयारी स्कोर बढ़ाते हैं।',
  },
  {
    key: 'brahmi',
    en: 'Brahmi',
    hi: 'ब्राह्मी',
    latin: 'Bacopa monnieri',
    image: 'https://images.unsplash.com/photo-1598532163257-ae3c6b2524b6?w=800&q=80&auto=format',
    accent: 'from-teal-700 to-cyan-500',
    accentBg: 'bg-teal-50',
    accentBorder: 'border-teal-300',
    descEn: 'The classical "Brain Tonic" — a Medhya rasayana sharpening memory, focus and cognitive performance across all ages.',
    descHi: 'शास्त्रीय "ब्रेन टॉनिक" — मेध्या रसायन जो सभी आयु समूहों में स्मृति, एकाग्रता और संज्ञानात्मक प्रदर्शन तेज करता है।',
    usesEn: ['Memory enhancement', 'Focus & clarity', 'Learning support', 'Neuroprotection'],
    usesHi: ['स्मृति वृद्धि', 'एकाग्रता', 'शिक्षण सहायता', 'न्यूरोप्रोटेक्शन'],
    patentNoteEn: 'Classical mention increases Section 3(p) scrutiny — IP-SAKTI builds narrative evidence to overcome objections.',
    patentNoteHi: 'शास्त्रीय उल्लेख से सेक्शन 3(p) जाँच गहरी होती है — IP-SAKTI आपत्तियों को दूर करने हेतु कथात्मक साक्ष्य बनाता है।',
  },
  {
    key: 'haldi',
    en: 'Turmeric · Haldi',
    hi: 'हल्दी',
    latin: 'Curcuma longa',
    image: 'https://images.unsplash.com/photo-1615484477778-ca3b77940c25?w=800&q=80&auto=format',
    accent: 'from-orange-700 to-amber-500',
    accentBg: 'bg-orange-50',
    accentBorder: 'border-orange-300',
    descEn: 'The Golden Rhizome — curcumin-rich anti-inflammatory powering wellness, cosmetics and functional food innovations.',
    descHi: 'सुनहरा प्रकंद — कर्क्यूमिन-युक्त सूजनरोधी जो स्वास्थ्य, सौंदर्य और कार्यात्मक खाद्य नवाचारों को संचालित करता है।',
    usesEn: ['Anti-inflammatory', 'Joint health', 'Digestive support', 'Skin radiance'],
    usesHi: ['सूजनरोधी', 'जोड़ स्वास्थ्य', 'पाचन सहायता', 'त्वचा चमक'],
    patentNoteEn: 'Nano/liposomal curcumin delivery crosses Section 3(p) with demonstrated bioenhancement — IP-SAKTI maps each claim to TKDL.',
    patentNoteHi: 'नैनो/लिपोसोमल कर्क्यूमिन वितरण, बायोएन्हांसमेंट प्रदर्शन के साथ सेक्शन 3(p) पार करता है — IP-SAKTI हर दावे को TKDL से जोड़ता है।',
  },
  {
    key: 'neem',
    en: 'Neem',
    hi: 'नीम',
    latin: 'Azadirachta indica',
    image: 'https://images.unsplash.com/photo-1597848212624-a19eb35e2651?w=800&q=80&auto=format',
    accent: 'from-green-800 to-emerald-500',
    accentBg: 'bg-green-50',
    accentBorder: 'border-green-300',
    descEn: 'The "Village Pharmacy" tree — purifying leaf, bark and seed oil powering skin care, blood purification and oral hygiene.',
    descHi: '"गाँव की फ़ार्मेसी" वृक्ष — शुद्धिकारक पत्ती, छाल और बीज तेल जो त्वचा देखभाल, रक्त शोधन और मौखिक स्वच्छता को संचालित करता है।',
    usesEn: ['Skin purifier', 'Blood detox', 'Oral care', 'Antifungal'],
    usesHi: ['त्वचा शोधक', 'रक्त विषाक्तता', 'मौखिक देखभाल', 'एंटीफंगल'],
    patentNoteEn: 'Neem extracts are heavily patented — IP-SAKTI\'s prior-art engine flags overlapping cliffs early to safeguard your filing.',
    patentNoteHi: 'नीम के अर्क पर कई पेटेंट हैं — IP-SAKTI का पूर्व-आधार इंजन अतिव्यापी क्लिफ्स पहले ही चिह्नित करता है।',
  },
  {
    key: 'amla',
    en: 'Amla',
    hi: 'आंवला',
    latin: 'Phyllanthus emblica',
    image: 'https://images.unsplash.com/photo-1607623814075-e51df1bdc82f?w=800&q=80&auto=format',
    accent: 'from-lime-700 to-green-500',
    accentBg: 'bg-lime-50',
    accentBorder: 'border-lime-300',
    descEn: 'The Vitamin C powerhouse berry — nature\'s most concentrated Rasayana for digestion, immunity and radiant skin.',
    descHi: 'विटामिन C का शक्तिशाली फल — प्रकृति का सबसे सघन रसायन पाचन, प्रतिरोधक क्षमता और चमकदार त्वचा के लिए।',
    usesEn: ['Vitamin C rich', 'Digestive tonic', 'Hair & skin', 'Iron absorption'],
    usesHi: ['विटामिन C युक्त', 'पाचन टॉनिक', 'बाल व त्वचा', 'आयरन अवशोषण'],
    patentNoteEn: 'Priority herbal ingredient — origin data captured in Innovation Passport for full traceability.',
    patentNoteHi: 'प्राथमिक घटक — स्रोतक्षेत्र की जानकारी इनोवेशन पासपोर्ट में पूर्ण अनुगमन हेतु अंकित की जाती है।',
  },
];

function useScrollReveal(threshold = 0.15) {
  const ref = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const obs = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setVisible(true);
          obs.unobserve(el);
        }
      },
      { threshold, rootMargin: '0px 0px -60px 0px' }
    );
    obs.observe(el);
    return () => obs.disconnect();
  }, [threshold]);

  return { ref, visible };
}

function HerbCard({ herb, index }: { herb: HerbEntry; index: number }) {
  const { lang } = useLang();
  const Hi = (en: string, hi: string) => (lang === 'hi' ? hi : en);
  const { ref, visible } = useScrollReveal(0.12);
  const isEven = index % 2 === 0;

  return (
    <div ref={ref} className="relative py-8 md:py-12">
      {/* Background glow */}
      <div
        className={`absolute inset-0 opacity-0 transition-opacity duration-1000 ${visible ? 'opacity-100' : ''}`}
        aria-hidden="true"
      >
        <div className={`absolute top-1/2 ${isEven ? 'left-0' : 'right-0'} -translate-y-1/2 w-[400px] h-[400px] bg-gradient-to-br ${herb.accent} rounded-full blur-[120px] opacity-[0.06]`} />
      </div>

      <div className={`relative flex flex-col ${isEven ? 'lg:flex-row' : 'lg:flex-row-reverse'} items-center gap-8 lg:gap-14`}>
        {/* Image side */}
        <div className="w-full lg:w-[45%] relative">
          <div
            className={`relative rounded-3xl overflow-hidden shadow-2xl shadow-black/10 transition-all duration-[1200ms] ease-out ${
              visible
                ? 'opacity-100 translate-y-0 scale-100'
                : 'opacity-0 translate-y-12 scale-90'
            }`}
          >
            {/* Image container with grow effect */}
            <div className="relative aspect-[4/5] md:aspect-[3/4] overflow-hidden">
              <img
                src={herb.image}
                alt={Hi(herb.en, herb.hi)}
                className={`w-full h-full object-cover transition-all duration-[1800ms] ease-out ${
                  visible ? 'scale-100' : 'scale-110'
                }`}
                loading="lazy"
              />
              {/* Gradient overlay */}
              <div className="absolute inset-0 bg-gradient-to-t from-black/40 via-transparent to-transparent" />

              {/* Floating badge on image */}
              <div
                className={`absolute top-4 ${isEven ? 'left-4' : 'right-4'} transition-all duration-700 delay-500 ${
                  visible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'
                }`}
              >
                <span className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-white/90 backdrop-blur-sm text-[11px] font-bold text-slate-800 shadow-lg`}>
                  <Leaf className="w-3.5 h-3.5 text-emerald-600" />
                  {herb.latin}
                </span>
              </div>

              {/* Bottom info on image */}
              <div className="absolute bottom-0 left-0 right-0 p-5 md:p-6">
                <h4 className="text-white text-2xl md:text-3xl font-black font-display drop-shadow-lg">
                  {Hi(herb.en, herb.hi)}
                </h4>
              </div>
            </div>
          </div>

          {/* Decorative elements */}
          <div
            className={`absolute -z-10 transition-all duration-[1400ms] delay-200 ${
              visible ? 'opacity-100' : 'opacity-0'
            } ${isEven ? '-bottom-4 -right-4' : '-bottom-4 -left-4'}`}
          >
            <div className={`w-24 h-24 rounded-2xl bg-gradient-to-br ${herb.accent} opacity-20 rotate-12`} />
          </div>
          <div
            className={`absolute -z-10 transition-all duration-[1400ms] delay-300 ${
              visible ? 'opacity-100' : 'opacity-0'
            } ${isEven ? '-top-3 -left-3' : '-top-3 -right-3'}`}
          >
            <div className={`w-16 h-16 rounded-xl bg-gradient-to-br ${herb.accent} opacity-15 -rotate-6`} />
          </div>
        </div>

        {/* Content side */}
        <div className="w-full lg:w-[55%] space-y-6">
          {/* Name and Latin */}
          <div
            className={`transition-all duration-700 delay-200 ${
              visible ? 'opacity-100 translate-x-0' : `opacity-0 ${isEven ? '-translate-x-8' : 'translate-x-8'}`
            }`}
          >
            <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-lg bg-gradient-to-r ${herb.accent} text-white text-[10px] font-bold uppercase tracking-wider mb-3`}>
              <Leaf className="w-3 h-3" />
              {Hi('Ayurvedic Herb', 'आयुर्वेदिक औषधि')}
            </span>
            <h3 className="text-3xl md:text-4xl font-black text-slate-900 font-display">
              {Hi(herb.en, herb.hi)}
            </h3>
            <p className="text-sm text-slate-400 italic mt-1">{herb.latin}</p>
          </div>

          {/* Description */}
          <p
            className={`text-[15px] text-slate-600 leading-relaxed max-w-lg transition-all duration-700 delay-300 ${
              visible ? 'opacity-100 translate-x-0' : `opacity-0 ${isEven ? '-translate-x-6' : 'translate-x-6'}`
            }`}
          >
            {Hi(herb.descEn, herb.descHi)}
          </p>

          {/* Uses tags */}
          <div
            className={`flex flex-wrap gap-2 transition-all duration-700 delay-[400ms] ${
              visible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'
            }`}
          >
            {(lang === 'hi' ? herb.usesHi : herb.usesEn).map((use, i) => (
              <span
                key={use}
                className={`px-3 py-1.5 rounded-full text-[11px] font-bold border ${herb.accentBg} ${herb.accentBorder} text-slate-700 transition-all duration-500`}
                style={{ transitionDelay: `${500 + i * 80}ms` }}
              >
                {use}
              </span>
            ))}
          </div>

          {/* Patent note card */}
          <div
            className={`rounded-2xl border-2 border-dashed ${herb.accentBorder} ${herb.accentBg} p-5 transition-all duration-700 delay-500 ${
              visible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-6'
            }`}
          >
            <div className="flex items-start gap-3">
              <div className={`w-9 h-9 rounded-xl bg-gradient-to-br ${herb.accent} flex items-center justify-center flex-shrink-0 mt-0.5`}>
                <BookOpen className="w-4 h-4 text-white" />
              </div>
              <div>
                <div className="text-[11px] font-bold uppercase tracking-wider text-slate-500 mb-1">
                  {Hi('IP-SAKTI Patent Insight', 'IP-SAKTI पेटेंट जानकारी')}
                </div>
                <p className="text-[13px] text-slate-600 leading-relaxed">
                  {Hi(herb.patentNoteEn, herb.patentNoteHi)}
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function HerbShowcase() {
  const { lang } = useLang();
  const Hi = (en: string, hi: string) => (lang === 'hi' ? hi : en);
  const { ref: headerRef, visible: headerVisible } = useScrollReveal(0.2);

  return (
    <section id="herbs" className="scroll-mt-20 relative">
      {/* Section header */}
      <div ref={headerRef} className="text-center max-w-2xl mx-auto mb-6 md:mb-10">
        <span
          className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-lg bg-emerald-800 text-white text-[10px] font-bold uppercase tracking-wider mb-4 transition-all duration-600 ${
            headerVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'
          }`}
        >
          <Leaf className="w-3 h-3" />
          {Hi('Ayurvedic Botanicals', 'आयुर्वेदिक वनस्पतियाँ')}
        </span>
        <h3
          className={`text-3xl md:text-4xl font-black text-emerald-900 font-display transition-all duration-700 delay-100 ${
            headerVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-6'
          }`}
        >
          {Hi('Rooted in Ancient Wisdom', 'प्राचीन ज्ञान में जड़ें')}
        </h3>
        <p
          className={`mt-3 text-sm text-slate-600 max-w-lg mx-auto transition-all duration-700 delay-200 ${
            headerVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'
          }`}
        >
          {Hi(
            'Explore the herbs that form the backbone of Ayurveda — each one IP-verified, TKDL-mapped and ready for innovation.',
            'उन जड़ी-बूटियों को जानें जो आयुर्वेद की रीढ़ हैं — हर एक IP-सत्यापित, TKDL-मैप्ड और नवाचार के लिए तैयार।'
          )}
        </p>
      </div>

      {/* Scroll hint */}
      <div className="flex justify-center mb-6 md:mb-10">
        <div className="flex items-center gap-2 px-4 py-2 rounded-full bg-white border border-emerald-200 shadow-sm text-[11px] font-semibold text-emerald-700 animate-bounce">
          <ChevronDown className="w-4 h-4" />
          {Hi('Scroll to explore each herb', 'प्रत्येक जड़ी-बूटी जानने के लिए स्क्रॉल करें')}
        </div>
      </div>

      {/* Herb cards */}
      <div className="space-y-4 md:space-y-8">
        {HERBS.map((herb, i) => (
          <HerbCard key={herb.key} herb={herb} index={i} />
        ))}
      </div>
    </section>
  );
}
