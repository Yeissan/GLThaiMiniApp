#!/usr/bin/env python3
"""Sincroniza el catálogo con el grupo de Telegram.

- Lee los mensajes nuevos del grupo y apunta los capítulos subidos en cada tema.
- Crea un tema para cada serie que todavía no lo tenga y publica su ficha.
- Mantiene fijado en cada tema un mensaje con la lista de capítulos (con enlaces)
  y lo actualiza cuando aparecen capítulos nuevos.

Variables (se configuran en GitHub, nunca en el código):
  TG_BOT_TOKEN   clave del bot (Secret)
  TG_CHAT_ID     id del grupo (opcional, por defecto el grupo GL Thai)
  MINIAPP_LINK   enlace corto de la app del bot, p. ej. https://t.me/MiBot/series (opcional)
  MAX_NEW        máximo de temas nuevos por ejecución (por defecto 25)
"""
from pathlib import Path
import hashlib
import io
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / 'data' / 'catalog.json'
STATE = ROOT / 'data' / 'telegram.json'

TOKEN = os.environ.get('TG_BOT_TOKEN', '').strip()
CHAT = int(os.environ.get('TG_CHAT_ID', '').strip() or '-1003974971985')
MINIAPP = os.environ.get('MINIAPP_LINK', '').strip().rstrip('/')
PAGES = os.environ.get('PAGES_URL', 'https://yeissan.github.io/GLThaiMiniApp/').strip()
MAX_NEW = int(os.environ.get('MAX_NEW', '').strip() or '25')
API = os.environ.get('TG_API', 'https://api.telegram.org')
INTERNAL = str(CHAT)[4:] if str(CHAT).startswith('-100') else str(abs(CHAT))
COLORS = [7322096, 16766590, 13338331, 9367192, 16749490, 16478047]
VIDEO_EXT = ('.mp4', '.mkv', '.avi', '.mov', '.m4v', '.webm', '.ts', '.wmv', '.flv', '.mpg')


class TgError(Exception):
    def __init__(self, code, desc):
        super().__init__(f'{code}: {desc}')
        self.code, self.desc = code, desc


def call(method, files=None, **params):
    """Llama a la API de Telegram. Espera y reintenta si Telegram pide ir más despacio."""
    for _ in range(5):
        data = {k: (json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else str(v))
                for k, v in params.items() if v is not None}
        url = f'{API}/bot{TOKEN}/{method}'
        if files:
            boundary = 'glthai' + hashlib.md5(str(time.time()).encode()).hexdigest()
            body = io.BytesIO()
            for k, v in data.items():
                body.write(f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n'.encode())
                body.write(v.encode() + b'\r\n')
            for k, (name, blob) in files.items():
                body.write(f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"; '
                           f'filename="{name}"\r\nContent-Type: image/jpeg\r\n\r\n'.encode())
                body.write(blob + b'\r\n')
            body.write(f'--{boundary}--\r\n'.encode())
            req = urllib.request.Request(url, body.getvalue(),
                                         {'Content-Type': f'multipart/form-data; boundary={boundary}'})
        else:
            req = urllib.request.Request(url, urllib.parse.urlencode(data).encode())
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                res = json.load(r)
        except urllib.error.HTTPError as e:
            res = json.load(e)
        if res.get('ok'):
            return res['result']
        wait = (res.get('parameters') or {}).get('retry_after')
        if res.get('error_code') == 429 and wait:
            print(f'   Telegram pide esperar {wait} s…')
            time.sleep(int(wait) + 1)
            continue
        raise TgError(res.get('error_code'), res.get('description', ''))
    raise TgError(429, 'Demasiados intentos')


def esc(t):
    return str(t or '').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def norm(t):
    return re.sub(r'[^a-z0-9]+', '', (t or '').lower())


def link(thread, msg=None):
    return f'https://t.me/c/{INTERNAL}/{thread}' + (f'/{msg}' if msg else '')


def app_link(sid):
    if MINIAPP:
        return f'{MINIAPP}?startapp={urllib.parse.quote(sid)}'
    return f'{PAGES}#serie={urllib.parse.quote(sid)}'


# ---------------------------------------------------------------- capítulos

def episode_number(text):
    """Saca (temporada, capítulo) del texto o nombre de archivo. None si no hay número."""
    t = text or ''
    m = re.search(r'(?i)S(\d{1,2})\s*[._ -]?\s*E[Pp]?\s*(\d{1,3})', t)
    if m:
        return int(m.group(1)), int(m.group(2))
    m = re.search(r'(?i)\b(\d{1,2})x(\d{1,3})\b', t)
    if m:
        return int(m.group(1)), int(m.group(2))
    m = re.search(r'(?i)(?:\bep(?:isodio|isode)?|\bcap(?:[íi]tulo)?|\bchapter|\be)\s*[._#:-]?\s*(\d{1,3})\b', t)
    if m:
        return 1, int(m.group(1))
    return None


def read_updates(state, by_thread, by_name):
    """Lee lo nuevo del grupo: temas creados a mano y vídeos subidos a los temas."""
    offset = state.get('offset')
    total = 0
    while True:
        try:
            ups = call('getUpdates', offset=offset, timeout=0, limit=100,
                       allowed_updates=['message'])
        except TgError as e:
            if e.code == 409:
                print('AVISO: el bot ya recibe sus mensajes por otro sitio (webhook u otro programa),')
                print('       así que no puedo leer los capítulos nuevos. Los temas sí se crean.')
                return
            raise
        if not ups:
            break
        for u in ups:
            offset = u['update_id'] + 1
            m = u.get('message') or {}
            if (m.get('chat') or {}).get('id') != CHAT or not m.get('message_thread_id'):
                continue
            thread = m['message_thread_id']
            created = m.get('forum_topic_created')
            if created:
                sid = by_name.get(norm(created.get('name')))
                if sid and not state['series'].get(sid, {}).get('thread_id'):
                    st = state['series'].setdefault(sid, {})
                    st.update(thread_id=thread, topic_url=link(thread))
                    by_thread[thread] = sid
                    print(f' + Tema creado a mano detectado: {created.get("name")}')
                continue
            sid = by_thread.get(thread)
            if not sid:
                continue
            doc = m.get('document') or {}
            vid = m.get('video') or {}
            is_video = bool(vid) or (doc and ((doc.get('mime_type') or '').startswith('video')
                                               or (doc.get('file_name') or '').lower().endswith(VIDEO_EXT)))
            if not is_video:
                continue
            fname = vid.get('file_name') or doc.get('file_name') or ''
            st = state['series'].setdefault(sid, {})
            eps = st.setdefault('episodes', [])
            found = episode_number(m.get('caption')) or episode_number(Path(fname).stem)
            if not found:
                last = max([e['number'] for e in eps if e['season'] == 1] or [0])
                found = (1, last + 1)
            eps[:] = [e for e in eps if (e['season'], e['number']) != found]
            eps.append({'season': found[0], 'number': found[1], 'msg_id': m['message_id'],
                        'url': link(thread, m['message_id'])})
            eps.sort(key=lambda e: (e['season'], e['number']))
            total += 1
            print(f' + {sid}: capítulo {found[1]} (temporada {found[0]})')
    state['offset'] = offset
    print(f'Capítulos nuevos detectados: {total}')


# ---------------------------------------------------------------- mensajes

def ficha(s):
    lines = [f'🎬 <b>{esc(s["title"])}</b>']
    if s.get('title_en') and norm(s['title_en']) != norm(s['title']):
        lines.append(f'🇬🇧 {esc(s["title_en"])}')
    if s.get('originaltitle') and norm(s['originaltitle']) != norm(s['title']):
        lines.append(f'🇹🇭 {esc(s["originaltitle"])}')
    lines.append('')
    meta = []
    if s.get('rating'):
        try:
            meta.append(f'⭐ {float(s["rating"]):.1f}')
        except ValueError:
            pass
    if s.get('year'):
        meta.append(f'📅 {esc(s["year"])}')
    if s.get('runtime'):
        meta.append(f'⏱ {esc(s["runtime"])} min')
    if meta:
        lines.append(' · '.join(meta))
    if s.get('genres'):
        lines.append('🌸 ' + ' · '.join(esc(g) for g in s['genres']))
    est = [x for x in [s.get('status'), f'{s["total_episodes"]} capítulos' if s.get('total_episodes') else ''] if x]
    if est:
        lines.append('📺 ' + ' · '.join(esc(x) for x in est))
    head = '\n'.join(lines)
    tail = '\n\n👇 La lista de capítulos está fijada arriba del tema.'
    plot = (s.get('plot') or '').split('\n')[0].strip()
    room = 1000 - len(head) - len(tail) - 4
    if plot and room > 80:
        if len(plot) > room:
            plot = plot[:room - 1].rsplit(' ', 1)[0] + '…'
        head += '\n\n<i>' + esc(plot) + '</i>'
    return head + tail


def chapter_list(s, st):
    urls = {(e['season'], e['number']): e.get('telegram_url') for e in s.get('episodes', [])}
    for e in st.get('episodes', []):
        urls[(e['season'], e['number'])] = e['url']
    seasons = sorted({k[0] for k in urls} or {1})
    total = int(s.get('total_episodes') or 0)
    lines = [f'📋 <b>Capítulos de {esc(s["title"])}</b>', '']
    for t in seasons:
        nums = sorted(n for (ss, n) in urls if ss == t)
        top = max(nums + ([total] if len(seasons) == 1 else []) or [0])
        if len(seasons) > 1:
            lines.append(f'<b>Temporada {t}</b>')
        for n in range(1, top + 1):
            u = urls.get((t, n))
            if u:
                lines.append(f'▶️ <a href="{esc(u)}">Capítulo {n:02d}</a>')
            else:
                lines.append(f'⏳ Capítulo {n:02d} · próximamente')
        if len(seasons) > 1 and t != seasons[-1]:
            lines.append('')
    if len(lines) <= 2:
        lines.append('⏳ Los capítulos aparecerán aquí cuando se suban.')
    lines += ['', '<i>Toca un capítulo para verlo. Esta lista se actualiza sola.</i>']
    text = '\n'.join(lines)
    if len(text) > 4000:
        text = text[:3950].rsplit('\n', 1)[0] + '\n…'
    return text


def buttons(s):
    return {'inline_keyboard': [[{'text': '📱 Ver en la app', 'url': app_link(s['id'])}]]}


def poster_bytes(s):
    p = ROOT / (s.get('poster') or '')
    if not s.get('poster') or not p.exists():
        return None
    try:
        from PIL import Image
        im = Image.open(p).convert('RGB')
        im.thumbnail((1000, 1500))
        b = io.BytesIO()
        im.save(b, 'JPEG', quality=88)
        return b.getvalue()
    except Exception:
        return p.read_bytes() if p.suffix.lower() in ('.jpg', '.jpeg', '.png') else None


def send_list(s, st, thread):
    text = chapter_list(s, st)
    h = hashlib.md5(text.encode()).hexdigest()
    if st.get('list_msg') and st.get('list_hash') == h:
        return
    if st.get('list_msg'):
        try:
            call('editMessageText', chat_id=CHAT, message_id=st['list_msg'], text=text,
                 parse_mode='HTML', disable_web_page_preview=True)
            st['list_hash'] = h
            print(f' ~ Lista actualizada: {s["title"]}')
            return
        except TgError as e:
            if 'not modified' in e.desc:
                st['list_hash'] = h
                return
            print(f'   No pude editar la lista de {s["title"]} ({e.desc}); la vuelvo a publicar.')
    msg = call('sendMessage', chat_id=CHAT, message_thread_id=thread, text=text,
               parse_mode='HTML', disable_web_page_preview=True, disable_notification=True)
    st.update(list_msg=msg['message_id'], list_hash=h)
    try:
        call('pinChatMessage', chat_id=CHAT, message_id=msg['message_id'], disable_notification=True)
    except TgError as e:
        print(f'   No pude fijar la lista ({e.desc}). ¿El bot tiene permiso para fijar mensajes?')
    print(f' + Lista publicada y fijada: {s["title"]}')


def main():
    if not TOKEN:
        print('Falta la clave del bot (Secret TG_BOT_TOKEN). No hago nada con Telegram.')
        return 0
    catalog = json.loads(CATALOG.read_text(encoding='utf-8'))['series']
    state = json.loads(STATE.read_text(encoding='utf-8')) if STATE.exists() else {}
    state.setdefault('series', {})

    # Temas que ya existen (puestos a mano en serie.json)
    for s in catalog:
        st = state['series'].setdefault(s['id'], {})
        if s.get('thread_id') and not st.get('thread_id'):
            st.update(thread_id=s['thread_id'], topic_url=link(s['thread_id']))
    by_thread = {st['thread_id']: sid for sid, st in state['series'].items() if st.get('thread_id')}
    by_name = {}
    for s in catalog:
        for t in (s['title'], s.get('title_en')):
            if t:
                by_name[norm(t)] = s['id']

    me = call('getMe')
    print(f'Bot: @{me.get("username")}')
    try:
        read_updates(state, by_thread, by_name)
    finally:
        STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding='utf-8')

    created = 0
    try:
        for i, s in enumerate(catalog):
            st = state['series'].setdefault(s['id'], {})
            thread = st.get('thread_id')
            if not thread:
                if created >= MAX_NEW:
                    continue
                topic = call('createForumTopic', chat_id=CHAT, name=s['title'][:128],
                             icon_color=COLORS[i % len(COLORS)])
                thread = topic['message_thread_id']
                st.update(thread_id=thread, topic_url=link(thread), created_by_bot=True)
                created += 1
                print(f' + Tema creado: {s["title"]}')
                photo = poster_bytes(s)
                if photo:
                    msg = call('sendPhoto', files={'photo': ('poster.jpg', photo)}, chat_id=CHAT,
                               message_thread_id=thread, caption=ficha(s), parse_mode='HTML',
                               reply_markup=buttons(s))
                else:
                    msg = call('sendMessage', chat_id=CHAT, message_thread_id=thread, text=ficha(s),
                               parse_mode='HTML', reply_markup=buttons(s))
                st['ficha_msg'] = msg['message_id']
                time.sleep(3)
            send_list(s, st, thread)
            time.sleep(1)
    except TgError as e:
        print(f'\nERROR de Telegram: {e.desc}')
        if 'not enough rights' in e.desc or 'CHAT_ADMIN_REQUIRED' in e.desc:
            print('El bot tiene que ser administrador del grupo con permiso para gestionar temas y fijar mensajes.')
        elif 'chat not found' in e.desc:
            print('El bot no está en el grupo, o el id del grupo (TG_CHAT_ID) no es correcto.')
        STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding='utf-8')
        return 1
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding='utf-8')
    pending = sum(1 for s in catalog if not state['series'].get(s['id'], {}).get('thread_id'))
    print(f'\nTemas nuevos: {created}. Pendientes para la próxima vez: {pending}.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
