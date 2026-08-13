import { useEffect, useState } from 'react';
import {
  INTRO_FALLBACK_AUTHOR_SOURCE,
  introAuthorCaption,
  introSlideLabel,
  introSlideSource,
} from '../intro';
import { introAuthorPhotoUrl } from '../socket';

export function IntroScreen({ intro, isAdmin = false, introHtml = null }) {
  const [failedPhotoKeys, setFailedPhotoKeys] = useState([]);
  const slideIndex = intro?.slide_index;
  const authors = Array.isArray(intro?.authors) ? intro.authors : [];
  const isAuthorSlide = Number.isInteger(slideIndex) && slideIndex >= 1 && slideIndex <= 12;
  const slideSource = introSlideSource(slideIndex);
  const hasMultipleAuthors = authors.length > 1;

  useEffect(() => {
    setFailedPhotoKeys([]);
  }, [slideIndex]);

  const markPhotoFailed = (photoKey) => {
    setFailedPhotoKeys((current) => (
      current.includes(photoKey) ? current : [...current, photoKey]
    ));
  };

  return (
    <div className="w-full flex flex-col gap-4">
      <div className="w-full rounded-xl border border-slate-700 bg-slate-950/40 p-3 shadow-2xl">
        {slideSource && (
          <img
            src={slideSource}
            alt={introSlideLabel(slideIndex)}
            className="mx-auto max-h-[72vh] w-full rounded-lg object-contain"
          />
        )}
        {isAuthorSlide && authors.length > 0 && (
          <div className={hasMultipleAuthors ? 'grid grid-cols-3 gap-2 md:gap-4' : ''}>
            {authors.map((author) => {
              const photoKey = `${author.sector}:${author.slot}`;
              const source = author.has_photo && !failedPhotoKeys.includes(photoKey)
                ? introAuthorPhotoUrl(author.sector, author.slot)
                : INTRO_FALLBACK_AUTHOR_SOURCE;
              const caption = introAuthorCaption(author);

              return (
                <figure key={photoKey} className="min-w-0">
                  <img
                    src={source}
                    alt={author.name}
                    onError={() => markPhotoFailed(photoKey)}
                    className={hasMultipleAuthors
                      ? 'aspect-[4/3] max-h-[58vh] w-full rounded-lg object-contain'
                      : 'mx-auto max-h-[72vh] w-full rounded-lg object-contain'}
                  />
                  {caption && (
                    <figcaption className={`mt-3 rounded-lg bg-slate-900/80 px-2 py-3 text-center font-bold text-white ${hasMultipleAuthors ? 'text-sm md:text-xl' : 'text-xl md:text-2xl'}`}>
                      {caption}
                    </figcaption>
                  )}
                </figure>
              );
            })}
          </div>
        )}
        {!slideSource && (!isAuthorSlide || authors.length === 0) && (
          <div className="flex min-h-72 items-center justify-center text-red-300">
            Слайд интро недоступен
          </div>
        )}
      </div>

      {isAdmin && (
        <div className="rounded-xl border border-slate-700 bg-slate-800 p-4">
          <div className="mb-3 text-[10px] font-bold uppercase tracking-widest text-slate-500">
            Текст вступления
          </div>
          {introHtml ? (
            <div
              className="space-y-2 text-sm leading-relaxed text-slate-100 [&_h1]:mb-3 [&_h1]:text-lg [&_h1]:font-bold [&_li]:ml-5 [&_li]:list-disc [&_p]:mb-2"
              dangerouslySetInnerHTML={{ __html: introHtml }}
            />
          ) : (
            <div className="text-sm italic text-slate-500">
              В паке нет intro.md
            </div>
          )}
        </div>
      )}
    </div>
  );
}
