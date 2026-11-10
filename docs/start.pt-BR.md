# Começar a usar o personagent

[English](start.md) · [简体中文](start.zh-CN.md) · [繁體中文](start.zh-TW.md) · [日本語](start.ja.md) · [한국어](start.ko.md) · [Español](start.es.md) · [Français](start.fr.md) · [Deutsch](start.de.md) · Português (Brasil) · [Русский](start.ru.md) · [Guia completo](guide.pt-BR.md)

## Abrir

Instale o personagent pelo PyPI e abra:

```sh
python -m pip install personagent
personagent
```

Com o [uv](https://docs.astral.sh/uv/), `uvx personagent` executa sem uma etapa de instalação separada.

No Windows, a página abre em uma janela própria. No macOS e no Linux, ela abre no seu navegador; `pip install "personagent[app]"` dá a ela uma janela lá também.

Um agente de programação pode fazer a configuração por você: peça que ele leia [setup-for-agents.md](setup-for-agents.md) e configure o personagent.

No Windows, você também pode baixar o ZIP do código-fonte, descompactar e clicar duas vezes em `start.bat`. Ele cria um ambiente Python próprio na pasta e abre a mesma página. Na primeira vez, ele também coloca um ícone do personagent na sua área de trabalho e no menu Iniciar.

Para executar a partir de um clone, dê a ele um venv próprio: `python -m venv .venv`, depois `.venv/bin/python -m pip install -e .` e `.venv/bin/python -m persona_agent`. No Windows, o interpretador é `.venv\Scripts\python.exe`, ou você pode clicar duas vezes em `start.bat`.

## Adicione uma chave e converse

Escolha um serviço de modelos, cole a chave de API dele e clique em **Verificar e começar a conversar**. Os modelos gratuitos do OpenRouter e o personagem ouvinte acolhedor vêm selecionados no início. A chave é gratuita e o limite é de 50 solicitações por dia. **Configurações avançadas** contém o nome do modelo e o endereço da API, e **Escolha um nome ou personalidade** contém o nome e a personalidade do personagem.

A chave fica no seu computador; clique em **Mostrar** para conferir. As mensagens do chat vão para o serviço de modelos que você escolher, pelas tarifas normais desse serviço.

Seu personagem responde na página. Suas configurações ficam salvas, então a próxima abertura vai direto para o chat.

Depois de configurado, **Personagem e configurações** tem uma caixa **Persona** com o texto em que o personagem se baseia. Reescreva quem ele é e como fala, depois clique em **Salvar persona**. A mudança vale na hora, e o que o personagem aprendeu é mantido.

Abaixo, **Mais recursos** ativa a busca na web, a compreensão de imagens e falar primeiro. A busca usa o DuckDuckGo por padrão; uma chave do Tavily a torna mais confiável. Até você conectar um app, a visão **Conversa** mostra uma barra curta de primeiros passos.

## Leve para outros apps

1. Clique em **Conectar apps** e escolha um app. Depois de conectado, seu personagem responde nos grupos e nas mensagens diretas desse app.
   - **Escanear para conectar**: QQ e WeChat pessoal. Clique em **Gerar QR code** e confirme no celular.
     - QQ: escaneie com o QQ para celular. O QQ cria um bot ou deixa você escolher um que já tem, e o personagent busca as chaves dele. Se você mesmo criou o bot na [página de bots do QQ](https://q.qq.com/qqbot/openclaw/login.html), clique em **Colar valores em vez disso** e informe o AppID e o AppSecret.
     - WeChat: escaneie com o WeChat. O bot só conversa um a um, porque o WeChat não repassa mensagens de grupo para esses bots.
   - **Colar um ou dois valores**: Telegram (um token do @BotFather), Discord (um token de bot, com Message Content Intent ativado), KOOK, Feishu, DingTalk, Slack, bot de IA do WeCom, Mattermost e Misskey. A página diz quais valores copiar do console do app. Todo o resto usa os padrões.
   - **Avançado**: apps do WeCom, contas oficiais do WeChat e webhooks do QQ precisam de um endereço público que encaminhe para a porta de callback deles. OneBot v11 (NapCat) e Satori precisam de outro software em execução neste computador.
2. O personagent conecta QQ, WeChat, Telegram e Discord por conta própria. Os outros apps passam pelo AstrBot, uma ponte de terceiros. Na primeira vez que você conecta um deles, o personagent baixa o AstrBot com um ambiente Python 3.12 separado, então mantenha a página aberta até terminar. Depois, o AstrBot roda em segundo plano, sem painel para entrar.
3. O personagent verifica as credenciais com o app antes de salvá-las. Se o app as recusar, a página avisa e nada é salvo.
4. Os apps conectados ficam listados no topo de **Conectar apps**, onde você pode configurá-los de novo ou desconectá-los.

Para encontrar um bot do QQ, abra o QQ para celular e vá em Contatos → Bots. Converse com ele em privado ou adicione-o a um grupo que seja seu. Este caminho usa a plataforma oficial de bots do QQ, então você não precisa de conta pessoal do QQ nem de software extra. O QQ decide onde o bot pode entrar. Até o bot ser certificado, ele só pode entrar em grupos cujo dono seja o administrador dele, e não há sandbox para configurar. Em um grupo, ele só vê mensagens que o mencionam com @, a menos que o dono do grupo ative o recebimento de todas as mensagens no perfil do bot nesse grupo. O [guia de bots do QQ](https://bot.q.qq.com/wiki/bot_new_product-intro/) cobre a certificação e o resto do lado da conta.

Se um QR code expirar, peça um novo. Se um download falhar, tente de novo sem repetir a configuração do modelo. Conectar um app abre ao personagem apenas os grupos e as mensagens diretas desse app; os outros adaptadores mantêm suas listas de permissão. O LINE não é oferecido, porque o AstrBot só recebe callbacks do LINE pelo painel dele, que o personagent não executa.

## Da próxima vez

Abra o personagent de novo. Suas configurações são mantidas e os apps conectados voltam sozinhos. Se ele já estiver rodando, abrir de novo traz a janela dele de volta. Mantenha-a aberta enquanto usa: os processos que ele iniciou param junto com ele, quer você clique em **Sair** ou feche a janela, e o que uma falha deixou para trás é encerrado na próxima inicialização. No Windows, `personagent shortcut` coloca na sua área de trabalho e no menu Iniciar um ícone que o abre sem terminal.

Quando há uma versão mais nova no PyPI, a visão **Conversa** mostra um aviso com um link para as notas da versão e o comando de atualização de acordo com a forma como esta cópia foi instalada. Uma cópia descompactada do ZIP do código-fonte recebe, em vez disso, um link para baixar o novo código da página de versões. O personagent consulta o pypi.org no máximo uma vez por dia, e a solicitação leva apenas o número da versão. Defina `UPDATE_CHECK_ENABLED=false` no `.env` para desativar a verificação.

Se preferir a linha de comando, use `personagent start --terminal`, `personagent init --terminal`, `personagent up` ou os comandos `chat`, `demo` (sem chave), `run` e `connect`. Eles mantêm seu `.env`, sua persona editada e as memórias aprendidas. O [guia completo](guide.pt-BR.md) cobre as outras plataformas.
