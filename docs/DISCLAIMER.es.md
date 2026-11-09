# Aviso legal

[English](DISCLAIMER.md) · [简体中文](DISCLAIMER.zh-CN.md) · [繁體中文](DISCLAIMER.zh-TW.md) · [日本語](DISCLAIMER.ja.md) · [한국어](DISCLAIMER.ko.md) · Español · [Français](DISCLAIMER.fr.md) · [Deutsch](DISCLAIMER.de.md) · [Português (Brasil)](DISCLAIMER.pt-BR.md) · [Русский](DISCLAIMER.ru.md)

personagent es software libre bajo la [licencia MIT](../LICENSE). Pone un personaje de IA en tus chats, y quien lo ejecuta eres tú. Eres responsable de lo que dice, de dónde lo dice y de qué cuentas usa. Esta página no es asesoramiento legal.

## Plataformas de chat y tus cuentas

personagent llega a una plataforma de chat de dos maneras. Conecta por sí mismo los bots oficiales de QQ, WeChat personal, Telegram y Discord. Cualquier otra plataforma pasa por un puente de terceros, normalmente el AstrBot que personagent descarga y ejecuta por ti. Tu riesgo depende de cómo inicia sesión la conexión.

- **Las API oficiales de bots** están hechas para bots. Incluyen la API oficial de bots de QQ, la API de bots iLink de Tencent para WeChat personal, Telegram, Discord, Slack, KOOK, Feishu/Lark, DingTalk, WeCom y plataformas similares. Aun así debes cumplir las condiciones para desarrolladores y los límites de frecuencia de cada plataforma.
- **Los clientes no oficiales** inician sesión como una cuenta de usuario normal y la manejan con software. La plataforma no lo autoriza y puede prohibirlo en sus condiciones. Puede restringir, congelar o cerrar la cuenta para siempre. Esto abarca:
  - **QQ a través de NapCat, LLOneBot, Lagrange o cualquier otra implementación de OneBot**, que es la opción avanzada OneBot v11. Un bot oficial de QQ no necesita ninguno de ellos. Tencent no los autoriza, y el riesgo es máximo desde direcciones IP en la nube o en el extranjero.
  - **WhatsApp, Signal, Messenger, Instagram, Google Messages y otros a través de un puente mautrix**, que es como el conector de Matrix llega a ellos. El puente es un cliente no oficial de cada red, y algunas de estas redes regulan la mensajería automatizada en sus condiciones. Consulta [las notas del conector de Matrix](../integrations/matrix/README.es.md#condiciones-de-cada-red).
  - Cualquier otra cosa que inicie sesión como una persona.

Si usas alguno de estos, usa una cuenta dedicada que puedas permitirte perder, nunca la principal. Siempre que puedas, ejecútalo desde una red doméstica y no desde un servidor en la nube. Lee las condiciones vigentes de cada red que conectes. Ni el autor de personagent ni los mantenedores de ningún proyecto de terceros con el que funciona (AstrBot, NapCat, Koishi, mautrix y otros) aceptan responsabilidad por una cuenta perdida o restringida.

## Di a la gente que es un bot

- Di a las personas de un chat que están hablando con una IA, y consigue el acuerdo del propietario o los administradores del grupo antes de añadirlo. Pon a la cuenta un nombre que lo deje claro, y dilo en su perfil si la plataforma lo tiene.
- Cuando alguien pregunta en serio si es una IA, personagent está hecho para decirlo. No edites la persona para que lo niegue.
- No lo uses para hacerte pasar por una persona real, ni para engañar a nadie sobre con quién o con qué está hablando. Algunas plataformas y algunos países exigen identificar a los bots o restringen las cuentas automatizadas. Comprueba las normas que se te aplican.
- Mantenlo fuera de grupos donde sus respuestas puedan dañar o engañar a la gente, como grupos sobre temas médicos, legales, financieros o de crisis, y grupos con menores.
- Si alguien le pide que se vaya, o pregunta qué sabe de él, tómatelo en serio. El administrador puede hacer que olvide una nota (`<name>, forget ...`), y todo lo que guarda está en su carpeta de inicio (ver más abajo).

## Los personajes de ChatGPT, DeepSeek y Claude

Estos tres personajes listos son personificaciones hechas por fans. ChatGPT, DeepSeek y Claude son marcas de OpenAI, DeepSeek y Anthropic, respectivamente. personagent no está afiliado a ninguna de ellas ni cuenta con su respaldo. Los retratos son ilustraciones originales; toman prestado un color o un motivo, como una ballena o una estrella radiante, pero ninguno de los logotipos de las empresas.

El personaje funciona con el servicio de modelos que elijas, no con esos productos, salvo que elijas uno de ellos. Si le preguntan si es el de verdad, dice que no.

## Qué ve tu proveedor de modelos

Cada respuesta envía al proveedor de modelos un prompt formado por la persona, los mensajes recientes del chat (con nombres), las notas que el bot ha guardado sobre el chat y lo que ha recuperado de lo aprendido. Si configuras un modelo de visión, las imágenes van a él. Otros servicios que actives también ven partes de esto. Entre ellos están los endpoints de respaldo, juez, autoevaluación y embeddings que configures, y la búsqueda web, que envía una consulta breve a Tavily si defines una clave y a DuckDuckGo si no. La comprobación de actualizaciones solo envía a pypi.org el número de versión de personagent, como máximo una vez al día; `UPDATE_CHECK_ENABLED=false` la desactiva.

Lee la política de retención de datos de cada proveedor antes de usarlo. Algunos proveedores conservan los prompts, y algunos entrenan con ellos salvo que te excluyas. Los modelos gratuitos de OpenRouter, que son el valor predeterminado, pueden llegar a esos proveedores. Un modelo local (Ollama, llama.cpp) mantiene los prompts en tu máquina. Las personas del chat no aceptaron las condiciones de ningún proveedor, así que diles adónde van sus mensajes.

## Qué guarda en tu máquina

Todo lo que guarda está en su carpeta de inicio. Los ajustes y las claves de API están en `.env`. Las credenciales de los bots y el AstrBot que ejecuta por ti están en `platforms/`. `runtime/` contiene las notas de los chats, las reacciones que evaluó (citadas literalmente), el registro de lo que aprendió y los ejemplos aprendidos. Si defines `SERVER_LOG_FILE`, los registros también pueden contener detalles de las conversaciones. Mantén la carpeta privada. Nunca la publiques ni la adjuntes a una incidencia, y haz una copia de seguridad si te importa lo que ha aprendido. Las leyes sobre guardar y tratar mensajes de otras personas varían según el país, y cumplir las tuyas es responsabilidad tuya.

Puede aprender algo mal. Un cambio necesita dos reacciones coincidentes del mismo chat, al menos una de la persona a la que iba la respuesta. Cada cambio queda en un registro de solo adición, que puedes revisar y deshacer con `personagent learned` o en la vista Actividad de la página local. Revísalo de vez en cuando.

## Sin garantía

El software se proporciona «tal cual», sin garantía de ningún tipo, expresa o implícita. Los autores no son responsables de ninguna reclamación, daño o pérdida derivados de su uso. Consulta la [LICENSE](../LICENSE).
