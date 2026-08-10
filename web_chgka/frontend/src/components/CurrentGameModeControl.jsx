const buttonClass = 'flex-1 rounded px-2 py-2 text-[10px] font-black uppercase tracking-wider transition-colors disabled:opacity-40';

export function CurrentGameModeControl({ mode, loading, onModeChange }) {
  return (
    <div className="rounded border border-indigo-700/60 bg-indigo-950/20 p-3">
      <div className="mb-2 text-[10px] font-bold uppercase tracking-widest text-indigo-300">
        Режим текущей игры
      </div>
      <div className="grid grid-cols-2 gap-2">
        <button
          type="button"
          disabled={loading}
          onClick={() => onModeChange('regular')}
          className={`${buttonClass} ${mode === 'regular' ? 'bg-emerald-700 text-white ring-1 ring-emerald-400' : 'bg-slate-800 text-slate-400 hover:bg-slate-700'}`}
        >
          Обычная
        </button>
        <button
          type="button"
          disabled={loading}
          onClick={() => onModeChange('debug')}
          className={`${buttonClass} ${mode === 'debug' ? 'bg-amber-700 text-white ring-1 ring-amber-400' : 'bg-slate-800 text-slate-400 hover:bg-slate-700'}`}
        >
          Тестовая
        </button>
      </div>
      <p className="mt-2 text-[10px] leading-relaxed text-slate-500">
        В историю сыгранных вопросов входят только обычные игры.
      </p>
    </div>
  );
}
