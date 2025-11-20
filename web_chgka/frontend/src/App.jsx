import { useState, useEffect } from 'react'
import io from 'socket.io-client'
import { GameTable } from './components/GameTable'
import { useGameSound } from './hooks/useGameSound'

// Подключаемся к бэкенду. 
const socket = io(import.meta.env.DEV ? 'http://localhost:8000' : '/', {
  transports: ['websocket']
})

function App() {
  const [gameState, setGameState] = useState(null)
  const [isConnected, setIsConnected] = useState(socket.connected)
  
  // Подключаем звук
  const { playSound } = useGameSound(gameState);

  useEffect(() => {
    function onConnect() { setIsConnected(true) }
    function onDisconnect() { setIsConnected(false) }
    function onStateUpdate(newState) { setGameState(newState) }
    function onPlaySound(data) { playSound(data.sound); }

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

  return (
    <div className="min-h-screen bg-slate-900 text-white flex flex-col items-center justify-center p-4">
      <h1 className="text-2xl md:text-3xl font-bold mb-4 text-center">
        Что? Где? Когда?
        <span className={`ml-3 inline-block w-3 h-3 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`} title={isConnected ? "Online" : "Offline"}/>
      </h1>
      
      {/* Панель управления */}
      <div className="flex gap-4 mb-6 flex-wrap justify-center">
        <button 
          onClick={handleSpinClick}
          disabled={gameState?.is_spinning}
          className="bg-yellow-500 hover:bg-yellow-600 disabled:opacity-50 text-black font-bold py-2 px-6 rounded text-lg transition-all shadow-lg active:translate-y-1"
        >
          {gameState?.is_spinning ? '...' : 'ВРАЩАТЬ'}
        </button>

        <button 
          onClick={handleGongClick}
          className="bg-red-600 hover:bg-red-700 text-white font-bold py-2 px-6 rounded text-lg transition-all shadow-lg active:translate-y-1"
        >
          ГОНГ
        </button>
        
        <button 
          onClick={handleResetClick}
          className="bg-gray-700 hover:bg-gray-600 text-white font-bold py-2 px-4 rounded text-sm transition-all shadow-lg active:translate-y-1"
        >
          Сброс
        </button>
      </div>

      {/* Игровой стол */}
      <div className="w-full max-w-[80vh] flex justify-center">
            <GameTable gameState={gameState} />
      </div>
    </div>
  )
}

export default App
