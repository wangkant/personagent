# astrbot_plugin_personagent

[English](README.md) · [简体中文](README.zh-CN.md) · [繁體中文](README.zh-TW.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Español](README.es.md) · [Français](README.fr.md) · [Deutsch](README.de.md) · Português (Brasil) · [Русский](README.ru.md)


Este plugin do [AstrBot](https://github.com/AstrBotDevs/AstrBot) conecta o AstrBot ao [personagent](https://github.com/wangkant/personagent). Ele encaminha cada mensagem permitida ao agente e devolve as respostas do agente ao chat.

## Você precisa dele?

Não para QQ, WeChat, Telegram ou Discord. O personagent os conecta por conta própria, sem AstrBot. Execute `personagent` para abrir a página local e adicione-os em **Conectar apps**.

Você precisa deste plugin quando o AstrBot carrega a conversa. Isso acontece em dois casos.

- **Você adiciona outra plataforma na página do personagent.** KOOK, Feishu/Lark, DingTalk, Slack, bot de IA do WeCom, Mattermost, Misskey e as plataformas em Avançado passam todas pelo AstrBot. A página baixa e executa um AstrBot para você e instala este plugin nele, então não há nada a fazer aqui.
- **Você já executa um AstrBot** com plataformas e plugins próprios. Instale o plugin como descrito abaixo.

## O que ele faz

- Recebe mensagens de grupo e mensagens diretas de todos os adaptadores de plataforma do AstrBot (Telegram, Discord, Slack, QQ...), exceto os de `excluded_platforms`.
- Encaminha mensagens de grupos e remetentes da lista de permissão ao `POST /v1/events` do agente como evento neutro de plataforma. Ele lê cada plataforma do jeito que o adaptador a entrega, incluindo a quem a mensagem se dirige, o que foi citado, figurinhas, imagens, mensagens de voz e a hora em que a plataforma diz que foi enviada.
- Devolve as respostas do agente pelo AstrBot na forma que cada plataforma espera. As respostas podem levar texto e imagens e, em chats em grupo, uma menção quando o agente pede.
- Consulta a caixa de saída do agente para entregar o que ele diz sem ser solicitado, como uma mensagem programada, uma pergunta de acompanhamento ou a desculpa que ele publica em um grupo quando o modelo está fora do ar. Veja [Caixa de saída](#caixa-de-saída).
- Interrompe o pipeline do próprio AstrBot quando o agente assume a conversa (`block_default`), para que o modelo embutido do AstrBot nunca responda no lugar da persona.

A persona, a memória, o debounce e a simulação de digitação rodam todos no agente. Este plugin é um conector como definido no [`docs/connectors.md`](https://github.com/wangkant/personagent/blob/main/docs/connectors.pt-BR.md) do agente.

## Instalar no seu próprio AstrBot

Você precisa do AstrBot, iniciado pelo menos uma vez para que a pasta de dados exista, e do personagent (`python -m pip install personagent`; veja o README dele).

### Com a configuração do personagent

```bash
personagent connect astrbot
```

O comando primeiro procura a pasta de dados do AstrBot, a que contém `cmd_config.json`, `plugins/` e `config/`. Se não encontrar nenhuma, oferece baixar o AstrBot. Depois pergunta se o AstrBot roda no Docker, em qual app de chat o bot entra (com o token desse app, onde o AstrBot ainda precisa de um), os grupos, o administrador e quem pode enviar mensagens diretas ao bot. Para QQ pelo NapCat, também pergunta o número da conta do bot. Por fim, copia este plugin, gera um token compartilhado, grava-o nos dois lados e grava as listas de permissão. `personagent init --terminal` oferece a mesma etapa no final.

Para pular as perguntas, passe a pasta de dados:

```bash
personagent connect astrbot <AstrBot data dir>        # add --qq to route QQ (NapCat) as well
```

Executado assim, uma primeira conexão deixa as listas de permissão **vazias**, e você as preenche nas configurações do plugin. `personagent connect astrbot --help` lista as flags que também ativam uma plataforma no AstrBot.

Você pode executar o comando de novo a qualquer momento. Ele mantém as listas de permissão, outras plataformas excluídas e qualquer `personagent_url` que este plugin aceite (veja [Onde o agente pode rodar](#onde-o-agente-pode-rodar)). Um `personagent_url` que o plugin recusaria é substituído pelo padrão de loopback. O roteamento do QQ só muda quando você passa `--qq` ou `--no-qq`, e o `CONNECTOR_QQ_PLATFORMS` do agente acompanha. Quando ele pergunta, as listas atuais são os padrões: pressione Enter para manter uma ou digite `-` para limpá-la.

Depois reinicie o AstrBot e inicie o agente (veja [Verificar se funciona](#verificar-se-funciona)).

### Pela WebUI do AstrBot

1. Baixe `astrbot_plugin_personagent.zip` da [versão mais recente do personagent](https://github.com/wangkant/personagent/releases/latest).
2. Envie-o em **Install from File** na página de plugins do AstrBot.
3. Defina `connector_token` como o `CONNECTOR_TOKEN` do `.env` do personagent e preencha as listas de permissão como descrito abaixo.
4. Se o AstrBot roda em outro computador que não o do personagent, defina `personagent_url` como um endereço HTTPS (veja [Onde o agente pode rodar](#onde-o-agente-pode-rodar)).

Para atualizar, envie o zip da versão mais nova do mesmo jeito. O AstrBot 4.29 e posteriores substituem a cópia instalada. Em versões mais antigas, desinstale o plugin primeiro e deixe **Also delete plugin configuration file** desmarcado.

### Manualmente

1. Copie esta pasta para `<AstrBot data dir>/plugins/astrbot_plugin_personagent/`.
2. Reinicie o AstrBot ou recarregue os plugins na WebUI. O AstrBot instala `requirements.txt`, que lista apenas `httpx`.
3. Abra as configurações do plugin na WebUI. Elas são salvas em `<AstrBot data dir>/config/astrbot_plugin_personagent_config.json`.
   - Adicione a `groups` os IDs de grupo em que a persona pode entrar.
   - Adicione a `dm_users` os IDs de remetente cujas mensagens diretas ela pode responder.
   - Se o `.env` do agente define `CONNECTOR_TOKEN`, coloque o mesmo valor em `connector_token`. É obrigatório quando o agente está em outro host.
   - Deixe `personagent_url` no padrão quando o agente roda no mesmo host com o `SERVER_PORT=8080` padrão.

O plugin **nega por padrão**. Com listas vazias, ele não encaminha nada, e o AstrBot se comporta como se o plugin não estivesse instalado. Escreva os IDs como o AstrBot os mostra; envie `/sid` em um chat para vê-los. Um ID sem prefixo corresponde em todos os adaptadores. `qq_official:ID` corresponde apenas nesse adaptador, e `qq_official:*` encaminha todas as conversas desse tipo nele.

Um `*` sozinho em `groups` ou `dm_users` encaminha todas as conversas desse tipo em todos os adaptadores e as marca como `prefiltered: false`. Então decidem sozinhos `ACCESS_GROUPS` e `ACCESS_DM_USERS` do próprio agente. O agente recusa uma plataforma sem entradas ali, exceto grupos do QQ, aos quais responde a menos que `ACCESS_GROUPS` liste algum.

### Verificar se funciona

1. Inicie o agente com `personagent run`, que inicia apenas o servidor. O banner deve mostrar `agent: on`.
2. Diga o nome do bot (o `PERSONA_NAME` do agente) em um grupo permitido.

Se nenhuma resposta chegar, procure linhas `personagent:` no log do AstrBot, leia o que `personagent run` imprimiu depois do banner e veja [Solução de problemas](#solução-de-problemas).

## Configuração

| Chave | Tipo | Padrão | Descrição |
| --- | --- | --- | --- |
| `personagent_url` | string | `http://127.0.0.1:8080` | URL base do agente. O plugin acrescenta `/v1/events` e `/v1/outbox`. Precisa ser loopback, ou HTTPS com `connector_token` definido. |
| `connector_token` | string | `""` | Segredo compartilhado. Precisa ser igual ao `CONNECTOR_TOKEN` do agente. Obrigatório para qualquer `personagent_url` que não seja loopback. |
| `timeout_s` | int | `420` | Segundos de espera em cada tentativa. Veja [Tempos limite](#tempos-limite). |
| `excluded_platforms` | list | `["aiocqhttp"]` | Nomes de adaptadores nunca encaminhados. Remova `aiocqhttp` para rotear o QQ (NapCat) por este plugin. Veja [QQ pelo NapCat](#qq-pelo-napcat). |
| `groups` | list | `[]` | IDs de grupo a encaminhar. Vazio não encaminha nenhum grupo. `adapter:ID` ou `adapter:*` limita uma entrada a um adaptador. Um `*` sozinho encaminha todos os grupos sem filtro. |
| `dm_users` | list | `[]` | IDs de remetente cujas mensagens diretas são encaminhadas. Vazio não encaminha nenhuma. `adapter:ID` ou `adapter:*` limita uma entrada a um adaptador. Um `*` sozinho encaminha todas as mensagens diretas sem filtro. |
| `block_default` | bool | `true` | Interrompe o pipeline do AstrBot quando o agente assume a conversa. |
| `forward_quoted_text` | bool | `true` | Envia o texto e o autor de uma mensagem citada junto com o id, quando a plataforma os fornece. Enquanto isto estiver ativo e `quote_max_chars` for maior que 0, todo evento declara o recurso `quote_text`. |
| `quote_max_chars` | int | `200` | Maior texto citado enviado. Citações mais longas são cortadas. |
| `max_inline_image_bytes` | int | `4000000` | Maior imagem enviada inline. Imagens que o agente não consegue buscar sozinho (Telegram, arquivos locais, endereços privados) vão inline. Uma maior chega como a nota `(sent an image)`. Mantenha abaixo de `VISION_MAX_IMAGE_BYTES` do agente. |
| `outbox_enabled` | bool | `true` | Consulta e entrega a caixa de saída do agente. Veja [Caixa de saída](#caixa-de-saída). |
| `outbox_wait_s` | int | `25` | Quanto uma consulta da caixa de saída pode esperar no agente, no máximo 30. |
| `connector_id` | string | `""` | Nome deste AstrBot para o agente. Vazio gera um uma vez e o mantém. Dois hosts de AstrBot precisam de nomes diferentes. |

### Onde o agente pode rodar

- **Mesmo host**, ou um contêiner que compartilha o namespace de rede do host ou usa a rede do host: mantenha o `personagent_url` de loopback padrão.
- **Outro contêiner ou host**: use um `personagent_url` HTTPS e defina o mesmo segredo não vazio em `connector_token` e no `CONNECTOR_TOKEN` do agente. Um túnel privado que termine em uma URL de loopback visível para o AstrBot também funciona. Nesse caso, defina também o mesmo token nos dois lados, porque o agente recusa solicitações sem token que chegam por um proxy.

O plugin recusa `http://` sem criptografia para qualquer coisa que não seja loopback, como `http://host.docker.internal:8080`, mesmo com token. Cada mensagem então registra `refusing unsafe personagent_url`, e o modelo do próprio AstrBot responde no lugar.

**AstrBot no Docker.** Dentro de um contêiner, `127.0.0.1` é o próprio contêiner, então o `personagent_url` padrão não alcança nada. Você tem duas opções:

- Dê ao AstrBot a rede do host: `network_mode: host` no arquivo compose, ou `docker run --network host`. O Docker Desktop precisa da versão 4.34 ou posterior com host networking ativado. Um contêiner do NapCat no mesmo arquivo compose também precisa da rede do host.
- Coloque o agente atrás de HTTPS e defina esse endereço como `personagent_url` (`personagent connect astrbot <dir> --url https://...`).

O agente escuta em `127.0.0.1:8080` por padrão. Se você definir o `SERVER_HOST` dele como um endereço que não seja loopback, ele se recusa a iniciar sem `CONNECTOR_TOKEN`. Defina o token antes de colocar um proxy ou túnel na frente do agente, mesmo em um único host.

### Tempos limite

Cada solicitação dura o mesmo que o turno do agente, que é um debounce curto mais cada chamada ao modelo e nova tentativa. Se `timeout_s` acabar, o agente ainda termina o turno e guarda o que aprendeu, mas a resposta se perde e o modelo do próprio AstrBot responde à mensagem.

Mantenha 3 × `LLM_TIMEOUT_S` do agente abaixo de `timeout_s`. As chamadas ao modelo de um turno dividem 1,5 × `LLM_TIMEOUT_S`, novas tentativas incluídas, e uma mensagem primeiro espera o turno que estava pensando quando ela chegou. Com o padrão do agente (`LLM_TIMEOUT_S=120`), isso dá 360 s, o que o `timeout_s` padrão de 420 cobre. Se você aumentar `LLM_TIMEOUT_S` no agente, aumente também `timeout_s`.

O plugin tenta de novo um 429 ou 500 do agente até duas vezes, respeitando `Retry-After` em um 429, enquanto a solicitação assinada ainda estiver recente.

### `block_default` e posse

O plugin interrompe o pipeline do AstrBot sempre que o agente informa que a conversa é dele (`owned: true`), tendo respondido ou não, para que o modelo embutido do AstrBot fique de fora dos turnos em que a persona não participa.

Erros de transporte, respostas inválidas e conversas que o agente recusa seguem para o pipeline normal do AstrBot. Se a resposta do agente não tiver o campo `owned`, o plugin usa `handled`.

## QQ pelo NapCat

O personagent conecta bots oficiais do QQ por conta própria, sem AstrBot. Esta seção cobre apenas uma conta do QQ executada pelo NapCat (ou outra implementação do OneBot v11) atrás do adaptador `aiocqhttp` do AstrBot. Quando você adiciona OneBot v11 na própria página do personagent, ela remove `aiocqhttp` de `excluded_platforms` e define `CONNECTOR_QQ_PLATFORMS` para você.

1. Remova `aiocqhttp` de `excluded_platforms` e adicione os grupos do QQ a `groups`.
2. No `.env` do agente, defina `CONNECTOR_QQ_PLATFORMS=aiocqhttp` e `QQ_BOT_ID` (o número da conta do bot).
3. Opcional: defina o `QQ_ONEBOT_URL` do agente como o servidor HTTP do NapCat. Isso ativa a varredura de menções perdidas, que também precisa de `QQ_BOT_ID`. Mensagens proativas, a pergunta de acompanhamento após uma rejeição e a desculpa de um grupo quando o modelo falha passam pela [caixa de saída](#caixa-de-saída) deste plugin enquanto ele estiver consultando. Caso contrário, passam direto pelo NapCat, desde que essa URL esteja definida.
4. Se o NapCat também publica no `/v1/onebot` do agente, desative isso. A rota está obsoleta, e executar as duas entrega cada mensagem duas vezes.

`personagent connect astrbot <data dir> --qq` remove `aiocqhttp` de `excluded_platforms` e define `CONNECTOR_QQ_PLATFORMS`. Executado sem pasta, também pergunta `QQ_BOT_ID`. O guia de implantação também cobre este caminho: [docs/deploy.md](https://github.com/wangkant/personagent/blob/main/docs/deploy.pt-BR.md#qq-pelo-napcat-onebot).

Não omita `CONNECTOR_QQ_PLATFORMS=aiocqhttp`. Sem ele, o agente arquiva os chats do QQ sob IDs com prefixo `aiocqhttp:`, o que foi aprendido sob os IDs simples do QQ deixa de corresponder e os registros não podem ser reindexados depois.

Como os IDs do QQ continuam simples, as configurações de QQ do próprio agente continuam valendo. As entradas de QQ em `ACCESS_GROUPS` filtram os grupos (sem entradas significa todos os grupos do QQ), e só são respondidas as mensagens diretas do administrador em `ADMIN_IDS` ou de quem está em `ACCESS_DM_USERS`. O assistente grava no `.env` do agente os grupos do QQ que você informa. Para adicionar um grupo do QQ depois, adicione-o tanto a `groups` quanto a `ACCESS_GROUPS`, ou não liste nenhum grupo do QQ em `ACCESS_GROUPS`.

Antes de o AstrBot carregar um grupo do QQ movimentado, revise duas configurações do AstrBot. As duas rodam antes dos manipuladores de plugins.

- `platform_settings.rate_limit` tem padrão de 30 mensagens por 60 s. Mensagens acima do limite são atrasadas, não descartadas. Aumente ou desative o limite.
- `content_safety.internal_keywords` vem ativado e descarta mensagens que correspondem à lista de palavras-chave, incluindo as que a persona teria respondido. Revise a lista.

## Plataformas

O agente fala um formato neutro, e o plugin traduz nas bordas usando os mecanismos próprios de cada plataforma. A tabela abaixo foi conferida com os adaptadores do AstrBot 4.25.5.

Em todas as plataformas:

- Só são encaminhadas mensagens escritas por uma pessoa. Avisos do QQ (cutucadas, retiradas, entradas) e solicitações, e entradas e mudanças de tópico do Slack, não são turnos.
- Vídeos, arquivos e mensagens de voz chegam como uma nota à qual a persona pode reagir, como `(sent a video)`, `(sent a file: deck.pdf)` ou `(sent a voice message)`, com a transcrição da plataforma quando ela tem uma.
- Mensagens citadas trazem texto e autor quando a plataforma os fornece (`forward_quoted_text`).
- Onde o adaptador a mantém, a hora da mensagem é a da plataforma, e não a hora em que o AstrBot a recebeu.
- As respostas são divididas abaixo do limite de tamanho da plataforma, contando a menção e os escapes como a plataforma conta. Nunca viram uma imagem de texto, e citam as pessoas como a plataforma faz.
- A caixa de saída só é usada onde a plataforma pode enviar sem solicitação.

| Plataforma (adaptador) | O que funciona | O que a própria plataforma não consegue fazer |
| --- | --- | --- |
| QQ via OneBot (`aiocqhttp`) | Grupos e mensagens diretas. @ e resposta ao bot, também quando o adaptador não conseguiu resolver o @. Nomes de rostos, figurinhas da loja (`mface`) e imagens marcadas como figurinhas. Menções como um @ real do QQ, seguido de um espaço. Respostas longas são divididas abaixo do `forward_threshold` do AstrBot, então nenhuma vira um cartão de encaminhamento combinado. Caixa de saída. | Markdown aparece como digitado. |
| QQ oficial (`qq_official`, `qq_official_webhook`) | Mensagens de grupo que dão @ no bot e mensagens diretas. Rostos como `[表情:name]`. As respostas pedem texto simples em vez do markdown do adaptador. | Os grupos entregam só mensagens que dão @ no bot, então a persona não consegue acompanhar uma conversa. Sem citações, sem nomes (só openids), sem menções nas respostas. Só é possível responder até 5 minutos depois de uma mensagem, então não há caixa de saída. |
| Telegram (`telegram`) | Grupos, tópicos (`<chat>#<thread>`) e mensagens diretas. Resposta ao bot para qualquer tipo de mensagem, sem o prefixo de ativação `/@bot` do adaptador. Emoji de figurinhas, mais a imagem das estáticas. Imagens buscadas pelo bot do adaptador, então o token do bot nunca sai do AstrBot. Um nome de usuário mencionado vira o id numérico da pessoa depois que ela escreve. As respostas mencionam por nome de usuário, ou por um link `tg://user` para quem não tem, e mostram `*`, `_` e caracteres parecidos como digitados. Caixa de saída. | Com o modo de privacidade do BotFather ativo (o padrão), os grupos entregam só comandos, @menções e respostas ao bot. Desative-o para que a persona possa acompanhar a conversa. Figurinhas animadas e de vídeo não podem ser vistas. |
| Discord (`discord`) | Canais e threads como grupos, e mensagens diretas. Um `@bot` inicial (que o adaptador remove), um ping de um dos cargos do bot e respostas ao bot se dirigem a ele. Citações com texto. Figurinhas. Anexos de voz e vídeo como notas. Menções como `<@id>`, com `@everyone` e `@here` inertes. Respostas divididas em 2000 caracteres. Caixa de saída, incluindo mensagens diretas. | Precisa do intent Message Content. |
| Slack (`slack`) | Canais e mensagens diretas. Uma resposta em thread sob a mensagem do bot se dirige a ele. Links expandidos. Os ids de mensagem são o `ts` do Slack. Menções como `<@id>`. `&`, `<` e `>` escapados para que o texto não possa acionar um canal. Respostas divididas em 3000 caracteres. Caixa de saída. | Uma resposta em thread não traz o texto da mensagem pai. Sem indicador de digitação para bots. As respostas caem no canal, não na thread (adaptador). |
| KOOK (`kook`) | Canais e mensagens diretas. @ e pings de um cargo que o bot tem. Citações quando o KOOK as inclui. Emoji `(emj)` e a hora real de envio. Menções no texto, com as tags no estilo `(met)` do texto da persona inertes. Imagens enviadas como arquivo, pois o adaptador só envia JPEG base64. Caixa de saída. | O adaptador do AstrBot descarta mensagens simples de imagem, arquivo, voz e vídeo (não cartões) antes que qualquer plugin as veja. Sem indicador de digitação. |
| Lark / Feishu (`lark`) | Grupos e mensagens diretas. @ e respostas ao bot (o Lark nomeia o app como remetente). Citações com texto. Figurinhas como emoji. Caixa de saída. | Sem a permissão "ler todas as mensagens do grupo", só chegam mensagens com @. Toda resposta cita a mensagem que responde, e o markdown é renderizado (adaptador). Os nomes são prefixos de id. |
| DingTalk (`dingtalk`) | Grupos e mensagens diretas. As imagens, que o adaptador entrega como arquivos locais, vão inline. Vídeos como nota. Caixa de saída. Mensagens diretas alcançam quem escreveu ao bot. | Os grupos entregam só mensagens que dão @ no bot. Sem citações, e sem menções ou respostas com citação nas respostas. Toda resposta é markdown com o título "AstrBot" (adaptador). |
| LINE (`line`) | Grupos, salas e mensagens diretas. @ no bot. Ids de citação. Palavras-chave de figurinhas. Os balões de um turno são enviados em uma chamada, cinco por vez, para que o reply token gratuito os cubra. Caixa de saída, que conta na cota de push. | O LINE não envia o texto citado. Sem menções nas respostas (adaptador). Imagens enviadas precisam de um `callback_api_base` HTTPS público. Os nomes são prefixos de id. |
| Mattermost (`mattermost`) | Canais e mensagens diretas. @ no bot. Raiz da thread como citação. Imagens inline. Menções por nome de usuário depois que a pessoa escreve. `@channel`, `@all` e `@here` inertes. Respostas divididas em 4000 caracteres. Caixa de saída. | O texto citado exigiria uma consulta que o plugin não faz. Sem indicador de digitação. |
| Misskey (`misskey`) | Mensagens diretas de chat e salas, com `@bot` em qualquer lugar de uma mensagem de sala. Menções como `@user@host` depois que a pessoa escreve, com qualquer outro `@` do texto da persona inerte. Respostas divididas em 3000 caracteres. Caixa de saída para chat e salas. | Notas (publicações públicas) não são encaminhadas, porque o AstrBot as classifica como eventos de sistema e uma resposta seria pública. `unique_session` quebra as salas (adaptador). |
| Satori (`satori`) | O que o backend Satori fizer de ponte: grupos, mensagens diretas, @, respostas ao bot, citações com texto. Carimbos de data/hora em milissegundos lidos como segundos. Caixa de saída. | O id do grupo é a guilda, então os canais de uma guilda compartilham uma conversa. Valem os limites da plataforma conectada. |
| WebChat (`webchat`) | O chat do painel, como mensagens diretas. Citações e imagens. Caixa de saída, mostrada ao vivo ou salva na conversa. | Só um a um. |
| App WeCom (`wecom`) | Mensagens diretas, imagens e voz com transcrição. O modo de atendimento ao cliente encaminha só as mensagens do cliente, com a hora real de envio. Respostas divididas por bytes. Caixa de saída no modo app, depois que alguém escreve desde o início do AstrBot. | Só mensagens diretas, sem citações. O modo de atendimento ao cliente não pode enviar sem solicitação. Markdown aparece como digitado. |
| Bot de IA do WeCom (`wecom_ai_bot`) | Grupos (o WeCom entrega uma mensagem de grupo só quando o bot recebe @) e mensagens diretas. Notas de voz, arquivo e vídeo. Um turno enviado como uma resposta em streaming. | Só responde dentro da resposta a uma mensagem, então não há caixa de saída nem menções. A resposta é renderizada como markdown. Defina `wecom_ai_bot_name` no AstrBot para que "@bot" seja removido do texto. |
| Conta oficial do WeChat (`weixin_official_account`) | Mensagens diretas e voz com transcrição. Um turno enviado como uma mensagem. | O modo passivo entrega uma resposta por mensagem do usuário, dentro da janela de 5 s do WeChat. O resto espera a próxima mensagem do usuário, e um turno em que a persona não participa deixa o usuário esperando (adaptador). Imagens só no modo ativo. Sem caixa de saída. |
| WeChat pessoal (`weixin_oc`) | Mensagens diretas. Citações com texto. Imagens inline. Voz com transcrição. Indicador de digitação. Caixa de saída. | Sem grupos. Depois de um novo login, ninguém pode ser alcançado até escrever de novo. |
| Qualquer outro adaptador | Encaminhado como o AstrBot entrega. Menções como At. | Caixa de saída não declarada. |

## Caixa de saída

Algumas mensagens não respondem a nada: uma mensagem programada, a pergunta de acompanhamento após uma rejeição ou a desculpa em um grupo quando o modelo está fora do ar. (A desculpa de uma mensagem direta volta na resposta do próprio evento.) O agente coloca essas mensagens em fila, e este plugin as busca em `POST <personagent_url>/v1/outbox` com a mesma assinatura dos eventos, então o agente nunca precisa alcançar o AstrBot. A caixa de saída vem ativada (`outbox_enabled`).

- Cada entrega sai pela própria sessão do AstrBot da conversa, em ordem, e cada mensagem é enviada no máximo uma vez.
- Uma entrega vai só para uma sessão que o próprio plugin obteve de uma mensagem dessa mesma conversa. Essas sessões ficam no armazenamento de plugins do AstrBot, então sobrevivem a um recarregamento. Nada mais que publique um evento no agente pode apontar a caixa de saída para outro chat, e o plugin recusa essa entrega.
- O plugin confere de novo as listas de permissão e `excluded_platforms` na hora do envio e recusa uma conversa removida nesse meio-tempo.
- Plataformas que não podem falar primeiro (veja a tabela) nunca recebem mensagens da caixa de saída, porque o plugin não a declara para as conversas delas.
- Um agente sem caixa de saída responde 404. O plugin pergunta de novo a cada dez minutos.

O agente conhece este AstrBot por `connector_id`, que o plugin gera uma vez e mantém. Dois hosts de AstrBot falando com um agente precisam de ids diferentes.

## Autenticação de solicitações

Quando `connector_token` está definido, toda solicitação leva quatro cabeçalhos:

- `X-Personagent-Token`: o token.
- `X-Personagent-Timestamp`: segundos unix.
- `X-Personagent-Nonce`: um valor aleatório novo.
- `X-Personagent-Signature`: `sha256=` seguido do HMAC-SHA256 em hexadecimal, com o token como chave, de `timestamp + "." + nonce + "." + body`.

O corpo é JSON canônico: UTF-8, chaves ordenadas, separadores compactos e caracteres não ASCII sem escape. A assinatura cobre esses bytes exatos, então um proxy não pode reescrever o corpo. O agente rejeita uma assinatura incorreta, um nonce reutilizado ou um carimbo de data/hora a mais de cinco minutos do próprio relógio. Mantenha os dois relógios sincronizados.

O corpo também leva a hora da mensagem segundo o adaptador como `sent_at`. O agente a verifica separadamente com `CONNECTOR_MAX_EVENT_AGE_S` (24 horas por padrão), então um evento antigo reenviado com assinatura nova ainda é rejeitado. O plugin não encaminha uma mensagem cujo adaptador não dá um carimbo válido, e o AstrBot a trata como de costume.

## Identidades no lado do agente

O agente prefixa cada id encaminhado com a plataforma, como `<platform>:<raw id>` (por exemplo, `telegram:12345`), então ids de plataformas diferentes nunca colidem. Plataformas listadas em `CONNECTOR_QQ_PLATFORMS` mantêm ids simples. `ADMIN_IDS`, `ACCESS_GROUPS` e `ACCESS_DM_USERS` do agente aceitam ids na mesma forma. Por exemplo, `ADMIN_IDS=telegram:12345` torna essa conta administradora no Telegram, em grupos e mensagens diretas. Uma plataforma com entradas em `ACCESS_GROUPS` ou `ACCESS_DM_USERS` é filtrada pelo agente além das listas de permissão deste plugin.

## Solução de problemas

As linhas do plugin no log do AstrBot começam com `personagent:`.

| Mensagem de log | O que fazer |
| --- | --- |
| `refusing unsafe personagent_url` | `personagent_url` é HTTP sem criptografia para outro host, ou HTTPS sem `connector_token`. Veja [Onde o agente pode rodar](#onde-o-agente-pode-rodar). |
| `agent refused the request (403): invalid, stale, or replayed request envelope` | `connector_token` está vazio ou não corresponde ao `CONNECTOR_TOKEN` do agente, os dois relógios diferem em mais de cinco minutos, ou um proxy alterou o corpo. Se o log do agente disser `connector replay guard full`, espere esvaziar. |
| `agent refused the request (403): stale or invalid sent_at` | A mensagem é mais antiga que `CONNECTOR_MAX_EVENT_AGE_S` do agente. Isso costuma acontecer depois que o AstrBot entrega um acúmulo. |
| `agent refused the request (403): authentication required` ou `... only local requests accepted` | O agente não tem `CONNECTOR_TOKEN` e a solicitação não é local. Defina o mesmo token nos dois lados. |
| `agent at capacity (429)` | O agente já executava `CONNECTOR_MAX_INFLIGHT` turnos e ainda recusou a mensagem depois das tentativas, então o modelo do próprio AstrBot respondeu. Aumente `CONNECTOR_MAX_INFLIGHT` se isso acontecer com frequência. |
| `agent rejected the body as too large (413)` | Geralmente uma imagem inline grande. Aumente `SERVER_MAX_BODY_BYTES` do agente. |
| `agent rejected the event schema (400)` | O evento não tinha id de mensagem ou de remetente (alguns adaptadores os omitem), ou este plugin tem um bug. Informe com a linha do log. |
| `timed out waiting for the agent` | Veja [Tempos limite](#tempos-limite). |
| `dropping event without a valid time the platform sent it` | O adaptador não deu carimbo de data/hora. O AstrBot trata essa mensagem por conta própria. |
| `agent request failed: ...` ou `agent request failed (<status>)` | Geralmente o agente não está rodando ou `personagent_url` está errado. Um 404 significa caminho errado: `personagent_url` é a URL base, sem `/v1/events`. Um 500 significa que o agente falhou, então veja o log dele. |
| `outbox off: ...` | A caixa de saída segue a mesma regra de `personagent_url` dos eventos. Veja a primeira linha. |
| `outbox: agent has no outbox (turned off, or an older version); retrying in 10 minutes` | `CONNECTOR_OUTBOX_ENABLED` do agente está desativado. |
| `outbox: outbox pull refused (403)` ou `outbox pull failed: ...` | As mesmas causas dos eventos: o token, os relógios ou o agente parado. O plugin espera até um minuto entre as tentativas. |
| `outbox: no running platform '<id>'` | Uma entrega para um adaptador desativado ou renomeado no AstrBot. O plugin a informa ao agente como falha. |
| `could not store connector_id` | O armazenamento de plugins do AstrBot falhou. Defina `connector_id` você mesmo, ou o agente verá um AstrBot novo depois de cada reinício. |

Se o modelo do próprio AstrBot de repente responder com outra voz, o plugin não alcançou o agente, ou o agente não assumiu a conversa. Confira a tabela acima e execute `personagent doctor`. Se a página local iniciou o agente, abra **Atividade** ali para ver se a mensagem chegou e por que a persona ficou em silêncio. Se você o iniciou com `personagent run`, leia o terminal dele.

Se o próprio log do agente disser que o conector envia `X-Personagent-Token` mas `CONNECTOR_TOKEN` está em branco, o agente está ignorando o token. Defina o mesmo valor no `.env` do agente.

No QQ, Telegram, Discord, KOOK, QQ oficial e Misskey, a hora da mensagem é a da plataforma, não a hora em que o AstrBot a recebeu. Quando o AstrBot fica parado por mais tempo que `CONNECTOR_MAX_EVENT_AGE_S` do agente, o agente recusa como antigo o acúmulo que o AstrBot entrega.

## Limitação conhecida: menções no Telegram

O adaptador de Telegram do AstrBot identifica um remetente pelo id numérico de usuário (`telegram:<numeric id>`), mas identifica uma menção `@username` em uma mensagem só pelo nome de usuário. O plugin reescreve um nome de usuário mencionado para o id numérico de quem o usa depois que essa pessoa escreve desde o início do AstrBot. Até lá, a menção chega ao agente com o nome de usuário.

As respostas mencionam alguém por nome de usuário, ou com um link `tg://user` quando a pessoa não tem. O plugin não menciona quem não viu desde o início do AstrBot.
