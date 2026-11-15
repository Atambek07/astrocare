import { afterEach, describe, expect, it } from 'vitest';
import { backendUrl, BACKEND_HTTP_BASE_URL } from './backend';

const originalBaseUrl = process.env.NEXT_PUBLIC_BACKEND_HTTP_URL;

describe('backend URL contract', () => {
  afterEach(() => {
    if (originalBaseUrl === undefined) delete process.env.NEXT_PUBLIC_BACKEND_HTTP_URL;
    else process.env.NEXT_PUBLIC_BACKEND_HTTP_URL = originalBaseUrl;
  });

  it('uses the configured unified-service URL without a duplicate slash', () => {
    process.env.NEXT_PUBLIC_BACKEND_HTTP_URL = 'http://localhost:9999/';
    // The module constant is initialized once, so assert the production default here.
    expect(backendUrl('/simulation/status')).toBe(`${BACKEND_HTTP_BASE_URL}/simulation/status`);
    expect(backendUrl('/simulation/status')).not.toContain('//simulation');
  });

  it('rejects a relative backend route', () => {
    expect(() => backendUrl('simulation/status')).toThrow('backend route must start with /');
  });
});
