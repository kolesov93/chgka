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
    <div className="min-h-screen bg-slate-900 text-white flex flex-col items-center justify-start p-4">
      
      {/* Заголовок */}
      <div className="w-full max-w-4xl flex justify-between items-center mb-4">
        <h1 className="text-xl font-bold text-slate-400 flex items-center gap-2">
          CHGKA <span className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`}/>
        </h1>
        <div className="flex gap-2">
            <button 
                onClick={stopAllSounds}
                className="text-xs bg-red-900 hover:bg-red-800 text-white py-1 px-3 rounded transition-all font-bold"
            >
                SILENCE
            </button>
            <button 
                onClick={handleResetClick}
                className="text-xs bg-slate-800 hover:bg-slate-700 text-slate-400 py-1 px-3 rounded transition-all"
            >
                RESET
            </button>
        </div>
      </div>

      {/* ТАБЛО */}
      <ScoreBoard score={gameState?.score} />

      {/* СТОЛ */}
      <div className="w-full max-w-[60vh] flex justify-center mb-8 relative">
            <GameTable gameState={gameState} />
      </div>

      {/* АДМИНКА */}
      <div className="w-full max-w-4xl bg-slate-800 p-4 rounded-xl shadow-2xl border border-slate-700 grid md:grid-cols-2 gap-6">
        
        {/* Левая колонка: Управление */}
        <div className="flex flex-col gap-6 justify-center">
            {/* Кнопки */}
            <div className="flex flex-wrap gap-4 justify-center items-center">
                <button 
                onClick={handleSpinClick}
                disabled={gameState?.is_spinning}
                className="bg-yellow-500 hover:bg-yellow-400 disabled:opacity-50 disabled:cursor-not-allowed text-black font-black py-3 px-6 rounded-lg text-xl shadow-lg active:scale-95 transition-all uppercase tracking-wider"
                >
                {gameState?.is_spinning ? '...' : 'ВРАЩАТЬ'}
                </button>

                <button 
                onClick={handleGongClick}
                className="bg-slate-700 hover:bg-slate-600 text-white font-bold py-3 px-4 rounded shadow active:scale-95 transition-all"
                >
                🔔
                </button>
            </div>
            
            {/* Очки */}
            <div className={`flex gap-2 justify-center transition-opacity ${gameState?.is_spinning ? 'opacity-30 pointer-events-none' : 'opacity-100'}`}>
                    <button 
                        onClick={handleScoreZnatoki}
                        className="bg-green-700 hover:bg-green-600 text-white font-bold py-2 px-4 rounded shadow active:scale-95 transition-all flex flex-col items-center w-32"
                    >
                        <span className="text-xs uppercase opacity-70">Знатоки</span>
                        <span className="text-xl">+1</span>
                    </button>
                    
                    <button 
                        onClick={handleScoreTV}
                        className="bg-red-700 hover:bg-red-600 text-white font-bold py-2 px-4 rounded shadow active:scale-95 transition-all flex flex-col items-center w-32"
                    >
                        <span className="text-xs uppercase opacity-70">Телезрители</span>
                        <span className="text-xl">+1</span>
                    </button>
            </div>

            {/* Звук */}
            <div className="flex items-center justify-center gap-3 bg-slate-900/50 p-2 rounded-lg">
                <span className="text-xs text-slate-400 uppercase font-bold">Vol</span>
                <input 
                    type="range" 
                    min="0" max="1" step="0.05"
                    value={masterVolume}
                    onChange={(e) => setMasterVolume(parseFloat(e.target.value))}
                    className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-yellow-500"
                />
                <span className="text-xs text-slate-400 w-8 text-right">{Math.round(masterVolume * 100)}%</span>
            </div>
        </div>

        {/* Правая колонка: Логи */}
        <div className="flex flex-col">
            <div className="text-xs text-slate-500 mb-1 uppercase font-bold">Game Log</div>
            <GameLog logs={gameState?.logs} />
        </div>

      </div>

    </div>
  )
}

export default App
