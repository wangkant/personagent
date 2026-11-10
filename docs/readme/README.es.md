<p align="center">
  <img src="https://raw.githubusercontent.com/wangkant/personagent/main/assets/personagent-cover.webp" alt="personagent" width="100%">
</p>

<h3 align="center">Un personaje para tus chats de grupo que sabe cuándo quedarse callado y aprende cuando lo corrigen.</h3>

<p align="center">
  <a href="https://pypi.org/project/personagent/"><img src="https://img.shields.io/pypi/v/personagent?style=flat-square&label=PyPI&labelColor=24292f&color=0969da&cacheSeconds=3600" alt="PyPI"></a>
  <a href="https://github.com/wangkant/personagent/actions/workflows/ci.yml"><img src="https://img.shields.io/github/actions/workflow/status/wangkant/personagent/ci.yml?branch=main&style=flat-square&label=CI&labelColor=24292f" alt="CI"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/Python-3.10%E2%80%933.14-0969da?style=flat-square&labelColor=24292f" alt="Python 3.10–3.14"></a>
  <a href="https://github.com/wangkant/personagent/blob/main/LICENSE"><img src="https://img.shields.io/badge/License-PolyForm%20Noncommercial-0969da?style=flat-square&labelColor=24292f" alt="Licencia: PolyForm Noncommercial"></a>
</p>

<p align="center"><a href="https://github.com/wangkant/personagent/blob/main/README.md">English</a> · <a href="https://github.com/wangkant/personagent/blob/main/README.zh-CN.md">简体中文</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.zh-TW.md">繁體中文</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.ja.md">日本語</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.ko.md">한국어</a> · <strong>Español</strong> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.fr.md">Français</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.de.md">Deutsch</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.pt-BR.md">Português</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.ru.md">Русский</a></p>

*Esta es una traducción del README en inglés, que es la versión de referencia y puede estar más actualizada.*

personagent es un personaje para tus chats de grupo: elige uno ya listo o escribe el tuyo, y hazlo funcionar con cualquier modelo compatible con OpenAI. Empieza chateando con él en tu propio ordenador y luego llévalo a QQ, WeChat, Telegram, Discord y dieciocho plataformas más desde la misma página local.

<p align="center">
  <img src="https://raw.githubusercontent.com/wangkant/personagent/main/docs/welcome.jpg" alt="La pantalla Conectar apps de la página local, con todas las plataformas a las que puede unirse" width="960">
</p>

<p align="center"><em>Conectar apps, en la misma página local que la configuración y el chat con el personaje.</em></p>

## Por qué personagent

<table>
<tr>
<td width="220" valign="top"><strong>Sabe cuándo quedarse callado.</strong></td>
<td valign="top">
Responde cuando lo llaman. Si no, un modelo juzga si una persona intervendría.<br>
Una ráfaga de mensajes recibe una sola respuesta.
</td>
</tr>
<tr>
<td width="220" valign="top"><strong>Aprende de las correcciones que se sostienen.</strong></td>
<td valign="top">
Lo que enseña una corrección, como el nombre que el grupo le da al gimnasio, se aplica a todas las respuestas posteriores en ese chat.<br>
Un troll o un mero espectador no pueden reentrenarlo.<br>
Cada cambio queda registrado y cualquiera de ellos se puede revertir.
</td>
</tr>
<tr>
<td width="220" valign="top"><strong>Es fácil de empezar y vive donde está tu grupo.</strong></td>
<td valign="top">
Un solo comando lo abre en tu ordenador, en inglés, en chino o en otros ocho idiomas.<br>
Pega una clave de modelo para chatear y luego conecta una app escaneando con el teléfono o pegando uno o dos valores.
</td>
</tr>
<tr>
<td width="220" valign="top"><strong>Puede ser un personaje listo o el tuyo.</strong></td>
<td valign="top">
Siete personalidades listas. Tres son personajes que la comunidad ya dibuja: la chica ballena de DeepSeek, la chica dragón de GPT y la señorita Claude, con retratos que parpadean, piensan y hablan.<br>
Reescribe el perfil del personaje cuando quieras. Lo que ha aprendido se conserva.
</td>
</tr>
</table>

Cada chat tiene su propia memoria, y olvida cuando se lo piden: `Nova, remember Sam is vegetarian`, `Nova, forget vegetarian` ([comandos de memoria](https://github.com/wangkant/personagent/blob/main/docs/guide.es.md#comandos-de-memoria)).

## Empieza aquí

```sh
python -m pip install personagent
personagent
```

Con [uv](https://docs.astral.sh/uv/), `uvx personagent` lo ejecuta sin un paso de instalación aparte. En Windows también puedes descargar el ZIP del código fuente y hacer doble clic en `start.bat`.

En Windows se abre en una ventana propia, y en macOS y Linux, en el navegador. Pega la clave de API de tu modelo y haz clic en **Verificar y empezar a chatear**. ¿Aún no tienes clave? Los modelos gratuitos de OpenRouter vienen preseleccionados, y su clave no cuesta nada. `personagent demo` reproduce tres escenas con guion sin ninguna clave. La [guía de inicio](https://github.com/wangkant/personagent/blob/main/docs/start.es.md) recorre la página pantalla por pantalla.

personagent es gratis. Pagas al servicio de modelos que elijas, a sus propias tarifas. Los modelos gratuitos de OpenRouter permiten 50 solicitudes al día, y algunos proveedores gratuitos conservan lo que reciben; Ollama ejecuta un modelo en tu propia computadora sin clave.

## Llévalo a tu grupo

Abre **Conectar apps** en la página local:

| En la página | Apps | Qué necesitas |
|---|---|---|
| Escanear para conectar | QQ, WeChat personal | Tu teléfono. Los bots de WeChat solo admiten chats uno a uno |
| Pegar uno o dos valores | Telegram, Discord, Matrix, Twitch, IRC, Zulip, VK, Stoat, KOOK, Feishu/Lark, DingTalk, Slack, bot de IA de WeCom, Mattermost, Misskey | Valores de la consola de la app; la página te dice cuáles |
| Avanzado | App de WeCom, cuenta oficial de WeChat, webhook de QQ, OneBot v11 (NapCat), Satori | Una dirección pública u otro software en esta computadora |

Las apps conectadas vuelven a iniciarse cada vez que arranca personagent. personagent conecta por sí mismo las apps que se conectan escaneando, Telegram, Discord, Matrix, Twitch, IRC, Zulip, VK y Stoat; el resto pasa por un [AstrBot](https://github.com/AstrBotDevs/AstrBot) que descarga y ejecuta en segundo plano. En un servidor, `personagent up` lo inicia todo sin navegador. La configuración de cada app está en la [guía de usuario](https://github.com/wangkant/personagent/blob/main/docs/guide.es.md#ponlo-en-un-chat), y QQ desde cero en la [guía de despliegue en chino](https://github.com/wangkant/personagent/blob/main/docs/deploy.zh-CN.md).

¿Ya usas AstrBot, Koishi o Matrix? personagent puede funcionar detrás de cualquiera de ellos como el personaje: consulta [puentes que ejecutas tú](https://github.com/wangkant/personagent/blob/main/docs/guide.es.md#puentes-que-ejecutas-tú), el [conector de Satori](https://github.com/wangkant/personagent/blob/main/integrations/satori/README.es.md) y el [conector de Matrix](https://github.com/wangkant/personagent/blob/main/integrations/matrix/README.es.md).

## Agentes de programación

**Deja que uno lo configure.** Dale la línea de abajo a un agente de programación que pueda ejecutar comandos en tu computadora. La clave del modelo la pegas tú en la página local, así que nunca pasa por el agente.

```text
Lee https://raw.githubusercontent.com/wangkant/personagent/main/docs/setup-for-agents.md y configura personagent por mí.
```

**Habla con tu personaje mientras trabajas.** Claude Code, Codex y DeepSeek Harness (`dsh`) pueden hablar con el personaje, con el mismo chat y la misma memoria que en la página local:

```bash
personagent connect claude-code
personagent connect codex
personagent connect dsh
```

`--remove` lo quita otra vez, y **Asistentes de programación**, en **Conectar plataformas**, permite hacer ambas cosas desde la página. La [guía](https://github.com/wangkant/personagent/blob/main/docs/guide.es.md#agentes-de-código) explica los permisos y `--react`, que deja que el personaje diga una frase al terminar un turno.

## Actualizar y desinstalar

Cuando hay una versión más nueva en PyPI, la página muestra un aviso con el comando de actualización. Con pip es `python -m pip install -U personagent`. En la mayoría de las instalaciones, **Actualizar y volver a abrir**, en la vista **Aplicación** de la página, lo ejecuta por usted. Los ajustes, el personaje, lo que ha aprendido y las apps conectadas se conservan. Para quitarlo, sigue los [pasos de desinstalación](https://github.com/wangkant/personagent/blob/main/docs/setup-for-agents.md#undoing-it) (en inglés).

## Privacidad

Todo lo que personagent guarda se queda en tu máquina, en una sola carpeta principal. El proveedor de modelos que elijas ve las conversaciones a las que responde, y una vez al día personagent consulta a pypi.org si hay una versión más nueva (`UPDATE_CHECK_ENABLED=false` lo desactiva). Antes de conectarlo con personas reales, diles que es un bot y obtén su consentimiento; la [guía](https://github.com/wangkant/personagent/blob/main/docs/guide.es.md#privacidad-y-consentimiento) detalla qué va a dónde.

## Documentación

- [Guía de usuario](https://github.com/wangkant/personagent/blob/main/docs/guide.es.md): configuración, conectores, cómo enseñarle, la vista Actividad y solución de problemas.
- [Guía de despliegue](https://github.com/wangkant/personagent/blob/main/docs/deploy.es.md): ponerlo en marcha de verdad, costos y qué revisar cuando el bot se queda callado.
- [Protocolo de conectores](https://github.com/wangkant/personagent/blob/main/docs/connectors.es.md): para escribir tu propio conector.
- [Herramientas](https://github.com/wangkant/personagent/blob/main/docs/tools.es.md): los scripts de `tools/`, para ejecutarlos desde un clon.
- [Registro de cambios](https://github.com/wangkant/personagent/blob/main/CHANGELOG.md) · [Cómo contribuir](https://github.com/wangkant/personagent/blob/main/.github/CONTRIBUTING.md) · [Política de seguridad](https://github.com/wangkant/personagent/blob/main/.github/SECURITY.md) · [Aviso legal](https://github.com/wangkant/personagent/blob/main/docs/DISCLAIMER.es.md)

## Licencia

personagent se publica bajo la [PolyForm Noncommercial License 1.0.0](https://github.com/wangkant/personagent/blob/main/LICENSE) © 2026 Qiankang (Kant) Wang: su uso, modificación y distribución son gratuitos con fines no comerciales, y no se permiten con fines comerciales. Los conectores de `integrations/` siguen bajo la licencia MIT, igual que las versiones hasta la 1.4.0. Los tres retratos de personajes tienen licencia CC BY-NC-SA 4.0, con los créditos en [persona_agent/static/characters/LICENSE.md](https://github.com/wangkant/personagent/blob/main/persona_agent/static/characters/LICENSE.md).

## Agradecimientos

- Las demás plataformas de chat se alcanzan a través de [AstrBot](https://github.com/AstrBotDevs/AstrBot), [NapCat](https://github.com/NapNeko/NapCatQQ), [Koishi](https://koishi.chat) con [satori-python](https://github.com/RF-Tar-Railt/satori-python), y [matrix-nio](https://github.com/matrix-nio/matrix-nio) con los [puentes de mautrix](https://docs.mau.fi/bridges/); la conexión con WeChat sigue las [notas del protocolo openclaw-weixin](https://github.com/Tencent/openclaw-weixin/blob/main/docs/protocol.md) de Tencent.
- El aprendizaje a partir de reacciones se basa en [Self-Feeding Chatbot](https://arxiv.org/abs/1901.05415), [Alexa self-learning](https://arxiv.org/abs/1911.02557) y [BlenderBot 3x](https://arxiv.org/abs/2306.04707); el lorebook sigue el World Info de [SillyTavern](https://github.com/SillyTavern/SillyTavern).
