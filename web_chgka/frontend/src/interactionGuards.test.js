import assert from 'node:assert/strict';
import { readdirSync, readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import test from 'node:test';

import { requiresAnswerMediaConfirmation } from './interactionGuards.js';

function runtimeSourceFiles(directory) {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const path = `${directory}/${entry.name}`;
    if (entry.isDirectory()) return runtimeSourceFiles(path);
    if (!/\.(?:js|jsx)$/.test(entry.name) || entry.name.endsWith('.test.js')) return [];
    return [path];
  });
}

test('answer media needs an application confirmation only before the answer phase', () => {
  const answerMedia = { section: 'answer' };

  assert.equal(requiresAnswerMediaConfirmation(answerMedia, 'QUESTION_READING'), true);
  assert.equal(requiresAnswerMediaConfirmation(answerMedia, 'DISCUSSION'), true);
  assert.equal(requiresAnswerMediaConfirmation(answerMedia, 'TEAM_ANSWER'), false);
  assert.equal(requiresAnswerMediaConfirmation({ section: 'question' }, 'QUESTION_READING'), false);
  assert.equal(requiresAnswerMediaConfirmation(null, 'QUESTION_READING'), false);
});

test('frontend runtime does not call browser-native dialogs', () => {
  const sourceDirectory = fileURLToPath(new URL('.', import.meta.url));
  const forbiddenCall = new RegExp('\\b(?:con' + 'firm|al' + 'ert|pro' + 'mpt)\\s*\\(');
  const violations = runtimeSourceFiles(sourceDirectory).flatMap((path) => {
    const source = readFileSync(path, 'utf8');
    return forbiddenCall.test(source) ? [path] : [];
  });

  assert.deepEqual(violations, []);
});
