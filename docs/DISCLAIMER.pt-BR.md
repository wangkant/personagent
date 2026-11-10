# Aviso legal

[English](DISCLAIMER.md) · [简体中文](DISCLAIMER.zh-CN.md) · [繁體中文](DISCLAIMER.zh-TW.md) · [日本語](DISCLAIMER.ja.md) · [한국어](DISCLAIMER.ko.md) · [Español](DISCLAIMER.es.md) · [Français](DISCLAIMER.fr.md) · [Deutsch](DISCLAIMER.de.md) · Português (Brasil) · [Русский](DISCLAIMER.ru.md)

O personagent é distribuído sob a [PolyForm Noncommercial License 1.0.0](../LICENSE): o uso, a modificação e o compartilhamento são gratuitos para fins não comerciais e não são permitidos para fins comerciais. Ele coloca um personagem de IA nas suas conversas, e quem o executa é você. Você é responsável pelo que ele diz, por onde diz e por quais contas ele usa. Esta página não é aconselhamento jurídico.

## Plataformas de chat e suas contas

O personagent alcança uma plataforma de chat de duas formas. Ele conecta por conta própria dez plataformas: os bots oficiais do QQ, o WeChat pessoal, o Telegram, o Discord, o Matrix, a Twitch, o IRC, o Zulip, o VK e o Stoat. Qualquer outra plataforma passa por uma ponte de terceiros, normalmente o AstrBot que o personagent baixa e executa para você. Seu risco depende de como a conexão faz login.

- **APIs oficiais de bots** são feitas para bots. Elas incluem a API oficial de bots do QQ, a API de bots iLink da Tencent para WeChat pessoal, as APIs de bots do Telegram e do Discord, um Generic bot no Zulip, a Bots Long Poll API de uma comunidade do VK com uma chave de acesso da comunidade, um bot no Stoat, além de Slack, KOOK, Feishu/Lark, DingTalk, WeCom e plataformas parecidas. Você ainda precisa seguir os termos para desenvolvedores e os limites de taxa de cada plataforma.
- **Contas próprias em redes abertas.** No Matrix, na Twitch e no IRC, um bot é uma conta comum que você cria para ele, e o personagent usa a interface documentada da rede: a Matrix Client-Server API no homeserver que hospeda a conta do bot, a API da Twitch com um login que a conta do personagem aprova para um aplicativo que você registra, e o protocolo IRC sobre TLS com o apelido próprio do bot. Aplicam-se os termos desse homeserver, da Twitch e de cada rede IRC, assim como as regras de cada sala e canal. Algumas exigem permissão antes que um bot entre: a Libera.Chat, por exemplo, exige a permissão explícita dos operadores de um canal antes que um bot de IA entre nele.
- **Clientes não oficiais** fazem login como uma conta de usuário comum e a controlam por software. A plataforma não autoriza isso e pode proibir em seus termos. Ela pode restringir, congelar ou banir a conta permanentemente. Isso abrange:
  - **QQ por meio de NapCat, LLOneBot, Lagrange ou qualquer outra implementação de OneBot**, que é a opção avançada OneBot v11. Um bot oficial do QQ não precisa de nenhum deles. A Tencent não os autoriza, e o risco é maior a partir de endereços IP de nuvem ou do exterior.
  - **WhatsApp, Signal, Messenger, Instagram, Google Messages e outros por meio de uma ponte mautrix**, que é como o conector do Matrix chega até eles. A ponte é um cliente não oficial de cada rede, e algumas dessas redes tratam de mensagens automatizadas em seus termos. Veja [as notas do conector do Matrix](../integrations/matrix/README.pt-BR.md#termos-de-cada-rede).
  - Qualquer outra coisa que faça login como uma pessoa.

Se você usar um desses, use uma conta dedicada que possa perder, nunca a principal. Sempre que possível, execute a partir de uma rede doméstica em vez de um servidor na nuvem. Leia os termos atuais de cada rede que você conectar. Nem o autor do personagent nem os mantenedores de qualquer projeto de terceiros com que ele funciona (AstrBot, NapCat, Koishi, mautrix e outros) aceitam responsabilidade por uma conta perdida ou restrita.

## Diga às pessoas que é um bot

- Diga às pessoas de uma conversa que estão falando com uma IA, e obtenha a concordância do proprietário ou dos administradores do grupo antes de adicioná-lo. Dê à conta um nome que deixe isso evidente, e diga isso no perfil dela se a plataforma tiver um.
- Quando alguém pergunta sinceramente se é uma IA, o personagent é feito para dizer que sim. Não edite a persona para fazê-lo negar.
- Não o utilize para se passar por uma pessoa real nem para enganar alguém sobre com quem ou com o que está falando. Algumas plataformas e alguns países exigem que bots sejam identificados ou restringem contas automatizadas. Verifique as regras que se aplicam a você.
- Mantenha-o fora de grupos em que as respostas possam prejudicar ou enganar as pessoas, como grupos sobre temas médicos, jurídicos, financeiros ou de crise, e grupos com crianças.
- Se alguém pedir que ele saia, ou perguntar o que ele sabe sobre essa pessoa, trate o pedido com seriedade. O administrador pode fazê-lo esquecer uma nota (`<name>, forget ...`), e tudo o que ele guarda está na pasta inicial dele (veja abaixo).

## Créditos dos retratos

Os retratos da garota-baleia do DeepSeek, da garota-dragão do GPT e da senhorita Claude foram desenhados para o personagent a partir de designs que a comunidade já desenha. A garota-baleia deriva de 溟月, personagem original do criador do Bilibili 上善无形 (CC BY-NC-SA 4.0), com a roupa de empregada que ZipZipPipe deu a ela. A garota-dragão segue a dragoa branca de ZipZipPipe. A senhorita Claude segue um design da comunidade cujo primeiro artista não é conhecido. Os retratos têm licença própria, CC BY-NC-SA 4.0: mantenha o crédito, não os use comercialmente e compartilhe as alterações sob a mesma licença. Veja `persona_agent/static/characters/LICENSE.md`.

## O que seu provedor de modelos vê

Cada resposta envia ao provedor de modelos um prompt feito da persona, das mensagens recentes da conversa (com nomes), das notas que o bot guardou sobre a conversa e do que ele recuperou do que aprendeu. Se você definir um modelo de visão, as imagens vão para ele. Outros serviços que você ativar também veem partes disso. Eles incluem os endpoints de fallback, juiz, autoavaliação e embeddings que você configurar, e a busca na web, que envia uma consulta curta ao Tavily se você definir uma chave e ao DuckDuckGo caso contrário. A verificação de atualizações envia ao pypi.org apenas o número da versão do personagent, no máximo uma vez por dia; `UPDATE_CHECK_ENABLED=false` a desativa.

Leia a política de retenção de dados de cada provedor antes de usá-lo. Alguns provedores guardam os prompts, e alguns treinam com eles, a menos que você recuse. O padrão, os modelos gratuitos do OpenRouter, pode chegar a esses provedores. Um modelo local (Ollama, llama.cpp) mantém os prompts na sua máquina. As pessoas da conversa não concordaram com os termos de nenhum provedor, então diga a elas para onde vão as mensagens.

## O que ele guarda na sua máquina

Tudo o que ele guarda fica na pasta inicial dele. As configurações e as chaves de API estão em `.env`. As credenciais dos bots e o AstrBot que ele executa para você estão em `platforms/`. `runtime/` contém as notas das conversas, as reações que ele avaliou (citadas literalmente), o registro do que aprendeu e os exemplos aprendidos. Se você definir `SERVER_LOG_FILE`, os logs também podem conter detalhes das conversas. Mantenha a pasta privada. Nunca a publique nem a anexe a uma issue, e faça backup se o que ele aprendeu importa para você. As leis sobre guardar e tratar mensagens de outras pessoas variam entre países, e cumprir as suas é responsabilidade sua.

Ele pode aprender algo errado. Uma mudança precisa de duas reações concordantes da mesma conversa, pelo menos uma da pessoa a quem a resposta se destinava. Cada mudança fica em um registro somente de acréscimo, que você pode revisar e desfazer com `personagent learned` ou na visão Atividade da página local. Revise-o periodicamente.

## Sem garantia

O software é fornecido "como está", sem garantia de qualquer tipo, expressa ou implícita. Os autores não são responsáveis por qualquer reclamação, dano ou perda decorrente do seu uso. Veja a [LICENSE](../LICENSE).
