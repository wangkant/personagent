<p align="center">
  <img src="https://raw.githubusercontent.com/wangkant/personagent/main/assets/personagent-cover.webp" alt="personagent" width="100%">
</p>

<h3 align="center">Агент, который ведёт себя как человек, на всех платформах, которыми вы пользуетесь.<br>У него собственный характер, он помнит, учится у тех, с кем общается, и сам решает, когда высказаться.</h3>

<p align="center">
  <a href="https://pypi.org/project/personagent/"><img src="https://img.shields.io/pypi/v/personagent?style=flat-square&label=PyPI&labelColor=24292f&color=0969da&cacheSeconds=3600" alt="PyPI"></a>
  <a href="https://github.com/wangkant/personagent/actions/workflows/ci.yml"><img src="https://img.shields.io/github/actions/workflow/status/wangkant/personagent/ci.yml?branch=main&style=flat-square&label=CI&labelColor=24292f" alt="CI"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/Python-3.10%E2%80%933.14-0969da?style=flat-square&labelColor=24292f" alt="Python 3.10–3.14"></a>
  <a href="https://github.com/wangkant/personagent/blob/main/LICENSE"><img src="https://img.shields.io/badge/License-PolyForm%20Noncommercial-0969da?style=flat-square&labelColor=24292f" alt="Лицензия: PolyForm Noncommercial"></a>
</p>

<p align="center"><a href="https://github.com/wangkant/personagent/blob/main/README.md">English</a> · <a href="https://github.com/wangkant/personagent/blob/main/README.zh-CN.md">简体中文</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.zh-TW.md">繁體中文</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.ja.md">日本語</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.ko.md">한국어</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.es.md">Español</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.fr.md">Français</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.de.md">Deutsch</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.pt-BR.md">Português</a> · <strong>Русский</strong></p>

*Это перевод английского README. Эталоном остаётся английская версия, она может быть новее.*

personagent — это агент, который ведёт себя как человек: у него собственный характер, он помнит, учится у тех, с кем общается, и сам решает, когда высказаться. Он работает везде, где он вам нужен: в групповых и личных чатах в QQ, WeChat, Telegram, Discord и ещё восемнадцати платформах, в окне на вашем компьютере и в помощниках для программирования, таких как Claude Code и Codex. Его характер вы выбираете или пишете сами, и он работает на любой модели, совместимой с OpenAI.

<p align="center">
  <img src="https://raw.githubusercontent.com/wangkant/personagent/main/docs/welcome.jpg" alt="Раздел «Подключение платформ» на локальной странице: платформы, которые подключаются по QR-коду или вводом одного-двух значений, свёрнутые дополнительные платформы и помощники для программирования, к которым можно подключиться" width="960">
</p>

<p align="center"><em>Раздел «Подключение платформ» находится на той же локальной странице, что и настройка и чат с персонажем.</em></p>

## Почему personagent

<table>
<tr>
<td width="220" valign="top"><strong>У него собственный характер.</strong></td>
<td valign="top">
Семь готовых характеров. Три из них — персонажи, которых сообщество уже изображает: девушка-кит DeepSeek, девушка-дракон GPT и леди Claude; их портреты моргают, думают и говорят.<br>
Персону можно изменить в любое время. Всё, что усвоил персонаж, сохраняется.
</td>
</tr>
<tr>
<td width="220" valign="top"><strong>Он говорит как человек.</strong></td>
<td valign="top">
Он пишет так, как люди пишут в чате: короткими простыми фразами на языке разговора, без списков, заголовков и дежурных фраз помощника, и прямо говорит, если чего-то не знает.<br>
Ответ приходит несколькими короткими сообщениями, каждое — через время, нужное, чтобы его набрать; на платформах с индикатором набора текста он при этом отображается.<br>
Он собирает стикеры, которые присылают люди, и использует их к месту, а ночью почти не вступает в разговор, пока к нему не обратятся.<br>
Если включить эту возможность, он сам начинает разговор после долгого молчания и возвращается к планам, о которых упоминали люди.
</td>
</tr>
<tr>
<td width="220" valign="top"><strong>Он помнит.</strong></td>
<td valign="top">
У каждого чата своя память: недавние сообщения, которые сохраняются после перезапуска, сводка предыдущего разговора, события с датами и факты о людях, и он сам поддерживает её в актуальном состоянии.<br>
Всё, что он помнит, перечислено в разделе «Активность», где любой элемент можно удалить или вернуть.
</td>
</tr>
<tr>
<td width="220" valign="top"><strong>Он учится на исправлениях, которые выдерживают проверку.</strong></td>
<td valign="top">
То, чему учит исправление, например как группа называет спортзал, переходит во все последующие ответы в этом чате.<br>
Тролль или посторонний участник не может его переучить.<br>
Если реакции не могут решить изменение, персонаж решает сам и записывает причину; никому не нужно ничего одобрять.<br>
Каждое изменение записывается, и любое из них можно отменить.
</td>
</tr>
<tr>
<td width="220" valign="top"><strong>Он знает, когда промолчать.</strong></td>
<td valign="top">
В группе он отвечает, когда к нему обращаются. В остальных случаях модель решает, вступил бы в разговор человек.<br>
На шквал сообщений он отвечает один раз.
</td>
</tr>
<tr>
<td width="220" valign="top"><strong>Он подключается ко всем вашим платформам.</strong></td>
<td valign="top">
Двадцать две платформы для общения подключаются с одной страницы — сканированием кода телефоном или вводом одного-двух значений, как для групповых, так и для личных чатов.<br>
Тот же агент отвечает в окне на вашем компьютере, а также в Claude Code, Codex и DeepSeek Harness.<br>
Любую другую платформу можно добавить через мост AstrBot, Koishi или Matrix либо через собственный коннектор.
</td>
</tr>
<tr>
<td width="220" valign="top"><strong>Он работает с тем, что у вас уже есть.</strong></td>
<td valign="top">
Любая модель, совместимая с OpenAI: бесплатные модели OpenRouter, платный сервис или модель, запущенная на вашем компьютере через Ollama.<br>
Одна команда открывает его — на английском, китайском или ещё восьми языках, а один вставленный ключ модели позволяет начать общение.
</td>
</tr>
</table>

Он также запоминает и забывает сведения по просьбе в чате: `Nova, remember Sam is vegetarian`, `Nova, forget vegetarian` ([команды памяти](https://github.com/wangkant/personagent/blob/main/docs/guide.ru.md#команды-памяти)). Что он сохраняет и как долго, описано в разделе руководства [память](https://github.com/wangkant/personagent/blob/main/docs/guide.ru.md#память).

## С чего начать

```sh
python -m pip install personagent
personagent
```

С [uv](https://docs.astral.sh/uv/) команда `uvx personagent` запускает его без отдельной установки. В Windows можно также скачать ZIP с исходным кодом и дважды щёлкнуть `start.bat`.

В Windows он открывается в отдельном окне, а в macOS и Linux — в браузере. Вставьте API-ключ модели и нажмите **Проверить и начать общение**. Если ключа ещё нет, по умолчанию выбраны бесплатные модели OpenRouter, ключ для которых предоставляется бесплатно. `personagent demo` воспроизводит три заранее заданные сцены без всякого ключа. [Руководство по началу работы](https://github.com/wangkant/personagent/blob/main/docs/start.ru.md) описывает страницу экран за экраном.

personagent бесплатен. Вы платите выбранному сервису моделей по его собственным тарифам. Бесплатные модели OpenRouter дают 50 запросов в день, а некоторые бесплатные поставщики сохраняют получаемые данные; Ollama запускает модель на вашем компьютере без всякого ключа.

## Подключите свои платформы

Откройте раздел **Подключение платформ** на локальной странице:

| На странице | Платформы | Что нужно |
|---|---|---|
| Подключение по QR-коду | QQ, личный WeChat | Ваш телефон. Боты WeChat получают только личные чаты |
| Ввод одного-двух значений | Telegram, Discord, Matrix, Twitch, IRC, Zulip, VK, Stoat, KOOK, Feishu/Lark, DingTalk, Slack, ИИ-бот WeCom, Mattermost, Misskey | Значения из консоли платформы; на странице указано, какие именно |
| Дополнительно | Приложение WeCom, официальный аккаунт WeChat, вебхук QQ, OneBot v11 (NapCat), Satori | Публичный адрес или другое ПО на этом компьютере |

Подключённые платформы запускаются заново при каждом запуске personagent. Платформы с подключением по QR-коду, Telegram, Discord, Matrix, Twitch, IRC, Zulip, VK и Stoat personagent подключает сам; остальные работают через [AstrBot](https://github.com/AstrBotDevs/AstrBot), который он скачивает и запускает в фоновом режиме. На сервере без дисплея команда `personagent connect <платформа>` подключает любую из этих десяти платформ из терминала с теми же шагами и проверками, что и страница, а `personagent up` запускает всё без браузера. Настройка каждой платформы описана в [руководстве пользователя](https://github.com/wangkant/personagent/blob/main/docs/guide.ru.md#добавьте-его-в-чат), а QQ с нуля — в [китайском руководстве по развёртыванию](https://github.com/wangkant/personagent/blob/main/docs/deploy.zh-CN.md).

У вас уже работает AstrBot, Koishi или Matrix? personagent может работать за ним в роли агента: см. [мосты, которые вы запускаете сами](https://github.com/wangkant/personagent/blob/main/docs/guide.ru.md#мосты-которые-вы-запускаете-сами), [коннектор Satori](https://github.com/wangkant/personagent/blob/main/integrations/satori/README.ru.md) и [коннектор Matrix](https://github.com/wangkant/personagent/blob/main/integrations/matrix/README.ru.md).

## Помощники для программирования

**Поручите настройку помощнику.** Передайте строку ниже помощнику для программирования, который может выполнять команды на вашем компьютере. Ключ модели вы вставляете на локальной странице самостоятельно, поэтому он никогда не проходит через помощника.

```text
Прочитай https://raw.githubusercontent.com/wangkant/personagent/main/docs/setup-for-agents.md и настрой для меня personagent.
```

**Общайтесь с персонажем во время работы.** Claude Code, Codex и DeepSeek Harness (`dsh`) могут обращаться к персонажу — с тем же чатом и той же памятью, что и на локальной странице:

```bash
personagent connect claude-code
personagent connect codex
personagent connect dsh
```

`--remove` отменяет подключение; обе операции можно выполнить и на странице, в блоке **Помощники для программирования** раздела **Подключение платформ**. В [руководстве](https://github.com/wangkant/personagent/blob/main/docs/guide.ru.md#помощники-для-программирования) описаны разрешения и `--react`, с которым персонаж может сказать реплику в конце хода.

## Обновление и удаление

Когда на PyPI появляется новая версия, страница показывает уведомление с командой обновления. Для pip это `python -m pip install -U personagent`. В большинстве установок кнопка **Обновить и перезапустить** в разделе **Приложение** выполняет эту команду за вас. Настройки, персонаж, всё усвоенное и подключённые платформы сохраняются. Чтобы удалить personagent, следуйте [инструкции по удалению](https://github.com/wangkant/personagent/blob/main/docs/setup-for-agents.md#undoing-it) (на английском).

## Конфиденциальность

Всё, что хранит personagent, остаётся на вашем компьютере, в одной домашней папке. Выбранный вами поставщик модели видит разговоры, на которые отвечает, а раз в день personagent спрашивает у pypi.org, не вышла ли новая версия (`UPDATE_CHECK_ENABLED=false` это отключает). Прежде чем подключать его к реальным людям, предупредите их, что это бот, и получите их согласие; в [руководстве](https://github.com/wangkant/personagent/blob/main/docs/guide.ru.md#конфиденциальность-и-согласие) перечислено, что куда передаётся.

## Документация

- [Руководство пользователя](https://github.com/wangkant/personagent/blob/main/docs/guide.ru.md): настройка, коннекторы, обучение, раздел «Активность», устранение неполадок.
- [Руководство по развёртыванию](https://github.com/wangkant/personagent/blob/main/docs/deploy.ru.md): эксплуатация в рабочей среде, расходы и что проверить, если бот перестал отвечать.
- [Протокол коннекторов](https://github.com/wangkant/personagent/blob/main/docs/connectors.ru.md): для написания собственного коннектора.
- [Инструменты](https://github.com/wangkant/personagent/blob/main/docs/tools.ru.md): скрипты в `tools/` для запуска из клона репозитория.
- [Список изменений](https://github.com/wangkant/personagent/blob/main/CHANGELOG.md) · [Участие в разработке](https://github.com/wangkant/personagent/blob/main/.github/CONTRIBUTING.md) · [Политика безопасности](https://github.com/wangkant/personagent/blob/main/.github/SECURITY.md) · [Отказ от ответственности](https://github.com/wangkant/personagent/blob/main/docs/DISCLAIMER.ru.md)

## Лицензия

personagent распространяется по лицензии [PolyForm Noncommercial License 1.0.0](https://github.com/wangkant/personagent/blob/main/LICENSE) © 2026 Qiankang (Kant) Wang: использование, изменение и распространение бесплатны в некоммерческих целях и не допускаются в коммерческих. Коннекторы в `integrations/` остаются под лицензией MIT, как и версии до 1.4.0 включительно. Три портрета персонажей распространяются по лицензии CC BY-NC-SA 4.0, авторство указано в [persona_agent/static/characters/LICENSE.md](https://github.com/wangkant/personagent/blob/main/persona_agent/static/characters/LICENSE.md).

## Благодарности

- Другие чат-платформы доступны через [AstrBot](https://github.com/AstrBotDevs/AstrBot), [NapCat](https://github.com/NapNeko/NapCatQQ), [Koishi](https://koishi.chat) с [satori-python](https://github.com/RF-Tar-Railt/satori-python) и [matrix-nio](https://github.com/matrix-nio/matrix-nio) с [мостами mautrix](https://docs.mau.fi/bridges/); подключение WeChat следует [заметкам о протоколе openclaw-weixin](https://github.com/Tencent/openclaw-weixin/blob/main/docs/protocol.md) от Tencent.
- Обучение на реакциях опирается на [Self-Feeding Chatbot](https://arxiv.org/abs/1901.05415), [самообучение Alexa](https://arxiv.org/abs/1911.02557) и [BlenderBot 3x](https://arxiv.org/abs/2306.04707); лорбук следует World Info из [SillyTavern](https://github.com/SillyTavern/SillyTavern).
