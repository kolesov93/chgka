export const ENTRYPOINT_PLAYER = 'player';
export const ENTRYPOINT_ADMIN = 'admin';
export const ENTRYPOINT_ADMIN_HISTORY = 'admin-history';

export const PLAYER_ENTRY_PATH = '/play';
export const ADMIN_ENTRY_PATH = '/admin';
export const ADMIN_HISTORY_PATH = '/admin/history';


export function isAdminEntrypoint(entrypoint) {
  return entrypoint === ENTRYPOINT_ADMIN || entrypoint === ENTRYPOINT_ADMIN_HISTORY;
}


export function resolveEntrypoint(pathname) {
  const path = typeof pathname === 'string' ? pathname : '';
  if (path === ADMIN_HISTORY_PATH || path === `${ADMIN_HISTORY_PATH}/`) {
    return {
      entrypoint: ENTRYPOINT_ADMIN_HISTORY,
      canonicalPath: ADMIN_HISTORY_PATH,
    };
  }
  if (path === ADMIN_ENTRY_PATH || path === `${ADMIN_ENTRY_PATH}/`) {
    return {
      entrypoint: ENTRYPOINT_ADMIN,
      canonicalPath: ADMIN_ENTRY_PATH,
    };
  }
  if (path === PLAYER_ENTRY_PATH || path === `${PLAYER_ENTRY_PATH}/`) {
    return {
      entrypoint: ENTRYPOINT_PLAYER,
      canonicalPath: PLAYER_ENTRY_PATH,
    };
  }
  return {
    entrypoint: ENTRYPOINT_PLAYER,
    canonicalPath: PLAYER_ENTRY_PATH,
  };
}
