# Matrix 커넥터

[English](README.md) · [简体中文](README.zh-CN.md) · [繁體中文](README.zh-TW.md) · [日本語](README.ja.md) · 한국어 · [Español](README.es.md) · [Français](README.fr.md) · [Deutsch](README.de.md) · [Português (Brasil)](README.pt-BR.md) · [Русский](README.ru.md)


이 커넥터는 [personagent](https://github.com/wangkant/personagent)를 Matrix 방에, 그리고 [mautrix 브리지](https://docs.mau.fi/bridges/)를 통해 WhatsApp, Signal, Messenger, Instagram, Google Messages 등의 네트워크에 둡니다. Matrix와 브리지는 직접 운영하는 서드파티 소프트웨어입니다. personagent가 로컬 페이지에서 연결하는 플랫폼에는 필요하지 않습니다.

커넥터는 [matrix-nio](https://github.com/matrix-nio/matrix-nio)로 만든 작은 독립 프로세스로, libolm 없이 종단 간 암호화를 지원합니다. 일반 Matrix 사용자로 홈서버에 로그인해 허용된 각 방 메시지를 플랫폼 중립 이벤트로 에이전트의 `POST /v1/events`에 전달하고([docs/connectors.md](../../docs/connectors.ko.md)), 에이전트의 답변을 방에 올립니다. 에이전트의 아웃박스도 폴링하므로 예약된 말 걸기, 후속 질문, 변명도 Matrix에 도달합니다.

## 하는 일

받을 때, 허용된 방의 각 메시지에 대해:

- 이벤트는 플랫폼 `matrix`와 원본 Matrix ID를 쓰므로 에이전트는 `matrix:@alex:example.org`와 `matrix:!room:example.org`를 저장합니다.
- 봇의 `m.direct`에 있거나, 봇과 `MATRIX_IGNORE_USERS`의 사용자를 빼고 멤버가 정확히 한 명인 방은 다이렉트 채팅으로 칩니다. 다이렉트 채팅은 사람으로, 그룹은 방으로 구분합니다. `MATRIX_GROUPS`에 ID로 적은 방은 항상 그룹입니다.
- 메시지가 봇을 멘션하거나 봇의 메시지에 답장하면 `addressed`가 true입니다. 멘션은 `m.mentions`, 또는 `m.mentions`를 못 보내는 오래된 클라이언트의 필이나 텍스트 속 봇 사용자 ID입니다.
- 답장에는 인용된 메시지의 보낸 사람과 텍스트가 담깁니다. 커넥터는 최근 이벤트 캐시에서 가져오거나 부모 이벤트를 받아 옵니다. 오래된 클라이언트가 앞에 붙이는 답장 대체 텍스트(`> <@alex:example.org> ...`)는 제거하므로, 에이전트가 다른 사람의 말을 보낸 사람의 말로 읽는 일은 없습니다.
- 4 MB까지의 이미지와 스티커는 내려받아 암호화된 방에서는 복호화한 뒤 바이트로 에이전트에 보냅니다. 음성 메시지, 동영상, 파일은 말로 설명합니다.
- 방의 메시지는 보낸 순서대로 에이전트에 도달합니다. 이미지 다음에 보낸 메시지는 이미지 다운로드가 끝날 때까지 기다립니다. 에이전트는 여전히 여러 턴을 동시에 처리할 수 있습니다.
- 타임스탬프는 홈서버의 `origin_server_ts`입니다.
- 커넥터는 봇 자신의 메시지, `m.notice` 메시지(봇이 보내는 유형), 수정, 반응, `MATRIX_IGNORE_USERS`의 메시지, 시작할 때 첫 동기화가 돌려주는 밀린 메시지, 그리고 브리지가 새 방에 채워 넣는 기록처럼 `MATRIX_MAX_EVENT_AGE_S`보다 오래된 것을 건너뜁니다.

보낼 때:

- 텍스트 답변은 `m.text`입니다. 에이전트가 그룹에서 누군가를 멘션하라고 하면 답변이 필로 시작하고 그 사람을 `m.mentions`에 넣습니다. 다른 답변은 모두 빈 `m.mentions`를 담으므로, 어떤 클라이언트도 텍스트 속 이름을 알림으로 바꾸지 않습니다.
- 이미지 답변은 업로드되며, 암호화된 방에서는 암호화됩니다.
- 에이전트가 턴을 처리하는 동안 입력 중 알림이 표시됩니다.
- 스레드의 메시지에는 그 스레드에서 답합니다.
- 에이전트가 대화를 맡으면 봇이 메시지를 읽음으로 표시합니다(`MATRIX_READ_RECEIPTS_ENABLED`). 브리지를 통하면 상대 네트워크에서 읽음 표시로 보입니다.
- 아웃박스 전달은 대화가 마지막으로 온 방으로 갑니다. 이벤트의 `reply_handle`이 방 ID입니다.

## 설치

실행 중인 personagent와 봇용 Matrix 계정이 필요합니다. 사람과 공유하지 말고 전용 계정을 만드세요.

커넥터는 이 저장소의 스크립트이므로 저장소 사본(클론 또는 GitHub ZIP)과 자체 Python 환경이 필요합니다. `matrix-nio`는 personagent의 의존성이 아니기 때문입니다. personagent의 `.venv`가 있는 클론에서는 그 환경에 설치하세요.

```bash
.venv/bin/python -m pip install -r integrations/matrix/requirements.txt
```

PyPI에서 pip로 personagent를 설치했거나 uvx로 실행한다면 사본 옆에 별도의 venv를 만드세요.

```bash
python -m venv connector-venv
connector-venv/bin/python -m pip install -r integrations/matrix/requirements.txt
```

Windows의 인터프리터는 `.venv\Scripts\python.exe` 또는 `connector-venv\Scripts\python.exe`입니다. 다음으로 설정 파일을 복사합니다.

```bash
cp integrations/matrix/.env.example integrations/matrix/.env
```

`integrations/matrix/.env`를 편집합니다.

```ini
MATRIX_URL=https://matrix.example.org
MATRIX_USER_ID=@nova:example.org
MATRIX_PASSWORD=...
MATRIX_GROUPS=!AbCdEf:example.org
MATRIX_DM_USERS=@alex:example.org
PERSONAGENT_URL=http://127.0.0.1:8080
```

그런 다음 같은 인터프리터로 에이전트 옆에서 커넥터를 시작합니다.

```bash
.venv/bin/python integrations/matrix/matrix_connector.py
# or: .venv/bin/python integrations/matrix/matrix_connector.py --config /path/to/matrix.env
```

`MATRIX_GROUPS`에 있는 방에 봇을 초대하면 참여합니다. Element에서 방 ID는 방 설정의 고급 항목에 있습니다.

### 로그인

비밀번호 로그인이 가장 쉬운 시작 방법입니다. 커넥터는 받은 세션(사용자 ID, 기기 ID, 액세스 토큰)을 `MATRIX_STORE_DIR/session.json`에 저장해 다음 시작 때 다시 쓰므로, 재시작해도 새 기기가 생기지 않습니다. 그 파일을 지우면 다시 로그인합니다.

기존 액세스 토큰을 쓰려면 `MATRIX_ACCESS_TOKEN`을 설정하세요. 커넥터가 홈서버에 토큰의 계정을 묻습니다. 직접 쓰는 세션의 토큰은 쓰지 마세요. 그 세션에서 로그아웃하면 봇도 로그아웃됩니다.

홈서버가 봇을 로그아웃시키면(`M_UNKNOWN_TOKEN`) 커넥터는 그렇게 알리는 오류와 함께 멈춥니다. 비밀번호 로그인이었다면 다시 시작하면 다시 로그인합니다. `MATRIX_ACCESS_TOKEN`이면 먼저 새 토큰을 설정하세요. 다른 동기화 실패는 최대 1분까지 두 배씩 늘어나는 지연 후 다시 시도합니다.

### 에이전트를 실행할 수 있는 곳

규칙은 프로토콜이 정합니다. `PERSONAGENT_URL`은 루프백 주소이거나, `CONNECTOR_TOKEN`을 에이전트의 `CONNECTOR_TOKEN`으로 설정한 HTTPS여야 합니다. 그렇지 않으면 커넥터가 시작을 거부합니다. 호스트가 하나여도 에이전트 앞에 프록시나 터널을 두기 전에 양쪽에 토큰을 설정하세요.

## 설정 항목

[.env.example](.env.example)에 모든 설정이 있습니다. 목록은 쉼표로 구분하고 글롭을 받으므로 `@*:example.org`는 서버 전체와 일치합니다. 빈 목록은 아무에게도 답하지 않습니다. 단독 `*`는 모두와 일치하고 이벤트에 `prefiltered: false`를 표시합니다. 그러면 에이전트 자체의 `ACCESS_GROUPS` / `ACCESS_DM_USERS`만 결정하고, 거기에 항목이 없는 플랫폼은 거부됩니다.

| 설정 | 의미 |
|---|---|
| `MATRIX_GROUPS` | 답할 그룹 방의 방 ID. `*`는 봇이 참여한 모든 방입니다. |
| `MATRIX_DM_USERS` | 다이렉트 채팅으로 봇과 말할 수 있는 사람. `*`는 모두입니다. |
| `MATRIX_INVITE_FROM` | 봇이 초대를 받아들이는 사용자. `MATRIX_GROUPS`의 방 초대와 `MATRIX_DM_USERS`의 다이렉트 채팅 초대는 항상 받아들입니다. 다른 초대는 보류됩니다. |
| `MATRIX_IGNORE_USERS` | 절대 답하지 않으며, 다이렉트 채팅과 그룹을 구분할 때 멤버로 세지 않습니다. |
| `MATRIX_E2EE_ENABLED` | 종단 간 암호화. 아래를 참고하세요. |
| `MATRIX_TIMEOUT_S` | 한 턴에 걸릴 수 있는 시간. 에이전트의 `LLM_TIMEOUT_S × (1 + LLM_MAX_RETRIES)`보다 크게 두세요. |
| `MATRIX_OUTBOX_ENABLED` | 에이전트의 아웃박스를 폴링합니다. |

## 브리지: WhatsApp, Signal, Messenger, Instagram 등

mautrix 브리지는 다른 네트워크에 그 네트워크 계정으로 로그인해 채팅을 포털이라 불리는 Matrix 방에 미러링합니다. 상대편의 모든 사람은 `@whatsapp_4912345:example.org` 같은 고스트 사용자로 Matrix에 나타납니다. 브리지에 로그인한 것이 봇의 Matrix 계정이면 페르소나가 그 네트워크에 살게 됩니다. WhatsApp 연락처가 페르소나의 번호로 메시지를 보내면 브리지가 포털 방에 올리고, 이 커넥터가 전달하며, 답변은 같은 길로 돌아갑니다.

| 네트워크 | 브리지 |
|---|---|
| WhatsApp | [mautrix-whatsapp](https://github.com/mautrix/whatsapp) |
| Signal | [mautrix-signal](https://github.com/mautrix/signal) |
| Facebook Messenger, Instagram DM | [mautrix-meta](https://github.com/mautrix/meta) |
| Google Messages (Android 휴대폰을 통한 RCS와 SMS) | [mautrix-gmessages](https://github.com/mautrix/gmessages) |
| Google Voice, LinkedIn, Twitter/X DM, Bluesky DM, Google Chat, Zulip, IRC, iMessage | 다른 [mautrix 브리지](https://github.com/mautrix) |
| Telegram, Discord, Slack | mautrix 브리지가 있지만 이 네트워크들에는 공식 봇 API가 있습니다. personagent는 Telegram과 Discord에 직접 연결하고, Slack은 로컬 페이지가 실행하는 AstrBot으로 연결합니다. |

설정 방법:

1. 직접 관리하는 홈서버(Synapse 또는 애플리케이션 서비스를 지원하는 다른 서버)를 실행하고 [문서](https://docs.mau.fi/bridges/)에 따라 브리지를 설치합니다. 브리지의 `permissions`에서 봇 계정에 `user` 권한 수준을 줍니다.
2. 봇으로 Element에 로그인해 브리지 봇(예: `@whatsappbot:example.org`)과의 채팅을 열고 `login`을 보냅니다. 페르소나가 쓸 네트워크 계정을 연결합니다. WhatsApp, Signal, Google Messages는 페르소나의 휴대폰으로 QR 코드를 스캔합니다. Messenger와 Instagram은 Meta 로그인 정보를 줍니다. [브리지 사용법](https://docs.mau.fi/bridges/general/using-bridges.html)을 참고하세요.
3. 커넥터가 포털에 참여하게 하고 브리지 자체의 메시지를 제외합니다.

   ```ini
   MATRIX_INVITE_FROM=@whatsappbot:example.org
   MATRIX_IGNORE_USERS=@whatsappbot:example.org,@whatsapp_4900000000:example.org
   MATRIX_DM_USERS=@whatsapp_*:example.org
   MATRIX_GROUPS=!groupPortal:example.org
   ```

   `MATRIX_IGNORE_USERS`의 두 번째 항목은 페르소나 자신의 번호에 대한 브리지 고스트입니다. [더블 퍼피팅](https://docs.mau.fi/bridges/general/double-puppeting.html)이 없으면 페르소나의 휴대폰에서 입력한 메시지가 그 고스트로 Matrix에 도착해 봇이 자기에게 답하게 됩니다. `MATRIX_GROUPS=*`는 봇이 있는 모든 그룹 포털을 전달하고, personagent는 `ACCESS_GROUPS`에 `matrix:!room:server`로 있는 방에서만 답합니다. 여기에 방 ID를 적으면 대신 커넥터에서 방을 고를 수 있습니다.

### 퍼피팅

- 브리지는 네트워크의 비공식 클라이언트로, 일반 사용자 계정(연결된 기기 또는 웹 세션)으로 로그인합니다. 봇 API를 쓰지 않으며, 네트워크 어디에도 계정이 봇이라고 표시되지 않습니다.
- 페르소나에는 자체 계정이 필요하고 보통 자체 전화번호가 있으며, 휴대폰은 연결 가능한 상태여야 합니다. WhatsApp은 휴대폰이 약 2주 동안 오프라인이면 연결된 기기를 끊고, Google Messages는 Android 휴대폰이 온라인일 때만 작동합니다.
- 그룹 채팅에서 페르소나의 계정은 다른 멤버와 똑같아 보입니다. 사람들에게 봇과 이야기하고 있다고 알려 주세요.
- 반응, 수정, 삭제, 투표, 통화는 에이전트에 전달되지 않습니다.

### 각 네트워크의 약관

연결하기 전에 각 네트워크의 약관을 읽으세요.

- [WhatsApp](https://www.whatsapp.com/legal/terms-of-service)은 자동 메시지 전송을 허용되지 않는 통신으로 나열하고, 승인하지 않은 비개인적 사용을 금지하며, 이를 하는 계정을 차단할 수 있습니다. 승인된 자동화 경로는 WhatsApp Business Platform이며 브리지는 이를 쓰지 않습니다.
- [Signal](https://signal.org/legal/)도 자동 메시지 전송을 허용되지 않는 것으로 나열합니다.
- [Facebook](https://www.facebook.com/terms.php)과 [Instagram](https://help.instagram.com/581066165581870)은 Meta의 허가 없는 자동 접근을 금지하며, Meta는 인식하지 못하는 클라이언트로 로그인한 계정을 잠글 수 있습니다.
- Google Messages는 [Google 약관](https://policies.google.com/terms)과 SMS, RCS에 관한 이동통신사 약관의 적용을 받으며, 이동통신사는 자동 메시지에 요금을 매기거나 제한할 수 있습니다.

잃어도 괜찮은 전용 계정을 쓰고, 사람들이 봇과 이야기한다는 것을 아는 대화에서만 쓰며, [DISCLAIMER.md](../../docs/DISCLAIMER.ko.md)를 읽으세요.

## 종단 간 암호화

`MATRIX_E2EE_ENABLED=false`(기본값)이면 봇은 암호화되지 않은 방만 읽습니다. 암호화된 방에서는 복호화할 수 없다고 기록하고, 거기에 평문 답변을 보내지 않습니다.

`MATRIX_E2EE_ENABLED=true`이면:

- `MATRIX_STORE_DIR`(기본값은 스크립트 옆의 `runtime/`로, git이 무시합니다)에 기기 키와 동기화 토큰이 저장됩니다. 이 디렉터리를 보관하세요. 잃으면 봇은 새 기기가 되어 그 이전의 암호화된 내용을 읽지 못합니다.
- 기기는 재시작 전후로 같아야 합니다. 비밀번호 로그인은 저장된 세션으로 유지합니다. 액세스 토큰을 쓰면 `MATRIX_DEVICE_ID`를 토큰의 기기로 설정하세요.
- 봇은 검증 여부와 상관없이 방의 모든 기기와 키를 공유합니다. 대화식으로 자신을 검증할 수 없어서 사람들에게 기기가 미검증으로 보입니다. 키 백업과 교차 서명은 없습니다.
- 키가 도착하지 않은 메시지는 기록하고 건너뛰며 다시 시도하지 않습니다.
- mautrix 브리지는 포털을 암호화할 수 있습니다([종단 대 브리지 암호화](https://docs.mau.fi/bridges/general/end-to-bridge-encryption.html)). 브리지가 그 키를 서버에 보관하므로 보호는 거기서 끝나고, 상대 네트워크는 자체 암호화로 메시지를 전달합니다. 브리지가 포털을 암호화한다면 `MATRIX_E2EE_ENABLED`를 켜세요.

## 테스트

`tests/test_matrix_connector.py`는 Matrix 클라이언트와 에이전트를 흉내 내므로 matrix-nio와 네트워크 없이 실행됩니다.

```bash
python -m pytest tests/test_matrix_connector.py
```
