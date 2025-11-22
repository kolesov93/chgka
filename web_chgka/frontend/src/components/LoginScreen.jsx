import { useState, useEffect } from 'react';

export function LoginScreen({ socket, gameState }) {
  const [name, setName] = useState('');
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isAdminMode, setIsAdminMode] = useState(false);
  const [adminPassword, setAdminPassword] = useState('');
  const [adminError, setAdminError] = useState('');
  const [isAdminSubmitting, setIsAdminSubmitting] = useState(false);

  const handleSubmit = (e) => {
    e.preventDefault();
    
    if (!name.trim()) {
      setError('Введите имя');
      return;
    }

    setIsSubmitting(true);
    setError('');
    
    socket.emit('join_game', { name: name.trim() });
  };

  const handleAdminLogin = (e) => {
    e.preventDefault();
    
    if (!adminPassword.trim()) {
      setAdminError('Введите пароль');
      return;
    }

    setAdminError('');
    setIsAdminSubmitting(true);
    socket.emit('authenticate_admin', { password: adminPassword.trim() });
  };

  // Слушаем ответ от сервера
  useEffect(() => {
    function onJoinFailedHandler(data) {
      setIsSubmitting(false);
      setError(data.message || 'Ошибка подключения');
    }

    socket.on('join_failed', onJoinFailedHandler);

    return () => {
      socket.off('join_failed', onJoinFailedHandler);
    };
  }, [socket]);

  // Следим за результатом админской аутентификации
  useEffect(() => {
    function onAuthSuccessHandler() {
      setIsAdminSubmitting(false);
      setAdminPassword('');
      setAdminError('');
      setIsAdminMode(false);
    }

    function onAuthFailedHandler(data) {
      setIsAdminSubmitting(false);
      setAdminError(data.message || 'Неверный пароль');
    }

    socket.on('auth_success', onAuthSuccessHandler);
    socket.on('auth_failed', onAuthFailedHandler);

    return () => {
      socket.off('auth_success', onAuthSuccessHandler);
      socket.off('auth_failed', onAuthFailedHandler);
    };
  }, [socket]);

  return (
    <div className="min-h-screen bg-slate-900 text-white flex items-center justify-center p-4">
      <div className="w-full max-w-md bg-slate-800 p-8 rounded-xl shadow-2xl border border-slate-700">
        <h1 className="text-3xl font-bold text-center mb-8 text-yellow-500">
          Что? Где? Когда?
        </h1>
        
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="player-name" className="block text-sm font-bold text-slate-400 mb-2 uppercase">
              Введите ваше имя
            </label>
            <input
              id="player-name"
              type="text"
              value={name}
              onChange={(e) => {
                setName(e.target.value);
                setError('');
              }}
              disabled={isSubmitting}
              className="w-full px-4 py-3 bg-slate-900 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-yellow-500 disabled:opacity-50"
              placeholder="Ваше имя"
              maxLength={50}
              autoFocus
            />
            {error && (
              <p className="mt-2 text-sm text-red-400">{error}</p>
            )}
          </div>

          <button
            type="submit"
            disabled={isSubmitting || !name.trim()}
            className="w-full bg-yellow-500 hover:bg-yellow-400 disabled:opacity-50 disabled:cursor-not-allowed text-black font-black py-3 rounded-lg text-lg shadow-lg active:scale-95 transition-all uppercase tracking-wider"
          >
            {isSubmitting ? 'Подключение...' : 'Присоединиться'}
          </button>
        </form>

        <div className="mt-8 border-t border-slate-700 pt-6">
          {!isAdminMode ? (
            <div className="text-center">
              <button
                type="button"
                onClick={() => {
                  setIsAdminMode(true);
                  setAdminError('');
                }}
                className="text-sm text-slate-400 hover:text-yellow-400 transition-colors font-bold uppercase tracking-wider"
              >
                Войти как ведущий
              </button>
            </div>
          ) : (
            <form onSubmit={handleAdminLogin} className="space-y-4">
              <div>
                <label htmlFor="admin-password" className="block text-sm font-bold text-slate-400 mb-2 uppercase">
                  Пароль ведущего
                </label>
                <input
                  id="admin-password"
                  type="password"
                  value={adminPassword}
                  onChange={(e) => {
                    setAdminPassword(e.target.value);
                    setAdminError('');
                  }}
                  disabled={isAdminSubmitting}
                  className="w-full px-4 py-3 bg-slate-900 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-yellow-500 disabled:opacity-50"
                  placeholder="Введите пароль"
                />
                {adminError && (
                  <p className="mt-2 text-sm text-red-400">{adminError}</p>
                )}
              </div>

              <div className="flex gap-2">
                <button
                  type="submit"
                  disabled={isAdminSubmitting || !adminPassword.trim()}
                  className="flex-1 bg-yellow-500 hover:bg-yellow-400 disabled:opacity-50 disabled:cursor-not-allowed text-black font-black py-3 rounded-lg text-lg shadow-lg active:scale-95 transition-all uppercase tracking-wider"
                >
                  {isAdminSubmitting ? 'Проверяем...' : 'Войти'}
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setIsAdminMode(false);
                    setAdminPassword('');
                    setAdminError('');
                  }}
                  disabled={isAdminSubmitting}
                  className="flex-1 bg-slate-700 hover:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed text-white font-bold py-3 rounded-lg text-lg shadow active:scale-95 transition-all uppercase tracking-wider"
                >
                  Отмена
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}

