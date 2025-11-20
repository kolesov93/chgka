import { useEffect, useRef } from 'react';

const SOUNDS = {
  volchok: '/sounds/volchok.mp3',
  gong: '/sounds/sig1.mp3',
  intro: '/sounds/meeting.mp3',
};

export function useGameSound(gameState) {
  const volchokRef = useRef(new Audio(SOUNDS.volchok));
  const fadeIntervalRef = useRef(null);
  const startFadeTimeoutRef = useRef(null);
  
  // Настройка волчка
  useEffect(() => {
    volchokRef.current.loop = true;
  }, []);

  const clearTimers = () => {
    if (fadeIntervalRef.current) clearInterval(fadeIntervalRef.current);
    if (startFadeTimeoutRef.current) clearTimeout(startFadeTimeoutRef.current);
    fadeIntervalRef.current = null;
    startFadeTimeoutRef.current = null;
  };

  // Функция запуска затухания
  const startFadeOut = (durationMs) => {
    const audio = volchokRef.current;
    const stepTime = 50; // каждые 50мс
    const steps = durationMs / stepTime;
    const volStep = 1.0 / steps;

    fadeIntervalRef.current = setInterval(() => {
      const newVolume = audio.volume - volStep;
      if (newVolume > 0.01) {
        audio.volume = newVolume;
      } else {
        // Финиш
        audio.volume = 0;
        audio.pause();
        clearInterval(fadeIntervalRef.current);
      }
    }, stepTime);
  };

  // Реакция на вращение
  useEffect(() => {
    const audio = volchokRef.current;

    if (gameState?.is_spinning) {
      // --- СТАРТ ---
      clearTimers();
      
      // Сброс параметров аудио
      audio.volume = 1.0;
      audio.currentTime = 0;
      
      // Запускаем воспроизведение
      audio.play().catch(e => console.log("Audio play failed:", e));

      // Планируем затухание
      const totalDuration = gameState.spin_duration || 0; // в секундах
      const fadeDuration = totalDuration / 2; // затухание в половину времени вращения

      if (totalDuration > fadeDuration) {
        // Ждем (Все время - 2 сек), потом начинаем гасить
        const waitTimeMs = (totalDuration - fadeDuration) * 1000;
        
        startFadeTimeoutRef.current = setTimeout(() => {
            startFadeOut(fadeDuration * 1000);
        }, waitTimeMs);
      } else {
        // Если вращение слишком короткое (меньше 2с), гасим сразу
        startFadeOut(totalDuration * 1000);
      }

    } else {
      // --- СТОП (Экстренный или штатный) ---
      // Если по какой-то причине таймеры еще работают или звук играет
      clearTimers();
      audio.pause();
      audio.volume = 1.0; // Сбрасываем громкость для следующего раза
    }
    
    return () => clearTimers();
  }, [gameState?.is_spinning, gameState?.spin_duration]); // Перезапускаем только при старте/стопе

  // Функция для проигрывания разовых звуков
  const playSound = (soundName) => {
    const path = SOUNDS[soundName];
    if (path) {
      const audio = new Audio(path);
      audio.play().catch(e => console.error("Error playing sound:", e));
    }
  };

  return { playSound };
}
