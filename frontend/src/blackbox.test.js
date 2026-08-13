import test from 'node:test';
import assert from 'node:assert/strict';

import {
  BLACKBOX_DURATION_MS,
  BLACKBOX_IMAGE_SOURCE,
  BLACKBOX_SOUND_SOURCE,
  blackboxEndedPayload,
  blackboxPlayback,
  blackboxRemainingMs,
  formatBlackboxRemaining,
} from './blackbox.js';


test('blackbox uses the static image and music assets', () => {
  assert.equal(BLACKBOX_IMAGE_SOURCE, '/images/blackbox.png');
  assert.equal(BLACKBOX_SOUND_SOURCE, '/sounds/yashik.mp3');
  assert.equal(BLACKBOX_DURATION_MS, 31_488);
});


test('blackbox snapshot becomes reconnect-aware synchronized playback', () => {
  assert.deepEqual(
    blackboxPlayback({
      started_at_ms: 10_000,
      server_now_ms: 13_750,
      playback_generation: 4,
    }),
    {
      type: 'audio',
      media_id: 'blackbox',
      playback_state: 'playing',
      position_ms: 0,
      started_at_ms: 10_000,
      server_now_ms: 13_750,
      playback_generation: 4,
    },
  );
  assert.equal(blackboxPlayback(null), null);
  assert.equal(blackboxPlayback({ started_at_ms: 10_000 }), null);
});


test('natural completion reports only the guarded playback generation', () => {
  assert.deepEqual(
    blackboxEndedPayload({ media_id: 'blackbox', playback_generation: 4 }),
    { playback_generation: 4 },
  );
  assert.equal(blackboxEndedPayload({ playback_generation: -1 }), null);
  assert.equal(blackboxEndedPayload(null), null);
});


test('blackbox countdown combines server progress and time since receipt', () => {
  const blackbox = {
    started_at_ms: 10_000,
    server_now_ms: 13_750,
    received_at_ms: 100_000,
  };

  assert.equal(blackboxRemainingMs(blackbox, 102_500), 25_238);
  assert.equal(formatBlackboxRemaining(blackboxRemainingMs(blackbox, 102_500)), '0:26');
  assert.equal(blackboxRemainingMs(blackbox, 200_000), 0);
  assert.equal(formatBlackboxRemaining(0), '0:00');
});


test('malformed blackbox timing does not invent a countdown', () => {
  assert.equal(blackboxRemainingMs({ started_at_ms: 10_000 }, 12_000), null);
  assert.equal(formatBlackboxRemaining(null), '—:—');
});
