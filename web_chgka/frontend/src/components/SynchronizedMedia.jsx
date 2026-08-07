import { useCallback, useEffect, useRef, useState } from 'react';

import { mediaUrl } from '../socket';
import {
  normalizedVolume,
  playbackEndedPayload,
  playbackPositionSeconds,
  shouldSeek,
} from '../mediaPlayback';


export function SynchronizedMedia({ media, volume = 1, onEnded }) {
  const elementRef = useRef(null);
  const snapshotReceivedAtRef = useRef(Date.now());
  const [playbackBlocked, setPlaybackBlocked] = useState(false);

  const synchronize = useCallback(() => {
    const element = elementRef.current;
    if (!element || !media) return;

    const elapsedSinceSnapshotMs = Date.now() - snapshotReceivedAtRef.current;
    const targetSeconds = playbackPositionSeconds(media, elapsedSinceSnapshotMs);
    if (shouldSeek(element.currentTime, targetSeconds)) {
      try {
        element.currentTime = targetSeconds;
      } catch {
        // Metadata may not be available yet; onLoadedMetadata retries the sync.
      }
    }

    if (media.playback_state === 'playing') {
      const playPromise = element.play();
      if (playPromise) {
        playPromise
          .then(() => setPlaybackBlocked(false))
          .catch(() => setPlaybackBlocked(true));
      }
      return;
    }

    element.pause();
    setPlaybackBlocked(false);
    if (media.playback_state === 'stopped' && element.currentTime !== 0) {
      element.currentTime = 0;
    }
  }, [media]);

  useEffect(() => {
    if (elementRef.current) elementRef.current.volume = normalizedVolume(volume);
  }, [volume]);

  useEffect(() => {
    snapshotReceivedAtRef.current = Date.now();
    synchronize();
  }, [synchronize]);

  const unlockPlayback = () => {
    if (media?.playback_state === 'playing') synchronize();
  };

  const reportEnded = () => {
    const payload = playbackEndedPayload(media);
    if (payload && onEnded) onEnded(payload);
  };

  const commonProps = {
    ref: elementRef,
    src: mediaUrl(media.media_id),
    preload: 'auto',
    onLoadedMetadata: synchronize,
    onEnded: reportEnded,
  };

  return (
    <div className="flex w-full flex-col items-center gap-3">
      {media.type === 'video' ? (
        <video
          key={media.media_id}
          {...commonProps}
          playsInline
          className="max-h-[520px] w-full rounded bg-black object-contain"
        />
      ) : (
        <audio key={media.media_id} {...commonProps} />
      )}
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
