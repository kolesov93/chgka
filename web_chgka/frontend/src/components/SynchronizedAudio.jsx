import { useCallback, useEffect, useRef, useState } from 'react';

import { mediaUrl } from '../socket';
import {
  normalizedVolume,
  playbackPositionSeconds,
  shouldSeek,
} from '../mediaPlayback';


export function SynchronizedAudio({ media, volume = 1 }) {
  const audioRef = useRef(null);
  const snapshotReceivedAtRef = useRef(Date.now());
  const [playbackBlocked, setPlaybackBlocked] = useState(false);

  const synchronize = useCallback(() => {
    const audio = audioRef.current;
    if (!audio || !media) return;

    const elapsedSinceSnapshotMs = Date.now() - snapshotReceivedAtRef.current;
    const targetSeconds = playbackPositionSeconds(media, elapsedSinceSnapshotMs);
    if (shouldSeek(audio.currentTime, targetSeconds)) {
      try {
        audio.currentTime = targetSeconds;
      } catch {
        // Metadata may not be available yet; onLoadedMetadata retries the sync.
      }
    }

    if (media.playback_state === 'playing') {
      const playPromise = audio.play();
      if (playPromise) {
        playPromise
          .then(() => setPlaybackBlocked(false))
          .catch(() => setPlaybackBlocked(true));
      }
      return;
    }

    audio.pause();
    setPlaybackBlocked(false);
    if (media.playback_state === 'stopped' && audio.currentTime !== 0) {
      audio.currentTime = 0;
    }
  }, [media]);

  useEffect(() => {
    if (audioRef.current) audioRef.current.volume = normalizedVolume(volume);
  }, [volume]);

  useEffect(() => {
    snapshotReceivedAtRef.current = Date.now();
    synchronize();
  }, [synchronize]);

  const unlockPlayback = () => {
    if (media?.playback_state === 'playing') synchronize();
  };

  return (
    <div className="flex flex-col items-center gap-3">
      <audio
        key={media.media_id}
        ref={audioRef}
        src={mediaUrl(media.media_id)}
        preload="auto"
        onLoadedMetadata={synchronize}
      />
      {playbackBlocked && (
        <button
          type="button"
          onClick={unlockPlayback}
          className="bg-yellow-500 hover:bg-yellow-400 text-black px-4 py-2 rounded font-bold text-xs uppercase tracking-wider"
        >
          Разрешить воспроизведение
        </button>
      )}
    </div>
  );
}
