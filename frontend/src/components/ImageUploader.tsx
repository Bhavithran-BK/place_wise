import React, { useState, useRef } from 'react';
import { Upload, Image as ImageIcon, Sparkles, AlertCircle } from 'lucide-react';

interface ImageUploaderProps {
  onImageSelected: (file: File) => void;
  onSelectSample: () => void;
  isLoading: boolean;
}

export const ImageUploader: React.FC<ImageUploaderProps> = ({
  onImageSelected,
  onSelectSample,
  isLoading,
}) => {
  const [isDragOver, setIsDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const file = e.dataTransfer.files[0];
      if (file.type.startsWith('image/')) {
        onImageSelected(file);
      }
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      onImageSelected(e.target.files[0]);
    }
  };

  return (
    <div className="w-full max-w-2xl mx-auto">
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setIsDragOver(true);
        }}
        onDragLeave={() => setIsDragOver(false)}
        onDrop={handleDrop}
        onClick={() => !isLoading && fileInputRef.current?.click()}
        className={`relative border-2 border-dashed rounded-3xl p-8 sm:p-12 text-center cursor-pointer transition-all duration-300 shadow-lg ${
          isDragOver
            ? 'border-emerald-500 bg-emerald-500/10 scale-[1.01]'
            : 'border-slate-300 dark:border-slate-700 hover:border-emerald-500 dark:hover:border-emerald-500/70 bg-white dark:bg-slate-900/60 hover:bg-slate-50 dark:hover:bg-slate-900/90'
        } ${isLoading ? 'opacity-60 cursor-not-allowed' : ''}`}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept="image/jpeg,image/png,image/webp"
          className="hidden"
          onChange={handleFileChange}
          disabled={isLoading}
        />

        <div className="mx-auto w-16 h-16 rounded-2xl bg-emerald-50 dark:bg-emerald-500/20 border border-emerald-200 dark:border-emerald-500/30 flex items-center justify-center mb-5 text-emerald-600 dark:text-emerald-400">
          <Upload className="w-8 h-8" />
        </div>

        <h3 className="text-xl font-extrabold text-slate-900 dark:text-white mb-2">
          Upload Room Photograph
        </h3>
        <p className="text-sm text-slate-600 dark:text-slate-400 max-w-md mx-auto mb-6 leading-relaxed">
          Capture or drop a photo of your living room, shop, kitchen, or bedroom. No measurements or floor plans needed.
        </p>

        <div className="flex flex-wrap items-center justify-center gap-3">
          <button
            type="button"
            className="px-5 py-2.5 rounded-xl bg-emerald-500 hover:bg-emerald-600 text-slate-950 font-bold text-sm transition-colors shadow-lg shadow-emerald-500/20 flex items-center gap-2 cursor-pointer"
          >
            <ImageIcon className="w-4 h-4" />
            Browse Image
          </button>

          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              onSelectSample();
            }}
            className="px-5 py-2.5 rounded-xl bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-800 dark:text-slate-200 border border-slate-200 dark:border-slate-700 text-sm font-bold transition-colors flex items-center gap-2 cursor-pointer"
          >
            <Sparkles className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
            Load Sample Room Demo
          </button>
        </div>

        <div className="mt-6 flex items-center justify-center gap-2 text-xs text-slate-500 dark:text-slate-400">
          <AlertCircle className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />
          <span>Supports JPG, PNG, WEBP • Auto-detected with YOLOv8 & SAM</span>
        </div>
      </div>
    </div>
  );
};
