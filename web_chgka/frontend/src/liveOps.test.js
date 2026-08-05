import test from 'node:test';
import assert from 'node:assert/strict';

import {
  LIVE_OPS_PHASES,
  buildOpenRoundPayload,
  parseBoundedInteger,
} from './liveOps.js';


test('bounded integer parsing rejects partial, boolean-like, and out-of-range input', () => {
  assert.equal(parseBoundedInteger('6', 0, 6), 6);
  assert.equal(parseBoundedInteger(' 2 ', 0, 6), 2);
  assert.equal(parseBoundedInteger('2.5', 0, 6), null);
  assert.equal(parseBoundedInteger('2x', 0, 6), null);
  assert.equal(parseBoundedInteger('', 0, 6), null);
  assert.equal(parseBoundedInteger('7', 0, 6), null);
});


test('normal round payload contains only the selected sector', () => {
  const questionTypes = Array(13).fill('normal');

  assert.deepEqual(
    buildOpenRoundPayload({ sector: '3', questionTypes, partNumber: '2' }),
    { sector: 3 },
  );
});


test('blitz round payload converts the displayed part to a zero-based index', () => {
  const questionTypes = Array(13).fill('normal');
  questionTypes[3] = 'blitz';

  assert.deepEqual(
    buildOpenRoundPayload({ sector: 4, questionTypes, partNumber: 2 }),
    { sector: 4, part_index: 1 },
  );
  assert.equal(
    buildOpenRoundPayload({ sector: 4, questionTypes, partNumber: 4 }),
    null,
  );
});


test('forceable phase list excludes LOGIN', () => {
  assert.deepEqual(LIVE_OPS_PHASES, [
    'PRE_ROUND',
    'QUESTION_READING',
    'DISCUSSION',
    'TEAM_ANSWER',
    'POST_ROUND',
  ]);
});
