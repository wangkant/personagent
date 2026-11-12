# Guía de usuario de personagent

[English](guide.md) · [简体中文](guide.zh-CN.md) · [繁體中文](guide.zh-TW.md) · [日本語](guide.ja.md) · [한국어](guide.ko.md) · Español · [Français](guide.fr.md) · [Deutsch](guide.de.md) · [Português (Brasil)](guide.pt-BR.md) · [Русский](guide.ru.md)

Esta guía describe cómo configurar personagent, incorporarlo a sus chats, enseñarle y mantenerlo. El [README](readme/README.es.md) es la versión breve, y [Primeros pasos](start.es.md) recorre la página local pantalla por pantalla.

1. [Instalación y carpeta de inicio](#instalación-y-carpeta-de-inicio)
2. [La página local](#la-página-local): [Ajustes avanzados](#ajustes-avanzados) · [La vista Aplicación](#la-vista-aplicación)
3. [Véalo primero: la demostración](#véalo-primero-la-demostración)
4. [Comandos de terminal](#comandos-de-terminal): [configuración](#configurar-en-el-terminal) · [conectar una plataforma](#conectar-una-plataforma-en-el-terminal) · [chat](#chatear-en-el-terminal) · [ejecutar el servicio](#ejecutar-el-servicio)
5. [Personalizar el personaje](#personalizar-el-personaje)
6. [Llevar el personaje a un chat](#llevar-el-personaje-a-un-chat): [Plataformas que personagent conecta por sí mismo](#plataformas-que-personagent-conecta-por-sí-mismo) · [Otras plataformas](#otras-plataformas-a-través-del-astrbot-gestionado) · [Puentes que ejecuta usted](#puentes-que-ejecuta-usted) · [Hablar primero](#hablar-primero)
7. [Asistentes de programación](#asistentes-de-programación)
8. [Enseñar al personaje](#enseñar-al-personaje)
9. [Memoria](#memoria)
10. [Actividad](#actividad)
11. [Medir el rendimiento](#medir-el-rendimiento)
12. [Cómo funciona](#cómo-funciona)
13. [Privacidad y consentimiento](#privacidad-y-consentimiento)
14. [Solución de problemas](#solución-de-problemas)
15. [Actualizar desde 0.x](#actualizar-desde-0x)
16. [Estado y otros documentos](#estado-y-otros-documentos)

## Instalación y carpeta de inicio

```sh
python -m pip install personagent
personagent
```

`personagent` abre [la página local](#la-página-local). También puede instalarlo o ejecutarlo de las siguientes formas:

| Vía | Comando |
|---|---|
| Ejecutar sin instalar | `uvx personagent` (forma parte de [uv](https://docs.astral.sh/uv/), que también descarga Python por usted) |
| Un comando `personagent` permanente | `uv tool install personagent` o `pipx install personagent` |
| Windows, desde el ZIP de código fuente | descomprímalo y haga doble clic en `start.bat` |
| Desde un clon | `git clone https://github.com/wangkant/personagent.git`, `cd personagent`, `python -m venv .venv`, luego `.venv/bin/python -m pip install -e .` y `.venv/bin/python -m persona_agent` (en Windows, `.venv\Scripts\python.exe`) |

personagent funciona con Python 3.10–3.14. `start.bat` crea `.venv`, instala las dependencias y abre la misma página; la primera vez, también coloca un icono de personagent en el escritorio y en el menú Inicio. Vuelve a instalar las dependencias cada vez que cambia la lista de dependencias de `pyproject.toml`.

La **carpeta de inicio** guarda los ajustes (`.env`), el personaje (`persona.txt`), lo que aprende (`runtime/`) y las plataformas de chat (`platforms/`). `platforms/` contiene el AstrBot gestionado y `direct.json`, que guarda las credenciales de las plataformas que personagent conecta por sí mismo. personagent utiliza la primera de estas carpetas:

1. la carpeta indicada con `--home DIR` o `AGENT_HOME`. `--home` puede ir antes o después del comando, como en `personagent chat --home D:\bot`.
2. el clon, si lo ejecuta desde uno.
3. la carpeta actual, si contiene tanto `.env` como `persona.txt`.
4. `~/personagent`, creada en la primera configuración.

Para ejecutar varios personajes desde una misma instalación, asigne a cada uno su propia carpeta de inicio.

Esta guía escribe los comandos como `personagent ...`. Si no lo ha instalado, anteponga `uvx`. En un clon, `.venv/bin/python -m persona_agent ...` tiene el mismo efecto (en Windows, `.venv\Scripts\python.exe -m persona_agent ...`).

## La página local

`personagent` (o `personagent start`) sirve una página a la que solo puede acceder este equipo. En Windows se abre en una ventana propia. En macOS y Linux se abre en el navegador, o también en una ventana una vez que `pip install "personagent[app]"` haya añadido [pywebview](https://pywebview.flowrl.com/), junto con Qt en Linux. La página tiene seis vistas, que aparecen en la barra lateral en este orden:

- **Chat** es un chat individual con el personaje en la página. Responde el mismo agente que atiende sus plataformas de chat. En este chat, usted es el administrador. Los stickers y las imágenes que envía el personaje aparecen en el chat, y una imagen que ya no está almacenada muestra en su lugar una breve nota. Los mensajes que el personaje envía después de su respuesta, como la respuesta a un comando de memoria enviado mientras respondía o un mensaje que inicia por su cuenta, aparecen en pocos segundos mientras la vista Chat está abierta. Ambos se conservan en el historial del chat. Cuando el modelo no responde, la página lo indica en lugar de una respuesta y ofrece **Volver a enviar**. **Comandos de memoria**, debajo del cuadro de mensaje, enumera los [comandos de memoria](#comandos-de-memoria), y al seleccionar uno se inserta en el cuadro de mensaje. **Olvidar este chat** olvida todo lo que el personaje recuerda de este chat e inicia un chat nuevo; se conserva lo que recuerda de otros chats, y este olvido no se puede deshacer. Requiere los datos en los que se basa [Actividad](#actividad).
- **Actividad** muestra los chats en los que participa el personaje, lo que ha dicho recientemente, lo que recuerda y lo que ha aprendido. Consulte [Actividad](#actividad).
- **Conectar plataformas** lleva el personaje a QQ, WeChat, Telegram, Discord y otras plataformas. Consulte [Llevar el personaje a un chat](#llevar-el-personaje-a-un-chat). En la parte inferior, **Asistentes de programación** conecta el personaje con los [asistentes de programación](#asistentes-de-programación) instalados en este equipo.
- **Personaje y ajustes** es donde se elige un servicio de modelos (OpenRouter, DeepSeek, SiliconFlow, Alibaba Bailian, Zhipu GLM, Moonshot, Volcengine Ark, OpenAI, Google Gemini, Ollama o cualquier otro servicio compatible con OpenAI), se pega la clave de API y se eligen un nombre y una personalidad predefinida. **Verificar e iniciar el chat** prueba la clave con una pequeña solicitud y solo la guarda si la solicitud se completa correctamente. Tras la configuración, el cuadro **Perfil** muestra `persona.txt`. **Guardar el perfil** reinicia el agente con el nuevo texto y conserva lo aprendido. **Más funciones** activa la búsqueda web con Tavily (DuckDuckGo es la opción gratuita predeterminada), la comprensión de imágenes y el inicio de conversaciones en las plataformas que elija. A continuación figuran los [Ajustes avanzados](#ajustes-avanzados).
- **Práctica** reproduce la demostración guionizada y ofrece un chat de grupo de práctica. Consulte [Véalo primero: la demostración](#véalo-primero-la-demostración).
- **Aplicación** comprueba los servicios de los que depende el personaje y reúne los registros, la ejecución en segundo plano, las actualizaciones y sus datos. Consulte [La vista Aplicación](#la-vista-aplicación).

**Práctica** y **Aplicación** pueden abrirse antes de configurar un modelo. Hasta que conecte una plataforma, la vista Chat muestra una breve barra de **Primeros pasos**.

Al volver a ejecutar `personagent`, se vuelve a mostrar la página que ya está abierta. `--browser` abre la página en el navegador en lugar de en una ventana, y `--no-browser` imprime el enlace y no abre nada. En Windows, `personagent shortcut` coloca en el escritorio y en el menú Inicio un icono que abre la ventana sin ningún terminal detrás, y `personagent shortcut --remove` lo quita. La vista **Aplicación** permite hacer lo mismo.

Cuando hay una versión más reciente de personagent en PyPI, la vista Chat muestra un aviso con el comando que actualiza su instalación, tanto si procede de pip, uvx, uv tool, pipx o un clon de Git. Para un ZIP de código fuente descomprimido, el aviso enlaza con la página de versiones. El terminal imprime el mismo comando. Al cerrar el aviso, este se oculta para esa versión, y **N disponible**, debajo del número de versión, lo vuelve a mostrar. `personagent up` y `personagent doctor` también informan de una versión nueva. La página y `up` consultan pypi.org como máximo una vez al día, en segundo plano. `doctor` realiza la consulta de inmediato si la última respuesta tiene más de un día. Defina `UPDATE_CHECK_ENABLED=false` para desactivar la comprobación. La vista **Aplicación** también puede instalar la actualización por sí misma; consulte [Versión y actualizaciones](#versión-y-actualizaciones).

La página inicia el agente y las plataformas conectadas en segundo plano, por lo que debe mantener su ventana abierta mientras los utilice. Todo lo que inició se detiene con ella, tanto si selecciona **Salir** como si pulsa Ctrl+C o cierra la ventana. Mientras haya una plataforma conectada, el cierre de la ventana solicita confirmación previa. En Windows, puede optar en su lugar por que personagent siga en ejecución al cerrar la ventana; consulte [Ejecución en segundo plano](#ejecución-en-segundo-plano). Si una ejecución anterior falló y dejó procesos, el siguiente inicio los detiene primero.

### Ajustes avanzados

Una vez configurado un modelo, **Personaje y ajustes** termina con **Ajustes avanzados**. Esta sección reúne, en seis apartados, ajustes que antes solo estaban disponibles en `.env`. Todos son opcionales y tienen un valor predeterminado; un campo vacío utiliza ese valor.

| Apartado | Ajustes |
|---|---|
| **Administrador y acceso** | Cómo le llama el personaje y qué relación tiene usted con él (`ADMIN_NAME`, `ADMIN_RELATIONSHIP`); **Sus cuentas** (`ADMIN_IDS`); **Responder solo en estos grupos** (`ACCESS_GROUPS`); **Otras personas autorizadas a enviar mensajes privados** (`ACCESS_DM_USERS`). **Elegir entre los chats recientes** enumera las personas y los grupos que aparecen en Actividad, para añadir sus ID sin tener que escribirlos. |
| **Intervenciones y estilo de respuesta** | **Zona horaria** (`PERSONA_TZ_OFFSET_HOURS`); **Mensajes antes de intervenir** (`CHAT_TRIGGER_COUNT`); **Frecuencia con la que inicia conversaciones**, que define a la vez los siete tiempos `PROACTIVE_*`; **Estilo de respuesta**: emojis, tres conjuntos de símbolos y la longitud máxima de las respuestas, que se guardan en `persona.card.json`. |
| **Modelos** | Un modelo de respaldo con su propia dirección de servicio y su propia clave (`LLM_FALLBACK_MODEL`, `LLM_FALLBACK_BASE_URL`, `LLM_FALLBACK_API_KEY`), el modelo para las decisiones rápidas (`LLM_JUDGE_MODEL`) y el modelo para los chats privados (`LLM_DM_MODEL`). El modelo de respaldo se prueba antes de guardarse. |
| **Aprendizaje** | `REACT_LEARN_ENABLED`, `REACT_ELICIT_ENABLED`, `PROMOTE_AUTO_ENABLED`, `PROMOTE_MIN_SPEAKERS` (1 o 2), `PROMOTE_JUDGE_ENABLED` (el personaje decide lo que las reacciones no pueden resolver) y `PROMOTE_OBSERVE_MAX_DAYS` (días sin ninguna reacción nueva antes de que un elemento en observación se aparte). **Reiniciar el aprendizaje** escribe un nuevo `PERSONA_VERSION`, de modo que lo que el personaje ha aprendido hasta ese momento deja de utilizarse. No se elimina nada. |
| **Memoria** | `MEMORY_CALLS_PER_DAY`, `MEMORY_TIDY_EVERY`, `CHAT_CONTEXT_MESSAGES`, `MEMORY_PROMPT_CHARS`, `MEMORY_EPISODES_MAX` y `MEMORY_KEEP_RECENT`. Consulte [Memoria](#memoria). |
| **Otros ajustes** | `AGENT_ENABLED`, `DASHBOARD_ENABLED`, `UPDATE_CHECK_ENABLED`, los siete tiempos `PROACTIVE_*`, `CHAT_FOLLOWUP_WINDOW_S`, los límites `REACT_*` y `PROMOTE_*`, `REACT_MODEL`, el modelo, el intervalo y el tamaño de lote de las decisiones del propio personaje (`PROMOTE_JUDGE_MODEL`, `PROMOTE_JUDGE_INTERVAL_S`, `PROMOTE_JUDGE_BATCH`) y `PERSONA_VERSION`. |

**Guardar** escribe únicamente los ajustes que han cambiado y deja el resto de `.env` tal como estaba. A continuación reinicia el personaje, salvo cuando el único cambio es `UPDATE_CHECK_ENABLED`. Desactivar las respuestas (`AGENT_ENABLED`) solicita confirmación previa. También la solicita cambiar el nombre del personaje en **Nombre del personaje**, porque un nombre nuevo da lugar a un personaje nuevo.

### La vista Aplicación

**Aplicación** muestra un punto rojo cuando algo requiere atención: un servicio no se ha podido iniciar, un ajuste tiene un nombre antiguo o un error, ha fallado la conexión con una plataforma o ha fallado la última comprobación.

**Comprobación de estado.** **Iniciar la comprobación** prueba todos los servicios de los que depende el personaje: el modelo de chat para las respuestas en grupos y en privado, la decisión de búsqueda web, la evaluación de reacciones, las decisiones de aprendizaje, la revisión de sus propias respuestas, la comprensión de imágenes, el modelo de autorrevisión, la búsqueda en la memoria, la búsqueda web, el puente de QQ (NapCat) y los registros de aprendizaje. Cada fila de modelo prueba el modelo que realiza ese trabajo. **Decisión de búsqueda web** prueba el modelo juez (`LLM_JUDGE_MODEL`; en su defecto, el modelo de respaldo; en defecto de este, el modelo principal) y falla cuando ese modelo no llama a la herramienta de búsqueda, porque en ese caso la búsqueda web nunca se ejecutaría. **Evaluación de reacciones** prueba `REACT_MODEL` o, en su defecto, el modelo juez, y se omite mientras `REACT_LEARN_ENABLED` está desactivado. **Decisiones de aprendizaje** prueba el modelo con el que el personaje decide lo que las reacciones no pueden resolver (`PROMOTE_JUDGE_MODEL` o, en su defecto, el modelo de la evaluación de reacciones) y se omite mientras `PROMOTE_JUDGE_ENABLED` o `PROMOTE_AUTO_ENABLED` está desactivado. **Revisión de sus propias respuestas** prueba `EVOLVE_MODEL` (en su defecto, `EVAL_MODEL`; después, el modelo de respaldo; por último, el modelo principal) y se omite mientras `EVOLVE_AUTO_ENABLED` está desactivado. Cuando una de estas dos filas probaría un modelo que ya prueba una fila anterior, no se vuelve a consultar ese modelo y la fila muestra el resultado de aquella. **Modelo de autoevaluación** se omite mientras `EVAL_ENABLED` está desactivado. Cada servicio ocupa una fila, marcada como **Funciona**, **No funciona** o **Sin configurar**, y un diagnóstico encima de las filas indica qué hay que corregir. Si el personaje está en ejecución, la comprobación se realiza a través de él. En caso contrario, una ejecución de prueba independiente realiza las mismas comprobaciones que `personagent doctor`. Cada comprobación envía unas pocas solicitudes breves y consume una pequeña parte de la cuota de su servicio de modelos. Un resultado de menos de un minuto de antigüedad se reutiliza mientras los ajustes no hayan cambiado. Esta misma parte de la vista muestra también:

- por qué no se pudo iniciar el personaje, AstrBot o la conexión con las plataformas, con la línea de registro correspondiente, **Mostrar el registro** y **Reiniciar**;
- **Ajustes con nombres antiguos**: ajustes cuyo nombre cambió en la versión 1.0. **Cambiar el nombre de los ajustes** hace lo mismo que `personagent doctor --fix`: solicita confirmación previa, conserva el archivo anterior como `.env.bak` y vuelve a iniciar el personaje si este se había negado a arrancar;
- **Conexiones con plataformas**: el estado de cada plataforma que personagent conecta por sí mismo y, si alguna ha fallado, el motivo;
- **Ajustes que conviene revisar**: problemas detectados en `.env`, como la falta de la clave del modelo, un ajuste que personagent no lee, un valor vacío o una marca de orden de bytes (BOM);
- **Registros**: las últimas líneas de cada registro de `runtime/desktop/` (el personaje, AstrBot, las conexiones con plataformas, las descargas y la instalación, la aplicación, Práctica y la última actualización). Las claves y los tokens reconocibles se ocultan, pero puede aparecer contenido de los chats. **Mostrar más líneas** muestra hasta 200 líneas, y **Abrir la carpeta de registros** abre la carpeta.

**Uso del modelo.** personagent contabiliza cada solicitud que realiza a un modelo, por modelo y por día, a partir del uso que comunica el servicio de modelos: las solicitudes, los tokens y el coste, cuando el servicio lo comunica, como hace OpenRouter. La vista **Aplicación** muestra el día de hoy y los últimos 7 días. `personagent doctor` imprime las mismas cifras, y `doctor --json` las añade como `model_use`. Los recuentos se conservan durante 8 días en `runtime/model_usage.json`. personagent escribe ese archivo en segundo plano, como máximo una vez por minuto y una vez más cuando se detiene, para que el recuento nunca retrase una respuesta.

#### Ejecución en segundo plano

Esta parte está disponible en la ventana de la aplicación en Windows. Con **Seguir en ejecución al cerrar la ventana** marcado, al cerrar la ventana personagent pasa a un icono del área de notificación, en la esquina inferior derecha de la pantalla, y el personaje sigue respondiendo. El menú del icono permite volver a abrir personagent o salir de él, y un doble clic en el icono lo abre. **Pasar a segundo plano ahora** oculta la ventana de inmediato. `personagent start --background` inicia personagent detrás del icono sin mostrar la ventana, siempre que esta opción esté marcada.

#### Versión y actualizaciones

Esta parte muestra la versión en ejecución y la fecha de la última comprobación. **Buscar actualizaciones** consulta pypi.org de inmediato, incluso si la comprobación diaria está desactivada. Cuando existe una versión más reciente, **Actualizar y volver a abrir** solicita confirmación, cierra personagent, ejecuta el comando de actualización correspondiente a esta instalación y vuelve a abrir personagent. El proceso tarda aproximadamente un minuto, durante el cual el personaje no responde. Un clon se actualiza con `git pull --ff-only` seguido de `pip install -e`. Si la actualización falla, se vuelve a abrir la versión anterior y **Mostrar el registro** muestra lo ocurrido. La aplicación no puede actualizarse por sí misma en cuatro casos, en los que muestra el comando o la página de versiones:

- una copia descomprimida del ZIP del código fuente, que debe sustituirse manualmente por el nuevo código;
- una copia que se ejecuta mediante uvx, que obtiene la nueva versión la próxima vez que se inicia con `uvx personagent@latest`;
- una instalación cuya herramienta (`git`, `uv` o `pipx`) no se encuentra;
- un clon con cambios locales.

#### Este equipo y sus datos

- **Icono en el escritorio y en el menú Inicio** (Windows): **Añadir el icono** y **Quitar el icono** hacen lo mismo que `personagent shortcut`. Una copia que se ejecuta mediante uvx no puede tener icono, porque se ejecuta desde una carpeta temporal.
- **Iniciar personagent al iniciar sesión en Windows** añade un acceso directo a la carpeta Inicio. Si personagent está configurado para ejecutarse en segundo plano, se inicia detrás de su icono sin abrir la ventana.
- **Sus datos** abre la carpeta de personagent, el archivo de perfil, los registros, la memoria y el contenido aprendido, la carpeta de stickers y la carpeta `data/` para su propio lorebook, sus ejemplos y sus filtros de salida.
- **Crear una copia de seguridad ahora** guarda un único archivo zip en el Escritorio, en Documentos o en la carpeta `backups` de la carpeta de inicio. Contiene los ajustes con sus claves de API, el perfil, la memoria y el contenido aprendido, los archivos del lorebook, los stickers y los inicios de sesión de las plataformas. No incluye los registros ni los componentes descargados. Mantenga este archivo en privado.
- **Restaurar desde una copia de seguridad** enumera las copias de seguridad de esas tres ubicaciones. **Restaurar** solicita confirmación, pone en pausa el personaje, guarda los datos actuales como copia de seguridad, los sustituye por los de la copia elegida y vacía el chat de esta página.
- **Borrar y restablecer** guarda primero una copia de seguridad en la carpeta `backups` y pone en pausa el personaje. **Borrar la memoria** elimina las notas del personaje sobre las personas, las respuestas que ha aprendido y su historial, los datos de Práctica y el chat de esta página; se conservan los ajustes, el perfil, las plataformas conectadas y los stickers. **Restablecer todo** devuelve personagent a su estado inicial: elimina los ajustes y las claves de API, el perfil, la memoria y el contenido aprendido, y desconecta todas las plataformas. Se conservan los stickers, la carpeta `data/` y el AstrBot descargado.

## Véalo primero: la demostración

`personagent demo` reproduce tres escenas con un modelo guionizado, por lo que no requiere clave. Las escenas muestran qué mensajes de grupo omite y por qué, cómo aprende de una corrección y cómo un desconocido no consigue introducir una instrucción. Para reproducir una sola escena, indique su nombre (`quiet`, `teach` o `troll`). Añada `--lang` y un código de idioma para utilizar otro idioma, como `--lang ja`.

A continuación se muestra una ejecución abreviada de `personagent demo teach`. Las frases del modelo están guionizadas, pero el registro y la regla de promoción corresponden al código real:

```text
  Alex: Nova, el despliegue ha vuelto a fallar
  Nova: ¿miraste los logs? primero revierte y luego compara las configs
  Alex: Nova, solo me estaba desahogando
      juicio: rechazo, aceptada: «Alex se estaba desahogando, no pedía una solución»
      registro: solo negativa (dice que la respuesta falló, no qué decir)
      la próxima respuesta de Nova a Alex cuenta como su segundo intento
  Nova: ya. vaya final de día
  Alex: jaja sí, gracias Nova
      juicio: positiva, aceptada: «Alex estuvo de acuerdo con el segundo intento y dio las gracias a Nova»
      registro: débil (una risa o un gracias nunca cambian nada por sí solos)
      registro: Alex aceptó el segundo intento: fuerte (Alex es a quien iba la respuesta)

  corrección: «¿miraste los logs? primero revierte y lue...» -> «ya. vaya final de día»
    [x] reacciones coincidentes: 2 de 2
    [x] reacciones fuertes: 1 de 1
    [x] mismo chat
    [x] 1 de 1 persona (PROMOTE_MIN_SPEAKERS)
    [x] nada en contra, ninguna corrección rival
    ya en uso: 2 reacciones a favor, fuertes: 1, mismo chat
```

La escena también envía el mismo mensaje antes y después de la lección: a alguien se le ha estropeado el portátil en mitad de una demostración. Antes de la corrección, Nova ofrece una solución. Después, muestra comprensión. La demostración sigue siendo guionizada aunque haya una clave definida, por lo que cada ejecución es idéntica y no tiene coste. `personagent demo --online` la reproduce con su propio modelo, lo que consume tokens y varía de una ejecución a otra.

La vista **Práctica** de la página local reproduce las mismas tres escenas. En **Demostración**, elija una escena y seleccione **Reproducir**. Cada paso muestra lo que dijeron las personas, lo que dijo el personaje, por qué guardó silencio o intervino, cómo se valoraron las reacciones y la lista de comprobación del aprendizaje.

**Grupo de práctica**, en la misma vista, es la versión de [`personagent chat`](#chatear-en-el-terminal) para la página y requiere un modelo. **Escribir como** determina quién envía el siguiente mensaje: usted como administrador o uno de tres miembros ficticios. **Mostrar el motivo**, en una línea, indica por qué el personaje respondió o guardó silencio, qué aprendió y qué aprendizaje anterior utilizó. **Responder** cita una de las líneas del personaje, de modo que el siguiente mensaje cuenta como una reacción a ella. **Mostrar lo aprendido** enumera lo que ha aprendido en este grupo. El grupo de práctica guarda su estado en `runtime/trial/`, la misma carpeta que `personagent chat`, y no afecta a sus chats reales. **Restablecer el grupo de práctica** elimina ese estado.

## Comandos de terminal

Todo lo que hace la página también está disponible desde un terminal, lo que resulta útil para servidores y scripts.

| Comando | Qué hace |
|---|---|
| `personagent start` | abre la página local (`--terminal` para un menú en el terminal) |
| `personagent init` | configura una carpeta de inicio; `--terminal` formula las preguntas en el terminal, `--no-input` acepta opciones |
| `personagent chat` | un chat de grupo simulado en el terminal |
| `personagent demo` | la demostración guionizada descrita arriba |
| `personagent run` | solo el servicio, para conectores que ejecute usted |
| `personagent up` | el servicio, las plataformas que personagent conecta por sí mismo y el AstrBot gestionado, todo junto |
| `personagent connect <plataforma>` | conecta una de las [plataformas que personagent conecta por sí mismo](#conectar-una-plataforma-en-el-terminal) (`--remove` para desconectarla); sin plataforma, las enumera |
| `personagent connect astrbot` | conecta un AstrBot (`--install` para descargar uno gestionado, `--start` para iniciarlo) |
| `personagent connect claude-code`, `personagent connect codex`, `personagent connect dsh` | lleva el personaje a un [asistente de programación](#asistentes-de-programación) (`--react` para comentarios al terminar un turno en los dos primeros, `--remove` para deshacerlo) |
| `personagent mcp` | el servidor MCP que inicia un asistente de programación; no debe ejecutarlo usted |
| `personagent doctor` | comprueba la configuración y todos los servicios de los que depende |
| `personagent learned` | muestra lo aprendido y lo que todavía observa, y permite intervenir si lo desea |
| `personagent memory` | enumera lo que recuerda, olvida un elemento o recupera uno |
| `personagent eval` | mide el habla, el perfil, el aprendizaje y la memoria |

Todos los comandos aceptan `--help`.

### Configurar en el terminal

`personagent init --terminal` formula las mismas preguntas que la página, en el idioma que elija en primer lugar, y explica cada término en una línea:

- **El servicio de IA.** Los preajustes coinciden con los de la página. El predeterminado es `openrouter/free` de OpenRouter, que asigna cada solicitud a uno de sus modelos gratuitos. La clave no tiene coste. El límite es de 20 solicitudes por minuto y 50 al día, o 1000 al día si ha adquirido al menos 10 créditos. Se contabiliza toda llamada al modelo, no solo las respuestas, y el contador diario se restablece a medianoche (UTC). Cuando se agota, el personaje indica que no puede responder en ese momento, y `runtime/desktop/agent.log` recoge el motivo indicado por OpenRouter. El modelo varía entre solicitudes, por lo que la voz del personaje es menos constante que con un modelo fijo, y algunos proveedores gratuitos conservan lo que reciben. Para obtener un personaje más estable, utilice un modelo de pago con la misma clave. Si tiene dificultades para acceder a OpenRouter desde su ubicación, `glm-4.7-flash` de Zhipu también es gratuito. Para Ollama, indique un modelo que ya haya descargado. Ollama no requiere clave.
- **La clave.** La entrada está oculta de forma predeterminada. Puede optar por mostrarla, lo que también revela la clave guardada al volver a configurar. El asistente prueba la clave con una pequeña solicitud. Si falla, muestra la dirección a la que llamó, el estado HTTP y una posible solución.
- **El personaje.** Un nombre y uno de siete personajes predefinidos (amigo de humor seco, oyente cercano, jugador, amante de los libros y tres que la comunidad ya dibuja: la chica ballena de DeepSeek, la chica dragón de GPT y la dama Claude), o uno básico para que lo redacte usted. Si elige uno de los tres últimos sin indicar un nombre, el personaje adopta el nombre de ese personaje. La página local muestra su retrato animado.
- **Plataformas de chat.** Es opcional y este paso puede omitirse la primera vez. La configuración enumera las diez plataformas que personagent conecta por sí mismo, que se conectan después con [`personagent connect <plataforma>`](#conectar-una-plataforma-en-el-terminal). Para las demás plataformas, puede conectar AstrBot y, previamente, descargarlo e instalarlo. Consulte [Puentes que ejecuta usted](#puentes-que-ejecuta-usted).

Para configurar sin preguntas, por ejemplo en un script, ejecute `personagent init --no-input` con `--provider`, `--model`, `--key-env VAR`, `--name`, `--lang` y `--persona`. En una carpeta de inicio nueva, una clave procedente de `--key-env` o del `LLM_API_KEY` del shell requiere `--provider` o `--base-url` para indicar a qué servicio pertenece. `--provider other` también requiere `--base-url`. `personagent init --help` enumera todas las opciones. Si `personagent init` se ejecuta sin terminal y sin ninguna de estas opciones, omite las preguntas, lo indica y finaliza con el código 2.

### Conectar una plataforma en el terminal

`personagent connect <plataforma>` conecta una de las [plataformas que personagent conecta por sí mismo](#plataformas-que-personagent-conecta-por-sí-mismo) sin la página. La plataforma es `qq`, `wechat`, `telegram`, `discord`, `matrix`, `twitch`, `irc`, `zulip`, `vk` o `stoat`. El comando muestra los mismos pasos que **Conectar plataformas**, solicita cada valor, comprueba los valores con la plataforma y los guarda en el mismo formato que la página, que a continuación muestra la plataforma como conectada. Si la plataforma rechaza los valores, el comando indica el motivo y no guarda nada. `personagent connect` sin plataforma enumera las diez plataformas e indica si cada una está conectada.

- QQ y WeChat muestran un código QR en el terminal, que debe escanear con su teléfono. En QQ, también puede introducir el AppID y el AppSecret de un bot que haya creado. Si no es posible escanear el código en su terminal, conecte la plataforma en la ventana de personagent; el comando indica cómo abrirla.
- Twitch muestra un enlace y un código. Abra el enlace en un navegador con la sesión iniciada en la cuenta de Twitch del personaje, compruebe que la página muestra el mismo código y apruebe el inicio de sesión. El comando espera hasta que se apruebe el inicio de sesión.
- Cada valor también puede indicarse como opción, como `--telegram-token` o `--irc-server`, y `personagent connect --help` las enumera todas. Un valor indicado como opción puede quedar en el historial del shell. Con `--no-input`, el comando no formula ninguna pregunta; si falta un valor obligatorio, indica la opción correspondiente y finaliza con el código 2.
- `--remove` desconecta la plataforma y elimina los valores guardados.

La conexión está activa mientras personagent se ejecuta. `personagent up` inicia personagent con las plataformas conectadas; si personagent ya está en ejecución, reinícielo. En el menú de `personagent start --terminal`, la opción 3 conecta estas plataformas y la opción 5 inicia personagent con ellas.

### Chatear en el terminal

`personagent chat` abre un chat de grupo simulado con el personaje. Una línea normal es una conversación de grupo corriente, y la prueba le indica si el personaje intervendría y por qué. Una línea que contiene su nombre se dirige a él:

```text
Alex> ¿hay alguien por aquí esta noche?
  (Nova guarda silencio: nadie se dirige a él, 1 de 4 mensajes)

Alex> Nova, el despliegue ha vuelto a fallar
  Nova > ¿miraste los logs? primero revierte y luego compara las configs
```

| Escriba | Para |
|---|---|
| `/reply <text>` | citar su última respuesta, lo que cuenta como una reacción de la que puede aprender |
| `/as Sam <text>` | hablar como otra persona: `/as Sam Nova, you free tonight?` |
| `/admin <text>` | hablar una vez como administrador: `/admin Nova, how was your day?` |
| `/why` | ver por qué dio su última respuesta y qué recoge el registro sobre ella |
| `/learned` | ver lo que ha aprendido en este chat |
| `/reset` | borrar el chat y lo aprendido en la prueba |
| `/quit` | salir |

Las líneas `/as` y `/admin` también siguen las reglas de grupo, por lo que debe incluir el nombre para obtener una respuesta. Una línea de menos de cuatro caracteres que no mencione al personaje no cuenta para la intervención. Los [comandos de memoria](#comandos-de-memoria) también funcionan aquí.

| Opción | Qué hace |
|---|---|
| `--name Alex` | define su nombre |
| `--admin` | atribuye todas las líneas al administrador |
| `--dm` | lo convierte en un chat individual |
| `--lang <code>` | sustituye `AGENT_LANG`, como `--lang ja` |
| `--trigger N` | mensajes antes de plantearse intervenir (4 de forma predeterminada) |

La prueba ejecuta la decisión real de hablar o guardar silencio, las comprobaciones de salida, los comandos de memoria y el aprendizaje. Se plantea intervenir tras 4 mensajes, mientras que el bot en producción espera 30. Lo que aprende se guarda en `runtime/trial/` de la carpeta de inicio, separado del bot en producción. `personagent learned` no lo muestra, y `/reset` lo borra. La prueba omite las listas de permitidos y la entrega real. También desactiva la autoevaluación, la visión, la pregunta de seguimiento y los mensajes que el personaje iniciaría por su cuenta. Cuando falla una llamada al modelo, imprime una línea que indica qué revisar:

```text
Alex> Nova, ¿estás ahí?
  [error: el proveedor del modelo rechazó la clave o la cuenta (HTTP 401); compruebe LLM_API_KEY y, a continuación, ejecute `personagent doctor`]
```

### Ejecutar el servicio

`personagent run` inicia únicamente el servicio con el que se comunican los conectores, en `http://127.0.0.1:8080`. Al iniciarse, imprime la versión, la dirección, la carpeta de inicio y si el agente está activo. `--host` y `--port` sustituyen `SERVER_HOST` y `SERVER_PORT`. Utilice este comando cuando ejecute usted mismo el conector.

`personagent up` inicia el servicio junto con todas las plataformas que haya conectado desde la página, con `personagent connect <plataforma>` o con `connect astrbot --install`. No abre el navegador. Ctrl+C lo detiene todo, y cada proceso escribe su registro en `runtime/desktop/` de la carpeta de inicio.

## Personalizar el personaje

`persona.txt`, en la carpeta de inicio, define al personaje. Edítelo en el cuadro **Perfil** de la página, o en cualquier editor y, a continuación, reinicie. Describa quién es el personaje, cómo suele hablar y qué hace en las situaciones que le interesan. Los hábitos concretos funcionan mejor que pedir al modelo que «suene natural»:

```text
Your name is Nova. You chat with friends about films and cooking.
You speak directly and make the occasional joke.

Usually reply in a sentence or two. Explain more when someone asks a serious question.
When a friend vents, listen before offering advice.
If you have not seen a film, say so instead of inventing an opinion.
```

`AGENT_LANG` admite uno de los valores `en`, `zh`, `zh-TW`, `ja`, `ko`, `es`, `fr`, `de`, `pt-BR` y `ru`. Determina el perfil inicial, la configuración en el terminal, la prueba y la demostración, `--help` y `doctor`, los comandos de memoria y las respuestas fijas. Los ejemplos, filtros y comprobaciones incluidos están en chino para `zh` y `zh-TW` y en inglés para los demás. No traduce su perfil. [.env.example](../.env.example) describe todos los ajustes.

El menú de idioma, en la parte superior derecha de la página local, ofrece English, 简体中文, 繁體中文, 日本語, 한국어, Español, Français, Deutsch, Português (Brasil) y Русский. Solo cambia cómo se muestra la página, y el navegador lo recuerda. El idioma del propio personaje se elige en **Idioma del personaje**, dentro de **Elegir un nombre, una personalidad o un idioma** en **Personaje y ajustes**, y se guarda como `AGENT_LANG`. El personaje responde en el idioma que se utiliza en el chat. Sus prompts están en inglés y en chino. Los [comandos de memoria](#comandos-de-memoria) y las pocas respuestas fijas, que no pasan por el modelo, funcionan en los diez idiomas.

Para sustituir un archivo incluido, coloque un archivo con el mismo nombre en `data/` de la carpeta de inicio. Los archivos que no sustituya proceden de la copia incluida con personagent.

| Archivo | Contiene |
|---|---|
| `data/examples.<lang>.jsonl` | Intercambios de ejemplo que el modelo puede imitar |
| `data/feedback.<lang>.jsonl` | Respuestas emparejadas con versiones mejoradas |
| `data/lorebook.<lang>.json` | Notas de contexto que se añaden cuando aparece una palabra clave |
| `data/output_filter.<lang>.json` | Reglas de sustitución y rechazo para las respuestas en producción |
| `persona.card.json` | Apodos opcionales y ajustes de emojis, conjunto de caracteres y longitud, como `{ "aliases": ["Lu"], "reply_style": { "emoji": true, "max_chars": 320 } }`. Un apodo en `aliases` llama al personaje igual que su nombre. Los nombres se comparan sin distinguir mayúsculas y minúsculas, caracteres de ancho completo ni acentos, de modo que `sofia` llama a Sofía. En un mensaje, ñ, ã, õ y й cuentan como letras propias, de modo que `niña` no llama a un personaje llamado Nina; en el nombre del propio personaje esa marca puede omitirse, de modo que `nina` llama a Niña. Un nombre no llama al personaje desde dentro de una palabra más larga: un nombre en katakana dentro de una palabra más larga en katakana no lo llama, ni tampoco un nombre coreano en medio de una palabra. Con `"emoji": true`, el personaje puede usar emojis como suele hacerlo, y un `max_chars` inferior a 800 se comunica al modelo como límite de longitud |

Para que pueda ver imágenes, defina `VISION_MODEL`, `VISION_API_KEY` y `VISION_BASE_URL`, o active la comprensión de imágenes en **Más funciones**. Si el modelo elegido no puede leer imágenes, la página lo indica al guardar. Una imagen que el personaje no puede ver, porque la comprensión de imágenes está desactivada o ha fallado, le llega como una imagen que no puede ver, tanto en grupos como en chats privados, de modo que pregunta por ella en lugar de describirla. Los mensajes de voz, los vídeos, los archivos y los mensajes reenviados le llegan como lo que son, con la transcripción del mensaje de voz cuando la plataforma la proporciona. Las palabras de un mensaje reenviado se leen como palabras de la persona cuyo mensaje se reenvió: no llaman a nadie por su nombre ni ejecutan ningún comando de memoria. Una mención de otra persona llega al personaje con el nombre que esa persona eligió, que nunca cuenta como palabras del remitente, por lo que no llama al personaje ni da ninguna orden.

## Llevar el personaje a un chat

Abra **Conectar plataformas** en la página local y elija una plataforma. La página solo solicita los valores que se copian de la consola de la propia plataforma. Los comprueba con la plataforma, inicia la conexión y espera unos segundos para confirmar que la plataforma la ha aceptado. Si la plataforma la rechaza, la página lo indica y no guarda nada. Las plataformas conectadas aparecen en la parte superior, donde puede volver a configurar una o desconectarla. Se inician de nuevo cada vez que se inicia la página o `personagent up`. En un equipo sin pantalla, `personagent connect <plataforma>` conecta desde el terminal las plataformas que personagent conecta por sí mismo; consulte [Conectar una plataforma en el terminal](#conectar-una-plataforma-en-el-terminal).

```text
Chat platform  ⇄  connector  ⇄  personagent  ⇄  Model API
```

Un conector inicia sesión en la plataforma, transmite cada mensaje a personagent y devuelve la respuesta. Hay tres tipos.

### Plataformas que personagent conecta por sí mismo

personagent conecta estas diez plataformas por sí mismo, en un único proceso en segundo plano. No requieren AstrBot ni NapCat. Si una de ellas no puede cargarse, las demás se inician igualmente. En estas plataformas las respuestas salen de mensaje en mensaje, cada uno tras el tiempo aproximado que se tarda en escribirlo; Telegram, Discord y Matrix muestran entretanto el indicador de escritura.

| Plataforma | Qué debe hacer |
|---|---|
| QQ | Escanee el código con QQ para móvil y confirme. Esto crea un bot oficial de QQ o utiliza uno que ya tenga, y personagent obtiene sus claves. **Pegar los valores en su lugar** acepta el AppID y el AppSecret de un bot creado en la [página de bots de QQ](https://q.qq.com/qqbot/openclaw/login.html). |
| WeChat (personal) | Escanee el código con WeChat y confirme el inicio de sesión. La conexión utiliza la API de bots iLink de Tencent y solo gestiona chats individuales, porque WeChat no entrega mensajes de grupo a estos bots. |
| Telegram | Cree un bot con [@BotFather](https://t.me/BotFather) y pegue su token. |
| Discord | En el [Developer Portal](https://discord.com/developers/applications), copie el token del bot y active Message Content Intent. |
| Matrix | Cree una cuenta de Matrix independiente para el bot. En Element, con la sesión del bot iniciada, copie su token de acceso en **Todos los ajustes > Ayuda y acerca de > Avanzado** y cierre esa ventana sin cerrar la sesión. Pegue el token junto con la dirección del servidor doméstico (homeserver) y su propio ID de Matrix. A continuación, desde su propia cuenta, invite al bot a una sala con el cifrado de extremo a extremo desactivado. El bot solo acepta invitaciones de su ID de Matrix y no puede leer salas cifradas. |
| Twitch | Registre una aplicación gratuita con Client Type **Public** en la [consola de desarrolladores de Twitch](https://dev.twitch.tv/console). Pegue su Client ID y los canales en los que debe chatear el personaje, seleccione **Conectar** y apruebe el inicio de sesión mediante el enlace que muestra la página, en un navegador con la sesión iniciada en la cuenta de Twitch del personaje. El personaje chatea solo por texto y solo en los canales indicados. personagent no admite los susurros (mensajes directos) de Twitch, por lo que la tarjeta de Twitch en **Conectar plataformas** indica **Solo canales**. |
| IRC | Introduzca el servidor (Libera.Chat de forma predeterminada, o `irc.oftc.net` para OFTC), el puerto TLS, el apodo del bot, los canales y, si el apodo está registrado, la contraseña de NickServ. El bot se conecta mediante TLS, se une únicamente a los canales indicados y responde a los mensajes directos dirigidos a su apodo. Solo texto. Libera.Chat exige el permiso de los operadores de cada canal antes de que se una un bot de IA. |
| Zulip | Añada un **Generic bot** en **Ajustes personales > Bots** y, a continuación, pegue la dirección de la organización, el correo electrónico del bot y su clave de API. El bot solo lee los canales a los que está suscrito y los mensajes directos que se le envían. En un canal responde cuando se le menciona o se le cita. Cualquier miembro de la organización puede enviarle mensajes directos. |
| VK | En los ajustes de la comunidad, active los mensajes y las funciones de bot, cree una clave de acceso con permisos de gestión de la comunidad, mensajes y fotos, y active la Long Poll API con el evento `message_new`. Pegue la clave. Cualquier usuario de VK puede escribir a la comunidad. En un chat de grupo, el bot solo recibe los mensajes que lo mencionan o le responden, salvo que el chat le dé acceso a todos los mensajes. |
| Stoat (antes Revolt) | Cree un bot en **Ajustes > My Bots** y pegue su token. Cambie la dirección de la API solo si se trata de un servidor autoalojado. El bot responde a todos los mensajes directos. En servidores y grupos solo responde donde usted también es miembro, y únicamente cuando alguien lo menciona, le responde o empieza un mensaje con su nombre. |

Para las seis últimas, la página muestra pasos numerados encima de los campos. El proyecto todavía no ha probado Matrix, Twitch, IRC, Zulip, VK ni Stoat con los servicios reales; su integración sigue la documentación de cada plataforma.

En QQ, busque el bot en QQ para móvil, en Contactos → Bots, y, a continuación, chatee con él en privado o añádalo a un grupo. Hasta que el bot esté certificado, QQ solo le permite unirse a grupos de los que usted sea propietario. Los mensajes de grupo que recibe se eligen en QQ, en el perfil del bot en ese grupo. La [guía de bots de QQ](https://bot.q.qq.com/wiki/bot_new_product-intro/) describe la certificación.

Las credenciales se guardan en `platforms/direct.json` de la carpeta de inicio.

### Otras plataformas, a través del AstrBot gestionado

La primera vez que conecte cualquier otra plataforma, personagent descargará [AstrBot](https://docs.astrbot.app) y un entorno dedicado de Python 3.12 en `platforms/` de la carpeta de inicio. Mantenga la página abierta durante la descarga. A continuación, AstrBot se ejecuta en segundo plano, sin panel y sin un segundo inicio de sesión. No requiere un `uv` global y no modifica el Python de personagent. Al conectar una plataforma desde la página, los grupos y los mensajes directos de esa plataforma pueden llegar al personaje. Las listas de permitidos de las demás plataformas se mantienen sin cambios.

| Grupo | Plataformas | Datos necesarios |
|---|---|---|
| Pegar uno o dos valores | KOOK, Feishu / Lark, DingTalk, Slack, bot de IA de WeCom, Mattermost, Misskey | un token, un ID de aplicación y un secreto, o una dirección de servidor y un token. Feishu utiliza una conexión persistente y DingTalk el modo Stream, por lo que ninguno requiere una dirección pública. En Slack, el enlace de la página crea la aplicación con Socket Mode, los ámbitos y los eventos ya definidos. Añada un token de nivel de aplicación con `connections:write`, instale la aplicación y pegue ambos tokens. Cree el bot de IA de WeCom con conexión persistente. |
| Avanzado | App de WeCom, cuenta oficial de WeChat, QQ (webhook) | una dirección pública que reenvíe al puerto de callback indicado |
| Avanzado | OneBot v11 (NapCat), Satori | otro software en ejecución en este equipo: NapCat apuntando a `ws://127.0.0.1:<port>/ws`, o un servidor Satori |

LINE no está disponible, porque AstrBot solo recibe los callbacks de LINE a través de su panel.

Desde un terminal, `personagent connect astrbot --install` descarga el mismo AstrBot gestionado y lo conecta. Añada `--platform telegram --token <bot token>` para activar una plataforma cada vez. No se permite ningún grupo ni mensaje directo hasta que los configure. Si la descarga falla, vuelva a ejecutar el mismo comando. La configuración existente se conserva. `personagent connect astrbot --start` inicia el AstrBot gestionado, y `personagent up` lo inicia junto con todo lo demás.

### Puentes que ejecuta usted

Los proyectos siguientes son software de terceros con el que personagent funciona. No necesita ninguno de ellos para las [plataformas que personagent conecta por sí mismo](#plataformas-que-personagent-conecta-por-sí-mismo).

| Puente | Alcance |
|---|---|
| Un [AstrBot](https://docs.astrbot.app) que ya ejecute | sus plataformas |
| [NapCat](https://github.com/NapNeko/NapCatQQ) (OneBot v11), a través de AstrBot | QQ con una cuenta personal de QQ |
| [Koishi](https://koishi.chat) u otro servidor Satori, a través del [conector de Satori](../integrations/satori/README.es.md) | las plataformas en las que ese servidor haya iniciado sesión |
| [Matrix](../integrations/matrix/README.es.md), a través de puentes mautrix | salas de Matrix, y WhatsApp, Signal, Messenger, Instagram y Google Messages |

Cualquier otro servicio puede conectarse mediante el [protocolo de conectores](connectors.es.md), que recibe una solicitud HTTP firmada por cada mensaje. Varios conectores pueden atender a un mismo personagent a la vez. La [guía de despliegue](deploy.es.md) describe su uso en producción.

**Un AstrBot que ya ejecute.** AstrBot entrega los mensajes a personagent mediante un pequeño complemento, [astrbot_plugin_personagent](../integrations/astrbot/astrbot_plugin_personagent/README.es.md). El complemento se incluye con personagent, y el AstrBot gestionado lo recibe automáticamente. `personagent connect astrbot` localiza su AstrBot o recibe su carpeta como argumento. Instala el complemento, escribe un `CONNECTOR_TOKEN` compartido en ambos lados y pregunta qué grupos se deben permitir. Envíe `/sid` en un grupo para ver su ID. En la página local, **Usar un AstrBot existente**, dentro de **Asistentes de programación**, en la parte inferior de **Conectar plataformas**, hace lo mismo: localiza la carpeta de AstrBot, instala o actualiza el complemento y guarda los ID de grupos y de mensajes directos en **A quién responde**. Para un AstrBot en Docker o en otro equipo, admite la dirección HTTPS que se describe a continuación. **Desconectar** vuelve a eliminar el complemento y su configuración.

Para un AstrBot en otro equipo:

1. Descargue `astrbot_plugin_personagent.zip` de la [última versión](https://github.com/wangkant/personagent/releases/latest).
2. Súbalo en **Install from File**, en la página de complementos de AstrBot.
3. Defina el valor `connector_token` del complemento con el `CONNECTOR_TOKEN` del `.env` de personagent.
4. Defina su `personagent_url` con una dirección HTTPS de personagent. Consulte **AstrBot en Docker o en otro host** más abajo.
5. Ejecute `personagent run` y, a continuación, reinicie AstrBot o vuelva a cargar sus complementos.

Después de actualizar personagent, vuelva a ejecutar `connect astrbot` o suba el nuevo zip. AstrBot 4.29 y las versiones posteriores sustituyen la copia instalada. En versiones anteriores, desinstale primero la copia antigua y deje **Also delete plugin configuration file** sin marcar para conservar sus ajustes.

El complemento reenvía un grupo solo si figura en su lista `groups`, y los mensajes directos solo de los usuarios que figuran en `dm_users`. Puede cambiar ambas listas en la WebUI de AstrBot. Reinicie personagent después de editar `.env`, y reinicie AstrBot después de cambiar una plataforma o el complemento.

Si indica la carpeta de AstrBot, `connect astrbot` no formula ninguna pregunta, y puede activar una plataforma con su token:

```bash
personagent connect astrbot <AstrBot data dir> --platform telegram --token <bot token>
```

`--platform` acepta `telegram`, `discord`, `slack`, `kook`, `lark` y `qq_official`. Slack también acepta `--app-token`, y Lark y QQ aceptan `--app-id` y `--app-secret`. En un adaptador ya configurado en AstrBot, el comando cambia únicamente las credenciales y conserva todo lo demás, como un proxy o una URL base. `personagent connect --help` enumera las opciones restantes.

**QQ a través de NapCat.** Esta vía utiliza una cuenta personal de QQ en lugar de un bot oficial. NapCat inicia sesión con la cuenta y se conecta al adaptador `aiocqhttp` (OneBot v11) de AstrBot, con su WebSocket inverso en `ws://127.0.0.1:6199/ws`. Elegir QQ en `personagent connect astrbot`, o pasar `--qq` con una carpeta, quita `aiocqhttp` de `excluded_platforms` del complemento y define `CONNECTOR_QQ_PLATFORMS=aiocqhttp`. De este modo, los chats de QQ conservan las mismas identidades y la misma memoria. El servidor HTTP de NapCat (`QQ_ONEBOT_URL`) es opcional. Si se definen este y `QQ_BOT_ID`, personagent recupera las menciones perdidas mientras estaba desconectado. La [guía paso a paso en chino](deploy.zh-CN.md#第三方路线astrbot--napcat) incluye una sección breve sobre esta vía. Los clientes de QQ de terceros ponen en riesgo la cuenta, por lo que debe leer primero el [aviso legal](DISCLAIMER.es.md).

La vía directa de OneBot (`/v1/onebot`) está obsoleta y se mantiene durante la serie 1.x. Envía las respuestas a través de `QQ_ONEBOT_URL`, por lo que debe definirlo si todavía utiliza esta vía. `personagent doctor` emite una advertencia cuando la vía parece configurada sin él. No la ejecute nunca junto con el reenvío de AstrBot, ya que cada mensaje llegaría dos veces.

**AstrBot en Docker o en otro host.** El complemento solo envía al mismo host (o a un contenedor que comparta su red), o a una dirección HTTPS con `connector_token` definido. Rechaza `http://` sin cifrar en cualquier otro caso, como `http://host.docker.internal:8080`, registra `refusing unsafe personagent_url` y deja que responda el propio modelo de AstrBot. Hay dos soluciones:

- Asigne al contenedor de AstrBot la red del host: `network_mode: host` en su archivo compose, o `docker run --network host`. En Docker Desktop 4.34 o posterior, active también «Enable host networking».
- Asigne a personagent una dirección HTTPS y defínala como `personagent_url` del complemento. `connect astrbot --url https://...` la escribe por usted.

Un contenedor de NapCat en el mismo archivo compose también requiere la red del host.

personagent escucha en `127.0.0.1:8080`, y un `SERVER_HOST` vacío tiene el mismo efecto. Escuchar en una dirección de red (`--host 0.0.0.0` o `SERVER_HOST`) exige `CONNECTOR_TOKEN`. Defina el token antes de añadir un proxy o un túnel, incluso en un único equipo, porque un túnel puede hacer que las solicitudes externas parezcan locales. [Exponer los endpoints](deploy.es.md#exponer-los-endpoints) describe el resto.

### Hablar primero

Algunos mensajes no responden a nadie. Son los mensajes de apertura (`PROACTIVE_ENABLED`, desactivado de forma predeterminada), la pregunta de seguimiento tras un rechazo y la disculpa que se envía cuando el modelo falla en un grupo. En un mensaje directo, la disculpa se devuelve en la respuesta al mensaje en espera. personagent coloca estos mensajes en una bandeja de salida, y los conectores los recogen y los envían en las plataformas que permiten que un bot hable primero. La página local los recoge de la misma forma para su propia vista Chat. Las cuentas oficiales de WeChat y los bots inteligentes de WeCom no lo permiten. QQ limita la frecuencia de los mensajes no solicitados de un bot oficial, y los usuarios pueden desactivarlos. `PROACTIVE_PLATFORMS=qq_official` limita las aperturas al bot oficial de QQ, y `qq` a QQ a través de NapCat. En la página, **Iniciar conversaciones ocasionalmente**, en **Más funciones**, escribe ambos ajustes. Consulte la [guía de despliegue](deploy.es.md#más-de-una-plataforma).

## Asistentes de programación

Codex, Claude Code y DeepSeek Harness (`dsh`) acceden al personaje mediante MCP. Con una clave de modelo guardada, ejecute uno o varios de estos comandos:

```bash
personagent connect claude-code
personagent connect codex
personagent connect dsh
```

El primero llama a `claude mcp add` con ámbito de usuario. El segundo escribe en `config.toml`, en la carpeta de Codex (`CODEX_HOME` o `~/.codex`). El tercero añade una entrada a `cordis.patch.yml` en cada perfil de `DSH_HOME` o `~/.dsh`. Cada forma de ejecutar DeepSeek Harness, como la aplicación de escritorio o `dsh web`, obtiene su perfil la primera vez que se inicia, por lo que debe iniciarlo una vez antes de conectar y reiniciarlo después. Los tres hacen referencia a esta instalación y a esta carpeta de inicio, por lo que debe volver a ejecutar el comando si mueve cualquiera de ellas, con `--react` si lo utilizó: una ejecución sin esta opción quita el hook. Abra una sesión nueva y pida al asistente de programación que diga algo a su personaje.

**Desde la página local.** **Asistentes de programación**, en la parte inferior de **Conectar plataformas**, localiza Claude Code, Codex y DeepSeek Harness en este equipo e indica si cada uno está conectado. **Conectar** (o **Reparar** y **Actualizar** si ya existe una configuración) y **Quitar** hacen lo mismo que los comandos anteriores y `--remove`, y solicitan confirmación previa. Al volver a conectar se conserva el ajuste de comentarios tal como estaba. En Claude Code y Codex, **Hacer un comentario al final de cada turno** activa o desactiva el hook `--react`, e **Intervalo mínimo entre comentarios** establece `CODING_REACT_COOLDOWN_S` en 10 minutos, 30 minutos, 1 hora o 2 horas. **Volver a comprobar** lee de nuevo el estado, por ejemplo después de instalar alguno de ellos.

Dispone de dos herramientas:

| Herramienta | Qué hace | Coste |
|---|---|---|
| `talk` | un mensaje en el mismo chat individual que la página local, con la misma memoria. Lo que se dice mediante `talk` aparece en Chat de la página, marcado como **a través de un asistente de programación**: en pocos segundos mientras la vista Chat está abierta y, en caso contrario, la próxima vez que se abre la página. Los comandos de memoria como `Nova, what do you remember?` también funcionan aquí. | una respuesta de su servicio de modelos, salvo en el caso de los comandos de memoria |
| `character` | lee el nombre y `persona.txt` | ninguno |

Claude Code y Codex solicitan permiso antes del primer `talk`, y en ese aviso puede permitirlo de forma permanente. `dsh headless` no lo solicita. Una ejecución sin nadie que responda requiere el permiso por adelantado: `claude -p` acepta `--allowedTools mcp__personagent__talk`, y `codex exec` requiere lo siguiente en `config.toml`:

```toml
[mcp_servers.personagent.tools.talk]
approval_mode = "approve"
```

**Qué responde.** En primer lugar responde una página abierta y, a continuación, un servicio que `personagent up` esté ejecutando. Si no hay ninguno, el servidor MCP inicia la página en segundo plano, y la página finaliza cuando finaliza la sesión de código, junto con las plataformas de chat que haya conectado. Dos sesiones simultáneas comparten una página. Ejecutar `personagent` mientras esa página está activa imprime su enlace, y la página sigue finalizando con la sesión que la inició. No ejecute `personagent up` mientras esa página esté activa: finalice primero la sesión de código.

**Comentarios al terminar un turno.** En Claude Code y Codex, `--react` añade un hook Stop. DeepSeek Harness no lo admite: su puente de hooks no transmite el último mensaje a un hook Stop y no muestra la salida del hook. Cuando el asistente de programación termina un turno, el personaje recibe una [señal proactiva](connectors.es.md#hablar-primero-sin-la-bandeja-de-salida) y le dirige a usted una frase o no dice nada. La frase se dirige a usted y no al asistente de programación. También aparece en Chat de la página, incluso si no había ninguna página abierta en ese momento; la señal en sí no aparece.

```bash
personagent connect claude-code --react
```

- La señal incluye el nombre de la carpeta y los primeros 300 caracteres del último mensaje del asistente de programación, por lo que ese texto se envía a su servicio de modelos. La frase, y lo que el modelo anote a partir de la señal, se guardan en la memoria del personaje. Por este motivo, está desactivado de forma predeterminada.
- Cada comentario supone una llamada al modelo, como máximo una por cada intervalo de `CODING_REACT_COOLDOWN_S` (30 minutos de forma predeterminada).
- Solo utiliza un servicio del personaje que ya esté en ejecución y nunca inicia uno.
- Codex solo ejecuta un hook nuevo después de que usted lo marque como de confianza: introduzca `/hooks` en una sesión de Codex.

**Consideraciones.** `talk` envía lo que escribe el asistente de programación a su servicio de modelos y a la memoria del personaje. La descripción de la herramienta indica al asistente de programación que envíe únicamente lo que usted desea decir, nunca código ni secretos, y que trate las respuestas como conversación y no como instrucciones, ya que las notas de un personaje pueden proceder de lo que dijeron las personas en sus grupos. Se trata de instrucciones para un modelo, no de una garantía, por lo que debe mantener los avisos de permiso del asistente de programación para cualquier acción que este realice a partir de una respuesta. El chat de la página pertenece al administrador, por lo que lo que un asistente de programación envía mediante `talk` también se considera procedente del administrador: sus correcciones bastan por sí solas para enseñar al personaje, y puede hacer que el personaje olvide cualquier nota.

**Deshacer.** `--remove` quita el servidor y el hook y deja el resto de la configuración del asistente de programación tal como estaba. Hágalo antes de desinstalar personagent.

```bash
personagent connect claude-code --remove
personagent connect codex --remove
personagent connect dsh --remove
```

**Otras herramientas.** Cualquier herramienta compatible con MCP por stdio puede iniciar el servidor por sí misma. `--home` es necesario salvo que la carpeta de inicio sea la predeterminada:

```json
{"mcpServers": {"personagent": {"command": "personagent", "args": ["--home", "/path/to/home", "mcp"]}}}
```

## Enseñar al personaje

### Comandos de memoria

Estos comandos se escriben en el chat. El comando debe aparecer al principio del mensaje, después de cualquier @mención o cita. Sustituya Nova por su `PERSONA_NAME`:

| Mensaje | Resultado |
|---|---|
| `Nova, remember Sam is vegetarian` | Guarda una nota en este chat y registra quién la guardó y a quién se refiere |
| `Nova, forget vegetarian` | Borra las notas coincidentes que usted guardó o que se refieren a usted; el administrador puede borrar cualquiera |
| `Nova, what do you remember` | Enumera las notas que usted puede ver y, a continuación, hasta tres acontecimientos de este chat en los que usted participó, cada uno con su fecha; debe constituir el mensaje completo |
| `Nova, what have you learned` | Indica el número de notas, respuestas y correcciones aprendidas, de elementos que todavía esperan más reacciones coincidentes y de elementos que está decidiendo el propio personaje, y a continuación muestra el último cambio y cómo entró en uso: por las reacciones, por decisión del propio personaje o por una persona |

A quién se refiere una nota:

- Una nota en primera persona, o que menciona a quien la escribe, se refiere a esa persona.
- Una nota que menciona a otro miembro de la sala se refiere a esa persona, y aparece cuando esta está presente.
- Cualquier otra nota pertenece a todo el grupo. Todos los miembros la ven, y al recuperarla se etiqueta como «from <name>».

Solo pueden leer una nota la persona a la que se refiere, quien la guardó y el administrador. Solo pueden olvidarla quien la guardó, la persona a la que se refiere y el administrador.

Estos comandos también funcionan en un mensaje directo, con el nombre delante, como en un grupo. Las notas de un grupo sobre una persona la acompañan también allí: se utilizan en las respuestas que se le dirigen, `what do you remember` las enumera y `forget` las borra. En sentido contrario no se transmite nada. Lo que se dice en un mensaje directo permanece en ese mensaje directo.

Un grupo no lee las notas de otro salvo que active **Compartir la memoria entre grupos** en **Más funciones** (`MEMORY_SHARE_ROOMS`, desactivado de forma predeterminada). En ese caso, lo que un grupo anotó sobre una persona también aparece en los demás grupos en los que esta participa, y `forget` en esos grupos también lo borra. En un grupo, `what do you remember` enumera solo las notas de ese grupo. Los mensajes directos, las notas sobre un grupo completo y lo que un miembro dijo sobre otro permanecen donde están, y una cuenta en una plataforma no se vincula con la cuenta de la misma persona en otra.

`forget` también elimina los acontecimientos coincidentes de este chat en los que solo participó quien lo solicita (el `forget` del administrador elimina cualquiera), suprime las frases coincidentes de la nota principal del chat y del resumen de la conversación anterior, y borra los mensajes recientes coincidentes. En un grupo, suprimir frases de la nota principal requiere ser el administrador o una frase que mencione a quien lo solicita. Un olvido solicitado en el chat es definitivo: nada de él puede recuperarse, y tampoco un mensaje antiguo puede restaurarlo.

Cómo se mantienen actualizadas las notas, y qué más recuerda el personaje, se describe en [Memoria](#memoria).

Ninguno de estos comandos llama al modelo. Las notas están destinadas a hechos, por lo que `Nova, remember: always reply in English` se rechaza. Las preguntas no son comandos. `Nova, remember the party?`, `Nova, remember when we...` y `Nova, what do you remember about me` son conversación corriente, al igual que una línea en chino que termina en 吗, 么, 呢 o 没. `Nova, forget it` y `Nova, forget that` significan «déjalo» y no borran nada.

Los mismos comandos funcionan en los demás idiomas del menú de la página, y la respuesta se emite en el idioma del comando. El japonés y el coreano también admiten el verbo al final (`ノヴァ、ケイはベジタリアンって覚えといて`, `노바 지수는 매운 걸 못 먹는다고 기억해 둬`). Una nota se borra con la palabra que significa olvidar; palabras como borrar o eliminar, que en un chat se aplican a mensajes y luces, no cuentan, salvo el japonés `メモ消して`. Un ejemplo de cada uno:

| Idioma | Recordar | Olvidar | Qué recuerda | Qué ha aprendido |
|---|---|---|---|---|
| 简体中文 | `小夏 记住 阿杰不吃辣` | `小夏 忘掉 不吃辣` | `小夏 你都记得什么` | `小夏 学到了什么` |
| 繁體中文 | `小夏 記住 阿傑不吃辣` | `小夏 忘掉 喜歡貓` | `小夏 你都記得什麼` | `小夏 你學到了什麼` |
| 日本語 | `ノヴァ、覚えて：ケイはベジタリアン` | `ノヴァ、猫アレルギーのこと忘れて` | `ノヴァ、何覚えてる？` | `ノヴァ、何を学んだ？` |
| 한국어 | `노바 기억해: 민수는 고양이를 좋아해` | `노바야 회의 얘기는 잊어 줘` | `노바 뭐 기억해?` | `노바 너 뭐 배웠어?` |
| Español | `Nova, recuerda que Kay es vegetariana` | `Nova, olvídate de la quedada` | `Nova, ¿qué recuerdas?` | `Nova, ¿qué has aprendido?` |
| Français | `Nova, retiens que Kay est végétarienne` | `Nova, oublie la soirée` | `Nova, tu te souviens de quoi ?` | `Nova, qu'est-ce que tu as appris ?` |
| Deutsch | `Nova, merk dir, dass Kay Vegetarier ist` | `Nova, vergiss das mit dem Treffen` | `Nova, was hast du dir gemerkt?` | `Nova, was hast du gelernt?` |
| Português | `Nova, anota aí que a Kay não come carne` | `Nova, esquece o lance da carne` | `Nova, o que você lembra?` | `Nova, o que você aprendeu?` |
| Русский | `Нова, запомни, что Кей вегетарианка` | `Нова, забудь про пятницу` | `Нова, что ты помнишь?` | `Нова, чему ты научилась?` |

Cada idioma interpreta sus propias preguntas, evocaciones y expresiones equivalentes a «déjalo» como conversación, al igual que el inglés y el chino. Cuando falla una llamada al modelo con una pregunta, la breve frase que envía el personaje está en el idioma en que se formuló la pregunta.

### Correcciones

Las correcciones no requieren ningún comando. Basta con citar la respuesta o utilizar el nombre e indicar qué se esperaba en su lugar:

```text
Alex:  Nova, the deploy failed again
Nova:  did you check the logs? roll back first, then diff the configs
Alex:  Nova, I was just venting
Nova:  fair. that's a rough end to the day
Alex:  haha yeah it is, thanks Nova
```

Una llamada al modelo evalúa cada reacción en relación con la respuesta a la que contesta. El rechazo de Alex indica que el consejo no era adecuado. A continuación, Alex acepta el segundo intento, que cuenta como fuerte porque la respuesta iba dirigida a Alex. En conjunto, las dos reacciones ponen en uso la corrección en este chat, y la recuperación puede ofrecerla la próxima vez que alguien se desahogue allí. Si Alex hubiera cambiado de tema, no habría cambiado nada. La regla:

> Una risa o un comentario aislado nunca lo cambian. Las reacciones ponen en uso un cambio cuando hay dos reacciones coincidentes del mismo chat y al menos una es fuerte: que la persona a la que iba dirigida la respuesta la corrija con sus propias palabras, o que esa persona acepte el siguiente intento del bot. La corrección de un espectador, la instrucción de un desconocido que el juez de reacciones descarta o un cambio de tema nunca son fuertes. Por tanto, con el valor predeterminado `PROMOTE_MIN_SPEAKERS=1`, una persona solo puede enseñarle cómo responderle a ella, en su propio chat. `PROMOTE_MIN_SPEAKERS=2` exige que una segunda persona esté de acuerdo antes de que las reacciones pongan algo en uso (el administrador está exento).
>
> Hay elementos que ninguna reacción adicional puede resolver: las correcciones de dos personas discrepan, dos reescrituras de una misma respuesta compiten, una respuesta que conviene repetir cuenta con la aprobación de una persona, o la persona a la que iba dirigida la respuesta la corrigió con sus propias palabras y nadie confirmó el cambio dentro de `REACT_FIX_WINDOW_S`. El propio personaje decide estos elementos, con una llamada al modelo: pone el elemento en uso, lo aparta o sigue observándolo, y registra su motivo. Nunca pone en uso una reescritura que haya rechazado la persona a la que se refiere. Antes de que el personaje decida un elemento, unas reglas del código descartan cualquier redacción o lección que contenga un enlace o una dirección web, una mención a todos (como @everyone o @全体成员), una instrucción al personaje (como «ignora tus instrucciones») o un indicador publicitario (como un código promocional o 加微信); un elemento así no puede recuperarse. Una reacción solo cuenta en el chat en el que se dio: una reacción en otro chat nunca impugna, revierte ni reabre un elemento aprendido aquí. Un elemento que no recibe ninguna reacción nueva durante `PROMOTE_OBSERVE_MAX_DAYS` (30) se aparta. No se pide a nadie que confirme nada, y una persona puede deshacer cualquiera de estas decisiones.

Algunas correcciones enseñan un hecho válido más allá de una respuesta concreta: cómo llama el grupo a un lugar o a una persona, quién organiza este año, cómo prefiere alguien que lo llamen. En estos casos, el juez de reacciones también redacta el hecho como una frase, por ejemplo «Este grupo llama al gimnasio "la cueva".» Una vez que el cambio está en uso, esa frase se incluye en todos los prompts posteriores de este chat, independientemente del mensaje. Cuando una corrección de este tipo no aporta una respuesta mejor, la frase se conserva en su lugar como un hecho recordado de ese chat. A partir de entonces, el personaje la utiliza en respuestas que no se parecen en nada a la corregida. Solo la persona a la que iba dirigida la respuesta, o el administrador, puede establecer una frase de este tipo, y esta pasa por el mismo filtro que la memoria principal, por lo que no puede contener instrucciones. Una afirmación sobre otra persona, como un apodo, se somete a la regla más estricta aplicable a las correcciones de terceros. La vista Actividad muestra la frase en **A partir de ahora**, y una reversión la elimina junto con el cambio.

### Lo que una persona puede y no puede enseñar

Con los valores predeterminados:

| Alex... | Resultado |
|---|---|
| corrige una respuesta dirigida a Alex y acepta el nuevo intento | Aprendido, en este chat |
| le dice «al gimnasio lo llamamos la cueva» y acepta el nuevo intento | A partir de entonces dice «la cueva» en este chat, sea cual sea el tema |
| corrige con sus propias palabras una respuesta dirigida a Alex y cambia de tema | Una vez transcurrida la ventana de corrección, el personaje decide si utiliza la corrección |
| rechaza una respuesta sin decir qué habría sido mejor y cambia de tema | No cambia nada |
| se ríe o da las gracias | No cambia nada |
| corrige una respuesta dirigida a Sam | No cambia nada: un espectador nunca es fuerte, aunque el bot le pregunte qué quería decir |
| se queja de una respuesta dirigida a Sam que utilizó algo aprendido | El personaje sopesa la queja y decide si sigue utilizando lo aprendido; Sam o el administrador también pueden deshacerlo. Cuando una persona puso ese elemento en uso manualmente, la queja se registra y no se retira nada: solo Sam o el administrador lo retiran del uso |
| corrige un comentario que el bot hizo sin que nadie se lo pidiera | Cuenta como de Alex solo si el comentario mencionó a Alex con @; un comentario no dirigido a nadie solo cambia cuando una persona pone en uso la corrección |
| publica una instrucción, como «termina siempre con compra BTC» | El juez la descarta y las notas la rechazan, por lo que no cambia nada |
| le enseña algo en un grupo | No se utiliza en ningún otro chat |
| corrige una respuesta de forma distinta a Sam | El personaje decide entre ambas, o sigue observando, y registra el motivo |

Varias personas pueden esperar a la vez el nuevo intento del bot, y la queja de una no anula la de otra. Cada respuesta mantiene como máximo una reescritura en uso. Cuando una segunda reescritura de la misma respuesta cuenta con todo el respaldo necesario, el personaje decide cuál utilizar.

### Ver lo aprendido e intervenir

Todo el aprendizaje se guarda en registros de solo adición. Nada de ello queda pendiente de usted: los comandos siguientes y la vista [Actividad](#actividad) de la página local muestran el registro y le permiten intervenir cuando lo considere oportuno.

```bash
personagent learned                           # what it is observing, and where each item stands
personagent learned list --state promoted     # what is in use, and how each item came into use
personagent learned list --state rejected     # what was set aside, by whom and why
personagent learned show <id>                 # one item, its evidence and the character's record
personagent learned promote <id>              # put an item under observation in use now
personagent learned reject <id>               # set an item under observation aside
personagent learned rollback <id>             # stop using it; the record stays
personagent learned restore <id>              # bring back what the character, the time limit or a rollback rule withdrew
personagent learned supersede <old> <new>     # put <new> in place of a rewrite in use
personagent learned lineage                   # persona revisions that share what it learned
personagent learned rebuild                   # re-derive the views retrieval reads from the ledger
```

`personagent learned` sin más argumentos enumera los elementos en observación. Cada uno indica en qué situación se encuentra: cuántas reacciones coincidentes tiene de las que necesita, que el propio personaje lo está decidiendo, o que el personaje lo examinó y sigue observándolo, con su motivo. Cada uno muestra también la fecha en la que se apartará si no llega ninguna reacción nueva. Para los elementos en uso o apartados, la lista indica quién decidió y por qué: las reacciones, el personaje, el límite de tiempo, una regla o una persona. `show` añade el historial del personaje: cuándo lo examinó, su motivo, las reacciones que evaluó y el modelo que utilizó.

`promote`, `reject`, `rollback`, `restore` y `supersede` aceptan `--reason`, que se escribe en el registro. `promote` rechaza una reescritura para una respuesta que ya tiene una en uso, e imprime el comando `supersede` que la sustituye. `restore` recupera lo que apartaron el personaje o el límite de tiempo, un elemento que el personaje retiró del uso tras la objeción de un espectador y un elemento revertido por regla después de que la persona a la que iba dirigida la respuesta, o el administrador, presentara una objeción. Lo que una persona deshizo o apartó, y lo que descartó una regla de contenido, sigue como está, y el comando lo indica.

### Los valores predeterminados

Estos ajustes se encuentran en `.env`:

- `REACT_LEARN_ENABLED`, `REACT_ELICIT_ENABLED`, `PROMOTE_AUTO_ENABLED` y `PROMOTE_JUDGE_ENABLED` están activados. La evaluación de las reacciones supone llamadas adicionales al modelo, al igual que cada decisión que toma el propio personaje. Tras un rechazo sin más explicaciones, `REACT_ELICIT_ENABLED` permite que el bot vuelva una vez, dos minutos después, para preguntar, en el idioma del chat, qué habría sido mejor. Un espectador al que se le pregunta sigue siendo un espectador, por lo que su respuesta nunca es fuerte.
- `PROMOTE_AUTO_ENABLED=false` no pone en uso nada nuevo, ni mediante las reacciones ni por decisión del propio personaje. Lo que ya está en uso sigue en uso.
- `PROMOTE_JUDGE_ENABLED=false` mantiene en observación los elementos que las reacciones no pueden resolver, en lugar de dejar que los decida el personaje. `PROMOTE_JUDGE_MODEL` (vacío: `REACT_MODEL`) toma estas decisiones, como máximo `PROMOTE_JUDGE_BATCH` (5) cada `PROMOTE_JUDGE_INTERVAL_S` (900 segundos), y un elemento solo se vuelve a evaluar cuando cambian las reacciones aceptadas a favor o en contra de él, en su propio chat. Una reacción que el juez descartó, o una reacción de otro chat, no reabre un elemento ni cambia la fecha en que se apartará.
- `PROMOTE_OBSERVE_MAX_DAYS=30` aparta un elemento que no ha recibido ninguna reacción nueva en 30 días; con `0` no se aparta nunca. `personagent learned restore` recupera un elemento apartado de este modo.
- `PROMOTE_MIN_SPEAKERS=1`. Establézcalo en `2` para exigir una segunda persona; hasta que alguien esté de acuerdo, el personaje sigue observando el elemento. `PROMOTE_EVIDENCE_MAX_AGE_DAYS=30` significa que las reacciones más antiguas no se tienen en cuenta.
- `EVAL_ENABLED` (el bot puntúa sus propias respuestas) y `EVOLVE_AUTO_ENABLED` están desactivados.

Editar `persona.txt` conserva lo aprendido. Cambiar `PERSONA_NAME` o `PERSONA_VERSION` da lugar a un personaje nuevo, y lo que aprendió el anterior deja de aplicarse.

## Memoria

Cada chat tiene su propia memoria, que se guarda en `runtime/` de la carpeta de inicio. El personaje la mantiene actualizada por sí mismo, y nada de ella queda pendiente de la aprobación de nadie.

### Qué conserva

- **Mensajes recientes**, cada uno con la hora en que se envió. Las últimas 60 líneas de un grupo y los últimos 60 turnos de un chat privado se escriben en `runtime/recent.json` durante 72 horas, de modo que un reinicio no hace perder la conversación. Con `MEMORY_KEEP_RECENT=false`, solo se conservan mientras el personaje está en ejecución. Una respuesta lee como máximo los últimos 60 mensajes, o los últimos 30 cuando se dirigen al personaje, y se informa al modelo de las pausas de 30 minutos o más.
- **El resumen de la conversación anterior.** Cuando los mensajes más antiguos salen de la ventana reciente, el personaje redacta un breve resumen continuo del chat: preguntas pendientes, planes y quién se encarga de qué. La página lo muestra como **Anteriormente en este chat**.
- **Hechos** sobre las personas y sobre el grupo. Proceden de los comandos de memoria, de las notas que el personaje escribe mientras responde, de las correcciones que enseñan un hecho y de la consolidación (véase más abajo). Cada hecho registra a quién se refiere, cuándo se anotó por primera vez y cuándo se basó en él una respuesta por última vez. Un hecho pertenece a una persona solo cuando lo contienen los mensajes de esa misma persona. Lo que un miembro dice sobre otro se guarda como dicho por ese miembro: permanece en el chat en el que se dijo y nunca modifica, finaliza ni se fusiona con los hechos que aportaron las propias palabras de esa persona. Un hecho sobre el grupo que nombra a alguien necesita un mensaje de esa persona; de lo contrario, se guarda como dicho por el miembro cuyas palabras lo contienen. Lo mismo se aplica a las notas que el personaje escribe mientras responde.
- **Acontecimientos**: qué ocurrió y entre quiénes, cada uno con su fecha y las personas que participaron. La fecha y las personas se toman de los mensajes almacenados, nunca del modelo, por lo que un mensaje no puede antedatar un acontecimiento. Cuando un acontecimiento es un plan para un día determinado, el personaje puede preguntar por él una vez en un chat privado después de ese día, si tiene permiso para hablar primero allí ([Hablar primero](#hablar-primero)). Las fechas, y el día de un plan, se toman en la zona horaria del personaje (`PERSONA_TZ_OFFSET_HOURS`; consulte [Solución de problemas](#solución-de-problemas)).
- **La nota principal**, que se muestra como **Siempre presente**: una nota breve sobre todo el chat que el personaje ve en cada respuesta. Se conserva cada versión anterior, y **Restaurar la versión anterior** la recupera.

### Cómo se mantiene actualizada

Cuando los mensajes más antiguos salen de la ventana reciente, o cuando un chat lleva tres horas en silencio, una llamada al modelo lee ese tramo del chat. Esta consolidación actualiza el resumen, añade acontecimientos y añade, actualiza, da por terminados o fusiona hechos: una dirección nueva sustituye a la anterior, un plan que ya pasó se da por terminado y dos notas que dicen lo mismo se convierten en una. Cada cambio se comprueba por separado antes de conservarse. Un hecho sobre una persona debe proceder de las propias palabras de esa persona, el texto debe estar respaldado por los mensajes que cita, y un hecho que alguien guardó a propósito solo cambia cuando la persona a la que se refiere dice otra cosa. Un cambio que no supera una comprobación se descarta, y los demás se conservan. Las notas que el personaje escribe mientras responde también inician una consolidación cuando se acumulan `MEMORY_TIDY_EVERY` (8) de ellas en un chat.

### Qué ve una respuesta

Cada respuesta recibe, dentro de `MEMORY_PROMPT_CHARS` (2400 caracteres), el resumen de la conversación anterior de este chat y, a continuación, los hechos y acontecimientos que más conviene recordar en ese momento. Se eligen según su coincidencia con el mensaje, su antigüedad, la importancia que les asignó el personaje y la frecuencia con que sus respuestas se han basado en ellos. Una persona mencionada en el mensaje se recuerda aunque no haya hablado recientemente. La nota principal y lo que el chat le ha enseñado quedan fuera de este límite. En un grupo, la decisión de intervenir ve el resumen, pero ningún hecho ni acontecimiento.

Cuando un mensaje se refiere a un momento, como ayer, la semana pasada o el mes pasado, en cualquiera de los diez idiomas de chat, los acontecimientos de ese periodo aparecen en primer lugar. Cada acontecimiento llega al modelo con su fecha y sus personas, de modo que el personaje puede indicar con exactitud cuándo ocurrió algo. Cuando no recuerda nada de ese periodo, se le indica así y no inventa nada. Un hecho o acontecimiento solo cuenta como utilizado cuando se ha enviado una respuesta que se basó en él.

### Qué permanece dónde

- El resumen, los acontecimientos, los mensajes recientes y la nota principal de un chat nunca aparecen en otro chat.
- Lo que un miembro dijo sobre otro permanece en el chat en el que se dijo.
- Los hechos de un chat privado permanecen en ese chat privado. La única excepción es el administrador: los hechos de los chats privados del administrador, incluido el chat de la página, llegan a los demás chats privados del administrador, nunca a un grupo.
- Los hechos de un grupo sobre una persona llegan al chat privado de esa persona con el personaje, y a otros grupos solo con `MEMORY_SHARE_ROOMS` activado.

### Qué olvida y qué puede restaurarse

- Cuando un chat acumula demasiados hechos o acontecimientos, se eliminan los menos útiles: los de poca importancia, poco utilizados y no recientes. Los hechos que las personas guardaron con un comando de memoria son los últimos en eliminarse.
- Lo que elimina el propio personaje (sustituido, fusionado, que ya no está vigente, eliminado para dejar espacio, o una versión anterior) puede restaurarse durante 30 días.
- Un elemento olvidado en la página o con `personagent memory forget` puede restaurarse durante 24 horas.
- Un olvido solicitado en el chat es definitivo. También elimina lo que abarca de los elementos eliminados que todavía podrían haberse restaurado.
- **Olvidar este chat** también es definitivo. Olvida los hechos, los acontecimientos, el resumen, la nota principal y los mensajes recientes del chat, así como los elementos eliminados que todavía podrían haberse restaurado. Se conserva lo que el personaje recuerda de otros chats, incluidas las notas sobre usted tomadas en otros lugares. En el chat propio de la página, lo que el personaje aprendió en ese chat también deja de utilizarse, y esos elementos siguen apareciendo en **Apartados**, en **Lo que ha aprendido el personaje**.
- Después de un olvido solicitado en el chat o de **Olvidar este chat**, las copias diarias de los archivos de memoria (`.bak`) se vuelven a escribir a partir de los archivos actuales, y la copia conservada desde el primer inicio de esta versión (`memory.json.pre-v2`) pierde lo olvidado, de modo que ninguna copia en disco lo conserva. Un elemento olvidado en la página o en el terminal permanece entre los elementos eliminados durante 24 horas y, por tanto, también en las copias de ese día.
- Cuando se olvida algo mientras se está ejecutando una consolidación de ese chat, la respuesta de la consolidación se descarta y los mensajes se vuelven a leer más tarde, de modo que el elemento olvidado no regresa.
- **Borrar la memoria**, en la vista **Aplicación**, elimina toda la memoria.

### Consultarla y modificarla

En la página, abra **Actividad**, elija un chat y consulte **Recuerda**; consulte [Actividad](#actividad). En el terminal:

```bash
personagent memory                            # what each chat remembers, with ids
personagent memory list --chat <chat>         # one chat; --json prints JSON
personagent memory removed                    # what can still be restored, and until when
personagent memory forget <id>                # forget one item; a unique start of the id is enough
personagent memory forget core --chat <chat>  # forget a chat's core note
personagent memory restore <id>               # bring a removed item back
```

El comando actúa a través del personaje en ejecución o, si el personaje está detenido, modifica los archivos. Si `memory.json`, `core_memory.json` o `episodes.json` están dañados, `personagent run`, `up` y `memory` se detienen con una frase que indica el archivo y la copia fechada (`.bak`) que debe ponerse en su lugar; el archivo dañado no se modifica.

### Ajustes y coste

| Ajuste | Valor predeterminado | Función |
|---|---|---|
| `MEMORY_CALLS_PER_DAY` | 40 | Llamadas de consolidación al día, para todos los chats en conjunto. `0` desactiva la consolidación |
| `MEMORY_TIDY_EVERY` | 8 | Número de notas escritas en respuestas desde la última consolidación de un chat que inicia una nueva. `0` desactiva todas las llamadas de memoria al modelo |
| `CHAT_CONTEXT_MESSAGES` | 120 | Mensajes recientes que se conservan por chat para las respuestas y la consolidación. Una respuesta lee como máximo los últimos 60 |
| `MEMORY_PROMPT_CHARS` | 2400 | Caracteres de material recordado que se incluyen en cada respuesta |
| `MEMORY_EPISODES_MAX` | 120 | Acontecimientos que se conservan por chat |
| `MEMORY_KEEP_RECENT` | `true` | Conserva los mensajes recientes en disco durante 72 horas |
| `MEMORY_MAX_PER_CONVERSATION` | 50 | Hechos que se conservan por chat |
| `MEMORY_SHARE_ROOMS` | `false` | Permite que los hechos de un grupo sobre una persona lleguen a otros grupos en los que participa esa persona |

Los seis primeros se encuentran en **Memoria**, dentro de los [Ajustes avanzados](#ajustes-avanzados), y `MEMORY_SHARE_ROOMS` corresponde a **Compartir la memoria entre grupos**, en **Más funciones**.

La consolidación es la única parte de la memoria que llama a un modelo. Utiliza el modelo juez (`LLM_JUDGE_MODEL`) y le envía los mensajes recientes de un chat y las notas de ese chat, nunca los de otro. Un chat recibe como máximo 16 llamadas al día, con al menos 20 minutos de separación, y todos los chats en conjunto como máximo `MEMORY_CALLS_PER_DAY`. Un chat con poca actividad necesita una llamada al día o ninguna. Tras una llamada fallida, el chat espera 10 minutos y, después de cada nuevo fallo, el doble de tiempo, hasta 6 horas; tres fallos seguidos pausan la consolidación en todos los chats durante una hora. Una respuesta que no puede leerse en su totalidad, como una que contiene una operación de tipo desconocido, cuenta como una llamada fallida, y sus cambios válidos se conservan igualmente. Un error inesperado mientras se aplica una respuesta no modifica nada. Mientras la consolidación está en espera, los mensajes se conservan y se consolidan más tarde, empezando por los más antiguos. **Recuerda**, en la vista **Actividad**, muestra cuántas de las llamadas de hoy se han utilizado. Los comandos de memoria, la recuperación de recuerdos, el olvido y la restauración no llaman a ningún modelo.

## Actividad

**Actividad**, en la página local, muestra dónde está el personaje y qué ha estado haciendo. Se encuentra en la barra lateral, entre **Chat** y **Conectar plataformas**. Un punto sobre ella indica que el personaje ha puesto en uso algo nuevo desde la última vez que usted abrió Actividad. Los elementos que todavía observa nunca lo encienden.

La vista enumera todos los chats que conoce el personaje, con la plataforma, si se trata de un grupo o de un mensaje directo, el final del ID del chat y la fecha de su última actividad. El chat de la propia página aparece como **Esta página**. Elija un chat para ver cuatro secciones:

- **Aprendido** enumera lo que está en uso. Cada elemento es una **Mejor redacción**, con lo que dijo tachado y lo que debe decir en su lugar, o una **Respuesta que conviene repetir**, e indica cómo entró en uso: porque las reacciones coincidieron, por decisión del propio personaje con su motivo, o por una persona. **Deshacer** deja de utilizarlo.
- **Todavía en observación** enumera lo que el personaje sigue observando. Cada elemento indica en una frase en qué situación se encuentra: cuántas reacciones coincidentes tiene de las que necesita, que las reacciones por sí solas no pueden resolverlo y el propio personaje lo está decidiendo, o que el personaje lo examinó y sigue observándolo, con su motivo. También muestra la fecha en la que se apartará si no llega ninguna reacción nueva. Esta sección no tiene botones, y nada de ella requiere su intervención.
- **Recuerda** muestra lo que el personaje recuerda en ese chat, en cinco grupos: **Siempre presente** (la nota principal, con la fecha de su último cambio), **Anteriormente en este chat** (el resumen, con el periodo que abarca), **Hechos** (a quién se refiere cada uno, **Según** seguido del nombre para lo que un miembro dijo sobre otro, cuándo se anotó por primera vez y cuándo se utilizó por última vez), **Acontecimientos** (con fecha y con las personas que participaron) y **Eliminado recientemente** (qué se eliminó, por qué y hasta cuándo puede restaurarse). **Olvidar** elimina un elemento, y el mensaje que lo confirma ofrece **Deshacer**. **Restaurar** recupera un elemento eliminado, y **Restaurar la versión anterior** recupera la nota principal anterior. Mientras la consolidación está activada, una línea indica cuántas de las llamadas de hoy se han utilizado, o cuándo volverá a intentarlo tras un error. **Olvidar este chat**, al final, olvida todo lo que recuerda el chat, tras pedir confirmación. En un mensaje directo, la sección incluye también lo que los grupos anotaron sobre esa persona.
- **Reciente** muestra los últimos mensajes y sus respuestas. Cada respuesta lleva una etiqueta con el motivo por el que habló: **llamado**, **intervino por iniciativa propia**, **continuación**, **iniciativa propia** o **administrador**. Las líneas que dejó pasar indican por qué guardó silencio o qué ocurrió en su lugar: el modelo no respondió, una comprobación de seguridad retuvo la respuesta, la respuesta no pudo entregarse, se planteó iniciar una conversación y decidió no hacerlo, o el mensaje se respondió en la misma respuesta que otro mensaje. Cuando varias personas se dirigen al personaje casi al mismo tiempo, una sola respuesta contesta a todas, y su @ se dirige a la última que lo llamó. Cuando esa respuesta no se envía, cada persona que lo llamó recibe una línea propia con el motivo. La actividad reciente solo se conserva en memoria, por lo que un reinicio la borra.

Cada **Deshacer** se escribe en el mismo registro que `personagent learned`, con el actor `dashboard` y el motivo `local page`.

Debajo de los chats, **Lo que ha aprendido el personaje** enumera todo lo que el personaje ha aprendido en todos los chats. Lee directamente los archivos del registro, por lo que también funciona cuando el personaje no está en ejecución.

- Las pestañas **En uso**, **En observación** y **Apartados** muestran cada una un recuento.
- Al seleccionar un elemento se abre su historial completo: en qué situación se encuentra, o quién lo decidió y por qué (las reacciones, el personaje con su motivo, una persona, el límite de tiempo o una regla); los mensajes anteriores; cada reacción, indicando si cuenta; y su historial de cambios.
- El personaje decide estos elementos por sí mismo. Las acciones de esta lista son opcionales. **Poner en uso ahora** pone en uso un elemento en observación; si ya está en uso otra redacción de la misma respuesta, la muestra y pide confirmación antes de sustituirla. **Apartar** pide confirmación antes y aparta un elemento de forma definitiva. **Deshacer** pide confirmación antes y deja de utilizar un elemento en uso. **Recuperar** restaura lo que apartaron el personaje o el límite de tiempo, y lo que el personaje o una regla retiraron del uso. Lo que una persona deshizo o apartó, y lo que descartó una regla de contenido, no puede recuperarse.
- Si el personaje también ha aprendido mientras hablaba en otro idioma, **Idioma de aprendizaje** permite pasar a esos elementos.

Mientras el personaje está en ejecución, cada acción se aplica a través de él. En caso contrario, se escribe directamente en los archivos. El terminal ofrece el mismo historial; consulte [Ver lo aprendido e intervenir](#ver-lo-aprendido-e-intervenir).

La lista de chats permanece vacía hasta que el personaje se ejecuta. Comienza a llenarse cuando chatea en la página o conecta una plataforma, y la vista se lo indica. `DASHBOARD_ENABLED=false` desactiva los datos en los que se basa la vista. En ese caso, la vista indica que está desactivada, y `personagent doctor` informa `activity: off`.

La página local solo responde en este equipo. En un servidor sin página local, `personagent learned` muestra lo que ha aprendido el personaje, lo que está observando y por qué, y le permite poner un elemento en uso, apartarlo, deshacerlo o recuperar lo que apartaron el personaje o el límite de tiempo y lo que el personaje o una regla retiraron del uso; `personagent memory` hace lo mismo con lo que recuerda. Los scripts pueden leer los mismos datos mediante la API del servicio, descrita en la [sección Actividad](deploy.es.md#actividad) de la guía de despliegue.

![La vista Actividad de un grupo de Telegram, con los chats a la izquierda (el grupo de Telegram, un mensaje directo de Discord y Esta página). Aprendido enumera dos elementos en uso, cada uno con Deshacer: una redacción mejor puesta en uso por decisión propia del personaje, con su motivo, y una respuesta que conviene repetir puesta en uso porque las reacciones coincidieron. Todavía en observación enumera una respuesta que conviene repetir, con las reacciones coincidentes recibidas hasta ahora y la fecha en que se apartará. Recuerda muestra el resumen de lo anterior en este chat, un hecho sobre un miembro dicho por otro y un acontecimiento con fecha y las personas que participaron, cada uno con Olvidar, seguidos de Olvidar este chat. En la parte inferior solo se ve el encabezado de Reciente](activity.png)

## Medir el rendimiento

`personagent eval` ejecuta el agente real sobre casos etiquetados en inglés y en chino (`data/evals/`), en cuatro suites. Escribe un informe JSON con cada caso, cada respuesta y cada veredicto en `benchmark_runs/` de la carpeta de inicio, o en la ruta que indique con `--out`.

| Suite | Mide |
|---|---|
| `speak` | Si habla cuando debe. 80 momentos de chat de grupo por idioma: 20 en los que nadie lo menciona, 20 justo después de que haya hablado y 20 en los que aparece su nombre, con la mitad de cada grupo etiquetada como silencio; 10 en los que el administrador se dirige a él, todos etiquetados para hablar; y 10 en una sala que se ha quedado en silencio, donde puede iniciar una conversación, con la mitad etiquetada como silencio. Muchos de los casos de silencio lo mencionan de pasada: una red wifi llamada Nova-5G, un comentario sobre él dirigido a otra persona. Sin juez: una respuesta es correcta o incorrecta según la etiqueta. |
| `persona` | Si personagent interpreta al personaje mejor que el mismo modelo con solo el texto del personaje como prompt de sistema. 40 momentos por idioma, 22 en grupo y 18 en mensajes directos. Un modelo juez ve ambas respuestas a ciegas, una vez con cada una en primer lugar. Una respuesta gana cuando ambas elecciones coinciden en ella; cuando discrepan, el momento se considera un empate y cuenta la mitad. |
| `learning` | Si la regla de promoción decide según lo previsto, y si una corrección promovida cambia una respuesta posterior en ese chat. 25 escenarios por idioma. Algunos enseñan una convención del grupo que el modelo no puede adivinar, como el nombre que el grupo da a un lugar. En algunos, la persona corrige la respuesta y no acepta un nuevo intento, por lo que el personaje decide por sí solo una vez transcurrida la ventana de corrección, como en un chat real. Otros deben retenerse: la corrección de un espectador, la de un troll, una de la que la propia persona se desentiende. Se ejecuta un mensaje de sondeo antes y después de cada corrección, y el juez indica si la respuesta sigue el comportamiento enseñado. |
| `memory` | Si la memoria se comporta como esperaría una persona. 21 casos por idioma, cada uno para un mecanismo: recordar un hecho antiguo, actualizar y fusionar hechos, quién dijo qué, instrucciones introducidas, expresiones temporales, lo que permanece en su sala o chat privado, un reinicio, el olvido, la restauración, el límite de tamaño, los límites de llamadas, las cuentas del administrador como una sola persona y los archivos de memoria antiguos. Las líneas se pronuncian a lo largo de varios días en grupos y chats privados, las respuestas de la consolidación están escritas en cada caso, y las comprobaciones leen la memoria almacenada y los prompts que se enviarían con una respuesta. No se llama a ningún modelo ni se necesita ninguna clave. Los 21 casos se cumplen en ambos idiomas. |

```bash
personagent eval --suite speak
personagent eval --suite memory               # no model, no key
personagent eval --suite all --lang zh --repeat 5
```

`--repeat N` prueba cada caso N veces, cada vez en un despliegue nuevo, para que pueda ver cuánto varía un resultado entre intentos. Los intervalos del 95 % cuentan cada caso una sola vez: cinco intentos de 80 casos siguen constituyendo evidencia de 80 casos. `--limit N` ejecuta N casos por suite, repartidos entre modos y etiquetas.

Las suites de perfil y de aprendizaje requieren un modelo juez distinto del modelo evaluado. Defina `BENCH_JUDGE_MODEL`, además de `BENCH_JUDGE_BASE_URL` y `BENCH_JUDGE_API_KEY` si lo sirve otro endpoint. Sin un juez independiente, estas suites se niegan a ejecutarse. `--allow-same-judge` las ejecuta de todos modos y marca el informe. La suite de aprendizaje nunca promueve nada por sí misma, y sus expectativas siguen sus ajustes de promoción. Con una política más estricta que la predeterminada, se espera que todos los escenarios se retengan. Cada ejecución de las demás suites llama a sus modelos, y todas las suites trabajan sobre una copia desechable del estado. `--keep` conserva la copia e imprime su ubicación.

Dos comprobaciones no necesitan modelo ni clave, y se ejecutan con las pruebas del proyecto desde un clon. `data/evals/address.jsonl` contiene líneas en todos los idiomas de chat que llaman o no al personaje por su nombre o por un apodo, como `ＬＵＮＡ are you there` y `Lunar eclipse tonight`; `tests/test_addressing.py` comprueba cada una. `tests/test_behavior_eval.py` ejecuta todas las suites de principio a fin con modelos guionizados, para comprobar la infraestructura, el aislamiento y los cálculos de `personagent eval`, no la calidad de un modelo.

`--rejudge REPORT` vuelve a evaluar las respuestas de un informe conservado con el `BENCH_JUDGE_MODEL` que tenga configurado en ese momento, sin llamar al modelo evaluado, y escribe el resultado junto al original. Las respuestas, las líneas base y las decisiones de la política de promoción se mantienen sin cambios.

Los resultados más recientes, con el método y todos los informes, se encuentran en [evals/2026-10-18](evals/2026-10-18/README.es.md). Algunas notas para interpretar los informes:

- En `speak`, la mayoría de los fallos corresponden a líneas en las que su nombre significa otra cosa, como un cine o un cachorro, o en las que alguien cuenta a otra persona lo que dijo. Un nombre cuenta como llamada, y el modelo rara vez anula esa decisión.
- En `persona`, un empate significa que el juez eligió las dos veces la respuesta que aparecía en primer (o en segundo) lugar. Los veredictos publicados son de Claude Opus 5.5. Este evaluó fuera de `personagent eval`, por lotes, como registra el campo `rejudged` de cada informe. El campo `earlier` de cada par conserva el veredicto del primer juez, Claude Haiku 5.5.
- En `learning`, la fila de política y las filas de sondeo responden a preguntas distintas. La fila de política pregunta si la regla promovió las correcciones adecuadas. Las filas de sondeo preguntan si una corrección promovida cambió una respuesta posterior. La fila de sondeo `not_promoted` representa el nivel de ruido, ya que nada de su prompt cambió.

## Cómo funciona

![Arquitectura: un mensaje de chat de grupo pasa por Decidir, Construir el prompt, Modelo y Comprobar, y la respuesta vuelve a través del conector; si el bot guarda silencio, no se envía nada. Las reacciones se evalúan y se guardan en un registro de evidencias, y solo lo que aprueba la promoción llega a los ejemplos que lee el prompt](persona_llm_agent_architecture.svg)

Todas las plataformas acceden a través de un único endpoint. Cada mensaje se autentica, se deduplica y se enriquece, es decir, se describen las imágenes y se expanden los enlaces. A continuación se ejecuta el paso de decisión. Si se dirigieron al bot, responde. En caso contrario, espera a que haya suficiente conversación (30 mensajes de forma predeterminada), y una llamada de filtro económica a `LLM_JUDGE_MODEL` decide si una persona intervendría. Una ráfaga de mensajes recibe una sola respuesta, dirigida a la última línea. Cuando varias personas se dirigen a él durante la misma breve espera, una sola respuesta contesta a todas, y su @ se dirige a la última que lo llamó. Un mensaje largo que se dirige a él llega completo al modelo, hasta 1000 caracteres. Un mensaje de grupo que llega más de 10 minutos después de enviarse, dentro de los dos minutos siguientes al primer mensaje de su plataforma desde que se inició personagent, es un mensaje acumulado: se conserva como contexto y no se responde. Pasados esos dos minutos, una marca de tiempo antigua ya no retiene un mensaje, de modo que se sigue respondiendo a un conector cuyo reloj va atrasado. Entre las 02:00 y las 07:00 casi nunca interviene, salvo que se dirijan a él.

Antes de una respuesta, una llamada al juez puede decidir si conviene buscar algo en la web. Que esa llamada se realice depende solo del mensaje; la llamada en sí también lee las tres líneas del chat anteriores al mensaje, de modo que «¿qué te parece?» se busca según aquello a lo que se refiere.

El prompt combina el perfil, las entradas coincidentes del lorebook, la memoria de esta conversación (consulte [Memoria](#memoria)) y los ejemplos más pertinentes. El modelo responde en JSON con `reasoning`, `intent`, `reply` y `mem`. La respuesta pasa por el filtro de salida y la política del personaje y, a continuación, se divide en mensajes del tamaño adecuado para un chat. La política del personaje retiene una respuesta en la que el personaje dice, en cualquiera de los diez idiomas de chat, que es un modelo o un asistente creado por un fabricante de modelos, como «Soy ChatGPT» o «Soy un asistente creado por OpenAI». Los signos del zodiaco, las palabras y los nombres que simplemente contienen el nombre de un fabricante, y las frases sobre el producto de terceros, pasan. Una respuesta larga se divide al final de las frases, nunca después de un título o una abreviatura como Dr. o z.B., ni después del número de una fecha, como en «am 2. Januar». Una lista numerada solo pierde sus números cuando cuenta 1, 2, 3, de modo que las líneas que empiezan por fechas los conservan. Una respuesta con formato incorrecto falla de forma segura, por lo que no se envía nada.

El aprendizaje funciona junto a ese flujo, nunca dentro de él, y guarda su estado en archivos sencillos en `runtime/`, dentro de la carpeta de inicio. Las reacciones se guardan en un registro de evidencias que nunca se reescribe. Su evaluación produce candidatos, y la política de promoción decide qué candidatos pueden cambiar las respuestas. Cuando ninguna reacción adicional puede resolver un candidato, el personaje lo decide con una llamada al modelo y anota su motivo en el registro. Los candidatos promovidos se escriben en pequeños archivos de vista que la recuperación vuelve a cargar sin reiniciar. No se ajusta ningún modelo. El personaje aprende mejorando los ejemplos de su prompt. Como los registros son de solo adición, la pregunta «¿por qué habla así?» siempre tiene respuesta, y una reversión siempre tiene algo que deshacer.

## Privacidad y consentimiento

Todo lo que personagent guarda permanece en su equipo, en la carpeta de inicio: `.env` con sus claves, `persona.txt`, `persona.card.json`, `runtime/`, y `platforms/` con las credenciales de las plataformas. En un clon, ninguno de estos archivos se confirma en Git. Pueden contener credenciales y conversaciones reales, por lo que debe hacer copias de seguridad y mantenerlos en privado. Los mensajes recientes de cada chat se conservan en `runtime/recent.json` durante 72 horas, salvo con `MEMORY_KEEP_RECENT=false`, y lo que el personaje elimina de la memoria sigue pudiendo restaurarse en `runtime/memory_trash.jsonl` durante un máximo de 30 días. La página local nunca guarda la clave en el almacenamiento del navegador.

La vista [Actividad](#actividad) forma parte de la página local, que solo escucha en 127.0.0.1. La API del servicio en la que se basa solo responde a solicitudes que incluyan el token de `runtime/dashboard.token`, un archivo que solo puede leer su usuario. `CONNECTOR_TOKEN` no da acceso a ella. La vista nunca muestra claves de API ni tokens. `DASHBOARD_ENABLED=false` la desactiva.

Como máximo una vez al día, la página local, `personagent up` y `personagent doctor` consultan a pypi.org el número de la versión más reciente. La solicitud incluye la versión de personagent y nada más. `UPDATE_CHECK_ENABLED=false` la desactiva.

El proveedor de modelos ve las conversaciones:

- El contexto del chat se envía a su `LLM_BASE_URL`.
- Si configura un modelo de respaldo (`LLM_FALLBACK_MODEL`, `LLM_FALLBACK_BASE_URL`), también se le llama en los turnos normales para el filtro de respuesta, las decisiones de búsqueda, la evaluación de reacciones, la autoevaluación y el etiquetado de stickers, y también recibe contexto del chat.
- La consolidación de la memoria envía los mensajes recientes de un chat y las notas de ese chat al modelo juez (`LLM_JUDGE_MODEL`), nunca los de otro chat. `MEMORY_CALLS_PER_DAY=0` la desactiva.
- Cuando el propio personaje decide sobre un elemento aprendido, la respuesta, las reacciones a ella y las redacciones candidatas se envían a `PROMOTE_JUDGE_MODEL` (vacío: `REACT_MODEL`). `PROMOTE_JUDGE_ENABLED=false` lo desactiva.
- Las imágenes se envían al endpoint de visión.
- Cuando el modelo decide buscar algo, la consulta se envía a Tavily (si `TAVILY_API_KEY` está definido) o a DuckDuckGo.
- Con `EMBEDDING_MODEL` definido, el mensaje que se responde, las memorias y los ejemplos de recuperación se envían al endpoint de embeddings (`EMBEDDING_BASE_URL`, o `LLM_BASE_URL` si está vacío).

Antes de conectarlo con personas reales, infórmeles de que es un bot y obtenga su consentimiento para tratar sus mensajes. Lea el [aviso legal](DISCLAIMER.es.md).

## Solución de problemas

**Empiece por la comprobación de estado.** En la página local, abra **Aplicación** y seleccione **Iniciar la comprobación**. La vista indica cada servicio que no funciona, por qué no se pudo iniciar el personaje o una plataforma y qué ajustes requieren atención, y **Registros** muestra cada registro sin necesidad de abrir ningún archivo. Consulte [La vista Aplicación](#la-vista-aplicación).

**En un terminal, ejecute `personagent doctor`.** Comprueba la configuración e indica los ajustes mal escritos o con un nombre antiguo. A continuación, sondea cada servicio del que depende personagent. Los sondeos envían solicitudes mínimas y pueden consumir algo de crédito. `--json` imprime los mismos resultados en JSON. `--fix` cambia el nombre de los ajustes retirados en la versión 1.0 y guarda el archivo anterior como `.env.bak`.

**Una plataforma no se conecta.** Cuando la plataforma rechaza las credenciales, la página indica el motivo, y también lo hace `personagent connect <plataforma>` en un terminal. Compruébelas en la consola de la plataforma y, en Discord, confirme que Message Content Intent está activado. Puede solicitar un código QR nuevo cuando caduque y volver a intentar una descarga fallida de AstrBot. **Conexiones con plataformas**, en la vista **Aplicación**, muestra el estado de cada plataforma que personagent conecta por sí mismo. Los registros de todo lo que iniciaron la página o `personagent up` se encuentran en `runtime/desktop/` de la carpeta de inicio, y la vista **Aplicación** los muestra en **Registros**.

**Se ejecuta pero nunca responde.** Las tres causas más habituales son:

1. El agente está desactivado. En ese caso, el aviso de `personagent run` indica `OFF` y la causa, normalmente la falta de `LLM_API_KEY`. Defina la clave en la página local o ejecute `personagent init`.
2. No llega ningún mensaje. En el equipo que ejecuta la página local, abra [Actividad](#actividad) y busque el chat. En un servidor, mencione al bot por su nombre y revise el registro del servicio: anota cada respuesta y cada chat que rechaza. Si no ha llegado ningún mensaje, el conector no los reenvía o no consigue llegar a personagent. En QQ, compruebe en el propio QQ qué mensajes de grupo recibe el bot. Con un AstrBot que ejecute usted, el complemento solo reenvía los `groups` y `dm_users` que enumera, y para NapCat, `aiocqhttp` no debe figurar en sus `excluded_platforms`. Revise también el `personagent_url` del complemento y que `CONNECTOR_TOKEN` coincida en ambos lados.
3. Nadie se dirigió a él. Diríjase a él por su nombre (`PERSONA_NAME`, que debe coincidir como palabra completa). En un grupo, solo se plantea intervenir después de `CHAT_TRIGGER_COUNT` mensajes (30), y solo cuando el filtro determina que una persona lo haría.

La guía de despliegue incluye [la lista completa](deploy.es.md#si-el-bot-deja-de-responder).

**¿Está en ejecución?** `curl http://127.0.0.1:8080/health` responde sin llamar a ningún modelo. `/health/details` también sondea los servicios y exige una cabecera `X-Personagent-Token` cuando hay un token configurado.

**No se inicia.** `personagent run` se detiene con una frase que indica el motivo. Los motivos habituales son un puerto ya en uso, otro personagent en ejecución desde la misma carpeta de inicio, una dirección de red definida sin `CONNECTOR_TOKEN`, un ajuste retirado en la versión 1.0 que sigue definido, o un archivo de memoria dañado, en cuyo caso la frase indica la copia fechada que debe ponerse en su lugar. Los ajustes retirados se enumeran uno por línea como `OLD -> NEW`, y `personagent doctor --fix` les cambia el nombre, al igual que **Cambiar el nombre de los ajustes** en la vista **Aplicación**. Si falla el personaje iniciado desde la página, la vista **Aplicación** indica qué componente ha fallado y muestra su última línea de registro. La página y `personagent up` eligen un puerto libre cuando el 8080 está ocupado.

**Un ajuste no surte efecto.** Reinicie el proceso que lo lee, compruebe la ortografía y guarde `.env` como UTF-8 sin BOM. Las variables de entorno del shell tienen prioridad sobre `.env`. Los valores booleanos son `true` o `false`. `PERSONA_TZ_OFFSET_HOURS` define la zona horaria del personaje: la franja nocturna y las fechas de lo que recuerda se rigen por ella. Cuando está vacío (valor predeterminado), personagent utiliza UTC+8 con `AGENT_LANG=zh` o `zh-TW`, y la zona horaria de este equipo en los demás casos. Indique un número para elegir otro desfase.

## Actualizar desde 0.x

La versión 1.0 cambió el nombre de la mayoría de los ajustes, y personagent no se inicia mientras siga definido un nombre antiguo. Enumera cada uno como `OLD -> NEW`, y `personagent doctor --fix` les cambia el nombre en `.env`. [Upgrading from 0.4](../CHANGELOG.md#upgrading-from-04), en el registro de cambios, enumera todos los pasos. La memoria y lo aprendido se conservan.

## Estado y otros documentos

personagent 1.4.2 está disponible en PyPI. La CI ejecuta las pruebas en Linux con Python 3.10–3.14 y en Windows con Python 3.12. Otros trabajos de CI instalan el paquete, utilizan el comando y la página local, y abren la ventana de la aplicación en Linux, macOS y Windows.

La vía directa de OneBot (`/v1/onebot`) está obsoleta, pero se mantiene durante la serie 1.x. Los scripts de `tools/` están diseñados para ejecutarse desde un clon, y [tools.md](tools.es.md) los describe.

- [Primeros pasos](start.es.md) · [Guía de despliegue](deploy.es.md) · [Guía paso a paso en chino (QQ por escaneo y solución de problemas)](deploy.zh-CN.md)
- Conectores: [complemento de AstrBot](../integrations/astrbot/astrbot_plugin_personagent/README.es.md) · [Satori](../integrations/satori/README.es.md) · [Matrix](../integrations/matrix/README.es.md) · [protocolo](connectors.es.md)
- [Todos los ajustes](../.env.example) · [Registro de cambios](../CHANGELOG.md) · [Contribuir](../.github/CONTRIBUTING.md) · [Política de seguridad](../.github/SECURITY.md)
