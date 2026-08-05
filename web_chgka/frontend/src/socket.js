import io from 'socket.io-client';

const backendOrigin = import.meta.env.DEV ? 'http://localhost:8000' : '';

export const mediaUrl = (mediaId) => `${backendOrigin}/media/${encodeURIComponent(mediaId)}`;
export const introAuthorPhotoUrl = (sector, slot) => (
  `${backendOrigin}/intro/author-photo/${encodeURIComponent(sector)}/${encodeURIComponent(slot)}`
);

export const socket = io(backendOrigin || '/', {
  transports: ['websocket'],
});
