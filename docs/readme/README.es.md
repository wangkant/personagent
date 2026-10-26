<p align="center">
  <img src="https://raw.githubusercontent.com/wangkant/personagent/main/assets/personagent-cover.webp" alt="personagent: conversaciones ilustradas" width="100%">
</p>

<h3 align="center">Un personaje para tus chats de grupo que sabe cuándo quedarse callado y aprende cuando lo corrigen.</h3>

<p align="center">
  <a href="https://pypi.org/project/personagent/"><img src="https://img.shields.io/pypi/v/personagent?color=3776AB&label=PyPI&cacheSeconds=3600" alt="PyPI"></a>
  <a href="https://github.com/wangkant/personagent/actions/workflows/ci.yml"><img src="https://github.com/wangkant/personagent/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/Python-3.10%E2%80%933.14-3776AB?logo=python&logoColor=white" alt="Python 3.10–3.14"></a>
  <a href="https://github.com/wangkant/personagent/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-2f855a.svg" alt="Licencia: MIT"></a>
</p>

<p align="center"><a href="https://github.com/wangkant/personagent/blob/main/README.md">English</a> · <a href="https://github.com/wangkant/personagent/blob/main/README.zh-CN.md">简体中文</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.zh-TW.md">繁體中文</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.ja.md">日本語</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.ko.md">한국어</a> · <strong>Español</strong> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.fr.md">Français</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.de.md">Deutsch</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.pt-BR.md">Português</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.ru.md">Русский</a></p>

*Esta es una traducción del README en inglés, que es la versión de referencia y puede estar más actualizada. Las guías a las que enlaza están en inglés.*

personagent es un personaje para tus chats de grupo: elige uno o escribe el tuyo, y hazlo funcionar con cualquier modelo compatible con OpenAI. Se conecta por sí mismo a QQ, WeChat, Telegram y Discord, y desde la misma página a KOOK, Feishu, DingTalk, Slack, WeCom, Mattermost y Misskey.

Empieza con un chat local en el navegador: añade una clave de modelo y saluda. Cuando quieras llevar el personaje a un grupo, conecta una app escaneando con el teléfono o pegando uno o dos valores.

<p align="center">
  <img src="https://raw.githubusercontent.com/wangkant/personagent/main/docs/welcome.jpg" alt="La pantalla Conectar apps de la página local, con todas las plataformas a las que puede unirse" width="960">
</p>

<p align="center"><em>Conectar apps, en la misma página local que la configuración y el chat con el personaje. Captura de una instalación desechable con un modelo de prueba local.</em></p>

## Empieza aquí

Instálalo desde PyPI y ábrelo:

```sh
python -m pip install personagent
personagent
```

Con [uv](https://docs.astral.sh/uv/), `uvx personagent` lo ejecuta sin un paso de instalación aparte.

El navegador abre una página local con tres vistas: **Chat**, **Conectar apps** y **Personaje y ajustes**. Pega la clave de API de tu modelo y haz clic en **Verificar y empezar a chatear**; una pequeña solicitud la comprueba. Hay 10 servicios de modelos preconfigurados, además de cualquier otro compatible con OpenAI, y nombres y personalidades predefinidos para el personaje. El cuadro **Perfil del personaje** contiene `persona.txt`; al guardarlo, el agente se reinicia y conserva lo que ha aprendido. **Más funciones** activa la búsqueda web, la comprensión de imágenes y la opción de hablar primero. Si vuelves a ejecutar `personagent`, reutiliza la página que ya esté abierta. El menú de arriba a la derecha muestra la página en inglés, en chino o en otros ocho idiomas. El personaje responde en el idioma del chat; sus instrucciones internas y sus datos están en inglés y en chino, así que lo bien que se desenvuelva en otro idioma depende del modelo.

En Windows también puedes descargar el ZIP del código fuente y hacer doble clic en `start.bat`. Python 3.10–3.14. Consulta la [guía rápida de inicio](https://github.com/wangkant/personagent/blob/main/docs/start.md); los comandos de terminal y los conectores están en la [guía completa](https://github.com/wangkant/personagent/blob/main/docs/guide.md).

## Deja que tu agente de programación lo configure

Un agente de programación que pueda ejecutar comandos en tu computadora puede instalar y configurar personagent por ti. Dale esto:

```text
Lee https://raw.githubusercontent.com/wangkant/personagent/main/docs/setup-for-agents.md y configura personagent por mí.
```

Te pregunta el idioma, el nombre y la personalidad del personaje, tu servicio de modelos y las apps de chat que quieres; luego instala personagent, crea la carpeta principal y abre la página local. La clave del modelo la pegas tú en esa página, así que nunca pasa por el agente. Las [instrucciones que sigue](https://github.com/wangkant/personagent/blob/main/docs/setup-for-agents.md) son Markdown sencillo que también puedes leer.

## Por qué personagent

<table>
<tr>
<td width="220" valign="top"><img src="https://raw.githubusercontent.com/wangkant/personagent/main/persona_agent/static/listening.webp" alt="" width="220"></td>
<td valign="top">
<strong>Sabe cuándo quedarse callado.</strong><br>
Responde cuando lo llaman. Si no, un modelo juzga si una persona intervendría: nada de tirar los dados.<br>
Una ráfaga de mensajes recibe una sola respuesta, no una por mensaje.
</td>
</tr>
<tr>
<td width="220" valign="top"><img src="https://raw.githubusercontent.com/wangkant/personagent/main/persona_agent/static/learned-notebook.webp" alt="" width="220"></td>
<td valign="top">
<strong>Aprende de las correcciones que se sostienen.</strong><br>
Lo que enseña una corrección, como el nombre que el grupo le da al gimnasio, se aplica a todas las respuestas posteriores en ese chat.<br>
Un cambio necesita dos reacciones coincidentes del mismo chat, y una de ellas fuerte.<br>
Un troll o un mero espectador no pueden reentrenarlo.<br>
Cada cambio queda registrado y cualquiera de ellos se puede revertir.
</td>
</tr>
<tr>
<td width="220" valign="top"><img src="https://raw.githubusercontent.com/wangkant/personagent/main/persona_agent/static/empty-chats.webp" alt="" width="220"></td>
<td valign="top">
<strong>Es fácil de empezar y vive donde está tu grupo.</strong><br>
Configuración y chat en el navegador, en inglés, en chino o en otros ocho idiomas, con 11 servicios de modelos y ajustes avanzados opcionales.<br>
Se une por sí mismo a QQ, WeChat, Telegram y Discord, y a una docena de apps más desde la misma página; su vista Actividad muestra lo que ha hecho.
</td>
</tr>
</table>

- Cada chat tiene su propia memoria.
- Editar el personaje conserva lo que ha aprendido.
- Está medido: `personagent eval` evalúa cuándo habla, si se mantiene en su papel y si las correcciones perduran ([resultados](https://github.com/wangkant/personagent#measured)).

## Llévalo a tu grupo

Abre **Conectar apps** en la página local. Ahí las apps se agrupan así:

| En la página | Apps | Qué necesitas |
|---|---|---|
| Escanear para conectar | QQ, WeChat personal | Tu teléfono. Los bots de WeChat solo admiten chats uno a uno |
| Pegar uno o dos valores | Telegram, Discord, KOOK, Feishu/Lark, DingTalk, Slack, bot de IA de WeCom, Mattermost, Misskey | Valores de la consola de la app; la página te dice cuáles |
| Avanzado | App de WeCom, cuenta oficial de WeChat, webhook de QQ, OneBot v11 (NapCat), Satori | Una dirección pública u otro software en esta computadora |

Las credenciales se comprueban antes de guardarse, y las apps conectadas vuelven a iniciarse cada vez que arranca personagent. personagent conecta por sí mismo QQ, WeChat, Telegram y Discord; el resto pasa por un [AstrBot](https://github.com/AstrBotDevs/AstrBot) que descarga y ejecuta en segundo plano, sin nada más que abrir. En un servidor, `personagent up` inicia el personaje y todas las apps conectadas sin navegador.

**¿Ya usas AstrBot, Koishi o Matrix?** Para un AstrBot en esta computadora, `personagent connect astrbot` instala el plugin y el token compartido. Para uno en otra máquina, sube `astrbot_plugin_personagent.zip` de la [última versión](https://github.com/wangkant/personagent/releases/latest) mediante **Install from File** en su página de plugins, y luego configura su token y la dirección HTTPS de personagent como se describe en las guías de abajo. [Koishi](https://koishi.chat) se une mediante el [conector de Satori](https://github.com/wangkant/personagent/blob/main/integrations/satori/README.md), y [Matrix](https://matrix.org), con WhatsApp y Signal detrás de puentes de mautrix, mediante el [conector de Matrix](https://github.com/wangkant/personagent/blob/main/integrations/matrix/README.md).

La configuración de cada una está en la [guía de usuario](https://github.com/wangkant/personagent/blob/main/docs/guide.md#put-it-in-a-chat) y en la [guía de despliegue](https://github.com/wangkant/personagent/blob/main/docs/deploy.md); la [guía paso a paso en chino](https://github.com/wangkant/personagent/blob/main/docs/deploy.zh-CN.md) cubre QQ desde cero.

## Cómo se compara

Los proyectos con los que se suele comparar, según la documentación de cada uno en octubre de 2026:

- **AstrBot** (AGPL-3.0) es un framework de bots para más de 18 plataformas, con una WebUI y un gran mercado de plugins. Puede responder sin que le pregunten, al azar (el 10 % de las veces, desactivado por defecto), y deja el aprendizaje a los plugins.
- **MaiBot** (GPL-3.0) es un bot de personaje para QQ, a través de NapCat, con una WebUI y un lanzador de un clic. Un modelo planificador decide con qué frecuencia habla, y adopta expresiones y jerga del chat.
- **El plugin de personajes de ChatLuna** para Koishi (AGPL-3.0) interviene según reglas: un intervalo fijo, la actividad del chat o el tiempo que lleva en silencio.
- **ElizaOS** (MIT) es un framework de agentes en TypeScript para Discord, Telegram, Slack y más, donde un modelo decide si responder.

Lo que personagent trae integrado, donde los demás lo dejan a plugins o no lo describen: aprende de cómo reacciona la gente a sus respuestas (correcciones, rechazos, reintentos que aceptaron); un cambio necesita dos reacciones coincidentes del mismo chat, y una de ellas fuerte; cada cambio queda registrado y se puede revertir; y su comportamiento se mide en una evaluación publicada ([abajo](https://github.com/wangkant/personagent#measured)).

En qué van por delante: apps de escritorio con todos los ajustes en una WebUI, grandes ecosistemas de plugins, y jerga, paquetes de stickers y memoria de imágenes. Si ya usas AstrBot o Koishi, no tienes que elegir: personagent puede funcionar detrás de cualquiera de los dos como el personaje.

## Medido

`personagent eval` hace pasar al agente real por momentos de chat etiquetados. La última ejecución, el 2026-10-18, probó el personaje incluido con dos modelos a través de OpenRouter, repitió cada caso tres veces y usó Claude Opus 5.5 como juez a ciegas. Inglés / chino:

| | deepseek-v4.1-flash | gpt-6-luna |
|---|---|---|
| Acierta cuándo hablar (60 momentos) | 83 % / 80 % | 93 % / 91 % |
| Interpreta al personaje mejor que el mismo modelo con solo sus instrucciones (40 momentos) | 63 % / 58 % | 75 % / 53 % |
| Usa lo que enseñó una corrección en un mensaje posterior redactado de otra forma | 76 % / 56 % | 71 % / 67 % |

- Rara vez ignora un mensaje dirigido a él. La mayoría de los fallos son su nombre usado para otra cosa, como un cine o un cachorro.
- En chino, su ventaja sobre las instrucciones simples está dentro del margen de ruido.
- Antes de que las correcciones conservaran su lección, algo que se arregló tras la primera ejecución de ese día, solo 2 de 58 mensajes posteriores la aplicaban.
- Ninguna corrección de un troll, de un espectador o de alguien que se había ido logró colarse, en 84 intentos.

Los [resultados completos](https://github.com/wangkant/personagent/tree/main/docs/evals/2026-10-18) incluyen los intervalos, los fallos por tipo, el método, lo que las cifras no muestran y todos los informes.

## Documentación

- [Guía de usuario](https://github.com/wangkant/personagent/blob/main/docs/guide.md) ([中文](https://github.com/wangkant/personagent/blob/main/docs/guide.zh-CN.md)): instalación, configuración, el chat en la terminal, conectores, cómo enseñarle, la vista Actividad y solución de problemas.
- [Guía de despliegue](https://github.com/wangkant/personagent/blob/main/docs/deploy.md): ponerlo en marcha de verdad: conectores, QQ, exponer los endpoints, costos y qué revisar cuando el bot se queda callado.
- [Tutorial de despliegue en chino](https://github.com/wangkant/personagent/blob/main/docs/deploy.zh-CN.md): QQ desde cero, paso a paso.
- [Protocolo de conectores](https://github.com/wangkant/personagent/blob/main/docs/connectors.md): una solicitud HTTP firmada por mensaje, para escribir tu propio conector.
- [Herramientas](https://github.com/wangkant/personagent/blob/main/docs/tools.md): los scripts de `tools/`, para ejecutarlos desde un clon.
- [Registro de cambios](https://github.com/wangkant/personagent/blob/main/CHANGELOG.md), incluida la [actualización desde 0.4](https://github.com/wangkant/personagent/blob/main/CHANGELOG.md#upgrading-from-04).
- [Cómo contribuir](https://github.com/wangkant/personagent/blob/main/.github/CONTRIBUTING.md) · [Política de seguridad](https://github.com/wangkant/personagent/blob/main/.github/SECURITY.md) · [Aviso legal](https://github.com/wangkant/personagent/blob/main/docs/DISCLAIMER.md)

## Privacidad

Todo lo que personagent guarda se queda en tu máquina, en una sola carpeta principal: `.env` con tus claves, `persona.txt`, `runtime/` y `platforms/` con el AstrBot gestionado y las credenciales de las conexiones directas. El proveedor de modelos que elijas sí ve las conversaciones a las que responde, y una vez al día personagent consulta a pypi.org si hay una versión más nueva (`UPDATE_CHECK_ENABLED=false` lo desactiva). Antes de conectarlo con personas reales, diles que es un bot y obtén su consentimiento; la [guía](https://github.com/wangkant/personagent/blob/main/docs/guide.md#privacy-and-consent) detalla exactamente qué va a dónde.

## Estado

La versión 1.3.0 está en PyPI, publicada el 2026-10-18. QQ es la plataforma más probada, a través de AstrBot en la 1.0 y de forma directa desde la 1.1. Las conexiones de WeChat, Telegram y Discord comprueban las credenciales con los servicios reales antes de guardarlas y, por lo demás, se prueban con sustitutos; los conectores de Satori y Matrix se prueban con sustitutos. La CI ejecuta las pruebas en Linux con Python 3.10–3.14 y en Windows con Python 3.12, además de trabajos que instalan el paquete y ejercitan el comando y la página local.

## Licencia

[MIT](https://github.com/wangkant/personagent/blob/main/LICENSE) © 2026 Qiankang (Kant) Wang.

## Agradecimientos

- Las demás plataformas de chat se alcanzan a través de [AstrBot](https://github.com/AstrBotDevs/AstrBot), [NapCat](https://github.com/NapNeko/NapCatQQ), [Koishi](https://koishi.chat) con [satori-python](https://github.com/RF-Tar-Railt/satori-python), y [matrix-nio](https://github.com/matrix-nio/matrix-nio) con los [puentes de mautrix](https://docs.mau.fi/bridges/); la conexión con WeChat sigue las [notas del protocolo openclaw-weixin](https://github.com/Tencent/openclaw-weixin/blob/main/docs/protocol.md) de Tencent.
- El aprendizaje a partir de reacciones se basa en [Self-Feeding Chatbot](https://arxiv.org/abs/1901.05415), [Alexa self-learning](https://arxiv.org/abs/1911.02557) y [BlenderBot 3x](https://arxiv.org/abs/2306.04707); el lorebook sigue el World Info de [SillyTavern](https://github.com/SillyTavern/SillyTavern).
