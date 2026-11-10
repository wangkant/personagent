# Protocolo de conectores

[English](connectors.md) · [简体中文](connectors.zh-CN.md) · [繁體中文](connectors.zh-TW.md) · [日本語](connectors.ja.md) · [한국어](connectors.ko.md) · [Español](connectors.es.md) · [Français](connectors.fr.md) · [Deutsch](connectors.de.md) · Português (Brasil) · [Русский](connectors.ru.md)

O agente nunca fala diretamente com uma plataforma de chat. Quem faz isso é um conector. Ele faz login em uma plataforma, ou em um framework que abrange várias, transforma cada mensagem recebida em um evento neutro, envia o evento ao personagent e entrega o que volta. Tudo o que é específico da plataforma fica no conector, então o agente vê o mesmo formato vindo de qualquer plataforma.

Este repositório traz quatro conectores:

| Conector | Alcança | Caminho |
|---|---|---|
| Direto | Bots oficiais do QQ, WeChat pessoal (iLink), Telegram e Discord, sem outro software. A página local e `personagent up` o executam como um só processo, `python -m persona_agent.direct`. | `persona_agent/direct/` |
| Plugin do AstrBot | As plataformas do AstrBot, uma ponte de terceiros. O AstrBot que o personagent gerencia para KOOK, Feishu/Lark, DingTalk, Slack, WeCom, Mattermost, Misskey, OneBot v11 e os demais recebe o plugin automaticamente. Para um AstrBot que você já executa, `personagent connect astrbot` faz a configuração. Você também pode enviar `astrbot_plugin_personagent.zip` de uma GitHub Release com Instalar de arquivo do AstrBot e definir `connector_token` você mesmo. | `integrations/astrbot/` |
| Satori | Todas as implementações de Satori (Koishi e outras, de terceiros): QQ, Telegram, Discord, KOOK, Lark, DingTalk, LINE, WhatsApp, Matrix, Zulip, e-mail e mais. | `integrations/satori/` |
| Matrix | Salas do Matrix e, por meio de pontes mautrix de terceiros, WhatsApp, Signal, Messenger, Instagram, Google Messages e mais. | `integrations/matrix/` |

Agentes de programação não são plataformas de chat, então têm um caminho próprio: um servidor MCP, `personagent mcp`, explicado no [guia do usuário](guide.pt-BR.md#agentes-de-código).

Os quatro falam o protocolo descrito nesta página. Para escrever um novo, você precisa desta página e de um cliente HTTP. O auxiliar em Python em `integrations/sdk/personagent_connector.py` assina as solicitações e executa o ciclo da caixa de saída por você. Ele recebe a URL base, o token e o `connector_id` do conector, e precisa de `httpx`.

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
| Pessoas cujas mensagens diretas são encaminhadas | `SATORI_DM_USERS` | `MATRIX_DM_USERS` | `dm_users` |
| O servidor da plataforma | `SATORI_URL` | `MATRIX_URL` | O do próprio AstrBot |

Uma lista de grupos ou de mensagens diretas vazia não encaminha nada desse tipo. `*` encaminha tudo e marca os eventos com `"prefiltered": false`, o que deixa a decisão para `ACCESS_GROUPS` e `ACCESS_DM_USERS` do agente. O README de cada conector lista as demais configurações.

## Endereçamento

O personagent guarda cada id como `<platform>:<id>`, por exemplo `telegram:-1001234` para um grupo ou `discord:4242` para um usuário. `platform` é o nome que o conector dá à plataforma, em minúsculas e sem `:`.

O QQ é a única exceção, mantida por compatibilidade. Os ids dele são guardados sem prefixo (`123456`), e `qq:123456` significa a mesma coisa em qualquer configuração. Se um conector traz o QQ e você quer alinhar o estado aprendido dele com uma implantação de QQ existente, coloque a plataforma dele em `CONNECTOR_QQ_PLATFORMS`. O adaptador de QQ do plugin do AstrBot é `aiocqhttp`. Os ids das plataformas listadas ali também são guardados sem prefixo.

## Autenticação

Os dois endpoints abaixo usam o mesmo esquema. Quando `CONNECTOR_TOKEN` está definido no agente, cada solicitação traz quatro cabeçalhos:

- `X-Personagent-Token`: o token.
- `X-Personagent-Timestamp`: segundos unix. Um valor a mais de cinco minutos do relógio do agente é recusado.
- `X-Personagent-Nonce`: um valor aleatório novo. Um nonce reutilizado é recusado.
- `X-Personagent-Signature`: `sha256=` seguido do HMAC-SHA256 em hexadecimal de `timestamp + "." + nonce + "." + body`, com o token como chave.

O corpo é JSON canônico: UTF-8, chaves ordenadas, separadores compactos e não ASCII sem escape. O token também é a chave de assinatura, então mantenha-o fora dos logs.

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

Os campos obrigatórios são `platform`, `conversation_type` (`group` ou `dm`), `sender_id`, `message_id` e `sent_at`, mais `conversation_id` para grupos. `sent_at` é quando a plataforma carimbou a mensagem, em segundos unix. Envie os ids brutos da plataforma. O agente acrescenta o prefixo.

O conector define `addressed`. É verdadeiro quando a mensagem menciona o bot, responde a uma das mensagens do bot ou é dirigida ao bot pelas regras da própria plataforma. O agente também percebe sozinho o próprio nome no texto. Ele lê uma citação da própria mensagem, ou uma @ ao bot, como uma reação com a qual pode aprender, então defina `addressed` nas respostas ao bot. Uma citação da mensagem de outro membro nunca é uma reação ao bot.

Um evento cujo `sender_id` é igual ao `bot_id` é a própria mensagem do bot devolvida como eco. O agente a descarta sem ler e responde `{"handled": false, "owned": true, "replies": []}`, de modo que a lógica de bot do próprio conector também fica quieta. Ignore esses eventos no conector.

Os segmentos vêm em ordem:

| Tipo | Campos | Observações |
|---|---|---|
| `text` | `text` | |
| `mention` | `user_id`, `name` | Uma menção a alguém. Menciona o bot quando `user_id` é igual a `bot_id`. |
| `image` | `url` ou `b64`, `sticker` (booleano) | `sticker` marca uma figurinha enviada como imagem. |
| `emoji` | `name`, `id` | Uma figurinha da plataforma ou emoji personalizado que o agente não consegue ver. `name` é como uma pessoa o chamaria. |
| `reply` | `message_id`, `text`, `sender_id`, `sender_name` | A mensagem que esta cita. Envie `text` sempre que a plataforma fornecer. |

Descreva qualquer outra coisa em palavras, como um segmento `text` do tipo `(sent a voice message)` ou `(sent a file: deck.pdf)`. O agente descarta tipos de segmento desconhecidos.

Estes campos opcionais ativam mais do agente:

| Campo | Significado |
|---|---|
| `connector_id` | Um id estável para esta instância do conector. A caixa de saída exige. |
| `reply_handle` | O que o conector precisar para alcançar esta conversa depois sem uma mensagem recebida: o `unified_msg_origin` do AstrBot, um id de sala do Matrix ou um login do Satori mais um id de canal. O agente o trata como opaco, guarda por conversa e devolve nas entregas da caixa de saída. |
| `capabilities` | O que o conector sabe fazer. `outbox` significa que ele consulta a caixa de saída e pode enviar por conta própria. `quote_text` significa que os segmentos de resposta trazem o texto citado. |
| `prefiltered` | `true` (o padrão) quando o conector aplicou a própria lista de permissão. `false` faz das listas do agente o único filtro. |
| `proactive` | Marca um evento de mensagem direta como uma deixa escrita pelo conector, não como palavras da pessoa. Veja "Falar primeiro sem a caixa de saída". |

A resposta é assim:

```json
{"handled": true, "owned": true, "replies": [
  {"type": "text", "text": "not bad, rained all afternoon", "mention_user_id": "telegram:42"},
  {"type": "image", "b64": "..."}
]}
```

- `replies`: envie em ordem, cada uma como uma mensagem separada. Quando `mention_user_id` está presente, é o id com prefixo a mencionar. Exiba a menção do jeito da plataforma.
- `owned`: o agente assumiu esta conversa. Quando é verdadeiro, impeça qualquer outra lógica de bot de responder, mesmo que `replies` esteja vazio, porque a persona escolheu ficar quieta. Quando é falso, a mensagem é sua. Ou a conversa não está nas listas de permissão do agente, ou o agente não consegue responder de jeito nenhum (sem `LLM_API_KEY`, ou `AGENT_ENABLED=false`). No segundo caso, o log do agente traz uma linha ERROR com a causa.
- A solicitação dura até o turno terminar, que é um debounce curto mais o tempo do modelo. As chamadas ao modelo de um turno dividem um único orçamento de 1,5 × `LLM_TIMEOUT_S`, novas tentativas incluídas, tanto em um grupo quanto em uma mensagem direta, e uma mensagem que chega enquanto um turno anterior da sua conversa ainda está pensando aguarda esse turno terminar antes de começar o seu. Reserve pelo menos 3 × `LLM_TIMEOUT_S` segundos (360 com o padrão).
- Um comando de memória (como "remember ...") que chega enquanto um turno da sua conversa ainda está pensando é respondido depois desse turno. Um conector que declarou `outbox` recebe `{"handled": false, "owned": true, "replies": []}` na hora e o resultado depois, como uma entrega `follow_up`. Sem `outbox`, o resultado vem na resposta a uma solicitação: a dele mesmo ou a de outra solicitação em espera da mesma conversa, então uma resposta pode trazer `replies` que mencionam outra pessoa que não o remetente do evento.

## Caixa de saída: `POST /v1/outbox`

Algumas mensagens não respondem a uma solicitação. Exemplos são uma abertura agendada, a pergunta de acompanhamento depois de uma rejeição, a resposta a um comando de memória que esperou atrás de um turno e a desculpa quando o modelo está fora do ar em um grupo. O agente as enfileira por conversa, e um conector que declarou `outbox` as busca, então um conector atrás de NAT ou firewall funciona do mesmo jeito. Conversas guardadas com ids de QQ sem prefixo (veja Endereçamento) também usam a caixa de saída enquanto o conector delas estiver consultando. Caso contrário, passam pela API HTTP do NapCat, quando `QQ_ONEBOT_URL` está definido.

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

`items` tem a mesma forma de `replies`. `reason` é `proactive`, `follow_up` ou `excuse`, e `conversation_type` é `group` ou `dm`. `conversation_key` é a chave sob a qual o agente guarda a conversa, como `private:telegram:42` para uma mensagem direta. `conversation_id` é o id bruto que o evento trouxe, que em uma mensagem direta é o id do usuário. O agente lembra `reply_handle`, `connector_id` e `capabilities` do último evento admitido em cada conversa, então uma conversa fica alcançável depois de enviar uma mensagem.

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

## Falar primeiro sem a caixa de saída

Um conector que não consegue consultar ainda pode abrir uma mensagem direta. O próprio agendador dele, como uma tarefa de plugin do AstrBot ou uma entrada de cron, envia um evento comum de mensagem direta com `"proactive": true` para `/v1/events`. O agente lê o texto como uma deixa para a persona ("está quieto há um dia; a prova era hoje de manhã"), corta em 500 caracteres e nunca o guarda como palavras da pessoa. As instruções proativas do motor continuam decidindo o turno e podem manter a persona em silêncio. Se a persona falar, a resposta volta na resposta HTTP para o agendador repassar.

O evento precisa de tudo o que os eventos normais do conector trazem: os cabeçalhos assinados, todos os campos obrigatórios, o mesmo `platform` e `sender_id` bruto que o conector envia para essa pessoa, texto não vazio e um `message_id` novo a cada vez. Um evento com `message_id` repetido é descartado em silêncio. A deixa conta para o mesmo intervalo de mensagens diretas que as aberturas do próprio agente (`PROACTIVE_DM_COOLDOWN_S`), e não conta como atividade da pessoa.

Defina sempre o indicador; sem ele, o agente guarda a deixa como palavras da pessoa. Um evento de grupo com o indicador é assumido (`owned: true`, para o conector manter o próprio bot quieto) e descartado sem ler.

## Capacidades e o que piora

| Faltando | Efeito |
|---|---|
| `outbox` | Sem aberturas agendadas, sem pergunta de acompanhamento e sem desculpa quando uma chamada ao modelo falha em um grupo. Ids de QQ ainda os recebem pelo NapCat quando `QQ_ONEBOT_URL` está definido e acessível. A desculpa de uma mensagem direta volta nos `replies` da resposta e não precisa da caixa de saída. |
| `quote_text` | O agente só entende uma mensagem citada se viu essa mensagem ele mesmo. |
| `reply_handle` | Igual a faltar `outbox`. |
| `addressed` errado | A persona trata mensagens dirigidas a ela como conversa de fundo. |

## Escrever um conector

1. Receba uma mensagem da plataforma. Ignore as mensagens do próprio bot e os eventos que não são mensagens (entradas, remoções, cutucadas).
2. Monte o evento descrito acima. Defina `addressed` pelas regras de menção e resposta da própria plataforma.
3. Assine e envie o evento. Envie `replies` em ordem e, quando `owned` for verdadeiro, mantenha outra lógica de bot quieta.
4. Se a plataforma puder enviar por conta própria, acrescente `connector_id`, `reply_handle` e `capabilities: ["outbox"]`, e execute o ciclo de consulta: consulte, entregue cada entrega pelo `reply_handle` dela e confirme na próxima consulta.

`integrations/sdk/personagent_connector.py` cuida das etapas 3 e 4.
