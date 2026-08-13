export function RespondentBanner({ respondent, superblitz = false }) {
  if (!respondent?.name) return null;

  return (
    <div className="mb-4 w-full rounded-xl border border-violet-500/60 bg-violet-950/55 px-4 py-3 text-center shadow-lg">
      <div className="text-[10px] font-bold uppercase tracking-[0.2em] text-violet-300">
        {superblitz ? 'Играет суперблиц' : 'Отвечает'}
      </div>
      <div className="mt-1 text-xl font-black text-white">{respondent.name}</div>
    </div>
  );
}
