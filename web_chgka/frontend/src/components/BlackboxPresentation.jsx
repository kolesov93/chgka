import { useEffect, useMemo, useState } from 'react';

import {
  BLACKBOX_IMAGE_SOURCE,
  BLACKBOX_SOUND_SOURCE,
  blackboxEndedPayload,
  blackboxPlayback,
  blackboxRemainingMs,
  formatBlackboxRemaining,
} from '../blackbox';
import { SynchronizedMedia } from './SynchronizedMedia';


export function BlackboxAudio({ blackbox, volume, onEnded }) {
  const playback = useMemo(
    () => blackboxPlayback(blackbox),
    [
      blackbox?.started_at_ms,
      blackbox?.server_now_ms,
      blackbox?.playback_generation,
    ],
  );
  if (!playback) return null;

  const reportEnded = (payload) => {
    const completion = blackboxEndedPayload(payload);
    if (completion && onEnded) onEnded(completion);
  };

  return (
    <SynchronizedMedia
      media={playback}
      source={BLACKBOX_SOUND_SOURCE}
      volume={volume}
      onEnded={reportEnded}
    />
  );
}


export function BlackboxScreen() {
  return (
    <div className="flex min-h-[420px] w-full items-center justify-center rounded-xl border border-slate-700 bg-slate-800/40 p-6">
      <img
        src={BLACKBOX_IMAGE_SOURCE}
        alt="Чёрный ящик"
        className="max-h-[520px] max-w-full object-contain"
      />
    </div>
  );
}


export function BlackboxCountdown({ blackbox }) {
  const [nowMs, setNowMs] = useState(() => Date.now());

  useEffect(() => {
    if (!blackbox) return undefined;
    setNowMs(Date.now());
    const interval = setInterval(() => setNowMs(Date.now()), 250);
    return () => clearInterval(interval);
  }, [blackbox?.started_at_ms, blackbox?.playback_generation]);

  return (
    <span className="font-black tabular-nums text-yellow-400">
      {formatBlackboxRemaining(blackboxRemainingMs(blackbox, nowMs))}
    </span>
  );
}
