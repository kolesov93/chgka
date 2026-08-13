import { APP_BASE_PATH, appPath } from './appPaths.js';

export const ENTRYPOINT_PLAYER = 'player';
export const ENTRYPOINT_ADMIN = 'admin';
export const ENTRYPOINT_ADMIN_HISTORY = 'admin-history';

export const PLAYER_ENTRY_PATH = appPath('play', APP_BASE_PATH);
export const ADMIN_ENTRY_PATH = appPath('admin', APP_BASE_PATH);
export const ADMIN_HISTORY_PATH = appPath('admin/history', APP_BASE_PATH);

const BASE_DOCUMENT_TITLE = 'Что? Где? Когда?';


export function entrypointDocumentTitle(entrypoint) {
  if (entrypoint === ENTRYPOINT_ADMIN) return `${BASE_DOCUMENT_TITLE} — Ведущий`;
  if (entrypoint === ENTRYPOINT_ADMIN_HISTORY) {
    return `${BASE_DOCUMENT_TITLE} — История игр`;
  }
  return BASE_DOCUMENT_TITLE;
}


export function entrypointLoginSubtitle(entrypoint) {
  if (entrypoint === ENTRYPOINT_ADMIN) return '[ведущий]';
  if (entrypoint === ENTRYPOINT_ADMIN_HISTORY) return '[история игр]';
  return null;
}


export function isAdminEntrypoint(entrypoint) {
  return entrypoint === ENTRYPOINT_ADMIN || entrypoint === ENTRYPOINT_ADMIN_HISTORY;
}


export function resolveEntrypoint(pathname, basePath = APP_BASE_PATH) {
  const path = typeof pathname === 'string' ? pathname : '';
  const playerPath = appPath('play', basePath);
  const adminPath = appPath('admin', basePath);
  const adminHistoryPath = appPath('admin/history', basePath);

  if (path === adminHistoryPath || path === `${adminHistoryPath}/`) {
    return {
      entrypoint: ENTRYPOINT_ADMIN_HISTORY,
      canonicalPath: adminHistoryPath,
    };
  }
  if (path === adminPath || path === `${adminPath}/`) {
    return {
      entrypoint: ENTRYPOINT_ADMIN,
      canonicalPath: adminPath,
    };
  }
  if (path === playerPath || path === `${playerPath}/`) {
    return {
      entrypoint: ENTRYPOINT_PLAYER,
      canonicalPath: playerPath,
    };
  }
  return {
    entrypoint: ENTRYPOINT_PLAYER,
    canonicalPath: playerPath,
  };
}
