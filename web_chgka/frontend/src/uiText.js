const PHASE_LABELS = {
  LOGIN: 'Ожидание игроков',
  INTRO: 'Интро',
  PRE_ROUND: 'Ожидание вращения',
  QUESTION_READING: 'Чтение вопроса',
  DISCUSSION: 'Обсуждение',
  TEAM_ANSWER: 'Ответ команды',
  POST_ROUND: 'Разбор ответа',
  GAME_OVER: 'Игра завершена',
};

const QUESTION_KIND_LABELS = {
  normal: 'обычный вопрос',
  blitz: 'блиц',
  superblitz: 'суперблиц',
};

const MEDIA_SECTION_LABELS = {
  intro: 'вступление',
  question: 'вопрос',
  answer: 'ответ',
  comment: 'комментарий',
  sources: 'источники',
  current: 'текущее медиа',
};

const MEDIA_TYPE_LABELS = {
  image: 'изображение',
  audio: 'аудио',
  video: 'видео',
};

const PLAYBACK_STATE_LABELS = {
  stopped: 'Готово к воспроизведению',
  playing: 'Воспроизводится',
  paused: 'Пауза',
};

export function phaseLabel(value) {
  return PHASE_LABELS[value] || 'Неизвестная фаза';
}

export function questionKindLabel(value) {
  return QUESTION_KIND_LABELS[value] || 'неизвестный тип вопроса';
}

export function mediaSectionLabel(value) {
  return MEDIA_SECTION_LABELS[value] || 'неизвестная секция';
}

export function mediaTypeLabel(value) {
  return MEDIA_TYPE_LABELS[value] || 'медиа';
}

export function playbackStateLabel(value) {
  return PLAYBACK_STATE_LABELS[value] || 'Состояние неизвестно';
}

export function responseMessage(response, fallback = 'Операция отклонена') {
  const message = response?.message;
  return typeof message === 'string' && message.trim() ? message : fallback;
}
