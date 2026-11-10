import React, { useState, useEffect } from 'react';
import { Navbar } from './components/Navbar';
import { ImageUploader } from './components/ImageUploader';
import { ObjectCanvas } from './components/ObjectCanvas';
import { ObjectList } from './components/ObjectList';
import { DemoGallery } from './components/DemoGallery';
import { ShowcaseGallery } from './components/ShowcaseGallery';
import { VoiceRecorder } from './components/VoiceRecorder';
import { ResultViewer } from './components/ResultViewer';
import { MetricsModal } from './components/MetricsModal';
import { RoomData, DetectedObject, InstructionResult } from './types';
import {
  uploadRoom,
  detectObjects,
  patchObjects,
  arrangeRoom,
  renderOutputs,
} from './api/client';
import {
  Sparkles,
  Loader2,
  ArrowLeft,
  Mic,
  Sliders,
  CheckCircle2,
  ArrowRight,
  Layers,
  Wand2,
} from 'lucide-react';

export default function App() {
  const [currentRoom, setCurrentRoom] = useState<RoomData | null>(null);
  const [selectedObjectId, setSelectedObjectId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string>('');
  const [serverHealthy, setServerHealthy] = useState<boolean>(false);
  const [activeStep, setActiveStep] = useState<number>(1);
  const [instructionPlan, setInstructionPlan] = useState<InstructionResult | null>(null);
  const [renderResults, setRenderResults] = useState<{
    plan_image_url: string;
    rearranged_image_url: string;
    cleaned_image_url?: string;
    plan: any;
  } | null>(null);
  const [currentStrategy, setCurrentStrategy] = useState<'balanced' | 'spacious' | 'cozy'>('balanced');
  const [showMetrics, setShowMetrics] = useState(false);

  // Light / Dark mode state
  const [darkMode, setDarkMode] = useState<boolean>(() => {
    const saved = localStorage.getItem('placewise_theme');
    if (saved) return saved === 'dark';
    return false; // Default to light so user immediately sees the crisp light mode, or can toggle
  });

  useEffect(() => {
    if (darkMode) {
      document.documentElement.classList.add('dark');
      document.body.classList.add('dark');
      document.documentElement.style.colorScheme = 'dark';
      document.body.style.backgroundColor = '#030712';
      document.body.style.color = '#f1f5f9';
      localStorage.setItem('placewise_theme', 'dark');
    } else {
      document.documentElement.classList.remove('dark');
      document.body.classList.remove('dark');
      document.documentElement.style.colorScheme = 'light';
      document.body.style.backgroundColor = '#f8fafc';
      document.body.style.color = '#0f172a';
      localStorage.setItem('placewise_theme', 'light');
    }
  }, [darkMode]);

  const toggleTheme = () => setDarkMode((prev) => !prev);

  // Poll backend health
  useEffect(() => {
    const checkHealth = async () => {
      try {
        const res = await fetch('http://127.0.0.1:8000/api/health');
        if (res.ok) setServerHealthy(true);
      } catch {
        setServerHealthy(false);
      }
    };
    checkHealth();
    const interval = setInterval(checkHealth, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleImageUploaded = async (file: File) => {
    setIsLoading(true);
    setStatusMessage('Uploading photograph...');
    try {
      const room = await uploadRoom(file);

      setStatusMessage('Analyzing space with YOLOv8 & SAM...');
      const detectionRes = await detectObjects(room.room_id);

      setCurrentRoom({
        ...room,
        status: 'detected',
        detected_objects: detectionRes.objects || [],
      });
      setActiveStep(2);
    } catch (err: any) {
      alert(`Error: ${err.message || 'Processing failed'}`);
    } finally {
      setIsLoading(false);
      setStatusMessage('');
    }
  };

  const handleSelectSample = async (demoPath?: string) => {
    setIsLoading(true);
    setStatusMessage('Loading benchmark sample room...');
    const targetUrl = demoPath
      ? `http://127.0.0.1:8000${demoPath}`
      : 'http://127.0.0.1:8000/storage/uploads/demo_room_01.jpg';

    try {
      const res = await fetch(targetUrl);
      const blob = await res.blob();
      const filename = targetUrl.split('/').pop() || 'sample_room.jpg';
      const file = new File([blob], filename, { type: 'image/jpeg' });
      await handleImageUploaded(file);
    } catch (err: any) {
      alert(`Could not load sample room: ${err.message}`);
      setIsLoading(false);
    }
  };

  const handleToggleAction = async (objectId: string, action: 'KEEP' | 'REMOVE' | null) => {
    if (!currentRoom) return;
    const safeObjects = currentRoom.detected_objects || [];
    const updated = safeObjects.map((o) =>
      o.object_id === objectId ? { ...o, action } : o
    );
    setCurrentRoom({ ...currentRoom, detected_objects: updated });

    try {
      await patchObjects(currentRoom.room_id, [{ object_id: objectId, action }]);
    } catch (e) {
      console.error('Failed to sync object action', e);
    }
  };

  const handleUpdateObject = async (objectId: string, updates: Partial<DetectedObject>) => {
    if (!currentRoom) return;
    const safeObjects = currentRoom.detected_objects || [];
    const updated = safeObjects.map((o) =>
      o.object_id === objectId ? { ...o, ...updates } : o
    );
    setCurrentRoom({ ...currentRoom, detected_objects: updated });

    try {
      await patchObjects(currentRoom.room_id, [
        {
          object_id: objectId,
          class_name: updates.class,
          action: updates.action,
          fixed: updates.fixed,
        },
      ]);
    } catch (e) {
      console.error('Failed to sync object update', e);
    }
  };

  // Spoken feedback helper using browser speech synthesis + Gnani Timbre
  const playVoiceFeedback = (text: string) => {
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
      const utter = new SpeechSynthesisUtterance(text);
      utter.rate = 0.95;
      utter.pitch = 1.0;
      // Try finding Indian English or Tamil voice
      const voices = window.speechSynthesis.getVoices();
      const inVoice = voices.find(
        (v) => v.lang.includes('IN') || v.lang.includes('ta') || v.name.includes('India')
      );
      if (inVoice) utter.voice = inVoice;
      window.speechSynthesis.speak(utter);
    }
  };

  // Called when Tanglish voice instruction is parsed
  const handleInstructionsParsed = (result: InstructionResult) => {
    setInstructionPlan(result);
    if (!currentRoom) return;

    const safeObjects = currentRoom.detected_objects || [];
    const actionMap = new Map(result.actions.map((a) => [a.object_id, a.action as any]));
    const updated = safeObjects.map((obj) => ({
      ...obj,
      action: actionMap.get(obj.object_id) || obj.action || 'KEEP',
    }));

    setCurrentRoom({
      ...currentRoom,
      status: 'instructed',
      detected_objects: updated,
      voice_transcript: result.raw_transcript,
    });

    // Provide natural spoken feedback
    const removedCount = result.actions.filter((a) => a.action === 'REMOVE').length;
    const spokenMessage =
      removedCount > 0
        ? `${removedCount} objects remove panna poren. Matha things neat ah arrange panniyachu.`
        : 'All furniture neat ah arrange panniyachu.';
    playVoiceFeedback(spokenMessage);
  };

  // Trigger spatial arrangement and output rendering
  const handleGenerateArrangement = async () => {
    if (!currentRoom) return;
    setIsLoading(true);
    setStatusMessage('Solving spatial geometry & overlap constraints...');

    try {
      await arrangeRoom(currentRoom.room_id, currentStrategy);
      setStatusMessage('Inpainting removed objects & rendering outputs...');
      const rendered = await renderOutputs(currentRoom.room_id);

      setRenderResults(rendered);
      setActiveStep(4);
    } catch (err: any) {
      alert(`Arrangement failed: ${err.message || 'Error generating outputs'}`);
    } finally {
      setIsLoading(false);
      setStatusMessage('');
    }
  };

  // Alternative strategy regeneration (Balanced, Spacious, Cozy)
  const handleRegenerateStrategy = async (strategy: 'balanced' | 'spacious' | 'cozy') => {
    if (!currentRoom) return;
    setIsLoading(true);
    setStatusMessage(`Applying '${strategy}' spatial strategy with 0 collision...`);
    setCurrentStrategy(strategy);

    try {
      await arrangeRoom(currentRoom.room_id, strategy);
      setStatusMessage('Re-rendering photograph and annotated spatial plan...');
      const rendered = await renderOutputs(currentRoom.room_id);
      setRenderResults(rendered);
      playVoiceFeedback(`Layout regenerated with ${strategy} spatial flow.`);
    } catch (err: any) {
      alert(`Strategy change failed: ${err.message || 'Error re-generating layout'}`);
    } finally {
      setIsLoading(false);
      setStatusMessage('');
    }
  };

  const handleReset = () => {
    setCurrentRoom(null);
    setSelectedObjectId(null);
    setInstructionPlan(null);
    setRenderResults(null);
    setActiveStep(1);
  };

  return (
    <div
      className={`min-h-screen flex flex-col font-['Plus_Jakarta_Sans',sans-serif] transition-colors duration-200 ${
        darkMode ? 'bg-slate-950 text-slate-100' : 'bg-slate-50 text-slate-900'
      }`}
    >
      <Navbar
        serverHealthy={serverHealthy}
        onReset={handleReset}
        darkMode={darkMode}
        onToggleTheme={toggleTheme}
        onOpenMetrics={() => setShowMetrics(true)}
      />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 flex flex-col">
        {/* Step Progression Bar */}
        <div className="mb-8 flex items-center justify-between max-w-3xl mx-auto w-full px-4">
          {/* Step 1 */}
          <div
            onClick={() => setActiveStep(1)}
            className="flex items-center gap-2 cursor-pointer group"
          >
            <span
              className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold transition-all ${
                activeStep > 1
                  ? 'bg-emerald-500 text-slate-950'
                  : activeStep === 1
                  ? 'bg-emerald-500/20 text-emerald-600 dark:text-emerald-400 border border-emerald-500/40 ring-4 ring-emerald-500/10'
                  : 'bg-slate-200 dark:bg-slate-800 text-slate-400 dark:text-slate-500'
              }`}
            >
              {activeStep > 1 ? '✓' : '1'}
            </span>
            <span
              className={`text-xs font-bold transition-colors ${
                activeStep === 1
                  ? 'text-slate-900 dark:text-white'
                  : 'text-slate-500 dark:text-slate-400 group-hover:text-slate-700 dark:group-hover:text-slate-300'
              }`}
            >
              Upload Photo
            </span>
          </div>

          <div
            className={`h-0.5 flex-1 mx-3 sm:mx-6 transition-colors ${
              activeStep >= 2 ? 'bg-emerald-500' : 'bg-slate-200 dark:bg-slate-800'
            }`}
          />

          {/* Step 2 */}
          <div
            onClick={() => currentRoom && setActiveStep(2)}
            className={`flex items-center gap-2 ${
              currentRoom ? 'cursor-pointer group' : 'opacity-40 pointer-events-none'
            }`}
          >
            <span
              className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold transition-all ${
                activeStep > 2
                  ? 'bg-emerald-500 text-slate-950'
                  : activeStep === 2
                  ? 'bg-emerald-500/20 text-emerald-600 dark:text-emerald-400 border border-emerald-500/40 ring-4 ring-emerald-500/10'
                  : 'bg-slate-200 dark:bg-slate-800 text-slate-400 dark:text-slate-500'
              }`}
            >
              {activeStep > 2 ? '✓' : '2'}
            </span>
            <span
              className={`text-xs font-bold transition-colors ${
                activeStep === 2
                  ? 'text-slate-900 dark:text-white'
                  : 'text-slate-500 dark:text-slate-400 group-hover:text-slate-700 dark:group-hover:text-slate-300'
              }`}
            >
              Detect Objects
            </span>
          </div>

          <div
            className={`h-0.5 flex-1 mx-3 sm:mx-6 transition-colors ${
              activeStep >= 3 ? 'bg-emerald-500' : 'bg-slate-200 dark:bg-slate-800'
            }`}
          />

          {/* Step 3 */}
          <div
            onClick={() => currentRoom && setActiveStep(3)}
            className={`flex items-center gap-2 ${
              currentRoom ? 'cursor-pointer group' : 'opacity-40 pointer-events-none'
            }`}
          >
            <span
              className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold transition-all ${
                activeStep > 3
                  ? 'bg-emerald-500 text-slate-950'
                  : activeStep === 3
                  ? 'bg-emerald-500/20 text-emerald-600 dark:text-emerald-400 border border-emerald-500/40 ring-4 ring-emerald-500/10'
                  : 'bg-slate-200 dark:bg-slate-800 text-slate-400 dark:text-slate-500'
              }`}
            >
              {activeStep > 3 ? '✓' : '3'}
            </span>
            <span
              className={`text-xs font-bold transition-colors ${
                activeStep === 3
                  ? 'text-slate-900 dark:text-white'
                  : 'text-slate-500 dark:text-slate-400 group-hover:text-slate-700 dark:group-hover:text-slate-300'
              }`}
            >
              Tanglish Voice
            </span>
          </div>

          <div
            className={`h-0.5 flex-1 mx-3 sm:mx-6 transition-colors ${
              activeStep >= 4 ? 'bg-emerald-500' : 'bg-slate-200 dark:bg-slate-800'
            }`}
          />

          {/* Step 4 */}
          <div
            onClick={() => renderResults && setActiveStep(4)}
            className={`flex items-center gap-2 ${
              renderResults ? 'cursor-pointer group' : 'opacity-40 pointer-events-none'
            }`}
          >
            <span
              className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold transition-all ${
                activeStep === 4
                  ? 'bg-emerald-500 text-slate-950 ring-4 ring-emerald-500/20'
                  : 'bg-slate-200 dark:bg-slate-800 text-slate-400 dark:text-slate-500'
              }`}
            >
              4
            </span>
            <span
              className={`text-xs font-bold transition-colors ${
                activeStep === 4
                  ? 'text-slate-900 dark:text-white'
                  : 'text-slate-500 dark:text-slate-400 group-hover:text-slate-700 dark:group-hover:text-slate-300'
              }`}
            >
              Rearranged Result
            </span>
          </div>
        </div>

        {/* Global Loading Overlay */}
        {isLoading && (
          <div className="fixed inset-0 bg-slate-950/70 dark:bg-slate-950/80 backdrop-blur-md z-50 flex flex-col items-center justify-center">
            <div className="p-8 rounded-3xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 flex flex-col items-center shadow-2xl max-w-sm text-center">
              <Loader2 className="w-10 h-10 text-emerald-500 animate-spin mb-4" />
              <h4 className="font-bold text-slate-900 dark:text-white text-lg mb-1">{statusMessage}</h4>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Gnani Prisma • YOLOv8 • SAM • Deterministic Layout Engine
              </p>
            </div>
          </div>
        )}

        {/* STEP 1: Upload & Initial State */}
        {activeStep === 1 && (
          <div className="flex-1 flex flex-col justify-center items-center py-4">
            <div className="text-center max-w-2xl mb-8">
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-600 dark:text-emerald-400 text-xs font-semibold mb-4">
                <Sparkles className="w-3.5 h-3.5" />
                <span>AI Space Rearrangement Engine</span>
              </div>
              <h1 className="text-3xl sm:text-5xl font-extrabold tracking-tight mb-4">
                <span className="text-slate-900 dark:text-white">Rearrange Your Space with </span>
                <span className="text-transparent bg-clip-text bg-gradient-to-r from-emerald-600 to-teal-500 dark:from-emerald-400 dark:to-teal-300">
                  Regional Voice
                </span>
              </h1>
              <p className="text-sm sm:text-base text-slate-600 dark:text-slate-400 leading-relaxed">
                Upload one photograph of your room or shop. Speak what to keep or remove in Tanglish.
                Receive an annotated layout plan and visual preview of your rearranged space.
              </p>
            </div>

            <ImageUploader
              onImageSelected={handleImageUploaded}
              onSelectSample={handleSelectSample}
              isLoading={isLoading}
            />

            <DemoGallery onSelectDemo={(path) => handleSelectSample(path)} />

            {/* Visual Showcase Gallery */}
            <ShowcaseGallery />
          </div>
        )}

        {/* STEP 2: Object Detection & Verification */}
        {activeStep === 2 && currentRoom && (
          <div className="flex-1 flex flex-col">
            <div className="flex items-center justify-between mb-4">
              <button
                onClick={handleReset}
                className="flex items-center gap-2 text-xs font-semibold text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white px-3 py-1.5 rounded-lg bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700 transition-colors"
              >
                <ArrowLeft className="w-3.5 h-3.5" />
                Upload Another Room
              </button>

              <button
                onClick={() => setActiveStep(3)}
                className="px-5 py-2 rounded-xl bg-gradient-to-tr from-emerald-500 to-teal-400 text-slate-950 font-bold text-xs flex items-center gap-2 shadow-lg shadow-emerald-500/20 hover:scale-[1.02] transition-all"
              >
                <Mic className="w-4 h-4" />
                Proceed to Voice Control (Step 3)
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">
              <div className="lg:col-span-2 space-y-4">
                <ObjectCanvas
                  imageUrl={currentRoom.image_url}
                  originalWidth={currentRoom.width}
                  originalHeight={currentRoom.height}
                  objects={currentRoom.detected_objects || []}
                  selectedObjectId={selectedObjectId}
                  onSelectObject={setSelectedObjectId}
                  onToggleAction={handleToggleAction}
                />

                <div className="p-4 rounded-xl bg-white dark:bg-slate-900/40 border border-slate-200 dark:border-slate-800/80 flex items-center justify-between text-xs text-slate-600 dark:text-slate-400 shadow-sm">
                  <div className="flex items-center gap-4">
                    <span className="flex items-center gap-1.5">
                      <span className="w-3 h-3 rounded border border-emerald-500 bg-emerald-500/20" />
                      Green = KEEP
                    </span>
                    <span className="flex items-center gap-1.5">
                      <span className="w-3 h-3 rounded border border-rose-500 bg-rose-500/20" />
                      Red = REMOVE
                    </span>
                    <span className="flex items-center gap-1.5">
                      <span className="w-3 h-3 rounded border border-sky-500 bg-sky-500/20" />
                      Blue = Selected
                    </span>
                  </div>
                  <span className="italic hidden sm:inline">Tap any bounding box to select & label</span>
                </div>
              </div>

              <div className="lg:col-span-1 h-[650px]">
                <ObjectList
                  objects={currentRoom.detected_objects || []}
                  selectedObjectId={selectedObjectId}
                  onSelectObject={setSelectedObjectId}
                  onUpdateObject={handleUpdateObject}
                  clarificationMessage={instructionPlan?.clarification_message}
                  clarificationCandidates={instructionPlan?.clarification_candidates}
                />
              </div>
            </div>
          </div>
        )}

        {/* STEP 3: Voice Instruction (Gnani Prisma) */}
        {activeStep === 3 && currentRoom && (
          <div className="flex-1 flex flex-col max-w-4xl mx-auto w-full">
            <div className="flex items-center justify-between mb-4">
              <button
                onClick={() => setActiveStep(2)}
                className="flex items-center gap-2 text-xs font-semibold text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white px-3 py-1.5 rounded-lg bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700 transition-colors"
              >
                <ArrowLeft className="w-3.5 h-3.5" />
                Back to Object Canvas
              </button>

              {instructionPlan && (
                <button
                  onClick={handleGenerateArrangement}
                  className="px-6 py-2.5 rounded-xl bg-gradient-to-tr from-emerald-500 to-teal-400 text-slate-950 font-extrabold text-sm flex items-center gap-2 shadow-lg shadow-emerald-500/25 hover:scale-[1.02] transition-all"
                >
                  <Wand2 className="w-4 h-4" />
                  Generate Arrangement Plan
                  <ArrowRight className="w-4 h-4" />
                </button>
              )}
            </div>

            <VoiceRecorder
              roomId={currentRoom.room_id}
              onInstructionsParsed={handleInstructionsParsed}
            />

            {/* Instruction Plan Feedback Box */}
            {instructionPlan && (
              <div className="mt-6 p-6 rounded-3xl bg-white dark:bg-slate-900/90 border border-emerald-500/30 shadow-2xl transition-colors">
                {/* Ambiguity or Contradiction Alert if clarification is needed */}
                {instructionPlan.clarification_required && (
                  <div className="mb-4 p-4 rounded-2xl bg-amber-500/10 border border-amber-500/30 text-amber-900 dark:text-amber-200 text-xs flex items-start gap-3 shadow-sm">
                    <span className="text-base">⚠️</span>
                    <div>
                      <span className="font-bold block text-sm mb-0.5">Clarification Needed:</span>
                      <p>{instructionPlan.clarification_message}</p>
                      {instructionPlan.clarification_candidates && instructionPlan.clarification_candidates.length > 0 && (
                        <p className="mt-1 text-[11px] text-amber-800 dark:text-amber-300">
                          Candidate objects: <span className="font-mono font-bold">{instructionPlan.clarification_candidates.join(', ')}</span>.
                          Tap the buttons below to manually set KEEP or REMOVE.
                        </p>
                      )}
                    </div>
                  </div>
                )}

                <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-slate-200 dark:border-slate-800">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold uppercase tracking-wider text-emerald-700 dark:text-emerald-400 bg-emerald-500/10 px-3 py-1 rounded-full border border-emerald-500/20">
                      Mode: {instructionPlan.mode}
                    </span>
                    <span className="text-xs text-slate-600 dark:text-slate-400">
                      Resolved actions for {instructionPlan.actions.length} objects
                    </span>
                  </div>

                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => {
                        const rem = instructionPlan.actions.filter((a) => a.action === 'REMOVE').length;
                        playVoiceFeedback(
                          rem > 0
                            ? `${rem} objects remove panna poren. Matha things neat ah arrange panniyachu.`
                            : 'All furniture neat ah arrange panniyachu.'
                        );
                      }}
                      className="px-3 py-1.5 rounded-xl bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 text-xs font-semibold flex items-center gap-1.5 transition-colors"
                      title="Play spoken confirmation"
                    >
                      <span>🔊</span>
                      <span>Gnani Timbre Voice</span>
                    </button>

                    <button
                      onClick={handleGenerateArrangement}
                      className="px-4 py-1.5 rounded-xl bg-emerald-500 hover:bg-emerald-600 text-slate-950 font-bold text-xs flex items-center gap-2 transition-colors shadow-md shadow-emerald-500/20"
                    >
                      Apply & Rearrange Space
                      <ArrowRight className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3 mt-4">
                  {instructionPlan.actions.map((act) => {
                    const isCandidate = instructionPlan.clarification_candidates?.includes(act.object_id);
                    return (
                      <div
                        key={act.object_id}
                        className={`p-3 rounded-xl border flex items-center justify-between transition-all ${
                          isCandidate
                            ? 'ring-2 ring-amber-500/50 border-amber-500 bg-amber-500/10'
                            : act.action === 'KEEP'
                            ? 'border-emerald-500/40 bg-emerald-500/10 text-emerald-800 dark:text-emerald-300'
                            : 'border-rose-500/40 bg-rose-500/10 text-rose-800 dark:text-rose-300'
                        }`}
                      >
                        <div className="flex flex-col min-w-0">
                          <span className="font-mono text-xs font-bold truncate">{act.object_id}</span>
                          {act.object_class && (
                            <span className="text-[10px] text-slate-500 dark:text-slate-400 capitalize">
                              {act.object_class}
                            </span>
                          )}
                        </div>

                        {/* Interactive toggle buttons for manual correction */}
                        <div className="flex items-center gap-1">
                          <button
                            type="button"
                            onClick={() => {
                              const newAction = act.action === 'KEEP' ? 'REMOVE' : 'KEEP';
                              handleToggleAction(act.object_id, newAction);
                              setInstructionPlan({
                                ...instructionPlan,
                                actions: instructionPlan.actions.map((a) =>
                                  a.object_id === act.object_id ? { ...a, action: newAction } : a
                                ),
                              });
                            }}
                            className={`text-[10px] font-extrabold px-2.5 py-1 rounded transition-transform active:scale-95 cursor-pointer shadow-sm ${
                              act.action === 'KEEP'
                                ? 'bg-emerald-500 text-slate-950 hover:bg-emerald-600'
                                : 'bg-rose-500 text-white hover:bg-rose-600'
                            }`}
                            title="Click to toggle KEEP / REMOVE"
                          >
                            {act.action}
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        )}

        {/* STEP 4: Rearranged Results & Before/After Slider */}
        {activeStep === 4 && renderResults && currentRoom && (
          <div className="flex-1 flex flex-col">
            <div className="flex items-center justify-between mb-4">
              <button
                onClick={() => setActiveStep(3)}
                className="flex items-center gap-2 text-xs font-semibold text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white px-3 py-1.5 rounded-lg bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700 transition-colors"
              >
                <ArrowLeft className="w-3.5 h-3.5" />
                Change Voice Instruction
              </button>

              <button
                onClick={handleReset}
                className="px-4 py-1.5 rounded-xl bg-slate-200 dark:bg-slate-800 hover:bg-slate-300 dark:hover:bg-slate-700 text-slate-800 dark:text-slate-200 border border-slate-300 dark:border-slate-700 text-xs font-semibold transition-colors"
              >
                Upload New Room
              </button>
            </div>

            <ResultViewer
              originalImageUrl={currentRoom.image_url}
              planImageUrl={renderResults.plan_image_url}
              rearrangedImageUrl={renderResults.rearranged_image_url}
              cleanedImageUrl={renderResults.cleaned_image_url}
              plan={renderResults.plan}
              summary={renderResults.plan?.summary}
              roomId={currentRoom.room_id}
              onRearrangeAgain={() => setActiveStep(3)}
              onRegenerateStrategy={handleRegenerateStrategy}
              isRegenerating={isLoading}
            />
          </div>
        )}
      </main>

      <MetricsModal
        isOpen={showMetrics}
        onClose={() => setShowMetrics(false)}
      />
    </div>
  );
}
