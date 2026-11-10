# personagent 배포하기

[English](deploy.md) · [简体中文](deploy.zh-CN.md) · [繁體中文](deploy.zh-TW.md) · [日本語](deploy.ja.md) · 한국어 · [Español](deploy.es.md) · [Français](deploy.fr.md) · [Deutsch](deploy.de.md) · [Português (Brasil)](deploy.pt-BR.md) · [Русский](deploy.ru.md)

[빠른 시작](start.ko.md)과 [사용자 가이드](guide.ko.md)는 첫 채팅까지 안내합니다. 설치, [홈 폴더](guide.ko.md#설치와-홈-폴더), 로컬 페이지에서의 설정, 플랫폼 연결을 다룹니다. 이 가이드는 실제 운영에 필요한 것과, 봇이 조용해졌을 때 확인할 것을 설명합니다.

## 동작하는 가장 짧은 설정

로컬 페이지(`personagent`, 터미널 마법사는 `personagent init --terminal`)는 작은 요청 한 번으로 키를 확인한 뒤 홈 폴더에 `.env`를 씁니다. 채팅에는 키가 필요하고, `.env.example`은 OpenRouter의 무료 모델로 시작합니다.

```
LLM_API_KEY=...
LLM_BASE_URL=https://openrouter.ai/api/v1
LLM_MODEL=openrouter/free
```

키만 설정한 `.env`는 `https://api.deepseek.com`과 `deepseek-flash`를 뜻합니다. 호스팅이든 로컬(Ollama, llama.cpp)이든 OpenAI 호환 엔드포인트라면 어디든 지정할 수 있습니다. API 주소는 제공업체 문서에 적힌 그대로 붙여 넣으십시오. 루트여도 되고 `.../v1`이나 `.../api/paas/v4` 같은 버전 베이스여도 됩니다. `persona.txt`를 쓰기 전까지는 함께 제공되는 `data/persona.example.<lang>.txt`가 대신합니다. `PERSONA_NAME`이 설정되기 전까지(설정 과정에서 설정됩니다) 캐릭터의 이름은 "bot"입니다.

페이지는 `PERSONA_NAME`, `AGENT_LANG`, `CONNECTOR_TOKEN`도 씁니다. 페이지에서 연결한 플랫폼은 `.env`에 더 적을 것이 없습니다. 자격 증명은 `<home>/platforms/`에 들어갑니다. `direct.json`에는 personagent가 직접 연결하는 플랫폼이, 나머지는 관리형 AstrBot의 자체 설정에 보관됩니다. 선택 항목:

```
ADMIN_IDS=telegram:12345             # the admin's accounts, <platform>:<id>
# QQ through NapCat (OneBot) only
QQ_BOT_ID=...                        # the bot account's number
CONNECTOR_QQ_PLATFORMS=aiocqhttp
```

키는 이 컴퓨터에 머무릅니다. 선택한 모델 제공업체는 대화를 볼 수 있습니다. `.env.example`의 나머지 항목에는 동작하는 기본값이 있습니다. `SERVER_HOST`와 `SERVER_PORT`는 `127.0.0.1:8080`, `QQ_ONEBOT_URL`은 비어 있고(NapCat HTTP 서버 없음), `ACCESS_GROUPS`가 비어 있으면 모든 그룹을 커넥터에 맡깁니다.

## 실행하기

`personagent`는 로컬 페이지를 엽니다. 페이지가 열려 있는 동안 에이전트, 직접 연결된 플랫폼을 유지하는 프로세스, 그리고 설치되어 있다면 관리형 AstrBot을 실행합니다. `personagent`를 다시 실행하면 열려 있는 페이지를 재사용합니다. `personagent up`은 브라우저 없이 같은 프로세스를 시작합니다.

어느 쪽이든 어떻게 끝나든 그 프로세스들은 함께 끝납니다. 이전에 충돌한 실행이 남긴 것은 다음 시작 때 중지됩니다. 각 프로세스의 로그는 `<home>/runtime/desktop/`(`agent.log`, `direct.log`, `astrbot.log`)에 기록됩니다.

로컬 페이지와 `personagent up`은 하루에 많아야 한 번 새 personagent가 나왔는지 pypi.org에 묻습니다. 나왔다면 채팅 보기와 터미널에 이 사본을 업데이트하는 명령이 표시됩니다. 요청에는 버전 번호만 담기고, `UPDATE_CHECK_ENABLED=false`로 확인을 끌 수 있습니다.

`personagent run`은 에이전트만 시작합니다. [서비스 실행하기](guide.ko.md#서비스-실행하기)에서 설명합니다. 직접 운영하는 커넥터(직접 실행하는 AstrBot, Satori, Matrix)가 연결할 때 사용하십시오. `personagent doctor`는 설정을 확인하고 모든 상위 서비스를 점검합니다.

**1.0에서 이름이 바뀐 설정.** 1.0에서 폐지된 설정 이름이 남아 있으면 시작이 종료 코드 2로 거부되고, 각각을 `OLD -> NEW`로 나열합니다. `personagent doctor --fix`는 `<home>/.env`에서 이름을 바꿉니다. 값과 주석은 유지하고, 이전 파일을 `.env.bak`으로 저장하며, 새 이름이 이미 설정된 이전 줄은 주석 처리합니다. `.env`가 아니라 환경에 설정된 폐지 이름은 설정한 곳에서 바꿔야 합니다. `personagent doctor`는 남아 있는 동안 1로 종료하고, `--json`은 `retired_settings` 아래에 나열합니다. `HOST`, `PORT`, `LOG_FILE`은 `.env`에 적혀 있을 때만 해당됩니다.

### 활동

[활동](guide.ko.md#활동)은 로컬 페이지의 보기 중 하나입니다. 추가 설치가 필요 없고, 인터넷에서 아무것도 불러오지 않으며, 키나 토큰을 보여 주지 않습니다. 로컬 페이지가 시작한 에이전트 서비스의 JSON API를 읽습니다. `personagent run`만 쓴다면 서비스 로그를 읽고 대신 `personagent learned`를 사용하십시오. `DASHBOARD_ENABLED=false`는 API를 끕니다. 그러면 보기에 그렇게 표시되고, `personagent doctor`는 `activity: off (...)`를 출력합니다.

API는 에이전트 서비스의 `/api/dashboard/` 아래에 있습니다.

- `GET conversations`와 `GET conversation?id=<chat id>`는 서비스가 알고 있는 채팅과 채팅 하나의 세부 내용을 읽습니다.
- `POST candidates/<id>/promote`, `replace`, `reject`, `rollback`은 학습한 내용을 바꿉니다. 각 변경은 `personagent learned`와 같은 학습 기록에 행위자 `dashboard`로 기록됩니다.
- `POST memory/forget`은 본문 `{"conv": "<chat id>", "note": "<note id>"}`로 기억 메모 하나를 삭제합니다. `conv`와 id는 `GET conversation`의 `memories` 항목에 있는 값입니다. `note`가 없으면 그 채팅의 핵심 메모를 삭제합니다.

모든 호출에는 런타임 폴더(`AGENT_RUNTIME_DIR`로 옮기지 않으면 `<home>/runtime/`)의 `dashboard.token`에 있는 토큰을 `X-Personagent-Dashboard-Token` 헤더에 담아야 합니다. 이 파일은 소유자만 읽을 수 있고, 서비스가 시작할 때 만듭니다. 헤더가 없는 호출은 401(`dashboard_token`), 잘못된 토큰은 403(`wrong_token`)을 받습니다. `CONNECTOR_TOKEN`과 `X-Personagent-Token`으로는 열 수 없습니다. 이들은 커넥터와 `/health/details` 전용입니다.

- 쓰기에는 `X-Personagent-Dashboard: 1`과 `Content-Type: application/json`도 필요합니다. 요청이 `Origin`을 보낸다면 서비스 자신의 것이어야 합니다.
- 브라우저의 교차 사이트 요청은 거부됩니다.
- 응답에서는 모든 자격 증명이 `***`로 바뀝니다. 시작 점검의 URL은 사용자 이름, 비밀번호, 쿼리도 가려집니다.
- 같은 컴퓨터의 스크립트는 로컬 페이지와 같은 방식으로 API를 호출할 수 있습니다.

서비스는 페이지를 제공하지 않습니다. `GET /`은 로컬 페이지와 `personagent learned`를 안내하는 짧은 메모를 돌려주며, 예전 `?token=` 링크도 이제 이것을 엽니다. 로컬 페이지는 127.0.0.1에만 바인딩됩니다. 로컬 페이지가 없는 서버에서는 `personagent learned`로 학습 내용을 검토하고 뒤집으십시오.

## 호스트가 제공해야 하는 것

1. **쓰기 가능한 홈.** 시작할 때 `runtime/` 밖의 `<home>/.personagent.instance.lock`에 잠금을 겁니다. 읽기 전용 홈은 시작에 실패합니다.
2. **홈 하나에 프로세스 하나.** 같은 홈에서 두 번째 `personagent run`을 실행하면 그렇다고 한 문장으로 알리고 종료합니다.
3. **비어 있는 포트.** 사용 중이거나 금지된 포트도 한 문장으로 알리고 종료합니다. `--port`나 `SERVER_PORT`로 다른 포트를 고르십시오.

`AGENT_RUNTIME_DIR`은 홈 아래로 해석되어야 하며, 그렇지 않으면 시작에 실패합니다. 상대 경로의 `PERSONA_FILE`이나 `PERSONA_CARD_FILE`도 홈 아래로 해석되므로, 다른 곳에 둔 페르소나에는 절대 경로가 필요합니다.

## 플랫폼 연결하기

로컬 페이지의 **플랫폼 연결**에서 플랫폼을 추가하십시오. personagent는 무언가를 저장하기 전에 자격 증명을 플랫폼에 확인합니다. 플랫폼이 거부하면 페이지에 거부 내용이 표시되고 아무것도 남지 않습니다.

디스플레이가 없는 서버에서는 personagent가 직접 연결하는 플랫폼을 터미널에서 `personagent connect <platform>`(예: `personagent connect telegram`)으로 연결하십시오. 이 명령은 페이지와 같은 단계와 확인을 거쳐 값을 같은 형식으로 저장합니다. QQ와 WeChat은 터미널에 QR 코드를 표시하고, Twitch는 링크와 코드를 출력합니다. `--no-input`을 지정하고 모든 값을 옵션으로 주면 명령은 아무것도 묻지 않으며, 필수 값이 없으면 코드 2로 종료합니다. 그런 다음 `personagent up`이 personagent를 연결된 플랫폼과 함께 시작합니다. [명령과 옵션](guide.ko.md#터미널에서-플랫폼-연결하기)은 사용자 가이드에서 설명합니다.

**personagent가 직접 연결하는 것.** QQ, 개인 WeChat, Telegram, Discord, Matrix, Twitch, IRC, Zulip, VK, Stoat는 하나의 "direct" 프로세스에서 실행되며 AstrBot도 NapCat도 필요하지 않습니다. 불러올 수 없는 플랫폼은 건너뛰고 나머지 플랫폼은 그대로 시작합니다. 아래 표는 처음 네 개 플랫폼을 다룹니다. 나머지 여섯 개 플랫폼에 필요한 사항과 제한은 사용자 가이드의 [해당 절](guide.ko.md#personagent가-직접-연결하는-플랫폼)에 나와 있습니다.

| 플랫폼 | 할 일 | 제한 |
|---|---|---|
| QQ(공식 봇) | 모바일 QQ로 QR 코드를 스캔하면 QQ가 봇을 만들거나 만들어 둔 봇을 고릅니다. AppID와 AppSecret 붙여 넣기는 대체 수단입니다. | 봇이 인증되기 전까지 QQ는 사용자가 소유한 그룹에만 참여를 허용합니다. 그룹 메시지 권한은 QQ에서 설정합니다. |
| 개인 WeChat | WeChat으로 스캔합니다(Tencent의 iLink 봇 API). | 일대일 채팅만 가능합니다. WeChat은 이런 봇에 그룹 메시지를 주지 않습니다. |
| Telegram | @BotFather의 토큰을 붙여 넣습니다. | |
| Discord | 봇 토큰을 붙여 넣고 Message Content Intent를 켭니다. | |

**관리형 AstrBot을 통해.** 다른 모든 플랫폼은 personagent가 자체 Python 3.12 런타임과 함께 내려받아 헤드리스로 실행하는 AstrBot을 거칩니다. 대시보드가 없고 두 번째 로그인도 필요 없습니다. KOOK, Feishu/Lark(장기 연결), DingTalk(Stream 모드), Slack(Socket Mode, 가이드 링크가 앱을 미리 채워 줍니다), WeCom AI 봇(장기 연결), Mattermost, Misskey는 값을 한두 개 묻습니다. 고급 그룹에는 공개 주소나 다른 소프트웨어가 필요합니다. WeCom 앱, WeChat 공식 계정, QQ 웹훅, OneBot v11(NapCat), Satori가 이에 해당합니다. LINE은 제공하지 않습니다.

두 경로 모두 연결된 플랫폼은 플랫폼이 봇에 전달하는 모든 그룹과 DM에 답합니다. `ACCESS_GROUPS`나 `ACCESS_DM_USERS`에 그 플랫폼 항목이 생기면 달라집니다([personagent 자체 허용 목록](#이미-실행-중인-astrbot을-통해) 참고). ID는 `<platform>:<id>` 형식으로 도착합니다. 예를 들어 `qq_official:<openid>`, `weixin_oc:<id>`, `telegram:<id>`, `discord:<id>`입니다. QQ 공식 봇에는 QQ 번호가 아니라 openid가 보입니다. 플랫폼을 직접 연결하면 같은 플랫폼의 AstrBot 연결은 제거됩니다.

## 이미 실행 중인 AstrBot을 통해

AstrBot, NapCat(OneBot), Koishi([Satori 커넥터](../integrations/satori/README.ko.md) 경유), Matrix([Matrix 커넥터](../integrations/matrix/README.ko.md)와 mautrix 브리지 경유)는 personagent와 함께 동작하는 서드파티 브리지입니다. personagent가 직접 연결하는 플랫폼에는 이 중 어느 것도 필요하지 않습니다.

AstrBot은 `integrations/astrbot/astrbot_plugin_personagent/`의 플러그인을 통해 personagent에 메시지를 넘깁니다. 플러그인은 각 메시지를 `POST /v1/events`로 보내고 응답의 답장을 전달합니다. personagent의 아웃박스도 가져오므로(`outbox_enabled`, 기본값 켜짐), 플랫폼이 봇에 허용하는 곳에서는 페르소나가 먼저 말할 수 있습니다. 표는 플러그인 README에 있습니다. 관리형 AstrBot에는 플러그인이 자동으로 들어갑니다. 직접 운영하는 AstrBot은 한 번 시작해서 데이터 폴더(`cmd_config.json`, `plugins/`, `config/`가 있는 폴더)를 만들게 한 다음 실행하십시오.

```
personagent connect astrbot                       # asks, and finds AstrBot's folder itself
personagent connect astrbot <AstrBot data dir>    # asks nothing
```

이 명령은 플러그인을 `<data dir>/plugins/`에 복사하고 같은 `CONNECTOR_TOKEN`을 `.env`와 플러그인 설정 양쪽에 씁니다. 플러그인에 이미 허용되는 URL(터널을 포함한 루프백 URL 또는 HTTPS)이 없다면 `personagent_url`을 `http://127.0.0.1:<SERVER_PORT>`로 설정합니다.

다른 컴퓨터의 AstrBot이라면 [최신 릴리스](https://github.com/wangkant/personagent/releases/latest)에서 `astrbot_plugin_personagent.zip`을 내려받아 AstrBot 플러그인 페이지의 **Install from File**에서 업로드하십시오. `connector_token`을 personagent `.env`의 `CONNECTOR_TOKEN`으로, `personagent_url`을 personagent의 HTTPS 주소로 설정하십시오([엔드포인트 공개하기](#엔드포인트-공개하기) 참고).

personagent를 업그레이드한 뒤에는 `connect astrbot`을 다시 실행하거나 새 zip을 업로드하십시오. AstrBot 4.29 이상은 설치된 사본을 교체합니다. 더 오래된 버전은 먼저 제거하되 **Also delete plugin configuration file**은 체크하지 마십시오.

`connect astrbot` 옵션:

- `--qq`는 `excluded_platforms`에서 `aiocqhttp`를 빼고, `--no-qq`는 되돌립니다. 둘 다 없으면 QQ 경로는 그대로입니다. `CONNECTOR_QQ_PLATFORMS`는 플러그인의 최종 동작을 따라갑니다.
- `--platform qq_official|telegram|discord|slack|kook|lark --token <token>`은 AstrBot 자체 설정에서 그 어댑터도 켭니다. Slack은 `--app-token`도, Lark와 QQ는 `--app-id`와 `--app-secret`도 받습니다. 이미 있는 어댑터 항목은 다른 설정(프록시, 베이스 URL, 폴링)을 유지하고 새 자격 증명만 받습니다.
- `--url https://...`는 플러그인이 보낼 HTTPS 주소를 설정합니다.
- `--install`은 대신 관리형 AstrBot을 내려받고, `--start`는 그것을 시작합니다.

첫 실행에서는 허용 목록이 비어 있습니다. 다시 실행하면 다른 제외 플랫폼과 함께 유지됩니다.

플러그인의 기본값은 거부입니다. AstrBot WebUI에서 `groups`와, DM을 위해 `dm_users`를 채우거나 `connect`의 질문에 답하십시오. DM은 `dm_users`가 비어 있지 않으면 전달됩니다. [플러그인 README](../integrations/astrbot/astrbot_plugin_personagent/README.ko.md)에 모든 키가 있습니다. 관리형 AstrBot은 연결한 각 플랫폼을 `<platform>:*`로 엽니다. 플러그인을 설치한 뒤에는 AstrBot을 재시작하거나 WebUI에서 플러그인을 다시 불러오십시오. personagent 쪽에서는:

- `CONNECTOR_TOKEN`은 각 요청을 인증합니다. 요청에는 `X-Personagent-Token` 헤더와, 토큰을 키로 `timestamp.nonce.body`에 계산한 HMAC-SHA256이 담기고, 재전송 방지가 재사용된 nonce를 거부합니다. 가로챈 요청은 재전송하거나 변조할 수 없습니다. 토큰은 서명 키이기도 하므로 로그에 남기지 말고, 유출되면 교체하십시오. 한 호스트에서는 선택이고, 호스트 간에는 필수입니다.
- `ADMIN_IDS`는 관리자의 계정을 `<platform>:<id>`(`telegram:12345`, `discord:4242`)로 나열합니다. ID만 있거나 `qq:<id>`면 QQ 번호입니다. `ADMIN_NAME`은 관리자의 이름을 설정합니다. 나열된 계정은 모두 한 사람의 것이고, 그 사람은 그룹과 DM에서 더 친밀한 페르소나를 받으며, 봇이 그룹에 대해 기억하는 내용을 관리할 수 있고, 혼자서 가르칠 수 있습니다. AstrBot을 통할 때 플랫폼은 AstrBot이 보여 주는 어댑터 이름이고, 채팅에서 `/sid`를 쓰면 ID가 표시됩니다.
- `ACCESS_GROUPS`와 `ACCESS_DM_USERS`는 같은 `<platform>:<id>` 형식으로 personagent가 직접 플랫폼을 제한하게 합니다. 플랫폼마다 따로 제한됩니다. 항목이 없는 플랫폼은 커넥터에 맡겨지고, 항목이 하나라도 있으면 그 플랫폼은 항목으로만 제한됩니다. personagent가 거부한 턴은 처리되지 않은 채 돌아가므로 AstrBot 자체 모델이 답할 수 있습니다.

Docker나 다른 호스트의 AstrBot은 [사용자 가이드](guide.ko.md#직접-실행하는-브리지)를 참고하십시오.

### NapCat(OneBot)을 통한 QQ

이 경로는 공식 봇 대신 개인 QQ 계정을 사용합니다. 대상 그룹에 사용자 본인의 계정이 아닌 두 번째 QQ 계정이 필요합니다([DISCLAIMER.md](DISCLAIMER.ko.md) 참고). 보통 QR 코드로, 재시작 후에도 유지되는 세션으로, AstrBot의 `aiocqhttp` 어댑터에 연결된 OneBot v11 구현에 로그인합니다. [NapCat](https://github.com/NapNeko/NapCatQQ)은 테스트되었고 QQ NT 데스크톱 클라이언트에 붙습니다. LLOneBot과 Lagrange도 OneBot v11 구현입니다.

관리형 AstrBot에서는 로컬 페이지에서 **고급 > OneBot v11 (NapCat)**을 추가하고 NapCat을 `ws://127.0.0.1:6199/ws`로 지정하십시오. [중국어 가이드](deploy.zh-CN.md)에 단계별 설명이 있습니다. 직접 운영하는 AstrBot에서는 플러그인의 `excluded_platforms`에서 `aiocqhttp`를 빼고, `CONNECTOR_QQ_PLATFORMS=aiocqhttp`를 설정하고(`--qq`가 둘 다 해 줍니다), `QQ_BOT_ID`를 설정하십시오(`personagent connect astrbot`이 묻습니다).

**여기서는 `CONNECTOR_QQ_PLATFORMS`가 필수입니다.** 없으면 QQ ID가 네임스페이스가 붙은 채(`aiocqhttp:123456`) 도착해 모든 대화가 새것처럼 보입니다. 기억, 기록, 학습한 예시는 접두사 없는 ID를 키로 쓰고, 학습 기록은 대화 ID에서 행 ID를 만들기 때문에 갈라진 것은 나중에 복구할 수 없습니다.

접두사 없는 ID는 QQ 권한을 가지므로, `ADMIN_IDS`, `ACCESS_GROUPS`, `ACCESS_DM_USERS`의 QQ 항목은 플러그인 허용 목록 위에 추가로 적용됩니다. QQ DM은 `dm_users`에 있고 *동시에* 관리자나 `ACCESS_DM_USERS` 항목에서 와야 합니다. `ACCESS_GROUPS`에 QQ 그룹이 있으면 QQ 그룹은 양쪽에 모두 있어야 합니다. 그 권한을 커넥터에 맡길 수 있을 때만 플랫폼을 `CONNECTOR_QQ_PLATFORMS`에 넣으십시오.

**NapCat의 HTTP 서버**(`QQ_ONEBOT_URL`, 기본값은 비어 있음)는 이 경로에서 선택 사항입니다. personagent는 스스로도 메시지를 보냅니다.

- 자발적 메시지(`PROACTIVE_ENABLED`, 기본값 꺼짐)
- 거부 2분 뒤에 묻는 질문(`REACT_ELICIT_ENABLED`)
- 모델 호출이 실패했을 때 그룹에 보내는 변명

이것들은 플러그인이 가져오는 동안에는 플러그인의 아웃박스를 통해 돌아갑니다. 가져오지 않을 때는 URL이 설정되어 있으면 `QQ_ONEBOT_URL`로 갑니다. 서버가 필요한 것은 오프라인 동안 놓친 @ 멘션 훑기뿐이며, `QQ_BOT_ID`도 함께 필요합니다. 훑기는 시작할 때와 그 뒤 30분마다 실행됩니다. `ACCESS_GROUPS`의 QQ 그룹과 마지막 재시작 이후 활동이 있던 그룹을 대상으로 한 시간 이내의 @ 멘션을 재생합니다. URL이 비어 있으면 `personagent doctor`는 OneBot 브리지를 "not configured"로 표시합니다.

**모든 커넥터 경로에서 잃는 것**(직접, AstrBot, 다른 커넥터). 되돌리는 설정은 없습니다.

- 비전 모델이 설명하지 못한 이미지의 OCR 대체 처리
- NapCat을 통한 인용 조회. 인용은 personagent 자체의 최근 메시지 색인과, 커넥터가 인용과 함께 보내는 인용 텍스트로 해석합니다
- 그룹에 올라온 이미지에서 새 스티커 수집

## 플랫폼 여러 개

각 커넥터가 플랫폼 이름을 붙이므로(`telegram:-1001234`, `matrix:!room:example.org`) 여러 커넥터를 하나의 personagent에 나란히 실행할 수 있습니다. direct 프로세스, AstrBot, Satori, Matrix를 모두 동시에 실행할 수 있습니다. 한 채팅을 두 커넥터로 들여오지 마십시오. 모든 메시지가 두 번 도착합니다. 네임스페이스가 붙은 ID는 접두사 없는 QQ 번호와 충돌하지 않습니다.

아무도 요청하지 않은 메시지는 personagent의 아웃박스를 가져오는 커넥터를 통해 플랫폼에 도달합니다. 자발적으로 말을 거는 메시지, 거부 뒤에 묻는 질문, 그룹에서 모델 호출이 실패했을 때의 변명이 이에 해당합니다. DM의 변명은 메시지를 가져온 요청의 응답으로 돌아갑니다.

direct 프로세스와 여기 있는 세 커넥터는 봇이 먼저 보낼 수 있는 플랫폼에서 아웃박스를 가져옵니다. QQ는 공식 봇의 자발적 메시지에 속도 제한을 두며, 상대방이 끌 수도 있습니다. 직접 만든 커넥터는 이벤트와 함께 `connector_id`, `reply_handle`, `"capabilities": ["outbox"]`를 보내고 `/v1/outbox`를 롱 폴링합니다([커넥터 프로토콜](connectors.ko.md) 참고). 그런 커넥터가 없으면 personagent는 메시지를 가져온 요청 안에서만 말합니다. 자발 루프는 그 대화를 건너뛰고, 질문과 변명은 보내지지 않습니다.

로컬 페이지도 아웃박스를 가져오지만, 페이지 자체의 채팅에 대해서만 가져옵니다. 아웃박스를 가져오지 않는 프로그램(채팅에서 말하는 코딩 어시스턴트 등)에서 온 이벤트 때문에 아웃박스를 가져오는 커넥터가 그 채팅을 잃지는 않습니다([커넥터 프로토콜](connectors.ko.md#아웃박스-post-v1outbox) 참고).

`PROACTIVE_PLATFORMS`는 자발 루프가 먼저 말할 수 있는 곳을 제한합니다. `PROACTIVE_PLATFORMS=qq_official`은 QQ 공식 봇으로, `qq`는 NapCat을 통한 QQ로 한정합니다. `CONNECTOR_OUTBOX_ENABLED=false`는 아웃박스를 완전히 끕니다.

아웃박스 없이 DM에서 먼저 발언하려면, 직접 운영하는 스케줄러(AstrBot 플러그인 작업, cron 항목)가 `"proactive": true`를 표시한 DM 이벤트를 보낼 수 있습니다. [아웃박스 없이 먼저 발언하기](connectors.ko.md#아웃박스-없이-먼저-발언하기)를 참고하십시오.

## 엔드포인트 공개하기

커넥터와 personagent가 같은 컴퓨터에 있으면 `SERVER_HOST=127.0.0.1`을 유지하십시오. 컨테이너는 호스트의 네트워크 네임스페이스나 호스트 네트워킹을 쓸 때만 같은 컴퓨터로 간주합니다. 로컬 페이지와 `personagent up`은 항상 `127.0.0.1`에 바인딩합니다. 그 밖의 경우:

1. `SERVER_HOST=0.0.0.0`(또는 `--host 0.0.0.0`)과 `CONNECTOR_TOKEN`을 설정하십시오. 토큰 없는 네트워크 바인딩은 시작이 거부됩니다. `QQ_ONEBOT_SECRET`은 필수가 아니지만, 없으면 폐지 예정인 `/v1/onebot`이 네트워크 바인딩에서 꺼집니다. 그곳으로 가는 모든 요청은 403 `onebot_disabled`를 받고, 로그에 이유가 한 번 기록됩니다.
2. 앞단에 HTTPS 리버스 프록시나 사설 터널을 두십시오. 여기 있는 모든 커넥터는 루프백이나 토큰이 설정된 HTTPS로만 보냅니다. AstrBot 플러그인은 그 외를 `refusing unsafe personagent_url`로 기록하고, Satori와 Matrix 커넥터는 시작을 거부합니다.
3. 서명이 본문을 포함하므로 본문을 한 바이트도 바꾸지 말고, 시계 차이를 5분 이내로 유지하십시오.

자격 증명이 비어 있으면 그 엔드포인트는 `http://127.0.0.1`이나 `http://localhost`를 직접 호출하는 로컬 프로그램만 응대합니다. 다음 중 하나라도 있는 요청은 403 `non_local_request`를 받습니다.

- `Origin` 헤더
- `none`이 아닌 `Sec-Fetch-Site`
- `localhost`, `127.0.0.1`, `::1`이 아닌 `Host`
- 프록시 헤더: `X-Forwarded-For`, `Forwarded`, `X-Real-IP`, `CF-Connecting-IP`, `Via`, `X-Forwarded-Host`, `X-Forwarded-Proto`, `X-Forwarded-Port`, `True-Client-IP`, `X-Client-IP`, `X-Original-Forwarded-For`

같은 호스트의 프록시가 이 중 아무것도 붙이지 않으면 여전히 로컬로 보입니다. 한 호스트에서도 프록시나 터널을 추가하기 전에 `CONNECTOR_TOKEN`(`/v1/onebot`을 쓴다면 `QQ_ONEBOT_SECRET`도)을 설정하십시오.

## 상태 엔드포인트

- `GET /health`는 무료이고 공개되어 있으며 아무것도 호출하지 않습니다.
- `GET /health/details`는 상위 서비스를 점검합니다(60초 캐시). `CONNECTOR_TOKEN`이 비어 있으면 로컬 요청에만 답합니다. 토큰이 설정되어 있으면 루프백에서 온 것이라도 일치하는 `X-Personagent-Token` 헤더가 있는 요청에**만** 답합니다. 중요한 점검이 실패하거나 실행할 수 없으면 503을 돌려줍니다. 중요한 점검은 채팅 모델과, QQ가 직접 OneBot 수신을 쓸 때(`QQ_BOT_ID`와 `QQ_ONEBOT_URL`이 설정되고 `CONNECTOR_QQ_PLATFORMS`가 없을 때)의 OneBot 브리지입니다.
- `personagent doctor [--json]`은 같은 점검에 설정 확인을 더해 실행하고, 같은 경우에 0이 아닌 값으로 종료합니다. 마지막 업데이트 확인이 하루 지났으면 pypi.org에 최신 버전도 묻습니다(`UPDATE_CHECK_ENABLED=false`로 건너뛸 수 있습니다).

## 비용

- **점검은 크레딧을 씁니다.** `personagent doctor`와 `/health/details`는 설정된 각 모델 엔드포인트(채팅, DM, 평가, 비전)에 아주 작은 채팅 완성을 한 번 보냅니다. `EMBEDDING_MODEL`이 있으면 임베딩을 한 번, `TAVILY_API_KEY`가 있으면 Tavily 검색을 한 번 보냅니다. `/health`와 설정 및 학습 기록 확인은 무료입니다.
- **`tools/`의 스크립트**는 제각각입니다. 무료인 것도 모델을 호출하는 것도 있습니다. [tools.md](tools.ko.md)의 표에 나와 있습니다.
- **`personagent eval`**은 케이스마다 모델을 호출합니다. 페르소나와 학습 스위트에는 판정용 두 번째 모델(`BENCH_JUDGE_MODEL`)도 필요합니다.
- **메모리.** 네임스페이스가 붙은(QQ 외) 대화가 256개를 넘으면 가장 오래 활동이 없던 유휴 대화가 최근 기록과 대기 중인 반응을 잃습니다. 장기 기억, 핵심 메모, 학습 기록은 남습니다. 요청 처리 중인 대화는 절대 밀려나지 않습니다. 장기 기억은 시작할 때 디스크에서 불러오며 이 상한의 대상이 아닙니다.
- **디스크.** `runtime/`의 증거 로그와 후보 학습 기록은 추가 전용이고 잘리지 않습니다. `personagent doctor`는 어느 쪽이든 50MB를 넘으면 경고합니다(`LEDGER_EVIDENCE_WARN_BYTES`, `LEDGER_CANDIDATES_WARN_BYTES`). 봇이 배운 모든 것이 들어 있으니 `runtime/`을 백업하십시오.

## 봇이 조용해졌을 때

원인은 흔한 순서로 나열했습니다. 로컬 페이지가 에이전트를 실행한다면 [활동](guide.ko.md#활동)에서 메시지가 도착하는지, 왜 조용했는지 알 수 있습니다. 서버에서는 서비스 로그를 읽고, 학습 내용은 `personagent learned`를 사용하십시오.

1. **아무것도 도착하지 않습니다.** 로컬 페이지에서 플랫폼이 연결됨으로 표시되는지 확인하고 `runtime/desktop/direct.log`나 `astrbot.log`를 읽으십시오. QQ 공식 봇은 그룹에 있어야 하고, 어떤 그룹 메시지를 받을지는 QQ가 정합니다. 개인 WeChat 봇은 그룹을 받지 않습니다. 직접 실행하는 AstrBot에서는 플러그인의 `groups`(DM은 `dm_users`도)를 채우고, NapCat이라면 `excluded_platforms`에서 `aiocqhttp`를 빼십시오. Satori와 Matrix 커넥터는 각자의 `.env`에 자체 허용 목록이 있습니다. 각 README를 참고하십시오. 이 경우 채팅은 활동에 나타나지 않습니다.
2. **에이전트가 꺼져 있습니다.** `personagent run` 배너에 `agent: OFF`와 이유, 해결법이 표시됩니다. `LLM_API_KEY`가 없으면 로컬 페이지에서 키를 추가하고(또는 `LLM_API_KEY`를 설정하고) 재시작하십시오. `AGENT_ENABLED=false`라면 `<home>/.env`에서 `true`로 바꾸고 재시작하십시오. 그때까지 모든 이벤트는 `owned: false`를 받고, 첫 이벤트에서 같은 조언을 담은 ERROR 줄이 한 번 기록됩니다.
3. **대신 AstrBot 자체 모델이 답합니다.** 요청이 실패했거나, personagent가 메시지를 돌려보냈거나(항목 5), 에이전트가 꺼져 있어서(항목 2) 플러그인이 대체 동작을 했습니다. AstrBot 로그에 `refusing unsafe personagent_url`, `agent refused the request (403): <message>`(또는 다른 상태, 아래 표 참고), `timed out waiting for the agent`가 나옵니다. `timeout_s`는 디바운스와 턴 안의 모델 호출에 더해, 메시지가 도착했을 때 생각 중이던 턴까지 포함해야 합니다. 그룹이든 DM이든 한 턴의 모델 호출은 모두 합쳐 1.5 × `LLM_TIMEOUT_S`까지이므로 3 × `LLM_TIMEOUT_S`를 그보다 작게 유지하십시오. 기본값(420)은 에이전트 기본값(3 × 120 = 360초)을 포함합니다. `LLM_TIMEOUT_S`를 올리면 이것도 올리십시오.
4. **부르지 않았습니다.** 그룹에서는 이름(`PERSONA_NAME`)이나 @에 답합니다. 그렇지 않으면 대화가 충분히 쌓이기를 기다리고(`CHAT_TRIGGER_COUNT`, 기본값 30개 메시지) 그래도 넘어갈 수 있습니다. 해당 시간대의 02:00부터 07:00까지는 부르지 않은 채팅에 대부분 끼어들지 않습니다. 시간대는 `PERSONA_TZ_OFFSET_HOURS`입니다. 비워 두면 `AGENT_LANG`이 `zh`나 `zh-TW`일 때 UTC+8, 그 외에는 이 컴퓨터의 오프셋입니다. 활동에 최근 각 턴의 이유가 표시됩니다. 같은 판단을 오프라인으로 보려면 `personagent chat --trigger 4`를 실행하십시오.
5. **personagent의 허용 목록.** `ACCESS_GROUPS`와 `ACCESS_DM_USERS`는 모든 경로에 적용되고, 접두사 없는 ID의 QQ DM에는 관리자나 항목도 필요합니다. 이들이 돌려보낸 메시지는 처리되지 않은 채 돌아가므로 AstrBot을 통하면 그 모델이 답할 수 있습니다. personagent는 거부한 각 대화를 거부한 설정과 함께 INFO로 한 번 기록합니다.
6. **모델 호출이 실패합니다.** 거부된 키(401 또는 403)나 잔액 부족(402 또는 할당량 소진)은 제공업체 호스트와 고칠 설정을 알려 주는 ERROR 줄을 한 번 기록합니다. `personagent doctor`를 실행하십시오. 각 모델 엔드포인트에 아주 작은 요청을 보내 상태를 보여 주므로 잘못된 `LLM_BASE_URL`이나 `LLM_MODEL`도 잡아냅니다. 모델이 내려가 있는 동안 페르소나는 불리면 캐릭터다운 짧은 변명을 보냅니다. 대화당 5분에 한 번까지입니다.
7. **설정 이름 오타.** 시작 로그와 `personagent doctor`는 `.env.example`이 모르는 모든 키와 `#`으로 시작하는 값을 나열합니다.
8. **`.env`의 BOM.** 첫 번째 설정의 이름에 BOM이 붙어 프로세스에 도달하지 못합니다. 시작할 때와 `personagent doctor`가 알려 줍니다. BOM 없는 UTF-8로 다시 저장하십시오.
9. **NapCat에서 `QQ_BOT_ID`가 없거나 틀렸습니다.** AstrBot을 통하면 @ 멘션은 동작하지만, 놓친 멘션 훑기가 이것으로 대조합니다. 직접 OneBot 수신에서는 @ 멘션이 인식되지 않습니다. 봇은 문제없이 시작하고, 아무것도 기록하지 않고, 답하지 않습니다. `personagent doctor`는 `QQ_BOT_ID`가 비어 있고 다른 QQ 설정이 있으면 경고합니다. QQ 공식 봇은 이것을 쓰지 않습니다.
10. **답은 하는데 배운 것을 잊었습니다.** NapCat QQ가 `CONNECTOR_QQ_PLATFORMS=aiocqhttp` 없이 도착하고 있거나, `PERSONA_NAME`이나 `PERSONA_VERSION`이 바뀌어 새 캐릭터가 시작된 것입니다. 이전 캐릭터의 승격된 내용이 통째로 거부되면 로그가 경고합니다. `persona.txt`를 편집하는 것은 페이지의 페르소나 칸에서 하더라도 새 캐릭터를 시작하지 않습니다. 하나의 `PERSONA_VERSION` 아래의 개정은 학습 범위를 공유합니다(`runtime/persona_lineage.json`). 계보에 없는 페르소나 해시로 학습된 행을 합치려면 `personagent learned lineage adopt <hash>`를 실행한 뒤 `personagent learned rebuild`를 실행하십시오. 해시는 `personagent learned show <id>`의 후보 범위에 있습니다. `AGENT_LANG`을 중국어와 다른 언어 사이에서 옮기면 `runtime/`의 다른 학습 파일로도 전환됩니다.

`/v1/events`의 오류는 아래와 같습니다. AstrBot 플러그인은 메시지를 기록하고, `code`는 클라이언트가 분기에 쓸 수 있는 안정적인 필드입니다.

| 상태 | `code` | AstrBot 로그의 메시지 | 원인 |
|---|---|---|---|
| 403 | `unauthenticated` | authentication required | `CONNECTOR_TOKEN`이 없고 호출자가 이 컴퓨터에 있지 않음 |
| 403 | `non_local_request` | no credential is configured; only local requests accepted | `CONNECTOR_TOKEN`이 없고 요청이 브라우저, 프록시, 또는 다른 호스트 이름을 거쳐 옴 |
| 403 | `invalid_envelope` | invalid, stale, or replayed request envelope | 토큰, 헤더, 서명의 누락 또는 오류, 5분을 넘는 시계 차이, 재사용된 nonce, 또는 재전송 방지 가득 참(에이전트 로그의 `connector replay guard full`) |
| 403 | `stale_event` | stale or invalid sent_at | `sent_at`이 현재와 `CONNECTOR_MAX_EVENT_AGE_S`(24시간)를 넘게 차이 남. 미래 또는 밀리초 타임스탬프 포함 |
| 400 | `invalid_schema` | invalid event schema | 필수 필드 누락: `platform`, `conversation_type`, `sender_id`, `message_id`, `sent_at`, 그룹은 `conversation_id` |
| 400 | `client_disconnected` | client disconnected | 호출자가 보내는 도중 연결을 끊음 |
| 408 | `body_timeout` | request body not received in time | 본문 도착에 30초를 넘게 걸림 |
| 413 | `body_too_large` | request body too large | `SERVER_MAX_BODY_BYTES`(8MB) 초과. 대개 인라인 이미지 |
| 429 | `capacity_exceeded` | webhook capacity exceeded | 처리 중인 턴이 `CONNECTOR_MAX_INFLIGHT`를 초과함. 3초 뒤 다시 시도하십시오 |

## 레거시: 직접 OneBot 수신

NapCat의 웹훅은 여전히 `POST /v1/onebot`으로 이벤트를 보낼 수 있고, personagent는 `QQ_ONEBOT_URL`을 통해 답합니다. 이 경로는 폐지 예정이며 1.x 동안 유지됩니다. 대신 QQ 공식 봇 연결이나 `CONNECTOR_QQ_PLATFORMS=aiocqhttp`를 쓰는 AstrBot 경유 NapCat을 사용하십시오. 이 경로는 처음 사용할 때 한 번 경고하고 모든 응답에 `Deprecation: true`를 표시합니다.

AstrBot 경유 NapCat으로 옮기려면 로컬 페이지에서 OneBot v11(NapCat)을 추가하거나, 직접 운영하는 AstrBot이라면 `personagent connect astrbot <AstrBot data dir> --qq`를 실행하고 허용 목록을 채우십시오. NapCat의 WebSocket 클라이언트를 거기로 지정하고 NapCat의 HTTP 클라이언트를 끄십시오(HTTP 서버는 유지). `CONNECTOR_QQ_PLATFORMS`가 ID를 유지하므로 기억과 학습은 이어집니다.

레거시 경로를 아직 쓴다면:

- [NapCat 문서](https://napneko.github.io/)대로 양방향을 설정하십시오. 보내기용으로 `QQ_ONEBOT_URL`의 **HTTP 서버**와, `http://127.0.0.1:8080/v1/onebot`(`SERVER_HOST`, `SERVER_PORT`)으로 보내는 **HTTP 클라이언트**가 필요합니다. `QQ_ONEBOT_URL`은 기본값이 비어 있으니 `.env`에 쓰십시오. 없으면 봇이 받기만 하고 답하지 않습니다. 프리플라이트와 `personagent doctor`는 이 경로가 설정된 것처럼 보이는데(`QQ_BOT_ID`나 `QQ_ONEBOT_SECRET`이 설정되고 `CONNECTOR_QQ_PLATFORMS`가 비어 있음) `QQ_ONEBOT_URL`이 비어 있으면 경고합니다.
- NapCat이 다른 컴퓨터에 있으면 `QQ_ONEBOT_SECRET`을 HTTP 클라이언트의 `secret`으로 설정하십시오. 그렇지 않으면 포트에 닿는 누구나 이벤트를 위조할 수 있습니다. 그러면 본문에 `x-signature: sha1=<hex>`가 있어야 하고(403 `bad_signature`), 타임스탬프가 5분을 넘게 어긋난 이벤트는 403 `stale_event`를 받습니다. 시크릿이 없으면 이 경로는 이 호스트의 프로그램에만 답하고, 네트워크 바인딩에서는 꺼집니다(403 `onebot_disabled`).
- 같은 계정으로 AstrBot을 쓴다면 `aiocqhttp`를 `excluded_platforms`에 그대로 두십시오. 그렇지 않으면 모든 메시지가 두 번 도착합니다.

보내기는 `curl http://127.0.0.1:3000/get_login_info`로 확인하십시오. 받기는 그룹에서 봇에 메시지를 보내면서 personagent 로그를 지켜보며 확인하십시오.
