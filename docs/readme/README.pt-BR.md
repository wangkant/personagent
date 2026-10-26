<p align="center">
  <img src="https://raw.githubusercontent.com/wangkant/personagent/main/assets/personagent-cover.webp" alt="personagent: conversas ilustradas" width="100%">
</p>

<h3 align="center">Um personagem para seus grupos de chat que sabe quando ficar quieto e aprende quando é corrigido.</h3>

<p align="center">
  <a href="https://pypi.org/project/personagent/"><img src="https://img.shields.io/pypi/v/personagent?color=3776AB&label=PyPI&cacheSeconds=3600" alt="PyPI"></a>
  <a href="https://github.com/wangkant/personagent/actions/workflows/ci.yml"><img src="https://github.com/wangkant/personagent/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/Python-3.10%E2%80%933.14-3776AB?logo=python&logoColor=white" alt="Python 3.10–3.14"></a>
  <a href="https://github.com/wangkant/personagent/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-2f855a.svg" alt="Licença: MIT"></a>
</p>

<p align="center"><a href="https://github.com/wangkant/personagent/blob/main/README.md">English</a> · <a href="https://github.com/wangkant/personagent/blob/main/README.zh-CN.md">简体中文</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.zh-TW.md">繁體中文</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.ja.md">日本語</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.ko.md">한국어</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.es.md">Español</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.fr.md">Français</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.de.md">Deutsch</a> · <strong>Português</strong> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.ru.md">Русский</a></p>

*Esta é uma tradução do README em inglês, que é a versão de referência e pode estar mais atualizada. Os guias indicados aqui estão em inglês.*

O personagent é um personagem para seus grupos de chat: escolha um pronto ou escreva o seu, e rode em qualquer modelo compatível com OpenAI. Ele se conecta sozinho ao QQ, WeChat, Telegram e Discord, e ao KOOK, Feishu, DingTalk, Slack, WeCom, Mattermost e Misskey pela mesma página.

Comece numa conversa local no navegador: adicione uma chave de modelo e diga oi. Quando quiser o personagem num grupo, conecte um app escaneando com o celular ou colando um ou dois valores.

<p align="center">
  <img src="https://raw.githubusercontent.com/wangkant/personagent/main/docs/welcome.jpg" alt="A tela Conectar apps da página local, com todas as plataformas em que ele pode entrar" width="960">
</p>

<p align="center"><em>Conectar apps, na mesma página local da configuração e da conversa com o personagem. Captura de tela de uma instalação descartável com um modelo de teste local.</em></p>

## Comece aqui

Instale pelo PyPI e abra:

```sh
python -m pip install personagent
personagent
```

Com o [uv](https://docs.astral.sh/uv/), `uvx personagent` roda sem uma etapa de instalação separada.

O navegador abre uma página local com três visões: **Conversa**, **Conectar apps** e **Personagem e configurações**. Cole sua chave de API do modelo e clique em **Verificar e começar a conversar →**; uma pequena solicitação confere a chave. Há 10 serviços de modelo pré-configurados, além de qualquer outro compatível com OpenAI, e opções prontas de nome e personalidade para o personagem. A caixa **Persona** guarda o `persona.txt`; salvar reinicia o agente e mantém o que ele aprendeu. **Mais recursos** ativa busca na web, compreensão de imagens e falar primeiro. Rodar `personagent` de novo reaproveita uma página que já está aberta. O menu no canto superior direito mostra a página em inglês, chinês ou mais oito idiomas. Os prompts embutidos do personagem são em inglês ou chinês; se ele responde em outro idioma depende do modelo.

No Windows, você também pode baixar o ZIP do código-fonte e dar dois cliques em `start.bat`. Python 3.10–3.14. Veja o [guia rápido de primeiros passos](https://github.com/wangkant/personagent/blob/main/docs/start.md); comandos de terminal e conectores estão no [guia completo](https://github.com/wangkant/personagent/blob/main/docs/guide.md).

## Deixe seu agente de programação configurar

Um agente de programação que consiga rodar comandos no seu computador pode instalar e configurar o personagent para você. Passe isto para ele:

```text
Leia https://raw.githubusercontent.com/wangkant/personagent/main/docs/setup-for-agents.md e configure o personagent para mim.
```

Ele pergunta o idioma, o nome e a personalidade do personagem, seu serviço de modelo e os apps de chat que você quer; depois instala o personagent, cria a pasta principal e inicia a página local. Você mesmo cola sua chave de modelo nessa página, então a chave nunca passa pelo agente. As [instruções que ele segue](https://github.com/wangkant/personagent/blob/main/docs/setup-for-agents.md) são Markdown simples que você também pode ler.

## Por que o personagent

<table>
<tr>
<td width="220" valign="top"><img src="https://raw.githubusercontent.com/wangkant/personagent/main/persona_agent/static/listening.webp" alt="" width="220"></td>
<td valign="top">
<strong>Ele sabe quando ficar quieto.</strong><br>
Responde quando é chamado. Fora isso, um modelo avalia se uma pessoa entraria na conversa: nada de sorteio.<br>
Uma rajada de mensagens recebe uma resposta, não uma para cada.
</td>
</tr>
<tr>
<td width="220" valign="top"><img src="https://raw.githubusercontent.com/wangkant/personagent/main/persona_agent/static/learned-notebook.webp" alt="" width="220"></td>
<td valign="top">
<strong>Ele aprende com correções que se sustentam.</strong><br>
O que uma correção ensina, como o nome que o grupo dá para a academia, vale para todas as respostas seguintes naquela conversa.<br>
Uma mudança precisa de duas reações concordantes da mesma conversa, uma delas forte.<br>
Um troll ou alguém de fora não consegue retreiná-lo.<br>
Toda mudança fica registrada, e qualquer uma pode ser desfeita.
</td>
</tr>
<tr>
<td width="220" valign="top"><img src="https://raw.githubusercontent.com/wangkant/personagent/main/persona_agent/static/empty-chats.webp" alt="" width="220"></td>
<td valign="top">
<strong>É fácil de começar e fica onde seu grupo está.</strong><br>
Configuração e conversa no navegador em inglês, chinês ou mais oito idiomas, com 11 serviços de modelo e configurações avançadas opcionais.<br>
Entra sozinho no QQ, WeChat, Telegram e Discord e em mais uma dúzia de apps pela mesma página; a visão Atividade mostra o que ele fez.
</td>
</tr>
</table>

- Cada conversa tem sua própria memória.
- Editar o personagem mantém o que ele aprendeu.
- Ele é medido: `personagent eval` avalia quando ele fala, se continua no personagem e se as correções pegam ([resultados](https://github.com/wangkant/personagent#measured)).

## Coloque no seu grupo

Abra **Conectar apps** na página local. Os apps ficam agrupados assim:

| Na página | Apps | O que você precisa |
|---|---|---|
| Escanear para conectar | QQ, WeChat pessoal | Seu celular. Bots do WeChat só têm conversas privadas |
| Colar um ou dois valores | Telegram, Discord, KOOK, Feishu/Lark, DingTalk, Slack, bot de IA do WeCom, Mattermost, Misskey | Valores do console do app; a página diz quais |
| Avançado | App do WeCom, Conta Oficial do WeChat, webhook do QQ, OneBot v11 (NapCat), Satori | Um endereço público ou outro software neste computador |

As credenciais são verificadas antes de serem salvas, e os apps conectados voltam a iniciar sempre que o personagent inicia. O personagent conecta o QQ, WeChat, Telegram e Discord por conta própria; o resto passa por um [AstrBot](https://github.com/AstrBotDevs/AstrBot) que ele baixa e roda em segundo plano, sem mais nada para abrir. Num servidor, `personagent up` inicia o personagem e todos os apps conectados sem navegador.

**Já usa AstrBot, Koishi ou Matrix?** Para um AstrBot neste computador, `personagent connect astrbot` instala o plugin e o token compartilhado. Para um em outra máquina, envie o `astrbot_plugin_personagent.zip` da [versão mais recente](https://github.com/wangkant/personagent/releases/latest) em **Install from File** na página de plugins dele e depois configure o token e o endereço HTTPS do personagent como os guias abaixo descrevem. O [Koishi](https://koishi.chat) entra pelo [conector Satori](https://github.com/wangkant/personagent/blob/main/integrations/satori/README.md), e o [Matrix](https://matrix.org), com WhatsApp e Signal por trás de pontes mautrix, pelo [conector Matrix](https://github.com/wangkant/personagent/blob/main/integrations/matrix/README.md).

A configuração de cada um está no [guia do usuário](https://github.com/wangkant/personagent/blob/main/docs/guide.md#put-it-in-a-chat) e no [guia de implantação](https://github.com/wangkant/personagent/blob/main/docs/deploy.md); o [guia passo a passo em chinês](https://github.com/wangkant/personagent/blob/main/docs/deploy.zh-CN.md) cobre o QQ do zero.

## Como ele se compara

Os projetos com que as pessoas costumam compará-lo, segundo a documentação de cada um em outubro de 2026:

- **AstrBot** (AGPL-3.0) é um framework de bots para mais de 18 plataformas, com WebUI e um grande mercado de plugins. Ele pode responder ao acaso sem ser chamado (10% das vezes, desativado por padrão) e deixa o aprendizado para plugins.
- **MaiBot** (GPL-3.0) é um bot de personagem para QQ, via NapCat, com WebUI e um inicializador de um clique. Um modelo planejador decide com que frequência ele fala, e ele pega expressões e gírias da conversa.
- **O plugin de personagem do ChatLuna** para Koishi (AGPL-3.0) entra na conversa por regras: um intervalo fixo, o movimento da conversa ou há quanto tempo ela está parada.
- **ElizaOS** (MIT) é um framework de agentes em TypeScript para Discord, Telegram, Slack e outros, em que um modelo decide se responde.

O que o personagent traz embutido, onde os outros deixam para plugins ou não descrevem: ele aprende com a forma como as pessoas reagem às respostas dele (correções, rejeições, novas tentativas que elas aceitaram); uma mudança precisa de duas reações concordantes da mesma conversa, uma delas forte; toda mudança é registrada e pode ser desfeita; e o comportamento dele é medido numa avaliação publicada ([abaixo](https://github.com/wangkant/personagent#measured)).

Onde eles estão à frente: apps de desktop com todas as configurações numa WebUI, grandes ecossistemas de plugins, e gírias, pacotes de figurinhas e memória de imagens. Se você já usa AstrBot ou Koishi, não precisa escolher: o personagent pode rodar por trás de qualquer um deles como o personagem.

## Medições

`personagent eval` conduz o agente real por momentos de conversa rotulados. A rodada mais recente, em 2026-10-18, colocou o personagem padrão em dois modelos via OpenRouter, testou cada caso três vezes e teve o Claude Opus 5.5 como juiz às cegas. Inglês / chinês:

| | deepseek-v4.1-flash | gpt-6-luna |
|---|---|---|
| Acerta quando falar (60 momentos) | 83% / 80% | 93% / 91% |
| Interpreta o personagem melhor que o mesmo modelo só com o prompt dele (40 momentos) | 63% / 58% | 75% / 53% |
| Usa o que uma correção ensinou numa mensagem posterior, escrita de outro jeito | 76% / 56% | 71% / 67% |

- Ele raramente ignora uma mensagem dirigida a ele. A maioria das falhas é o nome dele usado para outra coisa, como um cinema ou um filhote.
- Em chinês, a vantagem dele sobre o prompt simples fica dentro do ruído.
- Antes de as correções manterem a lição, o que foi corrigido depois da primeira rodada daquele dia, só 2 de 58 mensagens posteriores a usavam.
- Nenhuma correção de troll, de alguém de fora ou de quem saiu da conversa passou, em 84 tentativas.

Os [resultados completos](https://github.com/wangkant/personagent/tree/main/docs/evals/2026-10-18) trazem os intervalos, as falhas por tipo, o método, o que os números não mostram e todos os relatórios.

## Documentação

- [Guia do usuário](https://github.com/wangkant/personagent/blob/main/docs/guide.md) ([中文](https://github.com/wangkant/personagent/blob/main/docs/guide.zh-CN.md)): instalação, configuração, a conversa no terminal, conectores, como ensiná-lo, a visão Atividade, solução de problemas.
- [Guia de implantação](https://github.com/wangkant/personagent/blob/main/docs/deploy.md): rodar para valer: conectores, QQ, exposição dos endpoints, custos e o que verificar quando o bot fica em silêncio.
- [中文部署教程](https://github.com/wangkant/personagent/blob/main/docs/deploy.zh-CN.md): QQ do zero, passo a passo (em chinês).
- [Protocolo de conectores](https://github.com/wangkant/personagent/blob/main/docs/connectors.md): uma requisição HTTP assinada por mensagem, para escrever seu próprio conector.
- [Ferramentas](https://github.com/wangkant/personagent/blob/main/docs/tools.md): os scripts em `tools/`, para rodar a partir de um clone.
- [Changelog](https://github.com/wangkant/personagent/blob/main/CHANGELOG.md), incluindo [como atualizar a partir da 0.4](https://github.com/wangkant/personagent/blob/main/CHANGELOG.md#upgrading-from-04).
- [Como contribuir](https://github.com/wangkant/personagent/blob/main/.github/CONTRIBUTING.md) · [Política de segurança](https://github.com/wangkant/personagent/blob/main/.github/SECURITY.md) · [Aviso legal](https://github.com/wangkant/personagent/blob/main/docs/DISCLAIMER.md)

## Privacidade

Tudo o que o personagent guarda fica na sua máquina, numa única pasta principal: `.env` com suas chaves, `persona.txt`, `runtime/` e `platforms/` com o AstrBot gerenciado e as credenciais das conexões diretas. O provedor de modelo que você escolher vê, sim, as conversas que ele responde, e uma vez por dia o personagent pergunta ao pypi.org se há uma versão mais nova (`UPDATE_CHECK_ENABLED=false` desativa isso). Antes de conectá-lo a pessoas reais, avise que é um bot e peça o consentimento delas; o [guia](https://github.com/wangkant/personagent/blob/main/docs/guide.md#privacy-and-consent) lista exatamente o que vai para onde.

## Status

A 1.3.0 está no PyPI, lançada em 2026-10-18. O QQ é a plataforma mais testada na prática, via AstrBot na 1.0 e diretamente desde a 1.1. As conexões com WeChat, Telegram e Discord verificam as credenciais nos serviços reais antes de salvar e, fora isso, são testadas com substitutos; os conectores Satori e Matrix são testados com substitutos. O CI roda os testes no Linux com Python 3.10–3.14 e no Windows com Python 3.12, além de jobs que instalam o pacote e exercitam o comando e a página local.

## Licença

[MIT](https://github.com/wangkant/personagent/blob/main/LICENSE) © 2026 Qiankang (Kant) Wang.

## Agradecimentos

- As outras plataformas de chat são alcançadas pelo [AstrBot](https://github.com/AstrBotDevs/AstrBot), [NapCat](https://github.com/NapNeko/NapCatQQ), [Koishi](https://koishi.chat) com [satori-python](https://github.com/RF-Tar-Railt/satori-python) e [matrix-nio](https://github.com/matrix-nio/matrix-nio) com as [pontes mautrix](https://docs.mau.fi/bridges/); a conexão com o WeChat segue as [notas de protocolo do openclaw-weixin](https://github.com/Tencent/openclaw-weixin/blob/main/docs/protocol.md) da Tencent.
- O aprendizado a partir de reações se baseia em [Self-Feeding Chatbot](https://arxiv.org/abs/1901.05415), [Alexa self-learning](https://arxiv.org/abs/1911.02557) e [BlenderBot 3x](https://arxiv.org/abs/2306.04707); o lorebook segue o World Info do [SillyTavern](https://github.com/SillyTavern/SillyTavern).
