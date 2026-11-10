# Aviso legal

[English](DISCLAIMER.md) · [简体中文](DISCLAIMER.zh-CN.md) · [繁體中文](DISCLAIMER.zh-TW.md) · [日本語](DISCLAIMER.ja.md) · [한국어](DISCLAIMER.ko.md) · Español · [Français](DISCLAIMER.fr.md) · [Deutsch](DISCLAIMER.de.md) · [Português (Brasil)](DISCLAIMER.pt-BR.md) · [Русский](DISCLAIMER.ru.md)

personagent se publica bajo la [PolyForm Noncommercial License 1.0.0](../LICENSE): su uso, modificación y distribución son gratuitos con fines no comerciales, y no se permiten con fines comerciales. personagent introduce un personaje de IA en sus chats, y es usted quien lo ejecuta. Usted es responsable de lo que dice, de dónde lo dice y de qué cuentas utiliza. Esta página no constituye asesoramiento jurídico.

## Plataformas de chat y sus cuentas

personagent accede a una plataforma de chat de dos maneras. Conecta por sí mismo los bots oficiales de QQ, WeChat personal, Telegram y Discord. Cualquier otra plataforma utiliza un puente de terceros, normalmente el AstrBot que personagent descarga y ejecuta por usted. El riesgo depende de la forma en que la conexión inicia sesión.

- **Las API oficiales de bots** están diseñadas para bots. Incluyen la API oficial de bots de QQ, la API de bots iLink de Tencent para WeChat personal, Telegram, Discord, Slack, KOOK, Feishu/Lark, DingTalk, WeCom y plataformas similares. Aun así, debe cumplir las condiciones para desarrolladores y los límites de frecuencia de cada plataforma.
- **Los clientes no oficiales** inician sesión como una cuenta de usuario normal y la controlan mediante software. La plataforma no lo autoriza y puede prohibirlo en sus condiciones. Puede restringir, congelar o cerrar la cuenta de forma permanente. Esto incluye:
  - **QQ a través de NapCat, LLOneBot, Lagrange o cualquier otra implementación de OneBot**, que corresponde a la opción avanzada OneBot v11. Un bot oficial de QQ no necesita ninguno de ellos. Tencent no los autoriza, y el riesgo es máximo desde direcciones IP en la nube o en el extranjero.
  - **WhatsApp, Signal, Messenger, Instagram, Google Messages y otras redes a través de un puente mautrix**, que es la forma en que el conector de Matrix accede a ellas. El puente es un cliente no oficial de cada red, y algunas de estas redes regulan la mensajería automatizada en sus condiciones. Consulte [las notas del conector de Matrix](../integrations/matrix/README.es.md#condiciones-de-cada-red).
  - Cualquier otro software que inicie sesión como una persona.

Si utiliza alguna de estas opciones, use una cuenta dedicada cuya pérdida pueda asumir, nunca su cuenta principal. Siempre que sea posible, ejecútelo desde una red doméstica y no desde un servidor en la nube. Lea las condiciones vigentes de cada red que conecte. Ni el autor de personagent ni los mantenedores de ningún proyecto de terceros con el que funciona (AstrBot, NapCat, Koishi, mautrix y otros) asumen responsabilidad alguna por una cuenta perdida o restringida.

## Informe a las personas de que es un bot

- Informe a las personas de un chat de que están hablando con una IA, y obtenga el consentimiento del propietario o de los administradores del grupo antes de añadirlo. Asigne a la cuenta un nombre que lo deje claro, e indíquelo en su perfil si la plataforma lo permite.
- Cuando alguien pregunta en serio si es una IA, personagent está diseñado para reconocerlo. No edite el perfil para que lo niegue.
- No lo utilice para suplantar a una persona real ni para engañar a nadie sobre con quién o con qué está hablando. Algunas plataformas y algunos países exigen identificar a los bots o restringen las cuentas automatizadas. Compruebe las normas que le son aplicables.
- Manténgalo fuera de grupos en los que sus respuestas puedan perjudicar o engañar a las personas, como grupos sobre temas médicos, jurídicos, financieros o de crisis, y grupos con menores.
- Si alguien le pide que se retire, o pregunta qué sabe sobre él, atienda la solicitud con seriedad. El administrador puede hacer que olvide una nota (`<name>, forget ...`), y todo lo que guarda se encuentra en su carpeta de inicio (véase más abajo).

## Créditos de los retratos

Los retratos de la chica ballena de DeepSeek, la chica dragón de GPT y la dama Claude se dibujaron para personagent a partir de diseños que la comunidad ya dibuja. La chica ballena deriva de 溟月, un personaje original del creador de Bilibili 上善无形 (CC BY-NC-SA 4.0), con el traje de sirvienta que le asignó ZipZipPipe. La chica dragón se basa en la dragona blanca de ZipZipPipe. La dama Claude se basa en un diseño de la comunidad cuyo primer artista se desconoce. Los retratos tienen su propia licencia, CC BY-NC-SA 4.0: conserve la atribución, no los utilice con fines comerciales y comparta las modificaciones bajo la misma licencia. Consulte `persona_agent/static/characters/LICENSE.md`.

## Qué ve su proveedor de modelos

Cada respuesta envía al proveedor de modelos un prompt formado por el perfil, los mensajes recientes del chat (con nombres), las notas que el bot ha guardado sobre el chat y lo que ha recuperado de lo aprendido. Si configura un modelo de visión, las imágenes se envían a él. Otros servicios que active también ven partes de esta información. Entre ellos se encuentran los endpoints de respaldo, de juez, de autoevaluación y de embeddings que configure, y la búsqueda web, que envía una consulta breve a Tavily si define una clave y a DuckDuckGo en caso contrario. La comprobación de actualizaciones solo envía a pypi.org el número de versión de personagent, como máximo una vez al día; `UPDATE_CHECK_ENABLED=false` la desactiva.

Lea la política de retención de datos de cada proveedor antes de utilizarlo. Algunos proveedores conservan los prompts, y algunos los utilizan para entrenar sus modelos salvo que usted lo rechace expresamente. Los modelos gratuitos de OpenRouter, que son el valor predeterminado, pueden enviar las solicitudes a esos proveedores. Un modelo local (Ollama, llama.cpp) mantiene los prompts en su equipo. Las personas del chat no han aceptado las condiciones de ningún proveedor, por lo que debe informarles de adónde se envían sus mensajes.

## Qué guarda en su equipo

Todo lo que guarda se encuentra en su carpeta de inicio. Los ajustes y las claves de API están en `.env`. Las credenciales de los bots y el AstrBot que ejecuta por usted están en `platforms/`. `runtime/` contiene las notas de los chats, las reacciones que evaluó (citadas literalmente), el registro de lo que aprendió y los ejemplos aprendidos. Si define `SERVER_LOG_FILE`, los registros también pueden contener detalles de las conversaciones. Mantenga la carpeta en privado. No la publique ni la adjunte nunca a una incidencia, y haga una copia de seguridad si le importa lo que ha aprendido. Las leyes sobre el almacenamiento y el tratamiento de mensajes de otras personas varían según el país, y el cumplimiento de las que le sean aplicables es responsabilidad suya.

Puede aprender algo de forma incorrecta. Un cambio requiere dos reacciones coincidentes del mismo chat, al menos una de la persona a la que iba dirigida la respuesta. Cada cambio queda en un registro de solo adición, que puede revisar y deshacer con `personagent learned` o en la vista Actividad de la página local. Revíselo periódicamente.

## Sin garantía

El software se proporciona «tal cual», sin garantía de ningún tipo, expresa o implícita. Los autores no son responsables de ninguna reclamación, daño o pérdida derivados de su uso. Consulte la [LICENSE](../LICENSE).
