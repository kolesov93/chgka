export const BLACKBOX_IMAGE_SOURCE = '/images/blackbox.png';
export const BLACKBOX_SOUND_SOURCE = '/sounds/yashik.mp3';
// ffprobe reports 31.488313 seconds for the committed static track.
export const BLACKBOX_DURATION_MS = 31_488;


export function blackboxPlayback(blackbox) {
  if (
    !blackbox
    || !Number.isFinite(blackbox.started_at_ms)
    || !Number.isFinite(blackbox.server_now_ms)
    || !Number.isInteger(blackbox.playback_generation)
    || blackbox.playback_generation < 0
  ) {
    return null;
  }

  return {
    type: 'audio',
    media_id: 'blackbox',
    playback_state: 'playing',
    position_ms: 0,
    started_at_ms: blackbox.started_at_ms,
    server_now_ms: blackbox.server_now_ms,
    playback_generation: blackbox.playback_generation,
  };
}


export function blackboxEndedPayload(playbackPayload) {
  if (
    !playbackPayload
    || !Number.isInteger(playbackPayload.playback_generation)
    || playbackPayload.playback_generation < 0
  ) {
    return null;
  }
  return { playback_generation: playbackPayload.playback_generation };
}


export function blackboxRemainingMs(blackbox, localNowMs = Date.now()) {
  if (
    !blackbox
    || !Number.isFinite(blackbox.started_at_ms)
    || !Number.isFinite(blackbox.server_now_ms)
    || !Number.isFinite(blackbox.received_at_ms)
    || !Number.isFinite(localNowMs)
  ) {
    return null;
  }

  const elapsedBeforeSnapshot = Math.max(
    0,
    blackbox.server_now_ms - blackbox.started_at_ms,
  );
  const elapsedAfterSnapshot = Math.max(0, localNowMs - blackbox.received_at_ms);
  return Math.max(0, BLACKBOX_DURATION_MS - elapsedBeforeSnapshot - elapsedAfterSnapshot);
}


export function formatBlackboxRemaining(remainingMs) {
  if (typeof remainingMs !== 'number' || !Number.isFinite(remainingMs)) return '—:—';
  const totalSeconds = Math.max(0, Math.ceil(remainingMs / 1000));
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = String(totalSeconds % 60).padStart(2, '0');
  return `${minutes}:${seconds}`;
}
