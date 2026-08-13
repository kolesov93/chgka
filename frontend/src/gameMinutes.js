export const CAPTAIN_EARLY_WINDOW_MS = 5_000;

export function timerServerNow(timer, localNowMs = Date.now()) {
  if (!Number.isFinite(timer?.server_now_ms)) return localNowMs;
  const receivedAtMs = Number.isFinite(timer?.received_at_ms)
    ? timer.received_at_ms
    : localNowMs;
  return timer.server_now_ms + Math.max(0, localNowMs - receivedAtMs);
}

export function timerRemainingSeconds(timer, localNowMs = Date.now()) {
  if (!Number.isFinite(timer?.discussion_deadline_ms)) return null;
  const raw = (timer.discussion_deadline_ms - timerServerNow(timer, localNowMs)) / 1000;
  return raw >= 0 ? Math.ceil(raw) : Math.floor(raw);
}

export function captainEarlySeconds(timer, localNowMs = Date.now()) {
  if (timer?.segment !== 'base' || !Number.isFinite(timer?.started_at_ms)) return 0;
  const remainingMs = timer.started_at_ms
    + CAPTAIN_EARLY_WINDOW_MS
    - timerServerNow(timer, localNowMs);
  return Math.max(0, Math.min(5, Math.ceil(remainingMs / 1000)));
}

export function timerHasElapsed(timer, localNowMs = Date.now()) {
  return Number.isFinite(timer?.discussion_deadline_ms)
    && timerServerNow(timer, localNowMs) >= timer.discussion_deadline_ms;
}

export function timerSegmentLabel(segment) {
  return {
    base: 'Основная минута',
    earned: 'Дополнительная минута',
    credit: 'Минута в кредит',
  }[segment] || 'Обсуждение';
}

export function creditRecoveryValue(credit) {
  if (credit?.repayment_scheduled) return 'scheduled';
  if (credit?.debt) return 'debt';
  if (credit?.used) return 'used';
  return 'available';
}

export function canUseEarnedMinute(gameState, localNowMs = Date.now()) {
  const round = gameState?.round || {};
  if (
    gameState?.phase !== 'TEAM_ANSWER'
    || !['base', 'earned'].includes(round.answer_timer_segment)
    || (gameState?.team?.earned_minutes ?? 0) <= 0
    || round.credit_used
    || round.credit_repayment
    || round.early_answer
    || round.strategy_request
  ) return false;
  if (!['blitz', 'superblitz'].includes(round.kind)) return true;
  return round.extra_part_index === undefined || round.extra_part_index === round.part_index;
}

export function canTakeCreditMinute(gameState, localNowMs = Date.now()) {
  const score = gameState?.score || {};
  const round = gameState?.round || {};
  return gameState?.phase === 'TEAM_ANSWER'
    && ['base', 'earned'].includes(round.answer_timer_segment)
    && score.tv === 5
    && Number.isInteger(score.znatoki)
    && score.znatoki >= 0
    && score.znatoki <= 4
    && !gameState?.team?.credit?.used
    && !round.credit_repayment
    && !round.early_answer
    && !round.strategy_request;
}

export function canCaptainRequestEarlyAnswer(gameState, localNowMs = Date.now()) {
  const round = gameState?.round || {};
  if (
    round.kind !== 'normal'
    || round.credit_repayment
    || round.strategy_request
  ) return false;
  if (gameState?.phase === 'QUESTION_READING') return true;
  if (gameState?.phase !== 'DISCUSSION' || gameState?.timer?.segment !== 'base') return false;
  return captainEarlySeconds(gameState.timer, localNowMs) > 0
    && !timerHasElapsed(gameState.timer, localNowMs);
}

export function canHostDeclareEarlyAnswer(gameState, localNowMs = Date.now()) {
  const round = gameState?.round || {};
  if (
    round.kind !== 'normal'
    || round.credit_repayment
    || round.strategy_request
  ) return false;
  if (gameState?.phase === 'QUESTION_READING') return true;
  return gameState?.phase === 'DISCUSSION'
    && gameState?.timer?.segment === 'base'
    && !timerHasElapsed(gameState.timer, localNowMs);
}

export function canScheduleRepayment(gameState) {
  const phase = gameState?.phase;
  return Boolean(
    gameState?.team?.credit?.debt
    && !gameState?.team?.credit?.repayment_scheduled
    && !gameState?.team?.credit?.repayment_request
    && (phase === 'PRE_ROUND' || phase === 'POST_ROUND')
    && !gameState?.is_spinning
    && !(phase === 'POST_ROUND' && gameState?.round?.advance_next_part),
  );
}
