function clampLevel(value) {
  if (!Number.isFinite(value)) return 1;
  return Math.max(0, Math.min(1, value));
}

export function soundFadeMultiplier(soundControl, localNowMs = Date.now()) {
  if (!soundControl || soundControl.mode === 'normal') return 1;
  if (soundControl.mode === 'stopped') return 0;
  if (soundControl.mode !== 'fading') return 1;

  if (
    soundControl.fade_started_at_ms == null
    || soundControl.fade_duration_ms == null
    || soundControl.server_now_ms == null
    || soundControl.received_at_ms == null
  ) {
    return 0;
  }
  const startedAtMs = Number(soundControl.fade_started_at_ms);
  const durationMs = Number(soundControl.fade_duration_ms);
  const serverNowMs = Number(soundControl.server_now_ms);
  const receivedAtMs = Number(soundControl.received_at_ms);
  if (
    !Number.isFinite(startedAtMs)
    || !Number.isFinite(durationMs)
    || durationMs <= 0
    || !Number.isFinite(serverNowMs)
    || !Number.isFinite(receivedAtMs)
  ) {
    return 0;
  }

  const elapsedSinceSnapshotMs = Math.max(0, localNowMs - receivedAtMs);
  const effectiveServerNowMs = serverNowMs + elapsedSinceSnapshotMs;
  const progress = Math.max(0, Math.min(1, (effectiveServerNowMs - startedAtMs) / durationMs));
  const fadeFrom = clampLevel(Number(soundControl.fade_from));
  return clampLevel(fadeFrom * (1 - progress));
}
