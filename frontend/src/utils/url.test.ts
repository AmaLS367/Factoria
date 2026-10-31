import { describe, expect, it } from 'vitest';
import { isSafeUrl } from './url';

describe('isSafeUrl', () => {
  it('returns true for valid http URLs', () => {
    expect(isSafeUrl('http://example.com')).toBe(true);
    expect(isSafeUrl('http://example.com/path?query=param#hash')).toBe(true);
  });

  it('returns true for valid https URLs', () => {
    expect(isSafeUrl('https://example.com')).toBe(true);
    expect(isSafeUrl('https://sub.domain.org/path')).toBe(true);
  });

  it('returns false for unsafe or unsupported protocols', () => {
    expect(isSafeUrl('ftp://example.com')).toBe(false);
    expect(isSafeUrl('javascript:alert(1)')).toBe(false);
    expect(isSafeUrl('file:///etc/passwd')).toBe(false);
    expect(isSafeUrl('data:text/html,<script>alert(1)</script>')).toBe(false);
  });

  it('returns false for invalid URLs or non-URL strings', () => {
    expect(isSafeUrl('')).toBe(false);
    expect(isSafeUrl('not a url')).toBe(false);
    expect(isSafeUrl('/relative/path')).toBe(false);
  });
});
