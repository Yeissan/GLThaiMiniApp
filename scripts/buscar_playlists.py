#!/usr/bin/env python3
"""Busca en YouTube la playlist oficial de cada serie y la guarda en data/playlists.json.

- Si la serie es de un canal conocido (GMMTV, one31, Ch3) busca dentro de ese canal.
- Si salió en YouTube sin canal conocido, busca el capítulo 1 y solo acepta canales
  verificados (así se evitan las copias subidas por fans), y luego busca la playlist
  dentro de ese canal.
- Solo busca las series que todavía no tienen resultado (o cuyo intento falló hace
  más de 7 días), para no hacerlo cada vez.
"""
from pathlib import Path
import json
import re
import sys
import time
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / 'data' / 'catalog.json'
OUT = ROOT / 'data' / 'playlists.json'
CHANNELS = {
    'YouTube GMMTV': '@gmmtv',
    'YouTube one31': '@one31official',
    'YouTube Ch3Thailand': '@ch3thailand',
}
BAD = ('behind', 'highlight', 'teaser', 'trailer', 'reaction', 'bts', 'ost', 'making', 'shorts',
       'special', 'interview', 'cut', 'fancon', 'fan meeting', 'live', 'react', 'promo', 'spoiler',
       'fin |', 'clip', 'full cut', 'ซีนเด็ด', 'ตัวอย่าง', 'เบื้องหลัง', 'ไฮไลท์', 'คลิป')
# Canales verificados que suben series de otros (no son oficiales)
BAD_OWNERS = ('kisszeries', 'huace', 'docvee', 'dzhaber')
RETRY_DAYS = 7


def get(url):
    req = urllib.request.Request(url, headers={
        'Accept-Language': 'en-US,en;q=0.9',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36',
        'Cookie': 'CONSENT=YES+1; SOCS=CAI'})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode('utf-8', 'replace')


def initial(html):
    m = re.search(r'ytInitialData\s*=\s*(\{.+?\});\s*</script>', html, re.S)
    return json.loads(m.group(1)) if m else {}


def text(x):
    if isinstance(x, dict):
        if 'simpleText' in x:
            return x['simpleText']
        if 'runs' in x:
            return ''.join(r.get('text', '') for r in x['runs'])
        if isinstance(x.get('content'), str):
            return x['content']
    return ''


def walk(o, fn):
    if isinstance(o, dict):
        fn(o)
        for v in o.values():
            walk(v, fn)
    elif isinstance(o, list):
        for v in o:
            walk(v, fn)


def find_playlists(data):
    out = {}

    def fn(o):
        if 'playlistRenderer' in o:
            p = o['playlistRenderer']
            out.setdefault(p.get('playlistId'), (text(p.get('title')), int(p.get('videoCount') or 0)))
        if 'lockupViewModel' in o:
            l = o['lockupViewModel']
            cid = l.get('contentId') or ''
            if 'PLAYLIST' in (l.get('contentType') or '') or cid.startswith('PL'):
                md = ((l.get('metadata') or {}).get('lockupMetadataViewModel')) or {}
                n = re.findall(r'(\d+) (?:videos|episodes)', json.dumps(l))
                out.setdefault(cid, (text(md.get('title')), int(n[0]) if n else 0))
    walk(data, fn)
    return [(k, t, n) for k, (t, n) in out.items() if k]


def find_verified_channel(data, names):
    """Primer vídeo de un canal verificado cuyo título nombre la serie."""
    found = []

    def fn(o):
        v = o.get('videoRenderer')
        if not v:
            return
        title = text(v.get('title'))
        badges = json.dumps(v.get('ownerBadges') or [])
        if 'VERIFIED' not in badges and 'ARTIST' not in badges:
            return
        if not any(n and n in norm(title) for n in names):
            return
        run = ((v.get('ownerText') or {}).get('runs') or [{}])[0]
        if any(b in (run.get('text') or '').lower() for b in BAD_OWNERS):
            return
        url = ((run.get('navigationEndpoint') or {}).get('browseEndpoint') or {}).get('canonicalBaseUrl')
        if url:
            found.append((url, run.get('text', '')))
    walk(data, fn)
    return found[0] if found else None


def norm(t):
    return re.sub(r'[^a-z0-9฀-๿]+', '', (t or '').lower())


def names_of(s):
    out = []
    for t in (s.get('title_en'), s.get('title'), s.get('originaltitle')):
        n = norm(re.sub(r'(?i)\bthe series\b', '', t or ''))
        if len(n) >= 3 and n not in out:
            out.append(n)
        thai = ''.join(re.findall(r'[฀-๿]+', t or ''))
        if len(thai) >= 3 and thai not in out:
            out.append(thai)
    return out


def best(playlists, names):
    good = []
    for pid, title, count in playlists:
        nt = norm(title)
        if not any(n in nt for n in names):
            continue
        low = title.lower()
        if any(b in low for b in BAD):
            continue
        score = count
        if re.search(r'(?i)\b(ep|full|eng ?sub|episode|ตอน)', title):
            score += 1000
        good.append((score, pid, title))
    good.sort(reverse=True)
    return good[0] if good else None


def search_channel(handle, s, names):
    for t in dict.fromkeys([s.get('title_en'), s['title'], s.get('originaltitle')]):
        if not t:
            continue
        url = f'https://www.youtube.com{handle if handle.startswith("/") else "/" + handle}/search?query={urllib.parse.quote(t)}'
        hit = best(find_playlists(initial(get(url))), names)
        time.sleep(1)
        if hit:
            return hit
    return None


def main():
    catalog = json.loads(CATALOG.read_text(encoding='utf-8'))['series']
    cache = json.loads(OUT.read_text(encoding='utf-8')) if OUT.exists() else {}
    now = int(time.time())
    done = 0
    for s in catalog:
        of = s.get('oficial') or {}
        name = of.get('name', '')
        if name not in CHANNELS and name != 'Buscar en YouTube':
            continue
        old = cache.get(s['id'])
        if old and any(b in (old.get('name') or '').lower() for b in BAD_OWNERS):
            old = None
        if old and (old.get('url') or now - old.get('checked', 0) < RETRY_DAYS * 86400):
            continue
        names = names_of(s)
        try:
            entry = {'checked': now}
            if name in CHANNELS:
                handle, chan = CHANNELS[name], name
            else:
                t = s.get('title_en') or s['title']
                data = initial(get('https://www.youtube.com/results?search_query='
                                   + urllib.parse.quote(f'{t} EP1')))
                time.sleep(1)
                ch = find_verified_channel(data, names)
                handle, chan = (ch[0], 'YouTube ' + ch[1]) if ch else (None, None)
            if handle:
                hit = search_channel(handle, s, names)
                if hit:
                    entry.update(url=f'https://www.youtube.com/playlist?list={hit[1]}', name=chan,
                                 playlist=hit[2])
                    print(f' + {s["title"]}: {chan} · {hit[2]}')
                elif name == 'Buscar en YouTube':
                    # Canal oficial encontrado pero sin playlist: al menos su buscador
                    entry.update(url=f'https://www.youtube.com{handle}/search?query='
                                     + urllib.parse.quote(s.get('title_en') or s['title']), name=chan)
                    print(f' ~ {s["title"]}: solo canal {chan}')
            if not entry.get('url'):
                print(f' - {s["title"]}: sin playlist oficial')
            cache[s['id']] = entry
            done += 1
        except Exception as e:
            print(f' ! {s["title"]}: {e}')
    OUT.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'Series revisadas: {done}')


if __name__ == '__main__':
    sys.exit(main())
