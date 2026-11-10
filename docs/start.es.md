# Empezar a usar personagent

[English](start.md) · [简体中文](start.zh-CN.md) · [繁體中文](start.zh-TW.md) · [日本語](start.ja.md) · [한국어](start.ko.md) · Español · [Français](start.fr.md) · [Deutsch](start.de.md) · [Português (Brasil)](start.pt-BR.md) · [Русский](start.ru.md) · [Guía completa](guide.es.md)

## Ábrelo

Instala personagent desde PyPI y ábrelo:

```sh
python -m pip install personagent
personagent
```

Con [uv](https://docs.astral.sh/uv/), `uvx personagent` lo ejecuta sin un paso de instalación aparte.

En Windows la página se abre en una ventana propia. En macOS y Linux se abre en tu navegador; `pip install "personagent[app]"` le da también allí una ventana.

Un agente de programación puede hacer la configuración por ti: pídele que lea [setup-for-agents.md](setup-for-agents.md) y configure personagent.

En Windows también puedes descargar el ZIP del código fuente, descomprimirlo y hacer doble clic en `start.bat`. Crea su propio entorno de Python en la carpeta y abre la misma página. La primera vez, también pone un icono de personagent en tu escritorio y en el menú Inicio.

Para ejecutarlo desde un clon, dale un venv propio: `python -m venv .venv`, luego `.venv/bin/python -m pip install -e .` y `.venv/bin/python -m persona_agent`. En Windows el intérprete es `.venv\Scripts\python.exe`, o puedes hacer doble clic en `start.bat`.

## Añade una clave y chatea

Elige un servicio de modelos, pega su clave de API y haz clic en **Verificar y empezar a chatear**. Al principio están seleccionados los modelos gratuitos de OpenRouter y el personaje del buen oyente. La clave es gratuita y el límite es de 50 solicitudes al día. **Ajustes avanzados** contiene el nombre del modelo y la dirección de la API, y **Elige un nombre o una personalidad** contiene el nombre y la personalidad del personaje.

La clave se queda en tu ordenador; haz clic en **Mostrar** para comprobarla. Los mensajes del chat van al servicio de modelos que elijas, con las tarifas habituales de ese servicio.

Tu personaje responde en la página. Tus ajustes se guardan, así que el siguiente inicio va directo al chat.

Una vez configurado, **Personaje y ajustes** tiene un cuadro **Perfil del personaje** con el texto en el que se basa el personaje. Reescribe quién es y cómo habla, y haz clic en **Guardar perfil**. El cambio se aplica al instante y lo que el personaje ha aprendido se conserva.

Debajo, **Más funciones** activa la búsqueda web, la comprensión de imágenes y hablar primero. La búsqueda usa DuckDuckGo de forma predeterminada; una clave de Tavily la hace más fiable. Hasta que conectes una aplicación, la vista **Chat** muestra una barra breve de primeros pasos.

## Llévalo a otras aplicaciones

1. Haz clic en **Conectar apps** y elige una aplicación. Una vez conectada, tu personaje responde en los grupos y mensajes directos de esa aplicación.
   - **Escanear para conectar**: QQ y WeChat personal. Haz clic en **Obtener un código QR** y confirma en tu teléfono.
     - QQ: escanea con QQ para móvil. QQ crea un bot o te deja elegir uno que ya tengas, y personagent obtiene sus claves. Si creaste el bot tú en la [página de bots de QQ](https://q.qq.com/qqbot/openclaw/login.html), haz clic en **Pegar valores en su lugar** e introduce su AppID y AppSecret.
     - WeChat: escanea con WeChat. El bot solo chatea de uno a uno, porque WeChat no pasa los mensajes de grupo a estos bots.
   - **Pegar uno o dos valores**: Telegram (un token de @BotFather), Discord (un token de bot, con Message Content Intent activado), KOOK, Feishu, DingTalk, Slack, bot de IA de WeCom, Mattermost y Misskey. La página te indica qué valores copiar de la consola de la aplicación. Todo lo demás usa valores predeterminados.
   - **Avanzado**: las aplicaciones de WeCom, las cuentas oficiales de WeChat y los webhooks de QQ necesitan una dirección pública que reenvíe a su puerto de callback. OneBot v11 (NapCat) y Satori necesitan otro software en ejecución en este ordenador.
2. personagent conecta QQ, WeChat, Telegram y Discord por sí mismo. Las demás aplicaciones pasan por AstrBot, un puente de terceros. La primera vez que conectas una de ellas, personagent descarga AstrBot con un entorno de Python 3.12 aparte, así que mantén la página abierta hasta que termine. Después AstrBot se ejecuta en segundo plano, sin panel en el que iniciar sesión.
3. personagent comprueba las credenciales con la aplicación antes de guardarlas. Si la aplicación las rechaza, la página te lo dice y no se guarda nada.
4. Las aplicaciones conectadas aparecen en la parte superior de **Conectar apps**, donde puedes volver a configurarlas o desconectarlas.

Para encontrar un bot de QQ, abre QQ para móvil y ve a Contactos → Bots. Chatea con él en privado o añádelo a un grupo que sea tuyo. Esta vía usa la plataforma oficial de bots de QQ, así que no necesitas una cuenta personal de QQ ni software adicional. QQ decide adónde puede ir el bot. Hasta que el bot esté certificado, solo puede unirse a grupos de los que su administrador sea propietario, y no hay ningún entorno de pruebas que configurar. En un grupo solo ve los mensajes que lo mencionan con @, salvo que el propietario del grupo active recibir todos los mensajes en el perfil del bot en ese grupo. La [guía de bots de QQ](https://bot.q.qq.com/wiki/bot_new_product-intro/) cubre la certificación y el resto de la parte de la cuenta.

Si un código QR caduca, pide otro. Si falla una descarga, reinténtala sin repetir la configuración del modelo. Conectar una aplicación abre al personaje solo los grupos y mensajes directos de esa aplicación; los demás adaptadores mantienen sus listas de permitidos. LINE no se ofrece, porque AstrBot solo recibe las llamadas de LINE a través de su panel, que personagent no ejecuta.

## La próxima vez

Vuelve a abrir personagent. Tus ajustes se conservan y las aplicaciones conectadas se reanudan solas. Si ya está en marcha, abrirlo de nuevo vuelve a mostrar su ventana. Mantenla abierta mientras lo uses: los procesos que inició se detienen con él, tanto si haces clic en **Salir** como si cierras la ventana, y lo que deje un fallo se detiene en el siguiente inicio. En Windows, `personagent shortcut` pone un icono en tu escritorio y en el menú Inicio que lo abre sin terminal.

Cuando hay una versión más reciente en PyPI, la vista **Chat** muestra un aviso con un enlace a las notas de la versión y el comando de actualización según cómo se instaló esta copia. Una copia descomprimida del ZIP del código fuente recibe en su lugar un enlace para descargar el nuevo código desde la página de versiones. personagent consulta pypi.org como máximo una vez al día, y la solicitud solo lleva su número de versión. Define `UPDATE_CHECK_ENABLED=false` en `.env` para desactivar la comprobación.

Si prefieres la línea de comandos, usa `personagent start --terminal`, `personagent init --terminal`, `personagent up` o los comandos `chat`, `demo` (no necesita clave), `run` y `connect`. Conservan tu `.env`, tu persona editada y los recuerdos aprendidos. La [guía completa](guide.es.md) cubre las demás plataformas.
