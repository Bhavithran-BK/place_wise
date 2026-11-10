import React, { useState, useRef, useEffect } from 'react';
import { Mic, MicOff, Send, Volume2, Sparkles, RefreshCw, AlertCircle, Play, CheckCircle2 } from 'lucide-react';
import { transcribeAudio, transcribeText, parseInstructions } from '../api/client';
import { InstructionResult, TranscriptResult } from '../types';

interface VoiceRecorderProps {
  roomId: string;
  onInstructionsParsed: (result: InstructionResult) => void;
  disabled?: boolean;
}

// Resamples audio buffer to 16kHz mono (optimal for Gnani Prisma STT)
function downsampleTo16kHz(buffer: Float32Array, sampleRate: number): Float32Array {
  if (sampleRate === 16000) return buffer;
  const ratio = sampleRate / 16000;
  const newLength = Math.round(buffer.length / ratio);
  const result = new Float32Array(newLength);
  for (let i = 0; i < newLength; i++) {
    const srcIndex = Math.min(buffer.length - 1, Math.floor(i * ratio));
    result[i] = buffer[srcIndex];
  }
  return result;
}

// Encodes raw 16kHz PCM samples into a standard 16-bit Mono WAV Blob
function encodeWav(samples: Float32Array, sampleRate: number = 16000): Blob {
  const buffer = new ArrayBuffer(44 + samples.length * 2);
  const view = new DataView(buffer);

  const writeString = (offset: number, str: string) => {
    for (let i = 0; i < str.length; i++) {
      view.setUint8(offset + i, str.charCodeAt(i));
    }
  };

  writeString(0, 'RIFF');
  view.setUint32(4, 36 + samples.length * 2, true);
  writeString(8, 'WAVE');
  writeString(12, 'fmt ');
  view.setUint32(16, 16, true); // SubChunk1Size (16 for PCM)
  view.setUint16(20, 1, true); // AudioFormat (1 = PCM)
  view.setUint16(22, 1, true); // NumChannels (1 = Mono)
  view.setUint32(24, sampleRate, true); // SampleRate (16000 Hz)
  view.setUint32(28, sampleRate * 2, true); // ByteRate (16000 * 1 * 2 = 32000)
  view.setUint16(32, 2, true); // BlockAlign (1 * 2)
  view.setUint16(34, 16, true); // BitsPerSample (16 bits)
  writeString(36, 'data');
  view.setUint32(40, samples.length * 2, true);

  // Write 16-bit PCM integer samples
  let offset = 44;
  for (let i = 0; i < samples.length; i++, offset += 2) {
    const s = Math.max(-1, Math.min(1, samples[i]));
    view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7fff, true);
  }

  return new Blob([view], { type: 'audio/wav' });
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
  const [transcriptionError, setTranscriptionError] = useState<string | null>(null);
  const [manualText, setManualText] = useState('');
  const [activePreset, setActivePreset] = useState<string | null>(null);
  const [transcriptionConfirmed, setTranscriptionConfirmed] = useState(false);

  // AudioContext recording refs
  const audioContextRef = useRef<AudioContext | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const audioChunksPcmRef = useRef<Float32Array[]>([]);
  const processorRef = useRef<ScriptProcessorNode | null>(null);

  // Fallback MediaRecorder ref
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const fallbackChunksRef = useRef<Blob[]>([]);

  // Suggested Tanglish presets for quick demo & testing
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
    {
      label: "Remove all books & keep sofas",
      text: "Remove all books and keep both sofas.",
      desc: "Plural & Multi-object test",
    },
  ];

  const startRecording = async () => {
    setTranscriptionError(null);
    setTranscriptionConfirmed(false);
    audioChunksPcmRef.current = [];
    fallbackChunksRef.current = [];

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaStreamRef.current = stream;

      // Primary: Web Audio API pure PCM 16kHz WAV recorder
      try {
        const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext;
        const audioCtx = new AudioContextClass();
        audioContextRef.current = audioCtx;

        const source = audioCtx.createMediaStreamSource(stream);
        // 4096 buffer size, 1 input channel, 1 output channel
        const processor = audioCtx.createScriptProcessor(4096, 1, 1);
        processorRef.current = processor;

        processor.onaudioprocess = (e) => {
          const input = e.inputBuffer.getChannelData(0);
          audioChunksPcmRef.current.push(new Float32Array(input));
        };

        source.connect(processor);
        processor.connect(audioCtx.destination);
      } catch (audioCtxErr) {
        console.warn('AudioContext recording fallback to MediaRecorder', audioCtxErr);
        // Fallback: MediaRecorder with true webm
        const mr = new MediaRecorder(stream);
        mediaRecorderRef.current = mr;
        mr.ondataavailable = (e) => {
          if (e.data.size > 0) fallbackChunksRef.current.push(e.data);
        };
        mr.start();
      }

      setIsRecording(true);
      setStatusText('Listening in Tanglish / Tamil / English...');
    } catch (err: any) {
      console.warn('Microphone access denied or unavailable', err);
      setTranscriptionError('Microphone unavailable or permission denied. Please use the text input below.');
      setStatusText('');
    }
  };

  const stopRecording = async () => {
    if (!isRecording) return;
    setIsRecording(false);
    setStatusText('Processing recorded audio for Gnani Prisma STT...');

    // Stop MediaStream tracks
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach((track) => track.stop());
    }

    let finalAudioBlob: Blob | null = null;

    // Check if AudioContext PCM recording succeeded
    if (audioContextRef.current && audioChunksPcmRef.current.length > 0) {
      try {
        const audioCtx = audioContextRef.current;
        const sampleRate = audioCtx.sampleRate;

        if (processorRef.current) {
          processorRef.current.disconnect();
          processorRef.current = null;
        }
        await audioCtx.close();
        audioContextRef.current = null;

        // Concatenate all float arrays
        const totalSamples = audioChunksPcmRef.current.reduce((sum, chunk) => sum + chunk.length, 0);
        const merged = new Float32Array(totalSamples);
        let offset = 0;
        for (const chunk of audioChunksPcmRef.current) {
          merged.set(chunk, offset);
          offset += chunk.length;
        }

        // Resample to 16000Hz (Gnani Prisma standard)
        const resampled16k = downsampleTo16kHz(merged, sampleRate);
        finalAudioBlob = encodeWav(resampled16k, 16000);
      } catch (pcmErr) {
        console.error('PCM encode error', pcmErr);
      }
    }

    // Fallback if PCM failed
    if (!finalAudioBlob && mediaRecorderRef.current) {
      mediaRecorderRef.current.stop();
      await new Promise((resolve) => setTimeout(resolve, 100));
      finalAudioBlob = new Blob(fallbackChunksRef.current, { type: 'audio/webm' });
    }

    if (finalAudioBlob && finalAudioBlob.size > 0) {
      await handleAudioCaptured(finalAudioBlob);
    } else {
      setTranscriptionError('No audio was captured. Please speak again.');
      setStatusText('');
    }
  };

  const handleAudioCaptured = async (audioBlob: Blob) => {
    setIsProcessing(true);
    setTranscriptionError(null);
    setTranscriptionConfirmed(false);

    try {
      setStatusText('Transcribing with Gnani Prisma v2.5 STT...');
      const sttRes: TranscriptResult = await transcribeAudio(roomId, audioBlob);

      if (sttRes.success && sttRes.transcript) {
        setTranscript(sttRes.transcript);
        setTranscriptionConfirmed(true);
        setStatusText('Generating structured action plan...');

        const plan = await parseInstructions(roomId, sttRes.transcript);
        onInstructionsParsed(plan);
        setStatusText('Action plan created successfully!');
      } else {
        const err = sttRes.error || 'Gnani Prisma could not transcribe audio. Please re-record or type your instruction.';
        setTranscriptionError(err);
        setStatusText('');
      }
    } catch (err: any) {
      console.error('Transcription error:', err);
      setTranscriptionError(err.message || 'Audio upload failed. Check connection.');
      setStatusText('');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleApplyText = async (textToApply: string) => {
    if (!textToApply.trim()) return;
    setIsProcessing(true);
    setTranscriptionError(null);
    setStatusText('Processing instruction...');
    setTranscript(textToApply);

    try {
      await transcribeText(roomId, textToApply);
      setTranscriptionConfirmed(true);
      const plan = await parseInstructions(roomId, textToApply);
      onInstructionsParsed(plan);
      setStatusText('Action plan generated!');
    } catch (err: any) {
      setTranscriptionError(`Error: ${err.message || 'Failed to process instruction'}`);
      setStatusText('');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleRerecord = () => {
    setTranscript('');
    setTranscriptionError(null);
    setTranscriptionConfirmed(false);
    setStatusText('Ready to record');
    setActivePreset(null);
  };

  return (
    <div className="w-full bg-white dark:bg-slate-900/90 border border-slate-200 dark:border-slate-800 rounded-3xl p-6 sm:p-8 shadow-2xl relative overflow-hidden backdrop-blur-xl transition-colors">
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
          <span>16kHz PCM WAV Engine</span>
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
                ? 'bg-rose-500 text-white scale-110 shadow-rose-500/50 ring-4 ring-rose-500/30 animate-pulse'
                : 'bg-gradient-to-tr from-emerald-500 to-teal-400 text-slate-950 hover:scale-105 shadow-emerald-500/30'
            } ${disabled || isProcessing ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
            title={isRecording ? 'Click to stop recording' : 'Click to start recording voice instruction'}
          >
            {isRecording ? (
              <MicOff className="w-8 h-8 sm:w-10 sm:h-10" />
            ) : (
              <Mic className="w-8 h-8 sm:w-10 sm:h-10" />
            )}
          </button>
        </div>

        <div className="text-center">
          <span className="text-sm font-bold text-slate-900 dark:text-white block">
            {isRecording ? 'Recording 16kHz PCM... Tap again to finish' : 'Tap Microphone to Speak'}
          </span>
          <span className="text-xs text-slate-500 dark:text-slate-400 mt-0.5 block">
            {statusText || 'Example: "Table and chair remove pannunga. Remaining arrange pannunga."'}
          </span>
        </div>

        {/* Animated Audio Waveform when recording */}
        {isRecording && (
          <div className="flex items-center gap-1.5 mt-4 h-8">
            {[...Array(16)].map((_, i) => (
              <div
                key={i}
                className="w-1 bg-emerald-500 rounded-full h-full animate-bounce"
                style={{ animationDelay: `${(i % 5) * 0.12}s` }}
              />
            ))}
          </div>
        )}
      </div>

      {/* Transcription Error Banner */}
      {transcriptionError && (
        <div className="mt-4 p-4 rounded-2xl bg-amber-500/10 border border-amber-500/30 text-amber-800 dark:text-amber-200 text-xs flex items-start gap-3 relative z-10">
          <AlertCircle className="w-4 h-4 text-amber-500 shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="font-semibold">{transcriptionError}</p>
            <p className="text-[11px] text-amber-700/80 dark:text-amber-300/80 mt-0.5">
              You can type your Tanglish instruction directly in the text box below or click any demo preset.
            </p>
          </div>
        </div>
      )}

      {/* Confirmed Transcript Display Box with Re-record button */}
      {transcript && transcriptionConfirmed && (
        <div className="mt-4 p-4 rounded-2xl bg-slate-50 dark:bg-slate-950/80 border border-slate-200 dark:border-slate-800 relative z-10">
          <div className="flex items-center justify-between text-xs text-slate-500 dark:text-slate-400 mb-1.5">
            <span className="font-semibold text-emerald-600 dark:text-emerald-400 flex items-center gap-1.5">
              <CheckCircle2 className="w-3.5 h-3.5" /> Transcribed via Gnani Prisma v2.5:
            </span>
            <div className="flex items-center gap-2">
              <span className="font-mono text-[11px] bg-slate-200 dark:bg-slate-900 px-2 py-0.5 rounded border border-slate-300 dark:border-slate-800 text-slate-700 dark:text-slate-300">
                Tanglish / Tamil
              </span>
              <button
                type="button"
                onClick={handleRerecord}
                className="flex items-center gap-1 text-[11px] text-slate-500 hover:text-slate-800 dark:hover:text-slate-200 transition-colors"
                title="Clear and re-record"
              >
                <RefreshCw className="w-3 h-3" />
                Re-record
              </button>
            </div>
          </div>
          <p className="text-base sm:text-lg font-medium text-slate-900 dark:text-slate-100 font-mono">
            "{transcript}"
          </p>
        </div>
      )}

      {/* 1-Click Tanglish Preset Buttons */}
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

      {/* Manual Text Input Bar (Fallback) */}
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
            placeholder="Or type here (e.g. 'Table and chair remove pannunga. Remaining arrange pannunga.')..."
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
