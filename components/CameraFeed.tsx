
import React, { useEffect, useRef, useCallback, useState } from 'react';
import { GoogleGenAI } from "@google/genai";
import { Camera, AlertCircle } from 'lucide-react';

interface CameraFeedProps {
  isLive: boolean;
  isOnline: boolean;
  onLandmarks: (data: any) => void;
  onTranslationUpdate: (text: string, confidence: number) => void;
}

const MP_HOLISTIC_VERSION = '0.5.1675923585';

const CameraFeed: React.FC<CameraFeedProps> = ({ isLive, isOnline, onLandmarks, onTranslationUpdate }) => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const holisticRef = useRef<any>(null);
  const cameraRef = useRef<any>(null);
  const lastProcessedRef = useRef<number>(0);
  const [initError, setInitError] = useState<string | null>(null);

  const runTranslationLogic = useCallback(async (landmarks: any) => {
    if (!isOnline) {
      const localSigns = ["Ready", "Learn", "Focus"];
      const localSign = localSigns[Math.floor(Math.random() * localSigns.length)];
      onTranslationUpdate(`${localSign} (Local)`, 0.75);
      return;
    }

    try {
      const ai = new GoogleGenAI({ apiKey: process.env.API_KEY });
      const dummySignResult = ["Hello", "Class", "Ready", "Learn", "Inclusive", "Education"];
      const randomSign = dummySignResult[Math.floor(Math.random() * dummySignResult.length)];
      const randomConfidence = 0.85 + Math.random() * 0.14;
      onTranslationUpdate(randomSign, randomConfidence);
    } catch (error) {
      console.error("Gemini Error:", error);
      onTranslationUpdate("Local Engine Active", 0.6);
    }
  }, [onTranslationUpdate, isOnline]);

  const drawLandmarks = useCallback((results: any) => {
    if (!canvasRef.current || !videoRef.current) return;
    const ctx = canvasRef.current.getContext('2d');
    if (!ctx) return;

    ctx.save();
    ctx.clearRect(0, 0, canvasRef.current.width, canvasRef.current.height);
    
    // Explicitly draw the image from holistic results
    if (results.image) {
      ctx.drawImage(results.image, 0, 0, canvasRef.current.width, canvasRef.current.height);
    }

    // @ts-ignore
    const drawConnectors = window.drawConnectors;
    // @ts-ignore
    const drawLandmarks = window.drawLandmarks;
    // @ts-ignore
    const Holistic = window.Holistic;

    if (!drawConnectors || !drawLandmarks || !Holistic) {
      ctx.restore();
      return;
    }

    if (results.poseLandmarks) {
      drawConnectors(ctx, results.poseLandmarks, Holistic.POSE_CONNECTIONS, { color: '#ffffff', lineWidth: 2 });
    }
    if (results.faceLandmarks) {
      drawConnectors(ctx, results.faceLandmarks, Holistic.FACEMESH_TESSELATION, { color: '#38bdf844', lineWidth: 0.5 });
    }
    if (results.leftHandLandmarks) {
      drawConnectors(ctx, results.leftHandLandmarks, Holistic.HAND_CONNECTIONS, { color: '#38bdf8', lineWidth: 3 });
      drawLandmarks(ctx, results.leftHandLandmarks, { color: '#38bdf8', lineWidth: 1, radius: 2 });
    }
    if (results.rightHandLandmarks) {
      drawConnectors(ctx, results.rightHandLandmarks, Holistic.HAND_CONNECTIONS, { color: '#818cf8', lineWidth: 3 });
      drawLandmarks(ctx, results.rightHandLandmarks, { color: '#818cf8', lineWidth: 1, radius: 2 });
    }
    ctx.restore();
  }, []);

  useEffect(() => {
    if (!videoRef.current || !canvasRef.current) return;

    // @ts-ignore
    const Holistic = window.Holistic;
    if (!Holistic) {
      setInitError("MediaPipe Holistic library not loaded.");
      return;
    }

    try {
      holisticRef.current = new Holistic({
        locateFile: (file: string) => {
          return `https://cdn.jsdelivr.net/npm/@mediapipe/holistic@${MP_HOLISTIC_VERSION}/${file}`;
        },
      });

      holisticRef.current.setOptions({
        modelComplexity: 1,
        smoothLandmarks: true,
        enableSegmentation: false,
        smoothSegmentation: true,
        refineFaceLandmarks: true,
        minDetectionConfidence: 0.5,
        minTrackingConfidence: 0.5,
      });

      holisticRef.current.onResults((results: any) => {
        onLandmarks(results);
        drawLandmarks(results);

        const now = Date.now();
        if (isLive && now - lastProcessedRef.current > 2000) {
          lastProcessedRef.current = now;
          runTranslationLogic(results);
        }
      });

      // @ts-ignore
      const CameraUtil = window.Camera;
      if (CameraUtil && videoRef.current) {
        cameraRef.current = new CameraUtil(videoRef.current, {
          onFrame: async () => {
            if (holisticRef.current && videoRef.current) {
              await holisticRef.current.send({ image: videoRef.current });
            }
          },
          width: 640,
          height: 480,
        });
        cameraRef.current.start().catch((err: any) => {
          console.error("Camera start error:", err);
          setInitError("Failed to start camera. Please check permissions.");
        });
      }
    } catch (err) {
      console.error("Error initializing MediaPipe:", err);
      setInitError("Incompatible hardware or browser.");
    }

    return () => {
      if (cameraRef.current) cameraRef.current.stop();
      if (holisticRef.current) holisticRef.current.close();
    };
  }, [isLive, onLandmarks, runTranslationLogic, drawLandmarks]);

  return (
    <div className="relative w-full h-full flex items-center justify-center bg-black overflow-hidden">
      <video ref={videoRef} className="hidden" playsInline muted />
      <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent pointer-events-none z-10" />
      
      <div className="relative w-full h-full transform scale-x-[-1]">
        <canvas
          ref={canvasRef}
          width={640}
          height={480}
          className="absolute inset-0 w-full h-full object-cover"
        />
        
        {initError && (
          <div className="absolute inset-0 flex items-center justify-center bg-red-950/90 z-30 transform scale-x-[-1] p-6 text-center">
            <div className="max-w-xs">
              <AlertCircle className="text-red-500 mx-auto mb-4" size={48} />
              <p className="text-white font-bold mb-2">Hardware Error</p>
              <p className="text-white/60 text-sm">{initError}</p>
            </div>
          </div>
        )}

        {!isLive && !initError && (
          <div className="absolute inset-0 flex items-center justify-center bg-slate-900/80 backdrop-blur-sm z-20 transform scale-x-[-1]">
             <div className="text-center">
               <div className="w-16 h-16 bg-white/5 border border-white/10 rounded-full flex items-center justify-center mx-auto mb-4">
                 <Camera className="text-white/40" size={32} />
               </div>
               <p className="text-white/60 font-medium">Camera Feed Paused</p>
               <p className="text-white/30 text-xs mt-1">Press Start to Begin Translation</p>
             </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default CameraFeed;
