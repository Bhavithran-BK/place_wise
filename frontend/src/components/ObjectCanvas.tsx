import React, { useRef, useState } from 'react';
import { DetectedObject } from '../types';
import { getFullImageUrl } from '../api/client';
import { Check, Trash2, Pin } from 'lucide-react';

interface ObjectCanvasProps {
  imageUrl: string;
  originalWidth: number;
  originalHeight: number;
  objects: DetectedObject[];
  selectedObjectId: string | null;
  onSelectObject: (id: string | null) => void;
  onToggleAction?: (id: string, action: 'KEEP' | 'REMOVE' | null) => void;
}

export const ObjectCanvas: React.FC<ObjectCanvasProps> = ({
  imageUrl,
  originalWidth,
  originalHeight,
  objects = [],
  selectedObjectId,
  onSelectObject,
  onToggleAction,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [hoveredObjectId, setHoveredObjectId] = useState<string | null>(null);

  const safeObjects = objects || [];

  // Color mapping based on action state
  const getObjectColor = (obj: DetectedObject, isSelected: boolean) => {
    if (obj.action === 'KEEP') return { border: '#10b981', fill: 'rgba(16, 185, 129, 0.2)', textBg: 'bg-emerald-600' };
    if (obj.action === 'REMOVE') return { border: '#ef4444', fill: 'rgba(239, 68, 68, 0.25)', textBg: 'bg-rose-600' };
    if (isSelected) return { border: '#38bdf8', fill: 'rgba(56, 189, 248, 0.2)', textBg: 'bg-sky-500' };
    return { border: '#e2e8f0', fill: 'rgba(226, 232, 240, 0.08)', textBg: 'bg-slate-800' };
  };

  return (
    <div className="relative w-full rounded-2xl overflow-hidden border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/60 shadow-xl flex flex-col items-center transition-colors">
      <div className="relative w-full max-h-[70vh] flex items-center justify-center overflow-hidden bg-slate-100 dark:bg-black/40" ref={containerRef}>
        <img
          src={getFullImageUrl(imageUrl)}
          alt="Uploaded Room"
          className="w-full h-auto max-h-[70vh] object-contain select-none block"
        />

        {/* Scaled SVG overlay using viewBox for pixel-perfect coordinates */}
        {originalWidth > 0 && originalHeight > 0 && (
          <svg
            viewBox={`0 0 ${originalWidth} ${originalHeight}`}
            className="absolute inset-0 w-full h-full pointer-events-none"
            preserveAspectRatio="xMidYMid meet"
          >
            <defs>
              <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
                <feDropShadow dx="0" dy="2" stdDeviation="4" floodColor="#10b981" floodOpacity="0.6"/>
              </filter>
            </defs>

            {safeObjects.map((obj) => {
              if (!obj || !obj.bbox || obj.bbox.length < 4) return null;
              const [x1, y1, x2, y2] = obj.bbox;
              const w = x2 - x1;
              const h = y2 - y1;
              const isSelected = selectedObjectId === obj.object_id;
              const isHovered = hoveredObjectId === obj.object_id;
              const colors = getObjectColor(obj, isSelected);

              return (
                <g
                  key={obj.object_id}
                  className="pointer-events-auto cursor-pointer transition-all duration-150"
                  onClick={() => onSelectObject(isSelected ? null : obj.object_id)}
                  onMouseEnter={() => setHoveredObjectId(obj.object_id)}
                  onMouseLeave={() => setHoveredObjectId(null)}
                >
                  {/* Bounding box rectangle */}
                  <rect
                    x={x1}
                    y={y1}
                    width={w}
                    height={h}
                    fill={colors.fill}
                    stroke={colors.border}
                    strokeWidth={isSelected || isHovered ? 3.5 : 2}
                    strokeDasharray={obj.action === 'REMOVE' ? '6 4' : 'none'}
                    rx={6}
                    filter={isSelected ? 'url(#glow)' : undefined}
                  />

                  {/* Top-left label badge with class & confidence */}
                  <g transform={`translate(${x1}, ${Math.max(18, y1 - 6)})`}>
                    <rect
                      x={0}
                      y={-18}
                      width={Math.max(80, (obj.object_id.length + 8) * 9)}
                      height={20}
                      fill={colors.border}
                      rx={4}
                    />
                    <text
                      x={6}
                      y={-4}
                      fill="#0f172a"
                      fontSize="12"
                      fontWeight="bold"
                      fontFamily="sans-serif"
                    >
                      {obj.object_id} • {Math.round((obj.confidence || 0.9) * 100)}%
                    </text>
                  </g>
                </g>
              );
            })}
          </svg>
        )}
      </div>

      {/* Footer controls for selected object */}
      {selectedObjectId && (
        <div className="w-full bg-slate-50 dark:bg-slate-900 border-t border-slate-200 dark:border-slate-800 p-3 px-5 flex flex-wrap items-center justify-between gap-3 text-sm">
          {(() => {
            const selected = safeObjects.find((o) => o.object_id === selectedObjectId);
            if (!selected) return null;
            return (
              <>
                <div className="flex items-center gap-3">
                  <span className="font-mono font-bold text-slate-800 dark:text-white bg-slate-200 dark:bg-slate-800 px-2.5 py-1 rounded-md border border-slate-300 dark:border-slate-700">
                    {selected.object_id}
                  </span>
                  <span className="text-slate-600 dark:text-slate-400">Class: <strong className="text-slate-900 dark:text-slate-200 capitalize">{selected.class}</strong></span>
                  <span className="text-slate-600 dark:text-slate-400">Confidence: <strong className="text-emerald-600 dark:text-emerald-400">{Math.round((selected.confidence || 0.9) * 100)}%</strong></span>
                  {selected.fixed && (
                    <span className="flex items-center gap-1 text-xs bg-amber-500/10 border border-amber-500/30 text-amber-600 dark:text-amber-300 px-2 py-0.5 rounded font-semibold">
                      <Pin className="w-3 h-3" /> Fixed
                    </span>
                  )}
                </div>

                {onToggleAction && (
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-slate-500 dark:text-slate-400 mr-1">Action:</span>
                    <button
                      onClick={() => onToggleAction(selected.object_id, selected.action === 'KEEP' ? null : 'KEEP')}
                      className={`px-3 py-1 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-all ${
                        selected.action === 'KEEP'
                          ? 'bg-emerald-500 text-slate-950 font-bold shadow-md shadow-emerald-500/20'
                          : 'bg-slate-200 dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-300 dark:hover:bg-slate-700'
                      }`}
                    >
                      <Check className="w-3.5 h-3.5" />
                      KEEP
                    </button>
                    <button
                      onClick={() => onToggleAction(selected.object_id, selected.action === 'REMOVE' ? null : 'REMOVE')}
                      className={`px-3 py-1 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-all ${
                        selected.action === 'REMOVE'
                          ? 'bg-rose-500 text-white font-bold shadow-md shadow-rose-500/20'
                          : 'bg-slate-200 dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-300 dark:hover:bg-slate-700'
                      }`}
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                      REMOVE
                    </button>
                  </div>
                )}
              </>
            );
          })()}
        </div>
      )}
    </div>
  );
};
