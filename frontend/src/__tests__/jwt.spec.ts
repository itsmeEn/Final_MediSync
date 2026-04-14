import { describe, it, expect } from 'vitest';
import { isJwtExpired } from 'src/utils/jwt';

const base64Url = (input: string) =>
  Buffer.from(input, 'utf8')
    .toString('base64')
    .replace(/=/g, '')
    .replace(/\+/g, '-')
    .replace(/\//g, '_');

const makeJwt = (expSecondsFromNow: number) => {
  const header = base64Url(JSON.stringify({ alg: 'none', typ: 'JWT' }));
  const payload = base64Url(JSON.stringify({ exp: Math.floor(Date.now() / 1000) + expSecondsFromNow }));
  return `${header}.${payload}.`;
};

describe('jwt utils', () => {
  it('treats missing/invalid tokens as expired', () => {
    expect(isJwtExpired('')).toBe(true);
    expect(isJwtExpired('not-a-jwt')).toBe(true);
  });

  it('detects non-expired tokens', () => {
    const token = makeJwt(3600);
    expect(isJwtExpired(token, 0)).toBe(false);
  });

  it('detects expired tokens', () => {
    const token = makeJwt(-10);
    expect(isJwtExpired(token, 0)).toBe(true);
  });
});

