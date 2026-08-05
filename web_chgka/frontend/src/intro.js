export const INTRO_LAST_SLIDE = 13;

export function introSlideSource(slideIndex) {
  if (!Number.isInteger(slideIndex) || slideIndex < 0 || slideIndex > INTRO_LAST_SLIDE) {
    return null;
  }

  const fileName = slideIndex === 0 ? '00_owl' : String(slideIndex).padStart(2, '0');
  const extension = slideIndex === 0 || slideIndex === INTRO_LAST_SLIDE ? 'png' : 'jpg';
  return `/images/intro/${fileName}.${extension}`;
}

export function introSlideLabel(slideIndex) {
  if (slideIndex === 0) return 'Стартовый слайд';
  if (slideIndex === INTRO_LAST_SLIDE) return 'Финальный слайд';
  if (Number.isInteger(slideIndex) && slideIndex > 0 && slideIndex < INTRO_LAST_SLIDE) {
    return `Автор ${slideIndex} из 12`;
  }
  return 'Неизвестный слайд';
}

export function introNextStepLabel(slideIndex) {
  if (slideIndex === 0) return 'Показать автора 1';
  if (Number.isInteger(slideIndex) && slideIndex > 0 && slideIndex < 12) {
    return `Показать автора ${slideIndex + 1}`;
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
