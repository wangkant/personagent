# Começar a usar o personagent

[English](start.md) · [简体中文](start.zh-CN.md) · [繁體中文](start.zh-TW.md) · [日本語](start.ja.md) · [한국어](start.ko.md) · [Español](start.es.md) · [Français](start.fr.md) · [Deutsch](start.de.md) · Português (Brasil) · [Русский](start.ru.md) · [Guia completo](guide.pt-BR.md)

## Abrir

Não é preciso instalar nada antes: o instalador traz o próprio Python. Cole uma linha em um terminal.

No Windows, pressione a tecla Windows, digite `PowerShell`, pressione Enter e cole:

```powershell
irm https://raw.githubusercontent.com/wangkant/personagent/main/install.ps1 | iex
```

No macOS, abra o Terminal (em Aplicativos > Utilitários); no Linux, qualquer terminal. Cole:

```sh
curl -LsSf https://raw.githubusercontent.com/wangkant/personagent/main/install.sh | sh
```

A primeira execução leva alguns minutos. Ela instala o personagent, o abre e, no Windows, adiciona um ícone do personagent à área de trabalho e ao menu Iniciar; no macOS, deixa `personagent.command` na área de trabalho e, no Linux, uma entrada no menu de aplicativos. Quando o PyPI ou o GitHub estão lentos, o instalador passa sozinho a usar espelhos na China continental; `PERSONAGENT_MIRROR=cn` antes do comando faz com que ele os use desde o início, e `off`, nunca. Se o próprio `raw.githubusercontent.com` estiver inacessível, os mesmos dois arquivos estão disponíveis em `https://cdn.jsdelivr.net/gh/wangkant/personagent@main/install.ps1` e `.../install.sh`. Execute a mesma linha novamente para atualizar, e `uv tool uninstall personagent` para remover o programa; a pasta do personagent é mantida.

Com o Python 3.10 ou posterior já instalado, você pode instalar pelo PyPI:

```sh
python -m pip install personagent
personagent
```

Com o [uv](https://docs.astral.sh/uv/), `uvx personagent` o executa sem uma etapa de instalação separada.

No Windows, a página abre em uma janela própria. No macOS e no Linux, ela abre no navegador; `pip install "personagent[app]"` permite que ela também abra em uma janela própria nesses sistemas.

Um assistente de programação pode fazer a configuração por você: peça que ele leia [setup-for-agents.md](setup-for-agents.md) e configure o personagent.

No Windows, você também pode baixar o ZIP do código-fonte, descompactá-lo e clicar duas vezes em `start.bat`. Ele cria um ambiente Python próprio na pasta, baixando antes o Python quando o computador não o tem, e abre a mesma página. Na primeira vez, ele também adiciona um ícone do personagent à área de trabalho e ao menu Iniciar.

Para executá-lo a partir de um clone, crie para ele um venv próprio: `python -m venv .venv`, depois `.venv/bin/python -m pip install -e .` e `.venv/bin/python -m persona_agent`. No Windows, o interpretador é `.venv\Scripts\python.exe`, ou você pode clicar duas vezes em `start.bat`.

## Entrar e conversar

Os modelos gratuitos do OpenRouter e o personagem Ouvinte acolhedor vêm selecionados inicialmente. Clique em **Entrar com o OpenRouter**: o navegador abre a página do OpenRouter, onde você entra ou cria uma conta e aprova o acesso. O personagent recebe uma chave do OpenRouter, verifica-a com uma pequena solicitação, salva-a e abre a conversa. A chave fica salva neste computador. Até você removê-la em [openrouter.ai/keys](https://openrouter.ai/keys), ela pode gastar o crédito da sua conta do OpenRouter; os modelos gratuitos não precisam de crédito, e o limite deles é de 50 solicitações por dia. Se nenhuma janela do navegador aparecer, a página oferece um link para a página do OpenRouter; **Cancelar** para de esperar, e uma tentativa não aprovada em dez minutos expira. No terminal, `personagent init --terminal` oferece o mesmo login: mostra um endereço para abrir em qualquer dispositivo e pede o código que a página do OpenRouter exibe.

Você também pode colar uma chave: escolha um serviço de modelo, cole a chave de API dele e clique em **Verificar e iniciar a conversa**. **Obter uma chave de API** abre a página de chaves do serviço selecionado. A pequena solicitação enviada para verificar uma chave só tem custo em um serviço pago. Quando uma chave funciona, o nome do modelo em **Nome do modelo e endereço** oferece os modelos que o serviço lista, com os modelos gratuitos do OpenRouter marcados; qualquer outro nome ainda pode ser digitado. **Nome do modelo e endereço** contém o nome do modelo e o endereço da API, e **Escolher um nome, uma personalidade ou um idioma** contém o nome, a personalidade e o idioma em que o personagem conversa. O menu no canto superior direito da página muda apenas o idioma em que a própria página é exibida.

Se o Ollama ou o LM Studio já estiver em execução no computador com um modelo carregado, ou se a chave de um serviço de modelo já estiver definida em uma variável de ambiente (como `DEEPSEEK_API_KEY` ou `OPENAI_API_KEY`), a página indica isso acima do serviço de modelo, e um clique em **Usar Ollama** ou **Usar esta chave** faz a verificação e inicia a conversa. Um modelo local não precisa de chave, e nada sai do computador.

A chave permanece no seu computador; clique em **Mostrar** para conferi-la. As mensagens da conversa são enviadas ao serviço de modelo que você escolher, pelas tarifas habituais desse serviço.

O personagem responde na página, com figurinhas e imagens quando as envia. As mensagens que ele envia depois, como uma mensagem iniciada por ele mesmo, aparecem na conversa em poucos segundos. As configurações ficam salvas, de modo que a próxima abertura leva diretamente à conversa.

Após a configuração, **Personagem e configurações** apresenta uma caixa **Persona** com o texto que define o personagem. Reescreva quem ele é e como se expressa e, em seguida, clique em **Salvar a persona**. A alteração entra em vigor imediatamente, e o que o personagem aprendeu é mantido. Para começar de uma ideia, descreva o personagem em uma frase acima da caixa e clique em **Escrever um rascunho**. Para trazer um personagem que alguém compartilhou como cartão de personagem do Tavern (PNG, JSON ou CHARX), use **Importar um cartão de personagem** abaixo da caixa; [o guia](guide.pt-BR.md#cartões-de-personagem-e-rascunhos) explica no que cada parte se transforma.

Abaixo dela, **Mais recursos** ativa a pesquisa na web, a compreensão de imagens e o início de conversas por iniciativa própria. A pesquisa usa o DuckDuckGo por padrão; uma chave do Tavily a torna mais confiável. Logo abaixo, **Configurações avançadas** reúne as configurações que antes só estavam disponíveis no `.env`. Até que você conecte uma plataforma, a tela **Conversa** mostra uma barra curta de **Primeiros passos**.

Outras duas telas não exigem nenhuma plataforma. **Prática** reproduz uma demonstração roteirizada e oferece um grupo de prática, no qual é possível ver por que o personagem responde ou permanece em silêncio. **Aplicativo** verifica cada serviço de que o personagem depende, exibe os registros e reúne as atualizações, os backups e o ícone da área de trabalho.

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
5. Para qualquer outro programa que aceite um endereço compatível com OpenAI, como Open WebUI, SillyTavern ou um script, ative **Outros programas** na parte inferior de **Conectar plataformas** e copie o endereço, a chave e o modelo para esse programa. O [guia completo](guide.pt-BR.md#outros-programas) descreve isso.
6. Sem a página, por exemplo em um servidor sem monitor, `personagent connect <plataforma>` conecta QQ, WeChat, Telegram, Discord, Matrix, Twitch, IRC, Zulip, VK ou Stoat pelo terminal, com as mesmas etapas e verificações. `personagent connect` sozinho lista essas plataformas. O [guia completo](guide.pt-BR.md#conectar-uma-plataforma-no-terminal) descreve o comando.

Para encontrar um bot do QQ, abra o QQ no celular e acesse Contatos → Bots. Converse com ele em particular ou adicione-o a um grupo do qual você seja o proprietário. Este caminho usa a plataforma oficial de bots do QQ; portanto, você não precisa de uma conta pessoal do QQ nem de software adicional. O QQ decide onde o bot pode entrar. Até que o bot seja certificado, ele só pode entrar em grupos cujo proprietário seja o administrador dele, e não há sandbox a configurar. Em um grupo, ele só vê as mensagens que o mencionam com @, a menos que o proprietário do grupo ative o recebimento de todas as mensagens no perfil do bot nesse grupo. O [guia de bots do QQ](https://bot.q.qq.com/wiki/bot_new_product-intro/) trata da certificação e dos demais aspectos da conta.

Se um QR code expirar, solicite um novo. Se um download falhar, tente novamente sem repetir a configuração do modelo. Conectar uma plataforma dá ao personagem acesso apenas aos grupos e às conversas privadas dessa plataforma; os outros adaptadores mantêm suas listas de permissão. O LINE não é oferecido, porque o AstrBot só recebe callbacks do LINE pelo painel dele, que o personagent não executa.

## Da próxima vez

Abra o personagent novamente. As configurações são mantidas, e as plataformas conectadas são retomadas automaticamente. Se ele já estiver em execução, abri-lo novamente exibe a janela existente. Mantenha-a aberta enquanto o utiliza: os processos que ele iniciou são encerrados junto com ele, seja ao clicar em **Sair**, seja ao fechar a janela, e o que uma falha tiver deixado em execução é encerrado na próxima inicialização. No Windows, `personagent shortcut` adiciona à área de trabalho e ao menu Iniciar um ícone que o abre sem terminal. Também no Windows, **Executar em segundo plano**, na tela **Aplicativo**, permite que o personagent continue em execução após o fechamento da janela, representado por um ícone na área de notificação, e o personagem continua respondendo.

Quando há uma versão mais recente no PyPI, a tela **Conversa** mostra um aviso com um link para as notas da versão e o comando de atualização correspondente à forma como esta cópia foi instalada. Uma cópia descompactada do ZIP do código-fonte recebe, em vez disso, um link para baixar o novo código na página de versões. Na maioria das instalações, **Atualizar e reabrir**, na tela **Aplicativo**, instala a atualização. O personagent consulta o pypi.org no máximo uma vez por dia, e a solicitação contém apenas o número da versão. Defina `UPDATE_CHECK_ENABLED=false` no `.env` para desativar a verificação.

Se preferir a linha de comando, use `personagent start --terminal`, `personagent init --terminal`, `personagent up` ou os comandos `chat`, `demo` (sem chave), `run` e `connect`. Eles mantêm o `.env` existente, a persona editada e as memórias aprendidas. O [guia completo](guide.pt-BR.md) trata das demais plataformas.
