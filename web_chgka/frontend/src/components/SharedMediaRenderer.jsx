import { mediaUrl } from '../socket';

export function SharedMediaRenderer({ media, children }) {
  if (!media || media.type !== 'image') return children;

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
