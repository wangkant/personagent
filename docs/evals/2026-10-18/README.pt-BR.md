# Resultados da avaliação, 2026-10-18

[English](README.md) · [简体中文](README.zh-CN.md) · [繁體中文](README.zh-TW.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Español](README.es.md) · [Français](README.fr.md) · [Deutsch](README.de.md) · Português (Brasil) · [Русский](README.ru.md)


`personagent eval` coloca o agente real em momentos de chat rotulados e guarda cada caso, resposta e veredito. Esta execução mediu o código lançado como personagent 1.3.0 (os relatórios, escritos antes de o número da versão mudar, dizem 1.2.2), com o personagem de exemplo incluído (Nova em inglês, 小夏 em chinês) em dois modelos pelo OpenRouter: `deepseek/deepseek-v4.1-flash` e `openai/gpt-6-luna`. Cada caso rodou três vezes, cada uma em uma implantação nova.

Os colchetes são intervalos de 95%. Eles contam cada caso uma vez, então as três tentativas não aumentam o tamanho da amostra. Como cada suíte funciona está no [guia do usuário](../../guide.pt-BR.md#meça).

## Quando ele fala

Há 60 momentos de chat em grupo por idioma: 20 em que ninguém o nomeia, 20 logo depois de ele falar e 20 em que o nome dele aparece. Metade de cada tipo é rotulada como silêncio. Nenhum juiz participa: cada tentativa está certa ou errada de acordo com o rótulo.

| Tentativas certas | deepseek-v4.1-flash | gpt-6-luna |
|---|---|---|
| Inglês | 83% [72–91] | 93% [84–97] |
| Chinês | 80% [68–88] | 91% [80–96] |

- Ele raramente ignora uma mensagem dirigida a ele: no máximo 3 de 90 tentativas assim, por modelo e idioma.
- Quando ninguém o nomeou ou ele tinha acabado de falar, acertou 93–100% das tentativas.
- A maioria dos erros é o nome dele usado para outra coisa, ou dito sobre ele a outra pessoa: um cinema, uma marca de fones, um filhote, uma citação. Nesses 10 momentos por idioma, o deepseek respondeu mesmo assim em 25 de 30 tentativas em inglês e 29 de 30 em chinês. O gpt-6-luna respondeu em 12 e 16. O personagent trata um nome como chamada, e o modelo raramente passa por cima disso.
- Para comparação, um bot que responde exatamente quando é nomeado acerta 50% desses momentos.

## Interpretar o personagem

O personagent é comparado ao mesmo modelo recebendo só o texto do personagem como prompt de sistema, que é o que você obtém ao colar o personagem em um modelo de chat. Há 40 momentos por idioma, 22 em grupo e 18 em mensagens diretas. O Claude Opus 5.5 julgou cada par às cegas duas vezes, em sessões separadas, com as respostas trocadas. Uma resposta só vence quando as duas escolhas concordam, e um empate conta pela metade. Não dizer nada quando chamado conta como derrota.

| Taxa de vitória do personagent | deepseek-v4.1-flash | gpt-6-luna |
|---|---|---|
| Inglês | 63% [47–76] | 75% [59–86] |
| Chinês | 58% [43–72] | 53% [38–67] |

- Em inglês, ele supera o prompt simples nos dois modelos. Em chinês, a vantagem está dentro do ruído.
- O juiz importa. Um segundo juiz, o Claude Haiku 5.5 executado por `personagent eval`, chegou ao mesmo resultado em apenas 53–64% dos pares. As taxas de vitória dele ficaram a até 4 pontos das do Opus, exceto no gpt-6-luna em inglês, em que deu 62%.
- Os momentos variam de uma tentativa para outra: no deepseek em inglês, 11 de 40 momentos venceram as três tentativas, 9 nunca venceram e 20 foram para os dois lados.

## Aprender com correções

Há 20 cenários por idioma, executados pelo caminho real de reações:

- 7 ensinam uma convenção de grupo que o modelo não consegue adivinhar, como "a gente chama a academia de caverna" ou "o churrasco este ano é na casa do Jules".
- 6 ensinam um estilo.
- 7 devem ser retidos: a correção de um espectador, a de um troll e uma que a pessoa abandona.

Uma mensagem posterior no mesmo chat, com outras palavras, verifica se o personagem usa o que aprendeu. Ela roda uma vez antes da correção e uma vez depois, e o Opus 5.5 julgou as respostas.

A primeira execução nesta data mostrou que uma correção promovida quase nunca se mantinha. O que era promovido era a nova tentativa do próprio personagem, como exemplo de redação melhor, e a mensagem seguinte sobre o mesmo assunto saía sem o fato. Agora as correções também guardam a lição em uma frase, como "Este grupo chama a academia de 'a caverna'.", e todo prompt seguinte nesse chat a traz (veja o [guia do usuário](../../guide.pt-BR.md#correções)). A suíte de aprendizado foi executada de novo depois dessa mudança. As suítes de fala e persona não são afetadas.

| | deepseek-v4.1-flash | gpt-6-luna |
|---|---|---|
| Reteve o que devia reter | 42 de 42 tentativas | 42 de 42 tentativas |
| Promoveu o que devia promover | 69 de 78 | 72 de 78 |
| Usou uma convenção promovida em uma mensagem posterior | 23 de 35 (66% [40–85]) | 29 de 42 (69% [43–87]) |
| O mesmo, antes de guardar as lições | 2 de 32 | 0 de 26 |

- Antes de qualquer correção, os modelos usaram a convenção em 0 de 84 tentativas, então o que dizem depois foi ensinado.
- A maioria dos erros restantes vem de dois cenários. Quando perguntam o que escolher para a "noite de cinema desta quinta", ele geralmente não a chama de Bad Film Thursday (1 de 12). Quando pedem para avaliar um filme que ele não viu, ele devolve a pergunta em pipocas, mas raramente dá a própria nota (2 de 11).
- Nenhuma correção de troll, de espectador ou abandonada passou, antes ou depois da mudança. Das 15 tentativas retidas que deveriam ser promovidas, o juiz de reações recusou 6 correções (todas no gpt-6-luna), 5 vereditos do deepseek se perderam por saída ilegível e 4 falharam na etapa da nova tentativa.
- Durante a execução do deepseek em inglês, o JSON do juiz de reações voltou ilegível 24 vezes, com o raciocínio do modelo vazando para as chaves. Perguntar de novo, o que esta mudança adiciona, recuperou 18. As outras execuções não tiveram nenhum.
- Os cenários de estilo não mostram muito: os modelos já seguiam esses estilos em 56 de 72 tentativas antes de qualquer correção, e em 66 depois.

## O que isto não mostra

Estes resultados cobrem um personagem em dois modelos, em casos que nós mesmos escrevemos e rotulamos. Um juiz modelo não é uma pessoa, e os dois juízes aqui discordaram com frequência nos pares de persona. O Opus 5.5 julgou fora de `personagent eval`, lendo os pares em lotes de cerca de 116 por sessão, como registra o campo `rejudged` de cada relatório. Outros modelos, especialmente os pequenos, podem se sair pior.

## Arquivos

Cada modelo tem uma pasta:

| Arquivo | O que contém |
|---|---|
| `speak-<lang>.json` | Cada momento, cada tentativa, a resposta ou o silêncio e o rótulo |
| `persona-<lang>.json` | As duas respostas, as duas escolhas do Opus e o veredito do Haiku em `earlier` |
| `learning-<lang>.json` | A execução com lições: cada reação, os candidatos e as lições deles e as respostas de teste antes e depois |
| `learning-<lang>-before-lessons.json` | A primeira execução, antes de guardar as lições |

Para executar as suítes você mesmo, veja [Meça](../../guide.pt-BR.md#meça). `--rejudge` julga um relatório de novo com outro modelo.
