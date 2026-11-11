# Implantar o personagent

[English](deploy.md) · [简体中文](deploy.zh-CN.md) · [繁體中文](deploy.zh-TW.md) · [日本語](deploy.ja.md) · [한국어](deploy.ko.md) · [Español](deploy.es.md) · [Français](deploy.fr.md) · [Deutsch](deploy.de.md) · Português (Brasil) · [Русский](deploy.ru.md)

O [início rápido](start.pt-BR.md) e o [guia do usuário](guide.pt-BR.md) levam você até a primeira conversa. Eles cobrem a instalação, a [pasta inicial](guide.pt-BR.md#instalação-e-a-pasta-inicial), a configuração na página local e a conexão de uma plataforma. Este guia cobre o que uma implantação real precisa e o que verificar quando o bot fica em silêncio.

## A menor configuração que funciona

A página local (`personagent`, ou `personagent init --terminal` para o assistente de terminal) verifica a chave com uma pequena requisição e depois grava `.env` na pasta inicial. Conversar exige uma chave, e `.env.example` começa com os modelos gratuitos do OpenRouter:

```
LLM_API_KEY=...
LLM_BASE_URL=https://openrouter.ai/api/v1
LLM_MODEL=openrouter/free
```

Um `.env` que define só a chave significa `https://api.deepseek.com` e `deepseek-flash`. Você pode apontá-los para qualquer endpoint compatível com OpenAI, hospedado ou local (Ollama, llama.cpp). Cole o endereço da API como o provedor documenta, seja uma raiz ou uma base com versão como `.../v1` ou `.../api/paas/v4`. Até você escrever um `persona.txt`, o `data/persona.example.<lang>.txt` incluído faz o papel dele. Até `PERSONA_NAME` ser definido (a configuração define), o personagem se chama "bot".

A página também grava `PERSONA_NAME`, `AGENT_LANG` e um `CONNECTOR_TOKEN`. Plataformas conectadas pela página não precisam de mais nada no `.env`. As credenciais vão para `<home>/platforms/`: `direct.json` guarda as plataformas que o personagent conecta por conta própria, e o AstrBot gerenciado guarda o restante na própria configuração. Adições opcionais:

```
ADMIN_IDS=telegram:12345             # the admin's accounts, <platform>:<id>
# QQ through NapCat (OneBot) only
QQ_BOT_ID=...                        # the bot account's number
CONNECTOR_QQ_PLATFORMS=aiocqhttp
```

As chaves ficam nesta máquina. O provedor de modelos que você escolher vê as conversas. Todo o resto de `.env.example` tem um padrão que funciona. `SERVER_HOST` e `SERVER_PORT` são `127.0.0.1:8080`, `QQ_ONEBOT_URL` fica vazio (sem servidor HTTP do NapCat), e um `ACCESS_GROUPS` vazio deixa todos os grupos para o conector.

## Executar

`personagent` abre a página local. Enquanto a página está aberta, ele executa o agente, o processo que mantém as plataformas conectadas diretamente e o AstrBot gerenciado, quando há um instalado. Executar `personagent` de novo reutiliza uma página aberta. `personagent up` inicia os mesmos processos sem navegador.

Em ambos os casos, esses processos são encerrados junto com ele, independentemente de como ele seja encerrado. O que uma execução anterior interrompida por falha tiver deixado em execução é encerrado na próxima inicialização. Cada processo grava seu log em `<home>/runtime/desktop/` (`agent.log`, `direct.log`, `astrbot.log`).

A página local e `personagent up` perguntam ao pypi.org no máximo uma vez por dia se saiu um personagent mais novo. Se saiu, a visão Conversa e o terminal mostram o comando que atualiza esta cópia. A requisição contém apenas o número da versão, e `UPDATE_CHECK_ENABLED=false` desativa a verificação.

`personagent run` inicia só o agente, como descreve [Executar o serviço](guide.pt-BR.md#executar-o-serviço). Use quando seus próprios conectores (um AstrBot que você executa, Satori, Matrix) falarem com ele. `personagent doctor` verifica as configurações e testa cada serviço externo.

**Configurações renomeadas na 1.0.** Enquanto algum nome de configuração que a 1.0 aposentou continuar definido, o início recusa com o código de saída 2 e lista cada um como `OLD -> NEW`. `personagent doctor --fix` os renomeia em `<home>/.env`. Ele mantém os valores e comentários, salva o arquivo antigo como `.env.bak` e comenta uma linha antiga cujo nome novo já esteja definido. Um nome aposentado definido no ambiente e não no `.env` precisa ser renomeado onde está definido. `personagent doctor` sai com 1 enquanto restar algum, e `--json` os lista em `retired_settings`. `HOST`, `PORT` e `LOG_FILE` só contam quando estão escritos no `.env`.

### Atividade

[Atividade](guide.pt-BR.md#atividade) é uma visão da página local. Não precisa de instalação extra, não carrega nada da internet e nunca mostra chaves ou tokens. Ela lê a API JSON do serviço do agente que a página local iniciou. Com `personagent run` sozinho, leia o log do serviço e use `personagent learned` e `personagent memory`. `DASHBOARD_ENABLED=false` desativa a API. A visão então informa isso, e `personagent doctor` imprime `activity: off (...)`.

A API fica em `/api/dashboard/` no serviço do agente:

- `GET conversations` e `GET conversation?id=<chat id>` leem as conversas que o serviço conhece e uma conversa em detalhe. Cada conversa em `conversations` traz `learned`, `observing` (o número de itens em observação) e `latest` (quando algo entrou em uso pela última vez). `conversation` devolve as listas `learned` e `observing`. Um item em observação traz `standing` (a etapa em que está, o que ainda lhe falta, o motivo do personagem e a data em que será deixado de lado); um item em uso traz `by` (`reactions`, `character` ou `person`) e `why`. A resposta também traz o que a conversa lembra: `memories`, `core_note` e `core_at`, `thread`, `episodes`, `removed` e `memory_status`.
- `POST candidates/<id>/promote`, `replace`, `reject`, `rollback` e `restore` são as ações opcionais de uma pessoa sobre o que ele aprendeu. Cada uma vai para o mesmo registro de `personagent learned`, com o ator `dashboard`. `restore` traz de volta o que o personagem ou o limite de tempo deixou de lado e o que o personagem ou uma regra tirou de uso; o que uma pessoa desfez ou deixou de lado, e o que uma regra de conteúdo descartou, continua como está. `promote` não traz de volta um item que foi desfeito.
- `POST memory/forget` com o corpo `{"conv": "<chat id>", "kind": "note", "id": "<id>"}` esquece um item e responde com o `tid` que `POST memory/restore` (`{"tid": "<tid>"}`) aceita para trazê-lo de volta. `kind` é `note`, `episode`, `thread` ou `core`. O corpo anterior `{"conv": "<chat id>", "note": "<note id>"}` continua funcionando e, sem `note`, esquece a nota principal da conversa.
- `POST memory/forget_chat` com `{"conv": "<chat id>"}` esquece tudo o que essa conversa lembra. Isso não pode ser desfeito.
- `GET memory/list?conv=<chat id>` lista o que cada conversa lembra e o que ainda pode ser restaurado; `personagent memory` o lê enquanto o serviço está em execução.

Toda chamada precisa do cabeçalho `X-Personagent-Dashboard-Token` com o token de `dashboard.token` na pasta de execução (`<home>/runtime/`, a menos que `AGENT_RUNTIME_DIR` a mova). Somente a conta de usuário do sistema que executa o serviço pode ler o arquivo, e o serviço o cria ao iniciar. Uma chamada sem o cabeçalho recebe 401 (`dashboard_token`), e um token errado recebe 403 (`wrong_token`). `CONNECTOR_TOKEN` e `X-Personagent-Token` não a abrem. Eles são só para conectores e `/health/details`.

- Gravações também precisam de `X-Personagent-Dashboard: 1` e `Content-Type: application/json`. Quando a requisição envia um `Origin`, ele deve ser o do próprio serviço.
- Requisições de navegador entre sites são recusadas.
- As respostas substituem toda credencial por `***`. URLs nas verificações de início também têm usuário, senha e query mascarados.
- Scripts no mesmo computador podem chamar a API da mesma forma que a página local.

O serviço não serve nenhuma página. `GET /` responde com uma nota curta que aponta para a página local e para `personagent learned`, e é isso que um link antigo com `?token=` abre agora. A página local se vincula só a 127.0.0.1. Em um servidor sem página local, `personagent learned` mostra o que o personagem aprendeu, o que está observando e por quê, e permite colocar um item em uso, deixá-lo de lado, desfazê-lo ou trazer de volta o que o personagem ou o limite de tempo deixou de lado e o que o personagem ou uma regra tirou de uso. `personagent memory` lista o que ele lembra e esquece ou restaura um item.

## O que o host precisa fornecer

1. **Uma pasta inicial gravável.** O início obtém um bloqueio em `<home>/.personagent.instance.lock`, fora de `runtime/`. Uma pasta inicial somente leitura não inicia.
2. **Um processo por pasta inicial.** Um segundo `personagent run` na mesma pasta sai com uma frase dizendo isso.
3. **Uma porta livre.** Uma porta ocupada ou proibida também sai com uma frase. Escolha outra com `--port` ou `SERVER_PORT`.

`AGENT_RUNTIME_DIR` precisa ser resolvido dentro da pasta inicial, ou o início falha. Um `PERSONA_FILE` ou `PERSONA_CARD_FILE` relativo também é resolvido dentro dela, então uma persona guardada em outro lugar precisa de um caminho absoluto.

Um `memory.json`, `core_memory.json` ou `episodes.json` danificado interrompe o início com o código de saída 2 e uma frase que nomeia o arquivo e a cópia `.bak` a colocar no lugar dele. O arquivo danificado não é alterado.

## Conectar plataformas

Adicione plataformas em **Conectar plataformas** na página local. O personagent verifica as credenciais com a plataforma antes de salvar qualquer coisa. Se a plataforma as recusar, a página mostra a recusa e não guarda nada.

Em um servidor sem monitor, conecte as plataformas que o personagent conecta por conta própria a partir de um terminal com `personagent connect <plataforma>`, por exemplo `personagent connect telegram`. O comando executa as mesmas etapas e verificações da página e salva os valores no mesmo formato. O QQ e o WeChat exibem o código QR no terminal, e a Twitch exibe um link e um código. Com `--no-input` e todos os valores informados como opções, o comando não faz nenhuma pergunta e sai com o código 2 quando falta um valor obrigatório. Em seguida, `personagent up` inicia o personagent com as plataformas conectadas. O guia do usuário descreve [o comando e as opções dele](guide.pt-BR.md#conectar-uma-plataforma-no-terminal).

**Conectadas pelo próprio personagent.** QQ, WeChat pessoal, Telegram, Discord, Matrix, Twitch, IRC, Zulip, VK e Stoat são executados em um único processo "direct", sem AstrBot e sem NapCat. Uma plataforma que não pode ser carregada é ignorada, e as demais iniciam normalmente. A tabela abrange as quatro primeiras; o guia do usuário descreve [o que as outras seis exigem e quais são seus limites](guide.pt-BR.md#plataformas-que-o-personagent-conecta-por-conta-própria).

| Plataforma | O que você faz | Limites |
|---|---|---|
| QQ (bot oficial) | Leia um QR code com o QQ no celular; ele cria um bot ou seleciona um que você já criou. A alternativa é colar o AppID e o AppSecret. | Até que o bot seja certificado, o QQ só permite que ele entre em grupos dos quais você é o proprietário. As permissões de mensagens de grupo são definidas no QQ. |
| WeChat pessoal | Leia o código com o WeChat (a API de bots iLink da Tencent). | Somente conversas individuais. O WeChat não entrega mensagens de grupo a esses bots. |
| Telegram | Cole o token do @BotFather. | |
| Discord | Cole o token do bot, com Message Content Intent ativado. | |

**Pelo AstrBot gerenciado.** Todas as outras plataformas passam por um AstrBot que o personagent baixa, junto com o próprio runtime Python 3.12, e executa sem interface. Ele não tem painel e não precisa de um segundo login. KOOK, Feishu/Lark (conexão persistente), DingTalk (modo Stream), Slack (Socket Mode, e o link do guia preenche o aplicativo), Bot de IA do WeCom (conexão persistente), Mattermost e Misskey solicitam um ou dois valores. O grupo Avançado requer um endereço público ou outro software: Aplicativo do WeCom, Conta Oficial do WeChat, webhook do QQ, OneBot v11 (NapCat) e Satori. O LINE não é oferecido.

Nos dois caminhos, uma plataforma conectada responde a todo grupo e conversa privada que a plataforma entrega ao bot. Isso muda quando `ACCESS_GROUPS` ou `ACCESS_DM_USERS` tem uma entrada para essa plataforma (veja [as listas de permissão do personagent](#por-um-astrbot-que-você-já-executa)). Os IDs chegam como `<platform>:<id>`, por exemplo `qq_official:<openid>`, `weixin_oc:<id>`, `telegram:<id>` e `discord:<id>`. O bot oficial do QQ vê openids, não números de QQ. Conectar uma plataforma diretamente remove a conexão do AstrBot para essa mesma plataforma.

## Por um AstrBot que você já executa

AstrBot, NapCat (OneBot), Koishi (pelo [conector Satori](../integrations/satori/README.pt-BR.md)) e Matrix (pelo [conector Matrix](../integrations/matrix/README.pt-BR.md) e pontes mautrix) são pontes de terceiros com as quais o personagent funciona. Nenhuma é necessária para as plataformas que o personagent conecta por conta própria.

O AstrBot entrega mensagens ao personagent por um plugin em `integrations/astrbot/astrbot_plugin_personagent/`. O plugin envia cada mensagem para `POST /v1/events` e repassa as respostas recebidas. Ele também busca a caixa de saída do personagent (`outbox_enabled`, ativado por padrão), então a persona pode falar primeiro onde a plataforma permitir isso a um bot. O README do plugin tem a tabela. O AstrBot gerenciado recebe o plugin automaticamente. Para o seu próprio AstrBot, inicie-o uma vez para que ele crie a pasta de dados (a que contém `cmd_config.json`, `plugins/` e `config/`) e depois execute:

```
personagent connect astrbot                       # asks, and finds AstrBot's folder itself
personagent connect astrbot <AstrBot data dir>    # asks nothing
```

O comando copia o plugin para `<data dir>/plugins/` e grava um mesmo `CONNECTOR_TOKEN` no `.env` e na configuração do plugin. Ele define `personagent_url` como `http://127.0.0.1:<SERVER_PORT>`, a menos que o plugin já tenha uma URL que aceite (uma URL de loopback, túneis incluídos, ou HTTPS).

Para um AstrBot em outra máquina, baixe `astrbot_plugin_personagent.zip` da [versão mais recente](https://github.com/wangkant/personagent/releases/latest) e envie-o em **Install from File** na página de plugins do AstrBot. Defina `connector_token` como o `CONNECTOR_TOKEN` do `.env` do personagent, e `personagent_url` como um endereço HTTPS do personagent (veja [Expor os endpoints](#expor-os-endpoints)).

Depois de atualizar o personagent, execute `connect astrbot` de novo ou envie o novo zip. O AstrBot 4.29 e posteriores substituem a cópia instalada. Em versões anteriores, desinstale primeiro e deixe **Also delete plugin configuration file** desmarcado.

Opções de `connect astrbot`:

- `--qq` remove `aiocqhttp` de `excluded_platforms`, e `--no-qq` o adiciona novamente. Sem nenhum dos dois, o roteamento do QQ fica como está. `CONNECTOR_QQ_PLATFORMS` acompanha o que o plugin acabar fazendo.
- `--platform qq_official|telegram|discord|slack|kook|lark --token <token>` também ativa esse adaptador na configuração do próprio AstrBot. O Slack também aceita `--app-token`, e o Lark e o QQ aceitam `--app-id` e `--app-secret`. Uma entrada de adaptador que já existe mantém as outras configurações (proxy, URL base, polling) e recebe só as credenciais novas.
- `--url https://...` define um endereço HTTPS para onde o plugin envia.
- `--install` baixa em vez disso um AstrBot gerenciado, e `--start` o inicia.

A primeira execução deixa as listas de permissão vazias. Uma nova execução as mantém, junto com outras plataformas excluídas.

O plugin nega por padrão. Preencha `groups`, e `dm_users` para mensagens privadas, na WebUI do AstrBot, ou responda às perguntas de `connect`. Mensagens privadas são encaminhadas quando `dm_users` não está vazio. O [README do plugin](../integrations/astrbot/astrbot_plugin_personagent/README.pt-BR.md) lista todas as chaves. O AstrBot gerenciado abre cada plataforma que você conecta com `<platform>:*`. Depois de instalar o plugin, reinicie o AstrBot ou recarregue os plugins na WebUI. No lado do personagent:

- `CONNECTOR_TOKEN` autentica cada requisição. A requisição leva o cabeçalho `X-Personagent-Token` mais um HMAC-SHA256, com o token como chave, sobre `timestamp.nonce.body`, e uma proteção contra repetição rejeita nonces reutilizados. Uma requisição capturada não pode ser repetida nem alterada. O token também é a chave de assinatura, então mantenha-o fora dos logs e troque-o se vazar. É opcional em um host e obrigatório entre hosts.
- `ADMIN_IDS` lista as contas do administrador como `<platform>:<id>` (`telegram:12345`, `discord:4242`). Um ID puro ou `qq:<id>` é um número de QQ. `ADMIN_NAME` define o nome do administrador. Todas as contas listadas pertencem a uma pessoa, que recebe a persona mais próxima em grupos e conversas privadas, pode gerenciar o que o bot lembra sobre um grupo e pode ensiná-lo sozinha. Pelo AstrBot, a plataforma é o nome de adaptador que o AstrBot mostra, e `/sid` em uma conversa mostra um ID.
- `ACCESS_GROUPS` e `ACCESS_DM_USERS` deixam o personagent restringir uma plataforma por conta própria, na mesma forma `<platform>:<id>`. Cada plataforma é restrita separadamente. Uma plataforma sem entradas fica para o conector, e uma única entrada restringe essa plataforma às suas entradas. Um turno que o personagent recusa volta sem ser assumido, então o modelo do próprio AstrBot pode responder.

Para o AstrBot no Docker ou em outro host, veja [o guia do usuário](guide.pt-BR.md#pontes-que-você-mesmo-executa).

### QQ pelo NapCat (OneBot)

Este caminho usa uma conta pessoal de QQ em vez de um bot oficial. Você precisa de uma segunda conta de QQ nos grupos de destino, que não seja a sua (veja [DISCLAIMER.md](DISCLAIMER.pt-BR.md)). Ela faz login, em geral por QR code e em uma sessão que persiste após reinicializações, em uma implementação de OneBot v11 conectada ao adaptador `aiocqhttp` do AstrBot. O [NapCat](https://github.com/NapNeko/NapCatQQ) é testado e se conecta ao cliente de desktop QQ NT. LLOneBot e Lagrange são outras implementações de OneBot v11.

No AstrBot gerenciado, adicione **Avançado > OneBot v11 (NapCat)** na página local e aponte o NapCat para `ws://127.0.0.1:6199/ws`. O [guia em chinês](deploy.zh-CN.md) explica passo a passo. Com o seu próprio AstrBot, remova `aiocqhttp` de `excluded_platforms` do plugin, defina `CONNECTOR_QQ_PLATFORMS=aiocqhttp` (`--qq` faz as duas coisas) e defina `QQ_BOT_ID` (`personagent connect astrbot` pergunta).

**`CONNECTOR_QQ_PLATFORMS` é obrigatório aqui.** Sem ele, os IDs do QQ chegam com namespace (`aiocqhttp:123456`) e toda conversa parece nova. Memória, histórico e exemplos aprendidos usam como chave o ID puro, e os registros derivam os IDs de linha do ID da conversa, então a divisão não pode ser reparada depois.

IDs puros carregam a autoridade do QQ, então as entradas de QQ de `ADMIN_IDS`, `ACCESS_GROUPS` e `ACCESS_DM_USERS` se aplicam além das listas de permissão do plugin. Uma conversa privada do QQ precisa estar em `dm_users` *e* vir do administrador ou de uma entrada de `ACCESS_DM_USERS`. Quando `ACCESS_GROUPS` lista grupos de QQ, um grupo de QQ precisa estar nos dois. Coloque uma plataforma em `CONNECTOR_QQ_PLATFORMS` só se você confiar essa autoridade ao conector dela.

**O servidor HTTP do NapCat** (`QQ_ONEBOT_URL`, vazio por padrão) é opcional neste caminho. O personagent também envia mensagens por iniciativa própria:

- mensagens proativas (`PROACTIVE_ENABLED`, desativado por padrão);
- a pergunta feita dois minutos depois de uma rejeição (`REACT_ELICIT_ENABLED`);
- a desculpa enviada em um grupo quando a chamada ao modelo falha.

Elas voltam pela caixa de saída do plugin enquanto o plugin a estiver buscando. Quando não estiver, vão para `QQ_ONEBOT_URL`, se a URL estiver definida. Só a varredura de @menções perdidas enquanto offline precisa do servidor, junto com `QQ_BOT_ID`. A varredura é executada na inicialização e depois a cada 30 minutos. Ela cobre os grupos de QQ em `ACCESS_GROUPS` mais qualquer grupo com atividade desde o último reinício, e reproduz @menções com menos de uma hora. Com a URL vazia, `personagent doctor` mostra a ponte OneBot como "not configured".

**Perdido em todo caminho de conector** (direto, AstrBot ou outro conector), sem configuração que traga de volta:

- o OCR de reserva para imagens que nenhum modelo de visão descreveu;
- a busca de citações pelo NapCat. As citações são resolvidas pelo índice próprio do personagent de mensagens recentes e pelo texto citado que um conector envia com a citação.

Novas figurinhas são coletadas em todos os caminhos, como no QQ: a partir de imagens postadas em grupos que chegam incorporadas à mensagem ou marcadas como figurinhas. Uma foto que um conector envia apenas como link não é coletada.

## Mais de uma plataforma

Vários conectores podem ser executados lado a lado com um único personagent, porque cada um nomeia sua plataforma (`telegram:-1001234`, `matrix:!room:example.org`). O processo direct, o AstrBot, o Satori e o Matrix podem ser executados ao mesmo tempo. Não encaminhe uma mesma conversa por dois conectores; caso contrário, cada mensagem chega duas vezes. IDs com namespace nunca colidem com um número de QQ puro.

Mensagens que ninguém pediu chegam a uma plataforma por um conector que busca a caixa de saída do personagent. São as aberturas proativas, a pergunta depois de uma rejeição e a desculpa quando a chamada ao modelo falha em um grupo. A desculpa de uma conversa privada volta na resposta à requisição que trouxe a mensagem.

O processo direct e os três conectores daqui buscam a caixa de saída, nas plataformas em que um bot pode enviar primeiro. O QQ limita a taxa de mensagens espontâneas de um bot oficial, e uma pessoa pode desativá-las. Um conector seu envia `connector_id`, `reply_handle` e `"capabilities": ["outbox"]` com os eventos e faz long polling em `/v1/outbox` (veja [o protocolo de conectores](connectors.pt-BR.md)). Sem um conector assim, o personagent só fala dentro da requisição que trouxe uma mensagem. Os loops proativos ignoram essas conversas, e a pergunta e a desculpa não são enviadas.

A página local também busca a caixa de saída, apenas para a própria conversa. Um evento de um programa que não busca a caixa de saída, como um assistente de programação que fala em uma conversa, não tira essa conversa de um conector que a busca (veja [o protocolo de conectores](connectors.pt-BR.md#caixa-de-saída-post-v1outbox)).

`PROACTIVE_PLATFORMS` limita onde o loop proativo pode falar primeiro. `PROACTIVE_PLATFORMS=qq_official` o mantém no bot oficial do QQ, e `qq` no QQ pelo NapCat. `CONNECTOR_OUTBOX_ENABLED=false` desativa a caixa de saída por completo.

Para falar primeiro em uma conversa privada sem a caixa de saída, seu próprio agendador (uma tarefa de plugin do AstrBot, uma entrada de cron) pode enviar um evento de conversa privada marcado com `"proactive": true`. Veja [Falar primeiro sem a caixa de saída](connectors.pt-BR.md#falar-primeiro-sem-a-caixa-de-saída).

## Expor os endpoints

Mantenha `SERVER_HOST=127.0.0.1` quando o conector e o personagent compartilharem uma máquina. Um contêiner conta como a mesma máquina só com o namespace de rede do host ou com rede do host. A página local e `personagent up` sempre se vinculam a `127.0.0.1`. Caso contrário:

1. Defina `SERVER_HOST=0.0.0.0` (ou `--host 0.0.0.0`) e `CONNECTOR_TOKEN`. O início recusa um vínculo de rede sem o token. Ele não exige `QQ_ONEBOT_SECRET`, mas sem ele o obsoleto `/v1/onebot` fica desativado em um vínculo de rede. Toda requisição a ele recebe 403 `onebot_disabled`, e o log diz o motivo uma vez.
2. Coloque na frente um proxy reverso HTTPS ou um túnel privado. Todos os conectores daqui enviam só para loopback, ou para HTTPS com um token definido. O plugin do AstrBot registra qualquer outra coisa como `refusing unsafe personagent_url`, e os conectores Satori e Matrix se recusam a iniciar.
3. Mantenha o corpo intacto byte a byte, porque a assinatura o cobre, e mantenha os relógios a menos de cinco minutos um do outro.

Com uma credencial vazia, o endpoint dela atende só programas locais que chamam `http://127.0.0.1` ou `http://localhost` diretamente. Uma requisição recebe 403 `non_local_request` se tiver qualquer um destes:

- um cabeçalho `Origin`;
- um `Sec-Fetch-Site` diferente de `none`;
- um `Host` diferente de `localhost`, `127.0.0.1` ou `::1`;
- um cabeçalho de proxy: `X-Forwarded-For`, `Forwarded`, `X-Real-IP`, `CF-Connecting-IP`, `Via`, `X-Forwarded-Host`, `X-Forwarded-Proto`, `X-Forwarded-Port`, `True-Client-IP`, `X-Client-IP` ou `X-Original-Forwarded-For`.

Um proxy no mesmo host que não adicione nenhum destes ainda parece local. Defina `CONNECTOR_TOKEN` (e `QQ_ONEBOT_SECRET`, se usar `/v1/onebot`) antes de adicionar qualquer proxy ou túnel, mesmo em um único host.

## Endpoints de saúde

- `GET /health` é gratuito e aberto, e não chama nada.
- `GET /health/details` testa os serviços externos (em cache por 60 s). Com `CONNECTOR_TOKEN` vazio, responde só a requisições locais. Com um token definido, responde **só** a requisições com um cabeçalho `X-Personagent-Token` correspondente, mesmo vindas do loopback. Retorna 503 quando um teste crítico falha ou não pode ser executado. Os testes críticos são os modelos de conversa e, quando o QQ usa a entrada direta do OneBot (`QQ_BOT_ID` e `QQ_ONEBOT_URL` definidos, `CONNECTOR_QQ_PLATFORMS` não definido), a ponte OneBot.
- `personagent doctor [--json]` executa os mesmos testes mais a verificação das configurações, e sai com valor diferente de zero no mesmo caso. Quando a última verificação de atualização tem um dia, também pergunta ao pypi.org pela versão mais nova (`UPDATE_CHECK_ENABLED=false` evita essa consulta).

## Custos

- **Os testes gastam crédito.** `personagent doctor` e `/health/details` enviam uma pequena conclusão de conversa a cada modelo para o qual o agente envia trabalho: respostas em grupos e em conversas privadas, a decisão de pesquisa na web, a avaliação de reações (enquanto `REACT_LEARN_ENABLED` estiver ativado), a autoavaliação (enquanto `EVAL_ENABLED` estiver ativado) e a visão. Também enviam um embedding se `EMBEDDING_MODEL` estiver definido, e uma busca do Tavily se `TAVILY_API_KEY` estiver definido. `/health` e as verificações de configurações e registros são gratuitos.
- **O uso do modelo é contabilizado.** Cada solicitação a um modelo é contada por modelo e por dia a partir do uso que o provedor informa, com o custo quando o provedor o informa. `personagent doctor` imprime o dia de hoje e os últimos 7 dias, e a visão Aplicativo da página local mostra o mesmo. O arquivo de contagem é gravado em segundo plano, no máximo uma vez por minuto e mais uma vez no encerramento.
- **Aprendizado e memória.** As decisões de aprendizado do próprio personagem custam uma chamada cada a `PROMOTE_JUDGE_MODEL`, no máximo `PROMOTE_JUDGE_BATCH` a cada `PROMOTE_JUDGE_INTERVAL_S`. A consolidação da memória custa uma chamada por trecho de conversa a `LLM_JUDGE_MODEL`, no máximo 16 por conversa e `MEMORY_CALLS_PER_DAY` (40) para todas as conversas juntas a cada dia. `PROMOTE_JUDGE_ENABLED=false` e `MEMORY_CALLS_PER_DAY=0` as desativam.
- **Os scripts em `tools/`** variam. Alguns são gratuitos e outros chamam um modelo. A tabela em [tools.md](tools.pt-BR.md) diz quais.
- **`personagent eval`** chama o modelo em cada caso, exceto na suíte `memory`, que é executada offline com respostas roteirizadas. As suítes de persona e aprendizado também precisam de um segundo modelo como juiz (`BENCH_JUDGE_MODEL`).
- **Memória.** Acima de 256 conversas com namespace (não QQ), a conversa ociosa com atividade menos recente sai da memória e perde as reações pendentes. As mensagens dela ainda não consolidadas são consolidadas antes, e as mensagens recentes permanecem em `runtime/recent.json` por 72 horas, a menos que `MEMORY_KEEP_RECENT=false`. Fatos, eventos, notas principais e registros permanecem. Uma conversa no meio de uma requisição nunca é removida. As memórias de longo prazo são carregadas do disco no início e não têm esse limite.
- **Disco.** O log de evidências e o registro de candidatos em `runtime/` só crescem e nunca são truncados. `personagent doctor` avisa quando qualquer um passa de 50 MB (`LEDGER_EVIDENCE_WARN_BYTES`, `LEDGER_CANDIDATES_WARN_BYTES`). Os arquivos de memória continuam pequenos: `recent.json` guarda as conversas ativas nas últimas 72 horas, e `memory_trash.jsonl` guarda os itens removidos por no máximo 30 dias. Antes da primeira alteração de cada dia, `memory.json`, `core_memory.json` e `episodes.json` são copiados para um arquivo de mesmo nome terminado em `.bak`, e a primeira inicialização desta versão guarda o arquivo de memória antigo como `memory.json.pre-v2`. Depois de **Esquecer esta conversa** ou de um esquecimento pedido no chat, as cópias `.bak` são gravadas de novo a partir dos arquivos atuais e `memory.json.pre-v2` perde o que foi esquecido, de modo que nenhuma cópia em disco o mantém. Faça backup de `runtime/`, porque ele guarda tudo o que o bot aprendeu e lembra.

## Quando o bot fica em silêncio

As causas estão listadas da mais comum para a menos comum. Quando a página local executa o agente, [Atividade](guide.pt-BR.md#atividade) mostra se as mensagens chegam e por que ele permaneceu em silêncio. Em um servidor, leia o log do serviço e use `personagent learned` para o que ele aprendeu.

1. **Nada chega até ele.** Na página local, verifique se a plataforma aparece como conectada e leia `runtime/desktop/direct.log` ou `astrbot.log`. O bot oficial do QQ precisa estar no grupo, e o QQ decide quais mensagens de grupo ele recebe. Um bot de WeChat pessoal nunca recebe grupos. Em um AstrBot que você executa, preencha `groups` do plugin (e `dm_users` para mensagens privadas), e, para o NapCat, remova `aiocqhttp` de `excluded_platforms`. Os conectores Satori e Matrix têm listas de permissão próprias no `.env` deles. Veja os README deles. Nesse caso, a conversa nunca aparece em Atividade.
2. **O agente está desativado.** O banner de `personagent run` diz `agent: OFF`, com o motivo e a solução. Sem `LLM_API_KEY`, adicione uma chave na página local (ou defina `LLM_API_KEY`) e reinicie. Com `AGENT_ENABLED=false`, defina como `true` em `<home>/.env` e reinicie. Até lá, todo evento recebe `owned: false`, e o primeiro registra uma única linha ERROR com o mesmo conselho.
3. **O modelo do próprio AstrBot responde no lugar.** O plugin recorreu a ele porque a requisição falhou, o personagent recusou a mensagem (item 5) ou o agente está desativado (item 2). O log do AstrBot mostra `refusing unsafe personagent_url`, `agent refused the request (403): <message>` (ou outro status, veja a tabela abaixo) ou `timed out waiting for the agent`. `timeout_s` precisa cobrir o debounce e as chamadas ao modelo no turno, e também o turno que estava pensando quando a mensagem chegou. As chamadas ao modelo de um turno dividem 1,5 × `LLM_TIMEOUT_S`, tanto em um grupo quanto em uma conversa privada, então mantenha 3 × `LLM_TIMEOUT_S` abaixo dele. O padrão (420) cobre o padrão do agente (3 × 120 = 360 s). Aumente-o quando aumentar `LLM_TIMEOUT_S`.
4. **Ele não foi chamado.** Em um grupo, responde ao nome (`PERSONA_NAME`) ou a um @. Caso contrário, espera conversa suficiente (`CHAT_TRIGGER_COUNT`, 30 mensagens por padrão) e ainda pode optar por não responder. Das 02:00 às 07:00 no fuso horário dele, quase não entra em conversas em que não foi chamado. O fuso horário é `PERSONA_TZ_OFFSET_HOURS`. Vazio, é UTC+8 quando `AGENT_LANG` é `zh` ou `zh-TW`, e caso contrário o desta máquina. Uma mensagem de grupo que chega mais de 10 minutos depois de ter sido enviada, nos dois minutos seguintes à primeira mensagem da plataforma dela desde o início, é um acúmulo: é mantida como contexto e não é respondida, e o log do serviço informa isso. Atividade mostra o motivo de cada turno recente. Para ver a mesma decisão offline, execute `personagent chat --trigger 4`.
5. **As listas de permissão do personagent.** `ACCESS_GROUPS` e `ACCESS_DM_USERS` se aplicam em todos os caminhos, e uma conversa privada do QQ com ID puro também precisa do administrador ou de uma entrada. Uma mensagem recusada por elas volta sem ser assumida, então pelo AstrBot o modelo dele pode responder. O personagent registra cada conversa recusada uma vez, em INFO, com a configuração que a recusou.
6. **A chamada ao modelo falha.** Uma chave rejeitada (401 ou 403) ou um saldo vazio (402 ou cota esgotada) registra uma linha ERROR que nomeia o host do provedor e a configuração a corrigir. Execute `personagent doctor`. Ele envia uma pequena requisição a cada endpoint de modelo e mostra o status, o que também detecta um `LLM_BASE_URL` ou `LLM_MODEL` incorreto. Quando o modelo principal excede o tempo limite ou a conexão cai, e `LLM_FALLBACK_MODEL` nomeia outro modelo, a chamada passa imediatamente para o modelo reserva, de modo que o turno ainda é respondido dentro do seu tempo limite. Um erro que um provedor envia dentro de uma resposta normal, como as falhas de origem do OpenRouter, é tratado como o erro HTTP correspondente. Enquanto o modelo está indisponível, a persona envia uma desculpa curta dentro do personagem quando é chamada, no máximo uma vez por conversa a cada cinco minutos; a Atividade mostra o turno como "o modelo não respondeu".
7. **Uma configuração com erro de digitação.** O log de início e `personagent doctor` listam toda chave que `.env.example` não conhece e qualquer valor que comece com `#`.
8. **Um BOM no `.env`.** O nome da primeira configuração carrega o BOM e nunca chega ao processo. O início e `personagent doctor` informam isso. Salve o arquivo de novo como UTF-8 sem BOM.
9. **`QQ_BOT_ID` não definido ou errado com o NapCat.** Pelo AstrBot, as @menções ainda funcionam, mas a varredura de menções perdidas compara com ele. Na entrada direta do OneBot, uma @menção nunca é reconhecida. O bot inicia sem problemas, não registra nada e nunca responde. `personagent doctor` avisa quando `QQ_BOT_ID` está vazio e outras configurações de QQ estão definidas. O bot oficial do QQ não o usa.
10. **Ele responde, mas esqueceu o que aprendeu.** Ou o QQ do NapCat está chegando sem `CONNECTOR_QQ_PLATFORMS=aiocqhttp`, ou `PERSONA_NAME` ou `PERSONA_VERSION` mudou, o que inicia um novo personagem. O log avisa quando o material promovido do personagem antigo é recusado por inteiro. Editar `persona.txt`, inclusive na caixa Persona da página, não inicia um novo personagem. As revisões sob um mesmo `PERSONA_VERSION` compartilham um escopo de aprendizado (`runtime/persona_lineage.json`). Para incorporar linhas aprendidas sob um hash de persona que a linhagem não lista, execute `personagent learned lineage adopt <hash>` e depois `personagent learned rebuild`. O hash está no escopo do candidato em `personagent learned show <id>`. Mudar `AGENT_LANG` entre chinês e outro idioma também troca para os outros arquivos aprendidos em `runtime/`.

Os erros de `/v1/events` estão listados abaixo. O plugin do AstrBot registra a mensagem, e `code` é o campo estável em que um cliente pode se basear.

| Status | `code` | Mensagem no log do AstrBot | Causa |
|---|---|---|---|
| 403 | `unauthenticated` | authentication required | sem `CONNECTOR_TOKEN`, e quem chama não está nesta máquina |
| 403 | `non_local_request` | no credential is configured; only local requests accepted | sem `CONNECTOR_TOKEN`, e a requisição veio por um navegador, um proxy ou outro nome de host |
| 403 | `invalid_envelope` | invalid, stale, or replayed request envelope | token, cabeçalhos ou assinatura ausentes ou errados, relógios com mais de 5 min de diferença, nonce reutilizado ou proteção contra repetição cheia (`connector replay guard full` no log do agente) |
| 403 | `stale_event` | stale or invalid sent_at | `sent_at` difere de agora em mais de `CONNECTOR_MAX_EVENT_AGE_S` (24 h), incluindo carimbos de tempo futuros ou em milissegundos |
| 400 | `invalid_schema` | invalid event schema | falta um campo obrigatório: `platform`, `conversation_type`, `sender_id`, `message_id`, `sent_at`, e `conversation_id` para grupos |
| 400 | `client_disconnected` | client disconnected | quem chama encerrou a conexão durante o envio |
| 408 | `body_timeout` | request body not received in time | o corpo levou mais de 30 s para chegar |
| 413 | `body_too_large` | request body too large | acima de `SERVER_MAX_BODY_BYTES` (8 MB), em geral uma imagem embutida |
| 429 | `capacity_exceeded` | webhook capacity exceeded | acima de `CONNECTOR_MAX_INFLIGHT` turnos em andamento; tente de novo após 3 s |

## Legado: a entrada direta do OneBot

O webhook do NapCat ainda pode enviar eventos para `POST /v1/onebot`, e o personagent responde por `QQ_ONEBOT_URL`. Esta rota está obsoleta e permanece durante a 1.x. Use em vez disso a conexão do bot oficial do QQ, ou o NapCat pelo AstrBot com `CONNECTOR_QQ_PLATFORMS=aiocqhttp`. A rota avisa uma vez no primeiro uso e marca toda resposta com `Deprecation: true`.

Para passar ao NapCat pelo AstrBot, adicione OneBot v11 (NapCat) na página local, ou execute `personagent connect astrbot <AstrBot data dir> --qq` para o seu próprio AstrBot e preencha as listas de permissão. Aponte o cliente WebSocket do NapCat para ele e desative o cliente HTTP do NapCat (mantenha o servidor HTTP). Memória e aprendizado são mantidos, porque `CONNECTOR_QQ_PLATFORMS` preserva os IDs.

Se você ainda usa a rota legada:

- Configure as duas direções como a [documentação do NapCat](https://napneko.github.io/) descreve. Você precisa de um **servidor HTTP** em `QQ_ONEBOT_URL` para enviar e de um **cliente HTTP** que envie para `http://127.0.0.1:8080/v1/onebot` (`SERVER_HOST`, `SERVER_PORT`). `QQ_ONEBOT_URL` é vazio por padrão, então escreva-o no `.env`. Sem ele, o bot recebe mas nunca responde. A verificação prévia e `personagent doctor` avisam quando esta rota parece configurada (`QQ_BOT_ID` ou `QQ_ONEBOT_SECRET` definido, `CONNECTOR_QQ_PLATFORMS` vazio) e `QQ_ONEBOT_URL` está vazio.
- Se o NapCat estiver em outra máquina, defina `QQ_ONEBOT_SECRET` como o `secret` do cliente HTTP. Caso contrário, qualquer um que alcance a porta pode forjar eventos. Os corpos então precisam levar `x-signature: sha1=<hex>` (403 `bad_signature`), e eventos com carimbo de tempo desviado em mais de cinco minutos recebem 403 `stale_event`. Sem o segredo, a rota responde só a programas neste host, e em um vínculo de rede fica desativada (403 `onebot_disabled`).
- Com o AstrBot na mesma conta, mantenha `aiocqhttp` em `excluded_platforms`; caso contrário, cada mensagem chega duas vezes.

Verifique o envio com `curl http://127.0.0.1:3000/get_login_info`. Verifique o recebimento observando o log do personagent enquanto escreve para o bot em um grupo.
