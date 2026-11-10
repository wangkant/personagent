<p align="center">
  <img src="https://raw.githubusercontent.com/wangkant/personagent/main/assets/personagent-cover.webp" alt="personagent" width="100%">
</p>

<h3 align="center">Um personagem para seus grupos de chat que sabe quando ficar quieto e aprende quando é corrigido.</h3>

<p align="center">
  <a href="https://pypi.org/project/personagent/"><img src="https://img.shields.io/pypi/v/personagent?style=flat-square&label=PyPI&labelColor=24292f&color=0969da&cacheSeconds=3600" alt="PyPI"></a>
  <a href="https://github.com/wangkant/personagent/actions/workflows/ci.yml"><img src="https://img.shields.io/github/actions/workflow/status/wangkant/personagent/ci.yml?branch=main&style=flat-square&label=CI&labelColor=24292f" alt="CI"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/Python-3.10%E2%80%933.14-0969da?style=flat-square&labelColor=24292f" alt="Python 3.10–3.14"></a>
  <a href="https://github.com/wangkant/personagent/blob/main/LICENSE"><img src="https://img.shields.io/badge/License-MIT-0969da?style=flat-square&labelColor=24292f" alt="Licença: MIT"></a>
</p>

<p align="center"><a href="https://github.com/wangkant/personagent/blob/main/README.md">English</a> · <a href="https://github.com/wangkant/personagent/blob/main/README.zh-CN.md">简体中文</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.zh-TW.md">繁體中文</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.ja.md">日本語</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.ko.md">한국어</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.es.md">Español</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.fr.md">Français</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.de.md">Deutsch</a> · <strong>Português</strong> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.ru.md">Русский</a></p>

*Esta é uma tradução do README em inglês, que é a versão de referência e pode estar mais atualizada.*

O personagent é um personagem para seus grupos de chat: escolha um pronto ou escreva o seu, e rode em qualquer modelo compatível com OpenAI. Comece conversando com ele no navegador e depois leve para o QQ, WeChat, Telegram, Discord e mais uma dúzia de apps pela mesma página local.

<p align="center">
  <img src="https://raw.githubusercontent.com/wangkant/personagent/main/docs/welcome.jpg" alt="A tela Conectar apps da página local, com todas as plataformas em que ele pode entrar" width="960">
</p>

<p align="center"><em>Conectar apps, na mesma página local da configuração e da conversa com o personagem.</em></p>

## Por que o personagent

<table>
<tr>
<td width="220" valign="top"><strong>Ele sabe quando ficar quieto.</strong></td>
<td valign="top">
Responde quando é chamado. Fora isso, um modelo avalia se uma pessoa entraria na conversa.<br>
Uma rajada de mensagens recebe uma única resposta.
</td>
</tr>
<tr>
<td width="220" valign="top"><strong>Ele aprende com correções que se sustentam.</strong></td>
<td valign="top">
O que uma correção ensina, como o nome que o grupo dá para a academia, vale para todas as respostas seguintes naquela conversa.<br>
Uma mudança precisa de duas reações concordantes da mesma conversa, uma delas forte.<br>
Um troll ou alguém de fora não consegue retreiná-lo.<br>
Toda mudança fica registrada, e qualquer uma pode ser desfeita.
</td>
</tr>
<tr>
<td width="220" valign="top"><strong>É fácil de começar e fica onde seu grupo está.</strong></td>
<td valign="top">
Um comando abre uma página local no navegador, em inglês, chinês ou mais oito idiomas.<br>
Cole uma chave de modelo para conversar: dez serviços de modelo já vêm pré-configurados, e qualquer outro compatível com OpenAI funciona.<br>
Conecte um app escaneando com o celular ou colando um ou dois valores. A visão Atividade mostra o que o personagem fez por lá.
</td>
</tr>
<tr>
<td width="220" valign="top"><strong>Pode ser um personagem pronto ou o seu.</strong></td>
<td valign="top">
Sete personalidades prontas. Três são personagens que a comunidade já desenha, a garota-baleia do DeepSeek, a garota-dragão do GPT e a senhorita Claude, com retratos que piscam, pensam enquanto a resposta está a caminho e falam quando ela chega.<br>
Reescreva a persona quando quiser. O que o personagem aprendeu é mantido.
</td>
</tr>
</table>

- Cada conversa tem sua própria memória, e ele esquece quando pedem: `Nova, remember Sam is vegetarian`, `Nova, forget vegetarian`, `Nova, what do you remember` ([comandos de memória](https://github.com/wangkant/personagent/blob/main/docs/guide.pt-BR.md#comandos-de-memória)). O que um grupo anotou sobre alguém acompanha essa pessoa na conversa privada com ele, e nunca o contrário.
- Ele responde no idioma da conversa. As personas iniciais existem em cada um dos dez idiomas da página; os exemplos, filtros e prompts embutidos são em inglês e chinês.
- Ele é medido: `personagent eval` avalia quando ele fala, se continua no personagem e se as correções pegam ([resultados](https://github.com/wangkant/personagent#measured)).

## Comece aqui

```sh
python -m pip install personagent
personagent
```

Com o [uv](https://docs.astral.sh/uv/), `uvx personagent` roda sem uma etapa de instalação separada. No Windows, você também pode baixar o ZIP do código-fonte e dar dois cliques em `start.bat`. O personagent é testado no Linux com Python 3.10–3.14 e no Windows com Python 3.12.

O navegador abre numa página local. Cole uma chave de API de modelo e clique em **Verificar e começar a conversar**; uma pequena solicitação confere a chave. Ainda não tem chave? Os modelos gratuitos do OpenRouter já vêm selecionados, e a chave deles não custa nada. Para ver como é antes de conseguir qualquer chave, `personagent demo` mostra três cenas roteirizadas de graça. O [guia de primeiros passos](https://github.com/wangkant/personagent/blob/main/docs/start.pt-BR.md) percorre a página tela por tela.

## Quanto custa

O personagent é gratuito. Você paga o serviço de modelo que escolher, pelos preços dele.

- **De graça para começar.** Os modelos gratuitos do OpenRouter permitem 50 solicitações por dia; o modelo pode mudar de uma solicitação para outra, e alguns provedores gratuitos guardam o que recebem. O `glm-4.7-flash` da Zhipu também é gratuito, e o Ollama roda um modelo no seu próprio computador, sem chave.
- **O que chama o modelo.** Cada resposta e duas etapas menores: decidir se entra na conversa quando ninguém chamou e avaliar como as pessoas reagem às respostas dele. `personagent doctor` e `personagent eval` também enviam solicitações; o [guia de implantação](https://github.com/wangkant/personagent/blob/main/docs/deploy.pt-BR.md#custos) traz o resto.
- **O que nunca chama.** `personagent demo` e os comandos de memória.

## Coloque no seu grupo

Abra **Conectar apps** na página local. Os apps ficam agrupados assim:

| Na página | Apps | O que você precisa |
|---|---|---|
| Escanear para conectar | QQ, WeChat pessoal | Seu celular. Bots do WeChat só têm conversas privadas |
| Colar um ou dois valores | Telegram, Discord, KOOK, Feishu/Lark, DingTalk, Slack, bot de IA do WeCom, Mattermost, Misskey | Valores do console do app; a página diz quais |
| Avançado | App do WeCom, Conta Oficial do WeChat, webhook do QQ, OneBot v11 (NapCat), Satori | Um endereço público ou outro software neste computador |

As credenciais são verificadas antes de serem salvas, e os apps conectados voltam a iniciar sempre que o personagent inicia. O personagent conecta por conta própria os apps de escanear, o Telegram e o Discord; o resto passa por um [AstrBot](https://github.com/AstrBotDevs/AstrBot) que ele baixa e roda em segundo plano, sem mais nada para abrir. Num servidor, `personagent up` inicia o personagem e todos os apps conectados sem navegador. A configuração de cada app está no [guia do usuário](https://github.com/wangkant/personagent/blob/main/docs/guide.pt-BR.md#coloque-em-um-chat), e o QQ do zero, passo a passo, no [guia de implantação em chinês](https://github.com/wangkant/personagent/blob/main/docs/deploy.zh-CN.md).

Já tem uma ponte rodando?

- **AstrBot**: `personagent connect astrbot` instala o plugin e o token compartilhado. O [guia](https://github.com/wangkant/personagent/blob/main/docs/guide.pt-BR.md#pontes-que-você-mesmo-executa) explica o que fazer quando ele está em outra máquina.
- **[Koishi](https://koishi.chat)**, ou qualquer servidor Satori: o [conector Satori](https://github.com/wangkant/personagent/blob/main/integrations/satori/README.pt-BR.md).
- **[Matrix](https://matrix.org)**, com WhatsApp e Signal por trás de pontes mautrix: o [conector Matrix](https://github.com/wangkant/personagent/blob/main/integrations/matrix/README.pt-BR.md).

## Agentes de programação

**Deixe um deles configurar.** Passe a linha abaixo para um agente de programação que consiga rodar comandos no seu computador. Ele pergunta o que você quer, instala o personagent e inicia a página local. Você mesmo cola sua chave de modelo nessa página, então a chave nunca passa pelo agente.

```text
Leia https://raw.githubusercontent.com/wangkant/personagent/main/docs/setup-for-agents.md e configure o personagent para mim.
```

**Fale com seu personagem enquanto trabalha.** Com a chave de modelo configurada, o Claude Code, o Codex e o DeepSeek Harness (`dsh`) conseguem falar com o personagem:

```bash
personagent connect claude-code
personagent connect codex
personagent connect dsh
```

Abra uma sessão nova lá (reinicie o DeepSeek Harness antes) e peça para ele dizer algo ao seu personagem. É o mesmo chat privado e a mesma memória da página local. No Claude Code e no Codex, `--react` deixa o personagem dizer uma frase quando um turno termina. `--remove` tira tudo de novo. O [guia](https://github.com/wangkant/personagent/blob/main/docs/guide.pt-BR.md#agentes-de-código) cobre as permissões, o que `--react` envia ao seu serviço de modelo e outras ferramentas MCP.

## Medições

`personagent eval` conduz o agente real por momentos de conversa rotulados. A rodada mais recente, em 2026-10-18, foi medida na versão 1.3.0: o personagem padrão em dois modelos via OpenRouter, cada caso testado três vezes, com o Claude Opus 5.5 como juiz às cegas. Inglês / chinês:

| | deepseek-v4.1-flash | gpt-6-luna |
|---|---|---|
| Acerta quando falar (60 momentos) | 83% / 80% | 93% / 91% |
| Interpreta o personagem melhor que o mesmo modelo só com o prompt dele (40 momentos) | 63% / 58% | 75% / 53% |
| Usa o que uma correção ensinou numa mensagem posterior, escrita de outro jeito | 76% / 56% | 71% / 67% |

- Ele raramente ignora uma mensagem dirigida a ele. A maioria das falhas é o nome dele usado para outra coisa, como um cinema ou um filhote.
- Nenhuma das 84 correções de trolls, de pessoas de fora ou de quem saiu da conversa passou.

Os [resultados completos](https://github.com/wangkant/personagent/tree/main/docs/evals/2026-10-18) trazem os intervalos, as falhas por tipo, o método e todos os relatórios.

## Como ele se compara

Projetos com que ele costuma ser comparado, em novembro de 2026:

- **AstrBot** (AGPL-3.0) é um framework de bots para mais de uma dúzia de plataformas, com WebUI e um grande mercado de plugins. Ele pode responder ao acaso sem ser chamado (10% das vezes, desativado por padrão) e deixa o aprendizado para plugins.
- **MaiBot** (GPL-3.0) é um bot de personagem para QQ, via NapCat, com WebUI e um inicializador de um clique. Um modelo planejador decide com que frequência ele fala, e ele pega expressões e gírias da conversa.
- **O plugin de personagem do ChatLuna** para Koishi (AGPL-3.0) entra na conversa por regras: um intervalo fixo, o movimento da conversa ou há quanto tempo ela está parada.
- **ElizaOS** (MIT) é um framework de agentes em TypeScript para Discord, Telegram, Slack e outros, em que um modelo decide se responde.

O que o personagent traz embutido: ele aprende com a forma como as pessoas reagem às respostas dele (correções, rejeições, novas tentativas que elas aceitaram), mantém um registro de cada mudança com um jeito de desfazê-la e publica uma avaliação de como se comporta.

Onde eles estão à frente: apps de desktop com todas as configurações numa WebUI, grandes ecossistemas de plugins, e gírias, pacotes de figurinhas e memória de imagens. Se você já usa AstrBot ou Koishi, não precisa escolher: o personagent pode rodar por trás de qualquer um deles como o personagem.

## Atualizar e desinstalar

Quando há uma versão mais nova no PyPI, a página mostra um aviso com o comando de atualização para o jeito como você instalou. Com pip, é `python -m pip install -U personagent`. A pasta principal continua a mesma: configurações, personagem, o que ele aprendeu e apps conectados.

Para remover, primeiro tire o personagent de qualquer agente de programação que você conectou (`personagent connect claude-code --remove`, ou o mesmo com `codex` ou `dsh`). Depois feche o personagent e rode `python -m pip uninstall personagent`. Por fim, apague a pasta principal, que é `~/personagent` numa instalação pelo PyPI, a menos que você tenha escolhido outra: ela guarda sua chave, o personagem e tudo o que ele aprendeu, então não dá para desfazer. Os [passos completos](https://github.com/wangkant/personagent/blob/main/docs/setup-for-agents.md#undoing-it) (em inglês) cobrem uv, pipx e o que revogar.

## Privacidade

Tudo o que o personagent guarda fica na sua máquina, numa única pasta principal: `.env` com suas chaves, `persona.txt`, `runtime/` e `platforms/` com o AstrBot gerenciado e as credenciais das conexões diretas. O provedor de modelo que você escolher vê as conversas que ele responde, e uma vez por dia o personagent pergunta ao pypi.org se há uma versão mais nova (`UPDATE_CHECK_ENABLED=false` desativa isso). Antes de conectá-lo a pessoas reais, avise que é um bot e peça o consentimento delas; o [guia](https://github.com/wangkant/personagent/blob/main/docs/guide.pt-BR.md#privacidade-e-consentimento) lista o que vai para onde.

## Documentação

- [Guia do usuário](https://github.com/wangkant/personagent/blob/main/docs/guide.pt-BR.md): instalação, configuração, a conversa no terminal, conectores, como ensiná-lo, a visão Atividade, solução de problemas.
- [Guia de implantação](https://github.com/wangkant/personagent/blob/main/docs/deploy.pt-BR.md): rodar para valer: conectores, QQ, exposição dos endpoints, custos e o que verificar quando o bot fica em silêncio.
- [Protocolo de conectores](https://github.com/wangkant/personagent/blob/main/docs/connectors.pt-BR.md): uma requisição HTTP assinada por mensagem, para escrever seu próprio conector.
- [Ferramentas](https://github.com/wangkant/personagent/blob/main/docs/tools.pt-BR.md): os scripts em `tools/`, para rodar a partir de um clone.
- [Changelog](https://github.com/wangkant/personagent/blob/main/CHANGELOG.md) · [Como contribuir](https://github.com/wangkant/personagent/blob/main/.github/CONTRIBUTING.md) · [Política de segurança](https://github.com/wangkant/personagent/blob/main/.github/SECURITY.md) · [Aviso legal](https://github.com/wangkant/personagent/blob/main/docs/DISCLAIMER.pt-BR.md)

## Licença

O código é [MIT](https://github.com/wangkant/personagent/blob/main/LICENSE) © 2026 Qiankang (Kant) Wang. Os três retratos dos personagens são licenciados sob CC BY-NC-SA 4.0, com os créditos em [persona_agent/static/characters/LICENSE.md](https://github.com/wangkant/personagent/blob/main/persona_agent/static/characters/LICENSE.md).

## Agradecimentos

- As outras plataformas de chat são alcançadas pelo [AstrBot](https://github.com/AstrBotDevs/AstrBot), [NapCat](https://github.com/NapNeko/NapCatQQ), [Koishi](https://koishi.chat) com [satori-python](https://github.com/RF-Tar-Railt/satori-python) e [matrix-nio](https://github.com/matrix-nio/matrix-nio) com as [pontes mautrix](https://docs.mau.fi/bridges/); a conexão com o WeChat segue as [notas de protocolo do openclaw-weixin](https://github.com/Tencent/openclaw-weixin/blob/main/docs/protocol.md) da Tencent.
- O aprendizado a partir de reações se baseia em [Self-Feeding Chatbot](https://arxiv.org/abs/1901.05415), [Alexa self-learning](https://arxiv.org/abs/1911.02557) e [BlenderBot 3x](https://arxiv.org/abs/2306.04707); o lorebook segue o World Info do [SillyTavern](https://github.com/SillyTavern/SillyTavern).
