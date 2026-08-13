import { useEffect, useState } from 'react';
import {
  ENTRYPOINT_ADMIN_HISTORY,
  entrypointLoginSubtitle,
  isAdminEntrypoint,
} from '../entrypoint';
import { MAX_PARTICIPANTS_PER_GROUP } from '../participants';


function PlayerLoginForm({ socket }) {
  const [names, setNames] = useState(['']);
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
    const normalizedNames = names.map((name) => name.trim());
    if (normalizedNames.some((name) => !name)) {
      setError('Введите имя каждого участника');
      return;
    }

    setIsSubmitting(true);
    setError('');
    socket.emit('join_game', { participants: normalizedNames });
  };

  const updateName = (index, value) => {
    setNames((current) => current.map((name, itemIndex) => (
      itemIndex === index ? value : name
    )));
    setError('');
  };

  const addParticipant = () => {
    setNames((current) => (
      current.length >= MAX_PARTICIPANTS_PER_GROUP ? current : [...current, '']
    ));
    setError('');
  };

  const removeParticipant = (index) => {
    setNames((current) => current.filter((_name, itemIndex) => itemIndex !== index));
    setError('');
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="space-y-2">
        {names.map((name, index) => (
          <div key={index} className="flex gap-2">
            <label htmlFor={`participant-name-${index}`} className="sr-only">
              Имя участника {index + 1}
            </label>
            <input
              id={`participant-name-${index}`}
              type="text"
              value={name}
              onChange={(event) => updateName(index, event.target.value)}
              disabled={isSubmitting}
              className="min-w-0 flex-1 rounded-lg border border-slate-600 bg-slate-900 px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-yellow-500 disabled:opacity-50"
              placeholder={index === 0 ? 'Введите имя' : 'Имя ещё одного участника'}
              maxLength={50}
              autoComplete={index === 0 ? 'name' : 'off'}
              autoFocus={index === 0}
            />
            {names.length > 1 && (
              <button
                type="button"
                onClick={() => removeParticipant(index)}
                disabled={isSubmitting}
                aria-label={`Удалить участника ${index + 1}`}
                className="w-11 rounded-lg border border-slate-600 bg-slate-800 text-xl text-slate-400 hover:border-red-700 hover:text-red-300 disabled:opacity-50"
              >
                ×
              </button>
            )}
          </div>
        ))}
        <button
          type="button"
          onClick={addParticipant}
          disabled={isSubmitting || names.length >= MAX_PARTICIPANTS_PER_GROUP}
          className="flex w-full items-center justify-center gap-2 rounded-lg border border-dashed border-slate-600 py-2 text-sm font-bold text-slate-400 transition-colors hover:border-yellow-600 hover:text-yellow-400 disabled:cursor-not-allowed disabled:opacity-40"
        >
          <span className="text-xl leading-none">+</span>
          Добавить участника
        </button>
        {error && <p className="mt-2 text-sm text-red-400">{error}</p>}
      </div>

      <button
        type="submit"
        disabled={isSubmitting || names.some((name) => !name.trim())}
        className="w-full rounded-lg bg-yellow-500 py-3 text-lg font-black uppercase tracking-wider text-black shadow-lg transition-all hover:bg-yellow-400 active:scale-95 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {isSubmitting ? 'Подключение...' : 'Присоединиться'}
      </button>
    </form>
  );
}


function AdminLoginForm({ socket, historyOnly = false }) {
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
    socket.emit('authenticate_admin', {
      password: normalizedPassword,
      ...(historyOnly ? { client_kind: 'history' } : {}),
    });
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
  const isAdmin = isAdminEntrypoint(entrypoint);
  const isHistory = entrypoint === ENTRYPOINT_ADMIN_HISTORY;
  const subtitle = entrypointLoginSubtitle(entrypoint);

  return (
    <div
      className={`flex min-h-screen items-center justify-center p-4 text-white ${
        isHistory ? 'bg-teal-950' : isAdmin ? 'bg-indigo-950' : 'bg-slate-900'
      }`}
    >
      <div
        className={`w-full max-w-md rounded-xl border p-8 shadow-2xl ${
          isHistory
            ? 'border-teal-700 bg-teal-900/80'
            : isAdmin
            ? 'border-indigo-700 bg-indigo-900/80'
            : 'border-slate-700 bg-slate-800'
        }`}
      >
        <h1 className={`${subtitle ? 'mb-1' : 'mb-8'} text-center text-3xl font-bold text-yellow-500`}>
          Что? Где? Когда?
        </h1>
        {subtitle && (
          <div
            className={`mb-8 text-center text-xs font-bold uppercase tracking-[0.2em] ${
              isHistory ? 'text-teal-200' : 'text-indigo-200'
            }`}
          >
            {subtitle}
          </div>
        )}

        {sessionNotice && (
          <p
            role="status"
            className="mb-6 rounded-lg border border-yellow-700 bg-yellow-950/60 px-4 py-3 text-sm text-yellow-200"
          >
            {sessionNotice}
          </p>
        )}

        {isAdmin
          ? (
              <AdminLoginForm
                socket={socket}
                historyOnly={entrypoint === ENTRYPOINT_ADMIN_HISTORY}
              />
            )
          : <PlayerLoginForm socket={socket} />}
      </div>
    </div>
  );
}
