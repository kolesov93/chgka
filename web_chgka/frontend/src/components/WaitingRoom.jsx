import { useState } from 'react';
import { CurrentGameModeControl } from './CurrentGameModeControl';

export function WaitingRoom({
  socket,
  players = [],
  currentGameMode,
  gameModeLoading,
  onGameModeChange,
}) {
  const [isStarting, setIsStarting] = useState(false);

  const handleStartGame = () => {
    if (confirm('Начать игру?')) {
      setIsStarting(true);
      socket.emit('start_game');
    }
  };

  const handleKickPlayer = (playerName) => {
    if (confirm(`Отключить игрока "${playerName}"?`)) {
      socket.emit('admin_kick', { name: playerName });
    }
  };

  // Считаем только не-админов
  const regularPlayers = players.filter(p => p.role !== 'admin');
  const playerCount = regularPlayers.length;

  return (
    <div className="min-h-screen bg-indigo-950 text-white flex items-center justify-center p-4">
      <div className="w-full max-w-2xl bg-slate-800 p-8 rounded-xl shadow-2xl border border-slate-700">
        <h1 className="text-3xl font-bold text-center mb-2 text-yellow-500">
          Ожидание игроков
        </h1>
        <p className="text-center text-slate-400 mb-8">
          Игроков: {playerCount}
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
          {playerCount === 0 ? (
            <p className="text-center text-slate-500 italic">Пока никого нет</p>
          ) : (
            <div className="space-y-2">
              {regularPlayers.map((player, idx) => (
                <div
                  key={idx}
                  className={`p-3 rounded-lg border ${
                    player.online
                      ? 'bg-slate-700/50 border-slate-600'
                      : 'bg-slate-800/50 border-slate-700'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <span className={`w-2.5 h-2.5 rounded-full ${player.online ? 'bg-green-500' : 'bg-slate-600'}`} />
                      <span className={`font-bold ${player.online ? 'text-white' : 'text-slate-500'}`}>
                        {player.name}
                      </span>
                      {!player.online && (
                        <span className="text-xs text-slate-600">(оффлайн)</span>
                      )}
                    </div>
                    <button
                      onClick={() => handleKickPlayer(player.name)}
                      className="text-xs bg-red-900/50 hover:bg-red-800 text-red-300 hover:text-white px-3 py-1 rounded font-bold uppercase transition-colors"
                    >
                      Отключить
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
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
