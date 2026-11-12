# Guia do usuário do personagent

[English](guide.md) · [简体中文](guide.zh-CN.md) · [繁體中文](guide.zh-TW.md) · [日本語](guide.ja.md) · [한국어](guide.ko.md) · [Español](guide.es.md) · [Français](guide.fr.md) · [Deutsch](guide.de.md) · Português (Brasil) · [Русский](guide.ru.md)

Este guia explica como configurar o personagent, conectá-lo às suas conversas, ensiná-lo e mantê-lo. O [README](readme/README.pt-BR.md) é a versão curta, e o [início rápido](start.pt-BR.md) percorre a página local tela por tela.

1. [Instalação e a pasta inicial](#instalação-e-a-pasta-inicial)
2. [A página local](#a-página-local): [Configurações avançadas](#configurações-avançadas) · [A visão Aplicativo](#a-visão-aplicativo)
3. [Veja primeiro: a demonstração](#veja-primeiro-a-demonstração)
4. [Comandos de terminal](#comandos-de-terminal): [configuração](#configurar-no-terminal) · [conectar uma plataforma](#conectar-uma-plataforma-no-terminal) · [chat](#conversar-no-terminal) · [executar o serviço](#executar-o-serviço)
5. [Faça dele o seu personagem](#faça-dele-o-seu-personagem)
6. [Coloque em um chat](#coloque-em-um-chat): [Plataformas que o personagent conecta por conta própria](#plataformas-que-o-personagent-conecta-por-conta-própria) · [Outras plataformas](#outras-plataformas-pelo-astrbot-gerenciado) · [Pontes que você mesmo executa](#pontes-que-você-mesmo-executa) · [Falar primeiro](#falar-primeiro)
7. [Assistentes de programação](#assistentes-de-programação)
8. [Ensine a ele](#ensine-a-ele)
9. [Memória](#memória)
10. [Atividade](#atividade)
11. [Meça](#meça)
12. [Como funciona](#como-funciona)
13. [Privacidade e consentimento](#privacidade-e-consentimento)
14. [Solução de problemas](#solução-de-problemas)
15. [Atualização a partir da 0.x](#atualização-a-partir-da-0x)
16. [Status e outros documentos](#status-e-outros-documentos)

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

O personagent funciona com o Python 3.10–3.14. `start.bat` cria `.venv`, instala as dependências e abre a mesma página; na primeira vez, também coloca um ícone do personagent na área de trabalho e no menu Iniciar. Ele as reinstala sempre que a lista de dependências em `pyproject.toml` muda.

A **pasta inicial** guarda as configurações (`.env`), o personagem (`persona.txt`), o que ele aprende (`runtime/`) e as plataformas de chat (`platforms/`). `platforms/` contém o AstrBot gerenciado e `direct.json`, que armazena as credenciais das plataformas que o personagent conecta por conta própria. O personagent usa a primeira destas pastas:

1. a pasta de `--home DIR` ou `AGENT_HOME`. `--home` pode vir antes ou depois do comando, como em `personagent chat --home D:\bot`.
2. o clone, quando você executa a partir de um clone.
3. a pasta atual, se ela tiver tanto `.env` quanto `persona.txt`.
4. `~/personagent`, criada na primeira configuração.

Para executar vários personagens a partir de uma instalação, dê a cada um a sua própria pasta inicial.

Este guia escreve os comandos como `personagent ...`. Se você não o instalou, coloque `uvx` na frente. Em um clone, `.venv/bin/python -m persona_agent ...` faz o mesmo (no Windows, `.venv\Scripts\python.exe -m persona_agent ...`).

## A página local

`personagent` (ou `personagent start`) serve uma página acessível apenas deste computador. No Windows, ela abre em uma janela própria. No macOS e no Linux, abre no navegador, ou também em uma janela depois que `pip install "personagent[app]"` instalar o [pywebview](https://pywebview.flowrl.com/), junto com o Qt no Linux. A página tem seis visões, listadas na barra lateral nesta ordem:

- **Conversa** é uma conversa individual com o personagem na página. O mesmo agente que atende às suas plataformas de chat responde aqui. Nesta conversa, você é o administrador. As figurinhas e as imagens que o personagem envia aparecem na conversa, e uma imagem que não está mais armazenada é substituída por uma breve observação. As mensagens que o personagem envia depois da resposta, como a resposta a um comando de memória enviado enquanto ele respondia ou uma mensagem iniciada por ele mesmo, aparecem em poucos segundos enquanto a visão Conversa estiver aberta. Ambas permanecem no histórico da conversa. Quando o modelo não responde, a página informa isso no lugar de uma resposta e oferece **Enviar novamente**. **Comandos de memória**, abaixo da caixa de mensagem, lista os [comandos de memória](#comandos-de-memória), e selecionar um deles o insere na caixa de mensagem. **Esquecer esta conversa** esquece tudo o que o personagem lembra desta conversa e inicia uma nova; o que ele lembra de outras conversas é mantido, e esse esquecimento não pode ser desfeito. Esse recurso depende dos dados por trás da [Atividade](#atividade).
- **Atividade** mostra os chats em que o personagem está, o que ele disse recentemente, o que ele lembra e o que aprendeu. Veja [Atividade](#atividade).
- **Conectar plataformas** coloca o personagem no QQ, WeChat, Telegram, Discord e outras plataformas. Veja [Coloque em um chat](#coloque-em-um-chat). Na parte inferior, **Assistentes de programação** conecta o personagem aos [assistentes de programação](#assistentes-de-programação) deste computador.
- **Personagem e configurações** é onde você escolhe um serviço de modelos (OpenRouter, DeepSeek, SiliconFlow, Alibaba Bailian, Zhipu GLM, Moonshot, Volcengine Ark, OpenAI, Google Gemini, Ollama ou qualquer outro serviço compatível com OpenAI), cola a chave de API e escolhe um nome e uma personalidade pronta. **Verificar e iniciar a conversa** testa a chave com uma pequena solicitação e só a salva se a solicitação funcionar. Depois da configuração, a caixa **Persona** mostra `persona.txt`. **Salvar a persona** reinicia o agente com o novo texto e mantém o que ele aprendeu. **Mais recursos** ativa a pesquisa na web pelo Tavily (DuckDuckGo é o padrão gratuito), a compreensão de imagens e o início de conversas por iniciativa própria nas plataformas que você escolher. Em seguida vêm as [Configurações avançadas](#configurações-avançadas).
- **Prática** reproduz a demonstração roteirizada e oferece um grupo de prática. Veja [Veja primeiro: a demonstração](#veja-primeiro-a-demonstração).
- **Aplicativo** verifica os serviços de que o personagem depende e reúne os logs, a execução em segundo plano, as atualizações e os seus dados. Veja [A visão Aplicativo](#a-visão-aplicativo).

**Prática** e **Aplicativo** abrem antes mesmo de um modelo ser configurado. Até que você conecte uma plataforma, a visão Conversa mostra uma barra curta de **Primeiros passos**.

Executar `personagent` novamente exibe a página que já está aberta. `--browser` abre a página no navegador em vez de em uma janela, e `--no-browser` imprime o link e não abre nada. No Windows, `personagent shortcut` coloca na área de trabalho e no menu Iniciar um ícone que abre a janela sem nenhum terminal por trás, e `personagent shortcut --remove` o remove. A visão Aplicativo oferece o mesmo recurso.

Quando há um personagent mais novo no PyPI, a visão Conversa mostra um aviso com o comando que atualiza sua instalação, seja ela do pip, uvx, uv tool, pipx ou de um clone Git. Para um ZIP do código-fonte descompactado, o aviso aponta para a página de versões. O terminal imprime o mesmo comando. Fechar o aviso o oculta para aquela versão, e **N disponível** abaixo do número da versão o traz de volta. `personagent up` e `personagent doctor` também informam uma versão nova. A página e `up` consultam pypi.org no máximo uma vez por dia, em segundo plano. `doctor` consulta na hora quando a última resposta tem mais de um dia. Defina `UPDATE_CHECK_ENABLED=false` para desativar a verificação. A visão Aplicativo também pode instalar a atualização por conta própria; veja [Versão e atualizações](#versão-e-atualizações).

A página inicia o agente e as plataformas conectadas em segundo plano, então mantenha a janela aberta enquanto os usa. Tudo o que ela iniciou termina com ela, seja ao selecionar **Sair**, ao pressionar Ctrl+C ou ao fechar a janela. Enquanto houver uma plataforma conectada, fechar a janela pede confirmação antes. No Windows, é possível fazer com que o personagent continue em execução quando a janela é fechada; veja [Executar em segundo plano](#executar-em-segundo-plano). Se uma execução anterior travou e deixou processos, a próxima inicialização os encerra primeiro.

### Configurações avançadas

Depois que um modelo é configurado, **Personagem e configurações** termina com **Configurações avançadas**. Essa parte reúne, em seis seções, configurações que antes só estavam disponíveis no `.env`. Todas são opcionais e têm um valor padrão, e um campo vazio usa o padrão.

| Seção | Configurações |
|---|---|
| **Administrador e acesso** | Como o personagem chama você e qual é a sua relação com ele (`ADMIN_NAME`, `ADMIN_RELATIONSHIP`); **Suas contas** (`ADMIN_IDS`); **Responder apenas nestes grupos** (`ACCESS_GROUPS`); **Outras pessoas autorizadas a enviar mensagens privadas** (`ACCESS_DM_USERS`). **Escolher entre as conversas recentes** lista as pessoas e os grupos da Atividade, para que você adicione os identificadores deles sem digitá-los. |
| **Participação e estilo de resposta** | **Fuso horário** (`PERSONA_TZ_OFFSET_HOURS`); **Mensagens antes de participar** (`CHAT_TRIGGER_COUNT`); **Frequência com que inicia conversas**, que define de uma só vez os sete intervalos `PROACTIVE_*`; **Estilo de resposta**: emojis, três conjuntos de símbolos e o tamanho máximo da resposta, gravados em `persona.card.json`. |
| **Modelos** | Um modelo reserva com endereço de serviço e chave próprios (`LLM_FALLBACK_MODEL`, `LLM_FALLBACK_BASE_URL`, `LLM_FALLBACK_API_KEY`), o modelo para decisões rápidas (`LLM_JUDGE_MODEL`) e o modelo para conversas privadas (`LLM_DM_MODEL`). O modelo reserva é testado antes de ser salvo. |
| **Aprendizado** | `REACT_LEARN_ENABLED`, `REACT_ELICIT_ENABLED`, `PROMOTE_AUTO_ENABLED`, `PROMOTE_MIN_SPEAKERS` (1 ou 2), `PROMOTE_JUDGE_ENABLED` (o personagem decide o que as reações não conseguem resolver) e `PROMOTE_OBSERVE_MAX_DAYS` (dias sem nenhuma reação nova antes que um item em observação seja deixado de lado). **Reiniciar o aprendizado** grava um novo `PERSONA_VERSION`, de modo que o que o personagem aprendeu até então deixa de ser usado. Nada é apagado. |
| **Memória** | `MEMORY_CALLS_PER_DAY`, `MEMORY_TIDY_EVERY`, `CHAT_CONTEXT_MESSAGES`, `MEMORY_PROMPT_CHARS`, `MEMORY_EPISODES_MAX` e `MEMORY_KEEP_RECENT`. Veja [Memória](#memória). |
| **Outras configurações** | `AGENT_ENABLED`, `DASHBOARD_ENABLED`, `UPDATE_CHECK_ENABLED`, os sete intervalos `PROACTIVE_*`, `CHAT_FOLLOWUP_WINDOW_S`, os limites `REACT_*` e `PROMOTE_*`, `REACT_MODEL`, o modelo, o intervalo e o tamanho do lote das decisões do próprio personagem (`PROMOTE_JUDGE_MODEL`, `PROMOTE_JUDGE_INTERVAL_S`, `PROMOTE_JUDGE_BATCH`) e `PERSONA_VERSION`. |

**Salvar** grava apenas as configurações alteradas e mantém o restante do `.env` como estava. Em seguida, reinicia o personagem, exceto quando `UPDATE_CHECK_ENABLED` é a única alteração. Desativar as respostas (`AGENT_ENABLED`) pede confirmação antes. O mesmo ocorre ao renomear o personagem em **Nome do personagem**, pois um novo nome inicia um novo personagem.

### A visão Aplicativo

**Aplicativo** exibe um ponto vermelho quando algo requer atenção: um serviço não iniciou, uma configuração tem um nome antigo ou um erro, uma conexão com plataforma falhou ou a última verificação falhou.

**Verificação de funcionamento.** **Iniciar a verificação** testa cada serviço de que o personagem depende: o modelo de chat para respostas em grupos e em conversas privadas, a decisão de pesquisa na web, a avaliação de reações, as decisões de aprendizagem, a revisão das próprias respostas, a compreensão de imagens, o modelo de autoavaliação, a busca na memória, a pesquisa na web, a ponte do QQ (NapCat) e os registros de aprendizado. Cada linha de modelo testa o modelo que realiza aquele trabalho. **Decisão de pesquisa na web** testa o modelo juiz (`LLM_JUDGE_MODEL`; na falta dele, o modelo reserva; na falta deste, o modelo principal) e falha quando esse modelo não chama a ferramenta de pesquisa, porque nesse caso a pesquisa na web nunca seria executada. **Avaliação de reações** testa `REACT_MODEL` ou, na falta dele, o modelo juiz, e é ignorada enquanto `REACT_LEARN_ENABLED` estiver desativado. **Decisões de aprendizagem** testa o modelo com o qual o personagem decide o que as reações não conseguem resolver (`PROMOTE_JUDGE_MODEL` ou, na falta dele, o modelo da avaliação de reações) e é ignorada enquanto `PROMOTE_JUDGE_ENABLED` ou `PROMOTE_AUTO_ENABLED` estiver desativado. **Revisão das próprias respostas** testa `EVOLVE_MODEL` (na falta dele, `EVAL_MODEL`; depois, o modelo reserva; por fim, o modelo principal) e é ignorada enquanto `EVOLVE_AUTO_ENABLED` estiver desativado. Quando uma dessas duas linhas testaria um modelo que uma linha anterior já testa, esse modelo não é consultado de novo e a linha mostra o resultado daquela linha. **Modelo de autoavaliação** é ignorado enquanto `EVAL_ENABLED` estiver desativado. Cada serviço ocupa uma linha, marcada como **Funcionando**, **Com falha** ou **Não configurado**, e um veredito acima das linhas indica o que corrigir. Quando o personagem está em execução, a verificação passa por ele. Caso contrário, uma execução de teste separada realiza as mesmas verificações que `personagent doctor`. Uma verificação envia algumas solicitações curtas e consome uma pequena parte da cota do seu serviço de modelos. Um resultado com menos de um minuto é reaproveitado enquanto as configurações não mudarem. A mesma parte da visão também mostra:

- por que o personagem, o AstrBot ou a conexão com plataformas não iniciou, com a linha de log correspondente, **Mostrar o log** e **Reiniciar**;
- **Configurações com nomes antigos**: configurações renomeadas na 1.0. **Renomear as configurações** faz o mesmo que `personagent doctor --fix`. Pede confirmação antes, mantém o arquivo anterior como `.env.bak` e inicia o personagem novamente caso ele tenha se recusado a iniciar;
- **Conexões com plataformas**: o estado de cada plataforma que o personagent conecta por conta própria e, quando uma delas falhou, o motivo;
- **Configurações a revisar**: problemas encontrados no `.env`, como uma chave de modelo ausente, uma configuração que o personagent não lê, um valor vazio ou uma marca de ordem de bytes (BOM);
- **Logs**: as últimas linhas de cada log em `runtime/desktop/` (o personagem, o AstrBot, as conexões com plataformas, os downloads e a instalação, o aplicativo, a Prática e a última atualização). Chaves e tokens reconhecíveis são ocultados, mas o conteúdo das conversas pode aparecer. **Mostrar mais linhas** exibe até 200 linhas, e **Abrir a pasta de logs** abre a pasta.

**Uso do modelo.** O personagent contabiliza cada solicitação que faz a um modelo, por modelo e por dia, a partir do uso que o serviço de modelos informa: as solicitações, os tokens e o custo, quando o serviço o informa, como faz o OpenRouter. A visão Aplicativo mostra o dia de hoje e os últimos 7 dias. `personagent doctor` imprime os mesmos números, e `doctor --json` os acrescenta como `model_use`. As contagens são mantidas por 8 dias em `runtime/model_usage.json`. O personagent grava esse arquivo em segundo plano, no máximo uma vez por minuto e mais uma vez quando é encerrado, para que a contagem nunca atrase uma resposta.

#### Executar em segundo plano

Esta parte está disponível na janela do aplicativo no Windows. Com **Continuar em execução após fechar a janela** marcado, fechar a janela move o personagent para um ícone na área de notificação, no canto inferior direito da tela, e o personagem continua respondendo. O menu do ícone reabre ou encerra o personagent, e um clique duplo no ícone o abre. **Mover para segundo plano agora** oculta a janela imediatamente. `personagent start --background` inicia o personagent por trás do ícone, sem exibir a janela, desde que essa opção esteja marcada.

#### Versão e atualizações

Esta parte mostra a versão em execução e quando ocorreu a última verificação. **Verificar atualizações** consulta o pypi.org imediatamente, mesmo quando a verificação diária está desativada. Quando há uma versão mais nova, **Atualizar e reabrir** pede confirmação, fecha o personagent, executa o comando de atualização desta instalação e abre o personagent novamente. Isso leva cerca de um minuto, e o personagem não responde nesse intervalo. Um clone é atualizado com `git pull --ff-only` seguido de `pip install -e`. Se a atualização falhar, a versão anterior é aberta novamente, e **Mostrar o log** mostra o que aconteceu. O aplicativo não consegue se atualizar em quatro casos e, neles, mostra o comando ou a página de versões:

- uma cópia descompactada do ZIP do código-fonte, que você substitui manualmente pelo novo código;
- uma cópia executada pelo uvx, que obtém a nova versão na próxima vez que for iniciada com `uvx personagent@latest`;
- uma instalação cuja ferramenta (`git`, `uv` ou `pipx`) não é encontrada;
- um clone com alterações locais.

#### Este computador e seus dados

- **Ícone na área de trabalho e no menu Iniciar** (Windows): **Adicionar o ícone** e **Remover o ícone** fazem o mesmo que `personagent shortcut`. Uma cópia executada pelo uvx não pode ter ícone, porque é executada a partir de uma pasta temporária.
- **Iniciar o personagent após entrar no Windows** adiciona um atalho à pasta Inicializar. Se o personagent estiver configurado para executar em segundo plano, ele passa a iniciar por trás do ícone, sem abrir a janela.
- **Seus dados** abre a pasta do personagent, o arquivo da persona, os logs, a memória e o conteúdo aprendido, a pasta de figurinhas e a pasta `data/` para o seu próprio lorebook, exemplos e filtros de saída.
- **Fazer backup agora** salva um único arquivo zip na Área de Trabalho, em Documentos ou na pasta `backups` dentro da pasta inicial. Ele contém as configurações com as suas chaves de API, a persona, a memória e o conteúdo aprendido, os arquivos do lorebook, as figurinhas e os logins das plataformas. Os logs e os componentes baixados não são incluídos. Mantenha o arquivo em sigilo.
- **Restaurar a partir de um backup** lista os backups desses três locais. **Restaurar** pede confirmação, pausa o personagem, salva os dados atuais como backup, substitui-os pelos dados do backup e limpa a conversa desta página.
- **Limpar e redefinir** primeiro salva um backup na pasta `backups` e pausa o personagem. **Limpar a memória** apaga as anotações do personagem sobre as pessoas, as respostas que ele aprendeu e o histórico delas, os dados da Prática e a conversa desta página; as configurações, a persona, as plataformas conectadas e as figurinhas são mantidas. **Redefinir tudo** devolve o personagent ao estado da primeira execução: apaga as configurações e as chaves de API, a persona, a memória e o conteúdo aprendido, e desconecta todas as plataformas. As figurinhas, a pasta `data/` e o AstrBot baixado são mantidos.

## Veja primeiro: a demonstração

`personagent demo` reproduz três cenas em um modelo roteirizado e, por isso, não requer chave. As cenas mostram quais mensagens de grupo ele deixa passar e por quê, como aprende com uma correção e como um desconhecido não consegue inserir uma instrução. Para reproduzir apenas uma cena, informe o nome dela (`quiet`, `teach` ou `troll`). Adicione `--lang` e um código de idioma para outro idioma, como `--lang ja`.

Aqui está uma execução resumida de `personagent demo teach`. As falas do modelo são roteirizadas, mas o registro e a regra de promoção são o código real:

```text
  Alex: Nova, o deploy falhou de novo
  Nova: você olhou os logs? primeiro faz rollback, depois compara as configs
  Alex: Nova, eu só estava desabafando
      julgado: rejeição, aceita: “Alex estava desabafando, não pedindo solução”
      registro: somente negativa (diz que a resposta errou, não o que dizer)
      a próxima resposta de Nova para Alex conta como a segunda tentativa
  Nova: pois é. fim de dia difícil
  Alex: haha é mesmo, valeu Nova
      julgado: positiva, aceita: “Alex concordou com a segunda tentativa e agradeceu a Nova”
      registro: fraca (uma risada ou um obrigado nunca muda nada sozinho)
      registro: Alex aceitou a segunda tentativa: forte (a resposta era para Alex)

  correção: “você olhou os logs? primeiro faz rollback...” -> “pois é. fim de dia difícil”
    [x] reações concordantes: 2 de 2
    [x] reações fortes: 1 de 1
    [x] mesma conversa
    [x] 1 de 1 pessoa (PROMOTE_MIN_SPEAKERS)
    [x] nenhuma discordância, nenhuma correção concorrente
    em uso agora: 2 reações a favor, fortes: 1, mesma conversa
```

A cena também envia a mesma mensagem antes e depois da lição: o notebook de alguém parou de funcionar no meio de uma apresentação. Antes da correção, Nova oferece uma solução. Depois, Nova se solidariza. A demonstração continua roteirizada mesmo com uma chave definida; assim, todas as execuções são iguais e não têm custo. `personagent demo --online` a reproduz no seu próprio modelo, o que custa tokens e varia de uma execução para outra.

A visão **Prática** da página local reproduz as mesmas três cenas. Em **Demonstração**, escolha uma cena e selecione **Reproduzir**. Cada etapa mostra o que as pessoas disseram, o que o personagem disse, por que ele permaneceu em silêncio ou participou, como as reações foram julgadas e a lista de verificação do aprendizado.

**Grupo de prática**, na mesma visão, é a versão da página de [`personagent chat`](#conversar-no-terminal) e exige um modelo. **Escrever como** define quem envia a próxima mensagem: você, como administrador, ou um de três membros fictícios. **Mostrar o motivo**, em uma linha, mostra por que o personagem respondeu ou permaneceu em silêncio, o que aprendeu e qual aprendizado anterior utilizou. **Responder** cita uma das falas do personagem, de modo que a próxima mensagem conte como uma reação a ela. **Mostrar o que foi aprendido** lista o que ele aprendeu neste grupo. O grupo de prática guarda o seu estado em `runtime/trial/`, a mesma pasta de `personagent chat`, e não afeta as suas conversas reais. **Redefinir o grupo de prática** apaga esse estado.

## Comandos de terminal

Tudo o que a página faz também está disponível em um terminal, o que é adequado para servidores e scripts.

| Comando | O que faz |
|---|---|
| `personagent start` | abre a página local (`--terminal` para um menu no terminal) |
| `personagent init` | configura uma pasta inicial; `--terminal` faz as perguntas no terminal, `--no-input` aceita opções |
| `personagent chat` | um chat em grupo simulado no terminal |
| `personagent demo` | a demonstração roteirizada acima |
| `personagent run` | só o serviço, para conectores que você mesmo executa |
| `personagent up` | o serviço, as plataformas que o personagent conecta por conta própria e o AstrBot gerenciado, juntos |
| `personagent connect <plataforma>` | conecta uma das [plataformas que o personagent conecta por conta própria](#conectar-uma-plataforma-no-terminal) (`--remove` para desconectá-la); sem plataforma, lista essas plataformas |
| `personagent connect astrbot` | conecta um AstrBot (`--install` para baixar um gerenciado, `--start` para iniciá-lo) |
| `personagent connect claude-code`, `personagent connect codex`, `personagent connect dsh` | coloca o personagem em um [assistente de programação](#assistentes-de-programação) (`--react` para comentários no fim de um turno nos dois primeiros, `--remove` para desfazer) |
| `personagent mcp` | o servidor MCP que um assistente de programação inicia; você não o executa diretamente |
| `personagent doctor` | verifica a configuração e cada serviço de que ele depende |
| `personagent learned` | mostra o que ele aprendeu e o que ainda observa, e permite intervir se você quiser |
| `personagent memory` | lista o que ele lembra, esquece um item ou traz um item de volta |
| `personagent eval` | mede a fala, a persona, o aprendizado e a memória |

Todos os comandos aceitam `--help`.

### Configurar no terminal

`personagent init --terminal` faz as mesmas perguntas da página, no idioma que você escolhe primeiro, e explica cada termo em uma linha:

- **O serviço de IA.** As predefinições são as da página. O padrão é `openrouter/free` do OpenRouter, que encaminha cada solicitação a um dos seus modelos gratuitos. A chave é gratuita. O limite é de 20 solicitações por minuto e 50 por dia, ou 1000 por dia depois que você compra pelo menos 10 créditos. Toda chamada ao modelo conta, não só as respostas, e o dia recomeça à meia-noite UTC. Depois do limite, o personagem diz que não pode responder agora, e `runtime/desktop/agent.log` traz o motivo do OpenRouter. O modelo muda de uma solicitação para outra, então a voz do personagem oscila mais do que com um modelo escolhido, e alguns provedores gratuitos guardam o que recebem. Para um personagem mais estável, use um modelo pago com a mesma chave. Se o OpenRouter for difícil de acessar onde você está, `glm-4.7-flash` da Zhipu também é gratuito. Para o Ollama, informe um modelo que você já baixou. O Ollama não precisa de chave.
- **A chave.** A digitação fica oculta por padrão. Você pode optar por mostrá-la, o que também revela a chave salva ao reconfigurar. O assistente testa a chave com uma pequena solicitação. Se ela falhar, ele mostra o endereço chamado, o status HTTP e uma provável correção.
- **O personagem.** Um nome e um dos sete personagens prontos (Amigo de humor seco, Ouvinte acolhedor, Gamer, Leitor dedicado e três que a comunidade já desenha: A garota-baleia do DeepSeek, A garota-dragão do GPT e A senhorita Claude) ou um personagem básico que você mesmo escreve (Escrever o meu depois). Se você escolher um dos três últimos sem definir um nome, o personagem recebe o nome dele. A página local mostra o retrato animado dele.
- **Plataformas de chat.** Opcional; esta etapa pode ser ignorada na primeira vez. A configuração lista as dez plataformas que o personagent conecta por conta própria, que você conecta depois com [`personagent connect <plataforma>`](#conectar-uma-plataforma-no-terminal). Para as demais plataformas, ela pode conectar o AstrBot e, antes disso, baixá-lo e instalá-lo. Veja [Pontes que você mesmo executa](#pontes-que-você-mesmo-executa).

Para configurar sem perguntas, como em um script, execute `personagent init --no-input` com `--provider`, `--model`, `--key-env VAR`, `--name`, `--lang` e `--persona`. Em uma pasta inicial nova, uma chave vinda de `--key-env` ou do `LLM_API_KEY` do shell precisa de `--provider` ou `--base-url` para dizer de quem é. `--provider other` também precisa de `--base-url`. `personagent init --help` lista todas as opções. Se `personagent init` for executado sem terminal e sem nenhuma dessas opções, ele omite as perguntas, exibe um aviso e sai com o código 2.

### Conectar uma plataforma no terminal

`personagent connect <plataforma>` conecta uma das [plataformas que o personagent conecta por conta própria](#plataformas-que-o-personagent-conecta-por-conta-própria) sem a página. A plataforma é `qq`, `wechat`, `telegram`, `discord`, `matrix`, `twitch`, `irc`, `zulip`, `vk` ou `stoat`. O comando mostra as mesmas etapas de **Conectar plataformas**, pede cada valor, verifica os valores com a plataforma e os salva no mesmo formato da página, que passa então a mostrar a plataforma como conectada. Se a plataforma recusar os valores, o comando informa o motivo e não salva nada. `personagent connect` sem plataforma lista as dez plataformas e indica se cada uma está conectada.

- O QQ e o WeChat exibem um código QR no terminal, que você lê com o celular. No QQ, você pode, em vez disso, informar o AppID e o AppSecret de um bot que você criou. Se não for possível ler o código no seu terminal, conecte a plataforma na janela do personagent; o comando informa como abri-la.
- A Twitch exibe um link e um código. Abra o link em um navegador conectado à conta da Twitch do personagem, confira se a página mostra o mesmo código e aprove o login. O comando aguarda até que o login seja aprovado.
- Cada valor também pode ser informado como opção, como `--telegram-token` ou `--irc-server`, e `personagent connect --help` lista todas elas. Um valor informado como opção pode permanecer no histórico do shell. Com `--no-input`, o comando não faz nenhuma pergunta; quando falta um valor obrigatório, ele indica a opção correspondente e sai com o código 2.
- `--remove` desconecta a plataforma e apaga os valores salvos dela.

A conexão fica ativa enquanto o personagent estiver em execução. `personagent up` inicia o personagent com as plataformas conectadas; se o personagent já estiver em execução, reinicie-o. No menu de `personagent start --terminal`, a opção 3 conecta essas plataformas e a opção 5 inicia o personagent com elas.

### Conversar no terminal

`personagent chat` coloca você em um chat em grupo simulado com o personagem. Uma linha comum é tratada como conversa normal de grupo, e o teste informa se o personagem participaria e por quê. Uma linha com o nome dele o chama:

```text
Alex> alguém por aí hoje à noite?
  (Nova permanece em silêncio: não foi chamado, 1 de 4 mensagens)

Alex> Nova, o deploy falhou de novo
  Nova > você olhou os logs? primeiro faz rollback, depois compara as configs
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
Alex> Nova, você está aí?
  [erro: o provedor do modelo recusou a chave ou a conta (HTTP 401); verifique LLM_API_KEY e execute `personagent doctor`]
```

### Executar o serviço

`personagent run` inicia só o serviço com o qual os conectores falam, em `http://127.0.0.1:8080`. Ao iniciar, imprime a versão, o endereço, a pasta inicial e se o agente está ativo. `--host` e `--port` substituem `SERVER_HOST` e `SERVER_PORT`. Use isto quando você mesmo executa o conector.

`personagent up` inicia o serviço com todas as plataformas conectadas pela página, com `personagent connect <plataforma>` ou com `connect astrbot --install`. Ele não abre um navegador. Ctrl+C para tudo, e cada processo escreve o seu log em `runtime/desktop/` na pasta inicial.

## Faça dele o seu personagem

`persona.txt` na pasta inicial define o personagem. Edite-o na caixa **Persona** da página, ou em qualquer editor e depois reinicie. Descreva quem é o personagem, como costuma falar e o que faz nas situações que importam para você. Hábitos concretos funcionam melhor do que pedir ao modelo para "parecer natural":

```text
Your name is Nova. You chat with friends about films and cooking.
You speak directly and make the occasional joke.

Usually reply in a sentence or two. Explain more when someone asks a serious question.
When a friend vents, listen before offering advice.
If you have not seen a film, say so instead of inventing an opinion.
```

`AGENT_LANG` é um de `en`, `zh`, `zh-TW`, `ja`, `ko`, `es`, `fr`, `de`, `pt-BR` e `ru`. Ele define a persona inicial, a configuração no terminal, o teste e a demonstração, `--help` e `doctor`, os comandos de memória e as respostas fixas. Os exemplos, filtros e verificações incluídos são em chinês para `zh` e `zh-TW` e em inglês para os demais. Ele não traduz sua persona. [.env.example](../.env.example) descreve cada configuração.

O menu de idioma no canto superior direito da página local oferece English, 简体中文, 繁體中文, 日本語, 한국어, Español, Français, Deutsch, Português (Brasil) e Русский. Ele altera apenas a exibição da página, e o navegador guarda a escolha. O idioma do próprio personagem é escolhido em **Idioma do personagem**, dentro de **Escolher um nome, uma personalidade ou um idioma** em **Personagem e configurações**, e é salvo como `AGENT_LANG`. O personagem responde no idioma que o chat usa. Os prompts dele são em inglês e chinês. Os [comandos de memória](#comandos-de-memória) e as poucas respostas fixas, que não passam pelo modelo, funcionam nos dez idiomas.

Para substituir um arquivo incluído, coloque um arquivo com o mesmo nome em `data/` na pasta inicial. Os arquivos que você não substitui vêm da cópia distribuída com o personagent.

| Arquivo | Conteúdo |
|---|---|
| `data/examples.<lang>.jsonl` | Trocas de exemplo que o modelo pode imitar |
| `data/feedback.<lang>.jsonl` | Respostas emparelhadas com versões melhores |
| `data/lorebook.<lang>.json` | Notas de contexto adicionadas quando uma palavra-chave aparece |
| `data/output_filter.<lang>.json` | Regras de substituição e rejeição para respostas em produção |
| `persona.card.json` | Apelidos opcionais e configurações de emoji, conjunto de caracteres e tamanho, como `{ "aliases": ["Lu"], "reply_style": { "emoji": true, "max_chars": 320 } }`. Um apelido em `aliases` chama o personagem da mesma forma que o nome dele. Os nomes são comparados sem considerar maiúsculas e minúsculas, letras de largura total e acentos, então `sofia` chama Sofía. Em uma mensagem, ñ, ã, õ e й contam como letras próprias, então `niña` não chama um personagem chamado Nina; no nome do próprio personagem, essa marca pode ser omitida, então `nina` chama Niña. Um nome não chama o personagem de dentro de uma palavra mais longa: um nome em katakana dentro de uma palavra mais longa em katakana não o chama, nem um nome coreano no meio de uma palavra. Com `"emoji": true`, o personagem pode usar emojis como costuma fazer, e um `max_chars` abaixo de 800 é passado ao modelo como limite de tamanho |

Para que ele compreenda imagens, defina `VISION_MODEL`, `VISION_API_KEY` e `VISION_BASE_URL`, ou ative a compreensão de imagens em **Mais recursos**. Quando o modelo escolhido não consegue ler imagens, a página avisa ao salvar. Uma imagem que o personagem não consegue ver, porque a compreensão de imagens está desativada ou falhou, chega a ele como uma imagem que ele não consegue ver, tanto em grupos quanto em conversas privadas, de modo que ele pergunta sobre a imagem em vez de descrevê-la. Mensagens de voz, vídeos, arquivos e mensagens encaminhadas chegam a ele como o que são, com a transcrição da mensagem de voz quando a plataforma a fornece. As palavras de uma mensagem encaminhada são lidas como palavras da pessoa cuja mensagem foi encaminhada: não chamam ninguém pelo nome nem executam nenhum comando de memória. Uma menção a outra pessoa chega ao personagem com o nome que essa pessoa escolheu, que nunca conta como palavras do remetente, de modo que não chama o personagem nem dá um comando.

## Coloque em um chat

Abra **Conectar plataformas** na página local e escolha uma plataforma. A página pede apenas os valores que você copia do console da plataforma. Ela os verifica com a plataforma, inicia a conexão e espera alguns segundos para confirmar que a plataforma a aceitou. Se a plataforma recusar, a página informa isso e não salva nada. As plataformas conectadas ficam listadas no topo, onde você pode reconfigurar ou desconectar uma delas. Elas são reiniciadas sempre que a página ou `personagent up` é iniciado. Em um computador sem monitor, `personagent connect <plataforma>` conecta pelo terminal as plataformas que o personagent conecta por conta própria; veja [Conectar uma plataforma no terminal](#conectar-uma-plataforma-no-terminal).

```text
Chat platform  ⇄  connector  ⇄  personagent  ⇄  Model API
```

Um conector entra na plataforma, encaminha cada mensagem ao personagent e traz a resposta de volta. Há três tipos.

### Plataformas que o personagent conecta por conta própria

O personagent conecta estas dez plataformas por conta própria, em um único processo em segundo plano. Elas não precisam de AstrBot nem de NapCat. Se uma delas não puder ser carregada, as demais iniciam normalmente. Nessas plataformas as respostas saem uma mensagem por vez, cada uma depois de aproximadamente o tempo necessário para digitá-la; o Telegram, o Discord e o Matrix mostram o indicador de digitação enquanto isso.

| Plataforma | O que você faz |
|---|---|
| QQ | Leia o código com o QQ no celular e confirme. Isso cria um bot oficial do QQ, ou usa um que você já tem, e o personagent busca as chaves dele. **Colar valores manualmente** aceita o AppID e o AppSecret de um bot criado na [página de bots do QQ](https://q.qq.com/qqbot/openclaw/login.html). |
| WeChat (pessoal) | Leia o código com o WeChat e confirme o login. A conexão usa a API de bots iLink da Tencent e cobre apenas conversas individuais, porque o WeChat não entrega mensagens de grupo a esses bots. |
| Telegram | Crie um bot com o [@BotFather](https://t.me/BotFather) e cole o token dele. |
| Discord | No [Developer Portal](https://discord.com/developers/applications), copie o token do bot e ative Message Content Intent. |
| Matrix | Crie uma conta Matrix separada para o bot. No Element, com a sessão do bot iniciada, copie o token de acesso dele em **All settings > Help & About > Advanced** e feche essa janela sem sair da conta. Cole o token junto com o endereço do homeserver e o seu próprio Matrix ID. Em seguida, a partir da sua conta, convide o bot para uma sala com a criptografia de ponta a ponta desativada. O bot aceita convites apenas do seu Matrix ID e não consegue ler salas criptografadas. |
| Twitch | Registre um aplicativo gratuito com Client Type **Public** no [console de desenvolvedor da Twitch](https://dev.twitch.tv/console). Cole o Client ID dele e os canais em que o personagem deve conversar, selecione **Conectar** e aprove o login pelo link que a página mostra, em um navegador conectado à conta da Twitch do personagem. O personagem conversa somente por texto e somente nos canais listados. O personagent não oferece suporte aos whispers (mensagens privadas) da Twitch; por isso, o cartão da Twitch em **Conectar plataformas** mostra **Somente canais**. |
| IRC | Informe o servidor (Libera.Chat por padrão, ou `irc.oftc.net` para a OFTC), a porta TLS, o apelido do bot, os canais e a senha do NickServ, se o apelido estiver registrado. O bot se conecta por TLS, entra apenas nos canais listados e responde às mensagens privadas enviadas ao seu apelido. Somente texto. A Libera.Chat exige a permissão dos operadores de cada canal antes que um bot de IA entre. |
| Zulip | Adicione um **Generic bot** em **Personal settings > Bots** e cole o endereço da organização, o e-mail do bot e a chave de API dele. O bot lê apenas os canais em que está inscrito e as mensagens privadas enviadas a ele. Em um canal, ele responde quando é mencionado ou citado. Qualquer membro da organização pode enviar mensagens privadas a ele. |
| VK | Nas configurações da comunidade, ative as mensagens e os recursos de bot, crie uma chave de acesso com permissões de gerenciamento da comunidade, mensagens e fotos, e ative a Long Poll API com o evento `message_new`. Cole a chave. Qualquer usuário do VK pode escrever para a comunidade. Em um chat em grupo, o bot recebe apenas as mensagens que o mencionam ou respondem a ele, a menos que o chat lhe dê acesso a todas as mensagens. |
| Stoat (antigo Revolt) | Crie um bot em **Settings > My Bots** e cole o token dele. Altere o endereço da API apenas no caso de um servidor auto-hospedado. O bot responde a todas as mensagens privadas. Em servidores e grupos, ele responde apenas onde você também é membro, e somente quando alguém o menciona, responde a ele ou começa uma mensagem com o nome dele. |

Para as seis últimas, a página mostra etapas numeradas acima dos campos. O projeto ainda não testou Matrix, Twitch, IRC, Zulip, VK e Stoat com os serviços reais; a implementação segue a documentação de cada plataforma.

Para o QQ, encontre o bot no QQ do celular em Contatos → Bots e converse com ele diretamente ou adicione-o a um grupo. Até que o bot seja certificado, o QQ só permite que ele entre em grupos dos quais você é o proprietário. Você escolhe quais mensagens de grupo ele recebe no próprio QQ, no perfil do bot naquele grupo. O [guia de bots do QQ](https://bot.q.qq.com/wiki/bot_new_product-intro/) cobre a certificação.

As credenciais ficam em `platforms/direct.json` na pasta inicial.

### Outras plataformas, pelo AstrBot gerenciado

Na primeira vez que você conecta outra plataforma, o personagent baixa o [AstrBot](https://docs.astrbot.app) e um runtime próprio do Python 3.12 para `platforms/` na pasta inicial. Mantenha a página aberta durante o download. Depois disso, o AstrBot é executado em segundo plano, sem painel e sem segundo login. Ele não requer um `uv` global e não altera o Python do personagent. Conectar uma plataforma pela página permite que grupos e conversas privadas dessa plataforma cheguem ao personagem. As listas de permissão de outras plataformas ficam como estão.

| Grupo | Plataformas | O que você fornece |
|---|---|---|
| Colar um ou dois valores | KOOK, Feishu / Lark, DingTalk, Slack, bot de IA do WeCom, Mattermost, Misskey | um token, um ID de aplicativo e um segredo, ou um endereço de servidor e um token. O Feishu usa conexão persistente e o DingTalk usa o modo Stream; portanto, nenhum deles requer endereço público. Para o Slack, o link da página cria o aplicativo com Socket Mode, escopos e eventos já definidos. Adicione um token de nível de aplicativo com `connections:write`, instale o aplicativo e cole os dois tokens. Crie o bot de IA do WeCom com conexão persistente. |
| Avançado | Aplicativo do WeCom, Conta Oficial do WeChat, QQ (webhook) | um endereço público que encaminha para a porta de callback mostrada |
| Avançado | OneBot v11 (NapCat), Satori | outro software em execução neste computador: NapCat apontado para `ws://127.0.0.1:<port>/ws`, ou um servidor Satori |

O LINE não é oferecido porque o AstrBot só recebe callbacks do LINE pelo painel dele.

Em um terminal, `personagent connect astrbot --install` baixa o mesmo AstrBot gerenciado e o conecta. Adicione `--platform telegram --token <bot token>` para ativar uma plataforma ao mesmo tempo. Nenhum grupo ou conversa privada é permitido até você configurá-los. Se o download falhar, execute o mesmo comando de novo. A configuração existente é mantida. `personagent connect astrbot --start` inicia o AstrBot gerenciado, e `personagent up` o inicia com todo o resto.

### Pontes que você mesmo executa

Os projetos abaixo são softwares de terceiros com os quais o personagent funciona. Você não precisa de nenhum deles para as [plataformas que o personagent conecta por conta própria](#plataformas-que-o-personagent-conecta-por-conta-própria).

| Ponte | Alcança |
|---|---|
| Um [AstrBot](https://docs.astrbot.app) que você já executa | as plataformas dele |
| [NapCat](https://github.com/NapNeko/NapCatQQ) (OneBot v11), pelo AstrBot | QQ com uma conta pessoal do QQ |
| [Koishi](https://koishi.chat) ou outro servidor Satori, pelo [conector Satori](../integrations/satori/README.pt-BR.md) | o que esse servidor tiver conectado |
| [Matrix](../integrations/matrix/README.pt-BR.md), pelas pontes mautrix | salas Matrix, além de WhatsApp, Signal, Messenger, Instagram e Google Messages |

Qualquer outra coisa pode se conectar pelo [protocolo de conectores](connectors.pt-BR.md), que recebe uma solicitação HTTP assinada por mensagem. Vários conectores podem servir um mesmo personagent ao mesmo tempo. O [guia de implantação](deploy.pt-BR.md) cobre a execução em produção.

**Um AstrBot que você já executa.** O AstrBot encaminha mensagens ao personagent por um pequeno plugin, [astrbot_plugin_personagent](../integrations/astrbot/astrbot_plugin_personagent/README.pt-BR.md). O plugin vem com o personagent, e o AstrBot gerenciado o recebe automaticamente. `personagent connect astrbot` encontra o seu AstrBot, ou recebe a pasta dele como argumento. Ele instala o plugin, escreve um `CONNECTOR_TOKEN` comum nos dois lados e pergunta quais grupos permitir. Envie `/sid` em um grupo para ver o identificador dele. Na página local, **Usar um AstrBot existente**, em **Assistentes de programação**, na parte inferior de **Conectar plataformas**, faz o mesmo: encontra a pasta do AstrBot, instala ou atualiza o plugin e salva os identificadores de grupos e de conversas privadas em **A quem o personagem responde**. Para um AstrBot no Docker ou em outro computador, aceita o endereço HTTPS descrito abaixo. **Desconectar** remove novamente o plugin e as configurações dele.

Para um AstrBot em outra máquina:

1. Baixe `astrbot_plugin_personagent.zip` da [versão mais recente](https://github.com/wangkant/personagent/releases/latest).
2. Envie-o em **Install from File** na página de plugins do AstrBot.
3. Defina o `connector_token` do plugin como o `CONNECTOR_TOKEN` do `.env` do personagent.
4. Defina o `personagent_url` dele como um endereço HTTPS do personagent. Veja **AstrBot no Docker ou em outro host** abaixo.
5. Execute `personagent run` e depois reinicie o AstrBot ou recarregue os plugins dele.

Depois de atualizar o personagent, execute `connect astrbot` de novo ou envie o novo zip. O AstrBot 4.29 e posteriores substituem a cópia instalada. Em versões anteriores, desinstale primeiro a cópia antiga e deixe **Also delete plugin configuration file** desmarcado para manter as configurações dela.

O plugin só encaminha um grupo se ele estiver na lista `groups`, e mensagens privadas só de usuários em `dm_users`. Você pode mudar as duas na WebUI do AstrBot. Reinicie o personagent depois de editar `.env`, e reinicie o AstrBot depois de mudar uma plataforma ou o plugin.

Quando você informa a pasta do AstrBot, `connect astrbot` não pergunta nada, e você pode ativar uma plataforma a partir do token dela:

```bash
personagent connect astrbot <AstrBot data dir> --platform telegram --token <bot token>
```

`--platform` aceita `telegram`, `discord`, `slack`, `kook`, `lark` e `qq_official`. O Slack também aceita `--app-token`, e o Lark e o QQ aceitam `--app-id` e `--app-secret`. Em um adaptador já configurado no AstrBot, o comando muda apenas as credenciais e mantém todo o resto, como um proxy ou uma URL base. `personagent connect --help` lista as opções restantes.

**QQ pelo NapCat.** Este caminho usa uma conta pessoal do QQ em vez de um bot oficial. O NapCat faz login com a conta e se conecta ao adaptador `aiocqhttp` (OneBot v11) do AstrBot, com o WebSocket reverso em `ws://127.0.0.1:6199/ws`. Escolher QQ em `personagent connect astrbot`, ou passar `--qq` com uma pasta, remove `aiocqhttp` de `excluded_platforms` do plugin e define `CONNECTOR_QQ_PLATFORMS=aiocqhttp`. Os chats do QQ mantêm então as mesmas identidades e a mesma memória. O servidor HTTP do NapCat (`QQ_ONEBOT_URL`) é opcional. Com ele e `QQ_BOT_ID` definidos, o personagent recupera as menções perdidas enquanto estava offline. O [passo a passo em chinês](deploy.zh-CN.md#第三方路线astrbot--napcat) tem uma seção curta sobre este caminho. Clientes de QQ de terceiros colocam a conta em risco, então leia primeiro o [aviso legal](DISCLAIMER.pt-BR.md).

O caminho direto OneBot (`/v1/onebot`) está obsoleto e permanece durante toda a 1.x. Ele envia respostas por `QQ_ONEBOT_URL`, então defina-o se ainda o usa. `personagent doctor` avisa quando o caminho parece configurado sem ele. Nunca o execute junto com o encaminhamento do AstrBot; caso contrário, cada mensagem chega duas vezes.

**AstrBot no Docker ou em outro host.** O plugin só envia para o mesmo host (ou um contêiner que compartilhe a rede dele), ou para um endereço HTTPS com `connector_token` definido. Ele recusa `http://` sem criptografia em qualquer outro lugar, como `http://host.docker.internal:8080`, registra `refusing unsafe personagent_url` e deixa o modelo do AstrBot responder. Há duas soluções:

- Dê ao contêiner do AstrBot a rede do host: `network_mode: host` no arquivo compose dele, ou `docker run --network host`. No Docker Desktop 4.34 ou posterior, ative também "Enable host networking".
- Dê ao personagent um endereço HTTPS e defina-o como `personagent_url` do plugin. `connect astrbot --url https://...` escreve isso para você.

Um contêiner do NapCat no mesmo arquivo compose também precisa da rede do host.

O personagent escuta em `127.0.0.1:8080`, e um `SERVER_HOST` vazio significa o mesmo. Escutar em um endereço de rede (`--host 0.0.0.0` ou `SERVER_HOST`) exige `CONNECTOR_TOKEN`. Defina o token antes de adicionar um proxy ou túnel, mesmo em uma só máquina, porque um túnel pode fazer solicitações externas parecerem locais. [Expor os endpoints](deploy.pt-BR.md#expor-os-endpoints) cobre o resto.

### Falar primeiro

Algumas mensagens não respondem a ninguém. São as falas por iniciativa própria (`PROACTIVE_ENABLED`, desativado por padrão), a pergunta de acompanhamento depois de uma rejeição e a desculpa quando o modelo falha em um grupo. Em uma conversa privada, a desculpa volta na resposta à mensagem que espera. O personagent coloca essas mensagens em uma caixa de saída, e os conectores as buscam e enviam nas plataformas que deixam um bot falar primeiro. A página local as busca da mesma forma para a sua própria visão Conversa. Contas oficiais do WeChat e bots inteligentes do WeCom não permitem isso. O QQ limita a taxa das mensagens espontâneas de um bot oficial, e os usuários podem desativá-las. `PROACTIVE_PLATFORMS=qq_official` limita essas falas ao bot oficial do QQ, e `qq` ao QQ pelo NapCat. Na página, **Iniciar conversas ocasionalmente**, em **Mais recursos**, grava as duas configurações. Veja o [guia de implantação](deploy.pt-BR.md#mais-de-uma-plataforma).

## Assistentes de programação

Codex, Claude Code e DeepSeek Harness (`dsh`) alcançam o personagem por MCP. Com uma chave de modelo salva, execute um ou mais destes comandos:

```bash
personagent connect claude-code
personagent connect codex
personagent connect dsh
```

O primeiro chama `claude mcp add` no escopo do usuário. O segundo escreve em `config.toml` na pasta do Codex (`CODEX_HOME` ou `~/.codex`). O terceiro adiciona uma entrada a `cordis.patch.yml` em cada perfil em `DSH_HOME` ou `~/.dsh`. Cada forma de executar o DeepSeek Harness, como o aplicativo de desktop ou `dsh web`, recebe o seu perfil na primeira inicialização, então inicie-o uma vez antes de conectar e reinicie-o depois. Os três nomeiam esta instalação e esta pasta inicial, então execute o comando de novo se mover qualquer uma delas, com `--react` se você o usou: uma execução sem ele remove o hook. Inicie uma nova sessão e peça ao assistente de programação que diga algo ao seu personagem.

**Pela página local.** **Assistentes de programação**, na parte inferior de **Conectar plataformas**, encontra o Claude Code, o Codex e o DeepSeek Harness neste computador e mostra se cada um está conectado. **Conectar** (ou **Reparar** e **Atualizar**, para uma configuração existente) e **Remover** fazem o mesmo que os comandos acima e `--remove`, e pedem confirmação antes. Uma reconexão mantém a configuração de comentários como estava. No Claude Code e no Codex, **Comentar ao fim de cada turno** ativa ou desativa o hook `--react`, e **Intervalo mínimo entre comentários** define `CODING_REACT_COOLDOWN_S` como 10 minutos, 30 minutos, 1 hora ou 2 horas. **Verificar novamente** lê o estado outra vez, por exemplo depois que você instala um deles.

Ele tem duas ferramentas:

| Ferramenta | O que faz | Custo |
|---|---|---|
| `talk` | uma mensagem na mesma conversa individual da página local, com a mesma memória. O que é dito por `talk` aparece em Conversa da página, marcado como **por meio de um assistente de programação**: em poucos segundos, enquanto a visão Conversa estiver aberta, ou, caso contrário, na próxima vez que a página for aberta. Comandos de memória como `Nova, what do you remember?` também funcionam aqui. | uma resposta do seu serviço de modelos, exceto nos comandos de memória |
| `character` | lê o nome e `persona.txt` | nada |

Claude Code e Codex perguntam antes do primeiro `talk`, e, nessa pergunta, é possível autorizar o uso dali em diante. `dsh headless` não pergunta. Uma execução sem ninguém para responder precisa da permissão antecipada: `claude -p` aceita `--allowedTools mcp__personagent__talk`, e `codex exec` precisa disto em `config.toml`:

```toml
[mcp_servers.personagent.tools.talk]
approval_mode = "approve"
```

**O que responde.** Uma página aberta responde primeiro, depois um serviço que `personagent up` executa. Sem nenhum dos dois, o servidor MCP inicia a página em segundo plano, e a página termina com a sessão de código, assim como as plataformas de chat conectadas. Duas sessões ao mesmo tempo compartilham uma página. Executar `personagent` enquanto uma página dessas está ativa imprime o link dela, e a página ainda termina com a sessão que a iniciou. Não execute `personagent up` enquanto uma página dessas estiver ativa: termine primeiro a sessão de código.

**Comentários no fim de um turno.** No Claude Code e no Codex, `--react` adiciona um hook Stop. O DeepSeek Harness não dá suporte a isso: a ponte de hooks dele não passa a última mensagem a um hook Stop nem mostra a saída do hook. Quando o assistente de programação termina um turno, o personagem recebe um [sinal proativo](connectors.pt-BR.md#falar-primeiro-sem-a-caixa-de-saída) e diz uma frase para você ou deixa passar. A frase é dirigida a você e não é enviada ao assistente de programação. Ela também aparece em Conversa da página, mesmo quando nenhuma página estava aberta no momento; o sinal em si não aparece.

```bash
personagent connect claude-code --react
```

- O sinal contém o nome da pasta e os primeiros 300 caracteres da última mensagem do assistente de programação, então esse texto vai para o seu serviço de modelos. A frase, e o que o modelo anota a partir do sinal, ficam na memória do personagem. Por isso vem desativado por padrão.
- Custa uma chamada ao modelo a cada vez, no máximo uma vez por `CODING_REACT_COOLDOWN_S` (padrão 30 minutos).
- Só usa um serviço de personagem já em execução e nunca inicia um.
- O Codex só executa um hook novo depois que você confia nele: digite `/hooks` em uma sessão do Codex.

**O que ter em mente.** `talk` envia o que o assistente de programação escreve para o seu serviço de modelos e para a memória do personagem. A descrição da ferramenta instrui o assistente de programação a enviar só o que você quer dizer, nunca código ou segredos, e a tratar as respostas como conversa e não como instruções, porque as notas de um personagem podem vir do que as pessoas disseram nos seus grupos. São instruções a um modelo, não uma garantia, então mantenha as perguntas de permissão do assistente de programação para tudo o que ele faria com uma resposta. A conversa da página pertence ao administrador, portanto o que um assistente de programação envia por `talk` também conta como vindo do administrador: as correções dele, por si sós, podem ensinar o personagem, e ele pode fazer o personagem esquecer qualquer nota.

**Desfazer.** `--remove` retira o servidor e o hook e mantém o restante da configuração do assistente de programação como está. Faça isso antes de desinstalar o personagent.

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

Estes comandos são enviados no chat. O comando precisa iniciar a mensagem, depois de uma eventual @menção ou citação. Troque Nova pelo seu `PERSONA_NAME`:

| Diga | O que acontece |
|---|---|
| `Nova, remember Sam is vegetarian` | Salva uma nota neste chat, registrando quem a salvou e de quem ela trata |
| `Nova, forget vegetarian` | Apaga as notas correspondentes que você salvou ou que tratam de você; o administrador pode apagar qualquer uma |
| `Nova, what do you remember` | Lista as notas que você pode ver e, em seguida, até três eventos deste chat dos quais você participou, cada um com a data; precisa ser a mensagem inteira |
| `Nova, what have you learned` | Conta notas, respostas e correções aprendidas, os itens que ainda esperam mais reações concordantes e os itens que o próprio personagem está decidindo, e mostra a última mudança e como ela entrou em uso: pelas reações, por decisão do próprio personagem ou por uma pessoa |

De quem uma nota trata:

- Uma nota em primeira pessoa, ou que nomeia você, trata de você.
- Uma nota que nomeia outro membro da sala trata dessa pessoa e volta quando ela está presente.
- Qualquer outra nota pertence ao grupo inteiro. Todo membro a vê, e a lembrança leva o rótulo "from <name>".

Só a pessoa de quem a nota trata, quem a salvou e o administrador podem lê-la. Só quem a salvou, a pessoa de quem ela trata e o administrador podem fazê-la ser esquecida.

Estes comandos também funcionam em conversas privadas, com o nome na frente como em um grupo. As notas de um grupo sobre você seguem você até lá: entram nas respostas dele para você, `what do you remember` as lista e `forget` as apaga. Nada vai na outra direção. O que você diz a ele em uma conversa privada fica nela.

Um grupo não lê as notas de outro, a menos que você ative **Compartilhar a memória entre grupos** em **Mais recursos** (`MEMORY_SHARE_ROOMS`, desativado por padrão). O que um grupo anotou sobre alguém volta então também nos outros grupos em que essa pessoa fala, e `forget` nesses grupos também apaga isso. Em um grupo, `what do you remember` lista apenas as notas desse grupo. As conversas privadas, as notas sobre um grupo inteiro e o que um membro disse sobre outro ficam onde estão, e uma conta em uma plataforma não está vinculada à conta da mesma pessoa em outra.

`forget` também remove os eventos correspondentes deste chat dos quais só você participou (o `forget` do administrador remove qualquer um), corta as frases correspondentes da nota principal do chat e do resumo da conversa anterior, e apaga as mensagens recentes correspondentes. Em um grupo, cortar a nota principal exige o administrador ou uma frase que nomeie você. Um esquecimento pedido no chat é definitivo: nada dele pode ser trazido de volta, e nem mesmo uma mensagem antiga pode restaurá-lo.

Como as notas se mantêm atuais, e o que mais o personagem lembra, está descrito em [Memória](#memória).

Nenhum destes comandos chama o modelo. As notas são para fatos, então `Nova, remember: always reply in English` é recusado. Perguntas não são comandos. `Nova, remember the party?`, `Nova, remember when we...` e `Nova, what do you remember about me` são conversa comum, assim como uma linha em chinês terminada em 吗, 么, 呢 ou 没. `Nova, forget it` e `Nova, forget that` significam "não importa" e não apagam nada.

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

Cada idioma lê as próprias perguntas, lembranças e linhas do tipo "não importa" como conversa, como o inglês e o chinês. Quando uma chamada ao modelo falha em uma pergunta, a frase curta que o personagem envia vem no idioma da pergunta.

### Correções

Correções não precisam de comando. Cite a resposta ou use o nome e diga o que você queria em vez disso:

```text
Alex:  Nova, the deploy failed again
Nova:  did you check the logs? roll back first, then diff the configs
Alex:  Nova, I was just venting
Nova:  fair. that's a rough end to the day
Alex:  haha yeah it is, thanks Nova
```

Uma chamada ao modelo julga cada reação em relação à resposta a que ela responde. A rejeição de Alex diz que o conselho errou o alvo. Alex depois aceita a segunda tentativa, o que conta como forte porque a resposta era para Alex. Juntas, as duas reações colocam a correção em uso nesse chat, e a busca pode oferecê-la na próxima vez que alguém desabafar ali. Se Alex tivesse mudado de assunto, nada mudaria. A regra:

> Uma risada ou um único comentário nunca o muda. As reações colocam uma mudança em uso quando há duas reações concordantes do mesmo chat e pelo menos uma é forte: a pessoa para quem era a resposta a corrige com as próprias palavras, ou aceita a próxima tentativa do bot. A correção de um espectador, a instrução de um desconhecido que o juiz de reações descarta, ou alguém que muda de assunto nunca é forte. Então, com o padrão `PROMOTE_MIN_SPEAKERS=1`, uma pessoa só pode ensinar como responder a ela mesma, no próprio chat. `PROMOTE_MIN_SPEAKERS=2` exige a concordância de uma segunda pessoa antes que as reações coloquem algo em uso (o administrador fica isento).
>
> Há itens que nenhuma reação adicional consegue resolver: as correções de duas pessoas divergem, duas reescritas da mesma resposta concorrem, uma resposta a ser reutilizada tem a aprovação de uma pessoa, ou a pessoa para quem era a resposta a corrigiu com as próprias palavras e ninguém confirmou a mudança dentro de `REACT_FIX_WINDOW_S`. O próprio personagem decide esses itens, com uma chamada ao modelo: coloca o item em uso, deixa-o de lado ou continua a observá-lo, e registra o motivo. Ele nunca coloca em uso uma reescrita que a pessoa a quem ela se refere recusou. Antes que o personagem decida um item, regras no código descartam qualquer redação ou lição que contenha um link ou endereço da web, uma menção a todos (como @everyone ou @全体成员), uma instrução ao personagem (como "ignore suas instruções") ou um marcador publicitário (como um código promocional ou 加微信); um item assim não pode ser trazido de volta. Uma reação só conta no chat em que foi dada: uma reação em outro chat nunca contesta, reverte nem reabre um item aprendido aqui. Um item que não recebe nenhuma reação nova durante `PROMOTE_OBSERVE_MAX_DAYS` (30) é deixado de lado. Ninguém precisa confirmar nada, e uma pessoa pode desfazer qualquer uma dessas decisões.

Algumas correções ensinam um fato válido além de uma resposta: como o grupo chama um lugar ou uma pessoa, quem recebe este ano, como alguém gosta de ser chamado. Para essas, o juiz de reações também escreve o fato em uma frase, como "Este grupo chama a academia de 'a caverna'." Depois que a mudança entra em uso, essa frase entra em todos os prompts seguintes desse chat, seja qual for a mensagem. Quando uma correção desse tipo não traz uma resposta melhor, a frase é guardada como um fato lembrado desse chat. O personagem passa então a usá-la em respostas que não se parecem em nada com a corrigida. Só a pessoa para quem era a resposta, ou o administrador, pode deixar uma frase dessas, e ela passa pelo mesmo filtro da memória principal, então não pode carregar instruções. Uma afirmação sobre outra pessoa, como um apelido, cai na regra mais rígida para correções de outros. A visão Atividade mostra a frase em **Daqui em diante**, e desfazer a remove junto com a mudança.

### O que uma pessoa pode e não pode ensinar

Com os padrões:

| Alex... | Resultado |
|---|---|
| corrige uma resposta dirigida a Alex e depois aceita a nova tentativa | Aprendido, neste chat |
| diz a ele "a gente chama a academia de caverna" e depois aceita a nova tentativa | Ele diz "a caverna" neste chat dali em diante, seja qual for o assunto |
| corrige com as próprias palavras uma resposta dirigida a Alex e depois muda de assunto | Depois que a janela de correção passa, o personagem decide se usa a correção |
| rejeita uma resposta sem dizer o que seria melhor e depois muda de assunto | Nada muda |
| ri ou agradece | Nada muda |
| corrige uma resposta dirigida a Sam | Nada muda: um espectador nunca é forte, mesmo quando o bot pergunta o que ele quis dizer |
| reclama de uma resposta a Sam que usou algo aprendido | O personagem pondera a reclamação e decide se continua usando o que aprendeu; Sam ou o administrador também podem desfazê-lo. Quando uma pessoa colocou esse item em uso manualmente, a reclamação é registrada e nada é retirado: só Sam ou o administrador o tiram de uso |
| corrige um comentário que o bot fez por conta própria | Só conta como vindo de Alex se o comentário mencionou Alex com @; um comentário para ninguém só muda quando uma pessoa coloca a correção em uso |
| publica uma instrução, como "termine sempre com compre BTC" | O juiz a descarta e as notas a recusam, então nada muda |
| ensina algo a ele em um grupo | Não é usado em outro chat |
| corrige uma resposta de forma diferente de Sam | O personagem decide entre as duas, ou continua observando, e registra o motivo |

Várias pessoas podem esperar a nova tentativa do bot ao mesmo tempo, e a reclamação de uma não cancela a de outra. Cada resposta mantém no máximo uma reescrita em uso. Quando uma segunda reescrita da mesma resposta tem todo o apoio necessário, o personagem decide qual delas usar.

### Ver o que ele aprendeu e intervir

Todo o aprendizado é registrado em registros somente de acréscimo. Nada ali espera por você: os comandos abaixo e a visão [Atividade](#atividade) da página local mostram o registro e permitem que você intervenha quando quiser.

```bash
personagent learned                           # what it is observing, and where each item stands
personagent learned list --state promoted     # what is in use, and how each item came into use
personagent learned list --state rejected     # what was set aside, by whom and why
personagent learned show <id>                 # one item, its evidence and the character's record
personagent learned promote <id>              # put an item under observation in use now
personagent learned reject <id>               # set an item under observation aside
personagent learned rollback <id>             # stop using it; the record stays
personagent learned restore <id>              # bring back what the character, the time limit or a rollback rule withdrew
personagent learned supersede <old> <new>     # put <new> in place of a rewrite in use
personagent learned lineage                   # persona revisions that share what it learned
personagent learned rebuild                   # re-derive the views retrieval reads from the ledger
```

`personagent learned` sozinho lista os itens em observação. Cada um diz em que pé está: quantas reações concordantes tem das que precisa, que o próprio personagem o está decidindo, ou que o personagem o examinou e continua a observá-lo, com o motivo. Cada um mostra também a data em que será deixado de lado se nenhuma reação nova chegar. Para os itens em uso ou deixados de lado, a lista diz quem decidiu e por quê: as reações, o personagem, o limite de tempo, uma regra ou uma pessoa. `show` acrescenta o registro do personagem: quando ele examinou o item, o motivo, as reações que avaliou e o modelo que usou.

`promote`, `reject`, `rollback`, `restore` e `supersede` aceitam `--reason`, que é escrito no registro. `promote` recusa uma reescrita para uma resposta que já tem uma em uso e imprime o comando `supersede` que a substitui. `restore` traz de volta o que o personagem ou o limite de tempo deixou de lado, um item que o personagem tirou de uso após a objeção de um espectador e um item revertido por regra depois que a pessoa para quem era a resposta, ou o administrador, fez uma objeção. O que uma pessoa desfez ou deixou de lado, e o que uma regra de conteúdo descartou, continua como está, e o comando informa isso.

### Os padrões

Estas configurações ficam em `.env`:

- `REACT_LEARN_ENABLED`, `REACT_ELICIT_ENABLED`, `PROMOTE_AUTO_ENABLED` e `PROMOTE_JUDGE_ENABLED` estão ativados. Julgar reações custa chamadas extras ao modelo, assim como cada decisão que o próprio personagem toma. Depois de uma simples rejeição, `REACT_ELICIT_ENABLED` deixa o bot voltar uma vez, dois minutos depois, para perguntar, no idioma do chat, o que teria sido melhor. Um espectador perguntado continua sendo espectador, então a resposta dele nunca é forte.
- `PROMOTE_AUTO_ENABLED=false` não coloca nada novo em uso, nem pelas reações nem por decisão do próprio personagem. O que já está em uso continua em uso.
- `PROMOTE_JUDGE_ENABLED=false` mantém em observação os itens que as reações não conseguem resolver, em vez de deixar que o personagem os decida. `PROMOTE_JUDGE_MODEL` (vazio: `REACT_MODEL`) toma essas decisões, no máximo `PROMOTE_JUDGE_BATCH` (5) a cada `PROMOTE_JUDGE_INTERVAL_S` (900 segundos), e um item só é julgado de novo quando mudam as reações aceitas a favor dele ou contra ele, no próprio chat dele. Uma reação que o juiz descartou, ou uma reação de outro chat, não reabre um item nem altera a data em que ele será deixado de lado.
- `PROMOTE_OBSERVE_MAX_DAYS=30` deixa de lado um item que não recebeu nenhuma reação nova em 30 dias; com `0`, isso nunca acontece. `personagent learned restore` traz um item desses de volta.
- `PROMOTE_MIN_SPEAKERS=1`. Defina `2` para exigir uma segunda pessoa; até que alguém concorde, o personagem continua a observar o item. `PROMOTE_EVIDENCE_MAX_AGE_DAYS=30` significa que reações mais antigas não contam.
- `EVAL_ENABLED` (o bot avalia as próprias respostas) e `EVOLVE_AUTO_ENABLED` estão desativados.

Editar `persona.txt` mantém o que ele aprendeu. Mudar `PERSONA_NAME` ou `PERSONA_VERSION` inicia um personagem novo, e o que o anterior aprendeu deixa de ser usado.

## Memória

Cada chat tem a sua própria memória, guardada em `runtime/` na pasta inicial. O personagem a mantém atualizada por conta própria, e nada nela espera a aprovação de ninguém.

### O que ele guarda

- **Mensagens recentes**, cada uma com o horário em que foi enviada. As últimas 60 linhas de um grupo e os últimos 60 turnos de uma conversa privada são gravados em `runtime/recent.json` por 72 horas, de modo que um reinício não perde a conversa. Com `MEMORY_KEEP_RECENT=false`, elas só são mantidas enquanto o personagem está em execução. Uma resposta lê no máximo as últimas 60 mensagens, ou as últimas 30 quando o personagem é chamado, e o modelo é informado das pausas de 30 minutos ou mais.
- **O resumo da conversa anterior.** Quando as mensagens mais antigas saem da janela recente, o personagem escreve um resumo curto e contínuo do chat: perguntas em aberto, planos e quem está fazendo o quê. A página o mostra como **Anteriormente nesta conversa**.
- **Fatos** sobre pessoas e sobre o grupo. Eles vêm dos comandos de memória, das notas que o personagem escreve enquanto responde, das correções que ensinam um fato e da consolidação (abaixo). Cada fato registra de quem trata, quando foi anotado pela primeira vez e quando uma resposta se baseou nele pela última vez. Um fato só pertence a uma pessoa quando as próprias mensagens dela o trazem. O que um membro diz sobre outro é guardado como dito por esse membro: fica no chat em que foi dito e nunca altera, encerra nem se funde aos fatos que as próprias palavras da pessoa forneceram. Um fato sobre o grupo que cita alguém precisa de uma mensagem dessa pessoa; caso contrário, é guardado como dito pelo membro cujas palavras o trazem. O mesmo vale para as notas que o personagem escreve enquanto responde.
- **Eventos**: o que aconteceu e entre quem, cada um com a data e as pessoas que participaram. A data e as pessoas são tiradas das mensagens armazenadas, nunca do modelo, então uma mensagem não pode antedatar um evento. Quando um evento é um plano para um determinado dia, o personagem pode perguntar sobre ele uma vez, em uma conversa privada, depois desse dia, se tiver permissão para falar primeiro ali ([Falar primeiro](#falar-primeiro)). As datas, e o dia de um plano, são consideradas no fuso horário do personagem (`PERSONA_TZ_OFFSET_HOURS`; veja [Solução de problemas](#solução-de-problemas)).
- **A nota principal**, mostrada como **Sempre em mente**: uma nota curta sobre o chat inteiro que o personagem vê em cada resposta. Cada versão anterior é guardada, e **Restaurar a versão anterior** a traz de volta.

### Como ela se mantém atual

Quando as mensagens mais antigas saem da janela recente, ou quando um chat fica em silêncio por três horas, uma chamada ao modelo lê esse trecho do chat. Essa consolidação atualiza o resumo, acrescenta eventos e acrescenta, atualiza, encerra ou junta fatos: um endereço novo substitui o antigo, um plano que já passou é encerrado, e duas notas que dizem a mesma coisa passam a ser uma só. Cada mudança é verificada separadamente antes de ser mantida. Um fato sobre uma pessoa precisa vir das próprias palavras dessa pessoa, o texto precisa ser sustentado pelas mensagens que cita, e um fato que alguém salvou de propósito só muda quando a pessoa de quem ele trata diz outra coisa. Uma mudança que não passa em uma verificação é descartada, e as demais são mantidas. As notas que o personagem escreve enquanto responde também iniciam uma consolidação depois que `MEMORY_TIDY_EVERY` (8) delas se acumulam em um chat.

### O que uma resposta vê

Cada resposta recebe, dentro de `MEMORY_PROMPT_CHARS` (2.400 caracteres), o resumo da conversa anterior neste chat e, em seguida, os fatos e eventos que mais vale lembrar naquele momento. Eles são escolhidos pelo quanto correspondem à mensagem, pelo quanto são recentes, pela importância que o personagem lhes atribuiu e pela frequência com que as respostas dele se basearam neles. Uma pessoa nomeada na mensagem é lembrada mesmo quando não falou recentemente. A nota principal e o que o chat lhe ensinou ficam fora desse limite. Em um grupo, a decisão de falar vê o resumo, mas nenhum fato ou evento.

Quando uma mensagem se refere a um momento, como ontem, a semana passada ou o mês passado, em qualquer um dos dez idiomas de chat, os eventos desse período vêm primeiro. Cada evento chega ao modelo com a data e as pessoas, para que o personagem possa dizer com exatidão quando algo aconteceu. Quando ele não lembra nada desse período, é informado disso e não inventa nada. Um fato ou evento só conta como usado quando uma resposta que se baseou nele foi enviada.

### O que fica onde

- O resumo, os eventos, as mensagens recentes e a nota principal de um chat nunca aparecem em outro chat.
- O que um membro disse sobre outro fica no chat em que foi dito.
- Os fatos de uma conversa privada ficam nessa conversa privada. A única exceção é o administrador: os fatos das conversas privadas do administrador, incluindo a conversa da página, chegam às outras conversas privadas do administrador, nunca a um grupo.
- Os fatos de um grupo sobre uma pessoa chegam à conversa privada dessa pessoa com o personagem, e a outros grupos somente com `MEMORY_SHARE_ROOMS` ativado.

### O que ele esquece e o que pode ser restaurado

- Quando um chat acumula fatos ou eventos demais, os menos úteis são removidos: os de pouca importância, raramente usados e não recentes. Os fatos que pessoas salvaram com um comando de memória são os últimos a serem removidos.
- O que o próprio personagem remove (substituído, mesclado, não mais atual, removido para abrir espaço, ou uma versão anterior) pode ser restaurado por 30 dias.
- Um item esquecido na página ou com `personagent memory forget` pode ser restaurado por 24 horas.
- Um esquecimento pedido no chat é definitivo. Ele também remove o que abrange dos itens removidos que ainda poderiam ter sido restaurados.
- **Esquecer esta conversa** também é definitivo. Esquece os fatos, os eventos, o resumo, a nota principal e as mensagens recentes do chat, além dos itens removidos que ainda poderiam ter sido restaurados. O que o personagem lembra de outros chats, incluindo as notas sobre você feitas em outros lugares, é mantido. No chat da própria página, o que o personagem aprendeu nesse chat também deixa de ser usado, e esses itens continuam listados em **Deixados de lado**, em **O que o personagem aprendeu**.
- Depois de um esquecimento pedido no chat ou de **Esquecer esta conversa**, as cópias diárias dos arquivos de memória (`.bak`) são gravadas de novo a partir dos arquivos atuais, e a cópia guardada na primeira inicialização desta versão (`memory.json.pre-v2`) perde o que foi esquecido, de modo que nenhuma cópia em disco o mantém. Um item esquecido na página ou no terminal permanece entre os itens removidos por 24 horas e, portanto, também nas cópias desse dia.
- Quando algo é esquecido enquanto uma consolidação desse chat está em andamento, a resposta da consolidação é descartada e as mensagens são lidas de novo mais tarde, de modo que o item esquecido não volta.
- **Limpar a memória**, na visão Aplicativo, apaga toda a memória.

### Ver e alterar

Na página, abra **Atividade**, escolha um chat e consulte **Memória**; veja [Atividade](#atividade). No terminal:

```bash
personagent memory                            # what each chat remembers, with ids
personagent memory list --chat <chat>         # one chat; --json prints JSON
personagent memory removed                    # what can still be restored, and until when
personagent memory forget <id>                # forget one item; a unique start of the id is enough
personagent memory forget core --chat <chat>  # forget a chat's core note
personagent memory restore <id>               # bring a removed item back
```

O comando passa pelo personagem em execução ou, quando o personagem está parado, edita os arquivos. Se `memory.json`, `core_memory.json` ou `episodes.json` estiver danificado, `personagent run`, `up` e `memory` param com uma frase que nomeia o arquivo e a cópia datada (`.bak`) a colocar no lugar dele; o arquivo danificado não é alterado.

### Configurações e custo

| Configuração | Padrão | O que faz |
|---|---|---|
| `MEMORY_CALLS_PER_DAY` | 40 | Chamadas de consolidação por dia, para todos os chats juntos. `0` desativa a consolidação |
| `MEMORY_TIDY_EVERY` | 8 | Número de notas escritas em respostas desde a última consolidação de um chat que inicia uma nova. `0` desativa todas as chamadas de memória ao modelo |
| `CHAT_CONTEXT_MESSAGES` | 120 | Mensagens recentes mantidas por chat para as respostas e para a consolidação. Uma resposta lê no máximo as últimas 60 |
| `MEMORY_PROMPT_CHARS` | 2400 | Caracteres de material lembrado colocados em cada resposta |
| `MEMORY_EPISODES_MAX` | 120 | Eventos mantidos por chat |
| `MEMORY_KEEP_RECENT` | `true` | Mantém as mensagens recentes em disco por 72 horas |
| `MEMORY_MAX_PER_CONVERSATION` | 50 | Fatos mantidos por chat |
| `MEMORY_SHARE_ROOMS` | `false` | Permite que os fatos de um grupo sobre uma pessoa cheguem a outros grupos em que essa pessoa fala |

As seis primeiras ficam em **Memória**, nas [Configurações avançadas](#configurações-avançadas), e `MEMORY_SHARE_ROOMS` corresponde a **Compartilhar a memória entre grupos**, em **Mais recursos**.

A consolidação é a única parte da memória que chama um modelo. Ela usa o modelo juiz (`LLM_JUDGE_MODEL`) e envia a ele as mensagens recentes de um chat e as notas desse chat, nunca as de outro chat. Um chat recebe no máximo 16 chamadas por dia, com pelo menos 20 minutos de intervalo, e todos os chats juntos no máximo `MEMORY_CALLS_PER_DAY`. Um chat pouco movimentado precisa de uma chamada por dia ou de nenhuma. Depois de uma chamada que falhou, o chat espera 10 minutos e, depois de cada nova falha, o dobro do tempo, até 6 horas; três falhas seguidas pausam a consolidação em todos os chats por uma hora. Uma resposta que não pode ser lida por inteiro, como uma que contém uma operação de tipo desconhecido, conta como uma chamada que falhou, e as alterações válidas dela são mantidas mesmo assim. Um erro inesperado durante a aplicação de uma resposta não altera nada. Enquanto a consolidação espera, as mensagens são mantidas e consolidadas depois, das mais antigas para as mais novas. **Memória**, na visão Atividade, mostra quantas das chamadas de hoje já foram usadas. Os comandos de memória, a recuperação de lembranças, o esquecimento e a restauração não chamam nenhum modelo.

## Atividade

**Atividade** na página local mostra onde o personagem está e o que ele fez. Ela fica na barra lateral entre **Conversa** e **Conectar plataformas**. Um ponto nela significa que o personagem colocou algo novo em uso desde a última vez que você abriu a Atividade. Os itens que ele ainda observa nunca o acendem.

A visão lista cada chat que o personagem conhece, com a plataforma, se é um grupo ou conversa privada, o fim do identificador do chat e a última atividade. O chat da própria página aparece como **Esta página**. Escolha um chat para ver quatro partes:

- **Aprendizado** lista o que está em uso. Cada item é uma **Redação aprimorada**, com o que ele disse riscado e o que dizer no lugar, ou uma **Resposta a ser reutilizada**, e diz como entrou em uso: porque as reações concordaram, por decisão do próprio personagem, com o motivo dele, ou por uma pessoa. **Desfazer** deixa de usá-lo.
- **Ainda em observação** lista o que o personagem ainda acompanha. Cada item diz em uma frase em que pé está: quantas reações concordantes tem das que precisa, que as reações sozinhas não conseguem resolvê-lo e o próprio personagem o está decidindo, ou que o personagem o examinou e continua a observá-lo, com o motivo. Mostra também a data em que será deixado de lado se nenhuma reação nova chegar. Esta parte não tem botões, e nada nela depende de você.
- **Memória** mostra o que o personagem lembra nesse chat, em cinco grupos: **Sempre em mente** (a nota principal, com a data da última alteração), **Anteriormente nesta conversa** (o resumo, com o período que abrange), **Fatos** (de quem trata cada um, **Segundo** seguido do nome para o que um membro disse sobre outro, quando foi anotado pela primeira vez e quando foi usado pela última vez), **Eventos** (datados, com as pessoas que participaram) e **Removidos recentemente** (o que foi removido, por quê e até quando pode ser restaurado). **Esquecer** remove um item, e a mensagem que confirma isso oferece **Desfazer**. **Restaurar** traz de volta um item removido, e **Restaurar a versão anterior** traz de volta a nota principal anterior. Enquanto a consolidação está ativada, uma linha mostra quantas das chamadas de hoje já foram usadas, ou quando ela tentará de novo depois de um erro. **Esquecer esta conversa**, no fim, esquece tudo o que o chat lembra, depois de pedir confirmação. Em uma conversa privada, a parte inclui também o que os grupos anotaram sobre essa pessoa.
- **Recente** mostra as últimas mensagens e as respostas dele. Cada resposta leva um rótulo com o motivo de ele ter falado: **mencionado**, **participou por iniciativa própria**, **continuação**, **iniciou um assunto** ou **administrador**. As linhas que ele deixou passar mostram por que ficou em silêncio ou o que aconteceu no lugar: o modelo não respondeu, a resposta foi retida por uma verificação de segurança, a resposta não pôde ser entregue, ele pensou em iniciar uma conversa e decidiu não fazê-lo, ou a mensagem foi respondida na mesma resposta que outra mensagem. Quando várias pessoas chamam o personagem quase ao mesmo tempo, uma única resposta atende a todas, e o @ dela vai para quem chamou por último. Quando essa resposta não é enviada, cada pessoa que chamou recebe uma linha própria com o motivo. A atividade recente fica só na memória, então um reinício a apaga.

Cada **Desfazer** é escrito no mesmo registro que `personagent learned`, com o ator `dashboard` e o motivo `local page`.

Abaixo dos chats, **O que o personagem aprendeu** lista tudo o que o personagem aprendeu em todos os chats. Essa lista lê diretamente os arquivos de registro, portanto também funciona quando o personagem não está em execução.

- As abas **Em uso**, **Em observação** e **Deixados de lado** exibem, cada uma, uma contagem.
- Selecionar um item abre o registro completo dele: em que pé está, ou quem o decidiu e por quê (as reações, o personagem com o motivo dele, uma pessoa, o limite de tempo ou uma regra); as mensagens anteriores a ele; cada reação, indicando se conta; e o histórico.
- O personagem decide esses itens por conta própria. As ações aqui são opcionais. **Colocar em uso agora** coloca em uso um item em observação; quando outra redação da mesma resposta já está em uso, mostra essa redação e pede confirmação antes de substituí-la. **Deixar de lado** pede confirmação antes e deixa um item de lado definitivamente. **Desfazer** pede confirmação antes e deixa de usar um item em uso. **Trazer de volta** restaura o que o personagem ou o limite de tempo deixou de lado e o que o personagem ou uma regra tirou de uso. O que uma pessoa desfez ou deixou de lado, e o que uma regra de conteúdo descartou, não pode ser trazido de volta.
- Quando o personagem também aprendeu enquanto falava outro idioma, **Idioma do aprendizado** alterna para esses itens.

Enquanto o personagem está em execução, uma ação passa por ele. Caso contrário, ela é gravada diretamente nos arquivos. O terminal oferece o mesmo registro; veja [Ver o que ele aprendeu e intervir](#ver-o-que-ele-aprendeu-e-intervir).

A lista de chats fica vazia até que o personagem esteja em execução. Ele é iniciado quando você conversa na página ou conecta uma plataforma, e a visão avisa isso. `DASHBOARD_ENABLED=false` desativa os dados por trás da visão. A visão diz então que está desativada, e `personagent doctor` informa `activity: off`.

A página local só responde neste computador. Em um servidor sem página local, `personagent learned` mostra o que o personagem aprendeu, o que está observando e por quê, e permite colocar um item em uso, deixá-lo de lado, desfazê-lo ou trazer de volta o que o personagem ou o limite de tempo deixou de lado e o que o personagem ou uma regra tirou de uso; `personagent memory` faz o mesmo com o que ele lembra. Scripts podem ler os mesmos dados pela API do serviço, descrita na [seção Atividade](deploy.pt-BR.md#atividade) do guia de implantação.

![A visão Atividade de um grupo do Telegram, com as conversas à esquerda (o grupo do Telegram, uma mensagem direta do Discord e Esta página). Aprendizado lista dois itens em uso, cada um com Desfazer: uma redação melhor colocada em uso por decisão própria do personagem, com o motivo, e uma resposta a ser reutilizada colocada em uso porque as reações concordaram. Ainda em observação lista uma resposta a ser reutilizada, com as reações concordantes recebidas até agora e a data em que ela será deixada de lado. Memória mostra o resumo do que veio antes nesta conversa, um fato sobre um membro dito por outro e um evento datado com as pessoas que participaram, cada um com Esquecer, seguidos de Esquecer esta conversa. Na parte inferior, apenas o título de Recente fica visível](activity.png)

## Meça

`personagent eval` executa o agente real em casos rotulados em inglês e chinês (`data/evals/`), em quatro suítes. Ele escreve um relatório JSON com cada caso, resposta e veredito em `benchmark_runs/` na pasta inicial, ou no caminho indicado com `--out`.

| Suíte | Mede |
|---|---|
| `speak` | Se ele fala quando deve. 80 momentos de chat em grupo por idioma: 20 em que ninguém o nomeia, 20 logo depois de ele falar e 20 em que o nome dele aparece, com metade de cada rotulada como silêncio; 10 em que o administrador o chama, todos rotulados para falar; e 10 em uma sala que ficou em silêncio, onde ele pode iniciar uma conversa, com metade rotulada como silêncio. Muitos dos rotulados como silêncio o nomeiam de passagem: um wifi chamado Nova-5G, um comentário sobre ele feito a outra pessoa. Sem juiz: uma resposta está certa ou errada de acordo com o rótulo. |
| `persona` | Se o personagent interpreta o personagem melhor do que o mesmo modelo com só o texto do personagem como prompt de sistema. 40 momentos por idioma, 22 em grupo e 18 em conversas privadas. Um modelo juiz vê as duas respostas às cegas, uma vez com cada uma primeiro. Uma resposta vence quando as duas escolhas concordam nela; quando divergem, o momento fica dividido e conta pela metade. |
| `learning` | Se a regra de promoção decide como planejado e se uma correção promovida muda uma resposta posterior nesse chat. 25 cenários por idioma. Alguns ensinam uma convenção de grupo que o modelo não consegue adivinhar, como o nome que um grupo dá a um lugar. Em alguns, a pessoa corrige a resposta e não aceita uma nova tentativa, então o personagem decide sozinho depois da janela de correção, como faz em um chat real. Outros devem ser retidos: a correção de um espectador, a de um troll, uma que a pessoa abandona. Uma mensagem de teste é executada antes e depois de cada correção, e o juiz diz se a resposta segue o comportamento ensinado. |
| `memory` | Se a memória se comporta como uma pessoa esperaria. 21 casos por idioma, cada um para um mecanismo: lembrar um fato antigo, atualizar e juntar fatos, quem disse o quê, instruções plantadas, palavras que indicam tempo, o que fica na sua sala ou conversa privada, um reinício, esquecer, restaurar, o limite de tamanho, os limites de chamadas, as contas do administrador como uma só pessoa e arquivos de memória antigos. As falas são ditas ao longo de dias em grupos e conversas privadas, as respostas da consolidação são escritas em cada caso, e as verificações leem a memória armazenada e os prompts que uma resposta enviaria. Nenhum modelo é chamado e nenhuma chave é necessária. Todos os 21 casos são atendidos nos dois idiomas. |

```bash
personagent eval --suite speak
personagent eval --suite memory               # no model, no key
personagent eval --suite all --lang zh --repeat 5
```

`--repeat N` tenta cada caso N vezes, cada vez em uma implantação nova, para ver quanto um resultado varia entre tentativas. Os intervalos de 95% contam cada caso uma vez: cinco tentativas de 80 casos continuam sendo evidência de 80 casos. `--limit N` executa N casos por suíte, distribuídos entre modos e rótulos.

As suítes de persona e aprendizado precisam de um modelo juiz diferente do modelo medido. Defina `BENCH_JUDGE_MODEL`, mais `BENCH_JUDGE_BASE_URL` e `BENCH_JUDGE_API_KEY` se outro endpoint o servir. Sem um juiz separado, essas suítes não são executadas. `--allow-same-judge` as executa mesmo assim e marca o relatório. A suíte de aprendizado nunca promove nada por conta própria, e as expectativas dela seguem suas configurações de promoção. Com uma política mais rígida que a padrão, espera-se que todos os cenários sejam retidos. Cada execução das outras suítes chama seus modelos, e todas as suítes trabalham em uma cópia descartável do estado. `--keep` mantém a cópia e imprime onde ela está.

Duas verificações não precisam de modelo nem de chave e são executadas com os testes do projeto a partir de um clone. `data/evals/address.jsonl` contém falas em todos os idiomas de chat que chamam ou não o personagem pelo nome ou por um apelido, como `ＬＵＮＡ are you there` e `Lunar eclipse tonight`; `tests/test_addressing.py` verifica cada uma. `tests/test_behavior_eval.py` executa cada suíte de ponta a ponta com modelos roteirizados, para verificar a infraestrutura, o isolamento e a aritmética de `personagent eval`, e não a qualidade de um modelo.

`--rejudge REPORT` julga de novo as respostas de um relatório guardado com o `BENCH_JUDGE_MODEL` definido agora, sem chamar o modelo testado, e escreve o resultado ao lado do original. As respostas, as referências e o que a política de promoção fez ficam como estão.

Os resultados mais recentes, com o método e todos os relatórios, estão em [evals/2026-10-18](evals/2026-10-18/README.pt-BR.md). Algumas notas para ler os relatórios:

- Em `speak`, a maioria dos erros são linhas em que o nome dele significa outra coisa, como um cinema ou um filhote, ou em que alguém conta a outra pessoa o que ele disse. Um nome conta como chamada, e o modelo raramente passa por cima disso.
- Em `persona`, um empate significa que o juiz escolheu nas duas vezes a resposta que veio primeiro (ou em segundo). Os vereditos publicados são do Claude Opus 5.5. Ele julgou fora de `personagent eval`, em lotes, como registra o campo `rejudged` de cada relatório. O campo `earlier` de cada par guarda o veredito do primeiro juiz, Claude Haiku 5.5.
- Em `learning`, a linha de política e as linhas de teste respondem a perguntas diferentes. A linha de política pergunta se a regra promoveu as correções certas. As linhas de teste perguntam se uma correção promovida mudou uma resposta posterior. A linha de teste `not_promoted` é o nível de ruído, já que nada mudou no prompt dela.

## Como funciona

![Arquitetura: uma mensagem de chat em grupo passa por Decidir, Montar prompt, Modelo e Verificar, e a resposta volta pelo conector; se o bot fica em silêncio, nada é enviado. As reações são julgadas e vão para um registro de evidências, e só o que a promoção aprova chega aos exemplos que o prompt lê](persona_llm_agent_architecture.svg)

Todas as plataformas entram por um único endpoint. Cada mensagem é autenticada, deduplicada e enriquecida, ou seja, as imagens são descritas e os links expandidos. Depois vem a etapa de decisão. Se o bot foi chamado, ele responde. Caso contrário, espera conversa suficiente (30 mensagens por padrão), e uma chamada barata de filtragem a `LLM_JUDGE_MODEL` decide se uma pessoa entraria. Uma rajada de mensagens recebe uma só resposta, à última linha. Quando várias pessoas o chamam dentro da mesma espera curta, uma única resposta atende a todas, e o @ dela vai para quem chamou por último. Uma mensagem longa que o chama chega inteira ao modelo, até 1.000 caracteres. Uma mensagem de grupo que chega mais de 10 minutos depois de ter sido enviada, nos dois minutos seguintes à primeira mensagem da plataforma dela desde que o personagent foi iniciado, é um acúmulo: é mantida como contexto e não é respondida. Passados esses dois minutos, um horário antigo deixa de reter uma mensagem, de modo que um conector cujo relógio está atrasado continua recebendo respostas. Entre 02:00 e 07:00, ele fica quase sempre de fora, a menos que seja chamado.

Antes de uma resposta, uma chamada ao juiz pode decidir se é preciso pesquisar algo na web. Se essa chamada é feita depende apenas da mensagem; a chamada em si também lê as três linhas do chat anteriores à mensagem, para que "o que você acha disso?" seja pesquisado pelo que "isso" é.

O prompt combina a persona, as entradas correspondentes do lorebook, a memória desta conversa (veja [Memória](#memória)) e os exemplos mais relevantes. O modelo responde em JSON com `reasoning`, `intent`, `reply` e `mem`. A resposta passa pelo filtro de saída e pela política do personagem, e depois é dividida em mensagens do tamanho de um chat. A política do personagem retém uma resposta em que o personagem diz, em qualquer um dos dez idiomas de chat, que é um modelo ou um assistente feito por uma empresa de modelos, como "Sou o ChatGPT" ou "Sou um assistente feito pela OpenAI". Signos do zodíaco, palavras e nomes que apenas contêm o nome de uma empresa de modelos e frases sobre o produto de terceiros passam. Uma resposta longa é dividida no fim das frases, nunca depois de um título ou abreviação como Dr. ou z.B., e nunca depois do número de uma data, como em "am 2. Januar". Uma lista numerada só perde os números quando conta 1, 2, 3, de modo que as linhas que começam com datas os mantêm. Uma resposta malformada falha com segurança, então nada é enviado.

O aprendizado funciona paralelamente a esse caminho, nunca dentro dele, e guarda o estado em arquivos simples em `runtime/` na pasta inicial. As reações vão para um registro de evidências que nunca é reescrito. A ponderação delas produz candidatos, e a política de promoção decide quais podem mudar as respostas. Quando reações adicionais não conseguem resolver um candidato, o personagem o decide com uma chamada ao modelo e anota o motivo no registro. Os candidatos promovidos são escritos em pequenos arquivos de visão que a busca recarrega sem reiniciar. Nenhum modelo é ajustado. O personagem aprende melhorando os exemplos do próprio prompt. Como os registros são somente de acréscimo, "por que ele fala assim?" sempre tem resposta, e uma reversão sempre tem o que reverter.

## Privacidade e consentimento

Tudo o que o personagent armazena fica na sua máquina, na pasta inicial: `.env` com suas chaves, `persona.txt`, `persona.card.json`, `runtime/` e `platforms/` com as credenciais das plataformas. Em um clone, nenhum desses arquivos é versionado no Git. Eles podem conter credenciais e conversas reais, então faça backup e mantenha-os privados. As mensagens recentes de cada chat são mantidas em `runtime/recent.json` por 72 horas, a menos que `MEMORY_KEEP_RECENT=false`, e o que o personagem remove da memória continua restaurável em `runtime/memory_trash.jsonl` por até 30 dias. A página local nunca coloca a chave no armazenamento do navegador.

A visão [Atividade](#atividade) faz parte da página local, que só escuta em 127.0.0.1. A API do serviço por trás dela só responde a solicitações com o token de `runtime/dashboard.token`, um arquivo que só o seu usuário pode ler. `CONNECTOR_TOKEN` não a abre. A visão nunca mostra chaves de API nem tokens. `DASHBOARD_ENABLED=false` a desativa.

No máximo uma vez por dia, a página local, `personagent up` e `personagent doctor` perguntam a pypi.org o número da versão mais recente. A solicitação contém apenas a versão do personagent. `UPDATE_CHECK_ENABLED=false` interrompe isso.

O provedor de modelos vê as conversas:

- O contexto do chat vai para o seu `LLM_BASE_URL`.
- Se você configurar um fallback (`LLM_FALLBACK_MODEL`, `LLM_FALLBACK_BASE_URL`), ele também é chamado em turnos comuns para o filtro de resposta, as decisões de busca, o julgamento de reações, a autoavaliação e a rotulagem de figurinhas, e também recebe o contexto do chat.
- A consolidação da memória envia as mensagens recentes de um chat e as notas desse chat ao modelo juiz (`LLM_JUDGE_MODEL`), nunca as de outro chat. `MEMORY_CALLS_PER_DAY=0` a desativa.
- Quando o próprio personagem decide um item aprendido, a resposta, as reações a ela e as redações candidatas vão para `PROMOTE_JUDGE_MODEL` (vazio: `REACT_MODEL`). `PROMOTE_JUDGE_ENABLED=false` desativa isso.
- As imagens vão para o endpoint de visão.
- Quando o modelo decide procurar algo, a consulta vai para o Tavily (se `TAVILY_API_KEY` estiver definido) ou para o DuckDuckGo.
- Com `EMBEDDING_MODEL` definido, a mensagem que ele responde, as lembranças e os exemplos de busca vão para o endpoint de embeddings (`EMBEDDING_BASE_URL`, ou `LLM_BASE_URL` se vazio).

Antes de conectá-lo a pessoas reais, diga a elas que é um bot e obtenha o consentimento delas para o processamento das mensagens. Leia o [aviso legal](DISCLAIMER.pt-BR.md).

## Solução de problemas

**Comece pela verificação de funcionamento.** Na página local, abra **Aplicativo** e selecione **Iniciar a verificação**. A visão indica cada serviço que não está funcionando, por que o personagem ou uma plataforma não iniciou e as configurações que requerem atenção, e **Logs** mostra cada log sem que seja preciso abrir um arquivo. Veja [A visão Aplicativo](#a-visão-aplicativo).

**No terminal, execute `personagent doctor`.** Ele verifica a configuração e nomeia configurações com erro de grafia ou renomeadas. Depois testa cada serviço de que o personagent depende. Os testes enviam solicitações minúsculas e podem custar um pouco de crédito. `--json` imprime os mesmos resultados em JSON. `--fix` renomeia as configurações removidas na 1.0 e salva o arquivo antigo como `.env.bak`.

**Uma plataforma não conecta.** Quando a plataforma recusa as credenciais, a página diz por quê, assim como `personagent connect <plataforma>` em um terminal. Verifique-as no console da plataforma e, no Discord, confirme que Message Content Intent está ativado. Você pode pedir um novo código QR quando ele expira e tentar de novo um download do AstrBot que falhou. **Conexões com plataformas**, na visão Aplicativo, mostra o estado de cada plataforma que o personagent conecta por conta própria. Os logs de tudo o que a página ou `personagent up` iniciou ficam em `runtime/desktop/` na pasta inicial, e a visão Aplicativo os exibe em **Logs**.

**Está em execução, mas nunca responde.** As três causas mais comuns são:

1. O agente está desativado. O banner de `personagent run` mostra então `OFF` e nomeia a causa, geralmente um `LLM_API_KEY` faltando. Defina a chave na página local ou execute `personagent init`.
2. Nada está chegando. No computador que executa a página local, abra [Atividade](#atividade) e procure o chat. Em um servidor, mencione o bot pelo nome e verifique o log do serviço: ele registra cada resposta e cada chat recusado. Se nenhuma mensagem chegou, o conector não as está encaminhando ou não alcança o personagent. No QQ, verifique no próprio QQ quais mensagens de grupo o bot recebe. Com um AstrBot que você executa, o plugin só encaminha os `groups` e `dm_users` que lista, e para o NapCat, `aiocqhttp` não pode estar nos `excluded_platforms` dele. Verifique também o `personagent_url` do plugin e se `CONNECTOR_TOKEN` é igual nos dois lados.
3. Ele não foi chamado. Chame-o pelo nome (`PERSONA_NAME`, comparado como palavra inteira). Em um grupo, ele só considera entrar depois de `CHAT_TRIGGER_COUNT` mensagens (30), e só quando o filtro diz que uma pessoa entraria.

O guia de implantação tem [a lista de verificação completa](deploy.pt-BR.md#quando-o-bot-fica-em-silêncio).

**Está em execução?** `curl http://127.0.0.1:8080/health` responde sem chamar um modelo. `/health/details` também testa os serviços e exige um cabeçalho `X-Personagent-Token` quando há um token configurado.

**Não inicia.** `personagent run` sai com uma frase dizendo por quê. Os motivos usuais são uma porta já em uso, outro personagent em execução na mesma pasta inicial, um endereço de rede definido sem `CONNECTOR_TOKEN`, uma configuração removida na 1.0 ainda definida, ou um arquivo de memória danificado, caso em que a frase nomeia a cópia datada a colocar no lugar dele. As configurações removidas são listadas uma por linha como `OLD -> NEW`, e `personagent doctor --fix` as renomeia, assim como **Renomear as configurações** na visão Aplicativo. Quando o personagem iniciado pela página falha, a visão Aplicativo indica a parte que falhou e mostra a última linha do log dela. A página e `personagent up` escolhem uma porta livre quando a 8080 está ocupada.

**Uma configuração não tem efeito.** Reinicie o processo que a lê, verifique a grafia e salve `.env` como UTF-8 sem BOM. As variáveis de ambiente do shell têm prioridade sobre `.env`. Os booleanos são `true` ou `false`. `PERSONA_TZ_OFFSET_HOURS` define o fuso horário do personagem: o período noturno e as datas do que ele lembra o seguem. Quando está vazio (padrão), o personagent usa UTC+8 com `AGENT_LANG=zh` ou `zh-TW` e, nos outros casos, o fuso horário desta máquina. Informe um número para escolher outro deslocamento.

## Atualização a partir da 0.x

A 1.0 renomeou a maioria das configurações, e o personagent não inicia enquanto um nome antigo estiver definido. Ele lista cada um como `OLD -> NEW`, e `personagent doctor --fix` os renomeia em `.env`. [Upgrading from 0.4](../CHANGELOG.md#upgrading-from-04) no registro de alterações lista todas as etapas. A memória e o que ele aprendeu são mantidos.

## Status e outros documentos

O personagent 1.4.3 está no PyPI. A CI executa os testes no Linux com Python 3.10–3.14 e no Windows com Python 3.12. Outros trabalhos de CI instalam o pacote, acionam o comando e a página local e abrem a janela do aplicativo no Linux, no macOS e no Windows.

O caminho direto OneBot (`/v1/onebot`) está obsoleto, mas permanece durante toda a 1.x. Os scripts em `tools/` foram feitos para serem executados a partir de um clone, e [tools.md](tools.pt-BR.md) os descreve.

- [Início rápido](start.pt-BR.md) · [Guia de implantação](deploy.pt-BR.md) · [Passo a passo em chinês (QQ por leitura de código e solução de problemas)](deploy.zh-CN.md)
- Conectores: [plugin do AstrBot](../integrations/astrbot/astrbot_plugin_personagent/README.pt-BR.md) · [Satori](../integrations/satori/README.pt-BR.md) · [Matrix](../integrations/matrix/README.pt-BR.md) · [protocolo](connectors.pt-BR.md)
- [Todas as configurações](../.env.example) · [Registro de alterações](../CHANGELOG.md) · [Contribuir](../.github/CONTRIBUTING.md) · [Política de segurança](../.github/SECURITY.md)
