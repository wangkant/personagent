# Protocolo de conectores

[English](connectors.md) · [简体中文](connectors.zh-CN.md) · [繁體中文](connectors.zh-TW.md) · [日本語](connectors.ja.md) · [한국어](connectors.ko.md) · Español · [Français](connectors.fr.md) · [Deutsch](connectors.de.md) · [Português (Brasil)](connectors.pt-BR.md) · [Русский](connectors.ru.md)

El agente nunca habla directamente con una plataforma de chat. De eso se encarga un conector. Inicia sesión en una plataforma, o en un framework que abarca muchas, convierte cada mensaje entrante en un evento neutro, envía el evento a personagent y entrega lo que vuelve. Todo lo específico de la plataforma se queda en el conector, así que el agente ve el mismo formato desde cualquier plataforma.

Este repositorio incluye cuatro conectores:

| Conector | Alcanza | Ruta |
|---|---|---|
| Directo | Bots oficiales de QQ, WeChat personal (iLink), Telegram y Discord, sin ningún otro software. La página local y `personagent up` lo ejecutan como un solo proceso, `python -m persona_agent.direct`. | `persona_agent/direct/` |
| Plugin de AstrBot | Las plataformas de AstrBot, un puente de terceros. El AstrBot que personagent gestiona para KOOK, Feishu/Lark, DingTalk, Slack, WeCom, Mattermost, Misskey, OneBot v11 y demás recibe el plugin automáticamente. Para un AstrBot que ya tengas en marcha, `personagent connect astrbot` lo configura. También puedes subir `astrbot_plugin_personagent.zip` desde una GitHub Release con Instalar desde archivo de AstrBot y definir `connector_token` tú mismo. | `integrations/astrbot/` |
| Satori | Todas las implementaciones de Satori (Koishi y otras, de terceros): QQ, Telegram, Discord, KOOK, Lark, DingTalk, LINE, WhatsApp, Matrix, Zulip, correo electrónico y más. | `integrations/satori/` |
| Matrix | Salas de Matrix y, a través de puentes mautrix de terceros, WhatsApp, Signal, Messenger, Instagram, Google Messages y más. | `integrations/matrix/` |

Los agentes de programación no son plataformas de chat, así que tienen su propia vía: un servidor MCP, `personagent mcp`, que se explica en la [guía de usuario](guide.es.md#agentes-de-código).

Los cuatro hablan el protocolo descrito en esta página. Para escribir uno nuevo necesitas esta página y un cliente HTTP. El ayudante de Python en `integrations/sdk/personagent_connector.py` firma las solicitudes y ejecuta el bucle de la bandeja de salida por ti. Recibe la URL base, el token y el `connector_id` del conector, y necesita `httpx`.

## Configuración

La página local configura el conector directo. Los otros tres usan los mismos nombres, así que un ajuste significa lo mismo en cada uno:

| Significado | Satori | Matrix | Clave del plugin de AstrBot |
|---|---|---|---|
| La URL base de personagent, como `http://127.0.0.1:8080`. El conector añade `/v1/events` y `/v1/outbox`. | `PERSONAGENT_URL` | `PERSONAGENT_URL` | `personagent_url` |
| El token compartido, igual al `CONNECTOR_TOKEN` del agente | `CONNECTOR_TOKEN` | `CONNECTOR_TOKEN` | `connector_token` |
| El id de este conector (`connector_id` más abajo) | `SATORI_CONNECTOR_ID` | `MATRIX_CONNECTOR_ID` | `connector_id` |
| Cuánto puede tardar una solicitud, en segundos | `SATORI_TIMEOUT_S` | `MATRIX_TIMEOUT_S` | `timeout_s` |
| Consultar la bandeja de salida | `SATORI_OUTBOX_ENABLED` | `MATRIX_OUTBOX_ENABLED` | `outbox_enabled` |
| Grupos que reenviar | `SATORI_GROUPS` | `MATRIX_GROUPS` | `groups` |
| Personas cuyos mensajes directos se reenvían | `SATORI_DM_USERS` | `MATRIX_DM_USERS` | `dm_users` |
| El servidor de la plataforma | `SATORI_URL` | `MATRIX_URL` | El propio de AstrBot |

Una lista de grupos o de mensajes directos vacía no reenvía nada de ese tipo. `*` lo reenvía todo y marca los eventos con `"prefiltered": false`, lo que deja la decisión a `ACCESS_GROUPS` y `ACCESS_DM_USERS` del agente. El README de cada conector enumera sus demás ajustes.

## Direcciones

personagent guarda cada id como `<platform>:<id>`, por ejemplo `telegram:-1001234` para un grupo o `discord:4242` para un usuario. `platform` es el nombre que el conector da a la plataforma, en minúsculas y sin `:`.

QQ es la única excepción, mantenida por compatibilidad. Sus id se guardan sin prefijo (`123456`), y `qq:123456` significa lo mismo en cualquier ajuste. Si un conector lleva QQ y quieres que su estado aprendido coincida con un despliegue de QQ existente, pon su plataforma en `CONNECTOR_QQ_PLATFORMS`. El adaptador de QQ del plugin de AstrBot es `aiocqhttp`. Los id de las plataformas indicadas ahí también se guardan sin prefijo.

## Autenticación

Los dos endpoints siguientes usan el mismo esquema. Cuando `CONNECTOR_TOKEN` está definido en el agente, cada solicitud lleva cuatro cabeceras:

- `X-Personagent-Token`: el token.
- `X-Personagent-Timestamp`: segundos unix. Se rechaza un valor a más de cinco minutos del reloj del agente.
- `X-Personagent-Nonce`: un valor aleatorio nuevo. Se rechaza un nonce reutilizado.
- `X-Personagent-Signature`: `sha256=` seguido del HMAC-SHA256 en hexadecimal de `timestamp + "." + nonce + "." + body`, con el token como clave.

El cuerpo es JSON canónico: UTF-8, claves ordenadas, separadores compactos y caracteres no ASCII sin escapar. El token es también la clave de firma, así que mantenlo fuera de los registros.

Sin token, el agente solo acepta programas locales que llamen directamente a `127.0.0.1` o `localhost`. Un conector debe negarse a enviar a cualquier cosa que no sea una URL de loopback, o una URL HTTPS con token.

## Entrada: `POST /v1/events`

Cada solicitud trae un mensaje y devuelve las respuestas a él.

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

Los campos obligatorios son `platform`, `conversation_type` (`group` o `dm`), `sender_id`, `message_id` y `sent_at`, más `conversation_id` para los grupos. `sent_at` es cuándo la plataforma selló el mensaje, en segundos unix. Envía los id sin procesar de la plataforma. El agente añade el prefijo.

El conector define `addressed`. Es verdadero cuando el mensaje menciona al bot, responde a uno de los mensajes del bot o va dirigido al bot según las propias reglas de la plataforma. El agente también nota por sí solo su nombre en el texto. Lee una cita de su propio mensaje, o una @ al bot, como una reacción de la que puede aprender, así que define `addressed` en las respuestas al bot. Una cita del mensaje de otro miembro nunca es una reacción al bot.

Un evento cuyo `sender_id` es igual a su `bot_id` es el propio mensaje del bot devuelto como eco. El agente lo descarta sin leerlo y responde `{"handled": false, "owned": true, "replies": []}`, de modo que la lógica de bot del propio conector también se queda callada. Omite esos eventos en el conector.

Los segmentos vienen en orden:

| Tipo | Campos | Notas |
|---|---|---|
| `text` | `text` | |
| `mention` | `user_id`, `name` | Una mención a alguien. Menciona al bot cuando `user_id` es igual a `bot_id`. |
| `image` | `url` o `b64`, `sticker` (booleano) | `sticker` marca un sticker enviado como imagen. |
| `emoji` | `name`, `id` | Un sticker de la plataforma o emoji personalizado que el agente no puede ver. `name` es como lo llamaría una persona. |
| `reply` | `message_id`, `text`, `sender_id`, `sender_name` | El mensaje que este cita. Envía `text` siempre que la plataforma lo proporcione. |

Describe cualquier otra cosa con palabras, como un segmento `text` del tipo `(sent a voice message)` o `(sent a file: deck.pdf)`. El agente descarta los tipos de segmento desconocidos.

Estos campos opcionales activan más funciones del agente:

| Campo | Significado |
|---|---|
| `connector_id` | Un id estable para esta instancia del conector. La bandeja de salida lo exige. |
| `reply_handle` | Lo que el conector necesite para llegar a esta conversación más tarde sin un mensaje entrante: el `unified_msg_origin` de AstrBot, un id de sala de Matrix o un inicio de sesión de Satori más un id de canal. El agente lo trata como opaco, lo guarda por conversación y lo devuelve en las entregas de la bandeja de salida. |
| `capabilities` | Lo que el conector puede hacer. `outbox` significa que consulta la bandeja de salida y puede enviar sin que se lo pidan. `quote_text` significa que los segmentos de respuesta llevan el texto citado. |
| `prefiltered` | `true` (el valor predeterminado) cuando el conector aplicó su propia lista de permitidos. `false` hace que las listas del agente sean el único filtro. |
| `proactive` | Marca un evento de mensaje directo como una señal escrita por el conector, no como palabras de la persona. Consulta «Hablar primero sin la bandeja de salida». |

La respuesta tiene este aspecto:

```json
{"handled": true, "owned": true, "replies": [
  {"type": "text", "text": "not bad, rained all afternoon", "mention_user_id": "telegram:42"},
  {"type": "image", "b64": "..."}
]}
```

- `replies`: envíalas en orden, cada una como un mensaje aparte. Cuando `mention_user_id` está presente, es el id con prefijo que hay que mencionar. Muestra la mención como lo haga la plataforma.
- `owned`: el agente se ha hecho cargo de esta conversación. Cuando es verdadero, impide que otra lógica de bot responda, aunque `replies` esté vacío, porque la persona decidió callar. Cuando es falso, el mensaje te toca a ti. O bien la conversación no está en las listas de permitidos del agente, o bien el agente no puede responder en absoluto (sin `LLM_API_KEY`, o `AGENT_ENABLED=false`). En el segundo caso, el registro del agente lleva una línea ERROR que indica la causa.
- La solicitud dura hasta que termina el turno, que es un breve antirrebote más el tiempo del modelo. Las llamadas al modelo de un turno comparten un único presupuesto de 1,5 × `LLM_TIMEOUT_S`, reintentos incluidos, tanto en un grupo como en un mensaje directo, y un mensaje que llega mientras un turno anterior de su conversación sigue pensando espera a que ese turno termine antes de empezar el suyo. Deja al menos 3 × `LLM_TIMEOUT_S` segundos (360 con el valor por defecto).
- Un comando de memoria (como «remember ...») que llega mientras un turno de su conversación sigue pensando se responde después de ese turno. Un conector que declaró `outbox` recibe `{"handled": false, "owned": true, "replies": []}` enseguida y el resultado más tarde como una entrega `follow_up`. Sin `outbox`, el resultado llega en la respuesta a una solicitud: la suya propia o la de otra solicitud en espera de la misma conversación, así que una respuesta puede traer `replies` que mencionan a alguien distinto del remitente del evento.

## Bandeja de salida: `POST /v1/outbox`

Algunos mensajes no responden a una solicitud. Por ejemplo, un saludo programado, la pregunta de seguimiento tras un rechazo, la respuesta a un comando de memoria que esperó detrás de un turno y la excusa cuando el modelo está caído en un grupo. El agente los pone en cola por conversación, y un conector que declaró `outbox` los recoge, así que un conector detrás de NAT o de un cortafuegos funciona igual. Las conversaciones guardadas con id de QQ sin prefijo (consulta Direcciones) también usan la bandeja de salida mientras su conector la consulta. Si no, pasan por la API HTTP de NapCat, cuando `QQ_ONEBOT_URL` está definido.

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

El agente retiene la solicitud hasta `wait_s` segundos (30 como máximo) hasta que algo entre en la cola, y entonces responde:

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

`items` tiene la misma forma que `replies`. `reason` es `proactive`, `follow_up` o `excuse`, y `conversation_type` es `group` o `dm`. `conversation_key` es la clave con la que el agente guarda la conversación, como `private:telegram:42` para un mensaje directo. `conversation_id` es el id sin procesar que traía el evento, que en un mensaje directo es el id de usuario. El agente recuerda `reply_handle`, `connector_id` y `capabilities` del último evento admitido en cada conversación, así que una conversación es alcanzable en cuanto ha enviado un mensaje.

Informa de cada entrega en `acks` en la siguiente consulta:

| `status` | Significado |
|---|---|
| `sent` | Salieron todos los elementos. |
| `partial` | Salieron los primeros `sent_items` elementos. |
| `failed` | No salió nada. |
| `expired` | El envío no empezó dentro de `expires_in_s`. |
| `refused` | El conector ya no permite la conversación. |
| `unsupported` | La plataforma no puede enviar sin que se lo pidan a esta conversación. |

Reglas:

- **Como máximo una vez.** El agente entrega algo una sola vez y nunca más, pase lo que pase con el ack. Conserva los últimos cientos de `delivery_id` y nunca envíes uno dos veces.
- **En orden.** Envía las entregas de una conversación en el orden en que las recibiste. Conversaciones distintas pueden salir en paralelo.
- **Solo cuentan las entregas confirmadas.** El agente trata una entrega sin confirmar como no enviada y registra como enviadas solo las confirmadas. Espera el ack hasta tu siguiente consulta, y como máximo `expires_in_s` más 60 segundos desde que entregó. Termina de enviar un lote antes de volver a consultar.
- **Actividad.** Un conector que no ha consultado durante 90 segundos se da por desaparecido. No se pone nada en cola para sus conversaciones hasta que vuelva a consultar, y lo que estuviera en cola para él, o entregado sin ack, termina como no enviado. Vuelve a consultar en cuanto se entregue un lote. Esa consulta también lleva los ack del lote.
- **`unsupported` persiste.** Tras ese ack, el agente deja de poner en cola para la conversación hasta que un evento traiga un `reply_handle` distinto.
- **Tipos de cuerpo.** La firma no cubre la ruta de la URL. Por eso el agente rechaza un cuerpo de evento en el endpoint de la bandeja de salida y un cuerpo `outbox.pull` en el endpoint de eventos, con `400` y el código `invalid_schema`. Un evento puede llevar `"kind": "event"`. Se rechaza un evento con cualquier otro `kind`.

Un 404 sin `code` significa que el agente no ofrece la bandeja de salida. Un `404` con el código `outbox_disabled` significa que el operador la desactivó con `CONNECTOR_OUTBOX_ENABLED`. En ambos casos, espera un buen rato antes de volver a consultar.

## Hablar primero sin la bandeja de salida

Un conector que no puede consultar sigue pudiendo abrir un mensaje directo. Su propio planificador, como una tarea de un plugin de AstrBot o una entrada de cron, envía un evento normal de mensaje directo con `"proactive": true` a `/v1/events`. El agente lee el texto como una señal para la persona («lleva un día callado; su examen era esta mañana»), lo corta a 500 caracteres y nunca lo guarda como palabras de la persona. Las instrucciones proactivas del motor siguen decidiendo el turno y pueden mantener callada a la persona. Si la persona habla, la respuesta vuelve en la respuesta HTTP para que el planificador la retransmita.

El evento necesita todo lo que llevan los eventos normales del conector: las cabeceras firmadas, todos los campos obligatorios, el mismo `platform` y `sender_id` sin procesar que el conector envía para esa persona, texto no vacío y un `message_id` nuevo cada vez. Un evento con un `message_id` repetido se descarta en silencio. La señal cuenta para el mismo tiempo de espera de mensajes directos que los saludos del propio agente (`PROACTIVE_DM_COOLDOWN_S`), y no cuenta como actividad de la persona.

Define siempre el indicador; sin él, el agente guarda la señal como palabras de la persona. Un evento de grupo con el indicador se reclama (`owned: true`, para que el conector mantenga callado a su bot) y se descarta sin leer.

## Capacidades y qué se degrada

| Falta | Efecto |
|---|---|
| `outbox` | Sin saludos programados, sin pregunta de seguimiento y sin excusa cuando falla una llamada al modelo en un grupo. Los id de QQ siguen recibiéndolos a través de NapCat cuando `QQ_ONEBOT_URL` está definido y es accesible. La excusa de un mensaje directo vuelve en los `replies` de la respuesta y no necesita la bandeja de salida. |
| `quote_text` | El agente solo entiende un mensaje citado si vio ese mensaje él mismo. |
| `reply_handle` | Igual que si falta `outbox`. |
| `addressed` incorrecto | La persona trata los mensajes dirigidos a ella como charla de fondo. |

## Escribir un conector

1. Recibe un mensaje de la plataforma. Omite los mensajes del propio bot y los eventos que no son mensajes (entradas, retiradas, toques).
2. Construye el evento descrito arriba. Define `addressed` según las propias reglas de mención y respuesta de la plataforma.
3. Firma y envía el evento. Envía `replies` en orden y, cuando `owned` sea verdadero, mantén callada otra lógica de bot.
4. Si la plataforma puede enviar sin que se lo pidan, añade `connector_id`, `reply_handle` y `capabilities: ["outbox"]`, y ejecuta el bucle de consulta: consulta, envía cada entrega a través de su `reply_handle` y confirma en la siguiente consulta.

`integrations/sdk/personagent_connector.py` se encarga de los pasos 3 y 4.
