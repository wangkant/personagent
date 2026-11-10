# Conector de Matrix

[English](README.md) · [简体中文](README.zh-CN.md) · [繁體中文](README.zh-TW.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · Español · [Français](README.fr.md) · [Deutsch](README.de.md) · [Português (Brasil)](README.pt-BR.md) · [Русский](README.ru.md)


Este conector lleva [personagent](https://github.com/wangkant/personagent) a salas de Matrix y, mediante [puentes mautrix](https://docs.mau.fi/bridges/), a WhatsApp, Signal, Messenger, Instagram, Google Messages y otras redes. Los puentes son software de terceros que usted ejecuta en un servidor doméstico bajo su control. personagent no los necesita para las plataformas que conecta desde su página local.

personagent también conecta Matrix por sí mismo, sin este conector: la vista **Conectar plataformas** de su página local, o `personagent connect matrix`, solicita la dirección del servidor doméstico, el token de acceso de la cuenta del bot y su propio ID de Matrix. Esa conexión integrada solo lee salas sin cifrado de extremo a extremo y solo se une a las salas a las que usted invita al bot desde ese ID de Matrix. Utilice este conector en su lugar cuando el bot deba leer salas cifradas, responder en portales de puentes o en salas a las que lo inviten otras personas, o cuando desee elegir salas y personas mediante listas de permitidos.

El conector es un pequeño proceso independiente basado en [matrix-nio](https://github.com/matrix-nio/matrix-nio), que admite cifrado de extremo a extremo sin libolm. Inicia sesión en un servidor doméstico (homeserver) como un usuario normal de Matrix, reenvía cada mensaje permitido de una sala al `POST /v1/events` del agente como un evento independiente de la plataforma ([docs/connectors.md](../../docs/connectors.es.md)) y publica las respuestas del agente en la sala. También consulta periódicamente la bandeja de salida del agente, de modo que los mensajes programados, las preguntas de seguimiento y las disculpas también llegan a Matrix.

## Funcionamiento

En la recepción, para cada mensaje de una sala permitida:

- El evento utiliza la plataforma `matrix` y los ID originales de Matrix, de modo que el agente guarda `matrix:@alex:example.org` y `matrix:!room:example.org`.
- Una sala se considera un chat directo cuando figura en el `m.direct` del bot, o cuando tiene exactamente un miembro además del bot y de los usuarios de `MATRIX_IGNORE_USERS`. Un chat directo se identifica por la persona, y un grupo, por la sala. Una sala indicada por su ID en `MATRIX_GROUPS` es siempre un grupo.
- `addressed` es verdadero cuando el mensaje menciona al bot o responde a uno de sus mensajes. Una mención es `m.mentions` o, en clientes demasiado antiguos para enviar `m.mentions`, una píldora o el ID de usuario del bot en el texto.
- Una respuesta incluye el remitente y el texto del mensaje citado. El conector los obtiene de una caché de eventos recientes o recupera el evento principal. Elimina el texto alternativo de respuesta que anteponen los clientes antiguos (`> <@alex:example.org> ...`), de modo que el agente nunca atribuye al remitente las palabras de otra persona.
- Las imágenes y los stickers de hasta 4 MB se descargan, se descifran en las salas cifradas y se envían al agente como bytes. Los mensajes de voz, los vídeos y los archivos se describen con palabras.
- Los mensajes de una sala llegan al agente en el orden en que se enviaron. Un mensaje enviado después de una imagen espera a que la imagen se descargue. El agente puede seguir procesando varios turnos a la vez.
- La marca de tiempo es el `origin_server_ts` del servidor doméstico.
- El conector omite los mensajes del propio bot, los mensajes `m.notice` (el tipo que envían los bots), las ediciones, las reacciones, los mensajes de `MATRIX_IGNORE_USERS`, los mensajes acumulados que devuelve la primera sincronización al iniciarse y todo lo anterior a `MATRIX_MAX_EVENT_AGE_S`, como el historial que un puente vuelca en una sala nueva.

En el envío:

- Las respuestas de texto son `m.text`. Cuando el agente solicita mencionar a alguien en un grupo, la respuesta comienza con una píldora e incluye a esa persona en `m.mentions`. Todas las demás respuestas incluyen un `m.mentions` vacío, de modo que ningún cliente convierte un nombre del texto en una notificación.
- Las respuestas con imagen se suben, y se cifran en las salas cifradas.
- Se muestra un indicador de escritura mientras el agente procesa un turno.
- Un mensaje de un hilo se responde en ese mismo hilo.
- Cuando el agente asume la conversación, el bot marca el mensaje como leído (`MATRIX_READ_RECEIPTS_ENABLED`). A través de un puente, esto aparece como la confirmación de lectura en la otra red.
- Las entregas de la bandeja de salida se dirigen a la última sala de la que procedió la conversación. El `reply_handle` del evento es el ID de la sala.

## Instalación

Se requiere un personagent en ejecución y una cuenta de Matrix para el bot. Cree una cuenta dedicada en lugar de compartir la de una persona.

El conector es un script de este repositorio, por lo que requiere una copia del repositorio (un clon o el ZIP de GitHub) y su propio entorno de Python, ya que `matrix-nio` no es una dependencia de personagent. En un clon que ya tenga el `.venv` de personagent, instálelo en ese entorno:

```bash
.venv/bin/python -m pip install -r integrations/matrix/requirements.txt
```

Si instaló personagent desde PyPI con pip, o lo ejecuta con uvx, cree un entorno virtual independiente junto a la copia:

```bash
python -m venv connector-venv
connector-venv/bin/python -m pip install -r integrations/matrix/requirements.txt
```

En Windows, el intérprete es `.venv\Scripts\python.exe` o `connector-venv\Scripts\python.exe`. A continuación, copie el archivo de ajustes:

```bash
cp integrations/matrix/.env.example integrations/matrix/.env
```

Edite `integrations/matrix/.env`:

```ini
MATRIX_URL=https://matrix.example.org
MATRIX_USER_ID=@nova:example.org
MATRIX_PASSWORD=...
MATRIX_GROUPS=!AbCdEf:example.org
MATRIX_DM_USERS=@alex:example.org
PERSONAGENT_URL=http://127.0.0.1:8080
```

A continuación, inicie el conector junto al agente, con el mismo intérprete:

```bash
.venv/bin/python integrations/matrix/matrix_connector.py
# or: .venv/bin/python integrations/matrix/matrix_connector.py --config /path/to/matrix.env
```

Invite al bot a una sala que figure en `MATRIX_GROUPS` y el bot se unirá a ella. En Element, el ID de la sala se encuentra en los ajustes de la sala, en Avanzado.

### Iniciar sesión

El inicio de sesión con contraseña es la forma más sencilla de comenzar. El conector guarda la sesión que obtiene (ID de usuario, ID de dispositivo y token de acceso) en `MATRIX_STORE_DIR/session.json` y la reutiliza en el siguiente inicio, de modo que un reinicio no crea un dispositivo nuevo. Elimine ese archivo para volver a iniciar sesión.

Para utilizar un token de acceso existente, defina `MATRIX_ACCESS_TOKEN`. El conector consulta al servidor doméstico a qué cuenta pertenece el token. No utilice el token de una sesión que use usted, ya que al cerrar esa sesión también se cierra la del bot.

Cuando el servidor doméstico cierra la sesión del bot (`M_UNKNOWN_TOKEN`), el conector se detiene con un error que lo indica. Tras un inicio de sesión con contraseña, al volver a iniciarlo se inicia sesión de nuevo. Con `MATRIX_ACCESS_TOKEN`, defina primero un token nuevo. Cualquier otra sincronización fallida se reintenta tras una espera que se duplica hasta un máximo de un minuto.

### Dónde puede ejecutarse el agente

El protocolo establece la regla. `PERSONAGENT_URL` debe ser una dirección de bucle local, o HTTPS con un `CONNECTOR_TOKEN` igual al `CONNECTOR_TOKEN` del agente. En caso contrario, el conector no se inicia. Defina el token en ambos lados antes de colocar un proxy o un túnel delante del agente, incluso en un único host.

## Ajustes

[.env.example](.env.example) enumera todos los ajustes. Las listas se separan con comas y admiten comodines, de modo que `@*:example.org` coincide con todo un servidor. Con una lista vacía no se responde a nadie. Un `*` aislado coincide con todos y marca el evento con `prefiltered: false`. En ese caso, deciden únicamente `ACCESS_GROUPS` / `ACCESS_DM_USERS` del propio agente, y se rechaza una plataforma que no tenga entradas en ellos.

| Ajuste | Significado |
|---|---|
| `MATRIX_GROUPS` | Salas de grupo en las que se responde, por ID de sala. `*` significa todas las salas a las que se ha unido el bot. |
| `MATRIX_DM_USERS` | Personas que pueden hablar con el bot en un chat directo. `*` significa todas. |
| `MATRIX_INVITE_FROM` | Usuarios cuyas invitaciones acepta el bot. Las invitaciones a salas indicadas en `MATRIX_GROUPS` y las de chat directo de `MATRIX_DM_USERS` se aceptan siempre. Las demás quedan pendientes. |
| `MATRIX_IGNORE_USERS` | Nunca reciben respuesta y no cuentan como miembros cuando el conector distingue un chat directo de un grupo. |
| `MATRIX_E2EE_ENABLED` | Cifrado de extremo a extremo. Consulte más abajo. |
| `MATRIX_TIMEOUT_S` | Duración máxima de un turno. Manténgalo por encima de 3 × `LLM_TIMEOUT_S` del agente. |
| `MATRIX_OUTBOX_ENABLED` | Consultar periódicamente la bandeja de salida del agente. |

## Puentes: WhatsApp, Signal, Messenger, Instagram y más

Un puente mautrix inicia sesión en otra red como una cuenta de esa red y refleja sus chats en salas de Matrix denominadas portales. Cada participante del otro lado aparece en Matrix como un usuario fantasma, como `@whatsapp_4912345:example.org`. Cuando la cuenta de Matrix del bot es la que inició sesión en el puente, el personaje reside en esa red. Un contacto de WhatsApp escribe al número del personaje, el puente publica el mensaje en una sala portal, este conector lo reenvía y la respuesta regresa por la misma vía.

| Red | Puente |
|---|---|
| WhatsApp | [mautrix-whatsapp](https://github.com/mautrix/whatsapp) |
| Signal | [mautrix-signal](https://github.com/mautrix/signal) |
| Facebook Messenger, mensajes directos de Instagram | [mautrix-meta](https://github.com/mautrix/meta) |
| Google Messages (RCS y SMS a través de un teléfono Android) | [mautrix-gmessages](https://github.com/mautrix/gmessages) |
| Google Voice, LinkedIn, mensajes directos de Twitter/X y Bluesky, Google Chat, iMessage | Los demás [puentes mautrix](https://github.com/mautrix) |
| Telegram, Discord, Slack, Zulip, IRC | Existen puentes, pero a estas redes se puede llegar sin ellos. personagent conecta Telegram, Discord, Zulip e IRC por sí mismo, y Slack a través del AstrBot que ejecuta su página local. |

Para configurar uno:

1. Ejecute un servidor doméstico que controle usted (Synapse u otro servidor que admita servicios de aplicación) e instale el puente según [su documentación](https://docs.mau.fi/bridges/). Asigne a la cuenta del bot el nivel de permiso `user` en los `permissions` del puente.
2. Inicie sesión en Element como el bot, abra un chat con el bot del puente (por ejemplo, `@whatsappbot:example.org`) y envíe `login`. Vincule la cuenta de la red que utilizará el personaje. Para WhatsApp, Signal y Google Messages, escanee el código QR con el teléfono del personaje. Para Messenger e Instagram, proporcione los datos de inicio de sesión de Meta. Consulte [Usar puentes](https://docs.mau.fi/bridges/general/using-bridges.html).
3. Permita que el conector se una a los portales y excluya los mensajes del propio puente:

   ```ini
   MATRIX_INVITE_FROM=@whatsappbot:example.org
   MATRIX_IGNORE_USERS=@whatsappbot:example.org,@whatsapp_4900000000:example.org
   MATRIX_DM_USERS=@whatsapp_*:example.org
   MATRIX_GROUPS=!groupPortal:example.org
   ```

   La segunda entrada de `MATRIX_IGNORE_USERS` es el fantasma del puente correspondiente al número del propio personaje. Sin [doble títere](https://docs.mau.fi/bridges/general/double-puppeting.html), un mensaje escrito en el teléfono del personaje llega a Matrix desde ese fantasma, y el bot se respondería a sí mismo. `MATRIX_GROUPS=*` reenvía todos los portales de grupo en los que está el bot, y personagent responde entonces solo en las salas que su `ACCESS_GROUPS` incluye como `matrix:!room:server`. Indique aquí los ID de sala para seleccionar las salas en el conector.

### Títeres

- El puente es un cliente no oficial de la red, con la sesión iniciada como una cuenta de usuario normal (un dispositivo vinculado o una sesión web). No utiliza una API para bots, y nada en la red identifica la cuenta como un bot.
- El personaje necesita su propia cuenta, normalmente con su propio número de teléfono, y el teléfono debe permanecer accesible. WhatsApp desconecta los dispositivos vinculados cuando el teléfono lleva unas dos semanas sin conexión, y Google Messages solo funciona mientras el teléfono Android está en línea.
- En los chats de grupo, la cuenta del personaje parece la de un miembro más. Informe a los participantes de que están hablando con un bot.
- Las reacciones, ediciones, eliminaciones, encuestas y llamadas no se reenvían al agente.

### Condiciones de cada red

Lea las condiciones de cada red antes de conectarla.

- [WhatsApp](https://www.whatsapp.com/legal/terms-of-service) incluye el envío automático de mensajes entre las comunicaciones no permitidas, prohíbe el uso no personal que no haya autorizado y puede bloquear las cuentas que incurran en cualquiera de ambas prácticas. Su vía autorizada para la automatización es WhatsApp Business Platform, que un puente no utiliza.
- [Signal](https://signal.org/legal/) también considera no permitido el envío automático de mensajes.
- [Facebook](https://www.facebook.com/terms.php) e [Instagram](https://help.instagram.com/581066165581870) prohíben el acceso automatizado sin permiso de Meta, y Meta puede bloquear una cuenta que inicie sesión desde un cliente que no reconoce.
- Google Messages está sujeto a las [condiciones de Google](https://policies.google.com/terms) y a las de su operador móvil para SMS y RCS, que puede cobrar o restringir los mensajes automatizados.

Utilice una cuenta dedicada cuya pérdida pueda asumir, solo en conversaciones en las que los participantes sepan que hablan con un bot, y lea [DISCLAIMER.md](../../docs/DISCLAIMER.es.md).

## Cifrado de extremo a extremo

Con `MATRIX_E2EE_ENABLED=false` (el valor predeterminado), el bot solo lee salas sin cifrar. En una sala cifrada registra que no puede descifrar el mensaje y nunca envía allí una respuesta en texto sin cifrar.

Con `MATRIX_E2EE_ENABLED=true`:

- `MATRIX_STORE_DIR` (de forma predeterminada, `runtime/` junto al script, que git ignora) guarda las claves del dispositivo y el token de sincronización. Conserve este directorio. Si se pierde, el bot pasa a ser un dispositivo nuevo que no puede leer nada cifrado antes de ese momento.
- El dispositivo debe ser el mismo entre reinicios. Un inicio de sesión con contraseña lo conserva mediante la sesión guardada. Con un token de acceso, defina `MATRIX_DEVICE_ID` con el dispositivo del token.
- El bot comparte sus claves con todos los dispositivos de la sala, estén verificados o no. No puede verificarse de forma interactiva, por lo que los participantes ven su dispositivo como no verificado. No dispone de copia de seguridad de claves ni de firma cruzada.
- Un mensaje cuya clave no ha llegado se registra y se omite, sin reintentos.
- Un puente mautrix puede cifrar sus portales ([cifrado de extremo a puente](https://docs.mau.fi/bridges/general/end-to-bridge-encryption.html)). El puente guarda esas claves en su servidor, por lo que la protección termina allí, y la otra red transporta el mensaje con su propio cifrado. Si su puente cifra los portales, active `MATRIX_E2EE_ENABLED`.

## Pruebas

`tests/test_matrix_connector.py` simula el cliente de Matrix y el agente, por lo que se ejecuta sin matrix-nio y sin red:

```bash
python -m pytest tests/test_matrix_connector.py
```
