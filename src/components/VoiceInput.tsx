import React, { useState, useRef, useEffect, useCallback } from 'react';
import { Mic, MicOff, Loader2 } from 'lucide-react';

interface VoiceInputProps {
  onTranscript: (text: string) => void;
  disabled?: boolean;
}

const LANGUAGES = [
  { code: 'ta-IN', label: 'Tamil' },
  { code: 'en-IN', label: 'English' },
];

const VoiceInput: React.FC<VoiceInputProps> = ({ onTranscript, disabled }) => {
  const [supported, setSupported] = useState(true);
  const [listening, setListening] = useState(false);
  const [lang, setLang] = useState('ta-IN');
  const recognitionRef = useRef<any>(null);

  useEffect(() => {
    const SpeechRecognition =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognition) {
      setSupported(false);
    }
  }, []);

  const stopListening = useCallback(() => {
    if (recognitionRef.current) {
      recognitionRef.current.stop();
      recognitionRef.current = null;
    }
    setListening(false);
  }, []);

  const startListening = useCallback(() => {
    const SpeechRecognition =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognition) return;

    stopListening();

    const recognition = new SpeechRecognition();
    recognition.lang = lang;
    recognition.continuous = true;
    recognition.interimResults = true;

    recognition.onresult = (event: any) => {
      let finalTranscript = '';
      for (let i = event.resultIndex; i < event.results.length; i++) {
        finalTranscript += event.results[i][0].transcript;
      }
      onTranscript(finalTranscript);
    };

    recognition.onerror = () => {
      setListening(false);
    };

    recognition.onend = () => {
      setListening(false);
    };

    recognitionRef.current = recognition;
    recognition.start();
    setListening(true);
  }, [lang, onTranscript, stopListening]);

  const toggleListening = () => {
    if (listening) {
      stopListening();
    } else {
      startListening();
    }
  };

  useEffect(() => {
    return () => stopListening();
  }, [stopListening]);

  if (!supported) return null;

  return (
    <div className="voice-input-group">
      <select
        className="voice-lang-select"
        value={lang}
        onChange={(e) => {
          if (listening) stopListening();
          setLang(e.target.value);
        }}
        disabled={disabled || listening}
      >
        {LANGUAGES.map((l) => (
          <option key={l.code} value={l.code}>{l.label}</option>
        ))}
      </select>
      <button
        type="button"
        className={`voice-mic-btn ${listening ? 'recording' : ''}`}
        onClick={toggleListening}
        disabled={disabled}
        title={listening ? 'Stop recording' : 'Start voice input'}
      >
        {listening ? <Loader2 size={18} className="voice-spinner" /> : <Mic size={18} />}
      </button>
      {listening && <span className="voice-pulse" />}
    </div>
  );
};

export default VoiceInput;
