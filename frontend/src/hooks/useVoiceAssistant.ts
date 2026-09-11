'use client';
import { useCallback, useEffect, useRef, useState } from 'react';

interface RecognitionLike {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  onstart: (() => void) | null;
  onresult: ((e: RecognitionEventLike) => void) | null;
  onend: (() => void) | null;
  onerror: ((e: { error: string }) => void) | null;
  start: () => void;
  stop: () => void;
  abort: () => void;
}

interface RecognitionEventLike {
  resultIndex: number;
  results: ArrayLike<{
    isFinal: boolean;
    0: { transcript: string; confidence: number };
  }>;
}

interface UseVoiceAssistantOptions {
  lang?: string;
}

function getRecognitionCtor(): (new () => RecognitionLike) | null {
  if (typeof window === 'undefined') return null;
  const w = window as unknown as {
    SpeechRecognition?: new () => RecognitionLike;
    webkitSpeechRecognition?: new () => RecognitionLike;
  };
  return w.SpeechRecognition || w.webkitSpeechRecognition || null;
}

export function useVoiceAssistant({ lang = 'en-IN' }: UseVoiceAssistantOptions = {}) {
  const recognitionRef = useRef<RecognitionLike | null>(null);
  const [isListening, setIsListening] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [interim, setInterim] = useState('');
  const [voiceOutput, setVoiceOutput] = useState(true);
  const voiceOutputRef = useRef(true);

  useEffect(() => {
    voiceOutputRef.current = voiceOutput;
  }, [voiceOutput]);

  const supported = typeof window !== 'undefined' && getRecognitionCtor() !== null;
  const synthSupported = typeof window !== 'undefined' && 'speechSynthesis' in window;

  const toggleVoiceOutput = useCallback(() => {
    setVoiceOutput((v) => {
      const next = !v;
      voiceOutputRef.current = next;
      if (next) {
        setError(null);
      } else if (synthSupported) {
        window.speechSynthesis.cancel();
        setIsSpeaking(false);
      }
      return next;
    });
  }, [synthSupported]);

  const stopListening = useCallback(() => {
    recognitionRef.current?.stop();
    recognitionRef.current = null;
    setIsListening(false);
  }, []);

  const startListening = useCallback(
    (onFinal: (transcript: string) => void) => {
      if (!supported) {
        setError('Voice input is not supported in this browser. Try Chrome or Edge.');
        return;
      }
      setError(null);
      const Ctor = getRecognitionCtor()!;
      if (recognitionRef.current) {
        recognitionRef.current.abort();
        recognitionRef.current = null;
      }

      const rec = new Ctor();
      rec.lang = lang;
      rec.continuous = false;
      rec.interimResults = true;

      rec.onstart = () => setIsListening(true);
      rec.onresult = (e: RecognitionEventLike) => {
        let interimText = '';
        let finalText = '';
        for (let i = e.resultIndex; i < e.results.length; i++) {
          const result = e.results[i];
          if (result.isFinal) {
            finalText += result[0].transcript;
          } else {
            interimText += result[0].transcript;
          }
        }
        setInterim(interimText);
        if (finalText.trim()) {
          onFinal(finalText.trim());
        }
      };
      rec.onerror = (e) => {
        if (e.error === 'not-allowed' || e.error === 'service-not-allowed') {
          setError('Microphone permission denied. Allow mic access to use voice input.');
        } else if (e.error === 'no-speech') {
          setError('No speech detected. Try again.');
        } else {
          setError(`Speech error: ${e.error}`);
        }
      };
      rec.onend = () => {
        recognitionRef.current = null;
        setIsListening(false);
        setInterim('');
      };

      recognitionRef.current = rec;
      try {
        rec.start();
      } catch {
        setError('Could not start voice recognition.');
        setIsListening(false);
      }
    },
    [lang, supported]
  );

  const toggleListening = useCallback(
    (onFinal: (transcript: string) => void) => {
      if (isListening) {
        stopListening();
      } else {
        startListening(onFinal);
      }
    },
    [isListening, startListening, stopListening]
  );

  const speak = useCallback(
    (text: string, onEnd?: () => void) => {
      if (!synthSupported || !voiceOutputRef.current) return;
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      const voices = window.speechSynthesis.getVoices();
      const preferred = voices.find((v) => v.lang.replace('_', '-').toLowerCase().startsWith(lang.toLowerCase().slice(0, 2)));
      if (preferred) {
        utterance.voice = preferred;
      } else if (voices.length > 0) {
        utterance.voice = voices.find((v) => v.lang.startsWith('en')) || voices[0];
      }
      utterance.rate = 1;
      utterance.onstart = () => setIsSpeaking(true);
      utterance.onend = () => {
        setIsSpeaking(false);
        onEnd?.();
      };
      utterance.onerror = () => {
        setIsSpeaking(false);
        onEnd?.();
      };
      window.speechSynthesis.speak(utterance);
    },
    [lang, synthSupported]
  );

  const cancelSpeech = useCallback(() => {
    if (synthSupported) {
      window.speechSynthesis.cancel();
      setIsSpeaking(false);
    }
  }, [synthSupported]);

  const clearError = useCallback(() => setError(null), []);

  useEffect(() => {
    return () => {
      recognitionRef.current?.abort();
      if (synthSupported) {
        window.speechSynthesis.cancel();
      }
    };
  }, [synthSupported]);

  return {
    supported,
    synthSupported,
    isListening,
    isSpeaking,
    voiceOutput,
    toggleVoiceOutput,
    interim,
    error,
    startListening,
    stopListening,
    toggleListening,
    speak,
    cancelSpeech,
    clearError,
  };
}