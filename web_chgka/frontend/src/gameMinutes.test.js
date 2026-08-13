import assert from 'node:assert/strict';
import test from 'node:test';

import {
  canScheduleRepayment,
  canCaptainRequestEarlyAnswer,
  canHostDeclareEarlyAnswer,
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

test('earned and credit actions appear after the host requests the team answer', () => {
  const state = gameState({
    phase: 'TEAM_ANSWER',
    round: { kind: 'normal', sector: 2, answer_timer_segment: 'base' },
  });
  assert.equal(canUseEarnedMinute(state), true);
  assert.equal(canTakeCreditMinute(state), true);

  assert.equal(canUseEarnedMinute(gameState()), false);
  assert.equal(canTakeCreditMinute(gameState({
    ...state,
    score: { znatoki: 2, tv: 4 },
  })), false);
  assert.equal(canTakeCreditMinute(gameState({
    ...state,
    team: { ...state.team, credit: { ...state.team.credit, used: true } },
  })), false);
  assert.equal(canUseEarnedMinute(gameState({
    ...state,
    round: { ...state.round, early_answer: true },
  })), false);
});

test('early answer is available while reading and keeps asymmetric timer access', () => {
  const reading = gameState({ phase: 'QUESTION_READING' });
  assert.equal(canCaptainRequestEarlyAnswer(reading), true);
  assert.equal(canHostDeclareEarlyAnswer(reading), true);

  assert.equal(canCaptainRequestEarlyAnswer(gameState(), 1_000), true);
  assert.equal(canCaptainRequestEarlyAnswer(gameState(), 4_000), false);
  assert.equal(canHostDeclareEarlyAnswer(gameState(), 4_000), true);
  assert.equal(canHostDeclareEarlyAnswer(gameState({
    round: { kind: 'normal', strategy_request: { type: 'early_answer' } },
  }), 1_000), false);
});

test('blitz earned minutes stay locked to the initially selected part', () => {
  assert.equal(canUseEarnedMinute(gameState({
    phase: 'TEAM_ANSWER',
    round: {
      kind: 'blitz',
      part_index: 1,
      extra_part_index: 1,
      answer_timer_segment: 'earned',
    },
  })), true);
  assert.equal(canUseEarnedMinute(gameState({
    phase: 'TEAM_ANSWER',
    round: {
      kind: 'blitz',
      part_index: 2,
      extra_part_index: 1,
      answer_timer_segment: 'earned',
    },
  })), false);
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
  assert.equal(canScheduleRepayment(gameState({
    phase: 'PRE_ROUND',
    team: {
      earned_minutes: 0,
      credit: { ...debt, repayment_request: { type: 'repayment' } },
    },
  })), false);
  assert.equal(creditRecoveryValue(debt), 'debt');
  assert.equal(creditRecoveryValue({ ...debt, repayment_scheduled: true }), 'scheduled');
  assert.equal(creditRecoveryValue({ ...debt, debt: false }), 'used');
  assert.equal(creditRecoveryValue(null), 'available');
  assert.equal(timerSegmentLabel('credit'), 'Минута в кредит');
});
