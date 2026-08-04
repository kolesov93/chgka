import { useState } from 'react';
import { mediaUrl, socket } from '../socket';

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

export function AdminQuestionPanel({ adminQuestion, phase, sharedMedia, addNotification }) {
  const [mediaPreview, setMediaPreview] = useState(null);

  if (!adminQuestion) return null;

  const isBlitz = adminQuestion.kind === 'blitz' || adminQuestion.kind === 'superblitz';
  const header = isBlitz
    ? `${adminQuestion.kind.toUpperCase()} • Сектор ${adminQuestion.sector} • Часть ${(adminQuestion.part_index ?? 0) + 1}/3`
    : `Сектор ${adminQuestion.sector}`;

  const renderHtml = (html, section) => {
    if (!html) return null;

    const handleClick = (event) => {
      const element = event.target?.closest?.('.media-placeholder[data-media-type][data-media-path]');
      if (!element) return;

      const mediaType = element.getAttribute('data-media-type');
      const mediaPath = element.getAttribute('data-media-path');
      if (!mediaType || !mediaPath) return;

      if (mediaType !== 'image') {
        addNotification({
          type: 'warning',
          message: `Пока поддерживаем только картинки (media_type=${mediaType})`,
        });
        return;
      }

      socket.emit(
        'admin_resolve_media',
        { media_type: mediaType, media_path: mediaPath },
        (response) => {
          if (!response?.ok) {
            addNotification({
              type: 'warning',
              message: `Не удалось открыть медиа: ${response?.error || 'unknown'}`,
            });
            return;
          }

          setMediaPreview({
            media_id: response.media_id,
            type: response.type,
            url: mediaUrl(response.media_id),
            section,
            path: mediaPath,
          });
        },
      );
    };

    return (
      <div
        className="text-sm text-slate-200 [&_p]:mb-2 [&_ul]:list-disc [&_ul]:pl-5 [&_.media-placeholder]:inline-block [&_.media-placeholder]:w-10 [&_.media-placeholder]:h-6 [&_.media-placeholder]:rounded [&_.media-placeholder]:bg-slate-700 [&_.media-placeholder]:border [&_.media-placeholder]:border-slate-500 [&_.media-placeholder]:cursor-pointer [&_.media-placeholder]:align-middle [&_.media-placeholder:hover]:bg-slate-600"
        onClick={handleClick}
        dangerouslySetInnerHTML={{ __html: html }}
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

  const highlightQuestion = phase === 'QUESTION_READING' || phase === 'DISCUSSION';
  const highlightAnswer = phase === 'TEAM_ANSWER' || phase === 'POST_ROUND';

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
              Preview: <span className="text-slate-200">{mediaPreview.path}</span>
              <span className="text-slate-600"> • </span>
              <span className="text-slate-500">секция:</span>{' '}
              <span className="text-slate-200">{mediaPreview.section}</span>
            </div>
            {mediaPreview.type === 'image' && (
              <div className="rounded border border-slate-700 bg-slate-900/40 p-2 flex justify-center">
                <img
                  src={mediaPreview.url}
                  alt={mediaPreview.path}
                  className="max-h-[320px] w-auto object-contain"
                />
              </div>
            )}
            <div className="flex gap-2">
              <button
                onClick={sharePreview}
                className="flex-1 bg-blue-700 hover:bg-blue-600 text-white py-2 rounded shadow active:scale-95 transition-all font-bold uppercase tracking-wider text-[10px]"
              >
                Показать игрокам
              </button>
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
