import { useEffect, useState } from 'react';

import {
  canScheduleRepayment,
  canTakeCreditMinute,
  canUseEarnedMinute,
  captainEarlySeconds,
  timerServerNow,
} from '../gameMinutes';
import { socket } from '../socket';
import { responseMessage } from '../uiText';

export function CaptainControls({ gameState, myGroupId, isConnected, addNotification }) {
  const [localNowMs, setLocalNowMs] = useState(Date.now());
  const [pendingAction, setPendingAction] = useState(null);
  const captain = gameState?.team?.captain;
  const isCaptainGroup = Boolean(myGroupId && captain?.group_id === myGroupId);
  const timer = gameState?.timer;

  useEffect(() => {
    if (!isCaptainGroup || gameState?.phase !== 'DISCUSSION') return undefined;
    setLocalNowMs(Date.now());
    const interval = setInterval(() => setLocalNowMs(Date.now()), 200);
    return () => clearInterval(interval);
  }, [gameState?.phase, isCaptainGroup, timer?.generation]);

  if (!isCaptainGroup) return null;

  const round = gameState?.round || {};
  const serverNowMs = timerServerNow(timer, localNowMs);
  const earlySeconds = captainEarlySeconds(timer, localNowMs);
  const showEarlyAnswer = gameState?.phase === 'DISCUSSION'
    && round.kind === 'normal'
    && !round.credit_repayment
    && earlySeconds > 0
    && Number.isFinite(timer?.discussion_deadline_ms)
    && serverNowMs < timer.discussion_deadline_ms;
  const showEarned = canUseEarnedMinute(gameState, localNowMs);
  const showCredit = canTakeCreditMinute(gameState, localNowMs);
  const showRepayment = canScheduleRepayment(gameState);

  if (!showEarlyAnswer && !showEarned && !showCredit && !showRepayment) return null;

  const emitAction = (event, payload = {}) => {
    setPendingAction(event);
    socket.emit(event, payload, (response) => {
      setPendingAction(null);
      if (!response?.ok) {
        addNotification?.({
          type: 'warning',
          message: responseMessage(response, 'Действие капитана отклонено'),
        });
      }
    });
  };
  const timerPayload = { timer_generation: timer?.generation };

  return (
    <div className="mb-4 w-full max-w-3xl rounded-xl border border-amber-700/70 bg-amber-950/35 p-3 shadow-lg">
      <div className="mb-2 text-center text-[10px] font-black uppercase tracking-widest text-amber-300">
        Управление капитана
      </div>
      <div className="grid gap-2 sm:grid-cols-2">
        {showEarlyAnswer && (
          <button
            type="button"
            disabled={!isConnected || pendingAction !== null}
            onClick={() => emitAction('captain_early_answer', timerPayload)}
            className="rounded-lg bg-purple-700 px-4 py-3 font-black uppercase tracking-wide text-white hover:bg-purple-600 disabled:opacity-40"
          >
            Досрочный ответ · {earlySeconds}
          </button>
        )}
        {showEarned && (
          <button
            type="button"
            disabled={!isConnected || pendingAction !== null}
            onClick={() => emitAction('captain_spend_earned_minute', timerPayload)}
            className="rounded-lg bg-sky-700 px-4 py-3 font-bold text-white hover:bg-sky-600 disabled:opacity-40"
          >
            Дополнительная минута · осталось {gameState.team.earned_minutes}
          </button>
        )}
        {showCredit && (
          <button
            type="button"
            disabled={!isConnected || pendingAction !== null}
            onClick={() => {
              if (confirm('Взять единственную минуту в кредит в этой игре?')) {
                emitAction('captain_take_credit_minute', timerPayload);
              }
            }}
            className="rounded-lg bg-rose-800 px-4 py-3 font-bold text-white hover:bg-rose-700 disabled:opacity-40"
          >
            Взять минуту в кредит
          </button>
        )}
        {showRepayment && (
          <button
            type="button"
            disabled={!isConnected || pendingAction !== null}
            onClick={() => {
              if (confirm('Следующий раунд пройдёт без обсуждения. Вернуть минуту в кредит?')) {
                emitAction('captain_schedule_credit_repayment');
              }
            }}
            className="rounded-lg bg-rose-800 px-4 py-3 font-bold text-white hover:bg-rose-700 disabled:opacity-40 sm:col-span-2"
          >
            Вернуть кредит в следующем раунде
          </button>
        )}
      </div>
    </div>
  );
}
