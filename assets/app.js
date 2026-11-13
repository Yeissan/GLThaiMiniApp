// Catálogo GL Thai · página "Series" del bot
const tg = window.Telegram?.WebApp;
if (tg) {
  tg.ready();
  tg.expand();
  try { tg.setHeaderColor('#0a0612'); tg.setBackgroundColor('#0a0612'); } catch (e) {}
}

const $ = id => document.getElementById(id);
const shelf = $('shelf'), detail = $('detail'), q = $('q');
let catalog = [];
let current = null;

const esc = s => String(s ?? '').replace(/[&<>"']/g, c =>
  ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const norm = s => String(s ?? '').toLowerCase().replace(/[^a-z0-9]+/g, '');

function toast(msg) {
  const t = $('toast');
  t.textContent = msg;
  t.hidden = false;
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => { t.hidden = true; }, 2800);
}

function openTelegram(url) {
  if (!url) return;
  if (tg?.openTelegramLink && /^https:\/\/t\.me\//.test(url)) tg.openTelegramLink(url);
  else window.open(url, '_blank');
}

// ---------- estante de pósters

function paintShelf() {
  const x = q.value.trim().toLowerCase();
  const rows = catalog.filter(s =>
    [s.title, s.title_en, s.originaltitle, (s.genres || []).join(' ')].join(' ').toLowerCase().includes(x));
  shelf.innerHTML = rows.length
    ? rows.map(s => `
      <button class="card" type="button" data-id="${esc(s.id)}" aria-pressed="${s.id === current}">
        <div class="pic">${s.poster ? `<img src="${esc(s.poster)}" alt="" loading="lazy">` : ''}</div>
        <div class="t">${esc(s.title)}</div>
      </button>`).join('')
    : '<div class="empty">No encontré ninguna serie con ese nombre.</div>';
}

// ---------- ficha

function show(id, scroll) {
  const s = catalog.find(x => x.id === id) || catalog[0];
  if (!s) return;
  current = s.id;
  shelf.querySelectorAll('.card').forEach(b => b.setAttribute('aria-pressed', b.dataset.id === s.id));
  if (scroll) shelf.querySelector(`[data-id="${CSS.escape(s.id)}"]`)?.scrollIntoView({ inline: 'center', block: 'nearest' });
  if (location.hash !== '#serie=' + encodeURIComponent(s.id)) history.replaceState(null, '', '#serie=' + encodeURIComponent(s.id));

  detail.style.setProperty('--bk', s.banner ? `url("${s.banner}")` : 'none');

  const eps = s.episodes || [];
  const seasons = [...new Set(eps.map(e => e.season || 1))].sort((a, b) => a - b);
  if (!seasons.length) seasons.push(1);
  const multi = seasons.length > 1;
  const byKey = new Map(eps.map(e => [`${e.season || 1}-${e.number}`, e]));
  const total = Number(s.total_episodes) || 0;
  let chips = '', shown = 0, linked = 0;
  for (const t of seasons) {
    const nums = eps.filter(e => (e.season || 1) === t).map(e => e.number);
    const top = Math.max(0, ...nums, multi ? 0 : total);
    for (let n = 1; n <= top; n++) {
      const e = byKey.get(`${t}-${n}`);
      const url = e?.telegram_url || '';
      shown++;
      if (url) linked++;
      chips += url
        ? `<button class="ep" type="button" data-url="${esc(url)}" title="Ver capítulo ${n}"><small>${multi ? 'T' + t : 'Cap'}</small>${String(n).padStart(2, '0')}</button>`
        : `<div class="ep miss" title="Todavía no está en Telegram"><small>${multi ? 'T' + t : 'Cap'}</small>${String(n).padStart(2, '0')}</div>`;
    }
  }
  const pct = shown ? Math.round(linked / shown * 100) : 0;
  const rating = Number(s.rating);
  const showEn = s.title_en && norm(s.title_en) !== norm(s.title);
  const showOrig = s.originaltitle && norm(s.originaltitle) !== norm(s.title);
  const plot = (s.description || s.plot || '').trim();

  detail.innerHTML = `
    <div class="poster">${s.poster ? `<img src="${esc(s.poster)}" alt="Póster de ${esc(s.title)}">` : ''}</div>
    <div class="info">
      <div class="top">
        ${showOrig ? `<div class="orig">${esc(s.originaltitle)}</div>` : ''}
        <h2>${esc(s.title)}</h2>
        ${showEn ? `<div class="en"><span>EN</span>${esc(s.title_en)}</div>` : ''}
        <div class="meta">
          ${rating ? `<span class="chip star">★ ${rating.toFixed(1)}</span>` : ''}
          ${s.year ? `<span class="chip">${esc(s.year)}</span>` : ''}
          ${s.status ? `<span class="chip ${s.status === 'En emisión' ? 'live' : ''}">${esc(s.status)}</span>` : ''}
          ${s.runtime ? `<span class="chip">${esc(s.runtime)} min</span>` : ''}
          ${(s.genres || []).map(g => `<span class="chip">${esc(g)}</span>`).join('')}
        </div>
      </div>
      <div class="rest">
        ${plot ? `<p class="plot">${esc(plot)}</p>` : ''}
        ${(s.cast || []).length ? `<p class="cast">Reparto: <b>${s.cast.slice(0, 6).map(a => esc(a.name)).join(' · ')}</b></p>` : ''}
        <button class="go" type="button" id="go" ${s.topic_url ? '' : 'disabled'}>
          ${s.topic_url ? '💬 Abrir el tema en Telegram' : 'Tema en Telegram · próximamente'}
        </button>
        ${s.oficial?.url ? `<a class="oficial" href="${esc(s.oficial.url)}" target="_blank" rel="noopener" id="of">📺 Ver oficial · ${esc(s.oficial.name)} <span>${s.oficial.gratis ? 'Gratis' : 'De pago'}</span></a>` : ''}
        <div class="eps-head"><h3>Capítulos</h3><p>${linked} de ${shown} en Telegram${multi ? ' · ' + seasons.length + ' temporadas' : ''}</p></div>
        <div class="bar"><i style="width:${pct}%"></i></div>
        <div class="eps">${chips || '<div class="empty">Los capítulos aparecerán aquí.</div>'}</div>
      </div>
    </div>`;

  $('go').addEventListener('click', () => openTelegram(s.topic_url));
  $('of')?.addEventListener('click', e => {
    if (tg?.openLink) { e.preventDefault(); tg.openLink(s.oficial.url); }
  });
  detail.querySelectorAll('.ep[data-url]').forEach(b =>
    b.addEventListener('click', () => openTelegram(b.dataset.url)));
  detail.querySelectorAll('.ep.miss').forEach(b =>
    b.addEventListener('click', () => toast('Este capítulo todavía no está en Telegram.')));
}

// ---------- arranque

function wanted() {
  const m = location.hash.match(/^#serie=(.+)$/);
  if (m) return decodeURIComponent(m[1]);
  return tg?.initDataUnsafe?.start_param || new URLSearchParams(location.search).get('serie') || '';
}

shelf.addEventListener('click', e => {
  const b = e.target.closest('.card');
  if (b) show(b.dataset.id);
});
q.addEventListener('input', paintShelf);
window.addEventListener('hashchange', () => { const id = wanted(); if (id && id !== current) show(id, true); });

fetch('data/catalog.json', { cache: 'no-store' })
  .then(r => { if (!r.ok) throw new Error('No se pudo cargar el catálogo.'); return r.json(); })
  .then(d => {
    catalog = d.series || [];
    const eps = catalog.reduce((a, s) => a + (s.episodes || []).filter(e => e.telegram_url).length, 0);
    $('count').innerHTML = `<b>${catalog.length}</b> series · <b>${eps}</b> caps`;
    paintShelf();
    if (catalog.length) show(wanted(), true);
    else detail.innerHTML = '<div class="loading">Todavía no hay series en el catálogo.</div>';
  })
  .catch(err => {
    detail.innerHTML = `<div class="loading">No pude cargar el catálogo.<br>${esc(err.message)}</div>`;
  });
