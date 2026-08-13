import { groupDisplayName } from '../participants';

export function ParticipantRoster({
  groups,
  onApprove,
  onKick,
  captain = null,
  onSelectCaptain,
  compact = false,
}) {
  if (groups.length === 0) {
    return <div className="text-xs italic text-slate-600">Нет участников</div>;
  }

  return (
    <div className={compact ? 'space-y-1' : 'space-y-2'}>
      {groups.map((group, groupIndex) => {
        const alternatingBackground = groupIndex % 2 === 0
          ? 'bg-slate-700/55 border-slate-600'
          : 'bg-slate-950/45 border-slate-700';
        const background = group.pending
          ? 'bg-yellow-900/30 border-yellow-700/50'
          : alternatingBackground;
        return (
          <div
            key={group.group_id}
            className={`flex items-center justify-between gap-3 rounded border ${background} ${compact ? 'px-2 py-1.5' : 'p-3'}`}
          >
            <div className="min-w-0 flex-1">
              {(group.participants || []).map((participant) => {
                const isCaptain = captain?.participant_id === participant.id;
                return (
                <div key={participant.id} className="flex min-h-6 items-center gap-2">
                  <span
                    className={`h-2 w-2 shrink-0 rounded-full ${
                      group.pending
                        ? 'animate-pulse bg-yellow-500'
                        : group.online
                          ? 'bg-green-500'
                          : 'bg-slate-600'
                    }`}
                  />
                  <span
                    className={`${compact ? 'text-sm' : 'font-bold'} ${
                      group.pending
                        ? 'text-yellow-300'
                        : group.online
                          ? 'text-white'
                          : 'text-slate-500'
                    }`}
                  >
                    {participant.name}
                  </span>
                  {!group.online && !group.pending && (
                    <span className="text-[10px] text-slate-600">(оффлайн)</span>
                  )}
                  {!group.pending && onSelectCaptain && (
                    <button
                      type="button"
                      disabled={isCaptain}
                      onClick={() => onSelectCaptain(participant)}
                      aria-label={isCaptain
                        ? `${participant.name} — капитан`
                        : `Сделать капитаном: ${participant.name}`}
                      title={isCaptain ? 'Капитан' : 'Сделать капитаном'}
                      className={`ml-auto rounded px-1.5 py-0.5 text-xs transition-colors ${
                        isCaptain
                          ? 'cursor-default bg-amber-700/50 text-amber-200'
                          : 'bg-slate-800 text-slate-500 hover:bg-amber-900/50 hover:text-amber-300'
                      }`}
                    >
                      👑
                    </button>
                  )}
                </div>
                );
              })}
              {group.pending && (
                <div className="mt-1 text-[10px] font-bold uppercase tracking-wider text-yellow-500">
                  Группа ожидает допуска
                </div>
              )}
            </div>
            <div className="flex shrink-0 flex-col gap-1">
              {group.pending && onApprove && (
                <button
                  type="button"
                  onClick={() => onApprove(group)}
                  className="rounded bg-green-700 px-2 py-1 text-[10px] font-bold uppercase text-white transition-colors hover:bg-green-600"
                >
                  Пустить
                </button>
              )}
              {onKick && (
                <button
                  type="button"
                  onClick={() => onKick(group)}
                  aria-label={`Отключить группу ${groupDisplayName(group)}`}
                  className="rounded bg-red-900/50 px-2 py-1 text-[10px] font-bold uppercase text-red-300 transition-colors hover:bg-red-800 hover:text-white"
                >
                  Отключить
                </button>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
