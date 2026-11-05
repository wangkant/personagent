# Conector de Matrix

[English](README.md) · [简体中文](README.zh-CN.md) · [繁體中文](README.zh-TW.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · Español · [Français](README.fr.md) · [Deutsch](README.de.md) · [Português (Brasil)](README.pt-BR.md) · [Русский](README.ru.md)


Este conector pone [personagent](https://github.com/wangkant/personagent) en salas de Matrix y, mediante [puentes mautrix](https://docs.mau.fi/bridges/), en WhatsApp, Signal, Messenger, Instagram, Google Messages y otras redes. Matrix y los puentes son software de terceros que ejecutas tú. personagent no los necesita para las plataformas que conecta desde su página local.

El conector es un pequeño proceso independiente basado en [matrix-nio](https://github.com/matrix-nio/matrix-nio), que admite cifrado de extremo a extremo sin libolm. Inicia sesión en un homeserver como un usuario normal de Matrix, reenvía cada mensaje permitido de una sala al `POST /v1/events` del agente como evento neutro respecto a la plataforma ([docs/connectors.md](../../docs/connectors.es.md)) y publica las respuestas del agente en la sala. También sondea la bandeja de salida del agente, así que los mensajes programados, las preguntas de seguimiento y las excusas llegan igualmente a Matrix.

## Qué hace

Al recibir, para cada mensaje de una sala permitida:

- El evento usa la plataforma `matrix` y los ids originales de Matrix, así que el agente guarda `matrix:@alex:example.org` y `matrix:!room:example.org`.
- Una sala cuenta como chat directo cuando el `m.direct` del bot la lista, o cuando tiene exactamente un miembro además del bot y los usuarios de `MATRIX_IGNORE_USERS`. Un chat directo se identifica por la persona, y un grupo por la sala. Una sala nombrada por id en `MATRIX_GROUPS` siempre es un grupo.
- `addressed` es verdadero cuando el mensaje menciona al bot o responde a uno de sus mensajes. Una mención es `m.mentions` o, desde clientes demasiado antiguos para enviar `m.mentions`, una píldora o el id de usuario del bot en el texto.
- Una respuesta lleva el remitente y el texto del mensaje citado. El conector los toma de una caché de eventos recientes o recupera el evento padre. Elimina el texto alternativo de respuesta que anteponen los clientes antiguos (`> <@alex:example.org> ...`), así que el agente nunca lee las palabras de otro como si fueran del remitente.
- Las imágenes y stickers de hasta 4 MB se descargan, se descifran en salas cifradas y se envían al agente como bytes. Los mensajes de voz, vídeos y archivos se describen con palabras.
- Los mensajes de una sala llegan al agente en el orden en que se enviaron. Un mensaje enviado después de una imagen espera a que la imagen se descargue. El agente puede seguir trabajando en varios turnos a la vez.
- La marca de tiempo es el `origin_server_ts` del homeserver.
- El conector omite los mensajes del propio bot, los mensajes `m.notice` (el tipo que envían los bots), las ediciones, las reacciones, los mensajes de `MATRIX_IGNORE_USERS`, el atraso que devuelve la primera sincronización al arrancar y todo lo anterior a `MATRIX_MAX_EVENT_AGE_S`, como el historial que un puente vuelca en una sala nueva.

Al enviar:

- Las respuestas de texto son `m.text`. Cuando el agente pide mencionar a alguien en un grupo, la respuesta empieza con una píldora y lista a esa persona en `m.mentions`. Todas las demás respuestas llevan un `m.mentions` vacío, así que ningún cliente convierte un nombre del texto en un aviso.
- Las respuestas con imagen se suben, y se cifran en salas cifradas.
- Se muestra un aviso de escritura mientras el agente trabaja en un turno.
- Un mensaje en un hilo se responde en ese hilo.
- Cuando el agente se queda con la conversación, el bot marca el mensaje como leído (`MATRIX_READ_RECEIPTS_ENABLED`). A través de un puente, esto aparece como la marca de leído en la otra red.
- Las entregas de la bandeja de salida van a la sala de la que vino por última vez la conversación. El `reply_handle` del evento es el id de la sala.

## Instalación

Necesitas un personagent en ejecución y una cuenta de Matrix para el bot. Crea una cuenta dedicada en lugar de compartirla con una persona.

El conector es un script de este repositorio, así que necesita una copia del repositorio (un clon o el ZIP de GitHub) y su propio entorno de Python, porque `matrix-nio` no es una dependencia de personagent. En un clon que ya tenga el `.venv` de personagent, instala en ese entorno:

```bash
.venv/bin/python -m pip install -r integrations/matrix/requirements.txt
```

Si instalaste personagent desde PyPI con pip, o lo ejecutas con uvx, crea un venv aparte junto a la copia:

```bash
python -m venv connector-venv
connector-venv/bin/python -m pip install -r integrations/matrix/requirements.txt
```

En Windows, el intérprete es `.venv\Scripts\python.exe` o `connector-venv\Scripts\python.exe`. A continuación, copia el archivo de ajustes:

```bash
cp integrations/matrix/.env.example integrations/matrix/.env
```

Edita `integrations/matrix/.env`:

```ini
MATRIX_URL=https://matrix.example.org
MATRIX_USER_ID=@nova:example.org
MATRIX_PASSWORD=...
MATRIX_GROUPS=!AbCdEf:example.org
MATRIX_DM_USERS=@alex:example.org
PERSONAGENT_URL=http://127.0.0.1:8080
```

Luego inicia el conector junto al agente, con el mismo intérprete:

```bash
.venv/bin/python integrations/matrix/matrix_connector.py
# or: .venv/bin/python integrations/matrix/matrix_connector.py --config /path/to/matrix.env
```

Invita al bot a una sala listada en `MATRIX_GROUPS` y se unirá. En Element, el id de la sala está en los ajustes de la sala, en Avanzado.

### Iniciar sesión

Iniciar sesión con contraseña es la forma más fácil de empezar. El conector guarda la sesión que obtiene (id de usuario, id de dispositivo y token de acceso) en `MATRIX_STORE_DIR/session.json` y la reutiliza en el siguiente arranque, así que reiniciar no crea un dispositivo nuevo. Borra ese archivo para iniciar sesión de nuevo.

Para usar un token de acceso existente, define `MATRIX_ACCESS_TOKEN`. El conector pregunta al homeserver a qué cuenta pertenece el token. No uses el token de una sesión que usas tú, porque cerrar esa sesión también cierra la del bot.

Cuando el homeserver cierra la sesión del bot (`M_UNKNOWN_TOKEN`), el conector se detiene con un error que lo indica. Tras un inicio de sesión con contraseña, volver a arrancarlo inicia sesión de nuevo. Con `MATRIX_ACCESS_TOKEN`, define primero un token nuevo. Cualquier otra sincronización fallida se reintenta tras una espera que se duplica hasta un minuto.

### Dónde puede ejecutarse el agente

La regla la fija el protocolo. `PERSONAGENT_URL` debe ser una dirección de bucle local, o HTTPS con `CONNECTOR_TOKEN` igual al `CONNECTOR_TOKEN` del agente. Si no, el conector se niega a iniciarse. Define el token en ambos lados antes de poner un proxy o túnel delante del agente, incluso en un solo host.

## Ajustes

[.env.example](.env.example) lista todos los ajustes. Las listas van separadas por comas y aceptan comodines, así que `@*:example.org` coincide con todo un servidor. Una lista vacía no responde a nadie. Un `*` solo coincide con todos y marca el evento con `prefiltered: false`. Entonces deciden solo `ACCESS_GROUPS` / `ACCESS_DM_USERS` del propio agente, y una plataforma sin entradas allí se rechaza.

| Ajuste | Significado |
|---|---|
| `MATRIX_GROUPS` | Salas de grupo en las que responder, por id de sala. `*` significa todas las salas a las que se ha unido el bot. |
| `MATRIX_DM_USERS` | Personas que pueden hablar con el bot en un chat directo. `*` significa todos. |
| `MATRIX_INVITE_FROM` | Usuarios cuyas invitaciones acepta el bot. Las invitaciones a salas nombradas en `MATRIX_GROUPS` y las de chat directo de `MATRIX_DM_USERS` siempre se aceptan. Las demás quedan pendientes. |
| `MATRIX_IGNORE_USERS` | Nunca se les responde, y no cuentan como miembros cuando el conector distingue un chat directo de un grupo. |
| `MATRIX_E2EE_ENABLED` | Cifrado de extremo a extremo. Consulta más abajo. |
| `MATRIX_TIMEOUT_S` | Cuánto puede durar un turno. Mantenlo por encima de `LLM_TIMEOUT_S × (1 + LLM_MAX_RETRIES)` del agente. |
| `MATRIX_OUTBOX_ENABLED` | Sondear la bandeja de salida del agente. |

## Puentes: WhatsApp, Signal, Messenger, Instagram y más

Un puente mautrix inicia sesión en otra red como una cuenta de esa red y refleja sus chats en salas de Matrix llamadas portales. Todos los del otro lado aparecen en Matrix como un usuario fantasma, como `@whatsapp_4912345:example.org`. Cuando la cuenta de Matrix del bot es la que inició sesión en el puente, la persona vive en esa red. Un contacto de WhatsApp escribe al número de la persona, el puente publica el mensaje en una sala portal, este conector lo reenvía y la respuesta vuelve por el mismo camino.

| Red | Puente |
|---|---|
| WhatsApp | [mautrix-whatsapp](https://github.com/mautrix/whatsapp) |
| Signal | [mautrix-signal](https://github.com/mautrix/signal) |
| Facebook Messenger, mensajes directos de Instagram | [mautrix-meta](https://github.com/mautrix/meta) |
| Google Messages (RCS y SMS a través de un teléfono Android) | [mautrix-gmessages](https://github.com/mautrix/gmessages) |
| Google Voice, LinkedIn, mensajes directos de Twitter/X y Bluesky, Google Chat, Zulip, IRC, iMessage | Los demás [puentes mautrix](https://github.com/mautrix) |
| Telegram, Discord, Slack | Existen puentes mautrix, pero estas redes tienen API oficiales de bots. personagent conecta Telegram y Discord por sí mismo, y Slack a través del AstrBot que ejecuta su página local. |

Para configurar uno:

1. Ejecuta un homeserver que controles (Synapse u otro servidor que admita servicios de aplicación) e instala el puente siguiendo [su documentación](https://docs.mau.fi/bridges/). Da a la cuenta del bot el nivel de permiso `user` en los `permissions` del puente.
2. Inicia sesión en Element como el bot, abre un chat con el bot del puente (por ejemplo `@whatsappbot:example.org`) y envía `login`. Vincula la cuenta de red que usará la persona. Para WhatsApp, Signal y Google Messages, escanea el código QR con el teléfono de la persona. Para Messenger e Instagram, da el inicio de sesión de Meta. Consulta [Usar puentes](https://docs.mau.fi/bridges/general/using-bridges.html).
3. Deja que el conector se una a los portales y mantén fuera los mensajes del propio puente:

   ```ini
   MATRIX_INVITE_FROM=@whatsappbot:example.org
   MATRIX_IGNORE_USERS=@whatsappbot:example.org,@whatsapp_4900000000:example.org
   MATRIX_DM_USERS=@whatsapp_*:example.org
   MATRIX_GROUPS=!groupPortal:example.org
   ```

   La segunda entrada de `MATRIX_IGNORE_USERS` es el fantasma del puente para el número de la propia persona. Sin [doble títere](https://docs.mau.fi/bridges/general/double-puppeting.html), un mensaje escrito en el teléfono de la persona llega a Matrix desde ese fantasma, y el bot se respondería a sí mismo. `MATRIX_GROUPS=*` reenvía todos los portales de grupo en los que está el bot, y personagent responde entonces solo en las salas que su `ACCESS_GROUPS` lista como `matrix:!room:server`. Lista aquí ids de sala para elegir las salas en el conector.

### Títeres

- El puente es un cliente no oficial de la red, con la sesión iniciada como una cuenta de usuario normal (un dispositivo vinculado o una sesión web). No usa una API de bots, y nada en la red marca la cuenta como bot.
- La persona necesita su propia cuenta, normalmente con su propio número de teléfono, y el teléfono debe seguir accesible. WhatsApp desconecta los dispositivos vinculados cuando el teléfono lleva unas dos semanas sin conexión, y Google Messages solo funciona mientras el teléfono Android está en línea.
- En los chats de grupo, la cuenta de la persona parece un miembro más. Di a la gente que está hablando con un bot.
- Las reacciones, ediciones, eliminaciones, encuestas y llamadas no se reenvían al agente.

### Condiciones de cada red

Lee las condiciones de cada red antes de conectarla.

- [WhatsApp](https://www.whatsapp.com/legal/terms-of-service) incluye el envío automático de mensajes entre las comunicaciones no permitidas, prohíbe el uso no personal que no haya autorizado y puede bloquear las cuentas que hagan cualquiera de las dos cosas. Su vía autorizada para la automatización es WhatsApp Business Platform, que un puente no usa.
- [Signal](https://signal.org/legal/) también incluye el envío automático de mensajes como no permitido.
- [Facebook](https://www.facebook.com/terms.php) e [Instagram](https://help.instagram.com/581066165581870) prohíben el acceso automatizado sin permiso de Meta, y Meta puede bloquear una cuenta que inicie sesión desde un cliente que no reconoce.
- Google Messages está sujeto a las [condiciones de Google](https://policies.google.com/terms) y a las de tu operador móvil para SMS y RCS, que pueden cobrar o restringir los mensajes automatizados.

Usa una cuenta dedicada que puedas permitirte perder, solo en conversaciones en las que la gente sepa que habla con un bot, y lee [DISCLAIMER.md](../../docs/DISCLAIMER.es.md).

## Cifrado de extremo a extremo

Con `MATRIX_E2EE_ENABLED=false` (el valor predeterminado), el bot solo lee salas sin cifrar. En una sala cifrada registra que no puede descifrar el mensaje, y nunca envía allí una respuesta en texto plano.

Con `MATRIX_E2EE_ENABLED=true`:

- `MATRIX_STORE_DIR` (por defecto `runtime/` junto al script, que git ignora) guarda las claves del dispositivo y el token de sincronización. Conserva este directorio. Si se pierde, el bot se convierte en un dispositivo nuevo que no puede leer nada cifrado antes de ese momento.
- El dispositivo debe ser el mismo entre reinicios. Un inicio de sesión con contraseña lo mantiene mediante la sesión guardada. Con un token de acceso, define `MATRIX_DEVICE_ID` con el dispositivo del token.
- El bot comparte sus claves con todos los dispositivos de la sala, verificados o no. No puede verificarse de forma interactiva, así que la gente ve su dispositivo como no verificado. No tiene copia de seguridad de claves ni firma cruzada.
- Un mensaje cuya clave no ha llegado se registra y se omite, sin reintentos.
- Un puente mautrix puede cifrar sus portales ([cifrado de extremo a puente](https://docs.mau.fi/bridges/general/end-to-bridge-encryption.html)). El puente guarda esas claves en tu servidor, así que la protección termina ahí, y la otra red lleva el mensaje con su propio cifrado. Si tu puente cifra los portales, activa `MATRIX_E2EE_ENABLED`.

## Pruebas

`tests/test_matrix_connector.py` simula el cliente de Matrix y el agente, así que se ejecuta sin matrix-nio y sin red:

```bash
python -m pytest tests/test_matrix_connector.py
```
