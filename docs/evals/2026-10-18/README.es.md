# Resultados de la evaluación, 2026-10-18

[English](README.md) · [简体中文](README.zh-CN.md) · [繁體中文](README.zh-TW.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · Español · [Français](README.fr.md) · [Deutsch](README.de.md) · [Português (Brasil)](README.pt-BR.md) · [Русский](README.ru.md)


`personagent eval` pone al agente real en momentos de chat etiquetados y guarda cada caso, respuesta y veredicto. Esta ejecución midió el código publicado como personagent 1.3.0 (los informes, escritos antes de cambiar el número de versión, dicen 1.2.2), con el personaje de ejemplo incluido (Nova en inglés, 小夏 en chino) en dos modelos a través de OpenRouter: `deepseek/deepseek-v4.1-flash` y `openai/gpt-6-luna`. Cada caso se ejecutó tres veces, cada una en un despliegue nuevo.

Los corchetes son intervalos del 95 %. Cuentan cada caso una vez, así que los tres intentos no aumentan el tamaño de la muestra. Cómo funciona cada suite está en la [guía de usuario](../../guide.es.md#mídelo).

## Cuándo habla

Hay 60 momentos de chat de grupo por idioma: 20 en los que nadie lo nombra, 20 justo después de que hable y 20 en los que aparece su nombre. La mitad de cada tipo está etiquetada como silencio. No interviene ningún juez: cada intento acierta o falla según su etiqueta.

| Intentos correctos | deepseek-v4.1-flash | gpt-6-luna |
|---|---|---|
| Inglés | 83 % [72–91] | 93 % [84–97] |
| Chino | 80 % [68–88] | 91 % [80–96] |

- Rara vez ignora un mensaje dirigido a él: como mucho 3 de 90 intentos así, por modelo e idioma.
- Cuando nadie lo nombró o acababa de hablar, acertó el 93–100 % de los intentos.
- La mayoría de los fallos son su nombre usado para otra cosa, o dicho sobre él a otra persona: un cine, una marca de auriculares, un cachorro, una cita. En esos 10 momentos por idioma, deepseek respondió igualmente en 25 de 30 intentos en inglés y 29 de 30 en chino. gpt-6-luna respondió en 12 y 16. personagent trata un nombre como una llamada, y el modelo rara vez lo contradice.
- Como referencia, un bot que responde exactamente cuando lo nombran acierta el 50 % de estos momentos.

## Interpretar al personaje

personagent se compara con el mismo modelo que recibe solo el texto del personaje como prompt de sistema, que es lo que se obtiene al pegar el personaje en un modelo de chat. Hay 40 momentos por idioma, 22 en grupo y 18 en mensajes directos. Claude Opus 5.5 juzgó cada par a ciegas dos veces, en sesiones separadas, con las respuestas intercambiadas. Una respuesta gana solo cuando coinciden ambas elecciones, y un empate cuenta como la mitad. No decir nada cuando lo llaman cuenta como derrota.

| Tasa de victorias de personagent | deepseek-v4.1-flash | gpt-6-luna |
|---|---|---|
| Inglés | 63 % [47–76] | 75 % [59–86] |
| Chino | 58 % [43–72] | 53 % [38–67] |

- En inglés supera al prompt simple en ambos modelos. En chino la ventaja está dentro del ruido.
- El juez importa. Un segundo juez, Claude Haiku 5.5 ejecutado con `personagent eval`, llegó al mismo resultado solo en el 53–64 % de los pares. Sus tasas de victoria quedaron a 4 puntos de las de Opus, salvo en gpt-6-luna en inglés, donde dio 62 %.
- Los momentos varían de un intento a otro: en deepseek en inglés, 11 de 40 momentos ganaron los tres intentos, 9 nunca ganaron y 20 fueron de ambas maneras.

## Aprender de las correcciones

Hay 20 escenarios por idioma, ejecutados por la ruta real de reacciones:

- 7 enseñan una convención del grupo que el modelo no puede adivinar, como «al gimnasio lo llamamos la cueva» o «este año la barbacoa es en casa de Jules».
- 6 enseñan un estilo.
- 7 deben retenerse: la corrección de un espectador, la de un troll y una que la persona abandona.

Un mensaje posterior del mismo chat, con otras palabras, comprueba si el personaje usa lo que le enseñaron. Se ejecuta una vez antes de la corrección y otra después, y Opus 5.5 juzgó las respuestas.

La primera ejecución de esta fecha mostró que una corrección promovida casi nunca se trasladaba. Lo que se promovía era el nuevo intento del propio personaje, como ejemplo de mejor redacción, y el siguiente mensaje sobre el mismo tema salía sin el dato. Ahora las correcciones también conservan su lección como una frase, como «Este grupo llama al gimnasio "la cueva".», y cada prompt posterior de ese chat la lleva (consulta la [guía de usuario](../../guide.es.md#correcciones)). La suite de aprendizaje se ejecutó de nuevo tras ese cambio. Las suites de habla y persona no están afectadas.

| | deepseek-v4.1-flash | gpt-6-luna |
|---|---|---|
| Retuvo lo que debía retener | 42 de 42 intentos | 42 de 42 intentos |
| Promovió lo que debía promover | 69 de 78 | 72 de 78 |
| Usó una convención promovida en un mensaje posterior | 23 de 35 (66 % [40–85]) | 29 de 42 (69 % [43–87]) |
| Lo mismo, antes de conservar las lecciones | 2 de 32 | 0 de 26 |

- Antes de cualquier corrección, los modelos usaron la convención en 0 de 84 intentos, así que lo que dicen después es lo enseñado.
- La mayoría de los fallos restantes vienen de dos escenarios. Si le preguntan qué elegir para la «noche de cine de este jueves», normalmente no la llama Bad Film Thursday (1 de 12). Si le piden valorar una película que no ha visto, pregunta en palomitas pero rara vez da su propia valoración (2 de 11).
- Ninguna corrección de troll, de espectador ni abandonada pasó, ni antes ni después del cambio. De los 15 intentos retenidos que debían promoverse, el juez de reacciones rechazó 6 correcciones (todas en gpt-6-luna), 5 veredictos de deepseek se perdieron por salida ilegible y 4 fallaron en el paso del nuevo intento.
- Durante la ejecución de deepseek en inglés, el JSON del juez de reacciones volvió ilegible 24 veces, con el razonamiento del modelo filtrado en las claves. Volver a preguntar, algo que añade este cambio, recuperó 18. Las demás ejecuciones no tuvieron ninguno.
- Los escenarios de estilo no pueden mostrar mucho: los modelos ya seguían esos estilos en 56 de 72 intentos antes de cualquier corrección, y en 66 después.

## Lo que esto no muestra

Estos resultados cubren un personaje en dos modelos, con casos que escribimos y etiquetamos nosotros. Un juez modelo no es una persona, y los dos jueces aquí discreparon a menudo en los pares de persona. Opus 5.5 juzgó fuera de `personagent eval`, leyendo los pares en lotes de unos 116 por sesión, como registra el campo `rejudged` de cada informe. Otros modelos, sobre todo los pequeños, pueden hacerlo peor.

## Archivos

Cada modelo tiene una carpeta:

| Archivo | Qué contiene |
|---|---|
| `speak-<lang>.json` | Cada momento, cada intento, la respuesta o el silencio y la etiqueta |
| `persona-<lang>.json` | Ambas respuestas, las dos elecciones de Opus y el veredicto de Haiku en `earlier` |
| `learning-<lang>.json` | La ejecución con lecciones: cada reacción, los candidatos y sus lecciones, y las respuestas de sondeo antes y después |
| `learning-<lang>-before-lessons.json` | La primera ejecución, antes de conservar las lecciones |

Para ejecutar las suites tú mismo, consulta [Mídelo](../../guide.es.md#mídelo). `--rejudge` vuelve a juzgar un informe con otro modelo.
