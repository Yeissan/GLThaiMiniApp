#!/usr/bin/env python3

from pathlib import Path
import json
import re
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
SERIES = ROOT / 'series'
OUT = ROOT / 'data' / 'catalog.json'


def txt(node, name, default=''):
    x = node.find(name)

    return (
        (x.text or '').strip()
        if x is not None and x.text
        else default
    )


def texts(node, name):
    return [
        (x.text or '').strip()
        for x in node.findall(name)
        if x.text
    ]


def safe_json(path, default):
    try:
        if path.exists():
            return json.loads(
                path.read_text(
                    encoding='utf-8-sig'
                )
            )

        return default

    except Exception as e:
        print(f'WARN {path}: {e}')
        return default


def rel(path):
    return path.relative_to(ROOT).as_posix()


def image_for(folder, names):

    for n in names:

        p = folder / n

        if p.exists():
            return rel(p)

    return ''


# ==========================================
# LEER NFO DE CAPÍTULO
# ==========================================

def nfo_episode(path):

    root = ET.parse(path).getroot()

    num = (
        txt(root, 'episode')
        or txt(root, 'displayepisode')
    )

    try:
        num = int(float(num))
    except:
        num = 0


    season = txt(root, 'season')

    try:
        season = int(float(season))
    except:
        season = 1


    stem = path.stem


    image = image_for(
        path.parent,
        [
            stem + '.jpg',
            stem + '.jpeg',
            stem + '.png',
            stem + '-thumb.jpg'
        ]
    )


    telegram = (
        txt(root, 'telegram_url')
        or txt(root, 'telegram')
    )


    return {

        'number':
            num,

        'season':
            season,

        'title':
            txt(root, 'title')
            or f'Capítulo {num}',

        'description':
            txt(root, 'plot')
            or txt(root, 'outline'),

        'image':
            image,

        'telegram_url':
            telegram

    }


# ==========================================
# CONSTRUIR UNA SERIE
# ==========================================

def build_series(folder):

    nfo = folder / 'tvshow.nfo'

    if not nfo.exists():
        return None


    root = ET.parse(nfo).getroot()


    # Datos manuales de la serie
    serie = safe_json(
        folder / 'serie.json',
        {}
    )


    title = txt(
        root,
        'title',
        folder.name
    )


    sid = (
        serie.get('id')
        or re.sub(
            r'[^a-z0-9]+',
            '-',
            title.lower()
        ).strip('-')
    )


    # ======================================
    # CAPÍTULOS
    # ======================================

    eps = []


    # Detecta automáticamente NFO de capítulos
    for p in sorted(
        folder.rglob('*.nfo')
    ):

        if p.name.lower() == 'tvshow.nfo':
            continue

        try:
            eps.append(
                nfo_episode(p)
            )

        except Exception as e:
            print(
                f'WARN episode {p}: {e}'
            )


    # ======================================
    # episodes.json opcional
    # ======================================

    manual = safe_json(
        folder / 'episodes.json',
        []
    )


    bynum = {

        (
            e.get('season', 1),
            e.get('number', 0)
        ):
        e

        for e in eps
    }


    for m in manual:

        key = (
            m.get('season', 1),
            m.get('number', 0)
        )


        base = bynum.get(
            key,
            {}
        )


        merged = {

            **base,

            **{
                k: v
                for k, v in m.items()
                if v not in ('', None)
            }

        }


        bynum[key] = merged


    eps = sorted(

        bynum.values(),

        key=lambda e: (
            e.get('season', 1),
            e.get('number', 0)
        )

    )


    # ======================================
    # IMÁGENES
    # ======================================

    poster = image_for(

        folder,

        [
            'folder.jpg',
            'poster.jpg',
            'folder.png',
            'poster.png'
        ]

    )


    banner = (

        image_for(

            folder,

            [
                'banner.jpg',
                'backdrop.jpg',
                'fanart.jpg',
                'banner.png',
                'backdrop.png'
            ]

        )

        or poster

    )


    # ======================================
    # TOTAL DE CAPÍTULOS
    # ======================================

    total_episodes = (

        serie.get('total_episodes')
        or serie.get('episodes_total')
        or serie.get('episode_count')
        or len(eps)

    )


    # ======================================
    # ENLACE TELEGRAM
    # ======================================

    topic_url = (

        serie.get('topic_url')
        or serie.get('telegram_url')
        or ''

    )


    # ======================================
    # DATOS FINALES
    # ======================================

    d = {

        'id':
            sid,

        'title':
            title,

        'originaltitle':
            txt(
                root,
                'originaltitle'
            ),

        'year':
            txt(
                root,
                'year'
            ),

        'rating':
            txt(
                root,
                'rating'
            ),

        'plot':
            txt(
                root,
                'plot'
            )
            or txt(
                root,
                'outline'
            ),

        'description':
            serie.get('description')
            or '',

        'runtime':
            txt(
                root,
                'runtime'
            ),

        'premiered':
            txt(
                root,
                'premiered'
            ),

        'status':
            txt(
                root,
                'status'
            ),

        'genres':
            texts(
                root,
                'genre'
            ),

        'studios':
            texts(
                root,
                'studio'
            ),

        'tags':
            texts(
                root,
                'tag'
            ),

        'poster':
            poster,

        'banner':
            banner,

        'country':
            serie.get(
                'country',
                ''
            ),

        'display_genres':
            serie.get(
                'display_genres',
                []
            ),

        # Telegram
        'topic_url':
            topic_url,

        # Total real
        'total_episodes':
            total_episodes,

        'cast': [

            {

                'name':
                    txt(
                        a,
                        'name'
                    ),

                'role':
                    txt(
                        a,
                        'role'
                    )

            }

            for a in root.findall(
                'actor'
            )

        ],

        'episodes':
            eps

    }


    return d


# ==========================================
# GENERAR CATÁLOGO
# ==========================================

def main():

    items = []


    if not SERIES.exists():

        print(
            f'ERROR: no existe {SERIES}'
        )

        return


    for folder in sorted(
        [
            p
            for p in SERIES.iterdir()
            if p.is_dir()
        ]
    ):

        try:

            x = build_series(
                folder
            )

            if x:
                items.append(x)

        except Exception as e:

            print(
                f'ERROR {folder}: {e}'
            )


    OUT.parent.mkdir(
        parents=True,
        exist_ok=True
    )


    OUT.write_text(

        json.dumps(

            {
                'series':
                    items
            },

            ensure_ascii=False,

            indent=2

        ),

        encoding='utf-8'

    )


    print(
        f'Generated {OUT} with {len(items)} series'
    )


if __name__ == '__main__':
    main()
