import test from 'node:test';
import assert from 'node:assert/strict';

import {
  formatIntroRemaining,
  introNextStepLabel,
  introRemainingMs,
  introSlideSource,
} from './intro.js';


test('intro slide sources preserve the temporary asset naming contract', () => {
  assert.equal(introSlideSource(0), '/images/intro/00_owl.png');
  assert.equal(introSlideSource(1), '/images/intro/01.jpg');
  assert.equal(introSlideSource(12), '/images/intro/12.jpg');
  assert.equal(introSlideSource(13), '/images/intro/13.png');
  assert.equal(introSlideSource(14), null);
});


test('intro next step labels describe the exact host action', () => {
  assert.equal(introNextStepLabel(0), 'Показать автора 1');
  assert.equal(introNextStepLabel(7), 'Показать автора 8');
  assert.equal(introNextStepLabel(12), 'Показать финальный слайд');
  assert.equal(introNextStepLabel(13), 'Перейти к игре');
});


test('intro countdown combines server progress and time since receipt', () => {
  const intro = {
    started_at_ms: 1_000,
    duration_ms: 87_757,
    server_now_ms: 11_000,
    received_at_ms: 100_000,
  };

  assert.equal(introRemainingMs(intro, 100_000), 77_757);
  assert.equal(introRemainingMs(intro, 102_500), 75_257);
  assert.equal(formatIntroRemaining(75_257), '1:16');
  assert.equal(introRemainingMs(intro, 200_000), 0);
});


test('malformed intro timing does not invent a countdown', () => {
  assert.equal(introRemainingMs({ duration_ms: 1000 }, 5_000), null);
  assert.equal(formatIntroRemaining(null), '—:—');
});
