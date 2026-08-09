import { useEffect, useState } from 'react';

import {
  formatJournalTimestamp,
  gameModeLabel,
  gameScoreLabel,
  gameStatusLabel,
  questionHistoryLabel,
} from '../gameHistory';
import { responseMessage } from '../uiText';

const modeButtonClass = 'flex-1 rounded px-2 py-2 text-[10px] font-black uppercase tracking-wider transition-colors disabled:opacity-40';

export function GameHistoryPanel({ socket, addNotification, initiallyOpen = false }) {
  const [isOpen, setIsOpen] = useState(initiallyOpen);
  const [history, setHistory] = useState(null);
  const [detail, setDetail] = useState(null);
  const [loading, setLoading] = useState(true);

  const warn = (response, fallback) => {
    addNotification?.({
      type: 'warning',
      message: responseMessage(response, fallback),
    });
  };

  const loadHistory = () => {
    setLoading(true);
    socket.emit('admin_get_game_history', null, (response) => {
      setLoading(false);
      if (!response?.ok) {
        warn(response, 'Не удалось загрузить историю игр');
        return;
      }
      setHistory(response.history);
    });
  };

  useEffect(() => {
    loadHistory();
  }, []);

  const selectSession = (sessionId) => {
    socket.emit('admin_get_game_session', { session_id: sessionId }, (response) => {
      if (!response?.ok) {
        warn(response, 'Не удалось загрузить журнал игры');
        return;
      }
      setDetail(response.detail);
    });
  };

  const setCurrentMode = (mode) => {
    socket.emit('admin_set_current_game_mode', { mode }, (response) => {
      if (!response?.ok) {
        warn(response, 'Не удалось изменить режим игры');
        return;
      }
      setHistory(response.history);
    });
  };

  const togglePastMode = (session) => {
    const mode = session.mode === 'regular' ? 'debug' : 'regular';
    if (!confirm(`Пометить эту игру как «${gameModeLabel(mode).toLowerCase()}»?`)) return;
    socket.emit(
      'admin_set_game_session_mode',
      { session_id: session.id, mode },
      (response) => {
        if (!response?.ok) {
          warn(response, 'Не удалось изменить режим сохранённой игры');
          return;
        }
        setHistory(response.history);
        if (detail?.session?.id === session.id) {
          selectSession(session.id);
        }
      },
    );
  };

  const currentMode = history?.current_mode || null;
  const sessions = history?.sessions || [];
  const usedQuestions = history?.used_questions || [];

  return (
    <div className="rounded-lg border border-indigo-700/70 bg-indigo-950/20">
      <div className="p-3">
        <div className="mb-2 text-[10px] font-bold uppercase tracking-widest text-indigo-300">
          Режим текущей игры
        </div>
        <div className="grid grid-cols-2 gap-2">
          <button
            type="button"
            disabled={loading}
            onClick={() => setCurrentMode('regular')}
            className={`${modeButtonClass} ${currentMode === 'regular' ? 'bg-emerald-700 text-white ring-1 ring-emerald-400' : 'bg-slate-800 text-slate-400 hover:bg-slate-700'}`}
          >
            Обычная
          </button>
          <button
            type="button"
            disabled={loading}
            onClick={() => setCurrentMode('debug')}
            className={`${modeButtonClass} ${currentMode === 'debug' ? 'bg-amber-700 text-white ring-1 ring-amber-400' : 'bg-slate-800 text-slate-400 hover:bg-slate-700'}`}
          >
            Тестовая
          </button>
        </div>
        <p className="mt-2 text-[10px] leading-relaxed text-slate-500">
          В общую историю сыгранных вопросов входят только обычные игры.
        </p>
      </div>

      <button
        type="button"
        onClick={() => setIsOpen((current) => !current)}
        className="flex w-full items-center justify-between border-t border-indigo-800/60 px-3 py-2 text-xs font-bold uppercase tracking-widest text-indigo-300 hover:bg-indigo-950/30"
      >
        <span>История игр</span>
        <span>{isOpen ? '▲' : '▼'}</span>
      </button>

      {isOpen && (
        <div className="flex flex-col gap-4 border-t border-indigo-800/60 p-3">
          <div className="flex items-center justify-between text-[10px] text-slate-500">
            <span>Сыграно уникальных вопросов: {usedQuestions.length}</span>
            <button type="button" onClick={loadHistory} className="font-bold uppercase text-indigo-300 hover:text-indigo-200">
              Обновить
            </button>
          </div>

          {usedQuestions.length > 0 && (
            <details className="rounded border border-slate-700 bg-slate-950/30 p-2">
              <summary className="cursor-pointer text-[10px] font-bold uppercase tracking-wider text-slate-400">
                Сыгранные вопросы обычных игр
              </summary>
              <div className="mt-2 max-h-40 space-y-1 overflow-y-auto text-xs text-slate-300">
                {usedQuestions.map((question) => (
                  <div key={question.question_id} className="border-b border-slate-800 pb-1 last:border-0">
                    {questionHistoryLabel(question)}
                    {question.open_count > 1 && <span className="ml-1 text-slate-500">×{question.open_count}</span>}
                  </div>
                ))}
              </div>
            </details>
          )}

          <div>
            <div className="mb-2 text-[10px] font-bold uppercase tracking-widest text-slate-500">
              Сессии
            </div>
            <div className="max-h-48 space-y-2 overflow-y-auto">
              {sessions.length === 0 && <div className="text-xs italic text-slate-600">История пока пуста</div>}
              {sessions.map((session) => (
                <div
                  key={session.id}
                  className={`rounded border p-2 ${session.id === history?.current_session?.id ? 'border-indigo-500 bg-indigo-950/30' : 'border-slate-700 bg-slate-900/40'}`}
                >
                  <button type="button" onClick={() => selectSession(session.id)} className="w-full text-left">
                    <div className="flex items-start justify-between gap-2">
                      <span className="text-xs font-bold text-white">{formatJournalTimestamp(session.created_at)}</span>
                      <span className={session.mode === 'regular' ? 'text-[10px] font-bold text-emerald-400' : 'text-[10px] font-bold text-amber-400'}>
                        {gameModeLabel(session.mode)}
                      </span>
                    </div>
                    <div className="mt-1 text-[10px] text-slate-500">
                      {gameStatusLabel(session.status)} · счёт {gameScoreLabel(session.score)} · вопросов {session.opened_questions}
                    </div>
                  </button>
                  <button
                    type="button"
                    onClick={() => togglePastMode(session)}
                    className="mt-2 text-[9px] font-bold uppercase tracking-wider text-slate-500 hover:text-indigo-300"
                  >
                    Сменить на {session.mode === 'regular' ? 'тестовую' : 'обычную'}
                  </button>
                </div>
              ))}
            </div>
          </div>

          {detail && (
            <div className="rounded border border-slate-700 bg-black/30 p-2">
              <div className="mb-2 flex items-center justify-between gap-2">
                <span className="text-[10px] font-bold uppercase tracking-widest text-slate-400">
                  Журнал {formatJournalTimestamp(detail.session.created_at)}
                </span>
                <button type="button" onClick={() => setDetail(null)} className="text-xs text-slate-500 hover:text-white">×</button>
              </div>
              {detail.opened_questions.length > 0 && (
                <div className="mb-3 rounded bg-slate-900/60 p-2">
                  <div className="mb-1 text-[9px] font-bold uppercase text-slate-500">Открытые вопросы</div>
                  {detail.opened_questions.map((question) => (
                    <div key={question.question_id} className="text-[11px] text-slate-300">
                      {questionHistoryLabel(question)}
                    </div>
                  ))}
                </div>
              )}
              <div className="max-h-64 space-y-1 overflow-y-auto font-mono text-[10px] text-green-300">
                {detail.events.map((event) => (
                  <div key={event.sequence_number} className="border-b border-slate-800 pb-1 last:border-0">
                    <span className="mr-2 text-slate-600">{formatJournalTimestamp(event.occurred_at, { withDate: false })}</span>
                    {event.display_message}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
