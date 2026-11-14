<p align="center">
  <img src="https://raw.githubusercontent.com/wangkant/personagent/main/assets/personagent-cover.webp" alt="personagent" width="100%">
</p>

<h3 align="center">Um agente que se comporta como uma pessoa, em todas as plataformas que você usa.<br>Tem personalidade própria, lembra, aprende com as pessoas com quem conversa e decide por conta própria quando falar.</h3>

<p align="center">
  <a href="https://pypi.org/project/personagent/"><img src="https://img.shields.io/pypi/v/personagent?style=flat-square&label=PyPI&labelColor=24292f&color=0969da&cacheSeconds=3600" alt="PyPI"></a>
  <a href="https://github.com/wangkant/personagent/actions/workflows/ci.yml"><img src="https://img.shields.io/github/actions/workflow/status/wangkant/personagent/ci.yml?branch=main&style=flat-square&label=CI&labelColor=24292f" alt="CI"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/Python-3.10%E2%80%933.14-0969da?style=flat-square&labelColor=24292f" alt="Python 3.10–3.14"></a>
  <a href="https://github.com/wangkant/personagent/blob/main/LICENSE"><img src="https://img.shields.io/badge/License-PolyForm%20Noncommercial-0969da?style=flat-square&labelColor=24292f" alt="Licença: PolyForm Noncommercial"></a>
</p>

<p align="center"><a href="https://github.com/wangkant/personagent/blob/main/README.md">English</a> · <a href="https://github.com/wangkant/personagent/blob/main/README.zh-CN.md">简体中文</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.zh-TW.md">繁體中文</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.ja.md">日本語</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.ko.md">한국어</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.es.md">Español</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.fr.md">Français</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.de.md">Deutsch</a> · <strong>Português</strong> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.ru.md">Русский</a></p>

*Esta é uma tradução do README em inglês, que é a versão de referência e pode estar mais atualizada.*

O personagent é um agente que se comporta como uma pessoa: tem personalidade própria, lembra, aprende com as pessoas com quem conversa e decide por conta própria quando falar. Ele funciona onde você precisar: em conversas em grupo e conversas privadas no QQ, no WeChat, no Telegram, no Discord e em outras dezoito plataformas, em uma janela no seu computador e dentro de assistentes de programação como o Claude Code e o Codex. Você escolhe ou escreve a personalidade dele, e ele funciona com qualquer modelo compatível com OpenAI.

<p align="center">
  <img src="https://raw.githubusercontent.com/wangkant/personagent/main/docs/welcome.jpg" alt="A tela Conectar plataformas da página local: as plataformas que se conectam com QR code ou colando alguns valores, as plataformas avançadas recolhidas e os assistentes de programação em que ele pode entrar" width="960">
</p>

<p align="center"><em>Conectar plataformas, na mesma página local da configuração e da conversa com o personagem.</em></p>

## Por que o personagent

<table>
<tr>
<td width="220" valign="top"><strong>Ele tem personalidade própria.</strong></td>
<td valign="top">
Sete personalidades prontas. Três são personagens que a comunidade já desenha: a garota-baleia do DeepSeek, a garota-dragão do GPT e a senhorita Claude, com retratos que piscam, pensam e falam.<br>
Reescreva a persona quando quiser. O que o personagem aprendeu é mantido.
</td>
</tr>
<tr>
<td width="220" valign="top"><strong>Ele fala como uma pessoa.</strong></td>
<td valign="top">
Ele escreve como as pessoas escrevem em um chat: frases curtas e simples no idioma da conversa, sem listas, títulos nem frases de assistente, e diz que não sabe quando não sabe.<br>
Na maioria das plataformas, a resposta chega em algumas mensagens curtas, com uma pausa de digitação entre elas; o Telegram, o Discord e o Matrix também mostram o indicador de digitação.<br>
Ele guarda as figurinhas que as pessoas enviam e as usa quando combinam, e de madrugada quase não participa, a menos que seja chamado.<br>
Se você ativar, ele inicia uma conversa depois de um longo silêncio e retoma os planos que as pessoas mencionaram.
</td>
</tr>
<tr>
<td width="220" valign="top"><strong>Ele lembra.</strong></td>
<td valign="top">
Cada conversa tem sua própria memória: mensagens recentes que sobrevivem a um reinício, um resumo da conversa anterior, eventos datados e fatos sobre as pessoas, que ele mantém atualizados por conta própria.<br>
Tudo o que ele lembra aparece na visão Atividade, onde qualquer item pode ser esquecido ou trazido de volta.
</td>
</tr>
<tr>
<td width="220" valign="top"><strong>Ele aprende com correções que se sustentam.</strong></td>
<td valign="top">
O que uma correção ensina, como o nome que o grupo dá para a academia, vale para todas as respostas seguintes naquela conversa.<br>
Um troll ou alguém de fora não consegue retreiná-lo.<br>
Quando as reações não conseguem resolver uma mudança, ele mesmo decide e registra o motivo; ninguém precisa aprovar nada.<br>
Toda mudança fica registrada, e qualquer uma pode ser desfeita.
</td>
</tr>
<tr>
<td width="220" valign="top"><strong>Ele sabe quando ficar quieto.</strong></td>
<td valign="top">
Em um grupo, responde quando é chamado. Fora isso, um modelo avalia se uma pessoa entraria na conversa.<br>
Uma rajada de mensagens recebe uma única resposta.
</td>
</tr>
<tr>
<td width="220" valign="top"><strong>Ele se conecta a todas as suas plataformas.</strong></td>
<td valign="top">
Vinte e duas plataformas de chat se conectam por uma única página, lendo um QR code com o celular ou colando alguns valores. A maioria aceita tanto conversas em grupo quanto conversas privadas.<br>
O mesmo agente responde em uma janela no seu computador e dentro do Claude Code, do Codex e do DeepSeek Harness.<br>
Qualquer outra plataforma pode ser adicionada por meio de uma ponte AstrBot, Koishi ou Matrix, ou de um conector que você mesmo escreva.
</td>
</tr>
<tr>
<td width="220" valign="top"><strong>Ele funciona com o que você já tem.</strong></td>
<td valign="top">
Qualquer modelo compatível com OpenAI: os modelos gratuitos do OpenRouter, um serviço pago ou um modelo executado no seu próprio computador com o Ollama.<br>
Um comando o abre, em inglês, chinês ou mais oito idiomas, e basta colar uma chave de modelo para começar a conversar.
</td>
</tr>
</table>

Ele também lembra e esquece o que lhe for solicitado no chat: `Nova, remember Sam is vegetarian`, `Nova, forget vegetarian` ([comandos de memória](https://github.com/wangkant/personagent/blob/main/docs/guide.pt-BR.md#comandos-de-memória)). O que ele guarda, e por quanto tempo, está na seção [memória](https://github.com/wangkant/personagent/blob/main/docs/guide.pt-BR.md#memória) do guia.

## Comece aqui

```sh
python -m pip install personagent
personagent
```

Com o [uv](https://docs.astral.sh/uv/), `uvx personagent` o executa sem uma etapa de instalação separada. No Windows, você também pode baixar o ZIP do código-fonte e dar dois cliques em `start.bat`.

No Windows, ele abre em uma janela própria; no macOS e no Linux, no navegador. Cole uma chave de API de modelo e clique em **Verificar e iniciar a conversa**. Caso ainda não tenha uma chave, os modelos gratuitos do OpenRouter já vêm selecionados, e a chave deles é gratuita. `personagent demo` mostra três cenas roteirizadas sem chave nenhuma. O [guia de primeiros passos](https://github.com/wangkant/personagent/blob/main/docs/start.pt-BR.md) percorre a página tela por tela.

O personagent é gratuito. Você paga o serviço de modelo que escolher, pelos preços dele. Uma mensagem pode gerar mais de uma solicitação ao modelo: além da resposta, o personagem às vezes decide se fala em um grupo, avalia como uma resposta foi recebida ou organiza a própria memória. Os modelos gratuitos do OpenRouter permitem 50 solicitações por dia, e alguns provedores gratuitos guardam o que recebem; o Ollama executa um modelo no seu próprio computador, sem chave.

## Conecte suas plataformas

Abra **Conectar plataformas** na página local:

| Na página | Plataformas | O que é necessário |
|---|---|---|
| Conectar com QR code | QQ, WeChat pessoal | O seu celular. Os bots do WeChat só participam de conversas privadas |
| Colar alguns valores | Telegram, Discord, Matrix, Twitch, IRC, Zulip, VK, Stoat, KOOK, Feishu/Lark, DingTalk, Slack, Bot de IA do WeCom, Mattermost, Misskey | Valores do console da plataforma; a página indica quais |
| Avançado | Aplicativo do WeCom, Conta Oficial do WeChat, webhook do QQ, OneBot v11 (NapCat), Satori | Um endereço público ou outro software neste computador |

As plataformas conectadas são iniciadas novamente sempre que o personagent é iniciado. O personagent conecta por conta própria as plataformas com QR code, o Telegram, o Discord, o Matrix, o Twitch, o IRC, o Zulip, o VK e o Stoat; o resto passa por um [AstrBot](https://github.com/AstrBotDevs/AstrBot) que ele baixa e executa em segundo plano. Em um servidor sem monitor, `personagent connect <plataforma>` conecta qualquer uma dessas dez plataformas pelo terminal, com as mesmas etapas e verificações da página, e `personagent up` inicia tudo sem navegador. A configuração de cada plataforma está no [guia do usuário](https://github.com/wangkant/personagent/blob/main/docs/guide.pt-BR.md#coloque-em-um-chat), e o QQ do zero no [guia de implantação em chinês](https://github.com/wangkant/personagent/blob/main/docs/deploy.zh-CN.md).

Já usa AstrBot, Koishi ou Matrix? O personagent pode funcionar por trás de qualquer um deles como o agente: veja [pontes que você mesmo executa](https://github.com/wangkant/personagent/blob/main/docs/guide.pt-BR.md#pontes-que-você-mesmo-executa), o [conector Satori](https://github.com/wangkant/personagent/blob/main/integrations/satori/README.pt-BR.md) e o [conector Matrix](https://github.com/wangkant/personagent/blob/main/integrations/matrix/README.pt-BR.md).

## Assistentes de programação

**Configuração por um assistente.** Envie a linha abaixo a um assistente de programação capaz de executar comandos no seu computador. Você mesmo cola a chave de modelo na página local; assim, a chave nunca passa pelo assistente.

```text
Leia https://raw.githubusercontent.com/wangkant/personagent/main/docs/setup-for-agents.md e configure o personagent para mim.
```

**Fale com seu personagem enquanto trabalha.** O Claude Code, o Codex e o DeepSeek Harness (`dsh`) conseguem falar com o personagem, com o mesmo chat e a mesma memória da página local:

```bash
personagent connect claude-code
personagent connect codex
personagent connect dsh
```

`--remove` desfaz a conexão, e **Assistentes de programação**, em **Conectar plataformas**, faz as duas coisas pela página. O [guia](https://github.com/wangkant/personagent/blob/main/docs/guide.pt-BR.md#assistentes-de-programação) cobre as permissões e o `--react`, que deixa o personagem dizer uma frase quando um turno termina.

## Atualizar e desinstalar

Quando há uma versão mais nova no PyPI, a página mostra um aviso com o comando de atualização. Com pip, é `python -m pip install -U personagent`. Na maioria das instalações, **Atualizar e reabrir**, na visão **Aplicativo** da página, executa esse comando por você. As configurações, o personagem, o que ele aprendeu e as plataformas conectadas são mantidos. Para remover, siga [Remover o personagent](https://github.com/wangkant/personagent/blob/main/docs/guide.pt-BR.md#remover-o-personagent) no guia.

## Privacidade

Tudo o que o personagent guarda fica na sua máquina, em uma única pasta inicial. O provedor de modelo que você escolher vê as conversas que ele responde, e uma vez por dia o personagent pergunta ao pypi.org se há uma versão mais nova (`UPDATE_CHECK_ENABLED=false` desativa isso). Antes de conectá-lo a pessoas reais, avise que é um bot e peça o consentimento delas; o [guia](https://github.com/wangkant/personagent/blob/main/docs/guide.pt-BR.md#privacidade-e-consentimento) lista o que vai para onde.

## Documentação

- [Guia do usuário](https://github.com/wangkant/personagent/blob/main/docs/guide.pt-BR.md): configuração, conectores, como ensiná-lo, a visão Atividade, solução de problemas.
- [Guia de implantação](https://github.com/wangkant/personagent/blob/main/docs/deploy.pt-BR.md): execução em produção, custos e o que verificar quando o bot fica em silêncio.
- [Protocolo de conectores](https://github.com/wangkant/personagent/blob/main/docs/connectors.pt-BR.md): para escrever seu próprio conector.
- [Ferramentas](https://github.com/wangkant/personagent/blob/main/docs/tools.pt-BR.md): os scripts em `tools/`, para execução a partir de um clone.
- [Changelog](https://github.com/wangkant/personagent/blob/main/CHANGELOG.md) · [Como contribuir](https://github.com/wangkant/personagent/blob/main/.github/CONTRIBUTING.md) · [Política de segurança](https://github.com/wangkant/personagent/blob/main/.github/SECURITY.md) · [Aviso legal](https://github.com/wangkant/personagent/blob/main/docs/DISCLAIMER.pt-BR.md)

## Licença

O personagent é distribuído sob a [PolyForm Noncommercial License 1.0.0](https://github.com/wangkant/personagent/blob/main/LICENSE) © 2026 Qiankang (Kant) Wang: o uso, a modificação e o compartilhamento são gratuitos para fins não comerciais e não são permitidos para fins comerciais. Os conectores em `integrations/` continuam sob a licença MIT, assim como as versões até a 1.4.0. Os três retratos dos personagens são licenciados sob CC BY-NC-SA 4.0, com os créditos em [persona_agent/static/characters/LICENSE.md](https://github.com/wangkant/personagent/blob/main/persona_agent/static/characters/LICENSE.md).

## Agradecimentos

- As outras plataformas de chat são alcançadas pelo [AstrBot](https://github.com/AstrBotDevs/AstrBot), [NapCat](https://github.com/NapNeko/NapCatQQ), [Koishi](https://koishi.chat) com [satori-python](https://github.com/RF-Tar-Railt/satori-python) e [matrix-nio](https://github.com/matrix-nio/matrix-nio) com as [pontes mautrix](https://docs.mau.fi/bridges/); a conexão com o WeChat segue as [notas de protocolo do openclaw-weixin](https://github.com/Tencent/openclaw-weixin/blob/main/docs/protocol.md) da Tencent.
- O aprendizado a partir de reações se baseia em [Self-Feeding Chatbot](https://arxiv.org/abs/1901.05415), [Alexa self-learning](https://arxiv.org/abs/1911.02557) e [BlenderBot 3x](https://arxiv.org/abs/2306.04707); o lorebook segue o World Info do [SillyTavern](https://github.com/SillyTavern/SillyTavern).
