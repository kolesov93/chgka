import { useEffect, useRef, useState } from 'react';
import { inlineImagePreviews } from '../inlineMedia';
import { mediaUrl, socket } from '../socket';
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
    section: 'текущая',
    name: fallbackNames[media.type] || 'Текущее медиа',
    media_ref: null,
  };
}

export function AdminQuestionPanel({
  adminQuestion,
  phase,
  sharedMedia,
  volume,
  addNotification,
}) {
  const [mediaPreview, setMediaPreview] = useState(null);
  const [resolvedImages, setResolvedImages] = useState({});
  const resolutionGenerationRef = useRef(0);
  const sharedMediaIdRef = useRef(sharedMedia?.media_id);
  const previousSharedMediaIdRef = useRef(sharedMedia?.media_id);
  sharedMediaIdRef.current = sharedMedia?.media_id;

  useEffect(() => {
    const previousId = previousSharedMediaIdRef.current;
    const currentId = sharedMedia?.media_id;
    previousSharedMediaIdRef.current = currentId;
    if (!previousId || previousId === currentId) return;

    setMediaPreview((current) => (
      current?.media_id === previousId ? null : current
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

  if (!adminQuestion) return null;

  const mediaByRef = Object.fromEntries(
    (adminQuestion.media || []).map((media) => [media.media_ref, media]),
  );

  const isBlitz = adminQuestion.kind === 'blitz' || adminQuestion.kind === 'superblitz';
  const header = isBlitz
    ? `${adminQuestion.kind.toUpperCase()} • Сектор ${adminQuestion.sector} • Часть ${(adminQuestion.part_index ?? 0) + 1}/3`
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
              setResolvedImages((current) => ({
                ...current,
                [mediaRef]: { status: 'error' },
              }));
              addNotification({
                type: 'warning',
                message: `Не удалось открыть изображение: ${response?.error || 'unknown'}`,
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
            addNotification({
              type: 'warning',
              message: `Не удалось открыть медиа: ${response?.error || 'unknown'}`,
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
    if (
      mediaPreview?.section === 'answer'
      && (phase === 'QUESTION_READING' || phase === 'DISCUSSION')
      && !confirm('Это медиа из секции "Ответ". Точно показать игрокам прямо сейчас?')
    ) {
      return;
    }

    socket.emit('admin_share_media', { media_id: mediaPreview.media_id });
  };

  const shareNextMedia = () => {
    socket.emit('admin_share_next_media', {
      expected_media_id: sharedMedia?.media_id,
    }, (response) => {
      if (!response?.ok) {
        addNotification({
          type: 'warning',
          message: response?.error === 'no_next_media'
            ? 'В этой секции больше нет медиа'
            : `Не удалось показать следующее медиа: ${response?.error || 'unknown'}`,
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
          <div className="text-[10px] text-slate-500 uppercase font-bold tracking-widest">
            Шарим: {sharedMedia ? 'да' : 'нет'}
          </div>
        </div>

        {mediaPreview ? (
          <div className="flex flex-col gap-3">
            <div className="text-[11px] text-slate-400">
              Preview: <span className="text-slate-200">{mediaPreview.name}</span>
              <span className="text-slate-600"> • </span>
              <span className="text-slate-500">секция:</span>{' '}
              <span className="text-slate-200">{mediaPreview.section}</span>
            </div>
            {mediaPreview.type === 'image' && (
              <div className="rounded border border-slate-700 bg-slate-900/40 p-2 flex justify-center">
                <img
                  src={mediaPreview.url}
                  alt={mediaPreview.name}
                  className="max-h-[320px] w-auto object-contain"
                />
              </div>
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
            <div className="flex flex-wrap gap-2">
              <button
                onClick={sharePreview}
                disabled={previewIsShared}
                className="flex-1 bg-blue-700 hover:bg-blue-600 text-white py-2 rounded shadow active:scale-95 transition-all font-bold uppercase tracking-wider text-[10px]"
              >
                {previewIsShared ? 'Показано игрокам' : 'Показать игрокам'}
              </button>
              {(mediaPreview.type === 'audio' || mediaPreview.type === 'video') && previewIsShared && (
                <>
                  <button
                    onClick={() => socket.emit('admin_play_media')}
                    className="bg-green-700 hover:bg-green-600 text-white py-2 px-3 rounded shadow active:scale-95 transition-all font-bold uppercase tracking-wider text-[10px]"
                  >
                    Play
                  </button>
                  <button
                    onClick={() => socket.emit('admin_pause_media')}
                    className="bg-yellow-700 hover:bg-yellow-600 text-white py-2 px-3 rounded shadow active:scale-95 transition-all font-bold uppercase tracking-wider text-[10px]"
                  >
                    Pause
                  </button>
                  <button
                    onClick={() => socket.emit('admin_stop_media')}
                    className="bg-red-900 hover:bg-red-800 text-white py-2 px-3 rounded shadow active:scale-95 transition-all font-bold uppercase tracking-wider text-[10px]"
                  >
                    Stop
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
              <button
                onClick={() => socket.emit('admin_hide_media')}
                className="flex-1 bg-slate-700 hover:bg-slate-600 text-slate-200 py-2 rounded shadow active:scale-95 transition-all font-bold uppercase tracking-wider text-[10px]"
              >
                Скрыть
              </button>
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
