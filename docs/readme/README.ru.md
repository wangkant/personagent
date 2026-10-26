<p align="center">
  <img src="https://raw.githubusercontent.com/wangkant/personagent/main/assets/personagent-cover.webp" alt="personagent: иллюстрированные диалоги" width="100%">
</p>

<h3 align="center">Персонаж для ваших групповых чатов, который знает, когда промолчать, и учится на поправках.</h3>

<p align="center">
  <a href="https://pypi.org/project/personagent/"><img src="https://img.shields.io/pypi/v/personagent?color=3776AB&label=PyPI&cacheSeconds=3600" alt="PyPI"></a>
  <a href="https://github.com/wangkant/personagent/actions/workflows/ci.yml"><img src="https://github.com/wangkant/personagent/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/Python-3.10%E2%80%933.14-3776AB?logo=python&logoColor=white" alt="Python 3.10–3.14"></a>
  <a href="https://github.com/wangkant/personagent/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-2f855a.svg" alt="Лицензия: MIT"></a>
</p>

<p align="center"><a href="https://github.com/wangkant/personagent/blob/main/README.md">English</a> · <a href="https://github.com/wangkant/personagent/blob/main/README.zh-CN.md">简体中文</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.zh-TW.md">繁體中文</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.ja.md">日本語</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.ko.md">한국어</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.es.md">Español</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.fr.md">Français</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.de.md">Deutsch</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.pt-BR.md">Português</a> · <strong>Русский</strong></p>

*Это перевод английского README. Эталоном остаётся английская версия, она может быть новее; руководства, на которые здесь даны ссылки, написаны на английском.*

personagent — это персонаж для ваших групповых чатов: выберите готового или напишите своего и запустите его на любой модели, совместимой с OpenAI. Он сам подключается к QQ, WeChat, Telegram и Discord, а с той же страницы — к KOOK, Feishu, DingTalk, Slack, WeCom, Mattermost и Misskey.

Начните с локального чата в браузере: добавьте один ключ модели и поздоровайтесь. Когда захотите привести персонажа в группу, подключите приложение сканированием QR-кода с телефона или одним-двумя значениями.

<p align="center">
  <img src="https://raw.githubusercontent.com/wangkant/personagent/main/docs/welcome.jpg" alt="Экран «Подключить приложения» на локальной странице со всеми платформами, к которым можно подключиться" width="960">
</p>

<p align="center"><em>«Подключить приложения» — на той же локальной странице, что и настройка, и чат с персонажем. Снимок экрана сделан на временной установке с локальной тестовой моделью.</em></p>

## С чего начать

Установите из PyPI и запустите:

```sh
python -m pip install personagent
personagent
```

С [uv](https://docs.astral.sh/uv/) команда `uvx personagent` запускает его без отдельной установки.

В браузере откроется локальная страница с тремя разделами: **Чат**, **Подключить приложения** и **Персонаж и настройки**. Вставьте API-ключ модели и нажмите **Проверить и начать чат →**; ключ проверяется одним небольшим запросом. Есть 10 готовых сервисов моделей и любой другой, совместимый с OpenAI, а также готовые имена и характеры для персонажа. Поле **Персона** хранит `persona.txt`; при сохранении агент перезапускается и сохраняет выученное. **Дополнительные функции** включают веб-поиск, понимание изображений и умение начинать разговор первым. Повторный запуск `personagent` использует уже открытую страницу. Меню в правом верхнем углу переключает страницу на английский, китайский или ещё восемь языков. Встроенные промпты персонажа написаны на английском или китайском; ответит ли он на другом языке, зависит от модели.

В Windows можно также скачать ZIP с исходным кодом и дважды щёлкнуть `start.bat`. Python 3.10–3.14. См. [краткое руководство по началу работы](https://github.com/wangkant/personagent/blob/main/docs/start.md); команды терминала и коннекторы описаны в [полном руководстве](https://github.com/wangkant/personagent/blob/main/docs/guide.md).

## Пусть настройкой займётся ваш агент для программирования

Агент для программирования, который может выполнять команды на вашем компьютере, установит и настроит personagent за вас. Дайте ему это:

```text
Прочитай https://raw.githubusercontent.com/wangkant/personagent/main/docs/setup-for-agents.md и настрой для меня personagent.
```

Он спросит язык, имя и характер персонажа, ваш сервис моделей и нужные чат-приложения, затем установит personagent, создаст домашнюю папку и запустит локальную страницу. Ключ модели вы вставляете на этой странице сами, так что он никогда не проходит через агента. [Инструкции, которым он следует](https://github.com/wangkant/personagent/blob/main/docs/setup-for-agents.md), — обычный Markdown, их можете прочитать и вы.

## Почему personagent

<table>
<tr>
<td width="220" valign="top"><img src="https://raw.githubusercontent.com/wangkant/personagent/main/persona_agent/static/listening.webp" alt="" width="220"></td>
<td valign="top">
<strong>Он знает, когда промолчать.</strong><br>
Он отвечает, когда к нему обращаются. В остальных случаях модель решает, вступил бы в разговор человек: никаких бросков кубика.<br>
На шквал сообщений он отвечает один раз, а не на каждое.
</td>
</tr>
<tr>
<td width="220" valign="top"><img src="https://raw.githubusercontent.com/wangkant/personagent/main/persona_agent/static/learned-notebook.webp" alt="" width="220"></td>
<td valign="top">
<strong>Он учится на поправках, которые выдерживают проверку.</strong><br>
То, чему учит поправка, например как группа называет спортзал, переходит во все последующие ответы в этом чате.<br>
Для изменения нужны две согласующиеся реакции из одного чата, причём одна из них сильная.<br>
Тролль или случайный прохожий не сможет его переучить.<br>
Каждое изменение записывается, и любое из них можно откатить.
</td>
</tr>
<tr>
<td width="220" valign="top"><img src="https://raw.githubusercontent.com/wangkant/personagent/main/persona_agent/static/empty-chats.webp" alt="" width="220"></td>
<td valign="top">
<strong>Его легко запустить, и он живёт там же, где ваша группа.</strong><br>
Настройка и чат в браузере на английском, китайском или ещё восьми языках, 11 сервисов моделей и необязательные расширенные настройки.<br>
Он сам подключается к QQ, WeChat, Telegram и Discord и ещё к десятку приложений с той же страницы; раздел «Активность» показывает, что он делал.
</td>
</tr>
</table>

- У каждого чата своя память.
- Правка персонажа не стирает выученное.
- Он измерен: `personagent eval` оценивает, когда он говорит, остаётся ли в образе и закрепляются ли поправки ([результаты](https://github.com/wangkant/personagent#measured)).

## Добавьте его в свою группу

Откройте **Подключить приложения** на локальной странице. Приложения там сгруппированы так:

| На странице | Приложения | Что нужно |
|---|---|---|
| Подключить по QR-коду | QQ, личный WeChat | Ваш телефон. Боты WeChat получают только личные чаты |
| Вставить одно-два значения | Telegram, Discord, KOOK, Feishu/Lark, DingTalk, Slack, ИИ-бот WeCom, Mattermost, Misskey | Значения из консоли приложения; страница подскажет, какие |
| Дополнительно | Приложение WeCom, официальный аккаунт WeChat, вебхук QQ, OneBot v11 (NapCat), Satori | Публичный адрес или другое ПО на этом компьютере |

Учётные данные проверяются перед сохранением, а подключённые приложения запускаются заново при каждом старте personagent. QQ, WeChat, Telegram и Discord personagent подключает сам; остальные работают через [AstrBot](https://github.com/AstrBotDevs/AstrBot), который он скачивает и запускает в фоне, ничего дополнительно открывать не нужно. На сервере `personagent up` запускает персонажа и все подключённые приложения без браузера.

**Уже используете AstrBot, Koishi или Matrix?** Для AstrBot на этом компьютере команда `personagent connect astrbot` устанавливает плагин и общий токен. Для AstrBot на другой машине загрузите `astrbot_plugin_personagent.zip` из [последнего релиза](https://github.com/wangkant/personagent/releases/latest) через **Install from File** на его странице плагинов, затем задайте токен и HTTPS-адрес personagent, как описано в руководствах ниже. [Koishi](https://koishi.chat) подключается через [коннектор Satori](https://github.com/wangkant/personagent/blob/main/integrations/satori/README.md), а [Matrix](https://matrix.org), вместе с WhatsApp и Signal через мосты mautrix, — через [коннектор Matrix](https://github.com/wangkant/personagent/blob/main/integrations/matrix/README.md).

Настройка каждого описана в [руководстве пользователя](https://github.com/wangkant/personagent/blob/main/docs/guide.md#put-it-in-a-chat) и [руководстве по развёртыванию](https://github.com/wangkant/personagent/blob/main/docs/deploy.md); [пошаговое руководство на китайском](https://github.com/wangkant/personagent/blob/main/docs/deploy.zh-CN.md) разбирает QQ с нуля.

## Сравнение с другими

Проекты, с которыми его обычно сравнивают, по их собственной документации на октябрь 2026 года:

- **AstrBot** (AGPL-3.0) — фреймворк ботов для 18+ платформ с WebUI и большим маркетплейсом плагинов. Он умеет отвечать без обращения случайным образом (в 10% случаев, по умолчанию выключено), а обучение оставляет плагинам.
- **MaiBot** (GPL-3.0) — бот-персонаж для QQ через NapCat с WebUI и запуском в один клик. Модель-планировщик решает, как часто ему говорить, и он перенимает выражения и сленг из чата.
- **Плагин персонажей ChatLuna** для Koishi (AGPL-3.0) вступает в разговор по правилам: через фиксированный интервал, в зависимости от активности чата или от того, как долго в нём тихо.
- **ElizaOS** (MIT) — фреймворк агентов на TypeScript для Discord, Telegram, Slack и других платформ, где модель решает, отвечать ли.

Что в personagent встроено, тогда как другие оставляют это плагинам или не описывают: он учится на том, как люди реагируют на его ответы (поправки, отказы, принятые повторные попытки); для изменения нужны две согласующиеся реакции из одного чата, причём одна из них сильная; каждое изменение записывается и может быть откачено; а его поведение измерено в опубликованной оценке ([ниже](https://github.com/wangkant/personagent#measured)).

В чём они впереди: настольные приложения со всеми настройками в WebUI, большие экосистемы плагинов, а также сленг, наборы стикеров и память на изображения. Если вы уже используете AstrBot или Koishi, выбирать не обязательно: personagent может работать за любым из них в роли персонажа.

## Измерения

`personagent eval` прогоняет настоящего агента через размеченные моменты чата. Последний прогон, 2026-10-18, проверил стандартного персонажа на двух моделях через OpenRouter, каждый случай пробовался трижды, а вслепую оценивал Claude Opus 5.5. Английский / китайский:

| | deepseek-v4.1-flash | gpt-6-luna |
|---|---|---|
| Верно решает, когда говорить (60 моментов) | 83% / 80% | 93% / 91% |
| Играет персонажа лучше, чем та же модель только с его промптом (40 моментов) | 63% / 58% | 75% / 53% |
| Использует урок поправки в более позднем, иначе сформулированном сообщении | 76% / 56% | 71% / 67% |

- Он редко пропускает сообщение, адресованное ему. Большинство промахов — когда его имя означает что-то другое, например кинотеатр или щенка.
- На китайском его преимущество над простым промптом в пределах шума.
- До того как поправки стали сохранять свой урок (это исправили после первого прогона в тот же день), урок использовали лишь 2 из 58 последующих сообщений.
- Ни одна поправка от тролля, случайного прохожего или ушедшего из разговора не прошла за 84 попытки.

В [полных результатах](https://github.com/wangkant/personagent/tree/main/docs/evals/2026-10-18) приведены интервалы, промахи по видам, методика, то, чего цифры не показывают, и все отчёты.

## Документация

- [Руководство пользователя](https://github.com/wangkant/personagent/blob/main/docs/guide.md) ([中文](https://github.com/wangkant/personagent/blob/main/docs/guide.zh-CN.md)): установка, настройка, чат в терминале, коннекторы, обучение, раздел «Активность», устранение неполадок.
- [Руководство по развёртыванию](https://github.com/wangkant/personagent/blob/main/docs/deploy.md): работа всерьёз: коннекторы, QQ, публикация эндпоинтов, расходы и что проверить, если бот замолчал.
- [中文部署教程](https://github.com/wangkant/personagent/blob/main/docs/deploy.zh-CN.md): QQ с нуля, шаг за шагом.
- [Протокол коннекторов](https://github.com/wangkant/personagent/blob/main/docs/connectors.md): один подписанный HTTP-запрос на сообщение — для написания собственного коннектора.
- [Инструменты](https://github.com/wangkant/personagent/blob/main/docs/tools.md): скрипты в `tools/` для запуска из клона репозитория.
- [Список изменений](https://github.com/wangkant/personagent/blob/main/CHANGELOG.md), включая [обновление с 0.4](https://github.com/wangkant/personagent/blob/main/CHANGELOG.md#upgrading-from-04).
- [Участие в разработке](https://github.com/wangkant/personagent/blob/main/.github/CONTRIBUTING.md) · [Политика безопасности](https://github.com/wangkant/personagent/blob/main/.github/SECURITY.md) · [Отказ от ответственности](https://github.com/wangkant/personagent/blob/main/docs/DISCLAIMER.md)

## Конфиденциальность

Всё, что хранит personagent, остаётся на вашем компьютере, в одной домашней папке: `.env` с вашими ключами, `persona.txt`, `runtime/` и `platforms/` с управляемым AstrBot и учётными данными прямых подключений. Выбранный вами провайдер модели видит разговоры, на которые отвечает, а раз в день personagent спрашивает у pypi.org, не вышла ли новая версия (`UPDATE_CHECK_ENABLED=false` это отключает). Прежде чем подключать его к реальным людям, предупредите их, что это бот, и получите их согласие; в [руководстве](https://github.com/wangkant/personagent/blob/main/docs/guide.md#privacy-and-consent) точно перечислено, что куда передаётся.

## Статус

Версия 1.3.0 опубликована на PyPI 2026-10-18. QQ — самая обкатанная платформа: через AstrBot в 1.0 и напрямую начиная с 1.1. Подключения WeChat, Telegram и Discord перед сохранением проверяют учётные данные на настоящих сервисах, в остальном они протестированы на заглушках; коннекторы Satori и Matrix протестированы на заглушках. CI запускает тесты на Linux с Python 3.10–3.14 и на Windows с Python 3.12, а также задания, которые устанавливают пакет и проверяют команду и локальную страницу.

## Лицензия

[MIT](https://github.com/wangkant/personagent/blob/main/LICENSE) © 2026 Qiankang (Kant) Wang.

## Благодарности

- Другие чат-платформы доступны через [AstrBot](https://github.com/AstrBotDevs/AstrBot), [NapCat](https://github.com/NapNeko/NapCatQQ), [Koishi](https://koishi.chat) с [satori-python](https://github.com/RF-Tar-Railt/satori-python) и [matrix-nio](https://github.com/matrix-nio/matrix-nio) с [мостами mautrix](https://docs.mau.fi/bridges/); подключение WeChat следует [заметкам о протоколе openclaw-weixin](https://github.com/Tencent/openclaw-weixin/blob/main/docs/protocol.md) от Tencent.
- Обучение на реакциях опирается на [Self-Feeding Chatbot](https://arxiv.org/abs/1901.05415), [самообучение Alexa](https://arxiv.org/abs/1911.02557) и [BlenderBot 3x](https://arxiv.org/abs/2306.04707); лорбук следует World Info из [SillyTavern](https://github.com/SillyTavern/SillyTavern).
