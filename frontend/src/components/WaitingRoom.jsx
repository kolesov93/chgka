import { useState } from 'react';
import { CurrentGameModeControl } from './CurrentGameModeControl';
import { ParticipantRoster } from './ParticipantRoster';
import { participantCount, participantGroups } from '../participants';

export function WaitingRoom({
  socket,
  players = [],
  captain,
  currentGameMode,
  gameModeLoading,
  onGameModeChange,
}) {
  const [isStarting, setIsStarting] = useState(false);

  const handleStartGame = () => {
    setIsStarting(true);
    socket.emit('start_game');
  };

  const handleKickGroup = (group) => {
    socket.emit('admin_kick', { group_id: group.group_id });
  };

  const groups = participantGroups(players);
  const playerCount = participantCount(groups, { pending: false });

  return (
    <div className="min-h-screen bg-indigo-950 text-white flex items-center justify-center p-4">
      <div className="w-full max-w-2xl bg-slate-800 p-8 rounded-xl shadow-2xl border border-slate-700">
        <h1 className="text-3xl font-bold text-center mb-2 text-yellow-500">
          Ожидание игроков
        </h1>
        <p className="text-center text-slate-400 mb-8">
          Участников: {playerCount} · подключений: {groups.filter((group) => !group.pending).length}
        </p>

        <div className="mb-8">
          <CurrentGameModeControl
            mode={currentGameMode}
            loading={gameModeLoading}
            onModeChange={onGameModeChange}
          />
        </div>

        {/* Список игроков */}
        <div className="mb-8">
          <ParticipantRoster
            groups={groups}
            captain={captain}
            onSelectCaptain={(participant) => socket.emit(
              'admin_select_captain',
              { participant_id: participant.id },
            )}
            onKick={handleKickGroup}
          />
        </div>

        {/* Кнопка "Начать" */}
        <button
          onClick={handleStartGame}
          disabled={isStarting || playerCount === 0}
          className="w-full bg-green-600 hover:bg-green-500 disabled:opacity-50 disabled:cursor-not-allowed text-white font-black py-4 rounded-lg text-xl shadow-lg active:scale-95 transition-all uppercase tracking-wider"
        >
          {isStarting ? 'Запуск...' : 'Начать игру'}
        </button>
      </div>
    </div>
  );
}
