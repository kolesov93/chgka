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
  
  // Подключаем звук (он сам следит за gameState.is_spinning)
  const { playSound } = useGameSound(gameState);

  useEffect(() => {
    function onConnect() {
      setIsConnected(true)
    }

    function onDisconnect() {
      setIsConnected(false)
    }

    function onStateUpdate(newState) {
      console.log("State updated:", newState)
      setGameState(newState)
    }

    function onPlaySound(data) {
        console.log("Playing sound:", data);
        playSound(data.sound);
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
  // playSound в deps не добавляем, чтобы не провоцировать переподписки, 
  // в реальном проекте обернули бы в useCallback

  const handleSpinClick = () => {
    socket.emit('admin_spin')
  }

  const handleGongClick = () => {
    socket.emit('admin_sound', { sound: 'gong' })
  }

  const handleResetClick = () => {
    if (confirm('Точно сбросить игру?')) {
      socket.emit('admin_reset')
    }
  }

  return (
    <div className="min-h-screen bg-slate-900 text-white flex flex-col items-center justify-center p-4">
      <h1 className="text-3xl font-bold mb-4">
        Что? Где? Когда? - Web
      </h1>
      
      <div className={`mb-4 px-4 py-2 rounded ${isConnected ? 'bg-green-600' : 'bg-red-600'}`}>
        Status: {isConnected ? 'Connected' : 'Disconnected'}
      </div>

      {/* Панель управления (видна всем, по-хорошему надо скрыть для обычных игроков) */}
      <div className="flex gap-4 mb-8 flex-wrap justify-center">
        <button 
          onClick={handleSpinClick}
          disabled={gameState?.is_spinning}
          className="bg-yellow-500 hover:bg-yellow-600 disabled:opacity-50 text-black font-bold py-2 px-6 rounded text-lg transition-all shadow-lg active:translate-y-1"
        >
          {gameState?.is_spinning ? 'Вращаем...' : 'КРУТИТЬ ВОЛЧОК'}
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
      <GameTable gameState={gameState} />
    </div>
  )
}

export default App
