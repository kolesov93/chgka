import {
  ENTRYPOINT_ADMIN_HISTORY,
  ENTRYPOINT_PLAYER,
  isAdminEntrypoint,
} from './entrypoint.js';

export const ADMIN_TOKEN_KEY = 'chgka_admin_token';
export const PLAYER_TOKEN_KEY = 'chgka_player_token';

const DEFAULT_AUTH_EXPIRED_MESSAGE =
  'Сессия ведущего истекла. Введите пароль ещё раз.';

export function getSessionRestorePayload(storage, entrypoint) {
  if (isAdminEntrypoint(entrypoint)) {
    const adminToken = storage.getItem(ADMIN_TOKEN_KEY);
    return adminToken
      ? {
          token: adminToken,
          ...(entrypoint === ENTRYPOINT_ADMIN_HISTORY
            ? { client_kind: 'history' }
            : {}),
        }
      : null;
  }
  if (entrypoint === ENTRYPOINT_PLAYER) {
    const playerToken = storage.getItem(PLAYER_TOKEN_KEY);
    return playerToken ? { player_token: playerToken } : null;
  }

  return null;
}

export function saveAdminToken(storage, token) {
  storage.setItem(ADMIN_TOKEN_KEY, token);
  storage.removeItem(PLAYER_TOKEN_KEY);
}

export function getAdminExpiryMs(data) {
  const value = data?.expires_at_ms;
  return Number.isFinite(value) && value > 0 ? value : null;
}

export function getExpiredAdminSession(data) {
  return {
    role: 'player',
    name: '',
    hasJoined: false,
    isPending: false,
    packInfo: null,
    adminQuestion: null,
    notice: data?.message || DEFAULT_AUTH_EXPIRED_MESSAGE,
  };
}
