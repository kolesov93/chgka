import assert from 'node:assert/strict';
import test from 'node:test';

import {
  approvedParticipantOptions,
  participantCount,
  participantGroups,
} from './participants.js';

const players = [
  { role: 'admin', name: 'Ведущий' },
  {
    role: 'player',
    group_id: 'group-1',
    online: true,
    pending: false,
    participants: [
      { id: 'p1', name: 'Иван' },
      { id: 'p2', name: 'Мария' },
      { id: 'p3', name: 'Алексей' },
    ],
  },
  {
    role: 'player',
    group_id: 'group-2',
    online: false,
    pending: false,
    participants: [{ id: 'p4', name: 'Иван' }],
  },
  {
    role: 'player',
    group_id: 'group-3',
    online: true,
    pending: true,
    participants: [{ id: 'p5', name: 'Ожидающий' }],
  },
];

test('participant counts distinguish people, groups and pending admission', () => {
  const groups = participantGroups(players);
  assert.equal(groups.length, 3);
  assert.equal(participantCount(groups), 5);
  assert.equal(participantCount(groups, { pending: false }), 4);
});

test('respondent options include approved offline people and disambiguate duplicate names', () => {
  assert.deepEqual(approvedParticipantOptions(players), [
    { value: 'p1', label: 'Иван · подключение 1', online: true },
    { value: 'p2', label: 'Мария', online: true },
    { value: 'p3', label: 'Алексей', online: true },
    { value: 'p4', label: 'Иван · подключение 2', online: false },
  ]);
});
