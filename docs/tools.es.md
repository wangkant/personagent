# Los scripts de `tools/`

[English](tools.md) · [简体中文](tools.zh-CN.md) · [繁體中文](tools.zh-TW.md) · [日本語](tools.ja.md) · [한국어](tools.ko.md) · Español · [Français](tools.fr.md) · [Deutsch](tools.de.md) · [Português (Brasil)](tools.pt-BR.md) · [Русский](tools.ru.md)

Los scripts de `tools/` son para quienes ejecutan personagent desde un clon. No se instalan con el paquete y leen `.env` y `runtime/` del clon. Ejecútalos con el intérprete del clon, desde la raíz del repositorio:

```bash
.venv/bin/python tools/<script>.py --help     # Windows: .venv\Scripts\python.exe
```

Las tareas cotidianas son subcomandos de `personagent` en lugar de scripts: `personagent doctor`, `personagent learned` y `personagent eval`. Para probar un cambio de prompt, usa `personagent chat`. Para medirlo, usa `personagent eval`.

| Script | Qué hace | Necesita | Llama a un modelo | Estado |
|---|---|---|---|---|
| `import_stickers_folder.py` | Importa una carpeta de imágenes a la biblioteca de stickers y etiqueta cada una, para que una biblioteca nueva no empiece vacía. `--dry-run` muestra los recuentos y `--no-tag` solo copia los archivos | Una carpeta de imágenes, además de `VISION_MODEL`, `VISION_API_KEY` y `VISION_BASE_URL` para etiquetar | Sí, una llamada de visión por imagen, salvo que pases `--dry-run` o `--no-tag` | Compatible |
| `bootstrap_from_history.py` | Da a un despliegue nuevo un arranque único a partir del historial de un grupo de QQ. Crea el perfil de stickers y longitud de mensajes del administrador y guarda en la biblioteca los stickers que ve | El servidor HTTP de NapCat, un cliente de QQ de terceros, en `QQ_ONEBOT_URL` (obligatorio), y grupos de QQ en `ACCESS_GROUPS` o `--group` | No. El modelo de visión del bot en marcha etiqueta después los stickers guardados | Experimental, solo QQ y NapCat |
| `auto_reviewer.py` | Lee las puntuaciones bajas de autoevaluación de `runtime/eval.jsonl` y hace que un modelo convierta cada una en un par de antes y después. Con `--apply` te pregunta, par por par, si añadirlo al fondo compartido de comentarios | `EVAL_ENABLED=true` durante un tiempo, para que existan puntuaciones | Sí, una llamada por entrada revisada (`--limit`, 20 por defecto). `--dry-run` no llama a nada | Experimental. `--apply` escribe en un fondo que usan todos los chats. Para aprobar un arreglo solo en un chat, usa `personagent learned` |
| `evolution_benchmark.py` | Ejecuta el agente real sobre los escenarios de `data/benchmark/` durante varias rondas, una vez con el bucle de automejora activado y otra desactivado, y compara ambas. `run` hace las ejecuciones e `ingest` lee las puntuaciones del juez | `LLM_API_KEY` y un juez que no sea el modelo evaluado (`--judge export`, `openai` o `anthropic`, con `BENCH_JUDGE_MODEL`) | Sí, muchas: cada escenario, ronda y variante | Experimental |
| `scenario_probe.py` | Prueba escenarios candidatos de la evaluación contra el modelo real e informa de cuáles exponen el fallo que la evaluación necesita | `LLM_API_KEY`, un archivo de escenarios candidatos con la forma de `data/benchmark/scenarios.train.en.jsonl` y `--judge-model` para la pasada del juez | Sí, una respuesta, una autoevaluación y una llamada al juez por escenario | Experimental, para construir la evaluación |
| `sticker_holdout_eval.py` | Mide lo estable y preciso que es el filtro de aprobación de stickers con stickers que etiquetaste a mano | `runtime/holdout.jsonl` (formato en `tools/holdout.example.jsonl`) y los tres ajustes `VISION_*` | Sí, imágenes × `--runs` (5 por defecto) llamadas de visión, unas 150 para 30 imágenes | Experimental |
| `package_smoke.py` | Comprueba de principio a fin un comando `personagent` instalado: versión, `init --no-input`, `chat`, `run` con `/health` y `doctor --json` | Un `personagent` instalado (`--personagent PATH`) y nada más | No, responde un servidor sustituto | Compatible. La CI lo ejecuta en Linux y Windows |
| `welcome_smoke.py` | Comprueba de principio a fin la página local instalada: `start --no-browser`, guardar una clave, un chat con el personaje real, un segundo inicio que reutiliza la página y una salida limpia | Un `personagent` instalado (`--personagent PATH`) y nada más | No, responde el mismo servidor sustituto | Compatible. La CI lo ejecuta en Linux y Windows |
| `release_notes.py` | Comprueba una etiqueta de versión con `pyproject.toml` e imprime la sección del CHANGELOG de esa versión | La etiqueta, como `v1.1.0` | No | Compatible. El flujo de publicación lo ejecuta |

Los scripts experimentales son ayudas de investigación y mantenimiento y pueden cambiar o desaparecer sin periodo de retirada. Los scripts que llaman a un modelo gastan crédito de la cuenta de tu `.env`; lee primero `--help` y prueba `--dry-run` donde exista.
