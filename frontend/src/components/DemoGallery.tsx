import React from 'react';
import { Sparkles, ArrowRight, Home, Store, BedDouble } from 'lucide-react';

interface DemoGalleryProps {
  onSelectDemo: (demoPath: string) => void;
}

export const DemoGallery: React.FC<DemoGalleryProps> = ({ onSelectDemo }) => {
  const demos = [
    {
      id: 'demo-living',
      title: 'Cluttered Living Room',
      subtitle: 'Sofa, coffee table, 2 chairs, TV',
      tag: 'Scenario 1 • Tanglish',
      path: '/storage/uploads/demo_room_01.jpg',
      icon: Home,
      prompt: 'Indha rendu chairs vendaam. Sofa venum.',
    },
    {
      id: 'demo-bedroom',
      title: 'Rental Bedroom',
      subtitle: 'Bed, wardrobe, side table & chair',
      tag: 'Scenario 2 • Space Clear',
      path: '/storage/uploads/demo_bedroom.jpg',
      icon: BedDouble,
      prompt: 'Bed and wardrobe irukkattum. Chair remove pannunga.',
    },
    {
      id: 'demo-shop',
      title: 'Kirana Retail Shop',
      subtitle: 'Counter table, shelves, boxes & stool',
      tag: 'Scenario 3 • Commercial',
      path: '/storage/uploads/demo_shop.jpg',
      icon: Store,
      prompt: 'Indha boxes and stool vendaam. Counter neat ah arrange pannunga.',
    },
  ];

  return (
    <div className="w-full max-w-5xl mx-auto mt-10">
      <div className="flex items-center gap-2 mb-4 justify-center">
        <Sparkles className="w-4 h-4 text-emerald-400" />
        <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400">
          Fast Evaluation — 1-Click Hackathon Scenarios
        </h3>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-3.5">
        {demos.map((d) => {
          const Icon = d.icon;
          return (
            <div
              key={d.id}
              onClick={() => onSelectDemo(d.path)}
              className="group relative rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/60 hover:bg-slate-50 dark:hover:bg-slate-900 hover:border-emerald-500/50 p-4 transition-all duration-200 cursor-pointer flex flex-col justify-between shadow-lg"
            >
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[10px] font-extrabold uppercase tracking-wider text-emerald-700 dark:text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                    {d.tag}
                  </span>
                  <div className="w-7 h-7 rounded-lg bg-slate-100 dark:bg-slate-800 flex items-center justify-center text-slate-600 dark:text-slate-400 group-hover:text-emerald-500 group-hover:bg-emerald-500/20 transition-all">
                    <Icon className="w-3.5 h-3.5" />
                  </div>
                </div>

                <h4 className="font-bold text-slate-900 dark:text-white text-sm group-hover:text-emerald-600 dark:group-hover:text-emerald-300 transition-colors">
                  {d.title}
                </h4>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">{d.subtitle}</p>

                <div className="mt-3 p-2 rounded-lg bg-slate-50 dark:bg-slate-950/80 border border-slate-200 dark:border-slate-800/80 text-[11px] font-mono text-slate-600 dark:text-slate-400 italic">
                  "{d.prompt}"
                </div>
              </div>

              <div className="mt-4 pt-3 border-t border-slate-200 dark:border-slate-800/60 flex items-center justify-between text-xs font-semibold text-slate-600 dark:text-slate-400 group-hover:text-emerald-600 dark:group-hover:text-emerald-400 transition-colors">
                <span>Load Scenario</span>
                <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-1 transition-transform" />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
