import assert from 'node:assert/strict';
import test from 'node:test';

import { soundFadeMultiplier } from './soundFade.js';


function fading(overrides = {}) {
  return {
    generation: 1,
    mode: 'fading',
    fade_started_at_ms: 1_000,
    fade_duration_ms: 3_000,
    fade_from: 1,
    server_now_ms: 1_000,
    received_at_ms: 10_000,
    ...overrides,
  };
}

test('normal and stopped modes have stable multipliers', () => {
  assert.equal(soundFadeMultiplier({ mode: 'normal' }, 20_000), 1);
  assert.equal(soundFadeMultiplier({ mode: 'stopped' }, 20_000), 0);
  assert.equal(soundFadeMultiplier(null, 20_000), 1);
});

test('fade combines server progress with local time since receipt', () => {
  assert.equal(soundFadeMultiplier(fading(), 10_000), 1);
  assert.equal(soundFadeMultiplier(fading(), 11_500), 0.001 ** 0.5);
  assert.equal(soundFadeMultiplier(fading(), 12_500), 0.001 ** (5 / 6));
  assert.equal(soundFadeMultiplier(fading(), 13_000), 0);
});

test('reconnect snapshot resumes from server progress', () => {
  const snapshot = fading({
    server_now_ms: 2_500,
    received_at_ms: 20_000,
  });

  assert.equal(soundFadeMultiplier(snapshot, 20_000), 0.001 ** 0.5);
  assert.equal(soundFadeMultiplier(snapshot, 20_750), 0.001 ** 0.75);
});

test('repeated fade honors its reduced starting level', () => {
  const snapshot = fading({
    fade_started_at_ms: 2_500,
    fade_from: 0.001 ** 0.5,
    server_now_ms: 2_500,
  });

  assert.equal(soundFadeMultiplier(snapshot, 10_000), 0.001 ** 0.5);
  assert.ok(Math.abs(soundFadeMultiplier(snapshot, 11_500) - 0.001) < 1e-12);
});

test('malformed active fade fails closed at zero volume', () => {
  assert.equal(soundFadeMultiplier(fading({ fade_duration_ms: 0 }), 10_000), 0);
  assert.equal(soundFadeMultiplier(fading({ server_now_ms: null }), 10_000), 0);
});
