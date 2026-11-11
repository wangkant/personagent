# astrbot_plugin_personagent

[English](README.md) · [简体中文](README.zh-CN.md) · [繁體中文](README.zh-TW.md) · [日本語](README.ja.md) · 한국어 · [Español](README.es.md) · [Français](README.fr.md) · [Deutsch](README.de.md) · [Português (Brasil)](README.pt-BR.md) · [Русский](README.ru.md)


이 [AstrBot](https://github.com/AstrBotDevs/AstrBot) 플러그인은 AstrBot을 [personagent](https://github.com/wangkant/personagent)에 연결합니다. 허용된 메시지를 에이전트로 전달하고 에이전트의 답장을 채팅으로 돌려보냅니다.

## 필요합니까?

QQ, WeChat, Telegram, Discord, Matrix, Twitch, IRC, Zulip, VK, Stoat에는 필요 없습니다. personagent가 AstrBot 없이 직접 연결합니다. `personagent`를 실행해 로컬 페이지를 열고 **플랫폼 연결**에서 추가하거나, 터미널에서 `personagent connect <platform>`을 실행하십시오.

이 플러그인은 AstrBot이 대화를 중계할 때 필요합니다. 두 가지 경우가 있습니다.

- **personagent 페이지에서 다른 플랫폼을 추가할 때.** KOOK, Feishu/Lark, DingTalk, Slack, WeCom AI 봇, Mattermost, Misskey와 고급 설정 아래의 플랫폼은 모두 AstrBot을 거칩니다. 페이지가 AstrBot을 내려받아 실행하고 이 플러그인을 설치하므로 여기서 할 일은 없습니다.
- **이미 AstrBot을 실행 중이고** 자체 플랫폼과 플러그인이 있을 때. 아래 설명대로 플러그인을 설치하십시오.

## 하는 일

- AstrBot의 모든 플랫폼 어댑터(Telegram, Discord, Slack, QQ 등)에서 그룹 메시지와 DM을 받습니다. `excluded_platforms`에 있는 것은 제외합니다.
- 허용 목록의 그룹과 발신자 메시지를 플랫폼 중립 이벤트로 에이전트의 `POST /v1/events`에 전달합니다. 누구를 불렀는지, 무엇을 인용했는지, 스티커, 이미지, 음성 메시지, 플랫폼이 말하는 전송 시각까지 각 플랫폼을 어댑터가 전달하는 방식대로 읽습니다.
- 에이전트의 답장을 각 플랫폼이 기대하는 형식으로 AstrBot을 통해 돌려보냅니다. 답장에는 텍스트와 이미지를 담을 수 있고, 그룹 채팅에서는 에이전트가 요청하면 멘션도 붙습니다.
- 에이전트의 아웃박스를 가져와 예약된 말 걸기, 후속 질문, 모델이 멈췄을 때 그룹에 올리는 변명처럼 먼저 하는 말을 전달합니다. [아웃박스](#아웃박스)를 참고하십시오.
- 에이전트가 대화를 맡으면 AstrBot 자체 파이프라인을 멈춥니다(`block_default`). 그래서 AstrBot 내장 모델이 캐릭터 대신 답하지 않습니다.

페르소나, 기억, 디바운스, 타이핑 시뮬레이션은 모두 에이전트에서 실행됩니다. 이 플러그인은 에이전트의 [`docs/connectors.md`](https://github.com/wangkant/personagent/blob/main/docs/connectors.ko.md)가 정의하는 커넥터입니다.

## 내 AstrBot에 설치

AstrBot(데이터 폴더가 생기도록 한 번 이상 실행한 것)과 personagent(`python -m pip install personagent`, README 참고)가 필요합니다.

### personagent 설정으로

```bash
personagent connect astrbot
```

이 명령은 먼저 AstrBot의 데이터 폴더, 즉 `cmd_config.json`, `plugins/`, `config/`가 있는 폴더를 찾습니다. 찾지 못하면 AstrBot을 내려받을지 묻습니다. 이어서 AstrBot이 Docker에서 실행되는지, 봇이 참여할 채팅 플랫폼(AstrBot에 아직 필요하면 그 플랫폼의 토큰도), 그룹, 관리자, 봇에게 DM할 수 있는 사람을 묻습니다. NapCat을 통한 QQ에서는 봇 계정 번호도 묻습니다. 마지막으로 이 플러그인을 복사하고, 공유 토큰을 만들어 양쪽에 쓰고, 허용 목록을 씁니다. `personagent init --terminal`도 마지막에 같은 단계를 제안합니다.

질문을 건너뛰려면 데이터 폴더를 넘기십시오.

```bash
personagent connect astrbot <AstrBot data dir>        # add --qq to route QQ (NapCat) as well
```

이렇게 실행하면 첫 연결의 허용 목록은 **비어** 있으며 플러그인 설정에서 채웁니다. `personagent connect astrbot --help`에는 AstrBot에서 플랫폼도 켜는 플래그가 나와 있습니다.

이 명령은 언제든 다시 실행할 수 있습니다. 허용 목록, 다른 제외 플랫폼, 플러그인이 받아들이는 `personagent_url`은 유지됩니다([에이전트를 실행할 수 있는 곳](#에이전트를-실행할-수-있는-곳) 참고). 플러그인이 거부할 `personagent_url`은 루프백 기본값으로 바뀝니다. QQ 경로는 `--qq`나 `--no-qq`를 넘길 때만 바뀌고, 에이전트의 `CONNECTOR_QQ_PLATFORMS`가 이를 따릅니다. 물어볼 때는 현재 허용 목록이 기본값입니다. Enter로 유지하고 `-`를 입력하면 비웁니다.

그런 다음 AstrBot을 다시 시작하고 에이전트를 시작하십시오([작동 확인](#작동-확인) 참고).

### AstrBot WebUI에서

1. [personagent 최신 릴리스](https://github.com/wangkant/personagent/releases/latest)에서 `astrbot_plugin_personagent.zip`을 내려받습니다.
2. AstrBot 플러그인 페이지의 **Install from File**에서 업로드합니다.
3. `connector_token`을 personagent `.env`의 `CONNECTOR_TOKEN`으로 설정하고, 아래 설명대로 허용 목록을 채웁니다.
4. AstrBot이 personagent와 다른 컴퓨터에서 실행되면 `personagent_url`을 HTTPS 주소로 설정합니다([에이전트를 실행할 수 있는 곳](#에이전트를-실행할-수-있는-곳) 참고).

업데이트하려면 새 릴리스의 zip을 같은 방식으로 업로드합니다. AstrBot 4.29 이상은 설치된 사본을 교체합니다. 이전 버전에서는 먼저 플러그인을 제거하고 **Also delete plugin configuration file**은 체크하지 마십시오.

### 직접 설치

1. 이 폴더를 `<AstrBot data dir>/plugins/astrbot_plugin_personagent/`에 복사합니다.
2. AstrBot을 다시 시작하거나 WebUI에서 플러그인을 다시 불러옵니다. AstrBot이 `httpx`만 적힌 `requirements.txt`를 설치합니다.
3. WebUI에서 플러그인 설정을 엽니다. 설정은 `<AstrBot data dir>/config/astrbot_plugin_personagent_config.json`에 저장됩니다.
   - 캐릭터가 참여할 수 있는 그룹 ID를 `groups`에 추가합니다.
   - DM에 답해도 되는 발신자 ID를 `dm_users`에 추가합니다.
   - 에이전트의 `.env`가 `CONNECTOR_TOKEN`을 설정한다면 같은 값을 `connector_token`에 넣습니다. 에이전트가 다른 호스트에 있으면 필수입니다.
   - 에이전트가 같은 호스트에서 기본값 `SERVER_PORT=8080`으로 실행되면 `personagent_url`은 기본값으로 둡니다.

플러그인은 **기본 거부**입니다. 허용 목록이 비어 있으면 아무것도 전달하지 않고, AstrBot은 플러그인이 없는 것처럼 동작합니다. ID는 AstrBot에 보이는 대로 쓰십시오. 채팅에서 `/sid`를 보내면 볼 수 있습니다. 접두사 없는 ID는 모든 어댑터에 일치합니다. `qq_official:ID`는 그 어댑터에만 일치하고, `qq_official:*`는 그 어댑터의 같은 종류 대화를 모두 전달합니다.

`groups`나 `dm_users`의 단독 `*`는 모든 어댑터의 같은 종류 대화를 모두 전달하고 `prefiltered: false`로 표시합니다. 그러면 에이전트 자체의 `ACCESS_GROUPS`와 `ACCESS_DM_USERS`만 결정합니다. 에이전트는 거기에 항목이 없는 플랫폼을 거부하지만, QQ 그룹은 예외로 `ACCESS_GROUPS`에 QQ 그룹이 없으면 답합니다.

### 작동 확인

1. `personagent run`으로 에이전트를 시작합니다. 서버만 시작합니다. 배너에 `agent: on`이 보여야 합니다.
2. 허용된 그룹에서 봇 이름(에이전트의 `PERSONA_NAME`)을 말합니다.

답장이 없으면 AstrBot 로그에서 `personagent:` 줄을 찾고, `personagent run`이 배너 뒤에 출력한 내용을 읽은 다음 [문제 해결](#문제-해결)을 참고하십시오.

## 구성

| 키 | 유형 | 기본값 | 설명 |
| --- | --- | --- | --- |
| `personagent_url` | string | `http://127.0.0.1:8080` | 에이전트의 기본 URL. 플러그인이 `/v1/events`와 `/v1/outbox`를 덧붙입니다. 루프백이거나 `connector_token`이 설정된 HTTPS여야 합니다. |
| `connector_token` | string | `""` | 공유 비밀값. 에이전트의 `CONNECTOR_TOKEN`과 일치해야 합니다. 루프백이 아닌 `personagent_url`에는 필수입니다. |
| `timeout_s` | int | `420` | 시도마다 기다리는 초. [타임아웃](#타임아웃)을 참고하십시오. |
| `excluded_platforms` | list | `["aiocqhttp"]` | 절대 전달하지 않는 어댑터 이름. `aiocqhttp`를 빼면 QQ(NapCat)가 이 플러그인을 거칩니다. [NapCat을 통한 QQ](#napcat을-통한-qq)를 참고하십시오. |
| `groups` | list | `[]` | 전달할 그룹 ID. 비어 있으면 어떤 그룹도 전달하지 않습니다. `adapter:ID`나 `adapter:*`는 항목을 한 어댑터로 제한합니다. 단독 `*`는 모든 그룹을 필터 없이 전달합니다. |
| `dm_users` | list | `[]` | DM을 전달할 발신자 ID. 비어 있으면 DM을 전달하지 않습니다. `adapter:ID`나 `adapter:*`는 항목을 한 어댑터로 제한합니다. 단독 `*`는 모든 DM을 필터 없이 전달합니다. |
| `block_default` | bool | `true` | 에이전트가 대화를 맡으면 AstrBot 파이프라인을 멈춥니다. |
| `forward_quoted_text` | bool | `true` | 플랫폼이 제공하면 인용된 메시지의 본문과 작성자를 id와 함께 보냅니다. 이 옵션이 켜져 있고 `quote_max_chars`가 0보다 크면 모든 이벤트가 `quote_text` 기능을 선언합니다. |
| `quote_max_chars` | int | `200` | 보내는 인용문의 최대 길이. 더 긴 인용은 잘립니다. |
| `max_inline_image_bytes` | int | `4000000` | 인라인으로 보내는 이미지의 최대 크기. 에이전트가 직접 가져올 수 없는 이미지(Telegram, 로컬 파일, 사설 주소)는 인라인으로 보냅니다. 더 큰 이미지는 `(sent an image)` 메모로 도착합니다. 에이전트의 `VISION_MAX_IMAGE_BYTES`보다 작게 유지하십시오. |
| `outbox_enabled` | bool | `true` | 에이전트의 아웃박스를 가져와 전달합니다. [아웃박스](#아웃박스)를 참고하십시오. |
| `outbox_wait_s` | int | `25` | 아웃박스 요청 한 번이 에이전트에서 기다릴 수 있는 시간. 최대 30. |
| `connector_id` | string | `""` | 에이전트가 이 AstrBot을 부르는 이름. 비어 있으면 한 번 만들어 유지합니다. AstrBot 호스트 두 대에는 서로 다른 이름이 필요합니다. |

### 에이전트를 실행할 수 있는 곳

- **같은 호스트**, 또는 호스트의 네트워크 네임스페이스를 공유하거나 호스트 네트워크를 쓰는 컨테이너: 기본 루프백 `personagent_url`을 유지합니다.
- **다른 컨테이너나 호스트**: HTTPS `personagent_url`을 쓰고, `connector_token`과 에이전트의 `CONNECTOR_TOKEN`에 비어 있지 않은 같은 비밀값을 설정합니다. AstrBot에서 보이는 루프백 URL로 끝나는 사설 터널도 됩니다. 이 경우에도 양쪽에 같은 토큰을 설정하십시오. 에이전트가 프록시를 거쳐 온 토큰 없는 요청을 거부하기 때문입니다.

플러그인은 `http://host.docker.internal:8080`처럼 루프백이 아닌 곳으로 가는 평문 `http://`를 토큰이 있어도 거부합니다. 그러면 메시지마다 `refusing unsafe personagent_url`을 기록하고 AstrBot 자체 모델이 대신 답합니다.

**Docker의 AstrBot.** 컨테이너 안에서 `127.0.0.1`은 컨테이너 자신이므로 기본 `personagent_url`은 아무 곳에도 닿지 않습니다. 선택지는 두 가지입니다.

- AstrBot에 호스트 네트워크를 줍니다. compose 파일의 `network_mode: host` 또는 `docker run --network host`입니다. Docker Desktop은 4.34 이상에서 host networking을 켜야 합니다. 같은 compose 파일의 NapCat 컨테이너도 호스트 네트워크가 필요합니다.
- 에이전트를 HTTPS 뒤에 두고 그 주소를 `personagent_url`로 설정합니다(`personagent connect astrbot <dir> --url https://...`).

에이전트는 기본적으로 `127.0.0.1:8080`에서 수신합니다. `SERVER_HOST`를 루프백이 아닌 주소로 설정하면 `CONNECTOR_TOKEN`이 없을 때 시작을 거부합니다. 에이전트 앞에 프록시나 터널을 두기 전에 토큰을 설정하십시오. 호스트가 하나여도 마찬가지입니다.

### 타임아웃

각 요청은 에이전트의 턴만큼 지속됩니다. 턴은 짧은 디바운스와 모든 모델 호출 및 재시도로 이루어집니다. `timeout_s`가 끝나도 에이전트는 턴을 마치고 배운 것을 유지하지만, 답장은 사라지고 AstrBot 자체 모델이 대신 그 메시지에 답합니다.

에이전트의 3 × `LLM_TIMEOUT_S`를 `timeout_s`보다 작게 유지하십시오. 한 턴의 모델 호출은 재시도까지 합쳐 1.5 × `LLM_TIMEOUT_S`를 나눠 쓰고, 메시지는 먼저 도착했을 때 생각 중이던 턴이 끝나기를 기다립니다. 에이전트 기본값(`LLM_TIMEOUT_S=120`)에서는 360초이며, 기본 `timeout_s` 420이 이를 감당합니다. 에이전트에서 `LLM_TIMEOUT_S`를 올리면 `timeout_s`도 올리십시오.

서명된 요청이 아직 유효한 동안, 플러그인은 에이전트의 429나 500을 최대 두 번 재시도하고 429에서는 `Retry-After`를 따릅니다.

### `block_default`와 소유권

에이전트가 대화를 자기 것으로 보고하면(`owned: true`) 답장 여부와 상관없이 플러그인은 AstrBot 파이프라인을 멈춥니다. 그래서 캐릭터가 빠지는 턴에 AstrBot 내장 모델이 끼어들지 않습니다.

전송 오류, 잘못된 응답, 에이전트가 거절한 대화는 AstrBot의 일반 파이프라인으로 계속 갑니다. 에이전트 응답에 `owned` 필드가 없으면 플러그인은 대신 `handled`를 씁니다.

## NapCat을 통한 QQ

QQ 공식 봇은 personagent가 AstrBot 없이 직접 연결합니다. 이 절은 NapCat(또는 다른 OneBot v11 구현)으로 운영하는 QQ 계정을 AstrBot의 `aiocqhttp` 어댑터 뒤에서 쓰는 경우만 다룹니다. personagent 자체 페이지에서 OneBot v11을 추가하면 `excluded_platforms`에서 `aiocqhttp`를 빼고 `CONNECTOR_QQ_PLATFORMS`를 설정해 줍니다.

1. `excluded_platforms`에서 `aiocqhttp`를 빼고 QQ 그룹을 `groups`에 추가합니다.
2. 에이전트의 `.env`에 `CONNECTOR_QQ_PLATFORMS=aiocqhttp`와 `QQ_BOT_ID`(봇 계정 번호)를 설정합니다.
3. 선택: 에이전트의 `QQ_ONEBOT_URL`을 NapCat의 HTTP 서버로 설정합니다. 놓친 멘션을 따라잡는 처리가 켜지며, 여기에도 `QQ_BOT_ID`가 필요합니다. 먼저 보내는 메시지, 거절 뒤의 후속 질문, 모델 실패 시 그룹의 변명은 플러그인이 가져오는 동안 이 플러그인의 [아웃박스](#아웃박스)를 거칩니다. 그렇지 않으면 그 URL이 설정되어 있을 때 NapCat으로 직접 갑니다.
4. NapCat이 에이전트의 `/v1/onebot`에도 게시한다면 끄십시오. 이 경로는 더 이상 권장되지 않으며, 둘 다 실행하면 모든 메시지가 두 번 전달됩니다.

`personagent connect astrbot <data dir> --qq`는 `excluded_platforms`에서 `aiocqhttp`를 빼고 `CONNECTOR_QQ_PLATFORMS`를 설정합니다. 폴더 없이 실행하면 `QQ_BOT_ID`도 묻습니다. 배포 가이드도 이 경로를 다룹니다: [docs/deploy.md](https://github.com/wangkant/personagent/blob/main/docs/deploy.ko.md#napcatonebot을-통한-qq).

`CONNECTOR_QQ_PLATFORMS=aiocqhttp`를 건너뛰지 마십시오. 이것이 없으면 에이전트는 QQ 채팅을 `aiocqhttp:` 접두사가 붙은 ID로 기록하고, 접두사 없는 QQ ID로 배운 것은 더 이상 일치하지 않으며, 학습 기록은 나중에 키를 바꿀 수 없습니다.

QQ ID는 접두사 없이 유지되므로 에이전트 자체의 QQ 설정이 그대로 적용됩니다. `ACCESS_GROUPS`의 QQ 항목이 그룹을 제한하고(항목이 없으면 모든 QQ 그룹), DM은 `ADMIN_IDS`의 관리자나 `ACCESS_DM_USERS`의 사람에게만 답합니다. 마법사는 입력한 QQ 그룹을 에이전트의 `.env`에 씁니다. 나중에 QQ 그룹을 추가하려면 `groups`와 `ACCESS_GROUPS` 양쪽에 넣거나, `ACCESS_GROUPS`에 QQ 그룹을 하나도 쓰지 마십시오.

활발한 QQ 그룹을 AstrBot에 맡기기 전에 AstrBot 설정 두 가지를 확인하십시오. 둘 다 플러그인 핸들러보다 먼저 실행됩니다.

- `platform_settings.rate_limit`의 기본값은 60초에 30개 메시지입니다. 한도를 넘는 메시지는 버려지지 않고 지연됩니다. 한도를 올리거나 끄십시오.
- `content_safety.internal_keywords`는 기본으로 켜져 있으며 키워드 목록에 맞는 메시지를 버립니다. 캐릭터가 답했을 메시지도 포함됩니다. 목록을 확인하십시오.

## 플랫폼

에이전트는 하나의 중립 형식으로 말하고, 플러그인은 경계에서 각 플랫폼 자체의 방식으로 변환합니다. 아래 표는 AstrBot 4.25.5의 어댑터와 대조했습니다.

모든 플랫폼에서:

- 사람이 쓴 메시지만 전달합니다. QQ 알림(찌르기, 회수, 입장)과 요청, Slack의 입장과 주제 변경은 턴이 아닙니다.
- 동영상, 파일, 음성 메시지는 `(sent a video)`, `(sent a file: deck.pdf)`, `(sent a voice message)`처럼 캐릭터가 반응할 수 있는 메모로 도착하며, 플랫폼에 받아쓰기가 있으면 함께 옵니다.
- 인용된 메시지는 플랫폼이 제공하면 본문과 작성자를 담습니다(`forward_quoted_text`).
- 어댑터가 보관하는 경우, 메시지 시각은 AstrBot이 받은 시각이 아니라 플랫폼 자체의 시각입니다.
- 답장은 플랫폼의 길이 제한보다 짧게 나누며, 멘션과 이스케이프는 플랫폼의 방식대로 셉니다. 텍스트를 이미지로 바꾸지 않으며, 사람은 플랫폼의 방식대로 부릅니다.
- 아웃박스는 플랫폼이 먼저 보낼 수 있는 경우에만 씁니다.

| 플랫폼(어댑터) | 되는 것 | 플랫폼 자체가 못 하는 것 |
| --- | --- | --- |
| OneBot을 통한 QQ(`aiocqhttp`) | 그룹과 DM. 어댑터가 @를 찾지 못한 경우를 포함해 @와 봇 답장. 이모티콘 이름, 스토어 스티커(`mface`), 스티커로 표시된 이미지. 진짜 QQ @와 뒤따르는 공백 하나로 멘션. 긴 답장은 AstrBot의 `forward_threshold` 미만으로 나누어 병합 전달 카드가 되지 않습니다. 아웃박스. | Markdown은 입력한 그대로 보입니다. |
| QQ 공식(`qq_official`, `qq_official_webhook`) | 봇을 @한 그룹 메시지와 DM. 이모티콘은 `[表情:name]`으로 나타납니다. 답장은 어댑터의 markdown 대신 일반 텍스트를 요청합니다. | 그룹은 봇을 @한 메시지만 전달하므로 캐릭터가 대화를 따라갈 수 없습니다. 인용 없음, 이름 없음(openid만), 답장에서 멘션 없음. 답장은 메시지 후 5분 안에만 가능하므로 아웃박스가 없습니다. |
| Telegram(`telegram`) | 그룹, 토픽(`<chat>#<thread>`), DM. 모든 종류의 메시지에 대한 봇 답장. 어댑터의 `/@bot` 호출 접두사는 제거합니다. 스티커 이모지, 정적 스티커는 이미지도. 이미지는 어댑터의 봇으로 가져오므로 봇 토큰이 AstrBot 밖으로 나가지 않습니다. 멘션된 사용자 이름은 그 사람이 글을 쓴 뒤 숫자 id가 됩니다. 답장은 사용자 이름으로, 없는 사람은 `tg://user` 링크로 멘션하며 `*`, `_` 같은 문자는 입력한 그대로 보입니다. 아웃박스. | BotFather의 개인정보 모드가 켜져 있으면(기본값) 그룹은 명령, @멘션, 봇 답장만 전달합니다. 캐릭터가 대화를 따라가도록 끄십시오. 애니메이션과 동영상 스티커는 볼 수 없습니다. |
| Discord(`discord`) | 채널과 스레드를 그룹으로, 그리고 DM. 맨 앞의 `@bot`(어댑터가 제거), 봇 역할 핑, 봇 답장은 모두 봇을 부릅니다. 본문이 있는 인용. 스티커. 음성과 동영상 첨부는 메모로. 멘션은 `<@id>`이며 `@everyone`과 `@here`는 무효로 둡니다. 답장은 2000자에서 나눕니다. DM을 포함한 아웃박스. | Message Content 인텐트가 필요합니다. |
| Slack(`slack`) | 채널과 DM. 봇 메시지 아래의 스레드 답장은 봇을 부릅니다. 링크를 펼칩니다. 메시지 id는 Slack의 `ts`입니다. 멘션은 `<@id>`. `&`, `<`, `>`를 이스케이프해 텍스트가 채널을 호출하지 못하게 합니다. 답장은 3000자에서 나눕니다. 아웃박스. | 스레드 답장에는 부모 본문이 없습니다. 봇의 입력 표시 없음. 답은 스레드가 아니라 채널에 올라갑니다(어댑터). |
| KOOK(`kook`) | 채널과 DM. @와 봇이 가진 역할 핑. KOOK이 포함할 때의 인용. `(emj)` 이모지와 실제 전송 시각. 멘션은 텍스트 안에 넣고, 캐릭터가 쓴 텍스트의 `(met)` 형식 태그는 무효로 둡니다. 어댑터가 JPEG base64만 올리므로 이미지는 파일로 보냅니다. 아웃박스. | AstrBot의 어댑터는 플러그인이 보기 전에 일반 이미지, 파일, 음성, 동영상 메시지(카드 제외)를 버립니다. 입력 표시 없음. |
| Lark / Feishu(`lark`) | 그룹과 DM. @와 봇 답장(Lark는 앱을 발신자로 표시). 본문이 있는 인용. 스티커는 이모지로. 아웃박스. | "그룹 메시지 전체 읽기" 권한이 없으면 @ 메시지만 옵니다. 모든 답장은 답하는 메시지를 인용하고 markdown이 렌더링됩니다(어댑터). 이름은 id 접두사입니다. |
| DingTalk(`dingtalk`) | 그룹과 DM. 어댑터가 로컬 파일로 넘기는 이미지는 인라인으로 보냅니다. 동영상은 메모로. 아웃박스. DM은 봇에게 글을 쓴 사람에게 닿습니다. | 그룹은 봇을 @한 메시지만 전달합니다. 인용 없음, 답장에서 멘션이나 인용 답장 없음. 모든 답장은 제목이 "AstrBot"인 markdown입니다(어댑터). |
| LINE(`line`) | 그룹, 룸, DM. 봇 @. 인용 id. 스티커 키워드. 한 턴의 말풍선을 한 번의 호출로 다섯 개씩 보내 무료 reply token으로 충분합니다. 아웃박스는 푸시 할당량에 포함됩니다. | LINE은 인용 본문을 보내지 않습니다. 답장에서 멘션 없음(어댑터). 보내는 이미지에는 공개 HTTPS `callback_api_base`가 필요합니다. 이름은 id 접두사입니다. |
| Mattermost(`mattermost`) | 채널과 DM. 봇 @. 스레드 루트를 인용으로. 이미지는 인라인. 그 사람이 글을 쓴 뒤 사용자 이름으로 멘션. `@channel`, `@all`, `@here`는 무효로 둡니다. 답장은 4000자에서 나눕니다. 아웃박스. | 인용 본문에는 플러그인이 하지 않는 조회가 필요합니다. 입력 표시 없음. |
| Misskey(`misskey`) | 채팅 DM과 룸. 룸 메시지 어디에 있든 `@bot`을 인식합니다. 그 사람이 글을 쓴 뒤 `@user@host`로 멘션하고, 캐릭터가 쓴 텍스트의 다른 `@`는 무효로 둡니다. 답장은 3000자에서 나눕니다. 채팅과 룸의 아웃박스. | 노트(공개 게시물)는 전달하지 않습니다. AstrBot이 시스템 이벤트로 분류하고 답장이 공개되기 때문입니다. `unique_session`은 룸을 망가뜨립니다(어댑터). |
| Satori(`satori`) | Satori 백엔드가 연결하는 것: 그룹, DM, @, 봇 답장, 본문이 있는 인용. 밀리초 타임스탬프는 초로 읽습니다. 아웃박스. | 그룹 id는 길드이므로 길드의 채널이 한 대화를 공유합니다. 연결된 플랫폼의 제한이 적용됩니다. |
| WebChat(`webchat`) | 대시보드 채팅을 DM으로. 인용과 이미지. 아웃박스는 실시간으로 보이거나 대화에 저장됩니다. | 일대일만 됩니다. |
| WeCom 앱(`wecom`) | DM, 이미지, 받아쓰기가 있는 음성. 고객 서비스 모드는 고객의 메시지만 실제 전송 시각으로 전달합니다. 답장은 바이트로 나눕니다. 앱 모드의 아웃박스는 AstrBot 시작 후 누군가 글을 쓴 뒤 가능합니다. | DM만, 인용 없음. 고객 서비스 모드는 먼저 보낼 수 없습니다. Markdown은 입력한 그대로 보입니다. |
| WeCom AI 봇(`wecom_ai_bot`) | 그룹(WeCom은 봇이 @될 때만 그룹 메시지를 전달)과 DM. 음성, 파일, 동영상 메모. 한 턴을 하나의 스트리밍 답변으로 보냅니다. | 메시지에 대한 답변 안에서만 답할 수 있어 아웃박스도 멘션도 없습니다. 답변은 markdown으로 렌더링됩니다. "@bot"이 본문에서 제거되도록 AstrBot에서 `wecom_ai_bot_name`을 설정하십시오. |
| WeChat 공식 계정(`weixin_official_account`) | DM과 받아쓰기가 있는 음성. 한 턴을 한 메시지로 보냅니다. | 패시브 모드는 사용자 메시지마다 WeChat의 5초 창 안에서 답장 하나만 전달합니다. 나머지는 사용자의 다음 메시지를 기다리고, 캐릭터가 빠지는 턴에는 사용자가 기다리게 됩니다(어댑터). 이미지는 액티브 모드에서만. 아웃박스 없음. |
| 개인 WeChat(`weixin_oc`) | DM. 본문이 있는 인용. 이미지는 인라인. 받아쓰기가 있는 음성. 입력 표시. 아웃박스. | 그룹 없음. 다시 로그인한 뒤에는 상대가 다시 글을 쓸 때까지 아무에게도 닿지 않습니다. |
| 그 밖의 어댑터 | AstrBot이 전달하는 대로 전달합니다. 멘션은 At으로. | 아웃박스를 선언하지 않습니다. |

## 아웃박스

아무것에도 답하지 않는 메시지가 있습니다. 예약된 말 걸기, 거절 뒤의 후속 질문, 모델이 멈췄을 때 그룹의 변명입니다. (DM의 변명은 이벤트 자체의 응답으로 돌아옵니다.) 에이전트가 이 메시지를 대기열에 넣고, 이 플러그인이 이벤트와 같은 서명으로 `POST <personagent_url>/v1/outbox`에서 가져오므로 에이전트가 AstrBot에 접근할 필요가 없습니다. 아웃박스는 기본으로 켜져 있습니다(`outbox_enabled`).

- 각 전달은 대화 자체의 AstrBot 세션을 통해 순서대로 나가며, 각 메시지는 최대 한 번 보냅니다.
- 전달은 플러그인이 같은 대화의 메시지에서 직접 얻은 세션으로만 갑니다. 이 세션들은 AstrBot의 플러그인 저장소에 보관되어 다시 불러와도 남습니다. 에이전트에 이벤트를 게시하는 다른 어떤 것도 아웃박스를 다른 채팅으로 돌릴 수 없으며, 플러그인은 그런 전달을 거부합니다.
- 플러그인은 전송할 때 허용 목록과 `excluded_platforms`를 다시 확인하고, 그사이 제거된 대화를 거부합니다.
- 먼저 말할 수 없는 플랫폼(표 참고)은 아웃박스 메시지를 받지 않습니다. 플러그인이 그 대화에 아웃박스를 선언하지 않기 때문입니다.
- 아웃박스가 없는 에이전트는 404로 답합니다. 플러그인은 10분마다 다시 묻습니다.

에이전트는 이 AstrBot을 `connector_id`로 압니다. 플러그인이 한 번 만들어 유지합니다. 한 에이전트와 통신하는 AstrBot 호스트 두 대에는 서로 다른 id가 필요합니다.

## 요청 인증

`connector_token`이 설정되면 모든 요청에 헤더 네 개가 붙습니다.

- `X-Personagent-Token`: 토큰.
- `X-Personagent-Timestamp`: Unix 초.
- `X-Personagent-Nonce`: 새 난수 값.
- `X-Personagent-Signature`: `sha256=` 뒤에, 토큰을 키로 한 `timestamp + "." + nonce + "." + body`의 16진 HMAC-SHA256.

본문은 정규 JSON입니다. UTF-8, 키 정렬, 간결한 구분자, 이스케이프하지 않은 비 ASCII 문자입니다. 서명은 이 정확한 바이트를 대상으로 하므로 프록시가 본문을 고치면 안 됩니다. 에이전트는 잘못된 서명, 재사용된 nonce, 자기 시계와 5분 넘게 차이 나는 타임스탬프를 거부합니다. 두 시계를 맞춰 두십시오.

본문에는 어댑터 자체의 메시지 시각도 `sent_at`으로 들어 있습니다. 에이전트는 이를 `CONNECTOR_MAX_EVENT_AGE_S`(기본 24시간)와 따로 비교하므로, 새 서명으로 다시 보낸 오래된 이벤트도 거부됩니다. 어댑터가 유효한 타임스탬프를 주지 않는 메시지는 플러그인이 전달하지 않고 AstrBot이 평소대로 처리합니다. 캐릭터는 각 메시지를 이 시각과 함께 보며, AstrBot이 재시작 후 전달하는 밀린 메시지처럼 도착 시점에 10분이 넘은 그룹 메시지는 맥락으로 보관되고 답장 대상이 되지 않습니다.

## 에이전트 쪽의 ID

에이전트는 전달된 모든 id 앞에 플랫폼을 붙여 `<platform>:<raw id>`(예: `telegram:12345`)로 만들므로 플랫폼이 달라도 id가 충돌하지 않습니다. `CONNECTOR_QQ_PLATFORMS`에 있는 플랫폼은 접두사 없는 id를 유지합니다. 에이전트의 `ADMIN_IDS`, `ACCESS_GROUPS`, `ACCESS_DM_USERS`는 같은 형식의 id를 받습니다. 예를 들어 `ADMIN_IDS=telegram:12345`는 그 계정을 Telegram의 그룹과 DM에서 관리자로 만듭니다. `ACCESS_GROUPS`나 `ACCESS_DM_USERS`에 항목이 있는 플랫폼은 이 플러그인의 허용 목록과 함께 에이전트에서도 제한됩니다.

## 문제 해결

AstrBot 로그에서 플러그인의 줄은 `personagent:`로 시작합니다.

| 로그 메시지 | 할 일 |
| --- | --- |
| `refusing unsafe personagent_url` | `personagent_url`이 다른 호스트로 가는 평문 HTTP이거나 `connector_token` 없는 HTTPS입니다. [에이전트를 실행할 수 있는 곳](#에이전트를-실행할-수-있는-곳)을 참고하십시오. |
| `agent refused the request (403): invalid, stale, or replayed request envelope` | `connector_token`이 비어 있거나 에이전트의 `CONNECTOR_TOKEN`과 다르거나, 두 시계가 5분 넘게 차이 나거나, 프록시가 본문을 바꿨습니다. 에이전트 로그에 `connector replay guard full`이 있으면 비워질 때까지 기다리십시오. |
| `agent refused the request (403): stale or invalid sent_at` | 메시지가 에이전트의 `CONNECTOR_MAX_EVENT_AGE_S`보다 오래되었습니다. 보통 AstrBot이 밀린 메시지를 전달한 뒤에 일어납니다. |
| `agent refused the request (403): authentication required` 또는 `... only local requests accepted` | 에이전트에 `CONNECTOR_TOKEN`이 없고 요청이 로컬이 아닙니다. 양쪽에 같은 토큰을 설정하십시오. |
| `agent at capacity (429)` | 에이전트가 이미 `CONNECTOR_MAX_INFLIGHT`개의 턴을 실행 중이고 재시도 뒤에도 메시지를 거절해 AstrBot 자체 모델이 답했습니다. 자주 일어나면 `CONNECTOR_MAX_INFLIGHT`를 올리십시오. |
| `agent rejected the body as too large (413)` | 보통 큰 인라인 이미지입니다. 에이전트의 `SERVER_MAX_BODY_BYTES`를 올리십시오. |
| `agent rejected the event schema (400)` | 이벤트에 메시지 id나 발신자 id가 없거나(일부 어댑터는 생략합니다) 이 플러그인의 버그입니다. 로그 줄과 함께 알려 주십시오. |
| `timed out waiting for the agent` | [타임아웃](#타임아웃)을 참고하십시오. |
| `dropping event without a valid time the platform sent it` | 어댑터가 타임스탬프를 주지 않았습니다. AstrBot이 그 메시지를 직접 처리합니다. |
| `agent request failed: ...` 또는 `agent request failed (<status>)` | 보통 에이전트가 실행 중이 아니거나 `personagent_url`이 잘못되었습니다. 404는 경로 오류입니다. `personagent_url`은 `/v1/events` 없는 기본 URL입니다. 500은 에이전트 실패이므로 그 로그를 확인하십시오. |
| `outbox off: ...` | 아웃박스는 이벤트와 같은 `personagent_url` 규칙을 따릅니다. 첫 행을 참고하십시오. |
| `outbox: agent has no outbox (turned off, or an older version); retrying in 10 minutes` | 에이전트의 `CONNECTOR_OUTBOX_ENABLED`가 꺼져 있습니다. |
| `outbox: outbox pull refused (403)` 또는 `outbox pull failed: ...` | 원인은 이벤트와 같습니다. 토큰, 시계, 또는 에이전트가 실행 중이 아닌 경우입니다. 플러그인은 시도 간격을 최대 1분까지 늘립니다. |
| `outbox: no running platform '<id>'` | AstrBot에서 꺼졌거나 이름이 바뀐 어댑터로 가는 전달입니다. 플러그인은 에이전트에 실패로 보고합니다. |
| `could not store connector_id` | AstrBot의 플러그인 저장소가 실패했습니다. `connector_id`를 직접 설정하십시오. 그러지 않으면 에이전트는 재시작할 때마다 새 AstrBot을 봅니다. |

AstrBot 자체 모델이 갑자기 다른 말투로 답하면, 플러그인이 에이전트에 닿지 못했거나 에이전트가 대화를 맡지 않은 것입니다. 위 표를 확인한 다음 `personagent doctor`를 실행하십시오. 로컬 페이지가 에이전트를 시작했다면 거기서 **활동**을 열어 메시지가 도착했는지, 캐릭터가 왜 말하지 않았는지 확인하십시오. `personagent run`으로 시작했다면 터미널 출력을 확인하십시오.

에이전트 자체 로그에 커넥터가 `X-Personagent-Token`을 보내는데 `CONNECTOR_TOKEN`이 비어 있다고 나오면, 에이전트가 토큰을 무시하는 것입니다. 에이전트의 `.env`에 같은 값을 설정하십시오.

QQ, Telegram, Discord, KOOK, QQ 공식, Misskey에서 메시지 시각은 AstrBot이 받은 시각이 아니라 플랫폼 자체의 시각입니다. AstrBot이 에이전트의 `CONNECTOR_MAX_EVENT_AGE_S`보다 오래 멈춰 있었으면, 에이전트는 AstrBot이 전달하는 밀린 메시지를 오래된 것으로 거부합니다.

## 알려진 제한: Telegram 멘션

AstrBot의 Telegram 어댑터는 발신자를 숫자 사용자 id(`telegram:<numeric id>`)로 식별하지만, 메시지 안의 `@username` 멘션은 사용자 이름으로만 식별합니다. 플러그인은 그 사람이 AstrBot 시작 후 글을 쓰면 멘션된 사용자 이름을 숫자 id로 바꿉니다. 그전까지 멘션은 사용자 이름으로 에이전트에 도착합니다.

답장은 사용자 이름으로, 없는 사람은 `tg://user` 링크로 멘션합니다. 플러그인은 AstrBot 시작 후 보지 못한 사람을 멘션하지 않습니다.
