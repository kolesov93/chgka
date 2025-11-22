import { useState } from 'react';

export function WaitingRoom({ socket, gameState, players = [] }) {
  const [isStarting, setIsStarting] = useState(false);

  const handleStartGame = () => {
    if (confirm('Начать игру?')) {
      setIsStarting(true);
      socket.emit('start_game');
    }
  };

  const playerCount = players.length;

  return (
    <div className="min-h-screen bg-slate-900 text-white flex items-center justify-center p-4">
      <div className="w-full max-w-2xl bg-slate-800 p-8 rounded-xl shadow-2xl border border-slate-700">
        <h1 className="text-3xl font-bold text-center mb-2 text-yellow-500">
          Ожидание игроков
        </h1>
        <p className="text-center text-slate-400 mb-8">
          Участники: {playerCount}
        </p>

        {/* Список игроков */}
        <div className="mb-8">
          {playerCount === 0 ? (
            <p className="text-center text-slate-500 italic">Пока никого нет</p>
          ) : (
            <div className="space-y-2">
              {players.map((player, idx) => (
                <div
                  key={player.sid || idx}
                  className={`p-3 rounded-lg border ${
                    player.role === 'admin'
                      ? 'bg-yellow-900/30 border-yellow-700'
                      : 'bg-slate-700/50 border-slate-600'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-bold">
                      {player.name}
                      {player.role === 'admin' && (
                        <span className="ml-2 text-xs text-yellow-500">[Админ]</span>
                      )}
                    </span>
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


