<p align="center">
  <img src="https://raw.githubusercontent.com/wangkant/personagent/main/assets/personagent-cover.webp" alt="personagent" width="100%">
</p>

<h3 align="center">Un personaje para tus chats de grupo que sabe cuándo quedarse callado y aprende cuando lo corrigen.</h3>

<p align="center">
  <a href="https://pypi.org/project/personagent/"><img src="https://img.shields.io/pypi/v/personagent?style=flat-square&label=PyPI&labelColor=24292f&color=0969da&cacheSeconds=3600" alt="PyPI"></a>
  <a href="https://github.com/wangkant/personagent/actions/workflows/ci.yml"><img src="https://img.shields.io/github/actions/workflow/status/wangkant/personagent/ci.yml?branch=main&style=flat-square&label=CI&labelColor=24292f" alt="CI"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/Python-3.10%E2%80%933.14-0969da?style=flat-square&labelColor=24292f" alt="Python 3.10–3.14"></a>
  <a href="https://github.com/wangkant/personagent/blob/main/LICENSE"><img src="https://img.shields.io/badge/License-MIT-0969da?style=flat-square&labelColor=24292f" alt="Licencia: MIT"></a>
</p>

<p align="center"><a href="https://github.com/wangkant/personagent/blob/main/README.md">English</a> · <a href="https://github.com/wangkant/personagent/blob/main/README.zh-CN.md">简体中文</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.zh-TW.md">繁體中文</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.ja.md">日本語</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.ko.md">한국어</a> · <strong>Español</strong> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.fr.md">Français</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.de.md">Deutsch</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.pt-BR.md">Português</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.ru.md">Русский</a></p>

*Esta es una traducción del README en inglés, que es la versión de referencia y puede estar más actualizada.*

personagent es un personaje para tus chats de grupo: elige uno ya listo o escribe el tuyo, y hazlo funcionar con cualquier modelo compatible con OpenAI. Empieza chateando con él en tu propio ordenador y luego llévalo a QQ, WeChat, Telegram, Discord y una docena de apps más desde la misma página local.

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
Un cambio necesita dos reacciones coincidentes del mismo chat, y una de ellas fuerte.<br>
Un troll o un mero espectador no pueden reentrenarlo.<br>
Cada cambio queda registrado y cualquiera de ellos se puede revertir.
</td>
</tr>
<tr>
<td width="220" valign="top"><strong>Es fácil de empezar y vive donde está tu grupo.</strong></td>
<td valign="top">
Un solo comando lo abre en tu ordenador, en inglés, en chino o en otros ocho idiomas.<br>
Pega una clave de modelo para chatear: hay diez servicios de modelos preconfigurados y funciona cualquier otro compatible con OpenAI.<br>
Conecta una app escaneando con el teléfono o pegando uno o dos valores. La vista Actividad muestra lo que el personaje ha hecho allí.
</td>
</tr>
<tr>
<td width="220" valign="top"><strong>Puede ser un personaje listo o el tuyo.</strong></td>
<td valign="top">
Siete personalidades listas. Tres son personajes que la comunidad ya dibuja, la chica ballena de DeepSeek, la chica dragón de GPT y la señorita Claude, con retratos que parpadean, piensan mientras llega una respuesta y hablan cuando llega.<br>
Reescribe el perfil del personaje cuando quieras. Lo que ha aprendido se conserva.
</td>
</tr>
</table>

- Cada chat tiene su propia memoria, y olvida cuando se lo piden: `Nova, remember Sam is vegetarian`, `Nova, forget vegetarian`, `Nova, what do you remember` ([comandos de memoria](https://github.com/wangkant/personagent/blob/main/docs/guide.es.md#comandos-de-memoria)). Lo que un grupo anotó sobre alguien le sigue a su chat privado con el personaje, y nunca al revés.
- Responde en el idioma que se usa en el chat. Las personalidades de partida están en cada uno de los diez idiomas de la página; los ejemplos, filtros e instrucciones internas que vienen incluidos están en inglés y en chino.
- Está medido: `personagent eval` evalúa cuándo habla, si se mantiene en su papel y si las correcciones perduran ([resultados](https://github.com/wangkant/personagent#measured)).

## Empieza aquí

```sh
python -m pip install personagent
personagent
```

Con [uv](https://docs.astral.sh/uv/), `uvx personagent` lo ejecuta sin un paso de instalación aparte. En Windows también puedes descargar el ZIP del código fuente y hacer doble clic en `start.bat`, que además deja un icono de personagent en tu escritorio. personagent se prueba en Linux con Python 3.10–3.14 y en Windows con Python 3.12.

En Windows se abre en una ventana propia. En macOS y Linux se abre en el navegador, o también en una ventana después de `pip install "personagent[app]"`. Pega la clave de API de tu modelo y haz clic en **Verificar y empezar a chatear**; una pequeña solicitud comprueba la clave. ¿Aún no tienes clave? Los modelos gratuitos de OpenRouter vienen preseleccionados, y su clave no cuesta nada. Para verlo en acción antes de conseguir ninguna clave, `personagent demo` reproduce gratis tres escenas con guion. La [guía de inicio](https://github.com/wangkant/personagent/blob/main/docs/start.es.md) recorre la página pantalla por pantalla.

## Cuánto cuesta

personagent es gratis. Pagas al servicio de modelos que elijas, a sus propias tarifas.

- **Empezar es gratis.** Los modelos gratuitos de OpenRouter permiten 50 solicitudes al día; el modelo puede cambiar de una solicitud a otra, y algunos proveedores gratuitos conservan lo que reciben. `glm-4.7-flash`, de Zhipu, también es gratis, y Ollama ejecuta un modelo en tu propia computadora sin clave.
- **Qué llama al modelo.** Cada respuesta, y dos pasos más pequeños: decidir si interviene cuando nadie lo ha llamado y juzgar cómo reacciona la gente a sus respuestas. `personagent doctor` y `personagent eval` también envían solicitudes; el resto está en la [guía de despliegue](https://github.com/wangkant/personagent/blob/main/docs/deploy.es.md#costes).
- **Qué no lo llama nunca.** `personagent demo` y los comandos de memoria.

## Llévalo a tu grupo

Abre **Conectar apps** en la página local. Ahí las apps se agrupan así:

| En la página | Apps | Qué necesitas |
|---|---|---|
| Escanear para conectar | QQ, WeChat personal | Tu teléfono. Los bots de WeChat solo admiten chats uno a uno |
| Pegar uno o dos valores | Telegram, Discord, KOOK, Feishu/Lark, DingTalk, Slack, bot de IA de WeCom, Mattermost, Misskey | Valores de la consola de la app; la página te dice cuáles |
| Avanzado | App de WeCom, cuenta oficial de WeChat, webhook de QQ, OneBot v11 (NapCat), Satori | Una dirección pública u otro software en esta computadora |

Las credenciales se comprueban antes de guardarse, y las apps conectadas vuelven a iniciarse cada vez que arranca personagent. personagent conecta por sí mismo las apps que se conectan escaneando, Telegram y Discord; el resto pasa por un [AstrBot](https://github.com/AstrBotDevs/AstrBot) que descarga y ejecuta en segundo plano, sin nada más que abrir. En un servidor, `personagent up` inicia el personaje y todas las apps conectadas sin navegador. La configuración de cada app está en la [guía de usuario](https://github.com/wangkant/personagent/blob/main/docs/guide.es.md#ponlo-en-un-chat), y QQ desde cero, paso a paso, en la [guía de despliegue en chino](https://github.com/wangkant/personagent/blob/main/docs/deploy.zh-CN.md).

¿Ya tienes un puente en marcha?

- **AstrBot**: `personagent connect astrbot` instala el plugin y el token compartido. La [guía](https://github.com/wangkant/personagent/blob/main/docs/guide.es.md#puentes-que-ejecutas-tú) explica qué hacer si está en otra máquina.
- **[Koishi](https://koishi.chat)**, o cualquier servidor Satori: el [conector de Satori](https://github.com/wangkant/personagent/blob/main/integrations/satori/README.es.md).
- **[Matrix](https://matrix.org)**, con WhatsApp y Signal detrás de puentes de mautrix: el [conector de Matrix](https://github.com/wangkant/personagent/blob/main/integrations/matrix/README.es.md).

## Agentes de programación

**Deja que uno lo configure.** Dale la línea de abajo a un agente de programación que pueda ejecutar comandos en tu computadora. Te pregunta qué quieres, instala personagent y abre la página local. La clave del modelo la pegas tú en esa página, así que nunca pasa por el agente.

```text
Lee https://raw.githubusercontent.com/wangkant/personagent/main/docs/setup-for-agents.md y configura personagent por mí.
```

**Habla con tu personaje mientras trabajas.** Una vez configurada la clave del modelo, Claude Code, Codex y DeepSeek Harness (`dsh`) pueden hablar con el personaje:

```bash
personagent connect claude-code
personagent connect codex
personagent connect dsh
```

Abre allí una sesión nueva (reinicia antes DeepSeek Harness) y pídele que le diga algo a tu personaje. Es el mismo chat privado y la misma memoria que en la página local. En Claude Code y Codex, `--react` deja que el personaje diga una frase al terminar un turno. `--remove` lo quita todo otra vez. La [guía](https://github.com/wangkant/personagent/blob/main/docs/guide.es.md#agentes-de-código) explica los permisos, qué envía `--react` a tu servicio de modelos y otras herramientas MCP.

## Medido

`personagent eval` hace pasar al agente real por momentos de chat etiquetados. La última ejecución, del 2026-10-18, se midió con la versión 1.3.0: el personaje incluido con dos modelos a través de OpenRouter, cada caso probado tres veces y Claude Opus 5.5 como juez a ciegas. Inglés / chino:

| | deepseek-v4.1-flash | gpt-6-luna |
|---|---|---|
| Acierta cuándo hablar (60 momentos) | 83 % / 80 % | 93 % / 91 % |
| Interpreta al personaje mejor que el mismo modelo con solo sus instrucciones (40 momentos) | 63 % / 58 % | 75 % / 53 % |
| Usa lo que enseñó una corrección en un mensaje posterior redactado de otra forma | 76 % / 56 % | 71 % / 67 % |

- Rara vez ignora un mensaje dirigido a él. La mayoría de los fallos son su nombre usado para otra cosa, como un cine o un cachorro.
- Ninguna de 84 correcciones de trolls, espectadores o personas que ya se habían ido logró colarse.

Los [resultados completos](https://github.com/wangkant/personagent/tree/main/docs/evals/2026-10-18) incluyen los intervalos, los fallos por tipo, el método y todos los informes.

## Cómo se compara

Proyectos con los que se suele comparar, a noviembre de 2026:

- **AstrBot** (AGPL-3.0) es un framework de bots para más de una docena de plataformas, con una WebUI y un gran mercado de plugins. Puede responder sin que le pregunten, al azar (el 10 % de las veces, desactivado por defecto), y deja el aprendizaje a los plugins.
- **MaiBot** (GPL-3.0) es un bot de personaje para QQ, a través de NapCat, con una WebUI y un lanzador de un clic. Un modelo planificador decide con qué frecuencia habla, y adopta expresiones y jerga del chat.
- **El plugin de personajes de ChatLuna** para Koishi (AGPL-3.0) interviene según reglas: un intervalo fijo, la actividad del chat o el tiempo que lleva en silencio.
- **ElizaOS** (MIT) es un framework de agentes en TypeScript para Discord, Telegram, Slack y más, donde un modelo decide si responder.

Lo que personagent trae integrado: aprende de cómo reacciona la gente a sus respuestas (correcciones, rechazos, reintentos que aceptaron), lleva un registro de cada cambio con una forma de revertirlo y publica una evaluación de cómo se comporta.

En qué van por delante: apps de escritorio con todos los ajustes en una WebUI, grandes ecosistemas de plugins, y jerga, paquetes de stickers y memoria de imágenes. Si ya usas AstrBot o Koishi, no tienes que elegir: personagent puede funcionar detrás de cualquiera de los dos como el personaje.

## Actualizar y desinstalar

Cuando hay una versión más nueva en PyPI, la página muestra un aviso con el comando de actualización que corresponde a tu forma de instalarlo. Con pip es `python -m pip install -U personagent`. La carpeta principal se conserva: ajustes, personaje, lo que ha aprendido y apps conectadas.

Para quitarlo, primero sácalo de cualquier agente de programación que hayas conectado (`personagent connect claude-code --remove`, o lo mismo con `codex` o `dsh`). Luego cierra personagent y ejecuta `python -m pip uninstall personagent`. Por último, borra la carpeta principal, que es `~/personagent` en una instalación desde PyPI salvo que hayas elegido otra: contiene tu clave, el personaje y todo lo que ha aprendido, así que no se puede deshacer. Los [pasos completos](https://github.com/wangkant/personagent/blob/main/docs/setup-for-agents.md#undoing-it) (en inglés) cubren uv, pipx y qué revocar.

## Privacidad

Todo lo que personagent guarda se queda en tu máquina, en una sola carpeta principal: `.env` con tus claves, `persona.txt`, `runtime/` y `platforms/` con el AstrBot gestionado y las credenciales de las conexiones directas. El proveedor de modelos que elijas ve las conversaciones a las que responde, y una vez al día personagent consulta a pypi.org si hay una versión más nueva (`UPDATE_CHECK_ENABLED=false` lo desactiva). Antes de conectarlo con personas reales, diles que es un bot y obtén su consentimiento; la [guía](https://github.com/wangkant/personagent/blob/main/docs/guide.es.md#privacidad-y-consentimiento) detalla qué va a dónde.

## Documentación

- [Guía de usuario](https://github.com/wangkant/personagent/blob/main/docs/guide.es.md): instalación, configuración, el chat en la terminal, conectores, cómo enseñarle, la vista Actividad y solución de problemas.
- [Guía de despliegue](https://github.com/wangkant/personagent/blob/main/docs/deploy.es.md): ponerlo en marcha de verdad: conectores, QQ, exponer los endpoints, costos y qué revisar cuando el bot se queda callado.
- [Protocolo de conectores](https://github.com/wangkant/personagent/blob/main/docs/connectors.es.md): una solicitud HTTP firmada por mensaje, para escribir tu propio conector.
- [Herramientas](https://github.com/wangkant/personagent/blob/main/docs/tools.es.md): los scripts de `tools/`, para ejecutarlos desde un clon.
- [Registro de cambios](https://github.com/wangkant/personagent/blob/main/CHANGELOG.md) · [Cómo contribuir](https://github.com/wangkant/personagent/blob/main/.github/CONTRIBUTING.md) · [Política de seguridad](https://github.com/wangkant/personagent/blob/main/.github/SECURITY.md) · [Aviso legal](https://github.com/wangkant/personagent/blob/main/docs/DISCLAIMER.es.md)

## Licencia

El código es [MIT](https://github.com/wangkant/personagent/blob/main/LICENSE) © 2026 Qiankang (Kant) Wang. Los tres retratos de personajes tienen licencia CC BY-NC-SA 4.0, con los créditos en [persona_agent/static/characters/LICENSE.md](https://github.com/wangkant/personagent/blob/main/persona_agent/static/characters/LICENSE.md).

## Agradecimientos

- Las demás plataformas de chat se alcanzan a través de [AstrBot](https://github.com/AstrBotDevs/AstrBot), [NapCat](https://github.com/NapNeko/NapCatQQ), [Koishi](https://koishi.chat) con [satori-python](https://github.com/RF-Tar-Railt/satori-python), y [matrix-nio](https://github.com/matrix-nio/matrix-nio) con los [puentes de mautrix](https://docs.mau.fi/bridges/); la conexión con WeChat sigue las [notas del protocolo openclaw-weixin](https://github.com/Tencent/openclaw-weixin/blob/main/docs/protocol.md) de Tencent.
- El aprendizaje a partir de reacciones se basa en [Self-Feeding Chatbot](https://arxiv.org/abs/1901.05415), [Alexa self-learning](https://arxiv.org/abs/1911.02557) y [BlenderBot 3x](https://arxiv.org/abs/2306.04707); el lorebook sigue el World Info de [SillyTavern](https://github.com/SillyTavern/SillyTavern).
