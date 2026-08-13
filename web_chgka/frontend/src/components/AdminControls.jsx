import { GameLog } from './GameLog';
import { IntroHostControls } from './IntroHostControls';
import { LiveOpsPanel } from './LiveOpsPanel';
import { CurrentGameModeControl } from './CurrentGameModeControl';
import { ParticipantRoster } from './ParticipantRoster';
import { socket } from '../socket';
import {
  approvedParticipantOptions,
  groupDisplayName,
  participantCount,
  participantGroups,
} from '../participants';
import { responseMessage } from '../uiText';
import {
  canScheduleRepayment,
  canHostDeclareEarlyAnswer,
  canTakeCreditMinute,
  canUseEarnedMinute,
  timerSegmentLabel,
} from '../gameMinutes';

export function AdminControls({
  gameState,
  gameSettings,
  players,
  discussionRemaining,
  onTenSeconds,
  stopAllSounds,
  addNotification,
  currentGameMode,
  gameModeLoading,
  onGameModeChange,
}) {
  const usedQuestions = gameState?.used_questions || [];
  const phase = gameState?.phase || 'LOGIN';
  const isIntro = phase === 'INTRO';
  const isPreRound = phase === 'PRE_ROUND';
  const isQuestionReading = phase === 'QUESTION_READING';
  const isDiscussion = phase === 'DISCUSSION';
  const isTeamAnswer = phase === 'TEAM_ANSWER';
  const isPostRound = phase === 'POST_ROUND';
  const isGameOver = phase === 'GAME_OVER';
  const blackboxActive = Boolean(gameState?.blackbox);
  const round = gameState?.round || null;
  const roundKind = round?.kind || 'normal';
  const isBlitzRound = roundKind === 'blitz' || roundKind === 'superblitz';
  const partIndex = typeof round?.part_index === 'number' ? round.part_index : null;
  const partLabel = isBlitzRound && partIndex !== null ? `${partIndex + 1}/3` : null;
  const blitzHasNextPart = isBlitzRound && round?.advance_next_part === true;
  const hasWinner = (gameState?.score?.znatoki ?? 0) >= 6 || (gameState?.score?.tv ?? 0) >= 6;
  const groups = participantGroups(players);
  const approvedPlayerCount = participantCount(groups, { pending: false });
  const pendingPlayerCount = participantCount(groups.filter((group) => group.pending));
  const respondentOptions = approvedParticipantOptions(players);
  const respondent = round?.respondent || null;
  const isSuperblitz = roundKind === 'superblitz';
  const team = gameState?.team || {};
  const captain = team.captain || null;
  const timer = gameState?.timer || null;
  const hostEarlyAnswerAvailable = canHostDeclareEarlyAnswer(gameState);
  const earnedMinuteAvailable = canUseEarnedMinute(gameState);
  const creditMinuteAvailable = canTakeCreditMinute(gameState);
  const repaymentCanBeScheduled = canScheduleRepayment(gameState);
  const strategyRequest = round?.strategy_request || null;

  const spinForced = (sectorId) => {
    if (confirm(`Крутим на сектор ${sectorId}?`)) {
      socket.emit('admin_spin', { force_sector: sectorId });
    }
  };

  const resetGame = () => {
    const message = isGameOver
      ? 'Начать новую игру? Счёт и сыгранные сектора будут сброшены.'
      : 'Точно сбросить игру?';
    if (confirm(message)) socket.emit('admin_reset');
  };

  const signalTenSeconds = () => {
    onTenSeconds();
    socket.emit('admin_ten_seconds');
  };

  const fadeSounds = () => {
    socket.emit('admin_fade_sounds');
  };

  const silence = () => {
    socket.emit('admin_stop_sounds');
    stopAllSounds();
  };

  const kickGroup = (group) => {
    if (confirm(`Отключить группу «${groupDisplayName(group)}»?`)) {
      socket.emit('admin_kick', { group_id: group.group_id });
    }
  };

  const selectRespondent = (participantId) => {
    if (!participantId) return;
    socket.emit(
      'admin_select_respondent',
      { participant_id: participantId },
      (response) => {
        if (!response?.ok) {
          addNotification({
            type: 'warning',
            message: responseMessage(response, 'Не удалось выбрать отвечавшего'),
          });
        }
      },
    );
  };

  const emitHostAction = (event, payload = {}, fallbackMessage = 'Действие отклонено') => {
    socket.emit(event, payload, (response) => {
      if (!response?.ok) {
        addNotification({
          type: 'warning',
          message: responseMessage(response, fallbackMessage),
        });
      }
    });
  };

  const selectCaptain = (participant) => {
    emitHostAction(
      'admin_select_captain',
      { participant_id: participant.id },
      'Не удалось выбрать капитана',
    );
  };

  const timerPayload = { timer_generation: timer?.generation };

  const takeCredit = () => {
    if (confirm('Дать команде минуту в кредит?')) {
      emitHostAction('admin_take_credit_minute', timerPayload, 'Не удалось взять кредит');
    }
  };

  const resolveStrategyRequest = (approve) => {
    emitHostAction(
      'admin_resolve_strategy_request',
      { approve },
      'Не удалось обработать запрос капитана',
    );
  };

  const scheduleRepayment = () => {
    if (confirm('Следующий раунд пройдёт без обсуждения. Вернуть минуту в кредит?')) {
      emitHostAction(
        'admin_schedule_credit_repayment',
        {},
        'Не удалось назначить возврат кредита',
      );
    }
  };

  const respondentSelector = (
    <div className="mb-2 rounded border border-violet-800/60 bg-violet-950/25 p-2">
      <div className="mb-2 text-[10px] font-bold uppercase tracking-widest text-violet-300">
        {isSuperblitz ? 'Участник суперблица' : 'Кто отвечает'}
      </div>
      {respondentOptions.length === 0 ? (
        <div className="rounded border border-slate-700 bg-slate-900 px-2 py-2 text-xs text-slate-500">
          Нет допущенных участников
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-1.5">
          {respondentOptions.map((option) => {
            const isSelected = respondent?.participant_id === option.value;
            return (
              <button
                key={option.value}
                type="button"
                aria-pressed={isSelected}
                onClick={() => selectRespondent(option.value)}
                className={`min-h-9 rounded border px-2 py-1.5 text-left text-xs font-bold transition-colors ${
                  isSelected
                    ? 'border-violet-400 bg-violet-700 text-white ring-1 ring-violet-400'
                    : option.online
                      ? 'border-slate-600 bg-slate-800 text-slate-100 hover:border-violet-500 hover:bg-slate-700'
                      : 'border-slate-700 bg-slate-900 text-slate-500 hover:border-violet-700 hover:text-slate-300'
                }`}
              >
                {option.label}
                {!option.online && <span className="ml-1 font-normal">(оффлайн)</span>}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );

  return (
    <div className="w-full lg:w-[600px] flex flex-col gap-4">
      {strategyRequest && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-slate-950/80 p-4 backdrop-blur-sm">
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="strategy-request-title"
            className="w-full max-w-md rounded-2xl border border-amber-600/70 bg-slate-900 p-6 text-center shadow-2xl"
          >
            <div className="mb-2 text-[10px] font-black uppercase tracking-[0.22em] text-amber-400">
              Запрос капитана
            </div>
            <h2 id="strategy-request-title" className="text-xl font-black text-white">
              {strategyRequest.type === 'early_answer'
                ? 'Принять досрочный ответ?'
                : 'Дать минуту в кредит?'}
            </h2>
            <p className="mt-2 text-sm text-slate-400">
              Капитан: {strategyRequest.name}
            </p>
            <div className="mt-6 grid grid-cols-2 gap-3">
              <button
                type="button"
                onClick={() => resolveStrategyRequest(false)}
                className="rounded-lg bg-slate-700 px-4 py-3 font-bold text-slate-100 hover:bg-slate-600"
              >
                {strategyRequest.type === 'early_answer' ? 'Не принимать' : 'Не давать'}
              </button>
              <button
                type="button"
                onClick={() => resolveStrategyRequest(true)}
                className="rounded-lg bg-amber-600 px-4 py-3 font-black text-slate-950 hover:bg-amber-500"
              >
                {strategyRequest.type === 'early_answer' ? 'Принять' : 'Дать минуту'}
              </button>
            </div>
          </div>
        </div>
      )}
      <div className="bg-slate-800 p-4 rounded-xl shadow-2xl border border-slate-700 flex flex-col gap-6 sticky top-4">
        <div className="flex justify-between items-center border-b border-slate-700 pb-2">
          <span className="text-sm font-bold text-slate-400 uppercase">Панель ведущего</span>
          <div className="flex gap-2">
            <button
              onClick={resetGame}
              className="text-[10px] bg-slate-700 hover:bg-slate-600 text-slate-300 py-1 px-2 rounded font-bold uppercase tracking-wider"
            >
              {isGameOver ? 'Новая игра' : 'Сброс'}
            </button>
          </div>
        </div>

        <CurrentGameModeControl
          mode={currentGameMode}
          loading={gameModeLoading}
          onModeChange={onGameModeChange}
        />

        {isIntro && <IntroHostControls intro={gameState?.intro} />}

        {!isGameOver && !isIntro && (
          <div className="flex flex-col gap-3 border border-slate-700 p-3 rounded bg-slate-900/30">
          <div className="text-xs text-yellow-600 uppercase font-bold tracking-widest text-center">
            Управление Волчком
          </div>

          <button
            onClick={() => socket.emit('admin_spin')}
            disabled={gameState?.is_spinning || !isPreRound}
            className="w-full bg-yellow-500 hover:bg-yellow-400 disabled:opacity-50 disabled:cursor-not-allowed text-black font-black py-3 rounded-lg text-lg shadow active:scale-[0.98] transition-all uppercase tracking-wider"
          >
            {gameState?.is_spinning ? 'Вращаем...' : '🎲 Случайный выбор'}
          </button>

          <div className="text-[10px] text-slate-500 text-center uppercase font-bold mt-1">
            Или выбрать сектор
          </div>

          <div className="grid grid-cols-7 gap-1">
            {Array.from({ length: 13 }, (_, index) => index + 1).map((sectorId) => {
              const isUsed = usedQuestions.includes(sectorId);
              return (
                <button
                  key={sectorId}
                  onClick={() => spinForced(sectorId)}
                  disabled={gameState?.is_spinning || isUsed || !isPreRound}
                  className={`
                    text-xs font-bold py-2 rounded transition-all
                    ${isUsed
                      ? 'bg-slate-800 text-slate-600 cursor-not-allowed border border-slate-700'
                      : 'bg-slate-700 hover:bg-slate-600 text-white shadow active:scale-95 hover:ring-1 ring-yellow-500/50'}
                  `}
                >
                  {sectorId}
                </button>
              );
            })}
          </div>
          </div>
        )}

        {!isIntro && (
          <div className="border border-slate-700 p-3 rounded bg-slate-900/30">
            <div className="w-full">
            {isQuestionReading && (
              <>
                {isSuperblitz && (!respondent || partIndex === 0) && respondentSelector}
                {hostEarlyAnswerAvailable && (
                  <button
                    type="button"
                    onClick={() => emitHostAction(
                      'admin_early_answer',
                      timerPayload,
                      'Не удалось принять досрочный ответ',
                    )}
                    className="mb-2 w-full rounded bg-purple-800 py-2 text-[10px] font-black uppercase tracking-wider text-white hover:bg-purple-700"
                  >
                    Досрочный ответ
                  </button>
                )}
                <button
                  onClick={() => round?.credit_repayment
                    ? emitHostAction(
                      'admin_repayment_answer',
                      {},
                      'Не удалось принять ответ без обсуждения',
                    )
                    : socket.emit('admin_start_discussion')}
                  disabled={blackboxActive || (isSuperblitz && !respondent)}
                  className={`w-full disabled:cursor-not-allowed disabled:opacity-40 text-white py-3 rounded shadow active:scale-95 transition-all font-bold uppercase tracking-wider text-xs ${
                    round?.credit_repayment
                      ? 'bg-rose-800 hover:bg-rose-700'
                      : 'bg-blue-700 hover:bg-blue-600'
                  }`}
                >
                  {blackboxActive
                    ? 'Сначала завершите чёрный ящик'
                    : isSuperblitz && !respondent
                      ? 'Сначала выберите участника'
                      : round?.credit_repayment
                        ? 'Принять ответ без обсуждения'
                        : 'Начать обсуждение'}
                </button>
              </>
            )}
            {isDiscussion && (
              <div className="flex flex-col gap-2">
                <div className="flex items-center justify-between px-2 py-2 rounded bg-slate-950/40 border border-slate-800">
                  <span className="text-[10px] uppercase font-bold text-slate-400 tracking-widest">
                    {timerSegmentLabel(timer?.segment)}
                  </span>
                  <span
                    className={`text-lg font-black tabular-nums ${
                      typeof discussionRemaining === 'number' && discussionRemaining <= 10
                        ? 'text-yellow-400'
                        : 'text-white'
                    }`}
                  >
                    {typeof discussionRemaining === 'number' ? discussionRemaining : '—'}
                  </span>
                </div>
                {hostEarlyAnswerAvailable && (
                  <button
                    type="button"
                    onClick={() => emitHostAction(
                      'admin_early_answer',
                      timerPayload,
                      'Не удалось принять досрочный ответ',
                    )}
                    className="w-full rounded bg-purple-800 py-2 text-[10px] font-black uppercase tracking-wider text-white hover:bg-purple-700"
                  >
                    Досрочный ответ
                  </button>
                )}
                <div className="flex gap-2">
                  <button
                    onClick={signalTenSeconds}
                    className="flex-1 bg-yellow-600 hover:bg-yellow-500 text-black py-2 rounded shadow active:scale-95 transition-all font-black uppercase tracking-wider text-[10px]"
                  >
                    10 секунд (сигнал)
                  </button>
                  <button
                    onClick={() => socket.emit('admin_team_answer')}
                    className="flex-1 bg-purple-700 hover:bg-purple-600 text-white py-2 rounded shadow active:scale-95 transition-all font-bold uppercase tracking-wider text-[10px]"
                  >
                    Ответ команды
                  </button>
                </div>
              </div>
            )}
            {isTeamAnswer && (
              <div>
                {(earnedMinuteAvailable || creditMinuteAvailable) && (
                  <div className="mb-2 flex flex-wrap justify-center gap-2">
                    {earnedMinuteAvailable && (
                      <button
                        type="button"
                        onClick={() => emitHostAction(
                          'admin_spend_earned_minute',
                          timerPayload,
                          'Не удалось запустить дополнительную минуту',
                        )}
                        className="w-full max-w-sm rounded bg-sky-800 px-2 py-2 text-[10px] font-bold uppercase tracking-wider text-white hover:bg-sky-700"
                      >
                        Доп. минута · {team.earned_minutes}
                      </button>
                    )}
                    {creditMinuteAvailable && (
                      <button
                        type="button"
                        onClick={takeCredit}
                        className="w-full max-w-sm rounded bg-rose-800 px-2 py-2 text-[10px] font-bold uppercase tracking-wider text-white hover:bg-rose-700"
                      >
                        Минута в кредит
                      </button>
                    )}
                  </div>
                )}
                {!isSuperblitz && respondentSelector}
                <div className="flex gap-2">
                <button
                  onClick={() => socket.emit('admin_score', { winner: 'znatoki' })}
                  disabled={!respondent}
                  className="flex-1 bg-green-800 hover:bg-green-700 disabled:cursor-not-allowed disabled:opacity-40 text-white py-2 rounded shadow active:scale-95 transition-all flex flex-col items-center"
                >
                  <span className="text-[10px] uppercase opacity-70 font-bold">
                    {isBlitzRound && partIndex !== null && partIndex < 2
                      ? `Верно (${partLabel})`
                      : 'Знатоки'}
                  </span>
                  <span className="text-xl font-bold leading-none">
                    {isBlitzRound && partIndex !== null && partIndex < 2 ? '→' : '+1'}
                  </span>
                </button>

                <button
                  onClick={() => socket.emit('admin_score', { winner: 'tv' })}
                  disabled={!respondent}
                  className="flex-1 bg-red-800 hover:bg-red-700 disabled:cursor-not-allowed disabled:opacity-40 text-white py-2 rounded shadow active:scale-95 transition-all flex flex-col items-center"
                >
                  <span className="text-[10px] uppercase opacity-70 font-bold">
                    {isBlitzRound ? 'Неверно (ТВ +1)' : 'Телезрители'}
                  </span>
                  <span className="text-xl font-bold leading-none">+1</span>
                </button>
                </div>
              </div>
            )}
            {isPostRound && (
              <div className="flex flex-col gap-2">
                {repaymentCanBeScheduled && (
                  <button
                    type="button"
                    onClick={scheduleRepayment}
                    className="w-full rounded bg-rose-800 py-2 text-[10px] font-bold uppercase tracking-wider text-white hover:bg-rose-700"
                  >
                    Вернуть кредит в следующем раунде
                  </button>
                )}
                <button
                  onClick={() => socket.emit('admin_end_round')}
                  className={`w-full text-white py-3 rounded shadow active:scale-95 transition-all font-bold uppercase tracking-wider text-xs ${
                    hasWinner
                      ? 'bg-yellow-700 hover:bg-yellow-600'
                      : 'bg-emerald-700 hover:bg-emerald-600'
                  }`}
                >
                  {hasWinner
                    ? 'Завершить игру'
                    : blitzHasNextPart
                      ? 'Следующая часть'
                      : 'Завершить раунд'}
                </button>
              </div>
            )}
            {isPreRound && (
              <div className="flex flex-col gap-2">
                {repaymentCanBeScheduled && (
                  <button
                    type="button"
                    onClick={scheduleRepayment}
                    className="w-full rounded bg-rose-800 py-2 text-[10px] font-bold uppercase tracking-wider text-white hover:bg-rose-700"
                  >
                    Вернуть кредит в следующем раунде
                  </button>
                )}
                <div className="text-xs text-slate-500 font-bold uppercase tracking-widest">
                  Фаза: ожидание вращения
                </div>
              </div>
            )}
            {isGameOver && (
              <div className="rounded border border-yellow-800/60 bg-yellow-950/20 px-3 py-3 text-center text-xs font-bold uppercase tracking-widest text-yellow-300">
                Игра завершена
              </div>
            )}
            </div>
          </div>
        )}

        <div className="bg-slate-900/50 p-3 rounded-lg border border-slate-700 flex flex-col gap-3">
          <div className="flex items-center gap-3">
            <span className="text-xs text-slate-500 uppercase font-bold">Звук</span>
            <input
              type="range"
              min="0"
              max="1"
              step="0.05"
              value={gameSettings?.volume ?? 1.0}
              onChange={(event) => {
                socket.emit('admin_volume', { volume: parseFloat(event.target.value) });
              }}
              className="flex-1 h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-yellow-500"
            />
            <span className="text-xs text-slate-400 w-8 text-right">
              {Math.round((gameSettings?.volume ?? 1.0) * 100)}%
            </span>
          </div>
          <div className="grid grid-cols-2 gap-2">
            <button
              type="button"
              onClick={fadeSounds}
              className="rounded bg-amber-800 hover:bg-amber-700 px-3 py-2 text-[10px] font-bold uppercase tracking-wider text-white transition-colors"
            >
              Затухание 3 с
            </button>
            <button
              type="button"
              onClick={silence}
              className="rounded bg-red-900 hover:bg-red-800 px-3 py-2 text-[10px] font-bold uppercase tracking-wider text-white transition-colors"
            >
              Выключить звук
            </button>
          </div>
        </div>

        <div className="border border-slate-700 p-3 rounded bg-slate-900/30">
          <div className="text-xs text-slate-500 uppercase font-bold tracking-widest mb-2">
            Игроки ({approvedPlayerCount})
            {pendingPlayerCount > 0 && (
              <span className="text-yellow-500 ml-2">+ {pendingPlayerCount} ожидают</span>
            )}
          </div>
          <div className="space-y-1 max-h-40 overflow-y-auto">
            <ParticipantRoster
              groups={groups}
              captain={captain}
              compact
              onSelectCaptain={selectCaptain}
              onApprove={(group) => socket.emit('admin_approve', { group_id: group.group_id })}
              onKick={kickGroup}
            />
          </div>
        </div>

        <div className="pt-2 border-t border-slate-700">
          <LiveOpsPanel
            gameState={gameState}
            addNotification={addNotification}
          />
        </div>

        <div className="pt-2 border-t border-slate-700">
          <GameLog logs={gameState?.logs} />
        </div>
      </div>
    </div>
  );
}
