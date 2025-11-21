import { useEffect, useRef, useState } from 'react';

const SOUNDS = {
  volchok: '/sounds/volchok.mp3',
  gong: '/sounds/sig1.mp3',
  intro: '/sounds/meeting.mp3',
  win: ['/sounds/yes1.mp3', '/sounds/yes2.mp3'],
  lose: ['/sounds/no1.mp3', '/sounds/no2.mp3']
};

export function useGameSound(gameState) {
  const volchokRef = useRef(new Audio(SOUNDS.volchok));
  const fadeIntervalRef = useRef(null);
  const startFadeTimeoutRef = useRef(null);
  const fadeLevelRef = useRef(1.0); 
  
  const activeEffectsRef = useRef(new Set());
  
  const [masterVolume, setMasterVolumeState] = useState(1.0);
  const masterVolumeRef = useRef(1.0);

  // Применяем громкость к конкретному аудио с учетом его типа
  const applyVolume = (audio, isFadeActive = false) => {
      if (isFadeActive) {
          audio.volume = fadeLevelRef.current * masterVolumeRef.current;
      } else {
          audio.volume = masterVolumeRef.current;
      }
  };

  // 1. Реакция на изменение Master Volume
  useEffect(() => {
    masterVolumeRef.current = masterVolume;
    
    activeEffectsRef.current.forEach(audio => {
        if (!audio.paused) applyVolume(audio, false);
    });

    if (!volchokRef.current.paused) {
        const isFading = !!fadeIntervalRef.current;
        applyVolume(volchokRef.current, isFading);
    }
  }, [masterVolume]);

  useEffect(() => {
    volchokRef.current.loop = true;
  }, []);

  const clearTimers = () => {
    if (fadeIntervalRef.current) clearInterval(fadeIntervalRef.current);
    if (startFadeTimeoutRef.current) clearTimeout(startFadeTimeoutRef.current);
    fadeIntervalRef.current = null;
    startFadeTimeoutRef.current = null;
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

  const playSound = (soundNameOrCategory) => {
    let path = SOUNDS[soundNameOrCategory];
    
    if (Array.isArray(path)) {
        const randIndex = Math.floor(Math.random() * path.length);
        path = path[randIndex];
    }

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
      stopAllSounds, 
      masterVolume, 
      setMasterVolume: setMasterVolumeState 
  };
}
