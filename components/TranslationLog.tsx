
import React from 'react';
import { Mic, Quote, Sparkles } from 'lucide-react';

interface TranslationLogProps {
  currentTranslation: string;
  transcripts: {text: string, timestamp: number}[];
  showVisualizer: boolean;
}

const TranslationLog: React.FC<TranslationLogProps> = ({ currentTranslation, transcripts, showVisualizer }) => {
  return (
    <div className="h-full flex flex-col">
      {/* Current Focus is handled in the App center overlay now, but we'll show history here */}
      <div className="flex-1 overflow-y-auto custom-scrollbar space-y-3">
        {transcripts.map((item, i) => (
          <div 
            key={i} 
            className="px-6 py-5 rounded-3xl bg-white/[0.03] border border-white/5 flex flex-col gap-3 group hover:border-emerald-500/30 transition-all"
          >
            <div className="flex items-center justify-between">
              <span className="text-[9px] font-black uppercase tracking-[0.2em] flex items-center gap-2 text-emerald-400/60">
                <Mic size={12} />
                Captured Instruction
              </span>
              <span className="text-[9px] font-mono opacity-20">{new Date(item.timestamp).toLocaleTimeString()}</span>
            </div>
            <p className="text-sm font-bold leading-relaxed text-white/80 group-hover:text-white transition-colors italic">"{item.text}"</p>
          </div>
        ))}
        {transcripts.length === 0 && (
          <div className="h-full flex flex-col items-center justify-center text-white/5 text-center px-6">
            <Sparkles size={48} className="mb-6 opacity-5" />
            <p className="text-xs font-black uppercase tracking-[0.3em]">System Engine Ready</p>
            <p className="text-[10px] mt-2 font-medium">Activate microphone to begin real-time sign language synthesis.</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default TranslationLog;
