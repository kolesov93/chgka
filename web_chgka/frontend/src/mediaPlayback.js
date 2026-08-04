export function playbackPositionSeconds(media, elapsedSinceSnapshotMs = 0) {
  if (!media) return 0;

  if (
    media.playback_state === 'playing'
    && Number.isFinite(media.started_at_ms)
    && Number.isFinite(media.server_now_ms)
  ) {
    const elapsedMs = Number.isFinite(elapsedSinceSnapshotMs)
      ? Math.max(0, elapsedSinceSnapshotMs)
      : 0;
    return Math.max(
      0,
      (media.server_now_ms - media.started_at_ms + elapsedMs) / 1000,
    );
  }

  return Math.max(0, Number(media.position_ms || 0) / 1000);
}

export function shouldSeek(currentSeconds, targetSeconds, toleranceSeconds = 0.35) {
  if (!Number.isFinite(currentSeconds) || !Number.isFinite(targetSeconds)) return false;
  return Math.abs(currentSeconds - targetSeconds) > toleranceSeconds;
}

export function normalizedVolume(volume) {
  const numeric = Number(volume);
  if (!Number.isFinite(numeric)) return 1;
  return Math.max(0, Math.min(1, numeric));
}
