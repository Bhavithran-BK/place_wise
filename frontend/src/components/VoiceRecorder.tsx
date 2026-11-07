import React, { useState, useRef, useEffect } from 'react';
import { Mic, MicOff, Send, Volume2, Sparkles, RefreshCw, AlertCircle, Play, CheckCircle2 } from 'lucide-react';
import { transcribeAudio, transcribeText, parseInstructions } from '../api/client';
import { InstructionResult, TranscriptResult } from '../types';

interface VoiceRecorderProps {
  roomId: string;
  onInstructionsParsed: (result: InstructionResult) => void;
  disabled?: boolean;
}

export const VoiceRecorder: React.FC<VoiceRecorderProps> = ({
  roomId,
  onInstructionsParsed,
  disabled = false,
}) => {
  const [isRecording, setIsRecording] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [statusText, setStatusText] = useState('');
  const [manualText, setManualText] = useState('');
  const [activePreset, setActivePreset] = useState<string | null>(null);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const recognitionRef = useRef<any>(null);

  // Suggested Tanglish presets for instant judging demo
  const presets = [
    {
      label: "Remove chairs & keep sofa",
      text: "Indha rendu chairs vendaam. Sofa venum.",
      desc: "Removal & Keep combo",
    },
    {
      label: "Clear table & arrange remaining",
      text: "Table and chair remove pannunga. Remaining arrange pannunga.",
      desc: "Remove + Rearrange remaining",
    },
    {
      label: "Keep key furniture",
      text: "Sofa, TV, bookshelf ellame venum.",
      desc: "Keep-first instruction",
    },
    {
      label: "Neat arrangement",
      text: "Neat ah arrange pannunga",
      desc: "Full space rearrangement",
    },
  ];

  // Initialize Web Speech API for real-time live preview if supported
  useEffect(() => {
    const SpeechRecognition =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (SpeechRecognition) {
      const recognition = new SpeechRecognition();
      recognition.continuous = true;
      recognition.interimResults = true;
      recognition.lang = 'en-IN'; // Works for Indian-English and Tanglish phonetic capture

      recognition.onresult = (event: any) => {
        let current = '';
        for (let i = event.resultIndex; i < event.results.length; ++i) {
          current += event.results[i][0].transcript;
        }
        if (current) setTranscript(current);
      };

      recognition.onerror = () => {};
      recognitionRef.current = recognition;
    }
  }, []);

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      audioChunksRef.current = [];

      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) audioChunksRef.current.push(e.data);
      };

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/wav' });
        await handleAudioCaptured(audioBlob);
        stream.getTracks().forEach((track) => track.stop());
      };

      mediaRecorderRef.current = mediaRecorder;
      mediaRecorder.start();
      setIsRecording(true);
      setStatusText('Listening in Tanglish / Tamil / English...');

      if (recognitionRef.current) {
        try {
          recognitionRef.current.start();
        } catch {}
      }
    } catch (err) {
      console.warn('Microphone access denied or unavailable', err);
      setStatusText('Microphone unavailable. Use preset or type instruction.');
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      setStatusText('Processing audio with Gnani Prisma...');
      if (recognitionRef.current) {
        try {
          recognitionRef.current.stop();
        } catch {}
      }
    }
  };

  const handleAudioCaptured = async (audioBlob: Blob) => {
    setIsProcessing(true);
    try {
      // Send audio to backend
      const sttRes: TranscriptResult = await transcribeAudio(roomId, audioBlob);
      const text = sttRes.transcript || transcript;
      setTranscript(text);

      if (text) {
        setStatusText('Resolving intent to object actions...');
        const plan = await parseInstructions(roomId, text);
        onInstructionsParsed(plan);
        setStatusText('Plan created successfully!');
      } else {
        setStatusText('Could not catch instruction. Try a demo preset.');
      }
    } catch (err: any) {
      console.error(err);
      // Fallback: if backend STT had issues, parse what live recognition heard
      if (transcript) {
        const plan = await parseInstructions(roomId, transcript);
        onInstructionsParsed(plan);
      }
    } finally {
      setIsProcessing(false);
    }
  };

  const handleApplyText = async (textToApply: string) => {
    if (!textToApply.trim()) return;
    setIsProcessing(true);
    setStatusText('Parsing Tanglish instruction...');
    setTranscript(textToApply);
    try {
      await transcribeText(roomId, textToApply);
      const plan = await parseInstructions(roomId, textToApply);
      onInstructionsParsed(plan);
      setStatusText('Action plan generated!');
    } catch (err: any) {
      alert(`Error: ${err.message || 'Failed to process instruction'}`);
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div className="w-full bg-white dark:bg-slate-900/90 border border-slate-200 dark:border-slate-800 rounded-3xl p-6 sm:p-8 shadow-2xl relative overflow-hidden backdrop-blur-xl transition-colors">
      {/* Decorative gradient glow */}
      <div className="absolute top-0 right-0 -mt-10 -mr-10 w-60 h-60 bg-emerald-500/10 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-0 left-0 -mb-10 -ml-10 w-60 h-60 bg-teal-500/10 rounded-full blur-3xl pointer-events-none" />

      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 mb-6 relative z-10">
        <div>
          <div className="flex items-center gap-2">
            <span className="px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-700 dark:text-emerald-400 font-bold text-xs uppercase tracking-wider flex items-center gap-1.5">
              <Sparkles className="w-3.5 h-3.5" />
              Gnani Prisma v2.5 Voice Engine
            </span>
          </div>
          <h3 className="text-xl sm:text-2xl font-extrabold text-slate-900 dark:text-white mt-1">
            Speak Your Rearrangement in Tanglish
          </h3>
          <p className="text-xs sm:text-sm text-slate-600 dark:text-slate-400">
            Tell PLACEWISE what to keep, remove, or rearrange in everyday Tamil-English mix.
          </p>
        </div>

        <div className="flex items-center gap-2 text-xs font-mono text-slate-600 dark:text-slate-400 bg-slate-100 dark:bg-slate-950/60 px-3 py-1.5 rounded-xl border border-slate-200 dark:border-slate-800">
          <Volume2 className="w-4 h-4 text-emerald-500 dark:text-emerald-400" />
          <span>Code-Mixed STT Active</span>
        </div>
      </div>

      {/* Interactive Microphone Section */}
      <div className="flex flex-col items-center justify-center py-6 relative z-10">
        <div className="relative mb-4">
          <button
            type="button"
            onClick={isRecording ? stopRecording : startRecording}
            disabled={disabled || isProcessing}
            className={`w-20 h-20 sm:w-24 sm:h-24 rounded-full flex items-center justify-center transition-all duration-300 shadow-2xl ${
              isRecording
                ? 'bg-rose-500 text-white scale-110 shadow-rose-500/50 pulse-ring'
                : 'bg-gradient-to-tr from-emerald-500 to-teal-400 text-slate-950 hover:scale-105 shadow-emerald-500/30'
            } ${disabled || isProcessing ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
          >
            {isRecording ? (
              <MicOff className="w-8 h-8 sm:w-10 sm:h-10 animate-pulse" />
            ) : (
              <Mic className="w-8 h-8 sm:w-10 sm:h-10" />
            )}
          </button>
        </div>

        <div className="text-center">
          <span className="text-sm font-bold text-slate-900 dark:text-white block">
            {isRecording ? 'Listening... Tap to Stop' : 'Tap Microphone & Speak'}
          </span>
          <span className="text-xs text-slate-500 dark:text-slate-400 mt-0.5 block">
            {statusText || 'Example: "Indha rendu chairs vendaam, sofa venum"'}
          </span>
        </div>

        {/* Animated Audio Waveform when recording */}
        {isRecording && (
          <div className="flex items-center gap-1.5 mt-4 h-8">
            {[...Array(16)].map((_, i) => (
              <div
                key={i}
                className="w-1 bg-emerald-500 rounded-full wave-bar"
                style={{ animationDelay: `${(i % 5) * 0.1}s` }}
              />
            ))}
          </div>
        )}
      </div>

      {/* Live Transcript Display Box */}
      {transcript && (
        <div className="mt-4 p-4 rounded-2xl bg-slate-50 dark:bg-slate-950/80 border border-slate-200 dark:border-slate-800 relative z-10">
          <div className="flex items-center justify-between text-xs text-slate-500 dark:text-slate-400 mb-1.5">
            <span className="font-semibold text-emerald-600 dark:text-emerald-400 flex items-center gap-1.5">
              <CheckCircle2 className="w-3.5 h-3.5" /> Transcribed via Gnani Prisma:
            </span>
            <span className="font-mono text-[11px] bg-slate-200 dark:bg-slate-900 px-2 py-0.5 rounded border border-slate-300 dark:border-slate-800 text-slate-700 dark:text-slate-300">
              Tanglish
            </span>
          </div>
          <p className="text-base sm:text-lg font-medium text-slate-900 dark:text-slate-100 font-mono">
            "{transcript}"
          </p>
        </div>
      )}

      {/* 1-Click Tanglish Preset Buttons for Hackathon Judges */}
      <div className="mt-6 pt-6 border-t border-slate-200 dark:border-slate-800/80 relative z-10">
        <div className="flex items-center justify-between mb-3">
          <span className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 flex items-center gap-1.5">
            <Sparkles className="w-3.5 h-3.5 text-emerald-500" />
            Try Pre-Recorded Tanglish Instructions (Instant Demo)
          </span>
          <span className="text-[11px] text-slate-400">Click to run immediately</span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
          {presets.map((preset, idx) => (
            <button
              key={idx}
              type="button"
              onClick={() => {
                setActivePreset(preset.text);
                handleApplyText(preset.text);
              }}
              disabled={isProcessing}
              className={`p-3 rounded-xl border text-left transition-all duration-200 flex items-start justify-between gap-2 group ${
                activePreset === preset.text
                  ? 'border-emerald-500 bg-emerald-500/10'
                  : 'border-slate-200 dark:border-slate-800 bg-slate-50/60 dark:bg-slate-950/40 hover:bg-slate-100 dark:hover:bg-slate-900 hover:border-slate-300 dark:hover:border-slate-700'
              }`}
            >
              <div>
                <div className="text-xs font-bold text-slate-900 dark:text-white group-hover:text-emerald-600 dark:group-hover:text-emerald-300 transition-colors">
                  {preset.label}
                </div>
                <div className="text-[11px] font-mono text-emerald-600 dark:text-emerald-400/90 mt-0.5 italic">
                  "{preset.text}"
                </div>
              </div>
              <span className="text-[10px] uppercase font-bold text-slate-500 dark:text-slate-400 bg-white dark:bg-slate-900 px-2 py-0.5 rounded border border-slate-200 dark:border-slate-800 group-hover:text-emerald-600 dark:group-hover:text-emerald-400 shrink-0 shadow-sm">
                Run
              </span>
            </button>
          ))}
        </div>
      </div>

      {/* Manual Text Input Bar (Noisy Environment Fallback) */}
      <div className="mt-5 relative z-10">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleApplyText(manualText);
          }}
          className="flex items-center gap-2"
        >
          <input
            type="text"
            value={manualText}
            onChange={(e) => setManualText(e.target.value)}
            placeholder="Or type here (e.g. 'Chair vendaam, sofa venum')..."
            className="flex-1 bg-slate-50 dark:bg-slate-950/80 border border-slate-200 dark:border-slate-800 rounded-xl px-4 py-2.5 text-xs sm:text-sm text-slate-900 dark:text-white placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none focus:border-emerald-500 transition-colors"
          />
          <button
            type="submit"
            disabled={!manualText.trim() || isProcessing}
            className="px-4 py-2.5 rounded-xl bg-slate-100 dark:bg-slate-800 hover:bg-emerald-500 text-slate-700 dark:text-slate-300 hover:text-slate-950 text-xs font-bold transition-all disabled:opacity-40 disabled:hover:bg-slate-100 dark:disabled:hover:bg-slate-800 flex items-center gap-1.5 shadow-sm"
          >
            <Send className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Apply</span>
          </button>
        </form>
      </div>
    </div>
  );
};

