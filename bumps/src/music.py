#!/usr/bin/env python3
"""Sound for the snow-globe bumps. Every bed is synthesized here with numpy:
no samples, no recordings, nothing to license.

  python3 bumps/src/music.py OUTDIR [id ...]   -> OUTDIR/<id>.wav (48 kHz stereo, 12 s)

Tempos are chosen so that phrases land on the text cuts: 60/120 bpm gives
4-second phrases (three cards), 80 bpm gives 3-second bars (four cards).
"""
import math, os, sys, wave
import numpy as np
from scipy import signal

SR = 48000
DUR = 12.0
N = int(SR * DUR)


def mtof(m):
    return 440.0 * 2 ** ((m - 69) / 12.0)


def tt(dur):
    return np.arange(int(dur * SR)) / SR


def fade_tail(x, ms=40):
    n = min(len(x), int(SR * ms / 1000))
    if n > 0:
        x[-n:] *= np.linspace(1, 0, n)
    return x


def filt(x, kind, freq, order=2):
    sos = signal.butter(order, freq, kind, fs=SR, output='sos')
    return signal.sosfilt(sos, x, axis=0)


class Mix:
    def __init__(self, seed=1):
        self.b = np.zeros((N + SR * 4, 2))
        self.wet = np.zeros((N + SR * 4, 2))
        self.rng = np.random.default_rng(seed)

    def add(self, sig, t, gain=1.0, pan=0.0, send=0.0):
        i = int(round(t * SR))
        if i < 0:
            sig = sig[-i:]; i = 0
        if i >= len(self.b): return
        sig = sig[: len(self.b) - i]
        l = math.cos((pan + 1) * math.pi / 4) * gain
        r = math.sin((pan + 1) * math.pi / 4) * gain
        if sig.ndim == 1:
            st = np.stack([sig * l, sig * r], axis=1) * 1.4142
        else:
            st = sig * gain
        self.b[i:i + len(st)] += st
        if send:
            self.wet[i:i + len(st)] += st * send

    def render(self, reverb=1.8, lowpass=9000, wow=0.0, drive=1.0, fade_out=0.5, fade_in=0.02, end=11.92,
               highpass=35):
        x = self.b
        if reverb and np.abs(self.wet).max() > 0:
            n = int(SR * reverb * 1.4)
            env = np.exp(-6.9 * np.arange(n) / (SR * reverb))
            ir = self.rng.standard_normal((n, 2)) * env[:, None]
            ir = filt(ir, 'lowpass', 5200)
            ir = filt(ir, 'highpass', 250)
            ir[: int(SR * 0.012)] = 0
            ir /= np.sqrt((ir ** 2).sum(axis=0)).max()
            w = np.stack([signal.fftconvolve(self.wet[:, c], ir[:, c])[: len(x)] for c in (0, 1)], axis=1)
            x = x + w
        x = x[:N].copy()
        if wow:
            idx = np.arange(N) + wow * SR * 0.001 * (np.sin(2 * np.pi * 0.55 * np.arange(N) / SR)
                                                     + 0.3 * np.sin(2 * np.pi * 3.1 * np.arange(N) / SR))
            idx = np.clip(idx, 0, N - 1)
            x = np.stack([np.interp(idx, np.arange(N), x[:, c]) for c in (0, 1)], axis=1)
        x = filt(x, 'highpass', highpass)
        if lowpass:
            x = filt(x, 'lowpass', lowpass)
        peak = np.abs(x).max() or 1.0
        x = np.tanh(x / peak * drive * 1.2) / np.tanh(drive * 1.2)
        e = int(end * SR)
        x[e:] = 0
        fo = int(fade_out * SR)
        x[e - fo:e] *= np.linspace(1, 0, fo)[:, None] ** 1.5
        fi = int(fade_in * SR)
        x[:fi] *= np.linspace(0, 1, fi)[:, None]
        return x * 0.7


# ── instruments ─────────────────────────────────────────

def epiano(m, dur, vel=0.8):
    f = mtof(m); t = tt(dur + 0.25)
    idx = vel * 2.6 * np.exp(-t * 5) + 0.35
    x = np.sin(2 * np.pi * f * t + idx * np.sin(2 * np.pi * f * t))
    x += 0.10 * vel * np.sin(2 * np.pi * f * 7.01 * t) * np.exp(-t * 22)
    env = np.exp(-t * (0.9 + f / 700)) * (1 - np.exp(-t * 500))
    rel = np.ones_like(t); k = int(dur * SR)
    rel[k:] = np.exp(-(t[k:] - dur) * 18)
    return fade_tail(x * env * rel * vel, 30)


def piano(m, dur, vel=0.8, tack=False):
    f = mtof(m); t = tt(dur + 0.3)
    x = np.zeros_like(t)
    B = 0.0004
    for det in ((0.0, 4.0) if tack else (0.0,)):
        for k in range(1, 11):
            fk = f * 2 ** (det / 1200) * k * math.sqrt(1 + B * k * k)
            if fk > 9000: break
            a = (1.0 / k ** (0.9 if tack else 1.25)) * (0.6 + 0.4 * vel)
            x += a * np.sin(2 * np.pi * fk * t + k) * np.exp(-t * (1.6 + 0.9 * k + f / 500))
    x *= (1 - np.exp(-t * 900))
    k = int(dur * SR)
    x[k:] *= np.exp(-(t[k:] - dur) * 22)
    return fade_tail(x * vel * 0.6, 30)


def bass(m, dur, vel=0.9):
    f = mtof(m); t = tt(dur + 0.08)
    x = np.sin(2 * np.pi * f * t) + 0.45 * np.sin(2 * np.pi * 2 * f * t) + 0.18 * np.sin(2 * np.pi * 3 * f * t)
    env = (1 - np.exp(-t * 220)) * (0.55 + 0.45 * np.exp(-t * 4))
    k = int(dur * SR)
    env[k:] *= np.exp(-(t[k:] - dur) * 60)
    return fade_tail(np.tanh(x * env * vel * 1.2), 20)


def pad(midis, dur, vel=0.5, cutoff=900, attack=1.2, release=1.5):
    t = tt(dur + release)
    x = np.zeros_like(t)
    for m in midis:
        for det in (-7, 6):
            f = mtof(m) * 2 ** (det / 1200)
            x += signal.sawtooth(2 * np.pi * f * t + m)
    x = filt(x, 'lowpass', cutoff, 2)
    env = np.minimum(1, t / attack)
    k = int(dur * SR)
    env[k:] *= np.linspace(1, 0, len(t) - k)
    return x * env * vel / max(1, len(midis))


def organ(m, dur, vel=0.6, bars=(0.5, 1.0, 0.0, 0.55, 0.0, 0.3, 0.0, 0.0, 0.12)):
    f = mtof(m); t = tt(dur + 0.06)
    ratios = (0.5, 1, 1.5, 2, 3, 4, 5, 6, 8)
    vib = 1 + 0.0035 * np.sin(2 * np.pi * 6.3 * t)
    ph = 2 * np.pi * f * np.cumsum(vib) / SR
    x = sum(a * np.sin(r * ph) for r, a in zip(ratios, bars) if a)
    env = np.minimum(1, t / 0.012)
    k = int(dur * SR)
    env[k:] *= np.linspace(1, 0, len(t) - k)
    trem = 1 + 0.12 * np.sin(2 * np.pi * 6.3 * t + 1.0)
    return x * env * trem * vel * 0.4


def bell(m, dur=2.5, vel=0.6, partials=((1, 1, 1.6), (2.76, 0.4, 3.5), (5.4, 0.18, 7), (8.9, 0.07, 12))):
    f = mtof(m); t = tt(dur)
    x = sum(a * np.sin(2 * np.pi * f * r * t) * np.exp(-t * d) for r, a, d in partials if f * r < 16000)
    return fade_tail(x * (1 - np.exp(-t * 1500)) * vel, 60)


def musicbox(m, dur=2.2, vel=0.6):
    return bell(m, dur, vel, ((1, 1, 2.6), (2.0, 0.12, 5), (3.0, 0.22, 7), (6.27, 0.12, 14), (9.1, 0.05, 25)))


def marimba(m, dur=0.9, vel=0.7):
    return bell(m, dur, vel, ((1, 1, 7), (3.9, 0.3, 20), (9.2, 0.12, 45)))


def glock(m, dur=1.6, vel=0.5):
    return bell(m, dur, vel, ((1, 1, 3.5), (2.76, 0.3, 8), (5.4, 0.1, 16)))


def pluck(m, dur=1.6, vel=0.7, damp=0.996, seed=0):
    f = mtof(m); n = int(dur * SR)
    L = max(2, int(round(SR / f)))
    rng = np.random.default_rng(seed + int(m * 7))
    x = np.zeros(n); x[:L] = rng.uniform(-1, 1, L)
    x[:L] = filt(x[:L], 'lowpass', min(6000, f * 9), 1)
    a = np.zeros(L + 2); a[0] = 1; a[L] = -0.5 * damp; a[L + 1] = -0.5 * damp
    y = signal.lfilter([1], a, x)
    return fade_tail(y * vel * 0.5, 50)


def noise(n, rng):
    return rng.standard_normal(n)


def kick(vel=1.0, f0=150, f1=46, decay=9):
    t = tt(0.4)
    f = f1 + (f0 - f1) * np.exp(-t * 30)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * decay)
    x[: int(0.003 * SR)] += 0.4 * np.linspace(1, 0, int(0.003 * SR))
    return fade_tail(np.tanh(x * 1.6) * vel, 30)


def snare(rng, vel=0.8, decay=20, tone=185, lo=1200, hi=7000):
    t = tt(0.3)
    n = filt(noise(len(t), rng), 'bandpass', (lo, hi)) * np.exp(-t * decay)
    x = n + 0.5 * np.sin(2 * np.pi * tone * t) * np.exp(-t * 28)
    return fade_tail(x * vel * 0.7, 20)


def hat(rng, vel=0.4, decay=95, hp=7000):
    t = tt(0.3 if decay < 30 else 0.09)
    return fade_tail(filt(noise(len(t), rng), 'highpass', hp, 3) * np.exp(-t * decay) * vel * 0.5, 5)


def rim(rng, vel=0.6, f=1750):
    t = tt(0.08)
    x = np.sin(2 * np.pi * f * t) * np.exp(-t * 110) + 0.5 * np.sin(2 * np.pi * f * 0.53 * t) * np.exp(-t * 90)
    x += 0.3 * filt(noise(len(t), rng), 'bandpass', (1800, 4500)) * np.exp(-t * 220)
    return fade_tail(x * vel * 0.6, 5)


def shaker(rng, vel=0.3):
    t = tt(0.09)
    env = np.minimum(1, t / 0.012) * np.exp(-np.maximum(0, t - 0.012) * 55)
    return filt(noise(len(t), rng), 'bandpass', (4500, 9500)) * env * vel * 0.5


def woodblock(rng, vel=0.6, f=880):
    t = tt(0.12)
    x = np.sin(2 * np.pi * f * t) * np.exp(-t * 55) + 0.4 * np.sin(2 * np.pi * f * 2.4 * t) * np.exp(-t * 90)
    return fade_tail(x * vel * 0.6, 5)


def crackle(mix, amount=1.0, hiss=0.004):
    rng = mix.rng
    n = N
    x = np.zeros(n)
    k = rng.poisson(14 * DUR * amount)
    pos = rng.integers(0, n - 200, k)
    for p in pos:
        a = rng.uniform(0.02, 0.12) * (4 if rng.random() < 0.06 else 1)
        L = rng.integers(8, 60)
        x[p:p + L] += a * rng.uniform(-1, 1) * np.exp(-np.arange(L) / (L / 4))
    x = filt(x, 'bandpass', (900, 7000))
    h = filt(noise(n, rng), 'bandpass', (1500, 9000)) * hiss
    r = filt(noise(n, rng), 'lowpass', 90) * 0.01
    mix.add(x * 0.5 + h + r, 0, 1.0, 0.1)


# ── chords ──────────────────────────────────────────────
CH = {
    'Dm9':    (38, (53, 57, 60, 64)), 'G13':   (43, (53, 57, 59, 64)), 'Cmaj9': (36, (52, 55, 59, 62)),
    'A7b13':  (33, (55, 61, 65)),     'Fmaj7': (41, (57, 60, 64)),     'Em7':   (40, (55, 59, 62)),
    'Am9':    (45, (55, 59, 60, 64)), 'D9':    (38, (54, 57, 60, 64)), 'Ebmaj7': (39, (55, 58, 62)),
    'Abmaj7': (44, (55, 60, 63)),     'Bbmaj7': (46, (57, 62, 65)),    'Gm9':   (43, (53, 57, 58, 62)),
    'C9':     (36, (52, 58, 62)),     'Fm9':   (41, (56, 60, 63, 67)), 'Bb13':  (46, (56, 60, 62, 67)),
    'Dbmaj7': (37, (53, 56, 60)),     'Cm9':   (36, (51, 55, 58, 62)), 'F13':   (41, (51, 55, 57, 62)),
    'Bbmaj9': (46, (53, 57, 60, 62)), 'G7b9':  (43, (53, 56, 59, 62)), 'C':     (36, (52, 55, 60)),
    'F':      (41, (53, 57, 60)),     'G':     (43, (55, 59, 62)),     'G7':    (43, (53, 55, 59)),
    'Am':     (45, (52, 57, 60)),     'Dm':    (38, (53, 57, 62)),     'C6':    (36, (52, 55, 57, 60)),
    'E7':     (40, (56, 59, 62)),     'D7':    (38, (54, 57, 60)),     'A7':    (45, (55, 57, 61)),
}


def strum(mix, inst, notes, t, dur, vel, pan=0.0, send=0.25, spread=0.014, gain=1.0):
    for i, m in enumerate(notes):
        mix.add(inst(m, dur, vel * (0.92 + 0.08 * (i % 2))), t + i * spread, gain, pan + (i - len(notes) / 2) * 0.08, send)


# ── bed: lo-fi beat (the default sound of this channel between programs) ──
def lofi(chords, bpm=80, seed=1, keys='ep', drums='boombap', swing=0.58, melody=None, mel_inst=None,
         stop_bar=None, lowpass=7500, crackle_amt=1.0, bass_on=True, key_gain=0.5):
    """chords: one name per bar. 4/4. 80 bpm -> 4 bars, 120 -> 6, 60 -> 3."""
    mix = Mix(seed); rng = mix.rng
    beat = 60.0 / bpm
    bars = int(round(DUR / (4 * beat)))
    inst = {'ep': epiano, 'piano': piano, 'organ': organ}[keys]
    stop_bar = bars - 1 if stop_bar is None else stop_bar

    def sw(b):  # swung position of a beat (b in beats, 8th-note swing)
        frac = b % 1.0
        if abs(frac - 0.5) < 1e-6: return (math.floor(b) + swing) * beat
        if abs(frac - 0.25) < 1e-6: return (math.floor(b) + swing / 2) * beat
        if abs(frac - 0.75) < 1e-6: return (math.floor(b) + swing + (1 - swing) / 2) * beat
        return b * beat

    for bar in range(bars):
        name = chords[bar % len(chords)]
        root, voicing = CH[name]
        b0 = bar * 4
        last = bar == bars - 1
        human = lambda: rng.uniform(-0.006, 0.008)
        # keys
        strum(mix, inst, voicing, sw(b0) + human(), beat * (3.6 if last else 2.2), 0.62, -0.15, 0.3, gain=key_gain)
        if not last:
            strum(mix, inst, voicing[1:], sw(b0 + 2.5) + human(), beat * 1.2, 0.42, 0.15, 0.3, gain=key_gain)
        # bass
        if bass_on:
            mix.add(bass(root, beat * (3.0 if last else 1.6)), sw(b0), 0.22)
            if not last:
                mix.add(bass(root + 7 if root < 40 else root - 5, beat * 0.45, 0.7), sw(b0 + 2.5), 0.19)
                mix.add(bass(root, beat * 0.7, 0.8), sw(b0 + 3), 0.2)
        # drums
        if drums == 'none': continue
        cut = last and bar >= stop_bar
        for b in np.arange(0, 4, 0.5):
            if cut and b > 0.01: break
            v = 0.34 if b % 1 == 0 else 0.2
            mix.add(hat(rng, v * rng.uniform(0.8, 1.1)), sw(b0 + b) + human(), 0.8, 0.25)
        if drums == 'boombap':
            ks = [0, 1.5, 2.5] if bar % 2 == 0 else [0, 2.25, 2.5]
            ss = [1, 3]
        else:  # 'half': half-time, sparse
            ks = [0, 2.5] if bar % 2 == 0 else [0, 1.5]
            ss = [2]
        for b in ks:
            if cut and b > 0.01: break
            mix.add(kick(0.95), sw(b0 + b) + human(), 0.46)
        for b in ss:
            if cut: break
            mix.add(snare(rng, 0.75), sw(b0 + b) + human() + 0.008, 0.56, 0.05, 0.12)
    if melody:
        mi = mel_inst or glock
        for b, m, v in melody:
            mix.add(mi(m, vel=v), sw(b), 0.3, 0.2, 0.35)
    if crackle_amt:
        crackle(mix, crackle_amt)
    return mix.render(reverb=1.4, lowpass=lowpass, wow=1.2, drive=1.25)


# ── bed: drift (pads and a few bells, for long held shots) ──
def drift(root_chord, bells, seed=2, bell_inst=bell, cutoff=850, low=None, lowpass=8000, pad_vel=0.5,
          noise_bed=0.0, noise_band=(200, 900), chord2=None):
    mix = Mix(seed); rng = mix.rng
    mix.add(pad(root_chord, 5.6 if chord2 else 10.2, pad_vel, cutoff, attack=1.6, release=2.0), 0.0, 0.5, 0, 0.5)
    if chord2:
        mix.add(pad(chord2, 4.8, pad_vel, cutoff, attack=2.0, release=1.6), 5.6, 0.5, 0, 0.5)
    if low:
        t = tt(11.5)
        x = (np.sin(2 * np.pi * mtof(low) * t) + 0.4 * np.sin(2 * np.pi * mtof(low) * 2.003 * t)) * np.minimum(1, t / 2.5)
        mix.add(fade_tail(x, 1500), 0.0, 0.08)
    for t0, m, v in bells:
        mix.add(bell_inst(m, vel=v), t0, 0.32, rng.uniform(-0.5, 0.5), 0.6)
    if noise_bed:
        n = filt(noise(N, rng), 'bandpass', noise_band)
        lfo = 0.6 + 0.4 * np.sin(2 * np.pi * 0.13 * np.arange(N) / SR + 1)
        mix.add(n * lfo * noise_bed, 0, 1.0)
    return mix.render(reverb=3.2, lowpass=lowpass, wow=0.8, drive=0.9, fade_out=1.2, fade_in=0.4)


# ── bed: lounge (drum machine bossa, organ, for commercials) ──
def lounge(chords, bpm=120, seed=3, melody=None, comp='organ', stinger=None, lowpass=7500, mel_inst=None):
    mix = Mix(seed); rng = mix.rng
    beat = 60.0 / bpm
    bars = int(round(DUR / (4 * beat)))
    inst = organ if comp == 'organ' else epiano
    for bar in range(bars):
        root, voicing = CH[chords[bar % len(chords)]]
        b0 = bar * 4; last = bar == bars - 1
        T = lambda b: (b0 + b) * beat
        # bossa clave on rim, steady shaker, soft kick
        for b in (0, 1.5, 3) if bar % 2 == 0 else (1, 2.5):
            if last and b > 0: break
            mix.add(rim(rng, 0.55), T(b), 0.5, -0.3, 0.2)
        for b in np.arange(0, 4, 0.5):
            if last and b > 0.4: break
            mix.add(shaker(rng, 0.34 if b % 1 else 0.22), T(b), 0.5, 0.4)
        for b in (0, 1.5, 2, 3.5):
            if last and b > 0: break
            mix.add(kick(0.6, 110, 52, 14), T(b), 0.3)
        # comp: bossa stabs
        for b, d in ((0, 1.2), (1.5, 0.4), (2.5, 0.9)) if not last else ((0, 3.2),):
            strum(mix, inst, voicing, T(b), beat * d, 0.55, 0.1, 0.25, spread=0.004, gain=0.36)
        mix.add(bass(root, beat * (2.5 if last else 1.3), 0.8), T(0), 0.22)
        if not last:
            mix.add(bass(root + 7 if root < 40 else root - 5, beat * 0.4, 0.7), T(1.5), 0.2)
            mix.add(bass(root + 7 if root < 40 else root - 5, beat * 1.2, 0.8), T(2), 0.21)
            mix.add(bass(root, beat * 0.4, 0.7), T(3.5), 0.19)
    for b, m, v in (melody or []):
        mix.add((mel_inst or glock)(m, vel=v), b * beat, 0.3, 0.25, 0.4)
    if stinger:
        stinger(mix)
    crackle(mix, 0.5, 0.003)
    return mix.render(reverb=1.2, lowpass=lowpass, wow=1.0, drive=1.1)


# ── bed: parlor piano (ragtime-ish two-step, for very old film) ──
def parlor(chords, bpm=120, seed=4, melody=None, tack=True, march=False, lowpass=6000):
    mix = Mix(seed); rng = mix.rng
    beat = 60.0 / bpm
    bars = int(round(DUR / (4 * beat)))
    pn = lambda m, d, v: piano(m, d, v, tack=tack)
    for bar in range(bars):
        root, voicing = CH[chords[bar % len(chords)]]
        b0 = bar * 4; last = bar == bars - 1
        T = lambda b: (b0 + b) * beat + rng.uniform(-0.005, 0.006)
        if last:
            mix.add(pn(root, 2.5, 0.9), T(0), 0.5, -0.2, 0.2)
            mix.add(pn(root + 12, 2.5, 0.8), T(0), 0.4, -0.2, 0.2)
            strum(mix, pn, [v + 0 for v in voicing], T(0), 2.5, 0.8, 0.1, 0.25, spread=0.02, gain=0.36)
            strum(mix, pn, [v + 12 for v in voicing], T(1), 2.0, 0.6, 0.2, 0.25, spread=0.03, gain=0.3)
            continue
        fifth = root + 7 if root < 40 else root - 5
        for b, m in ((0, root), (2, fifth)):
            mix.add(pn(m, beat * 0.9, 0.85), T(b), 0.5, -0.25, 0.15)
            mix.add(pn(m + 12, beat * 0.9, 0.6), T(b), 0.3, -0.25, 0.15)
        for b in (1, 3):
            strum(mix, pn, voicing, T(b), beat * 0.45, 0.6, 0.0, 0.15, spread=0.003, gain=0.3)
        if march:
            for b in (1, 3):
                mix.add(snare(rng, 0.5, 30, 220, 1500, 8000), T(b), 0.3, 0.2, 0.15)
            for b in (0, 2):
                mix.add(kick(0.7, 100, 60, 12), T(b), 0.4)
            # a little roll into the next bar
            for k in range(4):
                mix.add(snare(rng, 0.25 + 0.06 * k, 45, 220, 1500, 8000), T(3.5 + k * 0.125), 0.3, 0.2, 0.1)
    for b, m, v in (melody or []):
        inst = glock if march else pn
        if march: mix.add(inst(m, vel=v), b * beat, 0.34, 0.3, 0.35)
        else: mix.add(pn(m, beat * 0.6, v), b * beat + rng.uniform(-0.004, 0.004), 0.42, 0.3, 0.2)
    crackle(mix, 1.6, 0.006)
    return mix.render(reverb=0.9, lowpass=lowpass, wow=2.2, drive=1.3, highpass=120)


# ── bed: music box ──────────────────────────────────────
def box(melody, bpm=120, seed=5, chord=None, pad_vel=0.3, wind=0.0):
    mix = Mix(seed); rng = mix.rng
    beat = 60.0 / bpm
    for b, m, v in melody:
        mix.add(musicbox(m, vel=v), b * beat + rng.uniform(-0.007, 0.007), 0.36, rng.uniform(-0.3, 0.3), 0.45)
        # the comb's mechanical tick
        mix.add(rim(rng, 0.05, 3200), b * beat, 0.3, 0.0, 0.0)
    if chord:
        mix.add(pad(chord, 10.0, pad_vel, 700, attack=2.0, release=2.0), 0.0, 0.5, 0, 0.5)
    if wind:
        n = filt(noise(N, rng), 'bandpass', (250, 700))
        lfo = 0.55 + 0.45 * np.sin(2 * np.pi * 0.11 * np.arange(N) / SR)
        mix.add(n * lfo * wind, 0, 1.0)
    return mix.render(reverb=2.2, lowpass=8500, wow=1.6, drive=0.9, fade_out=1.0)


# ── the beds, one per bump ──────────────────────────────
def mel(beats_notes, vel=0.5):
    return [(b, m, vel if len(x) < 3 else x[2]) for x in beats_notes for b, m in [x[:2]]]


BEDS = {}
def bed(name):
    def deco(fn): BEDS[name] = fn; return fn
    return deco


@bed('station')
def _station():
    # a lullaby in C, three 4-second phrases, 120 bpm in 8ths
    m = [(0, 76), (1, 72), (2, 67), (3, 72), (4, 76), (5, 79), (6, 76, 0.4), (7, 72, 0.4),
         (8, 77), (9, 72), (10, 69), (11, 72), (12, 77), (13, 81), (14, 77, 0.4), (15, 72, 0.4),
         (16, 79), (17, 76), (18, 72), (19, 67), (20, 74), (21, 71), (22, 72, 0.6)]
    return box(mel(m, 0.55), 120, 5, chord=(48, 55, 64), pad_vel=0.22)


@bed('snow')
def _snow():
    m = [(0, 81), (1.5, 76), (3, 72), (4, 74), (6, 69, 0.4),
         (8, 79), (9.5, 76), (11, 72), (12, 71), (14, 67, 0.4),
         (16, 76), (17.5, 72), (19, 69), (20, 72, 0.6)]
    return box(mel(m, 0.5), 120, 6, chord=(45, 52, 60, 64), pad_vel=0.3, wind=0.05)


@bed('jelly')
def _jelly():
    bells = [(0.6, 74, 0.5), (2.1, 81, 0.35), (4.0, 78, 0.45), (5.3, 86, 0.25), (6.6, 73, 0.4), (8.0, 81, 0.45), (9.4, 85, 0.25), (10.2, 78, 0.3)]
    return drift((50, 57, 61, 66), bells, 7, cutoff=700, low=38, noise_bed=0.05, noise_band=(120, 500))


@bed('orbit')
def _orbit():
    arp = [69, 76, 81, 83, 88, 83, 81, 76]
    bells = [(0.5 + i * 0.5, arp[i % 8] - (0 if i < 16 else 2 if i % 8 in (2, 3, 6) else 0), 0.3 + 0.1 * (i % 4 == 0)) for i in range(21)]
    return drift((45, 52, 57, 60, 64), bells, 8, bell_inst=lambda m, vel: pluck(m, 2.0, vel, 0.997), cutoff=1000, low=33, pad_vel=0.45)


@bed('lava')
def _lava():
    notes = [(0.8, 50), (1.55, 57), (2.3, 60), (4.0, 55), (4.75, 62), (5.5, 65, 0.4), (8.0, 50), (8.75, 57), (9.5, 64, 0.4)]
    bells = [(t, m, 0.5 if len(r) == 0 else r[0]) for t, m, *r in notes]
    return drift((38, 45, 53, 57), bells, 9, bell_inst=lambda m, vel: marimba(m, 1.4, vel), cutoff=500, low=26,
                 pad_vel=0.6, noise_bed=0.09, noise_band=(60, 260), lowpass=6000)


@bed('tvfield')
def _tvfield():
    mix = Mix(10); rng = mix.rng
    t = np.arange(N) / SR
    w = filt(noise(N, rng), 'bandpass', (180, 620)) * (0.5 + 0.5 * np.sin(2 * np.pi * 0.09 * t + 0.4)) ** 2
    w2 = filt(noise(N, rng), 'bandpass', (500, 1400)) * (0.5 + 0.5 * np.sin(2 * np.pi * 0.17 * t + 2.0)) ** 3
    mix.add(w * 0.22 + w2 * 0.07, 0, 1.0, -0.1)
    # the set: mains hum and a thin carrier, slightly to the right
    hum = 0.05 * np.sin(2 * np.pi * 60 * t) + 0.035 * np.sin(2 * np.pi * 120 * t) + 0.02 * np.sin(2 * np.pi * 180 * t)
    car = 0.012 * np.sin(2 * np.pi * 1000 * t) * (0.7 + 0.3 * np.sin(2 * np.pi * 0.3 * t))
    mix.add((hum + car) * np.minimum(1, t / 1.5), 0, 1.0, 0.25, 0.1)
    for t0, m in ((1.0, 64), (4.0, 71), (5.0, 67), (8.0, 62), (9.0, 69)):
        mix.add(epiano(m, 2.5, 0.45), t0, 0.26, -0.2, 0.7)
    mix.add(pad((40, 47, 55), 10.5, 0.3, 500, 2.5, 1.5), 0, 0.5, 0, 0.5)
    return mix.render(reverb=3.0, lowpass=7000, wow=1.0, drive=0.9, fade_out=1.0, fade_in=0.4)


@bed('fridge')
def _fridge():
    mix = Mix(11); rng = mix.rng
    t = np.arange(N) / SR
    # room tone, then the door: seal pop, hum gets louder and brighter while it is open
    room = filt(noise(N, rng), 'lowpass', 300) * 0.02
    op, cl = 1.5, 10.2
    openness = np.clip((t - op) / 0.5, 0, 1) * np.clip((cl + 0.35 - t) / 0.35, 0, 1)
    hum = (0.10 * np.sin(2 * np.pi * 60 * t) + 0.07 * np.sin(2 * np.pi * 120 * t + 0.4) + 0.03 * np.sin(2 * np.pi * 180 * t)
           + 0.018 * np.sin(2 * np.pi * 239.4 * t) + 0.012 * np.sin(2 * np.pi * 361 * t))
    fan = filt(noise(N, rng), 'bandpass', (300, 1800)) * 0.03
    mix.add(room + hum * (0.35 + 0.65 * openness) + fan * openness, 0, 1.0)
    pop = filt(noise(int(0.12 * SR), rng), 'bandpass', (150, 900)) * np.exp(-tt(0.12) * 40)
    mix.add(pop, op - 0.05, 0.9, 0, 0.2)
    mix.add(kick(0.5, 90, 50, 25), op - 0.05, 0.5)
    for i, (dt, f) in enumerate(((0.25, 1900), (0.4, 2600), (0.52, 2200))):   # bottles in the door
        mix.add(bell(69, 0.5, 0.25, ((f / 440, 1, 14), (f / 440 * 2.3, 0.3, 25))), op + dt, 0.25, 0.3, 0.3)
    mix.add(kick(0.9, 80, 42, 18), cl + 0.3, 0.7, 0, 0.25)
    mix.add(pop * 0.6, cl + 0.3, 0.8, 0, 0.2)
    for t0, m in ((4.0, 60), (4.0, 67), (8.0, 58), (8.0, 65)):
        mix.add(epiano(m, 3.0, 0.4), t0, 0.2, 0, 0.6)
    return mix.render(reverb=1.6, lowpass=7000, drive=1.0, fade_out=0.6, fade_in=0.3)


def pingpong_sfx(mix, t0=4.0):
    rng = mix.rng
    def tock(vel, f):
        t = tt(0.06)
        return (np.sin(2 * np.pi * f * t) * np.exp(-t * 70) + 0.4 * filt(noise(len(t), rng), 'bandpass', (2000, 6000)) * np.exp(-t * 200)) * vel
    # density rises fast, then thins out as they settle
    t = t0
    while t < 10.8:
        x = (t - t0)
        rate = 55 * math.exp(-((x - 1.6) / 1.3) ** 2) + 9 * math.exp(-x / 3.5) + 0.3
        t += rng.exponential(1.0 / rate)
        v = rng.uniform(0.15, 0.6) * (1.0 if x < 3.5 else 0.6)
        mix.add(tock(v, rng.uniform(1900, 3100)), t, 0.3, rng.uniform(-0.8, 0.8), 0.25)


@bed('pingpong')
def _pingpong():
    return lounge(['Fmaj7', 'Fmaj7', 'Gm9', 'C9', 'Fmaj7', 'Fmaj7'], 120, 12, stinger=pingpong_sfx, comp='ep')


@bed('sponsor')
def _sponsor():
    def fanfare(mix):
        for i, (b, ms) in enumerate(((0, (60, 64, 67)), (0.5, (60, 64, 67)), (1, (65, 69, 72)), (2, (67, 71, 74, 79)))):
            for m in ms:
                mix.add(organ(m + 12, 0.22 if i < 2 else 0.8, 0.5, (0, 1, 0.6, 0.8, 0.5, 0.4, 0.3, 0.2, 0.2)), b * 0.5, 0.2, 0.0, 0.3)
        for t0, m in ((4.05, 91), (4.4, 96), (6.1, 93), (8.6, 98), (9.0, 91)):   # sparkles on nothing
            mix.add(glock(m, 1.2, 0.35), t0, 0.22, 0.4, 0.6)
    return lounge(['Cmaj9', 'A7b13', 'Dm9', 'G13', 'Cmaj9', 'Cmaj9'], 120, 13, stinger=fanfare)


@bed('remote')
def _remote():
    m = [(0, 79), (1.5, 76), (3, 72), (4, 74), (5.5, 77), (7, 81, 0.4), (8, 79), (9.5, 76), (11, 72), (12, 71), (13.5, 74), (15, 67, 0.4),
         (16, 76), (17.5, 79), (19, 84), (20, 83, 0.5)]
    return lounge(['C6', 'Dm9', 'C6', 'G13', 'Fmaj7', 'C6'], 120, 14, melody=mel(m, 0.5), mel_inst=lambda m, vel: marimba(m, 0.9, vel))


@bed('sneeze')
def _sneeze():
    m = [(0, 72), (0.5, 76), (1, 79), (1.5, 76), (2, 84), (3, 79), (4, 77), (4.5, 81), (5, 84), (5.5, 81), (6, 89, 0.7), (7, 84),
         (8, 79), (8.5, 83), (9, 86), (9.5, 83), (10, 91), (11, 86), (12, 84), (12.5, 79), (13, 76), (13.5, 79), (14, 84), (15, 79),
         (16, 81), (16.5, 77), (17, 81), (17.5, 84), (18, 83), (19, 86), (20, 84, 0.8)]
    return parlor(['C', 'F', 'G7', 'C', 'F', 'C'], 120, 15, melody=mel(m, 0.6))


@bed('bert')
def _bert():
    m = [(0, 79), (1, 79), (1.5, 81), (2, 79), (3, 76), (4, 77), (5, 77), (5.5, 79), (6, 77), (7, 74),
         (8, 79), (9, 84), (10, 83), (11, 81), (12, 79), (13, 76), (14, 79, 0.4),
         (16, 81), (17, 84), (18, 83), (19, 79), (20, 84, 0.6)]
    return parlor(['C', 'G7', 'C', 'C', 'F', 'C'], 120, 16, melody=mel(m, 0.5), march=True, tack=False, lowpass=6500)


@bed('market')
def _market():
    return lofi(['Dm9', 'G13', 'Cmaj9'], 60, 17, keys='piano', drums='half', lowpass=5600, crackle_amt=1.8, key_gain=1.0,
                melody=mel([(2, 76), (3, 77), (3.5, 81, 0.35), (6, 74), (7, 76), (7.5, 79, 0.35), (10, 71), (11, 74, 0.4)], 0.42), mel_inst=lambda m, vel: piano(m, 1.2, vel))


@bed('hands')
def _hands():
    mix = Mix(18); rng = mix.rng
    beat = 0.5
    ost = [50, 57, 62, 57, 53, 57, 62, 65]
    ost2 = [48, 55, 60, 55, 52, 55, 60, 64]
    ost3 = [46, 53, 58, 53, 50, 53, 58, 62]
    for i in range(46):
        bar = i // 16
        seq = (ost, ost2, ost3)[min(bar, 2)]
        mix.add(marimba(seq[i % 8] + 12, 0.7, 0.55 if i % 4 == 0 else 0.38), i * 0.25, 0.34, -0.25, 0.3)
        # the line: a press on every beat, a ratchet between
        if i % 2 == 0:
            mix.add(kick(0.7, 90, 48, 16), i * 0.25, 0.3)
            if i % 4 == 2:
                clang = bell(62, 0.3, 0.4, ((3.1, 1, 16), (5.7, 0.6, 22), (8.2, 0.4, 30))) + snare(rng, 0.3, 40)[: int(0.5 * SR)]
                mix.add(clang, i * 0.25, 0.28, 0.35, 0.4)
        mix.add(hat(rng, 0.16 + 0.1 * (i % 2)), i * 0.25, 0.4, 0.5)
    for bar, (root, ch) in enumerate((('D', (50, 57, 65)), ('C', (48, 55, 64)), ('Bb', (46, 53, 62)))):
        mix.add(pad(ch, 3.6, 0.5, 1100, 0.5, 0.6), bar * 4, 0.42, 0, 0.4)
        mix.add(bass(ch[0] - 12, 3.4, 0.8), bar * 4, 0.2)
    crackle(mix, 1.2, 0.005)
    return mix.render(reverb=1.8, lowpass=6500, wow=1.5, drive=1.2)


@bed('horse')
def _horse():
    mix = Mix(19); rng = mix.rng
    P = 22 / 24.0   # one stride of the picture: 11 photographs, two frames each
    for st in range(13):
        t0 = st * P
        for dt, v, f in ((0.0, 0.6, 700), (0.17, 0.45, 820), (0.31, 0.7, 640)):
            mix.add(woodblock(rng, v, f * rng.uniform(0.96, 1.04)), t0 + dt + rng.uniform(-0.004, 0.004), 0.42, -0.2 + 0.05 * (st % 2), 0.2)
    chords = ['Am', 'Am', 'F', 'F', 'G', 'Am', 'Am']
    for bar in range(7):
        root, v = CH[chords[bar]]
        last = bar == 6
        t0 = bar * 2 * P
        for k in range(8 if not last else 0):
            note = (v + tuple(x + 12 for x in v))[(k * 2) % 6]
            mix.add(pluck(note + 12, 0.9, 0.5, 0.994, bar * 8 + k), t0 + k * P / 4, 0.36, 0.3, 0.3)
        mix.add(bass(root, 1.6 if not last else 1.0, 0.8), t0, 0.17)
        if last:
            strum(mix, lambda m, d, vel: pluck(m, 1.2, vel, 0.997), [x + 12 for x in v], t0, 1, 0.6, 0.2, 0.4, spread=0.03, gain=0.4)
    crackle(mix, 1.4, 0.005)
    return mix.render(reverb=1.2, lowpass=6500, wow=1.6, drive=1.2)


@bed('train')
def _train():
    mix = Mix(20); rng = mix.rng
    t = np.arange(N) / SR
    # chuffs: four to the beat at 120, accented in fours; louder as the train passes the camera (every 6 s)
    near = 0.55 + 0.45 * np.cos(2 * np.pi * (t - 1.5) / 6.0)
    ch = np.zeros(N)
    for i in range(int(11.6 / 0.125)):
        n = int(0.11 * SR)
        e = np.exp(-tt(0.11) * (26 if i % 4 else 16)) * np.minimum(1, tt(0.11) / 0.006)
        seg = filt(noise(n, rng), 'bandpass', (350, 2600) if i % 4 else (250, 2000)) * e * (1.0 if i % 4 == 0 else 0.5)
        a = int(i * 0.125 * SR)
        ch[a:a + n] += seg[: N - a]
    mix.add(ch * near * 0.5, 0, 1.0, 0.0, 0.15)
    # wheels on the rail joints
    for i in range(46):
        if i % 4 in (0, 1):
            mix.add(rim(rng, 0.3, 2400), i * 0.25 + (0.06 if i % 4 == 1 else 0), 0.3, 0.3, 0.2)
    # whistle at the top of each lap
    for t0 in (0.3, 6.3):
        tw = tt(0.7)
        v = 1 + 0.004 * np.sin(2 * np.pi * 5.5 * tw)
        wsl = sum(np.sin(2 * np.pi * f * np.cumsum(v) / SR) for f in (880, 1109, 1319)) * np.minimum(1, tw / 0.05) * np.clip((0.7 - tw) / 0.12, 0, 1)
        wsl += filt(noise(len(tw), rng), 'bandpass', (800, 3000)) * 0.6 * np.minimum(1, tw / 0.05) * np.clip((0.7 - tw) / 0.12, 0, 1)
        mix.add(wsl * 0.06, t0, 1.0, -0.2, 0.5)
        mix.add(wsl * 0.045, t0 + 0.85, 1.0, -0.2, 0.5)
    m = [(4, 72), (5, 76), (6, 79), (7, 76), (8, 81), (9, 79), (10, 76, 0.35), (12, 72), (13, 76), (14, 79), (15, 84), (16, 83), (17, 79), (18, 76, 0.35),
         (20, 77), (21, 76), (22, 74, 0.5)]
    for b, mm, v in mel(m, 0.5):
        mix.add(glock(mm, 1.4, v), b * 0.5, 0.3, 0.1, 0.4)
    for bar, c in enumerate(['C', 'C', 'F', 'C', 'G', 'C']):
        root, v = CH[c]
        mix.add(bass(root, 0.9, 0.7), bar * 2.0, 0.2); mix.add(bass(root + 7 if root < 40 else root - 5, 0.9, 0.6), bar * 2.0 + 1.0, 0.18)
    return mix.render(reverb=1.6, lowpass=7500, wow=1.0, drive=1.1)


@bed('chair')
def _chair():
    return lofi(['Ebmaj7', 'Abmaj7', 'Fm9'], 60, 21, keys='ep', drums='half', lowpass=6000,
                melody=mel([(1.5, 74), (2.5, 79, 0.35), (5.5, 72), (6.5, 75, 0.35), (9.5, 79), (10, 75), (10.5, 72, 0.4)], 0.4))


@bed('rover')
def _rover():
    return lofi(['Am9', 'D9', 'Am9', 'D9', 'Fmaj7', 'Em7'], 120, 22, keys='ep', drums='boombap', swing=0.54, lowpass=6800)


@bed('ratings')
def _ratings():
    return lofi(['Dm9', 'G13', 'Cmaj9', 'A7b13'], 80, 23)


@bed('twelve')
def _twelve():
    mix_bed = lofi(['Fm9', 'Bb13', 'Ebmaj7', 'Abmaj7'], 80, 24, crackle_amt=0.8)
    # a soft tick on every second, so the count is audible
    mix = Mix(25)
    for s in range(12):
        mix.add(rim(mix.rng, 0.5 if s % 4 else 0.8, 2100), float(s), 0.35, 0.3, 0.2)
    return mix_bed + mix.render(reverb=0.8, lowpass=8000, drive=0.8, fade_out=0.05) * 0.5


@bed('clock')
def _clock():
    return lofi(['Gm9', 'C9', 'Fmaj7', 'Dm9'], 80, 26, keys='ep', swing=0.6)


@bed('mail')
def _mail():
    return lofi(['Bbmaj9', 'G7b9', 'Cm9', 'F13'], 80, 27, keys='piano', lowpass=6000, key_gain=1.0)


def write_wav(path, x):
    x = np.clip(x, -1, 1)
    with wave.open(path, 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((x * 32767).astype('<i2').tobytes())


if __name__ == '__main__':
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    for name in (sys.argv[2:] or BEDS):
        x = BEDS[name]()
        assert x.shape == (N, 2), x.shape
        write_wav(os.path.join(out, name + '.wav'), x)
        rms = 20 * math.log10(np.sqrt((x ** 2).mean()) + 1e-9)
        print('%-10s peak %.2f  rms %.1f dB' % (name, np.abs(x).max(), rms))
