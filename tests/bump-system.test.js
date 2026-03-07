import { describe, it, expect } from 'vitest';
import { BUMP_DURATION, getBumpMessage } from '../engine.js';
import { readFileSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const bumps = JSON.parse(readFileSync(join(__dirname, '../bumps.json'), 'utf8'));

describe('bump system', () => {
  it('BUMP_DURATION is a positive number', () => {
    expect(BUMP_DURATION).toBeGreaterThan(0);
    expect(typeof BUMP_DURATION).toBe('number');
  });

  it('bump messages come from correct block pool', () => {
    // Morning bumps should come from morning + general pool
    const morningPool = [...bumps.morning, ...bumps.general];
    for (let i = 0; i < 20; i++) {
      const msg = getBumpMessage('morning', bumps);
      // The message may have [time] replaced, so check base text
      const matchesPool = morningPool.some(m =>
        msg === m || msg === m.replace('[time]', msg.match(/\d+:\d+[ap]m/)?.[0] || '')
      );
      expect(matchesPool).toBe(true);
    }
  });

  it('bump message replaces [time] placeholder', () => {
    // Use latenight which has "[time]" messages
    const date = new Date('2026-03-07T23:30:00');
    for (let i = 0; i < 50; i++) {
      const msg = getBumpMessage('latenight', bumps, date);
      expect(msg).not.toContain('[time]');
    }
  });
});
