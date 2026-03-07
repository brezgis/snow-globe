import { describe, it, expect } from 'vitest';
import {
  computeSchedulePosition, getCurrentBlock, getBlockStartTime,
  BUMP_DURATION, shuffleForToday,
} from '../engine.js';

const playlist = [
  { id: 'a', title: 'Video A', duration: 300 },
  { id: 'b', title: 'Video B', duration: 600 },
  { id: 'c', title: 'Video C', duration: 120 },
];

describe('computeSchedulePosition', () => {
  it('returns first video at elapsed=0', () => {
    const pos = computeSchedulePosition(playlist, 0);
    expect(pos.type).toBe('video');
    expect(pos.video.id).toBe('a');
    expect(pos.seekTo).toBe(0);
  });

  it('returns correct seekTo mid-video', () => {
    const pos = computeSchedulePosition(playlist, 150);
    expect(pos.type).toBe('video');
    expect(pos.video.id).toBe('a');
    expect(pos.seekTo).toBe(150);
    expect(pos.remainingSec).toBe(150);
  });

  it('returns bump between videos', () => {
    // After video A (300s), bump starts
    const pos = computeSchedulePosition(playlist, 305);
    expect(pos.type).toBe('bump');
    expect(pos.nextVideo.id).toBe('b');
    expect(pos.remainingSec).toBeCloseTo(BUMP_DURATION - 5);
  });

  it('returns second video after first bump', () => {
    // Video A (300) + bump (12) = 312
    const pos = computeSchedulePosition(playlist, 312);
    expect(pos.type).toBe('video');
    expect(pos.video.id).toBe('b');
    expect(pos.seekTo).toBe(0);
  });

  it('wraps around at cycle end (midnight crossover)', () => {
    // Total cycle: (300+12) + (600+12) + (120+12) = 1056
    const totalCycle = 300 + 12 + 600 + 12 + 120 + 12;
    expect(totalCycle).toBe(1056);

    // One full cycle + 10s should be same as 10s
    const pos1 = computeSchedulePosition(playlist, 10);
    const pos2 = computeSchedulePosition(playlist, totalCycle + 10);
    expect(pos2.video.id).toBe(pos1.video.id);
    expect(pos2.seekTo).toBeCloseTo(pos1.seekTo);
  });

  it('handles negative elapsed (DST spring-forward edge)', () => {
    // computeSchedulePosition uses modulo, should handle gracefully
    const pos = computeSchedulePosition(playlist, -100);
    expect(pos.type).toBeDefined();
    expect(['video', 'bump']).toContain(pos.type);
  });
});

describe('getCurrentBlock', () => {
  it('returns morning at 10am', () => {
    const d = new Date('2026-03-07T10:00:00');
    expect(getCurrentBlock(d).name).toBe('morning');
  });

  it('returns latenight at 23:00', () => {
    const d = new Date('2026-03-07T23:00:00');
    expect(getCurrentBlock(d).name).toBe('latenight');
  });

  it('returns latenight at 1am (midnight crossover)', () => {
    const d = new Date('2026-03-08T01:00:00');
    expect(getCurrentBlock(d).name).toBe('latenight');
  });

  it('returns deadhours at 4am', () => {
    const d = new Date('2026-03-08T04:00:00');
    expect(getCurrentBlock(d).name).toBe('deadhours');
  });
});

describe('bump insertion timing', () => {
  it('bump duration matches BUMP_DURATION constant', () => {
    // After video A ends, bump lasts exactly BUMP_DURATION seconds
    const bumpStart = computeSchedulePosition(playlist, 300);
    expect(bumpStart.type).toBe('bump');
    expect(bumpStart.remainingSec).toBe(BUMP_DURATION);

    const bumpEnd = computeSchedulePosition(playlist, 300 + BUMP_DURATION - 0.001);
    expect(bumpEnd.type).toBe('bump');

    const afterBump = computeSchedulePosition(playlist, 300 + BUMP_DURATION);
    expect(afterBump.type).toBe('video');
    expect(afterBump.video.id).toBe('b');
  });
});
