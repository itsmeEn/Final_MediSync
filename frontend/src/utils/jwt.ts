type JwtPayload = {
  exp?: number;
  [key: string]: unknown;
};

const base64UrlToBase64 = (value: string) => value.replace(/-/g, '+').replace(/_/g, '/');

const decodeBase64 = (value: string): string => {
  const normalized = base64UrlToBase64(value);
  const padded = normalized.padEnd(normalized.length + ((4 - (normalized.length % 4)) % 4), '=');

  if (typeof atob === 'function') {
    return atob(padded);
  }

  const b = (globalThis as unknown as { Buffer?: typeof Buffer }).Buffer;
  if (b) {
    return b.from(padded, 'base64').toString('binary');
  }

  throw new Error('No base64 decoder available');
};

export const decodeJwtPayload = (token: string): JwtPayload | null => {
  try {
    const parts = token.split('.');
    if (parts.length < 2) return null;
    const json = decodeBase64(parts[1] || '');
    return JSON.parse(json) as JwtPayload;
  } catch {
    return null;
  }
};

export const isJwtExpired = (token: string, leewaySeconds = 30): boolean => {
  const payload = decodeJwtPayload(token);
  const exp = typeof payload?.exp === 'number' ? payload.exp : null;
  if (!exp) return true;
  const nowSeconds = Math.floor(Date.now() / 1000);
  return nowSeconds >= exp - leewaySeconds;
};

