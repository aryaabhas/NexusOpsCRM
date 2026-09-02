import { describe, it, expect, beforeAll } from 'vitest';
import { escHtml, formatDate } from './ui';

// Mock browser globals needed for ui.js helper execution
beforeAll(() => {
  global.document = {
    createElement: () => ({
      innerHTML: '',
      get value() {
        return this.innerHTML;
      }
    })
  };
});

describe('escHtml Utility', () => {
  it('should correctly escape unsafe HTML characters', () => {
    const raw = '<script>alert("xss")</script>';
    const escaped = escHtml(raw);
    expect(escaped).toBe('&lt;script&gt;alert(&quot;xss&quot;)&lt;/script&gt;');
  });

  it('should return empty string for null/undefined inputs', () => {
    expect(escHtml(undefined)).toBe('');
    expect(escHtml(null)).toBe('');
  });
});

describe('formatDate Utility', () => {
  it('should format valid ISO dates to DD-MMM-YYYY format', () => {
    const rawDate = '2026-08-17T00:00:00.000Z';
    const formatted = formatDate(rawDate);
    // Since Intl.DateTimeFormat 'en-IN' returns format: 17-Aug-2026 or 17 Aug 2026
    expect(formatted).toMatch(/17[- ]Aug[- ]2026/);
  });

  it('should return raw date string if formatting fails', () => {
    const invalidDate = 'not-a-date';
    expect(formatDate(invalidDate)).toBe('not-a-date');
  });

  it('should return empty string for empty inputs', () => {
    expect(formatDate('')).toBe('');
    expect(formatDate(undefined)).toBe('');
  });
});
