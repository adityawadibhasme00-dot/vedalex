'use client';
import React, { useCallback, useEffect, useState } from 'react';
import { useVoiceAssistant } from '../hooks/useVoiceAssistant';
import { useLang } from '../lib/LangContext';
import { t } from '../lib/i18n';
import { Mic, MicOff, X, Volume2, VolumeX } from 'lucide-react';

interface VoiceAssistantProps {
  onCommand?: (command: string) => void;
}

export default function VoiceAssistant({ onCommand }: VoiceAssistantProps) {
  const { lang } = useLang();
  const { supported, isListening, interim, error, toggleListening, speak, clearError, voiceOutput, toggleVoiceOutput } = useVoiceAssistant({ lang: lang === 'hi' ? 'hi-IN' : 'en-IN' });
  const [isOpen, setIsOpen] = useState(false);
  const [lastCommand, setLastCommand] = useState('');

  const handleToggle = () => {
    if (!supported) {
      speak(t('voice_not_supported', lang));
      return;
    }
    toggleListening((transcript) => {
      setLastCommand(transcript);
      window.dispatchEvent(new CustomEvent('ipsakti:voice', { detail: transcript }));
      onCommand?.(transcript);
    });
  };

  const handleVoiceFeedback = useCallback(
    (e: Event) => {
      const message = (e as CustomEvent<string>).detail || '';
      if (message) speak(message);
    },
    [speak]
  );

  useEffect(() => {
    window.addEventListener('ipsakti:voice-feedback', handleVoiceFeedback);
    return () => window.removeEventListener('ipsakti:voice-feedback', handleVoiceFeedback);
  }, [handleVoiceFeedback]);

  return (
    <>
      {/* Floating Action Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="fixed bottom-24 left-6 z-50 w-14 h-14 rounded-full bg-gradient-to-tr from-blue-600 to-violet-600 flex items-center justify-center text-white shadow-lg shadow-blue-500/30 hover:scale-105 transition-transform"
        aria-label={t('voice_assistant', lang)}
      >
        <Volume2 className="w-6 h-6" />
      </button>

      {/* Overlay Panel */}
      {isOpen && (
        <div className="fixed bottom-24 left-4 right-4 mx-auto sm:mx-0 sm:left-24 sm:right-auto z-50 w-auto sm:w-80 max-w-md bg-white backdrop-blur-xl border border-emerald-200 rounded-3xl p-5 shadow-2xl animate-slide-up">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <span className="w-8 h-8 rounded-xl bg-blue-100 flex items-center justify-center">
                <Volume2 className="w-4 h-4 text-blue-600" />
              </span>
              {t('voice_assistant', lang)}
            </h3>
            <button onClick={() => setIsOpen(false)} className="text-slate-500 hover:text-slate-900">
              <X className="w-4 h-4" />
            </button>
          </div>

          <div className="bg-emerald-50 border border-emerald-200 rounded-2xl p-4 flex flex-col items-center gap-3">
            <button
              onClick={handleToggle}
              className={`w-16 h-16 rounded-full flex items-center justify-center transition-all ${
                isListening
                  ? 'bg-red-100 text-red-600 ring-4 ring-red-500/30 animate-pulse'
                  : 'bg-blue-100 text-blue-600 hover:bg-blue-200'
              }`}
            >
              {isListening ? <MicOff className="w-7 h-7" /> : <Mic className="w-7 h-7" />}
            </button>

            <p className="text-xs text-slate-500 text-center h-6">
              {isListening ? (
                <span className="text-blue-600">{interim || t('listening', lang)}</span>
              ) : (
                t('speak_now', lang)
              )}
            </p>

            {lastCommand && !isListening && (
              <div className="w-full">
                <div className="text-[10px] uppercase tracking-wider text-slate-500 mb-1 text-center">Heard</div>
                <p className="text-xs text-slate-700 text-center bg-emerald-50 border border-emerald-200 rounded-lg px-3 py-2 truncate">
                  “{lastCommand}”
                </p>
              </div>
            )}
          </div>

          <div className="mt-3 flex items-center justify-between rounded-xl border border-slate-200 bg-slate-50 px-3 py-2.5">
            <span className="flex items-center gap-2 text-xs font-semibold text-slate-700">
              {voiceOutput ? <Volume2 className="w-4 h-4 text-blue-600" /> : <VolumeX className="w-4 h-4 text-slate-400" />}
              Voice replies
            </span>
            <button
              type="button"
              role="switch"
              aria-checked={voiceOutput}
              aria-label="Toggle voice output"
              onClick={toggleVoiceOutput}
              className={`relative w-11 h-6 rounded-full transition-colors ${voiceOutput ? 'bg-blue-600' : 'bg-slate-300'}`}
            >
              <span
                className={`absolute top-0.5 w-5 h-5 rounded-full bg-white shadow transition-transform ${
                  voiceOutput ? 'translate-x-[22px]' : 'translate-x-0.5'
                }`}
              />
            </button>
          </div>

          {!voiceOutput && (
            <p className="text-[10px] text-center text-slate-400 mt-2">Assistant voice output is off. You can still tap the mic and speak commands.</p>
          )}

          {error && (
            <div className="mt-3 w-full bg-red-50/70 border border-red-500/30 rounded-xl px-3 py-2 text-xs text-red-700 flex justify-between items-center">
              <span>{error}</span>
              <button onClick={clearError} className="text-red-600 hover:text-red-800"><X className="w-3 h-3" /></button>
            </div>
          )}

          {!supported && (
            <p className="text-[10px] text-center text-slate-500 mt-2">
              {t('voice_not_supported', lang)}
            </p>
          )}
        </div>
      )}
    </>
  );
}