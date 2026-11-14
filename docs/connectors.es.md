# Protocolo de conectores

[English](connectors.md) · [简体中文](connectors.zh-CN.md) · [繁體中文](connectors.zh-TW.md) · [日本語](connectors.ja.md) · [한국어](connectors.ko.md) · Español · [Français](connectors.fr.md) · [Deutsch](connectors.de.md) · [Português (Brasil)](connectors.pt-BR.md) · [Русский](connectors.ru.md)

El agente nunca se comunica directamente con una plataforma de chat. De ello se encarga un conector. Este inicia sesión en una plataforma, o en un framework que abarca muchas, convierte cada mensaje entrante en un evento neutro, envía el evento a personagent y entrega lo que recibe como respuesta. Todo lo específico de la plataforma permanece en el conector, por lo que el agente recibe el mismo formato desde cualquier plataforma.

Este repositorio incluye cuatro conectores:

| Conector | Alcance | Ruta |
|---|---|---|
| Directo | Bots oficiales de QQ, WeChat personal (iLink), Telegram, Discord, Matrix, Twitch, IRC, Zulip, VK y Stoat, sin ningún otro software. La página local y `personagent up` lo ejecutan como un único proceso, `python -m persona_agent.direct`. | `persona_agent/direct/` |
| Complemento de AstrBot | Las plataformas de AstrBot, un puente de terceros. El AstrBot que personagent gestiona para KOOK, Feishu/Lark, DingTalk, Slack, WeCom, Mattermost, Misskey, OneBot v11 y otras plataformas recibe el complemento automáticamente. Para un AstrBot que ya tenga en ejecución, `personagent connect astrbot` lo configura. También puede subir `astrbot_plugin_personagent.zip` desde una GitHub Release mediante la opción de instalación desde archivo de AstrBot y definir `connector_token` usted mismo. | `integrations/astrbot/` |
| Satori | Todas las implementaciones de Satori (Koishi y otras, de terceros): QQ, Telegram, Discord, KOOK, Lark, DingTalk, LINE, WhatsApp, Matrix, Zulip, correo electrónico y otras. | `integrations/satori/` |
| Matrix | Salas de Matrix y, a través de puentes mautrix de terceros, WhatsApp, Signal, Messenger, Instagram, Google Messages y otras. | `integrations/matrix/` |

Los asistentes de programación no son plataformas de chat, por lo que disponen de su propia vía: un servidor MCP, `personagent mcp`, que se describe en la [guía de usuario](guide.es.md#asistentes-de-programación).

Los cuatro utilizan el protocolo descrito en esta página. Para escribir uno nuevo, solo necesita esta página y un cliente HTTP. El módulo auxiliar de Python `integrations/sdk/personagent_connector.py` firma las solicitudes y ejecuta el bucle de la bandeja de salida por usted. Recibe la URL base, el token y el `connector_id` del conector, y requiere `httpx`. Su [README](../integrations/sdk/README.es.md) incluye un ejemplo completo.

## Probarlo en su propio equipo

```
personagent run --port 8080
curl http://127.0.0.1:8080/health
```

`personagent run` sirve los dos endpoints descritos a continuación en `127.0.0.1`. Lee `CONNECTOR_TOKEN` del `.env` de la carpeta de inicio que indica su mensaje de arranque; `--home DIR` elige otra.

- Con `CONNECTOR_TOKEN` vacío, el agente acepta solo programas del mismo equipo que llamen a `127.0.0.1` o `localhost`, y estos no envían cabeceras de autenticación. `personagent init` lo deja vacío. La página local, `personagent up` y `personagent connect astrbot` escriben uno aleatorio cuando está vacío.
- Para establecer uno, escriba un valor aleatorio largo en `.env`, por ejemplo la salida de `python -c "import secrets; print(secrets.token_urlsafe(32))"`, configure el mismo valor en el conector y reinicie el agente.
- `GET /health` responde `{"status": "ok", "agent_enabled": true}` y no tiene coste. `"agent_enabled": false` significa que el agente no puede responder (sin `LLM_API_KEY`, o con `AGENT_ENABLED=false`), y todos los eventos reciben `owned: false`. `GET /health/details` comprueba además el modelo y los demás servicios, lo que puede tener un pequeño coste. Exige la cabecera `X-Personagent-Token` cuando hay un token configurado y, si no lo hay, una solicitud del mismo equipo; cualquier otra recibe `403` con el código `forbidden`.

## Configuración

La página local configura el conector directo. Los otros tres utilizan los mismos nombres, de modo que un ajuste tiene el mismo significado en cada uno:

| Significado | Satori | Matrix | Clave del complemento de AstrBot |
|---|---|---|---|
| La URL base de personagent, como `http://127.0.0.1:8080`. El conector añade `/v1/events` y `/v1/outbox`. | `PERSONAGENT_URL` | `PERSONAGENT_URL` | `personagent_url` |
| El token compartido, igual al `CONNECTOR_TOKEN` del agente | `CONNECTOR_TOKEN` | `CONNECTOR_TOKEN` | `connector_token` |
| El id de este conector (`connector_id` más abajo) | `SATORI_CONNECTOR_ID` | `MATRIX_CONNECTOR_ID` | `connector_id` |
| Tiempo máximo de una solicitud, en segundos | `SATORI_TIMEOUT_S` | `MATRIX_TIMEOUT_S` | `timeout_s` |
| Consultar la bandeja de salida | `SATORI_OUTBOX_ENABLED` | `MATRIX_OUTBOX_ENABLED` | `outbox_enabled` |
| Grupos que se reenvían | `SATORI_GROUPS` | `MATRIX_GROUPS` | `groups` |
| Personas cuyos mensajes directos se reenvían | `SATORI_DM_USERS` | `MATRIX_DM_USERS` | `dm_users` |
| El servidor de la plataforma | `SATORI_URL` | `MATRIX_URL` | El propio de AstrBot |

Una lista de grupos o de mensajes directos vacía no reenvía nada de ese tipo. `*` lo reenvía todo y marca los eventos con `"prefiltered": false`, lo que deja la decisión a `ACCESS_GROUPS` y `ACCESS_DM_USERS` del agente. El README de cada conector enumera sus demás ajustes.

## Direcciones

personagent guarda cada id como `<platform>:<id>`, por ejemplo `telegram:-1001234` para un grupo o `discord:4242` para un usuario. `platform` es el nombre que el conector asigna a la plataforma, en minúsculas y sin `:`.

QQ es la única excepción, que se mantiene por compatibilidad. Sus id se guardan sin prefijo (`123456`), y `qq:123456` tiene el mismo significado en cualquier ajuste. Si un conector gestiona QQ y desea que su estado aprendido coincida con un despliegue de QQ existente, añada su plataforma a `CONNECTOR_QQ_PLATFORMS`. El adaptador de QQ del complemento de AstrBot es `aiocqhttp`. Los id de las plataformas indicadas allí también se guardan sin prefijo.

## Autenticación

Los dos endpoints siguientes utilizan el mismo esquema. Cuando `CONNECTOR_TOKEN` está definido en el agente, cada solicitud incluye cuatro cabeceras:

- `X-Personagent-Token`: el token.
- `X-Personagent-Timestamp`: segundos unix. Se rechaza un valor que difiera más de cinco minutos del reloj del agente.
- `X-Personagent-Nonce`: un valor aleatorio nuevo. Se rechaza un nonce reutilizado.
- `X-Personagent-Signature`: `sha256=` seguido del HMAC-SHA256 en hexadecimal de `timestamp + "." + nonce + "." + body`, con el token como clave.

La firma cubre los bytes del cuerpo tal como se envían, por lo que cualquier JSON válido en UTF-8 es aceptado. Se recomienda JSON canónico (claves ordenadas, separadores compactos y caracteres no ASCII sin escapar), y los conectores incluidos lo envían, pero el agente no lo exige. El token es también la clave de firma, por lo que debe mantenerlo fuera de los registros.

Sin token, el agente solo acepta programas locales que llamen directamente a `127.0.0.1` o `localhost`. Un conector debe negarse a enviar a cualquier destino que no sea una URL de loopback o una URL HTTPS con token.

## Entrada: `POST /v1/events`

Cada solicitud contiene un mensaje y devuelve las respuestas a dicho mensaje.

```json
{
  "platform": "telegram",
  "conversation_type": "group",
  "conversation_id": "-1001234",
  "sender_id": "42",
  "sender_name": "Alex",
  "bot_id": "7000",
  "message_id": "881",
  "sent_at": 1790320000,
  "addressed": true,
  "text": "Nova, how was your day?",
  "segments": [
    {"type": "text", "text": "Nova, how was your day?"}
  ],
  "connector_id": "astrbot-7f3c",
  "reply_handle": "tg-bot:GroupMessage:-1001234",
  "capabilities": ["outbox", "quote_text"]
}
```

Los campos obligatorios son `platform`, `conversation_type` (`group` o `dm`), `sender_id`, `message_id` y `sent_at`, además de `conversation_id` para los grupos. `sent_at` es el momento en que la plataforma registró el mensaje, en segundos unix enteros (también se acepta una cadena de dígitos). El personaje ve cada mensaje con esa hora. Un mensaje de grupo que tiene más de 10 minutos de antigüedad al llegar, dentro de los dos minutos siguientes al primer mensaje de la plataforma desde que se inició el agente, es un mensaje acumulado que se entrega tras un reinicio: se conserva como contexto y no se responde. Pasados esos dos minutos, un `sent_at` antiguo ya no retiene un mensaje, de modo que se sigue respondiendo a un conector cuyo reloj va atrasado. Envíe los id sin procesar de la plataforma. El agente añade el prefijo.

El conector define `addressed`. Su valor es verdadero cuando el mensaje menciona al bot, responde a uno de los mensajes del bot o va dirigido al bot según las propias reglas de la plataforma. El agente también detecta por sí mismo su nombre en el texto. Interpreta una cita de su propio mensaje, o una @mención al bot, como una reacción de la que puede aprender, por lo que debe definir `addressed` en las respuestas al bot. Una cita del mensaje de otro miembro nunca es una reacción al bot. Una mención al bot dentro de un mensaje reenviado no se dirige al bot, por lo que no debe definir `addressed` para ella.

Un evento cuyo `sender_id` es igual a su `bot_id` es el propio mensaje del bot devuelto como eco. El agente lo descarta sin leerlo y responde `{"handled": false, "owned": true, "replies": []}`, de modo que la lógica de bot del propio conector tampoco responde. Omita esos eventos en el conector.

Los segmentos se envían en orden:

| Tipo | Campos | Notas |
|---|---|---|
| `text` | `text` | |
| `mention` | `user_id`, `name` | Una mención a alguien. Menciona al bot cuando `user_id` es igual a `bot_id`. El personaje lee `name` en lugar del id, por lo que conviene enviarlo. `name` llega al modelo marcado como un nombre que el remitente no escribió, por lo que nunca llama al personaje ni da ninguna orden. Una mención al bot después de un segmento `forward` no es una llamada. |
| `image` | `url` o `b64`, `sticker` (booleano) | `sticker` indica un sticker enviado como imagen. Una imagen de grupo enviada como `b64`, o marcada con `sticker`, puede recopilarse para la biblioteca de stickers; una foto enviada solo como `url` no se recopila. |
| `emoji` | `name`, `id` | Un sticker de la plataforma o un emoji personalizado que el agente no puede ver. `name` es el nombre que le daría una persona. |
| `media` | `kind`, `name`, `transcript`, `emoji` | Algo que el agente no puede ver. `kind` es `voice`, `video`, `file`, `photo` (una imagen que no se pudo obtener) o `sticker`. Añada `name` a un archivo, `transcript` a un mensaje de voz que la plataforma haya transcrito y `emoji` a un sticker. |
| `forward` | `name` | Los segmentos que le siguen se reenviaron desde `name` y no los escribió el remitente. `name` puede estar vacío. Su texto se lee como palabras de la persona cuyo mensaje se reenvió: no llama a nadie por su nombre ni ejecuta ningún comando de memoria. Coloque el comentario del propio remitente antes del segmento `forward` o envíelo como un mensaje independiente. |
| `reply` | `message_id`, `text`, `sender_id`, `sender_name` | El mensaje que este cita. Envíe `text` siempre que la plataforma lo proporcione. |

Envíe el contenido multimedia como un segmento `media`, nunca con palabras como `(sent a voice message)`: el personaje las leería como si las hubiera escrito el remitente. El agente descarta los tipos de segmento desconocidos.

Los siguientes campos opcionales activan funciones adicionales del agente:

| Campo | Significado |
|---|---|
| `connector_id` | Un id estable para esta instancia del conector. La bandeja de salida lo requiere. |
| `reply_handle` | Lo que el conector necesite para acceder a esta conversación más adelante sin un mensaje entrante: el `unified_msg_origin` de AstrBot, un id de sala de Matrix o un inicio de sesión de Satori junto con un id de canal. El agente lo trata como un valor opaco, lo guarda por conversación y lo devuelve en las entregas de la bandeja de salida. |
| `capabilities` | Lo que el conector puede hacer. `outbox` significa que consulta la bandeja de salida y puede enviar mensajes sin una solicitud previa. `quote_text` significa que los segmentos de respuesta incluyen el texto citado. |
| `prefiltered` | `true` (el valor predeterminado) cuando el conector aplicó su propia lista de permitidos. `false` hace que las listas del agente sean el único filtro. |
| `proactive` | Marca un evento de mensaje directo como una señal redactada por el conector, no como palabras de la persona. Consulte «Hablar primero sin la bandeja de salida». |

La respuesta tiene el siguiente aspecto:

```json
{"handled": true, "owned": true, "replies": [
  {"type": "text", "text": "not bad, rained all afternoon", "mention_user_id": "telegram:42"},
  {"type": "image", "b64": "..."}
]}
```

- `replies`: envíelas en orden, cada una como un mensaje independiente. Cuando `mention_user_id` está presente, es el id con prefijo que debe mencionarse. Muestre la mención según el formato de la plataforma. Un elemento con `"reason": "excuse"` es el breve mensaje que el personaje envía en un mensaje directo cuando ha fallado el modelo, no una respuesta. Envíelo como los demás o trátelo como un error.
- `owned`: el agente se ha hecho cargo del mensaje, porque superó las listas de permitidos del agente, con independencia de lo que haga después el personaje. Cuando es verdadero, impide que otra lógica de bot responda, aunque `replies` esté vacío, porque el personaje puede haber decidido guardar silencio. Cuando es falso, el agente no ha intervenido en el mensaje: la conversación no está en las listas de permitidos del agente o el agente no puede responder en absoluto (sin `LLM_API_KEY`, o con `AGENT_ENABLED=false`). Cuando el agente no puede responder, su registro incluye una línea ERROR que indica la causa. Un `message_id` repetido corresponde al propio agente (véase «Mensajes repetidos» más abajo).
- `handled`: verdadero cuando el turno propio de esta solicitud entregó algo, una respuesta o el resultado de un comando de memoria. Sirve para registros y estadísticas. Decida según `owned` y envíe lo que contenga `replies`, diga lo que diga `handled`: un mensaje `excuse`, por ejemplo, llega con `handled: false`.

Las combinaciones que encuentra un conector:

| Respuesta | Cuándo | Qué hace el conector |
|---|---|---|
| `handled: true`, `owned: true`, con respuestas | Una respuesta normal. | Envía `replies` y mantiene en silencio la otra lógica de bot. |
| `handled: false`, `owned: true`, `replies: []` | El personaje guardó silencio; el evento era el eco del propio bot; el mensaje se incorporó al turno de un mensaje posterior (véase «Mensajes enviados seguidos»); un comando de memoria cuyo resultado llega más tarde por la bandeja de salida; un evento de grupo con `proactive`; un `message_id` repetido (una reentrega). | No envía nada y mantiene en silencio la otra lógica de bot. |
| `handled: false`, `owned: true`, una respuesta con `"reason": "excuse"` | Falló el modelo en un mensaje directo. | La envía o la trata como un error. |
| `handled: false`, `owned: false`, `replies: []` | La conversación no está en las listas de permitidos o el agente no puede responder. | El mensaje corresponde al conector. |

Otras reglas:

- **Mensajes repetidos.** El agente recuerda los últimos 2000 mensajes que admitió, de todas las conversaciones. La clave es `platform`, la conversación (el `conversation_id` de un grupo o el `sender_id` de un mensaje directo) y `message_id`; para una plataforma incluida en `CONNECTOR_QQ_PLATFORMS` es el `message_id` sin prefijo. La lista se guarda periódicamente y al cerrar en la carpeta `runtime/` de la carpeta de inicio, por lo que se conserva tras un reinicio. Un mensaje enviado de nuevo, como una reentrega de la plataforma o un reintento tras un tiempo de espera agotado, recibe `{"handled": false, "owned": true, "replies": []}` de inmediato, aunque la primera solicitud siga en curso. No envíe nada para él; sus respuestas llegan solo en la primera. Un turno continúa aunque quien lo solicitó desista, de modo que tras un tiempo de espera agotado las respuestas se pierden; conceda tiempo suficiente en lugar de reintentar. Un mensaje rechazado por las listas de permitidos no se recuerda y se evalúa de nuevo si se vuelve a enviar.
- **Mensajes enviados seguidos.** Los mensajes de una conversación que llegan dentro de un breve antirrebote (2,5 segundos, o 5 segundos tras un mensaje de grupo que solo llama al personaje por su nombre) forman un único turno, que los responde en conjunto. Los mensajes que esperan tras un turno en curso también se incorporan al turno siguiente. Solo la solicitud del mensaje más reciente lleva las respuestas; cada solicitud anterior devuelve `{"handled": false, "owned": true, "replies": []}`. En un grupo, el `mention_user_id` de una respuesta indica la persona a quien responde el personaje, que puede haber enviado un mensaje anterior y no el de la solicitud que lleva la respuesta. Los comandos de memoria no se combinan; véase el último punto.
- La solicitud se mantiene abierta hasta que termina el turno, que consiste en un breve antirrebote más el tiempo del modelo. Las llamadas al modelo de un turno comparten un único presupuesto de 1,5 × `LLM_TIMEOUT_S`, reintentos incluidos, tanto en un grupo como en un mensaje directo, y un mensaje que llega mientras un turno anterior de su conversación sigue en curso espera a que ese turno termine antes de iniciar el suyo. Establezca un tiempo de espera de al menos 3 × `LLM_TIMEOUT_S` segundos (360 con el valor predeterminado).
- Un comando de memoria (como «remember ...») que llega mientras un turno de su conversación sigue en curso se responde después de ese turno. Un conector que declaró `outbox` recibe `{"handled": false, "owned": true, "replies": []}` de inmediato y el resultado más tarde como una entrega `follow_up`. Sin `outbox`, el resultado llega en la respuesta a una solicitud: la suya propia o la de otra solicitud en espera de la misma conversación, por lo que una respuesta puede incluir `replies` que mencionan a alguien distinto del remitente del evento.

## Bandeja de salida: `POST /v1/outbox`

Algunos mensajes no responden a ninguna solicitud. Por ejemplo, un saludo programado, la pregunta de seguimiento tras un rechazo, la respuesta a un comando de memoria que esperó a que terminara un turno y la disculpa que se envía cuando el modelo no está disponible en un grupo. El agente los pone en cola por conversación, y un conector que declaró `outbox` los recoge, por lo que un conector situado detrás de NAT o de un cortafuegos funciona igual. Las conversaciones guardadas con id de QQ sin prefijo (consulte Direcciones) también utilizan la bandeja de salida mientras su conector la consulta. En caso contrario, se envían a través de la API HTTP de NapCat, cuando `QQ_ONEBOT_URL` está definido.

Solicitud:

```json
{
  "kind": "outbox.pull",
  "connector_id": "astrbot-7f3c",
  "wait_s": 25,
  "max_deliveries": 10,
  "acks": [
    {"delivery_id": "d_5c1f...", "status": "sent", "sent_items": 2}
  ]
}
```

El agente retiene la solicitud durante un máximo de `wait_s` segundos (30 como máximo) hasta que haya algo en la cola y, entonces, responde:

```json
{
  "deliveries": [
    {
      "delivery_id": "d_9a07...",
      "conversation_key": "telegram:-1001234",
      "reply_handle": "tg-bot:GroupMessage:-1001234",
      "platform": "telegram",
      "conversation_type": "group",
      "conversation_id": "-1001234",
      "reason": "proactive",
      "expires_in_s": 300,
      "items": [{"type": "text", "text": "anyone still up?"}]
    }
  ],
  "next_wait_s": 25
}
```

`items` tiene la misma estructura que `replies`. `reason` es `proactive`, `follow_up` o `excuse`, y `conversation_type` es `group` o `dm`. `conversation_key` es la clave con la que el agente guarda la conversación, como `private:telegram:42` para un mensaje directo. `conversation_id` es el id sin procesar que incluía el evento, que en un mensaje directo es el id de usuario. El agente recuerda `reply_handle`, `connector_id` y `capabilities` del último evento admitido en cada conversación, por lo que una conversación es accesible en cuanto ha enviado un mensaje. Una excepción mantiene en su lugar a un conector que recoge la bandeja de salida: un evento de un conector sin la capacidad `outbox` no sustituye lo que otro conector con esa capacidad guardó para la misma conversación. Por tanto, un conector que recoge la bandeja de salida sigue pudiendo acceder a la conversación después de que otro programa, como un asistente de programación, haya hablado en ella. Un evento del mismo conector, o de cualquier conector que declare `outbox`, sustituye los valores guardados como hasta ahora.

La página local es en sí misma un conector de bandeja de salida, con el `connector_id` `local-welcome`. Solo recibe las entregas del chat de la propia página y las muestra en la vista Chat.

Informe de cada entrega en `acks` en la siguiente consulta:

| `status` | Significado |
|---|---|
| `sent` | Se enviaron todos los elementos. |
| `partial` | Se enviaron los primeros `sent_items` elementos. |
| `failed` | No se envió nada. |
| `expired` | El envío no comenzó dentro de `expires_in_s`. |
| `refused` | El conector ya no permite la conversación. |
| `unsupported` | La plataforma no permite enviar mensajes sin solicitud previa a esta conversación. |

Reglas:

- **Como máximo una vez.** El agente entrega cada elemento una sola vez y nunca más, independientemente del ack. Conserve los últimos cientos de `delivery_id` y no envíe nunca uno dos veces.
- **En orden.** Envíe las entregas de una conversación en el orden en que las recibió. Las de conversaciones distintas pueden enviarse en paralelo.
- **Solo cuentan las entregas confirmadas.** El agente trata una entrega sin confirmar como no enviada y registra como enviadas solo las confirmadas. Espera el ack hasta su siguiente consulta, y como máximo `expires_in_s` más 60 segundos desde la entrega. Termine de enviar un lote antes de volver a consultar.
- **Actividad.** Un conector que no ha realizado consultas durante 90 segundos se considera desaparecido. No se pone nada en cola para sus conversaciones hasta que vuelva a consultar, y lo que estuviera en cola para él, o entregado sin ack, se da por no enviado. Vuelva a consultar en cuanto se entregue un lote. Esa consulta también incluye los ack del lote.
- **`unsupported` persiste.** Tras ese ack, el agente deja de poner mensajes en cola para la conversación hasta que un evento incluya un `reply_handle` distinto.
- **Tipos de cuerpo.** La firma no cubre la ruta de la URL. Por ello, el agente rechaza un cuerpo de evento en el endpoint de la bandeja de salida y un cuerpo `outbox.pull` en el endpoint de eventos, con `400` y el código `invalid_schema`. Un evento puede incluir `"kind": "event"`. Se rechaza un evento con cualquier otro valor de `kind`.

Un 404 sin `code` significa que el agente no ofrece la bandeja de salida. Un `404` con el código `outbox_disabled` significa que el operador la desactivó con `CONNECTOR_OUTBOX_ENABLED`. En ambos casos, espere un tiempo prolongado antes de volver a consultar.

## Errores

Un error responde `{"error": "...", "code": "..."}`. `code` es estable, así que base sus decisiones en él. `error` es una frase para quien lee un registro, y su redacción puede cambiar.

| Estado | `code` | Endpoint | Causa |
|---|---|---|---|
| 400 | `invalid_schema` | ambos | El cuerpo no es un objeto JSON; falta un campo obligatorio o está vacío; `conversation_type` no es `group` ni `dm`; `segments` no es una lista; un cuerpo del tipo equivocado (véase «Tipos de cuerpo»); una consulta sin un `connector_id` válido (128 caracteres como máximo), con un `wait_s` o `max_deliveries` que no es un número, o con más de 1000 acks. |
| 400 | `client_disconnected` | ambos | El cliente cortó la conexión mientras enviaba el cuerpo. |
| 403 | `unauthenticated` | ambos | No hay `CONNECTOR_TOKEN` y el cliente no está en el equipo del agente. |
| 403 | `non_local_request` | ambos | No hay `CONNECTOR_TOKEN` y la solicitud lleva una cabecera que un programa local no envía: `Origin`, un `Sec-Fetch-Site` distinto de `none`, un `Host` distinto de `localhost`, `127.0.0.1` o `::1`, o una cabecera de proxy como `X-Forwarded-For`. |
| 403 | `invalid_envelope` | ambos | `CONNECTOR_TOKEN` está configurado y falta el token o una cabecera o es incorrecto, la firma no coincide, la marca de tiempo se desvía más de cinco minutos, el nonce ya se usó o la protección contra repeticiones está llena. |
| 403 | `stale_event` | events | `sent_at` no es un número entero de segundos o se aleja más de `CONNECTOR_MAX_EVENT_AGE_S` (24 horas) del reloj del agente, en cualquier sentido. Un valor en milisegundos queda en un futuro lejano. |
| 404 | `outbox_disabled` | outbox | `CONNECTOR_OUTBOX_ENABLED=false`, o el agente está desactivado (`AGENT_ENABLED=false`). |
| 408 | `body_timeout` | ambos | El cuerpo tardó más de 30 segundos en llegar. |
| 413 | `body_too_large` | ambos | El cuerpo supera `SERVER_MAX_BODY_BYTES` (8 000 000 bytes), normalmente por una imagen incrustada. |
| 429 | `capacity_exceeded` | ambos | Demasiadas solicitudes a la vez: más de `CONNECTOR_MAX_INFLIGHT` turnos (64 por defecto) en el endpoint de eventos, o 16 consultas en la bandeja de salida. La cabecera `Retry-After` indica los segundos de espera: 3, o 5 para la bandeja de salida. |

Una ruta incorrecta recibe `404 {"detail": "Not Found"}` y un método incorrecto, como `GET /v1/events`, recibe `405 {"detail": "Method Not Allowed"}`. Estas respuestas proceden del framework web y no llevan `code`.

## Hablar primero sin la bandeja de salida

Un conector que no puede realizar consultas puede, aun así, iniciar un mensaje directo. Su propio planificador, como una tarea de un complemento de AstrBot o una entrada de cron, envía un evento normal de mensaje directo con `"proactive": true` a `/v1/events`. El agente interpreta el texto como una señal para el personaje («lleva un día sin escribir; su examen era esta mañana»), lo recorta a 500 caracteres y nunca lo guarda como palabras de la persona. Las instrucciones proactivas del motor siguen decidiendo el turno y pueden hacer que el personaje guarde silencio. Si el personaje habla, la respuesta se devuelve en la respuesta HTTP para que el planificador la retransmita.

El evento requiere todo lo que incluyen los eventos normales del conector: las cabeceras firmadas, todos los campos obligatorios, los mismos valores sin procesar de `platform` y `sender_id` que el conector envía para esa persona, un texto no vacío y un `message_id` nuevo cada vez. Un evento con un `message_id` repetido no se procesa de nuevo y recibe `owned: true` sin respuestas. La señal cuenta para el mismo intervalo de espera de mensajes directos que los saludos del propio agente (`PROACTIVE_DM_COOLDOWN_S`), y no cuenta como actividad de la persona.

Defina siempre el indicador; sin él, el agente guarda la señal como palabras de la persona. Un evento de grupo con el indicador se reclama (`owned: true`, para que el conector mantenga en silencio a su bot) y se descarta sin leerlo.

## Capacidades y funciones degradadas

| Falta | Efecto |
|---|---|
| `outbox` | Sin saludos programados, sin pregunta de seguimiento y sin disculpa cuando falla una llamada al modelo en un grupo. Los id de QQ siguen recibiéndolos a través de NapCat cuando `QQ_ONEBOT_URL` está definido y es accesible. La disculpa de un mensaje directo se devuelve en los `replies` de la respuesta y no requiere la bandeja de salida. |
| `quote_text` | El agente solo entiende un mensaje citado si ha visto ese mensaje por sí mismo. |
| `reply_handle` | El mismo efecto que la falta de `outbox`. |
| `addressed` incorrecto | El personaje trata los mensajes dirigidos a él como conversación de fondo. |

## Escribir un conector

1. Reciba un mensaje de la plataforma. Omita los mensajes del propio bot y los eventos que no son mensajes (entradas, salidas, toques).
2. Construya el evento descrito arriba. Defina `addressed` según las propias reglas de mención y respuesta de la plataforma.
3. Firme y envíe el evento. Envíe `replies` en orden y, cuando `owned` sea verdadero, mantenga en silencio cualquier otra lógica de bot.
4. Si la plataforma permite enviar mensajes sin solicitud previa, añada `connector_id`, `reply_handle` y `capabilities: ["outbox"]`, y ejecute el bucle de consulta: consulte, envíe cada entrega a través de su `reply_handle` y confirme en la siguiente consulta.

`integrations/sdk/personagent_connector.py` se encarga de los pasos 3 y 4. Su [README](../integrations/sdk/README.es.md) los muestra en un programa breve.
