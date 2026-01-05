
import React, { useEffect, useRef } from 'react';
import * as THREE from 'three';
import { ISLProductionSequence } from '../types';

interface SignAvatarProps {
  sequence: ISLProductionSequence | null;
  speed: number;
  onComplete?: () => void;
}

const SignAvatar: React.FC<SignAvatarProps> = ({ sequence, speed, onComplete }) => {
  const mountRef = useRef<HTMLDivElement>(null);
  const bonesRef = useRef<{ [key: string]: THREE.Bone }>({});
  const requestRef = useRef<number>(0);

  useEffect(() => {
    if (!mountRef.current) return;

    const width = mountRef.current.clientWidth;
    const height = mountRef.current.clientHeight;

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000);
    camera.position.set(0, 1.4, 2.5);
    camera.lookAt(0, 1.4, 0);

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(width, height);
    renderer.setPixelRatio(window.devicePixelRatio);
    mountRef.current.appendChild(renderer.domElement);

    const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
    scene.add(ambientLight);
    const spotLight = new THREE.SpotLight(0x10b981, 1.5);
    spotLight.position.set(5, 5, 5);
    scene.add(spotLight);

    // Create a procedural humanoid skeleton for ISL
    const bones: { [key: string]: THREE.Bone } = {};
    const createBone = (name: string, pos: [number, number, number]) => {
      const bone = new THREE.Bone();
      bone.name = name;
      bone.position.set(...pos);
      bones[name] = bone;
      return bone;
    };

    const root = createBone('root', [0, 0, 0]);
    const spine = createBone('spine', [0, 0.6, 0]);
    const neck = createBone('neck', [0, 0.5, 0]);
    const head = createBone('head', [0, 0.2, 0]);
    
    const shoulderL = createBone('shoulderL', [0.2, 0.45, 0]);
    const armL = createBone('armL', [0.2, 0, 0]);
    const forearmL = createBone('forearmL', [0.3, 0, 0]);
    const handL = createBone('handL', [0.2, 0, 0]);

    const shoulderR = createBone('shoulderR', [-0.2, 0.45, 0]);
    const armR = createBone('armR', [-0.2, 0, 0]);
    const forearmR = createBone('forearmR', [-0.3, 0, 0]);
    const handR = createBone('handR', [-0.2, 0, 0]);

    root.add(spine);
    spine.add(neck);
    neck.add(head);
    spine.add(shoulderL);
    shoulderL.add(armL);
    armL.add(forearmL);
    forearmL.add(handL);
    spine.add(shoulderR);
    shoulderR.add(armR);
    armR.add(forearmR);
    forearmR.add(handR);

    bonesRef.current = bones;

    // Visualizing the skeleton with a futuristic neon look
    const skeletonHelper = new THREE.SkeletonHelper(root);
    // @ts-ignore
    skeletonHelper.material.linewidth = 3;
    scene.add(skeletonHelper);

    const animate = () => {
      requestRef.current = requestAnimationFrame(animate);
      renderer.render(scene, camera);
      
      // Gentle idle breathing
      const time = Date.now() * 0.001;
      spine.rotation.z = Math.sin(time * 0.5) * 0.02;
      head.rotation.y = Math.sin(time * 0.8) * 0.05;
    };
    animate();

    return () => {
      cancelAnimationFrame(requestRef.current);
      mountRef.current?.removeChild(renderer.domElement);
    };
  }, []);

  // Animation controller for sequence
  useEffect(() => {
    if (!sequence) return;

    let isCancelled = false;
    const runSequence = async () => {
      for (const step of sequence.isl_sequence) {
        if (isCancelled) break;
        
        const startTime = Date.now();
        const duration = step.duration_ms / speed;

        const animateStep = () => {
          const now = Date.now();
          const t = Math.min((now - startTime) / duration, 1);
          const ease = t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t;

          // Procedural ISL Mappings based on dataset descriptions
          if (step.handshape.includes('PALM')) {
            bonesRef.current.forearmL.rotation.z = ease * 1.5;
            bonesRef.current.handL.rotation.y = ease * 1.2;
          } else if (step.handshape.includes('BOOK')) {
            bonesRef.current.forearmL.rotation.z = ease * 1.0;
            bonesRef.current.forearmR.rotation.z = -ease * 1.0;
            bonesRef.current.handL.rotation.y = ease * 0.8;
            bonesRef.current.handR.rotation.y = -ease * 0.8;
          } else if (step.handshape.includes('POINT')) {
            bonesRef.current.forearmR.rotation.z = -ease * 1.4;
            bonesRef.current.handR.rotation.x = ease * 1.0;
          }

          if (t < 1 && !isCancelled) requestAnimationFrame(animateStep);
        };

        animateStep();
        await new Promise(r => setTimeout(r, duration + 100));
        
        // Reset bones smoothly for next sign
        // Explicitly type 'b' as THREE.Bone to avoid TS unknown inference error
        Object.values(bonesRef.current).forEach((b: THREE.Bone) => b.rotation.set(0, 0, 0));
      }
      onComplete?.();
    };

    runSequence();
    return () => { isCancelled = true; };
  }, [sequence, speed]);

  return <div ref={mountRef} className="w-full h-full" />;
};

export default SignAvatar;
