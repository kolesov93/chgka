import { useEffect, useRef, useState } from 'react';
import { currentAppPath } from '../appPaths';

const SOUNDS = {
  volchok: currentAppPath('sounds/volchok.mp3'),
  gong1: currentAppPath('sounds/gong1.mp3'),
  gong2: currentAppPath('sounds/gong2.mp3'),
  gong3: currentAppPath('sounds/gong3.mp3'),
  sig1: currentAppPath('sounds/sig1.mp3'),
  sig2: currentAppPath('sounds/sig2.mp3'),
  sig3: currentAppPath('sounds/sig3.mp3'),
  intro: currentAppPath('sounds/meeting.mp3'),
  yes1: currentAppPath('sounds/yes1.mp3'),
  yes2: currentAppPath('sounds/yes2.mp3'),
  no1: currentAppPath('sounds/no1.mp3'),
  no2: currentAppPath('sounds/no2.mp3'),
  sector13: currentAppPath('sounds/sector13.mp3'),
  final: currentAppPath('sounds/final.mp3'),
};

export function useGameSound(gameState, globalVolume = 1.0, soundFadeMultiplier = 1.0) {
  const volchokRef = useRef(new Audio(SOUNDS.volchok));
  const fadeIntervalRef = useRef(null);
  const startFadeTimeoutRef = useRef(null);
  const fadeLevelRef = useRef(1.0); 
  
  const activeEffectsRef = useRef(new Set());
  
  // Вместо локального стейта используем ref для актуального значения
  const masterVolumeRef = useRef(globalVolume);
  const soundFadeLevelRef = useRef(soundFadeMultiplier);

  useEffect(() => {
      masterVolumeRef.current = globalVolume;
      soundFadeLevelRef.current = soundFadeMultiplier;
      
      activeEffectsRef.current.forEach(audio => {
          if (!audio.paused) applyVolume(audio, false);
      });

      if (!volchokRef.current.paused) {
          const isFading = !!fadeIntervalRef.current;
          applyVolume(volchokRef.current, isFading);
      }
  }, [globalVolume, soundFadeMultiplier]);

  // Применяем громкость к конкретному аудио с учетом его типа
  const applyVolume = (audio, isFadeActive = false) => {
      const wheelFadeLevel = isFadeActive ? fadeLevelRef.current : 1.0;
      const effectiveVolume = (
        wheelFadeLevel
        * soundFadeLevelRef.current
        * masterVolumeRef.current
      );
      audio.volume = Math.max(0, Math.min(1, effectiveVolume));
  };

  // 1. Реакция на изменение Master Volume (удаляем старый эффект)
  // useEffect(() => { ... }, [masterVolume]) - УДАЛЕНО

  useEffect(() => {
    volchokRef.current.loop = true;
  }, []);

  const clearTimers = () => {
    if (fadeIntervalRef.current) clearInterval(fadeIntervalRef.current);
    if (startFadeTimeoutRef.current) clearTimeout(startFadeTimeoutRef.current);
    fadeIntervalRef.current = null;
    startFadeTimeoutRef.current = null;
  };

  const stopEffectsOnly = () => {
    activeEffectsRef.current.forEach(audio => {
      audio.pause();
      audio.currentTime = 0;
    });
    activeEffectsRef.current.clear();
  };

  const startFadeOut = (durationMs) => {
    const audio = volchokRef.current;
    const stepTime = 50; 
    const steps = durationMs / stepTime;
    
    fadeLevelRef.current = 1.0; 
    const fadeStep = 1.0 / steps;

    fadeIntervalRef.current = setInterval(() => {
      fadeLevelRef.current -= fadeStep;
      
      if (fadeLevelRef.current > 0.01) {
        // Пересчитываем громкость с учетом Master Volume
        applyVolume(audio, true);
      } else {
        // Конец
        fadeLevelRef.current = 0;
        audio.volume = 0;
        audio.pause();
        clearInterval(fadeIntervalRef.current);
        fadeIntervalRef.current = null;
      }
    }, stepTime);
  };

  useEffect(() => {
    const audio = volchokRef.current;

    if (gameState?.is_spinning) {
      // When the wheel starts spinning, stop any previously playing effects
      // (win/lose/sig sounds) so they don't overlap with the volchok loop.
      stopEffectsOnly();
      clearTimers();
      fadeLevelRef.current = 1.0;
      applyVolume(audio, true);
      audio.currentTime = 0;
      audio.play().catch(e => console.log("Audio play failed:", e));

      const totalDuration = gameState.spin_duration || 0;
      const fadeDuration = totalDuration / 2;

      if (totalDuration > fadeDuration) {
        const waitTimeMs = (totalDuration - fadeDuration) * 1000;
        startFadeTimeoutRef.current = setTimeout(() => {
            startFadeOut(fadeDuration * 1000);
        }, waitTimeMs);
      } else {
        startFadeOut(totalDuration * 1000);
      }

    } else {
      clearTimers();
      audio.pause();
    }
    
    return () => clearTimers();
  }, [gameState?.is_spinning, gameState?.spin_duration]);

  const playSound = (soundName) => {
    const path = SOUNDS[soundName];

    if (path) {
      const audio = new Audio(path);
      applyVolume(audio, false); // Сразу Master volume
      
      activeEffectsRef.current.add(audio);
      audio.onended = () => {
          activeEffectsRef.current.delete(audio);
      };

      audio.play().catch(e => console.error("Error playing sound:", e));
    }
  };

  const stopAllSounds = () => {
      clearTimers();
      volchokRef.current.pause();
      volchokRef.current.currentTime = 0;
      fadeLevelRef.current = 1.0;
      
      activeEffectsRef.current.forEach(audio => {
          audio.pause();
          audio.currentTime = 0;
      });
      activeEffectsRef.current.clear();
  };

  return { 
      playSound, 
      stopAllSounds
  };
}
