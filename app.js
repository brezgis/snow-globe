// snow-globe — schedule engine + player logic
// Pure logic lives in engine.js; this file handles DOM + YouTube.

import {
  BUMP_DURATION, BLOCKS, seededRandom, getDaySeed,
  shuffleForToday, computeSchedulePosition, getCurrentBlock,
  getBlockStartTime, formatTime, getBumpMessage,
} from './engine.js';

(function () {
  'use strict';

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
  const removedVideos = new Set();

  // ── DOM refs ────────────────────────────────────
  const $bump = document.getElementById('bump');
  const $bumpText = document.getElementById('bump-text');
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

    // show UI labels briefly on load
    setTimeout(() => {
      $blockLabel.classList.add('visible');
      $clock.classList.add('visible');
    }, 2000);
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

  // Time helpers, shuffle, and schedule engine imported from engine.js

  function syncToSchedule() {
    const block = getCurrentBlock();
    const playlist = playlists[block.name];
    if (!playlist || !playlist.length) return;

    // Shuffle playlist deterministically for today
    const todaysPlaylist = shuffleForToday(playlist, block.name, removedVideos);

    $blockLabel.textContent = block.label;

    const blockStart = getBlockStartTime(block);
    const now = new Date();
    const elapsed = (now - blockStart) / 1000;

    const pos = computeSchedulePosition(todaysPlaylist, elapsed);

    if (pos.type === 'bump') {
      showBump(block.name, pos.remainingSec);
    } else {
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
    player = new YT.Player('yt-player', {
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
      },
      events: {
        onReady: onPlayerReady,
        onStateChange: onPlayerStateChange,
        onError: onPlayerError,
      },
    });
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
  // getBumpMessage imported from engine.js

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

  function showBump(blockName, remainingSec) {
    if (isShowingBump) return;
    isShowingBump = true;

    // Pause/mute the player during bump
    if (playerReady && player.getPlayerState && player.getPlayerState() === 1) {
      player.pauseVideo();
    }

    const message = getBumpMessage(blockName, bumps);
    $bumpText.textContent = message;
    $bump.classList.add('active');
    playBumpAudio();
    currentVideoId = null; // force reload after bump
  }

  function hideBump() {
    if (!isShowingBump) return;
    $bump.classList.remove('active');
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

  // ── Go ──────────────────────────────────────────
  document.addEventListener('DOMContentLoaded', init);
})();
