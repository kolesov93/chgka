import { useEffect, useState } from 'react';
import { introHostControlView } from '../intro';
import { socket } from '../socket';

export function IntroHostControls({ intro }) {
  const [nowMs, setNowMs] = useState(() => Date.now());

  useEffect(() => {
    if (!intro) return undefined;
    setNowMs(Date.now());
    const interval = setInterval(() => setNowMs(Date.now()), 250);
    return () => clearInterval(interval);
  }, [intro?.started_at_ms]);

  const control = introHostControlView(intro, nowMs);

  return (
    <div className="flex min-h-56 flex-col gap-3 rounded border border-blue-800/60 bg-blue-950/20 p-3">
      <div className="text-center text-xs font-bold uppercase tracking-widest text-blue-300">
        Управление вступлением
      </div>

      <div className="grid min-h-14 grid-cols-2 gap-3 rounded border border-slate-800 bg-slate-950/40 px-3 py-2">
        <div className="min-w-0">
          <div className="text-[10px] font-bold uppercase tracking-widest text-slate-500">
            Сейчас
          </div>
          <div className="truncate text-sm font-bold text-white" title={control.slideLabel}>
            {control.slideLabel}
          </div>
        </div>
        <div className="text-right">
          <div className="text-[10px] font-bold uppercase tracking-widest text-slate-500">
            Музыка
          </div>
          <div className="font-black tabular-nums text-yellow-400" aria-live="off">
            {control.musicStatus}
          </div>
        </div>
      </div>

      <div className="mt-auto grid gap-2">
        <button
          type="button"
          onClick={() => socket.emit('admin_start_intro_music')}
          disabled={!control.canStartMusic}
          className="w-full rounded-lg bg-amber-700 py-3 text-xs font-bold uppercase tracking-wider text-white shadow transition-all hover:bg-amber-600 active:scale-[0.98] disabled:cursor-default disabled:bg-slate-700 disabled:text-slate-400 disabled:opacity-100"
        >
          {control.musicActionLabel}
        </button>
        <button
          type="button"
          onClick={() => socket.emit('admin_advance_intro', { expected_slide: control.slideIndex })}
          disabled={!control.canAdvance}
          className="w-full rounded-lg bg-blue-700 py-3 text-xs font-bold uppercase tracking-wider text-white shadow transition-all hover:bg-blue-600 active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-50"
        >
          {control.nextStepLabel}
        </button>
      </div>
    </div>
  );
}
