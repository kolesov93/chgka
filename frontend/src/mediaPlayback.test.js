import test from 'node:test';
import assert from 'node:assert/strict';

import {
  normalizedVolume,
  playbackEndedPayload,
  playbackPositionSeconds,
  shouldSeek,
} from './mediaPlayback.js';


test('stopped and paused media use the stored position', () => {
  assert.equal(playbackPositionSeconds({ playback_state: 'stopped', position_ms: 0 }), 0);
  assert.equal(playbackPositionSeconds({ playback_state: 'paused', position_ms: 2_500 }), 2.5);
});


test('playing media uses server serialization time', () => {
  const media = {
    playback_state: 'playing',
    started_at_ms: 10_000,
    server_now_ms: 13_750,
    position_ms: 0,
  };

  assert.equal(playbackPositionSeconds(media), 3.75);
  assert.equal(playbackPositionSeconds(media, 2_000), 5.75);
});


test('playback position and volume are clamped', () => {
  assert.equal(
    playbackPositionSeconds({ playback_state: 'playing', started_at_ms: 5_000, server_now_ms: 4_000 }),
    0,
  );
  assert.equal(normalizedVolume(-1), 0);
  assert.equal(normalizedVolume(2), 1);
  assert.equal(normalizedVolume('invalid'), 1);
});


test('seek tolerance avoids unnecessary playback jumps', () => {
  assert.equal(shouldSeek(5, 5.2), false);
  assert.equal(shouldSeek(5, 5.5), true);
});


test('ended payload identifies only a valid playing generation', () => {
  assert.deepEqual(
    playbackEndedPayload({
      media_id: 'video-token',
      playback_state: 'playing',
      playback_generation: 4,
    }),
    { media_id: 'video-token', playback_generation: 4 },
  );
  assert.equal(
    playbackEndedPayload({
      media_id: 'video-token',
      playback_state: 'paused',
      playback_generation: 4,
    }),
    null,
  );
  assert.equal(
    playbackEndedPayload({
      media_id: 'video-token',
      playback_state: 'playing',
    }),
    null,
  );
});
