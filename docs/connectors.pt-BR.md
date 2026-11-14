# Protocolo de conectores

[English](connectors.md) · [简体中文](connectors.zh-CN.md) · [繁體中文](connectors.zh-TW.md) · [日本語](connectors.ja.md) · [한국어](connectors.ko.md) · [Español](connectors.es.md) · [Français](connectors.fr.md) · [Deutsch](connectors.de.md) · Português (Brasil) · [Русский](connectors.ru.md)

O agente nunca fala diretamente com uma plataforma de chat. Quem faz isso é um conector. Ele faz login em uma plataforma, ou em um framework que abrange várias, transforma cada mensagem recebida em um evento neutro, envia o evento ao personagent e entrega o que volta. Tudo o que é específico da plataforma fica no conector, então o agente vê o mesmo formato vindo de qualquer plataforma.

Este repositório traz quatro conectores:

| Conector | Alcança | Caminho |
|---|---|---|
| Direto | Bots oficiais do QQ, WeChat pessoal (iLink), Telegram, Discord, Matrix, Twitch, IRC, Zulip, VK e Stoat, sem outro software. A página local e `personagent up` o executam como um só processo, `python -m persona_agent.direct`. | `persona_agent/direct/` |
| Plugin do AstrBot | As plataformas do AstrBot, uma ponte de terceiros. O AstrBot que o personagent gerencia para KOOK, Feishu/Lark, DingTalk, Slack, WeCom, Mattermost, Misskey, OneBot v11 e os demais recebe o plugin automaticamente. Para um AstrBot que você já executa, `personagent connect astrbot` faz a configuração. Você também pode enviar `astrbot_plugin_personagent.zip` de uma GitHub Release pela opção Install from File do AstrBot e definir `connector_token` manualmente. | `integrations/astrbot/` |
| Satori | Todas as implementações de Satori (Koishi e outras, de terceiros): QQ, Telegram, Discord, KOOK, Lark, DingTalk, LINE, WhatsApp, Matrix, Zulip, e-mail e mais. | `integrations/satori/` |
| Matrix | Salas do Matrix e, por meio de pontes mautrix de terceiros, WhatsApp, Signal, Messenger, Instagram, Google Messages e mais. | `integrations/matrix/` |

Assistentes de programação não são plataformas de chat e, por isso, têm um caminho próprio: um servidor MCP, `personagent mcp`, explicado no [guia do usuário](guide.pt-BR.md#assistentes-de-programação).

Os quatro falam o protocolo descrito nesta página. Para escrever um novo, você precisa desta página e de um cliente HTTP. O auxiliar em Python em `integrations/sdk/personagent_connector.py` assina as solicitações e executa o ciclo da caixa de saída por você. Ele recebe a URL base, o token e o `connector_id` do conector, e precisa de `httpx`. O [README](../integrations/sdk/README.pt-BR.md) dele traz um exemplo completo.

## Testar na sua própria máquina

```
personagent run --port 8080
curl http://127.0.0.1:8080/health
```

`personagent run` serve os dois endpoints descritos abaixo em `127.0.0.1`. Ele lê `CONNECTOR_TOKEN` do `.env` da pasta inicial indicada no aviso de inicialização; `--home DIR` escolhe outra.

- Com `CONNECTOR_TOKEN` vazio, o agente aceita apenas programas da mesma máquina que chamam `127.0.0.1` ou `localhost`, e eles não enviam cabeçalhos de autenticação. `personagent init` o deixa vazio. A página local, `personagent up` e `personagent connect astrbot` gravam um valor aleatório quando ele está vazio.
- Para definir um, coloque um valor aleatório longo no `.env`, por exemplo a saída de `python -c "import secrets; print(secrets.token_urlsafe(32))"`, configure o mesmo valor no conector e reinicie o agente.
- `GET /health` responde `{"status": "ok", "agent_enabled": true}` e não tem custo. `"agent_enabled": false` significa que o agente não consegue responder (sem `LLM_API_KEY`, ou `AGENT_ENABLED=false`), e todo evento recebe `owned: false`. `GET /health/details` também verifica o modelo e os outros serviços, o que pode ter um pequeno custo. Ele exige o cabeçalho `X-Personagent-Token` quando há um token definido e, caso contrário, uma solicitação da mesma máquina; qualquer outra recebe `403` com o código `forbidden`.

## Configuração

A página local configura o conector direto. Os outros três usam os mesmos nomes, então uma configuração significa a mesma coisa em cada um:

| Significado | Satori | Matrix | Chave do plugin do AstrBot |
|---|---|---|---|
| A URL base do personagent, como `http://127.0.0.1:8080`. O conector acrescenta `/v1/events` e `/v1/outbox`. | `PERSONAGENT_URL` | `PERSONAGENT_URL` | `personagent_url` |
| O token compartilhado, igual ao `CONNECTOR_TOKEN` do agente | `CONNECTOR_TOKEN` | `CONNECTOR_TOKEN` | `connector_token` |
| O id deste conector (`connector_id` abaixo) | `SATORI_CONNECTOR_ID` | `MATRIX_CONNECTOR_ID` | `connector_id` |
| Quanto tempo uma solicitação pode levar, em segundos | `SATORI_TIMEOUT_S` | `MATRIX_TIMEOUT_S` | `timeout_s` |
| Consultar a caixa de saída | `SATORI_OUTBOX_ENABLED` | `MATRIX_OUTBOX_ENABLED` | `outbox_enabled` |
| Grupos a encaminhar | `SATORI_GROUPS` | `MATRIX_GROUPS` | `groups` |
| Pessoas cujas mensagens privadas são encaminhadas | `SATORI_DM_USERS` | `MATRIX_DM_USERS` | `dm_users` |
| O servidor da plataforma | `SATORI_URL` | `MATRIX_URL` | O do próprio AstrBot |

Uma lista de grupos ou de conversas privadas vazia não encaminha nada desse tipo. `*` encaminha tudo e marca os eventos com `"prefiltered": false`, o que deixa a decisão para `ACCESS_GROUPS` e `ACCESS_DM_USERS` do agente. O README de cada conector lista as demais configurações.

## Endereçamento

O personagent guarda cada id como `<platform>:<id>`, por exemplo `telegram:-1001234` para um grupo ou `discord:4242` para um usuário. `platform` é o nome que o conector dá à plataforma, em minúsculas e sem `:`.

O QQ é a única exceção, mantida por compatibilidade. Os ids dele são guardados sem prefixo (`123456`), e `qq:123456` significa a mesma coisa em qualquer configuração. Se um conector traz o QQ e você quer alinhar o estado aprendido dele com uma implantação de QQ existente, coloque a plataforma dele em `CONNECTOR_QQ_PLATFORMS`. O adaptador de QQ do plugin do AstrBot é `aiocqhttp`. Os ids das plataformas listadas ali também são guardados sem prefixo.

## Autenticação

Os dois endpoints abaixo usam o mesmo esquema. Quando `CONNECTOR_TOKEN` está definido no agente, cada solicitação traz quatro cabeçalhos:

- `X-Personagent-Token`: o token.
- `X-Personagent-Timestamp`: segundos unix. Um valor a mais de cinco minutos do relógio do agente é recusado.
- `X-Personagent-Nonce`: um valor aleatório novo. Um nonce reutilizado é recusado.
- `X-Personagent-Signature`: `sha256=` seguido do HMAC-SHA256 em hexadecimal de `timestamp + "." + nonce + "." + body`, com o token como chave.

A assinatura cobre os bytes do corpo exatamente como são enviados, então qualquer JSON válido em UTF-8 é aceito. JSON canônico (chaves ordenadas, separadores compactos e não ASCII sem escape) é recomendado, e os conectores incluídos o enviam, mas o agente não o exige. O token também é a chave de assinatura, então mantenha-o fora dos logs.

Sem token, o agente só aceita programas locais que chamam `127.0.0.1` ou `localhost` diretamente. Um conector deve se recusar a enviar para qualquer coisa que não seja uma URL de loopback ou uma URL HTTPS com token.

## Entrada: `POST /v1/events`

Cada solicitação traz uma mensagem e devolve as respostas a ela.

```json
{
  "platform": "telegram",
  "conversation_type": "group",
  "conversation_id": "-1001234",
  "sender_id": "42",
  "sender_name": "Alex",
  "bot_id": "7000",
  "message_id": "881",
  "sent_at": 1790320000,
  "addressed": true,
  "text": "Nova, how was your day?",
  "segments": [
    {"type": "text", "text": "Nova, how was your day?"}
  ],
  "connector_id": "astrbot-7f3c",
  "reply_handle": "tg-bot:GroupMessage:-1001234",
  "capabilities": ["outbox", "quote_text"]
}
```

Os campos obrigatórios são `platform`, `conversation_type` (`group` ou `dm`), `sender_id`, `message_id` e `sent_at`, mais `conversation_id` para grupos. `sent_at` é quando a plataforma carimbou a mensagem, em segundos unix inteiros (uma string de dígitos também é aceita). O personagem vê cada mensagem com esse horário. Uma mensagem de grupo que tem mais de 10 minutos quando chega, nos dois minutos seguintes à primeira mensagem da plataforma desde que o agente foi iniciado, é um acúmulo entregue depois de um reinício: é mantida como contexto e não é respondida. Passados esses dois minutos, um `sent_at` antigo deixa de reter uma mensagem, de modo que um conector cujo relógio está atrasado continua recebendo respostas. Envie os ids brutos da plataforma. O agente acrescenta o prefixo.

O conector define `addressed`. É verdadeiro quando a mensagem menciona o bot, responde a uma das mensagens do bot ou é dirigida ao bot pelas regras da própria plataforma. O agente também percebe sozinho o próprio nome no texto. Ele lê uma citação da própria mensagem, ou uma @ ao bot, como uma reação com a qual pode aprender, então defina `addressed` nas respostas ao bot. Uma citação da mensagem de outro membro nunca é uma reação ao bot. Uma menção ao bot dentro de uma mensagem encaminhada não se dirige ao bot, então não defina `addressed` para ela.

Um evento cujo `sender_id` é igual ao `bot_id` é a própria mensagem do bot devolvida como eco. O agente a descarta sem ler e responde `{"handled": false, "owned": true, "replies": []}`, de modo que a lógica de bot do próprio conector também permaneça em silêncio. Ignore esses eventos no conector.

Os segmentos vêm em ordem:

| Tipo | Campos | Observações |
|---|---|---|
| `text` | `text` | |
| `mention` | `user_id`, `name` | Uma menção a alguém. Menciona o bot quando `user_id` é igual a `bot_id`. O personagem lê `name` no lugar do id, então envie-o. `name` chega ao modelo marcado como um nome que o remetente não escreveu, então nunca chama o personagem nem dá um comando. Uma menção ao bot depois de um segmento `forward` não é uma chamada. |
| `image` | `url` ou `b64`, `sticker` (booleano) | `sticker` marca uma figurinha enviada como imagem. Uma imagem de grupo enviada como `b64`, ou marcada com `sticker`, pode ser coletada para a biblioteca de figurinhas; uma foto enviada apenas como `url` não é coletada. |
| `emoji` | `name`, `id` | Uma figurinha da plataforma ou emoji personalizado que o agente não consegue ver. `name` é como uma pessoa o chamaria. |
| `media` | `kind`, `name`, `transcript`, `emoji` | Algo que o agente não consegue ver. `kind` é `voice`, `video`, `file`, `photo` (uma imagem que não pôde ser obtida) ou `sticker`. Acrescente `name` a um arquivo, `transcript` a uma mensagem de voz que a plataforma transcreveu e `emoji` a uma figurinha. |
| `forward` | `name` | Os segmentos depois dele foram encaminhados de `name`, não escritos pelo remetente. `name` pode estar vazio. O texto deles é lido como palavras da pessoa cuja mensagem foi encaminhada: não chama ninguém pelo nome nem executa nenhum comando de memória. Coloque o comentário do próprio remetente antes do segmento `forward` ou envie-o como uma mensagem separada. |
| `reply` | `message_id`, `text`, `sender_id`, `sender_name` | A mensagem que esta cita. Envie `text` sempre que a plataforma fornecer. |

Envie mídias como um segmento `media`, nunca em palavras como `(sent a voice message)`: o personagem as leria como se tivessem sido digitadas pelo remetente. O agente descarta tipos de segmento desconhecidos.

Estes campos opcionais ativam mais do agente:

| Campo | Significado |
|---|---|
| `connector_id` | Um id estável para esta instância do conector. A caixa de saída exige. |
| `reply_handle` | O que o conector precisar para alcançar esta conversa depois sem uma mensagem recebida: o `unified_msg_origin` do AstrBot, um id de sala do Matrix ou um login do Satori mais um id de canal. O agente o trata como opaco, guarda por conversa e devolve nas entregas da caixa de saída. |
| `capabilities` | O que o conector sabe fazer. `outbox` significa que ele consulta a caixa de saída e pode enviar por conta própria. `quote_text` significa que os segmentos de resposta trazem o texto citado. |
| `prefiltered` | `true` (o padrão) quando o conector aplicou a própria lista de permissão. `false` faz das listas do agente o único filtro. |
| `proactive` | Marca um evento de conversa privada como uma deixa escrita pelo conector, não como palavras da pessoa. Veja "Falar primeiro sem a caixa de saída". |

A resposta é assim:

```json
{"handled": true, "owned": true, "replies": [
  {"type": "text", "text": "not bad, rained all afternoon", "mention_user_id": "telegram:42"},
  {"type": "image", "b64": "..."}
]}
```

- `replies`: envie em ordem, cada uma como uma mensagem separada. Quando `mention_user_id` está presente, é o id com prefixo a mencionar. Exiba a menção da forma usada pela plataforma. Um item com `"reason": "excuse"` é a mensagem curta que o personagem envia em uma conversa privada quando o modelo falhou, não uma resposta. Envie-o como os demais ou trate-o como um erro.
- `owned`: o agente assumiu a mensagem, porque ela passou pelas listas de permissão do agente, independentemente do que a persona faça depois. Quando é verdadeiro, impeça qualquer outra lógica de bot de responder, mesmo que `replies` esteja vazio, porque a persona pode ter optado por permanecer em silêncio. Quando é falso, o agente não participou da mensagem: a conversa não está nas listas de permissão do agente, o agente não consegue responder de forma alguma (sem `LLM_API_KEY`, ou `AGENT_ENABLED=false`), ou o `message_id` já foi recebido antes (veja "Mensagens repetidas" abaixo). Quando o agente não consegue responder, o log dele traz uma linha ERROR com a causa.
- `handled`: verdadeiro quando o próprio turno desta solicitação entregou algo, uma resposta ou o resultado de um comando de memória. Serve para logs e estatísticas. Decida com base em `owned` e envie o que estiver em `replies`, seja qual for o valor de `handled`: uma mensagem `excuse`, por exemplo, vem com `handled: false`.

As combinações que um conector encontra:

| Resposta | Quando | O que o conector faz |
|---|---|---|
| `handled: true`, `owned: true`, com respostas | Uma resposta normal. | Envia `replies` e mantém em silêncio a outra lógica de bot. |
| `handled: false`, `owned: true`, `replies: []` | A persona ficou em silêncio; o evento era o eco do próprio bot; a mensagem foi incorporada ao turno de uma mensagem posterior (veja "Mensagens enviadas em sequência"); um comando de memória cujo resultado chega depois pela caixa de saída; um evento de grupo com `proactive`. | Não envia nada e mantém em silêncio a outra lógica de bot. |
| `handled: false`, `owned: true`, uma resposta com `"reason": "excuse"` | O modelo falhou em uma conversa privada. | Envia-a ou a trata como um erro. |
| `handled: false`, `owned: false`, `replies: []` | A conversa não está nas listas de permissão, o agente não consegue responder ou o `message_id` é repetido. | Para um `message_id` já enviado antes, não faz nada. Caso contrário, a mensagem é sua. |

Outras regras:

- **Mensagens repetidas.** O agente lembra as últimas 2.000 mensagens que admitiu, de todas as conversas. A chave é formada por `platform`, pela conversa (o `conversation_id` de um grupo, o `sender_id` de uma conversa privada) e por `message_id`; para uma plataforma em `CONNECTOR_QQ_PLATFORMS`, é o `message_id` sem prefixo. A lista é salva de tempos em tempos, e ao encerrar, na pasta `runtime/` da pasta inicial, então ela sobrevive a uma reinicialização. Uma mensagem enviada de novo, como uma reentrega da plataforma ou uma nova tentativa após um tempo esgotado, recebe `{"handled": false, "owned": false, "replies": []}` na hora, mesmo enquanto a primeira solicitação ainda está em andamento, e as respostas dela vêm só na primeira. Não a responda: mantenha um registro dos `message_id`s que você enviou. Um turno continua quando quem o chamou desiste, então, após um tempo esgotado, as respostas se perdem; reserve tempo suficiente em vez de tentar de novo. Uma mensagem recusada pelas listas de permissão não é lembrada e é avaliada de novo quando reenviada.
- **Mensagens enviadas em sequência.** Mensagens de uma conversa que chegam dentro de um debounce curto (2,5 segundos, ou 5 segundos após uma mensagem de grupo que apenas chama a persona pelo nome) formam um único turno, que responde a todas juntas. Mensagens que aguardam atrás de um turno em andamento também são lidas no turno seguinte. Só a solicitação da mensagem mais recente traz as respostas; cada solicitação anterior retorna `{"handled": false, "owned": true, "replies": []}`. Em um grupo, o `mention_user_id` de uma resposta indica a pessoa a quem a persona responde, que pode ter enviado uma mensagem anterior, e não aquela cuja solicitação traz a resposta. Comandos de memória não são combinados; veja o último item.
- A solicitação dura até o turno terminar, que é um debounce curto mais o tempo do modelo. As chamadas ao modelo de um turno dividem um único orçamento de 1,5 × `LLM_TIMEOUT_S`, novas tentativas incluídas, tanto em um grupo quanto em uma conversa privada, e uma mensagem que chega enquanto um turno anterior da sua conversa ainda está pensando aguarda esse turno terminar antes de começar o seu. Reserve pelo menos 3 × `LLM_TIMEOUT_S` segundos (360 com o padrão).
- Um comando de memória (como "remember ...") que chega enquanto um turno da sua conversa ainda está pensando é respondido depois desse turno. Um conector que declarou `outbox` recebe `{"handled": false, "owned": true, "replies": []}` na hora e o resultado depois, como uma entrega `follow_up`. Sem `outbox`, o resultado vem na resposta a uma solicitação: a dele mesmo ou a de outra solicitação em espera da mesma conversa, então uma resposta pode trazer `replies` que mencionam outra pessoa que não o remetente do evento.

## Caixa de saída: `POST /v1/outbox`

Algumas mensagens não respondem a uma solicitação. Exemplos são uma abertura agendada, a pergunta de acompanhamento depois de uma rejeição, a resposta a um comando de memória que esperou atrás de um turno e a desculpa quando o modelo está fora do ar em um grupo. O agente as enfileira por conversa, e um conector que declarou `outbox` as busca, de modo que um conector atrás de NAT ou firewall funciona da mesma forma. Conversas guardadas com ids de QQ sem prefixo (veja Endereçamento) também usam a caixa de saída enquanto o conector delas estiver consultando. Caso contrário, passam pela API HTTP do NapCat, quando `QQ_ONEBOT_URL` está definido.

Solicitação:

```json
{
  "kind": "outbox.pull",
  "connector_id": "astrbot-7f3c",
  "wait_s": 25,
  "max_deliveries": 10,
  "acks": [
    {"delivery_id": "d_5c1f...", "status": "sent", "sent_items": 2}
  ]
}
```

O agente segura a solicitação por até `wait_s` segundos (no máximo 30) até algo entrar na fila, e então responde:

```json
{
  "deliveries": [
    {
      "delivery_id": "d_9a07...",
      "conversation_key": "telegram:-1001234",
      "reply_handle": "tg-bot:GroupMessage:-1001234",
      "platform": "telegram",
      "conversation_type": "group",
      "conversation_id": "-1001234",
      "reason": "proactive",
      "expires_in_s": 300,
      "items": [{"type": "text", "text": "anyone still up?"}]
    }
  ],
  "next_wait_s": 25
}
```

`items` tem a mesma forma de `replies`. `reason` é `proactive`, `follow_up` ou `excuse`, e `conversation_type` é `group` ou `dm`. `conversation_key` é a chave sob a qual o agente guarda a conversa, como `private:telegram:42` para uma conversa privada. `conversation_id` é o id bruto que o evento trouxe, que em uma conversa privada é o id do usuário. O agente lembra `reply_handle`, `connector_id` e `capabilities` do último evento admitido em cada conversa, então uma conversa fica alcançável depois de enviar uma mensagem. Uma exceção mantém em seu lugar um conector que busca a caixa de saída: um evento de um conector sem a capacidade `outbox` não substitui o que outro conector com essa capacidade guardou para a mesma conversa. Assim, um conector que busca a caixa de saída continua alcançando a conversa depois que outro programa, como um assistente de programação, falou nela. Um evento do mesmo conector, ou de qualquer conector que declare `outbox`, substitui os valores guardados como antes.

A página local é, ela própria, um conector de caixa de saída, com o `connector_id` `local-welcome`. Ela recebe apenas as entregas da conversa da própria página e as mostra na visão Conversa.

Informe cada entrega em `acks` na próxima consulta:

| `status` | Significado |
|---|---|
| `sent` | Todos os itens saíram. |
| `partial` | Os primeiros `sent_items` itens saíram. |
| `failed` | Nada saiu. |
| `expired` | O envio não começou dentro de `expires_in_s`. |
| `refused` | O conector não permite mais a conversa. |
| `unsupported` | A plataforma não consegue enviar por conta própria para esta conversa. |

Regras:

- **No máximo uma vez.** O agente passa uma entrega uma vez e nunca mais, aconteça o que acontecer com o ack. Guarde as últimas centenas de `delivery_id` e nunca envie um duas vezes.
- **Em ordem.** Envie as entregas de uma conversa na ordem em que as recebeu. Conversas diferentes podem sair em paralelo.
- **Só contam entregas confirmadas.** O agente trata uma entrega sem confirmação como não enviada e registra como enviadas só as confirmadas. Ele espera o ack até sua próxima consulta, e no máximo `expires_in_s` mais 60 segundos depois de passar a entrega. Termine de enviar um lote antes de consultar de novo.
- **Atividade.** Um conector que não consultou por 90 segundos é considerado ausente. Nada entra na fila das conversas dele até ele consultar de novo, e o que estava na fila para ele, ou foi passado sem ack, termina como não enviado. Consulte de novo assim que um lote for entregue. Essa consulta também traz os acks do lote.
- **`unsupported` permanece.** Depois desse ack, o agente para de enfileirar para a conversa até um evento trazer um `reply_handle` diferente.
- **Tipos de corpo.** A assinatura não cobre o caminho da URL. Por isso, o agente recusa um corpo de evento no endpoint da caixa de saída e um corpo `outbox.pull` no endpoint de eventos, com `400` e o código `invalid_schema`. Um evento pode trazer `"kind": "event"`. Um evento com qualquer outro `kind` é recusado.

Um 404 sem `code` significa que o agente não oferece a caixa de saída. Um `404` com o código `outbox_disabled` significa que o operador a desativou com `CONNECTOR_OUTBOX_ENABLED`. Nos dois casos, espere bastante antes de consultar de novo.

## Erros

Um erro responde `{"error": "...", "code": "..."}`. `code` é estável, então baseie suas decisões nele. `error` é uma frase para quem lê um log, e o texto pode mudar.

| Status | `code` | Endpoint | Causa |
|---|---|---|---|
| 400 | `invalid_schema` | ambos | O corpo não é um objeto JSON; um campo obrigatório falta ou está vazio; `conversation_type` não é `group` nem `dm`; `segments` não é uma lista; um corpo do tipo errado (veja "Tipos de corpo"); uma consulta sem um `connector_id` válido (no máximo 128 caracteres), com `wait_s` ou `max_deliveries` que não é um número, ou com mais de 1.000 acks. |
| 400 | `client_disconnected` | ambos | Quem chamou desligou enquanto enviava o corpo. |
| 403 | `unauthenticated` | ambos | Não há `CONNECTOR_TOKEN`, e quem chamou não está na máquina do agente. |
| 403 | `non_local_request` | ambos | Não há `CONNECTOR_TOKEN`, e a solicitação traz um cabeçalho que um programa local não envia: `Origin`, um `Sec-Fetch-Site` diferente de `none`, um `Host` diferente de `localhost`, `127.0.0.1` ou `::1`, ou um cabeçalho de proxy como `X-Forwarded-For`. |
| 403 | `invalid_envelope` | ambos | `CONNECTOR_TOKEN` está definido, e o token ou um cabeçalho falta ou está errado, a assinatura não confere, o carimbo de tempo difere em mais de cinco minutos, o nonce já foi usado ou a proteção contra repetição está cheia. |
| 403 | `stale_event` | events | `sent_at` não é um número inteiro de segundos, ou se afasta mais de `CONNECTOR_MAX_EVENT_AGE_S` (24 horas) do relógio do agente, em qualquer direção. Um valor em milissegundos fica num futuro distante. |
| 404 | `outbox_disabled` | outbox | `CONNECTOR_OUTBOX_ENABLED=false`, ou o agente está desligado (`AGENT_ENABLED=false`). |
| 408 | `body_timeout` | ambos | O corpo levou mais de 30 segundos para chegar. |
| 413 | `body_too_large` | ambos | O corpo é maior que `SERVER_MAX_BODY_BYTES` (8.000.000 bytes), geralmente por causa de uma imagem embutida. |
| 429 | `capacity_exceeded` | ambos | Solicitações demais ao mesmo tempo: mais de `CONNECTOR_MAX_INFLIGHT` turnos (64 por padrão) no endpoint de eventos, ou 16 consultas na caixa de saída. O cabeçalho `Retry-After` informa os segundos de espera: 3, ou 5 para a caixa de saída. |

Um caminho errado recebe `404 {"detail": "Not Found"}` e um método errado, como `GET /v1/events`, recebe `405 {"detail": "Method Not Allowed"}`. Essas respostas vêm do framework web e não trazem `code`.

## Falar primeiro sem a caixa de saída

Um conector que não consegue consultar ainda pode abrir uma conversa privada. O próprio agendador dele, como uma tarefa de plugin do AstrBot ou uma entrada de cron, envia um evento comum de conversa privada com `"proactive": true` para `/v1/events`. O agente lê o texto como uma deixa para a persona ("está quieto há um dia; a prova era hoje de manhã"), corta em 500 caracteres e nunca o guarda como palavras da pessoa. As instruções proativas do motor continuam decidindo o turno e podem manter a persona em silêncio. Se a persona falar, a resposta volta na resposta HTTP para o agendador repassar.

O evento precisa de tudo o que os eventos normais do conector trazem: os cabeçalhos assinados, todos os campos obrigatórios, o mesmo `platform` e `sender_id` bruto que o conector envia para essa pessoa, texto não vazio e um `message_id` novo a cada vez. Um evento com `message_id` repetido é descartado em silêncio. A deixa conta para o mesmo intervalo de conversas privadas que as aberturas do próprio agente (`PROACTIVE_DM_COOLDOWN_S`), e não conta como atividade da pessoa.

Defina sempre o indicador; sem ele, o agente guarda a deixa como palavras da pessoa. Um evento de grupo com o indicador é assumido (`owned: true`, para que o conector mantenha o próprio bot em silêncio) e descartado sem ler.

## Capacidades e o que deixa de funcionar

| Faltando | Efeito |
|---|---|
| `outbox` | Sem aberturas agendadas, sem pergunta de acompanhamento e sem desculpa quando uma chamada ao modelo falha em um grupo. Ids de QQ ainda os recebem pelo NapCat quando `QQ_ONEBOT_URL` está definido e acessível. A desculpa de uma conversa privada volta nos `replies` da resposta e não precisa da caixa de saída. |
| `quote_text` | O agente só entende uma mensagem citada se viu essa mensagem ele mesmo. |
| `reply_handle` | Igual a faltar `outbox`. |
| `addressed` errado | A persona trata mensagens dirigidas a ela como conversa de fundo. |

## Escrever um conector

1. Receba uma mensagem da plataforma. Ignore as mensagens do próprio bot e os eventos que não são mensagens (entradas, remoções, cutucadas).
2. Monte o evento descrito acima. Defina `addressed` pelas regras de menção e resposta da própria plataforma.
3. Assine e envie o evento. Envie `replies` em ordem e, quando `owned` for verdadeiro, mantenha qualquer outra lógica de bot em silêncio.
4. Se a plataforma puder enviar por conta própria, acrescente `connector_id`, `reply_handle` e `capabilities: ["outbox"]`, e execute o ciclo de consulta: consulte, entregue cada entrega pelo `reply_handle` dela e confirme na próxima consulta.

`integrations/sdk/personagent_connector.py` cuida das etapas 3 e 4. O [README](../integrations/sdk/README.pt-BR.md) dele mostra as duas em um programa curto.
