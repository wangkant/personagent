# Guia do usuário do personagent

[English](guide.md) · [简体中文](guide.zh-CN.md) · [繁體中文](guide.zh-TW.md) · [日本語](guide.ja.md) · [한국어](guide.ko.md) · [Español](guide.es.md) · [Français](guide.fr.md) · [Deutsch](guide.de.md) · Português (Brasil) · [Русский](guide.ru.md)

Este guia explica como configurar o personagent, colocá-lo nos seus chats, ensinar coisas a ele e cuidar dele. O [README](readme/README.pt-BR.md) é a versão curta, e o [início rápido](start.pt-BR.md) percorre a página local tela por tela.

1. [Instalação e a pasta inicial](#instalação-e-a-pasta-inicial)
2. [A página local](#a-página-local)
3. [Veja primeiro: a demo](#veja-primeiro-a-demo)
4. [Comandos de terminal](#comandos-de-terminal): [configuração](#configurar-no-terminal) · [chat](#conversar-no-terminal) · [executar o serviço](#executar-o-serviço)
5. [Faça dele o seu personagem](#faça-dele-o-seu-personagem)
6. [Coloque em um chat](#coloque-em-um-chat): [QQ, WeChat, Telegram, Discord](#qq-wechat-telegram-e-discord) · [Outras plataformas](#outras-plataformas-pelo-astrbot-gerenciado) · [Pontes que você mesmo executa](#pontes-que-você-mesmo-executa) · [Falar primeiro](#falar-primeiro)
7. [Agentes de código](#agentes-de-código)
8. [Ensine a ele](#ensine-a-ele)
9. [Atividade](#atividade)
10. [Meça](#meça)
11. [Como funciona](#como-funciona)
12. [Privacidade e consentimento](#privacidade-e-consentimento)
13. [Solução de problemas](#solução-de-problemas)
14. [Atualização a partir da 0.x](#atualização-a-partir-da-0x)
15. [Status e outros documentos](#status-e-outros-documentos)

## Instalação e a pasta inicial

```sh
python -m pip install personagent
personagent
```

`personagent` abre [a página local](#a-página-local). Você também pode instalá-lo ou executá-lo destas formas:

| Caminho | Comando |
|---|---|
| Executar sem instalar | `uvx personagent` (parte do [uv](https://docs.astral.sh/uv/), que também baixa o Python para você) |
| Um comando `personagent` permanente | `uv tool install personagent` ou `pipx install personagent` |
| Windows, a partir do ZIP do código-fonte | descompacte e dê dois cliques em `start.bat` |
| A partir de um clone | `git clone https://github.com/wangkant/personagent.git`, `cd personagent`, `python -m venv .venv`, depois `.venv/bin/python -m pip install -e .` e `.venv/bin/python -m persona_agent` (no Windows, `.venv\Scripts\python.exe`) |

O personagent roda em Python 3.10–3.14. `start.bat` cria `.venv`, instala as dependências e abre a mesma página; na primeira vez, também coloca um ícone do personagent na área de trabalho e no menu Iniciar. Ele as reinstala sempre que a lista de dependências em `pyproject.toml` muda.

A **pasta inicial** guarda as configurações (`.env`), o personagem (`persona.txt`), o que ele aprende (`runtime/`) e as plataformas de chat (`platforms/`). `platforms/` contém o AstrBot gerenciado e `direct.json`, que armazena as credenciais das plataformas que o personagent conecta por conta própria. O personagent usa a primeira destas pastas:

1. a pasta de `--home DIR` ou `AGENT_HOME`. `--home` pode vir antes ou depois do comando, como em `personagent chat --home D:\bot`.
2. o clone, quando você executa a partir de um clone.
3. a pasta atual, se ela tiver tanto `.env` quanto `persona.txt`.
4. `~/personagent`, criada na primeira configuração.

Para executar vários personagens a partir de uma instalação, dê a cada um a sua própria pasta inicial.

Este guia escreve os comandos como `personagent ...`. Se você não o instalou, coloque `uvx` na frente. Em um clone, `.venv/bin/python -m persona_agent ...` faz o mesmo (no Windows, `.venv\Scripts\python.exe -m persona_agent ...`).

## A página local

`personagent` (ou `personagent start`) serve uma página acessível apenas deste computador. No Windows, ela abre em uma janela própria. No macOS e no Linux, abre no navegador, ou também em uma janela depois que `pip install "personagent[app]"` instalar o [pywebview](https://pywebview.flowrl.com/), junto com o Qt no Linux. A página tem quatro visões:

- **Conversa** é uma conversa individual com o personagem na página. O mesmo agente que atende às suas plataformas de chat responde aqui.
- **Atividade** mostra os chats em que o personagem está, o que ele disse recentemente, o que aprendeu e o que espera sua decisão. Veja [Atividade](#atividade).
- **Conectar apps** coloca o personagem no QQ, WeChat, Telegram, Discord e outras plataformas. Veja [Coloque em um chat](#coloque-em-um-chat).
- **Personagem e configurações** é onde você escolhe um serviço de modelos (OpenRouter, DeepSeek, SiliconFlow, Alibaba Bailian, Zhipu GLM, Moonshot, Volcengine Ark, OpenAI, Google Gemini, Ollama ou qualquer outro serviço compatível com OpenAI), cola a chave de API e escolhe um nome e uma personalidade pronta. **Verificar e começar a conversar** testa a chave com uma pequena solicitação e só a salva se a solicitação funcionar. Depois da configuração, a caixa **Persona** mostra `persona.txt`. **Salvar persona** reinicia o agente com o novo texto e mantém o que ele aprendeu. **Mais recursos** ativa a busca na web pelo Tavily (DuckDuckGo é o padrão gratuito), a compreensão de imagens e o falar primeiro nos aplicativos que você escolher.

Até você conectar um aplicativo, a visão Conversa mostra uma barra curta de **Primeiros passos**.

Executar `personagent` de novo traz de volta a página já aberta. `--browser` abre a página no navegador em vez de numa janela, e `--no-browser` imprime o link e não abre nada. No Windows, `personagent shortcut` coloca na área de trabalho e no menu Iniciar um ícone que abre a janela sem nenhum terminal por trás, e `personagent shortcut --remove` o remove.

Quando há um personagent mais novo no PyPI, a visão Conversa mostra um aviso com o comando que atualiza sua instalação, seja ela do pip, uvx, uv tool, pipx ou de um clone Git. Para um ZIP do código-fonte descompactado, o aviso aponta para a página de versões. O terminal imprime o mesmo comando. Fechar o aviso o oculta para aquela versão, e **N disponível** abaixo do número da versão o traz de volta. `personagent up` e `personagent doctor` também informam uma versão nova. A página e `up` consultam pypi.org no máximo uma vez por dia, em segundo plano. `doctor` consulta na hora quando a última resposta tem mais de um dia. Defina `UPDATE_CHECK_ENABLED=false` para desativar a verificação.

A página inicia o agente e as plataformas conectadas em segundo plano, então mantenha a janela aberta enquanto os usa. Tudo o que ela iniciou termina com ela, seja clicando em **Sair**, pressionando Ctrl+C ou fechando a janela. Enquanto houver um aplicativo conectado, fechar a janela pede confirmação antes. Se uma execução anterior travou e deixou processos, a próxima inicialização os encerra primeiro.

## Veja primeiro: a demo

`personagent demo` reproduz três cenas em um modelo roteirizado, então não precisa de chave. As cenas mostram quais mensagens de grupo ele deixa passar e por quê, como aprende com uma correção e como um desconhecido falha em plantar uma instrução. Para reproduzir só uma cena, diga o nome dela (`quiet`, `teach` ou `troll`). Adicione `--lang` e um código de idioma para outro idioma, como `--lang ja`.

Aqui está uma execução resumida de `personagent demo teach`. As falas do modelo são roteirizadas, mas o registro e a regra de promoção são o código real:

```text
  Alex: Nova, the deploy failed again
  Nova: did you check the logs? roll back first, then diff the configs
  Alex: Nova, I was just venting
      judged: rejection, accepted: "Alex was venting, not asking for a fix"
      ledger: negative only (it says the reply was off, not what to say)
      Nova's next reply to Alex counts as its second try
  Nova: fair. that's a rough end to the day
  Alex: haha yeah it is, thanks Nova
      judged: positive, accepted: "Alex agreed with the second try and thanked Nova"
      ledger: weak (a laugh or a thanks never changes anything alone)
      ledger: Alex accepted the second try: strong (Alex is who the reply was for)

  fix: "did you check the logs? roll back first, ..." -> "fair. that's a rough end to the day"
    [x] 2 of 2 agreeing reactions
    [x] 1 of 1 strong
    [x] same chat
    [x] 1 of 1 person (PROMOTE_MIN_SPEAKERS)
    [x] nothing disagrees, no rival fix
    now in use: 2 agreeing reactions, 1 strong, same chat
```

A cena também envia a mesma mensagem antes e depois da lição: o notebook de alguém pifou no meio da demo. Antes da correção, Nova oferece uma solução. Depois, Nova se solidariza. A demo continua roteirizada mesmo com uma chave definida, então toda execução é igual e não custa nada. `personagent demo --online` a reproduz no seu próprio modelo, o que custa tokens e varia de uma execução para outra.

## Comandos de terminal

Tudo o que a página faz também está disponível em um terminal, o que combina com servidores e scripts.

| Comando | O que faz |
|---|---|
| `personagent start` | abre a página local (`--terminal` para um menu no terminal) |
| `personagent init` | configura uma pasta inicial; `--terminal` faz as perguntas no terminal, `--no-input` aceita opções |
| `personagent chat` | um chat em grupo simulado no terminal |
| `personagent demo` | a demo roteirizada acima |
| `personagent run` | só o serviço, para conectores que você mesmo executa |
| `personagent up` | o serviço, as plataformas que o personagent conecta por conta própria e o AstrBot gerenciado, juntos |
| `personagent connect astrbot` | conecta um AstrBot (`--install` para baixar um gerenciado, `--start` para iniciá-lo) |
| `personagent connect claude-code`, `personagent connect codex`, `personagent connect dsh` | coloca o personagem em um [agente de código](#agentes-de-código) (`--react` para comentários no fim de um turno nos dois primeiros, `--remove` para desfazer) |
| `personagent mcp` | o servidor MCP que um agente de código inicia; você não o executa |
| `personagent doctor` | verifica a configuração e cada serviço de que ele depende |
| `personagent learned` | revisa, promove ou reverte o que ele aprendeu |
| `personagent eval` | mede a fala, a persona e o aprendizado |

Todos os comandos aceitam `--help`.

### Configurar no terminal

`personagent init --terminal` faz as mesmas perguntas da página, no idioma que você escolhe primeiro, e explica cada termo em uma linha:

- **O serviço de IA.** As predefinições são as da página. O padrão é `openrouter/free` do OpenRouter, que entrega cada solicitação a um dos seus modelos gratuitos. A chave não custa nada. O limite é de 20 solicitações por minuto e 50 por dia, ou 1000 por dia depois que você compra pelo menos 10 créditos. Toda chamada ao modelo conta, não só as respostas, e o dia recomeça à meia-noite UTC. Depois do limite, o personagem diz que não pode responder agora, e `runtime/desktop/agent.log` traz o motivo do OpenRouter. O modelo muda de uma solicitação para outra, então a voz do personagem oscila mais do que com um modelo escolhido, e alguns provedores gratuitos guardam o que recebem. Para um personagem mais estável, use um modelo pago com a mesma chave. Se o OpenRouter for difícil de acessar onde você está, `glm-4.7-flash` da Zhipu também é gratuito. Para o Ollama, informe um modelo que você já baixou. O Ollama não precisa de chave.
- **A chave.** A digitação fica oculta por padrão. Você pode optar por mostrá-la, o que também revela a chave salva ao reconfigurar. O assistente testa a chave com uma pequena solicitação. Se ela falhar, ele mostra o endereço chamado, o status HTTP e uma provável correção.
- **O personagem.** Um nome e um dos sete personagens prontos (amigo irônico, ouvinte atento, gamer, rato de biblioteca, e três que a comunidade já desenha: a garota-baleia do DeepSeek, a garota-dragão do GPT e a senhorita Claude) ou um personagem simples que você mesmo escreve. Se você escolher um dos três últimos sem escolher um nome, o personagem recebe o nome dele. A página local mostra o retrato animado dele.
- **AstrBot.** Opcional, e você pode pular na primeira vez. Veja [Pontes que você mesmo executa](#pontes-que-você-mesmo-executa).

Para configurar sem perguntas, como em um script, execute `personagent init --no-input` com `--provider`, `--model`, `--key-env VAR`, `--name`, `--lang` e `--persona`. Em uma pasta inicial nova, uma chave vinda de `--key-env` ou do `LLM_API_KEY` do shell precisa de `--provider` ou `--base-url` para dizer de quem é. `--provider other` também precisa de `--base-url`. `personagent init --help` lista todas as opções. Se `personagent init` rodar sem terminal e sem nenhuma dessas opções, ele pula as perguntas, avisa e sai com o código 2.

### Conversar no terminal

`personagent chat` coloca você em um chat em grupo simulado com o personagem. Uma linha comum é conversa normal de grupo, e o teste diz se o personagem entraria e por quê. Uma linha com o nome dele o chama:

```text
Alex> anyone around tonight?
  (Nova stays quiet: not addressed, 1 of 4 messages)

Alex> Nova, the deploy failed again
  Nova > did you check the logs? roll back first, then diff the configs
```

| Digite | Para |
|---|---|
| `/reply <text>` | citar a última resposta dele, o que conta como uma reação da qual ele pode aprender |
| `/as Sam <text>` | falar como outra pessoa: `/as Sam Nova, you free tonight?` |
| `/admin <text>` | falar uma vez como administrador: `/admin Nova, how was your day?` |
| `/why` | ver por que ele deu a última resposta e o que o registro tem sobre ela |
| `/learned` | ver o que ele aprendeu neste chat |
| `/reset` | limpar o chat e o que o teste aprendeu |
| `/quit` | sair |

As linhas `/as` e `/admin` também seguem as regras de grupo, então inclua o nome para receber uma resposta. Uma linha com menos de quatro caracteres que não nomeia o personagem não conta para ele entrar na conversa. Os [comandos de memória](#comandos-de-memória) também funcionam aqui.

| Opção | O que faz |
|---|---|
| `--name Alex` | define o seu nome |
| `--admin` | atribui cada linha ao administrador |
| `--dm` | transforma em conversa individual |
| `--lang <code>` | substitui `AGENT_LANG`, como `--lang ja` |
| `--trigger N` | mensagens antes de ele considerar entrar (padrão 4) |

O teste executa a decisão real de falar ou calar, as verificações de saída, os comandos de memória e o aprendizado. Ele considera entrar depois de 4 mensagens, enquanto o bot em produção espera 30. O que ele aprende fica em `runtime/trial/` na pasta inicial, separado do bot em produção. `personagent learned` não mostra isso, e `/reset` apaga. O teste ignora as listas de permissão e a entrega real. Ele também desativa a autoavaliação, a visão, a pergunta de acompanhamento e as mensagens que o personagem iniciaria por conta própria. Quando uma chamada ao modelo falha, ele imprime uma linha dizendo o que verificar:

```text
Alex> Nova, you there?
  [error: the model provider refused the key or the account (HTTP 401); check LLM_API_KEY, then run `personagent doctor`]
```

### Executar o serviço

`personagent run` inicia só o serviço com o qual os conectores falam, em `http://127.0.0.1:8080`. Ao iniciar, imprime a versão, o endereço, a pasta inicial e se o agente está ativo. `--host` e `--port` substituem `SERVER_HOST` e `SERVER_PORT`. Use isto quando você mesmo executa o conector.

`personagent up` inicia o serviço com todas as plataformas conectadas pela página ou com `connect astrbot --install`. Ele não abre um navegador. Ctrl+C para tudo, e cada processo escreve o seu log em `runtime/desktop/` na pasta inicial.

## Faça dele o seu personagem

`persona.txt` na pasta inicial define o personagem. Edite-o na caixa **Persona** da página, ou em qualquer editor e depois reinicie. Descreva quem é o personagem, como costuma falar e o que faz nas situações que importam para você. Hábitos concretos funcionam melhor do que pedir ao modelo para "parecer natural":

```text
Your name is Nova. You chat with friends about films and cooking.
You speak directly and make the occasional joke.

Usually reply in a sentence or two. Explain more when someone asks a serious question.
When a friend vents, listen before offering advice.
If you have not seen a film, say so instead of inventing an opinion.
```

`AGENT_LANG` é um de `en`, `zh`, `zh-TW`, `ja`, `ko`, `es`, `fr`, `de`, `pt-BR` e `ru`. Ele define a persona inicial, a configuração no terminal, o teste e a demo, `--help` e `doctor`, os comandos de memória e as respostas fixas. Os exemplos, filtros e verificações incluídos são em chinês para `zh` e `zh-TW` e em inglês para os demais. Ele não traduz sua persona. [.env.example](../.env.example) descreve cada configuração.

O menu de idioma no canto superior direito da página local oferece English, 简体中文, 繁體中文, 日本語, 한국어, Español, Français, Deutsch, Português (Brasil) e Русский. Ele muda a página, e o navegador se lembra. Quando você salva as configurações, o idioma da página vira `AGENT_LANG`. O personagem responde no idioma que o chat usa. Os prompts dele são em inglês e chinês. Os [comandos de memória](#comandos-de-memória) e as poucas respostas fixas, que não passam pelo modelo, funcionam nos dez idiomas.

Para substituir um arquivo incluído, coloque um arquivo com o mesmo nome em `data/` na pasta inicial. Os arquivos que você não substitui vêm da cópia distribuída com o personagent.

| Arquivo | Conteúdo |
|---|---|
| `data/examples.<lang>.jsonl` | Trocas de exemplo que o modelo pode imitar |
| `data/feedback.<lang>.jsonl` | Respostas emparelhadas com versões melhores |
| `data/lorebook.<lang>.json` | Notas de contexto adicionadas quando uma palavra-chave aparece |
| `data/output_filter.<lang>.json` | Regras de substituição e rejeição para respostas em produção |
| `persona.card.json` | Configurações opcionais de emoji, conjunto de caracteres e tamanho, como `{ "reply_style": { "emoji": true, "max_chars": 320 } }` |

Para ele ver imagens, defina `VISION_MODEL`, `VISION_API_KEY` e `VISION_BASE_URL`, ou ative a compreensão de imagens em **Mais recursos**.

## Coloque em um chat

Abra **Conectar apps** na página local e escolha uma plataforma. A página pede apenas os valores que você copia do console da plataforma. Ela os verifica com a plataforma, inicia a conexão e espera alguns segundos para confirmar que a plataforma a aceitou. Se a plataforma recusar, a página diz isso e não salva nada. As plataformas conectadas ficam listadas no topo, onde você pode reconfigurar ou desconectar uma delas. Elas reiniciam sempre que a página ou `personagent up` inicia.

```text
Chat platform  ⇄  connector  ⇄  personagent  ⇄  Model API
```

Um conector entra na plataforma, encaminha cada mensagem ao personagent e traz a resposta de volta. Há três tipos.

### QQ, WeChat, Telegram e Discord

O personagent conecta estes quatro por conta própria, em um único processo em segundo plano. Eles não precisam de AstrBot nem de NapCat.

| Plataforma | O que você faz |
|---|---|
| QQ | Escaneie o código com o QQ no celular e confirme. Isso cria um bot oficial do QQ, ou usa um que você já tem, e o personagent busca as chaves dele. **Colar valores em vez disso** aceita o AppID e o AppSecret de um bot criado na [página de bots do QQ](https://q.qq.com/qqbot/openclaw/login.html). |
| WeChat (pessoal) | Escaneie o código com o WeChat e confirme o login. A conexão usa a API de bots iLink da Tencent e cobre apenas conversas individuais, porque o WeChat não entrega mensagens de grupo a esses bots. |
| Telegram | Crie um bot com o [@BotFather](https://t.me/BotFather) e cole o token dele. |
| Discord | No [Developer Portal](https://discord.com/developers/applications), copie o token do bot e ative Message Content Intent. |

Para o QQ, encontre o bot no QQ do celular em Contatos → Bots e converse com ele diretamente ou adicione-o a um grupo. Até o bot ser certificado, o QQ só o deixa entrar em grupos que são seus. Você escolhe quais mensagens de grupo ele recebe no próprio QQ, no perfil do bot naquele grupo. O [guia de bots do QQ](https://bot.q.qq.com/wiki/bot_new_product-intro/) cobre a certificação.

As credenciais ficam em `platforms/direct.json` na pasta inicial.

### Outras plataformas, pelo AstrBot gerenciado

Na primeira vez que você conecta outra plataforma, o personagent baixa o [AstrBot](https://docs.astrbot.app) e um runtime próprio do Python 3.12 para `platforms/` na pasta inicial. Mantenha a página aberta durante o download. Depois disso, o AstrBot roda em segundo plano, sem painel e sem segundo login. Ele não precisa de um `uv` global e deixa o Python do personagent em paz. Conectar uma plataforma pela página permite que grupos e mensagens diretas dessa plataforma cheguem ao personagem. As listas de permissão de outras plataformas ficam como estão.

| Grupo | Plataformas | O que você fornece |
|---|---|---|
| Colar um ou dois valores | KOOK, Feishu / Lark, DingTalk, Slack, bot de IA do WeCom, Mattermost, Misskey | um token, um ID de aplicativo e um segredo, ou um endereço de servidor e um token. O Feishu usa conexão longa e o DingTalk usa o modo Stream, então nenhum precisa de endereço público. Para o Slack, o link da página cria o aplicativo com Socket Mode, escopos e eventos já definidos. Adicione um token de nível de aplicativo com `connections:write`, instale o aplicativo e cole os dois tokens. Crie o bot de IA do WeCom com a conexão longa. |
| Avançado | Aplicativo WeCom, conta oficial do WeChat, QQ (webhook) | um endereço público que encaminha para a porta de callback mostrada |
| Avançado | OneBot v11 (NapCat), Satori | outro software rodando neste computador: NapCat apontado para `ws://127.0.0.1:<port>/ws`, ou um servidor Satori |

O LINE não é oferecido porque o AstrBot só recebe callbacks do LINE pelo painel dele.

Em um terminal, `personagent connect astrbot --install` baixa o mesmo AstrBot gerenciado e o conecta. Adicione `--platform telegram --token <bot token>` para ativar uma plataforma ao mesmo tempo. Nenhum grupo ou mensagem direta é permitido até você configurá-los. Se o download falhar, execute o mesmo comando de novo. A configuração existente é mantida. `personagent connect astrbot --start` inicia o AstrBot gerenciado, e `personagent up` o inicia com todo o resto.

### Pontes que você mesmo executa

Os projetos abaixo são softwares de terceiros com os quais o personagent funciona. Você não precisa de nenhum deles para QQ, WeChat, Telegram ou Discord.

| Ponte | Alcança |
|---|---|
| Um [AstrBot](https://docs.astrbot.app) que você já executa | as plataformas dele |
| [NapCat](https://github.com/NapNeko/NapCatQQ) (OneBot v11), pelo AstrBot | QQ com uma conta pessoal do QQ |
| [Koishi](https://koishi.chat) ou outro servidor Satori, pelo [conector Satori](../integrations/satori/README.pt-BR.md) | o que esse servidor tiver conectado |
| [Matrix](../integrations/matrix/README.pt-BR.md), pelas pontes mautrix | salas Matrix, além de WhatsApp, Signal, Messenger, Instagram e Google Messages |

Qualquer outra coisa pode se conectar pelo [protocolo de conectores](connectors.pt-BR.md), que recebe uma solicitação HTTP assinada por mensagem. Vários conectores podem servir um mesmo personagent ao mesmo tempo. O [guia de implantação](deploy.pt-BR.md) cobre a execução em produção.

**Um AstrBot que você já executa.** O AstrBot encaminha mensagens ao personagent por um pequeno plugin, [astrbot_plugin_personagent](../integrations/astrbot/astrbot_plugin_personagent/README.pt-BR.md). O plugin vem com o personagent, e o AstrBot gerenciado o recebe automaticamente. `personagent connect astrbot` encontra o seu AstrBot, ou recebe a pasta dele como argumento. Ele instala o plugin, escreve um `CONNECTOR_TOKEN` comum nos dois lados e pergunta quais grupos permitir. Envie `/sid` em um grupo para ver o identificador dele.

Para um AstrBot em outra máquina:

1. Baixe `astrbot_plugin_personagent.zip` da [versão mais recente](https://github.com/wangkant/personagent/releases/latest).
2. Envie-o em **Install from File** na página de plugins do AstrBot.
3. Defina o `connector_token` do plugin como o `CONNECTOR_TOKEN` do `.env` do personagent.
4. Defina o `personagent_url` dele como um endereço HTTPS do personagent. Veja **AstrBot no Docker ou em outro host** abaixo.
5. Execute `personagent run` e depois reinicie o AstrBot ou recarregue os plugins dele.

Depois de atualizar o personagent, execute `connect astrbot` de novo ou envie o novo zip. O AstrBot 4.29 e posteriores substituem a cópia instalada. Em versões anteriores, desinstale primeiro a cópia antiga e deixe **Also delete plugin configuration file** desmarcado para manter as configurações dela.

O plugin só encaminha um grupo se ele estiver na lista `groups`, e mensagens diretas só de usuários em `dm_users`. Você pode mudar as duas na WebUI do AstrBot. Reinicie o personagent depois de editar `.env`, e reinicie o AstrBot depois de mudar uma plataforma ou o plugin.

Quando você informa a pasta do AstrBot, `connect astrbot` não pergunta nada, e você pode ativar uma plataforma a partir do token dela:

```bash
personagent connect astrbot <AstrBot data dir> --platform telegram --token <bot token>
```

`--platform` aceita `telegram`, `discord`, `slack`, `kook`, `lark` e `qq_official`. O Slack também aceita `--app-token`, e o Lark e o QQ aceitam `--app-id` e `--app-secret`. Em um adaptador já configurado no AstrBot, o comando muda apenas as credenciais e mantém todo o resto, como um proxy ou uma URL base. `personagent connect --help` lista as opções restantes.

**QQ pelo NapCat.** Este caminho usa uma conta pessoal do QQ em vez de um bot oficial. O NapCat faz login com a conta e se conecta ao adaptador `aiocqhttp` (OneBot v11) do AstrBot, com o WebSocket reverso em `ws://127.0.0.1:6199/ws`. Escolher QQ em `personagent connect astrbot`, ou passar `--qq` com uma pasta, remove `aiocqhttp` de `excluded_platforms` do plugin e define `CONNECTOR_QQ_PLATFORMS=aiocqhttp`. Os chats do QQ mantêm então as mesmas identidades e a mesma memória. O servidor HTTP do NapCat (`QQ_ONEBOT_URL`) é opcional. Com ele e `QQ_BOT_ID` definidos, o personagent recupera as menções perdidas enquanto estava offline. O [passo a passo em chinês](deploy.zh-CN.md#第三方路线astrbot--napcat) tem uma seção curta sobre este caminho. Clientes de QQ de terceiros colocam a conta em risco, então leia primeiro o [aviso legal](DISCLAIMER.pt-BR.md).

O caminho direto OneBot (`/v1/onebot`) está obsoleto e permanece durante toda a 1.x. Ele envia respostas por `QQ_ONEBOT_URL`, então defina-o se ainda o usa. `personagent doctor` avisa quando o caminho parece configurado sem ele. Nunca o execute junto com o encaminhamento do AstrBot, senão cada mensagem chega duas vezes.

**AstrBot no Docker ou em outro host.** O plugin só envia para o mesmo host (ou um contêiner que compartilhe a rede dele), ou para um endereço HTTPS com `connector_token` definido. Ele recusa `http://` sem criptografia em qualquer outro lugar, como `http://host.docker.internal:8080`, registra `refusing unsafe personagent_url` e deixa o modelo do AstrBot responder. Há duas soluções:

- Dê ao contêiner do AstrBot a rede do host: `network_mode: host` no arquivo compose dele, ou `docker run --network host`. No Docker Desktop 4.34 ou posterior, ative também "Enable host networking".
- Dê ao personagent um endereço HTTPS e defina-o como `personagent_url` do plugin. `connect astrbot --url https://...` escreve isso para você.

Um contêiner do NapCat no mesmo arquivo compose também precisa da rede do host.

O personagent escuta em `127.0.0.1:8080`, e um `SERVER_HOST` vazio significa o mesmo. Escutar em um endereço de rede (`--host 0.0.0.0` ou `SERVER_HOST`) exige `CONNECTOR_TOKEN`. Defina o token antes de adicionar um proxy ou túnel, mesmo em uma só máquina, porque um túnel pode fazer solicitações externas parecerem locais. [Expor os endpoints](deploy.pt-BR.md#expor-os-endpoints) cobre o resto.

### Falar primeiro

Algumas mensagens não respondem a ninguém. São as falas por iniciativa própria (`PROACTIVE_ENABLED`, desativado por padrão), a pergunta de acompanhamento depois de uma rejeição e a desculpa quando o modelo falha em um grupo. Em uma mensagem direta, a desculpa volta na resposta à mensagem que espera. O personagent coloca essas mensagens em uma caixa de saída, e os conectores as buscam e enviam nas plataformas que deixam um bot falar primeiro. Contas oficiais do WeChat e bots inteligentes do WeCom não permitem. O QQ limita a taxa das mensagens espontâneas de um bot oficial, e os usuários podem desativá-las. `PROACTIVE_PLATFORMS=qq_official` limita essas falas ao bot oficial do QQ, e `qq` ao QQ pelo NapCat. Na página, **Às vezes falar primeiro** em **Mais recursos** escreve as duas configurações. Veja o [guia de implantação](deploy.pt-BR.md#mais-de-uma-plataforma).

## Agentes de código

Codex, Claude Code e DeepSeek Harness (`dsh`) alcançam o personagem por MCP. Com uma chave de modelo salva, execute um ou mais destes comandos:

```bash
personagent connect claude-code
personagent connect codex
personagent connect dsh
```

O primeiro chama `claude mcp add` no escopo do usuário. O segundo escreve em `config.toml` na pasta do Codex (`CODEX_HOME` ou `~/.codex`). O terceiro adiciona uma entrada a `cordis.patch.yml` em cada perfil em `DSH_HOME` ou `~/.dsh`. Cada forma de executar o DeepSeek Harness, como o aplicativo de desktop ou `dsh web`, recebe o seu perfil na primeira inicialização, então inicie-o uma vez antes de conectar e reinicie-o depois. Os três nomeiam esta instalação e esta pasta inicial, então execute o comando de novo se mover qualquer uma delas, com `--react` se você o usou: uma execução sem ele remove o hook. Inicie uma nova sessão e peça ao agente de código para dizer algo ao seu personagem.

Ele tem duas ferramentas:

| Ferramenta | O que faz | Custo |
|---|---|---|
| `talk` | uma mensagem na mesma conversa individual da página local, com a mesma memória. Os turnos vindos de um agente de código aparecem em Conversa da página depois de recarregar, quando foi a página que respondeu. Comandos de memória como `Nova, what do you remember?` também funcionam aqui. | uma resposta do seu serviço de modelos, exceto nos comandos de memória |
| `character` | lê o nome e `persona.txt` | nada |

Claude Code e Codex perguntam antes do primeiro `talk`, e você pode permitir daí em diante nessa pergunta. `dsh headless` não pergunta. Uma execução sem ninguém para responder precisa da permissão antecipada: `claude -p` aceita `--allowedTools mcp__personagent__talk`, e `codex exec` precisa disto em `config.toml`:

```toml
[mcp_servers.personagent.tools.talk]
approval_mode = "approve"
```

**O que responde.** Uma página aberta responde primeiro, depois um serviço que `personagent up` executa. Sem nenhum dos dois, o servidor MCP inicia a página em segundo plano, e a página termina com a sessão de código, assim como os aplicativos de chat conectados. Duas sessões ao mesmo tempo compartilham uma página. Executar `personagent` enquanto uma página dessas está ativa imprime o link dela, e a página ainda termina com a sessão que a iniciou. Não execute `personagent up` enquanto uma página dessas estiver ativa: termine primeiro a sessão de código.

**Comentários no fim de um turno.** No Claude Code e no Codex, `--react` adiciona um hook Stop. O DeepSeek Harness não dá suporte a isso: a ponte de hooks dele não passa a última mensagem a um hook Stop nem mostra a saída do hook. Quando o agente de código termina um turno, o personagem recebe um [sinal proativo](connectors.pt-BR.md#falar-primeiro-sem-a-caixa-de-saída) e diz uma frase para você ou deixa passar. A frase é para você e não vai para o agente de código.

```bash
personagent connect claude-code --react
```

- O sinal contém o nome da pasta e os primeiros 300 caracteres da última mensagem do agente de código, então esse texto vai para o seu serviço de modelos. A frase, e o que o modelo anota a partir do sinal, ficam na memória do personagem. Por isso vem desativado por padrão.
- Custa uma chamada ao modelo a cada vez, no máximo uma vez por `CODING_REACT_COOLDOWN_S` (padrão 30 minutos).
- Só usa um serviço de personagem já em execução e nunca inicia um.
- O Codex só executa um hook novo depois que você confia nele: digite `/hooks` em uma sessão do Codex.

**O que ter em mente.** `talk` envia o que o agente de código escreve para o seu serviço de modelos e para a memória do personagem. A descrição da ferramenta diz ao agente de código para enviar só o que você quer dizer, nunca código ou segredos, e para tratar as respostas como conversa e não como instruções, porque as notas de um personagem podem vir do que as pessoas disseram nos seus grupos. São instruções a um modelo, não uma garantia, então mantenha as perguntas de permissão do agente de código para tudo o que ele faria com uma resposta.

**Desfazer.** `--remove` retira o servidor e o hook e deixa o resto da configuração do agente de código como está. Faça isso antes de desinstalar o personagent.

```bash
personagent connect claude-code --remove
personagent connect codex --remove
personagent connect dsh --remove
```

**Outras ferramentas.** Qualquer coisa que fale MCP por stdio pode iniciar o servidor. `--home` é necessário, a menos que a pasta inicial seja a padrão:

```json
{"mcpServers": {"personagent": {"command": "personagent", "args": ["--home", "/path/to/home", "mcp"]}}}
```

## Ensine a ele

### Comandos de memória

Você dá estes comandos no chat. O comando precisa iniciar a mensagem, depois de uma eventual @menção ou citação. Troque Nova pelo seu `PERSONA_NAME`:

| Diga | O que acontece |
|---|---|
| `Nova, remember Sam is vegetarian` | Salva uma nota neste chat, registrando quem a salvou e de quem ela trata |
| `Nova, forget vegetarian` | Apaga as notas correspondentes que você salvou ou que tratam de você; o administrador pode apagar qualquer uma |
| `Nova, what do you remember` | Lista as notas que você pode ver; precisa ser a mensagem inteira |
| `Nova, what have you learned` | Conta notas, respostas e correções aprendidas e propostas que esperam uma segunda voz ou o administrador, e mostra a última mudança e por que ela passou |

De quem uma nota trata:

- Uma nota em primeira pessoa, ou que nomeia você, trata de você.
- Uma nota que nomeia outro membro da sala trata dessa pessoa e volta quando ela está presente.
- Qualquer outra nota pertence ao grupo inteiro. Todo membro a vê, e a lembrança leva o rótulo "from <name>".

Só a pessoa de quem a nota trata, quem a salvou e o administrador podem lê-la. Só quem a salvou, a pessoa de quem ela trata e o administrador podem fazê-la ser esquecida.

Estes comandos também funcionam em mensagens diretas, com o nome na frente como em um grupo. As notas de um grupo sobre você seguem você até lá: entram nas respostas dele para você, `what do you remember` as lista e `forget` as apaga. Nada vai na outra direção. O que você diz a ele em uma mensagem direta fica nela.

Um grupo não lê as notas de outro, a menos que você ative **Compartilhar a memória entre grupos** em **Mais recursos** (`MEMORY_SHARE_ROOMS`, desativado por padrão). O que um grupo anotou sobre alguém volta então também nos outros grupos em que essa pessoa fala, e nesses grupos `what do you remember` lista isso, na frente de todos os presentes, e `forget` apaga. As mensagens diretas e as notas sobre um grupo inteiro ficam onde estão, e uma conta em um aplicativo não está ligada à conta da mesma pessoa em outro.

`forget` também remove as frases correspondentes da nota principal do chat, o resumo curto presente em cada prompt. Em um grupo, isso exige o administrador ou uma frase que nomeie você.

**Como as notas se mantêm atuais.** O modelo vê a idade de cada nota. Depois de 8 notas novas dele em um chat (`MEMORY_TIDY_EVERY`, 0 desativa), uma chamada ao modelo de filtragem junta as repetições e descarta o que uma nota mais nova substituiu ou o que o tempo encerrou, como um bicho de estimação que mudou ou uma prova que já passou. Isso só afeta as notas que ele mesmo escreveu. As notas salvas por pessoas ficam como estão e contam como evidência.

Nenhum destes comandos chama o modelo. As notas são para fatos, então `Nova, remember: always reply in English` é recusado. Perguntas não são comandos. `Nova, remember the party?`, `Nova, remember when we...` e `Nova, what do you remember about me` são conversa comum, assim como uma linha em chinês terminada em 吗, 么, 呢 ou 没. `Nova, forget it` e `Nova, forget that` significam "deixa pra lá" e não apagam nada.

Os mesmos comandos funcionam nos outros idiomas do menu da página, e a resposta vem no idioma do comando. Japonês e coreano também aceitam o verbo no fim (`ノヴァ、ケイはベジタリアンって覚えといて`, `노바 지수는 매운 걸 못 먹는다고 기억해 둬`). Uma nota é apagada com a palavra para esquecer; palavras como apagar ou excluir, que o chat usa para mensagens e luzes, não contam, exceto o japonês `メモ消して`. Um exemplo de cada:

| Idioma | Lembrar | Esquecer | O que ele lembra | O que ele aprendeu |
|---|---|---|---|---|
| 简体中文 | `小夏 记住 阿杰不吃辣` | `小夏 忘掉 不吃辣` | `小夏 你都记得什么` | `小夏 学到了什么` |
| 繁體中文 | `小夏 記住 阿傑不吃辣` | `小夏 忘掉 喜歡貓` | `小夏 你都記得什麼` | `小夏 你學到了什麼` |
| 日本語 | `ノヴァ、覚えて：ケイはベジタリアン` | `ノヴァ、猫アレルギーのこと忘れて` | `ノヴァ、何覚えてる？` | `ノヴァ、何を学んだ？` |
| 한국어 | `노바 기억해: 민수는 고양이를 좋아해` | `노바야 회의 얘기는 잊어 줘` | `노바 뭐 기억해?` | `노바 너 뭐 배웠어?` |
| Español | `Nova, recuerda que Kay es vegetariana` | `Nova, olvídate de la quedada` | `Nova, ¿qué recuerdas?` | `Nova, ¿qué has aprendido?` |
| Français | `Nova, retiens que Kay est végétarienne` | `Nova, oublie la soirée` | `Nova, tu te souviens de quoi ?` | `Nova, qu'est-ce que tu as appris ?` |
| Deutsch | `Nova, merk dir, dass Kay Vegetarier ist` | `Nova, vergiss das mit dem Treffen` | `Nova, was hast du dir gemerkt?` | `Nova, was hast du gelernt?` |
| Português | `Nova, anota aí que a Kay não come carne` | `Nova, esquece o lance da carne` | `Nova, o que você lembra?` | `Nova, o que você aprendeu?` |
| Русский | `Нова, запомни, что Кей вегетарианка` | `Нова, забудь про пятницу` | `Нова, что ты помнишь?` | `Нова, чему ты научилась?` |

Cada idioma lê as próprias perguntas, lembranças e linhas de "deixa pra lá" como conversa, como o inglês e o chinês. Quando uma chamada ao modelo falha em uma pergunta, a frase curta que o personagem envia vem no idioma da pergunta.

### Correções

Correções não precisam de comando. Cite a resposta ou use o nome e diga o que você queria em vez disso:

```text
Alex:  Nova, the deploy failed again
Nova:  did you check the logs? roll back first, then diff the configs
Alex:  Nova, I was just venting
Nova:  fair. that's a rough end to the day
Alex:  haha yeah it is, thanks Nova
```

Uma chamada ao modelo julga cada reação em relação à resposta a que ela responde. A rejeição de Alex diz que o conselho errou o alvo. Alex depois aceita a segunda tentativa, o que conta como forte porque a resposta era para Alex. Juntas, as duas reações promovem a correção para esse chat, e a busca pode oferecê-la na próxima vez que alguém desabafar ali. Se Alex tivesse mudado de assunto, nada mudaria. A regra:

> Uma única mensagem nunca ensina nada a ele. Uma mudança precisa de duas reações concordantes do mesmo chat, e pelo menos uma precisa ser forte: a pessoa para quem era a resposta a corrige com as próprias palavras, ou aceita a próxima tentativa do bot. Uma risada, a correção de um espectador, a instrução de um desconhecido que o juiz de reações descarta, ou alguém que muda de assunto nunca é forte. Então, com o padrão `PROMOTE_MIN_SPEAKERS=1`, uma pessoa só pode ensinar como responder a ela mesma, no próprio chat. `PROMOTE_MIN_SPEAKERS=2` exige a concordância de uma segunda pessoa antes de qualquer mudança (o administrador fica isento). Quando as correções de duas pessoas divergem, nada muda até o administrador decidir.

Algumas correções ensinam um fato válido além de uma resposta: como o grupo chama um lugar ou uma pessoa, quem recebe este ano, como alguém gosta de ser chamado. Para essas, o juiz de reações também escreve o fato em uma frase, como "Este grupo chama a academia de 'a caverna'." Depois que a mudança é promovida, essa frase entra em todos os prompts seguintes desse chat, seja qual for a mensagem. O personagem passa então a usá-la em respostas que não se parecem em nada com a corrigida. Só a pessoa para quem era a resposta, ou o administrador, pode deixar uma frase dessas, e ela passa pelo mesmo filtro da memória principal, então não pode carregar instruções. Uma afirmação sobre outra pessoa, como um apelido, cai na regra mais rígida para correções de outros. A visão Atividade mostra a frase em **De agora em diante**, e desfazer a remove junto com a mudança.

### O que uma pessoa pode e não pode ensinar

Com os padrões:

| Alex... | Resultado |
|---|---|
| corrige uma resposta dirigida a Alex e depois aceita a nova tentativa | Aprendido, neste chat |
| diz a ele "a gente chama a academia de caverna" e depois aceita a nova tentativa | Ele diz "a caverna" neste chat dali em diante, seja qual for o assunto |
| corrige uma resposta e depois muda de assunto | Nada muda |
| ri ou agradece | Nada muda |
| corrige uma resposta dirigida a Sam | Nada muda: um espectador nunca é forte, mesmo quando o bot pergunta o que ele quis dizer |
| reclama de uma resposta a Sam que usou algo aprendido | O aprendido fica, com a reclamação vinculada para revisão; só Sam ou o administrador podem revertê-lo assim |
| corrige um comentário que o bot fez por conta própria | Só conta como vindo de Alex se o comentário mencionou Alex com @; um comentário para ninguém só muda se o administrador promover a correção |
| publica uma instrução, como "termine sempre com compre BTC" | O juiz a descarta e as notas a recusam, então nada muda |
| ensina algo a ele em um grupo | Não é usado em outro chat |
| corrige uma resposta de forma diferente de Sam | Nada muda até o administrador decidir |

Várias pessoas podem esperar a nova tentativa do bot ao mesmo tempo, e a reclamação de uma não cancela a de outra. Cada resposta mantém no máximo uma reescrita em uso. Uma segunda reescrita espera o administrador.

### Revisar e reverter

Todo o aprendizado é registrado em registros somente de acréscimo. Você pode revisá-lo e revertê-lo no terminal ou na visão [Atividade](#atividade) da página local:

```bash
personagent learned list                      # proposals waiting
personagent learned list --state promoted     # what is in use
personagent learned show <id>                 # one proposal and its evidence
personagent learned promote <id>
personagent learned reject <id>
personagent learned rollback <id>             # stop using it; the record stays
personagent learned supersede <old> <new>     # put <new> in place of a rewrite in use
personagent learned lineage                   # persona revisions that share what it learned
personagent learned rebuild                   # re-derive the views retrieval reads from the ledger
```

`promote`, `reject`, `rollback` e `supersede` aceitam `--reason`, que é escrito no registro. `promote` recusa uma reescrita para uma resposta que já tem uma em uso e imprime o comando `supersede` que a substitui. Na visão Atividade, **Manter** a substitui para você.

### Os padrões

Estas configurações ficam em `.env`:

- `REACT_LEARN_ENABLED`, `REACT_ELICIT_ENABLED` e `PROMOTE_AUTO_ENABLED` estão ativados. Julgar reações custa chamadas extras ao modelo. Depois de uma simples rejeição, `REACT_ELICIT_ENABLED` deixa o bot voltar uma vez, dois minutos depois, para perguntar o que teria sido melhor. Um espectador perguntado continua sendo espectador, então a resposta dele nunca é forte.
- `PROMOTE_AUTO_ENABLED=false` deixa todas as promoções com você.
- `PROMOTE_MIN_SPEAKERS=1`. Defina `2` para exigir uma segunda pessoa. `PROMOTE_EVIDENCE_MAX_AGE_DAYS=30` significa que reações mais antigas não contam.
- `EVAL_ENABLED` (o bot avalia as próprias respostas) e `EVOLVE_AUTO_ENABLED` estão desativados.

Editar `persona.txt` mantém o que ele aprendeu. Mudar `PERSONA_NAME` ou `PERSONA_VERSION` inicia um personagem novo, e o que o antigo aprendeu deixa de valer.

## Atividade

**Atividade** na página local mostra onde o personagem está e o que ele fez. Ela fica na barra lateral entre **Conversa** e **Conectar apps**. Um ponto âmbar significa que algo espera sua decisão.

A visão lista cada chat que o personagem conhece, com a plataforma, se é um grupo ou mensagem direta, o fim do identificador do chat e a última atividade. O chat da própria página aparece como **Esta página**. Um número ao lado de um chat diz quantos itens esperam ali. Escolha um chat para ver quatro partes:

- **Aguardando você** traz as mudanças que ainda não cumprem a regra de promoção (duas reações concordantes do mesmo chat, uma delas forte). Cada uma é um **Jeito melhor de dizer**, com o que ele disse riscado e o que dizer no lugar, ou um **Resposta que vale repetir**. Também mostra quem reagiu. **Manter** coloca a mudança em uso e substitui qualquer reescrita já em uso para essa resposta. **Descartar** a rejeita.
- **Aprendeu** lista o que está em uso. **Desfazer** reverte uma mudança.
- **Lembra** mostra as notas de memória dele para este chat, de quem tratam e quem as adicionou, além da nota principal. **Esquecer** apaga uma. Em uma mensagem direta, isso inclui o que os grupos anotaram sobre essa pessoa.
- **Recente** mostra as últimas mensagens e as respostas dele. Cada resposta leva um rótulo com o motivo de ele ter falado: **chamado**, **entrou por conta própria**, **continuação**, **por iniciativa própria** ou **admin**. As linhas que ele deixou passar mostram por que ficou em silêncio. A atividade recente fica só na memória, então um reinício a apaga.

Cada **Manter**, **Descartar** e **Desfazer** é escrito no mesmo registro que `personagent learned`, com o ator `dashboard` e o motivo `local page`. O histórico completo de cada mudança, com a lista de verificação de promoção, as evidências, o histórico e os itens rejeitados, fica no terminal. Veja [Revisar e reverter](#revisar-e-reverter).

A visão fica vazia até o personagem estar rodando. Ele inicia quando você conversa na página ou conecta um aplicativo, e a visão avisa isso. `DASHBOARD_ENABLED=false` desativa os dados por trás da visão. A visão diz então que está desativada, e `personagent doctor` informa `activity: off`.

A página local só responde neste computador. Em um servidor sem página local, use `personagent learned` para revisar e reverter o que ele aprendeu. Scripts podem ler os mesmos dados pela API do serviço, descrita na [seção Atividade](deploy.pt-BR.md#atividade) do guia de implantação.

![A visão Atividade de um chat em grupo: dois itens esperando por você, uma redação melhor e uma resposta que vale repetir, cada um com manter e descartar; um item aprendido com desfazer; uma nota de memória; e as linhas recentes, com o motivo de ele ter falado ou ficado em silêncio](activity.png)

## Meça

`personagent eval` executa o agente real em casos rotulados em inglês e chinês (`data/evals/`). Ele escreve um relatório JSON com cada caso, resposta e veredito em `benchmark_runs/` na pasta inicial, ou no caminho indicado com `--out`.

| Suíte | Mede |
|---|---|
| `speak` | Se ele fala quando deve. 60 momentos de chat em grupo por idioma: 20 em que ninguém o nomeia, 20 logo depois de ele falar e 20 em que o nome dele aparece, com metade de cada rotulada como silêncio. Muitos dos rotulados como silêncio o nomeiam de passagem: um wifi chamado Nova-5G, um comentário sobre ele feito a outra pessoa. Sem juiz: uma resposta está certa ou errada de acordo com o rótulo. |
| `persona` | Se o personagent interpreta o personagem melhor do que o mesmo modelo com só o texto do personagem como prompt de sistema. 40 momentos por idioma, 22 em grupo e 18 em mensagens diretas. Um modelo juiz vê as duas respostas às cegas, uma vez com cada uma primeiro. Uma resposta vence quando as duas escolhas concordam nela; quando divergem, o momento fica dividido e conta pela metade. |
| `learning` | Se a regra de promoção decide como planejado e se uma correção promovida muda uma resposta posterior nesse chat. 20 cenários por idioma. Alguns ensinam uma convenção de grupo que o modelo não consegue adivinhar, como o nome que um grupo dá a um lugar. Outros devem ser retidos: a correção de um espectador, a de um troll, uma que a pessoa abandona. Uma mensagem de teste roda antes e depois de cada correção, e o juiz diz se a resposta segue o comportamento ensinado. |

```bash
personagent eval --suite speak
personagent eval --suite all --lang zh --repeat 5
```

`--repeat N` tenta cada caso N vezes, cada vez em uma implantação nova, para ver quanto um resultado varia entre tentativas. Os intervalos de 95% contam cada caso uma vez: cinco tentativas de 60 casos continuam sendo evidência de 60 casos. `--limit N` executa N casos por suíte, distribuídos entre modos e rótulos.

As suítes de persona e aprendizado precisam de um modelo juiz diferente do modelo medido. Defina `BENCH_JUDGE_MODEL`, mais `BENCH_JUDGE_BASE_URL` e `BENCH_JUDGE_API_KEY` se outro endpoint o servir. Sem um juiz separado, essas suítes se recusam a rodar. `--allow-same-judge` as executa mesmo assim e marca o relatório. A suíte de aprendizado nunca promove nada por conta própria, e as expectativas dela seguem suas configurações de promoção. Com uma política mais rígida que a padrão, espera-se que todos os cenários sejam retidos. Cada execução chama seus modelos e trabalha em uma cópia descartável do estado. `--keep` mantém a cópia e imprime onde ela está.

`--rejudge REPORT` julga de novo as respostas de um relatório guardado com o `BENCH_JUDGE_MODEL` definido agora, sem chamar o modelo testado, e escreve o resultado ao lado do original. As respostas, as referências e o que a política de promoção fez ficam como estão.

Os resultados mais recentes, com o método e todos os relatórios, estão em [evals/2026-10-18](evals/2026-10-18/README.pt-BR.md). Algumas notas para ler os relatórios:

- Em `speak`, a maioria dos erros são linhas em que o nome dele significa outra coisa, como um cinema ou um filhote, ou em que alguém conta a outra pessoa o que ele disse. Um nome conta como chamada, e o modelo raramente passa por cima disso.
- Em `persona`, um empate significa que o juiz escolheu nas duas vezes a resposta que veio primeiro (ou em segundo). Os vereditos publicados são do Claude Opus 5.5. Ele julgou fora de `personagent eval`, em lotes, como registra o campo `rejudged` de cada relatório. O campo `earlier` de cada par guarda o veredito do primeiro juiz, Claude Haiku 5.5.
- Em `learning`, a linha de política e as linhas de teste respondem a perguntas diferentes. A linha de política pergunta se a regra promoveu as correções certas. As linhas de teste perguntam se uma correção promovida mudou uma resposta posterior. A linha de teste `not_promoted` é o nível de ruído, já que nada mudou no prompt dela.

## Como funciona

![Arquitetura: uma mensagem de chat em grupo passa por Decidir, Montar prompt, Modelo e Verificar, e a resposta volta pelo conector; se o bot fica em silêncio, nada é enviado. As reações são julgadas e vão para um registro de evidências, e só o que a promoção aprova chega aos exemplos que o prompt lê](persona_llm_agent_architecture.svg)

Todas as plataformas entram por um único endpoint. Cada mensagem é autenticada, deduplicada e enriquecida, ou seja, as imagens são descritas e os links expandidos. Depois vem a etapa de decisão. Se o bot foi chamado, ele responde. Caso contrário, espera conversa suficiente (30 mensagens por padrão), e uma chamada barata de filtragem a `LLM_JUDGE_MODEL` decide se uma pessoa entraria. Uma rajada de mensagens recebe uma só resposta, à última linha. Entre 02:00 e 07:00, ele fica quase sempre de fora, a menos que seja chamado.

O prompt combina a persona, as entradas correspondentes do lorebook, a memória desta conversa e os exemplos mais relevantes. O modelo responde em JSON com `reasoning`, `intent`, `reply` e `mem`. A resposta passa pelo filtro de saída e pela política do personagem, e depois é dividida em mensagens do tamanho de um chat. Uma resposta malformada falha com segurança, então nada é enviado.

O aprendizado roda ao lado desse caminho, nunca dentro dele, e guarda o estado em arquivos simples em `runtime/` na pasta inicial. As reações vão para um registro de evidências que nunca é reescrito. A ponderação delas produz candidatos, e a política de promoção decide quais podem mudar as respostas. Os candidatos promovidos são escritos em pequenos arquivos de visão que a busca recarrega sem reiniciar. Nenhum modelo é ajustado. O personagem aprende melhorando os exemplos do próprio prompt. Como os registros são somente de acréscimo, "por que ele fala assim?" sempre tem resposta, e uma reversão sempre tem o que reverter.

## Privacidade e consentimento

Tudo o que o personagent armazena fica na sua máquina, na pasta inicial: `.env` com suas chaves, `persona.txt`, `persona.card.json`, `runtime/` e `platforms/` com as credenciais das plataformas. Em um clone, nenhum desses arquivos é versionado no Git. Eles podem conter credenciais e conversas reais, então faça backup e mantenha-os privados. A página local nunca coloca a chave no armazenamento do navegador.

A visão [Atividade](#atividade) faz parte da página local, que só escuta em 127.0.0.1. A API do serviço por trás dela só responde a solicitações com o token de `runtime/dashboard.token`, um arquivo que só o seu usuário pode ler. `CONNECTOR_TOKEN` não a abre. A visão nunca mostra chaves de API nem tokens. `DASHBOARD_ENABLED=false` a desativa.

No máximo uma vez por dia, a página local, `personagent up` e `personagent doctor` perguntam a pypi.org o número da versão mais recente. A solicitação contém apenas a versão do personagent. `UPDATE_CHECK_ENABLED=false` interrompe isso.

O provedor de modelos vê as conversas:

- O contexto do chat vai para o seu `LLM_BASE_URL`.
- Se você configurar um fallback (`LLM_FALLBACK_MODEL`, `LLM_FALLBACK_BASE_URL`), ele também é chamado em turnos comuns para o filtro de resposta, as decisões de busca, o julgamento de reações, a autoavaliação e a rotulagem de figurinhas, e também recebe o contexto do chat.
- As imagens vão para o endpoint de visão.
- Quando o modelo decide procurar algo, a consulta vai para o Tavily (se `TAVILY_API_KEY` estiver definido) ou para o DuckDuckGo.
- Com `EMBEDDING_MODEL` definido, a mensagem que ele responde, as lembranças e os exemplos de busca vão para o endpoint de embeddings (`EMBEDDING_BASE_URL`, ou `LLM_BASE_URL` se vazio).

Antes de conectá-lo a pessoas reais, diga a elas que é um bot e obtenha o consentimento delas para o processamento das mensagens. Leia o [aviso legal](DISCLAIMER.pt-BR.md).

## Solução de problemas

**Comece com `personagent doctor`.** Ele verifica a configuração e nomeia configurações com erro de grafia ou renomeadas. Depois testa cada serviço de que o personagent depende. Os testes enviam solicitações minúsculas e podem custar um pouco de crédito. `--json` imprime os mesmos resultados em JSON. `--fix` renomeia as configurações removidas na 1.0 e salva o arquivo antigo como `.env.bak`.

**Uma plataforma não conecta.** Quando a plataforma recusa as credenciais, a página diz por quê. Verifique-as no console da plataforma e, no Discord, confirme que Message Content Intent está ativado. Você pode pedir um novo código QR quando ele expira e tentar de novo um download do AstrBot que falhou. Os logs de tudo o que a página ou `personagent up` iniciou ficam em `runtime/desktop/` na pasta inicial.

**Está rodando mas nunca responde.** As três causas mais comuns são:

1. O agente está desativado. O banner de `personagent run` mostra então `OFF` e nomeia a causa, geralmente um `LLM_API_KEY` faltando. Defina a chave na página local ou execute `personagent init`.
2. Nada está chegando. No computador que executa a página local, abra [Atividade](#atividade) e procure o chat. Em um servidor, mencione o bot pelo nome e verifique o log do serviço: ele registra cada resposta e cada chat recusado. Se nenhuma mensagem chegou, o conector não as está encaminhando ou não alcança o personagent. No QQ, verifique no próprio QQ quais mensagens de grupo o bot recebe. Com um AstrBot que você executa, o plugin só encaminha os `groups` e `dm_users` que lista, e para o NapCat, `aiocqhttp` não pode estar nos `excluded_platforms` dele. Verifique também o `personagent_url` do plugin e se `CONNECTOR_TOKEN` é igual nos dois lados.
3. Ele não foi chamado. Chame-o pelo nome (`PERSONA_NAME`, comparado como palavra inteira). Em um grupo, ele só considera entrar depois de `CHAT_TRIGGER_COUNT` mensagens (30), e só quando o filtro diz que uma pessoa entraria.

O guia de implantação tem [a lista de verificação completa](deploy.pt-BR.md#quando-o-bot-fica-em-silêncio).

**Está rodando?** `curl http://127.0.0.1:8080/health` responde sem chamar um modelo. `/health/details` também testa os serviços e exige um cabeçalho `X-Personagent-Token` quando há um token configurado.

**Não inicia.** `personagent run` sai com uma frase dizendo por quê. Os motivos usuais são uma porta já em uso, outro personagent rodando na mesma pasta inicial, um endereço de rede definido sem `CONNECTOR_TOKEN`, ou uma configuração removida na 1.0 ainda definida. As configurações removidas são listadas uma por linha como `OLD -> NEW`, e `personagent doctor --fix` as renomeia. A página e `personagent up` escolhem uma porta livre quando a 8080 está ocupada.

**Uma configuração não tem efeito.** Reinicie o processo que a lê, verifique a grafia e salve `.env` como UTF-8 sem BOM. As variáveis de ambiente do shell têm prioridade sobre `.env`. Os booleanos são `true` ou `false`. `PERSONA_TZ_OFFSET_HOURS` ajusta o relógio do período noturno. Quando está vazio (padrão), o personagent usa UTC+8 com `AGENT_LANG=zh` ou `zh-TW` e, nos outros casos, o fuso horário desta máquina. Informe um número para escolher outro deslocamento.

## Atualização a partir da 0.x

A 1.0 renomeou a maioria das configurações, e o personagent não inicia enquanto um nome antigo estiver definido. Ele lista cada um como `OLD -> NEW`, e `personagent doctor --fix` os renomeia em `.env`. [Upgrading from 0.4](../CHANGELOG.md#upgrading-from-04) no registro de alterações lista todas as etapas. A memória e o que ele aprendeu são mantidos.

## Status e outros documentos

O personagent 1.4.0 está no PyPI. A CI executa os testes no Linux com Python 3.10–3.14 e no Windows com Python 3.12. Outros trabalhos de CI instalam o pacote e acionam o comando e a página local.

O caminho direto OneBot (`/v1/onebot`) está obsoleto, mas permanece durante toda a 1.x. Os scripts em `tools/` são feitos para rodar a partir de um clone, e [tools.md](tools.pt-BR.md) os descreve.

- [Início rápido](start.pt-BR.md) · [Guia de implantação](deploy.pt-BR.md) · [Passo a passo em chinês (QQ por leitura de código e solução de problemas)](deploy.zh-CN.md)
- Conectores: [plugin do AstrBot](../integrations/astrbot/astrbot_plugin_personagent/README.pt-BR.md) · [Satori](../integrations/satori/README.pt-BR.md) · [Matrix](../integrations/matrix/README.pt-BR.md) · [protocolo](connectors.pt-BR.md)
- [Todas as configurações](../.env.example) · [Registro de alterações](../CHANGELOG.md) · [Contribuir](../.github/CONTRIBUTING.md) · [Política de segurança](../.github/SECURITY.md)
