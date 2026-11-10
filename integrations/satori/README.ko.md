# Satori 커넥터

[English](README.md) · [简体中文](README.zh-CN.md) · [繁體中文](README.zh-TW.md) · [日本語](README.ja.md) · 한국어 · [Español](README.es.md) · [Français](README.fr.md) · [Deutsch](README.de.md) · [Português (Brasil)](README.pt-BR.md) · [Русский](README.ru.md)


이 커넥터는 [personagent](https://github.com/wangkant/personagent)를 [Satori](https://satori.chat) 서버에 연결합니다. Satori는 크로스 플랫폼 채팅 프로토콜입니다. [Koishi](https://koishi.chat)(`server-satori` 플러그인 포함), Chronocat, LLOneBot 같은 서버가 채팅 플랫폼에 로그인하고, 이런 클라이언트는 웹소켓 하나로 모든 로그인의 모든 메시지를 받습니다. 그래서 커넥터 프로세스 하나로 서버에 어댑터가 있는 모든 플랫폼에 페르소나를 둘 수 있습니다.

Satori와 Koishi는 서드파티 소프트웨어입니다. personagent가 직접 연결하는 QQ, WeChat, Telegram, Discord나 로컬 페이지가 AstrBot으로 설정하는 플랫폼에는 필요하지 않습니다. 이미 Koishi를 쓰고 있거나 Koishi로만 닿는 플랫폼을 원할 때 이 커넥터를 쓰세요.

커넥터는 허용된 각 메시지를 중립 이벤트로 에이전트의 `POST /v1/events`에 전달하고([docs/connectors.md](../../docs/connectors.ko.md)), 답변을 Satori로 돌려보냅니다. 에이전트의 아웃박스도 가져오므로 예약된 말 걸기, 후속 질문, 변명도 채팅에 도달합니다.

[satori-python](https://github.com/RF-Tar-Railt/satori-python)이 Satori 쪽(웹소켓, 로그인 목록, HTTP API)을 처리합니다. 이 커넥터는 Satori와 personagent의 이벤트 형식을 변환하고, 서명과 아웃박스 루프에 [`integrations/sdk/personagent_connector.py`](../sdk/personagent_connector.py)를 사용합니다.

## 설정 (Koishi 사용)

1. **Koishi.** 데스크톱 실행기나 `npm init koishi@latest`로 Koishi를 설치합니다. 콘솔에서 `adapter-telegram`이나 `adapter-discord` 같은 플랫폼 어댑터를 추가해 설정하고 봇이 온라인인지 확인합니다. `server`와 `server-satori` 플러그인을 켭니다. 그러면 Koishi가 `http://127.0.0.1:5140/satori`에서 Satori를 제공합니다. 이 컴퓨터 외의 것이 그 포트에 닿을 수 있다면 `server-satori`에 `token`을 설정하세요.

   Koishi는 다른 플러그인도 계속 실행합니다. 채팅 모델이나 답변 플러그인처럼 메시지에 답하는 것이 있으면 페르소나와 함께 답하고, 커넥터는 이를 막을 수 없습니다. 그 플러그인을 끄거나 전달하는 대화에서 제외하세요.

2. **에이전트.** personagent를 실행합니다(`personagent run`, README 참고). 커넥터와 에이전트가 다른 호스트에 있으면 에이전트의 `.env`에 `CONNECTOR_TOKEN`을 설정하고 에이전트를 HTTPS 뒤에 두세요. 호스트가 하나여도 프록시나 터널을 추가하기 전에 토큰을 설정하세요.

3. **커넥터.** 커넥터는 이 저장소의 스크립트이므로 저장소 사본(클론 또는 GitHub ZIP)과 자체 Python 환경이 필요합니다. `satori-python`은 personagent의 의존성이 아니기 때문입니다. personagent의 `.venv`가 있는 클론에서는 그 환경에 설치하세요.

   ```bash
   .venv/bin/python -m pip install -r integrations/satori/requirements.txt
   ```

   PyPI에서 pip로 personagent를 설치했거나 uvx로 실행한다면 사본 옆에 별도의 venv를 만드세요.

   ```bash
   python -m venv connector-venv
   connector-venv/bin/python -m pip install -r integrations/satori/requirements.txt
   ```

   Windows의 인터프리터는 `.venv\Scripts\python.exe` 또는 `connector-venv\Scripts\python.exe`입니다. 다음으로 설정 파일을 복사합니다.

   ```bash
   cp integrations/satori/.env.example integrations/satori/.env
   ```

   `integrations/satori/.env`에 Satori 서버의 URL과 토큰, 에이전트의 기본 URL과 `CONNECTOR_TOKEN`, 전달할 대화([허용 목록](#허용-목록) 참고)를 설정합니다. 그런 다음 같은 인터프리터로 커넥터를 시작합니다.

   ```bash
   .venv/bin/python integrations/satori/satori_connector.py
   ```

   `--config FILE`은 다른 설정 파일을 읽습니다. 모든 설정은 환경 변수로도 줄 수 있으며, 환경 변수가 파일보다 우선합니다.

4. **작동 확인.** 서버에 있는 봇마다 로그에 `Satori login telegram:7000 is ONLINE` 같은 줄이 나옵니다. 전달되는 그룹에서 봇을 멘션하세요. 에이전트 로그에 그 턴이 나오고 답변이 채팅에 나타납니다. 아무 일도 없으면 `SATORI_LOG_LEVEL=DEBUG`를 설정하세요.

## 설정 항목

| 설정 | 기본값 | 의미 |
|---|---|---|
| `SATORI_URL` | `http://127.0.0.1:5140/satori` | Satori 서버. 끝의 `/v1`은 없어도 됩니다. |
| `SATORI_TOKEN` | | 서버의 토큰(Koishi에서는 `server-satori` → `token`). |
| `PERSONAGENT_URL` | `http://127.0.0.1:8080` | 에이전트의 기본 URL. `/v1/events`와 `/v1/outbox`가 덧붙습니다. |
| `CONNECTOR_TOKEN` | | 에이전트의 `CONNECTOR_TOKEN`. |
| `SATORI_GROUPS` | | 전달할 그룹. 채널 또는 길드 ID로, `platform:id`도 가능합니다. 비우면 전달 안 함, `*`는 모두 전달합니다. |
| `SATORI_DM_USERS` | | DM을 전달할 사람. 사용자 ID로, `platform:id`도 가능합니다. 비우면 전달 안 함, `*`는 모두 전달합니다. |
| `SATORI_PLATFORMS` | 전체 | 커넥터를 이 Satori 플랫폼으로 제한합니다. |
| `SATORI_PLATFORM_NAMES` | `qq=qqbot` | 에이전트가 보는 플랫폼 이름을 바꿉니다: `satori_name=name, ...` |
| `SATORI_OUTBOX_ENABLED` | `true` | 에이전트의 아웃박스를 가져옵니다. |
| `SATORI_CONNECTOR_ID` | `SATORI_URL`에서 생성 | 에이전트 쪽의 이 커넥터 ID. 바꾸지 마세요. |
| `SATORI_TIMEOUT_S` | `420` | 한 턴에 걸릴 수 있는 시간. 에이전트의 3 × `LLM_TIMEOUT_S`보다 크게 두세요. |
| `SATORI_INLINE_IMAGES_ENABLED` | `false` | URL을 에이전트에 넘기지 않고 공개 이미지 URL을 커넥터에서 내려받습니다. |
| `SATORI_LOG_LEVEL` | `INFO` | |

에이전트 URL은 루프백 주소이거나 `CONNECTOR_TOKEN`이 설정된 HTTPS여야 합니다. 그렇지 않으면 커넥터가 시작을 거부합니다. `SATORI_TOKEN`이 평문 `http`로 다른 호스트에 전송될 상황이면 커넥터가 경고를 기록합니다.

## 허용 목록

커넥터는 기본적으로 거부합니다. 목록이 비어 있으면 아무것도 전달하지 않습니다.

- 그룹은 Satori 채널입니다. 채널 ID나 길드 ID가 `SATORI_GROUPS`에 있으면 전달됩니다. 그래서 Discord나 KOOK에서는 길드 ID 하나로 그 길드의 모든 채널이 허용되고, 각 채널은 여전히 별개의 대화입니다.
- DM은 보낸 사람의 사용자 ID가 `SATORI_DM_USERS`에 있으면 전달됩니다.
- 항목에는 `telegram:-1001234`나 `discord:4242`처럼 플랫폼을 적을 수 있으며, 그러면 그 플랫폼에서만 일치합니다. 플랫폼 없는 항목은 모든 플랫폼에서 일치합니다.
- `*`는 모든 그룹(또는 모든 DM)을 전달하고 이벤트에 `prefiltered: false`를 표시합니다. 그러면 에이전트 자체의 `ACCESS_GROUPS`와 `ACCESS_DM_USERS`가 결정하고, 거기에 항목이 없는 플랫폼은 거부됩니다.

Koishi의 `inspect` 플러그인은 메시지의 플랫폼, 채널, 길드, 사용자 ID를 출력합니다.

## 플랫폼 이름과 QQ

personagent는 ID를 `<platform>:<id>`로 저장하며, 플랫폼은 Satori 로그인의 플랫폼(`telegram`, `discord`, `onebot` 등)입니다. 4단계의 로그 줄에 표시됩니다. 특별한 경우가 두 가지 있습니다.

- **OneBot을 통한 QQ**(Koishi의 `adapter-onebot`, 뒤에 NapCat이나 LLOneBot)는 QQ 번호를 ID로 씁니다. 기존 QQ 배포에서 에이전트가 배운 것을 유지하려면 에이전트의 `CONNECTOR_QQ_PLATFORMS`에 플랫폼을 추가하세요(`CONNECTOR_QQ_PLATFORMS=onebot`). 그러면 ID가 NapCat의 QQ 번호처럼 접두사 없이 저장되고 `ACCESS_GROUPS`와 `ACCESS_DM_USERS`의 QQ 항목이 적용됩니다. ID가 실제로 QQ 번호인 플랫폼에만 하세요.
- **QQ 공식 봇 API**(Koishi의 `adapter-qq`)는 플랫폼을 `qq`라고 부르지만 ID는 QQ 번호가 아니라 openid입니다. 커넥터는 플랫폼 이름을 `qqbot`으로 바꿉니다. `SATORI_PLATFORM_NAMES`로 이 변경을 덮어쓸 수 있습니다. personagent는 Koishi 없이 QQ 공식 봇에 직접 연결할 수도 있습니다.

## 지원 기능

| 기능 | 상태 |
|---|---|
| 그룹 채팅과 DM | 지원. DM은 `DIRECT` 채널이거나 길드가 없는 메시지입니다. |
| 호출 감지(`addressed`) | 봇에 대한 `<at>`(ID로, 서버가 ID를 주지 않으면 봇 이름으로)와 봇 메시지에 대한 답장. `@all`은 멘션이 아니라 텍스트로 칩니다. |
| 인용 메시지 | 인용한 텍스트, 보낸 사람, ID를 `<quote>` 요소나 `message.quote`에서 가져옵니다. |
| 받은 이미지 | `data:`와 `internal:` 이미지, Satori 서버의 이미지는 인라인으로 넣습니다. 공개 URL은 에이전트가 가져오도록 넘깁니다. 사설 네트워크 URL은 `(sent an image)`로 설명합니다. 메시지당 최대 4개, 각 4 MB까지 내려받습니다. |
| 스티커와 이모지 | `<emoji>`와 QQ `<face>`는 이모지로 도착하며, 페르소나는 자신이 볼 수 없음을 압니다. |
| 음성, 동영상, 파일 | 말로 설명합니다: `(sent a voice message)`, `(sent a video)`, `(sent a file: deck.pdf)`. |
| 답변 | 텍스트와 `data:` URI 이미지를 각각 별도 메시지로 짧은 간격을 두고 보냅니다. 그룹에서는 에이전트가 요청한 멘션이 `<at>`이 됩니다. |
| 수동 답장 플랫폼 | 답변에 이벤트의 `referrer`를 담습니다. QQ 공식 봇 API가 메시지에 답할 때 필요합니다. |
| 아웃박스 | 예약된 말 걸기, 후속 질문, 변명은 그 대화를 받은 로그인을 통해 채널로 갑니다. 커넥터는 `SATORI_TOKEN`과 `CONNECTOR_TOKEN`에서 파생한 키로 각 답장 핸들에 서명하고, 자기가 서명한 핸들에만 보냅니다. 둘 중 하나를 바꾸면 대화가 메시지를 한 번 보낸 뒤에야 다시 닿습니다. `CONNECTOR_OUTBOX_ENABLED=false`인 에이전트는 404로 답하고, 커넥터는 10분마다 다시 시도합니다. |
| 입력 중 표시 | 없음. Satori에는 입력 중 API가 없습니다. |
| `owned` | 존중합니다: 커넥터는 다른 것을 보내지 않습니다. Koishi의 다른 플러그인은 막을 수 없습니다(1단계 참고). |

플랫폼 규칙은 여전히 적용됩니다. 예를 들어 QQ 공식 봇 API는 봇이 먼저 보내는 메시지를 엄격히 제한하므로, 거기서는 아웃박스 전달이 `failed`로 돌아올 수 있습니다.

## 테스트

`tests/test_satori_connector.py`는 satori-python과 네트워크 없이 실행됩니다. 요소 객체, 계정, 에이전트를 흉내 냅니다.
