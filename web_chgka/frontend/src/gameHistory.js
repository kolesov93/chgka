const MODE_LABELS = {
  regular: 'Обычная',
  debug: 'Тестовая',
};

const STATUS_LABELS = {
  lobby: 'Ожидание',
  active: 'Идёт',
  completed: 'Завершена',
  reset: 'Сброшена',
  interrupted: 'Прервана',
};

export function gameModeLabel(mode) {
  return MODE_LABELS[mode] || 'Неизвестный режим';
}

export function gameStatusLabel(status) {
  return STATUS_LABELS[status] || 'Неизвестный статус';
}

export function gameScoreLabel(score) {
  if (!score || !Number.isInteger(score.znatoki) || !Number.isInteger(score.tv)) {
    return '—';
  }
  return `${score.znatoki}:${score.tv}`;
}

export function questionHistoryLabel(question) {
  const sector = Number.isInteger(question?.sector) ? `Сектор ${question.sector}` : 'Сектор неизвестен';
  const part = Number.isInteger(question?.part_index)
    ? `, часть ${question.part_index + 1}/3`
    : '';
  const title = question?.title ? ` — ${question.title}` : '';
  return `${sector}${part}${title}`;
}

export function formatJournalTimestamp(value, { withDate = true } = {}) {
  const timestamp = Date.parse(value);
  if (!Number.isFinite(timestamp)) return '—';
  const options = withDate
    ? { dateStyle: 'short', timeStyle: 'short' }
    : { hour: '2-digit', minute: '2-digit', second: '2-digit' };
  return new Intl.DateTimeFormat('ru-RU', options).format(new Date(timestamp));
}
