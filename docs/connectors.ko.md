# 커넥터 프로토콜

[English](connectors.md) · [简体中文](connectors.zh-CN.md) · [繁體中文](connectors.zh-TW.md) · [日本語](connectors.ja.md) · 한국어 · [Español](connectors.es.md) · [Français](connectors.fr.md) · [Deutsch](connectors.de.md) · [Português (Brasil)](connectors.pt-BR.md) · [Русский](connectors.ru.md)

에이전트는 채팅 플랫폼과 직접 이야기하지 않아요. 그 일은 커넥터가 해요. 커넥터는 플랫폼 하나, 또는 여러 플랫폼을 다루는 프레임워크에 로그인해서 들어오는 메시지를 중립적인 이벤트로 바꿔 personagent에 보내고, 돌아온 것을 전달해요. 플랫폼에 특화된 것은 모두 커넥터에 남으므로, 에이전트는 어느 플랫폼에서나 같은 형식을 봐요.

이 저장소에는 커넥터 네 개가 들어 있어요.

| 커넥터 | 연결 대상 | 경로 |
|---|---|---|
| 직접 연결 | QQ 공식 봇, 개인 WeChat(iLink), Telegram, Discord, Matrix, Twitch, IRC, Zulip, VK, Stoat. 다른 소프트웨어가 필요하지 않습니다. 로컬 페이지와 `personagent up`이 하나의 프로세스 `python -m persona_agent.direct`로 실행해요. | `persona_agent/direct/` |
| AstrBot 플러그인 | 서드파티 브리지 AstrBot의 플랫폼. KOOK, Feishu/Lark, DingTalk, Slack, WeCom, Mattermost, Misskey, OneBot v11 등을 위해 personagent가 관리하는 AstrBot에는 플러그인이 자동으로 들어가요. 이미 실행 중인 AstrBot은 `personagent connect astrbot`으로 설정해요. GitHub Release의 `astrbot_plugin_personagent.zip`을 AstrBot의 파일에서 설치로 올리고 `connector_token`을 직접 설정할 수도 있어요. | `integrations/astrbot/` |
| Satori | 모든 Satori 구현(Koishi 등 서드파티): QQ, Telegram, Discord, KOOK, Lark, DingTalk, LINE, WhatsApp, Matrix, Zulip, 이메일 등. | `integrations/satori/` |
| Matrix | Matrix 방, 그리고 서드파티 mautrix 브리지를 통한 WhatsApp, Signal, Messenger, Instagram, Google Messages 등. | `integrations/matrix/` |

코딩 에이전트는 채팅 플랫폼이 아니어서 전용 경로가 있어요. MCP 서버 `personagent mcp`이고, [사용자 가이드](guide.ko.md#코딩-에이전트)에서 다뤄요.

네 커넥터 모두 이 페이지에서 설명하는 프로토콜을 써요. 새 커넥터를 만들려면 이 페이지와 HTTP 클라이언트만 있으면 돼요. `integrations/sdk/personagent_connector.py`의 Python 도우미가 요청에 서명하고 아웃박스 루프를 대신 돌려 줘요. 기본 URL, 토큰, 커넥터의 `connector_id`를 받고 `httpx`가 필요해요.

## 설정

로컬 페이지는 직접 연결 커넥터를 설정해요. 나머지 셋은 같은 이름을 쓰므로, 설정 하나는 어디서나 같은 뜻이에요.

| 의미 | Satori | Matrix | AstrBot 플러그인 키 |
|---|---|---|---|
| personagent의 기본 URL(예: `http://127.0.0.1:8080`). 커넥터가 `/v1/events`와 `/v1/outbox`를 덧붙여요. | `PERSONAGENT_URL` | `PERSONAGENT_URL` | `personagent_url` |
| 공유 토큰. 에이전트의 `CONNECTOR_TOKEN`과 같은 값 | `CONNECTOR_TOKEN` | `CONNECTOR_TOKEN` | `connector_token` |
| 이 커넥터의 ID(아래의 `connector_id`) | `SATORI_CONNECTOR_ID` | `MATRIX_CONNECTOR_ID` | `connector_id` |
| 요청 한 번에 걸려도 되는 시간(초) | `SATORI_TIMEOUT_S` | `MATRIX_TIMEOUT_S` | `timeout_s` |
| 아웃박스 가져오기 | `SATORI_OUTBOX_ENABLED` | `MATRIX_OUTBOX_ENABLED` | `outbox_enabled` |
| 전달할 그룹 | `SATORI_GROUPS` | `MATRIX_GROUPS` | `groups` |
| DM을 전달할 사람 | `SATORI_DM_USERS` | `MATRIX_DM_USERS` | `dm_users` |
| 플랫폼 서버 | `SATORI_URL` | `MATRIX_URL` | AstrBot 자체 설정 |

그룹이나 DM 목록이 비어 있으면 그 종류는 아무것도 전달하지 않아요. `*`는 그 종류를 모두 전달하고 이벤트에 `"prefiltered": false`를 표시해, 판단을 에이전트의 `ACCESS_GROUPS`와 `ACCESS_DM_USERS`에 맡겨요. 나머지 설정은 각 커넥터의 README에 있어요.

## 주소

personagent는 모든 ID를 `<platform>:<id>`로 저장해요. 예를 들어 그룹은 `telegram:-1001234`, 사용자는 `discord:4242`예요. `platform`은 커넥터가 플랫폼에 붙인 이름으로, 소문자이고 `:`이 없어요.

QQ는 유일한 예외로, 호환성을 위해 남겨 뒀어요. ID는 그대로(`123456`) 저장되고, 어떤 설정에서든 `qq:123456`은 같은 뜻이에요. 커넥터가 QQ를 다루고 학습 상태를 기존 QQ 배포와 맞추고 싶다면, 그 플랫폼 이름을 `CONNECTOR_QQ_PLATFORMS`에 적으세요. AstrBot 플러그인의 QQ 어댑터는 `aiocqhttp`예요. 거기 적힌 플랫폼의 ID도 그대로 저장돼요.

## 인증

아래 두 엔드포인트는 같은 방식을 써요. 에이전트에 `CONNECTOR_TOKEN`이 설정되어 있으면 모든 요청에 헤더 네 개가 붙어요.

- `X-Personagent-Token`: 토큰.
- `X-Personagent-Timestamp`: unix 초. 에이전트 시계와 5분 넘게 차이 나는 값은 거부돼요.
- `X-Personagent-Nonce`: 새 난수 값. 다시 쓴 nonce는 거부돼요.
- `X-Personagent-Signature`: `sha256=` 뒤에 토큰을 키로 한 `timestamp + "." + nonce + "." + body`의 16진수 HMAC-SHA256.

본문은 정규화된 JSON이에요. UTF-8, 키 정렬, 간결한 구분자, 비 ASCII 문자는 이스케이프하지 않아요. 토큰은 서명 키이기도 하니 로그에 남기지 마세요.

토큰이 없으면 에이전트는 `127.0.0.1`이나 `localhost`를 직접 호출하는 로컬 프로그램만 받아들여요. 커넥터는 루프백 URL이나 토큰이 있는 HTTPS URL이 아닌 곳으로 보내기를 거부해야 해요.

## 수신: `POST /v1/events`

요청마다 메시지 하나가 들어오고 그에 대한 답변이 돌아가요.

```json
{
  "platform": "telegram",
  "conversation_type": "group",
  "conversation_id": "-1001234",
  "sender_id": "42",
  "sender_name": "Alex",
  "bot_id": "7000",
  "message_id": "881",
  "sent_at": 1790320000,
  "addressed": true,
  "text": "Nova, how was your day?",
  "segments": [
    {"type": "text", "text": "Nova, how was your day?"}
  ],
  "connector_id": "astrbot-7f3c",
  "reply_handle": "tg-bot:GroupMessage:-1001234",
  "capabilities": ["outbox", "quote_text"]
}
```

필수 필드는 `platform`, `conversation_type`(`group` 또는 `dm`), `sender_id`, `message_id`, `sent_at`이고, 그룹에는 `conversation_id`도 필요해요. `sent_at`은 플랫폼이 메시지에 찍은 시각으로 unix 초예요. 플랫폼의 원래 ID를 보내세요. 접두사는 에이전트가 붙여요.

`addressed`는 커넥터가 설정해요. 메시지가 봇을 멘션하거나, 봇의 메시지에 답하거나, 플랫폼 자체 규칙으로 봇에게 한 말이면 true예요. 에이전트는 텍스트 속 자기 이름도 스스로 알아차려요. 자기 메시지 인용이나 봇 @는 배울 수 있는 반응으로 읽으니, 봇에게 답하는 메시지에는 `addressed`를 설정하세요. 다른 구성원 메시지의 인용은 봇에 대한 반응이 아니에요.

`sender_id`가 `bot_id`와 같은 이벤트는 봇 자신의 메시지가 되돌아온 거예요. 에이전트는 읽지 않고 버린 뒤 `{"handled": false, "owned": true, "replies": []}`라고 답하므로, 커넥터 자체의 봇 로직도 조용히 있어요. 이런 이벤트는 커넥터에서 건너뛰세요.

세그먼트는 순서대로 와요.

| 종류 | 필드 | 참고 |
|---|---|---|
| `text` | `text` | |
| `mention` | `user_id`, `name` | 누군가에 대한 멘션. `user_id`가 `bot_id`와 같으면 봇을 멘션한 거예요. |
| `image` | `url` 또는 `b64`, `sticker`(불리언) | `sticker`는 이미지로 보낸 스티커를 표시해요. |
| `emoji` | `name`, `id` | 에이전트가 볼 수 없는 플랫폼 스티커나 사용자 지정 이모지. `name`은 사람이 부를 법한 이름이에요. |
| `reply` | `message_id`, `text`, `sender_id`, `sender_name` | 이 메시지가 인용하는 메시지. 플랫폼이 제공하면 항상 `text`를 보내세요. |

그 밖의 것은 `(sent a voice message)`나 `(sent a file: deck.pdf)`처럼 `text` 세그먼트로 말로 설명하세요. 에이전트는 모르는 종류의 세그먼트를 버려요.

다음 선택 필드는 에이전트의 기능을 더 켜 줘요.

| 필드 | 의미 |
|---|---|
| `connector_id` | 이 커넥터 인스턴스의 안정적인 ID. 아웃박스에 필요해요. |
| `reply_handle` | 커넥터가 들어오는 메시지 없이 나중에 이 대화에 닿는 데 필요한 무엇이든. AstrBot의 `unified_msg_origin`, Matrix 방 ID, Satori 로그인과 채널 ID 같은 것이에요. 에이전트는 내용을 해석하지 않고 대화별로 저장해 아웃박스 배달 때 돌려줘요. |
| `capabilities` | 커넥터가 할 수 있는 일. `outbox`는 아웃박스를 폴링하고 먼저 보낼 수 있다는 뜻이에요. `quote_text`는 답장 세그먼트에 인용 텍스트가 있다는 뜻이에요. |
| `prefiltered` | 커넥터가 자체 허용 목록을 적용했으면 `true`(기본값). `false`면 에이전트의 목록이 유일한 필터가 돼요. |
| `proactive` | DM 이벤트를 그 사람의 말이 아니라 커넥터가 쓴 신호로 표시해요. "아웃박스 없이 먼저 말하기"를 보세요. |

응답은 이렇게 생겼어요.

```json
{"handled": true, "owned": true, "replies": [
  {"type": "text", "text": "not bad, rained all afternoon", "mention_user_id": "telegram:42"},
  {"type": "image", "b64": "..."}
]}
```

- `replies`: 순서대로, 각각 별도 메시지로 보내세요. `mention_user_id`가 있으면 그것이 멘션할 접두사 붙은 ID예요. 멘션은 플랫폼 방식대로 표시하세요.
- `owned`: 에이전트가 이 대화를 맡았어요. true이면 `replies`가 비어 있어도 다른 봇 로직이 답하지 못하게 하세요. 페르소나가 조용히 있기로 했기 때문이에요. false이면 그 메시지는 직접 처리할 몫이에요. 대화가 에이전트의 허용 목록에 없거나, 에이전트가 아예 답할 수 없는(`LLM_API_KEY`가 없거나 `AGENT_ENABLED=false`) 경우예요. 두 번째 경우 에이전트 로그에 원인을 밝힌 ERROR 줄이 하나 남아요.
- 요청은 턴이 끝날 때까지 이어져요. 짧은 디바운스와 모델에 걸리는 시간을 합한 시간이에요. 그룹이든 DM이든 한 턴의 모델 호출은 재시도까지 합쳐 1.5 × `LLM_TIMEOUT_S`라는 하나의 시간 예산을 나눠 쓰고, 같은 대화의 앞선 턴이 아직 생각하는 동안 도착한 메시지는 그 턴이 끝난 뒤에 자기 턴을 시작해요. 적어도 3 × `LLM_TIMEOUT_S`초(기본값으로는 360초)는 기다리세요.
- 대화의 턴이 아직 생각하는 동안 도착한 기억 명령("remember ..." 같은)에는 그 턴이 끝난 뒤에 답해요. `outbox`를 선언한 커넥터는 곧바로 `{"handled": false, "owned": true, "replies": []}`를 받고, 답은 나중에 `follow_up` 전달로 받아요. `outbox`가 없으면 답은 응답으로 와요. 그 요청 자신의 응답일 수도 있고, 같은 대화에서 기다리던 다른 요청의 응답일 수도 있어요. 그래서 응답에 이벤트를 보낸 사람이 아닌 다른 사람을 멘션하는 답장이 들어 있을 수 있어요.

## 아웃박스: `POST /v1/outbox`

요청에 대한 답이 아닌 메시지도 있어요. 예약된 말 걸기, 거부 뒤의 후속 질문, 턴이 끝나기를 기다린 기억 명령에 대한 답, 그룹에서 모델이 멈췄을 때의 변명 같은 것이에요. 에이전트는 이것들을 대화별로 대기열에 넣고, `outbox`를 선언한 커넥터가 가져가요. 그래서 NAT나 방화벽 뒤의 커넥터도 똑같이 작동해요. 접두사 없는 QQ ID로 저장된 대화('주소' 참고)도 커넥터가 가져가는 동안에는 아웃박스를 써요. 그렇지 않으면 `QQ_ONEBOT_URL`이 설정된 경우 NapCat의 HTTP API를 거쳐요.

요청:

```json
{
  "kind": "outbox.pull",
  "connector_id": "astrbot-7f3c",
  "wait_s": 25,
  "max_deliveries": 10,
  "acks": [
    {"delivery_id": "d_5c1f...", "status": "sent", "sent_items": 2}
  ]
}
```

에이전트는 대기열에 무언가 들어올 때까지 요청을 최대 `wait_s`초(상한 30) 붙잡고 있다가 답해요.

```json
{
  "deliveries": [
    {
      "delivery_id": "d_9a07...",
      "conversation_key": "telegram:-1001234",
      "reply_handle": "tg-bot:GroupMessage:-1001234",
      "platform": "telegram",
      "conversation_type": "group",
      "conversation_id": "-1001234",
      "reason": "proactive",
      "expires_in_s": 300,
      "items": [{"type": "text", "text": "anyone still up?"}]
    }
  ],
  "next_wait_s": 25
}
```

`items`는 `replies`와 모양이 같아요. `reason`은 `proactive`, `follow_up` 또는 `excuse`이고, `conversation_type`은 `group` 또는 `dm`이에요. `conversation_key`는 에이전트가 대화를 저장하는 키로, DM이면 `private:telegram:42` 같은 형태예요. `conversation_id`는 이벤트가 가져온 원래 ID로, DM에서는 사용자 ID예요. 에이전트는 각 대화에서 가장 최근에 받아들인 이벤트의 `reply_handle`, `connector_id`, `capabilities`를 기억하므로, 대화는 메시지를 한 번 보내면 닿을 수 있게 돼요.

다음 가져오기의 `acks`에 각 배달을 보고하세요.

| `status` | 의미 |
|---|---|
| `sent` | 모든 항목을 보냈어요. |
| `partial` | 처음 `sent_items`개 항목을 보냈어요. |
| `failed` | 아무것도 보내지 못했어요. |
| `expired` | `expires_in_s` 안에 보내기를 시작하지 못했어요. |
| `refused` | 커넥터가 이 대화를 더 이상 허용하지 않아요. |
| `unsupported` | 플랫폼이 이 대화에 먼저 보낼 수 없어요. |

규칙:

- **많아야 한 번.** ack가 어떻게 되든 에이전트는 배달을 한 번만 건네고 다시는 건네지 않아요. 최근 수백 개의 `delivery_id`를 보관하고 같은 것을 두 번 보내지 마세요.
- **순서대로.** 한 대화의 배달은 받은 순서대로 보내세요. 다른 대화는 동시에 보내도 돼요.
- **ack한 배달만 인정돼요.** 에이전트는 ack 없는 배달을 보내지 않은 것으로 취급하고, ack한 것만 보낸 것으로 기록해요. ack는 다음 가져오기까지 기다리되, 배달을 건넨 뒤 최대 `expires_in_s`에 60초를 더한 시간까지예요. 한 묶음을 다 보낸 뒤 다시 가져오세요.
- **활성 확인.** 90초 동안 가져오지 않은 커넥터는 사라진 것으로 봐요. 다시 가져올 때까지 그 대화에는 아무것도 대기열에 넣지 않고, 그를 위해 대기열에 있거나 ack 없이 건넨 것은 보내지 않은 것으로 끝나요. 한 묶음을 배달하면 바로 다시 가져오세요. 그 가져오기에 묶음의 ack도 실려요.
- **`unsupported`는 유지돼요.** 이 ack 뒤에는 이벤트가 다른 `reply_handle`을 가져올 때까지 에이전트가 그 대화의 대기열 추가를 멈춰요.
- **본문 종류.** 서명은 URL 경로를 포함하지 않아요. 그래서 에이전트는 아웃박스 엔드포인트로 온 이벤트 본문과 이벤트 엔드포인트로 온 `outbox.pull` 본문을 `400`과 코드 `invalid_schema`로 거부해요. 이벤트에는 `"kind": "event"`를 넣을 수 있어요. 다른 `kind`가 있는 이벤트는 거부돼요.

`code` 없는 404는 에이전트가 아웃박스를 제공하지 않는다는 뜻이에요. 코드 `outbox_disabled`인 `404`는 운영자가 `CONNECTOR_OUTBOX_ENABLED`로 껐다는 뜻이에요. 어느 쪽이든 한참 기다렸다가 다시 가져오세요.

## 아웃박스 없이 먼저 말하기

폴링할 수 없는 커넥터도 DM을 시작할 수 있어요. AstrBot 플러그인 작업이나 cron 항목 같은 자체 스케줄러가 `"proactive": true`가 붙은 일반 DM 이벤트를 `/v1/events`로 보내요. 에이전트는 텍스트를 페르소나에게 주는 신호("하루 동안 조용했어. 오늘 아침이 시험이었어")로 읽고, 500자에서 자르며, 그 사람의 말로는 절대 저장하지 않아요. 턴을 결정하는 것은 여전히 엔진의 먼저 말하기 지침이고, 페르소나를 조용히 둘 수도 있어요. 페르소나가 말하면 답변이 응답으로 돌아오고 스케줄러가 전달해요.

이 이벤트에는 커넥터의 일반 이벤트가 가진 것이 모두 필요해요. 서명 헤더, 모든 필수 필드, 그 사람에게 커넥터가 보내는 것과 같은 `platform`과 원래 `sender_id`, 비어 있지 않은 텍스트, 매번 새로운 `message_id`예요. `message_id`가 반복된 이벤트는 조용히 버려져요. 신호는 에이전트 자신의 말 걸기와 같은 DM 쿨다운(`PROACTIVE_DM_COOLDOWN_S`)에 포함되고, 그 사람의 활동으로 치지 않아요.

이 플래그는 항상 설정하세요. 없으면 에이전트가 신호를 그 사람의 말로 저장해요. 이 플래그가 붙은 그룹 이벤트는 맡아지고(`owned: true`이므로 커넥터는 자기 봇을 조용히 둬요) 읽지 않은 채 버려져요.

## 기능과 빠졌을 때의 영향

| 빠진 것 | 영향 |
|---|---|
| `outbox` | 예약된 말 걸기도, 후속 질문도, 그룹에서 모델 호출 실패 때의 변명도 없어요. QQ ID는 `QQ_ONEBOT_URL`이 설정되어 닿을 수 있으면 NapCat을 통해 여전히 받아요. DM의 변명은 응답의 `replies`로 돌아오므로 아웃박스가 필요 없어요. |
| `quote_text` | 에이전트는 자기가 직접 본 메시지일 때만 인용 메시지를 이해해요. |
| `reply_handle` | `outbox`가 없을 때와 같아요. |
| `addressed` 오류 | 페르소나가 자기에게 한 말을 배경 잡담으로 취급해요. |

## 커넥터 작성하기

1. 플랫폼에서 메시지를 받아요. 봇 자신의 메시지와 메시지가 아닌 이벤트(입장, 회수, 찌르기)는 건너뛰어요.
2. 위에서 설명한 이벤트를 만들어요. `addressed`는 플랫폼 자체의 멘션과 답장 규칙에서 설정해요.
3. 이벤트에 서명하고 보내요. `replies`를 순서대로 보내고, `owned`가 true이면 다른 봇 로직을 조용히 둬요.
4. 플랫폼이 먼저 보낼 수 있다면 `connector_id`, `reply_handle`, `capabilities: ["outbox"]`를 추가하고 가져오기 루프를 돌려요. 가져오고, 각 배달을 `reply_handle`로 전달하고, 다음 가져오기에서 ack해요.

`integrations/sdk/personagent_connector.py`가 3단계와 4단계를 처리해요.
