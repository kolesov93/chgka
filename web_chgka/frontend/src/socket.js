import io from 'socket.io-client';
import {
  DEVELOPMENT_BACKEND_ORIGIN,
  backendHttpUrl,
  backendSocketPath,
} from './backendUrls.js';

const isDevelopment = import.meta.env.DEV;
const backendOrigin = isDevelopment ? DEVELOPMENT_BACKEND_ORIGIN : '';

export const mediaUrl = (mediaId) => backendHttpUrl(
  `media/${encodeURIComponent(mediaId)}`,
  { isDevelopment },
);
export const introAuthorPhotoUrl = (sector, slot) => (
  backendHttpUrl(
    `intro/author-photo/${encodeURIComponent(sector)}/${encodeURIComponent(slot)}`,
    { isDevelopment },
  )
);

export const socket = io(backendOrigin || '/', {
  path: backendSocketPath({ isDevelopment }),
  transports: ['websocket'],
});
