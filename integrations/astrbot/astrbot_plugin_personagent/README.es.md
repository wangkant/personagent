# astrbot_plugin_personagent

[English](README.md) · [简体中文](README.zh-CN.md) · [繁體中文](README.zh-TW.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · Español · [Français](README.fr.md) · [Deutsch](README.de.md) · [Português (Brasil)](README.pt-BR.md) · [Русский](README.ru.md)


Este plugin de [AstrBot](https://github.com/AstrBotDevs/AstrBot) conecta AstrBot con [personagent](https://github.com/wangkant/personagent). Reenvía cada mensaje permitido al agente y devuelve las respuestas del agente al chat.

## ¿Lo necesitas?

No lo necesitas para QQ, WeChat, Telegram ni Discord. personagent los conecta por sí mismo, sin AstrBot. Ejecuta `personagent` para abrir su página local y añádelos en **Conectar apps**.

Necesitas este plugin cuando AstrBot lleva la conversación. Eso ocurre en dos casos.

- **Añades otra plataforma en la página de personagent.** KOOK, Feishu/Lark, DingTalk, Slack, el bot de IA de WeCom, Mattermost, Misskey y las plataformas de Avanzado pasan todas por AstrBot. La página descarga y ejecuta un AstrBot por ti e instala este plugin en él, así que aquí no tienes nada que hacer.
- **Ya ejecutas un AstrBot** con sus propias plataformas y plugins. Instala el plugin como se describe abajo.

## Qué hace

- Recibe mensajes de grupo y mensajes directos de todos los adaptadores de plataforma de AstrBot (Telegram, Discord, Slack, QQ...), salvo los de `excluded_platforms`.
- Reenvía los mensajes de grupos y remitentes de la lista de permitidos al `POST /v1/events` del agente como un evento neutro de plataforma. Lee cada plataforma tal como la entrega su adaptador, incluido a quién se dirige, qué se citó, stickers, imágenes, notas de voz y la hora en que la plataforma dice que se envió.
- Devuelve las respuestas del agente a través de AstrBot en la forma que cada plataforma espera. Las respuestas pueden llevar texto e imágenes y, en chats de grupo, una mención cuando el agente la pide.
- Consulta la bandeja de salida del agente para entregar lo que dice sin que le pregunten, como un saludo programado, una pregunta de seguimiento o la excusa que publica en un grupo cuando su modelo está caído. Consulta [Bandeja de salida](#bandeja-de-salida).
- Detiene el flujo propio de AstrBot cuando el agente reclama la conversación (`block_default`), para que el modelo integrado de AstrBot nunca responda en lugar de la persona.

La persona, la memoria, el debounce y la simulación de escritura se ejecutan en el agente. Este plugin es un conector tal como lo define el [`docs/connectors.md`](https://github.com/wangkant/personagent/blob/main/docs/connectors.es.md) del agente.

## Instalar en tu propio AstrBot

Necesitas AstrBot, iniciado al menos una vez para que exista su carpeta de datos, y personagent (`python -m pip install personagent`; consulta su README).

### Con la configuración de personagent

```bash
personagent connect astrbot
```

El comando busca primero la carpeta de datos de AstrBot, la que contiene `cmd_config.json`, `plugins/` y `config/`. Si no encuentra ninguna, ofrece descargar AstrBot. Luego pregunta si AstrBot se ejecuta en Docker, a qué app de chat se une el bot (con el token de esa app cuando AstrBot aún lo necesite), los grupos, el administrador y quién puede enviar mensajes directos al bot. Para QQ a través de NapCat también pregunta el número de la cuenta del bot. Por último copia este plugin, genera un token compartido, lo escribe en ambos lados y escribe las listas de permitidos. `personagent init --terminal` ofrece el mismo paso al final.

Para saltarte las preguntas, pasa la carpeta de datos:

```bash
personagent connect astrbot <AstrBot data dir>        # add --qq to route QQ (NapCat) as well
```

Ejecutado así, una primera conexión deja las listas de permitidos **vacías**, y las rellenas en los ajustes del plugin. `personagent connect astrbot --help` lista los indicadores que además activan una plataforma en AstrBot.

Puedes volver a ejecutar el comando cuando quieras. Conserva las listas de permitidos, las demás plataformas excluidas y cualquier `personagent_url` que este plugin acepte (consulta [Dónde puede ejecutarse el agente](#dónde-puede-ejecutarse-el-agente)). Un `personagent_url` que el plugin rechazaría se sustituye por el valor predeterminado de loopback. El enrutamiento de QQ solo cambia cuando pasas `--qq` o `--no-qq`, y `CONNECTOR_QQ_PLATFORMS` del agente lo sigue. Cuando pregunta, las listas actuales son los valores predeterminados: pulsa Enter para conservar una o escribe `-` para vaciarla.

Después reinicia AstrBot e inicia el agente (consulta [Comprobar que funciona](#comprobar-que-funciona)).

### Desde la WebUI de AstrBot

1. Descarga `astrbot_plugin_personagent.zip` de la [última versión de personagent](https://github.com/wangkant/personagent/releases/latest).
2. Súbelo en **Install from File** en la página de plugins de AstrBot.
3. Establece `connector_token` al `CONNECTOR_TOKEN` del `.env` de personagent y rellena las listas de permitidos como se describe abajo.
4. Si AstrBot se ejecuta en otro ordenador que personagent, establece `personagent_url` a una dirección HTTPS (consulta [Dónde puede ejecutarse el agente](#dónde-puede-ejecutarse-el-agente)).

Para actualizar, sube el zip de la versión más reciente de la misma forma. AstrBot 4.29 y posteriores sustituyen la copia instalada. En versiones anteriores, desinstala primero el plugin y deja **Also delete plugin configuration file** sin marcar.

### A mano

1. Copia esta carpeta a `<AstrBot data dir>/plugins/astrbot_plugin_personagent/`.
2. Reinicia AstrBot o recarga los plugins en su WebUI. AstrBot instala `requirements.txt`, que solo lista `httpx`.
3. Abre los ajustes del plugin en la WebUI. Se guardan en `<AstrBot data dir>/config/astrbot_plugin_personagent_config.json`.
   - Añade a `groups` los ID de grupo a los que puede unirse la persona.
   - Añade a `dm_users` los ID de remitente cuyos mensajes directos puede responder.
   - Si el `.env` del agente establece `CONNECTOR_TOKEN`, pon el mismo valor en `connector_token`. Es obligatorio cuando el agente está en otro host.
   - Deja `personagent_url` en su valor predeterminado cuando el agente se ejecuta en el mismo host con el `SERVER_PORT=8080` predeterminado.

El plugin **deniega por defecto**. Con listas vacías no reenvía nada, y AstrBot se comporta como si el plugin no estuviera instalado. Escribe los ID como los muestra AstrBot; envía `/sid` en un chat para verlos. Un ID sin prefijo coincide en todos los adaptadores. `qq_official:ID` coincide solo en ese adaptador, y `qq_official:*` reenvía todas las conversaciones de ese tipo en él.

Un `*` solo en `groups` o `dm_users` reenvía todas las conversaciones de ese tipo en todos los adaptadores y las marca con `prefiltered: false`. Entonces solo deciden `ACCESS_GROUPS` y `ACCESS_DM_USERS` del propio agente. El agente rechaza una plataforma sin entradas allí, salvo los grupos de QQ, a los que responde a menos que `ACCESS_GROUPS` liste alguno.

### Comprobar que funciona

1. Inicia el agente con `personagent run`, que solo inicia el servidor. Su banner debe mostrar `agent: on`.
2. Di el nombre del bot (el `PERSONA_NAME` del agente) en un grupo permitido.

Si no llega respuesta, busca líneas `personagent:` en el registro de AstrBot, lee lo que `personagent run` imprimió tras su banner y consulta [Solución de problemas](#solución-de-problemas).

## Configuración

| Clave | Tipo | Predeterminado | Descripción |
| --- | --- | --- | --- |
| `personagent_url` | string | `http://127.0.0.1:8080` | URL base del agente. El plugin añade `/v1/events` y `/v1/outbox`. Debe ser loopback o HTTPS con `connector_token` definido. |
| `connector_token` | string | `""` | Secreto compartido. Debe coincidir con el `CONNECTOR_TOKEN` del agente. Obligatorio para cualquier `personagent_url` que no sea loopback. |
| `timeout_s` | int | `420` | Segundos de espera en cada intento. Consulta [Tiempos de espera](#tiempos-de-espera). |
| `excluded_platforms` | list | `["aiocqhttp"]` | Nombres de adaptadores que nunca se reenvían. Quita `aiocqhttp` para enrutar QQ (NapCat) por este plugin. Consulta [QQ a través de NapCat](#qq-a-través-de-napcat). |
| `groups` | list | `[]` | ID de grupo que se reenvían. Vacío no reenvía ningún grupo. `adapter:ID` o `adapter:*` limita una entrada a un adaptador. Un `*` solo reenvía todos los grupos sin filtrar. |
| `dm_users` | list | `[]` | ID de remitente cuyos mensajes directos se reenvían. Vacío no reenvía ninguno. `adapter:ID` o `adapter:*` limita una entrada a un adaptador. Un `*` solo reenvía todos los mensajes directos sin filtrar. |
| `block_default` | bool | `true` | Detiene el flujo de AstrBot cuando el agente reclama la conversación. |
| `forward_quoted_text` | bool | `true` | Envía el texto y el autor de un mensaje citado junto con su id, cuando la plataforma los proporciona. Mientras esté activo y `quote_max_chars` sea mayor que 0, cada evento declara la capacidad `quote_text`. |
| `quote_max_chars` | int | `200` | Longitud máxima del texto citado enviado. Las citas más largas se cortan. |
| `max_inline_image_bytes` | int | `4000000` | Imagen más grande enviada en línea. Las imágenes que el agente no puede obtener por sí mismo (Telegram, archivos locales, direcciones privadas) se envían en línea. Una mayor llega como la nota `(sent an image)`. Mantenlo por debajo de `VISION_MAX_IMAGE_BYTES` del agente. |
| `outbox_enabled` | bool | `true` | Consulta y entrega la bandeja de salida del agente. Consulta [Bandeja de salida](#bandeja-de-salida). |
| `outbox_wait_s` | int | `25` | Cuánto puede esperar en el agente una consulta de la bandeja de salida, 30 como máximo. |
| `connector_id` | string | `""` | Nombre de este AstrBot para el agente. Vacío genera uno una vez y lo conserva. Dos hosts de AstrBot necesitan nombres distintos. |

### Dónde puede ejecutarse el agente

- **Mismo host**, o un contenedor que comparte el espacio de nombres de red del host o usa la red del host: conserva el `personagent_url` de loopback predeterminado.
- **Otro contenedor u host**: usa un `personagent_url` HTTPS y define el mismo secreto no vacío en `connector_token` y en el `CONNECTOR_TOKEN` del agente. También sirve un túnel privado que termine en una URL de loopback visible para AstrBot. Define también en ese caso el mismo token en ambos lados, porque el agente rechaza las solicitudes sin token que llegan a través de un proxy.

El plugin rechaza `http://` sin cifrar hacia cualquier cosa que no sea loopback, como `http://host.docker.internal:8080`, incluso con token. Entonces cada mensaje registra `refusing unsafe personagent_url` y responde el modelo propio de AstrBot.

**AstrBot en Docker.** Dentro de un contenedor, `127.0.0.1` es el propio contenedor, así que el `personagent_url` predeterminado no alcanza nada. Tienes dos opciones:

- Dale a AstrBot red del host: `network_mode: host` en su archivo compose o `docker run --network host`. Docker Desktop necesita la versión 4.34 o posterior con host networking activado. Un contenedor de NapCat en el mismo archivo compose también necesita red del host.
- Pon el agente detrás de HTTPS y define esa dirección como `personagent_url` (`personagent connect astrbot <dir> --url https://...`).

El agente escucha en `127.0.0.1:8080` por defecto. Si defines su `SERVER_HOST` a una dirección que no sea loopback, se niega a iniciarse salvo que `CONNECTOR_TOKEN` esté definido. Define el token antes de poner un proxy o túnel delante del agente, incluso en un solo host.

### Tiempos de espera

Cada solicitud dura lo que el turno del agente, que es un breve debounce más cada llamada al modelo y reintento. Si `timeout_s` se agota, el agente termina igualmente el turno y conserva lo aprendido, pero la respuesta se pierde y el modelo propio de AstrBot responde al mensaje.

Mantén `LLM_TIMEOUT_S × (1 + LLM_MAX_RETRIES)` del agente por debajo de `timeout_s`. Con los valores predeterminados del agente (`LLM_TIMEOUT_S=120`, `LLM_MAX_RETRIES=2`), un turno cuyas llamadas al modelo siguen agotando el tiempo puede superar los 360 s, que el `timeout_s` predeterminado de 420 cubre. Si subes cualquiera de los dos en el agente, sube también `timeout_s`.

El plugin reintenta un 429 o 500 del agente hasta dos veces, respetando `Retry-After` en un 429, mientras la solicitud firmada siga siendo reciente.

### `block_default` y propiedad

El plugin detiene el flujo de AstrBot cada vez que el agente informa de que la conversación es suya (`owned: true`), haya respondido o no, para que el modelo integrado de AstrBot no entre en los turnos en que la persona no participa.

Los errores de transporte, las respuestas no válidas y las conversaciones que el agente rechaza siguen al flujo normal de AstrBot. Si la respuesta del agente no tiene campo `owned`, el plugin usa `handled`.

## QQ a través de NapCat

personagent conecta los bots oficiales de QQ por sí mismo, sin AstrBot. Esta sección cubre solo una cuenta de QQ ejecutada con NapCat (u otra implementación de OneBot v11) detrás del adaptador `aiocqhttp` de AstrBot. Cuando añades OneBot v11 en la propia página de personagent, esta quita `aiocqhttp` de `excluded_platforms` y define `CONNECTOR_QQ_PLATFORMS` por ti.

1. Quita `aiocqhttp` de `excluded_platforms` y añade los grupos de QQ a `groups`.
2. En el `.env` del agente, define `CONNECTOR_QQ_PLATFORMS=aiocqhttp` y `QQ_BOT_ID` (el número de la cuenta del bot).
3. Opcional: define `QQ_ONEBOT_URL` del agente al servidor HTTP de NapCat. Esto activa el barrido de recuperación de menciones perdidas, que también necesita `QQ_BOT_ID`. Los mensajes proactivos, la pregunta de seguimiento tras un rechazo y la excusa de un grupo cuando el modelo falla pasan por la [bandeja de salida](#bandeja-de-salida) de este plugin mientras esté consultando. En caso contrario pasan directamente por NapCat, siempre que esa URL esté definida.
4. Si NapCat también publica en `/v1/onebot` del agente, desactívalo. La ruta está obsoleta y ejecutar ambas entrega cada mensaje dos veces.

`personagent connect astrbot <data dir> --qq` quita `aiocqhttp` de `excluded_platforms` y define `CONNECTOR_QQ_PLATFORMS`. Ejecutado sin carpeta, también pregunta `QQ_BOT_ID`. La guía de despliegue también cubre esta ruta: [docs/deploy.md](https://github.com/wangkant/personagent/blob/main/docs/deploy.es.md#qq-a-través-de-napcat-onebot).

No omitas `CONNECTOR_QQ_PLATFORMS=aiocqhttp`. Sin él, el agente archiva los chats de QQ bajo ID con prefijo `aiocqhttp:`, lo aprendido bajo los ID de QQ sin prefijo deja de coincidir y los registros no se pueden volver a indexar después.

Como los ID de QQ siguen sin prefijo, los ajustes de QQ del propio agente siguen aplicándose. Las entradas de QQ de `ACCESS_GROUPS` filtran los grupos (sin entradas significa todos los grupos de QQ), y los mensajes directos solo se responden al administrador en `ADMIN_IDS` o a quienes están en `ACCESS_DM_USERS`. El asistente escribe los grupos de QQ que le das en el `.env` del agente. Para añadir un grupo de QQ más tarde, añádelo tanto a `groups` como a `ACCESS_GROUPS`, o no listes ningún grupo de QQ en `ACCESS_GROUPS`.

Antes de que AstrBot lleve un grupo de QQ activo, revisa dos ajustes de AstrBot. Ambos se ejecutan antes que los manejadores de plugins.

- `platform_settings.rate_limit` es por defecto 30 mensajes cada 60 s. Los mensajes por encima del límite se retrasan, no se descartan. Sube o desactiva el límite.
- `content_safety.internal_keywords` está activo por defecto y descarta los mensajes que coinciden con su lista de palabras clave, incluidos los que la persona habría respondido. Revisa la lista.

## Plataformas

El agente habla un formato neutro, y el plugin traduce en los bordes con los mecanismos propios de cada plataforma. La tabla de abajo se comprobó con los adaptadores de AstrBot 4.25.5.

En todas las plataformas:

- Solo se reenvían los mensajes que escribió una persona. Los avisos de QQ (toques, retiradas, entradas) y las solicitudes, y las entradas y cambios de tema de Slack, no son turnos.
- Los vídeos, archivos y mensajes de voz llegan como una nota a la que la persona puede reaccionar, como `(sent a video)`, `(sent a file: deck.pdf)` o `(sent a voice message)`, con la transcripción de la plataforma cuando la tiene.
- Los mensajes citados llevan su texto y autor cuando la plataforma los proporciona (`forward_quoted_text`).
- Donde el adaptador la conserva, la hora del mensaje es la de la plataforma y no la hora en que AstrBot lo recibió.
- Las respuestas se dividen por debajo del límite de longitud de la plataforma, contando la mención y los escapes como los cuenta la plataforma. Nunca se convierten en una imagen de texto, y nombran a la gente como lo hace la plataforma.
- La bandeja de salida solo se usa donde la plataforma puede enviar sin que le pregunten.

| Plataforma (adaptador) | Qué funciona | Qué no puede hacer la plataforma |
| --- | --- | --- |
| QQ por OneBot (`aiocqhttp`) | Grupos y mensajes directos. @ y respuesta al bot, también cuando el adaptador no pudo resolver el @. Nombres de caras, stickers de tienda (`mface`) e imágenes marcadas como stickers. Menciones como un @ real de QQ, seguido de un espacio. Las respuestas largas se dividen por debajo de `forward_threshold` de AstrBot, así que ninguna se convierte en una tarjeta de reenvío combinado. Bandeja de salida. | El Markdown se ve tal como se escribe. |
| QQ oficial (`qq_official`, `qq_official_webhook`) | Mensajes de grupo que hacen @ al bot y mensajes directos. Caras como `[表情:name]`. Las respuestas piden texto plano en lugar del markdown del adaptador. | Los grupos entregan solo los mensajes que hacen @ al bot, así que la persona no puede seguir una conversación. Sin citas, sin nombres (solo openids), sin menciones en las respuestas. Solo se puede responder dentro de los 5 minutos siguientes a un mensaje, así que no hay bandeja de salida. |
| Telegram (`telegram`) | Grupos, temas (`<chat>#<thread>`) y mensajes directos. Respuesta al bot para cualquier tipo de mensaje, sin el prefijo de activación `/@bot` del adaptador. Emoji de stickers, más la imagen de los estáticos. Las imágenes se obtienen mediante el bot del adaptador, así que el token del bot nunca sale de AstrBot. Un nombre de usuario mencionado se convierte en el id numérico de la persona una vez que ha escrito. Las respuestas mencionan por nombre de usuario, o con un enlace `tg://user` a quien no tiene, y muestran `*`, `_` y similares tal como se escriben. Bandeja de salida. | Con el modo de privacidad de BotFather activo (por defecto), los grupos entregan solo comandos, @menciones y respuestas al bot. Desactívalo para que la persona pueda seguir la conversación. Los stickers animados y de vídeo no se pueden ver. |
| Discord (`discord`) | Canales e hilos como grupos, y mensajes directos. Un `@bot` inicial (que el adaptador quita), un ping a uno de los roles del bot y las respuestas al bot se dirigen a él. Citas con su texto. Stickers. Adjuntos de voz y vídeo como notas. Menciones como `<@id>`, con `@everyone` y `@here` inertes. Las respuestas se dividen a los 2000 caracteres. Bandeja de salida, también en mensajes directos. | Necesita la intención Message Content. |
| Slack (`slack`) | Canales y mensajes directos. Una respuesta en hilo bajo el mensaje del bot se dirige a él. Enlaces desplegados. Los id de mensaje son el `ts` de Slack. Menciones como `<@id>`. `&`, `<` y `>` escapados para que el texto no pueda avisar a un canal. Las respuestas se dividen a los 3000 caracteres. Bandeja de salida. | Una respuesta en hilo no lleva el texto del padre. Sin indicador de escritura para bots. Las respuestas caen en el canal, no en el hilo (adaptador). |
| KOOK (`kook`) | Canales y mensajes directos. @ y pings a un rol que tiene el bot. Citas cuando KOOK las incluye. Emoji `(emj)` y la hora real de envío. Menciones en línea en el texto, con las etiquetas de estilo `(met)` del texto de la persona inertes. Imágenes enviadas como archivo, porque el adaptador solo sube JPEG base64. Bandeja de salida. | El adaptador de AstrBot descarta los mensajes simples de imagen, archivo, voz y vídeo (no las tarjetas) antes de que los vea ningún plugin. Sin indicador de escritura. |
| Lark / Feishu (`lark`) | Grupos y mensajes directos. @ y respuestas al bot (Lark nombra la app como remitente). Citas con su texto. Stickers como emoji. Bandeja de salida. | Sin el permiso "leer todos los mensajes del grupo", solo llegan los mensajes con @. Cada respuesta cita el mensaje que contesta y el markdown se renderiza (adaptador). Los nombres son prefijos de id. |
| DingTalk (`dingtalk`) | Grupos y mensajes directos. Las imágenes, que el adaptador entrega como archivos locales, van en línea. Vídeos como nota. Bandeja de salida. Los mensajes directos llegan a quienes han escrito al bot. | Los grupos entregan solo los mensajes que hacen @ al bot. Sin citas, ni menciones ni respuestas con cita en las respuestas. Cada respuesta es markdown titulado "AstrBot" (adaptador). |
| LINE (`line`) | Grupos, salas y mensajes directos. @ al bot. Id de citas. Palabras clave de stickers. Las burbujas de un turno se envían en una llamada, de cinco en cinco, para que el reply token gratuito las cubra. Bandeja de salida, que cuenta para la cuota de push. | LINE no envía el texto citado. Sin menciones en las respuestas (adaptador). Las imágenes salientes necesitan un `callback_api_base` HTTPS público. Los nombres son prefijos de id. |
| Mattermost (`mattermost`) | Canales y mensajes directos. @ al bot. La raíz del hilo como cita. Imágenes en línea. Menciones por nombre de usuario una vez que la persona ha escrito. `@channel`, `@all` y `@here` inertes. Las respuestas se dividen a los 4000 caracteres. Bandeja de salida. | El texto citado requeriría una consulta que el plugin no hace. Sin indicador de escritura. |
| Misskey (`misskey`) | Mensajes directos de chat y salas, con `@bot` en cualquier parte de un mensaje de sala. Menciones como `@user@host` una vez que la persona ha escrito, con cualquier otro `@` del texto de la persona inerte. Las respuestas se dividen a los 3000 caracteres. Bandeja de salida para chat y salas. | Las notas (publicaciones públicas) no se reenvían, porque AstrBot las clasifica como eventos del sistema y una respuesta sería pública. `unique_session` rompe las salas (adaptador). |
| Satori (`satori`) | Lo que el backend de Satori conecte: grupos, mensajes directos, @, respuestas al bot, citas con texto. Las marcas de tiempo en milisegundos se leen como segundos. Bandeja de salida. | El id de grupo es el guild, así que los canales de un guild comparten una conversación. Se aplican los límites de la plataforma conectada. |
| WebChat (`webchat`) | El chat del panel, como mensajes directos. Citas e imágenes. Bandeja de salida, mostrada en directo o guardada en la conversación. | Solo uno a uno. |
| App de WeCom (`wecom`) | Mensajes directos, imágenes y voz con su transcripción. El modo de atención al cliente reenvía solo los mensajes del cliente, con la hora real de envío. Las respuestas se dividen por bytes. Bandeja de salida en modo app, una vez que alguien ha escrito desde que se inició AstrBot. | Solo mensajes directos, sin citas. El modo de atención al cliente no puede enviar sin que le pregunten. El Markdown se ve tal como se escribe. |
| Bot de IA de WeCom (`wecom_ai_bot`) | Grupos (WeCom entrega un mensaje de grupo solo cuando se hace @ al bot) y mensajes directos. Notas de voz, archivo y vídeo. Un turno enviado como una sola respuesta en streaming. | Solo responde dentro de la respuesta a un mensaje, así que no hay bandeja de salida ni menciones. La respuesta se renderiza como markdown. Define `wecom_ai_bot_name` en AstrBot para que "@bot" se quite del texto. |
| Cuenta oficial de WeChat (`weixin_official_account`) | Mensajes directos y voz con su transcripción. Un turno enviado como un solo mensaje. | El modo pasivo entrega una respuesta por mensaje del usuario, dentro de la ventana de 5 s de WeChat. El resto espera al siguiente mensaje del usuario, y un turno en que la persona no participa deja al usuario esperando (adaptador). Imágenes solo en modo activo. Sin bandeja de salida. |
| WeChat personal (`weixin_oc`) | Mensajes directos. Citas con su texto. Imágenes en línea. Voz con su transcripción. Indicador de escritura. Bandeja de salida. | Sin grupos. Tras volver a iniciar sesión no se puede contactar a nadie hasta que vuelva a escribir. |
| Cualquier otro adaptador | Se reenvía tal como lo entrega AstrBot. Menciones como un At. | No se declara bandeja de salida. |

## Bandeja de salida

Algunos mensajes no responden a nada: un saludo programado, la pregunta de seguimiento tras un rechazo o la excusa en un grupo cuando el modelo está caído. (La excusa de un mensaje directo vuelve en la respuesta del propio evento.) El agente pone estos mensajes en cola, y este plugin los consulta en `POST <personagent_url>/v1/outbox` con la misma firma que los eventos, así que el agente nunca tiene que alcanzar AstrBot. La bandeja de salida está activa por defecto (`outbox_enabled`).

- Cada entrega sale por la propia sesión de AstrBot de la conversación, en orden, y cada mensaje se envía como máximo una vez.
- Una entrega va solo a una sesión que el propio plugin obtuvo de un mensaje de esa misma conversación. Estas sesiones se guardan en el almacén de plugins de AstrBot, así que sobreviven a una recarga. Nada más que publique un evento al agente puede dirigir la bandeja de salida a otro chat, y el plugin rechaza tal entrega.
- El plugin vuelve a comprobar las listas de permitidos y `excluded_platforms` al enviar y rechaza una conversación que se haya quitado entretanto.
- Las plataformas que no pueden hablar primero (consulta la tabla) nunca reciben mensajes de la bandeja de salida, porque el plugin no la declara para sus conversaciones.
- Un agente sin bandeja de salida responde 404. El plugin vuelve a preguntar cada diez minutos.

El agente conoce este AstrBot por `connector_id`, que el plugin genera una vez y conserva. Dos hosts de AstrBot que hablan con un agente necesitan id distintos.

## Autenticación de solicitudes

Cuando `connector_token` está definido, cada solicitud lleva cuatro cabeceras:

- `X-Personagent-Token`: el token.
- `X-Personagent-Timestamp`: segundos unix.
- `X-Personagent-Nonce`: un valor aleatorio nuevo.
- `X-Personagent-Signature`: `sha256=` seguido del HMAC-SHA256 en hexadecimal, con el token como clave, de `timestamp + "." + nonce + "." + body`.

El cuerpo es JSON canónico: UTF-8, claves ordenadas, separadores compactos y caracteres no ASCII sin escapar. La firma cubre esos bytes exactos, así que un proxy no debe reescribir el cuerpo. El agente rechaza una firma incorrecta, un nonce reutilizado o una marca de tiempo a más de cinco minutos de su propio reloj. Mantén los dos relojes sincronizados.

El cuerpo también lleva la hora del mensaje según el adaptador como `sent_at`. El agente la comprueba aparte con `CONNECTOR_MAX_EVENT_AGE_S` (24 horas por defecto), así que un evento antiguo reenviado con una firma nueva se sigue rechazando. El plugin no reenvía un mensaje cuyo adaptador no da una marca de tiempo válida, y AstrBot lo maneja como siempre.

## Identidades en el lado del agente

El agente antepone a cada id reenviado su plataforma, como `<platform>:<raw id>` (por ejemplo `telegram:12345`), así que los id de distintas plataformas nunca chocan. Las plataformas listadas en `CONNECTOR_QQ_PLATFORMS` conservan id sin prefijo. `ADMIN_IDS`, `ACCESS_GROUPS` y `ACCESS_DM_USERS` del agente aceptan id en la misma forma. Por ejemplo, `ADMIN_IDS=telegram:12345` hace administradora a esa cuenta en Telegram, en grupos y mensajes directos. Una plataforma con entradas en `ACCESS_GROUPS` o `ACCESS_DM_USERS` queda filtrada por el agente además de por las listas de permitidos de este plugin.

## Solución de problemas

Las líneas del plugin en el registro de AstrBot empiezan por `personagent:`.

| Mensaje de registro | Qué hacer |
| --- | --- |
| `refusing unsafe personagent_url` | `personagent_url` es HTTP sin cifrar hacia otro host, o HTTPS sin `connector_token`. Consulta [Dónde puede ejecutarse el agente](#dónde-puede-ejecutarse-el-agente). |
| `agent refused the request (403): invalid, stale, or replayed request envelope` | `connector_token` está vacío o no coincide con el `CONNECTOR_TOKEN` del agente, los dos relojes difieren más de cinco minutos o un proxy cambió el cuerpo. Si el registro del agente dice `connector replay guard full`, espera a que se vacíe. |
| `agent refused the request (403): stale or invalid sent_at` | El mensaje es más antiguo que `CONNECTOR_MAX_EVENT_AGE_S` del agente. Suele ocurrir después de que AstrBot entregue mensajes atrasados. |
| `agent refused the request (403): authentication required` o `... only local requests accepted` | El agente no tiene `CONNECTOR_TOKEN` y la solicitud no es local. Define el mismo token en ambos lados. |
| `agent at capacity (429)` | El agente ya ejecutaba `CONNECTOR_MAX_INFLIGHT` turnos y siguió rechazando el mensaje tras los reintentos, así que respondió el modelo propio de AstrBot. Sube `CONNECTOR_MAX_INFLIGHT` si ocurre a menudo. |
| `agent rejected the body as too large (413)` | Suele ser una imagen grande en línea. Sube `SERVER_MAX_BODY_BYTES` del agente. |
| `agent rejected the event schema (400)` | El evento no tenía id de mensaje o de remitente (algunos adaptadores los omiten), o este plugin tiene un error. Infórmalo con la línea del registro. |
| `timed out waiting for the agent` | Consulta [Tiempos de espera](#tiempos-de-espera). |
| `dropping event without a valid time the platform sent it` | El adaptador no dio marca de tiempo. AstrBot maneja ese mensaje por sí mismo. |
| `agent request failed: ...` o `agent request failed (<status>)` | Suele ser que el agente no se está ejecutando o `personagent_url` es incorrecto. Un 404 significa una ruta incorrecta: `personagent_url` es la URL base, sin `/v1/events`. Un 500 significa que el agente falló, así que revisa su registro. |
| `outbox off: ...` | La bandeja de salida sigue la misma regla de `personagent_url` que los eventos. Consulta la primera fila. |
| `outbox: agent has no outbox (turned off, or an older version); retrying in 10 minutes` | `CONNECTOR_OUTBOX_ENABLED` del agente está desactivado. |
| `outbox: outbox pull refused (403)` o `outbox pull failed: ...` | Las mismas causas que para los eventos: el token, los relojes o que el agente no se esté ejecutando. El plugin espera hasta un minuto entre intentos. |
| `outbox: no running platform '<id>'` | Una entrega para un adaptador desactivado o renombrado en AstrBot. El plugin lo comunica al agente como fallido. |
| `could not store connector_id` | Falló el almacén de plugins de AstrBot. Define `connector_id` tú mismo, o el agente verá un AstrBot nuevo tras cada reinicio. |

Si el modelo propio de AstrBot responde de repente con otra voz, el plugin no alcanzó al agente o el agente no reclamó la conversación. Revisa la tabla de arriba y luego ejecuta `personagent doctor`. Si la página local inició el agente, abre allí **Actividad** para ver si llegó el mensaje y por qué la persona guardó silencio. Si lo iniciaste con `personagent run`, lee su terminal.

Si el registro del propio agente dice que el conector envía `X-Personagent-Token` pero `CONNECTOR_TOKEN` está vacío, el agente está ignorando el token. Define el mismo valor en el `.env` del agente.

En QQ, Telegram, Discord, KOOK, QQ oficial y Misskey, la hora del mensaje es la de la plataforma, no la hora en que AstrBot lo recibió. Cuando AstrBot ha estado caído más tiempo que `CONNECTOR_MAX_EVENT_AGE_S` del agente, el agente rechaza por antiguos los mensajes atrasados que entrega AstrBot.

## Limitación conocida: menciones de Telegram

El adaptador de Telegram de AstrBot identifica a un remitente por id numérico de usuario (`telegram:<numeric id>`), pero identifica una mención `@username` en un mensaje solo por nombre de usuario. El plugin reescribe un nombre de usuario mencionado al id numérico de quien lo usa una vez que esa persona ha escrito desde que se inició AstrBot. Hasta entonces, la mención llega al agente con el nombre de usuario.

Las respuestas mencionan a alguien por nombre de usuario, o con un enlace `tg://user` si no tiene. El plugin no menciona a nadie que no haya visto desde que se inició AstrBot.
