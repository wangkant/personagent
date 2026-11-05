# Conector de Satori

[English](README.md) · [简体中文](README.zh-CN.md) · [繁體中文](README.zh-TW.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · Español · [Français](README.fr.md) · [Deutsch](README.de.md) · [Português (Brasil)](README.pt-BR.md) · [Русский](README.ru.md)


Este conector une [personagent](https://github.com/wangkant/personagent) con un servidor [Satori](https://satori.chat). Satori es un protocolo de chat multiplataforma. Un servidor como [Koishi](https://koishi.chat) (con su plugin `server-satori`), Chronocat o LLOneBot inicia sesión en las plataformas de chat, y un cliente como este recibe cada mensaje de cada sesión por un solo websocket. Así, un único proceso de conector lleva la persona a todas las plataformas para las que el servidor tiene adaptador.

Satori y Koishi son software de terceros. personagent no los necesita para QQ, WeChat, Telegram o Discord, que conecta por sí mismo, ni para las plataformas que su página local configura a través de AstrBot. Usa este conector si ya ejecutas Koishi, o si quieres una plataforma a la que solo llega Koishi.

El conector reenvía cada mensaje permitido al `POST /v1/events` del agente como evento neutro ([docs/connectors.md](../../docs/connectors.es.md)) y devuelve las respuestas por Satori. También recoge la bandeja de salida del agente, así que los mensajes programados, las preguntas de seguimiento y las excusas llegan al chat.

[satori-python](https://github.com/RF-Tar-Railt/satori-python) se ocupa del lado de Satori: el websocket, la lista de sesiones y la API HTTP. Este conector traduce entre Satori y el formato de eventos de personagent, y usa [`integrations/sdk/personagent_connector.py`](../sdk/personagent_connector.py) para las firmas y el bucle de la bandeja de salida.

## Configuración, con Koishi

1. **Koishi.** Instala Koishi con el lanzador de escritorio o con `npm init koishi@latest`. En su consola, añade y configura un adaptador para tu plataforma, como `adapter-telegram` o `adapter-discord`, y comprueba que el bot esté en línea. Activa los plugins `server` y `server-satori`. Koishi servirá entonces Satori en `http://127.0.0.1:5140/satori`. Dale a `server-satori` un `token` si algo que no sea esta máquina puede llegar a ese puerto.

   Koishi sigue ejecutando sus otros plugins. Si alguno también responde mensajes, como un modelo de chat o un plugin de respuestas, responderá junto a la persona, y el conector no puede silenciarlo. Desactiva ese plugin o exclúyelo de las conversaciones que reenvías.

2. **El agente.** Ejecuta personagent (`personagent run`, consulta su README). Si el conector y el agente están en hosts distintos, define `CONNECTOR_TOKEN` en el `.env` del agente y pon el agente detrás de HTTPS. Define el token antes de añadir cualquier proxy o túnel, incluso en un solo host.

3. **El conector.** El conector es un script de este repositorio, así que necesita una copia del repositorio (un clon o el ZIP de GitHub) y su propio entorno de Python, porque `satori-python` no es una dependencia de personagent. En un clon que ya tenga el `.venv` de personagent, instala en ese entorno:

   ```bash
   .venv/bin/python -m pip install -r integrations/satori/requirements.txt
   ```

   Si instalaste personagent desde PyPI con pip, o lo ejecutas con uvx, crea un venv aparte junto a la copia:

   ```bash
   python -m venv connector-venv
   connector-venv/bin/python -m pip install -r integrations/satori/requirements.txt
   ```

   En Windows, el intérprete es `.venv\Scripts\python.exe` o `connector-venv\Scripts\python.exe`. A continuación, copia el archivo de ajustes:

   ```bash
   cp integrations/satori/.env.example integrations/satori/.env
   ```

   En `integrations/satori/.env`, define la URL y el token del servidor Satori, la URL base y el `CONNECTOR_TOKEN` del agente, y las conversaciones que se reenvían (consulta [Listas de permitidos](#listas-de-permitidos)). Luego inicia el conector con el mismo intérprete:

   ```bash
   .venv/bin/python integrations/satori/satori_connector.py
   ```

   `--config FILE` lee otro archivo de ajustes. Cualquier ajuste también puede darse como variable de entorno, que tiene prioridad sobre el archivo.

4. **Comprueba que funciona.** Para cada bot del servidor, el registro muestra una línea como `Satori login telegram:7000 is ONLINE`. Menciona al bot en un grupo reenviado. El registro del agente muestra el turno, y la respuesta aparece en el chat. Si no pasa nada, define `SATORI_LOG_LEVEL=DEBUG`.

## Ajustes

| Ajuste | Predeterminado | Significado |
|---|---|---|
| `SATORI_URL` | `http://127.0.0.1:5140/satori` | El servidor Satori. El `/v1` final es opcional. |
| `SATORI_TOKEN` | | El token del servidor (en Koishi, `server-satori` → `token`). |
| `PERSONAGENT_URL` | `http://127.0.0.1:8080` | La URL base del agente. Se añaden `/v1/events` y `/v1/outbox`. |
| `CONNECTOR_TOKEN` | | El `CONNECTOR_TOKEN` del agente. |
| `SATORI_GROUPS` | | Grupos que se reenvían, como ids de canal o de servidor, opcionalmente `platform:id`. Vacío no reenvía ninguno, `*` reenvía todos. |
| `SATORI_DM_USERS` | | Personas cuyos mensajes directos se reenvían, como ids de usuario, opcionalmente `platform:id`. Vacío no reenvía ninguno, `*` reenvía todos. |
| `SATORI_PLATFORMS` | todas | Limita el conector a estas plataformas de Satori. |
| `SATORI_PLATFORM_NAMES` | `qq=qqbot` | Renombra las plataformas tal como las ve el agente: `satori_name=name, ...` |
| `SATORI_OUTBOX_ENABLED` | `true` | Recoger la bandeja de salida del agente. |
| `SATORI_CONNECTOR_ID` | a partir de `SATORI_URL` | El id de este conector en el agente. Mantenlo estable. |
| `SATORI_TIMEOUT_S` | `420` | Cuánto puede durar un turno. Mantenlo por encima de `LLM_TIMEOUT_S × (1 + LLM_MAX_RETRIES)` del agente. |
| `SATORI_INLINE_IMAGES_ENABLED` | `false` | Descargar las URL de imágenes públicas en el conector en lugar de pasar la URL al agente. |
| `SATORI_LOG_LEVEL` | `INFO` | |

La URL del agente debe ser una dirección de bucle local, o HTTPS con `CONNECTOR_TOKEN` definido. Si no, el conector se niega a iniciarse. Si `SATORI_TOKEN` fuera a enviarse por `http` sin cifrar a otro host, el conector registra una advertencia.

## Listas de permitidos

El conector deniega por defecto. Con listas vacías no reenvía nada.

- Un grupo es un canal de Satori. Se reenvía cuando su id de canal o de servidor está en `SATORI_GROUPS`. Por eso, en Discord o KOOK, un id de servidor admite todos los canales de ese servidor, y cada canal sigue siendo una conversación aparte.
- Un mensaje directo se reenvía cuando el id de usuario del remitente está en `SATORI_DM_USERS`.
- Una entrada puede nombrar su plataforma, como `telegram:-1001234` o `discord:4242`, y entonces solo coincide en esa plataforma. Una entrada sin plataforma coincide en todas.
- `*` reenvía todos los grupos (o todos los mensajes directos) y marca el evento con `prefiltered: false`. Entonces deciden `ACCESS_GROUPS` y `ACCESS_DM_USERS` del propio agente, y una plataforma sin entradas allí se rechaza.

El plugin `inspect` de Koishi muestra los ids de plataforma, canal, servidor y usuario de un mensaje.

## Nombres de plataforma y QQ

personagent guarda los ids como `<platform>:<id>`, donde la plataforma es la de la sesión de Satori (`telegram`, `discord`, `onebot`, etc.). La línea de registro del paso 4 la muestra. Hay dos casos especiales:

- **QQ a través de OneBot** (el `adapter-onebot` de Koishi, con NapCat o LLOneBot detrás) usa números de QQ como ids. Para conservar lo que el agente aprendió en un despliegue de QQ existente, añade la plataforma a `CONNECTOR_QQ_PLATFORMS` del agente (`CONNECTOR_QQ_PLATFORMS=onebot`). Sus ids se guardan entonces sin prefijo, como los números de QQ de NapCat, y se les aplican las entradas de QQ de `ACCESS_GROUPS` y `ACCESS_DM_USERS`. Hazlo solo con una plataforma cuyos ids sean realmente números de QQ.
- **La API oficial de bots de QQ** (el `adapter-qq` de Koishi) llama a su plataforma `qq`, pero sus ids son openids, no números de QQ. El conector renombra la plataforma a `qqbot`. `SATORI_PLATFORM_NAMES` reemplaza ese cambio de nombre. personagent también puede conectar bots oficiales de QQ por sí mismo, sin Koishi.

## Qué funciona

| Función | Estado |
|---|---|
| Chats de grupo y mensajes directos | Sí. Un mensaje directo es un canal `DIRECT` o un mensaje sin servidor. |
| Detección de llamadas (`addressed`) | Un `<at>` al bot (por id, o por el nombre del bot si el servidor no da id) y una respuesta a un mensaje del bot. `@all` cuenta como texto, no como mención. |
| Mensajes citados | El texto citado, el remitente y el id, tomados de un elemento `<quote>` o de `message.quote`. |
| Imágenes recibidas | Las imágenes `data:` e `internal:` y las del servidor Satori se incrustan. Las URL públicas se pasan para que las recoja el agente. Las URL de redes privadas se describen como `(sent an image)`. Como máximo 4 descargas por mensaje, de 4 MB cada una. |
| Stickers y emoji | `<emoji>` y el `<face>` de QQ llegan como emoji, y la persona sabe que no puede verlos. |
| Voz, vídeo, archivos | Se describen con palabras: `(sent a voice message)`, `(sent a video)`, `(sent a file: deck.pdf)`. |
| Respuestas | Texto, e imágenes como URI `data:`, cada uno enviado como mensaje aparte con una pequeña pausa. En grupos, una mención que pide el agente se convierte en `<at>`. |
| Plataformas de respuesta pasiva | Las respuestas llevan el `referrer` del evento, que la API oficial de bots de QQ necesita para responder a un mensaje. |
| Bandeja de salida | Los mensajes programados, seguimientos y excusas van al canal por la sesión que recibió la conversación. El conector firma cada identificador de respuesta con una clave derivada de `SATORI_TOKEN` y `CONNECTOR_TOKEN`, y solo envía a identificadores que él firmó. Tras cambiar cualquiera de los tokens, una conversación vuelve a ser alcanzable cuando envía un mensaje. Un agente con `CONNECTOR_OUTBOX_ENABLED=false` responde 404, y el conector reintenta cada 10 minutos. |
| Indicador de escritura | No. Satori no tiene API de escritura. |
| `owned` | Se respeta: el conector no envía nada más. No puede detener otros plugins de Koishi (consulta el paso 1). |

Las reglas de cada plataforma siguen aplicándose. La API oficial de bots de QQ, por ejemplo, limita estrictamente los mensajes que un bot puede enviar sin que se lo pidan, así que las entregas de la bandeja de salida allí pueden volver como `failed`.

## Pruebas

`tests/test_satori_connector.py` se ejecuta sin satori-python y sin red. Simula los objetos de elementos, la cuenta y el agente.
