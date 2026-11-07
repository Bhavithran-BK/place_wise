import React from 'react';
import { Layers, ShieldCheck, Sun, Moon, BarChart3 } from 'lucide-react';

interface NavbarProps {
  serverHealthy: boolean;
  onReset: () => void;
  darkMode: boolean;
  onToggleTheme: () => void;
  onOpenMetrics?: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  serverHealthy,
  onReset,
  darkMode,
  onToggleTheme,
  onOpenMetrics,
}) => {
  return (
    <header className="sticky top-0 z-50 transition-colors duration-200 border-b bg-white/95 dark:bg-slate-900/90 border-slate-200 dark:border-slate-800 backdrop-blur-md shadow-sm dark:shadow-none">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Brand */}
        <div className="flex items-center gap-3 cursor-pointer select-none" onClick={onReset}>
          <div className="h-10 w-10 rounded-xl bg-emerald-500 flex items-center justify-center shadow-md shadow-emerald-500/20">
            <Layers className="h-5 w-5 text-slate-950 font-bold" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xl font-extrabold tracking-tight text-slate-900 dark:text-white">
                PLACE<span className="text-emerald-600 dark:text-emerald-400">WISE</span>
              </span>
              <span className="text-[11px] px-2 py-0.5 rounded-full bg-emerald-50 dark:bg-emerald-500/10 border border-emerald-200 dark:border-emerald-500/20 text-emerald-700 dark:text-emerald-400 font-bold tracking-wide">
                Voice Space Rearranger
              </span>
            </div>
            <p className="text-xs text-slate-500 dark:text-slate-400 hidden sm:block">
              Upload Photo • Speak Tanglish • Visual Rearrangement
            </p>
          </div>
        </div>

        {/* Status & Controls */}
        <div className="flex items-center gap-2.5 sm:gap-3">
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-slate-100 dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700 text-xs">
            <span
              className={`h-2 w-2 rounded-full ${
                serverHealthy ? 'bg-emerald-500 animate-pulse' : 'bg-amber-400'
              }`}
            />
            <span className="text-slate-700 dark:text-slate-300 font-semibold hidden sm:inline">
              {serverHealthy ? 'FastAPI + YOLOv8 Online' : 'Connecting...'}
            </span>
          </div>

          {onOpenMetrics && (
            <button
              onClick={onOpenMetrics}
              className="hidden md:flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-xl bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:text-emerald-600 dark:hover:text-emerald-400 border border-slate-200 dark:border-slate-700 transition-colors"
            >
              <BarChart3 className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />
              <span>Evaluation</span>
            </button>
          )}

          {/* Theme Toggle Button */}
          <button
            onClick={onToggleTheme}
            className="p-2 rounded-xl bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-200 hover:text-slate-950 dark:hover:text-white border border-slate-200 dark:border-slate-700 transition-colors shadow-sm flex items-center justify-center cursor-pointer"
            title={darkMode ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
            aria-label="Toggle theme"
          >
            {darkMode ? (
              <Sun className="w-4 h-4 text-amber-400" />
            ) : (
              <Moon className="w-4 h-4 text-slate-700" />
            )}
          </button>
        </div>
      </div>
    </header>
  );
};
