# Guía de usuario de personagent

[English](guide.md) · [简体中文](guide.zh-CN.md) · [繁體中文](guide.zh-TW.md) · [日本語](guide.ja.md) · [한국어](guide.ko.md) · Español · [Français](guide.fr.md) · [Deutsch](guide.de.md) · [Português (Brasil)](guide.pt-BR.md) · [Русский](guide.ru.md)

Esta guía cubre cómo configurar personagent, ponerlo en tus chats, enseñarle y cuidarlo. El [README](readme/README.es.md) es la versión corta, y [Primeros pasos](start.es.md) recorre la página local pantalla a pantalla.

1. [Instalación y carpeta de inicio](#instalación-y-carpeta-de-inicio)
2. [La página local](#la-página-local)
3. [Míralo primero: la demo](#míralo-primero-la-demo)
4. [Comandos de terminal](#comandos-de-terminal): [configuración](#configurar-en-el-terminal) · [chat](#chatear-en-el-terminal) · [ejecutar el servicio](#ejecutar-el-servicio)
5. [Hazlo tu personaje](#hazlo-tu-personaje)
6. [Ponlo en un chat](#ponlo-en-un-chat): [QQ, WeChat, Telegram, Discord](#qq-wechat-telegram-y-discord) · [Otras plataformas](#otras-plataformas-a-través-del-astrbot-gestionado) · [Puentes que ejecutas tú](#puentes-que-ejecutas-tú) · [Hablar primero](#hablar-primero)
7. [Agentes de código](#agentes-de-código)
8. [Enséñale](#enséñale)
9. [Actividad](#actividad)
10. [Mídelo](#mídelo)
11. [Cómo funciona](#cómo-funciona)
12. [Privacidad y consentimiento](#privacidad-y-consentimiento)
13. [Solución de problemas](#solución-de-problemas)
14. [Actualizar desde 0.x](#actualizar-desde-0x)
15. [Estado y otros documentos](#estado-y-otros-documentos)

## Instalación y carpeta de inicio

```sh
python -m pip install personagent
personagent
```

`personagent` abre [la página local](#la-página-local) en tu navegador. También puedes instalarlo o ejecutarlo de estas formas:

| Vía | Comando |
|---|---|
| Ejecutar sin instalar | `uvx personagent` (parte de [uv](https://docs.astral.sh/uv/), que también te descarga Python) |
| Un comando `personagent` permanente | `uv tool install personagent` o `pipx install personagent` |
| Windows, desde el ZIP de código fuente | descomprímelo y haz doble clic en `start.bat` |
| Desde un clon | `git clone https://github.com/wangkant/personagent.git`, `cd personagent`, `python -m venv .venv`, luego `.venv/bin/python -m pip install -e .` y `.venv/bin/python -m persona_agent` (en Windows, `.venv\Scripts\python.exe`) |

personagent funciona con Python 3.10–3.14. `start.bat` crea `.venv`, instala las dependencias y abre la misma página. Las vuelve a instalar cada vez que cambia la lista de dependencias de `pyproject.toml`.

La **carpeta de inicio** guarda los ajustes (`.env`), el personaje (`persona.txt`), lo que aprende (`runtime/`) y las plataformas de chat (`platforms/`). `platforms/` contiene el AstrBot gestionado y `direct.json`, que guarda las credenciales de las plataformas que personagent conecta por sí mismo. personagent usa la primera de estas carpetas:

1. la carpeta indicada con `--home DIR` o `AGENT_HOME`. `--home` puede ir antes o después del comando, como en `personagent chat --home D:\bot`.
2. el clon, si lo ejecutas desde uno.
3. la carpeta actual, si contiene tanto `.env` como `persona.txt`.
4. `~/personagent`, creada en la primera configuración.

Para ejecutar varios personajes desde una instalación, dale a cada uno su propia carpeta de inicio.

Esta guía escribe los comandos como `personagent ...`. Si no lo instalaste, pon `uvx` delante. En un clon, `.venv/bin/python -m persona_agent ...` hace lo mismo (en Windows, `.venv\Scripts\python.exe -m persona_agent ...`).

## La página local

`personagent` (o `personagent start`) sirve una página a la que solo puede acceder este ordenador y la abre en el navegador. La página tiene cuatro vistas:

- **Chat** es un chat uno a uno con el personaje en el navegador. Responde el mismo agente que atiende tus plataformas de chat.
- **Actividad** muestra los chats en los que está el personaje, lo que dijo últimamente, lo que aprendió y lo que espera tu decisión. Consulta [Actividad](#actividad).
- **Conectar apps** pone al personaje en QQ, WeChat, Telegram, Discord y otras plataformas. Consulta [Ponlo en un chat](#ponlo-en-un-chat).
- **Personaje y ajustes** es donde eliges un servicio de modelos (OpenRouter, DeepSeek, SiliconFlow, Alibaba Bailian, Zhipu GLM, Moonshot, Volcengine Ark, OpenAI, Google Gemini, Ollama o cualquier otro servicio compatible con OpenAI), pegas la clave de API y eliges un nombre y una personalidad lista. **Verificar y empezar a chatear** prueba la clave con una petición pequeña y la guarda solo si la petición tiene éxito. Tras la configuración, la casilla **Perfil del personaje** muestra `persona.txt`. **Guardar perfil** reinicia el agente con el nuevo texto y conserva lo aprendido. **Más funciones** activa la búsqueda web con Tavily (DuckDuckGo es la opción gratuita por defecto), la comprensión de imágenes y hablar primero en las apps que elijas.

Hasta que conectes una app, la vista Chat muestra una barra breve de **Primeros pasos**.

Volver a ejecutar `personagent` reutiliza la página que ya está abierta. `--no-browser` imprime el enlace en lugar de abrir un navegador.

Cuando hay un personagent más nuevo en PyPI, la vista Chat muestra un aviso con el comando que actualiza tu instalación, tanto si vino de pip, uvx, uv tool, pipx o un clon de Git. Para un ZIP de código fuente descomprimido, el aviso enlaza a la página de versiones. El terminal imprime el mismo comando. Cerrar el aviso lo oculta para esa versión, y **N disponible** bajo el número de versión lo recupera. `personagent up` y `personagent doctor` también informan de una versión nueva. La página y `up` preguntan a pypi.org como mucho una vez al día, en segundo plano. `doctor` pregunta enseguida si la última respuesta tiene más de un día. Define `UPDATE_CHECK_ENABLED=false` para desactivar la comprobación.

La página inicia el agente y las plataformas conectadas en segundo plano, así que mantén su ventana abierta mientras los uses. Todo lo que inició se detiene con ella, tanto si haces clic en **Salir**, pulsas Ctrl+C o cierras la ventana. Si una ejecución anterior falló y dejó procesos, el siguiente inicio los detiene primero.

## Míralo primero: la demo

`personagent demo` reproduce tres escenas con un modelo guionizado, así que no necesita clave. Las escenas muestran qué mensajes de grupo omite y por qué, cómo aprende de una corrección y cómo un desconocido no consigue plantar una instrucción. Para reproducir solo una escena, nómbrala (`quiet`, `teach` o `troll`). Añade `--lang` y un código de idioma para otro idioma, como `--lang ja`.

A continuación hay una ejecución recortada de `personagent demo teach`. Las frases del modelo están guionizadas, pero el registro y la regla de promoción son el código real:

```text
  Alex: Nova, the deploy failed again
  Nova: did you check the logs? roll back first, then diff the configs
  Alex: Nova, I was just venting
      judged: rejection, accepted: "Alex was venting, not asking for a fix"
      ledger: negative only (it says the reply was off, not what to say)
      Nova's next reply to Alex counts as its second try
  Nova: fair. that's a rough end to the day
  Alex: haha yeah it is, thanks Nova
      judged: positive, accepted: "Alex agreed with the second try and thanked Nova"
      ledger: weak (a laugh or a thanks never changes anything alone)
      ledger: Alex accepted the second try: strong (Alex is who the reply was for)

  fix: "did you check the logs? roll back first, ..." -> "fair. that's a rough end to the day"
    [x] 2 of 2 agreeing reactions
    [x] 1 of 1 strong
    [x] same chat
    [x] 1 of 1 person (PROMOTE_MIN_SPEAKERS)
    [x] nothing disagrees, no rival fix
    now in use: 2 agreeing reactions, 1 strong, same chat
```

La escena también envía el mismo mensaje antes y después de la lección: a alguien se le murió el portátil en mitad de una demo. Antes de la corrección, Nova ofrece una solución. Después, ofrece comprensión. La demo sigue guionizada aunque haya una clave definida, así que cada ejecución es idéntica y no cuesta nada. `personagent demo --online` la reproduce en tu propio modelo, lo que cuesta tokens y varía de una ejecución a otra.

## Comandos de terminal

Todo lo que hace la página también está disponible desde un terminal, lo que viene bien para servidores y scripts.

| Comando | Qué hace |
|---|---|
| `personagent start` | abre la página local (`--terminal` para un menú en el terminal) |
| `personagent init` | configura una carpeta de inicio; `--terminal` hace las preguntas en el terminal, `--no-input` acepta opciones |
| `personagent chat` | un chat de grupo simulado en el terminal |
| `personagent demo` | la demo guionizada de arriba |
| `personagent run` | solo el servicio, para conectores que ejecutas tú |
| `personagent up` | el servicio, las plataformas que personagent conecta por sí mismo y el AstrBot gestionado, todo junto |
| `personagent connect astrbot` | conecta un AstrBot (`--install` para descargar uno gestionado, `--start` para iniciarlo) |
| `personagent connect claude-code`, `personagent connect codex`, `personagent connect dsh` | pone al personaje en un [agente de código](#agentes-de-código) (`--react` para comentarios al terminar un turno en los dos primeros, `--remove` para deshacer) |
| `personagent mcp` | el servidor MCP que inicia un agente de código; no lo ejecutas tú |
| `personagent doctor` | comprueba la configuración y todos los servicios de los que depende |
| `personagent learned` | revisa, promueve o revierte lo aprendido |
| `personagent eval` | mide el habla, la persona y el aprendizaje |

Todos los comandos aceptan `--help`.

### Configurar en el terminal

`personagent init --terminal` hace las mismas preguntas que la página, en el idioma que elijas primero, y explica cada término en una línea:

- **El servicio de IA.** Los preajustes coinciden con los de la página. El predeterminado es `openrouter/free` de OpenRouter, que entrega cada petición a uno de sus modelos gratuitos. La clave no cuesta nada. El límite es de 20 peticiones por minuto y 50 al día, o 1000 al día si has comprado al menos 10 créditos. Cuenta toda llamada al modelo, no solo las respuestas, y el día se reinicia a medianoche UTC. Cuando se agota, el personaje dice que no puede responder ahora, y `runtime/desktop/agent.log` tiene el motivo de OpenRouter. El modelo cambia entre peticiones, así que la voz del personaje varía más que con un modelo elegido, y algunos proveedores gratuitos conservan lo que reciben. Para un personaje más estable, usa un modelo de pago con la misma clave. Si te cuesta acceder a OpenRouter desde donde estás, `glm-4.7-flash` de Zhipu también es gratuito. Para Ollama, nombra un modelo que ya hayas descargado. Ollama no necesita clave.
- **La clave.** La entrada está oculta por defecto. Puedes elegir mostrarla, lo que también revela la clave guardada al reconfigurar. El asistente prueba la clave con una petición pequeña. Si falla, muestra la dirección a la que llamó, el estado HTTP y una posible solución.
- **El personaje.** Un nombre y uno de cuatro personajes listos (amigo socarrón, oyente cálido, gamer, ratón de biblioteca) o uno simple para que lo escribas tú.
- **AstrBot.** Opcional, y puedes saltarlo la primera vez. Consulta [Puentes que ejecutas tú](#puentes-que-ejecutas-tú).

Para configurar sin preguntas, por ejemplo en un script, ejecuta `personagent init --no-input` con `--provider`, `--model`, `--key-env VAR`, `--name`, `--lang` y `--persona`. En una carpeta de inicio nueva, una clave de `--key-env` o del `LLM_API_KEY` de la shell necesita `--provider` o `--base-url` para indicar de quién es. `--provider other` también necesita `--base-url`. `personagent init --help` lista todas las opciones. Si `personagent init` se ejecuta sin terminal y sin ninguna de estas opciones, omite las preguntas, lo indica y sale con el código 2.

### Chatear en el terminal

`personagent chat` te pone en un chat de grupo simulado con el personaje. Una línea normal es charla de grupo corriente, y la prueba te dice si el personaje se uniría y por qué. Una línea que contiene su nombre lo llama:

```text
Alex> anyone around tonight?
  (Nova stays quiet: not addressed, 1 of 4 messages)

Alex> Nova, the deploy failed again
  Nova > did you check the logs? roll back first, then diff the configs
```

| Escribe | Para |
|---|---|
| `/reply <text>` | citar su última respuesta, lo que cuenta como una reacción de la que puede aprender |
| `/as Sam <text>` | hablar como otra persona: `/as Sam Nova, you free tonight?` |
| `/admin <text>` | hablar una vez como administrador: `/admin Nova, how was your day?` |
| `/why` | ver por qué dijo su última respuesta y qué guarda el registro sobre ella |
| `/learned` | ver lo que ha aprendido en este chat |
| `/reset` | borrar el chat y lo aprendido en la prueba |
| `/quit` | salir |

Las líneas `/as` y `/admin` también siguen las reglas de grupo, así que incluye el nombre para recibir respuesta. Una línea de menos de cuatro caracteres que no nombre al personaje no cuenta para unirse. Los [comandos de memoria](#comandos-de-memoria) también funcionan aquí.

| Opción | Qué hace |
|---|---|
| `--name Alex` | define tu nombre |
| `--admin` | hace que todas las líneas sean del administrador |
| `--dm` | lo convierte en un chat uno a uno |
| `--lang <code>` | sustituye `AGENT_LANG`, como `--lang ja` |
| `--trigger N` | mensajes antes de considerar unirse (por defecto 4) |

La prueba ejecuta la decisión real de hablar o callar, las comprobaciones de salida, los comandos de memoria y el aprendizaje. Considera unirse tras 4 mensajes, donde el bot en vivo espera 30. Lo que aprende se queda en `runtime/trial/` de la carpeta de inicio, separado del bot en vivo. `personagent learned` no lo muestra, y `/reset` lo borra. La prueba omite las listas de permitidos y la entrega real. También desactiva la autoevaluación, la visión, la pregunta de seguimiento y los mensajes que el personaje iniciaría por su cuenta. Cuando falla una llamada al modelo, imprime una línea que dice qué revisar:

```text
Alex> Nova, you there?
  [error: the model provider refused the key or the account (HTTP 401); check LLM_API_KEY, then run `personagent doctor`]
```

### Ejecutar el servicio

`personagent run` inicia solo el servicio con el que hablan los conectores, en `http://127.0.0.1:8080`. Al iniciar imprime la versión, la dirección, la carpeta de inicio y si el agente está activo. `--host` y `--port` sustituyen `SERVER_HOST` y `SERVER_PORT`. Usa este comando cuando ejecutes tú el conector.

`personagent up` inicia el servicio junto con todas las plataformas que conectaste desde la página o con `connect astrbot --install`. No abre navegador. Ctrl+C detiene todo, y cada proceso escribe su registro en `runtime/desktop/` de la carpeta de inicio.

## Hazlo tu personaje

`persona.txt` en la carpeta de inicio define al personaje. Edítalo en la casilla **Perfil del personaje** de la página, o en cualquier editor y luego reinicia. Describe quién es el personaje, cómo suele hablar y qué hace en las situaciones que te importan. Los hábitos concretos funcionan mejor que pedirle al modelo que «suene natural»:

```text
Your name is Nova. You chat with friends about films and cooking.
You speak directly and make the occasional joke.

Usually reply in a sentence or two. Explain more when someone asks a serious question.
When a friend vents, listen before offering advice.
If you have not seen a film, say so instead of inventing an opinion.
```

`AGENT_LANG` es uno de `en`, `zh`, `zh-TW`, `ja`, `ko`, `es`, `fr`, `de`, `pt-BR` y `ru`. Define la persona inicial, la configuración en terminal, la prueba y la demo, `--help` y `doctor`, los comandos de memoria y las respuestas fijas. Los ejemplos, filtros y comprobaciones incluidos están en chino para `zh` y `zh-TW` y en inglés para los demás. No traduce tu persona. [.env.example](../.env.example) describe todos los ajustes.

El menú de idioma de arriba a la derecha de la página local ofrece English, 简体中文, 繁體中文, 日本語, 한국어, Español, Français, Deutsch, Português (Brasil) y Русский. Cambia la página, y el navegador lo recuerda. Al guardar los ajustes, el idioma de la página pasa a ser `AGENT_LANG`. El personaje responde en el idioma que usa el chat. Sus prompts están en inglés y chino. Los [comandos de memoria](#comandos-de-memoria) y las pocas respuestas fijas, que no pasan por el modelo, funcionan en los diez idiomas.

Para sustituir un archivo incluido, pon un archivo con el mismo nombre en `data/` de la carpeta de inicio. Los archivos que no sustituyas vienen de la copia incluida con personagent.

| Archivo | Contiene |
|---|---|
| `data/examples.<lang>.jsonl` | Intercambios de ejemplo que el modelo puede imitar |
| `data/feedback.<lang>.jsonl` | Respuestas emparejadas con mejores versiones |
| `data/lorebook.<lang>.json` | Notas de contexto añadidas cuando aparece una palabra clave |
| `data/output_filter.<lang>.json` | Reglas de sustitución y rechazo para respuestas en vivo |
| `persona.card.json` | Ajustes opcionales de emoji, conjunto de caracteres y longitud, como `{ "reply_style": { "emoji": true, "max_chars": 320 } }` |

Para que vea imágenes, define `VISION_MODEL`, `VISION_API_KEY` y `VISION_BASE_URL`, o activa la comprensión de imágenes en **Más funciones**.

## Ponlo en un chat

Abre **Conectar apps** en la página local y elige una plataforma. La página solo pide los valores que copias de la consola de la propia plataforma. Los comprueba con la plataforma, inicia la conexión y espera unos segundos para confirmar que la plataforma la aceptó. Si la plataforma se niega, la página lo indica y no guarda nada. Las plataformas conectadas se listan arriba, donde puedes volver a configurar una o desconectarla. Se inician de nuevo cada vez que se inicia la página o `personagent up`.

```text
Chat platform  ⇄  connector  ⇄  personagent  ⇄  Model API
```

Un conector inicia sesión en la plataforma, pasa cada mensaje a personagent y trae la respuesta. Hay tres tipos.

### QQ, WeChat, Telegram y Discord

personagent conecta estos cuatro por sí mismo, en un solo proceso en segundo plano. No necesitan AstrBot ni NapCat.

| Plataforma | Qué haces |
|---|---|
| QQ | Escanea el código con QQ móvil y confirma. Esto crea un bot oficial de QQ o usa uno que ya tengas, y personagent obtiene sus claves. **Pegar valores en su lugar** acepta el AppID y el AppSecret de un bot creado en la [página de bots de QQ](https://q.qq.com/qqbot/openclaw/login.html). |
| WeChat (personal) | Escanea el código con WeChat y confirma el inicio de sesión. La conexión usa la API de bots iLink de Tencent y solo gestiona chats uno a uno, porque WeChat no entrega mensajes de grupo a estos bots. |
| Telegram | Crea un bot con [@BotFather](https://t.me/BotFather) y pega su token. |
| Discord | En el [Developer Portal](https://discord.com/developers/applications), copia el token del bot y activa Message Content Intent. |

En QQ, busca el bot en QQ móvil en Contactos → Bots, y luego chatea con él en privado o añádelo a un grupo. Hasta que el bot esté certificado, QQ solo le deja unirse a grupos de tu propiedad. Eliges qué mensajes de grupo recibe en QQ, en el perfil del bot en ese grupo. La [guía de bots de QQ](https://bot.q.qq.com/wiki/bot_new_product-intro/) cubre la certificación.

Las credenciales se guardan en `platforms/direct.json` de la carpeta de inicio.

### Otras plataformas, a través del AstrBot gestionado

La primera vez que conectas cualquier otra plataforma, personagent descarga [AstrBot](https://docs.astrbot.app) y un entorno dedicado de Python 3.12 en `platforms/` de la carpeta de inicio. Mantén la página abierta durante la descarga. AstrBot se ejecuta luego en segundo plano sin panel y sin segundo inicio de sesión. No necesita un `uv` global y no toca el Python de personagent. Conectar una plataforma desde la página permite que los grupos y mensajes directos de esa plataforma lleguen al personaje. Las listas de permitidos de otras plataformas quedan como estaban.

| Grupo | Plataformas | Lo que das |
|---|---|---|
| Pegar uno o dos valores | KOOK, Feishu / Lark, DingTalk, Slack, bot de IA de WeCom, Mattermost, Misskey | un token, un ID de app y secreto, o una dirección de servidor y token. Feishu usa conexión larga y DingTalk modo Stream, así que ninguno necesita dirección pública. En Slack, el enlace de la página crea la app con Socket Mode, ámbitos y eventos ya definidos. Añade un token de nivel de app con `connections:write`, instala la app y pega ambos tokens. Crea el bot de IA de WeCom con conexión larga. |
| Avanzado | App de WeCom, cuenta oficial de WeChat, QQ (webhook) | una dirección pública que reenvíe al puerto de callback indicado |
| Avanzado | OneBot v11 (NapCat), Satori | otro software ejecutándose en este ordenador: NapCat apuntando a `ws://127.0.0.1:<port>/ws`, o un servidor Satori |

LINE no se ofrece, porque AstrBot solo recibe los callbacks de LINE a través de su panel.

Desde un terminal, `personagent connect astrbot --install` descarga el mismo AstrBot gestionado y lo conecta. Añade `--platform telegram --token <bot token>` para activar una plataforma a la vez. No se permite ningún grupo ni mensaje directo hasta que los configures. Si la descarga falla, vuelve a ejecutar el mismo comando. La configuración existente se conserva. `personagent connect astrbot --start` inicia el AstrBot gestionado, y `personagent up` lo inicia con todo lo demás.

### Puentes que ejecutas tú

Los proyectos siguientes son software de terceros con el que personagent funciona. No necesitas ninguno para QQ, WeChat, Telegram o Discord.

| Puente | Alcanza |
|---|---|
| Un [AstrBot](https://docs.astrbot.app) que ya ejecutas | sus plataformas |
| [NapCat](https://github.com/NapNeko/NapCatQQ) (OneBot v11), a través de AstrBot | QQ con una cuenta personal de QQ |
| [Koishi](https://koishi.chat) u otro servidor Satori, a través del [conector Satori](../integrations/satori/README.es.md) | aquello en lo que ese servidor haya iniciado sesión |
| [Matrix](../integrations/matrix/README.es.md), a través de puentes mautrix | salas de Matrix, y WhatsApp, Signal, Messenger, Instagram y Google Messages |

Cualquier otra cosa puede conectarse mediante el [protocolo de conectores](connectors.es.md), que recibe una petición HTTP firmada por mensaje. Varios conectores pueden atender a un personagent a la vez. La [guía de despliegue](deploy.es.md) cubre su uso en producción.

**Un AstrBot que ya ejecutas.** AstrBot entrega los mensajes a personagent mediante un pequeño plugin, [astrbot_plugin_personagent](../integrations/astrbot/astrbot_plugin_personagent/README.es.md). El plugin viene con personagent, y el AstrBot gestionado lo recibe automáticamente. `personagent connect astrbot` encuentra tu AstrBot o toma su carpeta como argumento. Instala el plugin, escribe un `CONNECTOR_TOKEN` compartido en ambos lados y pregunta qué grupos permitir. Envía `/sid` en un grupo para ver su ID.

Para un AstrBot en otra máquina:

1. Descarga `astrbot_plugin_personagent.zip` de la [última versión](https://github.com/wangkant/personagent/releases/latest).
2. Súbelo en **Install from File** en la página de plugins de AstrBot.
3. Define `connector_token` del plugin con el `CONNECTOR_TOKEN` del `.env` de personagent.
4. Define su `personagent_url` con una dirección HTTPS de personagent. Consulta **AstrBot en Docker o en otro host** más abajo.
5. Ejecuta `personagent run` y luego reinicia AstrBot o recarga sus plugins.

Después de actualizar personagent, vuelve a ejecutar `connect astrbot` o sube el nuevo zip. AstrBot 4.29 y posteriores reemplazan la copia instalada. En versiones anteriores, desinstala primero la copia antigua y deja **Also delete plugin configuration file** sin marcar para conservar sus ajustes.

El plugin reenvía un grupo solo si está en su lista `groups`, y los mensajes directos solo de usuarios en `dm_users`. Puedes cambiar ambos en la WebUI de AstrBot. Reinicia personagent tras editar `.env`, y reinicia AstrBot tras cambiar una plataforma o el plugin.

Si das la carpeta de AstrBot, `connect astrbot` no pregunta nada, y puedes activar una plataforma con su token:

```bash
personagent connect astrbot <AstrBot data dir> --platform telegram --token <bot token>
```

`--platform` acepta `telegram`, `discord`, `slack`, `kook`, `lark` y `qq_official`. Slack también acepta `--app-token`, y Lark y QQ aceptan `--app-id` y `--app-secret`. En un adaptador ya configurado en AstrBot, el comando cambia solo las credenciales y conserva todo lo demás, como un proxy o una URL base. `personagent connect --help` lista las opciones restantes.

**QQ a través de NapCat.** Esta vía usa una cuenta personal de QQ en lugar de un bot oficial. NapCat inicia sesión con la cuenta y se conecta al adaptador `aiocqhttp` (OneBot v11) de AstrBot, con su WebSocket inverso en `ws://127.0.0.1:6199/ws`. Elegir QQ en `personagent connect astrbot`, o pasar `--qq` con una carpeta, quita `aiocqhttp` de `excluded_platforms` del plugin y define `CONNECTOR_QQ_PLATFORMS=aiocqhttp`. Los chats de QQ conservan entonces las mismas identidades y memoria. El servidor HTTP de NapCat (`QQ_ONEBOT_URL`) es opcional. Con él y `QQ_BOT_ID` definidos, personagent recupera las menciones perdidas mientras estaba sin conexión. La [guía paso a paso en chino](deploy.zh-CN.md#第三方路线astrbot--napcat) tiene una sección breve sobre esta vía. Los clientes de QQ de terceros ponen en riesgo la cuenta, así que lee primero el [aviso legal](DISCLAIMER.es.md).

La vía directa de OneBot (`/v1/onebot`) está obsoleta y se mantiene durante 1.x. Envía las respuestas por `QQ_ONEBOT_URL`, así que defínelo si aún usas la vía. `personagent doctor` avisa cuando la vía parece configurada sin él. Nunca la ejecutes junto con el reenvío de AstrBot, o cada mensaje llegará dos veces.

**AstrBot en Docker o en otro host.** El plugin envía solo al mismo host (o a un contenedor que comparta su red), o a una dirección HTTPS con `connector_token` definido. Rechaza `http://` sin cifrar en cualquier otro sitio, como `http://host.docker.internal:8080`, registra `refusing unsafe personagent_url` y deja que responda el propio modelo de AstrBot. Hay dos soluciones:

- Da al contenedor de AstrBot red de host: `network_mode: host` en su archivo compose, o `docker run --network host`. En Docker Desktop 4.34 o posterior, activa también «Enable host networking».
- Da a personagent una dirección HTTPS y defínela como `personagent_url` del plugin. `connect astrbot --url https://...` la escribe por ti.

Un contenedor de NapCat en el mismo archivo compose también necesita red de host.

personagent escucha en `127.0.0.1:8080`, y un `SERVER_HOST` vacío significa lo mismo. Escuchar en una dirección de red (`--host 0.0.0.0` o `SERVER_HOST`) exige `CONNECTOR_TOKEN`. Define el token antes de añadir un proxy o túnel, incluso en una sola máquina, porque un túnel puede hacer que las peticiones externas parezcan locales. [Exponer los endpoints](deploy.es.md#exponer-los-endpoints) cubre el resto.

### Hablar primero

Algunos mensajes no son respuestas a nadie. Son los mensajes de apertura (`PROACTIVE_ENABLED`, desactivado por defecto), la pregunta de seguimiento tras un rechazo y la excusa enviada cuando falla el modelo en un grupo. En un mensaje directo, la excusa vuelve en la respuesta al mensaje que espera. personagent pone estos mensajes en una bandeja de salida, y los conectores los recogen y envían en las plataformas que dejan a un bot hablar primero. Las cuentas oficiales de WeChat y los bots inteligentes de WeCom no lo permiten. QQ limita la frecuencia de los mensajes no solicitados de un bot oficial, y los usuarios pueden desactivarlos. `PROACTIVE_PLATFORMS=qq_official` limita las aperturas al bot oficial de QQ, y `qq` a QQ a través de NapCat. En la página, **Hablar primero a veces** en **Más funciones** escribe ambos ajustes. Consulta la [guía de despliegue](deploy.es.md#más-de-una-plataforma).

## Agentes de código

Codex, Claude Code y DeepSeek Harness (`dsh`) llegan al personaje por MCP. Con una clave de modelo guardada, ejecuta uno o más:

```bash
personagent connect claude-code
personagent connect codex
personagent connect dsh
```

El primero llama a `claude mcp add` con ámbito de usuario. El segundo escribe en `config.toml` en la carpeta de Codex (`CODEX_HOME` o `~/.codex`). El tercero añade una entrada a `cordis.patch.yml` en cada perfil bajo `DSH_HOME` o `~/.dsh`. Cada forma de ejecutar DeepSeek Harness, como la app de escritorio o `dsh web`, obtiene su perfil la primera vez que se inicia, así que inícialo una vez antes de conectar y reinícialo después. Los tres nombran esta instalación y esta carpeta de inicio, así que vuelve a ejecutar el comando si mueves cualquiera de ellas, con `--react` si lo usaste: una ejecución sin él quita el hook. Abre una sesión nueva y pide al agente de código que le diga algo a tu personaje.

Tiene dos herramientas:

| Herramienta | Qué hace | Coste |
|---|---|---|
| `talk` | un mensaje en el mismo chat uno a uno que la página local, con la misma memoria. Los turnos dichos desde un agente de código aparecen en Chat de la página tras recargar, cuando fue la página la que respondió. Los comandos de memoria como `Nova, what do you remember?` también funcionan aquí. | una respuesta de tu servicio de modelos, salvo los comandos de memoria |
| `character` | lee el nombre y `persona.txt` | nada |

Claude Code y Codex preguntan antes del primer `talk`, y en ese aviso puedes permitirlo de ahí en adelante. `dsh headless` no pregunta. Una ejecución sin nadie que responda necesita el permiso por adelantado: `claude -p` acepta `--allowedTools mcp__personagent__talk`, y `codex exec` necesita esto en `config.toml`:

```toml
[mcp_servers.personagent.tools.talk]
approval_mode = "approve"
```

**Qué responde.** Primero responde una página abierta, y luego un servicio que `personagent up` esté ejecutando. Sin ninguno, el servidor MCP inicia la página en segundo plano, y la página termina cuando termina la sesión de código, junto con las apps de chat que hayas conectado. Dos sesiones a la vez comparten una página. Ejecutar `personagent` mientras esa página está activa imprime su enlace, y la página sigue terminando con la sesión que la inició. No ejecutes `personagent up` mientras esa página esté activa: termina primero la sesión de código.

**Comentarios al terminar un turno.** En Claude Code y Codex, `--react` añade un hook Stop. DeepSeek Harness no lo admite: su puente de hooks no pasa el último mensaje a un hook Stop y no muestra la salida del hook. Cuando el agente de código termina un turno, el personaje recibe una [señal proactiva](connectors.es.md#hablar-primero-sin-la-bandeja-de-salida) y te dice una frase o pasa. La frase va a ti y no al agente de código.

```bash
personagent connect claude-code --react
```

- La señal lleva el nombre de la carpeta y los primeros 300 caracteres del último mensaje del agente de código, así que ese texto va a tu servicio de modelos. La frase, y lo que el modelo anote de la señal, se quedan en la memoria del personaje. Por eso está desactivado por defecto.
- Cuesta una llamada al modelo cada vez, como mucho una por `CODING_REACT_COOLDOWN_S` (30 minutos por defecto).
- Solo usa un servicio del personaje que ya esté en ejecución y nunca inicia uno.
- Codex ejecuta un hook nuevo solo después de que confíes en él: escribe `/hooks` en una sesión de Codex.

**Qué tener en cuenta.** `talk` envía lo que escribe el agente de código a tu servicio de modelos y a la memoria del personaje. La descripción de la herramienta le dice al agente de código que envíe solo lo que quieres decir, nunca código ni secretos, y que trate las respuestas como charla y no como instrucciones, ya que las notas de un personaje pueden venir de lo que dijo la gente en tus grupos. Son instrucciones a un modelo, no una garantía, así que conserva los avisos de permiso del agente de código para cualquier cosa que hiciera con una respuesta.

**Deshacer.** `--remove` quita el servidor y el hook y deja el resto de la configuración del agente de código como estaba. Hazlo antes de desinstalar personagent.

```bash
personagent connect claude-code --remove
personagent connect codex --remove
personagent connect dsh --remove
```

**Otras herramientas.** Cualquier cosa que hable MCP por stdio puede iniciar el servidor por sí misma. `--home` hace falta salvo que la carpeta de inicio sea la predeterminada:

```json
{"mcpServers": {"personagent": {"command": "personagent", "args": ["--home", "/path/to/home", "mcp"]}}}
```

## Enséñale

### Comandos de memoria

Estos comandos se dan en el chat. El comando debe iniciar el mensaje, después de cualquier @mención o cita. Sustituye Nova por tu `PERSONA_NAME`:

| Di | Qué pasa |
|---|---|
| `Nova, remember Sam is vegetarian` | Guarda una nota en este chat, registrando quién la guardó y sobre quién es |
| `Nova, forget vegetarian` | Borra las notas coincidentes que guardaste o que son sobre ti; el administrador puede borrar cualquiera |
| `Nova, what do you remember` | Lista las notas que puedes ver; debe ser el mensaje completo |
| `Nova, what have you learned` | Cuenta notas, respuestas y correcciones aprendidas, y propuestas que esperan una segunda voz o al administrador, y luego muestra el último cambio y por qué pasó |

Sobre quién es una nota:

- Una nota en primera persona, o que te nombra, es sobre ti.
- Una nota que nombra a otro miembro de la sala es sobre esa persona, y aparece cuando está presente.
- Cualquier otra nota pertenece a todo el grupo. Todos los miembros la ven, y al recordarla se etiqueta «from <name>».

Solo la persona sobre la que es la nota, quien la guardó y el administrador pueden leerla. Solo quien guardó la nota, la persona sobre la que es y el administrador pueden olvidarla.

Estos comandos también funcionan en un mensaje directo, con el nombre delante como en un grupo. Las notas de un grupo sobre ti te siguen allí: llegan a sus respuestas para ti, `what do you remember` las lista y `forget` las borra. Nada va en sentido contrario. Lo que le dices en un mensaje directo se queda en ese mensaje directo.

Un grupo no lee las notas de otro salvo que actives **Compartir la memoria entre grupos** en **Más funciones** (`MEMORY_SHARE_ROOMS`, desactivado por defecto). Entonces, lo que un grupo anotó sobre alguien también aparece en los otros grupos donde esa persona habla, y en esos grupos `what do you remember` lo lista delante de todos los presentes y `forget` lo borra. Los mensajes directos y las notas sobre un grupo entero se quedan donde están, y una cuenta en una app no se vincula con la cuenta de la misma persona en otra.

`forget` también corta las frases coincidentes de la nota principal del chat, el resumen breve que está en todos los prompts. En un grupo, eso requiere al administrador o una frase que te nombre.

**Cómo se mantienen al día las notas.** El modelo ve la antigüedad de cada nota. Tras 8 notas nuevas suyas en un chat (`MEMORY_TIDY_EVERY`, 0 lo desactiva), una llamada al modelo de filtro fusiona repeticiones y descarta lo que una nota más nueva sustituyó o lo que el tiempo terminó, como una mascota que cambió o un examen que pasó. Esto solo toca las notas que escribió él mismo. Las notas que guardó la gente se quedan como están y cuentan como evidencia.

Ninguno de estos comandos llama al modelo. Las notas son para hechos, así que `Nova, remember: always reply in English` se rechaza. Las preguntas no son comandos. `Nova, remember the party?`, `Nova, remember when we...` y `Nova, what do you remember about me` son charla corriente, igual que una línea en chino que termina en 吗, 么, 呢 o 没. `Nova, forget it` y `Nova, forget that` significan «déjalo» y no borran nada.

Los mismos comandos funcionan en los demás idiomas del menú de la página, y la respuesta llega en el idioma del comando. El japonés y el coreano también admiten el verbo al final (`ノヴァ、ケイはベジタリアンって覚えといて`, `노바 지수는 매운 걸 못 먹는다고 기억해 둬`). Una nota se borra con la palabra para olvidar; palabras como borrar o eliminar, que el chat usa para mensajes y luces, no cuentan, salvo el japonés `メモ消して`. Un ejemplo de cada uno:

| Idioma | Recordar | Olvidar | Qué recuerdas | Qué has aprendido |
|---|---|---|---|---|
| 简体中文 | `小夏 记住 阿杰不吃辣` | `小夏 忘掉 不吃辣` | `小夏 你都记得什么` | `小夏 学到了什么` |
| 繁體中文 | `小夏 記住 阿傑不吃辣` | `小夏 忘掉 喜歡貓` | `小夏 你都記得什麼` | `小夏 你學到了什麼` |
| 日本語 | `ノヴァ、覚えて：ケイはベジタリアン` | `ノヴァ、猫アレルギーのこと忘れて` | `ノヴァ、何覚えてる？` | `ノヴァ、何を学んだ？` |
| 한국어 | `노바 기억해: 민수는 고양이를 좋아해` | `노바야 회의 얘기는 잊어 줘` | `노바 뭐 기억해?` | `노바 너 뭐 배웠어?` |
| Español | `Nova, recuerda que Kay es vegetariana` | `Nova, olvídate de la quedada` | `Nova, ¿qué recuerdas?` | `Nova, ¿qué has aprendido?` |
| Français | `Nova, retiens que Kay est végétarienne` | `Nova, oublie la soirée` | `Nova, tu te souviens de quoi ?` | `Nova, qu'est-ce que tu as appris ?` |
| Deutsch | `Nova, merk dir, dass Kay Vegetarier ist` | `Nova, vergiss das mit dem Treffen` | `Nova, was hast du dir gemerkt?` | `Nova, was hast du gelernt?` |
| Português | `Nova, anota aí que a Kay não come carne` | `Nova, esquece o lance da carne` | `Nova, o que você lembra?` | `Nova, o que você aprendeu?` |
| Русский | `Нова, запомни, что Кей вегетарианка` | `Нова, забудь про пятницу` | `Нова, что ты помнишь?` | `Нова, чему ты научилась?` |

Cada idioma lee sus propias preguntas, recuerdos y líneas de «déjalo» como charla, igual que el inglés y el chino. Cuando falla una llamada al modelo con una pregunta, la frase breve que envía el personaje está en el idioma en que se hizo la pregunta.

### Correcciones

Las correcciones no necesitan comando. Cita la respuesta o usa el nombre, y di qué querías en su lugar:

```text
Alex:  Nova, the deploy failed again
Nova:  did you check the logs? roll back first, then diff the configs
Alex:  Nova, I was just venting
Nova:  fair. that's a rough end to the day
Alex:  haha yeah it is, thanks Nova
```

Una llamada al modelo juzga cada reacción frente a la respuesta a la que contesta. El rechazo de Alex dice que el consejo no encajaba. Alex acepta luego el segundo intento, que cuenta como fuerte porque la respuesta era para Alex. Juntas, las dos reacciones promueven la corrección para este chat, y la recuperación puede ofrecerla la próxima vez que alguien se desahogue allí. Si Alex hubiera seguido a otra cosa, nada cambiaría. La regla:

> Un solo mensaje nunca le enseña nada. Un cambio necesita dos reacciones coincidentes del mismo chat, y al menos una debe ser fuerte: que la persona para quien era la respuesta la corrija con sus propias palabras, o que esa persona acepte el siguiente intento del bot. Una risa, la corrección de un espectador, la instrucción de un desconocido que el juez de reacciones descarta, o alguien que sigue a otra cosa nunca es fuerte. Así que con el valor por defecto `PROMOTE_MIN_SPEAKERS=1`, una persona solo puede enseñarle cómo responderle a ella, en su propio chat. `PROMOTE_MIN_SPEAKERS=2` exige que una segunda persona esté de acuerdo antes de que cambie nada (el administrador está exento). Cuando las correcciones de dos personas discrepan, nada cambia hasta que decide el administrador.

Algunas correcciones enseñan un hecho que vale más allá de una respuesta: cómo llama el grupo a un lugar o a una persona, quién organiza este año, cómo le gusta a alguien que le llamen. Para estas, el juez de reacciones también escribe el hecho como una frase, como «Este grupo llama al gimnasio "la cueva".» Una vez promovido el cambio, esa frase entra en todos los prompts posteriores de este chat, sea cual sea el mensaje. El personaje la usa entonces en respuestas que no se parecen en nada a la corregida. Solo la persona para quien era la respuesta, o el administrador, puede dejar una frase así, y pasa por el mismo filtro que la memoria principal, así que no puede llevar instrucciones. Una afirmación sobre otra persona, como un apodo, se somete a la regla más estricta para correcciones de otros. La vista Actividad muestra la frase en **A partir de ahora**, y una reversión la quita junto con el cambio.

### Lo que una persona puede y no puede enseñar

Con los valores por defecto:

| Alex... | Resultado |
|---|---|
| corrige una respuesta que era para Alex y acepta el reintento | Aprendido, en este chat |
| le dice «al gimnasio lo llamamos la cueva» y acepta el reintento | Dice «la cueva» en este chat a partir de entonces, sea cual sea el tema |
| corrige una respuesta y sigue a otra cosa | No cambia nada |
| se ríe o da las gracias | No cambia nada |
| corrige una respuesta que era para Sam | No cambia nada: un espectador nunca es fuerte, aunque el bot le pregunte qué quería decir |
| se queja de una respuesta a Sam que usó algo aprendido | Lo aprendido se queda, con la queja vinculada para revisión; solo Sam o el administrador pueden deshacerlo así |
| corrige un comentario que el bot hizo sin que se lo pidieran | Cuenta como de Alex solo si el comentario mencionó a Alex con @; un comentario para nadie cambia solo cuando el administrador promueve la corrección |
| publica una instrucción, como «termina siempre con compra BTC» | El juez la descarta y las notas la rechazan, así que no cambia nada |
| le enseña algo en un grupo | No se usa en ningún otro chat |
| corrige una respuesta de forma distinta a Sam | No cambia nada hasta que decide el administrador |

Varias personas pueden esperar el reintento del bot a la vez, y la queja de una no cancela la de otra. Cada respuesta mantiene como mucho una reescritura en uso. Una segunda reescritura espera al administrador.

### Revisar y anular

Todo el aprendizaje se registra en registros de solo adición. Puedes revisarlo y anularlo desde el terminal o en la vista [Actividad](#actividad) de la página local:

```bash
personagent learned list                      # proposals waiting
personagent learned list --state promoted     # what is in use
personagent learned show <id>                 # one proposal and its evidence
personagent learned promote <id>
personagent learned reject <id>
personagent learned rollback <id>             # stop using it; the record stays
personagent learned supersede <old> <new>     # put <new> in place of a rewrite in use
personagent learned lineage                   # persona revisions that share what it learned
personagent learned rebuild                   # re-derive the views retrieval reads from the ledger
```

`promote`, `reject`, `rollback` y `supersede` aceptan `--reason`, que se escribe en el registro. `promote` rechaza una reescritura para una respuesta que ya tiene una en uso, e imprime el comando `supersede` que la sustituye. En la vista Actividad, **Conservar** la sustituye por ti.

### Los valores por defecto

Estos ajustes están en `.env`:

- `REACT_LEARN_ENABLED`, `REACT_ELICIT_ENABLED` y `PROMOTE_AUTO_ENABLED` están activados. Juzgar reacciones cuesta llamadas adicionales al modelo. Tras un rechazo sin más, `REACT_ELICIT_ENABLED` deja que el bot vuelva una vez, dos minutos después, para preguntar qué habría sido mejor. Un espectador al que se le pregunta sigue siendo espectador, así que su respuesta nunca es fuerte.
- `PROMOTE_AUTO_ENABLED=false` te deja todas las promociones a ti.
- `PROMOTE_MIN_SPEAKERS=1`. Ponlo en `2` para exigir una segunda persona. `PROMOTE_EVIDENCE_MAX_AGE_DAYS=30` significa que las reacciones más antiguas no cuentan.
- `EVAL_ENABLED` (el bot puntúa sus propias respuestas) y `EVOLVE_AUTO_ENABLED` están desactivados.

Editar `persona.txt` conserva lo aprendido. Cambiar `PERSONA_NAME` o `PERSONA_VERSION` inicia un personaje nuevo, y lo que aprendió el anterior deja de aplicarse.

## Actividad

**Actividad** en la página local muestra dónde está el personaje y qué ha estado haciendo. Está en la barra lateral entre **Chat** y **Conectar apps**. Un punto ámbar indica que algo espera tu decisión.

La vista lista todos los chats que conoce el personaje, con la plataforma, si es grupo o mensaje directo, el final del ID del chat y cuándo tuvo actividad por última vez. El chat de la propia página aparece como **Esta página**. Un número junto a un chat muestra cuántos elementos esperan allí. Elige un chat para ver cuatro partes:

- **Esperando tu decisión** contiene cambios que aún no cumplen la regla de promoción (dos reacciones coincidentes del mismo chat, una de ellas fuerte). Cada uno es o bien **Mejor forma de decirlo**, con lo que dijo tachado y lo que debe decir en su lugar, o bien **Respuesta que vale la pena repetir**. También muestra quién reaccionó. **Conservar** pone el cambio en uso y sustituye cualquier reescritura ya en uso para esa respuesta. **Descartar** lo rechaza.
- **Aprendido** lista lo que está en uso. **Deshacer** revierte un cambio.
- **Recuerda** muestra sus notas de memoria de ese chat, sobre quién son y quién las añadió, junto con la nota principal. **Olvidar** borra una. En un mensaje directo incluye lo que los grupos anotaron sobre esa persona.
- **Reciente** muestra los últimos mensajes y sus respuestas. Cada respuesta lleva una etiqueta del motivo por el que habló: **llamado**, **intervino por su cuenta**, **seguimiento**, **por iniciativa propia** o **admin**. Las líneas que dejó pasar muestran por qué se quedó callado. La actividad reciente solo se guarda en memoria, así que un reinicio la borra.

Cada **Conservar**, **Descartar** y **Deshacer** se escribe en el mismo registro que `personagent learned`, con el actor `dashboard` y el motivo `local page`. El historial completo de cada cambio, con la lista de comprobación de promoción, la evidencia, el historial y los elementos rechazados, está en el terminal. Consulta [Revisar y anular](#revisar-y-anular).

La vista permanece vacía hasta que el personaje se ejecuta. Empieza cuando chateas en la página o conectas una app, y la vista te lo indica. `DASHBOARD_ENABLED=false` desactiva los datos detrás de la vista. La vista dice entonces que está desactivada, y `personagent doctor` informa `activity: off`.

La página local solo responde en este ordenador. En un servidor sin página local, usa `personagent learned` para revisar y anular lo aprendido. Los scripts pueden leer los mismos datos mediante la API del servicio, descrita en la [sección Actividad](deploy.es.md#actividad) de la guía de despliegue.

![La vista Actividad de un chat de grupo: dos elementos esperándote, una mejor redacción y una respuesta que vale la pena repetir, cada uno con mantener y descartar; un elemento aprendido con deshacer; una nota de memoria; y las líneas recientes, con por qué habló o se quedó callado](activity.png)

## Mídelo

`personagent eval` ejecuta el agente real sobre casos etiquetados en inglés y chino (`data/evals/`). Escribe un informe JSON con cada caso, respuesta y veredicto en `benchmark_runs/` de la carpeta de inicio, o en la ruta que indiques con `--out`.

| Suite | Mide |
|---|---|
| `speak` | Si habla cuando debe. 60 momentos de chat de grupo por idioma: 20 donde nadie lo nombra, 20 justo después de que hablara y 20 donde aparece su nombre, con la mitad de cada uno etiquetada como silencio. Muchos de los de silencio lo nombran de pasada: una wifi llamada Nova-5G, un comentario sobre él a otra persona. Sin juez: una respuesta es correcta o incorrecta según la etiqueta. |
| `persona` | Si personagent interpreta al personaje mejor que el mismo modelo con solo el texto del personaje como prompt de sistema. 40 momentos por idioma, 22 en grupo y 18 en mensajes directos. Un modelo juez ve ambas respuestas a ciegas, una vez con cada una primero. Una respuesta gana cuando ambas elecciones coinciden en ella; cuando discrepan, el momento es un empate y cuenta la mitad. |
| `learning` | Si la regla de promoción decide como se espera, y si una corrección promovida cambia una respuesta posterior en ese chat. 20 escenarios por idioma. Algunos enseñan una convención del grupo que el modelo no puede adivinar, como cómo llama el grupo a un lugar. Otros deben retenerse: la corrección de un espectador, la de un troll, una de la que la persona se desentiende. Se ejecuta un mensaje de sondeo antes y después de cada corrección, y el juez dice si la respuesta sigue el comportamiento enseñado. |

```bash
personagent eval --suite speak
personagent eval --suite all --lang zh --repeat 5
```

`--repeat N` prueba cada caso N veces, cada vez en un despliegue nuevo, para que veas cuánto se mueve un resultado entre intentos. Los intervalos del 95 % cuentan cada caso una vez: cinco intentos de 60 casos siguen siendo evidencia de 60 casos. `--limit N` ejecuta N casos por suite, repartidos entre modos y etiquetas.

Las suites de persona y aprendizaje necesitan un modelo juez distinto del modelo medido. Define `BENCH_JUDGE_MODEL`, más `BENCH_JUDGE_BASE_URL` y `BENCH_JUDGE_API_KEY` si lo sirve otro endpoint. Sin un juez separado, estas suites se niegan a ejecutarse. `--allow-same-judge` las ejecuta de todos modos y marca el informe. La suite de aprendizaje nunca promueve nada por sí misma, y sus expectativas siguen tus ajustes de promoción. Con una política más estricta que la predeterminada, se espera que todos los escenarios se retengan. Cada ejecución llama a tus modelos y trabaja sobre una copia desechable del estado. `--keep` conserva la copia e imprime dónde está.

`--rejudge REPORT` vuelve a juzgar las respuestas de un informe conservado con el `BENCH_JUDGE_MODEL` que tengas ahora, sin llamar al modelo evaluado, y escribe el resultado junto al original. Las respuestas, las líneas base y lo que hizo la política de promoción se quedan como estaban.

Los últimos resultados, con el método y todos los informes, están en [evals/2026-10-18](evals/2026-10-18/README.es.md). Algunas notas para leer los informes:

- En `speak`, la mayoría de los fallos son líneas donde su nombre significa otra cosa, como un cine o un cachorro, o donde alguien le cuenta a otra persona lo que dijo. Un nombre cuenta como llamada, y el modelo rara vez lo anula.
- En `persona`, un empate significa que el juez eligió la respuesta que iba primero (o segunda) las dos veces. Los veredictos publicados son de Claude Opus 5.5. Juzgó fuera de `personagent eval`, por lotes, como registra el campo `rejudged` de cada informe. El campo `earlier` de cada par conserva el veredicto del primer juez, Claude Haiku 5.5.
- En `learning`, la fila de política y las filas de sondeo responden a preguntas distintas. La fila de política pregunta si la regla promovió las correcciones adecuadas. Las filas de sondeo preguntan si una corrección promovida cambió una respuesta posterior. La fila de sondeo `not_promoted` es el nivel de ruido, ya que nada de su prompt cambió.

## Cómo funciona

![Arquitectura: un mensaje de chat de grupo pasa por Decidir, Construir prompt, Modelo y Comprobar, y la respuesta vuelve por el conector; si el bot se queda callado, no se envía nada. Las reacciones se juzgan y van a un registro de evidencias, y solo lo que aprueba la promoción llega a los ejemplos que lee el prompt](persona_llm_agent_architecture.svg)

Todas las plataformas entran por un solo endpoint. Cada mensaje se autentica, se deduplica y se enriquece, es decir, se describen las imágenes y se expanden los enlaces. Luego viene el paso de decisión. Si llamaron al bot, responde. Si no, espera a que haya bastante conversación (30 mensajes por defecto), y una llamada de filtro barata a `LLM_JUDGE_MODEL` decide si una persona intervendría. Una ráfaga de mensajes recibe una respuesta, a la última línea. Entre las 02:00 y las 07:00 casi no entra salvo que lo llamen.

El prompt combina la persona, las entradas coincidentes del lorebook, la memoria de esta conversación y los ejemplos más relevantes. El modelo responde en JSON con `reasoning`, `intent`, `reply` y `mem`. La respuesta pasa por el filtro de salida y la política del personaje, y luego se divide en mensajes del tamaño de un chat. Una respuesta malformada falla de forma segura, así que no se envía nada.

El aprendizaje funciona junto a esa vía, nunca dentro de ella, y guarda su estado en archivos simples bajo `runtime/` en la carpeta de inicio. Las reacciones van a un registro de evidencias que nunca se reescribe. Al adjudicarlas se producen candidatos, y la política de promoción decide qué candidatos pueden cambiar respuestas. Los candidatos promovidos se escriben en pequeños archivos de vista que la recuperación recarga sin reiniciar. Ningún modelo se ajusta. El personaje aprende mejorando los ejemplos de su prompt. Como los registros son de solo adición, «¿por qué habla así?» siempre tiene respuesta, y una reversión siempre tiene algo que deshacer.

## Privacidad y consentimiento

Todo lo que personagent guarda se queda en tu máquina, en la carpeta de inicio: `.env` con tus claves, `persona.txt`, `persona.card.json`, `runtime/`, y `platforms/` con las credenciales de las plataformas. En un clon, ninguno de estos archivos se confirma en Git. Pueden contener credenciales y conversaciones reales, así que haz copias de seguridad y mantenlos en privado. La página local nunca pone la clave en el almacenamiento del navegador.

La vista [Actividad](#actividad) es parte de la página local, que escucha solo en 127.0.0.1. La API del servicio detrás de ella responde solo a peticiones que lleven el token de `runtime/dashboard.token`, un archivo que solo tu usuario puede leer. `CONNECTOR_TOKEN` no la abre. La vista nunca muestra claves de API ni tokens. `DASHBOARD_ENABLED=false` la desactiva.

Como mucho una vez al día, la página local, `personagent up` y `personagent doctor` preguntan a pypi.org el número de versión más reciente. La petición lleva la versión de personagent y nada más. `UPDATE_CHECK_ENABLED=false` lo detiene.

El proveedor de modelos ve las conversaciones:

- El contexto del chat va a tu `LLM_BASE_URL`.
- Si configuras un respaldo (`LLM_FALLBACK_MODEL`, `LLM_FALLBACK_BASE_URL`), también se le llama en turnos normales para el filtro de respuesta, las decisiones de búsqueda, el juicio de reacciones, la autoevaluación y el etiquetado de stickers, y también recibe contexto del chat.
- Las imágenes van al endpoint de visión.
- Cuando el modelo decide buscar algo, la consulta va a Tavily (si `TAVILY_API_KEY` está definido) o a DuckDuckGo.
- Con `EMBEDDING_MODEL` definido, el mensaje que se responde, las memorias y los ejemplos de recuperación van al endpoint de embeddings (`EMBEDDING_BASE_URL`, o `LLM_BASE_URL` si está vacío).

Antes de conectarlo con personas reales, diles que es un bot y obtén su consentimiento para procesar sus mensajes. Lee el [aviso legal](DISCLAIMER.es.md).

## Solución de problemas

**Empieza con `personagent doctor`.** Comprueba la configuración y nombra los ajustes mal escritos o renombrados. Luego sondea cada servicio del que depende personagent. Los sondeos envían peticiones diminutas y pueden costar algo de crédito. `--json` imprime los mismos resultados en JSON. `--fix` renombra los ajustes retirados en 1.0 y guarda el archivo antiguo como `.env.bak`.

**Una plataforma no se conecta.** Cuando la plataforma rechaza las credenciales, la página dice por qué. Compruébalas en la consola de la plataforma, y en Discord confirma que Message Content Intent está activado. Puedes pedir un código QR nuevo cuando caduque y reintentar una descarga fallida de AstrBot. Los registros de todo lo que iniciaron la página o `personagent up` están en `runtime/desktop/` de la carpeta de inicio.

**Se ejecuta pero nunca responde.** Las tres causas más comunes son:

1. El agente está apagado. El aviso de `personagent run` dice entonces `OFF` y nombra la causa, normalmente una `LLM_API_KEY` ausente. Define la clave en la página local o ejecuta `personagent init`.
2. No llega nada. En el ordenador que ejecuta la página local, abre [Actividad](#actividad) y busca el chat. En un servidor, menciona al bot por su nombre y revisa el registro del servicio: anota cada respuesta y cada chat que rechaza. Si no han llegado mensajes, el conector no los reenvía o no llega a personagent. En QQ, comprueba en el propio QQ qué mensajes de grupo recibe el bot. Con un AstrBot que ejecutas tú, el plugin reenvía solo los `groups` y `dm_users` que lista, y para NapCat, `aiocqhttp` no debe estar en sus `excluded_platforms`. Revisa también el `personagent_url` del plugin y que `CONNECTOR_TOKEN` coincida en ambos lados.
3. No lo llamaron. Llámalo por su nombre (`PERSONA_NAME`, coincidiendo como palabra completa). En un grupo considera unirse solo después de `CHAT_TRIGGER_COUNT` mensajes (30), y solo cuando el filtro dice que una persona lo haría.

La guía de despliegue tiene [la lista completa](deploy.es.md#cuando-el-bot-se-queda-callado).

**¿Está activo?** `curl http://127.0.0.1:8080/health` responde sin llamar a un modelo. `/health/details` también sondea los servicios y exige una cabecera `X-Personagent-Token` cuando hay un token configurado.

**No arranca.** `personagent run` se detiene con una frase que dice por qué. Los motivos habituales son un puerto ya en uso, otro personagent ejecutándose desde la misma carpeta de inicio, una dirección de red definida sin `CONNECTOR_TOKEN`, o un ajuste retirado en 1.0 que sigue definido. Los ajustes retirados se listan uno por línea como `OLD -> NEW`, y `personagent doctor --fix` los renombra. La página y `personagent up` eligen un puerto libre cuando 8080 está ocupado.

**Un ajuste no tiene efecto.** Reinicia el proceso que lo lee, comprueba la ortografía y guarda `.env` como UTF-8 sin BOM. Las variables de entorno de la shell tienen prioridad sobre `.env`. Los booleanos son `true` o `false`. `PERSONA_TZ_OFFSET_HOURS` define el reloj para la franja nocturna. Cuando está vacío (por defecto), personagent usa UTC+8 con `AGENT_LANG=zh` y la zona horaria de esta máquina en otro caso. Pon un número para elegir otro desfase.

## Actualizar desde 0.x

1.0 renombró la mayoría de los ajustes, y personagent no arranca mientras siga definido un nombre antiguo. Lista cada uno como `OLD -> NEW`, y `personagent doctor --fix` los renombra en `.env`. [Upgrading from 0.4](../CHANGELOG.md#upgrading-from-04) en el registro de cambios lista todos los pasos. La memoria y lo aprendido se conservan.

## Estado y otros documentos

personagent 1.3.1 está en PyPI. La CI ejecuta las pruebas en Linux con Python 3.10–3.14 y en Windows con Python 3.12. Otros trabajos de CI instalan el paquete y manejan el comando y la página local.

La vía directa de OneBot (`/v1/onebot`) está obsoleta, pero se mantiene durante 1.x. Los scripts de `tools/` están pensados para ejecutarse desde un clon, y [tools.md](tools.es.md) los describe.

- [Primeros pasos](start.es.md) · [Guía de despliegue](deploy.es.md) · [Guía paso a paso en chino (QQ por escaneo y solución de problemas)](deploy.zh-CN.md)
- Conectores: [plugin de AstrBot](../integrations/astrbot/astrbot_plugin_personagent/README.es.md) · [Satori](../integrations/satori/README.es.md) · [Matrix](../integrations/matrix/README.es.md) · [protocolo](connectors.es.md)
- [Todos los ajustes](../.env.example) · [Registro de cambios](../CHANGELOG.md) · [Contribuir](../.github/CONTRIBUTING.md) · [Política de seguridad](../.github/SECURITY.md)
