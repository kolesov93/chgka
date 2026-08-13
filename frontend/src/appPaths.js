export function normalizeBasePath(value = '/') {
  if (typeof value !== 'string') return '/';

  const segments = value.trim().split('/').filter(Boolean);
  return segments.length ? `/${segments.join('/')}/` : '/';
}


export function appPath(path = '', basePath = '/') {
  const normalizedBase = normalizeBasePath(basePath);
  const suffix = typeof path === 'string'
    ? path.trim().replace(/^\/+|\/+$/g, '')
    : '';

  if (!suffix) return normalizedBase;
  return normalizedBase === '/' ? `/${suffix}` : `${normalizedBase}${suffix}`;
}


export const APP_BASE_PATH = normalizeBasePath(import.meta.env?.BASE_URL || '/');


export function currentAppPath(path = '') {
  return appPath(path, APP_BASE_PATH);
}
