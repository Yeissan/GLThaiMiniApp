# GL Thai · Series

Página "Series" del bot de Telegram (catálogo neón) y programa que mantiene los temas del grupo.

## Cómo se actualiza

1. En el PC, doble clic en **CREAR CATALOGO.bat**. Crea `D:\GL\_Para GitHub\pc`.
2. En GitHub: **Add file → Upload files** y arrastra la carpeta `pc` (si son más de 100 archivos, en varias tandas).
3. GitHub hace el resto solo (pestaña **Actions → Actualizar catálogo y temas de Telegram**):
   - genera `data/catalog.json` (lo que ve la página);
   - crea en el grupo un tema para cada serie que no lo tenga, con su ficha;
   - fija en cada tema la lista de capítulos y la actualiza cada 3 horas
     cuando se suben capítulos nuevos al tema.

Para hacerlo al momento: **Actions → Actualizar catálogo y temas de Telegram → Run workflow**.

## Configuración (una sola vez)

En **Settings → Secrets and variables → Actions**:

- Secret `TG_BOT_TOKEN`: la clave del bot (de BotFather). Nadie más la ve.
- Variable `MINIAPP_LINK` (opcional): enlace corto de la app, por ejemplo `https://t.me/MiBot/series`,
  para que el botón "Ver en la app" abra la serie dentro de Telegram.
- Variable `TG_CHAT_ID` (opcional): id del grupo si cambia (por defecto `-1003974971985`).

El bot tiene que ser **administrador** del grupo con permiso para **gestionar temas** y **fijar mensajes**.

## Capítulos

Al subir un vídeo a un tema, se detecta el número si el pie o el nombre del archivo lo lleva
(`Capítulo 3`, `EP03`, `S02E03`…). Si no lo lleva, se toma como el siguiente capítulo.

## Otras fuentes

- `series/<NOMBRE>/` con `tvshow.nfo`, imágenes, `serie.json` y `episodes.json` (formato anterior) sigue funcionando.
- `data/telegram.json` lo escribe GitHub solo: no hace falta tocarlo.
