
import React, { useEffect, useState } from 'react';
import { ShieldCheck, Zap, Mic, Sparkles } from 'lucide-react';

interface DashboardProps {
  confidence: number;
  isLive: boolean;
  voiceActive?: boolean;
}

const Dashboard: React.FC<DashboardProps> = ({ confidence, isLive, voiceActive }) => {
  const [voiceLevel, setVoiceLevel] = useState(0);
  const roundedConfidence = Math.round(confidence * 100);

  useEffect(() => {
    if (!voiceActive || !isLive) {
      setVoiceLevel(0);
      return;
    }
    const interval = setInterval(() => {
      setVoiceLevel(Math.random() * 80 + 20);
    }, 120);
    return () => clearInterval(interval);
  }, [voiceActive, isLive]);

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-2">
         <div className="flex justify-between items-end mb-1">
            <span className="text-[10px] font-black text-white/30 uppercase tracking-widest">Synthesis Accuracy</span>
            <span className={`text-lg font-black ${roundedConfidence > 90 ? 'text-emerald-400' : 'text-amber-400'}`}>
              {isLive ? `${roundedConfidence}%` : '0%'}
            </span>
         </div>
         <div className="h-1.5 w-full bg-white/5 rounded-full overflow-hidden p-[2px]">
            <div 
              className={`h-full transition-all duration-700 rounded-full shadow-[0_0_10px_rgba(52,211,153,0.3)] ${roundedConfidence > 90 ? 'bg-emerald-500' : 'bg-amber-500'}`}
              style={{ width: isLive ? `${roundedConfidence}%` : '0%' }}
            />
         </div>
      </div>

      <div className={`p-5 rounded-3xl border transition-all duration-500 ${voiceActive ? 'bg-emerald-500/5 border-emerald-500/20' : 'bg-white/5 border-white/5 opacity-30'}`}>
        <div className="flex items-center justify-between mb-4">
           <div className="flex items-center gap-2 text-emerald-400">
             <Mic size={16} />
             <span className="text-[10px] font-black uppercase tracking-widest">Voice Feed</span>
           </div>
        </div>
        <div className="flex items-end gap-[3px] h-8">
          {[...Array(16)].map((_, i) => (
            <div 
              key={i} 
              className={`flex-1 rounded-full transition-all duration-100 ${voiceActive ? 'bg-emerald-400/60' : 'bg-white/10'}`}
              style={{ height: voiceActive ? `${Math.max(10, voiceLevel * (1 - Math.abs(i-8)/8))}%` : '10%' }}
            />
          ))}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
         <div className="p-4 rounded-2xl bg-white/5 border border-white/5">
            <div className="flex items-center gap-2 text-emerald-400 mb-2 opacity-50">
               <ShieldCheck size={14} />
               <span className="text-[9px] font-black uppercase tracking-widest">Uptime</span>
            </div>
            <p className="text-xl font-black italic">100%</p>
         </div>
         <div className="p-4 rounded-2xl bg-white/5 border border-white/5">
            <div className="flex items-center gap-2 text-sky-400 mb-2 opacity-50">
               <Zap size={14} />
               <span className="text-[9px] font-black uppercase tracking-widest">Process</span>
            </div>
            <p className="text-xl font-black italic">22ms</p>
         </div>
      </div>
    </div>
  );
};

export default Dashboard;
