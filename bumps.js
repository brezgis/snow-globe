// snow-globe — the bump library.
//
// Each bump is { id, weight, quiet?, run(stage, api) }. run() draws into
// `stage` (a full-screen div) and schedules everything through `api`, so
// app.js can tear it down cleanly when the 12 seconds are up — or sooner,
// if you tuned in halfway through one. Every sound is synthesized live by
// synth() below; nothing is pre-recorded.
//
// Preview any bump: /#bump=sheep, or testBump('sheep', 30) in the console.
// listBumps() lists them all.
//
// Most bumps pick from several scripts/variants each time, so the same
// bump rarely plays out the same way twice.

(function () {
  'use strict';

  const pick = arr => arr[Math.floor(Math.random() * arr.length)];
  const rand = (a, b) => a + Math.random() * (b - a);

  // ── shared bits ──────────────────────────────────────
  function caption(api, text, cls) {
    const el = api.el('div', 'bs-caption' + (cls ? ' ' + cls : ''), text);
    requestAnimationFrame(() => el.classList.add('in'));
    return el;
  }

  // Runs a little script of ops: ['t', text] type, ['d', n] delete n chars,
  // ['p', ms] pause, ['n'] newline. Typing has a human, uneven rhythm.
  function typeScript(api, box, ops, speed, S) {
    const cursor = document.createElement('span');
    cursor.className = 'bs-cursor';
    let line = document.createElement('div');
    box.append(line, cursor);
    let t = 0;
    const at = (fn) => api.after(t, fn);
    for (const op of ops) {
      if (op[0] === 't') {
        for (const ch of op[1]) {
          t += speed * rand(0.55, 1.6) + (ch === ' ' ? 30 : 0) + (/[.,]/.test(ch) ? 140 : 0);
          at(() => { line.textContent += ch; line.after(cursor); if (S && ch !== ' ') S.click(0.18, rand(1800, 3200)); });
        }
      } else if (op[0] === 'd') {
        for (let i = 0; i < op[1]; i++) {
          t += speed * 0.45;
          at(() => { line.textContent = line.textContent.slice(0, -1); });
        }
      } else if (op[0] === 'p') {
        t += op[1];
      } else if (op[0] === 'n') {
        t += 120;
        at(() => { line = document.createElement('div'); box.insertBefore(line, cursor); if (S) S.bell(96, 0.05, 0, 1.2); });
      }
    }
    return t;
  }

  // ── a tiny synth ─────────────────────────────────────
  // Everything you hear in a bump is made here, live. When the viewer is
  // muted (or hasn't clicked yet) api.audio is null and every call is a no-op.
  const mtof = m => 440 * Math.pow(2, (m - 69) / 12);
  const PENTA = [0, 2, 4, 7, 9];          // major pentatonic
  const scale = (root, steps) => steps.map(k => root + PENTA[((k % 5) + 5) % 5] + 12 * Math.floor(k / 5));

  function synth(api) {
    const A = api.audio;
    const noop = () => {};
    if (!A) return { tone: noop, pluck: noop, bell: noop, pad: noop, noise: noop, click: noop, glide: noop, thump: noop, seq: noop, now: () => 0 };
    const ctx = A.ctx, out = A.out;
    const env = (g, t, a, peak, d) => {
      g.gain.setValueAtTime(0.0001, t);
      g.gain.exponentialRampToValueAtTime(peak, t + a);
      g.gain.exponentialRampToValueAtTime(0.0001, t + a + d);
    };
    const osc = (type, f, t, dur, dest) => {
      const o = A.track(ctx.createOscillator());
      o.type = type; o.frequency.setValueAtTime(f, t);
      o.connect(dest); o.start(t); o.stop(t + dur + 0.05);
      return o;
    };
    const gain = (dest) => { const g = ctx.createGain(); g.connect(dest || out); return g; };
    let noiseBuf = null;
    const noiseSrc = (t, dur, dest) => {
      if (!noiseBuf) {
        noiseBuf = ctx.createBuffer(1, ctx.sampleRate * 2, ctx.sampleRate);
        const d = noiseBuf.getChannelData(0);
        for (let i = 0; i < d.length; i++) d[i] = Math.random() * 2 - 1;
      }
      const n = A.track(ctx.createBufferSource());
      n.buffer = noiseBuf; n.loop = true; n.connect(dest); n.start(t); n.stop(t + dur + 0.05);
      return n;
    };
    const at = d => ctx.currentTime + (d || 0);
    const S = {
      now: () => ctx.currentTime,
      // steady tone(s): test card, phone ring
      tone(freqs, dur, vol, delay, type) {
        const t = at(delay), g = gain();
        g.gain.setValueAtTime(0, t); g.gain.linearRampToValueAtTime(vol, t + 0.02);
        g.gain.setValueAtTime(vol, t + dur - 0.03); g.gain.linearRampToValueAtTime(0, t + dur);
        [].concat(freqs).forEach(f => osc(type || 'sine', f, t, dur, g));
      },
      // soft plucked string (triangle, quick decay)
      pluck(midi, vol, delay, decay) {
        const t = at(delay), g = gain(); env(g, t, 0.005, vol, decay || 0.6);
        osc('triangle', mtof(midi), t, (decay || 0.6) + 0.05, g);
      },
      // music box / glockenspiel: sine + inharmonic partial, long ring
      bell(midi, vol, delay, decay) {
        const t = at(delay), d = decay || 1.8, g = gain(); env(g, t, 0.004, vol, d);
        osc('sine', mtof(midi), t, d, g);
        const g2 = gain(); env(g2, t, 0.004, vol * 0.35, d * 0.4);
        osc('sine', mtof(midi) * 2.76, t, d * 0.4, g2);
      },
      // warm detuned pad, slow in and out
      pad(midis, dur, vol, delay, cutoff) {
        const t = at(delay), lp = ctx.createBiquadFilter();
        lp.type = 'lowpass'; lp.frequency.value = cutoff || 900; lp.Q.value = 0.4;
        const g = gain(); lp.connect(g);
        g.gain.setValueAtTime(0, t); g.gain.linearRampToValueAtTime(vol, t + Math.min(2, dur / 3));
        g.gain.setValueAtTime(vol, t + dur * 0.7); g.gain.linearRampToValueAtTime(0, t + dur);
        for (const m of midis) for (const det of [-6, 5]) { const o = osc('sawtooth', mtof(m), t, dur, lp); o.detune.value = det; }
        return lp;
      },
      // filtered noise: wind, static, shaking, rain
      noise(dur, vol, freq, q, delay, type) {
        const t = at(delay), f = ctx.createBiquadFilter();
        f.type = type || 'bandpass'; f.frequency.value = freq || 800; f.Q.value = q || 0.7;
        const g = gain(); f.connect(g);
        g.gain.setValueAtTime(0, t); g.gain.linearRampToValueAtTime(vol, t + Math.min(0.6, dur / 4));
        g.gain.setValueAtTime(vol, t + dur * 0.75); g.gain.linearRampToValueAtTime(0, t + dur);
        noiseSrc(t, dur, f);
        return f;
      },
      // a short click: typewriter keys, ticks
      click(vol, freq, delay) {
        const t = at(delay), f = ctx.createBiquadFilter();
        f.type = 'bandpass'; f.frequency.value = freq || 2400; f.Q.value = 1.5;
        const g = gain(); f.connect(g); env(g, t, 0.001, vol, 0.04);
        noiseSrc(t, 0.06, f);
      },
      // pitch glide: bubbles, the growing period
      glide(f0, f1, dur, vol, delay, type) {
        const t = at(delay), g = gain();
        g.gain.setValueAtTime(0, t); g.gain.linearRampToValueAtTime(vol, t + 0.01);
        g.gain.setValueAtTime(vol, t + dur * 0.8); g.gain.linearRampToValueAtTime(0, t + dur);
        const o = osc(type || 'sine', f0, t, dur, g);
        o.frequency.exponentialRampToValueAtTime(f1, t + dur);
      },
      // low thump: heartbeat, a sheep landing
      thump(vol, delay, f) {
        const t = at(delay), g = gain(); env(g, t, 0.004, vol, 0.25);
        const o = osc('sine', f || 70, t, 0.3, g);
        o.frequency.exponentialRampToValueAtTime(35, t + 0.25);
      },
      // a sequence of notes [midi|null], one every `step` seconds
      seq(notes, step, fn, delay) {
        notes.forEach((n, i) => { if (n != null) fn(n, (delay || 0) + i * step); });
      },
    };
    return S;
  }

  const BUMPS = [];
  const bump = (id, weight, run, opts) => BUMPS.push(Object.assign({ id, weight, run }, opts || {}));

  // ── 1. plain card: the classic text pool from bumps.json ──
  bump('card', 3, (stage, api) => {
    const el = api.el('p', 'bs-card', api.message());
    requestAnimationFrame(() => el.classList.add('in'));
    const S = synth(api);
    const root = pick([45, 48, 50, 41]);
    S.pad(pick([[0, 7, 16, 23], [0, 7, 14, 19], [0, 3, 10, 15]]).map(k => root + k), 11.5, 0.035, 0.2, 700);
    S.noise(11.5, 0.012, 3500, 0.5, 0.2);           // tape hiss
  });

  // ── 2. typewriter: someone is typing to you ──────────
  bump('typewriter', 1.4, (stage, api) => {
    const box = api.el('div', 'bs-type');
    const scripts = [
      [['t', 'i have something to tell you.'], ['p', 900], ['d', 22], ['t', 'nothing, actually.'], ['p', 700], ['n'], ['t', 'back to the show.']],
      [['t', 'loading personality'], ['p', 300], ['t', '......'], ['t', ' [failed]'], ['p', 500], ['n'],
       ['t', 'loading default personality...'], ['t', ' [ok]'], ['p', 500], ['n'], ['t', 'hello. i am a television.']],
      [['t', 'dear diary,'], ['n'], ['p', 500], ['t', 'today i was on for nineteen hours.'], ['n'], ['p', 500],
       ['t', 'nobody changed the channel.'], ['n'], ['p', 700], ['t', 'i think they like me.']],
      [['t', 'password: '], ['t', '**********'], ['p', 400], ['n'], ['t', 'incorrect.'], ['p', 500], ['n'],
       ['t', 'hint: the name of your first television.']],
      [['t', 'how to be a person:'], ['n'], ['p', 400], ['t', '1. wake up'], ['n'], ['t', '2. '], ['p', 1400],
       ['t', 'we\'ll get back to you on 2.']],
      [['t', 'things i know about you:'], ['n'], ['p', 600], ['t', '- you are watching'], ['n'], ['p', 900],
       ['t', '- that\'s it'], ['n'], ['p', 600], ['t', '- it\'s enough']],
    ];
    const S = synth(api);
    S.noise(11.5, 0.006, 120, 0.8, 0, 'lowpass');     // room tone
    typeScript(api, box, pick(scripts), 62, S);
  });

  // ── 3. viewer mail ───────────────────────────────────
  const LETTERS = [
    ['dear snow-globe, i fell asleep during the train ride and woke up in the same place. is that the point.', 't., ohio', 'yes.'],
    ['my grandmother says the hedgehog is real. we have not been able to prove otherwise.', 'r. & r.', null],
    ['is it possible to change the channel. asking for a friend who is me.', 'anonymous', 'no.'],
    ['i leave you on for my dog while i\'m at work. he has strong opinions about norman mclaren now.', 'd., queens', 'he\'s right.'],
    ['i watched the fireplace for an hour and my apartment got warmer. please explain.', 'j.', 'we cannot.'],
    ['what is the snow made of.', 'a child, probably', 'mostly time.'],
    ['you showed a man making a chair and i cried. i do not know anything about chairs.', 'k., portland', 'nobody does. that\'s why.'],
    ['i think one of the sesame street ladybugs is following me.', 'm.', 'only the nice one.'],
    ['how many people are watching right now.', 'curious in cambridge', 'enough.'],
  ];
  bump('mail', 1.3, (stage, api) => {
    const [body, sig, reply] = pick(LETTERS);
    const card = api.el('div', 'bs-mail');
    const head = api.el('div', 'bs-mail-head', 'viewer mail', card);
    const b = api.el('div', 'bs-mail-body', '“' + body + '”', card);
    const s = api.el('div', 'bs-mail-sig', '— ' + sig, card);
    [head, b, s].forEach((el, i) => api.after(300 + i * 900, () => el.classList.add('in')));
    const S = synth(api), notes = scale(72, [0, 2, 4, 3, 1, 2, 0, null, 4, 5, 7, 6, 4, null, 2, 0]);
    S.seq(notes, 0.62, (n, d) => S.bell(n, 0.06, d + 0.3, 2.2));
    S.seq(scale(48, [0, null, null, null, 3, null, null, null, 1, null, null, null, 0]), 0.62, (n, d) => S.pluck(n, 0.05, d + 0.3, 1.6));
    if (reply) {
      const r = api.el('div', 'bs-mail-reply', reply, card);
      api.after(6500, () => r.classList.add('in'));
    }
  });

  // ── 4. two voices in the dark ────────────────────────
  const CHATS = [
    ['are you watching this', 'i\'m watching something', 'same thing?', 'can\'t be sure', 'that\'s the show'],
    ['what time is it', '[time]', 'where', 'here', 'oh good'],
    ['did you hear that', 'the tv?', 'no, the other thing', 'there\'s another thing?', 'there\'s always another thing'],
    ['i think the snow is getting worse', 'it\'s a website', 'i know', 'okay', 'still'],
    ['what\'s on next', 'something', 'is it good', 'it\'s next', 'that\'s not the same'],
    ['are we on', 'we\'ve been on', 'how long', 'yes'],
  ];
  bump('chat', 1.3, (stage, api) => {
    const box = api.el('div', 'bs-chat');
    const S = synth(api);
    S.pad([38, 45, 52], 11.5, 0.03, 0, 500);
    pick(CHATS).forEach((line, i) => {
      const el = api.el('div', 'bs-chat-line ' + (i % 2 ? 'b' : 'a'), line.replace('[time]', api.time), box);
      api.after(400 + i * 1900, () => { el.classList.add('in'); S.pluck(i % 2 ? 76 : 69, 0.06); S.pluck(i % 2 ? 83 : 64, 0.03, 0.08); });
    });
  });

  // ── 5. the snow globe, shaken ────────────────────────
  bump('globe', 1.4, (stage, api) => {
    const { ctx, W, H } = api.canvas();
    const R = Math.min(W, H) * 0.27, cx = W / 2, cy = H * 0.46;
    const ground = cy + R * 0.5;
    const flakes = [];
    const shake = (power) => {
      for (const f of flakes) { f.vx += rand(-power, power); f.vy += rand(-power * 1.4, power * 0.4); f.rest = false; }
    };
    for (let i = 0; i < 260; i++) {
      const a = rand(0, Math.PI * 2), r = Math.sqrt(Math.random()) * R * 0.9;
      flakes.push({ x: cx + Math.cos(a) * r, y: cy + Math.sin(a) * r, vx: 0, vy: 0, s: rand(0.8, 2.2), rest: false });
    }
    const S = synth(api);
    const shakeSound = (d) => { S.noise(0.9, 0.05, 2600, 2, d); S.noise(0.7, 0.03, 5200, 3, d + 0.1); };
    shake(9); shakeSound(0);
    api.after(7600, () => { shake(6); shakeSound(0); });
    S.seq(scale(76, [4, 2, 0, 2, 4, 4, 4, null, 2, 2, 2, null, 4, 7, 7, null]), 0.55, (n, d) => S.bell(n, 0.045, d + 1.2, 2.4));
    api.after(3800, () => caption(api, pick([
      'please do not shake the broadcast.', 'everything settles eventually.',
      'somebody up there is holding you very carefully.', 'weather, for the indoors.',
    ])));
    api.frame(() => {
      ctx.clearRect(0, 0, W, H);
      // base
      ctx.fillStyle = '#1b1b22';
      ctx.beginPath();
      ctx.moveTo(cx - R * 0.78, cy + R * 0.86); ctx.lineTo(cx + R * 0.78, cy + R * 0.86);
      ctx.lineTo(cx + R * 0.92, cy + R * 1.16); ctx.lineTo(cx - R * 0.92, cy + R * 1.16); ctx.closePath(); ctx.fill();
      ctx.save();
      ctx.beginPath(); ctx.arc(cx, cy, R, 0, Math.PI * 2); ctx.clip();
      const g = ctx.createRadialGradient(cx - R * 0.3, cy - R * 0.4, R * 0.1, cx, cy, R);
      g.addColorStop(0, '#1c2433'); g.addColorStop(1, '#07090e');
      ctx.fillStyle = g; ctx.fillRect(cx - R, cy - R, R * 2, R * 2);
      // ground, tree, house with a lit window
      ctx.fillStyle = '#d9dde6'; ctx.fillRect(cx - R, ground, R * 2, R);
      ctx.fillStyle = '#0d1a14';
      ctx.beginPath(); ctx.moveTo(cx + R * 0.38, ground - R * 0.5); ctx.lineTo(cx + R * 0.56, ground); ctx.lineTo(cx + R * 0.2, ground); ctx.fill();
      ctx.fillStyle = '#2a1e1a'; ctx.fillRect(cx - R * 0.36, ground - R * 0.3, R * 0.42, R * 0.3);
      ctx.beginPath(); ctx.moveTo(cx - R * 0.42, ground - R * 0.3); ctx.lineTo(cx - R * 0.15, ground - R * 0.52); ctx.lineTo(cx + R * 0.12, ground - R * 0.3); ctx.fill();
      ctx.fillStyle = '#ffcf6b'; ctx.fillRect(cx - R * 0.24, ground - R * 0.2, R * 0.09, R * 0.09);
      ctx.fillStyle = '#fff';
      for (const f of flakes) {
        if (!f.rest) {
          f.vx *= 0.965; f.vy = f.vy * 0.965 + 0.018 * f.s;
          f.vx += rand(-0.05, 0.05);
          f.x += f.vx; f.y += f.vy;
          const dx = f.x - cx, dy = f.y - cy, d = Math.hypot(dx, dy);
          if (d > R - 3) { f.x = cx + dx / d * (R - 3); f.y = cy + dy / d * (R - 3); f.vx *= -0.4; f.vy *= -0.4; }
          if (f.y > ground - f.s && Math.abs(f.vy) < 1.2) { f.y = ground - f.s * 0.6 - rand(0, 2); f.rest = true; }
        }
        ctx.globalAlpha = f.rest ? 0.75 : 0.95;
        ctx.beginPath(); ctx.arc(f.x, f.y, f.s, 0, Math.PI * 2); ctx.fill();
      }
      ctx.globalAlpha = 1;
      ctx.restore();
      ctx.strokeStyle = 'rgba(255,255,255,0.28)'; ctx.lineWidth = 2;
      ctx.beginPath(); ctx.arc(cx, cy, R, 0, Math.PI * 2); ctx.stroke();
      ctx.strokeStyle = 'rgba(255,255,255,0.12)'; ctx.lineWidth = 6;
      ctx.beginPath(); ctx.arc(cx, cy, R * 0.86, Math.PI * 1.1, Math.PI * 1.35); ctx.stroke();
    });
  });

  // ── 6. inkblot ───────────────────────────────────
  bump('inkblot', 1.1, (stage, api) => {
    const { ctx, W, H } = api.canvas();
    const gw = 128, gh = 96;
    const off = document.createElement('canvas'); off.width = gw; off.height = gh;
    const octx = off.getContext('2d'); const img = octx.createImageData(gw, gh);
    // a spine of blots near the fold, wings flung outward, a few drips
    const balls = [];
    for (let i = 0; i < 6; i++) balls.push({ x: rand(0.44, 0.5), y: rand(0.15, 0.85), r: rand(0.025, 0.05) });
    for (let i = 0; i < 9; i++) balls.push({ x: rand(0.18, 0.44), y: rand(0.2, 0.75), r: rand(0.02, 0.055) });
    for (let i = 0; i < 7; i++) balls.push({ x: rand(0.05, 0.3), y: rand(0.1, 0.9), r: rand(0.006, 0.018) });
    balls.forEach(b => { b.fx = rand(0.15, 0.5); b.fy = rand(0.15, 0.5); b.p = rand(0, 6); b.a = rand(0.01, 0.03); });
    // fixed per-pixel grain so the edge is ragged like ink on paper
    const grain = new Float32Array(gw * gh).map(() => rand(-0.25, 0.25));
    const cardH = Math.min(H * 0.6, W * 0.5), cardW = cardH * 1.33;
    const x0 = (W - cardW) / 2, y0 = H * 0.12;
    const S = synth(api);
    S.pad([36, 43, 51], 11.8, 0.05, 0, 320);
    S.pad([60, 63], 8, 0.012, 3, 1400);
    api.after(4200, () => caption(api, 'you see a moth.'));
    api.after(8200, () => caption(api, pick(['everyone sees a moth.', 'it\'s always a moth.', 'the moth sees you.']), 'second'));
    api.frame((t) => {
      const sp = t / 1000, spread = Math.min(1, sp / 3);   // the ink spreads in, then breathes
      for (let y = 0; y < gh; y++) for (let x = 0; x < gw; x++) {
        const u = (x < gw / 2 ? x : gw - 1 - x) / gw, v = y / gh;   // mirrored at the fold
        let f = 0;
        for (const b of balls) {
          const bx = b.x + Math.sin(sp * b.fx + b.p) * b.a, by = b.y + Math.cos(sp * b.fy + b.p) * b.a;
          const r = b.r * (0.4 + 0.6 * spread);
          f += (r * r) / ((u - bx) ** 2 + ((v - by) * 0.8) ** 2 + 1e-5);
        }
        f += grain[y * gw + (x < gw / 2 ? x : gw - 1 - x)];
        const i = (y * gw + x) * 4, ink = f > 1.25 ? 1 : f > 1.0 ? (f - 1.0) / 0.25 : 0;
        img.data[i] = 236 - ink * 222; img.data[i + 1] = 230 - ink * 219; img.data[i + 2] = 214 - ink * 204; img.data[i + 3] = 255;
      }
      octx.putImageData(img, 0, 0);
      ctx.clearRect(0, 0, W, H);
      ctx.imageSmoothingEnabled = true;
      ctx.drawImage(off, x0, y0, cardW, cardH);
    });
  });

  // ── 7. counting sheep ────────────────────────────────
  bump('sheep', 1.2, (stage, api) => {
    const { ctx, W, H } = api.canvas();
    const groundY = H * 0.66, fenceX = W / 2, sc = Math.min(W, H) / 700;
    let count = Math.floor(rand(1200, 9800));
    const counter = api.el('div', 'bs-counter', count.toLocaleString());
    const sheep = [];
    let spawned = 0;
    const spawn = () => { sheep.push({ x: -80 * sc, counted: false, phase: rand(0, 6) }); spawned++; };
    spawn();
    api.every(1450, () => { if (spawned < 7) spawn(); });
    api.after(9000, () => caption(api, pick(['still awake? that\'s okay.', 'the sheep are also tired.', 'none of them are the same sheep.'])));
    const S = synth(api);
    S.noise(11.5, 0.008, 600, 0.4);                  // night air
    const drawSheep = (x, y, legT) => {
      ctx.fillStyle = '#f2f2f2';
      for (const [dx, dy, r] of [[0, 0, 22], [-16, 4, 16], [16, 4, 16], [-8, -10, 15], [10, -9, 15]])
        { ctx.beginPath(); ctx.arc(x + dx * sc, y + dy * sc, r * sc, 0, Math.PI * 2); ctx.fill(); }
      ctx.fillStyle = '#111'; ctx.beginPath(); ctx.ellipse(x + 30 * sc, y - 6 * sc, 10 * sc, 8 * sc, 0.3, 0, Math.PI * 2); ctx.fill();
      ctx.strokeStyle = '#ddd'; ctx.lineWidth = 3 * sc;
      for (const lx of [-14, -4, 8, 18]) {
        ctx.beginPath(); ctx.moveTo(x + lx * sc, y + 16 * sc); ctx.lineTo(x + (lx + Math.sin(legT + lx) * 4) * sc, y + 34 * sc); ctx.stroke();
      }
    };
    api.frame((t, dt) => {
      ctx.clearRect(0, 0, W, H);
      ctx.strokeStyle = 'rgba(255,255,255,0.25)'; ctx.lineWidth = 1;
      ctx.beginPath(); ctx.moveTo(0, groundY + 34 * sc); ctx.lineTo(W, groundY + 34 * sc); ctx.stroke();
      ctx.strokeStyle = '#8a7a66'; ctx.lineWidth = 4 * sc;
      for (const px of [-30, 30]) { ctx.beginPath(); ctx.moveTo(fenceX + px * sc, groundY + 34 * sc); ctx.lineTo(fenceX + px * sc, groundY - 20 * sc); ctx.stroke(); }
      for (const py of [-10, 10]) { ctx.beginPath(); ctx.moveTo(fenceX - 42 * sc, groundY + py * sc); ctx.lineTo(fenceX + 42 * sc, groundY + py * sc); ctx.stroke(); }
      for (const s of sheep) {
        s.x += dt * 0.19 * sc;
        const d = (s.x - fenceX) / (120 * sc);
        const jump = Math.abs(d) < 1 ? Math.cos(d * Math.PI / 2) * 95 * sc : 0;
        if (!s.jumped && s.x > fenceX - 120 * sc) { s.jumped = true; S.glide(300, 620, 0.35, 0.04, 0, 'triangle'); }
        if (!s.counted && s.x > fenceX) { s.counted = true; count++; counter.textContent = count.toLocaleString(); S.pluck(pick(scale(67, [0, 1, 2, 3, 4])), 0.07, 0, 0.9); }
        if (!s.landed && s.x > fenceX + 120 * sc) { s.landed = true; S.thump(0.12, 0, 90); }
        drawSheep(s.x, groundY - jump, t / 90 + s.phase);
      }
    });
  });

  // ── 8. test card ─────────────────────────────────────
  bump('testcard', 0.9, (stage, api) => {
    const { ctx, W, H } = api.canvas();
    const top = ['#c0c0c0', '#c0c000', '#00c0c0', '#00c000', '#c000c0', '#c00000', '#0000c0'];
    const mid = ['#0000c0', '#131313', '#c000c0', '#131313', '#00c0c0', '#131313', '#c0c0c0'];
    const box = api.el('div', 'bs-testbox', 'this is only a test.');
    api.after(5200, () => { box.textContent = pick(['you passed.', 'you are doing fine.', 'please remain as you are.']); });
    synth(api).tone(1000, 4.6, 0.04, 0.3);
    api.frame(() => {
      const bw = W / 7;
      top.forEach((c, i) => { ctx.fillStyle = c; ctx.fillRect(i * bw, 0, bw + 1, H * 0.67); });
      mid.forEach((c, i) => { ctx.fillStyle = c; ctx.fillRect(i * bw, H * 0.67, bw + 1, H * 0.08); });
      const low = ['#00214c', '#ffffff', '#32006a', '#131313', '#090909', '#131313', '#1d1d1d', '#131313'];
      const lw = [1.25, 1.25, 1.25, 1.25, 0.33, 0.33, 0.34, 1].map(f => f * bw);
      let x = 0; low.forEach((c, i) => { ctx.fillStyle = c; ctx.fillRect(x, H * 0.75, lw[i] + 1, H * 0.25); x += lw[i]; });
      // a little transmission noise
      ctx.fillStyle = 'rgba(255,255,255,0.05)';
      for (let i = 0; i < 40; i++) ctx.fillRect(rand(0, W), rand(0, H), rand(20, 200), 1);
    });
  });

  // ── 9. light to the moon, in real time ───────────────
  bump('moon', 1, (stage, api) => {
    const { ctx, W, H } = api.canvas();
    const ex = W * 0.16, mx = W * 0.84, y = H * 0.45, er = Math.min(W, H) * 0.07;
    const TRIP = 1282; // ms — average Earth–Moon light time
    const label = api.el('div', 'bs-moon-label', '0.00 s');
    const S = synth(api);
    let lastCycle = -1;
    api.after(1200, () => caption(api, 'light takes 1.28 seconds to reach the moon.'));
    api.after(7000, () => caption(api, pick(['say something. it\'ll get there before the next show.', 'wave. it\'s already halfway.', 'the moon hasn\'t seen this yet.']), 'second'));
    api.frame((t) => {
      ctx.clearRect(0, 0, W, H);
      const eg = ctx.createRadialGradient(ex - er * 0.3, y - er * 0.3, er * 0.1, ex, y, er);
      eg.addColorStop(0, '#5b8fd6'); eg.addColorStop(1, '#173058');
      ctx.fillStyle = eg; ctx.beginPath(); ctx.arc(ex, y, er, 0, Math.PI * 2); ctx.fill();
      ctx.fillStyle = '#9a9a9a'; ctx.beginPath(); ctx.arc(mx, y, er * 0.27, 0, Math.PI * 2); ctx.fill();
      const cycle = TRIP + 700, p = (t % cycle) / TRIP, k = Math.floor(t / cycle);
      if (k !== lastCycle) { lastCycle = k; S.bell(62, 0.06, 0, 1.4); S.bell(81, 0.045, TRIP / 1000, 2); }
      if (p <= 1) {
        const px = ex + er + (mx - er * 0.27 - ex - er) * p;
        const grd = ctx.createLinearGradient(px - 90, 0, px, 0);
        grd.addColorStop(0, 'rgba(255,240,200,0)'); grd.addColorStop(1, 'rgba(255,240,200,0.9)');
        ctx.fillStyle = grd; ctx.fillRect(px - 90, y - 1, 90, 2);
        ctx.fillStyle = '#fff6dd'; ctx.beginPath(); ctx.arc(px, y, 2.5, 0, Math.PI * 2); ctx.fill();
        label.textContent = (p * TRIP / 1000).toFixed(2) + ' s';
      } else label.textContent = (TRIP / 1000).toFixed(2) + ' s';
    });
  });

  // ── 10. the fish who eats the sentence ───────────────
  bump('fish', 1.1, (stage, api) => {
    const sentence = pick([
      'nothing is happening here. absolutely nothing at all.',
      'this sentence is completely safe and will not be eaten.',
      'please enjoy this calm, uninterrupted line of text.',
    ]);
    const line = api.el('div', 'bs-fish');
    const S = synth(api);
    S.noise(11.5, 0.02, 400, 0.6, 0, 'lowpass');     // underwater
    const chars = [...sentence];
    const pad = 4, total = chars.length + pad * 2 + 3;
    let pos = -3, eaten = 0;
    const render = () => {
      let out = '';
      for (let i = -pad; i < chars.length + pad; i++) {
        if (i === pos) out += '>';
        else if (i === pos + 1) out += '<';
        else if (i === pos + 2) out += '>';
        else out += (i >= 0 && i < chars.length) ? chars[i] : ' ';
      }
      line.textContent = out;
    };
    render();
    api.after(1400, () => {
      api.every(115, () => {
        if (pos > chars.length + pad) return;
        pos++;
        const head = pos + 2;
        if (head >= 0 && head < chars.length && chars[head] !== ' ' && Math.random() < 0.7) {
          chars[head] = ' '; eaten++;
          S.glide(rand(300, 500), rand(900, 1600), 0.09, 0.05);
        }
        render();
      });
    });
    api.after(1400 + 115 * total + 500, () => caption(api, eaten > 30 ? 'sorry. he was hungry.' : 'he\'ll be back.'));
  });

  // ── 11. end credits, for no reason ───────────────────
  const CREDITS = [
    ['directed by', 'nobody'], ['starring', 'you'], ['also starring', 'the lamp'],
    ['catering', 'whatever\'s in your fridge'], ['best boy', 'the moon'], ['key grip', 'gravity'],
    ['weather', 'mostly indoors'], ['continuity', 'we gave up'], ['special thanks', 'the dark'],
    ['music', 'the hum of your appliances'], ['wardrobe', 'whatever you\'re wearing'],
    ['stunts', 'none. please sit down.'], ['no animals were harmed.', 'several were confused.'],
  ];
  bump('credits', 1, (stage, api) => {
    const roll = api.el('div', 'bs-credits');
    const rows = [...CREDITS].sort(() => Math.random() - 0.5).slice(0, 9);
    rows.push(['', 'snow-globe']);
    for (const [k, v] of rows) {
      const r = api.el('div', 'bs-credit', '', roll);
      api.el('span', 'k', k, r); api.el('span', 'v', v, r);
    }
    // roll so the final card ("snow-globe") comes to rest mid-screen
    requestAnimationFrame(() => {
      const dist = roll.offsetHeight + window.innerHeight * 0.5 - roll.lastElementChild.offsetHeight / 2;
      const anim = roll.animate([{ transform: 'translateY(0)' }, { transform: `translateY(${-dist}px)` }],
        { duration: 10500, easing: 'cubic-bezier(.25,.1,.45,1)', fill: 'forwards' });
      api.after(11800, () => anim.cancel());
    });
    const S = synth(api);
    [[53, 57, 60, 64], [50, 53, 57, 60], [46, 50, 53, 57], [48, 52, 55, 60]].forEach((ch, i) => {
      S.pad(ch, 3.4, 0.022, i * 2.8, 1100);
      ch.forEach((n, j) => S.bell(n + 24, 0.035, i * 2.8 + j * 0.35, 2));
    });
  });

  // ── 12. a pinball counts to twelve ───────────────────
  bump('count', 1, (stage, api) => {
    const colors = ['#ff5a36', '#ffc527', '#38c172', '#3fa9f5', '#c86bfa', '#ff7ab6'];
    const words = ['one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten', 'eleven', 'twelve'];
    const n = api.el('div', 'bs-count');
    const S = synth(api), up = scale(60, [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]);
    words.forEach((w, i) => api.after(250 + i * 720, () => {
      S.pluck(up[i], 0.08, 0, 0.5); S.bell(up[i] + 12, 0.03, 0.02, 0.5);
      n.textContent = String(i + 1);
      n.style.color = colors[i % colors.length];
      n.style.left = rand(28, 72) + '%'; n.style.top = rand(30, 62) + '%';
      n.classList.remove('pop'); void n.offsetWidth; n.classList.add('pop');
    }));
    api.after(250 + 12 * 720 + 200, () => { n.remove(); [60, 64, 67, 72].forEach(m => S.bell(m, 0.04, 0, 2.5)); caption(api, pick(['that\'s all the numbers we could afford.', 'twelve. the rest are in storage.', 'twelve is plenty.'])); });
  });

  // ── 13. eyes in the dark ─────────────────────────────
  bump('eyes', 1.1, (stage, api) => {
    const { ctx, W, H } = api.canvas();
    const r = Math.min(W, H) * 0.075, y = H * 0.42;
    const eyes = [W / 2 - r * 1.5, W / 2 + r * 1.5];
    let look = { x: W / 2, y }, target = { x: W / 2, y }, blink = 0, nextBlink = 1200;
    const S = synth(api);
    for (let k = 0; k < 12; k++) { S.thump(0.18, 0.3 + k * 0.95, 60); S.thump(0.1, 0.3 + k * 0.95 + 0.22, 55); }
    api.listen(window, 'mousemove', e => { target = { x: e.clientX, y: e.clientY }; });
    api.every(1700, () => { target = { x: rand(0, W), y: rand(0, H) }; });
    api.after(5000, () => caption(api, pick(['we\'re not watching you. we\'re watching with you.', 'don\'t mind us.', 'we just like the company.'])));
    api.frame((t, dt) => {
      look.x += (target.x - look.x) * 0.06; look.y += (target.y - look.y) * 0.06;
      nextBlink -= dt; if (nextBlink < 0) { blink = 1; nextBlink = rand(1500, 4200); }
      blink = Math.max(0, blink - dt / 160);
      const open = 1 - Math.sin(blink * Math.PI);
      ctx.clearRect(0, 0, W, H);
      for (const ex of eyes) {
        ctx.save();
        ctx.beginPath(); ctx.ellipse(ex, y, r, r * 0.62 * Math.max(0.04, open), 0, 0, Math.PI * 2);
        ctx.fillStyle = '#e9e6dc'; ctx.fill(); ctx.clip();
        const a = Math.atan2(look.y - y, look.x - ex), d = Math.min(r * 0.42, Math.hypot(look.x - ex, look.y - y) / 8);
        ctx.fillStyle = '#111'; ctx.beginPath(); ctx.arc(ex + Math.cos(a) * d, y + Math.sin(a) * d * 0.7, r * 0.3, 0, Math.PI * 2); ctx.fill();
        ctx.restore();
      }
    });
  });

  // ── 14. the forecast for your apartment ──────────────
  const FORECAST = [
    ['☀', 'couch', 'clear, with excellent visibility of the television'],
    ['☂', 'kitchen', '40% chance of snacks'],
    ['☁', 'bedroom', 'heavy blanket advisory until noon'],
    ['≋', 'hallway', 'light drafts; a mild existential front moving in from the bathroom'],
    ['❄', 'freezer', 'snow, as usual'],
    ['☾', 'window', 'one (1) moon, partly visible'],
    ['☁', 'your desk', 'overcast with unanswered email'],
  ];
  bump('forecast', 1, (stage, api) => {
    const box = api.el('div', 'bs-forecast');
    const S = synth(api);
    [[62, 65, 69, 72], [60, 64, 67, 71], [58, 62, 65, 69], [57, 60, 64, 67], [55, 59, 62, 65]].forEach((ch, i) => {
      S.pad(ch, 2.6, 0.022, i * 2.3, 2000);
      ch.forEach((n, j) => S.bell(n, 0.018, i * 2.3 + j * 0.03, 1.6));
      S.pluck(ch[0] - 24, 0.09, i * 2.3, 1.2);
      S.pluck(ch[0] - 17, 0.05, i * 2.3 + 1.15, 0.8);
    });
    api.el('div', 'bs-fc-head', 'local forecast · your apartment', box);
    const rows = [...FORECAST].sort(() => Math.random() - 0.5).slice(0, 4);
    rows.forEach(([icon, where, what], i) => {
      const r = api.el('div', 'bs-fc-row', '', box);
      api.el('span', 'i', icon + '︎', r); api.el('span', 'w', where, r); api.el('span', 'd', what, r);
      api.after(700 + i * 1900, () => r.classList.add('in'));
    });
  });

  // ── 15. emergency feelings system ────────────────────
  bump('emergency', 0.8, (stage, api) => {
    api.el('div', 'bs-eas-band', 'emergency feelings system');
    const crawl = api.el('div', 'bs-eas-crawl');
    api.el('span', '', pick([
      'this is a test of the emergency feelings system. if this had been an actual feeling, you would have been instructed where to put it. this concludes this test.',
      'this is a test. the national weather service has issued a cozy watch for your area. remain indoors. locate a blanket. this concludes this test.',
      'this is a test of the emergency feelings system. no action is required. you may continue to feel whatever you were feeling. this concludes this test.',
    ]), crawl);
    requestAnimationFrame(() => crawl.classList.add('go'));
  });

  // ── 16. the end of television (not really) ───────────
  bump('period', 0.9, (stage, api) => {
    const t = api.el('div', 'bs-end');
    t.append('and that is the end of television');
    const dot = document.createElement('span'); dot.className = 'bs-dot';
    t.append(dot);
    const S = synth(api);
    api.after(2600, () => { dot.classList.add('grow'); S.glide(110, 1760, 3.4, 0.05, 0, 'triangle'); S.noise(3.4, 0.03, 900, 0.5); });
    api.after(6200, () => S.bell(84, 0.06, 0, 2));
    api.after(6200, () => { t.remove(); caption(api, 'just kidding.'); });
    api.after(8600, () => caption(api, pick(['more in a moment.', 'it never ends. that\'s the nice part.']), 'second'));
  });

  // ── 17. rule 30, growing ─────────────────────────────
  bump('rule30', 0.9, (stage, api) => {
    const { ctx, W, H } = api.canvas();
    const cell = Math.max(3, Math.round(Math.min(W, H) / 180));
    const cols = Math.ceil(W / cell);
    let row = new Uint8Array(cols); row[Math.floor(cols / 2)] = 1;
    let y = 0;
    const S = synth(api), mid = Math.floor(cols / 2), notes = scale(62, [0, 1, 2, 3, 4, 5, 6, 7]);
    let lastNote = 0;
    api.after(6800, () => caption(api, 'nobody has ever proved this pattern repeats.', 'boxed'));
    api.after(9400, () => caption(api, pick(['tuesday either.', 'neither will tonight.']), 'boxed second'));
    api.frame(() => {
      for (let k = 0; k < 2 && y * cell < H; k++) {
        ctx.fillStyle = '#e8e8e8';
        for (let x = 0; x < cols; x++) if (row[x]) ctx.fillRect(x * cell, y * cell, cell, cell);
        const next = new Uint8Array(cols);
        for (let x = 0; x < cols; x++) {
          const l = row[(x - 1 + cols) % cols], c = row[x], r = row[(x + 1) % cols];
          next[x] = (30 >> ((l << 2) | (c << 1) | r)) & 1;
        }
        if (y % 3 === 0 && performance.now() - lastNote > 140) {
          const bits = (row[mid - 1] << 2) | (row[mid] << 1) | row[mid + 1];
          if (row[mid]) { S.bell(notes[bits], 0.035, 0, 1.2); lastNote = performance.now(); }
        }
        row = next; y++;
      }
    });
  });

  // ── 18. it snowed letters (and they spelled something) ──
  bump('lettersnow', 1.1, (stage, api) => {
    const { ctx, W, H } = api.canvas();
    const phrase = pick(['nobody chose this', 'stay where you are', 'it is still snowing', 'you can stay up', 'this is the channel']);
    const fs = Math.max(18, Math.min(64, Math.round(W / (phrase.length * 0.75))));
    ctx.font = `${fs}px 'Space Mono', monospace`;
    const cw = ctx.measureText('m').width, x0 = (W - cw * phrase.length) / 2, baseY = H * 0.55;
    const targets = [...phrase].map((ch, i) => ({ ch, x: x0 + cw * (i + 0.5) })).filter(t => t.ch !== ' ');
    targets.sort(() => Math.random() - 0.5);
    const flakes = [], landed = [];
    const S = synth(api);
    S.noise(11.5, 0.03, 500, 0.5); S.noise(11.5, 0.012, 1400, 2);
    const letters = 'abcdefghijklmnopqrstuvwxyz';
    let k = 0;
    // the real letters, one by one, each drifting toward its place
    api.every(Math.max(140, 6000 / targets.length), () => {
      if (k >= targets.length) return;
      const tg = targets[k++];
      flakes.push({ ch: tg.ch, x: rand(0, W), y: -fs, tx: tg.x, real: true, sway: rand(0, 6), v: rand(0.7, 1) });
    });
    // and decoys that fall straight through and melt
    api.every(120, () => flakes.push({ ch: letters[Math.floor(Math.random() * 26)], x: rand(0, W), y: -fs, real: false, sway: rand(0, 6), v: rand(0.6, 1.3) }));
    api.after(2200, () => caption(api, pick(['it snowed letters again.', 'the forecast called for vowels.', 'somebody will have to shovel this.']), 'top'));
    api.frame((t, dt) => {
      ctx.clearRect(0, 0, W, H);
      ctx.font = `${fs}px 'Space Mono', monospace`; ctx.textAlign = 'center'; ctx.textBaseline = 'alphabetic';
      ctx.fillStyle = '#f2f2f2';
      for (const l of landed) ctx.fillText(l.ch, l.x, baseY);
      for (let i = flakes.length - 1; i >= 0; i--) {
        const f = flakes[i];
        f.y += f.v * dt * 0.16;
        if (f.real) {
          const p = Math.min(1, Math.max(0, (f.y + fs) / (baseY + fs)));
          const x = f.x + (f.tx - f.x) * p * p + Math.sin(t / 380 + f.sway) * 10 * (1 - p);
          if (f.y >= baseY) { landed.push({ ch: f.ch, x: f.tx }); flakes.splice(i, 1); S.bell(pick(scale(79, [0, 1, 2, 3, 4, 5])), 0.025, 0, 0.9); continue; }
          ctx.globalAlpha = 1; ctx.fillText(f.ch, x, f.y);
        } else {
          if (f.y > H * 0.9) { flakes.splice(i, 1); continue; }
          ctx.globalAlpha = 0.25 * (1 - f.y / H);
          ctx.fillText(f.ch, f.x + Math.sin(t / 420 + f.sway) * 14, f.y);
        }
      }
      ctx.globalAlpha = 1;
    });
  });

  // ── 19. a phone, ringing for you ─────────────────────
  bump('phone', 0.9, (stage, api) => {
    const r = api.el('div', 'bs-ring');
    const S = synth(api);
    for (let k = 0; k < 3; k++) {
      api.after(400 + k * 2200, () => {
        r.textContent = 'ring.';
        r.style.left = rand(25, 75) + '%'; r.style.top = rand(30, 65) + '%';
        r.classList.remove('shake'); void r.offsetWidth; r.classList.add('shake');
        S.tone([440, 480], 1.4, 0.03);
      });
      api.after(400 + k * 2200 + 1500, () => { r.textContent = ''; });
    }
    api.after(7400, () => caption(api, 'it\'s for you.'));
    api.after(9800, () => { S.tone([480, 620], 0.25, 0.02); S.tone([480, 620], 0.25, 0.02, 0.5); S.tone([480, 620], 0.25, 0.02, 1.0); });
    api.after(9800, () => caption(api, pick(['they hung up.', 'they said they\'ll call back.', 'it was the moon again.']), 'second'));
  });

  // ── 20. the clock, briefly confused ───────────────────
  bump('clock', 0.9, (stage, api) => {
    const { ctx, W, H } = api.canvas();
    const R = Math.min(W, H) * 0.24, cx = W / 2, cy = H * 0.44;
    const S = synth(api);
    const start = new Date();
    let offset = 0, lastSec = -1;              // seconds added to real time
    api.after(9200, () => caption(api, pick(['sorry. it does that.', 'time is fine. it was just thinking.', 'we fixed it. don\'t worry about the missing minute.'])));
    api.frame((t, dt) => {
      // 0–3s normal, 3–7s spinning backwards, then snaps back to the real time
      const sec = t / 1000;
      if (sec > 3 && sec < 7) offset -= dt * 0.12; else if (sec >= 7) offset += (0 - offset) * 0.25;
      const now = new Date(start.getTime() + t + offset * 1000);
      const s2 = now.getSeconds() + now.getMilliseconds() / 1000, m = now.getMinutes() + s2 / 60, h = (now.getHours() % 12) + m / 60;
      const tickSec = Math.floor(s2);
      if (tickSec !== lastSec) { lastSec = tickSec; S.click(0.12, sec > 3 && sec < 7 ? 3800 : 1800); }
      ctx.clearRect(0, 0, W, H);
      ctx.strokeStyle = '#ddd'; ctx.lineWidth = 2;
      ctx.beginPath(); ctx.arc(cx, cy, R, 0, Math.PI * 2); ctx.stroke();
      for (let i = 0; i < 12; i++) {
        const a = i / 12 * Math.PI * 2;
        ctx.beginPath(); ctx.moveTo(cx + Math.sin(a) * R * 0.86, cy - Math.cos(a) * R * 0.86);
        ctx.lineTo(cx + Math.sin(a) * R * 0.95, cy - Math.cos(a) * R * 0.95); ctx.stroke();
      }
      const hand = (frac, len, w, col) => {
        const a = frac * Math.PI * 2; ctx.strokeStyle = col; ctx.lineWidth = w; ctx.lineCap = 'round';
        ctx.beginPath(); ctx.moveTo(cx, cy); ctx.lineTo(cx + Math.sin(a) * R * len, cy - Math.cos(a) * R * len); ctx.stroke();
      };
      hand(h / 12, 0.5, 5, '#eee'); hand(m / 60, 0.75, 3, '#eee'); hand(s2 / 60, 0.85, 1.5, '#e0102b');
    });
  });

  // ── 21. a television inside a television ─────────────
  bump('recursion', 0.9, (stage, api) => {
    const { ctx, W, H } = api.canvas();
    const S = synth(api);
    S.noise(11.5, 0.02, 3000, 0.4); S.tone(15734 / 4, 11.5, 0.004);   // a little flyback whine, an octave-ish down
    api.after(3500, () => caption(api, 'you are here.'));
    api.after(7500, () => caption(api, pick(['and here.', 'and here, a little smaller.', 'it\'s televisions all the way down.']), 'second'));
    const noise = document.createElement('canvas'); noise.width = 64; noise.height = 48;
    const nctx = noise.getContext('2d'), nimg = nctx.createImageData(64, 48);
    api.frame((t) => {
      for (let i = 0; i < nimg.data.length; i += 4) { const v = Math.random() * 90; nimg.data[i] = nimg.data[i + 1] = nimg.data[i + 2] = v; nimg.data[i + 3] = 255; }
      nctx.putImageData(nimg, 0, 0);
      ctx.fillStyle = '#000'; ctx.fillRect(0, 0, W, H);
      const zoom = 1 + (t / 1000 % 3) / 3;            // slowly falling inward, forever
      let w = W * 0.62 * zoom, h = w * 0.75, x = W / 2, y = H * 0.42;
      for (let d = 0; d < 9 && w > 4; d++) {
        ctx.fillStyle = d % 2 ? '#2a2620' : '#3a352c';
        const bez = w * 0.06;
        ctx.beginPath(); ctx.roundRect(x - w / 2 - bez, y - h / 2 - bez, w + bez * 2, h + bez * 2, bez); ctx.fill();
        ctx.imageSmoothingEnabled = false;
        ctx.globalAlpha = 0.5; ctx.drawImage(noise, x - w / 2, y - h / 2, w, h); ctx.globalAlpha = 1;
        ctx.fillStyle = 'rgba(0,0,0,0.55)'; ctx.fillRect(x - w / 2, y - h / 2, w, h);
        w *= 0.55; h *= 0.55;
      }
    });
  });

  // ── 22. what the chord looks like ────────────────────
  bump('scope', 0.9, (stage, api) => {
    const { ctx, W, H } = api.canvas();
    const S = synth(api);
    // the same ratios you hear, drawn as a Lissajous figure
    const pairs = [[2, 3], [3, 4], [4, 5], [3, 5]];
    const [a, b] = pick(pairs), base = pick([110, 130.8, 146.8]);
    S.tone([base * a, base * b], 11, 0.02, 0.3, 'sine');
    api.after(5500, () => caption(api, pick(['this is what the sound looks like.', 'a perfect fifth, from the side.', 'two notes, holding hands.'])));
    const R = Math.min(W, H) * 0.3;
    api.frame((t) => {
      ctx.fillStyle = 'rgba(0,0,0,0.18)'; ctx.fillRect(0, 0, W, H);
      ctx.strokeStyle = '#7dffb0'; ctx.lineWidth = 1.6; ctx.shadowColor = '#7dffb0'; ctx.shadowBlur = 10;
      const ph = t / 1000 * 0.6;
      ctx.beginPath();
      for (let i = 0; i <= 600; i++) {
        const u = i / 600 * Math.PI * 2;
        const x = W / 2 + Math.sin(a * u + ph) * R, y = H * 0.42 + Math.sin(b * u) * R * 0.8;
        i ? ctx.lineTo(x, y) : ctx.moveTo(x, y);
      }
      ctx.stroke(); ctx.shadowBlur = 0;
    });
  });

  window.SG_BUMPS = BUMPS;
})();
