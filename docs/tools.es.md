# Los scripts de `tools/`

[English](tools.md) · [简体中文](tools.zh-CN.md) · [繁體中文](tools.zh-TW.md) · [日本語](tools.ja.md) · [한국어](tools.ko.md) · Español · [Français](tools.fr.md) · [Deutsch](tools.de.md) · [Português (Brasil)](tools.pt-BR.md) · [Русский](tools.ru.md)

Los scripts de `tools/` son para quienes ejecutan personagent desde un clon. No se instalan con el paquete y leen `.env` y `runtime/` del clon. Ejecútelos con el intérprete del clon, desde la raíz del repositorio:

```bash
.venv/bin/python tools/<script>.py --help     # Windows: .venv\Scripts\python.exe
```

Las tareas cotidianas son subcomandos de `personagent` en lugar de scripts: `personagent doctor`, `personagent learned` y `personagent eval`. Para probar un cambio de prompt, utilice `personagent chat`. Para medirlo, utilice `personagent eval`. `personagent eval --suite memory` se ejecuta sin conexión con respuestas de consolidación predefinidas, 21 casos por idioma, y no necesita ninguna clave; en esta versión se cumplen todos. Las demás suites llaman a un modelo.

| Script | Qué hace | Necesita | Llama a un modelo | Estado |
|---|---|---|---|---|
| `import_stickers_folder.py` | Importa una carpeta de imágenes a la biblioteca de stickers y etiqueta cada una, para que una biblioteca nueva no empiece vacía. `--dry-run` muestra los recuentos y `--no-tag` solo copia los archivos | Una carpeta de imágenes, además de `VISION_MODEL`, `VISION_API_KEY` y `VISION_BASE_URL` para etiquetar | Sí, una llamada de visión por imagen, salvo que se indique `--dry-run` o `--no-tag` | Compatible |
| `bootstrap_from_history.py` | Da a un despliegue nuevo un arranque único a partir del historial de un grupo de QQ. Crea el perfil de stickers y longitud de mensajes del administrador y guarda en la biblioteca los stickers que ve | El servidor HTTP de NapCat, un cliente de QQ de terceros, en `QQ_ONEBOT_URL` (obligatorio), y grupos de QQ en `ACCESS_GROUPS` o `--group` | No. El modelo de visión del bot en marcha etiqueta después los stickers guardados | Experimental, solo QQ y NapCat |
| `sticker_holdout_eval.py` | Mide la estabilidad y la precisión del filtro de aprobación de stickers con stickers que usted haya etiquetado manualmente | `runtime/holdout.jsonl` (formato en `tools/holdout.example.jsonl`) y los tres ajustes `VISION_*` | Sí, imágenes × `--runs` (5 por defecto) llamadas de visión, unas 150 para 30 imágenes | Experimental |
| `package_smoke.py` | Comprueba de principio a fin un comando `personagent` instalado: versión, `init --no-input`, `chat`, `run` con `/health` y `doctor --json` | Un `personagent` instalado (`--personagent PATH`) y nada más | No, responde un servidor sustituto | Compatible. La CI lo ejecuta en Linux y Windows |
| `welcome_smoke.py` | Comprueba de principio a fin la página local instalada: `start --no-browser`, guardar una clave, un chat con el personaje real, un segundo inicio que reutiliza la página y una salida limpia | Un `personagent` instalado (`--personagent PATH`) y nada más | No, responde el mismo servidor sustituto | Compatible. La CI lo ejecuta en Linux y Windows |
| `window_smoke.py` | Abre la ventana real de la aplicación en una carpeta de inicio temporal, configura la página y chatea dentro de la ventana, y después la cierra | `personagent` instalado con el extra de aplicación (`pip install "personagent[app]"`) en macOS y Linux; en Linux, además, una pantalla, como `xvfb-run` | No, responde el mismo servidor sustituto | Compatible. La CI lo ejecuta en Linux, macOS y Windows |
| `release_notes.py` | Comprueba una etiqueta de versión con `pyproject.toml` e imprime la sección del CHANGELOG de esa versión | La etiqueta, como `v1.1.0` | No | Compatible. El flujo de publicación lo ejecuta |
| `locale_gaps.py` | Cuenta, para cada idioma de `persona_agent/locales/`, cuántas frases del asistente de configuración, del chat en el terminal y de la demostración tienen traducción. Con un código de idioma, como `ja`, imprime las que aún faltan y se verían en inglés | Nada | No | Compatible. `tests/test_locales.py` falla si falta alguna |

Los scripts experimentales son ayudas de investigación y mantenimiento y pueden cambiar o desaparecer sin periodo de retirada. Los scripts que llaman a un modelo consumen crédito de la cuenta de su `.env`; lea primero `--help` y pruebe `--dry-run` cuando esté disponible.
