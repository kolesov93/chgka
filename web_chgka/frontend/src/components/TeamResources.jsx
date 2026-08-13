export function TeamResources({ team }) {
  const captain = team?.captain;
  const earnedMinutes = team?.earned_minutes ?? 0;
  const credit = team?.credit || {};
  const creditLabel = credit.repayment_scheduled
    ? credit.forced
      ? 'Кредит: обязательный возврат в следующем раунде'
      : 'Кредит: возврат в следующем раунде'
    : credit.debt
      ? 'Кредит: нужно вернуть'
      : credit.used
        ? 'Кредит: использован'
        : null;

  if (!captain && earnedMinutes === 0 && !creditLabel) return null;

  return (
    <div className="mb-4 flex w-full max-w-3xl flex-wrap justify-center gap-2 text-xs font-bold">
      {captain && (
        <div className="rounded-full border border-amber-700/60 bg-amber-950/40 px-3 py-1.5 text-amber-200">
          👑 Капитан: {captain.name}
        </div>
      )}
      {earnedMinutes > 0 && (
        <div className="rounded-full border border-sky-700/60 bg-sky-950/40 px-3 py-1.5 text-sky-200">
          Доп. минуты: {earnedMinutes}
        </div>
      )}
      {creditLabel && (
        <div className="rounded-full border border-rose-700/60 bg-rose-950/40 px-3 py-1.5 text-rose-200">
          {creditLabel}
        </div>
      )}
    </div>
  );
}
