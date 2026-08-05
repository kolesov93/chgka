import { useEffect, useState } from 'react';
import {
  formatIntroRemaining,
  introNextStepLabel,
  introRemainingMs,
  introSlideLabel,
  introSlideSource,
} from '../intro';
import { socket } from '../socket';

export function IntroScreen({ intro, isAdmin = false, introHtml = null }) {
  const [nowMs, setNowMs] = useState(() => Date.now());
  const slideIndex = intro?.slide_index;
  const slideSource = introSlideSource(slideIndex);

  useEffect(() => {
    if (!isAdmin || !intro) return undefined;
    setNowMs(Date.now());
    const interval = setInterval(() => setNowMs(Date.now()), 250);
    return () => clearInterval(interval);
  }, [isAdmin, intro?.started_at_ms]);

  const remaining = introRemainingMs(intro, nowMs);
  const musicStarted = Number.isFinite(intro?.started_at_ms);

  return (
    <div className="w-full flex flex-col gap-4">
      <div className="w-full rounded-xl border border-slate-700 bg-slate-950/40 p-3 shadow-2xl">
        {slideSource ? (
          <img
            src={slideSource}
            alt={introSlideLabel(slideIndex)}
            className="mx-auto max-h-[72vh] w-full rounded-lg object-contain"
          />
        ) : (
          <div className="flex min-h-72 items-center justify-center text-red-300">
            Intro-слайд недоступен
          </div>
        )}
      </div>

      {isAdmin && (
        <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(260px,0.7fr)]">
          <div className="rounded-xl border border-slate-700 bg-slate-800 p-4">
            <div className="mb-3 flex items-center justify-between gap-4">
              <div>
                <div className="text-[10px] font-bold uppercase tracking-widest text-slate-500">
                  Сейчас
                </div>
                <div className="font-bold text-white">{introSlideLabel(slideIndex)}</div>
              </div>
              <div className="text-right">
                <div className="text-[10px] font-bold uppercase tracking-widest text-slate-500">
                  Музыка
                </div>
                <div className="font-black tabular-nums text-yellow-400">
                  {musicStarted ? formatIntroRemaining(remaining) : 'Не запущена'}
                </div>
              </div>
            </div>
            {!musicStarted && (
              <button
                type="button"
                onClick={() => socket.emit('admin_start_intro_music')}
                className="mb-2 w-full rounded-lg bg-amber-700 py-3 text-xs font-bold uppercase tracking-wider text-white shadow transition-all hover:bg-amber-600 active:scale-[0.98]"
              >
                Запустить музыку
              </button>
            )}
            <button
              type="button"
              onClick={() => socket.emit('admin_advance_intro', { expected_slide: slideIndex })}
              disabled={!Number.isInteger(slideIndex)}
              className="w-full rounded-lg bg-blue-700 py-3 text-xs font-bold uppercase tracking-wider text-white shadow transition-all hover:bg-blue-600 active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-50"
            >
              {introNextStepLabel(slideIndex)}
            </button>
          </div>

          <div className="rounded-xl border border-slate-700 bg-slate-800 p-4">
            <div className="mb-3 text-[10px] font-bold uppercase tracking-widest text-slate-500">
              Текст вступления
            </div>
            {introHtml ? (
              <div
                className="space-y-2 text-sm leading-relaxed text-slate-100 [&_h1]:mb-3 [&_h1]:text-lg [&_h1]:font-bold [&_li]:ml-5 [&_li]:list-disc [&_p]:mb-2"
                dangerouslySetInnerHTML={{ __html: introHtml }}
              />
            ) : (
              <div className="text-sm italic text-slate-500">
                В паке нет intro.md
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
