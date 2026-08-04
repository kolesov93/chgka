import io from 'socket.io-client';

const backendOrigin = import.meta.env.DEV ? 'http://localhost:8000' : '';

export const mediaUrl = (mediaId) => `${backendOrigin}/media/${encodeURIComponent(mediaId)}`;

export const socket = io(backendOrigin || '/', {
  transports: ['websocket'],
});
