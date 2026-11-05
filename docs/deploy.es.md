# Desplegar personagent

[English](deploy.md) · [简体中文](deploy.zh-CN.md) · [繁體中文](deploy.zh-TW.md) · [日本語](deploy.ja.md) · [한국어](deploy.ko.md) · Español · [Français](deploy.fr.md) · [Deutsch](deploy.de.md) · [Português (Brasil)](deploy.pt-BR.md) · [Русский](deploy.ru.md)

El [inicio rápido](start.es.md) y la [guía de usuario](guide.md) te llevan hasta el primer chat. Cubren la instalación, la [carpeta de inicio](guide.md#install-and-the-home-folder), la configuración en la página local y la conexión de una plataforma. Esta guía cubre lo que necesita un despliegue real y qué revisar cuando el bot se queda callado.

## La configuración más corta que funciona

La página local (`personagent`, o `personagent init --terminal` para el asistente de terminal) comprueba la clave con una petición pequeña y escribe `.env` en la carpeta de inicio. Para chatear hace falta una clave, y `.env.example` te pone en los modelos gratuitos de OpenRouter:

```
LLM_API_KEY=...
LLM_BASE_URL=https://openrouter.ai/api/v1
LLM_MODEL=openrouter/free
```

Un `.env` que solo define la clave significa `https://api.deepseek.com` y `deepseek-flash`. Puedes apuntarlos a cualquier endpoint compatible con OpenAI, alojado o local (Ollama, llama.cpp). Pega la dirección de la API tal como la documenta el proveedor, ya sea una raíz o una base con versión como `.../v1` o `.../api/paas/v4`. Hasta que escribas un `persona.txt`, lo sustituye el `data/persona.example.<lang>.txt` incluido. Hasta que se defina `PERSONA_NAME` (la configuración lo define), el personaje se llama «bot».

La página también escribe `PERSONA_NAME`, `AGENT_LANG` y un `CONNECTOR_TOKEN`. Las plataformas conectadas desde la página no necesitan nada más en `.env`. Sus credenciales van a `<home>/platforms/`: `direct.json` guarda las plataformas que personagent conecta por sí mismo, y el AstrBot gestionado guarda el resto en su propia configuración. Añadidos opcionales:

```
ADMIN_IDS=telegram:12345             # the admin's accounts, <platform>:<id>
# QQ through NapCat (OneBot) only
QQ_BOT_ID=...                        # the bot account's number
CONNECTOR_QQ_PLATFORMS=aiocqhttp
```

Las claves se quedan en esta máquina. El proveedor de modelos que elijas ve las conversaciones. Todo lo demás de `.env.example` tiene un valor por defecto que funciona. `SERVER_HOST` y `SERVER_PORT` son `127.0.0.1:8080`, `QQ_ONEBOT_URL` está vacío (sin servidor HTTP de NapCat), y un `ACCESS_GROUPS` vacío deja todos los grupos al conector.

## Ejecutarlo

`personagent` abre la página local. Mientras la página está abierta, ejecuta el agente, el proceso que mantiene las plataformas conectadas directamente y el AstrBot gestionado si hay uno instalado. Volver a ejecutar `personagent` reutiliza una página abierta. `personagent up` inicia los mismos procesos sin navegador.

En ambos casos, esos procesos terminan con él, sea como sea que termine. Lo que haya dejado una ejecución anterior que falló se detiene en el siguiente inicio. Cada proceso escribe su registro en `<home>/runtime/desktop/` (`agent.log`, `direct.log`, `astrbot.log`).

La página local y `personagent up` preguntan a pypi.org como mucho una vez al día si hay un personagent más nuevo. Si lo hay, la vista Chat y el terminal muestran el comando que actualiza esta copia. La petición lleva solo el número de versión, y `UPDATE_CHECK_ENABLED=false` desactiva la comprobación.

`personagent run` inicia solo el agente, como describe [Ejecutar el servicio](guide.md#run-the-service). Úsalo cuando tus propios conectores (un AstrBot que ejecutas tú, Satori, Matrix) hablen con él. `personagent doctor` comprueba los ajustes y sondea todos los servicios externos.

**Ajustes renombrados en 1.0.** Mientras siga definido algún nombre de ajuste que 1.0 retiró, el inicio se niega con el código de salida 2 y lista cada uno como `OLD -> NEW`. `personagent doctor --fix` los renombra en `<home>/.env`. Conserva los valores y comentarios, guarda el archivo antiguo como `.env.bak` y comenta una línea antigua cuyo nombre nuevo ya esté definido. Un nombre retirado definido en el entorno y no en `.env` hay que renombrarlo donde esté definido. `personagent doctor` sale con 1 mientras quede alguno, y `--json` los lista en `retired_settings`. `HOST`, `PORT` y `LOG_FILE` solo cuentan cuando están escritos en `.env`.

### Actividad

[Actividad](guide.md#activity) es una vista de la página local. No necesita instalación adicional, no carga nada de internet y nunca muestra claves ni tokens. Lee la API JSON del servicio del agente que inició la página local. Con `personagent run` solo, lee el registro del servicio y usa `personagent learned` en su lugar. `DASHBOARD_ENABLED=false` desactiva la API. La vista entonces lo indica, y `personagent doctor` imprime `activity: off (...)`.

La API está bajo `/api/dashboard/` en el servicio del agente:

- `GET status`, `GET conversations` y `GET conversation?id=<chat id>` leen el estado del servicio, los chats que conoce y un chat en detalle.
- `POST candidates/<id>/promote`, `replace`, `reject` y `rollback` cambian lo que ha aprendido. Cada cambio va al mismo registro que `personagent learned`, con el actor `dashboard`.

Cada llamada necesita la cabecera `X-Personagent-Dashboard-Token` con el token de `dashboard.token` en la carpeta de ejecución (`<home>/runtime/` salvo que `AGENT_RUNTIME_DIR` la mueva). Solo el propietario puede leer el archivo, y el servicio lo crea al iniciarse. Una llamada sin la cabecera recibe 401 (`dashboard_token`), y un token incorrecto recibe 403 (`wrong_token`). `CONNECTOR_TOKEN` y `X-Personagent-Token` no la abren. Son solo para conectores y `/health/details`.

- Las escrituras también necesitan `X-Personagent-Dashboard: 1` y `Content-Type: application/json`. Si la petición envía un `Origin`, debe ser el del propio servicio.
- Se rechazan las peticiones de navegador entre sitios.
- Las respuestas sustituyen cada credencial por `***`. Las URL de las comprobaciones de inicio también ocultan el usuario, la contraseña y la consulta.
- Los scripts en el mismo ordenador pueden llamar a la API igual que la página local.

El servicio no sirve ninguna página. `GET /` responde con una nota breve que remite a la página local y a `personagent learned`, y eso es también lo que abre ahora un enlace antiguo con `?token=`. La página local solo se enlaza a 127.0.0.1. En un servidor sin página local, revisa y anula el aprendizaje con `personagent learned`.

## Lo que debe proporcionar el host

1. **Una carpeta de inicio con escritura.** El inicio toma un bloqueo en `<home>/.personagent.instance.lock`, fuera de `runtime/`. Una carpeta de inicio de solo lectura no arranca.
2. **Un proceso por carpeta de inicio.** Un segundo `personagent run` en la misma carpeta sale con una frase que lo dice.
3. **Un puerto libre.** Un puerto ocupado o prohibido también sale con una frase. Elige otro con `--port` o `SERVER_PORT`.

`AGENT_RUNTIME_DIR` debe resolverse dentro de la carpeta de inicio, o el inicio falla. Un `PERSONA_FILE` o `PERSONA_CARD_FILE` relativo también se resuelve dentro de ella, así que una persona guardada en otro sitio necesita una ruta absoluta.

## Conectar plataformas

Añade plataformas en **Conectar apps** en la página local. personagent comprueba las credenciales con la plataforma antes de guardar nada. Si la plataforma las rechaza, la página muestra el rechazo y no conserva nada.

**Conectadas por personagent mismo.** QQ, WeChat personal, Telegram y Discord se ejecutan en un solo proceso «direct», sin AstrBot ni NapCat.

| Plataforma | Qué haces | Límites |
|---|---|---|
| QQ (bot oficial) | Escanea un código QR con QQ móvil, que crea un bot o elige uno que hayas creado. Pegar el AppID y el AppSecret es la alternativa. | Hasta que el bot esté certificado, QQ solo le deja unirse a grupos de tu propiedad. Los permisos de mensajes de grupo se ajustan en QQ. |
| WeChat personal | Escanea con WeChat (la API de bots iLink de Tencent). | Solo chats uno a uno. WeChat no da mensajes de grupo a estos bots. |
| Telegram | Pega el token de @BotFather. | |
| Discord | Pega el token del bot, con Message Content Intent activado. | |

**A través del AstrBot gestionado.** Todas las demás plataformas pasan por un AstrBot que personagent descarga, junto con su propio entorno Python 3.12, y ejecuta sin interfaz. No tiene panel y no necesita un segundo inicio de sesión. KOOK, Feishu/Lark (conexión larga), DingTalk (modo Stream), Slack (Socket Mode, y el enlace de la guía rellena la app), bot de IA de WeCom (conexión larga), Mattermost y Misskey piden uno o dos valores. El grupo Avanzado necesita una dirección pública u otro software: aplicación de WeCom, cuenta oficial de WeChat, webhook de QQ, OneBot v11 (NapCat) y Satori. LINE no se ofrece.

En ambas vías, una plataforma conectada responde a todos los grupos y mensajes directos que la plataforma entrega al bot. Eso cambia en cuanto `ACCESS_GROUPS` o `ACCESS_DM_USERS` incluye una entrada para esa plataforma (consulta [las listas de permitidos de personagent](#a-través-de-un-astrbot-que-ya-ejecutas)). Los ID llegan como `<platform>:<id>`, por ejemplo `qq_official:<openid>`, `weixin_oc:<id>`, `telegram:<id>` y `discord:<id>`. El bot oficial de QQ ve openids, no números de QQ. Conectar una plataforma directamente elimina la conexión de AstrBot de esa misma plataforma.

## A través de un AstrBot que ya ejecutas

AstrBot, NapCat (OneBot), Koishi (a través del [conector Satori](../integrations/satori/README.md)) y Matrix (a través del [conector Matrix](../integrations/matrix/README.md) y puentes mautrix) son puentes de terceros con los que personagent funciona. Ninguno hace falta para QQ, WeChat, Telegram ni Discord.

AstrBot entrega los mensajes a personagent mediante un plugin en `integrations/astrbot/astrbot_plugin_personagent/`. El plugin envía cada mensaje a `POST /v1/events` y retransmite las respuestas que recibe. También recoge la bandeja de salida de personagent (`outbox_enabled`, activado por defecto), así que la persona puede hablar primero donde la plataforma se lo permita a un bot. El README del plugin tiene la tabla. El AstrBot gestionado recibe el plugin automáticamente. Para tu propio AstrBot, inícialo una vez para que cree su carpeta de datos (la que contiene `cmd_config.json`, `plugins/` y `config/`) y luego ejecuta:

```
personagent connect astrbot                       # asks, and finds AstrBot's folder itself
personagent connect astrbot <AstrBot data dir>    # asks nothing
```

El comando copia el plugin a `<data dir>/plugins/` y escribe un mismo `CONNECTOR_TOKEN` en `.env` y en la configuración del plugin. Define `personagent_url` como `http://127.0.0.1:<SERVER_PORT>` salvo que el plugin ya tenga una URL que acepte (una URL de bucle local, incluidos túneles, o HTTPS).

Para un AstrBot en otra máquina, descarga `astrbot_plugin_personagent.zip` de la [última versión](https://github.com/wangkant/personagent/releases/latest) y súbelo en **Install from File** en la página de plugins de AstrBot. Define su `connector_token` con el `CONNECTOR_TOKEN` del `.env` de personagent, y `personagent_url` con una dirección HTTPS de personagent (consulta [Exponer los endpoints](#exponer-los-endpoints)).

Después de actualizar personagent, vuelve a ejecutar `connect astrbot` o sube el nuevo zip. AstrBot 4.29 y posteriores reemplazan la copia instalada. En versiones anteriores, desinstálalo primero y deja **Also delete plugin configuration file** sin marcar.

Opciones de `connect astrbot`:

- `--qq` saca `aiocqhttp` de `excluded_platforms`, y `--no-qq` lo vuelve a poner. Sin ninguno, el enrutamiento de QQ queda como está. `CONNECTOR_QQ_PLATFORMS` sigue lo que termine haciendo el plugin.
- `--platform qq_official|telegram|discord|slack|kook|lark --token <token>` también activa ese adaptador en la configuración de AstrBot. Slack también acepta `--app-token`, y Lark y QQ aceptan `--app-id` y `--app-secret`. Una entrada de adaptador que ya existe conserva sus otros ajustes (proxy, URL base, sondeo) y solo recibe las credenciales nuevas.
- `--url https://...` define una dirección HTTPS a la que envía el plugin.
- `--install` descarga en su lugar un AstrBot gestionado, y `--start` lo inicia.

La primera ejecución deja vacías las listas de permitidos. Una nueva ejecución las conserva, junto con otras plataformas excluidas.

El plugin niega por defecto. Rellena `groups`, y `dm_users` para mensajes directos, en la WebUI de AstrBot, o responde a las preguntas de `connect`. Los mensajes directos se reenvían cuando `dm_users` no está vacío. El [README del plugin](../integrations/astrbot/astrbot_plugin_personagent/README.md) lista todas las claves. El AstrBot gestionado abre cada plataforma que conectas con `<platform>:*`. Después de instalar el plugin, reinicia AstrBot o recarga los plugins en su WebUI. En el lado de personagent:

- `CONNECTOR_TOKEN` autentica cada petición. La petición lleva la cabecera `X-Personagent-Token` más un HMAC-SHA256, con el token como clave, sobre `timestamp.nonce.body`, y un guardián antirrepetición rechaza los nonces reutilizados. Una petición capturada no se puede reenviar ni alterar. El token también es la clave de firma, así que mantenlo fuera de los registros y cámbialo si se filtra. Es opcional en un solo host y obligatorio entre hosts.
- `ADMIN_IDS` lista las cuentas del administrador como `<platform>:<id>` (`telegram:12345`, `discord:4242`). Un ID solo o `qq:<id>` es un número de QQ. `ADMIN_NAME` define el nombre del administrador. Todas las cuentas listadas pertenecen a una sola persona, que recibe la persona más cercana en grupos y mensajes directos, puede gestionar lo que el bot recuerda sobre un grupo y puede enseñarle por sí sola. A través de AstrBot, la plataforma es el nombre de adaptador que muestra AstrBot, y `/sid` en un chat muestra un ID.
- `ACCESS_GROUPS` y `ACCESS_DM_USERS` permiten que personagent restrinja una plataforma por sí mismo, con la misma forma `<platform>:<id>`. Cada plataforma se restringe por separado. Una plataforma sin entradas se deja al conector, y una sola entrada restringe esa plataforma a sus entradas. Un turno que personagent rechaza vuelve sin reclamar, así que puede responderlo el propio modelo de AstrBot.

Para AstrBot en Docker o en otro host, consulta [la guía de usuario](guide.md#bridges-you-run-yourself).

### QQ a través de NapCat (OneBot)

Esta vía usa una cuenta personal de QQ en lugar de un bot oficial. Necesitas una segunda cuenta de QQ en los grupos de destino, no la tuya (consulta [DISCLAIMER.md](DISCLAIMER.es.md)). Inicia sesión, normalmente con código QR y en una sesión que sobrevive a los reinicios, en una implementación de OneBot v11 conectada al adaptador `aiocqhttp` de AstrBot. [NapCat](https://github.com/NapNeko/NapCatQQ) está probado y se acopla al cliente de escritorio QQ NT. LLOneBot y Lagrange son otras implementaciones de OneBot v11.

En el AstrBot gestionado, añade **Avanzado > OneBot v11 (NapCat)** en la página local y apunta NapCat a `ws://127.0.0.1:6199/ws`. La [guía en chino](deploy.zh-CN.md) lo explica paso a paso. Con tu propio AstrBot, quita `aiocqhttp` de `excluded_platforms` del plugin, define `CONNECTOR_QQ_PLATFORMS=aiocqhttp` (`--qq` hace ambas cosas) y define `QQ_BOT_ID` (`personagent connect astrbot` lo pregunta).

**Aquí `CONNECTOR_QQ_PLATFORMS` es obligatorio.** Sin él, los ID de QQ llegan con espacio de nombres (`aiocqhttp:123456`) y todas las conversaciones parecen nuevas. La memoria, el historial y los ejemplos aprendidos usan como clave el ID sin prefijo, y los registros derivan los ID de fila del ID de conversación, así que la división no se puede reparar después.

Los ID sin prefijo llevan autoridad de QQ, así que las entradas de QQ de `ADMIN_IDS`, `ACCESS_GROUPS` y `ACCESS_DM_USERS` se aplican además de las listas de permitidos del plugin. Un mensaje directo de QQ debe estar en `dm_users` *y* venir del administrador o de una entrada de `ACCESS_DM_USERS`. Cuando `ACCESS_GROUPS` incluye grupos de QQ, un grupo de QQ debe estar en ambas. Pon una plataforma en `CONNECTOR_QQ_PLATFORMS` solo si confías esa autoridad a su conector.

**El servidor HTTP de NapCat** (`QQ_ONEBOT_URL`, vacío por defecto) es opcional en esta vía. personagent también envía mensajes por iniciativa propia:

- mensajes proactivos (`PROACTIVE_ENABLED`, desactivado por defecto);
- la pregunta que hace dos minutos después de un rechazo (`REACT_ELICIT_ENABLED`);
- la excusa enviada a un grupo cuando falla la llamada al modelo.

Estos vuelven por la bandeja de salida del plugin mientras el plugin la esté recogiendo. Si no, van a `QQ_ONEBOT_URL` si la URL está definida. Solo el barrido de @menciones perdidas sin conexión necesita el servidor, junto con `QQ_BOT_ID`. El barrido se ejecuta al inicio y luego cada 30 minutos. Cubre los grupos de QQ de `ACCESS_GROUPS` más cualquier grupo con actividad desde el último reinicio, y reproduce las @menciones de menos de una hora. Con la URL vacía, `personagent doctor` muestra el puente OneBot como "not configured".

**Lo que se pierde en todas las vías de conector** (directa, AstrBot u otro conector), sin ningún ajuste que lo recupere:

- el OCR de respaldo para imágenes que ningún modelo de visión describió;
- la búsqueda de citas a través de NapCat. Las citas se resuelven con el índice propio de personagent de mensajes recientes y con el texto citado que un conector envía con la cita;
- la recogida de stickers nuevos a partir de imágenes publicadas en grupos.

## Más de una plataforma

Varios conectores pueden funcionar a la vez contra un mismo personagent, porque cada uno nombra su plataforma (`telegram:-1001234`, `matrix:!room:example.org`). El proceso direct, AstrBot, Satori y Matrix pueden ejecutarse todos a la vez. No metas un mismo chat por dos conectores, o cada mensaje llegará dos veces. Los ID con espacio de nombres nunca chocan con un número de QQ sin prefijo.

Los mensajes que nadie pidió llegan a una plataforma mediante un conector que recoge la bandeja de salida de personagent. Son los mensajes proactivos, la pregunta tras un rechazo y la excusa cuando falla la llamada al modelo en un grupo. La excusa de un mensaje directo vuelve en la respuesta a la petición que trajo el mensaje.

El proceso direct y los tres conectores de aquí recogen la bandeja de salida, en las plataformas donde un bot puede escribir primero. QQ limita la frecuencia de los mensajes no solicitados de un bot oficial, y una persona puede desactivarlos. Un conector tuyo envía `connector_id`, `reply_handle` y `"capabilities": ["outbox"]` con sus eventos y hace sondeo largo a `/v1/outbox` (consulta [el protocolo de conectores](connectors.es.md)). Sin un conector así, personagent solo habla dentro de la petición que trajo un mensaje. Los bucles proactivos omiten esas conversaciones, y la pregunta y la excusa no se envían.

`PROACTIVE_PLATFORMS` limita dónde puede hablar primero el bucle proactivo. `PROACTIVE_PLATFORMS=qq_official` lo mantiene en el bot oficial de QQ, y `qq` en QQ a través de NapCat. `CONNECTOR_OUTBOX_ENABLED=false` desactiva por completo la bandeja de salida.

Para hablar primero en un mensaje directo sin la bandeja de salida, tu propio planificador (una tarea de plugin de AstrBot, una entrada de cron) puede enviar un evento de mensaje directo marcado con `"proactive": true`. Consulta [Hablar primero sin la bandeja de salida](connectors.es.md#hablar-primero-sin-la-bandeja-de-salida).

## Exponer los endpoints

Mantén `SERVER_HOST=127.0.0.1` cuando el conector y personagent compartan máquina. Un contenedor cuenta como la misma máquina solo con el espacio de nombres de red del host o con red de host. La página local y `personagent up` siempre se enlazan a `127.0.0.1`. En otro caso:

1. Define `SERVER_HOST=0.0.0.0` (o `--host 0.0.0.0`) y `CONNECTOR_TOKEN`. El inicio rechaza un enlace de red sin el token. No exige `QQ_ONEBOT_SECRET`, pero sin él el obsoleto `/v1/onebot` está desactivado en un enlace de red. Toda petición a él recibe 403 `onebot_disabled`, y el registro indica el motivo una vez.
2. Pon delante un proxy inverso HTTPS o un túnel privado. Todos los conectores de aquí envían solo al bucle local o a HTTPS con token definido. El plugin de AstrBot registra cualquier otra cosa como `refusing unsafe personagent_url`, y los conectores Satori y Matrix se niegan a iniciar.
3. Mantén el cuerpo intacto byte a byte, porque la firma lo cubre, y mantén los relojes a menos de cinco minutos entre sí.

Con una credencial vacía, su endpoint atiende solo a programas locales que llaman directamente a `http://127.0.0.1` o `http://localhost`. Una petición recibe 403 `non_local_request` si tiene alguno de estos elementos:

- una cabecera `Origin`;
- un `Sec-Fetch-Site` distinto de `none`;
- un `Host` distinto de `localhost`, `127.0.0.1` o `::1`;
- una cabecera de proxy: `X-Forwarded-For`, `Forwarded`, `X-Real-IP`, `CF-Connecting-IP`, `Via`, `X-Forwarded-Host`, `X-Forwarded-Proto`, `X-Forwarded-Port`, `True-Client-IP`, `X-Client-IP` o `X-Original-Forwarded-For`.

Un proxy en el mismo host que no añada ninguna de estas sigue pareciendo local. Define `CONNECTOR_TOKEN` (y `QQ_ONEBOT_SECRET` si usas `/v1/onebot`) antes de añadir cualquier proxy o túnel, incluso en un solo host.

## Endpoints de salud

- `GET /health` es gratuito y abierto, y no llama a nada.
- `GET /health/details` sondea los servicios externos (en caché 60 s). Con `CONNECTOR_TOKEN` vacío, solo responde a peticiones locales. Con un token definido, responde **solo** a peticiones con una cabecera `X-Personagent-Token` que coincida, incluso desde el bucle local. Devuelve 503 cuando un sondeo crítico falla o no puede ejecutarse. Los sondeos críticos son los modelos de chat y, cuando QQ usa la entrada directa de OneBot (`QQ_BOT_ID` y `QQ_ONEBOT_URL` definidos, `CONNECTOR_QQ_PLATFORMS` sin definir), el puente OneBot.
- `personagent doctor [--json]` ejecuta los mismos sondeos más la comprobación de ajustes, y sale con un valor distinto de cero en el mismo caso. Cuando la última comprobación de actualizaciones tiene un día, también pregunta a pypi.org por la versión más reciente (`UPDATE_CHECK_ENABLED=false` lo omite).

## Costes

- **Los sondeos gastan crédito.** `personagent doctor` y `/health/details` envían una compleción de chat diminuta a cada endpoint de modelo configurado (chat, mensaje directo, evaluación y visión). También envían un embedding si `EMBEDDING_MODEL` está definido y una búsqueda de Tavily si `TAVILY_API_KEY` está definido. `/health` y las comprobaciones de ajustes y registros son gratuitos.
- **Los scripts de `tools/`** varían. Algunos son gratuitos y otros llaman a un modelo. La tabla de [tools.md](tools.es.md) indica cuáles.
- **`personagent eval`** llama al modelo en cada caso. Las suites de persona y aprendizaje también necesitan un segundo modelo como juez (`BENCH_JUDGE_MODEL`).
- **Memoria.** Pasadas 256 conversaciones con espacio de nombres (no QQ), la inactiva con menos actividad reciente pierde su historial reciente y sus reacciones pendientes. Los recuerdos a largo plazo, las notas principales y los registros se quedan. Una conversación en medio de una petición nunca se expulsa. Los recuerdos a largo plazo se cargan del disco al iniciar y este límite no los afecta.
- **Disco.** El registro de evidencias y el registro de candidatos en `runtime/` solo se amplían y nunca se truncan. `personagent doctor` avisa si alguno pasa de 50 MB (`LEDGER_EVIDENCE_WARN_BYTES`, `LEDGER_CANDIDATES_WARN_BYTES`). Haz copia de seguridad de `runtime/`, porque guarda todo lo que el bot ha aprendido.

## Cuando el bot se queda callado

Las causas están ordenadas de más a menos comunes. Cuando la página local ejecuta el agente, [Actividad](guide.md#activity) muestra si llegan mensajes y por qué se quedó callado. En un servidor, lee el registro del servicio y usa `personagent learned` para lo aprendido.

1. **No le llega nada.** En la página local, comprueba que la plataforma aparece como conectada y lee `runtime/desktop/direct.log` o `astrbot.log`. El bot oficial de QQ debe estar en el grupo, y QQ decide qué mensajes de grupo recibe. Un bot de WeChat personal nunca recibe grupos. En un AstrBot que ejecutas tú, rellena `groups` del plugin (y `dm_users` para mensajes directos), y para NapCat saca `aiocqhttp` de `excluded_platforms`. Los conectores Satori y Matrix tienen sus propias listas de permitidos en su `.env`. Consulta sus README. En este caso el chat nunca aparece en Actividad.
2. **El agente está apagado.** El aviso de `personagent run` dice `agent: OFF`, con el motivo y la solución. Sin `LLM_API_KEY`, añade una clave en la página local (o define `LLM_API_KEY`) y reinicia. Con `AGENT_ENABLED=false`, ponlo en `true` en `<home>/.env` y reinicia. Hasta entonces, cada evento recibe `owned: false`, y el primero registra una sola línea ERROR con el mismo consejo.
3. **Responde el propio modelo de AstrBot.** El plugin recurrió a él porque la petición falló, personagent rechazó el mensaje (punto 5) o el agente está apagado (punto 2). El registro de AstrBot muestra `refusing unsafe personagent_url`, `agent refused the request (403): <message>` (u otro estado, consulta la tabla de abajo) o `timed out waiting for the agent`. `timeout_s` debe cubrir el debounce y todas las llamadas al modelo del turno, así que mantén `LLM_TIMEOUT_S × (1 + LLM_MAX_RETRIES)` por debajo. Su valor por defecto (420) cubre los valores por defecto del agente (120 × 3 = 360 s). Súbelo cuando subas esos dos.
4. **No lo llamaron.** En un grupo responde a su nombre (`PERSONA_NAME`) o a una @. Si no, espera a que haya bastante conversación (`CHAT_TRIGGER_COUNT`, 30 mensajes por defecto) y aun así puede pasar. De 02:00 a 07:00 en su zona horaria, casi no entra en chats donde no lo llamaron. La zona horaria es `PERSONA_TZ_OFFSET_HOURS`. Vacía, es UTC+8 cuando `AGENT_LANG` es `zh` o `zh-TW`, y si no, la de esta máquina. Actividad muestra el motivo de cada turno reciente. Para ver la misma decisión sin conexión, ejecuta `personagent chat --trigger 4`.
5. **Las listas de permitidos de personagent.** `ACCESS_GROUPS` y `ACCESS_DM_USERS` se aplican en todas las vías, y un mensaje directo de QQ con ID sin prefijo también necesita al administrador o una entrada. Un mensaje que rechazan vuelve sin reclamar, así que a través de AstrBot puede responderlo su propio modelo. personagent registra cada conversación rechazada una vez, en INFO, con el ajuste que la rechazó.
6. **La llamada al modelo falla.** Una clave rechazada (401 o 403) o un saldo vacío (402 o cuota agotada) registra una línea ERROR que nombra el host del proveedor y el ajuste que hay que corregir. Ejecuta `personagent doctor`. Envía una petición diminuta a cada endpoint de modelo y muestra el estado, lo que también detecta un `LLM_BASE_URL` o `LLM_MODEL` incorrecto. Mientras el modelo está caído, la persona envía una excusa breve en personaje cuando la llaman, como mucho una vez por conversación cada cinco minutos.
7. **Un ajuste mal escrito.** El registro de inicio y `personagent doctor` listan cada clave que `.env.example` no conoce y cualquier valor que empiece por `#`.
8. **Un BOM en `.env`.** El nombre del primer ajuste lleva el BOM y nunca llega al proceso. El inicio y `personagent doctor` lo informan. Vuelve a guardar el archivo como UTF-8 sin BOM.
9. **`QQ_BOT_ID` sin definir o incorrecto con NapCat.** A través de AstrBot las @menciones siguen funcionando, pero el barrido de menciones perdidas se basa en él. En la entrada directa de OneBot una @mención nunca se reconoce. El bot arranca sin problemas, no registra nada y nunca responde. `personagent doctor` avisa cuando `QQ_BOT_ID` está vacío y hay otros ajustes de QQ definidos. El bot oficial de QQ no lo usa.
10. **Responde, pero ha olvidado lo que aprendió.** O bien NapCat QQ llega sin `CONNECTOR_QQ_PLATFORMS=aiocqhttp`, o bien cambió `PERSONA_NAME` o `PERSONA_VERSION`, lo que inicia un personaje nuevo. El registro avisa cuando se rechaza en bloque el material promovido del personaje anterior. Editar `persona.txt`, también en la casilla Perfil del personaje de la página, no inicia un personaje nuevo. Sus revisiones bajo un mismo `PERSONA_VERSION` comparten un ámbito de aprendizaje (`runtime/persona_lineage.json`). Para incorporar filas aprendidas bajo un hash de persona que el linaje no incluye, ejecuta `personagent learned lineage adopt <hash>` y luego `personagent learned rebuild`. El hash está en el ámbito del candidato en `personagent learned show <id>`. Pasar `AGENT_LANG` del chino a otro idioma o al revés también cambia a los otros archivos aprendidos de `runtime/`.

Los errores de `/v1/events` se listan a continuación. El plugin de AstrBot registra el mensaje, y `code` es el campo estable sobre el que un cliente puede bifurcar.

| Estado | `code` | Mensaje en el registro de AstrBot | Causa |
|---|---|---|---|
| 403 | `unauthenticated` | authentication required | no hay `CONNECTOR_TOKEN` y quien llama no está en esta máquina |
| 403 | `non_local_request` | no credential is configured; only local requests accepted | no hay `CONNECTOR_TOKEN` y la petición vino a través de un navegador, un proxy u otro nombre de host |
| 403 | `invalid_envelope` | invalid, stale, or replayed request envelope | token, cabeceras o firma ausentes o incorrectos, relojes separados más de 5 min, un nonce reutilizado o un guardián antirrepetición lleno (`connector replay guard full` en el registro del agente) |
| 403 | `stale_event` | stale or invalid sent_at | `sent_at` difiere de ahora en más de `CONNECTOR_MAX_EVENT_AGE_S` (24 h), incluidas marcas de tiempo futuras o en milisegundos |
| 400 | `invalid_schema` | invalid event schema | falta un campo obligatorio: `platform`, `conversation_type`, `sender_id`, `message_id`, `sent_at` y `conversation_id` para grupos |
| 400 | `client_disconnected` | client disconnected | quien llama colgó durante el envío |
| 408 | `body_timeout` | request body not received in time | el cuerpo tardó más de 30 s en llegar |
| 413 | `body_too_large` | request body too large | supera `SERVER_MAX_BODY_BYTES` (8 MB), normalmente una imagen en línea |
| 429 | `capacity_exceeded` | webhook capacity exceeded | supera `CONNECTOR_MAX_INFLIGHT` turnos en curso; reintenta tras 3 s |

## Heredado: la entrada directa de OneBot

El webhook de NapCat aún puede enviar eventos a `POST /v1/onebot`, y personagent responde a través de `QQ_ONEBOT_URL`. Esta ruta está obsoleta y se mantiene durante 1.x. Usa en su lugar la conexión del bot oficial de QQ, o NapCat a través de AstrBot con `CONNECTOR_QQ_PLATFORMS=aiocqhttp`. La ruta avisa una vez en el primer uso y marca cada respuesta con `Deprecation: true`.

Para pasar a NapCat a través de AstrBot, añade OneBot v11 (NapCat) en la página local, o ejecuta `personagent connect astrbot <AstrBot data dir> --qq` para tu propio AstrBot y rellena las listas de permitidos. Apunta el cliente WebSocket de NapCat allí y desactiva el cliente HTTP de NapCat (conserva su servidor HTTP). La memoria y el aprendizaje se mantienen, porque `CONNECTOR_QQ_PLATFORMS` conserva los ID.

Si todavía usas la ruta heredada:

- Configura ambos sentidos como describe la [documentación de NapCat](https://napneko.github.io/). Necesitas un **servidor HTTP** en `QQ_ONEBOT_URL` para enviar y un **cliente HTTP** que envíe a `http://127.0.0.1:8080/v1/onebot` (`SERVER_HOST`, `SERVER_PORT`). `QQ_ONEBOT_URL` está vacío por defecto, así que escríbelo en `.env`. Sin él, el bot recibe pero nunca responde. La comprobación previa y `personagent doctor` avisan cuando esta ruta parece configurada (`QQ_BOT_ID` o `QQ_ONEBOT_SECRET` definidos, `CONNECTOR_QQ_PLATFORMS` vacío) y `QQ_ONEBOT_URL` está vacío.
- Si NapCat está en otra máquina, define `QQ_ONEBOT_SECRET` con el `secret` del cliente HTTP. Si no, cualquiera que llegue al puerto puede falsificar eventos. Entonces los cuerpos deben llevar `x-signature: sha1=<hex>` (403 `bad_signature`), y los eventos con una marca de tiempo desviada más de cinco minutos reciben 403 `stale_event`. Sin el secreto, la ruta responde solo a programas en este host, y en un enlace de red está desactivada (403 `onebot_disabled`).
- Con AstrBot en la misma cuenta, deja `aiocqhttp` en `excluded_platforms`, o cada mensaje llegará dos veces.

Comprueba el envío con `curl http://127.0.0.1:3000/get_login_info`. Comprueba la recepción mirando el registro de personagent mientras escribes al bot en un grupo.
