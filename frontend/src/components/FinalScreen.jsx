import { gameOverPresentation } from '../gameOver';


export function FinalScreen({ score }) {
  const presentation = gameOverPresentation(score);
  const winnerClass = presentation.winner === 'znatoki'
    ? 'text-emerald-300 border-emerald-700/60 bg-emerald-950/30'
    : presentation.winner === 'tv'
      ? 'text-red-300 border-red-700/60 bg-red-950/30'
      : 'text-yellow-300 border-yellow-700/60 bg-yellow-950/30';

  return (
    <div className={`w-full max-w-xl rounded-2xl border p-8 text-center shadow-2xl ${winnerClass}`}>
      <div className="mb-3 text-xs font-black uppercase tracking-[0.3em] opacity-70">
        Игра окончена
      </div>
      <div className="mb-4 text-5xl" aria-hidden="true">🏆</div>
      <h2 className="text-3xl font-black uppercase tracking-wide text-white">
        {presentation.title}
      </h2>
      <div className="mt-3 text-lg font-bold">
        {presentation.detail}
      </div>
    </div>
  );
}
