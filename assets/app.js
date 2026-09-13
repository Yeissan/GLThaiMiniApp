const app = document.getElementById('app');

let catalog = [];

const tg = window.Telegram?.WebApp;

if (tg) {
  tg.ready();
  tg.expand();
}


// ===============================
// UTILIDADES
// ===============================

const esc = s =>
  String(s ?? '').replace(
    /[&<>"']/g,
    c => ({
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      '"': '&quot;',
      "'": '&#39;'
    }[c])
  );


function abs(rel) {
  return rel || '';
}


function openTelegram(url) {
  if (!url) return;

  if (tg?.openTelegramLink) {
    tg.openTelegramLink(url);
  } else {
    location.href = url;
  }
}


function setHash(v) {
  location.hash = v;
}


// ===============================
// CATÁLOGO
// ===============================

function renderCatalog() {

  app.innerHTML = `
    <div class="topbar">
      <div>
        <div class="brand">GL Thai 💕</div>
        <div class="sub">Selecciona una serie</div>
      </div>
    </div>

    <input
      id="q"
      class="search"
      placeholder="Buscar serie…"
      autocomplete="off"
    >

    <div id="grid" class="grid"></div>

    <div class="footer-note">
      Catálogo actualizado automáticamente desde las carpetas del repositorio.
    </div>
  `;


  const q = document.getElementById('q');
  const grid = document.getElementById('grid');


  const paint = () => {

    const x = q.value.trim().toLowerCase();


    const rows = catalog.filter(s =>
      [
        s.title,
        s.originaltitle,
        s.country,
        (s.genres || []).join(' ')
      ]
        .join(' ')
        .toLowerCase()
        .includes(x)
    );


    grid.innerHTML = rows.length

      ? rows.map(s => `
          <button
            class="card"
            data-id="${esc(s.id)}"
          >

            <img
              src="${esc(abs(s.poster))}"
              alt="Portada de ${esc(s.title)}"
            >

            <div class="meta">

              <h3>
                ${esc(s.title)}
              </h3>

              <p>
                ${esc(s.year || '')}
                ${s.country ? ' • ' + esc(s.country) : ''}
              </p>

            </div>

          </button>
        `).join('')

      : `
          <div class="empty">
            No encontré series.
          </div>
        `;


    grid
      .querySelectorAll('.card')
      .forEach(b => {

        b.addEventListener('click', () => {

          setHash(
            'serie=' +
            encodeURIComponent(b.dataset.id)
          );

        });

      });

  };


  q.addEventListener('input', paint);

  paint();
}


// ===============================
// BLOQUE DE INFORMACIÓN
// ===============================

function info(label, val) {

  return val
    ? `
      <div class="info-item">

        <b>
          ${esc(label)}
        </b>

        ${esc(val)}

      </div>
    `
    : '';

}


// ===============================
// FICHA DE SERIE
// ===============================

function renderSeries(id) {

  const s = catalog.find(
    x => x.id === id
  );


  if (!s) {
    renderCatalog();
    return;
  }


  const eps = s.episodes || [];


  // Capítulos actualmente registrados
  const disponibles = eps.length;


  // Total de capítulos
  const total =
    Number(
      s.total_episodes ??
      s.episodes_total ??
      s.episode_count ??
      s.totalEpisodes ??
      disponibles
    ) || disponibles;


  app.innerHTML = `

    <div class="topbar">

      <button
        class="back"
        id="back"
      >
        ← Series
      </button>

      <div>

        <div class="brand">
          ${esc(s.title)}
        </div>

        <div class="sub">
          Ficha de la serie
        </div>

      </div>

    </div>


    <img
      class="hero"
      src="${esc(abs(s.banner || s.poster))}"
      alt="Banner de ${esc(s.title)}"
    >


    <h1 class="title">
      ${esc(s.title)}
    </h1>


    ${
      s.originaltitle
        ? `
          <div class="original">
            ${esc(s.originaltitle)}
          </div>
        `
        : ''
    }


    <div class="chips">

      ${
        [
          s.country,
          s.year,
          s.rating
            ? `⭐ ${s.rating}`
            : null,
          ...(s.display_genres || s.genres || [])
        ]
        .filter(Boolean)
        .map(
          x =>
            `<span class="chip">${esc(x)}</span>`
        )
        .join('')
      }

    </div>


    <p class="plot">
      ${esc(s.description || s.plot || '')}
    </p>


    <div class="info-grid">

      ${info(
        'Estado',
        s.status
      )}

      ${info(
        'Duración',
        s.runtime
          ? `${s.runtime} min`
          : ''
      )}

      ${info(
        'Estreno',
        s.premiered
      )}

      ${info(
        'Estudio',
        (s.studios || []).join(', ')
      )}

    </div>


    ${
      (s.cast || []).length

        ? `

          <h2 class="section-title">
            Reparto
          </h2>


          <div class="cast">

            ${
              s.cast
                .slice(0, 12)
                .map(a => `

                  <span>

                    ${esc(a.name)}

                    ${
                      a.role
                        ? ' · ' + esc(a.role)
                        : ''
                    }

                  </span>

                `)
                .join('')
            }

          </div>

        `

        : ''
    }


    <button
      class="chapter-link"
      id="open-chapters"
    >

      <span class="chapter-name">
        ▶ Ver capítulos
      </span>

      <span class="chapter-count">
        ${disponibles}/${total}
      </span>

      <span class="chapter-arrow">
        →
      </span>

    </button>


    <div
      id="episodes"
      class="episodes"
    >

      ${
        eps.length

          ? eps
              .map(
                (e, i) =>
                  chapterHTML(e, i, s)
              )
              .join('')

          : `
            <div class="empty">
              Todavía no hay capítulos registrados.
            </div>
          `
      }

    </div>

  `;


  // VOLVER AL CATÁLOGO

  document
    .getElementById('back')
    .addEventListener(
      'click',
      () => setHash('')
    );


  // BOTÓN VER CAPÍTULOS

  const chaptersButton =
    document.getElementById('open-chapters');


  if (chaptersButton) {

    chaptersButton.addEventListener(
      'click',
      () => {

        const url =
          s.telegram_url ||
          s.topic_url ||
          eps.find(e => e.topic_url)?.topic_url ||
          eps.find(e => e.telegram_url)?.telegram_url ||
          '';

        if (url) {

          openTelegram(url);

        } else {

          alert(
            'Todavía no hay un enlace de Telegram para esta serie.'
          );

        }

      }
    );

  }

}


// ===============================
// CAPÍTULO
// ===============================

function chapterHTML(e, i, s) {

  const num =
    e.number ??
    i + 1;


  const img =
    e.image ||
    s.banner ||
    s.poster;


  const title =
    e.title ||
    `Capítulo ${num}`;


  const description =
    e.description ||
    'Descripción pendiente.';


  return `

    <article class="episode">

      <img
        src="${esc(abs(img))}"
        alt="Capítulo ${esc(num)}"
      >


      <div class="episode-content">

        <h4>
          ${esc(title)}
        </h4>


        <p>
          ${esc(description)}
        </p>

      </div>

    </article>

  `;

}


// ===============================
// RUTAS
// ===============================

function route() {

  const m =
    location.hash.match(
      /^#serie=(.+)$/
    );


  if (m) {

    renderSeries(
      decodeURIComponent(
        m[1]
      )
    );

  } else {

    renderCatalog();

  }

}


// ===============================
// CARGAR CATÁLOGO
// ===============================

fetch(
  'data/catalog.json',
  {
    cache: 'no-store'
  }
)

.then(r => {

  if (!r.ok) {

    throw new Error(
      'No se pudo cargar data/catalog.json'
    );

  }

  return r.json();

})

.then(d => {

  catalog =
    d.series || [];

  route();

})

.catch(err => {

  app.innerHTML = `

    <div class="error">

      <b>
        No pude cargar el catálogo.
      </b>

      <br>

      ${esc(err.message)}

      <br><br>

      Ejecuta el generador o espera a que termine GitHub Actions.

    </div>

  `;

});


window.addEventListener(
  'hashchange',
  route
);
window.addEventListener(
  'hashchange',
  route
);
