export const LIVE_OPS_PHASES = [
  'PRE_ROUND',
  'QUESTION_READING',
  'DISCUSSION',
  'TEAM_ANSWER',
  'POST_ROUND',
];

export function parseBoundedInteger(value, minimum, maximum) {
  const text = String(value).trim();
  if (!/^-?\d+$/.test(text)) return null;
  const numeric = Number(text);
  if (!Number.isSafeInteger(numeric) || numeric < minimum || numeric > maximum) {
    return null;
  }
  return numeric;
}

export function buildOpenRoundPayload({ sector, questionTypes, partNumber = 1 }) {
  const sectorId = parseBoundedInteger(sector, 1, 13);
  if (sectorId === null || !Array.isArray(questionTypes) || questionTypes.length !== 13) {
    return null;
  }

  const kind = questionTypes[sectorId - 1];
  if (kind === 'normal') return { sector: sectorId };
  if (kind !== 'blitz' && kind !== 'superblitz') return null;

  const part = parseBoundedInteger(partNumber, 1, 3);
  if (part === null) return null;
  return { sector: sectorId, part_index: part - 1 };
}
