<p align="center">
  <img src="https://raw.githubusercontent.com/wangkant/personagent/main/assets/personagent-cover.webp" alt="personagent" width="100%">
</p>

<h3 align="center">Персонаж для ваших групповых чатов, который знает, когда промолчать, и учится на поправках.</h3>

<p align="center">
  <a href="https://pypi.org/project/personagent/"><img src="https://img.shields.io/pypi/v/personagent?color=3776AB&label=PyPI&cacheSeconds=3600" alt="PyPI"></a>
  <a href="https://github.com/wangkant/personagent/actions/workflows/ci.yml"><img src="https://github.com/wangkant/personagent/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/Python-3.10%E2%80%933.14-3776AB?logo=python&logoColor=white" alt="Python 3.10–3.14"></a>
  <a href="https://github.com/wangkant/personagent/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-2f855a.svg" alt="Лицензия: MIT"></a>
</p>

<p align="center"><a href="https://github.com/wangkant/personagent/blob/main/README.md">English</a> · <a href="https://github.com/wangkant/personagent/blob/main/README.zh-CN.md">简体中文</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.zh-TW.md">繁體中文</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.ja.md">日本語</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.ko.md">한국어</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.es.md">Español</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.fr.md">Français</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.de.md">Deutsch</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.pt-BR.md">Português</a> · <strong>Русский</strong></p>

*Это перевод английского README. Эталоном остаётся английская версия, она может быть новее.*

personagent — это персонаж для ваших групповых чатов: выберите готового или напишите своего и запустите его на любой модели, совместимой с OpenAI. Начните с чата с ним в браузере, а потом с той же локальной страницы приведите его в QQ, WeChat, Telegram, Discord и ещё десяток приложений.

<p align="center">
  <img src="https://raw.githubusercontent.com/wangkant/personagent/main/docs/welcome.jpg" alt="Экран «Подключить приложения» на локальной странице со всеми платформами, к которым можно подключиться" width="960">
</p>

<p align="center"><em>«Подключить приложения» — на той же локальной странице, что и настройка, и чат с персонажем.</em></p>

## Почему personagent

<table>
<tr>
<td width="220" valign="top"><strong>Он знает, когда промолчать.</strong></td>
<td valign="top">
Он отвечает, когда к нему обращаются. В остальных случаях модель решает, вступил бы в разговор человек.<br>
На шквал сообщений он отвечает один раз.
</td>
</tr>
<tr>
<td width="220" valign="top"><strong>Он учится на поправках, которые выдерживают проверку.</strong></td>
<td valign="top">
То, чему учит поправка, например как группа называет спортзал, переходит во все последующие ответы в этом чате.<br>
Для изменения нужны две согласующиеся реакции из одного чата, причём одна из них сильная.<br>
Тролль или случайный прохожий не сможет его переучить.<br>
Каждое изменение записывается, и любое из них можно откатить.
</td>
</tr>
<tr>
<td width="220" valign="top"><strong>Его легко запустить, и он живёт там же, где ваша группа.</strong></td>
<td valign="top">
Одна команда открывает локальную страницу в браузере — на английском, китайском или ещё восьми языках.<br>
Чтобы начать чат, вставьте один ключ модели: десять сервисов моделей уже настроены, подойдёт и любой другой, совместимый с OpenAI.<br>
Приложение подключается сканированием с телефона или вставкой одного-двух значений. Раздел «Активность» показывает, что персонаж там делал.
</td>
</tr>
<tr>
<td width="220" valign="top"><strong>Он может быть готовым персонажем или вашим собственным.</strong></td>
<td valign="top">
Семь готовых характеров. Три из них — персонажи, которых сообщество уже рисует: девушка-кит DeepSeek, девушка-дракон GPT и леди Claude; их портреты моргают, думают, пока ответ в пути, и говорят, когда он приходит.<br>
Переписывайте персону когда угодно. Всё, чему персонаж научился, сохраняется.
</td>
</tr>
</table>

- У каждого чата своя память, и по просьбе он забывает: `Nova, remember Sam is vegetarian`, `Nova, forget vegetarian`, `Nova, what do you remember` ([команды памяти](https://github.com/wangkant/personagent/blob/main/docs/guide.ru.md#команды-памяти)). То, что в группе отмечено о человеке, переходит и в его личный чат с персонажем, но не наоборот.
- Он отвечает на том языке, на котором идёт чат. Стартовые персоны есть на каждом из десяти языков страницы; встроенные примеры, фильтры и промпты написаны на английском и китайском.
- Он измерен: `personagent eval` оценивает, когда он говорит, остаётся ли в образе и закрепляются ли поправки ([результаты](https://github.com/wangkant/personagent#measured)).

## С чего начать

```sh
python -m pip install personagent
personagent
```

С [uv](https://docs.astral.sh/uv/) команда `uvx personagent` запускает его без отдельной установки. В Windows можно также скачать ZIP с исходным кодом и дважды щёлкнуть `start.bat`. personagent тестируется на Linux с Python 3.10–3.14 и на Windows с Python 3.12.

В браузере откроется локальная страница. Вставьте API-ключ модели и нажмите **Проверить и начать чат**; ключ проверяется одним небольшим запросом. Ключа ещё нет? По умолчанию выбраны бесплатные модели OpenRouter, и ключ для них ничего не стоит. Чтобы посмотреть на персонажа ещё до всякого ключа, запустите `personagent demo`: он бесплатно проиграет три заготовленные сцены. [Руководство по началу работы](https://github.com/wangkant/personagent/blob/main/docs/start.ru.md) проводит по странице экран за экраном.

## Сколько это стоит

personagent бесплатен. Вы платите выбранному сервису моделей по его собственным тарифам.

- **Начать можно бесплатно.** Бесплатные модели OpenRouter дают 50 запросов в день; модель может меняться от запроса к запросу, а некоторые бесплатные провайдеры сохраняют то, что получают. `glm-4.7-flash` от Zhipu тоже бесплатна, а Ollama запускает модель на вашем компьютере без всякого ключа.
- **Что обращается к модели.** Каждый ответ и два шага поменьше: решение, вступать ли в разговор, когда его никто не звал, и оценка того, как люди реагируют на его ответы. `personagent doctor` и `personagent eval` тоже отправляют запросы; остальное описано в [руководстве по развёртыванию](https://github.com/wangkant/personagent/blob/main/docs/deploy.ru.md#расходы).
- **Что не обращается никогда.** `personagent demo` и команды памяти.

## Добавьте его в свою группу

Откройте **Подключить приложения** на локальной странице. Приложения там сгруппированы так:

| На странице | Приложения | Что нужно |
|---|---|---|
| Подключить по QR-коду | QQ, личный WeChat | Ваш телефон. Боты WeChat получают только личные чаты |
| Вставить одно-два значения | Telegram, Discord, KOOK, Feishu/Lark, DingTalk, Slack, ИИ-бот WeCom, Mattermost, Misskey | Значения из консоли приложения; страница подскажет, какие |
| Дополнительно | Приложение WeCom, официальный аккаунт WeChat, вебхук QQ, OneBot v11 (NapCat), Satori | Публичный адрес или другое ПО на этом компьютере |

Учётные данные проверяются перед сохранением, а подключённые приложения запускаются заново при каждом старте personagent. Приложения с подключением по QR-коду, Telegram и Discord personagent подключает сам; остальные работают через [AstrBot](https://github.com/AstrBotDevs/AstrBot), который он скачивает и запускает в фоне, ничего дополнительно открывать не нужно. На сервере `personagent up` запускает персонажа и все подключённые приложения без браузера. Настройка каждого приложения описана в [руководстве пользователя](https://github.com/wangkant/personagent/blob/main/docs/guide.ru.md#добавьте-его-в-чат), а QQ с нуля, шаг за шагом, — в [китайском руководстве по развёртыванию](https://github.com/wangkant/personagent/blob/main/docs/deploy.zh-CN.md).

У вас уже работает свой мост?

- **AstrBot**: `personagent connect astrbot` устанавливает плагин и общий токен. В [руководстве](https://github.com/wangkant/personagent/blob/main/docs/guide.ru.md#мосты-которые-вы-запускаете-сами) описан и случай с AstrBot на другой машине.
- **[Koishi](https://koishi.chat)** или любой сервер Satori: [коннектор Satori](https://github.com/wangkant/personagent/blob/main/integrations/satori/README.ru.md).
- **[Matrix](https://matrix.org)**, вместе с WhatsApp и Signal через мосты mautrix: [коннектор Matrix](https://github.com/wangkant/personagent/blob/main/integrations/matrix/README.ru.md).

## Агенты для программирования

**Пусть настройкой займётся агент.** Дайте строку ниже агенту для программирования, который может выполнять команды на вашем компьютере. Он спросит, чего вы хотите, установит personagent и запустит локальную страницу. Ключ модели вы вставляете на этой странице сами, так что он никогда не проходит через агента.

```text
Прочитай https://raw.githubusercontent.com/wangkant/personagent/main/docs/setup-for-agents.md и настрой для меня personagent.
```

**Разговаривайте с персонажем прямо во время работы.** Когда ключ модели настроен, Claude Code, Codex и DeepSeek Harness (`dsh`) могут обращаться к персонажу:

```bash
personagent connect claude-code
personagent connect codex
personagent connect dsh
```

Откройте там новую сессию (DeepSeek Harness сначала перезапустите) и попросите агента что-нибудь сказать персонажу. Это тот же личный чат и та же память, что и на локальной странице. В Claude Code и Codex с `--react` персонаж может сказать реплику в конце хода. `--remove` всё убирает. В [руководстве](https://github.com/wangkant/personagent/blob/main/docs/guide.ru.md#агенты-для-кода) описаны разрешения, что именно `--react` отправляет в ваш сервис моделей, и другие инструменты с поддержкой MCP.

## Измерения

`personagent eval` прогоняет настоящего агента через размеченные моменты чата. Последний прогон, 2026-10-18, выполнен на версии 1.3.0: стандартный персонаж на двух моделях через OpenRouter, каждый случай пробовался трижды, а вслепую оценивал Claude Opus 5.5. Английский / китайский:

| | deepseek-v4.1-flash | gpt-6-luna |
|---|---|---|
| Верно решает, когда говорить (60 моментов) | 83% / 80% | 93% / 91% |
| Играет персонажа лучше, чем та же модель только с его промптом (40 моментов) | 63% / 58% | 75% / 53% |
| Использует урок поправки в более позднем, иначе сформулированном сообщении | 76% / 56% | 71% / 67% |

- Он редко пропускает сообщение, адресованное ему. Большинство промахов — когда его имя означает что-то другое, например кинотеатр или щенка.
- Ни одна из 84 поправок от троллей, случайных прохожих или ушедших из разговора не прошла.

В [полных результатах](https://github.com/wangkant/personagent/tree/main/docs/evals/2026-10-18) приведены интервалы, промахи по видам, методика и все отчёты.

## Сравнение с другими

Проекты, с которыми его обычно сравнивают, на ноябрь 2026 года:

- **AstrBot** (AGPL-3.0) — фреймворк ботов для более чем десятка платформ с WebUI и большим маркетплейсом плагинов. Он умеет отвечать без обращения случайным образом (в 10% случаев, по умолчанию выключено), а обучение оставляет плагинам.
- **MaiBot** (GPL-3.0) — бот-персонаж для QQ через NapCat с WebUI и запуском в один клик. Модель-планировщик решает, как часто ему говорить, и он перенимает выражения и сленг из чата.
- **Плагин персонажей ChatLuna** для Koishi (AGPL-3.0) вступает в разговор по правилам: через фиксированный интервал, в зависимости от активности чата или от того, как долго в нём тихо.
- **ElizaOS** (MIT) — фреймворк агентов на TypeScript для Discord, Telegram, Slack и других платформ, где модель решает, отвечать ли.

Что в personagent встроено: он учится на том, как люди реагируют на его ответы (поправки, отказы, принятые повторные попытки), ведёт запись каждого изменения с возможностью отката и публикует оценку своего поведения.

В чём они впереди: настольные приложения со всеми настройками в WebUI, большие экосистемы плагинов, а также сленг, наборы стикеров и память на изображения. Если вы уже используете AstrBot или Koishi, выбирать не обязательно: personagent может работать за любым из них в роли персонажа.

## Обновление и удаление

Когда на PyPI появляется новая версия, страница показывает уведомление с командой обновления для вашего способа установки. Для pip это `python -m pip install -U personagent`. Домашняя папка остаётся на месте: настройки, персонаж, всё выученное и подключённые приложения.

Чтобы удалить personagent, сначала уберите его из всех агентов для программирования, к которым вы его подключали (`personagent connect claude-code --remove` или то же самое с `codex` или `dsh`). Затем закройте personagent и выполните `python -m pip uninstall personagent`. Наконец, удалите домашнюю папку — при установке из PyPI это `~/personagent`, если вы не выбрали другую. В ней ваш ключ, персонаж и всё, чему он научился, так что отменить это нельзя. В [полной инструкции](https://github.com/wangkant/personagent/blob/main/docs/setup-for-agents.md#undoing-it) (на английском) описаны uv, pipx и то, что стоит отозвать.

## Конфиденциальность

Всё, что хранит personagent, остаётся на вашем компьютере, в одной домашней папке: `.env` с вашими ключами, `persona.txt`, `runtime/` и `platforms/` с управляемым AstrBot и учётными данными прямых подключений. Выбранный вами провайдер модели видит разговоры, на которые отвечает, а раз в день personagent спрашивает у pypi.org, не вышла ли новая версия (`UPDATE_CHECK_ENABLED=false` это отключает). Прежде чем подключать его к реальным людям, предупредите их, что это бот, и получите их согласие; в [руководстве](https://github.com/wangkant/personagent/blob/main/docs/guide.ru.md#конфиденциальность-и-согласие) перечислено, что куда передаётся.

## Документация

- [Руководство пользователя](https://github.com/wangkant/personagent/blob/main/docs/guide.ru.md): установка, настройка, чат в терминале, коннекторы, обучение, раздел «Активность», устранение неполадок.
- [Руководство по развёртыванию](https://github.com/wangkant/personagent/blob/main/docs/deploy.ru.md): работа всерьёз: коннекторы, QQ, публикация эндпоинтов, расходы и что проверить, если бот замолчал.
- [Протокол коннекторов](https://github.com/wangkant/personagent/blob/main/docs/connectors.ru.md): один подписанный HTTP-запрос на сообщение — для написания собственного коннектора.
- [Инструменты](https://github.com/wangkant/personagent/blob/main/docs/tools.ru.md): скрипты в `tools/` для запуска из клона репозитория.
- [Список изменений](https://github.com/wangkant/personagent/blob/main/CHANGELOG.md) · [Участие в разработке](https://github.com/wangkant/personagent/blob/main/.github/CONTRIBUTING.md) · [Политика безопасности](https://github.com/wangkant/personagent/blob/main/.github/SECURITY.md) · [Отказ от ответственности](https://github.com/wangkant/personagent/blob/main/docs/DISCLAIMER.ru.md)

## Лицензия

Код распространяется по лицензии [MIT](https://github.com/wangkant/personagent/blob/main/LICENSE) © 2026 Qiankang (Kant) Wang. Три портрета персонажей распространяются по лицензии CC BY-NC-SA 4.0, авторство указано в [persona_agent/static/characters/LICENSE.md](https://github.com/wangkant/personagent/blob/main/persona_agent/static/characters/LICENSE.md).

## Благодарности

- Другие чат-платформы доступны через [AstrBot](https://github.com/AstrBotDevs/AstrBot), [NapCat](https://github.com/NapNeko/NapCatQQ), [Koishi](https://koishi.chat) с [satori-python](https://github.com/RF-Tar-Railt/satori-python) и [matrix-nio](https://github.com/matrix-nio/matrix-nio) с [мостами mautrix](https://docs.mau.fi/bridges/); подключение WeChat следует [заметкам о протоколе openclaw-weixin](https://github.com/Tencent/openclaw-weixin/blob/main/docs/protocol.md) от Tencent.
- Обучение на реакциях опирается на [Self-Feeding Chatbot](https://arxiv.org/abs/1901.05415), [самообучение Alexa](https://arxiv.org/abs/1911.02557) и [BlenderBot 3x](https://arxiv.org/abs/2306.04707); лорбук следует World Info из [SillyTavern](https://github.com/SillyTavern/SillyTavern).
