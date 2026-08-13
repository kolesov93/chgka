export const MAX_PARTICIPANTS_PER_GROUP = 12;

export function participantGroups(players = []) {
  return players.filter((record) => record.role === 'player');
}

export function participantCount(groups = [], { pending = true } = {}) {
  return groups
    .filter((group) => pending || !group.pending)
    .reduce((total, group) => total + (group.participants?.length || 0), 0);
}

export function approvedParticipantOptions(players = []) {
  const groups = participantGroups(players).filter((group) => !group.pending);
  const nameCounts = new Map();
  groups.forEach((group) => {
    (group.participants || []).forEach((participant) => {
      nameCounts.set(participant.name, (nameCounts.get(participant.name) || 0) + 1);
    });
  });

  return groups.flatMap((group, groupIndex) => (
    (group.participants || []).map((participant) => ({
      value: participant.id,
      label: nameCounts.get(participant.name) > 1
        ? `${participant.name} · подключение ${groupIndex + 1}`
        : participant.name,
      online: Boolean(group.online),
    }))
  ));
}

export function groupDisplayName(group) {
  return (group?.participants || []).map((participant) => participant.name).join(', ');
}
