'use client';

import React, { useRef, useState, useEffect } from 'react';
import { Bot, Send, X, Sparkles, ChevronDown, Radar, FileDown, RefreshCw, MessageSquare } from 'lucide-react';
import { AyurvedaSeal } from './BotanicalDecor';

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

const HELP_TEXT =
  'Main aapki madad ke liye hoon. Ye kar sakta hoon:\n\n' +
  '• "open copilot" / "copilot kholo" — AI Copilot kholo\n' +
  '• "how to export" / "dossier banao" — Dossier PDF export\n' +
  '• "run assessment" / "evaluate karo" — Assessment dobara chalao\n' +
  '• "open what-if" — What-If Simulator kholo\n' +
  '• "abs kya hai" / "section 3(p)" — Regulatory concepts samjhao\n' +
  '• "status batao" — Aapke passport ki current halat\n\n' +
  'Ya koi bhi tab handle me likh kar open karwa sakte ho.';

const DEFAULT_KB_STATUS: Array<{ keys: string[]; text?: string; tab?: string }> = [
  {
    keys: ['3(p)', '3 p', 'section 3', 'section3', 'sec 3', 'patentable'],
    text:
      'Section 3(p) — Indian Patents Act, 1970:\n\n' +
      'Section 3(p) extras scientific principles jagah of "mere admixture" ya known properties. Agar Ayurveda formulation do known chizon ka bina naya synergistic effect ke combination hai, toh patentable nahi.\n\n' +
      'Round about: patentability ke liye synergistic/additive effect prove karna zaroori. Ye jeet patent tab me Patent Analysis + Section 3(p) flag me dikhta hai.',
    tab: 'patent',
  },
  {
    keys: ['abs', 'bio resource', 'bio-resource', 'biological resource', 'nba', 'access benefit'],
    text:
      'ABS (Access & Benefit Sharing):\n\n' +
      'Biological Diversity Act ke under, jarah ka ye har ingredient (e.g. Ashwagandha, Brahmi) Bharat ke kis state se aaya, supplier kaun, aur NBA/State Biodiversity Board ko benefit sharing clear hai ya nahi — ye track hota hai.\n\n' +
      'Ye jeet kaap passport ke provenance tab me milta hai. "Bio-Resource Ledger" Feature Hub card me bhi hai. Recommendation: Supplier + ABS status pahle set karo.',
    tab: 'provenance',
  },
  {
    keys: ['tkdl', 'traditional knowledge', 'prior art', 'neem', 'haldi', 'turmeric', 'charaka'],
    text:
      'TKDL (Traditional Knowledge Digital Library):\n\n' +
      'TKDL me classical granths (Charaka Samhita, Sushruta, neem-haldi cases vaghre) ke formulations prior art ke roop me recorded hain. Agar aapka claim koi classical text se match karta hai, toh foreign patents (EPO/USPTO) already TKDL ki wajah se reject/short-circuit ho sakte hain.\n\n' +
      'Iska full picture Patent Analysis + TKDL screening me aata hai.',
    tab: 'patent',
  },
  {
    keys: ['schedule t', 'gmp', 'ayush', 'ayurveda manufacture', 'manufacturing'],
    text:
      'Schedule T (Drugs & Cosmetics Rules):\n\n' +
      'Ayurveda medicine banane ke liye Schedule T ki GMP (Good Manufacturing Practices) zaroori — premises, equipment, Sanitization, QA records sab defined hain. Labelling ke liye Schedule T container-requirements (ingredient list Vahti) bhi lagte hain.\n\n' +
      'India compliance Jurisdiction Matrix tab me reflect hota hai.',
    tab: 'matrix',
  },
  {
    keys: ['schedule e', 'toxic', 'poison', 'restrict', 'banned'],
    text:
      'Schedule E:\n\n' +
      'Schedule E(1) me aise ayurvedic substances hain jinpe control/restrictions hain (toxic/purificatory processes). Agar aapke formula me koi Schedule E ingredient hai, purification SOP + dosage guidance zaroori.\n\n' +
      'Apne formulation ke ingredients claim list me check karo — Evidence Matrix me kaap safety flags dikhta hai.',
    tab: 'evidence',
  },
  {
    keys: ['fssai', 'food', 'aahara', 'nutraceutical', 'supplement india', 'ayurveda food'],
    text:
      'FSSAI (Ayurveda Aahara / Nutraceuticals):\n\n' +
      'Agar product food-like hai (Aahara/health supplement), FSSAI ke under Schedule IV (Ayurvedic Aahara claims) ya Nutraceutical regulations lagte hain — not drugs. Health claims (e.g. "acchi neend ke liye") strict phrases ke under he allowed.\n\n' +
      'India matrix me ye alag column ke roop me covered hai.',
    tab: 'matrix',
  },
  {
    keys: ['dshea', 'usa', 'united states', 'fda usa', 'american market', 'us market', 'america'],
    text:
      'United States (DSHEA / FDA):\n\n' +
      'US me product dietary supplement ho toh DSHEA structure marketing (seller regulated, no pre-approval takin) + cGMP (21 CFR 111). Koi bhi disease-preventive ya cure ka claim = "drug" claim, jisse NDI/food additive requirements trigger ho jaate hain.\n\n' +
      'Label par safety + disclaimer (FDA evaluation statement) zaroori. US ke liye Jurisdiction Matrix yo bata deta hai.',
    tab: 'matrix',
  },
  {
    keys: ['canada', 'nhp', 'npn', 'health canada', 'licensed natural'],
    text:
      'Canada (NHP / NPN):\n\n' +
      'Canada me Natural Health Products Directorate se Site Licence + Product Licence chahiye. Har NHP ko NPN number milta hai, aur claims NHP regulations ke specified "risk-based" categories me hi allowed.\n\n' +
      'Canada ke requirements matrix me visible hain.',
    tab: 'matrix',
  },
  {
    keys: ['who', 'monograph', 'gmp who', 'icmr', 'clinical', 'evidence study'],
    text:
      'Evidence & WHO Monographs:\n\n' +
      'Claim ko stronger karne ke liye: WHO COVID/quality monographs, classical granths, jako key clinical studies (ICMR/TKI marked). Strong evidence = reproducible study + peer review. Missing evidence ko Evidence Matrix me red flag dikhata hai.\n\n' +
      'Har claim ke against evidence status Evidence Matrix tab me hai.',
    tab: 'evidence',
  },
  {
    keys: ['status', 'kitna', 'kya haal', 'hal', 'current', 'progress', 'next step', 'next action'],
  },
];

const KB: Array<{ keys: string[]; text: string; tab?: string }> = DEFAULT_KB_STATUS.filter(
  (e): e is { keys: string[]; text: string; tab?: string } => typeof e.text === 'string',
);

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
    if (passportTitle) statusParts.push(`Passport: "${passportTitle.slice(0, 44)}${passportTitle.length > 44 ? '…' : ''}"`);
    if (typeof readiness === 'number') statusParts.push(`Patent Readiness: ${readiness}%`);
    if (passportId) statusParts.push('Assessment ready: India · USA · Canada');
    const statusLine = statusParts.length ? `\n\n${statusParts.join('  ·  ')}` : '\n\nAbhi koi passport nahi bana hai — Overview ke "Create a New Innovation Passport" se shuru karo.';
    const greeting = 'Namaste! Main aapka IP-SAKTI Assistant hoon 😊\n\n' + (lang === 'hi'
      ? 'Main aapko dashboard navigate karne, dossier export karne, regulatory concepts samjhane, aur assessment chalane me madad karunga.'
      : 'I can navigate your dashboard, export dossiers, explain regulatory concepts, and run assessments.') + statusLine;
    if (messages.length === 0) {
      push([
        { id: idRef.current++, role: 'bot', text: greeting },
        { id: idRef.current++, role: 'bot', text: 'Kya chahoge? Type karo jaise "open copilot", "abs kya hai", "how to export" — ya niche suggestions chuno.' },
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

    setTimeout(() => {
      let reply: ChatMsg[] = [];

      const tabHit = findTab(text);
      if (tabHit && /open|khol|khole|kholo|dikha|show|go to|ja|navigate|le jao|open karo|kholke/i.test(low)) {
        onNavigate(tabHit.tab);
        reply = [{ id: idRef.current++, role: 'bot', text: `Ab "${tabHit.tab}" tab khol raha hoon ⚡` }];
      } else if (exportExpr && /dossier|export|pdf|download/i.test(low)) {
        onQuickAction('export');
        reply = [{ id: idRef.current++, role: 'bot', text: 'Dossier export shuru kar raha hoon 📄 — file download aayegi.' }];
      } else if (runExpr && /\b(?:assessment|evaluate|analysis|readiness)\b/.test(low)) {
        onQuickAction('evaluate');
        reply = [{ id: idRef.current++, role: 'bot', text: 'Assessment dobara chala raha hoon 🔄 — results update ho jayenge.' }];
      } else if (/what\s*-?\s*if|simulat/i.test(low)) {
        onNavigate('whatif');
        reply = [{ id: idRef.current++, role: 'bot', text: 'What-If Simulator khol raha hoon — wahan claim mutate karke compliance diff dekh sakte ho.' }];
      } else if (/help|madad|saksham|kya kar|kya kr|features|can you do|kye kar/i.test(low)) {
        reply = [{ id: idRef.current++, role: 'bot', text: HELP_TEXT }];
      } else if (/status|kitna|hal|current|progress|next/i.test(low)) {
        const statusParts: string[] = [];
        if (passportTitle) statusParts.push(`Passport: "${passportTitle.slice(0, 44)}"`);
        if (typeof readiness === 'number') statusParts.push(`Patent Readiness: ${readiness}%`);
        if (passportId) statusParts.push('India · USA · Canada assessment ready');
        reply = [{
          id: idRef.current++,
          role: 'bot',
          text: 'Aapki current status:\n\n' + (statusParts.length ? statusParts.join('\n') : 'Passport abhi nahi bana. Overview pe first card se banao.') + '\n\nNext step: Evidence Matrix me gaps khol ke document upload karo.',
        }];
      } else {
        const kbAnswer = findKB(text);
        if (kbAnswer) {
          const tab = TAB_ALIASES.find((t) => kbAnswer && t.keys.some((k) => low.includes(k)));
          reply = [{ id: idRef.current++, role: 'bot', text: kbAnswer + (tab && tab.tab !== 'overview' ? `\n\nIs topic ke liye "${tab.tab}" tab kholna ho toh "open ${tab.tab}" likho.` : '') }];
        } else {
          reply = [{
            id: idRef.current++,
            role: 'bot',
            text: 'Maaf kijiye, ye mere training me nahi hai 😅\n\nMain practical actions me help karta hoon: "open copilot", "dossier export", "abs kya hai", "section 3(p)", "status batao", ya "help".\n\nRegulatory deep-dive ke liye AI Copilot tab me exact question poocho — wahan source-cited answers milte hain.',
          }];
        }
      }
      setThinking(false);
      push(reply);
    }, 600);
  };

  const chips = [
    { label: 'Status', act: () => submit('status batao') },
    { label: 'Open Copilot', act: () => submit('open copilot') },
    { label: 'What is ABS?', act: () => submit('abs kya hai') },
    { label: 'Export Dossier', act: () => submit('dossier export karo') },
    { label: 'Section 3(p)', act: () => submit('what is section 3(p)') },
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
                  <span className="w-1.5 h-1.5 rounded-full bg-lime-300 animate-pulse" /> Online · Aapki help ke liye
                </div>
              </div>
            </div>
            <button onClick={() => setOpen(false)} className="p-1.5 rounded-lg hover:bg-white/20 transition" aria-label="Close assistant">
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
              placeholder='Type kar... "open copilot" / "abs kya hai"'
              className="flex-1 min-w-0 text-xs px-3 py-2 rounded-xl bg-emerald-50 border border-emerald-200 focus:border-emerald-500 focus:outline-none text-slate-700"
            />
            <button type="submit" className="shrink-0 w-8 h-8 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white flex items-center justify-center transition" aria-label="Send">
              <Send className="w-3.5 h-3.5" />
            </button>
          </form>
        </div>
      )}

      <button
        onClick={() => setOpen((o) => !o)}
        className="pointer-events-auto w-14 h-14 rounded-full bg-gradient-to-br from-emerald-500 to-emerald-700 text-white shadow-xl shadow-emerald-900/30 flex items-center justify-center transition-transform hover:scale-105 relative"
        aria-label="Open IP-SAKTI Assistant"
      >
        {open ? <X className="w-6 h-6" /> : <Bot className="w-6 h-6" />}
        {!open && <span className="absolute -top-0.5 -right-0.5 w-3.5 h-3.5 rounded-full bg-amber-400 border-2 border-white animate-pulse" />}
      </button>
    </div>
  );
}