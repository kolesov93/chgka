import assert from 'node:assert/strict';
import test from 'node:test';

import {
  mediaSectionLabel,
  mediaTypeLabel,
  phaseLabel,
  playbackStateLabel,
  questionKindLabel,
  responseMessage,
} from './uiText.js';

test('game phases have Russian display labels and a safe fallback', () => {
  assert.equal(phaseLabel('PRE_ROUND'), 'Ожидание вращения');
  assert.equal(phaseLabel('QUESTION_READING'), 'Чтение вопроса');
  assert.equal(phaseLabel('UNKNOWN_PHASE'), 'Неизвестная фаза');
});

test('question kinds and media metadata have Russian display labels', () => {
  assert.equal(questionKindLabel('superblitz'), 'суперблиц');
  assert.equal(questionKindLabel('unknown'), 'неизвестный тип вопроса');
  assert.equal(mediaSectionLabel('answer'), 'ответ');
  assert.equal(mediaSectionLabel('unknown'), 'неизвестная секция');
  assert.equal(mediaTypeLabel('image'), 'изображение');
  assert.equal(mediaTypeLabel('unknown'), 'медиа');
  assert.equal(playbackStateLabel('playing'), 'Воспроизводится');
  assert.equal(playbackStateLabel('unknown'), 'Состояние неизвестно');
});

test('server response uses a Russian fallback instead of exposing an error code', () => {
  assert.equal(responseMessage({ message: 'Попробуйте ещё раз' }), 'Попробуйте ещё раз');
  assert.equal(
    responseMessage({ error: 'media_not_current' }, 'Не удалось открыть медиа'),
    'Не удалось открыть медиа',
  );
});
