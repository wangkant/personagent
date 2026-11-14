# Desplegar personagent

[English](deploy.md) · [简体中文](deploy.zh-CN.md) · [繁體中文](deploy.zh-TW.md) · [日本語](deploy.ja.md) · [한국어](deploy.ko.md) · Español · [Français](deploy.fr.md) · [Deutsch](deploy.de.md) · [Português (Brasil)](deploy.pt-BR.md) · [Русский](deploy.ru.md)

Los [primeros pasos](start.es.md) y la [guía de usuario](guide.es.md) le guían hasta el primer chat. Describen la instalación, la [carpeta de inicio](guide.es.md#instalación-y-carpeta-de-inicio), la configuración en la página local y la conexión de una plataforma. Esta guía describe lo que requiere un despliegue real y qué revisar cuando el bot deja de responder.

## La configuración mínima que funciona

La página local (`personagent`, o `personagent init --terminal` para el asistente de terminal) comprueba la clave con una pequeña solicitud y escribe `.env` en la carpeta de inicio. Para chatear se necesita una clave, y `.env.example` selecciona los modelos gratuitos de OpenRouter:

```
LLM_API_KEY=...
LLM_BASE_URL=https://openrouter.ai/api/v1
LLM_MODEL=openrouter/free
```

Un `.env` que solo define la clave equivale a `https://api.deepseek.com` y `deepseek-flash`. Puede apuntar estos valores a cualquier endpoint compatible con OpenAI, alojado o local (Ollama, llama.cpp). Pegue la dirección de la API tal como la documenta el proveedor, ya sea una raíz o una base con versión como `.../v1` o `.../api/paas/v4`. Hasta que escriba un `persona.txt`, se utiliza en su lugar el `data/persona.example.<lang>.txt` incluido. Hasta que se defina `PERSONA_NAME` (la configuración lo define), el personaje se llama «bot».

La página también escribe `PERSONA_NAME`, `AGENT_LANG` y un `CONNECTOR_TOKEN`. Las plataformas conectadas desde la página no requieren nada más en `.env`. Sus credenciales se guardan en `<home>/platforms/`: `direct.json` guarda las plataformas que personagent conecta por sí mismo, y el AstrBot gestionado guarda las demás en su propia configuración. Ajustes adicionales opcionales:

```
ADMIN_IDS=telegram:12345             # the admin's accounts, <platform>:<id>
# QQ through NapCat (OneBot) only
QQ_BOT_ID=...                        # the bot account's number
CONNECTOR_QQ_PLATFORMS=aiocqhttp
```

Las claves permanecen en este equipo. El proveedor de modelos que elija ve las conversaciones. Todo lo demás de `.env.example` tiene un valor predeterminado que funciona. `SERVER_HOST` y `SERVER_PORT` son `127.0.0.1:8080`, `QQ_ONEBOT_URL` está vacío (sin servidor HTTP de NapCat), y un `ACCESS_GROUPS` vacío deja el filtrado de todos los grupos al conector.

## Ejecutarlo

`personagent` abre la página local. Mientras la página está abierta, ejecuta el agente, el proceso que mantiene las plataformas conectadas directamente y el AstrBot gestionado, si hay uno instalado. Al volver a ejecutar `personagent`, se reutiliza una página abierta. `personagent up` inicia los mismos procesos sin navegador.

En ambos casos, esos procesos finalizan con él, independientemente de cómo finalice. Lo que haya dejado una ejecución anterior que falló se detiene en el siguiente inicio. Cada proceso escribe su registro en `<home>/runtime/desktop/` (`agent.log`, `direct.log`, `astrbot.log`).

La página local y `personagent up` consultan a pypi.org como máximo una vez al día si hay una versión más reciente de personagent. Si la hay, la vista Chat y el terminal muestran el comando que actualiza esta copia. La solicitud solo incluye el número de versión, y `UPDATE_CHECK_ENABLED=false` desactiva la comprobación.

`personagent run` inicia únicamente el agente, como se describe en [Ejecutar el servicio](guide.es.md#ejecutar-el-servicio). Utilícelo cuando sus propios conectores (un AstrBot que ejecute usted, Satori, Matrix) se comuniquen con él. `personagent doctor` comprueba los ajustes y sondea todos los servicios externos.

**Ajustes con nombre cambiado en la versión 1.0.** Mientras siga definido algún nombre de ajuste que la versión 1.0 retiró, el inicio se interrumpe con el código de salida 2 y enumera cada uno como `OLD -> NEW`. `personagent doctor --fix` les cambia el nombre en `<home>/.env`. Conserva los valores y los comentarios, guarda el archivo anterior como `.env.bak` y convierte en comentario una línea antigua cuyo nombre nuevo ya esté definido. Un nombre retirado que esté definido en el entorno y no en `.env` debe cambiarse allí donde esté definido. `personagent doctor` finaliza con el código 1 mientras quede alguno, y `--json` los enumera en `retired_settings`. `HOST`, `PORT` y `LOG_FILE` solo se tienen en cuenta cuando están escritos en `.env`.

### Actividad

[Actividad](guide.es.md#actividad) es una vista de la página local. No requiere ninguna instalación adicional, no carga nada de internet y nunca muestra claves ni tokens. Lee la API JSON del servicio del agente que inició la página local. Si solo se utiliza `personagent run`, lea el registro del servicio y utilice `personagent learned` y `personagent memory` en su lugar. `DASHBOARD_ENABLED=false` desactiva la API. En ese caso, la vista lo indica, y `personagent doctor` imprime `activity: off (...)`.

La API se encuentra en `/api/dashboard/`, en el servicio del agente:

- `GET conversations` y `GET conversation?id=<chat id>` leen los chats que conoce el servicio y un chat en detalle. Cada chat de `conversations` incluye `learned`, `observing` (el número de elementos en observación) y `latest` (cuándo entró algo en uso por última vez). `conversation` devuelve las listas `learned` y `observing`. Un elemento en observación incluye `standing` (su etapa, lo que todavía le falta, el motivo del personaje y la fecha en la que se apartará); un elemento en uso incluye `by` (`reactions`, `character` o `person`) y `why`. También devuelve lo que recuerda el chat: `memories`, `core_note` y `core_at`, `thread`, `episodes`, `removed` y `memory_status`.
- `POST candidates/<id>/promote`, `replace`, `reject`, `rollback` y `restore` son las acciones opcionales de una persona sobre lo que ha aprendido. Cada una se escribe en el mismo registro que `personagent learned`, con el actor `dashboard`. `restore` recupera lo que apartaron el personaje o el límite de tiempo, y lo que el personaje o una regla retiraron del uso; lo que una persona deshizo o apartó, y lo que descartó una regla de contenido, sigue como está. `promote` no recupera un elemento que se ha deshecho.
- `POST memory/forget` con el cuerpo `{"conv": "<chat id>", "kind": "note", "id": "<id>"}` olvida un elemento y responde con el `tid` que acepta `POST memory/restore` (`{"tid": "<tid>"}`) para recuperarlo. `kind` es `note`, `episode`, `thread` o `core`. El cuerpo anterior `{"conv": "<chat id>", "note": "<note id>"}` sigue funcionando y, sin `note`, olvida la nota principal del chat.
- `POST memory/forget_chat` con `{"conv": "<chat id>"}` olvida todo lo que recuerda ese chat. No se puede deshacer.
- `GET memory/list?conv=<chat id>` enumera lo que recuerda cada chat y lo que todavía puede restaurarse; `personagent memory` lo lee mientras el servicio está en ejecución.

Cada llamada requiere la cabecera `X-Personagent-Dashboard-Token` con el token de `dashboard.token` en la carpeta de ejecución (`<home>/runtime/`, salvo que `AGENT_RUNTIME_DIR` la cambie de ubicación). Solo el propietario puede leer el archivo, y el servicio lo crea al iniciarse. Una llamada sin la cabecera recibe 401 (`dashboard_token`), y un token incorrecto recibe 403 (`wrong_token`). `CONNECTOR_TOKEN` y `X-Personagent-Token` no dan acceso a ella. Se utilizan únicamente para los conectores y `/health/details`.

- Las escrituras también requieren `X-Personagent-Dashboard: 1` y `Content-Type: application/json`. Si la solicitud envía un `Origin`, debe ser el del propio servicio.
- Se rechazan las solicitudes de navegador entre sitios.
- Las respuestas sustituyen cada credencial por `***`. Las URL de las comprobaciones de inicio también ocultan el usuario, la contraseña y la consulta.
- Los scripts del mismo equipo pueden llamar a la API de la misma forma que la página local.

El servicio no sirve ninguna página. `GET /` responde con una nota breve que remite a la página local y a `personagent learned`, y eso es también lo que abre ahora un enlace antiguo con `?token=`. La página local solo se enlaza a 127.0.0.1. En un servidor sin página local, `personagent learned` muestra lo que ha aprendido el personaje, lo que está observando y por qué, y le permite poner un elemento en uso, apartarlo, deshacerlo o recuperar lo que apartaron el personaje o el límite de tiempo y lo que el personaje o una regla retiraron del uso. `personagent memory` enumera lo que recuerda y olvida o restaura un elemento.

## Requisitos del host

1. **Una carpeta de inicio con permisos de escritura.** El inicio establece un bloqueo en `<home>/.personagent.instance.lock`, fuera de `runtime/`. Una carpeta de inicio de solo lectura impide el inicio.
2. **Un proceso por carpeta de inicio.** Un segundo `personagent run` en la misma carpeta finaliza con una frase que lo indica.
3. **Un puerto libre.** Un puerto ocupado o prohibido también provoca la finalización con una frase. Elija otro con `--port` o `SERVER_PORT`.

`AGENT_RUNTIME_DIR` debe resolverse dentro de la carpeta de inicio; de lo contrario, el inicio falla. Un `PERSONA_FILE` o `PERSONA_CARD_FILE` relativo también se resuelve dentro de ella, por lo que un perfil guardado en otra ubicación requiere una ruta absoluta.

Un `memory.json`, `core_memory.json` o `episodes.json` dañado detiene el inicio con el código de salida 2 y una frase que indica el archivo y la copia `.bak` que debe ponerse en su lugar. El archivo dañado no se modifica.

## Conectar plataformas

Añada plataformas en **Conectar plataformas**, en la página local. personagent comprueba las credenciales con la plataforma antes de guardar nada. Si la plataforma las rechaza, la página muestra el rechazo y no conserva nada.

En un servidor sin pantalla, conecte las plataformas que personagent conecta por sí mismo desde un terminal con `personagent connect <plataforma>`, por ejemplo `personagent connect telegram`. El comando realiza los mismos pasos y comprobaciones que la página y guarda los valores en el mismo formato. QQ y WeChat muestran su código QR en el terminal, y Twitch muestra un enlace y un código. Con `--no-input` y todos los valores indicados como opciones, no formula ninguna pregunta y finaliza con el código 2 si falta un valor obligatorio. A continuación, `personagent up` inicia personagent con las plataformas conectadas. La guía de usuario describe [el comando y sus opciones](guide.es.md#conectar-una-plataforma-en-el-terminal).

**Conectadas por el propio personagent.** QQ, WeChat personal, Telegram, Discord, Matrix, Twitch, IRC, Zulip, VK y Stoat se ejecutan en un único proceso «direct», sin AstrBot ni NapCat. Si una plataforma no puede cargarse, se omite y las demás se inician igualmente. La tabla recoge las cuatro primeras; la guía de usuario indica [qué requieren las otras seis y cuáles son sus limitaciones](guide.es.md#plataformas-que-personagent-conecta-por-sí-mismo).

| Plataforma | Qué debe hacer | Límites |
|---|---|---|
| QQ (bot oficial) | Escanee un código QR con QQ para móvil, que crea un bot o selecciona uno que usted haya creado. La alternativa es pegar el AppID y el AppSecret. | Hasta que el bot esté certificado, QQ solo le permite unirse a grupos de los que usted sea propietario. En un grupo solo recibe los mensajes que lo mencionan con @, salvo que el propietario del grupo active la recepción de todos los mensajes en el perfil del bot en ese grupo; hasta entonces no puede intervenir por iniciativa propia. |
| WeChat personal | Escanee con WeChat (la API de bots iLink de Tencent). | Solo chats individuales. WeChat no entrega mensajes de grupo a estos bots. |
| Telegram | Pegue el token de @BotFather. | |
| Discord | Pegue el token del bot, con Message Content Intent activado. | |

**A través del AstrBot gestionado.** Todas las demás plataformas utilizan un AstrBot que personagent descarga, junto con su propio entorno de Python 3.12, y ejecuta sin interfaz. No tiene panel y no requiere un segundo inicio de sesión. KOOK, Feishu/Lark (conexión persistente), DingTalk (modo Stream), Slack (Socket Mode; el enlace de la guía rellena la configuración de la aplicación), bot de IA de WeCom (conexión persistente), Mattermost y Misskey solicitan uno o dos valores. El grupo Avanzado requiere una dirección pública u otro software: aplicación de WeCom, cuenta oficial de WeChat, webhook de QQ, OneBot v11 (NapCat) y Satori. LINE no está disponible.

En ambas vías, una plataforma conectada responde en todos los grupos y mensajes directos que la plataforma entrega al bot. Para limitarlo, utilice **Responder solo en estos grupos** en la página (consulte [Mantenerlo bajo control](#mantenerlo-bajo-control)). La página lo guarda como `ACCESS_GROUPS`, y `ACCESS_DM_USERS` hace lo mismo con los mensajes privados; en cuanto cualquiera de los dos incluye una entrada para una plataforma, esa plataforma queda limitada a sus entradas (consulte [las listas de permitidos de personagent](#a-través-de-un-astrbot-propio)). Los ID llegan como `<platform>:<id>`, por ejemplo `qq_official:<openid>`, `weixin_oc:<id>`, `telegram:<id>` y `discord:<id>`. El bot oficial de QQ ve openids, no números de QQ. Conectar una plataforma directamente elimina la conexión de AstrBot de esa misma plataforma.

## Mantenerlo bajo control

Todo lo siguiente se hace en la página local. Los ajustes están en **Personaje y ajustes** → **Ajustes avanzados** y se aplican al seleccionar **Guardar**.

- **Hacerse administrador.** Envíe un mensaje privado al personaje y, en **Administrador y acceso**, seleccione **Elegir entre los chats recientes** y después **Soy yo** junto a su cuenta. Es la forma de hacerlo con el bot oficial de QQ, que ve un openid en lugar de su número de QQ.
- **Responder solo en algunos grupos.** En la misma lista, marque **Responder en este grupo** en cada grupo que quiera conservar, o introduzca los ID en **Responder solo en estos grupos**. En cuanto figura un grupo de una plataforma, el personaje deja de responder en los demás grupos de esa plataforma.
- **Pausar todas las respuestas.** Desactive **Responder a los mensajes** en **Otros ajustes**. El personaje sigue conectado, pero no responde a nada hasta que lo vuelva a activar.
- **Deshacer algo que aprendió.** En **Actividad**, elija el chat y seleccione **Deshacer** junto al elemento, o ejecute `personagent learned rollback <id>`.
- **Retirarlo de un grupo.** Expulse el bot desde la propia plataforma. Desconectarlo en **Conectar plataformas** solo termina la conexión de personagent; el bot sigue siendo miembro de sus grupos.
- **Si lo expulsan o lo restringen.** Un grupo que expulsó al bot simplemente deja de enviarle mensajes, y no hay nada que reconectar. Si la plataforma bloquea el bot o lo desactiva, la conexión de una plataforma que personagent conecta por sí mismo se detiene y **Conectar plataformas** muestra el motivo.

## A través de un AstrBot propio

AstrBot, NapCat (OneBot), Koishi (a través del [conector de Satori](../integrations/satori/README.es.md)) y Matrix (a través del [conector de Matrix](../integrations/matrix/README.es.md) y de puentes mautrix) son puentes de terceros con los que personagent funciona. Ninguno es necesario para las plataformas que personagent conecta por sí mismo.

AstrBot entrega los mensajes a personagent mediante un complemento ubicado en `integrations/astrbot/astrbot_plugin_personagent/`. El complemento envía cada mensaje a `POST /v1/events` y retransmite las respuestas que recibe. También recoge la bandeja de salida de personagent (`outbox_enabled`, activado de forma predeterminada), por lo que el personaje puede hablar primero donde la plataforma lo permita a un bot. El README del complemento incluye la tabla. El AstrBot gestionado recibe el complemento automáticamente. Para su propio AstrBot, inícielo una vez para que cree su carpeta de datos (la que contiene `cmd_config.json`, `plugins/` y `config/`) y, a continuación, ejecute:

```
personagent connect astrbot                       # asks, and finds AstrBot's folder itself
personagent connect astrbot <AstrBot data dir>    # asks nothing
```

El comando copia el complemento en `<data dir>/plugins/` y escribe un mismo `CONNECTOR_TOKEN` en `.env` y en la configuración del complemento. Define `personagent_url` como `http://127.0.0.1:<SERVER_PORT>`, salvo que el complemento ya tenga una URL que acepte (una URL de bucle local, incluidos los túneles, o HTTPS).

Para un AstrBot en otro equipo, descargue `astrbot_plugin_personagent.zip` de la [última versión](https://github.com/wangkant/personagent/releases/latest) y súbalo en **Install from File**, en la página de complementos de AstrBot. Defina su `connector_token` con el `CONNECTOR_TOKEN` del `.env` de personagent, y `personagent_url` con una dirección HTTPS de personagent (consulte [Exponer los endpoints](#exponer-los-endpoints)).

Después de actualizar personagent, vuelva a ejecutar `connect astrbot` o suba el nuevo zip. AstrBot 4.29 y las versiones posteriores sustituyen la copia instalada. En versiones anteriores, desinstálelo primero y deje **Also delete plugin configuration file** sin marcar.

Opciones de `connect astrbot`:

- `--qq` quita `aiocqhttp` de `excluded_platforms`, y `--no-qq` lo vuelve a añadir. Sin ninguna de las dos, el enrutamiento de QQ se mantiene sin cambios. `CONNECTOR_QQ_PLATFORMS` se ajusta según la configuración resultante del complemento.
- `--platform qq_official|telegram|discord|slack|kook|lark --token <token>` también activa ese adaptador en la configuración de AstrBot. Slack también acepta `--app-token`, y Lark y QQ aceptan `--app-id` y `--app-secret`. Una entrada de adaptador ya existente conserva sus demás ajustes (proxy, URL base, sondeo) y solo recibe las credenciales nuevas.
- `--url https://...` define una dirección HTTPS a la que envía el complemento.
- `--install` descarga en su lugar un AstrBot gestionado, y `--start` lo inicia.

La primera ejecución deja vacías las listas de permitidos. Una nueva ejecución las conserva, junto con las demás plataformas excluidas.

El complemento deniega de forma predeterminada. Rellene `groups`, y `dm_users` para los mensajes directos, en la WebUI de AstrBot, o responda a las preguntas de `connect`. Los mensajes directos se reenvían cuando `dm_users` no está vacío. El [README del complemento](../integrations/astrbot/astrbot_plugin_personagent/README.es.md) enumera todas las claves. El AstrBot gestionado abre cada plataforma que usted conecta con `<platform>:*`. Después de instalar el complemento, reinicie AstrBot o vuelva a cargar los complementos en su WebUI. En el lado de personagent:

- `CONNECTOR_TOKEN` autentica cada solicitud. La solicitud incluye la cabecera `X-Personagent-Token` y un HMAC-SHA256, con el token como clave, sobre `timestamp.nonce.body`, y un mecanismo antirrepetición rechaza los nonces reutilizados. Una solicitud interceptada no puede reenviarse ni alterarse. El token es también la clave de firma, por lo que debe mantenerlo fuera de los registros y cambiarlo si se filtra. Es opcional en un único host y obligatorio entre hosts.
- `ADMIN_IDS` enumera las cuentas del administrador como `<platform>:<id>` (`telegram:12345`, `discord:4242`). Un ID sin prefijo o `qq:<id>` es un número de QQ. `ADMIN_NAME` define el nombre del administrador. Todas las cuentas enumeradas pertenecen a una sola persona, con la que el personaje mantiene un trato más cercano en grupos y mensajes directos, que puede gestionar lo que el bot recuerda sobre un grupo y que puede enseñarle por sí sola. A través de AstrBot, la plataforma es el nombre de adaptador que muestra AstrBot, y `/sid` en un chat muestra un ID.
- `ACCESS_GROUPS` y `ACCESS_DM_USERS` permiten que personagent restrinja una plataforma por sí mismo, con el mismo formato `<platform>:<id>`. Cada plataforma se restringe por separado. Una plataforma sin entradas se deja al conector, y una sola entrada restringe esa plataforma a sus entradas. Un turno que personagent rechaza se devuelve sin reclamar, por lo que puede responderlo el propio modelo de AstrBot.

Para AstrBot en Docker o en otro host, consulte [la guía de usuario](guide.es.md#puentes-que-ejecuta-usted).

### QQ a través de NapCat (OneBot)

Esta vía utiliza una cuenta personal de QQ en lugar de un bot oficial. Necesita una segunda cuenta de QQ en los grupos de destino, no la suya (consulte [DISCLAIMER.md](DISCLAIMER.es.md)). Esta cuenta inicia sesión, normalmente con un código QR y en una sesión que persiste tras los reinicios, en una implementación de OneBot v11 conectada al adaptador `aiocqhttp` de AstrBot. [NapCat](https://github.com/NapNeko/NapCatQQ) está probado y se acopla al cliente de escritorio QQ NT. LLOneBot y Lagrange son otras implementaciones de OneBot v11.

En el AstrBot gestionado, añada **Avanzado > OneBot v11 (NapCat)** en la página local y apunte NapCat a `ws://127.0.0.1:6199/ws`. La [guía en chino](deploy.zh-CN.md) lo explica paso a paso. Con su propio AstrBot, quite `aiocqhttp` de `excluded_platforms` del complemento, defina `CONNECTOR_QQ_PLATFORMS=aiocqhttp` (`--qq` hace ambas cosas) y defina `QQ_BOT_ID` (`personagent connect astrbot` lo solicita).

**Aquí `CONNECTOR_QQ_PLATFORMS` es obligatorio.** Sin él, los ID de QQ llegan con espacio de nombres (`aiocqhttp:123456`) y todas las conversaciones parecen nuevas. La memoria, el historial y los ejemplos aprendidos utilizan como clave el ID sin prefijo, y los registros derivan los ID de fila del ID de conversación, por lo que la división no puede repararse posteriormente.

Los ID sin prefijo conllevan la autoridad de QQ, por lo que las entradas de QQ de `ADMIN_IDS`, `ACCESS_GROUPS` y `ACCESS_DM_USERS` se aplican además de las listas de permitidos del complemento. Un mensaje directo de QQ debe figurar en `dm_users` *y* proceder del administrador o de una entrada de `ACCESS_DM_USERS`. Cuando `ACCESS_GROUPS` incluye grupos de QQ, un grupo de QQ debe figurar en ambas listas. Añada una plataforma a `CONNECTOR_QQ_PLATFORMS` solo si confía esa autoridad a su conector.

**El servidor HTTP de NapCat** (`QQ_ONEBOT_URL`, vacío de forma predeterminada) es opcional en esta vía. personagent también envía mensajes por iniciativa propia:

- mensajes proactivos (`PROACTIVE_ENABLED`, desactivado de forma predeterminada);
- la pregunta que formula dos minutos después de un rechazo (`REACT_ELICIT_ENABLED`);
- la disculpa que se envía a un grupo cuando falla la llamada al modelo.

Estos mensajes se devuelven a través de la bandeja de salida del complemento mientras el complemento la esté recogiendo. En caso contrario, se envían a `QQ_ONEBOT_URL` si la URL está definida. Solo la recuperación de @menciones perdidas durante la desconexión requiere el servidor, junto con `QQ_BOT_ID`. La recuperación se ejecuta al inicio y, después, cada 30 minutos. Abarca los grupos de QQ de `ACCESS_GROUPS` y cualquier grupo con actividad desde el último reinicio, y reproduce las @menciones de menos de una hora de antigüedad. Con la URL vacía, `personagent doctor` muestra el puente OneBot como "not configured".

**Funciones que se pierden en todas las vías de conector** (directa, AstrBot u otro conector), sin ningún ajuste que permita recuperarlas:

- el OCR de respaldo para imágenes que ningún modelo de visión ha descrito;
- la búsqueda de citas a través de NapCat. Las citas se resuelven con el índice propio de personagent de mensajes recientes y con el texto citado que un conector envía con la cita.

Los stickers nuevos se recopilan en todas las vías, como en QQ: a partir de imágenes publicadas en grupos que llegan incrustadas en el mensaje o marcadas como stickers. Una foto que un conector envía solo como enlace no se recopila.

## Más de una plataforma

Varios conectores pueden funcionar a la vez con un mismo personagent, porque cada uno indica el nombre de su plataforma (`telegram:-1001234`, `matrix:!room:example.org`). El proceso direct, AstrBot, Satori y Matrix pueden ejecutarse simultáneamente. No conecte un mismo chat a través de dos conectores, ya que cada mensaje llegaría dos veces. Los ID con espacio de nombres nunca coinciden con un número de QQ sin prefijo.

Los mensajes no solicitados llegan a una plataforma mediante un conector que recoge la bandeja de salida de personagent. Son los mensajes proactivos, la pregunta tras un rechazo y la disculpa que se envía cuando falla la llamada al modelo en un grupo. La disculpa de un mensaje directo se devuelve en la respuesta a la solicitud que contenía el mensaje.

El proceso direct y los tres conectores incluidos recogen la bandeja de salida, en las plataformas en las que un bot puede escribir primero. QQ limita la frecuencia de los mensajes no solicitados de un bot oficial, y una persona puede desactivarlos. Un conector propio envía `connector_id`, `reply_handle` y `"capabilities": ["outbox"]` con sus eventos y realiza un sondeo largo a `/v1/outbox` (consulte [el protocolo de conectores](connectors.es.md)). Sin un conector de este tipo, personagent solo habla dentro de la solicitud que contenía un mensaje. Los bucles proactivos omiten esas conversaciones, y la pregunta y la disculpa no se envían.

La página local también recoge la bandeja de salida, solo para su propio chat. Un evento de un programa que no recoge la bandeja de salida, como un asistente de programación que habla en un chat, no quita ese chat a un conector que la recoge (consulte [el protocolo de conectores](connectors.es.md#bandeja-de-salida-post-v1outbox)).

`PROACTIVE_PLATFORMS` limita dónde puede hablar primero el bucle proactivo. `PROACTIVE_PLATFORMS=qq_official` lo limita al bot oficial de QQ, y `qq` a QQ a través de NapCat. `CONNECTOR_OUTBOX_ENABLED=false` desactiva por completo la bandeja de salida.

Para hablar primero en un mensaje directo sin la bandeja de salida, su propio planificador (una tarea de complemento de AstrBot, una entrada de cron) puede enviar un evento de mensaje directo marcado con `"proactive": true`. Consulte [Hablar primero sin la bandeja de salida](connectors.es.md#hablar-primero-sin-la-bandeja-de-salida).

## Exponer los endpoints

Mantenga `SERVER_HOST=127.0.0.1` cuando el conector y personagent se ejecuten en el mismo equipo. Un contenedor cuenta como el mismo equipo solo con el espacio de nombres de red del host o con la red del host. La página local y `personagent up` siempre se enlazan a `127.0.0.1`. En los demás casos:

1. Defina `SERVER_HOST=0.0.0.0` (o `--host 0.0.0.0`) y `CONNECTOR_TOKEN`. El inicio rechaza un enlace de red sin el token. No exige `QQ_ONEBOT_SECRET`, pero sin él el obsoleto `/v1/onebot` queda desactivado en un enlace de red. Toda solicitud a él recibe 403 `onebot_disabled`, y el registro indica el motivo una vez.
2. Coloque delante un proxy inverso HTTPS o un túnel privado. Todos los conectores incluidos solo envían al bucle local o a HTTPS con un token definido. El complemento de AstrBot registra cualquier otro destino como `refusing unsafe personagent_url`, y los conectores de Satori y de Matrix se niegan a iniciarse.
3. Mantenga el cuerpo intacto byte a byte, porque la firma lo cubre, y mantenga los relojes con una diferencia inferior a cinco minutos.

Con una credencial vacía, su endpoint solo atiende a programas locales que llaman directamente a `http://127.0.0.1` o `http://localhost`. Una solicitud recibe 403 `non_local_request` si contiene alguno de estos elementos:

- una cabecera `Origin`;
- un `Sec-Fetch-Site` distinto de `none`;
- un `Host` distinto de `localhost`, `127.0.0.1` o `::1`;
- una cabecera de proxy: `X-Forwarded-For`, `Forwarded`, `X-Real-IP`, `CF-Connecting-IP`, `Via`, `X-Forwarded-Host`, `X-Forwarded-Proto`, `X-Forwarded-Port`, `True-Client-IP`, `X-Client-IP` o `X-Original-Forwarded-For`.

Un proxy en el mismo host que no añada ninguna de ellas sigue pareciendo local. Defina `CONNECTOR_TOKEN` (y `QQ_ONEBOT_SECRET` si utiliza `/v1/onebot`) antes de añadir cualquier proxy o túnel, incluso en un único host.

## Endpoints de salud

- `GET /health` es gratuito y abierto, y no llama a ningún servicio.
- `GET /health/details` sondea los servicios externos (con una caché de 60 s). Con `CONNECTOR_TOKEN` vacío, solo responde a solicitudes locales. Con un token definido, responde **solo** a solicitudes con una cabecera `X-Personagent-Token` coincidente, incluso desde el bucle local. Devuelve 503 cuando un sondeo crítico falla o no puede ejecutarse. Los sondeos críticos son los de los modelos de chat y, cuando QQ utiliza la entrada directa de OneBot (`QQ_BOT_ID` y `QQ_ONEBOT_URL` definidos, `CONNECTOR_QQ_PLATFORMS` sin definir), el del puente OneBot.
- `personagent doctor [--json]` ejecuta los mismos sondeos y la comprobación de ajustes, y finaliza con un valor distinto de cero en el mismo caso. Cuando la última comprobación de actualizaciones tiene un día de antigüedad, también consulta a pypi.org la versión más reciente (`UPDATE_CHECK_ENABLED=false` la omite).

## Costes

- **Los sondeos consumen crédito.** `personagent doctor` y `/health/details` envían una compleción de chat mínima a cada modelo al que el agente envía trabajo: las respuestas en grupos y en mensajes directos, la decisión de búsqueda web, la evaluación de reacciones (mientras `REACT_LEARN_ENABLED` está activado), la autorrevisión (mientras `EVAL_ENABLED` está activado) y la visión. También envían un embedding si `EMBEDDING_MODEL` está definido y una búsqueda de Tavily si `TAVILY_API_KEY` está definido. `/health` y las comprobaciones de ajustes y registros son gratuitos.
- **El uso del modelo se contabiliza.** Cada solicitud a un modelo se cuenta por modelo y por día a partir del uso que comunica el proveedor, con el coste cuando el proveedor lo comunica. `personagent doctor` imprime el día de hoy y los últimos 7 días, y la vista **Aplicación** de la página local muestra lo mismo. El archivo de recuento se escribe en segundo plano, como máximo una vez por minuto y una vez más al detenerse.
- **Aprendizaje y memoria.** Las decisiones de aprendizaje del propio personaje cuestan una llamada cada una a `PROMOTE_JUDGE_MODEL`, como máximo `PROMOTE_JUDGE_BATCH` cada `PROMOTE_JUDGE_INTERVAL_S`. La consolidación de la memoria cuesta una llamada por tramo de chat a `LLM_JUDGE_MODEL`, como máximo 16 por chat y `MEMORY_CALLS_PER_DAY` (40) para todos los chats en conjunto cada día. `PROMOTE_JUDGE_ENABLED=false` y `MEMORY_CALLS_PER_DAY=0` las desactivan.
- **Los scripts de `tools/`** varían. Algunos son gratuitos y otros llaman a un modelo. La tabla de [tools.md](tools.es.md) indica cuáles.
- **`personagent eval`** llama al modelo en cada caso, excepto en la suite `memory`, que se ejecuta sin conexión con respuestas predefinidas. Las suites de perfil y de aprendizaje también requieren un segundo modelo como juez (`BENCH_JUDGE_MODEL`).
- **Memoria.** Cuando se superan 256 conversaciones con espacio de nombres (no de QQ), la conversación inactiva con menos actividad reciente se descarta de la memoria y pierde sus reacciones pendientes. Sus mensajes aún no consolidados se consolidan antes, y sus mensajes recientes permanecen en `runtime/recent.json` durante 72 horas, salvo con `MEMORY_KEEP_RECENT=false`. Los hechos, los acontecimientos, las notas principales y los registros se conservan. Una conversación con una solicitud en curso nunca se descarta. Los recuerdos a largo plazo se cargan desde el disco al iniciar y este límite no les afecta.
- **Disco.** El registro de evidencias y el registro de candidatos de `runtime/` solo crecen y nunca se truncan. `personagent doctor` emite una advertencia si alguno supera los 50 MB (`LEDGER_EVIDENCE_WARN_BYTES`, `LEDGER_CANDIDATES_WARN_BYTES`). Los archivos de memoria siguen siendo pequeños: `recent.json` conserva los chats con actividad en las últimas 72 horas, y `memory_trash.jsonl` conserva los elementos eliminados durante un máximo de 30 días. Antes del primer cambio de cada día, `memory.json`, `core_memory.json` y `episodes.json` se copian en un archivo con el mismo nombre terminado en `.bak`, y el primer inicio de esta versión conserva el archivo de memoria anterior como `memory.json.pre-v2`. Después de **Olvidar este chat** o de un olvido solicitado en el chat, las copias `.bak` se vuelven a escribir a partir de los archivos actuales y `memory.json.pre-v2` pierde lo olvidado, de modo que ninguna copia en disco lo conserva. Haga copias de seguridad de `runtime/`, porque guarda todo lo que el bot ha aprendido y recuerda.

## Si el bot deja de responder

Las causas están ordenadas de la más a la menos habitual. Cuando la página local ejecuta el agente, [Actividad](guide.es.md#actividad) muestra si llegan mensajes y por qué guardó silencio. En un servidor, lea el registro del servicio y utilice `personagent learned` para consultar lo aprendido.

1. **No recibe ningún mensaje.** En la página local, compruebe que la plataforma aparece como conectada y lea `runtime/desktop/direct.log` o `astrbot.log`. El bot oficial de QQ debe estar en el grupo, y QQ determina qué mensajes de grupo recibe. Un bot de WeChat personal nunca recibe mensajes de grupos. En un AstrBot que ejecute usted, rellene `groups` del complemento (y `dm_users` para los mensajes directos) y, para NapCat, quite `aiocqhttp` de `excluded_platforms`. Los conectores de Satori y de Matrix tienen sus propias listas de permitidos en su `.env`; consulte sus README. En este caso, el chat nunca aparece en Actividad.
2. **El agente está desactivado.** El aviso de `personagent run` indica `agent: OFF`, con el motivo y la solución. Sin `LLM_API_KEY`, añada una clave en la página local (o defina `LLM_API_KEY`) y reinicie. Con `AGENT_ENABLED=false`, establézcalo en `true` en `<home>/.env` y reinicie. Hasta entonces, cada evento recibe `owned: false`, y el primero registra una única línea ERROR con la misma indicación.
3. **Responde el propio modelo de AstrBot.** El complemento recurrió a él porque la solicitud falló, personagent rechazó el mensaje (punto 5) o el agente está desactivado (punto 2). El registro de AstrBot muestra `refusing unsafe personagent_url`, `agent refused the request (403): <message>` (u otro estado; consulte la tabla siguiente) o `timed out waiting for the agent`. `timeout_s` debe abarcar el antirrebote y las llamadas al modelo del turno, así como el turno que estaba en curso cuando llegó el mensaje. Las llamadas al modelo de un turno comparten 1,5 × `LLM_TIMEOUT_S`, tanto en un grupo como en un mensaje directo, por lo que debe mantener 3 × `LLM_TIMEOUT_S` por debajo de ese valor. Su valor predeterminado (420) abarca el valor predeterminado del agente (3 × 120 = 360 s). Auméntelo cuando aumente `LLM_TIMEOUT_S`.
4. **Nadie se dirigió a él.** En un grupo, responde a su nombre (`PERSONA_NAME`) o a una @mención. En caso contrario, espera a que haya suficiente conversación (`CHAT_TRIGGER_COUNT`, 30 mensajes de forma predeterminada) e incluso entonces puede no intervenir. De 02:00 a 07:00 en su zona horaria, casi nunca interviene en chats en los que no se han dirigido a él. La zona horaria es `PERSONA_TZ_OFFSET_HOURS`. Si está vacía, es UTC+8 cuando `AGENT_LANG` es `zh` o `zh-TW` y, en los demás casos, la de este equipo. Un mensaje de grupo que llega más de 10 minutos después de enviarse, dentro de los dos minutos siguientes al primer mensaje de su plataforma desde el inicio, es un mensaje acumulado: se conserva como contexto y no se responde, y el registro del servicio lo indica. Actividad muestra el motivo de cada turno reciente. Para ver la misma decisión sin conexión, ejecute `personagent chat --trigger 4`.
5. **Las listas de permitidos de personagent.** `ACCESS_GROUPS` y `ACCESS_DM_USERS` se aplican en todas las vías, y un mensaje directo de QQ con un ID sin prefijo también requiere ser del administrador o figurar en una entrada. Un mensaje rechazado se devuelve sin reclamar, por lo que, a través de AstrBot, puede responderlo su propio modelo. personagent registra cada conversación rechazada una vez, en el nivel INFO, junto con el ajuste que la rechazó.
6. **La llamada al modelo falla.** Una clave rechazada (401 o 403) o un saldo agotado (402 o cuota agotada) registra una línea ERROR que indica el host del proveedor y el ajuste que debe corregirse. Ejecute `personagent doctor`. Este envía una solicitud mínima a cada endpoint de modelo y muestra el estado, lo que también permite detectar un `LLM_BASE_URL` o un `LLM_MODEL` incorrectos. Cuando el modelo principal agota el tiempo de espera o se interrumpe la conexión, y `LLM_FALLBACK_MODEL` indica otro modelo, la llamada pasa de inmediato al modelo de respaldo, de modo que el turno se responde dentro de su tiempo asignado. Un error que un proveedor envía dentro de una respuesta normal, como los fallos de origen de OpenRouter, se trata como el error HTTP correspondiente. Mientras el modelo no está disponible, el personaje envía una breve disculpa, sin salir de su papel, cuando se dirigen a él, como máximo una vez por conversación cada cinco minutos; Actividad muestra el turno como «el modelo no respondió».
7. **Un ajuste mal escrito.** El registro de inicio y `personagent doctor` enumeran cada clave que `.env.example` no reconoce y cualquier valor que empiece por `#`.
8. **Un BOM en `.env`.** El nombre del primer ajuste incluye el BOM y nunca llega al proceso. El inicio y `personagent doctor` lo notifican. Vuelva a guardar el archivo como UTF-8 sin BOM.
9. **`QQ_BOT_ID` sin definir o incorrecto con NapCat.** A través de AstrBot, las @menciones siguen funcionando, pero la recuperación de menciones perdidas depende de él. En la entrada directa de OneBot, una @mención nunca se reconoce. El bot se inicia sin problemas, no registra nada y nunca responde. `personagent doctor` emite una advertencia cuando `QQ_BOT_ID` está vacío y hay otros ajustes de QQ definidos. El bot oficial de QQ no lo utiliza.
10. **Responde, pero ha olvidado lo que aprendió.** O bien NapCat QQ llega sin `CONNECTOR_QQ_PLATFORMS=aiocqhttp`, o bien ha cambiado `PERSONA_NAME` o `PERSONA_VERSION`, lo que da lugar a un personaje nuevo. El registro emite una advertencia cuando se rechaza en bloque el material promovido del personaje anterior. Editar `persona.txt`, también desde el cuadro Perfil de la página, no da lugar a un personaje nuevo. Sus revisiones con un mismo `PERSONA_VERSION` comparten un ámbito de aprendizaje (`runtime/persona_lineage.json`). Para incorporar filas aprendidas con un hash de perfil que el linaje no incluye, ejecute `personagent learned lineage adopt <hash>` y, a continuación, `personagent learned rebuild`. El hash figura en el ámbito del candidato en `personagent learned show <id>`. Cambiar `AGENT_LANG` del chino a otro idioma, o a la inversa, también hace que se utilicen los otros archivos aprendidos de `runtime/`.

Los errores de `/v1/events` se enumeran a continuación. El complemento de AstrBot registra el mensaje, y `code` es el campo estable que un cliente puede utilizar para distinguir los casos.

| Estado | `code` | Mensaje en el registro de AstrBot | Causa |
|---|---|---|---|
| 403 | `unauthenticated` | authentication required | no hay `CONNECTOR_TOKEN` y el llamante no está en este equipo |
| 403 | `non_local_request` | no credential is configured; only local requests accepted | no hay `CONNECTOR_TOKEN` y la solicitud llegó a través de un navegador, un proxy u otro nombre de host |
| 403 | `invalid_envelope` | invalid, stale, or replayed request envelope | token, cabeceras o firma ausentes o incorrectos, relojes con una diferencia de más de 5 min, un nonce reutilizado o un mecanismo antirrepetición lleno (`connector replay guard full` en el registro del agente) |
| 403 | `stale_event` | stale or invalid sent_at | `sent_at` difiere de la hora actual en más de `CONNECTOR_MAX_EVENT_AGE_S` (24 h), incluidas las marcas de tiempo futuras o en milisegundos |
| 400 | `invalid_schema` | invalid event schema | falta un campo obligatorio: `platform`, `conversation_type`, `sender_id`, `message_id`, `sent_at` y `conversation_id` para los grupos |
| 400 | `client_disconnected` | client disconnected | el llamante cerró la conexión durante el envío |
| 408 | `body_timeout` | request body not received in time | el cuerpo tardó más de 30 s en llegar |
| 413 | `body_too_large` | request body too large | supera `SERVER_MAX_BODY_BYTES` (8 MB), normalmente por una imagen incrustada |
| 429 | `capacity_exceeded` | webhook capacity exceeded | supera `CONNECTOR_MAX_INFLIGHT` turnos en curso; vuelva a intentarlo al cabo de 3 s |

## Heredado: la entrada directa de OneBot

El webhook de NapCat todavía puede enviar eventos a `POST /v1/onebot`, y personagent responde a través de `QQ_ONEBOT_URL`. Esta ruta está obsoleta y se mantiene durante la serie 1.x. Utilice en su lugar la conexión del bot oficial de QQ, o NapCat a través de AstrBot con `CONNECTOR_QQ_PLATFORMS=aiocqhttp`. La ruta emite una advertencia en el primer uso y marca cada respuesta con `Deprecation: true`.

Para migrar a NapCat a través de AstrBot, añada OneBot v11 (NapCat) en la página local, o ejecute `personagent connect astrbot <AstrBot data dir> --qq` para su propio AstrBot y rellene las listas de permitidos. Apunte allí el cliente WebSocket de NapCat y desactive el cliente HTTP de NapCat (conserve su servidor HTTP). La memoria y el aprendizaje se mantienen, porque `CONNECTOR_QQ_PLATFORMS` conserva los ID.

Si todavía utiliza la ruta heredada:

- Configure ambos sentidos como se describe en la [documentación de NapCat](https://napneko.github.io/). Necesita un **servidor HTTP** en `QQ_ONEBOT_URL` para enviar y un **cliente HTTP** que envíe a `http://127.0.0.1:8080/v1/onebot` (`SERVER_HOST`, `SERVER_PORT`). `QQ_ONEBOT_URL` está vacío de forma predeterminada, por lo que debe escribirlo en `.env`. Sin él, el bot recibe mensajes pero nunca responde. La comprobación previa y `personagent doctor` emiten una advertencia cuando esta ruta parece configurada (`QQ_BOT_ID` o `QQ_ONEBOT_SECRET` definidos, `CONNECTOR_QQ_PLATFORMS` vacío) y `QQ_ONEBOT_URL` está vacío.
- Si NapCat está en otro equipo, defina `QQ_ONEBOT_SECRET` con el `secret` del cliente HTTP. De lo contrario, cualquiera que acceda al puerto puede falsificar eventos. En ese caso, los cuerpos deben incluir `x-signature: sha1=<hex>` (403 `bad_signature`), y los eventos con una marca de tiempo desviada más de cinco minutos reciben 403 `stale_event`. Sin el secreto, la ruta solo responde a programas de este host, y en un enlace de red está desactivada (403 `onebot_disabled`).
- Con AstrBot en la misma cuenta, mantenga `aiocqhttp` en `excluded_platforms`; de lo contrario, cada mensaje llegaría dos veces.

Compruebe el envío con `curl http://127.0.0.1:3000/get_login_info`. Compruebe la recepción consultando el registro de personagent mientras escribe al bot en un grupo.
