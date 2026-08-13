import assert from 'node:assert/strict';
import test from 'node:test';

import {
  canScheduleRepayment,
  canTakeCreditMinute,
  canUseEarnedMinute,
  captainEarlySeconds,
  creditRecoveryValue,
  timerHasElapsed,
  timerRemainingSeconds,
  timerSegmentLabel,
  timerServerNow,
} from './gameMinutes.js';

function timer(overrides = {}) {
  return {
    segment: 'base',
    started_at_ms: 10_000,
    discussion_deadline_ms: 70_000,
    server_now_ms: 12_000,
    received_at_ms: 1_000,
    generation: 3,
    ...overrides,
  };
}

function gameState(overrides = {}) {
  return {
    phase: 'DISCUSSION',
    score: { znatoki: 2, tv: 5 },
    timer: timer(),
    team: {
      earned_minutes: 2,
      credit: { used: false, debt: false, repayment_scheduled: false, forced: false },
    },
    round: { kind: 'normal', sector: 2 },
    ...overrides,
  };
}

test('timer timeline compensates time elapsed since state receipt', () => {
  const value = timer();
  assert.equal(timerServerNow(value, 4_000), 15_000);
  assert.equal(timerRemainingSeconds(value, 4_000), 55);
  assert.equal(timerHasElapsed(value, 4_000), false);

  assert.equal(
    timerHasElapsed(timer({ discussion_deadline_ms: 15_000 }), 4_000),
    true,
  );
});

test('captain early answer countdown is limited to the first five seconds', () => {
  assert.equal(captainEarlySeconds(timer(), 1_000), 3);
  assert.equal(captainEarlySeconds(timer(), 3_999), 1);
  assert.equal(captainEarlySeconds(timer(), 4_000), 0);
  assert.equal(captainEarlySeconds(timer({ segment: 'earned' }), 1_000), 0);
});

test('earned and credit actions require an elapsed base or earned segment', () => {
  const elapsedTimer = timer({ discussion_deadline_ms: 15_000 });
  const state = gameState({ timer: elapsedTimer });
  assert.equal(canUseEarnedMinute(state, 4_000), true);
  assert.equal(canTakeCreditMinute(state, 4_000), true);

  assert.equal(canUseEarnedMinute(gameState(), 4_000), false);
  assert.equal(canTakeCreditMinute(gameState({ score: { znatoki: 2, tv: 4 }, timer: elapsedTimer }), 4_000), false);
  assert.equal(canTakeCreditMinute(gameState({
    timer: elapsedTimer,
    team: { ...state.team, credit: { ...state.team.credit, used: true } },
  }), 4_000), false);
});

test('blitz earned minutes stay locked to the initially selected part', () => {
  const elapsedTimer = timer({ discussion_deadline_ms: 15_000, segment: 'earned' });
  assert.equal(canUseEarnedMinute(gameState({
    timer: elapsedTimer,
    round: { kind: 'blitz', part_index: 1, extra_part_index: 1 },
  }), 4_000), true);
  assert.equal(canUseEarnedMinute(gameState({
    timer: elapsedTimer,
    round: { kind: 'blitz', part_index: 2, extra_part_index: 1 },
  }), 4_000), false);
});

test('repayment scheduling and display values follow credit state', () => {
  const debt = { used: true, debt: true, repayment_scheduled: false, forced: false };
  assert.equal(canScheduleRepayment(gameState({
    phase: 'PRE_ROUND',
    team: { earned_minutes: 0, credit: debt },
  })), true);
  assert.equal(canScheduleRepayment(gameState({
    phase: 'POST_ROUND',
    team: { earned_minutes: 0, credit: debt },
    round: { kind: 'blitz', advance_next_part: true },
  })), false);
  assert.equal(creditRecoveryValue(debt), 'debt');
  assert.equal(creditRecoveryValue({ ...debt, repayment_scheduled: true }), 'scheduled');
  assert.equal(creditRecoveryValue({ ...debt, debt: false }), 'used');
  assert.equal(creditRecoveryValue(null), 'available');
  assert.equal(timerSegmentLabel('credit'), 'Минута в кредит');
});
