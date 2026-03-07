import { describe, it, expect } from 'vitest';
import { shuffleForToday, getDaySeed } from '../engine.js';
import { readFileSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const morning = JSON.parse(readFileSync(join(__dirname, '../playlists/morning.json'), 'utf8'));

describe('playlist immutability', () => {
  it('shuffleForToday does not modify source array', () => {
    const original = JSON.parse(JSON.stringify(morning));
    shuffleForToday(morning, 'morning', new Set());
    expect(morning).toEqual(original);
  });

  it('removedVideos Set filters correctly', () => {
    const removed = new Set([morning[0].id]);
    const result = shuffleForToday(morning, 'morning', removed);
    expect(result.find(v => v.id === morning[0].id)).toBeUndefined();
    expect(result.length).toBe(morning.length - 1);
  });

  it('different days produce different shuffles', () => {
    const day1 = new Date('2026-03-07');
    const day2 = new Date('2026-03-08');
    const shuffle1 = shuffleForToday(morning, 'morning', new Set(), day1);
    const shuffle2 = shuffleForToday(morning, 'morning', new Set(), day2);
    // Same length but different order
    expect(shuffle1.length).toBe(shuffle2.length);
    const order1 = shuffle1.map(v => v.id).join(',');
    const order2 = shuffle2.map(v => v.id).join(',');
    expect(order1).not.toBe(order2);
  });
});
