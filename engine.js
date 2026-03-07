// snow-globe engine — pure functions extracted for testability
// This module is imported by app.js and by tests.

export const BUMP_DURATION = 12; // seconds per bump card

export const BLOCKS = [
  { name: 'morning',    start: 8,  end: 12, label: 'morning' },
  { name: 'afternoon',  start: 12, end: 18, label: 'afternoon' },
  { name: 'evening',    start: 18, end: 22, label: 'evening' },
  { name: 'latenight',  start: 22, end: 26, label: 'late night' },  // 26 = 2am next day
  { name: 'deadhours',  start: 2,  end: 8,  label: 'dead hours' },
];

// Simple mulberry32 PRNG
export function seededRandom(seed) {
  return function() {
    seed |= 0; seed = seed + 0x6D2B79F5 | 0;
    let t = Math.imul(seed ^ seed >>> 15, 1 | seed);
    t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
    return ((t ^ t >>> 14) >>> 0) / 4294967296;
  };
}

export function getDaySeed(date) {
  const d = date || new Date();
  return d.getFullYear() * 10000 + (d.getMonth() + 1) * 100 + d.getDate();
}

export function shuffleForToday(playlist, blockName, removedVideos, date) {
  const seed = getDaySeed(date) + blockName.charCodeAt(0) * 1000;
  const rng = seededRandom(seed);
  const removed = removedVideos || new Set();
  const shuffled = [...playlist].filter(v => !removed.has(v.id));
  for (let i = shuffled.length - 1; i > 0; i--) {
    const j = Math.floor(rng() * (i + 1));
    [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
  }
  return shuffled;
}

export function computeSchedulePosition(playlist, elapsedSec) {
  let totalCycleDuration = 0;
  for (const v of playlist) {
    totalCycleDuration += v.duration + BUMP_DURATION;
  }

  const posInCycle = ((elapsedSec % totalCycleDuration) + totalCycleDuration) % totalCycleDuration;

  let cursor = 0;
  for (let i = 0; i < playlist.length; i++) {
    const video = playlist[i];

    if (posInCycle < cursor + video.duration) {
      return {
        type: 'video',
        video: video,
        index: i,
        seekTo: posInCycle - cursor,
        remainingSec: video.duration - (posInCycle - cursor),
      };
    }
    cursor += video.duration;

    if (posInCycle < cursor + BUMP_DURATION) {
      return {
        type: 'bump',
        nextVideo: playlist[(i + 1) % playlist.length],
        nextIndex: (i + 1) % playlist.length,
        remainingSec: BUMP_DURATION - (posInCycle - cursor),
      };
    }
    cursor += BUMP_DURATION;
  }

  return { type: 'video', video: playlist[0], index: 0, seekTo: 0, remainingSec: playlist[0].duration };
}

export function getCurrentBlock(date) {
  const now = date || new Date();
  let hour = now.getHours();

  for (const block of BLOCKS) {
    if (block.name === 'latenight') {
      if (hour >= 22 || hour < 2) return block;
    } else if (block.name === 'deadhours') {
      if (hour >= 2 && hour < 8) return block;
    } else {
      if (hour >= block.start && hour < block.end) return block;
    }
  }
  return BLOCKS[4]; // deadhours
}

export function getBlockStartTime(block, now) {
  const date = now || new Date();
  const start = new Date(date);
  start.setMinutes(0, 0, 0);

  if (block.name === 'latenight') {
    if (date.getHours() < 2) {
      start.setDate(start.getDate() - 1);
    }
    start.setHours(22);
  } else {
    start.setHours(block.start);
  }
  return start;
}

export function formatTime(date) {
  let h = date.getHours();
  const m = date.getMinutes().toString().padStart(2, '0');
  const ampm = h >= 12 ? 'pm' : 'am';
  h = h % 12 || 12;
  return `${h}:${m}${ampm}`;
}

export function getBumpMessage(blockName, bumps, date) {
  const now = date || new Date();
  const timeStr = formatTime(now);

  const pool = [];
  if (bumps[blockName]) pool.push(...bumps[blockName]);
  if (bumps.general) pool.push(...bumps.general);

  const msg = pool[Math.floor(Math.random() * pool.length)];
  return msg.replace('[time]', timeStr);
}
