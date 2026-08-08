import { useEffect, useState } from 'react';
import { ENTRYPOINT_ADMIN } from '../entrypoint';


function PlayerLoginForm({ socket }) {
  const [name, setName] = useState('');
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    function onJoinFailed(data) {
      setIsSubmitting(false);
      setError(data?.message || 'Ошибка подключения');
    }

    socket.on('join_failed', onJoinFailed);
    return () => socket.off('join_failed', onJoinFailed);
  }, [socket]);

  const handleSubmit = (event) => {
    event.preventDefault();
    const normalizedName = name.trim();
    if (!normalizedName) {
      setError('Введите имя');
      return;
    }

    setIsSubmitting(true);
    setError('');
    socket.emit('join_game', { name: normalizedName });
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label htmlFor="player-name" className="sr-only">
          Ваше имя
        </label>
        <input
          id="player-name"
          type="text"
          value={name}
          onChange={(event) => {
            setName(event.target.value);
            setError('');
          }}
          disabled={isSubmitting}
          className="w-full rounded-lg border border-slate-600 bg-slate-900 px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-yellow-500 disabled:opacity-50"
          placeholder="Введите имя"
          maxLength={50}
          autoComplete="name"
          autoFocus
        />
        {error && <p className="mt-2 text-sm text-red-400">{error}</p>}
      </div>

      <button
        type="submit"
        disabled={isSubmitting || !name.trim()}
        className="w-full rounded-lg bg-yellow-500 py-3 text-lg font-black uppercase tracking-wider text-black shadow-lg transition-all hover:bg-yellow-400 active:scale-95 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {isSubmitting ? 'Подключение...' : 'Присоединиться'}
      </button>
    </form>
  );
}


function AdminLoginForm({ socket }) {
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    function onAuthSuccess() {
      setIsSubmitting(false);
      setPassword('');
      setError('');
    }

    function onAuthFailed(data) {
      setIsSubmitting(false);
      setError(data?.message || 'Неверный пароль');
    }

    socket.on('auth_success', onAuthSuccess);
    socket.on('auth_failed', onAuthFailed);
    return () => {
      socket.off('auth_success', onAuthSuccess);
      socket.off('auth_failed', onAuthFailed);
    };
  }, [socket]);

  const handleSubmit = (event) => {
    event.preventDefault();
    const normalizedPassword = password.trim();
    if (!normalizedPassword) {
      setError('Введите пароль');
      return;
    }

    setIsSubmitting(true);
    setError('');
    socket.emit('authenticate_admin', { password: normalizedPassword });
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label htmlFor="admin-password" className="sr-only">
          Пароль ведущего
        </label>
        <input
          id="admin-password"
          type="password"
          value={password}
          onChange={(event) => {
            setPassword(event.target.value);
            setError('');
          }}
          disabled={isSubmitting}
          className="w-full rounded-lg border border-slate-600 bg-slate-900 px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-yellow-500 disabled:opacity-50"
          placeholder="Введите пароль"
          autoComplete="current-password"
          autoFocus
        />
        {error && <p className="mt-2 text-sm text-red-400">{error}</p>}
      </div>

      <button
        type="submit"
        disabled={isSubmitting || !password.trim()}
        className="w-full rounded-lg bg-yellow-500 py-3 text-lg font-black uppercase tracking-wider text-black shadow-lg transition-all hover:bg-yellow-400 active:scale-95 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {isSubmitting ? 'Проверяем...' : 'Войти'}
      </button>
    </form>
  );
}


export function LoginScreen({ socket, entrypoint, sessionNotice = '' }) {
  const isAdmin = entrypoint === ENTRYPOINT_ADMIN;

  return (
    <div
      className={`flex min-h-screen items-center justify-center p-4 text-white ${
        isAdmin ? 'bg-indigo-950' : 'bg-slate-900'
      }`}
    >
      <div
        className={`w-full max-w-md rounded-xl border p-8 shadow-2xl ${
          isAdmin
            ? 'border-indigo-700 bg-indigo-900/80'
            : 'border-slate-700 bg-slate-800'
        }`}
      >
        <h1 className="mb-8 text-center text-3xl font-bold text-yellow-500">
          Что? Где? Когда?
        </h1>

        {sessionNotice && (
          <p
            role="status"
            className="mb-6 rounded-lg border border-yellow-700 bg-yellow-950/60 px-4 py-3 text-sm text-yellow-200"
          >
            {sessionNotice}
          </p>
        )}

        {isAdmin
          ? <AdminLoginForm socket={socket} />
          : <PlayerLoginForm socket={socket} />}
      </div>
    </div>
  );
}
