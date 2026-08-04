import { mediaUrl } from '../socket';
import { SynchronizedAudio } from './SynchronizedAudio';

const playbackLabels = {
  stopped: 'Готово к воспроизведению',
  playing: 'Воспроизводится',
  paused: 'Пауза',
};

export function SharedMediaRenderer({ media, volume, children }) {
  if (!media) return children;

  if (media.type === 'audio') {
    return (
      <div className="w-full bg-slate-800/40 border border-slate-700 rounded-xl p-6 flex flex-col items-center gap-4">
        <div className="text-5xl">🔊</div>
        <div className="text-center">
          <div className="text-sm font-bold text-slate-200">{media.name || 'Аудио'}</div>
          <div className="text-xs text-slate-500 mt-1">
            {playbackLabels[media.playback_state] || media.playback_state}
          </div>
        </div>
        <SynchronizedAudio media={media} volume={volume} />
      </div>
    );
  }

  if (media.type !== 'image') return children;

  return (
    <div className="w-full bg-slate-800/40 border border-slate-700 rounded-xl p-4 flex justify-center">
      <img
        src={mediaUrl(media.media_id)}
        alt="Shared media"
        className="max-h-[520px] w-auto object-contain"
      />
    </div>
  );
}
