import { api } from 'src/boot/axios';

export const getMediaUrl = (path: string | undefined): string => {
  if (!path) return '';
  if (path.startsWith('http://') || path.startsWith('https://')) return path;

  const baseURL = api.defaults.baseURL || `http://${window.location.hostname}:8000`;
  let origin = baseURL;
  try {
    origin = new URL(baseURL).origin;
  } catch {
    origin = baseURL.replace(/\/+$/, '');
  }

  if (path.startsWith('/')) return `${origin}${path}`;
  return `${origin}/${path}`;
};

