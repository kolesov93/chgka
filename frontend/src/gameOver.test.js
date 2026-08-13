import test from 'node:test';
import assert from 'node:assert/strict';

import { gameOverPresentation } from './gameOver.js';


test('game over presentation names the experts winner', () => {
  assert.deepEqual(gameOverPresentation({ znatoki: 6, tv: 4 }), {
    winner: 'znatoki',
    title: 'Победа знатоков',
    detail: 'Финальный счёт 6:4',
  });
});


test('game over presentation names the viewers winner', () => {
  assert.deepEqual(gameOverPresentation({ znatoki: 2, tv: 6 }), {
    winner: 'tv',
    title: 'Победа телезрителей',
    detail: 'Финальный счёт 2:6',
  });
});


test('ambiguous recovery score asks for correction', () => {
  assert.deepEqual(gameOverPresentation({ znatoki: 6, tv: 6 }), {
    winner: null,
    title: 'Счёт требует исправления',
    detail: 'Некорректный финальный счёт 6:6',
  });
});
