import { mediaUrl } from '../socket';
import { authorMediaCaption, authorMediaSource, isAuthorMedia } from '../authorMedia';
import { playbackStateLabel } from '../uiText';
import { SynchronizedMedia } from './SynchronizedMedia';

export function SharedMediaRenderer({ media, volume, children }) {
  if (!media) return children;

  if (isAuthorMedia(media)) {
    const caption = authorMediaCaption(media);
    return (
      <figure className="w-full rounded-xl border border-slate-700 bg-slate-800/40 p-4 text-center">
        <img
          src={authorMediaSource(media, mediaUrl(media.media_id))}
          alt={caption || '13-й сектор'}
          className="mx-auto max-h-[520px] w-auto rounded-lg object-contain"
        />
        {caption && (
          <figcaption className="mx-auto mt-3 max-w-xl rounded-lg bg-slate-900/80 px-3 py-3 text-xl font-bold text-white md:text-2xl">
            {caption}
          </figcaption>
        )}
      </figure>
    );
  }

  if (media.type === 'audio') {
    return (
      <div className="w-full bg-slate-800/40 border border-slate-700 rounded-xl p-6 flex flex-col items-center gap-4">
        <div className="text-5xl">🔊</div>
        <div className="text-center">
          <div className="text-sm font-bold text-slate-200">{media.name || 'Аудио'}</div>
          <div className="text-xs text-slate-500 mt-1">
            {playbackStateLabel(media.playback_state)}
          </div>
        </div>
        <SynchronizedMedia media={media} volume={volume} />
      </div>
    );
  }

  if (media.type === 'video') {
    return (
      <div className="w-full bg-slate-800/40 border border-slate-700 rounded-xl p-4 flex flex-col items-center gap-3">
        <SynchronizedMedia media={media} volume={volume} />
        <div className="text-xs text-slate-500">
          {playbackStateLabel(media.playback_state)}
        </div>
      </div>
    );
  }

  if (media.type !== 'image') return children;

  return (
    <div className="w-full bg-slate-800/40 border border-slate-700 rounded-xl p-4 flex justify-center">
      <img
        src={mediaUrl(media.media_id)}
        alt="Медиа вопроса"
        className="max-h-[520px] w-auto object-contain"
      />
    </div>
  );
}
