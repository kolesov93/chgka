import { useState, useEffect } from 'react'
import io from 'socket.io-client'
import { GameTable } from './components/GameTable'
import { ScoreBoard } from './components/ScoreBoard'
import { GameLog } from './components/GameLog'
import { LoginScreen } from './components/LoginScreen'
import { WaitingRoom } from './components/WaitingRoom'
import { useGameSound } from './hooks/useGameSound'

const socket = io(import.meta.env.DEV ? 'http://localhost:8000' : '/', {
  transports: ['websocket']
})

const ADMIN_TOKEN_KEY = 'chgka_admin_token';
const PLAYER_TOKEN_KEY = 'chgka_player_token';

function App() {
  const [gameState, setGameState] = useState(null)
  const [gameSettings, setGameSettings] = useState({ volume: 1.0 })
  const [players, setPlayers] = useState([]) // Список игроков (только для админа)
  const [myRole, setMyRole] = useState('player')
  const [myName, setMyName] = useState('');
  const [packInfo, setPackInfo] = useState(null); // Только для админа: данные пака вопросов
  const [isConnected, setIsConnected] = useState(socket.connected)
  const [hasJoined, setHasJoined] = useState(false) // Флаг, что игрок ввел имя
  const [isPending, setIsPending] = useState(false) // Ожидает одобрения админа
  const [notifications, setNotifications] = useState([]) // Уведомления для админа
  
  const { playSound, stopAllSounds, masterVolume } = useGameSound(gameState, gameSettings?.volume);

  const handleVolumeChange = (e) => {
      const vol = parseFloat(e.target.value);
      // Отправляем на сервер
      socket.emit('admin_volume', { volume: vol });
  };

  const authenticateAdmin = (password) => {
    socket.emit('authenticate_admin', { password });
  };

  useEffect(() => {
    window.authenticateAdmin = authenticateAdmin;
    return () => { delete window.authenticateAdmin; };
  }, []);

  useEffect(() => {
    function onConnect() { 
      setIsConnected(true);
      
      // Восстанавливаем админа (если есть токен)
      const savedToken = localStorage.getItem(ADMIN_TOKEN_KEY);
      if (savedToken) {
        socket.emit('restore_session', { token: savedToken });
      }
      
      // Восстанавливаем игрока (если есть токен)
      const savedPlayerToken = localStorage.getItem(PLAYER_TOKEN_KEY);
      if (savedPlayerToken) {
        socket.emit('restore_session', { player_token: savedPlayerToken });
      }
    }
    
    function onDisconnect() { 
      setIsConnected(false)
      setMyRole('player')
      setMyName('')
    }
    
    function onStateUpdate(newState) { 
      setGameState(newState);
      // hasJoined теперь управляется через join_success / auth_restored
    }

    function onPlayersUpdate(data) {
        if (data && data.players) {
            setPlayers(data.players);
        }
    }

    function onRoleUpdate(data) {
      if (data && data.role) {
        setMyRole(data.role);
      }
    }
    
    function onPackInfo(data) {
      if (data && data.pack) {
        setPackInfo(data.pack);
      }
    }

    function onSettingsUpdate(newSettings) {
        if (newSettings) {
            setGameSettings(prev => ({ ...prev, ...newSettings }));
        }
    }
    
    function onPlaySound(data) { 
        if (data.category) {
            playSound(data.category);
        } else {
            playSound(data.sound); 
        }
    }

    function onStopSound() {
        stopAllSounds();
    }

    function onAuthSuccess(data) {
      const token = data.token;
      localStorage.setItem(ADMIN_TOKEN_KEY, token);
    }

    function onAuthFailed(data) {
      console.error('[Auth] Failed:', data.message || 'Неверный пароль');
      localStorage.removeItem(ADMIN_TOKEN_KEY);
    }

    function onAuthRestored() {
      console.log('[Auth] Session restored successfully');
    }

    function onJoinSuccess(data) {
      if (data.token) {
          localStorage.setItem(PLAYER_TOKEN_KEY, data.token);
      }
      if (data.name) {
          setMyName(data.name);
      }
      setIsPending(false);
      setHasJoined(true);
    }

    function onJoinPending(data) {
      // Игрок ожидает одобрения админа
      if (data.token) {
          localStorage.setItem(PLAYER_TOKEN_KEY, data.token);
      }
      if (data.name) {
          setMyName(data.name);
      }
      setIsPending(true);
      setHasJoined(true);
    }

    function onKicked(data) {
      // Сначала удаляем токен (до alert, который блокирует)
      localStorage.removeItem(PLAYER_TOKEN_KEY);
      setGameState(null);
      setMyRole('player');
      setMyName('');
      setHasJoined(false);
      setIsPending(false);
      
      // Показываем сообщение после сброса состояния
      alert(data.message || 'Вы были отключены');
      
      // Принудительно переподключаемся для чистого состояния
      socket.disconnect();
      socket.connect();
    }

    function onAdminNotification(data) {
      // Добавляем уведомление для админа
      const id = Date.now();
      setNotifications(prev => [...prev, { id, ...data }]);
      // Автоматически убираем через 5 секунд
      setTimeout(() => {
        setNotifications(prev => prev.filter(n => n.id !== id));
      }, 5000);
    }

    socket.on('connect', onConnect)
    socket.on('disconnect', onDisconnect)
    socket.on('state_update', onStateUpdate)
    socket.on('role_update', onRoleUpdate)
    socket.on('settings_update', onSettingsUpdate)
    socket.on('players_update', onPlayersUpdate)
    socket.on('play_sound', onPlaySound)
    socket.on('stop_sound', onStopSound)
    socket.on('auth_success', onAuthSuccess)
    socket.on('auth_failed', onAuthFailed)
    socket.on('auth_restored', onAuthRestored)
    socket.on('join_success', onJoinSuccess)
    socket.on('join_pending', onJoinPending)
    socket.on('kicked', onKicked)
    socket.on('admin_notification', onAdminNotification)
    socket.on('pack_info', onPackInfo)

    return () => {
      socket.off('connect', onConnect)
      socket.off('disconnect', onDisconnect)
      socket.off('state_update', onStateUpdate)
      socket.off('role_update', onRoleUpdate)
      socket.off('settings_update', onSettingsUpdate)
      socket.off('players_update', onPlayersUpdate)
      socket.off('play_sound', onPlaySound)
      socket.off('stop_sound', onStopSound)
      socket.off('auth_success', onAuthSuccess)
      socket.off('auth_failed', onAuthFailed)
      socket.off('auth_restored', onAuthRestored)
      socket.off('join_success', onJoinSuccess)
      socket.off('join_pending', onJoinPending)
      socket.off('kicked', onKicked)
      socket.off('admin_notification', onAdminNotification)
      socket.off('pack_info', onPackInfo)
    }
  }, []) 

  const handleJoinSuccess = () => {
     // Эта функция вызывалась из LoginScreen, но теперь основная логика в socket.on('join_success')
     // Оставим пустым или удалим пропс
  };
  
  const handleLogout = () => {
      if (confirm('Вы действительно хотите выйти?')) {
          socket.emit('leave_game');
          
          localStorage.removeItem(ADMIN_TOKEN_KEY);
          localStorage.removeItem(PLAYER_TOKEN_KEY);
          socket.disconnect();
          
          // Сбрасываем стейт
          setGameState(null);
          setMyRole('player');
          setMyName('');
          setHasJoined(false);
          setPlayers([]);
          setIsConnected(false);
          
          // Подключаемся заново
          socket.connect();
      }
  };

  const handleSpinRandom = () => socket.emit('admin_spin')
  
  const handleSpinForced = (sectorId) => {
      if (confirm(`Крутим на сектор ${sectorId}?`)) {
          socket.emit('admin_spin', { force_sector: sectorId })
      }
  }

  const handleGongClick = () => socket.emit('admin_sound', { sound: 'gong' })
  const handleResetClick = () => {
    if (confirm('Точно сбросить игру?')) socket.emit('admin_reset')
  }
  
  const handleSilenceClick = () => {
      socket.emit('admin_stop_sounds');
      stopAllSounds(); // Сразу останавливаем у себя
  }

  const handleScoreZnatoki = () => socket.emit('admin_score', { winner: 'znatoki' })
  const handleScoreTV = () => socket.emit('admin_score', { winner: 'tv' })
  const handleStartDiscussion = () => socket.emit('admin_start_discussion')
  const handleTeamAnswer = () => socket.emit('admin_team_answer')
  
  const handleKickPlayer = (playerName) => {
      if (confirm(`Отключить игрока "${playerName}"?`)) {
          socket.emit('admin_kick', { name: playerName });
      }
  }
  
  const handleApprovePlayer = (playerName) => {
      socket.emit('admin_approve', { name: playerName });
  }
  
  const dismissNotification = (id) => {
      setNotifications(prev => prev.filter(n => n.id !== id));
  }

  const usedQuestions = gameState?.used_questions || [];
  const phase = gameState?.phase || 'LOGIN';
  const isPreRound = phase === 'PRE_ROUND';
  const isQuestionReading = phase === 'QUESTION_READING';
  const isDiscussion = phase === 'DISCUSSION';
  const isTeamAnswer = phase === 'TEAM_ANSWER';

  // --- КОМПОНЕНТ ШАПКИ ПОЛЬЗОВАТЕЛЯ ---
  const UserHeader = () => (
      <div className="absolute top-4 right-4 flex items-center gap-4">
        {myName && (
            <div className="text-slate-400 text-sm font-bold">
                {myRole === 'admin' ? <span className="text-yellow-500">Ведущий</span> : myName}
            </div>
        )}
        <button 
            onClick={handleLogout}
            className="text-xs bg-slate-700 hover:bg-slate-600 text-slate-300 py-2 px-3 rounded font-bold uppercase tracking-wider transition-colors"
        >
            Выход
        </button>
      </div>
  );

  // --- КОМПОНЕНТ УВЕДОМЛЕНИЙ ---
  const NotificationsPanel = () => (
    notifications.length > 0 && (
      <div className="fixed top-4 left-1/2 -translate-x-1/2 z-50 flex flex-col gap-2">
        {notifications.map(n => (
          <div 
            key={n.id}
            className="bg-yellow-500 text-black px-4 py-3 rounded-lg shadow-lg flex items-center gap-3 animate-pulse"
          >
            <span className="font-bold">
              {n.type === 'player_waiting'
                ? `🔔 ${n.name} ожидает одобрения`
                : (n.message || `🔔 ${n.type}`)}
            </span>
            <button 
              onClick={() => dismissNotification(n.id)}
              className="text-black/50 hover:text-black font-bold"
            >
              ✕
            </button>
          </div>
        ))}
      </div>
    )
  );

  // --- УСЛОВНЫЙ РЕНДЕРИНГ ПО ФАЗЕ ---
  
  // Если игрок не залогинен — показываем форму входа
  if (myRole !== 'admin' && !hasJoined) {
    return <LoginScreen socket={socket} gameState={gameState} />;
  }
  
  // Если игрок ожидает одобрения админа
  if (myRole !== 'admin' && isPending) {
    return (
      <div className="min-h-screen bg-slate-900 text-white flex items-center justify-center relative">
        <UserHeader />
        <div className="text-center">
          <div className="text-6xl mb-6">⏳</div>
          <h1 className="text-3xl font-bold mb-4 text-yellow-500">Ожидание одобрения</h1>
          <p className="text-slate-400 mb-2">Игра уже началась</p>
          <p className="text-slate-500 text-sm">Администратор должен разрешить вам присоединиться</p>
        </div>
      </div>
    );
  }
  
  if (phase === 'LOGIN') {
    // Админ видит WaitingRoom
    if (myRole === 'admin') {
      return (
        <>
            <NotificationsPanel />
            <UserHeader />
            <WaitingRoom socket={socket} gameState={gameState} players={players} />
        </>
      );
    }
    
    // Игрок присоединился, но игра еще не началась - показываем экран ожидания
    return (
      <div className="min-h-screen bg-slate-900 text-white flex items-center justify-center relative">
        <UserHeader />
        <div className="text-center">
          <h1 className="text-4xl font-bold mb-4 text-yellow-500">Ожидание начала игры</h1>
          <p className="text-slate-400">Администратор запустит игру, когда все будут готовы</p>
        </div>
      </div>
    );
  }

  // Фаза PRE_ROUND и далее: показываем игру
  return (
    <div className="min-h-screen bg-slate-900 text-white p-4 flex flex-col lg:flex-row lg:items-start lg:justify-center gap-8 relative">
      <NotificationsPanel />
      <UserHeader />
      
      {/* --- ЛЕВАЯ КОЛОНКА: ИГРА --- */}
      <div className="flex-1 flex flex-col items-center w-full max-w-3xl">
          
          {/* Шапка */}
          <div className="w-full flex justify-between items-center mb-4">
            <h1 className="text-xl font-bold text-slate-400 flex items-center gap-2">
              CHGKA <span className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`}/>
            </h1>
            {/* Индикатор фазы для админа */}
            {myRole === 'admin' && (
              <div className="text-xs text-slate-500 uppercase font-bold">
                Phase: {phase}
              </div>
            )}
          </div>

          {/* Табло */}
          <ScoreBoard score={gameState?.score} />

          {/* Стол */}
          <div className="w-full flex justify-center mb-4">
             <GameTable
               gameState={gameState}
               isAdmin={myRole === 'admin'}
               questionTitles={packInfo?.question_titles || null}
             />
          </div>
      </div>

      {/* --- ПРАВАЯ КОЛОНКА: АДМИНКА (только для админов) --- */}
      {myRole === 'admin' && (
        <div className="w-full lg:w-[600px] flex flex-col gap-4">
            
            {/* Панель управления */}
            <div className="bg-slate-800 p-4 rounded-xl shadow-2xl border border-slate-700 flex flex-col gap-6 sticky top-4">
                
                {/* Header */}
                <div className="flex justify-between items-center border-b border-slate-700 pb-2">
                    <span className="text-sm font-bold text-slate-400 uppercase">Admin Panel</span>
                    <div className="flex gap-2">
                      <button 
                          onClick={handleSilenceClick}
                          className="text-[10px] bg-red-900 hover:bg-red-800 text-white py-1 px-2 rounded font-bold uppercase tracking-wider"
                      >
                          Silence
                      </button>
                      <button 
                          onClick={handleResetClick}
                          className="text-[10px] bg-slate-700 hover:bg-slate-600 text-slate-300 py-1 px-2 rounded font-bold uppercase tracking-wider"
                      >
                          Reset
                      </button>
                    </div>
                </div>

                {/* --- СЕКЦИЯ ВОЛЧКА --- */}
                <div className="flex flex-col gap-3 border border-slate-700 p-3 rounded bg-slate-900/30">
                   <div className="text-xs text-yellow-600 uppercase font-bold tracking-widest text-center">Управление Волчком</div>
                   
                   {/* Большая кнопка Случайно */}
                   <button 
                      onClick={handleSpinRandom}
                      disabled={gameState?.is_spinning || !isPreRound}
                      className="w-full bg-yellow-500 hover:bg-yellow-400 disabled:opacity-50 disabled:cursor-not-allowed text-black font-black py-3 rounded-lg text-lg shadow active:scale-[0.98] transition-all uppercase tracking-wider"
                   >
                      {gameState?.is_spinning ? 'Вращаем...' : '🎲 Случайный выбор'}
                   </button>

                   <div className="text-[10px] text-slate-500 text-center uppercase font-bold mt-1">Или выбрать сектор</div>
                   
                   {/* Сетка секторов */}
                   <div className="grid grid-cols-7 gap-1">
                      {Array.from({ length: 13 }, (_, i) => i + 1).map(sectorId => {
                          const isUsed = usedQuestions.includes(sectorId);
                          return (
                              <button
                                  key={sectorId}
                                  onClick={() => handleSpinForced(sectorId)}
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
                          )
                      })}
                   </div>
                </div>

                {/* --- СЕКЦИЯ ИГРЫ --- */}
                <div className="grid grid-cols-3 gap-4 items-center border border-slate-700 p-3 rounded bg-slate-900/30">
                   {/* Кнопка перехода фазы */}
                   <div className="col-span-2">
                      {isQuestionReading && (
                        <button
                          onClick={handleStartDiscussion}
                          className="w-full bg-blue-700 hover:bg-blue-600 text-white py-3 rounded shadow active:scale-95 transition-all font-bold uppercase tracking-wider text-xs"
                        >
                          Начать обсуждение
                        </button>
                      )}
                      {isDiscussion && (
                        <button
                          onClick={handleTeamAnswer}
                          className="w-full bg-purple-700 hover:bg-purple-600 text-white py-3 rounded shadow active:scale-95 transition-all font-bold uppercase tracking-wider text-xs"
                        >
                          Ответ команды
                        </button>
                      )}
                      {isTeamAnswer && (
                        <div className="flex gap-2">
                          <button 
                              onClick={handleScoreZnatoki}
                              className="flex-1 bg-green-800 hover:bg-green-700 text-white py-2 rounded shadow active:scale-95 transition-all flex flex-col items-center"
                          >
                              <span className="text-[10px] uppercase opacity-70 font-bold">Знатоки</span>
                              <span className="text-xl font-bold leading-none">+1</span>
                          </button>
                          
                          <button 
                              onClick={handleScoreTV}
                              className="flex-1 bg-red-800 hover:bg-red-700 text-white py-2 rounded shadow active:scale-95 transition-all flex flex-col items-center"
                          >
                              <span className="text-[10px] uppercase opacity-70 font-bold">Телезрители</span>
                              <span className="text-xl font-bold leading-none">+1</span>
                          </button>
                        </div>
                      )}
                      {isPreRound && (
                        <div className="text-xs text-slate-500 font-bold uppercase tracking-widest">
                          Фаза: ожидание вращения
                        </div>
                      )}
                   </div>

                   {/* Гонг */}
                   <button 
                      onClick={handleGongClick}
                      className="h-full bg-slate-700 hover:bg-slate-600 text-white font-bold rounded shadow active:scale-95 transition-all flex flex-col items-center justify-center"
                   >
                      <span className="text-2xl">🔔</span>
                      <span className="text-[10px] uppercase">Гонг</span>
                   </button>
                </div>

                {/* Звук */}
                <div className="bg-slate-900/50 p-3 rounded-lg flex items-center gap-3">
                   <span className="text-xs text-slate-500 uppercase font-bold">Vol</span>
                   <input 
                      type="range" 
                      min="0" max="1" step="0.05"
                      value={gameSettings?.volume ?? 1.0}
                      onChange={handleVolumeChange}
                      className="flex-1 h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-yellow-500"
                  />
                  <span className="text-xs text-slate-400 w-8 text-right">{Math.round((gameSettings?.volume ?? 1.0) * 100)}%</span>
                </div>

                {/* Список игроков */}
                <div className="border border-slate-700 p-3 rounded bg-slate-900/30">
                   <div className="text-xs text-slate-500 uppercase font-bold tracking-widest mb-2">
                     Игроки ({players.filter(p => p.role !== 'admin' && !p.pending).length})
                     {players.filter(p => p.pending).length > 0 && (
                       <span className="text-yellow-500 ml-2">
                         + {players.filter(p => p.pending).length} ожидают
                       </span>
                     )}
                   </div>
                   <div className="space-y-1 max-h-40 overflow-y-auto">
                      {players.filter(p => p.role !== 'admin').length === 0 ? (
                          <div className="text-xs text-slate-600 italic">Нет игроков</div>
                      ) : (
                          players.filter(p => p.role !== 'admin').map((player, idx) => (
                              <div 
                                key={idx} 
                                className={`flex items-center justify-between px-2 py-1.5 rounded ${
                                  player.pending 
                                    ? 'bg-yellow-900/30 border border-yellow-700/50' 
                                    : 'bg-slate-800'
                                }`}
                              >
                                  <div className="flex items-center gap-2">
                                      <span className={`w-2 h-2 rounded-full ${
                                        player.pending ? 'bg-yellow-500 animate-pulse' :
                                        player.online ? 'bg-green-500' : 'bg-slate-600'
                                      }`} />
                                      <span className={`text-sm ${
                                        player.pending ? 'text-yellow-300' :
                                        player.online ? 'text-white' : 'text-slate-500'
                                      }`}>
                                          {player.name}
                                          {player.pending && <span className="text-xs ml-1">(ждёт)</span>}
                                      </span>
                                  </div>
                                  <div className="flex gap-1">
                                    {player.pending && (
                                      <button
                                          onClick={() => handleApprovePlayer(player.name)}
                                          className="text-[10px] bg-green-700 hover:bg-green-600 text-white px-2 py-0.5 rounded font-bold uppercase transition-colors"
                                      >
                                          Пустить
                                      </button>
                                    )}
                                    <button
                                        onClick={() => handleKickPlayer(player.name)}
                                        className="text-[10px] bg-red-900/50 hover:bg-red-800 text-red-300 hover:text-white px-2 py-0.5 rounded font-bold uppercase transition-colors"
                                    >
                                        Kick
                                    </button>
                                  </div>
                              </div>
                          ))
                      )}
                   </div>
                </div>

                {/* Логи */}
                <div className="pt-2 border-t border-slate-700">
                    <GameLog logs={gameState?.logs} />
                </div>
            </div>

        </div>
      )}

    </div>
  )
}

export default App
