#!/usr/bin/env python3
"""Download the source footage for the snow-globe bumps.

Everything lands OUTSIDE the repo (default: /mnt/ssd240gb/anna/snow-globe-bumps/footage,
override with $SG_BUMP_WORK), one fresh directory per clip, with a meta.json
recording the source page and the license the API reported at download time.
Only public-domain / CC0 / CC BY material is listed here. See ../CREDITS.md.

  python3 bumps/src/fetch_sources.py            # everything
  python3 bumps/src/fetch_sources.py sneeze     # one clip
"""
import json, os, subprocess, sys, urllib.parse, urllib.request

WORK = os.environ.get('SG_BUMP_WORK', '/mnt/ssd240gb/anna/snow-globe-bumps')
UA = 'bump-builder/1.0 (static site build script)'

# key: (kind, name, [optional ffmpeg segment as (start_seconds, length_seconds)])
#   commons  -> a File: title on Wikimedia Commons (original file)
#   commons720 -> same, but the 720p transcode (for very large originals)
#   archive  -> (identifier, filename) on archive.org
SOURCES = {
    'sneeze':  ('commons', 'File:Edison kinetoscopic record of a sneeze, January 7, 1894.webm'),
    'market':  ('commons', 'File:A Trip down market street (1906).webm'),
    'jelly':   ('commons', 'File:Jellyfish- 2016 Deepwater Exploration of the Marianas.webm'),
    'orbit':   ('commons', 'File:ISS073-E-1225342-1227437-20251112-Night - 2025-11-12 ISS073 2096 Night.webm'),
    'lava2':   ('commons', 'File:Halemaʻumaʻu lava lake USGS multimediaFile-1585.webm'),
    'hands':   ('commons720', 'File:Master Hands.webm'),
    'horse':   ('commons', 'File:Horse in Motion - Sallie Gardner (animation).webm'),
    'snow':    ('commons', 'File:Snow under LED street light in Tuntorp, Brastad.webm'),
    'bert':    ('archive', ('DuckandC1951', None)),
    'remote':  ('archive', ('Televisi1961', None)),
}

def get(url):
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    return urllib.request.urlopen(req, timeout=60).read()

def commons_info(title):
    q = urllib.parse.urlencode({
        'action': 'query', 'format': 'json', 'titles': title, 'prop': 'videoinfo',
        'viprop': 'url|size|extmetadata|derivatives'})
    d = json.loads(get('https://commons.wikimedia.org/w/api.php?' + q))
    page = next(iter(d['query']['pages'].values()))
    vi = page['videoinfo'][0]
    em = vi['extmetadata']
    strip = lambda k: (em.get(k, {}).get('value') or '')
    return vi, {
        'title': title,
        'page': vi['descriptionurl'],
        'license': strip('LicenseShortName'),
        'license_url': strip('LicenseUrl'),
        'artist_html': strip('Artist'),
        'credit_html': strip('Credit'),
    }

def curl(url, dest):
    subprocess.run(['curl', '-sS', '-L', '--fail', '-A', UA, '-o', dest, url], check=True)

def fetch(key):
    kind, spec = SOURCES[key]
    d = os.path.join(WORK, 'footage', key)
    if os.path.isdir(d) and any(f != 'meta.json' for f in os.listdir(d)):
        print('have', key); return
    os.makedirs(d, exist_ok=True)
    if kind.startswith('commons'):
        vi, meta = commons_info(spec)
        url = vi['url']
        if kind == 'commons720':
            ders = [x for x in vi.get('derivatives', []) if str(x.get('transcodekey', '')).startswith('720p')]
            if ders: url = ders[0]['src']
        meta['download'] = url
        ext = os.path.splitext(urllib.parse.urlparse(url).path)[1] or '.webm'
        curl(url, os.path.join(d, 'source' + ext))
    else:
        ident, fname = spec
        md = json.loads(get('https://archive.org/metadata/' + ident))
        m = md['metadata']
        meta = {'title': m.get('title'), 'page': 'https://archive.org/details/' + ident,
                'license': m.get('licenseurl'), 'license_url': m.get('licenseurl'),
                'artist_html': m.get('creator') or m.get('sponsor') or '', 'credit_html': m.get('collection')}
        if not fname:
            vids = [f for f in md['files'] if f['name'].lower().endswith(('.mpeg', '.mpg', '.mp4'))]
            vids.sort(key=lambda f: (f.get('source') != 'original', -int(f.get('size', 0))))
            fname = vids[0]['name']
        url = 'https://archive.org/download/%s/%s' % (ident, urllib.parse.quote(fname))
        meta['download'] = url
        curl(url, os.path.join(d, 'source' + os.path.splitext(fname)[1]))
    json.dump(meta, open(os.path.join(d, 'meta.json'), 'w'), indent=1, ensure_ascii=False)
    print('got', key, meta['license'], meta['download'])

if __name__ == '__main__':
    for k in (sys.argv[1:] or SOURCES):
        try: fetch(k)
        except Exception as e: print('FAILED', k, e)
