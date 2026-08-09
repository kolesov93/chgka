import { GameLog } from './GameLog';
import { GameHistoryPanel } from './GameHistoryPanel';
import { LiveOpsPanel } from './LiveOpsPanel';
import { socket } from '../socket';

export function AdminControls({
  gameState,
  gameSettings,
  players,
  discussionRemaining,
  onTenSeconds,
  stopAllSounds,
  addNotification,
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
  const regularPlayers = players.filter((player) => player.role !== 'admin');
  const approvedPlayerCount = regularPlayers.filter((player) => !player.pending).length;
  const pendingPlayerCount = regularPlayers.filter((player) => player.pending).length;

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

  const kickPlayer = (playerName) => {
    if (confirm(`Отключить игрока "${playerName}"?`)) {
      socket.emit('admin_kick', { name: playerName });
    }
  };

  return (
    <div className="w-full lg:w-[600px] flex flex-col gap-4">
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

        <div className="border border-slate-700 p-3 rounded bg-slate-900/30">
          <div className="w-full">
            {isQuestionReading && (
              <button
                onClick={() => socket.emit('admin_start_discussion')}
                disabled={blackboxActive}
                className="w-full bg-blue-700 hover:bg-blue-600 disabled:cursor-not-allowed disabled:opacity-40 text-white py-3 rounded shadow active:scale-95 transition-all font-bold uppercase tracking-wider text-xs"
              >
                {blackboxActive ? 'Сначала завершите чёрный ящик' : 'Начать обсуждение'}
              </button>
            )}
            {isDiscussion && (
              <div className="flex flex-col gap-2">
                <div className="flex items-center justify-between px-2 py-2 rounded bg-slate-950/40 border border-slate-800">
                  <span className="text-[10px] uppercase font-bold text-slate-400 tracking-widest">
                    Обсуждение
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
              <div className="flex gap-2">
                <button
                  onClick={() => socket.emit('admin_score', { winner: 'znatoki' })}
                  className="flex-1 bg-green-800 hover:bg-green-700 text-white py-2 rounded shadow active:scale-95 transition-all flex flex-col items-center"
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
                  className="flex-1 bg-red-800 hover:bg-red-700 text-white py-2 rounded shadow active:scale-95 transition-all flex flex-col items-center"
                >
                  <span className="text-[10px] uppercase opacity-70 font-bold">
                    {isBlitzRound ? 'Неверно (ТВ +1)' : 'Телезрители'}
                  </span>
                  <span className="text-xl font-bold leading-none">+1</span>
                </button>
              </div>
            )}
            {isPostRound && (
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
            )}
            {isPreRound && (
              <div className="text-xs text-slate-500 font-bold uppercase tracking-widest">
                Фаза: ожидание вращения
              </div>
            )}
            {isIntro && (
              <div className="rounded border border-blue-800/60 bg-blue-950/20 px-3 py-3 text-center text-xs font-bold uppercase tracking-widest text-blue-300">
                Интро управляется рядом со слайдом
              </div>
            )}
            {isGameOver && (
              <div className="rounded border border-yellow-800/60 bg-yellow-950/20 px-3 py-3 text-center text-xs font-bold uppercase tracking-widest text-yellow-300">
                Игра завершена
              </div>
            )}
          </div>
        </div>

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
            {regularPlayers.length === 0 ? (
              <div className="text-xs text-slate-600 italic">Нет игроков</div>
            ) : (
              regularPlayers.map((player, index) => (
                <div
                  key={index}
                  className={`flex items-center justify-between px-2 py-1.5 rounded ${
                    player.pending
                      ? 'bg-yellow-900/30 border border-yellow-700/50'
                      : 'bg-slate-800'
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <span
                      className={`w-2 h-2 rounded-full ${
                        player.pending
                          ? 'bg-yellow-500 animate-pulse'
                          : player.online
                            ? 'bg-green-500'
                            : 'bg-slate-600'
                      }`}
                    />
                    <span
                      className={`text-sm ${
                        player.pending
                          ? 'text-yellow-300'
                          : player.online
                            ? 'text-white'
                            : 'text-slate-500'
                      }`}
                    >
                      {player.name}
                      {player.pending && <span className="text-xs ml-1">(ждёт)</span>}
                    </span>
                  </div>
                  <div className="flex gap-1">
                    {player.pending && (
                      <button
                        onClick={() => socket.emit('admin_approve', { name: player.name })}
                        className="text-[10px] bg-green-700 hover:bg-green-600 text-white px-2 py-0.5 rounded font-bold uppercase transition-colors"
                      >
                        Пустить
                      </button>
                    )}
                    <button
                      onClick={() => kickPlayer(player.name)}
                      className="text-[10px] bg-red-900/50 hover:bg-red-800 text-red-300 hover:text-white px-2 py-0.5 rounded font-bold uppercase transition-colors"
                    >
                      Отключить
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        <div className="pt-2 border-t border-slate-700">
          <GameHistoryPanel socket={socket} addNotification={addNotification} />
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
