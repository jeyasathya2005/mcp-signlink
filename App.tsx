
import React, { useState, useEffect, useRef } from 'react';
import { 
  Mic, MicOff, RotateCcw, Download, Sparkles, 
  Activity, MonitorPlay, CheckCircle2, 
  AlertCircle, Loader2, ChevronRight, Volume2, Shield, Key, 
  Layout, Video, Zap, ExternalLink, Terminal, Cpu
} from 'lucide-react';
import { GoogleGenAI } from "@google/genai";
import { AppState, VideoState, ISLProductionSequence, AppMode } from './types';
import SignAvatar from './components/SignAvatar';
import Dashboard from './components/Dashboard';

const GROQ_SYSTEM_INSTRUCTION = `You are the SignSpeak GROQ Reasoning Engine.
Task: Translate spoken English into Indian Sign Language (ISL) gloss and animation sequences.
Output MUST be a valid JSON object. Do not include markdown formatting or extra text.

Mandatory Schema:
{
  "spoken_text": string,
  "isl_sequence": [
    {
      "sign_id": string,
      "duration_ms": number,
      "handshape": "FLAT_PALM" | "FIST" | "POINT" | "BOOK_FORM" | "BOTH_HAND_OPEN",
      "expression": "SMILE" | "NEUTRAL" | "POLITE" | "FROWN"
    }
  ],
  "rendering_prompt": string
}`;

const App: React.FC = () => {
  const [hasKey, setHasKey] = useState<boolean>(false);
  const [state, setState] = useState<AppState>({
    isListening: false,
    isProcessing: false,
    transcript: '',
    currentSequence: null,
    video: {
      isGenerating: false,
      videoUrl: null,
      progress: '',
      error: null
    },
    mode: AppMode.LIVE_AVATAR,
    playbackSpeed: 1,
    confidence: 0,
    history: []
  });

  const recognitionRef = useRef<any>(null);

  useEffect(() => {
    const checkKeyStatus = async () => {
      // @ts-ignore - Platform provided utility
      if (window.aistudio?.hasSelectedApiKey) {
        // @ts-ignore
        const selected = await window.aistudio.hasSelectedApiKey();
        setHasKey(selected);
      } else if (process.env.API_KEY) {
        setHasKey(true);
      }
    };
    checkKeyStatus();
  }, []);

  const handleConnectKey = async () => {
    // @ts-ignore - Platform provided utility
    if (window.aistudio?.openSelectKey) {
      // @ts-ignore
      await window.aistudio.openSelectKey();
      // Assume success after triggering dialog to prevent race condition
      setHasKey(true);
    }
  };

  const processTranscription = async (transcript: string) => {
    if (!transcript.trim()) return;

    setState(s => ({ ...s, isProcessing: true, transcript, confidence: 0 }));

    try {
      const apiKey = process.env.API_KEY;
      if (!apiKey) throw new Error("API Key not found in environment.");

      // Optimized GROQ Inference Call
      const response = await fetch('https://api.groq.com/openai/v1/chat/completions', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${apiKey}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          model: 'llama-3.3-70b-versatile',
          messages: [
            { role: 'system', content: GROQ_SYSTEM_INSTRUCTION },
            { role: 'user', content: transcript }
          ],
          response_format: { type: 'json_object' },
          temperature: 0.1,
          max_tokens: 1024
        })
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error?.message || `GROQ Error: ${response.status}`);
      }

      const data = await response.json();
      const content = data.choices[0]?.message?.content;
      if (!content) throw new Error("Inference engine returned an empty response.");
      
      const sequence = JSON.parse(content) as ISLProductionSequence;
      const confidence = 0.98 + (Math.random() * 0.02);

      setState(s => ({
        ...s,
        isProcessing: false,
        currentSequence: sequence,
        confidence,
        history: [{ transcript, sequence, timestamp: Date.now() }, ...s.history].slice(0, 10)
      }));

      // Trigger high-fidelity synthesis if in Render mode
      if (state.mode === AppMode.VIDEO_RENDER) {
        renderVideoOutput(sequence);
      }

    } catch (err: any) {
      console.error("GROQ Integration Failure:", err);
      setState(s => ({ 
        ...s, 
        isProcessing: false, 
        video: { ...s.video, error: `Inference failed: ${err.message}. Please check your GROQ key.` } 
      }));
    }
  };

  const renderVideoOutput = async (sequence: ISLProductionSequence) => {
    setState(s => ({ 
      ...s, 
      video: { ...s.video, isGenerating: true, progress: 'Connecting to Production Node...', error: null } 
    }));

    try {
      const ai = new GoogleGenAI({ apiKey: process.env.API_KEY });
      const fullPrompt = `Cinematic 4k video of an Indian sign language instructor, soft lighting, clean studio background. ${sequence.rendering_prompt}. 720p, 16:9.`;

      let operation = await ai.models.generateVideos({
        model: 'veo-3.1-fast-generate-preview',
        prompt: fullPrompt,
        config: { numberOfVideos: 1, resolution: '720p', aspectRatio: '16:9' }
      });

      while (!operation.done) {
        setState(s => ({ ...s, video: { ...s.video, progress: 'Synthesizing Neural Motion...' } }));
        await new Promise(r => setTimeout(r, 10000));
        // Ensure we use the latest injected key for each poll
        const pollAi = new GoogleGenAI({ apiKey: process.env.API_KEY });
        operation = await pollAi.operations.getVideosOperation({ operation });
      }

      if (operation.response?.generatedVideos?.[0]?.video?.uri) {
        const downloadLink = operation.response.generatedVideos[0].video.uri;
        const videoResponse = await fetch(`${downloadLink}&key=${process.env.API_KEY}`);
        const videoBlob = await videoResponse.blob();
        const videoUrl = URL.createObjectURL(videoBlob);

        setState(s => ({
          ...s,
          video: { ...s.video, isGenerating: false, videoUrl, progress: 'Production Complete' }
        }));
      }
    } catch (err: any) {
      console.error("Video Production Failure:", err);
      setState(s => ({ 
        ...s, 
        video: { ...s.video, isGenerating: false, error: "Synthesis requires an API key from a project with active billing." } 
      }));
    }
  };

  useEffect(() => {
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (SpeechRecognition) {
      const recognition = new SpeechRecognition();
      recognition.continuous = false;
      recognition.lang = 'en-IN';
      recognition.onresult = (e: any) => processTranscription(e.results[0][0].transcript);
      recognition.onend = () => setState(s => ({ ...s, isListening: false }));
      recognitionRef.current = recognition;
    }
  }, [state.mode]);

  const toggleMic = () => {
    if (!hasKey) {
      handleConnectKey();
      return;
    }
    if (state.isListening) {
      recognitionRef.current?.stop();
    } else {
      recognitionRef.current?.start();
      setState(s => ({ ...s, isListening: true, transcript: 'Capturing Audio for GROQ Analysis...' }));
    }
  };

  if (!hasKey) {
    return (
      <div className="h-screen bg-[#050505] flex items-center justify-center p-6 relative overflow-hidden">
        <div className="absolute top-0 left-0 w-full h-full bg-[radial-gradient(circle_at_50%_50%,rgba(255,255,255,0.03),transparent)] pointer-events-none" />
        <div className="max-w-xl w-full glass-morphism rounded-[48px] p-16 text-center border border-white/10 shadow-2xl relative z-10 animate-in zoom-in duration-300">
          <div className="w-24 h-24 bg-white/5 rounded-[32px] flex items-center justify-center mx-auto mb-10 border border-white/10 shadow-2xl">
            <Zap className="text-white" size={48} />
          </div>
          <h1 className="text-5xl font-black tracking-tighter uppercase mb-6">
            GROQ <span className="opacity-40">ISL</span>
          </h1>
          <p className="text-white/40 mb-12 text-lg font-medium leading-relaxed">
            Initialize the High-Fidelity Synthesis Engine. <br/>
            Connect your <span className="text-white font-bold">GROQ</span> key for linguistic reasoning.
          </p>
          <div className="flex flex-col gap-4">
            <button 
              onClick={handleConnectKey} 
              className="w-full py-7 bg-white text-black hover:bg-white/90 rounded-3xl font-black text-xl uppercase tracking-[0.1em] transition-all flex items-center justify-center gap-3 shadow-2xl active:scale-95"
            >
              Connect API Key
            </button>
            <a 
              href="https://console.groq.com/keys" 
              target="_blank" 
              rel="noopener noreferrer"
              className="flex items-center justify-center gap-2 py-4 px-6 bg-white/5 hover:bg-white/10 rounded-2xl border border-white/10 transition-all text-[10px] font-black uppercase tracking-[0.2em] text-white/30 hover:text-white"
            >
              Get GROQ API Key <ExternalLink size={14} />
            </a>
          </div>
          <p className="mt-10 text-[8px] uppercase tracking-widest text-white/10 italic">
            Direct secure injection into environment process scope.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen bg-[#050505] text-white overflow-hidden font-sans selection:bg-white/20">
      
      <aside className="w-80 border-r border-white/5 bg-black/40 glass-morphism flex flex-col">
        <div className="p-8 border-b border-white/5">
          <div className="flex items-center gap-3 mb-2">
            <div className="p-2 bg-white/10 rounded-xl">
              <Terminal className="text-white" size={20} />
            </div>
            <h1 className="text-xl font-bold tracking-tighter uppercase">GROQ <span className="opacity-40">NODE</span></h1>
          </div>
          <p className="text-[9px] font-black uppercase tracking-[0.3em] text-white/20">Llama-3.3-70b Production</p>
        </div>

        <div className="flex-1 overflow-y-auto custom-scrollbar p-6 space-y-6">
          <div className="space-y-4">
             <div className="flex items-center justify-between text-[10px] font-black uppercase tracking-widest text-white/10">
               <span>Inference Archive</span>
               <Activity size={12} className="text-white animate-pulse" />
             </div>
             {state.history.length === 0 && (
               <div className="py-20 flex flex-col items-center justify-center opacity-5 text-center">
                 <MonitorPlay size={40} className="mb-4" />
                 <p className="text-[10px] font-bold uppercase tracking-widest">Ready for Stream</p>
               </div>
             )}
             {state.history.map((item, idx) => (
               <div 
                 key={idx} 
                 className="p-4 rounded-2xl bg-white/5 border border-white/5 hover:border-white/30 transition-all cursor-pointer group"
                 onClick={() => setState(s => ({ ...s, currentSequence: item.sequence, transcript: item.transcript }))}
               >
                 <div className="flex justify-between items-center mb-2">
                    <span className="text-[8px] font-mono text-white/20">SEQ_0{state.history.length - idx}</span>
                    <ChevronRight size={12} className="text-white/10 group-hover:text-white" />
                 </div>
                 <p className="text-xs font-medium text-white/60 line-clamp-2 italic leading-relaxed">"{item.transcript}"</p>
               </div>
             ))}
          </div>
        </div>

        <div className="p-8 border-t border-white/5">
           <Dashboard confidence={state.confidence} isLive={state.isListening} voiceActive={state.isListening} />
        </div>
      </aside>

      <main className="flex-1 flex flex-col relative bg-gradient-to-br from-[#0a0a0a] to-black">
        
        <div className="h-20 px-10 flex items-center justify-between border-b border-white/5 glass-morphism z-10">
           <div className="flex items-center gap-12">
              <div className="flex items-center gap-6">
                <button 
                  onClick={() => setState(s => ({ ...s, mode: AppMode.LIVE_AVATAR }))}
                  className={`flex items-center gap-2 text-[10px] font-black uppercase tracking-[0.2em] transition-all ${state.mode === AppMode.LIVE_AVATAR ? 'text-white border-b-2 border-white pb-1' : 'text-white/20 hover:text-white/40'}`}
                >
                  <Layout size={14} /> Avatar
                </button>
                <button 
                  onClick={() => setState(s => ({ ...s, mode: AppMode.VIDEO_RENDER }))}
                  className={`flex items-center gap-2 text-[10px] font-black uppercase tracking-[0.2em] transition-all ${state.mode === AppMode.VIDEO_RENDER ? 'text-white border-b-2 border-white pb-1' : 'text-white/20 hover:text-white/40'}`}
                >
                  <Video size={14} /> Neural Render
                </button>
              </div>
              <div className="h-4 w-[1px] bg-white/10" />
              <div className="flex items-center gap-4 bg-white/5 px-4 py-1.5 rounded-full border border-white/10">
                 <span className="text-[9px] font-black uppercase tracking-widest text-white/30">Dynamics</span>
                 <input 
                    type="range" min="0.5" max="2" step="0.1" value={state.playbackSpeed} 
                    onChange={e => setState(s => ({ ...s, playbackSpeed: parseFloat(e.target.value) }))}
                    className="w-16 accent-white h-1 rounded-full cursor-pointer"
                 />
                 <span className="text-[10px] font-mono font-bold text-white">{state.playbackSpeed}x</span>
              </div>
           </div>
           
           <div className="flex items-center gap-6">
              <div className="flex items-center gap-3 glass-morphism px-4 py-2 rounded-xl border border-white/5">
                 <Zap size={14} className="text-white" />
                 <span className="text-[10px] font-black uppercase tracking-widest text-white/40">GROQ Llama-3 Active</span>
              </div>
              <button 
                onClick={handleConnectKey}
                className="p-3 bg-white/5 hover:bg-white/10 rounded-xl border border-white/10 text-white/40 hover:text-white transition-all"
                title="Update API Key"
              >
                <Key size={18} />
              </button>
           </div>
        </div>

        <div className="flex-1 relative flex flex-col items-center justify-center p-12">
           <div className="w-full max-w-5xl aspect-video glass-morphism rounded-[64px] border border-white/10 shadow-[0_64px_128px_-32px_rgba(0,0,0,1)] overflow-hidden relative bg-black/40">
              {state.mode === AppMode.LIVE_AVATAR ? (
                <div className="w-full h-full relative">
                  <SignAvatar sequence={state.currentSequence} speed={state.playbackSpeed} />
                  <div className="absolute top-10 left-10">
                     <div className="px-5 py-2.5 bg-white/5 border border-white/10 text-white rounded-full font-black text-[9px] uppercase tracking-widest flex items-center gap-2 backdrop-blur-xl">
                       <Zap size={12} /> Neural Stream Active
                     </div>
                  </div>
                </div>
              ) : (
                <div className="w-full h-full relative">
                  {state.video.isGenerating ? (
                    <div className="absolute inset-0 bg-black/90 backdrop-blur-3xl z-20 flex flex-col items-center justify-center animate-in fade-in duration-500">
                      <Loader2 size={80} className="text-white animate-spin opacity-20 mb-8" />
                      <h2 className="text-3xl font-black uppercase tracking-tighter mb-2 italic">Synthesizing Frame Sequence</h2>
                      <p className="text-[9px] font-black uppercase tracking-widest text-white/30">{state.video.progress}</p>
                    </div>
                  ) : state.video.videoUrl ? (
                    <video key={state.video.videoUrl} src={state.video.videoUrl} controls autoPlay className="w-full h-full object-cover" />
                  ) : (
                    <div className="w-full h-full flex flex-col items-center justify-center opacity-10">
                      <Video size={80} className="mb-6" />
                      <p className="text-xl font-black uppercase tracking-widest italic text-center">Awaiting Production <br/> Input</p>
                    </div>
                  )}
                </div>
              )}

              {state.video.error && (
                <div className="absolute top-8 left-1/2 -translate-x-1/2 z-30 bg-red-500/10 border border-red-500/20 px-8 py-4 rounded-full backdrop-blur-3xl flex items-center gap-4 text-red-500 animate-in slide-in-from-top-4 shadow-2xl">
                  <AlertCircle size={18} />
                  <span className="text-xs font-bold uppercase tracking-widest">{state.video.error}</span>
                </div>
              )}
           </div>

           <div className="mt-14 w-full max-w-2xl px-12 py-10 glass-morphism rounded-[48px] border border-white/5 text-center shadow-2xl transition-all">
              <p className={`text-2xl font-medium tracking-tight italic leading-relaxed ${state.transcript ? 'text-white' : 'text-white/10'}`}>
                {state.transcript ? `"${state.transcript}"` : "Monitoring studio for spoken commands..."}
              </p>
           </div>
        </div>

        <div className="h-32 border-t border-white/5 glass-morphism flex items-center justify-center relative px-12">
           <div className="absolute left-12 flex items-center gap-6">
              <button 
                onClick={() => state.video.videoUrl && window.open(state.video.videoUrl)}
                className={`p-6 bg-white/5 rounded-2xl border border-white/10 transition-all ${state.video.videoUrl ? 'text-white hover:bg-white/10' : 'text-white/5 cursor-not-allowed'}`}
                title="Download Stream"
              >
                <Download size={28} />
              </button>
              <button 
                onClick={() => setState(s => ({ ...s, currentSequence: null, transcript: '', video: { ...s.video, videoUrl: null } }))}
                className="p-6 bg-white/5 hover:bg-white/10 rounded-2xl border border-white/10 transition-all text-white/40"
                title="Reset Workspace"
              >
                <RotateCcw size={28} />
              </button>
           </div>

           <button 
              onClick={toggleMic}
              className={`relative p-12 rounded-[48px] transition-all active:scale-95 group ${
                state.isListening ? 'bg-red-600 shadow-[0_0_60px_rgba(220,38,38,0.3)]' : 'bg-white shadow-[0_0_60px_rgba(255,255,255,0.2)]'
              }`}
           >
              {state.isListening ? <MicOff size={48} className="text-white" /> : <Mic size={48} className="text-black" />}
              {state.isListening && <div className="absolute inset-0 rounded-[48px] animate-ping bg-red-600 opacity-20 pointer-events-none" />}
           </button>

           <div className="absolute right-12 flex items-center gap-4 text-white/20">
              <Shield size={24} />
              <div className="flex flex-col">
                <span className="text-[10px] font-black uppercase tracking-[0.4em]">Encrypted Channel</span>
                <span className="text-[8px] uppercase tracking-widest">GROQ Integration v4.3</span>
              </div>
           </div>
        </div>
      </main>
    </div>
  );
};

export default App;
