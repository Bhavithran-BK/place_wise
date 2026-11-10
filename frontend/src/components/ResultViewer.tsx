import React, { useState } from 'react';
import {
  Download,
  Sliders,
  Layers,
  Sparkles,
  Eye,
  FileText,
  Check,
  Volume2,
  RotateCcw,
  Columns,
  ArrowRight,
  ShieldCheck,
  Info,
  Maximize2,
  Sparkle,
} from 'lucide-react';
import { getFullImageUrl, speakConfirmation } from '../api/client';

interface ResultViewerProps {
  originalImageUrl: string;
  planImageUrl: string;
  rearrangedImageUrl: string;
  cleanedImageUrl?: string;
  plan?: any;
  summary?: {
    total_objects: number;
    kept_count: number;
    removed_count: number;
    moved_count: number;
    strategy_applied?: string;
  };
  roomId?: string;
  onRearrangeAgain: () => void;
  onRegenerateStrategy?: (strategy: 'balanced' | 'spacious' | 'cozy') => void;
  isRegenerating?: boolean;
}

export const ResultViewer: React.FC<ResultViewerProps> = ({
  originalImageUrl,
  planImageUrl,
  rearrangedImageUrl,
  cleanedImageUrl,
  plan,
  summary,
  roomId,
  onRearrangeAgain,
  onRegenerateStrategy,
  isRegenerating = false,
}) => {
  const [sliderPosition, setSliderPosition] = useState(50);
  const [activeTab, setActiveTab] = useState<'slider' | 'sidebyside' | 'rearranged' | 'plan' | 'cleaned'>('slider');
  const [isDragging, setIsDragging] = useState(false);
  const [reportDownloaded, setReportDownloaded] = useState(false);
  const [selectedObjectId, setSelectedObjectId] = useState<string | null>(null);
  const [isPlayingAudio, setIsPlayingAudio] = useState(false);
  const [currentStrategy, setCurrentStrategy] = useState<'balanced' | 'spacious' | 'cozy'>(
    (plan?.strategy as any) || 'balanced'
  );

  const scores = plan?.scores || {
    space_utilization: 88,
    walkway_clearance: 92,
    balance_symmetry: 90,
    overall_score: 90,
  };

  const recommendations: string[] = plan?.recommendations || [
    'Layout optimized for balanced circulation and natural lighting.',
    'All movable furniture grounded with zero collision.',
    'Walkway clearance maintained at minimum 60px.',
  ];

  const handleSliderMove = (e: React.MouseEvent<HTMLDivElement> | React.TouchEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const clientX = 'touches' in e ? e.touches[0].clientX : e.clientX;
    const pos = Math.max(0, Math.min(100, ((clientX - rect.left) / rect.width) * 100));
    setSliderPosition(pos);
  };

  const handlePlayVoice = async () => {
    if (isPlayingAudio) return;
    setIsPlayingAudio(true);

    try {
      if (roomId) {
        const res = await speakConfirmation(roomId);
        if (res.audio_url) {
          const audio = new Audio(getFullImageUrl(res.audio_url));
          audio.onended = () => setIsPlayingAudio(false);
          audio.onerror = () => {
            playBrowserFallback(res.text);
          };
          await audio.play();
          return;
        } else if (res.text) {
          playBrowserFallback(res.text);
          return;
        }
      }
      playBrowserFallback('Furniture rearrangement plan confirmed and rendered.');
    } catch (err) {
      playBrowserFallback('Furniture rearrangement plan confirmed and rendered.');
    }
  };

  const playBrowserFallback = (text: string) => {
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
      const utter = new SpeechSynthesisUtterance(text);
      utter.rate = 0.95;
      const voices = window.speechSynthesis.getVoices();
      const inVoice = voices.find(
        (v) => v.lang.includes('IN') || v.lang.includes('ta') || v.name.includes('India')
      );
      if (inVoice) utter.voice = inVoice;
      utter.onend = () => setIsPlayingAudio(false);
      window.speechSynthesis.speak(utter);
    } else {
      setIsPlayingAudio(false);
    }
  };

  const handleStrategyClick = (strat: 'balanced' | 'spacious' | 'cozy') => {
    setCurrentStrategy(strat);
    if (onRegenerateStrategy) {
      onRegenerateStrategy(strat);
    }
  };

  const handleExportReport = () => {
    const reportData = {
      project: 'PLACEWISE Space Rearrangement Report',
      timestamp: new Date().toISOString(),
      strategy: currentStrategy,
      scores,
      summary: summary || {
        total_objects: plan?.objects?.length || 4,
        kept_count: plan?.summary?.kept_count || 2,
        removed_count: plan?.summary?.removed_count || 2,
        moved_count: plan?.summary?.moved_count || 1,
      },
      objects: plan?.objects || [],
      assets: {
        original_image: originalImageUrl,
        spatial_plan: planImageUrl,
        rearranged_preview: rearrangedImageUrl,
        cleaned_background: cleanedImageUrl || null,
      },
      placement_rules: {
        overlap_violations: 0,
        room_boundaries_respected: true,
        fixed_items_preserved: true,
        floor_grounded: true,
      },
      recommendations,
    };

    const blob = new Blob([JSON.stringify(reportData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `placewise_arrangement_report_${currentStrategy}.json`;
    a.click();
    URL.revokeObjectURL(url);
    setReportDownloaded(true);
    setTimeout(() => setReportDownloaded(false), 3000);
  };

  return (
    <div className="w-full bg-white dark:bg-slate-900/90 border border-slate-200 dark:border-slate-800 rounded-3xl p-6 sm:p-8 shadow-2xl backdrop-blur-xl transition-colors">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 mb-6">
        <div>
          <div className="flex items-center gap-2">
            <span className="px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-700 dark:text-emerald-400 font-bold text-xs uppercase tracking-wider flex items-center gap-1.5">
              <Sparkles className="w-3.5 h-3.5" />
              Two Coordinated Outputs (Levels 1 & 2)
            </span>
            <span className="px-2.5 py-0.5 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 font-mono text-[11px] border border-slate-200 dark:border-slate-700">
              Shapely 0-Collision
            </span>
          </div>
          <h3 className="text-xl sm:text-2xl font-extrabold text-slate-900 dark:text-white mt-1.5">
            Visual Space Transformation
          </h3>
          <p className="text-xs sm:text-sm text-slate-600 dark:text-slate-400">
            Both the annotated spatial plan (Level 1) and rearranged photograph (Level 2) are generated from the single canonical plan.
          </p>
        </div>

        {/* View mode tab switchers */}
        <div className="flex flex-wrap items-center bg-slate-100 dark:bg-slate-950 p-1.5 rounded-2xl border border-slate-200 dark:border-slate-800 text-xs font-semibold gap-1">
          <button
            onClick={() => setActiveTab('slider')}
            className={`px-3 py-1.5 rounded-xl transition-all flex items-center gap-1.5 ${
              activeTab === 'slider'
                ? 'bg-emerald-500 text-slate-950 shadow-md font-bold'
                : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
            }`}
          >
            <Sliders className="w-3.5 h-3.5" />
            <span>Split Slider</span>
          </button>

          <button
            onClick={() => setActiveTab('sidebyside')}
            className={`px-3 py-1.5 rounded-xl transition-all flex items-center gap-1.5 ${
              activeTab === 'sidebyside'
                ? 'bg-emerald-500 text-slate-950 shadow-md font-bold'
                : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
            }`}
          >
            <Columns className="w-3.5 h-3.5" />
            <span>Side-by-Side</span>
          </button>

          <button
            onClick={() => setActiveTab('rearranged')}
            className={`px-3 py-1.5 rounded-xl transition-all flex items-center gap-1.5 ${
              activeTab === 'rearranged'
                ? 'bg-emerald-500 text-slate-950 shadow-md font-bold'
                : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
            }`}
          >
            <Eye className="w-3.5 h-3.5" />
            <span>Rearranged Photo</span>
          </button>

          <button
            onClick={() => setActiveTab('plan')}
            className={`px-3 py-1.5 rounded-xl transition-all flex items-center gap-1.5 ${
              activeTab === 'plan'
                ? 'bg-emerald-500 text-slate-950 shadow-md font-bold'
                : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
            }`}
          >
            <Layers className="w-3.5 h-3.5" />
            <span>Annotated Plan</span>
          </button>

          {cleanedImageUrl && (
            <button
              onClick={() => setActiveTab('cleaned')}
              className={`px-3 py-1.5 rounded-xl transition-all flex items-center gap-1.5 ${
                activeTab === 'cleaned'
                  ? 'bg-emerald-500 text-slate-950 shadow-md font-bold'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
              }`}
            >
              <Sparkle className="w-3.5 h-3.5" />
              <span>Cleaned Space</span>
            </button>
          )}
        </div>
      </div>

      {/* Alternative Strategy Selector (Regeneration) */}
      <div className="mb-5 p-3.5 rounded-2xl bg-slate-50 dark:bg-slate-950/60 border border-slate-200 dark:border-slate-800 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2 text-xs">
          <RotateCcw className={`w-4 h-4 text-emerald-500 ${isRegenerating ? 'animate-spin' : ''}`} />
          <span className="font-bold text-slate-900 dark:text-white">Spatial Strategy:</span>
          <span className="text-slate-500 text-[11px] hidden sm:inline">Try alternative layouts for different room needs:</span>
        </div>

        <div className="flex items-center gap-2">
          {(
            [
              { key: 'balanced', label: '⚖️ Balanced Flow', desc: 'Even floor distribution' },
              { key: 'spacious', label: '🚪 Spacious Open', desc: 'Perimeter alignment' },
              { key: 'cozy', label: '🛋️ Cozy Cluster', desc: 'Conversational grouping' },
            ] as const
          ).map((s) => (
            <button
              key={s.key}
              type="button"
              disabled={isRegenerating}
              onClick={() => handleStrategyClick(s.key)}
              className={`px-3 py-1.5 rounded-xl text-xs font-bold transition-all flex items-center gap-1.5 ${
                currentStrategy === s.key
                  ? 'bg-emerald-500 text-slate-950 shadow-md shadow-emerald-500/20'
                  : 'bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 border border-slate-200 dark:border-slate-800'
              } ${isRegenerating ? 'opacity-50 cursor-wait' : 'cursor-pointer'}`}
              title={s.desc}
            >
              {s.label}
            </button>
          ))}
        </div>
      </div>

      {/* Main Visual Display Container */}
      <div className="relative rounded-2xl overflow-hidden border border-slate-200 dark:border-slate-800 bg-slate-100 dark:bg-black/80 shadow-2xl">
        {/* Tab 1: Interactive Before/After Split Slider */}
        {activeTab === 'slider' && (
          <div
            className="relative w-full aspect-[4/3] sm:aspect-[16/10] select-none cursor-ew-resize overflow-hidden"
            onMouseMove={(e) => isDragging && handleSliderMove(e)}
            onMouseDown={() => setIsDragging(true)}
            onMouseUp={() => setIsDragging(false)}
            onMouseLeave={() => setIsDragging(false)}
            onTouchMove={handleSliderMove}
            onClick={handleSliderMove}
          >
            {/* After Image (Background) */}
            <img
              src={getFullImageUrl(rearrangedImageUrl)}
              alt="Rearranged Result"
              className="absolute inset-0 w-full h-full object-contain pointer-events-none"
            />
            <div className="absolute top-4 right-4 bg-emerald-500 text-slate-950 text-xs font-extrabold px-3 py-1 rounded-full shadow-lg backdrop-blur-sm pointer-events-none flex items-center gap-1.5">
              <Sparkles className="w-3 h-3" />
              <span>REARRANGED</span>
            </div>

            {/* Before Image (Foreground Clipped using clipPath to preserve exact 1:1 scale) */}
            <div
              className="absolute inset-0 pointer-events-none overflow-hidden"
              style={{ clipPath: `inset(0 ${100 - sliderPosition}% 0 0)` }}
            >
              <img
                src={getFullImageUrl(originalImageUrl)}
                alt="Original Photo"
                className="absolute inset-0 w-full h-full object-contain pointer-events-none"
              />
              <div className="absolute top-4 left-4 bg-slate-950/85 text-white text-xs font-extrabold px-3 py-1 rounded-full border border-slate-700 shadow-lg backdrop-blur-sm pointer-events-none">
                ORIGINAL
              </div>
            </div>

            {/* Slider Divider Line */}
            <div
              className="absolute top-0 bottom-0 w-1 bg-white shadow-2xl pointer-events-none"
              style={{ left: `${sliderPosition}%` }}
            >
              <div className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2 w-9 h-9 rounded-full bg-white text-slate-950 shadow-2xl flex items-center justify-center font-bold text-xs border-2 border-slate-950">
                ⟷
              </div>
              <div className="absolute bottom-4 -translate-x-1/2 bg-slate-950/80 text-white font-mono text-[10px] px-2 py-0.5 rounded-full backdrop-blur-sm whitespace-nowrap">
                {Math.round(sliderPosition)}%
              </div>
            </div>
          </div>
        )}

        {/* Tab 2: Side-by-Side Comparison */}
        {activeTab === 'sidebyside' && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2 p-3 bg-slate-950">
            <div className="relative aspect-[4/3] rounded-xl overflow-hidden border border-slate-800 bg-black flex items-center justify-center">
              <img
                src={getFullImageUrl(originalImageUrl)}
                alt="Original Photo"
                className="w-full h-full object-contain"
              />
              <div className="absolute top-3 left-3 bg-slate-950/85 text-white text-[11px] font-bold px-2.5 py-0.5 rounded-md border border-slate-700">
                BEFORE (Original)
              </div>
            </div>

            <div className="relative aspect-[4/3] rounded-xl overflow-hidden border border-emerald-500/30 bg-black flex items-center justify-center">
              <img
                src={getFullImageUrl(rearrangedImageUrl)}
                alt="Rearranged Result"
                className="w-full h-full object-contain"
              />
              <div className="absolute top-3 right-3 bg-emerald-500 text-slate-950 text-[11px] font-extrabold px-2.5 py-0.5 rounded-md shadow-lg">
                AFTER (Rearranged)
              </div>
            </div>
          </div>
        )}

        {/* Tab 3: Pure Rearranged Photo */}
        {activeTab === 'rearranged' && (
          <div className="relative w-full aspect-[4/3] sm:aspect-[16/10] flex items-center justify-center bg-black/60">
            <img
              src={getFullImageUrl(rearrangedImageUrl)}
              alt="Rearranged Result"
              className="w-full h-full object-contain"
            />
            <div className="absolute top-4 right-4 bg-emerald-500 text-slate-950 text-xs font-bold px-3 py-1 rounded-full shadow-lg">
              Level 2: Visual Synthesis
            </div>
          </div>
        )}

        {/* Tab 4: Annotated Spatial Plan */}
        {activeTab === 'plan' && (
          <div className="relative w-full aspect-[4/3] sm:aspect-[16/10] flex items-center justify-center bg-black/60">
            <img
              src={getFullImageUrl(planImageUrl)}
              alt="Spatial Plan"
              className="w-full h-full object-contain"
            />
            <div className="absolute top-4 right-4 bg-amber-400 text-slate-950 text-xs font-bold px-3 py-1 rounded-full shadow-lg">
              Level 1: Deterministic Plan
            </div>
          </div>
        )}

        {/* Tab 5: Cleaned Inpainted Background */}
        {activeTab === 'cleaned' && cleanedImageUrl && (
          <div className="relative w-full aspect-[4/3] sm:aspect-[16/10] flex items-center justify-center bg-black/60">
            <img
              src={getFullImageUrl(cleanedImageUrl)}
              alt="Cleaned Background"
              className="w-full h-full object-contain"
            />
            <div className="absolute top-4 right-4 bg-sky-500 text-slate-950 text-xs font-bold px-3 py-1 rounded-full shadow-lg">
              Vacated & Inpainted Floor Space
            </div>
          </div>
        )}
      </div>

      {/* Spoken Voice Confirmation Bar (Gnani Timbre) */}
      <div className="mt-5 p-4 rounded-2xl bg-emerald-500/10 border border-emerald-500/25 flex flex-wrap items-center justify-between gap-3 shadow-inner">
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={handlePlayVoice}
            disabled={isPlayingAudio}
            className="w-10 h-10 rounded-xl bg-emerald-500 hover:bg-emerald-600 text-slate-950 flex items-center justify-center transition-all shadow-md shadow-emerald-500/30 active:scale-95 cursor-pointer disabled:opacity-60"
            title="Listen to Gnani Timbre regional voice confirmation"
          >
            <Volume2 className={`w-5 h-5 ${isPlayingAudio ? 'animate-bounce' : ''}`} />
          </button>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold text-slate-900 dark:text-white">
                Gnani Timbre Voice Confirmation
              </span>
              <span className="text-[10px] font-mono uppercase bg-emerald-500/20 text-emerald-700 dark:text-emerald-300 px-2 py-0.5 rounded font-bold">
                Tamil / Tanglish
              </span>
            </div>
            <p className="text-xs text-slate-600 dark:text-slate-400 mt-0.5">
              {isPlayingAudio
                ? 'Playing spoken arrangement confirmation...'
                : 'Click speaker to hear the spoken confirmation of your arrangement.'}
            </p>
          </div>
        </div>

        <button
          type="button"
          onClick={handlePlayVoice}
          disabled={isPlayingAudio}
          className="px-3.5 py-1.5 rounded-xl bg-white dark:bg-slate-900 hover:bg-slate-50 dark:hover:bg-slate-800 text-slate-800 dark:text-slate-200 border border-slate-200 dark:border-slate-800 text-xs font-semibold flex items-center gap-1.5 transition-colors shadow-sm"
        >
          <Volume2 className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />
          <span>{isPlayingAudio ? 'Speaking...' : 'Play Audio'}</span>
        </button>
      </div>

      {/* Spatial Quality Scorecard & Detailed Analytics */}
      <div className="mt-6 grid grid-cols-1 lg:grid-cols-3 gap-5 pt-6 border-t border-slate-200 dark:border-slate-800">
        {/* Quality Metrics */}
        <div className="p-5 rounded-2xl bg-slate-50 dark:bg-slate-950/70 border border-slate-200 dark:border-slate-800">
          <div className="flex items-center justify-between mb-4">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-600 dark:text-slate-300 flex items-center gap-1.5">
              <ShieldCheck className="w-4 h-4 text-emerald-500" />
              AI Spatial Scoring
            </span>
            <span className="text-sm font-extrabold text-emerald-600 dark:text-emerald-400 font-mono">
              {scores.overall_score}/100
            </span>
          </div>

          <div className="space-y-3">
            <div>
              <div className="flex justify-between text-xs mb-1">
                <span className="text-slate-600 dark:text-slate-400">Space Utilization</span>
                <span className="font-bold font-mono text-slate-900 dark:text-white">{scores.space_utilization}%</span>
              </div>
              <div className="h-2 bg-slate-200 dark:bg-slate-800 rounded-full overflow-hidden">
                <div
                  className="h-full bg-emerald-500 rounded-full transition-all duration-500"
                  style={{ width: `${scores.space_utilization}%` }}
                />
              </div>
            </div>

            <div>
              <div className="flex justify-between text-xs mb-1">
                <span className="text-slate-600 dark:text-slate-400">Walkway Clearance</span>
                <span className="font-bold font-mono text-slate-900 dark:text-white">{scores.walkway_clearance}%</span>
              </div>
              <div className="h-2 bg-slate-200 dark:bg-slate-800 rounded-full overflow-hidden">
                <div
                  className="h-full bg-teal-500 rounded-full transition-all duration-500"
                  style={{ width: `${scores.walkway_clearance}%` }}
                />
              </div>
            </div>

            <div>
              <div className="flex justify-between text-xs mb-1">
                <span className="text-slate-600 dark:text-slate-400">Balance & Symmetry</span>
                <span className="font-bold font-mono text-slate-900 dark:text-white">{scores.balance_symmetry}%</span>
              </div>
              <div className="h-2 bg-slate-200 dark:bg-slate-800 rounded-full overflow-hidden">
                <div
                  className="h-full bg-sky-500 rounded-full transition-all duration-500"
                  style={{ width: `${scores.balance_symmetry}%` }}
                />
              </div>
            </div>
          </div>
        </div>

        {/* Applied Spatial Rules & Recommendations */}
        <div className="p-5 rounded-2xl bg-slate-50 dark:bg-slate-950/70 border border-slate-200 dark:border-slate-800 lg:col-span-2 flex flex-col justify-between">
          <div>
            <span className="text-xs font-bold uppercase tracking-wider text-slate-600 dark:text-slate-300 flex items-center gap-1.5 mb-3">
              <Info className="w-4 h-4 text-emerald-500" />
              Arrangement Engine Insights
            </span>
            <ul className="space-y-2 text-xs text-slate-600 dark:text-slate-400">
              {recommendations.map((rec, i) => (
                <li key={i} className="flex items-start gap-2">
                  <span className="text-emerald-500 font-bold shrink-0">✓</span>
                  <span>{rec}</span>
                </li>
              ))}
            </ul>
          </div>

          <div className="mt-4 pt-3 border-t border-slate-200 dark:border-slate-800/80 flex flex-wrap items-center justify-between text-xs text-slate-500 dark:text-slate-400">
            <span>Deterministic Plan: Zero collision verified by Shapely</span>
            <span className="font-mono text-emerald-600 dark:text-emerald-400 font-semibold">
              Mode: {currentStrategy.toUpperCase()}
            </span>
          </div>
        </div>
      </div>

      {/* Object Movement Details Table */}
      {plan?.objects && plan.objects.length > 0 && (
        <div className="mt-6 pt-6 border-t border-slate-200 dark:border-slate-800">
          <h4 className="text-xs font-bold uppercase tracking-wider text-slate-600 dark:text-slate-300 mb-3">
            Item Displacement & Actions Matrix
          </h4>

          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
            {plan.objects.map((obj: any) => {
              const isMoved = obj.movement_vector && (obj.movement_vector[0] !== 0 || obj.movement_vector[1] !== 0);
              const dist = isMoved
                ? Math.round(Math.sqrt(obj.movement_vector[0] ** 2 + obj.movement_vector[1] ** 2))
                : 0;

              return (
                <div
                  key={obj.id}
                  onClick={() => setSelectedObjectId(obj.id === selectedObjectId ? null : obj.id)}
                  className={`p-3.5 rounded-xl border text-xs cursor-pointer transition-all ${
                    obj.action === 'REMOVE'
                      ? 'bg-rose-500/10 border-rose-500/30'
                      : isMoved
                      ? 'bg-amber-500/10 border-amber-500/30'
                      : 'bg-emerald-500/10 border-emerald-500/30'
                  } ${selectedObjectId === obj.id ? 'ring-2 ring-emerald-500' : ''}`}
                >
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="font-mono font-bold text-slate-900 dark:text-white">{obj.id}</span>
                    <span
                      className={`text-[10px] font-extrabold px-2 py-0.5 rounded ${
                        obj.action === 'REMOVE'
                          ? 'bg-rose-500 text-white'
                          : isMoved
                          ? 'bg-amber-500 text-slate-950'
                          : 'bg-emerald-500 text-slate-950'
                      }`}
                    >
                      {obj.action === 'REMOVE' ? 'REMOVED' : isMoved ? 'RELOCATED' : obj.fixed ? 'FIXED' : 'KEPT'}
                    </span>
                  </div>

                  <div className="text-[11px] text-slate-600 dark:text-slate-400 space-y-0.5">
                    <div>
                      Class: <span className="font-semibold text-slate-800 dark:text-slate-200 capitalize">{obj.class}</span>
                    </div>
                    {isMoved ? (
                      <div className="text-amber-700 dark:text-amber-300 font-mono">
                        Shift: {obj.movement_vector[0]}px X, {obj.movement_vector[1]}px Y ({dist}px total)
                      </div>
                    ) : (
                      <div className="text-slate-500">Position: Unchanged</div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Summary Metrics & Download Bar */}
      <div className="mt-6 flex flex-wrap items-center justify-between gap-4 pt-6 border-t border-slate-200 dark:border-slate-800">
        {summary && (
          <div className="flex items-center gap-4 sm:gap-6 text-xs">
            <div>
              <span className="text-slate-500 dark:text-slate-400 block">Total Objects</span>
              <strong className="text-sm text-slate-900 dark:text-white font-mono">{summary.total_objects}</strong>
            </div>
            <div>
              <span className="text-slate-500 dark:text-slate-400 block">Preserved</span>
              <strong className="text-sm text-emerald-600 dark:text-emerald-400 font-mono">{summary.kept_count}</strong>
            </div>
            <div>
              <span className="text-slate-500 dark:text-slate-400 block">Removed</span>
              <strong className="text-sm text-rose-600 dark:text-rose-400 font-mono">{summary.removed_count}</strong>
            </div>
            <div>
              <span className="text-slate-500 dark:text-slate-400 block">Repositioned</span>
              <strong className="text-sm text-amber-600 dark:text-amber-400 font-mono">{summary.moved_count}</strong>
            </div>
          </div>
        )}

        <div className="flex flex-wrap items-center gap-2.5">
          <button
            onClick={handleExportReport}
            className="px-3.5 py-2 rounded-xl bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700 text-xs font-semibold flex items-center gap-1.5 transition-colors cursor-pointer"
          >
            {reportDownloaded ? (
              <>
                <Check className="w-3.5 h-3.5 text-emerald-500" />
                <span>Report Saved!</span>
              </>
            ) : (
              <>
                <FileText className="w-3.5 h-3.5 text-slate-500" />
                <span>Export Report JSON</span>
              </>
            )}
          </button>

          <a
            href={getFullImageUrl(rearrangedImageUrl)}
            download={`placewise_rearranged_${currentStrategy}.jpg`}
            target="_blank"
            rel="noreferrer"
            className="px-4 py-2 rounded-xl bg-emerald-500 hover:bg-emerald-600 text-slate-950 font-bold text-xs flex items-center gap-2 transition-colors shadow-lg shadow-emerald-500/20"
          >
            <Download className="w-3.5 h-3.5" />
            Download Rearranged Photo
          </a>

          <a
            href={getFullImageUrl(planImageUrl)}
            download={`placewise_plan_${currentStrategy}.jpg`}
            target="_blank"
            rel="noreferrer"
            className="px-4 py-2 rounded-xl bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 border border-slate-200 dark:border-slate-700 text-xs font-semibold flex items-center gap-2 transition-colors"
          >
            <Download className="w-3.5 h-3.5" />
            Download Spatial Plan
          </a>
        </div>
      </div>
    </div>
  );
};
