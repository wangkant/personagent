# Conector Satori

[English](README.md) · [简体中文](README.zh-CN.md) · [繁體中文](README.zh-TW.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Español](README.es.md) · [Français](README.fr.md) · [Deutsch](README.de.md) · Português (Brasil) · [Русский](README.ru.md)


Este conector conecta o [personagent](https://github.com/wangkant/personagent) a um servidor [Satori](https://satori.chat). Satori é um protocolo de chat multiplataforma. Um servidor como o [Koishi](https://koishi.chat) (com o plugin `server-satori`), Chronocat ou LLOneBot faz login nas plataformas de chat, e um cliente como este recebe cada mensagem de cada login por um único websocket. Assim, um processo de conector coloca a persona em todas as plataformas para as quais o servidor tem adaptador.

Satori e Koishi são softwares de terceiros. O personagent não precisa deles para QQ, WeChat, Telegram, Discord, Matrix, Twitch, IRC, Zulip, VK ou Stoat, que conecta por conta própria, nem para as plataformas que a página local configura pelo AstrBot. Use este conector quando você já executa o Koishi, ou quando quer uma plataforma que só o Koishi alcança.

O conector encaminha cada mensagem permitida ao `POST /v1/events` do agente como evento neutro ([docs/connectors.md](../../docs/connectors.pt-BR.md)) e envia as respostas de volta pelo Satori. Ele também busca a caixa de saída do agente, então mensagens programadas, perguntas de acompanhamento e desculpas chegam ao chat.

O [satori-python](https://github.com/RF-Tar-Railt/satori-python) cuida do lado do Satori: o websocket, a lista de logins e a API HTTP. Este conector converte entre o Satori e o formato de eventos do personagent e usa [`integrations/sdk/personagent_connector.py`](../sdk/personagent_connector.py) para a assinatura e o loop da caixa de saída.

## Configuração, com Koishi

1. **Koishi.** Instale o Koishi com o inicializador de desktop ou `npm init koishi@latest`. No console dele, adicione e configure um adaptador para sua plataforma, como `adapter-telegram` ou `adapter-discord`, e confirme que o bot está online. Ative os plugins `server` e `server-satori`. O Koishi passa a servir o Satori em `http://127.0.0.1:5140/satori`. Dê um `token` ao `server-satori` se algo além desta máquina puder alcançar essa porta.

   O Koishi continua executando os outros plugins. Se algum também responder a mensagens, como um modelo de chat ou um plugin de resposta, ele responderá junto com a persona, e o conector não consegue silenciá-lo. Desative esse plugin ou remova dele as conversas que você encaminha.

2. **O agente.** Execute o personagent (`personagent run`, veja o README dele). Se o conector e o agente estiverem em hosts diferentes, defina `CONNECTOR_TOKEN` no `.env` do agente e coloque o agente atrás de HTTPS. Defina o token antes de adicionar qualquer proxy ou túnel, mesmo em um único host.

3. **O conector.** O conector é um script neste repositório, então precisa de uma cópia do repositório (um clone ou o ZIP do GitHub) e de um ambiente Python próprio, porque `satori-python` não é dependência do personagent. Em um clone que já tem o `.venv` do personagent, instale nesse ambiente:

   ```bash
   .venv/bin/python -m pip install -r integrations/satori/requirements.txt
   ```

   Se você instalou o personagent do PyPI com pip, ou o executa com uvx, crie um venv separado ao lado da cópia:

   ```bash
   python -m venv connector-venv
   connector-venv/bin/python -m pip install -r integrations/satori/requirements.txt
   ```

   No Windows, o interpretador é `.venv\Scripts\python.exe` ou `connector-venv\Scripts\python.exe`. Em seguida, copie o arquivo de configurações:

   ```bash
   cp integrations/satori/.env.example integrations/satori/.env
   ```

   Em `integrations/satori/.env`, defina a URL e o token do servidor Satori, a URL base e o `CONNECTOR_TOKEN` do agente e as conversas a encaminhar (veja [Listas de permissão](#listas-de-permissão)). Depois inicie o conector com o mesmo interpretador:

   ```bash
   .venv/bin/python integrations/satori/satori_connector.py
   ```

   `--config FILE` lê outro arquivo de configurações. Qualquer configuração também pode ser dada como variável de ambiente, que tem prioridade sobre o arquivo.

4. **Verifique se funciona.** Para cada bot do servidor, o log mostra uma linha como `Satori login telegram:7000 is ONLINE`. Mencione o bot em um grupo encaminhado. O log do agente mostra o turno, e a resposta aparece no chat. Se nada acontecer, defina `SATORI_LOG_LEVEL=DEBUG`.

## Configurações

| Configuração | Padrão | Significado |
|---|---|---|
| `SATORI_URL` | `http://127.0.0.1:5140/satori` | O servidor Satori. O `/v1` no fim é opcional. |
| `SATORI_TOKEN` | | O token do servidor (no Koishi, `server-satori` → `token`). |
| `PERSONAGENT_URL` | `http://127.0.0.1:8080` | A URL base do agente. `/v1/events` e `/v1/outbox` são acrescentados. |
| `CONNECTOR_TOKEN` | | O `CONNECTOR_TOKEN` do agente. |
| `SATORI_GROUPS` | | Grupos a encaminhar, como ids de canal ou servidor, opcionalmente `platform:id`. Vazio não encaminha nenhum, `*` encaminha todos. |
| `SATORI_DM_USERS` | | Pessoas cujas mensagens privadas são encaminhadas, como ids de usuário, opcionalmente `platform:id`. Vazio não encaminha nenhuma, `*` encaminha todas. |
| `SATORI_PLATFORMS` | todas | Limita o conector a estas plataformas Satori. |
| `SATORI_PLATFORM_NAMES` | `qq=qqbot` | Renomeia as plataformas como o agente as vê: `satori_name=name, ...` |
| `SATORI_OUTBOX_ENABLED` | `true` | Buscar a caixa de saída do agente. |
| `SATORI_CONNECTOR_ID` | a partir de `SATORI_URL` | O id deste conector no agente. Mantenha estável. |
| `SATORI_TIMEOUT_S` | `420` | Quanto um turno pode durar. Mantenha acima de 3 × `LLM_TIMEOUT_S` do agente. |
| `SATORI_INLINE_IMAGES_ENABLED` | `false` | Baixar URLs de imagens públicas no conector em vez de passar a URL ao agente. |
| `SATORI_LOG_LEVEL` | `INFO` | |

A URL do agente precisa ser um endereço de loopback, ou HTTPS com `CONNECTOR_TOKEN` definido. Caso contrário, o conector se recusa a iniciar. Se `SATORI_TOKEN` fosse enviado por `http` sem criptografia a outro host, o conector registra um aviso.

## Listas de permissão

O conector nega por padrão. Com listas vazias, não encaminha nada.

- Um grupo é um canal Satori. Ele é encaminhado quando o id de canal ou de servidor está em `SATORI_GROUPS`. No Discord ou KOOK, portanto, um id de servidor admite todos os canais desse servidor, e cada canal continua sendo uma conversa separada.
- Uma conversa privada é encaminhada quando o id de usuário do remetente está em `SATORI_DM_USERS`.
- Uma entrada pode nomear a plataforma, como `telegram:-1001234` ou `discord:4242`, e então só corresponde nessa plataforma. Uma entrada sem plataforma corresponde em todas.
- `*` encaminha todos os grupos (ou todas as mensagens privadas) e marca o evento com `prefiltered: false`. Nesse caso, a decisão cabe a `ACCESS_GROUPS` e `ACCESS_DM_USERS` do próprio agente, e uma plataforma sem entradas ali é recusada.

O plugin `inspect` do Koishi imprime os ids de plataforma, canal, servidor e usuário de uma mensagem.

## Nomes de plataforma e QQ

O personagent armazena ids como `<platform>:<id>`, em que a plataforma é a do login Satori (`telegram`, `discord`, `onebot` etc.). A linha de log do passo 4 a mostra. Dois casos são especiais:

- **QQ pelo OneBot** (o `adapter-onebot` do Koishi, com NapCat ou LLOneBot por trás) usa números QQ como ids. Para manter o que o agente aprendeu em uma implantação QQ existente, adicione a plataforma a `CONNECTOR_QQ_PLATFORMS` do agente (`CONNECTOR_QQ_PLATFORMS=onebot`). Os ids passam a ser armazenados sem prefixo, como os números QQ do NapCat, e as entradas QQ de `ACCESS_GROUPS` e `ACCESS_DM_USERS` se aplicam a eles. Faça isso só para uma plataforma cujos ids sejam realmente números QQ.
- **A API oficial de bots do QQ** (o `adapter-qq` do Koishi) chama a plataforma de `qq`, mas os ids são openids, não números QQ. O conector renomeia a plataforma para `qqbot`. `SATORI_PLATFORM_NAMES` substitui essa renomeação. O personagent também pode conectar bots oficiais do QQ por conta própria, sem Koishi.

## O que funciona

| Recurso | Status |
|---|---|
| Chats em grupo e conversas privadas | Sim. Uma conversa privada é um canal `DIRECT`, ou uma mensagem sem servidor. |
| Detecção de chamada (`addressed`) | Um `<at>` do bot (por id, ou pelo nome do bot quando o servidor não dá id) e uma resposta a uma mensagem do bot. `@all` conta como texto, não como menção. |
| Mensagens citadas | O texto citado, o remetente e o id, de um elemento `<quote>` ou de `message.quote`. |
| Imagens recebidas | Imagens `data:` e `internal:` e imagens no servidor Satori são embutidas. URLs públicas são passadas para o agente buscar. URLs de rede privada são descritas como `(sent an image)`. No máximo 4 downloads por mensagem, de 4 MB cada. |
| Figurinhas e emoji | `<emoji>` e o `<face>` do QQ chegam como emoji, e a persona sabe que não consegue vê-los. |
| Voz, vídeo, arquivos | Descritos em palavras: `(sent a voice message)`, `(sent a video)`, `(sent a file: deck.pdf)`. |
| Respostas | Texto, e imagens como URIs `data:`, cada um enviado como mensagem separada com um pequeno intervalo. Em grupos, uma menção solicitada pelo agente é convertida em um `<at>`. |
| Plataformas de resposta passiva | As respostas levam o `referrer` do evento, de que a API oficial de bots do QQ precisa para responder a uma mensagem. |
| Caixa de saída | Mensagens programadas, acompanhamentos e desculpas vão ao canal pelo login que recebeu a conversa. O conector assina cada identificador de resposta com uma chave derivada de `SATORI_TOKEN` e `CONNECTOR_TOKEN` e só envia a identificadores que ele assinou. Depois de mudar qualquer um dos tokens, uma conversa volta a ser alcançável quando envia uma mensagem. Um agente com `CONNECTOR_OUTBOX_ENABLED=false` responde 404, e o conector tenta de novo a cada 10 minutos. |
| Indicador de digitação | Não. O Satori não tem API de digitação. |
| `owned` | Respeitado: o conector não envia mais nada. Ele não pode parar outros plugins do Koishi (veja o passo 1). |

As regras das plataformas continuam valendo. A API oficial de bots do QQ, por exemplo, limita rigorosamente as mensagens que um bot pode enviar sem ser solicitado, então as entregas da caixa de saída ali podem voltar como `failed`.

## Testes

`tests/test_satori_connector.py` é executado sem satori-python e sem rede. Ele simula os objetos de elemento, a conta e o agente.
