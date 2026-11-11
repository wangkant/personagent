# Primeros pasos con personagent

[English](start.md) · [简体中文](start.zh-CN.md) · [繁體中文](start.zh-TW.md) · [日本語](start.ja.md) · [한국어](start.ko.md) · Español · [Français](start.fr.md) · [Deutsch](start.de.md) · [Português (Brasil)](start.pt-BR.md) · [Русский](start.ru.md) · [Guía completa](guide.es.md)

## Abrir personagent

Instale personagent desde PyPI y ábralo:

```sh
python -m pip install personagent
personagent
```

Con [uv](https://docs.astral.sh/uv/), `uvx personagent` lo ejecuta sin un paso de instalación independiente.

En Windows, la página se abre en una ventana propia. En macOS y Linux se abre en su navegador; `pip install "personagent[app]"` le proporciona también allí una ventana propia.

Un asistente de programación puede realizar la configuración por usted: pídale que lea [setup-for-agents.md](setup-for-agents.md) y configure personagent.

En Windows también puede descargar el archivo ZIP del código fuente, descomprimirlo y hacer doble clic en `start.bat`. Este crea su propio entorno de Python en la carpeta y abre la misma página. La primera vez, también coloca un icono de personagent en su escritorio y en el menú Inicio.

Para ejecutarlo desde un clon, asígnele un entorno virtual propio: `python -m venv .venv`, a continuación `.venv/bin/python -m pip install -e .` y `.venv/bin/python -m persona_agent`. En Windows, el intérprete es `.venv\Scripts\python.exe`; también puede hacer doble clic en `start.bat`.

## Añadir una clave y chatear

Elija un servicio de modelos, pegue su clave de API y seleccione **Verificar e iniciar el chat**. De forma predeterminada están seleccionados los modelos gratuitos de OpenRouter y el personaje del oyente cercano. La clave es gratuita y el límite es de 50 solicitudes al día. **Ajustes avanzados** contiene el nombre del modelo y la dirección de la API, y **Elegir un nombre o una personalidad** contiene el nombre y la personalidad del personaje.

La clave permanece en su equipo; seleccione **Mostrar** para comprobarla. Los mensajes del chat se envían al servicio de modelos que usted elija, con las tarifas habituales de dicho servicio.

El personaje responde en la página, con stickers e imágenes cuando los envía. Los mensajes que envía más tarde, como uno que inicia por su cuenta, aparecen en el chat en pocos segundos. Los ajustes se guardan, por lo que el siguiente inicio abre directamente el chat.

Una vez configurado, **Personaje y ajustes** contiene un cuadro **Perfil** con el texto en el que se basa el personaje. Modifique quién es y cómo habla, y seleccione **Guardar el perfil**. El cambio se aplica de inmediato y se conserva lo que el personaje ha aprendido.

Debajo, **Más funciones** activa la búsqueda web, la comprensión de imágenes y el inicio de conversaciones por iniciativa propia. La búsqueda utiliza DuckDuckGo de forma predeterminada; una clave de Tavily la hace más fiable. Más abajo, **Ajustes avanzados** reúne los ajustes que antes solo estaban disponibles en `.env`. Hasta que conecte una plataforma, la vista **Chat** muestra una breve barra de primeros pasos.

Hay otras dos vistas que no requieren conectar ninguna plataforma. **Práctica** reproduce una demostración guionizada y ofrece un chat de grupo de práctica, donde puede ver por qué el personaje responde o guarda silencio. **Aplicación** comprueba todos los servicios de los que depende el personaje, muestra los registros y reúne las actualizaciones, las copias de seguridad y el icono de escritorio.

**Actividad** muestra los chats en los que participa el personaje, lo que ha dicho recientemente, lo que recuerda y lo que ha aprendido. El personaje decide por sí mismo qué aprende y mantiene su memoria actualizada; nada de ello queda pendiente de usted. Aun así, puede deshacer cualquier cosa que haya aprendido, y olvidar o restaurar cualquier cosa que recuerde.

## Llevar el personaje a otras plataformas

1. Seleccione **Conectar plataformas** y elija una plataforma. Una vez conectada, el personaje responde en los grupos y los chats privados de esa plataforma.
   - **Escanear para conectar**: QQ y WeChat personal. Seleccione **Obtener un código QR** y confirme en su teléfono.
     - QQ: escanee con QQ para móvil. QQ crea un bot o le permite elegir uno que ya tenga, y personagent obtiene sus claves. Si creó el bot usted mismo en la [página de bots de QQ](https://q.qq.com/qqbot/openclaw/login.html), seleccione **Pegar los valores en su lugar** e introduzca su AppID y su AppSecret.
     - WeChat: escanee con WeChat. El bot solo admite chats individuales, porque WeChat no transmite los mensajes de grupo a estos bots.
   - **Pegar uno o dos valores**: Telegram (un token de @BotFather), Discord (un token de bot, con Message Content Intent activado), KOOK, Feishu, DingTalk, Slack, bot de IA de WeCom, Mattermost, Misskey, Matrix, Twitch, IRC, Zulip, VK y Stoat. La página indica qué valores debe copiar de la consola de la plataforma. Todo lo demás utiliza valores predeterminados. Twitch, además, le solicita que apruebe un inicio de sesión mediante un enlace.
   - **Avanzado**: las aplicaciones de WeCom, las cuentas oficiales de WeChat y los webhooks de QQ requieren una dirección pública que reenvíe a su puerto de callback. OneBot v11 (NapCat) y Satori requieren otro software en ejecución en este equipo.
2. personagent conecta por sí mismo QQ, WeChat, Telegram, Discord, Matrix, Twitch, IRC, Zulip, VK y Stoat. Las demás plataformas utilizan AstrBot, un puente de terceros. La primera vez que conecte una de ellas, personagent descargará AstrBot con un entorno de Python 3.12 independiente, por lo que debe mantener la página abierta hasta que finalice. A continuación, AstrBot se ejecuta en segundo plano, sin ningún panel en el que iniciar sesión.
3. personagent comprueba las credenciales con la plataforma antes de guardarlas. Si la plataforma las rechaza, la página se lo indica y no se guarda nada.
4. Las plataformas conectadas aparecen en la parte superior de **Conectar plataformas**, donde puede volver a configurarlas o desconectarlas.
5. Sin la página, por ejemplo en un servidor sin pantalla, `personagent connect <plataforma>` conecta QQ, WeChat, Telegram, Discord, Matrix, Twitch, IRC, Zulip, VK o Stoat desde el terminal, con los mismos pasos y comprobaciones. `personagent connect` por sí solo las enumera. La [guía completa](guide.es.md#conectar-una-plataforma-en-el-terminal) describe el comando.

Para encontrar un bot de QQ, abra QQ para móvil y vaya a Contactos → Bots. Puede chatear con él en privado o añadirlo a un grupo del que sea propietario. Esta vía utiliza la plataforma oficial de bots de QQ, por lo que no necesita una cuenta personal de QQ ni software adicional. QQ determina dónde puede participar el bot. Hasta que el bot esté certificado, solo puede unirse a grupos de los que su administrador sea propietario, y no es necesario configurar ningún entorno de pruebas. En un grupo, solo ve los mensajes que lo mencionan con @, salvo que el propietario del grupo active la recepción de todos los mensajes en el perfil del bot en ese grupo. La [guía de bots de QQ](https://bot.q.qq.com/wiki/bot_new_product-intro/) describe la certificación y el resto de la configuración de la cuenta.

Si un código QR caduca, solicite otro. Si falla una descarga, vuelva a intentarla sin repetir la configuración del modelo. Conectar una plataforma abre al personaje únicamente los grupos y los chats privados de esa plataforma; los demás adaptadores mantienen sus listas de permitidos. LINE no está disponible, porque AstrBot solo recibe las llamadas de LINE a través de su panel, que personagent no ejecuta.

## La próxima vez

Vuelva a abrir personagent. Los ajustes se conservan y las plataformas conectadas se reanudan automáticamente. Si ya está en ejecución, al abrirlo de nuevo se vuelve a mostrar su ventana. Manténgalo abierto mientras lo utilice: los procesos que inició se detienen con él, tanto si selecciona **Salir** como si cierra la ventana, y los procesos que deje un fallo se detienen en el siguiente inicio. En Windows, `personagent shortcut` coloca en su escritorio y en el menú Inicio un icono que lo abre sin terminal. También en Windows, **Ejecución en segundo plano**, en la vista **Aplicación**, permite que personagent siga en ejecución al cerrar la ventana, con un icono en el área de notificación, de modo que el personaje continúa respondiendo.

Cuando hay una versión más reciente en PyPI, la vista **Chat** muestra un aviso con un enlace a las notas de la versión y el comando de actualización correspondiente a la forma en que se instaló esta copia. Una copia descomprimida del archivo ZIP del código fuente recibe, en su lugar, un enlace para descargar el nuevo código desde la página de versiones. En la mayoría de las instalaciones, **Actualizar y volver a abrir**, en la vista **Aplicación**, instala la actualización. personagent consulta pypi.org como máximo una vez al día, y la solicitud solo incluye su número de versión. Defina `UPDATE_CHECK_ENABLED=false` en `.env` para desactivar la comprobación.

Si prefiere la línea de comandos, utilice `personagent start --terminal`, `personagent init --terminal`, `personagent up` o los comandos `chat`, `demo` (no requiere clave), `run` y `connect`. Estos conservan su `.env`, su perfil editado y los recuerdos aprendidos. La [guía completa](guide.es.md) describe las demás plataformas.
