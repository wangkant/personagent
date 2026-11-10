# astrbot_plugin_personagent

[English](README.md) · [简体中文](README.zh-CN.md) · [繁體中文](README.zh-TW.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · Español · [Français](README.fr.md) · [Deutsch](README.de.md) · [Português (Brasil)](README.pt-BR.md) · [Русский](README.ru.md)


Este complemento de [AstrBot](https://github.com/AstrBotDevs/AstrBot) conecta AstrBot con [personagent](https://github.com/wangkant/personagent). Reenvía cada mensaje permitido al agente y devuelve las respuestas del agente al chat.

## ¿Necesita este complemento?

No es necesario para QQ, WeChat, Telegram ni Discord. personagent conecta estas plataformas por sí mismo, sin AstrBot. Ejecute `personagent` para abrir su página local y añádalas en **Conectar plataformas**.

Este complemento es necesario cuando AstrBot gestiona la conversación. Esto ocurre en dos casos.

- **Se añade otra plataforma en la página de personagent.** KOOK, Feishu/Lark, DingTalk, Slack, el bot de IA de WeCom, Mattermost, Misskey y las plataformas de Avanzado pasan todas por AstrBot. La página descarga y ejecuta un AstrBot por usted e instala este complemento en él, por lo que no es necesario hacer nada aquí.
- **Ya ejecuta un AstrBot** con sus propias plataformas y complementos. Instale el complemento como se describe a continuación.

## Funcionamiento

- Recibe mensajes de grupo y mensajes directos de todos los adaptadores de plataforma de AstrBot (Telegram, Discord, Slack, QQ...), salvo los de `excluded_platforms`.
- Reenvía los mensajes de los grupos y remitentes de las listas de permitidos al `POST /v1/events` del agente como un evento independiente de la plataforma. Lee cada plataforma tal como la entrega su adaptador, incluidos el destinatario, lo que se citó, los stickers, las imágenes, las notas de voz y la hora de envío que indica la plataforma.
- Devuelve las respuestas del agente a través de AstrBot en la forma que espera cada plataforma. Las respuestas pueden incluir texto e imágenes y, en los chats de grupo, una mención cuando el agente la solicita.
- Consulta la bandeja de salida del agente para entregar los mensajes que este envía sin que se le pregunte, como un saludo programado, una pregunta de seguimiento o la disculpa que publica en un grupo cuando su modelo no está disponible. Consulte [Bandeja de salida](#bandeja-de-salida).
- Detiene el flujo propio de AstrBot cuando el agente asume la conversación (`block_default`), de modo que el modelo integrado de AstrBot nunca responda en lugar del personaje.

El personaje, la memoria, la agrupación de mensajes (debounce) y la simulación de escritura se ejecutan en el agente. Este complemento es un conector tal como lo define el [`docs/connectors.md`](https://github.com/wangkant/personagent/blob/main/docs/connectors.es.md) del agente.

## Instalación en un AstrBot propio

Se requiere AstrBot, iniciado al menos una vez para que exista su carpeta de datos, y personagent (`python -m pip install personagent`; consulte su README).

### Con la configuración de personagent

```bash
personagent connect astrbot
```

El comando busca primero la carpeta de datos de AstrBot, la que contiene `cmd_config.json`, `plugins/` y `config/`. Si no encuentra ninguna, ofrece descargar AstrBot. A continuación, pregunta si AstrBot se ejecuta en Docker, a qué plataforma de chat se une el bot (con el token de esa plataforma cuando AstrBot todavía lo necesite), los grupos, el administrador y quién puede enviar mensajes directos al bot. Para QQ a través de NapCat, también pregunta el número de la cuenta del bot. Por último, copia este complemento, genera un token compartido, lo escribe en ambos lados y escribe las listas de permitidos. `personagent init --terminal` ofrece el mismo paso al final.

Para omitir las preguntas, indique la carpeta de datos:

```bash
personagent connect astrbot <AstrBot data dir>        # add --qq to route QQ (NapCat) as well
```

Ejecutado de esta forma, una primera conexión deja las listas de permitidos **vacías**, y usted las completa en los ajustes del complemento. `personagent connect astrbot --help` enumera las opciones que, además, activan una plataforma en AstrBot.

Puede volver a ejecutar el comando en cualquier momento. Conserva las listas de permitidos, las demás plataformas excluidas y cualquier `personagent_url` que este complemento acepte (consulte [Dónde puede ejecutarse el agente](#dónde-puede-ejecutarse-el-agente)). Un `personagent_url` que el complemento rechazaría se sustituye por el valor predeterminado de bucle local. El enrutamiento de QQ solo cambia cuando se indica `--qq` o `--no-qq`, y `CONNECTOR_QQ_PLATFORMS` del agente se ajusta en consecuencia. Cuando el comando pregunta, las listas actuales son los valores predeterminados: pulse Enter para conservar una o escriba `-` para vaciarla.

A continuación, reinicie AstrBot e inicie el agente (consulte [Comprobar que funciona](#comprobar-que-funciona)).

### Desde la WebUI de AstrBot

1. Descargue `astrbot_plugin_personagent.zip` de la [última versión de personagent](https://github.com/wangkant/personagent/releases/latest).
2. Súbalo en **Install from File**, en la página de complementos de AstrBot.
3. Defina `connector_token` con el `CONNECTOR_TOKEN` del `.env` de personagent y complete las listas de permitidos como se describe a continuación.
4. Si AstrBot se ejecuta en un equipo distinto del de personagent, defina `personagent_url` con una dirección HTTPS (consulte [Dónde puede ejecutarse el agente](#dónde-puede-ejecutarse-el-agente)).

Para actualizar, suba el zip de la versión más reciente de la misma forma. AstrBot 4.29 y las versiones posteriores sustituyen la copia instalada. En versiones anteriores, desinstale primero el complemento y deje **Also delete plugin configuration file** sin marcar.

### Instalación manual

1. Copie esta carpeta en `<AstrBot data dir>/plugins/astrbot_plugin_personagent/`.
2. Reinicie AstrBot o vuelva a cargar los complementos en su WebUI. AstrBot instala `requirements.txt`, que solo incluye `httpx`.
3. Abra los ajustes del complemento en la WebUI. Se guardan en `<AstrBot data dir>/config/astrbot_plugin_personagent_config.json`.
   - Añada a `groups` los ID de los grupos en los que puede participar el personaje.
   - Añada a `dm_users` los ID de los remitentes cuyos mensajes directos puede responder.
   - Si el `.env` del agente define `CONNECTOR_TOKEN`, indique el mismo valor en `connector_token`. Es obligatorio cuando el agente está en otro host.
   - Deje `personagent_url` con su valor predeterminado cuando el agente se ejecute en el mismo host con el `SERVER_PORT=8080` predeterminado.

El complemento **deniega de forma predeterminada**. Con listas vacías no reenvía nada, y AstrBot se comporta como si el complemento no estuviera instalado. Escriba los ID tal como los muestra AstrBot; envíe `/sid` en un chat para consultarlos. Un ID sin prefijo coincide en todos los adaptadores. `qq_official:ID` coincide solo en ese adaptador, y `qq_official:*` reenvía todas las conversaciones de ese tipo en él.

Un `*` aislado en `groups` o `dm_users` reenvía todas las conversaciones de ese tipo en todos los adaptadores y las marca con `prefiltered: false`. En ese caso, deciden únicamente `ACCESS_GROUPS` y `ACCESS_DM_USERS` del propio agente. El agente rechaza una plataforma que no tenga entradas en ellos, salvo los grupos de QQ, a los que responde a menos que `ACCESS_GROUPS` incluya alguno.

### Comprobar que funciona

1. Inicie el agente con `personagent run`, que solo inicia el servidor. Su aviso inicial debe mostrar `agent: on`.
2. Escriba el nombre del bot (el `PERSONA_NAME` del agente) en un grupo permitido.

Si no llega ninguna respuesta, busque las líneas `personagent:` en el registro de AstrBot, lea lo que `personagent run` imprimió tras su aviso inicial y consulte [Solución de problemas](#solución-de-problemas).

## Configuración

| Clave | Tipo | Predeterminado | Descripción |
| --- | --- | --- | --- |
| `personagent_url` | string | `http://127.0.0.1:8080` | URL base del agente. El complemento añade `/v1/events` y `/v1/outbox`. Debe ser de bucle local o HTTPS con `connector_token` definido. |
| `connector_token` | string | `""` | Secreto compartido. Debe coincidir con el `CONNECTOR_TOKEN` del agente. Obligatorio para cualquier `personagent_url` que no sea de bucle local. |
| `timeout_s` | int | `420` | Segundos de espera en cada intento. Consulte [Tiempos de espera](#tiempos-de-espera). |
| `excluded_platforms` | list | `["aiocqhttp"]` | Nombres de adaptadores que nunca se reenvían. Quite `aiocqhttp` para enrutar QQ (NapCat) a través de este complemento. Consulte [QQ a través de NapCat](#qq-a-través-de-napcat). |
| `groups` | list | `[]` | ID de los grupos que se reenvían. Vacío no reenvía ningún grupo. `adapter:ID` o `adapter:*` limita una entrada a un adaptador. Un `*` aislado reenvía todos los grupos sin filtrar. |
| `dm_users` | list | `[]` | ID de los remitentes cuyos mensajes directos se reenvían. Vacío no reenvía ninguno. `adapter:ID` o `adapter:*` limita una entrada a un adaptador. Un `*` aislado reenvía todos los mensajes directos sin filtrar. |
| `block_default` | bool | `true` | Detiene el flujo de AstrBot cuando el agente asume la conversación. |
| `forward_quoted_text` | bool | `true` | Envía el texto y el autor de un mensaje citado junto con su ID, cuando la plataforma los proporciona. Mientras esté activo y `quote_max_chars` sea mayor que 0, cada evento declara la capacidad `quote_text`. |
| `quote_max_chars` | int | `200` | Longitud máxima del texto citado que se envía. Las citas más largas se recortan. |
| `max_inline_image_bytes` | int | `4000000` | Tamaño máximo de una imagen enviada en línea. Las imágenes que el agente no puede obtener por sí mismo (Telegram, archivos locales, direcciones privadas) se envían en línea. Una imagen de mayor tamaño llega como la nota `(sent an image)`. Manténgalo por debajo de `VISION_MAX_IMAGE_BYTES` del agente. |
| `outbox_enabled` | bool | `true` | Consulta y entrega la bandeja de salida del agente. Consulte [Bandeja de salida](#bandeja-de-salida). |
| `outbox_wait_s` | int | `25` | Tiempo máximo que una consulta de la bandeja de salida puede esperar en el agente, con un máximo de 30. |
| `connector_id` | string | `""` | Nombre de este AstrBot para el agente. Si está vacío, se genera uno una vez y se conserva. Dos hosts de AstrBot requieren nombres distintos. |

### Dónde puede ejecutarse el agente

- **El mismo host**, o un contenedor que comparte el espacio de nombres de red del host o utiliza la red del host: conserve el `personagent_url` de bucle local predeterminado.
- **Otro contenedor u otro host**: utilice un `personagent_url` HTTPS y defina el mismo secreto no vacío en `connector_token` y en el `CONNECTOR_TOKEN` del agente. También es válido un túnel privado que termine en una URL de bucle local accesible para AstrBot. En ese caso, defina también el mismo token en ambos lados, ya que el agente rechaza las solicitudes sin token que llegan a través de un proxy.

El complemento rechaza `http://` sin cifrar hacia cualquier destino que no sea de bucle local, como `http://host.docker.internal:8080`, incluso con token. En ese caso, cada mensaje registra `refusing unsafe personagent_url` y responde el modelo propio de AstrBot.

**AstrBot en Docker.** Dentro de un contenedor, `127.0.0.1` es el propio contenedor, por lo que el `personagent_url` predeterminado no llega a ningún destino. Hay dos opciones:

- Asigne a AstrBot la red del host: `network_mode: host` en su archivo compose o `docker run --network host`. Docker Desktop requiere la versión 4.34 o posterior con la red del host (host networking) activada. Un contenedor de NapCat en el mismo archivo compose también requiere la red del host.
- Coloque el agente detrás de HTTPS y defina esa dirección como `personagent_url` (`personagent connect astrbot <dir> --url https://...`).

El agente escucha en `127.0.0.1:8080` de forma predeterminada. Si se define su `SERVER_HOST` con una dirección que no sea de bucle local, el agente no se inicia salvo que `CONNECTOR_TOKEN` esté definido. Defina el token antes de colocar un proxy o un túnel delante del agente, incluso en un único host.

### Tiempos de espera

Cada solicitud dura lo mismo que el turno del agente, que consiste en una breve agrupación de mensajes más cada llamada al modelo y cada reintento. Si se agota `timeout_s`, el agente completa igualmente el turno y conserva lo aprendido, pero la respuesta se pierde y el modelo propio de AstrBot responde al mensaje.

Mantenga 3 × `LLM_TIMEOUT_S` del agente por debajo de `timeout_s`. Las llamadas al modelo de un turno comparten 1,5 × `LLM_TIMEOUT_S`, reintentos incluidos, y un mensaje espera primero al turno que se estaba procesando cuando llegó. Con el valor predeterminado del agente (`LLM_TIMEOUT_S=120`), son 360 s, que el `timeout_s` predeterminado de 420 cubre. Si aumenta `LLM_TIMEOUT_S` en el agente, aumente también `timeout_s`.

El complemento reintenta un 429 o un 500 del agente hasta dos veces, respetando `Retry-After` en un 429, mientras la solicitud firmada siga siendo reciente.

### `block_default` y propiedad

El complemento detiene el flujo de AstrBot cada vez que el agente indica que la conversación le corresponde (`owned: true`), haya respondido o no, de modo que el modelo integrado de AstrBot no intervenga en los turnos en los que el personaje no participa.

Los errores de transporte, las respuestas no válidas y las conversaciones que el agente rechaza continúan por el flujo normal de AstrBot. Si la respuesta del agente no tiene el campo `owned`, el complemento utiliza `handled`.

## QQ a través de NapCat

personagent conecta los bots oficiales de QQ por sí mismo, sin AstrBot. Esta sección trata únicamente de una cuenta de QQ ejecutada con NapCat (u otra implementación de OneBot v11) detrás del adaptador `aiocqhttp` de AstrBot. Cuando se añade OneBot v11 en la propia página de personagent, esta quita `aiocqhttp` de `excluded_platforms` y define `CONNECTOR_QQ_PLATFORMS` por usted.

1. Quite `aiocqhttp` de `excluded_platforms` y añada los grupos de QQ a `groups`.
2. En el `.env` del agente, defina `CONNECTOR_QQ_PLATFORMS=aiocqhttp` y `QQ_BOT_ID` (el número de la cuenta del bot).
3. Opcional: defina `QQ_ONEBOT_URL` del agente con el servidor HTTP de NapCat. Esto activa el barrido de recuperación de menciones perdidas, que también requiere `QQ_BOT_ID`. Los mensajes proactivos, la pregunta de seguimiento tras un rechazo y la disculpa en un grupo cuando el modelo falla pasan por la [bandeja de salida](#bandeja-de-salida) de este complemento mientras este la consulte. En caso contrario, pasan directamente por NapCat, siempre que esa URL esté definida.
4. Si NapCat también publica en `/v1/onebot` del agente, desactívelo. Esa vía está obsoleta, y ejecutar ambas entrega cada mensaje dos veces.

`personagent connect astrbot <data dir> --qq` quita `aiocqhttp` de `excluded_platforms` y define `CONNECTOR_QQ_PLATFORMS`. Si se ejecuta sin carpeta, también pregunta `QQ_BOT_ID`. La guía de despliegue también describe esta vía: [docs/deploy.md](https://github.com/wangkant/personagent/blob/main/docs/deploy.es.md#qq-a-través-de-napcat-onebot).

No omita `CONNECTOR_QQ_PLATFORMS=aiocqhttp`. Sin este ajuste, el agente archiva los chats de QQ con ID con el prefijo `aiocqhttp:`, lo aprendido con los ID de QQ sin prefijo deja de coincidir y los registros no se pueden volver a indexar posteriormente.

Como los ID de QQ siguen sin prefijo, los ajustes de QQ del propio agente siguen siendo aplicables. Las entradas de QQ de `ACCESS_GROUPS` filtran los grupos (sin entradas, se admiten todos los grupos de QQ), y los mensajes directos solo se responden al administrador indicado en `ADMIN_IDS` o a quienes figuran en `ACCESS_DM_USERS`. El asistente de configuración escribe en el `.env` del agente los grupos de QQ que usted indique. Para añadir un grupo de QQ más adelante, añádalo tanto a `groups` como a `ACCESS_GROUPS`, o no incluya ningún grupo de QQ en `ACCESS_GROUPS`.

Antes de que AstrBot gestione un grupo de QQ activo, revise dos ajustes de AstrBot. Ambos se ejecutan antes que los controladores de los complementos.

- `platform_settings.rate_limit` es, de forma predeterminada, de 30 mensajes cada 60 s. Los mensajes que superan el límite se retrasan, no se descartan. Aumente o desactive el límite.
- `content_safety.internal_keywords` está activo de forma predeterminada y descarta los mensajes que coinciden con su lista de palabras clave, incluidos los que el personaje habría respondido. Revise la lista.

## Plataformas

El agente utiliza un formato independiente de la plataforma, y el complemento lo traduce en los extremos con los mecanismos propios de cada plataforma. La tabla siguiente se comprobó con los adaptadores de AstrBot 4.25.5.

En todas las plataformas:

- Solo se reenvían los mensajes escritos por una persona. Los avisos de QQ (toques, retiradas, incorporaciones) y las solicitudes, así como las incorporaciones y los cambios de tema de Slack, no son turnos.
- Los vídeos, los archivos y los mensajes de voz llegan como una nota a la que el personaje puede reaccionar, como `(sent a video)`, `(sent a file: deck.pdf)` o `(sent a voice message)`, con la transcripción de la plataforma cuando existe.
- Los mensajes citados incluyen su texto y su autor cuando la plataforma los proporciona (`forward_quoted_text`).
- Cuando el adaptador la conserva, la hora del mensaje es la de la plataforma y no la hora en que AstrBot lo recibió.
- Las respuestas se dividen por debajo del límite de longitud de la plataforma, contando la mención y los caracteres de escape tal como los cuenta la plataforma. Nunca se convierten en una imagen de texto y nombran a las personas tal como lo hace la plataforma.
- La bandeja de salida solo se utiliza cuando la plataforma permite enviar mensajes sin que se le pregunte.

| Plataforma (adaptador) | Funciones compatibles | Limitaciones de la plataforma |
| --- | --- | --- |
| QQ a través de OneBot (`aiocqhttp`) | Grupos y mensajes directos. @ y respuesta al bot, también cuando el adaptador no pudo resolver el @. Nombres de caras, stickers de tienda (`mface`) e imágenes marcadas como stickers. Menciones como un @ real de QQ, seguido de un espacio. Las respuestas largas se dividen por debajo del `forward_threshold` de AstrBot, de modo que ninguna se convierte en una tarjeta de reenvío combinado. Bandeja de salida. | El Markdown se muestra tal como se escribe. |
| QQ oficial (`qq_official`, `qq_official_webhook`) | Mensajes de grupo que mencionan al bot con @ y mensajes directos. Caras como `[表情:name]`. Las respuestas solicitan texto sin formato en lugar del markdown del adaptador. | Los grupos entregan solo los mensajes que mencionan al bot con @, por lo que el personaje no puede seguir una conversación. Sin citas, sin nombres (solo openids) y sin menciones en las respuestas. Solo se puede responder en los 5 minutos siguientes a un mensaje, por lo que no hay bandeja de salida. |
| Telegram (`telegram`) | Grupos, temas (`<chat>#<thread>`) y mensajes directos. Respuesta al bot para cualquier tipo de mensaje, sin el prefijo de activación `/@bot` del adaptador. Emoji de los stickers, además de la imagen de los estáticos. Las imágenes se obtienen mediante el bot del adaptador, de modo que el token del bot nunca sale de AstrBot. Un nombre de usuario mencionado se convierte en el ID numérico de la persona una vez que esta ha escrito. Las respuestas mencionan por nombre de usuario, o con un enlace `tg://user` a quien no lo tiene, y muestran `*`, `_` y caracteres similares tal como se escriben. Bandeja de salida. | Con el modo de privacidad de BotFather activo (el valor predeterminado), los grupos entregan solo comandos, @menciones y respuestas al bot. Desactívelo para que el personaje pueda seguir la conversación. Los stickers animados y de vídeo no se pueden ver. |
| Discord (`discord`) | Canales e hilos como grupos, y mensajes directos. Un `@bot` inicial (que el adaptador quita), una mención a uno de los roles del bot y las respuestas al bot se dirigen a él. Citas con su texto. Stickers. Adjuntos de voz y vídeo como notas. Menciones como `<@id>`, con `@everyone` y `@here` desactivados. Las respuestas se dividen a los 2000 caracteres. Bandeja de salida, también en mensajes directos. | Requiere el intent Message Content. |
| Slack (`slack`) | Canales y mensajes directos. Una respuesta en un hilo bajo el mensaje del bot se dirige a él. Enlaces desplegados. Los ID de mensaje son el `ts` de Slack. Menciones como `<@id>`. `&`, `<` y `>` escapados para que el texto no pueda notificar a un canal. Las respuestas se dividen a los 3000 caracteres. Bandeja de salida. | Una respuesta en un hilo no incluye el texto del mensaje principal. Sin indicador de escritura para bots. Las respuestas se publican en el canal, no en el hilo (adaptador). |
| KOOK (`kook`) | Canales y mensajes directos. @ y menciones a un rol que tiene el bot. Citas cuando KOOK las incluye. Emoji `(emj)` y la hora real de envío. Menciones en línea en el texto, con las etiquetas de estilo `(met)` del texto del personaje desactivadas. Imágenes enviadas como archivo, ya que el adaptador solo sube JPEG en base64. Bandeja de salida. | El adaptador de AstrBot descarta los mensajes simples de imagen, archivo, voz y vídeo (no las tarjetas) antes de que los vea ningún complemento. Sin indicador de escritura. |
| Lark / Feishu (`lark`) | Grupos y mensajes directos. @ y respuestas al bot (Lark indica la aplicación como remitente). Citas con su texto. Stickers como emoji. Bandeja de salida. | Sin el permiso "leer todos los mensajes del grupo", solo llegan los mensajes con @. Cada respuesta cita el mensaje al que responde y el markdown se representa con formato (adaptador). Los nombres son prefijos de ID. |
| DingTalk (`dingtalk`) | Grupos y mensajes directos. Las imágenes, que el adaptador entrega como archivos locales, se envían en línea. Vídeos como nota. Bandeja de salida. Los mensajes directos llegan a quienes han escrito al bot. | Los grupos entregan solo los mensajes que mencionan al bot con @. Sin citas, menciones ni respuestas con cita en las respuestas. Cada respuesta es markdown con el título "AstrBot" (adaptador). |
| LINE (`line`) | Grupos, salas y mensajes directos. @ al bot. ID de las citas. Palabras clave de los stickers. Los mensajes de un turno se envían en una sola llamada, en grupos de cinco, para que los cubra el reply token gratuito. Bandeja de salida, que cuenta para la cuota de push. | LINE no envía el texto citado. Sin menciones en las respuestas (adaptador). Las imágenes salientes requieren un `callback_api_base` HTTPS público. Los nombres son prefijos de ID. |
| Mattermost (`mattermost`) | Canales y mensajes directos. @ al bot. La raíz del hilo como cita. Imágenes en línea. Menciones por nombre de usuario una vez que la persona ha escrito. `@channel`, `@all` y `@here` desactivados. Las respuestas se dividen a los 4000 caracteres. Bandeja de salida. | El texto citado requeriría una consulta que el complemento no realiza. Sin indicador de escritura. |
| Misskey (`misskey`) | Mensajes directos de chat y salas, con `@bot` en cualquier parte de un mensaje de sala. Menciones como `@user@host` una vez que la persona ha escrito, con cualquier otro `@` del texto del personaje desactivado. Las respuestas se dividen a los 3000 caracteres. Bandeja de salida para chat y salas. | Las notas (publicaciones públicas) no se reenvían, ya que AstrBot las clasifica como eventos del sistema y una respuesta sería pública. `unique_session` impide el funcionamiento de las salas (adaptador). |
| Satori (`satori`) | Lo que conecte el backend de Satori: grupos, mensajes directos, @, respuestas al bot y citas con texto. Las marcas de tiempo en milisegundos se leen como segundos. Bandeja de salida. | El ID de grupo es el guild, por lo que los canales de un guild comparten una conversación. Se aplican los límites de la plataforma conectada. |
| WebChat (`webchat`) | El chat del panel, como mensajes directos. Citas e imágenes. Bandeja de salida, mostrada en directo o guardada en la conversación. | Solo conversaciones individuales. |
| Aplicación de WeCom (`wecom`) | Mensajes directos, imágenes y voz con su transcripción. El modo de atención al cliente reenvía solo los mensajes del cliente, con la hora real de envío. Las respuestas se dividen por bytes. Bandeja de salida en modo aplicación, una vez que alguien ha escrito desde que se inició AstrBot. | Solo mensajes directos, sin citas. El modo de atención al cliente no puede enviar mensajes sin que se le pregunte. El Markdown se muestra tal como se escribe. |
| Bot de IA de WeCom (`wecom_ai_bot`) | Grupos (WeCom entrega un mensaje de grupo solo cuando se menciona al bot con @) y mensajes directos. Notas de voz, archivos y vídeos. Un turno enviado como una única respuesta en streaming. | Solo responde dentro de la respuesta a un mensaje, por lo que no hay bandeja de salida ni menciones. La respuesta se representa como markdown. Defina `wecom_ai_bot_name` en AstrBot para que "@bot" se quite del texto. |
| Cuenta oficial de WeChat (`weixin_official_account`) | Mensajes directos y voz con su transcripción. Un turno enviado como un único mensaje. | El modo pasivo entrega una respuesta por cada mensaje del usuario, dentro del margen de 5 s de WeChat. El resto espera al siguiente mensaje del usuario, y un turno en el que el personaje no participa deja al usuario en espera (adaptador). Imágenes solo en modo activo. Sin bandeja de salida. |
| WeChat personal (`weixin_oc`) | Mensajes directos. Citas con su texto. Imágenes en línea. Voz con su transcripción. Indicador de escritura. Bandeja de salida. | Sin grupos. Tras volver a iniciar sesión, no se puede contactar con nadie hasta que esa persona vuelva a escribir. |
| Cualquier otro adaptador | Se reenvía tal como lo entrega AstrBot. Menciones como un At. | No se declara bandeja de salida. |

## Bandeja de salida

Algunos mensajes no responden a ningún otro: un saludo programado, la pregunta de seguimiento tras un rechazo o la disculpa en un grupo cuando el modelo no está disponible. (La disculpa en un mensaje directo se devuelve en la respuesta del propio evento.) El agente pone estos mensajes en cola, y este complemento los consulta en `POST <personagent_url>/v1/outbox` con la misma firma que los eventos, de modo que el agente nunca necesita acceder a AstrBot. La bandeja de salida está activa de forma predeterminada (`outbox_enabled`).

- Cada entrega se envía a través de la propia sesión de AstrBot de la conversación, en orden, y cada mensaje se envía como máximo una vez.
- Una entrega solo se dirige a una sesión que el propio complemento obtuvo de un mensaje de esa misma conversación. Estas sesiones se guardan en el almacén de complementos de AstrBot, por lo que se conservan tras una recarga. Ningún otro remitente que publique un evento en el agente puede dirigir la bandeja de salida a otro chat, y el complemento rechaza una entrega de ese tipo.
- El complemento vuelve a comprobar las listas de permitidos y `excluded_platforms` al enviar y rechaza una conversación que se haya quitado entretanto.
- Las plataformas que no pueden hablar primero (consulte la tabla) nunca reciben mensajes de la bandeja de salida, ya que el complemento no la declara para sus conversaciones.
- Un agente sin bandeja de salida responde 404. El complemento vuelve a consultar cada diez minutos.

El agente identifica este AstrBot por `connector_id`, que el complemento genera una vez y conserva. Dos hosts de AstrBot que se comunican con un mismo agente requieren ID distintos.

## Autenticación de solicitudes

Cuando `connector_token` está definido, cada solicitud incluye cuatro cabeceras:

- `X-Personagent-Token`: el token.
- `X-Personagent-Timestamp`: segundos unix.
- `X-Personagent-Nonce`: un valor aleatorio nuevo.
- `X-Personagent-Signature`: `sha256=` seguido del HMAC-SHA256 en hexadecimal, con el token como clave, de `timestamp + "." + nonce + "." + body`.

El cuerpo es JSON canónico: UTF-8, claves ordenadas, separadores compactos y caracteres no ASCII sin escapar. La firma cubre exactamente esos bytes, por lo que un proxy no debe reescribir el cuerpo. El agente rechaza una firma incorrecta, un nonce reutilizado o una marca de tiempo que difiera más de cinco minutos de su propio reloj. Mantenga ambos relojes sincronizados.

El cuerpo también incluye la hora del mensaje según el adaptador como `sent_at`. El agente la comprueba por separado con `CONNECTOR_MAX_EVENT_AGE_S` (24 horas de forma predeterminada), de modo que un evento antiguo reenviado con una firma nueva se sigue rechazando. El complemento no reenvía un mensaje cuyo adaptador no proporciona una marca de tiempo válida, y AstrBot lo gestiona de la forma habitual.

## Identidades en el lado del agente

El agente antepone a cada ID reenviado su plataforma, como `<platform>:<raw id>` (por ejemplo, `telegram:12345`), de modo que los ID de distintas plataformas nunca entran en conflicto. Las plataformas incluidas en `CONNECTOR_QQ_PLATFORMS` conservan los ID sin prefijo. `ADMIN_IDS`, `ACCESS_GROUPS` y `ACCESS_DM_USERS` del agente aceptan ID con la misma forma. Por ejemplo, `ADMIN_IDS=telegram:12345` convierte esa cuenta de Telegram en administrador, en grupos y mensajes directos. Una plataforma con entradas en `ACCESS_GROUPS` o `ACCESS_DM_USERS` queda filtrada por el agente, además de por las listas de permitidos de este complemento.

## Solución de problemas

Las líneas del complemento en el registro de AstrBot comienzan por `personagent:`.

| Mensaje de registro | Qué hacer |
| --- | --- |
| `refusing unsafe personagent_url` | `personagent_url` es HTTP sin cifrar hacia otro host, o HTTPS sin `connector_token`. Consulte [Dónde puede ejecutarse el agente](#dónde-puede-ejecutarse-el-agente). |
| `agent refused the request (403): invalid, stale, or replayed request envelope` | `connector_token` está vacío o no coincide con el `CONNECTOR_TOKEN` del agente, los dos relojes difieren en más de cinco minutos o un proxy modificó el cuerpo. Si el registro del agente indica `connector replay guard full`, espere a que se vacíe. |
| `agent refused the request (403): stale or invalid sent_at` | El mensaje es más antiguo que `CONNECTOR_MAX_EVENT_AGE_S` del agente. Suele ocurrir después de que AstrBot entregue mensajes acumulados. |
| `agent refused the request (403): authentication required` o `... only local requests accepted` | El agente no tiene `CONNECTOR_TOKEN` y la solicitud no es local. Defina el mismo token en ambos lados. |
| `agent at capacity (429)` | El agente ya estaba procesando `CONNECTOR_MAX_INFLIGHT` turnos y siguió rechazando el mensaje tras los reintentos, por lo que respondió el modelo propio de AstrBot. Aumente `CONNECTOR_MAX_INFLIGHT` si ocurre con frecuencia. |
| `agent rejected the body as too large (413)` | Suele deberse a una imagen grande en línea. Aumente `SERVER_MAX_BODY_BYTES` del agente. |
| `agent rejected the event schema (400)` | El evento no tenía ID de mensaje o de remitente (algunos adaptadores los omiten), o este complemento tiene un error. Notifíquelo junto con la línea del registro. |
| `timed out waiting for the agent` | Consulte [Tiempos de espera](#tiempos-de-espera). |
| `dropping event without a valid time the platform sent it` | El adaptador no proporcionó una marca de tiempo. AstrBot gestiona ese mensaje por sí mismo. |
| `agent request failed: ...` o `agent request failed (<status>)` | Normalmente, el agente no está en ejecución o `personagent_url` es incorrecto. Un 404 indica una ruta incorrecta: `personagent_url` es la URL base, sin `/v1/events`. Un 500 indica que el agente falló; revise su registro. |
| `outbox off: ...` | La bandeja de salida sigue la misma regla de `personagent_url` que los eventos. Consulte la primera fila. |
| `outbox: agent has no outbox (turned off, or an older version); retrying in 10 minutes` | `CONNECTOR_OUTBOX_ENABLED` del agente está desactivado. |
| `outbox: outbox pull refused (403)` o `outbox pull failed: ...` | Las mismas causas que para los eventos: el token, los relojes o que el agente no esté en ejecución. El complemento espera hasta un minuto entre intentos. |
| `outbox: no running platform '<id>'` | Una entrega para un adaptador desactivado o con otro nombre en AstrBot. El complemento lo comunica al agente como fallido. |
| `could not store connector_id` | Falló el almacén de complementos de AstrBot. Defina `connector_id` usted mismo; de lo contrario, el agente verá un AstrBot nuevo tras cada reinicio. |

Si el modelo propio de AstrBot responde de repente con otra voz, el complemento no llegó al agente o el agente no asumió la conversación. Revise la tabla anterior y, a continuación, ejecute `personagent doctor`. Si la página local inició el agente, abra allí **Actividad** para comprobar si llegó el mensaje y por qué el personaje guardó silencio. Si lo inició con `personagent run`, lea la salida de su terminal.

Si el registro del propio agente indica que el conector envía `X-Personagent-Token` pero `CONNECTOR_TOKEN` está vacío, el agente está ignorando el token. Defina el mismo valor en el `.env` del agente.

En QQ, Telegram, Discord, KOOK, QQ oficial y Misskey, la hora del mensaje es la de la plataforma, no la hora en que AstrBot lo recibió. Cuando AstrBot ha estado fuera de servicio más tiempo que `CONNECTOR_MAX_EVENT_AGE_S` del agente, el agente rechaza por antiguos los mensajes acumulados que entrega AstrBot.

## Limitación conocida: menciones de Telegram

El adaptador de Telegram de AstrBot identifica a un remitente por su ID numérico de usuario (`telegram:<numeric id>`), pero identifica una mención `@username` en un mensaje solo por el nombre de usuario. El complemento sustituye un nombre de usuario mencionado por el ID numérico de su titular una vez que esa persona ha escrito desde que se inició AstrBot. Hasta entonces, la mención llega al agente con el nombre de usuario.

Las respuestas mencionan a una persona por su nombre de usuario, o con un enlace `tg://user` si no lo tiene. El complemento no menciona a nadie que no haya visto desde que se inició AstrBot.
