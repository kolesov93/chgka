import { useEffect, useRef } from 'react';
import { socket } from '../socket';

export function useSocketSoundEvents(playSound, stopAllSounds) {
  const playSoundRef = useRef(playSound);
  const stopAllSoundsRef = useRef(stopAllSounds);

  useEffect(() => {
    playSoundRef.current = playSound;
    stopAllSoundsRef.current = stopAllSounds;
  }, [playSound, stopAllSounds]);

  useEffect(() => {
    function onPlaySound(data) {
      if (data.sound) playSoundRef.current(data.sound);
      else if (data.category) playSoundRef.current(data.category);
    }

    function onStopSound() {
      stopAllSoundsRef.current();
    }

    socket.on('play_sound', onPlaySound);
    socket.on('stop_sound', onStopSound);

    return () => {
      socket.off('play_sound', onPlaySound);
      socket.off('stop_sound', onStopSound);
    };
  }, []);
}
