export const ENTRYPOINT_PLAYER = 'player';
export const ENTRYPOINT_ADMIN = 'admin';

export const PLAYER_ENTRY_PATH = '/play';
export const ADMIN_ENTRY_PATH = '/admin';


export function resolveEntrypoint(pathname) {
  const path = typeof pathname === 'string' ? pathname : '';
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
