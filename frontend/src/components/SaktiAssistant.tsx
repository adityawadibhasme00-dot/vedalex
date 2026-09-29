'use client';

import React, { useRef, useState, useEffect } from 'react';
import { Bot, Send, X, Sparkles, ChevronDown, Radar, FileDown, RefreshCw, MessageSquare } from 'lucide-react';
import { AyurvedaSeal } from './BotanicalDecor';
import { t } from '../lib/i18n';

interface SaktiAssistantProps {
  lang?: string;
  passportId?: string;
  passportTitle?: string;
  readiness?: number | null;
  onNavigate: (tab: string) => void;
  onQuickAction: (action: 'evaluate' | 'export' | 'whatif' | 'copilot') => void;
}

interface ChatMsg {
  id: number;
  role: 'bot' | 'user';
  text: string;
}

const TAB_ALIASES: Array<{ tab: string; keys: string[] }> = [
  { tab: 'overview', keys: ['overview', 'home', 'dashboard', 'main', 'landing', 'डैशबोर्ड'] },
  { tab: 'passport', keys: ['passport', 'innovation passport', 'create passport', 'passport khol', 'पासपोर्ट'] },
  { tab: 'patent', keys: ['patent', 'patentability', 'novelty', 'readiness', 'पेटेंट', 'फ्रीडम'] },
  { tab: 'evidence', keys: ['evidence', 'matrix', 'gap', 'evidence khol', 'साक्ष्य'] },
  { tab: 'copilot', keys: ['copilot', 'ai', 'chat', 'ask', 'assistant', 'copilot khol', 'पूछो'] },
  { tab: 'dossier', keys: ['dossier', 'document', 'report', 'checklist', 'डोसियर'] },
  { tab: 'matrix', keys: ['jurisdiction', 'matrix country', 'usa rules', 'india rules', 'jurisdiction khol'] },
  { tab: 'provenance', keys: ['provenance', 'abs', 'bio-resource', 'biolog', 'ledger', 'lineage', 'source khol'] },
  { tab: 'fto', keys: ['fto', 'freedom', 'infringe'] },
  { tab: 'doc_analyzer', keys: ['ocr', 'upload', 'document analyzer', 'sanitize', 'file khol'] },
  { tab: 'whatif', keys: ['what if', 'whatif', 'simulate', 'simulation', 'mutate', 'diff'] },
  { tab: 'settings', keys: ['settings', 'profile', 'preference', 'सेटिंग्स'] },
];

const HELP_KEY = 'sa_help_body';

const DEFAULT_KB_STATUS: Array<{ keys: string[]; text?: string; tab?: string }> = [
  {
    keys: ['3(p)', '3 p', 'section 3', 'section3', 'sec 3', 'patentable'],
    text:
      'Section 3(p) — Indian Patents Act, 1970:\n\n' +
      'Section 3(p) excludes scientific principles, "mere admixture", and known properties. An Ayurvedic formulation that only combines known ingredients without producing a new synergistic effect is not patentable.\n\n' +
      'What to do: patentability depends on proving a synergistic or additive effect. IP-SAKTI flags this in the Patent tab under Patent Analysis + Section 3(p).',
    tab: 'patent',
  },
  {
    keys: ['abs', 'bio resource', 'bio-resource', 'biological resource', 'nba', 'access benefit'],
    text:
      'ABS (Access & Benefit Sharing):\n\n' +
      'Under the Biological Diversity Act, for every ingredient (e.g. Ashwagandha, Brahmi) the system tracks which state in India it came from, who the supplier is, and whether benefit sharing with the NBA / State Biodiversity Board has been recorded.\n\n' +
      'You will find this in your passport\'s Provenance tab and in the "Bio-Resource Ledger" Feature Hub card. Recommendation: set the supplier and ABS status first.',
    tab: 'provenance',
  },
  {
    keys: ['tkdl', 'traditional knowledge', 'prior art', 'neem', 'haldi', 'turmeric', 'charaka'],
    text:
      'TKDL (Traditional Knowledge Digital Library):\n\n' +
      'Formulations from classical granths (Charaka Samhita, Sushruta Samhita, neem–haldi cases and similar) are recorded in TKDL as prior art. If your claim matches a classical text, foreign offices (EPO / USPTO) can reject or short-circuit the application on TKDL grounds.\n\n' +
      'The full picture appears under Patent Analysis + TKDL screening.',
    tab: 'patent',
  },
  {
    keys: ['schedule t', 'gmp', 'ayush', 'ayurveda manufacture', 'manufacturing'],
    text:
      'Schedule T (Drugs & Cosmetics Rules):\n\n' +
      'Manufacturing Ayurvedic medicine requires Schedule T GMP (Good Manufacturing Practices) — premises, equipment, sanitisation and QA records are all defined. Schedule T container and labelling requirements (the ingredient list on the pack) apply as well.\n\n' +
      'This is reflected in the India compliance column of the Jurisdiction Matrix.',
    tab: 'matrix',
  },
  {
    keys: ['schedule e', 'toxic', 'poison', 'restrict', 'banned'],
    text:
      'Schedule E:\n\n' +
      'Schedule E(1) lists Ayurvedic substances that are subject to control or restrictions (toxic or purificatory processes). If your formula contains a Schedule E ingredient, you need a purification SOP plus dosage guidance.\n\n' +
      'Check every ingredient in your formulation against the claim list — the Evidence Matrix shows CAP safety flags.',
    tab: 'evidence',
  },
  {
    keys: ['fssai', 'food', 'aahara', 'nutraceutical', 'supplement india', 'ayurveda food'],
    text:
      'FSSAI (Ayurvedic Aahara / Nutraceuticals):\n\n' +
      'If the product is food-like (Aahara or a health supplement), FSSAI Schedule IV (claims for Ayurvedic Aahara) or the Nutraceutical regulations apply — it is not a drug. Health claims (e.g. "for better sleep") are only allowed within the prescribed wording.\n\n' +
      'In the India matrix this is covered as a separate column.',
    tab: 'matrix',
  },
  {
    keys: ['dshea', 'usa', 'united states', 'fda usa', 'american market', 'us market', 'america'],
    text:
      'United States (DSHEA / FDA):\n\n' +
      'If the product is a dietary supplement in the US, the DSHEA structure applies to marketing (seller-regulated, no pre-market approval) along with cGMP (21 CFR 111). Any claim that prevents or cures a disease is treated as a drug claim, which triggers New Drug Investigation (NDI) and food additive requirements.\n\n' +
      'The label needs a safety statement and the FDA disclaimer. The Jurisdiction Matrix shows the US requirements.',
    tab: 'matrix',
  },
  {
    keys: ['canada', 'nhp', 'npn', 'health canada', 'licensed natural'],
    text:
      'Canada (NHP / NPN):\n\n' +
      'In Canada you need a Site Licence and a Product Licence from the Natural Health Products Directorate. Every NHP is assigned an NPN number, and claims are permitted only within the prescribed risk-based categories.\n\n' +
      'Canada requirements are visible in the matrix.',
    tab: 'matrix',
  },
  {
    keys: ['who', 'monograph', 'gmp who', 'icmr', 'clinical', 'evidence study'],
    text:
      'Evidence & WHO Monographs:\n\n' +
      'To strengthen a claim, use WHO quality monographs, classical granths, and key clinical studies (ICMR / TKI marked). Strong evidence means a reproducible study plus peer review. The Evidence Matrix shows a red flag wherever evidence is missing.\n\n' +
      'The evidence status for every claim is in the Evidence Matrix tab.',
    tab: 'evidence',
  },
  {
    keys: ['status', 'kitna', 'kya haal', 'hal', 'current', 'progress', 'next step', 'next action'],
  },
];

const KB: Array<{ keys: string[]; text: string; tab?: string }> = DEFAULT_KB_STATUS.filter(
  (e): e is { keys: string[]; text: string; tab?: string } => typeof e.text === 'string',
);

const UNIQUE_SCRIPTS: Array<{ lang: string; re: RegExp }> = [
  { lang: 'bn', re: /[\u0980-\u09FF]/ },
  { lang: 'gu', re: /[\u0A80-\u0AFF]/ },
  { lang: 'ta', re: /[\u0B80-\u0BFF]/ },
  { lang: 'te', re: /[\u0C00-\u0C7F]/ },
  { lang: 'kn', re: /[\u0C80-\u0CFF]/ },
  { lang: 'ml', re: /[\u0D00-\u0D7F]/ },
];

const DEVANAGARI = /[\u0900-\u097F]/;
const DEVANAGARI_LANGS = ['hi', 'mr', 'sa'];

function detectLang(text: string, fallback: string): string {
  for (const entry of UNIQUE_SCRIPTS) {
    if (entry.re.test(text)) return entry.lang;
  }
  if (DEVANAGARI.test(text)) {
    return DEVANAGARI_LANGS.includes(fallback) ? fallback : 'hi';
  }
  return fallback;
}

function findTab(text: string): { tab: string; keys: string[] } | null {
  const low = text.toLowerCase();
  for (const alias of TAB_ALIASES) {
    if (alias.keys.some((k) => low.includes(k))) return alias;
  }
  return null;
}

function findKB(text: string): string | null {
  const low = text.toLowerCase();
  for (const entry of KB) {
    if (entry.text && entry.keys.some((k) => low.includes(k))) return entry.text;
  }
  return null;
}

export default function SaktiAssistant({
  lang = 'en',
  passportId,
  passportTitle,
  readiness,
  onNavigate,
  onQuickAction,
}: SaktiAssistantProps) {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMsg[]>([]);
  const [input, setInput] = useState('');
  const [thinking, setThinking] = useState(false);
  const idRef = useRef(0);
  const scrollRef = useRef<HTMLDivElement>(null);

  const push = (msgs: ChatMsg[]) => {
    setMessages((prev) => [...prev, ...msgs]);
  };

  useEffect(() => {
    if (!open) return;
    const statusParts: string[] = [];
    if (passportTitle) statusParts.push(`${t('sa_passport_lbl', lang)} "${passportTitle.slice(0, 44)}${passportTitle.length > 44 ? '…' : ''}"`);
    if (typeof readiness === 'number') statusParts.push(`${t('sa_readiness_lbl', lang)} ${readiness}%`);
    if (passportId) statusParts.push(t('sa_assess_ready', lang));
    const statusLine = statusParts.length ? `\n\n${statusParts.join('  ·  ')}` : t('sa_no_passport', lang);
    const greeting = t('sa_greet', lang) + t('sa_greet_cap', lang) + statusLine;
    if (messages.length === 0) {
      push([
        { id: idRef.current++, role: 'bot', text: greeting },
        { id: idRef.current++, role: 'bot', text: t('sa_greet_ask', lang) },
      ]);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [messages, thinking]);

  const submit = (raw?: string) => {
    const text = (raw ?? input).trim();
    if (!text || thinking) return;
    setInput('');
    push([{ id: idRef.current++, role: 'user', text }]);
    setThinking(true);

    const low = text.toLowerCase();
    const runExpr = /\b(?:run|start|do|chal|karo|chalao|evaluate|assessment|analysis)\b/.test(low);
    const exportExpr = /(?:export|dossier|pdf|download|kar|banao)/.test(low) && !/open|khol/.test(low);

    const rlang = detectLang(text, lang);
    const tr = (key: string) => t(key, rlang);
    const fill = (s: string, pairs: Array<[string, string]>) => pairs.reduce((acc, [k, v]) => acc.split(k).join(v), s);

    setTimeout(() => {
      let reply: ChatMsg[] = [];

      const tabHit = findTab(text);
      if (tabHit && /open|khol|khole|kholo|dikha|show|go to|ja|navigate|le jao|open karo|kholke/i.test(low)) {
        onNavigate(tabHit.tab);
        reply = [{ id: idRef.current++, role: 'bot', text: fill(tr('sa_reply_open_tab'), [['{tab}', tabHit.tab]]) }];
      } else if (exportExpr && /dossier|export|pdf|download/i.test(low)) {
        onQuickAction('export');
        reply = [{ id: idRef.current++, role: 'bot', text: tr('sa_reply_export') }];
      } else if (runExpr && /\b(?:assessment|evaluate|analysis|readiness)\b/.test(low)) {
        onQuickAction('evaluate');
        reply = [{ id: idRef.current++, role: 'bot', text: tr('sa_reply_evaluate') }];
      } else if (/what\s*-?\s*if|simulat/i.test(low)) {
        onNavigate('whatif');
        reply = [{ id: idRef.current++, role: 'bot', text: tr('sa_reply_whatif') }];
      } else if (/help|madad|saksham|kya kar|kya kr|features|can you do|kye kar/i.test(low)) {
        reply = [{ id: idRef.current++, role: 'bot', text: tr(HELP_KEY) }];
      } else if (/status|kitna|hal|current|progress|next/i.test(low)) {
        const statusParts: string[] = [];
        if (passportTitle) statusParts.push(fill(tr('sa_status_passport'), [['{title}', passportTitle.slice(0, 44)]]));
        if (typeof readiness === 'number') statusParts.push(fill(tr('sa_status_readiness'), [['{n}', String(readiness)]]));
        if (passportId) statusParts.push(tr('sa_status_ready'));
        reply = [{
          id: idRef.current++,
          role: 'bot',
          text: tr('sa_reply_status_head') + '\n\n' + (statusParts.length ? statusParts.join('\n') : tr('sa_status_none')) + '\n\n' + tr('sa_status_next'),
        }];
      } else {
        const kbAnswer = findKB(text);
        if (kbAnswer) {
          const tab = TAB_ALIASES.find((t) => kbAnswer && t.keys.some((k) => low.includes(k)));
          const note = tab && tab.tab !== 'overview'
            ? '\n\n' + fill(tr('sa_kb_open_tab'), [['{tab}', tab.tab]])
            : '';
          const langNote = rlang === 'en' ? '' : tr('sa_en_note') + '\n\n';
          reply = [{ id: idRef.current++, role: 'bot', text: langNote + kbAnswer + note }];
        } else {
          reply = [{ id: idRef.current++, role: 'bot', text: tr('sa_fallback') }];
        }
      }
      setThinking(false);
      push(reply);
    }, 600);
  };

  const chips = [
    { label: t('sa_chip_status', lang), act: () => submit('status batao') },
    { label: t('sa_chip_copilot', lang), act: () => submit('open copilot') },
    { label: t('sa_chip_abs', lang), act: () => submit('abs kya hai') },
    { label: t('sa_chip_export', lang), act: () => submit('dossier export karo') },
    { label: t('sa_chip_3p', lang), act: () => submit('what is section 3(p)') },
  ];

  return (
    <div className="fixed bottom-6 right-6 z-40 flex flex-col items-end pointer-events-none">
      {open && (
        <div className="mb-3 w-[360px] max-w-[calc(100vw-3rem)] h-[440px] max-h-[70vh] flex flex-col glass-panel rounded-2xl border border-emerald-500/40 shadow-2xl overflow-hidden animate-slide-up pointer-events-auto">
          <div className="flex items-center justify-between px-4 py-3 bg-gradient-to-r from-emerald-600 to-emerald-700 text-white">
            <div className="flex items-center gap-2.5">
              <AyurvedaSeal className="w-7 h-7 text-white/90" />
              <div>
                <div className="text-sm font-bold font-display flex items-center gap-1.5">IP-SAKTI Assistant</div>
                <div className="text-[10px] text-emerald-100 flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-lime-300 animate-pulse" /> {t('sa_online', lang)}
                </div>
              </div>
            </div>
            <button onClick={() => setOpen(false)} className="p-1.5 rounded-lg hover:bg-white/20 transition" aria-label={t('sa_close', lang)}>
              <X className="w-4 h-4" />
            </button>
          </div>

          <div ref={scrollRef} className="flex-1 overflow-y-auto p-3 space-y-2.5 bg-white/70">
            {messages.map((m) => (
              <div key={m.id} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`max-w-[85%] px-3 py-2 text-xs leading-relaxed whitespace-pre-line rounded-2xl ${
                  m.role === 'user'
                    ? 'bg-emerald-600 text-white rounded-br-sm'
                    : 'bg-white border border-emerald-100 text-slate-700 rounded-bl-sm shadow-sm'
                }`}>
                  {m.text}
                </div>
              </div>
            ))}
            {thinking && (
              <div className="flex justify-start">
                <div className="px-3 py-2 rounded-2xl bg-white border border-emerald-100 shadow-sm flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-bounce" />
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-bounce [animation-delay:150ms]" />
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-bounce [animation-delay:300ms]" />
                </div>
              </div>
            )}
          </div>

          <div className="px-3 pt-2 flex flex-wrap gap-1.5 border-t border-emerald-100 bg-white/80">
            {chips.map((c, i) => (
              <button
                key={i}
                onClick={c.act}
                className="px-2 py-1 text-[10px] font-medium rounded-lg bg-emerald-50 hover:bg-emerald-100 text-emerald-700 border border-emerald-200 transition flex items-center gap-1"
              >
                <Sparkles className="w-3 h-3" />
                {c.label}
              </button>
            ))}
          </div>

          <form
            onSubmit={(e) => { e.preventDefault(); submit(); }}
            className="p-3 flex items-center gap-2 border-t border-emerald-100 bg-white"
          >
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={t('sa_input_ph', lang)}
              className="flex-1 min-w-0 text-xs px-3 py-2 rounded-xl bg-emerald-50 border border-emerald-200 focus:border-emerald-500 focus:outline-none text-slate-700"
            />
            <button type="submit" className="shrink-0 w-8 h-8 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white flex items-center justify-center transition" aria-label={t('sa_send', lang)}>
              <Send className="w-3.5 h-3.5" />
            </button>
          </form>
        </div>
      )}

      <button
        onClick={() => setOpen((o) => !o)}
        className="pointer-events-auto w-14 h-14 rounded-full bg-gradient-to-br from-emerald-500 to-emerald-700 text-white shadow-xl shadow-emerald-900/30 flex items-center justify-center transition-transform hover:scale-105 relative"
        aria-label={t('sa_open_aria', lang)}
      >
        {open ? <X className="w-6 h-6" /> : <Bot className="w-6 h-6" />}
        {!open && <span className="absolute -top-0.5 -right-0.5 w-3.5 h-3.5 rounded-full bg-amber-400 border-2 border-white animate-pulse" />}
      </button>
    </div>
  );
}