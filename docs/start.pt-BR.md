# Começar a usar o personagent

[English](start.md) · [简体中文](start.zh-CN.md) · [繁體中文](start.zh-TW.md) · [日本語](start.ja.md) · [한국어](start.ko.md) · [Español](start.es.md) · [Français](start.fr.md) · [Deutsch](start.de.md) · Português (Brasil) · [Русский](start.ru.md) · [Guia completo](guide.pt-BR.md)

## Abrir

Instale o personagent pelo PyPI e abra-o:

```sh
python -m pip install personagent
personagent
```

Com o [uv](https://docs.astral.sh/uv/), `uvx personagent` o executa sem uma etapa de instalação separada.

No Windows, a página abre em uma janela própria. No macOS e no Linux, ela abre no navegador; `pip install "personagent[app]"` permite que ela também abra em uma janela própria nesses sistemas.

Um assistente de programação pode fazer a configuração por você: peça que ele leia [setup-for-agents.md](setup-for-agents.md) e configure o personagent.

No Windows, você também pode baixar o ZIP do código-fonte, descompactá-lo e clicar duas vezes em `start.bat`. Ele cria um ambiente Python próprio na pasta e abre a mesma página. Na primeira vez, ele também adiciona um ícone do personagent à área de trabalho e ao menu Iniciar.

Para executá-lo a partir de um clone, crie para ele um venv próprio: `python -m venv .venv`, depois `.venv/bin/python -m pip install -e .` e `.venv/bin/python -m persona_agent`. No Windows, o interpretador é `.venv\Scripts\python.exe`, ou você pode clicar duas vezes em `start.bat`.

## Adicione uma chave e converse

Escolha um serviço de modelo, cole a chave de API dele e clique em **Verificar e iniciar a conversa**. Os modelos gratuitos do OpenRouter e o personagem Ouvinte acolhedor vêm selecionados inicialmente. A chave é gratuita, e o limite é de 50 solicitações por dia; a pequena solicitação enviada para verificá-la só tem custo em um serviço pago. **Configurações avançadas** contém o nome do modelo e o endereço da API, e **Escolher um nome, uma personalidade ou um idioma** contém o nome, a personalidade e o idioma em que o personagem conversa. O menu no canto superior direito da página muda apenas o idioma em que a própria página é exibida.

A chave permanece no seu computador; clique em **Mostrar** para conferi-la. As mensagens da conversa são enviadas ao serviço de modelo que você escolher, pelas tarifas habituais desse serviço.

O personagem responde na página, com figurinhas e imagens quando as envia. As mensagens que ele envia depois, como uma mensagem iniciada por ele mesmo, aparecem na conversa em poucos segundos. As configurações ficam salvas, de modo que a próxima abertura leva diretamente à conversa.

Após a configuração, **Personagem e configurações** apresenta uma caixa **Persona** com o texto que define o personagem. Reescreva quem ele é e como se expressa e, em seguida, clique em **Salvar a persona**. A alteração entra em vigor imediatamente, e o que o personagem aprendeu é mantido.

Abaixo dela, **Mais recursos** ativa a pesquisa na web, a compreensão de imagens e o início de conversas por iniciativa própria. A pesquisa usa o DuckDuckGo por padrão; uma chave do Tavily a torna mais confiável. Logo abaixo, **Configurações avançadas** reúne as configurações que antes só estavam disponíveis no `.env`. Até que você conecte uma plataforma, a visão **Conversa** mostra uma barra curta de **Primeiros passos**.

Outras duas visões não exigem nenhuma plataforma. **Prática** reproduz uma demonstração roteirizada e oferece um grupo de prática, no qual é possível ver por que o personagem responde ou permanece em silêncio. **Aplicativo** verifica cada serviço de que o personagem depende, exibe os logs e reúne as atualizações, os backups e o ícone da área de trabalho.

**Atividade** mostra as conversas em que o personagem está, o que ele disse recentemente, o que ele lembra e o que aprendeu. O personagem decide por conta própria o que aprende e mantém a memória atualizada; nada ali espera por você. Ainda assim, você pode desfazer qualquer coisa que ele aprendeu e esquecer ou restaurar qualquer coisa que ele lembra.

## Conecte outras plataformas

1. Clique em **Conectar plataformas** e escolha uma plataforma. Após a conexão, o personagem responde nos grupos e nas conversas privadas dessa plataforma.
   - **Conectar com QR code**: QQ e WeChat pessoal. Clique em **Gerar QR code** e confirme no celular.
     - QQ: leia o código com o QQ no celular. O QQ cria um bot ou permite que você escolha um que já possui, e o personagent obtém as chaves dele. Se você mesmo criou o bot na [página de bots do QQ](https://q.qq.com/qqbot/openclaw/login.html), clique em **Colar valores manualmente** e informe o AppID e o AppSecret.
     - WeChat: leia o código com o WeChat. O bot conversa apenas individualmente, porque o WeChat não repassa mensagens de grupo a esses bots.
   - **Colar alguns valores**: Telegram (um token do @BotFather), Discord (um token de bot, com Message Content Intent ativado), KOOK, Feishu, DingTalk, Slack, Bot de IA do WeCom, Mattermost, Misskey, Matrix, Twitch, IRC, Zulip, VK e Stoat. A página indica quais valores copiar do console da plataforma. Todo o restante usa os valores padrão. A Twitch também solicita que você aprove um login por meio de um link.
   - **Avançado**: o Aplicativo do WeCom, as Contas Oficiais do WeChat e os webhooks do QQ requerem um endereço público que encaminhe para a porta de callback deles. OneBot v11 (NapCat) e Satori requerem outro software em execução neste computador.
2. O personagent conecta QQ, WeChat, Telegram, Discord, Matrix, Twitch, IRC, Zulip, VK e Stoat por conta própria. As demais plataformas passam pelo AstrBot, uma ponte de terceiros. Na primeira vez que você conecta uma delas, o personagent baixa o AstrBot com um ambiente Python 3.12 separado; mantenha a página aberta até a conclusão. Depois disso, o AstrBot é executado em segundo plano, sem painel em que seja preciso fazer login.
3. O personagent verifica as credenciais com a plataforma antes de salvá-las. Se a plataforma as recusar, a página informa o motivo e nada é salvo.
4. As plataformas conectadas ficam listadas no topo de **Conectar plataformas**, onde você pode configurá-las novamente ou desconectá-las.
5. Sem a página, por exemplo em um servidor sem monitor, `personagent connect <plataforma>` conecta QQ, WeChat, Telegram, Discord, Matrix, Twitch, IRC, Zulip, VK ou Stoat pelo terminal, com as mesmas etapas e verificações. `personagent connect` sozinho lista essas plataformas. O [guia completo](guide.pt-BR.md#conectar-uma-plataforma-no-terminal) descreve o comando.

Para encontrar um bot do QQ, abra o QQ no celular e acesse Contatos → Bots. Converse com ele em particular ou adicione-o a um grupo do qual você seja o proprietário. Este caminho usa a plataforma oficial de bots do QQ; portanto, você não precisa de uma conta pessoal do QQ nem de software adicional. O QQ decide onde o bot pode entrar. Até que o bot seja certificado, ele só pode entrar em grupos cujo proprietário seja o administrador dele, e não há sandbox a configurar. Em um grupo, ele só vê as mensagens que o mencionam com @, a menos que o proprietário do grupo ative o recebimento de todas as mensagens no perfil do bot nesse grupo. O [guia de bots do QQ](https://bot.q.qq.com/wiki/bot_new_product-intro/) trata da certificação e dos demais aspectos da conta.

Se um QR code expirar, solicite um novo. Se um download falhar, tente novamente sem repetir a configuração do modelo. Conectar uma plataforma dá ao personagem acesso apenas aos grupos e às conversas privadas dessa plataforma; os outros adaptadores mantêm suas listas de permissão. O LINE não é oferecido, porque o AstrBot só recebe callbacks do LINE pelo painel dele, que o personagent não executa.

## Da próxima vez

Abra o personagent novamente. As configurações são mantidas, e as plataformas conectadas são retomadas automaticamente. Se ele já estiver em execução, abri-lo novamente exibe a janela existente. Mantenha-a aberta enquanto o utiliza: os processos que ele iniciou são encerrados junto com ele, seja ao clicar em **Sair**, seja ao fechar a janela, e o que uma falha tiver deixado em execução é encerrado na próxima inicialização. No Windows, `personagent shortcut` adiciona à área de trabalho e ao menu Iniciar um ícone que o abre sem terminal. Também no Windows, **Executar em segundo plano**, na visão **Aplicativo**, permite que o personagent continue em execução após o fechamento da janela, representado por um ícone na área de notificação, e o personagem continua respondendo.

Quando há uma versão mais recente no PyPI, a visão **Conversa** mostra um aviso com um link para as notas da versão e o comando de atualização correspondente à forma como esta cópia foi instalada. Uma cópia descompactada do ZIP do código-fonte recebe, em vez disso, um link para baixar o novo código na página de versões. Na maioria das instalações, **Atualizar e reabrir**, na visão **Aplicativo**, instala a atualização. O personagent consulta o pypi.org no máximo uma vez por dia, e a solicitação contém apenas o número da versão. Defina `UPDATE_CHECK_ENABLED=false` no `.env` para desativar a verificação.

Se preferir a linha de comando, use `personagent start --terminal`, `personagent init --terminal`, `personagent up` ou os comandos `chat`, `demo` (sem chave), `run` e `connect`. Eles mantêm o `.env` existente, a persona editada e as memórias aprendidas. O [guia completo](guide.pt-BR.md) trata das demais plataformas.
