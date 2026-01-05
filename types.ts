
export interface ISLSignInstruction {
  sign_id: string;
  duration_ms: number;
  handshape: string;
  expression: string;
  intensity?: number;
}

export interface ISLProductionSequence {
  spoken_text: string;
  isl_sequence: ISLSignInstruction[];
  rendering_prompt: string;
}

export interface VideoState {
  isGenerating: boolean;
  videoUrl: string | null;
  progress: string;
  error: string | null;
}

export enum AppMode {
  LIVE_AVATAR = 'LIVE_AVATAR',
  VIDEO_RENDER = 'VIDEO_RENDER'
}

export interface AppState {
  isListening: boolean;
  isProcessing: boolean;
  transcript: string;
  currentSequence: ISLProductionSequence | null;
  video: VideoState;
  mode: AppMode;
  playbackSpeed: number;
  confidence: number;
  history: { transcript: string; videoUrl?: string; sequence: ISLProductionSequence; timestamp: number }[];
}
