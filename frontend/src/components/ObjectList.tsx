import React, { useState } from 'react';
import { DetectedObject } from '../types';
import { Check, Trash2, Pin, Edit3, Sparkles, AlertCircle, HelpCircle } from 'lucide-react';

interface ObjectListProps {
  objects?: DetectedObject[];
  selectedObjectId: string | null;
  onSelectObject: (id: string | null) => void;
  onUpdateObject: (id: string, updates: Partial<DetectedObject>) => void;
  clarificationMessage?: string | null;
  clarificationCandidates?: string[];
}

export const ObjectList: React.FC<ObjectListProps> = ({
  objects = [],
  selectedObjectId,
  onSelectObject,
  onUpdateObject,
  clarificationMessage,
  clarificationCandidates = [],
}) => {
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editedName, setEditedName] = useState('');

  const safeObjects = objects || [];

  const handleStartRename = (obj: DetectedObject) => {
    setEditingId(obj.object_id);
    setEditedName(obj.class);
  };

  const handleSaveRename = (id: string) => {
    if (editedName.trim()) {
      onUpdateObject(id, { class: editedName.trim().toLowerCase() });
    }
    setEditingId(null);
  };

  const keepCount = safeObjects.filter((o) => o?.action === 'KEEP').length;
  const removeCount = safeObjects.filter((o) => o?.action === 'REMOVE').length;
  const unassignedCount = safeObjects.filter((o) => !o?.action).length;

  return (
    <div className="flex flex-col h-full bg-white dark:bg-slate-900/80 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 shadow-xl transition-colors">
      {/* Header */}
      <div className="flex items-center justify-between pb-4 border-b border-slate-200 dark:border-slate-800">
        <div>
          <h4 className="font-bold text-slate-900 dark:text-white text-base">Detected Objects</h4>
          <p className="text-xs text-slate-500 dark:text-slate-400">YOLOv8 + SAM Segmentation</p>
        </div>
        <div className="flex items-center gap-1.5 text-xs font-semibold">
          <span className="px-2.5 py-1 rounded-full bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border border-emerald-500/20 font-mono">
            {safeObjects.length} Items
          </span>
        </div>
      </div>

      {/* Clarification Alert Banner if Ambiguity/Contradiction was detected */}
      {clarificationMessage && (
        <div className="my-3 p-3.5 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-900 dark:text-amber-200 text-xs flex items-start gap-2.5 shadow-sm animate-pulse">
          <HelpCircle className="w-4 h-4 text-amber-500 shrink-0 mt-0.5" />
          <div>
            <span className="font-bold block mb-0.5">Clarification Required</span>
            <span>{clarificationMessage}</span>
          </div>
        </div>
      )}

      {/* Action Stats */}
      <div className="grid grid-cols-2 gap-2 my-3">
        <div className="bg-emerald-50 dark:bg-emerald-950/20 border border-emerald-200 dark:border-emerald-800/40 rounded-xl p-2.5 text-center">
          <div className="text-xs text-slate-500 dark:text-slate-400 flex items-center justify-center gap-1">
            <span className="w-2 h-2 rounded-full bg-emerald-500" />
            Marked to KEEP
          </div>
          <div className="text-lg font-bold text-emerald-600 dark:text-emerald-400">{keepCount}</div>
        </div>
        <div className="bg-rose-50 dark:bg-rose-950/20 border border-rose-200 dark:border-rose-800/40 rounded-xl p-2.5 text-center">
          <div className="text-xs text-slate-500 dark:text-slate-400 flex items-center justify-center gap-1">
            <span className="w-2 h-2 rounded-full bg-rose-500" />
            Marked to REMOVE
          </div>
          <div className="text-lg font-bold text-rose-600 dark:text-rose-400">{removeCount}</div>
        </div>
      </div>

      {/* Table Header: Object ID | Object Name | Action */}
      <div className="grid grid-cols-12 gap-2 text-[11px] font-bold uppercase tracking-wider text-slate-400 px-3 py-1.5 border-b border-slate-100 dark:border-slate-800">
        <span className="col-span-4">Object ID</span>
        <span className="col-span-4">Name</span>
        <span className="col-span-4 text-right">Action</span>
      </div>

      {/* Objects Scroll Area */}
      <div className="flex-1 overflow-y-auto space-y-2 pr-1 my-2">
        {safeObjects.length === 0 ? (
          <div className="text-center py-12 text-slate-400 text-sm">
            No objects detected yet.
          </div>
        ) : (
          safeObjects.map((obj) => {
            if (!obj) return null;
            const isSelected = selectedObjectId === obj.object_id;
            const isCandidate = clarificationCandidates.includes(obj.object_id);

            return (
              <div
                key={obj.object_id}
                onClick={() => onSelectObject(isSelected ? null : obj.object_id)}
                className={`p-3 rounded-xl border transition-all cursor-pointer ${
                  isCandidate
                    ? 'border-amber-500 bg-amber-500/10 ring-2 ring-amber-500/40'
                    : isSelected
                    ? 'border-sky-500 bg-sky-50 dark:bg-sky-500/10 ring-1 ring-sky-500/30'
                    : obj.action === 'KEEP'
                    ? 'border-emerald-500/30 bg-emerald-50/40 dark:bg-emerald-950/10'
                    : obj.action === 'REMOVE'
                    ? 'border-rose-500/30 bg-rose-50/40 dark:bg-rose-950/10'
                    : 'border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/40'
                }`}
              >
                <div className="grid grid-cols-12 gap-2 items-center">
                  {/* Object ID */}
                  <div className="col-span-4 flex items-center gap-1.5 min-w-0">
                    <span className="font-mono text-xs font-bold text-slate-800 dark:text-slate-200 bg-slate-200/80 dark:bg-slate-900 px-2 py-0.5 rounded border border-slate-300 dark:border-slate-700 truncate">
                      {obj.object_id}
                    </span>
                  </div>

                  {/* Object Name (Editable) */}
                  <div className="col-span-4 flex items-center gap-1 min-w-0">
                    {editingId === obj.object_id ? (
                      <input
                        type="text"
                        value={editedName}
                        onChange={(e) => setEditedName(e.target.value)}
                        onBlur={() => handleSaveRename(obj.object_id)}
                        onKeyDown={(e) => e.key === 'Enter' && handleSaveRename(obj.object_id)}
                        className="bg-white dark:bg-slate-900 border border-emerald-500 text-xs text-slate-900 dark:text-white px-2 py-0.5 rounded w-full focus:outline-none"
                        autoFocus
                        onClick={(e) => e.stopPropagation()}
                      />
                    ) : (
                      <span className="text-xs font-semibold text-slate-800 dark:text-white capitalize truncate">
                        {obj.class}
                      </span>
                    )}

                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleStartRename(obj);
                      }}
                      className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 p-0.5 shrink-0"
                      title="Rename class"
                    >
                      <Edit3 className="w-3 h-3" />
                    </button>
                  </div>

                  {/* Actions: Green KEEP, Red REMOVE */}
                  <div className="col-span-4 flex items-center justify-end gap-1">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onUpdateObject(obj.object_id, { action: obj.action === 'KEEP' ? null : 'KEEP' });
                      }}
                      className={`px-2 py-1 rounded text-[10px] font-bold flex items-center gap-0.5 transition-all ${
                        obj.action === 'KEEP'
                          ? 'bg-emerald-500 text-slate-950 shadow-sm shadow-emerald-500/30'
                          : 'bg-slate-200 dark:bg-slate-800 text-slate-600 dark:text-slate-400 hover:bg-emerald-500/20 hover:text-emerald-600'
                      }`}
                      title="Set action to KEEP (Green)"
                    >
                      <Check className="w-3 h-3" />
                      KEEP
                    </button>

                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onUpdateObject(obj.object_id, { action: obj.action === 'REMOVE' ? null : 'REMOVE' });
                      }}
                      className={`px-2 py-1 rounded text-[10px] font-bold flex items-center gap-0.5 transition-all ${
                        obj.action === 'REMOVE'
                          ? 'bg-rose-500 text-white shadow-sm shadow-rose-500/30'
                          : 'bg-slate-200 dark:bg-slate-800 text-slate-600 dark:text-slate-400 hover:bg-rose-500/20 hover:text-rose-600'
                      }`}
                      title="Set action to REMOVE (Red)"
                    >
                      <Trash2 className="w-3 h-3" />
                      REMOVE
                    </button>
                  </div>
                </div>

                {/* Sub-row: Pin fixed toggle */}
                <div className="flex items-center justify-between mt-2 pt-1.5 border-t border-slate-100 dark:border-slate-800/60 text-[11px]">
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onUpdateObject(obj.object_id, { fixed: !obj.fixed });
                    }}
                    className={`flex items-center gap-1 px-1.5 py-0.5 rounded transition-colors ${
                      obj.fixed
                        ? 'bg-amber-500/20 text-amber-700 dark:text-amber-300 border border-amber-500/30'
                        : 'text-slate-400 hover:text-slate-700 dark:hover:text-slate-300'
                    }`}
                  >
                    <Pin className="w-3 h-3" />
                    {obj.fixed ? 'Fixed (wall/floor)' : 'Can move'}
                  </button>

                  <span className="text-[10px] font-mono text-slate-400">
                    Conf: {Math.round((obj.confidence || 0.9) * 100)}%
                  </span>
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Next Step Callout */}
      <div className="pt-3 border-t border-slate-200 dark:border-slate-800">
        <div className="p-3 rounded-xl bg-gradient-to-r from-emerald-500/10 to-teal-500/10 border border-emerald-500/20 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-emerald-500" />
            <span className="text-xs text-slate-700 dark:text-slate-300 font-medium">Ready for Step 3: Voice input</span>
          </div>
          <span className="text-[10px] uppercase font-bold text-emerald-700 dark:text-emerald-400 bg-emerald-500/20 px-2 py-0.5 rounded-full">
            Gnani Prisma
          </span>
        </div>
      </div>
    </div>
  );
};

// Also export as ObjectEditor for direct naming compatibility
export const ObjectEditor = ObjectList;
export default ObjectList;
