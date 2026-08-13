import { currentAppPath } from './appPaths.js';

export const AUTHOR_FALLBACK_SOURCE = currentAppPath('images/intro/author-fallback.png');
export const SECTOR_THIRTEEN_SOURCE = currentAppPath('images/intro/13.png');


export function isAuthorMedia(media) {
  return media?.presentation_kind === 'author';
}


export function authorMediaCaption(media) {
  if (!isAuthorMedia(media) || media.author_asset === 'sector13') return null;
  const name = typeof media.author_name === 'string' ? media.author_name.trim() : '';
  if (!name) return null;
  const city = typeof media.author_city === 'string' ? media.author_city.trim() : '';
  return city ? `${name} (${city})` : name;
}


export function authorMediaSource(media, resolvedPhotoUrl = null) {
  if (!isAuthorMedia(media)) return resolvedPhotoUrl;
  if (media.author_asset === 'sector13') return SECTOR_THIRTEEN_SOURCE;
  return media.has_photo && resolvedPhotoUrl
    ? resolvedPhotoUrl
    : AUTHOR_FALLBACK_SOURCE;
}
