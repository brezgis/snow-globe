#!/usr/bin/env python3
"""Build the snow-globe bumps: bumps/<id>.mp4, bumps/posters/<id>.jpg, bumps/manifest.js.

  python3 bumps/src/build.py            # build everything that has its inputs
  python3 bumps/src/build.py sneeze     # one bump
  python3 bumps/src/build.py --check    # verify durations/sizes of what is in bumps/
  python3 bumps/src/build.py --manifest # only rewrite bumps/manifest.js

Inputs live OUTSIDE the repo, under $SG_BUMP_WORK
(default /mnt/ssd240gb/anna/snow-globe-bumps):

  footage/<key>/source.*   downloaded by fetch_sources.py
  renders/<id>/0001.jpg... rendered by scenes/<id>.py (see render_all.sh)
  fonts/                   Inter + Space Mono (see fetch_fonts.sh)
  work/                    scratch: audio beds, text cards, intermediates

Every bump is EXACTLY 12.000 s: 288 frames at 24 fps, 1280x720, H.264 High,
yuv420p, +faststart, AAC. app.js (BUMP_DURATION) and tv-guide.py assume 12.
"""
import json, math, os, re, subprocess, sys
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
OUT = os.path.join(REPO, 'bumps')
WORK = os.environ.get('SG_BUMP_WORK', '/mnt/ssd240gb/anna/snow-globe-bumps')
W, H, FPS, DUR = 1280, 720, 24, 12
FRAMES = FPS * DUR
TARGET_LUFS = -19.0
MAX_BYTES = 1_500_000

FONTS = {
    'semi': 'fonts/inter/Inter-SemiBold.ttf',
    'medium': 'fonts/inter/Inter-Medium.ttf',
    'regular': 'fonts/inter/Inter-Regular.ttf',
    'bold': 'fonts/inter/Inter-Bold.ttf',
    'mono': 'fonts/SpaceMono-Bold.ttf',
    'monoreg': 'fonts/SpaceMono-Regular.ttf',
}


def font(name, size):
    return ImageFont.truetype(os.path.join(WORK, FONTS[name]), size)


def run(cmd, **kw):
    r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, **kw)
    if r.returncode:
        sys.stderr.write(' '.join(map(str, cmd)) + '\n' + r.stderr[-3000:] + '\n')
        raise SystemExit(1)
    return r


def ffmpeg(*args):
    return run(['nice', '-n', '15', 'ffmpeg', '-v', 'error', '-y', *map(str, args)])


def wdir(bid):
    d = os.path.join(WORK, 'work', bid)
    os.makedirs(d, exist_ok=True)
    return d


def src(key):
    d = os.path.join(WORK, 'footage', key)
    f = [x for x in sorted(os.listdir(d)) if x.startswith('source.')]
    return os.path.join(d, f[0])


# ── text cards ──────────────────────────────────────────
def wrap(draw, text, fnt, maxw):
    lines = []
    for para in text.split('\n'):
        cur = ''
        for word in para.split(' '):
            trial = (cur + ' ' + word).strip()
            if draw.textlength(trial, font=fnt) <= maxw or not cur:
                cur = trial
            else:
                lines.append(cur); cur = word
        lines.append(cur)
    return lines


def tracked(draw, xy, text, fnt, fill, tracking):
    x, y = xy
    for ch in text:
        draw.text((x, y), ch, font=fnt, fill=fill)
        x += draw.textlength(ch, font=fnt) + tracking


def tracked_width(draw, text, fnt, tracking):
    return sum(draw.textlength(ch, font=fnt) + tracking for ch in text) - tracking


def card_png(path, text, y=0.5, size=46, maxw=0.66, face='semi', color=(255, 255, 255, 255), mark=False,
             shadow=0.0, x=0.5, align='center', leading=1.34, small=None):
    """One full-frame transparent PNG. y is the vertical centre of the text
    block as a fraction of the frame. `small` is an optional second, quieter
    line under the block. `mark` adds the station name under it."""
    img = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    fnt = font(face, size)
    lines = wrap(d, text, fnt, W * maxw)
    lh = size * leading
    block_h = lh * len(lines)
    top = H * y - block_h / 2
    for i, line in enumerate(lines):
        lw = d.textlength(line, font=fnt)
        lx = W * x - lw / 2 if align == 'center' else W * x
        d.text((lx, top + i * lh + (lh - size) / 2 - size * 0.08), line, font=fnt, fill=color)
    yy = top + block_h
    if small:
        sf = font('regular', int(size * 0.56))
        for j, sl in enumerate(wrap(d, small, sf, W * maxw)):
            lw = d.textlength(sl, font=sf)
            lx = W * x - lw / 2 if align == 'center' else W * x
            d.text((lx, yy + 14 + j * size * 0.56 * 1.4), sl, font=sf, fill=(255, 255, 255, 170))
            yy += size * 0.56 * 1.4
        yy += 14
    if mark:
        mf = font('mono', 19)
        t = 'snow-globe'
        tw = tracked_width(d, t, mf, 3.4)
        lx = W * x - tw / 2 if align == 'center' else W * x
        tracked(d, (lx, yy + 26), t, mf, (255, 255, 255, 175), 3.4)
    if shadow:
        a = img.split()[3]
        sh = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        blur = a.filter(ImageFilter.GaussianBlur(14)).point(lambda v: min(255, int(v * 2.6 * shadow)))
        tight = a.filter(ImageFilter.GaussianBlur(3)).point(lambda v: min(255, int(v * 1.6 * shadow)))
        sh.putalpha(Image.eval(Image.merge('L', [blur]), lambda v: v))
        sh2 = Image.new('RGBA', (W, H), (0, 0, 0, 0)); sh2.putalpha(tight)
        img = Image.alpha_composite(Image.alpha_composite(sh, sh2), img)
    img.save(path)
    return path


# Default timings. Three cards sit on 4-second phrases, four on 3-second bars.
T3 = [(0.5, 3.8), (4.0, 7.8), (8.0, 11.45)]
T4 = [(0.4, 2.85), (3.0, 5.85), (6.0, 8.85), (9.0, 11.45)]


def cards(lines, times=None, **kw):
    """lines: strings or (string, overrides). The last card carries the mark."""
    times = times or (T3 if len(lines) == 3 else T4)
    out = []
    for i, (ln, (t0, t1)) in enumerate(zip(lines, times)):
        o = dict(kw)
        if isinstance(ln, tuple): ln, extra = ln; o.update(extra)
        o.setdefault('mark', i == len(lines) - 1)
        out.append(dict(text=ln, t0=t0, t1=t1, **o))
    return out


# ── backgrounds ─────────────────────────────────────────
ENC_MID = ['-c:v', 'libx264', '-preset', 'veryfast', '-crf', '12', '-pix_fmt', 'yuv420p', '-an']
SQUARE = 'scale=iw*sar:ih,setsar=1'
FILL = 'scale=%d:%d:force_original_aspect_ratio=increase,crop=%d:%d' % (W, H, W, H)


def black(bid):
    out = os.path.join(wdir(bid), 'bg.mp4')
    ffmpeg('-f', 'lavfi', '-i', 'color=c=black:s=%dx%d:r=%d:d=%d' % (W, H, FPS, DUR), '-frames:v', FRAMES, *ENC_MID, out)
    return out


def frames(bid, name=None, vf=None):
    """A Blender render: renders/<name>/0001.jpg ... 0288.jpg."""
    d = os.path.join(WORK, 'renders', name or bid)
    n = len([f for f in os.listdir(d) if re.match(r'\d{4}\.jpg$', f)]) if os.path.isdir(d) else 0
    if n < FRAMES:
        raise FileNotFoundError('render %s has %d/%d frames' % (name or bid, n, FRAMES))
    out = os.path.join(wdir(bid), 'bg.mp4')
    ffmpeg('-framerate', FPS, '-start_number', 1, '-i', os.path.join(d, '%04d.jpg'), '-frames:v', FRAMES,
           '-vf', vf or 'null', *ENC_MID, out)
    return out


def footage(bid, key, ss, length=DUR, speed=1.0, pre='', grade='', box=None, loop=1, fill=FILL, name='bg'):
    """Cut `length` seconds of output from a source clip.

    ss      where to start in the source, seconds
    speed   <1 slows down (source seconds used = length * speed)
    pre     filters applied to the source before anything else (crops of burnt-in logos etc.)
    grade   filters applied after scaling
    box     (w, h, x, y): show the clip in a window on black instead of full frame
    loop    repeat the cut this many times to fill `length`
    """
    out = os.path.join(wdir(bid), name + '.mp4')
    one = length / loop
    chain = [SQUARE]
    if pre: chain.append(pre)
    chain.append('setpts=(PTS-STARTPTS)/%g' % speed)
    chain.append(('framerate=fps=%d' if speed < 1 else 'fps=%d') % FPS)   # blend frames when slowed
    if box:
        bw, bh, bx, by = box
        chain.append('scale=%d:%d:force_original_aspect_ratio=increase,crop=%d:%d' % (bw, bh, bw, bh))
    else:
        chain.append(fill)
    if grade: chain.append(grade)
    chain.append('trim=end_frame=%d,setpts=PTS-STARTPTS' % round(one * FPS))
    if loop > 1:
        chain.append('loop=loop=%d:size=%d:start=0' % (loop - 1, round(one * FPS)))
    if box:
        chain.append('pad=%d:%d:%d:%d:black' % (W, H, bx, by))
    ffmpeg('-ss', ss, '-t', one * speed + 1.0, '-i', src(key), '-vf', ','.join(chain),
           '-frames:v', round(length * FPS), *ENC_MID, out)
    return out


def concat(bid, parts):
    out = os.path.join(wdir(bid), 'bg.mp4')
    args = []
    for p in parts: args += ['-i', p]
    ffmpeg(*args, '-filter_complex', ''.join('[%d:v]' % i for i in range(len(parts))) + 'concat=n=%d:v=1:a=0' % len(parts),
           '-frames:v', FRAMES, *ENC_MID, out)
    return out


VIGNETTE = 'vignette=PI/4.5'
# a gentle common grade for archive footage: lift nothing, pull the whites down so type sits on top
def dim(amount=0.78, contrast=1.05, sat=1.0):
    return "eq=contrast=%g:saturation=%g,colorlevels=romax=%g:gomax=%g:bomax=%g" % (contrast, sat, amount, amount, amount)


# ── the bumps ───────────────────────────────────────────
# id, title, desc (shown in the reel), how the picture is made, the copy, and the bed (music.py).
# `blocks` limits a bump to some dayparts. `weight` is its share of the rotation.
BUMPS = []
def bump(**kw):
    kw.setdefault('audio', kw['id']); kw.setdefault('weight', 1); kw.setdefault('poster', 9.5)
    kw.setdefault('fade_in', 0.4); kw.setdefault('fade_out', 0.45)
    BUMPS.append(kw)


exec(open(os.path.join(HERE, 'bumps_def.py')).read())


# ── compose + encode ────────────────────────────────────
def loudness_gain(wav):
    r = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-i', wav, '-af', 'ebur128=peak=true', '-f', 'null', '-'],
                       stderr=subprocess.PIPE, text=True).stderr
    i = float(re.findall(r'I:\s+(-?[\d.]+) LUFS', r)[-1])
    return TARGET_LUFS - i


def build(b):
    bid = b['id']
    d = wdir(bid)
    bg = b['bg'](bid)
    wav = os.path.join(WORK, 'work', 'audio', b['audio'] + '.wav')
    run(['nice', 'python3', os.path.join(HERE, 'music.py'), os.path.dirname(wav), b['audio']])
    gain = loudness_gain(wav)
    inputs = ['-i', bg]
    fc = ['[0:v]format=yuv420p,setsar=1[v0]']
    last = 'v0'
    for i, c in enumerate(b.get('cards', [])):
        c = dict(c)
        t0, t1 = c.pop('t0'), c.pop('t1'); f = c.pop('fade', 0.14)
        png = card_png(os.path.join(d, 'card%d.png' % i), c.pop('text'), **c)
        inputs += ['-loop', '1', '-framerate', FPS, '-t', DUR, '-i', png]
        fc.append('[%d:v]format=rgba,fade=t=in:st=%g:d=%g:alpha=1,fade=t=out:st=%g:d=%g:alpha=1[c%d]' % (i + 1, t0, f, t1 - f, f, i))
        fc.append('[%s][c%d]overlay=0:0:format=auto[v%d]' % (last, i, i + 1))
        last = 'v%d' % (i + 1)
    fc.append('[%s]fade=t=in:st=0:d=%g,fade=t=out:st=%g:d=%g,format=yuv420p[vout]' % (
        last, b['fade_in'], DUR - b['fade_out'] - 2 / FPS, b['fade_out']))
    ai = len(inputs) // 2 if not b.get('cards') else None
    inputs += ['-i', wav]
    aidx = sum(1 for x in inputs if x == '-i') - 1
    fc.append('[%d:a]volume=%.2fdB,alimiter=limit=0.84:level=disabled,atrim=0:11.94,asetpts=PTS-STARTPTS[aout]' % (aidx, gain))
    out = os.path.join(OUT, bid + '.mp4')
    os.makedirs(os.path.join(OUT, 'posters'), exist_ok=True)
    crf = b.get('crf', 23)
    while True:
        ffmpeg(*inputs, '-filter_complex', ';'.join(fc), '-map', '[vout]', '-map', '[aout]',
               '-frames:v', FRAMES, '-r', FPS,
               '-c:v', 'libx264', '-preset', 'slow', '-crf', crf, '-maxrate', '1400k', '-bufsize', '2800k',
               '-profile:v', 'high', '-level', '3.1', '-pix_fmt', 'yuv420p', '-g', FPS * 2, '-keyint_min', FPS,
               '-c:a', 'aac', '-b:a', '112k', '-ar', '48000', '-ac', '2',
               '-movflags', '+faststart', '-map_metadata', '-1', out)
        size = os.path.getsize(out)
        if size <= MAX_BYTES or crf >= 34: break
        crf += 2
    ffmpeg('-ss', b['poster'], '-i', out, '-frames:v', 1, '-vf', 'scale=480:270', '-q:v', 6, os.path.join(OUT, 'posters', bid + '.jpg'))
    dur = probe(out)
    print('%-10s %7.1f KB  crf %d  %s  gain %+.1f dB' % (bid, size / 1000, crf, dur, gain))
    return out


def probe(path):
    r = run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration:stream=codec_name,nb_frames,duration,width,height,pix_fmt',
             '-of', 'json', path])
    j = json.loads(r.stdout)
    v = next(s for s in j['streams'] if s['codec_name'] == 'h264')
    a = next((s for s in j['streams'] if s['codec_name'] == 'aac'), None)
    ok = (abs(float(j['format']['duration']) - DUR) < 1e-6 and int(v['nb_frames']) == FRAMES
          and v['pix_fmt'] == 'yuv420p' and (v['width'], v['height']) == (W, H) and a is not None
          and float(a['duration']) <= DUR)
    return 'dur %s v %s/%sf a %s %s' % (j['format']['duration'], v['duration'], v['nb_frames'], a and a['duration'], 'OK' if ok else 'MISMATCH')


def manifest():
    items = []
    for b in BUMPS:
        p = os.path.join(OUT, b['id'] + '.mp4')
        if not os.path.exists(p) or b.get('hold'): continue
        it = {'id': b['id'], 'title': b['title'], 'desc': b['desc'], 'src': 'bumps/%s.mp4' % b['id'],
              'poster': 'bumps/posters/%s.jpg' % b['id'], 'weight': b['weight']}
        if b.get('blocks'): it['blocks'] = b['blocks']
        items.append(it)
    js = ('// Generated by bumps/src/build.py. Do not edit by hand.\n'
          '// Every file listed here is exactly %d seconds long (app.js BUMP_DURATION, tv-guide.py).\n'
          'window.SG_VIDEO_BUMPS = %s;\n' % (DUR, json.dumps(items, indent=2, ensure_ascii=False)))
    open(os.path.join(OUT, 'manifest.js'), 'w').write(js)
    print('manifest: %d bumps' % len(items))


def check():
    total = 0; bad = 0
    for b in BUMPS:
        p = os.path.join(OUT, b['id'] + '.mp4')
        if not os.path.exists(p): print('%-10s MISSING' % b['id']); continue
        s = os.path.getsize(p); total += s
        r = probe(p)
        bad += 'MISMATCH' in r or s > MAX_BYTES
        print('%-10s %7.1f KB  %s' % (b['id'], s / 1000, r))
    print('total %.2f MB, %d problem(s)' % (total / 1e6, bad))
    return bad


if __name__ == '__main__':
    args = sys.argv[1:]
    if '--check' in args:
        sys.exit(1 if check() else 0)
    if '--manifest' not in args:
        want = [a for a in args if not a.startswith('--')]
        for b in BUMPS:
            if want and b['id'] not in want: continue
            try:
                build(b)
            except FileNotFoundError as e:
                print('%-10s skipped: %s' % (b['id'], e))
    manifest()
