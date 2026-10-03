// snow-globe — schedule engine + player logic

(function () {
  'use strict';

  // ── Config ──────────────────────────────────────
  const BUMP_DURATION = 12; // seconds per bump card
  const NEXT_CHANCE = 0.5; // odds a given bump is an "up next" card instead of a text card

  const BLOCKS = [
    { name: 'morning',    start: 8,  end: 12, label: 'morning' },
    { name: 'afternoon',  start: 12, end: 18, label: 'afternoon' },
    { name: 'evening',    start: 18, end: 22, label: 'evening' },
    { name: 'latenight',  start: 22, end: 26, label: 'late night' },  // 26 = 2am next day
    { name: 'deadhours',  start: 2,  end: 8,  label: 'dead hours' },
  ];

  // ── State ───────────────────────────────────────
  let playlists = {};
  let bumps = {};
  let player = null;
  let playerReady = false;
  let isMuted = false;
  let currentVideoId = null;
  let bumpTimeout = null;
  let scheduleInterval = null;
  let isShowingBump = false;
  let pendingHideBump = false;
  let endedVideoId = null; // finished early (real length < listed duration)
  const removedVideos = new Set();

  // ── DOM refs ────────────────────────────────────
  const $bump = document.getElementById('bump');
  const $bumpText = document.getElementById('bump-text');
  const $nextNow = document.querySelector('#bump-next .nx-now');
  const $nextLater = document.querySelector('#bump-next .nx-later');
  const $blockLabel = document.getElementById('block-label');
  const $clock = document.getElementById('clock');
  const $muteBtn = document.getElementById('mute-btn');
  const $static = document.getElementById('static');
  const $loading = document.getElementById('loading');

  // ── Init ────────────────────────────────────────
  async function init() {
    drawStatic();
    await loadData();
    initYouTube();
    startClock();

    $muteBtn.addEventListener('click', function(e) {
      e.stopPropagation(); // prevent document-level unmuteOnClick from firing
      toggleMute();
    });

    setupGuideSheet();
    setupIdleUI();

    // open the snow-guide directly via /#sheet (handy for linking / previews)
    if (location.hash === '#sheet') setTimeout(sgOpen, 300);

    // show UI labels briefly on load
    setTimeout(() => {
      $blockLabel.classList.add('visible');
      $clock.classList.add('visible');
    }, 2000);

    // Preview the "up next" card directly: open /#next
    if (location.hash === '#next') {
      setTimeout(() => {
        $static.classList.add('off');
        if ($loading) $loading.style.display = 'none';
        window.testNext(600);
      }, 400);
    }
  }

  async function loadData() {
    const blockNames = ['morning', 'afternoon', 'evening', 'latenight', 'deadhours'];
    const fetches = blockNames.map(name =>
      fetch(`playlists/${name}.json`).then(r => {
        if (!r.ok) throw new Error(`Failed to load ${name}.json (${r.status})`);
        return r.json();
      }).then(data => {
        playlists[name] = data;
      })
    );
    fetches.push(
      fetch('bumps.json').then(r => {
        if (!r.ok) throw new Error(`Failed to load bumps.json (${r.status})`);
        return r.json();
      }).then(data => {
        bumps = data;
      })
    );
    try {
      await Promise.all(fetches);
    } catch (err) {
      console.error('loadData failed:', err);
      if ($loading) $loading.textContent = 'failed to load channel data — try refreshing';
      throw err;
    }
  }

  // ── Time helpers ────────────────────────────────
  function getCurrentBlock() {
    const now = new Date();
    let hour = now.getHours();

    // Handle late night wrap (22-26 means 22, 23, 0, 1)
    for (const block of BLOCKS) {
      if (block.name === 'latenight') {
        if (hour >= 22 || hour < 2) return block;
      } else if (block.name === 'deadhours') {
        if (hour >= 2 && hour < 8) return block;
      } else {
        if (hour >= block.start && hour < block.end) return block;
      }
    }
    // fallback
    return BLOCKS[4]; // deadhours
  }

  function getBlockStartTime(block) {
    const now = new Date();
    const start = new Date(now);
    start.setMinutes(0, 0, 0);

    if (block.name === 'latenight') {
      // If it's 0 or 1, the block started at 22 yesterday
      if (now.getHours() < 2) {
        start.setDate(start.getDate() - 1);
      }
      start.setHours(22);
    } else {
      start.setHours(block.start);
    }
    return start;
  }

  function formatTime(date) {
    let h = date.getHours();
    const m = date.getMinutes().toString().padStart(2, '0');
    const ampm = h >= 12 ? 'pm' : 'am';
    h = h % 12 || 12;
    return `${h}:${m}${ampm}`;
  }

  // ── Daily Shuffle ────────────────────────────────
  // Deterministic shuffle seeded by date — same order for everyone on the same day,
  // different order each day.
  function seededRandom(seed) {
    // Simple mulberry32 PRNG
    return function() {
      seed |= 0; seed = seed + 0x6D2B79F5 | 0;
      let t = Math.imul(seed ^ seed >>> 15, 1 | seed);
      t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
      return ((t ^ t >>> 14) >>> 0) / 4294967296;
    };
  }

  function getDaySeed(d) {
    const now = d || new Date();
    return now.getFullYear() * 10000 + (now.getMonth() + 1) * 100 + now.getDate();
  }

  // Seeded by the date the *block* started, so late night (10pm–2am) keeps one
  // order across midnight instead of reshuffling mid-show at 12:00am.
  function shuffleForToday(playlist, blockName, blockStart) {
    const block = BLOCKS.find(b => b.name === blockName);
    const start = blockStart || (block ? getBlockStartTime(block) : null);
    const seed = getDaySeed(start) + blockName.charCodeAt(0) * 1000;
    const rng = seededRandom(seed);
    const shuffled = [...playlist].filter(v => !removedVideos.has(v.id));
    for (let i = shuffled.length - 1; i > 0; i--) {
      const j = Math.floor(rng() * (i + 1));
      [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
    }
    return shuffled;
  }

  // ── Schedule Engine ─────────────────────────────
  // Given a playlist and elapsed seconds since block start,
  // figure out which video should be playing and at what offset.
  // Bumps are inserted between each video.
  function computeSchedulePosition(playlist, elapsedSec) {
    // Build a timeline: [video, bump, video, bump, ...]
    let totalCycleDuration = 0;
    for (const v of playlist) {
      totalCycleDuration += v.duration + BUMP_DURATION;
    }

    // Where are we in the cycle?
    const posInCycle = ((elapsedSec % totalCycleDuration) + totalCycleDuration) % totalCycleDuration;

    let cursor = 0;
    for (let i = 0; i < playlist.length; i++) {
      const video = playlist[i];

      // Video segment
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

      // Bump segment
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

    // Shouldn't get here, but fallback
    return { type: 'video', video: playlist[0], index: 0, seekTo: 0, remainingSec: playlist[0].duration };
  }

  function syncToSchedule() {
    const block = getCurrentBlock();
    const playlist = playlists[block.name];
    if (!playlist || !playlist.length) return;

    // Shuffle playlist deterministically for today
    const todaysPlaylist = shuffleForToday(playlist, block.name);

    $blockLabel.textContent = block.label;

    const blockStart = getBlockStartTime(block);
    const now = new Date();
    const elapsed = (now - blockStart) / 1000;

    const pos = computeSchedulePosition(todaysPlaylist, elapsed);

    if (pos.type === 'bump' || (pos.type === 'video' && pos.video.id === endedVideoId)) {
      showBump(block.name, pos.remainingSec);
    } else {
      endedVideoId = null;
      // Start loading video behind the bump; hideBump is called when video plays
      if (isShowingBump) {
        pendingHideBump = true;
        // Fallback: hide bump after 3s even if player doesn't fire
        setTimeout(() => { if (pendingHideBump) { hideBump(); pendingHideBump = false; } }, 3000);
      } else {
        pendingHideBump = false;
      }
      playVideo(pos.video.id, pos.seekTo, pos.video.title);
    }

    // Schedule next check — always resync within 30s as a safety net
    clearTimeout(bumpTimeout);
    const checkInMs = (pos.remainingSec + 0.5) * 1000;
    bumpTimeout = setTimeout(syncToSchedule, Math.min(checkInMs, 15000));
  }

  // ── YouTube Player ──────────────────────────────
  function initYouTube() {
    const tag = document.createElement('script');
    tag.src = 'https://www.youtube.com/iframe_api';
    document.head.appendChild(tag);
  }

  window.onYouTubeIframeAPIReady = function () {
    // Compute the initial video BEFORE creating the player.
    // Without an initial videoId, YouTube shows a recommendation grid
    // instead of a blank player, and loadVideoById may not recover.
    const block = getCurrentBlock();
    const playlist = playlists[block.name];
    let initialVideoId;
    let initialStart = 0;

    if (playlist && playlist.length) {
      const todaysPlaylist = shuffleForToday(playlist, block.name);
      const blockStart = getBlockStartTime(block);
      const elapsed = (new Date() - blockStart) / 1000;
      const pos = computeSchedulePosition(todaysPlaylist, elapsed);
      if (pos.type === 'video') {
        initialVideoId = pos.video.id;
        initialStart = Math.floor(pos.seekTo);
      } else if (pos.nextVideo) {
        // We're mid-bump — load the next video paused behind the bump overlay.
        initialVideoId = pos.nextVideo.id;
        initialStart = 0;
      }
    }

    const playerConfig = {
      width: '100%',
      height: '100%',
      playerVars: {
        autoplay: 1,
        controls: 0,
        disablekb: 1,
        fs: 0,
        iv_load_policy: 3,
        modestbranding: 1,
        rel: 0,
        showinfo: 0,
        mute: 1,
        origin: window.location.origin,
      },
      events: {
        onReady: onPlayerReady,
        onStateChange: onPlayerStateChange,
        onError: onPlayerError,
      },
    };

    if (initialVideoId) {
      playerConfig.videoId = initialVideoId;
      playerConfig.playerVars.start = initialStart;
    }

    player = new YT.Player('yt-player', playerConfig);
  };

  function onPlayerReady() {
    playerReady = true;
    // Start muted (browser requirement), show unmute hint
    player.mute();
    isMuted = true;
    $muteBtn.textContent = '🔇';
    
    // Activate click guard
    const guard = document.getElementById('click-guard');
    if (guard) guard.classList.add('active');
    
    // Click anywhere to unmute (first interaction)
    function unmuteOnClick() {
      player.unMute();
      isMuted = false;
      $muteBtn.textContent = '🔊';
      const hint = document.getElementById('unmute-hint');
      if (hint) hint.style.opacity = '0';
      setTimeout(() => { if (hint) hint.remove(); }, 1000);
      document.removeEventListener('click', unmuteOnClick);
    }
    document.addEventListener('click', unmuteOnClick);
    // Dismiss static
    setTimeout(() => {
      $static.classList.add('off');
      $loading.style.display = 'none';
    }, 800);
    syncToSchedule();
  }

  // Watch for near-end to skip before YouTube shows end screen
  let endCheckInterval = null;

  function startEndCheck() {
    clearInterval(endCheckInterval);
    endCheckInterval = setInterval(() => {
      if (!playerReady || isShowingBump) return;
      try {
        const duration = player.getDuration();
        const current = player.getCurrentTime();
        if (duration > 0 && current > 0 && (duration - current) < 3) {
          // Less than 3 seconds left — force transition now
          clearInterval(endCheckInterval);
          endedVideoId = currentVideoId;
          currentVideoId = null;
          syncToSchedule();
        }
      } catch(e) {}
    }, 500);
  }

  function onPlayerStateChange(event) {
    if (event.data === 1) {
      // Playing — hide bump now that video is rendering
      if (pendingHideBump) { hideBump(); pendingHideBump = false; }
      startEndCheck();
    }
    if (event.data === 0) {
      // Video ended naturally — resync
      clearInterval(endCheckInterval);
      endedVideoId = currentVideoId;
      syncToSchedule();
    }
  }

  function onPlayerError(event) {
    // Skip broken video — remove from playlist and resync
    console.warn('Player error:', event.data, 'video:', currentVideoId);
    if (currentVideoId) {
      console.warn('Removing unavailable video:', currentVideoId);
      removedVideos.add(currentVideoId);
    }
    currentVideoId = null;
    setTimeout(syncToSchedule, 500);
  }

  let nowPlayingTimeout = null;
  const $nowPlaying = document.getElementById('now-playing');

  function showNowPlaying(title) {
    if (!$nowPlaying || !title) return;
    $nowPlaying.textContent = title;
    $nowPlaying.style.opacity = '1';
    clearTimeout(nowPlayingTimeout);
    nowPlayingTimeout = setTimeout(() => {
      $nowPlaying.style.opacity = '0';
    }, 5000);
  }

  function playVideo(videoId, seekTo, title) {
    if (!playerReady) return;

    if (currentVideoId !== videoId) {
      currentVideoId = videoId;
      showNowPlaying(title);
      player.loadVideoById({
        videoId: videoId,
        startSeconds: Math.floor(seekTo),
      });
    } else {
      // Same video, just correct seek if drifted
      const currentTime = player.getCurrentTime();
      if (Math.abs(currentTime - seekTo) > 3) {
        player.seekTo(seekTo, true);
      }
    }

    if (isMuted) player.mute();
    else player.unMute();
  }

  // ── Bump Cards ──────────────────────────────────
  const recentBumps = [];
  function getBumpMessage(blockName) {
    const now = new Date();
    const timeStr = formatTime(now);

    // Pick from block-specific or general pool
    const pool = [];
    if (bumps[blockName]) pool.push(...bumps[blockName]);
    if (bumps.general) pool.push(...bumps.general);

    const fresh = pool.filter(m => !recentBumps.includes(m));
    const pick = fresh.length ? fresh : pool;
    const msg = pick[Math.floor(Math.random() * pick.length)];
    recentBumps.push(msg);
    if (recentBumps.length > Math.min(12, Math.floor(pool.length / 2))) recentBumps.shift();
    return msg.replace('[time]', timeStr);
  }

  // ── Bump Audio ───────────────────────────────────
  const BUMP_AUDIO_COUNT = 23;
  let bumpAudio = null;

  function playBumpAudio() {
    const idx = Math.floor(Math.random() * BUMP_AUDIO_COUNT) + 1;
    const padded = idx.toString().padStart(2, '0');
    bumpAudio = new Audio(`audio/bump_${padded}.mp3`);
    bumpAudio.volume = 0.5;
    bumpAudio.onerror = () => { bumpAudio = null; }; // suppress browser error UI
    // Delay audio slightly to sync with CSS opacity fade-in (1.2s transition)
    setTimeout(() => {
      if (bumpAudio) bumpAudio.play().catch(() => { bumpAudio = null; });
    }, 300);
  }

  function stopBumpAudio() {
    if (bumpAudio) {
      bumpAudio.pause();
      bumpAudio.currentTime = 0;
      bumpAudio = null;
    }
  }

  // ── TV Guide bump ────────────────────────────────
  function escHtml(s) {
    return String(s).replace(/[&<>"']/g, c => (
      { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]
    ));
  }

  // Three half-hour slot labels starting from the current half hour.
  function guideSlots() {
    const base = new Date();
    base.setSeconds(0, 0);
    base.setMinutes(base.getMinutes() < 30 ? 0 : 30);
    const slots = [];
    for (let i = 0; i < 3; i++) {
      const d = new Date(base.getTime() + i * 30 * 60000);
      const h = d.getHours() % 12 || 12;
      const m = d.getMinutes().toString().padStart(2, '0');
      slots.push(`${h}:${m}`);
    }
    return slots;
  }

  function pickShows(pool, n, used) {
    const out = [];
    let guard = 0;
    while (out.length < n && guard < 200) {
      const s = pool[Math.floor(Math.random() * pool.length)];
      if (!used.has(s)) { used.add(s); out.push(s); }
      guard++;
    }
    while (out.length < n) out.push('—');
    return out;
  }

  function shuffled(arr) {
    const a = [...arr];
    for (let i = a.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [a[i], a[j]] = [a[j], a[i]];
    }
    return a;
  }

  // "La Jetée – Chris Marker (1962)" → title "La Jetée", sub "Chris Marker (1962)"
  function splitShow(title) {
    const t = sgSplitTitle(title).name;
    const i = t.indexOf(' – ');
    return i > 0 ? { title: t.slice(0, i), sub: t.slice(i + 3) } : { title: t, sub: '' };
  }
  function fillNext($row, prog) {
    $row.classList.toggle('empty', !prog);
    if (!prog) return;
    const s = splitShow(prog.title);
    $row.querySelector('.nx-title').textContent = s.title;
    $row.querySelector('.nx-sub').textContent = s.sub;
  }
  // Returns true if the card was rendered, false to fall back to a text bump.
  function renderUpNext() {
    // programs that haven't started yet — during a bump, the next one is next
    const rows = upcomingPrograms(4).filter(r => r.start > Date.now());
    if (!rows.length || !$nextNow) return false;
    fillNext($nextNow, rows[0]);
    fillNext($nextLater, rows[1]);
    return true;
  }

  // ── Bump show/hide ───────────────────────────────
  function showBump(blockName, remainingSec) {
    if (isShowingBump) return;
    isShowingBump = true;

    // Pause/mute the player during bump
    if (playerReady && player.getPlayerState && player.getPlayerState() === 1) {
      player.pauseVideo();
    }

    // About half the time, an Adult Swim-style "next / later" card.
    if (Math.random() < NEXT_CHANCE && renderUpNext()) {
      $bump.classList.add('next-mode');
    } else {
      $bumpText.textContent = getBumpMessage(blockName);
    }

    $bump.classList.add('active');
    playBumpAudio();
    currentVideoId = null; // force reload after bump
  }

  function hideBump() {
    if (!isShowingBump) return;
    $bump.classList.remove('active');
    $bump.classList.remove('next-mode');
    stopBumpAudio();
    isShowingBump = false;
  }

  // ── Static Noise ────────────────────────────────
  function drawStatic() {
    const canvas = document.querySelector('#static canvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    canvas.width = 320;
    canvas.height = 240;

    let frame = 0;
    function render() {
      if (frame > 90) return; // stop after ~1.5s
      const imageData = ctx.createImageData(320, 240);
      const data = imageData.data;
      for (let i = 0; i < data.length; i += 4) {
        const v = Math.random() * 40;
        data[i] = v;
        data[i + 1] = v;
        data[i + 2] = v;
        data[i + 3] = 255;
      }
      ctx.putImageData(imageData, 0, 0);
      frame++;
      requestAnimationFrame(render);
    }
    render();
  }

  // ── Clock ───────────────────────────────────────
  function startClock() {
    function update() {
      $clock.textContent = formatTime(new Date());
    }
    update();
    setInterval(update, 30000);
  }

  // ── Mute ────────────────────────────────────────
  function toggleMute() {
    isMuted = !isMuted;
    if (playerReady) {
      if (isMuted) player.mute();
      else player.unMute();
    }
    $muteBtn.classList.toggle('muted', isMuted);
    $muteBtn.textContent = isMuted ? '🔇' : '🔊';
  }

  // ── Debug: test bump from console ────────────────
  window.testBump = function() {
    const block = getCurrentBlock();
    showBump(block.name, BUMP_DURATION);
    setTimeout(() => {
      hideBump();
      syncToSchedule();
    }, BUMP_DURATION * 1000);
  };

  // Force the "up next" card for testing: testNext() or testNext(20) to hold 20s.
  window.testNext = function(seconds) {
    const block = getCurrentBlock();
    if (isShowingBump) hideBump();
    isShowingBump = true;
    if (playerReady && player.getPlayerState && player.getPlayerState() === 1) player.pauseVideo();
    if (renderUpNext()) {
      $bump.classList.add('next-mode');
    } else {
      $bumpText.textContent = getBumpMessage(block.name);
    }
    $bump.classList.add('active');
    playBumpAudio();
    currentVideoId = null;
    setTimeout(() => { hideBump(); syncToSchedule(); }, (seconds || BUMP_DURATION) * 1000);
  };

  // ── snow-guide: liftable printed program guide ──
  // The real schedule only: the rest of the current block, then the next two.
  function sgEsc(s) {
    return String(s).replace(/[&<>"]/g, c => ({ '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;' }[c]));
  }
  // 24h "HH.MM" to match the European printed-guide look
  function sgTime(d) {
    return String(d.getHours()).padStart(2, '0') + '.' + String(d.getMinutes()).padStart(2, '0');
  }
  // pull a clean name (+ optional "network") out of a long YouTube title
  function sgSplitTitle(title) {
    const parts = String(title).split('|').map(s => s.trim()).filter(Boolean);
    let name = parts[0] || String(title);
    let net = parts.length > 1 ? parts[parts.length - 1] : '';
    if (net && net.length > 16) net = '';
    if (name.length > 66) name = name.slice(0, 64).replace(/[\s\-–—:,]+$/, '') + '…';
    return { name, net };
  }
  // Every program in a block, in airing order, with real start times
  // (the playlist loops until the block ends, exactly like the player).
  function blockPrograms(block, start) {
    const pl = playlists[block.name];
    if (!pl || !pl.length) return [];
    const order = shuffleForToday(pl, block.name, start);
    const end = start.getTime() + (block.end - block.start) * 3600000;
    const out = []; let t = start.getTime(); let i = 0;
    while (t < end && i < 2000) {
      const v = order[i % order.length];
      const durMs = (v.duration + BUMP_DURATION) * 1000;
      out.push({ start: t, end: t + durMs, video: v });
      t += durMs; i++;
    }
    return out;
  }
  // The block that follows `block` (whose start was `start`), and when it starts.
  function nextBlock(block, start) {
    const nextStart = new Date(start.getTime() + (block.end - block.start) * 3600000);
    const h = block.end % 24;
    return { block: BLOCKS.find(b => b.start % 24 === h), start: nextStart };
  }
  function rowFor(p, now) {
    const s = sgSplitTitle(p.video.title);
    return { time: sgTime(new Date(p.start)), title: s.name, net: s.net, now: now >= p.start && now < p.end };
  }
  // Next n programs from now, across block boundaries (used by the guide bump).
  function upcomingPrograms(n) {
    const now = Date.now();
    let block = getCurrentBlock(), start = getBlockStartTime(block);
    const rows = [];
    for (let k = 0; k < 3 && rows.length < n; k++) {
      for (const p of blockPrograms(block, start)) {
        if (p.end <= now) continue;
        rows.push({ start: p.start, time: formatTime(new Date(p.start)), title: p.video.title });
        if (rows.length >= n) break;
      }
      ({ block, start } = nextBlock(block, start));
    }
    return rows;
  }
  function sgBlockHTML(block, start, now, current) {
    const all = blockPrograms(block, start);
    let progs = current ? all.filter(p => p.end > now) : all;
    const cap = current ? 9 : 7;
    const more = Math.max(0, progs.length - cap);
    progs = progs.slice(0, cap);
    const lis = progs.map(p => {
      const r = rowFor(p, now);
      return `<li${r.now ? ' class="now"' : ''}><b>${sgEsc(r.time)}</b> <span>${sgEsc(r.title)}` +
        `${r.net ? ` <em>(${sgEsc(r.net)})</em>` : ''}</span></li>`;
    }).join('') + (more ? `<li class="more"><b></b> <span>…and ${more} more</span></li>` : '');
    const endD = new Date(start.getTime() + (block.end - block.start) * 3600000);
    return `<div class="chan${current ? ' chan--real' : ''}">` +
      `<h3><span class="cn">${sgEsc(sgTime(start))}</span> ${sgEsc(block.label.toUpperCase())}` +
      ` <span class="span">– ${sgEsc(sgTime(endD))}</span>` +
      `${current ? ' <span class="live">▶ now</span>' : ''}</h3><ul class="prog">${lis}</ul></div>`;
  }
  function sgBuild() {
    const cols = document.querySelector('#guidesheet .sheet-cols');
    if (!cols) return;
    const now = new Date();
    const sub = document.querySelector('#guidesheet .mast-sub');
    if (sub) {
      sub.textContent = now.toLocaleDateString(undefined, { weekday: 'long', month: 'long', day: 'numeric' })
        .toLowerCase() + ' · ' + formatTime(now);
    }
    let block = getCurrentBlock(), start = getBlockStartTime(block);
    let html = '';
    for (let k = 0; k < 3 && block; k++) {
      html += sgBlockHTML(block, start, now.getTime(), k === 0);
      ({ block, start } = nextBlock(block, start));
    }
    cols.innerHTML = html;
  }
  function sgOpen()  { const g = document.getElementById('guidesheet'); if (!g) return; sgBuild(); g.classList.add('open'); g.setAttribute('aria-hidden', 'false'); }
  function sgClose() { const g = document.getElementById('guidesheet'); if (!g) return; g.classList.remove('open'); g.setAttribute('aria-hidden', 'true'); }
  function sgToggle(){ const g = document.getElementById('guidesheet'); if (!g) return; g.classList.contains('open') ? sgClose() : sgOpen(); }
  function setupGuideSheet() {
    const btn = document.getElementById('guide-btn');
    if (btn) btn.addEventListener('click', e => { e.stopPropagation(); sgToggle(); });
    const g = document.getElementById('guidesheet');
    if (g) {
      g.addEventListener('click', e => { e.stopPropagation(); if (e.target === g) sgClose(); });
      const sheet = g.querySelector('.sheet'); if (sheet) sheet.addEventListener('click', e => e.stopPropagation());
      const cb = g.querySelector('.sheet-close'); if (cb) cb.addEventListener('click', e => { e.stopPropagation(); sgClose(); });
    }
    document.addEventListener('keydown', e => { if (e.key === 'Escape') sgClose(); });
  }
  window.testGuideSheet = sgOpen; // open from console for previewing

  // the bottom buttons (mute + guide) fade in on mouse activity, out when idle
  function setupIdleUI() {
    let t;
    const wake = () => {
      document.body.classList.add('ui-awake');
      clearTimeout(t);
      t = setTimeout(() => document.body.classList.remove('ui-awake'), 2800);
    };
    ['mousemove', 'mousedown', 'touchstart', 'keydown'].forEach(ev =>
      document.addEventListener(ev, wake, { passive: true }));
  }

  // ── Go ──────────────────────────────────────────
  document.addEventListener('DOMContentLoaded', init);
})();
