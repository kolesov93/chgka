import { useState, useEffect } from 'react'
import io from 'socket.io-client'
import { GameTable } from './components/GameTable'
import { ScoreBoard } from './components/ScoreBoard'
import { GameLog } from './components/GameLog'
import { useGameSound } from './hooks/useGameSound'

const socket = io(import.meta.env.DEV ? 'http://localhost:8000' : '/', {
  transports: ['websocket']
})

function App() {
  const [gameState, setGameState] = useState(null)
  const [isConnected, setIsConnected] = useState(socket.connected)
  
  const { playSound, stopAllSounds, masterVolume, setMasterVolume } = useGameSound(gameState);

  useEffect(() => {
    function onConnect() { setIsConnected(true) }
    function onDisconnect() { setIsConnected(false) }
    function onStateUpdate(newState) { setGameState(newState) }
    
    function onPlaySound(data) { 
        if (data.category) {
            playSound(data.category);
        } else {
            playSound(data.sound); 
        }
    }

    socket.on('connect', onConnect)
    socket.on('disconnect', onDisconnect)
    socket.on('state_update', onStateUpdate)
    socket.on('play_sound', onPlaySound)

    return () => {
      socket.off('connect', onConnect)
      socket.off('disconnect', onDisconnect)
      socket.off('state_update', onStateUpdate)
      socket.off('play_sound', onPlaySound)
    }
  }, []) 

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
  
  const handleScoreZnatoki = () => socket.emit('admin_score', { winner: 'znatoki' })
  const handleScoreTV = () => socket.emit('admin_score', { winner: 'tv' })

  const usedQuestions = gameState?.used_questions || [];

  return (
    <div className="min-h-screen bg-slate-900 text-white p-4 flex flex-col lg:flex-row lg:items-start lg:justify-center gap-8">
      
      {/* --- ЛЕВАЯ КОЛОНКА: ИГРА --- */}
      <div className="flex-1 flex flex-col items-center w-full max-w-3xl">
          
          {/* Шапка */}
          <div className="w-full flex justify-between items-center mb-4">
            <h1 className="text-xl font-bold text-slate-400 flex items-center gap-2">
              CHGKA <span className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`}/>
            </h1>
          </div>

          {/* Табло */}
          <ScoreBoard score={gameState?.score} />

          {/* Стол */}
          <div className="w-full flex justify-center mb-4">
             <GameTable gameState={gameState} />
          </div>
      </div>

      {/* --- ПРАВАЯ КОЛОНКА: АДМИНКА --- */}
      <div className="w-full lg:w-[600px] flex flex-col gap-4">
          
          {/* Панель управления */}
          <div className="bg-slate-800 p-4 rounded-xl shadow-2xl border border-slate-700 flex flex-col gap-6 sticky top-4">
              
              {/* Header */}
              <div className="flex justify-between items-center border-b border-slate-700 pb-2">
                  <span className="text-sm font-bold text-slate-400 uppercase">Admin Panel</span>
                  <div className="flex gap-2">
                    <button 
                        onClick={stopAllSounds}
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
                    disabled={gameState?.is_spinning}
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
                                disabled={gameState?.is_spinning || isUsed}
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
                 {/* Очки */}
                 <div className="col-span-2 flex gap-2">
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
                    value={masterVolume}
                    onChange={(e) => setMasterVolume(parseFloat(e.target.value))}
                    className="flex-1 h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-yellow-500"
                />
                <span className="text-xs text-slate-400 w-8 text-right">{Math.round(masterVolume * 100)}%</span>
              </div>

              {/* Логи */}
              <div className="pt-2 border-t border-slate-700">
                  <GameLog logs={gameState?.logs} />
              </div>
          </div>

      </div>

    </div>
  )
}

export default App
