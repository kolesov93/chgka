import { APP_BASE_PATH, appPath } from './appPaths.js';

export const DEVELOPMENT_BACKEND_ORIGIN = 'http://localhost:8000';


export function backendHttpUrl(
  path,
  {
    isDevelopment = false,
    basePath = APP_BASE_PATH,
    developmentOrigin = DEVELOPMENT_BACKEND_ORIGIN,
  } = {},
) {
  const publicPath = appPath(path, isDevelopment ? '/' : basePath);
  return isDevelopment ? `${developmentOrigin}${publicPath}` : publicPath;
}


export function backendSocketPath({ isDevelopment = false, basePath = APP_BASE_PATH } = {}) {
  return appPath('socket.io', isDevelopment ? '/' : basePath);
}
