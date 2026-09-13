# GL Thai Mini App

Mini App de catálogo para Telegram. Las imágenes, descripciones y metadatos viven en GitHub; los vídeos permanecen en Telegram.

## Estructura por serie
Crea una carpeta dentro de `series/`:

```
series/NOMBRE/
  tvshow.nfo
  folder.jpg
  banner.jpg
  overrides.json       # opcional
  episodes.json        # opcional
  episodes/            # opcional: NFO de episodios exportados desde Jellyfin/Kodi
    S01E01.nfo
    S01E01.jpg
```

El generador detecta automáticamente cada carpeta con `tvshow.nfo`, lee título, título original, año, valoración, argumento, duración, géneros, estudio, estado y reparto, y busca `folder.jpg` + `banner.jpg`.

### Capítulos automáticos
Si copias NFO de episodios (`S01E01.nfo`, etc.), el generador los detecta y usa `title`, `plot`, `season` y `episode`. Si junto al NFO existe `S01E01.jpg`, la usa como miniatura.

Para abrir un episodio directamente en Telegram, puedes añadir al NFO una etiqueta personalizada:

```xml
<telegram_url>https://t.me/...</telegram_url>
```

O editar `episodes.json` y poner `telegram_url` allí. Los valores manuales de `episodes.json` tienen prioridad sobre el escaneo automático.

### Datos que quieras corregir
Usa `overrides.json`:

```json
{
  "country": "Tailandia",
  "display_genres": ["Romance", "Escolar", "GL"],
  "topic_url": "https://t.me/...",
  "description": ""
}
```

`topic_url` es el enlace al tópico de Telegram de esa serie. Si un episodio tiene `telegram_url`, el botón abre ese capítulo; si no, usa `topic_url`.

## Actualización automática
Cada vez que subas/cambies algo dentro de `series/`, GitHub Actions ejecuta `scripts/build_catalog.py` y regenera `data/catalog.json`. No tienes que editar el catálogo principal a mano.

También puedes generarlo en tu PC:

```bash
python scripts/build_catalog.py
```

## GitHub Pages
1. Sube todo este proyecto a un repositorio.
2. En GitHub: Settings → Pages.
3. Source: `Deploy from a branch`.
4. Branch: `main` y carpeta `/ (root)`.
5. Guarda y espera a que aparezca la URL pública.
6. Esa URL será la que configures como Mini App/Web App del bot.

## Importante sobre tópicos de Telegram
La Mini App puede mostrar únicamente el enlace del tópico de la serie seleccionada. Sin embargo, si todos los tópicos están dentro del mismo grupo-foro y el usuario es miembro del grupo, Telegram puede permitirle navegar manualmente a otros tópicos. La Mini App por sí sola no puede cambiar los permisos de visibilidad de tópicos individuales.
