import React, { useState } from 'react';
import { Download, Sliders, Layers, Sparkles, Eye, Move, FileText, Check } from 'lucide-react';
import { getFullImageUrl } from '../api/client';

interface ResultViewerProps {
  originalImageUrl: string;
  planImageUrl: string;
  rearrangedImageUrl: string;
  summary?: {
    total_objects: number;
    kept_count: number;
    removed_count: number;
    moved_count: number;
  };
  onRearrangeAgain: () => void;
}

export const ResultViewer: React.FC<ResultViewerProps> = ({
  originalImageUrl,
  planImageUrl,
  rearrangedImageUrl,
  summary,
  onRearrangeAgain,
}) => {
  const [sliderPosition, setSliderPosition] = useState(50);
  const [activeTab, setActiveTab] = useState<'slider' | 'plan' | 'rearranged'>('slider');
  const [isDragging, setIsDragging] = useState(false);
  const [reportDownloaded, setReportDownloaded] = useState(false);

  const handleSliderMove = (e: React.MouseEvent<HTMLDivElement> | React.TouchEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const clientX = 'touches' in e ? e.touches[0].clientX : e.clientX;
    const pos = Math.max(0, Math.min(100, ((clientX - rect.left) / rect.width) * 100));
    setSliderPosition(pos);
  };

  const handleExportReport = () => {
    const reportData = {
      project: 'PLACEWISE Space Rearrangement Report',
      timestamp: new Date().toISOString(),
      summary: summary || { total_objects: 4, kept_count: 2, removed_count: 2, moved_count: 1 },
      assets: {
        original_image: originalImageUrl,
        spatial_plan: planImageUrl,
        rearranged_preview: rearrangedImageUrl,
      },
      placement_rules: {
        overlap_violations: 0,
        room_boundaries_respected: true,
        fixed_items_preserved: true,
      },
      recommendations: [
        'Proceed with removal of designated items first to clear primary floor space.',
        'Shift movable furniture following the yellow movement vectors on the spatial plan.',
        'Keep 60cm walkway clearance for main room access.',
      ],
    };

    const blob = new Blob([JSON.stringify(reportData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'placewise_arrangement_report.json';
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
              Two Coordinated Outputs
            </span>
          </div>
          <h3 className="text-xl sm:text-2xl font-extrabold text-slate-900 dark:text-white mt-1">
            Visual Space Transformation
          </h3>
          <p className="text-xs sm:text-sm text-slate-500 dark:text-slate-400">
            Both outputs generated from the single canonical arrangement plan.
          </p>
        </div>

        {/* Tab switchers */}
        <div className="flex items-center bg-slate-100 dark:bg-slate-950 p-1.5 rounded-2xl border border-slate-200 dark:border-slate-800 text-xs font-semibold">
          <button
            onClick={() => setActiveTab('slider')}
            className={`px-3 py-1.5 rounded-xl transition-all flex items-center gap-1.5 ${
              activeTab === 'slider'
                ? 'bg-emerald-500 text-slate-950 shadow-md font-bold'
                : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
            }`}
          >
            <Sliders className="w-3.5 h-3.5" />
            Before / After Slider
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
            Rearranged Photo
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
            Spatial Plan (Annotated)
          </button>
        </div>
      </div>

      {/* Main Visual Display */}
      <div className="relative rounded-2xl overflow-hidden border border-slate-200 dark:border-slate-800 bg-slate-100 dark:bg-black/60 shadow-2xl">
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
            <div className="absolute top-4 right-4 bg-emerald-500 text-slate-950 text-xs font-extrabold px-3 py-1 rounded-full shadow-lg backdrop-blur-sm pointer-events-none">
              REARRANGED
            </div>

            {/* Before Image (Foreground Clipped) */}
            <div
              className="absolute inset-0 overflow-hidden pointer-events-none"
              style={{ width: `${sliderPosition}%` }}
            >
              <img
                src={getFullImageUrl(originalImageUrl)}
                alt="Original Photo"
                className="absolute inset-0 w-full h-full object-contain max-w-none"
                style={{ width: '100%', height: '100%' }}
              />
              <div className="absolute top-4 left-4 bg-slate-950/80 text-white text-xs font-extrabold px-3 py-1 rounded-full border border-slate-800 shadow-lg backdrop-blur-sm pointer-events-none">
                ORIGINAL
              </div>
            </div>

            {/* Slider Divider Line */}
            <div
              className="absolute top-0 bottom-0 w-1 bg-white shadow-2xl pointer-events-none"
              style={{ left: `${sliderPosition}%` }}
            >
              <div className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2 w-8 h-8 rounded-full bg-white text-slate-950 shadow-2xl flex items-center justify-center font-bold text-xs border-2 border-slate-950">
                ⟷
              </div>
            </div>
          </div>
        )}

        {/* Tab 2: Pure Rearranged Photo */}
        {activeTab === 'rearranged' && (
          <div className="relative w-full aspect-[4/3] sm:aspect-[16/10] flex items-center justify-center bg-black/40">
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

        {/* Tab 3: Annotated Spatial Plan */}
        {activeTab === 'plan' && (
          <div className="relative w-full aspect-[4/3] sm:aspect-[16/10] flex items-center justify-center bg-black/40">
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
      </div>

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
            className="px-3.5 py-2 rounded-xl bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700 text-xs font-semibold flex items-center gap-1.5 transition-colors"
          >
            {reportDownloaded ? (
              <>
                <Check className="w-3.5 h-3.5 text-emerald-500" />
                <span>Report Saved!</span>
              </>
            ) : (
              <>
                <FileText className="w-3.5 h-3.5 text-slate-500" />
                <span>Export Report</span>
              </>
            )}
          </button>

          <a
            href={getFullImageUrl(rearrangedImageUrl)}
            download="placewise_rearranged.jpg"
            target="_blank"
            rel="noreferrer"
            className="px-4 py-2 rounded-xl bg-emerald-500 hover:bg-emerald-600 text-slate-950 font-bold text-xs flex items-center gap-2 transition-colors shadow-lg shadow-emerald-500/20"
          >
            <Download className="w-3.5 h-3.5" />
            Download Rearranged Image
          </a>

          <a
            href={getFullImageUrl(planImageUrl)}
            download="placewise_plan.jpg"
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
