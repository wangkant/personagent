<p align="center">
  <img src="https://raw.githubusercontent.com/wangkant/personagent/main/assets/personagent-cover.webp" alt="personagent" width="100%">
</p>

<h3 align="center">Un agente que se comporta como una persona, en todas las plataformas que usted utiliza.<br>Tiene un carácter propio, recuerda, aprende de las personas con las que habla y decide por sí mismo cuándo intervenir.</h3>

<p align="center">
  <a href="https://pypi.org/project/personagent/"><img src="https://img.shields.io/pypi/v/personagent?style=flat-square&label=PyPI&labelColor=24292f&color=0969da&cacheSeconds=3600" alt="PyPI"></a>
  <a href="https://github.com/wangkant/personagent/actions/workflows/ci.yml"><img src="https://img.shields.io/github/actions/workflow/status/wangkant/personagent/ci.yml?branch=main&style=flat-square&label=CI&labelColor=24292f" alt="CI"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/Python-3.10%E2%80%933.14-0969da?style=flat-square&labelColor=24292f" alt="Python 3.10–3.14"></a>
  <a href="https://github.com/wangkant/personagent/blob/main/LICENSE"><img src="https://img.shields.io/badge/License-PolyForm%20Noncommercial-0969da?style=flat-square&labelColor=24292f" alt="Licencia: PolyForm Noncommercial"></a>
</p>

<p align="center"><a href="https://github.com/wangkant/personagent/blob/main/README.md">English</a> · <a href="https://github.com/wangkant/personagent/blob/main/README.zh-CN.md">简体中文</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.zh-TW.md">繁體中文</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.ja.md">日本語</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.ko.md">한국어</a> · <strong>Español</strong> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.fr.md">Français</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.de.md">Deutsch</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.pt-BR.md">Português</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.ru.md">Русский</a></p>

*Esta es una traducción del README en inglés, que es la versión de referencia y puede estar más actualizada.*

personagent es un agente que se comporta como una persona: tiene un carácter propio, recuerda, aprende de las personas con las que habla y decide por sí mismo cuándo intervenir. Funciona allí donde usted lo necesite: en chats de grupo y chats privados de QQ, WeChat, Telegram, Discord y otras dieciocho plataformas, en una ventana de su equipo y dentro de asistentes de programación como Claude Code y Codex. Usted elige o redacta su carácter, y funciona con cualquier modelo compatible con OpenAI.

<p align="center">
  <img src="https://raw.githubusercontent.com/wangkant/personagent/main/docs/welcome.jpg" alt="La vista Conectar plataformas de la página local: las plataformas que se conectan escaneando un código o pegando algunos valores, las plataformas avanzadas contraídas y los asistentes de programación a los que puede unirse" width="960">
</p>

<p align="center"><em>Conectar plataformas, en la misma página local que la configuración y el chat con el personaje.</em></p>

## Por qué personagent

<table>
<tr>
<td width="220" valign="top"><strong>Tiene un carácter propio.</strong></td>
<td valign="top">
Siete personalidades predefinidas. Tres son personajes que la comunidad ya dibuja: la chica ballena de DeepSeek, la chica dragón de GPT y la dama Claude, con retratos que parpadean, piensan y hablan.<br>
Puede modificar el perfil del personaje en cualquier momento. Lo que ha aprendido se conserva.
</td>
</tr>
<tr>
<td width="220" valign="top"><strong>Habla como una persona.</strong></td>
<td valign="top">
Escribe como escriben las personas en un chat: frases cortas y sencillas en el idioma de la conversación, sin listas, títulos ni fórmulas de asistente, y dice que no sabe algo cuando no lo sabe.<br>
En la mayoría de las plataformas, la respuesta llega en varios mensajes cortos, con una pausa entre ellos como la de quien escribe; Telegram, Discord y Matrix muestran además el indicador de escritura.<br>
Recoge los stickers que envían las personas y los usa cuando encajan, y de madrugada apenas interviene si no lo llaman.<br>
Si usted lo activa, inicia una conversación tras un silencio prolongado y retoma los planes que las personas mencionaron.
</td>
</tr>
<tr>
<td width="220" valign="top"><strong>Recuerda.</strong></td>
<td valign="top">
Cada chat tiene su propia memoria: mensajes recientes que se conservan tras un reinicio, un resumen de la conversación anterior, acontecimientos con fecha y hechos sobre las personas, que mantiene actualizados por sí mismo.<br>
Todo lo que recuerda aparece en la vista Actividad, donde cualquier elemento puede olvidarse o recuperarse.
</td>
</tr>
<tr>
<td width="220" valign="top"><strong>Aprende de las correcciones fundadas.</strong></td>
<td valign="top">
Lo que enseña una corrección, como el nombre que el grupo da al gimnasio, se aplica a todas las respuestas posteriores en ese chat.<br>
Un troll o un simple espectador no pueden volver a entrenarlo.<br>
Cuando las reacciones no pueden resolver un cambio, decide por sí mismo y registra el motivo; nadie tiene que aprobar nada.<br>
Cada cambio queda registrado y cualquiera de ellos puede revertirse.
</td>
</tr>
<tr>
<td width="220" valign="top"><strong>Sabe cuándo guardar silencio.</strong></td>
<td valign="top">
En un grupo, responde cuando se dirigen a él. En caso contrario, un modelo determina si una persona intervendría.<br>
Una ráfaga de mensajes recibe una sola respuesta.
</td>
</tr>
<tr>
<td width="220" valign="top"><strong>Se conecta a todas sus plataformas.</strong></td>
<td valign="top">
Veintidós plataformas de chat se conectan desde una sola página, escaneando un código con el teléfono o pegando algunos valores. La mayoría admite tanto chats de grupo como chats privados.<br>
El mismo agente responde en una ventana de su equipo y dentro de Claude Code, Codex y DeepSeek Harness.<br>
Cualquier otra plataforma puede añadirse mediante un puente de AstrBot, Koishi o Matrix, o con un conector que usted mismo escriba.
</td>
</tr>
<tr>
<td width="220" valign="top"><strong>Funciona con lo que usted ya tiene.</strong></td>
<td valign="top">
Cualquier modelo compatible con OpenAI: los modelos gratuitos de OpenRouter, un servicio de pago o uno que se ejecute en su propio equipo con Ollama.<br>
Un solo comando lo abre, en inglés, en chino o en otros ocho idiomas, y basta con pegar una clave de modelo para empezar a chatear.
</td>
</tr>
</table>

También recuerda y olvida lo que se le pide en el chat: `Nova, remember Sam is vegetarian`, `Nova, forget vegetarian` ([comandos de memoria](https://github.com/wangkant/personagent/blob/main/docs/guide.es.md#comandos-de-memoria)). Qué conserva y durante cuánto tiempo se explica en la sección [memoria](https://github.com/wangkant/personagent/blob/main/docs/guide.es.md#memoria) de la guía.

## Primeros pasos

```sh
python -m pip install personagent
personagent
```

Con [uv](https://docs.astral.sh/uv/), `uvx personagent` lo ejecuta sin un paso de instalación independiente. En Windows también puede descargar el ZIP del código fuente y hacer doble clic en `start.bat`.

En Windows se abre en una ventana propia, y en macOS y Linux, en el navegador. Pegue la clave de API de su modelo y seleccione **Verificar e iniciar el chat**. ¿Todavía no dispone de una clave? Los modelos gratuitos de OpenRouter están preseleccionados, y su clave no tiene coste. `personagent demo` reproduce tres escenas guionizadas sin ninguna clave. La [guía de primeros pasos](https://github.com/wangkant/personagent/blob/main/docs/start.es.md) recorre la página pantalla por pantalla.

personagent es gratuito. Usted paga al servicio de modelos que elija, según sus propias tarifas. Un mensaje puede generar más de una solicitud al modelo: además de la respuesta, el personaje a veces decide si intervenir en un grupo, valora cómo se recibió una respuesta u ordena su memoria. Los modelos gratuitos de OpenRouter admiten 50 solicitudes al día, y algunos proveedores gratuitos conservan lo que reciben; Ollama ejecuta un modelo en su propio equipo sin clave.

## Conectar sus plataformas

Abra **Conectar plataformas** en la página local:

| En la página | Plataformas | Requisitos |
|---|---|---|
| Escanear para conectar | QQ, WeChat personal | Su teléfono. Los bots de WeChat solo admiten chats individuales |
| Pegar algunos valores | Telegram, Discord, Matrix, Twitch, IRC, Zulip, VK, Stoat, KOOK, Feishu/Lark, DingTalk, Slack, bot de IA de WeCom, Mattermost, Misskey | Valores de la consola de la plataforma; la página indica cuáles |
| Avanzado | App de WeCom, cuenta oficial de WeChat, webhook de QQ, OneBot v11 (NapCat), Satori | Una dirección pública u otro software en este equipo |

Las plataformas conectadas se vuelven a iniciar cada vez que se inicia personagent. personagent conecta por sí mismo las plataformas que se conectan mediante escaneo, Telegram, Discord, Matrix, Twitch, IRC, Zulip, VK y Stoat; las demás utilizan un [AstrBot](https://github.com/AstrBotDevs/AstrBot) que descarga y ejecuta en segundo plano. En un servidor sin pantalla, `personagent connect <plataforma>` conecta cualquiera de esas diez plataformas desde el terminal, con los mismos pasos y comprobaciones que la página, y `personagent up` lo inicia todo sin navegador. La configuración de cada plataforma se describe en la [guía de usuario](https://github.com/wangkant/personagent/blob/main/docs/guide.es.md#llevar-el-personaje-a-un-chat), y la de QQ desde cero, en la [guía de despliegue en chino](https://github.com/wangkant/personagent/blob/main/docs/deploy.zh-CN.md).

¿Ya utiliza AstrBot, Koishi o Matrix? personagent puede funcionar detrás de cualquiera de ellos como el agente: consulte [puentes que ejecuta usted](https://github.com/wangkant/personagent/blob/main/docs/guide.es.md#puentes-que-ejecuta-usted), el [conector de Satori](https://github.com/wangkant/personagent/blob/main/integrations/satori/README.es.md) y el [conector de Matrix](https://github.com/wangkant/personagent/blob/main/integrations/matrix/README.es.md).

## Asistentes de programación

**Configuración mediante un asistente.** Proporcione la línea siguiente a un asistente de programación que pueda ejecutar comandos en su equipo. Usted mismo pega la clave del modelo en la página local, por lo que la clave nunca pasa por el asistente.

```text
Lee https://raw.githubusercontent.com/wangkant/personagent/main/docs/setup-for-agents.md y configura personagent por mí.
```

**Conversación con el personaje mientras trabaja.** Claude Code, Codex y DeepSeek Harness (`dsh`) pueden hablar con el personaje, con el mismo chat y la misma memoria que en la página local:

```bash
personagent connect claude-code
personagent connect codex
personagent connect dsh
```

`--remove` lo vuelve a quitar, y **Asistentes de programación**, en **Conectar plataformas**, permite hacer ambas cosas desde la página. La [guía](https://github.com/wangkant/personagent/blob/main/docs/guide.es.md#asistentes-de-programación) explica los permisos y `--react`, que permite que el personaje diga una frase al terminar un turno.

## Actualizar y desinstalar

Cuando hay una versión más reciente en PyPI, la página muestra un aviso con el comando de actualización. Con pip, el comando es `python -m pip install -U personagent`. En la mayoría de las instalaciones, **Actualizar y volver a abrir**, en la vista **Aplicación** de la página, lo ejecuta por usted. Los ajustes, el personaje, lo que ha aprendido y las plataformas conectadas se conservan. Para desinstalarlo, siga los [pasos de desinstalación](https://github.com/wangkant/personagent/blob/main/docs/setup-for-agents.md#undoing-it) (en inglés).

## Privacidad

Todo lo que personagent guarda permanece en su equipo, en una única carpeta de inicio. El proveedor de modelos que elija ve las conversaciones a las que responde, y una vez al día personagent consulta a pypi.org si hay una versión más reciente (`UPDATE_CHECK_ENABLED=false` lo desactiva). Antes de conectarlo con personas reales, infórmeles de que es un bot y obtenga su consentimiento; la [guía](https://github.com/wangkant/personagent/blob/main/docs/guide.es.md#privacidad-y-consentimiento) detalla qué información se envía a cada lugar.

## Documentación

- [Guía de usuario](https://github.com/wangkant/personagent/blob/main/docs/guide.es.md): configuración, conectores, cómo enseñar al personaje, la vista Actividad y solución de problemas.
- [Guía de despliegue](https://github.com/wangkant/personagent/blob/main/docs/deploy.es.md): puesta en producción, costes y qué revisar cuando el bot deja de responder.
- [Protocolo de conectores](https://github.com/wangkant/personagent/blob/main/docs/connectors.es.md): para escribir su propio conector.
- [Herramientas](https://github.com/wangkant/personagent/blob/main/docs/tools.es.md): los scripts de `tools/`, para ejecutarlos desde un clon.
- [Registro de cambios](https://github.com/wangkant/personagent/blob/main/CHANGELOG.md) · [Cómo contribuir](https://github.com/wangkant/personagent/blob/main/.github/CONTRIBUTING.md) · [Política de seguridad](https://github.com/wangkant/personagent/blob/main/.github/SECURITY.md) · [Aviso legal](https://github.com/wangkant/personagent/blob/main/docs/DISCLAIMER.es.md)

## Licencia

personagent se publica bajo la [PolyForm Noncommercial License 1.0.0](https://github.com/wangkant/personagent/blob/main/LICENSE) © 2026 Qiankang (Kant) Wang: su uso, modificación y distribución son gratuitos con fines no comerciales, y no se permiten con fines comerciales. Los conectores de `integrations/` siguen bajo la licencia MIT, al igual que las versiones hasta la 1.4.0. Los tres retratos de personajes tienen licencia CC BY-NC-SA 4.0, con los créditos en [persona_agent/static/characters/LICENSE.md](https://github.com/wangkant/personagent/blob/main/persona_agent/static/characters/LICENSE.md).

## Agradecimientos

- Las demás plataformas de chat se integran a través de [AstrBot](https://github.com/AstrBotDevs/AstrBot), [NapCat](https://github.com/NapNeko/NapCatQQ), [Koishi](https://koishi.chat) con [satori-python](https://github.com/RF-Tar-Railt/satori-python), y [matrix-nio](https://github.com/matrix-nio/matrix-nio) con los [puentes de mautrix](https://docs.mau.fi/bridges/); la conexión con WeChat sigue las [notas del protocolo openclaw-weixin](https://github.com/Tencent/openclaw-weixin/blob/main/docs/protocol.md) de Tencent.
- El aprendizaje a partir de reacciones se basa en [Self-Feeding Chatbot](https://arxiv.org/abs/1901.05415), [Alexa self-learning](https://arxiv.org/abs/1911.02557) y [BlenderBot 3x](https://arxiv.org/abs/2306.04707); el lorebook sigue el World Info de [SillyTavern](https://github.com/SillyTavern/SillyTavern).
