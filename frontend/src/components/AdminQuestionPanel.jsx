import { useEffect, useRef, useState } from 'react';
import { BLACKBOX_IMAGE_SOURCE } from '../blackbox';
import { authorMediaCaption, authorMediaSource, isAuthorMedia } from '../authorMedia';
import { inlineImagePreviews } from '../inlineMedia';
import { requiresAnswerMediaConfirmation } from '../interactionGuards';
import { mediaUrl, socket } from '../socket';
import {
  mediaSectionLabel,
  questionKindLabel,
  responseMessage,
} from '../uiText';
import { BlackboxCountdown } from './BlackboxPresentation';
import { SynchronizedMedia } from './SynchronizedMedia';

function QuestionSection({ title, children, highlight = false, accentClass = '' }) {
  return (
    <div
      className={[
        'rounded-lg border p-3',
        'bg-slate-950/40 border-slate-700',
        highlight ? `ring-2 ${accentClass} border-transparent bg-slate-900/60` : '',
      ].join(' ')}
    >
      <div className="text-xs text-slate-400 uppercase font-bold tracking-widest mb-2">{title}</div>
      {children}
    </div>
  );
}

function previewFromResponse(response, fallbackSection) {
  return {
    media_id: response.media_id,
    type: response.type,
    url: mediaUrl(response.media_id),
    section: response.section || fallbackSection,
    name: response.name,
    media_ref: response.media_ref,
    presentation_kind: response.presentation_kind,
    author_name: response.author_name,
    author_city: response.author_city,
    author_asset: response.author_asset,
    has_photo: response.has_photo,
  };
}

function previewFromSharedMedia(media) {
  const fallbackNames = {
    image: 'Текущее изображение',
    audio: 'Текущее аудио',
    video: 'Текущее видео',
  };
  return {
    media_id: media.media_id,
    type: media.type,
    url: mediaUrl(media.media_id),
    section: isAuthorMedia(media) ? 'author' : 'current',
    name: isAuthorMedia(media)
      ? media.author_name || 'Автор вопроса'
      : fallbackNames[media.type] || 'Текущее медиа',
    media_ref: null,
    presentation_kind: media.presentation_kind,
    author_name: media.author_name,
    author_city: media.author_city,
    author_asset: media.author_asset,
    has_photo: media.has_photo,
  };
}

export function AdminQuestionPanel({
  adminQuestion,
  phase,
  sharedMedia,
  blackbox,
  volume,
  addNotification,
}) {
  const [mediaPreview, setMediaPreview] = useState(null);
  const [pendingAnswerShareId, setPendingAnswerShareId] = useState(null);
  const [resolvedImages, setResolvedImages] = useState({});
  const resolutionGenerationRef = useRef(0);
  const sharedMediaIdRef = useRef(sharedMedia?.media_id);
  const previousSharedMediaRef = useRef(sharedMedia || null);
  sharedMediaIdRef.current = sharedMedia?.media_id;

  useEffect(() => {
    const previous = previousSharedMediaRef.current;
    const previousId = previous?.media_id;
    const currentId = sharedMedia?.media_id;
    previousSharedMediaRef.current = sharedMedia || null;
    if (!previousId || previousId === currentId) return;

    setMediaPreview((current) => (
      current?.media_id === previousId && !isAuthorMedia(current) ? null : current
    ));
    setResolvedImages((current) => Object.fromEntries(
      Object.entries(current).filter(([, resolved]) => (
        resolved?.preview?.media_id !== previousId
      )),
    ));
  }, [sharedMedia?.media_id]);

  useEffect(() => {
    if (!sharedMedia?.media_id) return;
    setMediaPreview((current) => (
      current?.media_id === sharedMedia.media_id
        ? current
        : previewFromSharedMedia(sharedMedia)
    ));
  }, [sharedMedia?.media_id, sharedMedia?.type]);

  useEffect(() => {
    const generation = resolutionGenerationRef.current + 1;
    resolutionGenerationRef.current = generation;

    const images = (adminQuestion?.media || []).filter((media) => media.type === 'image');
    images.forEach((descriptor) => {
      socket.emit(
        'admin_resolve_media',
        { media_ref: descriptor.media_ref },
        (response) => {
          if (resolutionGenerationRef.current !== generation) return;

          if (!response?.ok) {
            setResolvedImages((current) => ({
              ...current,
              [descriptor.media_ref]: { status: 'error' },
            }));
            return;
          }

          const preview = previewFromResponse(response, descriptor.section);
          setResolvedImages((current) => ({
            ...current,
            [descriptor.media_ref]: { status: 'ready', preview },
          }));
          setMediaPreview((current) => {
            if (
              current?.media_ref !== descriptor.media_ref
              || current.media_id === sharedMediaIdRef.current
            ) {
              return current;
            }
            return preview;
          });
        },
      );
    });

    return () => {
      if (resolutionGenerationRef.current === generation) {
        resolutionGenerationRef.current += 1;
      }
    };
  }, [adminQuestion]);

  const authorPreview = adminQuestion?.author_media?.media_id
    ? previewFromResponse(adminQuestion.author_media, 'author')
    : null;
  const authorContextKey = [
    adminQuestion?.sector,
    adminQuestion?.kind,
    adminQuestion?.part_index ?? 0,
  ].join(':');

  useEffect(() => {
    if (phase === 'QUESTION_READING' && authorPreview) {
      setMediaPreview(authorPreview);
      return;
    }
    setMediaPreview((current) => (isAuthorMedia(current) ? null : current));
  }, [authorContextKey, adminQuestion?.author_media?.media_id, phase]);

  useEffect(() => {
    setPendingAnswerShareId(null);
  }, [mediaPreview?.media_id, authorContextKey, phase]);

  if (!adminQuestion) return null;

  const mediaByRef = Object.fromEntries(
    (adminQuestion.media || []).map((media) => [media.media_ref, media]),
  );

  const isBlitz = adminQuestion.kind === 'blitz' || adminQuestion.kind === 'superblitz';
  const header = isBlitz
    ? `${questionKindLabel(adminQuestion.kind)} • Сектор ${adminQuestion.sector} • Часть ${(adminQuestion.part_index ?? 0) + 1}/3`
    : `Сектор ${adminQuestion.sector}`;

  const renderHtml = (html, section) => {
    if (!html) return null;

    const handleClick = (event) => {
      const element = event.target?.closest?.('.media-placeholder[data-media-ref]');
      if (!element) return;

      const mediaRef = element.getAttribute('data-media-ref');
      const descriptor = mediaByRef[mediaRef];
      if (!descriptor) {
        addNotification({ type: 'warning', message: 'Медиа не найдено в текущей секции' });
        return;
      }

      if (descriptor.type === 'image') {
        const resolved = resolvedImages[mediaRef];
        if (resolved?.status === 'ready') {
          setMediaPreview(resolved.preview);
          return;
        }

        const generation = resolutionGenerationRef.current;
        socket.emit(
          'admin_resolve_media',
          { media_ref: mediaRef },
          (response) => {
            if (resolutionGenerationRef.current !== generation) return;

            if (!response?.ok) {
              console.warn('Не удалось открыть изображение:', response?.error);
              setResolvedImages((current) => ({
                ...current,
                [mediaRef]: { status: 'error' },
              }));
              addNotification({
                type: 'warning',
                message: responseMessage(response, 'Не удалось открыть изображение'),
              });
              return;
            }

            const preview = previewFromResponse(response, descriptor.section || section);
            setResolvedImages((current) => ({
              ...current,
              [mediaRef]: { status: 'ready', preview },
            }));
            setMediaPreview(preview);
          },
        );
        return;
      }

      socket.emit(
        'admin_resolve_media',
        { media_ref: mediaRef },
        (response) => {
          if (!response?.ok) {
            console.warn('Не удалось открыть медиа:', response?.error);
            addNotification({
              type: 'warning',
              message: responseMessage(response, 'Не удалось открыть медиа'),
            });
            return;
          }

          setMediaPreview(previewFromResponse(response, section));
        },
      );
    };

    return (
      <div
        className="text-sm text-slate-200 [&_p]:mb-2 [&_ul]:list-disc [&_ul]:pl-5 [&_span.media-placeholder]:inline-block [&_span.media-placeholder]:w-10 [&_span.media-placeholder]:h-6 [&_span.media-placeholder]:rounded [&_span.media-placeholder]:bg-slate-700 [&_span.media-placeholder]:border [&_span.media-placeholder]:border-slate-500 [&_span.media-placeholder]:cursor-pointer [&_span.media-placeholder]:align-middle [&_span.media-placeholder:hover]:bg-slate-600 [&_.media-inline-preview]:inline-flex [&_.media-inline-preview]:max-w-[12rem] [&_.media-inline-preview]:min-h-12 [&_.media-inline-preview]:items-center [&_.media-inline-preview]:justify-center [&_.media-inline-preview]:overflow-hidden [&_.media-inline-preview]:rounded [&_.media-inline-preview]:border [&_.media-inline-preview]:border-slate-600 [&_.media-inline-preview]:bg-slate-900/70 [&_.media-inline-preview]:p-1 [&_.media-inline-preview]:align-middle [&_.media-inline-preview]:cursor-pointer [&_.media-inline-preview:hover]:border-yellow-500/70 [&_.media-inline-preview:hover]:bg-slate-800 [&_.media-inline-preview-image]:max-h-32 [&_.media-inline-preview-image]:max-w-full [&_.media-inline-preview-image]:object-contain [&_.media-inline-preview-fallback]:px-2 [&_.media-inline-preview-fallback]:py-3 [&_.media-inline-preview-fallback]:text-[10px] [&_.media-inline-preview-fallback]:font-bold [&_.media-inline-preview-fallback]:uppercase [&_.media-inline-preview-fallback]:tracking-wider [&_.media-inline-preview-fallback]:text-slate-400"
        onClick={handleClick}
        dangerouslySetInnerHTML={{
          __html: inlineImagePreviews(html, adminQuestion.media || [], resolvedImages),
        }}
      />
    );
  };

  const sharePreview = () => {
    if (requiresAnswerMediaConfirmation(mediaPreview, phase)) {
      setPendingAnswerShareId(mediaPreview.media_id);
      return;
    }

    socket.emit('admin_share_media', { media_id: mediaPreview.media_id });
  };

  const confirmAnswerMediaShare = () => {
    if (!pendingAnswerShareId || pendingAnswerShareId !== mediaPreview?.media_id) {
      setPendingAnswerShareId(null);
      return;
    }
    socket.emit('admin_share_media', { media_id: pendingAnswerShareId });
    setPendingAnswerShareId(null);
  };

  const shareNextMedia = () => {
    socket.emit('admin_share_next_media', {
      expected_media_id: sharedMedia?.media_id,
    }, (response) => {
      if (!response?.ok) {
        console.warn('Не удалось показать следующее медиа:', response?.error);
        addNotification({
          type: 'warning',
          message: response?.error === 'no_next_media'
            ? 'В этой секции больше нет медиа'
            : responseMessage(response, 'Не удалось показать следующее медиа'),
        });
        return;
      }

      const preview = previewFromResponse(response, response.section);
      if (preview.type === 'image') {
        setResolvedImages((current) => ({
          ...current,
          [preview.media_ref]: { status: 'ready', preview },
        }));
      }
      setMediaPreview(preview);
    });
  };

  const reportMediaEnded = (payload) => {
    socket.emit('admin_media_ended', payload);
  };

  const highlightQuestion = phase === 'QUESTION_READING' || phase === 'DISCUSSION';
  const highlightAnswer = phase === 'TEAM_ANSWER' || phase === 'POST_ROUND';
  const previewIsShared = mediaPreview?.media_id === sharedMedia?.media_id;
  const blackboxActive = Boolean(blackbox);

  const startBlackbox = () => {
    socket.emit('admin_start_blackbox', {}, (response) => {
      if (!response?.ok) {
        console.warn('Не удалось запустить чёрный ящик:', response?.error);
        addNotification({
          type: 'warning',
          message: responseMessage(response, 'Не удалось запустить чёрный ящик'),
        });
      }
    });
  };

  const stopBlackbox = () => {
    socket.emit('admin_stop_blackbox', {
      playback_generation: blackbox?.playback_generation,
    });
  };

  return (
    <div className="w-full bg-slate-800/70 border border-slate-700 rounded-xl p-4 mb-4">
      <div className="text-xs text-slate-400 uppercase font-bold tracking-widest mb-2">{header}</div>
      {isBlitz && adminQuestion.round_title && (
        <div className="text-sm text-slate-300 mb-3">
          <span className="text-slate-500">Блиц:</span> {adminQuestion.round_title}
        </div>
      )}
      <div className="text-lg font-bold text-white mb-2">{adminQuestion.title}</div>
      {adminQuestion.author && (
        <div className="text-xs text-slate-500 mb-3">Автор: {adminQuestion.author}</div>
      )}

      {adminQuestion.blackbox && (
        <div className="mb-4 flex items-center gap-4 rounded-lg border border-red-800/70 bg-red-950/20 p-3">
          <img
            src={BLACKBOX_IMAGE_SOURCE}
            alt="Чёрный ящик"
            className="h-20 w-24 shrink-0 object-contain"
          />
          <div className="flex min-w-0 flex-1 flex-col gap-2">
            <div>
              <div className="flex items-center justify-between gap-3">
                <div className="text-xs font-black uppercase tracking-widest text-red-300">
                  Чёрный ящик
                </div>
                {blackboxActive && (
                  <div className="text-right">
                    <div className="text-[9px] font-bold uppercase tracking-widest text-slate-500">
                      Осталось
                    </div>
                    <BlackboxCountdown blackbox={blackbox} />
                  </div>
                )}
              </div>
              <div className="mt-1 text-xs text-slate-400">
                {blackboxActive
                  ? 'Музыка играет; игрокам показана заставка.'
                  : 'Запусти музыку перед чтением вопроса.'}
              </div>
            </div>
            {blackboxActive ? (
              <button
                type="button"
                onClick={stopBlackbox}
                className="self-start rounded bg-red-800 px-4 py-2 text-[10px] font-bold uppercase tracking-wider text-white hover:bg-red-700"
              >
                Остановить
              </button>
            ) : (
              <button
                type="button"
                onClick={startBlackbox}
                disabled={phase !== 'QUESTION_READING'}
                className="self-start rounded bg-yellow-600 px-4 py-2 text-[10px] font-black uppercase tracking-wider text-black hover:bg-yellow-500 disabled:cursor-not-allowed disabled:opacity-40"
              >
                Запустить музыку
              </button>
            )}
          </div>
        </div>
      )}

      <div className="flex flex-col gap-3">
        {isBlitz && adminQuestion.intro_html && (
          <QuestionSection title="Вступление">
            {renderHtml(adminQuestion.intro_html, 'intro')}
          </QuestionSection>
        )}

        <QuestionSection title="Вопрос" highlight={highlightQuestion} accentClass="ring-yellow-500/60">
          {renderHtml(adminQuestion.question_html, 'question')}
        </QuestionSection>

        <QuestionSection title="Ответ" highlight={highlightAnswer} accentClass="ring-green-500/60">
          {renderHtml(adminQuestion.answer_html, 'answer')}
        </QuestionSection>

        {adminQuestion.comment_html && (
          <QuestionSection title="Комментарий">
            {renderHtml(adminQuestion.comment_html, 'comment')}
          </QuestionSection>
        )}

        {adminQuestion.sources_html && (
          <QuestionSection title="Источники">
            {renderHtml(adminQuestion.sources_html, 'sources')}
          </QuestionSection>
        )}
      </div>

      <div className="mt-4 rounded-lg border border-slate-700 bg-slate-950/30 p-3">
        <div className="flex items-center justify-between gap-3 mb-3">
          <div className="text-xs text-slate-400 uppercase font-bold tracking-widest">Медиа</div>
          <div className="flex items-center gap-2">
            {phase === 'QUESTION_READING' && authorPreview && (
              <button
                type="button"
                onClick={() => setMediaPreview(authorPreview)}
                className={`rounded px-2 py-1 text-[10px] font-bold uppercase tracking-wider ${
                  isAuthorMedia(mediaPreview)
                    ? 'bg-violet-700 text-white'
                    : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
                }`}
              >
                Автор
              </button>
            )}
            <div className="text-[10px] text-slate-500 uppercase font-bold tracking-widest">
              Показывается игрокам: {sharedMedia ? 'да' : 'нет'}
            </div>
          </div>
        </div>

        {mediaPreview ? (
          <div className="flex flex-col gap-3">
            <div className="text-[11px] text-slate-400">
              Предпросмотр: <span className="text-slate-200">{mediaPreview.name}</span>
              <span className="text-slate-600"> • </span>
              <span className="text-slate-500">секция:</span>{' '}
              <span className="text-slate-200">{mediaSectionLabel(mediaPreview.section)}</span>
            </div>
            {mediaPreview.type === 'image' && (
              <figure className="rounded border border-slate-700 bg-slate-900/40 p-2 text-center">
                <img
                  src={isAuthorMedia(mediaPreview)
                    ? authorMediaSource(mediaPreview, mediaPreview.url)
                    : mediaPreview.url}
                  alt={mediaPreview.name}
                  className="mx-auto max-h-[320px] w-auto object-contain"
                />
                {authorMediaCaption(mediaPreview) && (
                  <figcaption className="mt-2 rounded bg-slate-800 px-2 py-2 text-base font-bold text-white">
                    {authorMediaCaption(mediaPreview)}
                  </figcaption>
                )}
              </figure>
            )}
            {(mediaPreview.type === 'audio' || mediaPreview.type === 'video') && (
              <div className="rounded border border-slate-700 bg-slate-900/40 p-3">
                {previewIsShared ? (
                  <SynchronizedMedia
                    media={sharedMedia}
                    volume={volume}
                    onEnded={reportMediaEnded}
                  />
                ) : mediaPreview.type === 'video' ? (
                  <video
                    src={mediaPreview.url}
                    controls
                    playsInline
                    preload="metadata"
                    className="max-h-[320px] w-full rounded bg-black object-contain"
                  />
                ) : (
                  <audio
                    src={mediaPreview.url}
                    controls
                    preload="metadata"
                    className="w-full"
                  />
                )}
              </div>
            )}
            {pendingAnswerShareId === mediaPreview.media_id && (
              <div
                role="alert"
                aria-labelledby="answer-media-confirmation-title"
                className="rounded-lg border border-amber-600/70 bg-amber-950/35 p-3"
              >
                <div
                  id="answer-media-confirmation-title"
                  className="text-xs font-black uppercase tracking-wider text-amber-300"
                >
                  Медиа находится в секции «Ответ»
                </div>
                <p className="mt-1 text-xs text-amber-100/80">
                  Если показать его сейчас, игроки могут увидеть часть ответа раньше времени.
                </p>
                <div className="mt-3 grid grid-cols-2 gap-2">
                  <button
                    type="button"
                    onClick={() => setPendingAnswerShareId(null)}
                    className="rounded bg-slate-700 px-3 py-2 text-[10px] font-bold uppercase tracking-wider text-slate-100 hover:bg-slate-600"
                  >
                    Не показывать
                  </button>
                  <button
                    type="button"
                    onClick={confirmAnswerMediaShare}
                    className="rounded bg-amber-600 px-3 py-2 text-[10px] font-black uppercase tracking-wider text-slate-950 hover:bg-amber-500"
                  >
                    Всё равно показать
                  </button>
                </div>
              </div>
            )}
            <div className="flex flex-wrap gap-2">
              <button
                onClick={sharePreview}
                disabled={previewIsShared || blackboxActive || pendingAnswerShareId === mediaPreview.media_id}
                className="flex-1 bg-blue-700 hover:bg-blue-600 disabled:cursor-not-allowed disabled:opacity-40 text-white py-2 rounded shadow active:scale-95 transition-all font-bold uppercase tracking-wider text-[10px]"
              >
                {previewIsShared
                  ? isAuthorMedia(mediaPreview) ? 'Автор показан' : 'Показано игрокам'
                  : blackboxActive
                    ? 'Сначала завершите чёрный ящик'
                    : isAuthorMedia(mediaPreview) ? 'Показать автора' : 'Показать игрокам'}
              </button>
              {(mediaPreview.type === 'audio' || mediaPreview.type === 'video') && previewIsShared && (
                <>
                  <button
                    onClick={() => socket.emit('admin_play_media')}
                    className="bg-green-700 hover:bg-green-600 text-white py-2 px-3 rounded shadow active:scale-95 transition-all font-bold uppercase tracking-wider text-[10px]"
                  >
                    Воспроизвести
                  </button>
                  <button
                    onClick={() => socket.emit('admin_pause_media')}
                    className="bg-yellow-700 hover:bg-yellow-600 text-white py-2 px-3 rounded shadow active:scale-95 transition-all font-bold uppercase tracking-wider text-[10px]"
                  >
                    Пауза
                  </button>
                  <button
                    onClick={() => socket.emit('admin_stop_media')}
                    className="bg-red-900 hover:bg-red-800 text-white py-2 px-3 rounded shadow active:scale-95 transition-all font-bold uppercase tracking-wider text-[10px]"
                  >
                    Остановить
                  </button>
                </>
              )}
              {previewIsShared && sharedMedia?.has_next && (
                <button
                  onClick={shareNextMedia}
                  className="bg-blue-800 hover:bg-blue-700 text-white py-2 px-3 rounded shadow active:scale-95 transition-all font-bold uppercase tracking-wider text-[10px]"
                >
                  Следующее медиа
                </button>
              )}
              {sharedMedia && (
                <button
                  onClick={() => socket.emit('admin_hide_media')}
                  className="flex-1 bg-slate-700 hover:bg-slate-600 text-slate-200 py-2 rounded shadow active:scale-95 transition-all font-bold uppercase tracking-wider text-[10px]"
                >
                  Скрыть
                </button>
              )}
              <button
                onClick={() => setMediaPreview(null)}
                className="bg-slate-800 hover:bg-slate-700 text-slate-400 py-2 px-3 rounded shadow active:scale-95 transition-all font-bold uppercase tracking-wider text-[10px]"
              >
                ✕
              </button>
            </div>
          </div>
        ) : (
          <div className="text-xs text-slate-500">
            Кликни по “плашке” медиа в тексте вопроса/ответа, чтобы открыть превью.
          </div>
        )}
      </div>
    </div>
  );
}
