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

  const handleSpinClick = () => socket.emit('admin_spin')
  const handleGongClick = () => socket.emit('admin_sound', { sound: 'gong' })
  const handleResetClick = () => {
    if (confirm('Точно сбросить игру?')) socket.emit('admin_reset')
  }
  
  const handleScoreZnatoki = () => socket.emit('admin_score', { winner: 'znatoki' })
  const handleScoreTV = () => socket.emit('admin_score', { winner: 'tv' })

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

              {/* Кнопки действия */}
              <div className="flex flex-col gap-3">
                 <button 
                    onClick={handleSpinClick}
                    disabled={gameState?.is_spinning}
                    className="w-full bg-yellow-500 hover:bg-yellow-400 disabled:opacity-50 disabled:cursor-not-allowed text-black font-black py-4 rounded-lg text-xl shadow-lg active:scale-95 transition-all uppercase tracking-wider"
                 >
                    {gameState?.is_spinning ? 'Вращаем...' : 'ВРАЩАТЬ ВОЛЧОК'}
                 </button>

                 <button 
                    onClick={handleGongClick}
                    className="w-full bg-slate-700 hover:bg-slate-600 text-white font-bold py-2 rounded shadow active:scale-95 transition-all"
                 >
                    🔔 ГОНГ
                 </button>
              </div>

              {/* Очки */}
              <div className={`grid grid-cols-2 gap-2 transition-opacity ${gameState?.is_spinning ? 'opacity-30 pointer-events-none' : 'opacity-100'}`}>
                    <button 
                        onClick={handleScoreZnatoki}
                        className="bg-green-800 hover:bg-green-700 text-white py-2 rounded shadow active:scale-95 transition-all flex flex-col items-center"
                    >
                        <span className="text-[10px] uppercase opacity-70 font-bold">Знатоки</span>
                        <span className="text-2xl font-bold leading-none">+1</span>
                    </button>
                    
                    <button 
                        onClick={handleScoreTV}
                        className="bg-red-800 hover:bg-red-700 text-white py-2 rounded shadow active:scale-95 transition-all flex flex-col items-center"
                    >
                        <span className="text-[10px] uppercase opacity-70 font-bold">Телезрители</span>
                        <span className="text-2xl font-bold leading-none">+1</span>
                    </button>
              </div>

              {/* Звук */}
              <div className="mt-2 bg-slate-900/50 p-3 rounded-lg">
                 <div className="flex justify-between text-xs text-slate-500 mb-1 uppercase font-bold">
                     <span>Master Volume</span>
                     <span>{Math.round(masterVolume * 100)}%</span>
                 </div>
                 <input 
                    type="range" 
                    min="0" max="1" step="0.05"
                    value={masterVolume}
                    onChange={(e) => setMasterVolume(parseFloat(e.target.value))}
                    className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-yellow-500"
                />
              </div>

              {/* Логи */}
              <div className="mt-2 pt-4 border-t border-slate-700">
                  <div className="text-xs text-slate-500 mb-2 uppercase font-bold">Game Log</div>
                  <GameLog logs={gameState?.logs} />
              </div>
          </div>

      </div>

    </div>
  )
}

export default App
