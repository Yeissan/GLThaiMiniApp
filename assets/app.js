const app=document.getElementById('app');
let catalog=[];
const tg=window.Telegram?.WebApp;
if(tg){tg.ready();tg.expand();}

const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function abs(rel){return rel||''}
function openTelegram(url){if(!url)return; if(tg?.openTelegramLink)tg.openTelegramLink(url); else location.href=url;}
function setHash(v){location.hash=v}

function renderCatalog(){
 app.innerHTML=`<div class="topbar"><div><div class="brand">GL Thai 💕</div><div class="sub">Selecciona una serie</div></div></div><input id="q" class="search" placeholder="Buscar serie…" autocomplete="off"><div id="grid" class="grid"></div><div class="footer-note">Catálogo actualizado automáticamente desde las carpetas del repositorio.</div>`;
 const q=document.getElementById('q'),grid=document.getElementById('grid');
 const paint=()=>{const x=q.value.trim().toLowerCase();const rows=catalog.filter(s=>[s.title,s.originaltitle,s.country,(s.genres||[]).join(' ')].join(' ').toLowerCase().includes(x));grid.innerHTML=rows.length?rows.map(s=>`<button class="card" data-id="${esc(s.id)}"><img src="${esc(abs(s.poster))}" alt="Portada de ${esc(s.title)}"><div class="meta"><h3>${esc(s.title)}</h3><p>${esc(s.year||'')} ${s.country?'• '+esc(s.country):''}</p></div></button>`).join(''):`<div class="empty">No encontré series.</div>`;grid.querySelectorAll('.card').forEach(b=>b.addEventListener('click',()=>setHash('serie='+encodeURIComponent(b.dataset.id))))};
 q.addEventListener('input',paint);paint();
}
function info(label,val){return val?`<div class="info-item"><b>${esc(label)}</b>${esc(val)}</div>`:''}
function renderSeries(id){
  const s = catalog.find(x => x.id === id);

  if(!s){
    renderCatalog();
    return;
  }

  const eps = s.episodes || [];

  app.innerHTML = `
    <div class="topbar">
      <button class="back" id="back">← Series</button>

      <div>
        <div class="brand">${esc(s.title)}</div>
        <div class="sub">Ficha de la serie</div>
      </div>
    </div>

    <img
      class="hero"
      src="${esc(abs(s.banner || s.poster))}"
      alt="Banner de ${esc(s.title)}"
    >

    <h1 class="title">${esc(s.title)}</h1>

    <div class="original">
      ${esc(s.originaltitle || '')}
    </div>

    <div class="chips">
      ${
        [
          s.country,
          s.year,
          s.rating ? `⭐ ${s.rating}` : null,
          ...(s.display_genres || s.genres || [])
        ]
        .filter(Boolean)
        .map(x => `<span class="chip">${esc(x)}</span>`)
        .join('')
      }
    </div>

    <p class="plot">
      ${esc(s.description || s.plot || '')}
    </p>

    ${
      (s.telegram_url || s.topic_url)
      ? `
        <div class="series-actions">
          <button
            class="btn series-telegram"
            data-tg="${esc(s.telegram_url || s.topic_url)}"
          >
            ▶ Ver capítulos en Telegram
          </button>
        </div>
      `
      : ''
    }

    <div class="info-grid">
      ${info('Estado', s.status)}
      ${info('Duración', s.runtime ? `${s.runtime} min` : '')}
      ${info('Estreno', s.premiered)}
      ${info('Estudio', (s.studios || []).join(', '))}
    </div>

    ${
      (s.cast || []).length
      ? `
        <h2 class="section-title">Reparto</h2>

        <div class="cast">
          ${
            s.cast
            .slice(0, 12)
            .map(a =>
              `<span>
                ${esc(a.name)}
                ${a.role ? ' · ' + esc(a.role) : ''}
              </span>`
            )
            .join('')
          }
        </div>
      `
      : ''
    }

    <h2 class="section-title">Capítulos</h2>

    <div id="episodes">
      ${
        eps.length
        ? eps.map((e, i) => episodeHTML(e, i, s)).join('')
        : `<div class="empty">Todavía no hay capítulos registrados.</div>`
      }
    </div>
  `;

  document
    .getElementById('back')
    .addEventListener('click', () => setHash(''));

  app
    .querySelectorAll('[data-tg]')
    .forEach(b =>
      b.addEventListener('click', () => openTelegram(b.dataset.tg))
    );
}
function episodeHTML(e,i,s){const num=e.number??i+1;const img=e.image||s.banner||s.poster;const direct=e.telegram_url;const topic=e.topic_url||s.topic_url;return `<article class="episode"><img src="${esc(abs(img))}" alt="Miniatura episodio ${esc(num)}"><div><h4>${esc(e.title||`Episodio ${num}`)}</h4><p>${esc(e.description||'')}</p></div><div class="actions">${direct?`<button class="btn" data-tg="${esc(direct)}">▶ Ver episodio en Telegram</button>`:topic?`<button class="btn" data-tg="${esc(topic)}">Abrir tópico en Telegram</button>`:`<button class="btn secondary" disabled>Enlace de Telegram pendiente</button>`}</div></article>`}
function route(){const m=location.hash.match(/^#serie=(.+)$/);if(m)renderSeries(decodeURIComponent(m[1]));else renderCatalog()}
fetch('data/catalog.json',{cache:'no-store'}).then(r=>{if(!r.ok)throw new Error('No se pudo cargar data/catalog.json');return r.json()}).then(d=>{catalog=d.series||[];route()}).catch(err=>{app.innerHTML=`<div class="error"><b>No pude cargar el catálogo.</b><br>${esc(err.message)}<br><br>Ejecuta el generador o espera a que termine GitHub Actions.</div>`});
window.addEventListener('hashchange',route);
