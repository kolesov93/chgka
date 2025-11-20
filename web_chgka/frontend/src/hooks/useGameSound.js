import { useEffect, useRef } from 'react';

const SOUNDS = {
  volchok: '/sounds/volchok.mp3',
  gong: '/sounds/sig1.mp3',
  intro: '/sounds/meeting.mp3',
  // Добавим остальные по мере надобности
};

export function useGameSound(gameState) {
  const volchokRef = useRef(new Audio(SOUNDS.volchok));
  
  // Настройка волчка (зацикливание)
  useEffect(() => {
    volchokRef.current.loop = true;
  }, []);

  // Реакция на вращение
  useEffect(() => {
    if (gameState?.is_spinning) {
      volchokRef.current.currentTime = 0;
      volchokRef.current.play().catch(e => console.log("Audio play failed:", e));
    } else {
      // Плавное затухание было бы круто, но пока просто стоп
      volchokRef.current.pause();
    }
  }, [gameState?.is_spinning]);

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

