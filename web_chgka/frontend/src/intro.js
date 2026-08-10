export const INTRO_LAST_SLIDE = 13;
export const INTRO_FALLBACK_AUTHOR_SOURCE = '/images/intro/author-fallback.png';

export function introSlideSource(slideIndex) {
  if (!Number.isInteger(slideIndex) || slideIndex < 0 || slideIndex > INTRO_LAST_SLIDE) {
    return null;
  }

  if (slideIndex === 0) return '/images/intro/00_owl.png';
  if (slideIndex === INTRO_LAST_SLIDE) return '/images/intro/13.png';
  return null;
}

export function introSlideLabel(slideIndex) {
  if (slideIndex === 0) return 'Стартовый слайд';
  if (slideIndex === INTRO_LAST_SLIDE) return 'Финальный слайд';
  if (Number.isInteger(slideIndex) && slideIndex > 0 && slideIndex < INTRO_LAST_SLIDE) {
    return `Авторы сектора ${slideIndex} из 12`;
  }
  return 'Неизвестный слайд';
}

export function introAuthorCaption(author) {
  if (!author?.name) return null;
  return author.city ? `${author.name} (${author.city})` : author.name;
}

export function introNextStepLabel(slideIndex) {
  if (slideIndex === 0) return 'Показать авторов сектора 1';
  if (Number.isInteger(slideIndex) && slideIndex > 0 && slideIndex < 12) {
    return `Показать авторов сектора ${slideIndex + 1}`;
  }
  if (slideIndex === 12) return 'Показать финальный слайд';
  if (slideIndex === INTRO_LAST_SLIDE) return 'Перейти к игре';
  return 'Следующий слайд';
}

export function introRemainingMs(intro, localNowMs = Date.now()) {
  if (
    !intro
    || !Number.isFinite(intro.started_at_ms)
    || !Number.isFinite(intro.duration_ms)
    || intro.duration_ms < 0
    || !Number.isFinite(intro.server_now_ms)
    || !Number.isFinite(intro.received_at_ms)
    || !Number.isFinite(localNowMs)
  ) {
    return null;
  }

  const elapsedBeforeSnapshot = Math.max(0, intro.server_now_ms - intro.started_at_ms);
  const elapsedAfterSnapshot = Math.max(0, localNowMs - intro.received_at_ms);
  return Math.max(0, intro.duration_ms - elapsedBeforeSnapshot - elapsedAfterSnapshot);
}

export function formatIntroRemaining(remainingMs) {
  if (typeof remainingMs !== 'number' || !Number.isFinite(remainingMs)) return '—:—';
  const totalSeconds = Math.max(0, Math.ceil(remainingMs / 1000));
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = String(totalSeconds % 60).padStart(2, '0');
  return `${minutes}:${seconds}`;
}

export function introHostControlView(intro, localNowMs = Date.now()) {
  const slideIndex = intro?.slide_index;
  const canAdvance = Number.isInteger(slideIndex);
  const musicStarted = Number.isFinite(intro?.started_at_ms);
  const remaining = introRemainingMs(intro, localNowMs);
  const musicFinished = musicStarted && remaining === 0;

  return {
    slideIndex,
    slideLabel: introSlideLabel(slideIndex),
    nextStepLabel: introNextStepLabel(slideIndex),
    canAdvance,
    canStartMusic: canAdvance && !musicStarted,
    musicStatus: musicStarted ? formatIntroRemaining(remaining) : 'Не запущена',
    musicActionLabel: musicFinished
      ? 'Музыка завершена'
      : musicStarted
        ? 'Музыка запущена'
        : 'Запустить музыку',
  };
}
