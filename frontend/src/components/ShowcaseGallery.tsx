import React from 'react';
import { ArrowRight, Volume2, Sparkles, Check, Move, Eye } from 'lucide-react';

export const ShowcaseGallery: React.FC = () => {
  const showcaseItems = [
    {
      title: 'Living Rooms & Lounges',
      subtitle: 'Remove bulky coffee tables and center seating',
      image: '/images/living_room.jpg',
      tag: 'Declutter & Reposition',
      voiceExample: '"Indha rendu chairs vendaam. Sofa center-la venum."',
    },
    {
      title: 'Compact Bedrooms',
      subtitle: 'Preserve key wardrobes and clear walkways',
      image: '/images/bedroom.jpg',
      tag: 'Space Optimization',
      voiceExample: '"Bed and wardrobe irukkattum. Corner box remove pannu."',
    },
    {
      title: 'Studies & Workspaces',
      subtitle: 'Open up natural lighting and streamline desks',
      image: '/images/workspace.jpg',
      tag: 'Focus Layouts',
      voiceExample: '"Table-ai window pakkam move pannunga."',
    },
    {
      title: 'Retail & Commercial Counters',
      subtitle: 'Optimize shelf visibility and customer queue lines',
      image: '/images/modern_lounge.jpg',
      tag: 'Commercial Utility',
      voiceExample: '"Stool vendaam. Display rack neat-a arrange pannunga."',
    },
  ];

  return (
    <div className="w-full max-w-6xl mx-auto mt-16 pt-12 border-t border-slate-200 dark:border-slate-800">
      {/* Title */}
      <div className="text-center max-w-2xl mx-auto mb-10">
        <span className="text-xs font-extrabold uppercase tracking-widest text-emerald-600 dark:text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-3 py-1 rounded-full inline-flex items-center gap-1.5">
          <Eye className="w-3.5 h-3.5" />
          Real-World Applications
        </span>
        <h2 className="text-2xl sm:text-3xl font-extrabold text-slate-900 dark:text-white mt-3">
          Designed for Everyday Physical Spaces
        </h2>
        <p className="text-sm text-slate-600 dark:text-slate-400 mt-2">
          No architectural floor plans or 3D modeling skills needed. Upload one photo and speak naturally in your mother tongue.
        </p>
      </div>

      {/* Picture Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        {showcaseItems.map((item, idx) => (
          <div
            key={idx}
            className="group rounded-3xl overflow-hidden border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/60 shadow-xl hover:shadow-2xl transition-all duration-300 flex flex-col"
          >
            {/* Image Banner */}
            <div className="relative h-48 w-full overflow-hidden bg-slate-100 dark:bg-slate-800">
              <img
                src={item.image}
                alt={item.title}
                className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
              />
              <div className="absolute top-3 left-3 bg-slate-950/80 backdrop-blur-md text-emerald-400 text-[10px] font-extrabold px-2.5 py-0.5 rounded-full border border-slate-800">
                {item.tag}
              </div>
            </div>

            {/* Content */}
            <div className="p-5 flex-1 flex flex-col justify-between">
              <div>
                <h3 className="font-extrabold text-slate-900 dark:text-white text-base group-hover:text-emerald-600 dark:group-hover:text-emerald-400 transition-colors">
                  {item.title}
                </h3>
                <p className="text-xs text-slate-600 dark:text-slate-400 mt-1 leading-relaxed">
                  {item.subtitle}
                </p>
              </div>

              {/* Voice Prompt Pill */}
              <div className="mt-4 p-2.5 rounded-xl bg-slate-50 dark:bg-slate-950/80 border border-slate-200 dark:border-slate-800/80">
                <div className="flex items-center gap-1.5 text-[10px] uppercase font-bold text-slate-500 dark:text-slate-400 mb-1">
                  <Volume2 className="w-3 h-3 text-emerald-500" />
                  Voice Instruction
                </div>
                <div className="text-xs font-mono text-emerald-700 dark:text-emerald-400 italic">
                  {item.voiceExample}
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* 3 Step Visual Flow */}
      <div className="mt-16 p-8 rounded-3xl bg-gradient-to-br from-slate-50 to-emerald-50/30 dark:from-slate-900/80 dark:to-emerald-950/20 border border-slate-200 dark:border-slate-800 shadow-xl">
        <h3 className="text-center font-extrabold text-slate-900 dark:text-white text-lg sm:text-xl mb-8">
          The PLACEWISE Engine in 3 Simple Steps
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 text-center">
          <div className="p-5 rounded-2xl bg-white dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800 shadow-sm">
            <div className="w-10 h-10 rounded-xl bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 font-bold mx-auto flex items-center justify-center text-sm mb-3 border border-emerald-500/20">
              1
            </div>
            <h4 className="font-bold text-slate-900 dark:text-white text-sm mb-1">
              Upload 1 Room Photo
            </h4>
            <p className="text-xs text-slate-600 dark:text-slate-400">
              YOLOv8 + SAM segment furniture items and generate spatial bounding footprints.
            </p>
          </div>

          <div className="p-5 rounded-2xl bg-white dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800 shadow-sm">
            <div className="w-10 h-10 rounded-xl bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 font-bold mx-auto flex items-center justify-center text-sm mb-3 border border-emerald-500/20">
              2
            </div>
            <h4 className="font-bold text-slate-900 dark:text-white text-sm mb-1">
              Speak in Tanglish
            </h4>
            <p className="text-xs text-slate-600 dark:text-slate-400">
              Gnani Prisma transcribes regional audio, resolved into KEEP and REMOVE actions.
            </p>
          </div>

          <div className="p-5 rounded-2xl bg-white dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800 shadow-sm">
            <div className="w-10 h-10 rounded-xl bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 font-bold mx-auto flex items-center justify-center text-sm mb-3 border border-emerald-500/20">
              3
            </div>
            <h4 className="font-bold text-slate-900 dark:text-white text-sm mb-1">
              Dual Visual Outputs
            </h4>
            <p className="text-xs text-slate-600 dark:text-slate-400">
              Receive both an annotated spatial plan with arrows and a clean inpainted photo preview.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

