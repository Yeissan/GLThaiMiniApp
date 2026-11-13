#!/usr/bin/env python3
"""Genera data/catalog.json juntando tres fuentes:

1. series/<NOMBRE>/   carpetas con tvshow.nfo, imágenes, serie.json y episodes.json
2. pc/series.json     lista exportada desde el PC (programa "Crear catalogo") + pc/img/
3. data/telegram.json temas y capítulos detectados en el grupo de Telegram

Las series se unen por su identificador (nombre sin tailandés, en minúsculas).
"""
from pathlib import Path
import json
import re
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SERIES = ROOT / 'series'
PC = ROOT / 'pc' / 'series.json'
TG = ROOT / 'data' / 'telegram.json'
OUT = ROOT / 'data' / 'catalog.json'
OFICIAL = ROOT / 'data' / 'oficial.json'   # enlaces exactos puestos a mano (tienen prioridad)
PLAYLISTS = ROOT / 'data' / 'playlists.json'   # playlists oficiales encontradas en YouTube

THAI = re.compile(r'[฀-๿]+')
GENRES = {
    'comedy': 'Comedia', 'romance': 'Romance', 'drama': 'Drama', 'mystery': 'Misterio',
    'fantasy': 'Fantasía', 'action': 'Acción', 'thriller': 'Suspense', 'family': 'Familia',
    'crime': 'Crimen', 'sci-fi & fantasy': 'Fantasía', 'action & adventure': 'Acción',
    'horror': 'Terror', 'music': 'Música', 'documentary': 'Documental', 'war': 'Bélica',
    'history': 'Historia', 'animation': 'Animación', 'kids': 'Infantil', 'reality': 'Reality',
}
STATUS = {'continuing': 'En emisión', 'returning series': 'En emisión', 'ended': 'Finalizada',
          'canceled': 'Cancelada', 'cancelled': 'Cancelada'}


def no_thai(t):
    """Quita el tailandés. Si no queda nada legible, devuelve ''."""
    t = (t or '').strip()
    if not THAI.search(t):
        return t
    t = re.sub(r'\s{2,}', ' ', THAI.sub(' ', t)).strip(' -–—:|·.,_()[]')
    return t if re.search(r'[A-Za-zÀ-ÿ]{2,}', t) else ''


def strip_year(t):
    return re.sub(r'\s*[\(\[]\d{4}[\)\]]\s*$', '', t or '').strip()


def make_id(t):
    return re.sub(r'[^a-z0-9]+', '-', (t or '').lower()).strip('-')


def load_json(path, default):
    try:
        if path.exists():
            return json.loads(path.read_text(encoding='utf-8-sig'))
    except Exception as e:
        print(f'AVISO {path}: {e}')
    return default


def rel(path):
    return path.relative_to(ROOT).as_posix()


def first_image(folder, names):
    for n in names:
        p = folder / n
        if p.exists():
            return rel(p)
    return ''


def txt(node, name):
    x = node.find(name) if node is not None else None
    return (x.text or '').strip() if x is not None and x.text else ''


def texts(node, name):
    return [(x.text or '').strip() for x in node.findall(name) if x.text] if node is not None else []


def genres_es(lst):
    out = []
    for g in lst:
        g = GENRES.get(g.strip().lower(), g.strip())
        if g and g not in out:
            out.append(g)
    if 'GL' not in out:
        out.append('GL')
    return out


def q(t):
    from urllib.parse import quote_plus
    return quote_plus(t)


def official(s, manual, pls=None):
    """Dónde verla oficialmente. Primero lo gratis, luego lo de pago."""
    if s['id'] in manual:
        return manual[s['id']]
    st = ' '.join(s.get('studios') or []).lower()
    t = s.get('title_en') or s['title']
    rules = [
        (('gmm25', 'gmm 25', 'gmmtv'), 'YouTube GMMTV', f'https://www.youtube.com/@gmmtv/search?query={q(t)}', True),
        (('one 31', 'one31', 'oned', 'one grand'), 'YouTube one31', f'https://www.youtube.com/@one31official/search?query={q(t)}', True),
        (('channel 3', '3plus', 'ch3'), 'YouTube Ch3Thailand', f'https://www.youtube.com/@ch3thailand/search?query={q(t)}', True),
        (('youtube',), 'Buscar en YouTube', f'https://www.youtube.com/results?search_query={q(t + " EP1")}', True),
        (('iqiyi',), 'iQIYI', f'https://www.iq.com/search?query={q(t)}', True),
        (('wetv',), 'WeTV', 'https://wetv.vip/', True),
        (('gagaoolala',), 'GagaOOLala', 'https://www.gagaoolala.com/', False),
        (('netflix',), 'Netflix', f'https://www.netflix.com/search?q={q(t)}', False),
    ]
    found = (pls or {}).get(s['id'], {})
    youtube = {'YouTube GMMTV', 'YouTube one31', 'YouTube Ch3Thailand', 'Buscar en YouTube'}
    backup = None
    for keys, name, url, free in rules:
        if not any(k in st for k in keys):
            continue
        if name in youtube and found:
            if found.get('url'):
                return {'name': found.get('name') or name, 'url': found['url'], 'gratis': True,
                        'playlist': bool(found.get('playlist'))}
            if name != 'Buscar en YouTube':
                backup = backup or {'name': name, 'url': url, 'gratis': free}
                continue          # ese canal no tiene la serie completa: probar la siguiente opción
        return {'name': name, 'url': url, 'gratis': free}
    return backup


def thread_of(url):
    m = re.search(r't\.me/c/\d+/(\d+)', url or '')
    return int(m.group(1)) if m else None


# ---------------------------------------------------------------- fuentes

def from_folder(folder):
    nfo = folder / 'tvshow.nfo'
    if not nfo.exists():
        return None
    root = ET.parse(nfo).getroot()
    serie = load_json(folder / 'serie.json', {})
    title = (serie.get('title_es') or no_thai(txt(root, 'title'))
             or no_thai(strip_year(folder.name)) or folder.name)
    en = serie.get('title_en') or no_thai(strip_year(folder.name))

    eps = {}
    for p in sorted(folder.rglob('*.nfo')):
        if p.name.lower() == 'tvshow.nfo':
            continue
        try:
            r = ET.parse(p).getroot()
            n = int(float(txt(r, 'episode') or 0))
            s = int(float(txt(r, 'season') or 1))
            if n:
                eps[(s, n)] = {'season': s, 'number': n,
                               'telegram_url': txt(r, 'telegram_url') or txt(r, 'telegram')}
        except Exception as e:
            print(f'AVISO capítulo {p}: {e}')
    for m in load_json(folder / 'episodes.json', []):
        key = (int(m.get('season', 1) or 1), int(m.get('number', 0) or 0))
        if key[1]:
            eps.setdefault(key, {'season': key[0], 'number': key[1]})
            if m.get('telegram_url'):
                eps[key]['telegram_url'] = m['telegram_url']

    poster = first_image(folder, ['folder.jpg', 'poster.jpg', 'folder.png', 'poster.png',
                                  'folder.webp', 'poster.webp', 'cover.jpg'])
    banner = first_image(folder, ['backdrop.jpg', 'fanart.jpg', 'banner.jpg', 'backdrop.png',
                                  'fanart.png', 'backdrop.webp', 'fanart.webp']) or poster
    return {
        'id': serie.get('id') or make_id(title),
        'title': title,
        'title_en': en,
        'originaltitle': txt(root, 'originaltitle'),
        'year': txt(root, 'year'),
        'rating': txt(root, 'rating'),
        'plot': serie.get('description') or txt(root, 'plot') or txt(root, 'outline'),
        'runtime': txt(root, 'runtime'),
        'status': txt(root, 'status'),
        'genres': texts(root, 'genre'),
        'studios': texts(root, 'studio'),
        'cast': [{'name': txt(a, 'name'), 'role': txt(a, 'role')} for a in root.findall('actor')],
        'poster': poster,
        'banner': banner,
        'topic_url': serie.get('topic_url') or serie.get('telegram_url') or '',
        'total_episodes': int(serie.get('total_episodes') or 0),
        'episodes': list(eps.values()),
    }


def from_pc(item):
    title = (item.get('title_es') or no_thai(item.get('title'))
             or no_thai(strip_year(item.get('folder'))) or item.get('folder') or '')
    eps = []
    total = 0
    for t in item.get('seasons') or []:
        for n in t.get('have') or []:
            eps.append({'season': int(t.get('n') or 1), 'number': int(n)})
        total += int(t.get('total') or 0)
    def img(p):
        return ('pc/' + p) if p and (ROOT / 'pc' / p).exists() else ''
    return {
        'id': make_id(title),
        'title': title,
        'title_en': item.get('title_en') or no_thai(strip_year(item.get('folder'))),
        'originaltitle': item.get('orig') or '',
        'year': item.get('year') or '',
        'rating': item.get('rating') or '',
        'plot': item.get('plot') or '',
        'runtime': item.get('runtime') or '',
        'status': item.get('status') or '',
        'genres': item.get('genres') or [],
        'studios': item.get('studios') or [],
        'cast': item.get('cast') or [],
        'poster': img(item.get('poster')),
        'banner': img(item.get('back')) or img(item.get('poster')),
        'topic_url': '',
        'total_episodes': total,
        'episodes': eps,
    }


def merge(a, b):
    """Completa la serie a con los datos de b sin borrar lo que ya tiene."""
    for k, v in b.items():
        if k == 'episodes':
            have = {(e['season'], e['number']): e for e in a['episodes']}
            for e in v:
                key = (e['season'], e['number'])
                if key not in have:
                    have[key] = dict(e)
                elif e.get('telegram_url') and not have[key].get('telegram_url'):
                    have[key]['telegram_url'] = e['telegram_url']
            a['episodes'] = list(have.values())
        elif k == 'total_episodes':
            a[k] = max(a.get(k) or 0, v or 0)
        elif not a.get(k) and v:
            a[k] = v
    return a


def main():
    items = {}

    def add(s):
        if not s or not s['id']:
            return
        items[s['id']] = merge(items[s['id']], s) if s['id'] in items else s

    if SERIES.exists():
        for folder in sorted(p for p in SERIES.iterdir() if p.is_dir()):
            try:
                add(from_folder(folder))
            except Exception as e:
                print(f'ERROR {folder}: {e}')

    pc = load_json(PC, {})
    for item in (pc.get('series', []) if isinstance(pc, dict) else pc):
        try:
            add(from_pc(item))
        except Exception as e:
            print(f'ERROR pc {item.get("folder")}: {e}')

    # Telegram: temas creados y capítulos detectados
    tg = load_json(TG, {}).get('series', {})
    for sid, t in tg.items():
        if sid not in items:
            continue
        s = items[sid]
        if t.get('topic_url'):
            s['topic_url'] = t['topic_url']
        merge(s, {'episodes': [
            {'season': e['season'], 'number': e['number'], 'telegram_url': e['url']}
            for e in t.get('episodes', [])]})

    manual = load_json(OFICIAL, {})
    pls = load_json(PLAYLISTS, {})
    out = []
    for s in sorted(items.values(), key=lambda x: x['title'].lower()):
        s['genres'] = genres_es(s['genres'])
        s['status'] = STATUS.get((s['status'] or '').lower(), s['status'] or '')
        s['episodes'].sort(key=lambda e: (e['season'], e['number']))
        if not s['total_episodes']:
            s['total_episodes'] = len(s['episodes'])
        s['thread_id'] = thread_of(s['topic_url'])
        s['oficial'] = official(s, manual, pls)
        out.append(s)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({'series': out}, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'Catálogo generado: {len(out)} series')


if __name__ == '__main__':
    main()
