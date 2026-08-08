export const BLACKBOX_IMAGE_SOURCE = '/images/blackbox.png';
export const BLACKBOX_SOUND_SOURCE = '/sounds/yashik.mp3';


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
