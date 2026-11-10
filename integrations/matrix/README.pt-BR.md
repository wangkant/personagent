# Conector Matrix

[English](README.md) · [简体中文](README.zh-CN.md) · [繁體中文](README.zh-TW.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Español](README.es.md) · [Français](README.fr.md) · [Deutsch](README.de.md) · Português (Brasil) · [Русский](README.ru.md)


Este conector coloca o [personagent](https://github.com/wangkant/personagent) em salas Matrix e, pelas [pontes mautrix](https://docs.mau.fi/bridges/), no WhatsApp, Signal, Messenger, Instagram, Google Messages e outras redes. Matrix e as pontes são softwares de terceiros que você mesmo executa. O personagent não precisa deles para as plataformas que conecta pela página local.

O conector é um pequeno processo independente baseado em [matrix-nio](https://github.com/matrix-nio/matrix-nio), que dá suporte a criptografia de ponta a ponta sem libolm. Ele faz login em um homeserver como um usuário Matrix comum, encaminha cada mensagem permitida de uma sala ao `POST /v1/events` do agente como evento neutro de plataforma ([docs/connectors.md](../../docs/connectors.pt-BR.md)) e publica as respostas do agente na sala. Ele também consulta a caixa de saída do agente, então mensagens programadas, perguntas de acompanhamento e desculpas também chegam ao Matrix.

## O que ele faz

Na entrada, para cada mensagem em uma sala permitida:

- O evento usa a plataforma `matrix` e os ids brutos do Matrix, então o agente armazena `matrix:@alex:example.org` e `matrix:!room:example.org`.
- Uma sala conta como chat direto quando o `m.direct` do bot a lista, ou quando ela tem exatamente um membro além do bot e dos usuários em `MATRIX_IGNORE_USERS`. Um chat direto é identificado pela pessoa, e um grupo pela sala. Uma sala nomeada por id em `MATRIX_GROUPS` é sempre um grupo.
- `addressed` é verdadeiro quando a mensagem menciona o bot ou responde a uma mensagem dele. Uma menção é `m.mentions` ou, vinda de clientes antigos demais para enviar `m.mentions`, uma pílula ou o id de usuário do bot no texto.
- Uma resposta traz o remetente e o texto da mensagem citada. O conector os obtém de um cache de eventos recentes ou busca o evento pai. Ele remove o texto alternativo de resposta que clientes antigos colocam no início (`> <@alex:example.org> ...`), então o agente nunca lê as palavras de outra pessoa como se fossem do remetente.
- Imagens e figurinhas de até 4 MB são baixadas, descriptografadas em salas criptografadas e enviadas ao agente como bytes. Mensagens de voz, vídeos e arquivos são descritos em palavras.
- As mensagens de uma sala chegam ao agente na ordem em que foram enviadas. Uma mensagem enviada depois de uma imagem espera a imagem ser baixada. O agente ainda pode trabalhar em vários turnos ao mesmo tempo.
- O carimbo de data/hora é o `origin_server_ts` do homeserver.
- O conector ignora as mensagens do próprio bot, mensagens `m.notice` (o tipo que bots enviam), edições, reações, mensagens de `MATRIX_IGNORE_USERS`, o atraso que a primeira sincronização devolve ao iniciar e tudo o que for mais antigo que `MATRIX_MAX_EVENT_AGE_S`, como o histórico que uma ponte preenche em uma sala nova.

Na saída:

- As respostas de texto são `m.text`. Quando o agente pede para mencionar alguém em um grupo, a resposta começa com uma pílula e lista essa pessoa em `m.mentions`. Todas as outras respostas levam um `m.mentions` vazio, então nenhum cliente transforma um nome no texto em notificação.
- As respostas com imagem são enviadas, e criptografadas em salas criptografadas.
- Um aviso de digitação aparece enquanto o agente trabalha em um turno.
- Uma mensagem em uma thread é respondida nessa thread.
- Depois que o agente assume a conversa, o bot marca a mensagem como lida (`MATRIX_READ_RECEIPTS_ENABLED`). Por uma ponte, isso aparece como a marca de leitura na outra rede.
- As entregas da caixa de saída vão para a sala de onde a conversa veio por último. O `reply_handle` do evento é o id da sala.

## Instalação

Você precisa de um personagent em execução e de uma conta Matrix para o bot. Crie uma conta dedicada em vez de compartilhar com uma pessoa.

O conector é um script neste repositório, então precisa de uma cópia do repositório (um clone ou o ZIP do GitHub) e de um ambiente Python próprio, porque `matrix-nio` não é dependência do personagent. Em um clone que já tem o `.venv` do personagent, instale nesse ambiente:

```bash
.venv/bin/python -m pip install -r integrations/matrix/requirements.txt
```

Se você instalou o personagent do PyPI com pip, ou o executa com uvx, crie um venv separado ao lado da cópia:

```bash
python -m venv connector-venv
connector-venv/bin/python -m pip install -r integrations/matrix/requirements.txt
```

No Windows, o interpretador é `.venv\Scripts\python.exe` ou `connector-venv\Scripts\python.exe`. Em seguida, copie o arquivo de configurações:

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

Depois inicie o conector ao lado do agente, com o mesmo interpretador:

```bash
.venv/bin/python integrations/matrix/matrix_connector.py
# or: .venv/bin/python integrations/matrix/matrix_connector.py --config /path/to/matrix.env
```

Convide o bot para uma sala listada em `MATRIX_GROUPS`, e ele entra. No Element, o id da sala fica nas configurações da sala, em Avançado.

### Login

O login com senha é a forma mais fácil de começar. O conector salva a sessão que obtém (id de usuário, id de dispositivo e token de acesso) em `MATRIX_STORE_DIR/session.json` e a reutiliza na próxima inicialização, então reiniciar não cria um dispositivo novo. Apague esse arquivo para fazer login de novo.

Para usar um token de acesso existente, defina `MATRIX_ACCESS_TOKEN`. O conector pergunta ao homeserver de qual conta é o token. Não use o token de uma sessão que você mesmo usa, porque sair dessa sessão também desconecta o bot.

Quando o homeserver desconecta o bot (`M_UNKNOWN_TOKEN`), o conector para com um erro que diz isso. Depois de um login com senha, iniciá-lo de novo faz login outra vez. Com `MATRIX_ACCESS_TOKEN`, defina primeiro um token novo. Qualquer outra sincronização com falha é tentada de novo após uma espera que dobra até um minuto.

### Onde o agente pode rodar

O protocolo define a regra. `PERSONAGENT_URL` precisa ser um endereço de loopback, ou HTTPS com `CONNECTOR_TOKEN` igual ao `CONNECTOR_TOKEN` do agente. Caso contrário, o conector se recusa a iniciar. Defina o token nos dois lados antes de colocar qualquer proxy ou túnel na frente do agente, mesmo em um único host.

## Configurações

[.env.example](.env.example) lista todas as configurações. As listas são separadas por vírgulas e aceitam curingas, então `@*:example.org` corresponde a um servidor inteiro. Uma lista vazia não responde a ninguém. Um `*` sozinho corresponde a todos e marca o evento com `prefiltered: false`. Então decidem sozinhos `ACCESS_GROUPS` / `ACCESS_DM_USERS` do próprio agente, e uma plataforma sem entradas ali é recusada.

| Configuração | Significado |
|---|---|
| `MATRIX_GROUPS` | Salas de grupo em que responder, por id de sala. `*` significa todas as salas em que o bot entrou. |
| `MATRIX_DM_USERS` | Pessoas que podem falar com o bot em um chat direto. `*` significa todos. |
| `MATRIX_INVITE_FROM` | Usuários cujos convites o bot aceita. Convites para salas nomeadas em `MATRIX_GROUPS` e convites de chat direto de `MATRIX_DM_USERS` são sempre aceitos. Os outros ficam pendentes. |
| `MATRIX_IGNORE_USERS` | Nunca recebem resposta e não contam como membros quando o conector distingue um chat direto de um grupo. |
| `MATRIX_E2EE_ENABLED` | Criptografia de ponta a ponta. Veja abaixo. |
| `MATRIX_TIMEOUT_S` | Quanto um turno pode durar. Mantenha acima de 3 × `LLM_TIMEOUT_S` do agente. |
| `MATRIX_OUTBOX_ENABLED` | Consultar a caixa de saída do agente. |

## Pontes: WhatsApp, Signal, Messenger, Instagram e mais

Uma ponte mautrix faz login em outra rede como uma conta dessa rede e espelha os chats dela em salas Matrix chamadas portais. Todos do outro lado aparecem no Matrix como um usuário fantasma, como `@whatsapp_4912345:example.org`. Quando a conta Matrix do bot é a que fez login na ponte, a persona vive nessa rede. Um contato do WhatsApp escreve para o número da persona, a ponte publica a mensagem em uma sala portal, este conector a encaminha e a resposta volta pelo mesmo caminho.

| Rede | Ponte |
|---|---|
| WhatsApp | [mautrix-whatsapp](https://github.com/mautrix/whatsapp) |
| Signal | [mautrix-signal](https://github.com/mautrix/signal) |
| Facebook Messenger, mensagens diretas do Instagram | [mautrix-meta](https://github.com/mautrix/meta) |
| Google Messages (RCS e SMS por um celular Android) | [mautrix-gmessages](https://github.com/mautrix/gmessages) |
| Google Voice, LinkedIn, mensagens diretas do Twitter/X e do Bluesky, Google Chat, Zulip, IRC, iMessage | As outras [pontes mautrix](https://github.com/mautrix) |
| Telegram, Discord, Slack | Existem pontes mautrix, mas estas redes têm APIs oficiais de bots. O personagent conecta o Telegram e o Discord por conta própria, e o Slack pelo AstrBot que a página local executa. |

Para configurar uma:

1. Execute um homeserver que você controla (Synapse ou outro servidor com suporte a serviços de aplicativo) e instale a ponte seguindo [a documentação dela](https://docs.mau.fi/bridges/). Dê à conta do bot o nível de permissão `user` em `permissions` da ponte.
2. Entre no Element como o bot, abra um chat com o bot da ponte (por exemplo, `@whatsappbot:example.org`) e envie `login`. Vincule a conta de rede que a persona vai usar. Para WhatsApp, Signal e Google Messages, escaneie o código QR com o celular da persona. Para Messenger e Instagram, forneça o login da Meta. Veja [Usar pontes](https://docs.mau.fi/bridges/general/using-bridges.html).
3. Deixe o conector entrar nos portais e mantenha de fora as mensagens da própria ponte:

   ```ini
   MATRIX_INVITE_FROM=@whatsappbot:example.org
   MATRIX_IGNORE_USERS=@whatsappbot:example.org,@whatsapp_4900000000:example.org
   MATRIX_DM_USERS=@whatsapp_*:example.org
   MATRIX_GROUPS=!groupPortal:example.org
   ```

   A segunda entrada em `MATRIX_IGNORE_USERS` é o fantasma da ponte para o próprio número da persona. Sem [marionete dupla](https://docs.mau.fi/bridges/general/double-puppeting.html), uma mensagem digitada no celular da persona chega ao Matrix por esse fantasma, e o bot responderia a si mesmo. `MATRIX_GROUPS=*` encaminha todos os portais de grupo em que o bot está, e o personagent então responde só nas salas que o `ACCESS_GROUPS` dele lista como `matrix:!room:server`. Liste ids de sala aqui para escolher as salas no conector.

### Marionetes

- A ponte é um cliente não oficial da rede, conectado como uma conta de usuário normal (um dispositivo vinculado ou uma sessão web). Ela não usa uma API de bots, e nada na rede marca a conta como bot.
- A persona precisa da própria conta, geralmente com o próprio número de telefone, e o celular precisa continuar acessível. O WhatsApp desconecta dispositivos vinculados quando o celular fica offline por cerca de duas semanas, e o Google Messages só funciona enquanto o celular Android está online.
- Em chats em grupo, a conta da persona parece um membro qualquer. Diga às pessoas que elas estão falando com um bot.
- Reações, edições, exclusões, enquetes e chamadas não são encaminhadas ao agente.

### Termos de cada rede

Leia os termos de cada rede antes de conectá-la.

- O [WhatsApp](https://www.whatsapp.com/legal/terms-of-service) inclui o envio automático de mensagens entre as comunicações não permitidas, proíbe o uso não pessoal que não tenha autorizado e pode banir contas que façam qualquer um dos dois. O caminho aprovado para automação é a WhatsApp Business Platform, que uma ponte não usa.
- O [Signal](https://signal.org/legal/) também lista o envio automático de mensagens como não permitido.
- O [Facebook](https://www.facebook.com/terms.php) e o [Instagram](https://help.instagram.com/581066165581870) proíbem o acesso automatizado sem permissão da Meta, e a Meta pode bloquear uma conta que faz login por um cliente que ela não reconhece.
- O Google Messages está sujeito aos [termos do Google](https://policies.google.com/terms) e aos termos da sua operadora para SMS e RCS, que podem cobrar ou restringir mensagens automatizadas.

Use uma conta dedicada que você possa perder, só em conversas em que as pessoas sabem que estão falando com um bot, e leia [DISCLAIMER.md](../../docs/DISCLAIMER.pt-BR.md).

## Criptografia de ponta a ponta

Com `MATRIX_E2EE_ENABLED=false` (o padrão), o bot só lê salas não criptografadas. Em uma sala criptografada, ele registra que não consegue descriptografar a mensagem e nunca envia ali uma resposta em texto puro.

Com `MATRIX_E2EE_ENABLED=true`:

- `MATRIX_STORE_DIR` (por padrão `runtime/` ao lado do script, que o git ignora) guarda as chaves do dispositivo e o token de sincronização. Mantenha este diretório. Se ele se perder, o bot vira um dispositivo novo que não consegue ler nada criptografado antes desse ponto.
- O dispositivo precisa continuar o mesmo entre reinícios. Um login com senha o mantém pela sessão salva. Com um token de acesso, defina `MATRIX_DEVICE_ID` como o dispositivo do token.
- O bot compartilha as chaves com todos os dispositivos da sala, verificados ou não. Ele não consegue se verificar de forma interativa, então as pessoas veem o dispositivo como não verificado. Ele não tem backup de chaves nem assinatura cruzada.
- Uma mensagem cuja chave não chegou é registrada e ignorada, sem nova tentativa.
- Uma ponte mautrix pode criptografar os portais ([criptografia de ponta a ponte](https://docs.mau.fi/bridges/general/end-to-bridge-encryption.html)). A ponte guarda essas chaves no seu servidor, então a proteção termina ali, e a outra rede leva a mensagem sob a própria criptografia. Se a sua ponte criptografa portais, ative `MATRIX_E2EE_ENABLED`.

## Testes

`tests/test_matrix_connector.py` simula o cliente Matrix e o agente, então roda sem matrix-nio e sem rede:

```bash
python -m pytest tests/test_matrix_connector.py
```
