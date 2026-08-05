import test from 'node:test';
import assert from 'node:assert/strict';

import {
  formatIntroRemaining,
  INTRO_FALLBACK_AUTHOR_SOURCE,
  introAuthorCaption,
  introNextStepLabel,
  introRemainingMs,
  introSlideLabel,
  introSlideSource,
} from './intro.js';


test('intro slide sources keep only the static boundary assets', () => {
  assert.equal(introSlideSource(0), '/images/intro/00_owl.png');
  assert.equal(introSlideSource(1), null);
  assert.equal(introSlideSource(12), null);
  assert.equal(introSlideSource(13), '/images/intro/13.png');
  assert.equal(introSlideSource(14), null);
  assert.equal(INTRO_FALLBACK_AUTHOR_SOURCE, '/images/intro/author-fallback.png');
});


test('intro next step labels describe the exact host action', () => {
  assert.equal(introSlideLabel(4), 'Авторы сектора 4 из 12');
  assert.equal(introNextStepLabel(0), 'Показать авторов сектора 1');
  assert.equal(introNextStepLabel(7), 'Показать авторов сектора 8');
  assert.equal(introNextStepLabel(12), 'Показать финальный слайд');
  assert.equal(introNextStepLabel(13), 'Перейти к игре');
});


test('author caption adds optional city in parentheses', () => {
  assert.equal(introAuthorCaption({ name: 'Анна', city: 'Казань' }), 'Анна (Казань)');
  assert.equal(introAuthorCaption({ name: 'Анна', city: null }), 'Анна');
  assert.equal(introAuthorCaption(null), null);
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
  assert.equal(introRemainingMs({
    started_at_ms: null,
    duration_ms: 87_757,
    server_now_ms: 10_000,
    received_at_ms: 20_000,
  }, 20_000), null);
  assert.equal(formatIntroRemaining(null), '—:—');
});
