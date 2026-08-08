import test from 'node:test';
import assert from 'node:assert/strict';

import {
  BLACKBOX_IMAGE_SOURCE,
  BLACKBOX_SOUND_SOURCE,
  blackboxEndedPayload,
  blackboxPlayback,
} from './blackbox.js';


test('blackbox uses the static image and music assets', () => {
  assert.equal(BLACKBOX_IMAGE_SOURCE, '/images/blackbox.png');
  assert.equal(BLACKBOX_SOUND_SOURCE, '/sounds/yashik.mp3');
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
