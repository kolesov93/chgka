import test from 'node:test';
import assert from 'node:assert/strict';

import {
  formatJournalTimestamp,
  gameModeLabel,
  gameScoreLabel,
  gameStatusLabel,
  questionHistoryLabel,
} from './gameHistory.js';

test('journal labels are Russian and have safe fallbacks', () => {
  assert.equal(gameModeLabel('regular'), 'Обычная');
  assert.equal(gameModeLabel('debug'), 'Тестовая');
  assert.equal(gameModeLabel('other'), 'Неизвестный режим');
  assert.equal(gameStatusLabel('interrupted'), 'Прервана');
  assert.equal(gameScoreLabel({ znatoki: 6, tv: 4 }), '6:4');
  assert.equal(gameScoreLabel(null), '—');
});

test('blitz question history is labeled by its individual part', () => {
  assert.equal(
    questionHistoryLabel({ sector: 4, part_index: 1, title: 'Второй вопрос' }),
    'Сектор 4, часть 2/3 — Второй вопрос',
  );
  assert.equal(
    questionHistoryLabel({ sector: 3, part_index: null, title: 'Обычный вопрос' }),
    'Сектор 3 — Обычный вопрос',
  );
});

test('invalid journal timestamp uses a stable placeholder', () => {
  assert.equal(formatJournalTimestamp('not-a-date'), '—');
});
