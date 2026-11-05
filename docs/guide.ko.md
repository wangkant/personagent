# personagent 사용자 가이드

[English](guide.md) · [简体中文](guide.zh-CN.md) · [繁體中文](guide.zh-TW.md) · [日本語](guide.ja.md) · 한국어 · [Español](guide.es.md) · [Français](guide.fr.md) · [Deutsch](guide.de.md) · [Português (Brasil)](guide.pt-BR.md) · [Русский](guide.ru.md)

이 가이드는 personagent를 설정하고, 채팅에 넣고, 가르치고, 관리하는 방법을 설명해요. [README](readme/README.ko.md)는 짧은 소개이고, [시작하기](start.ko.md)는 로컬 페이지를 화면별로 안내해요.

1. [설치와 홈 폴더](#설치와-홈-폴더)
2. [로컬 페이지](#로컬-페이지)
3. [먼저 보기: 데모](#먼저-보기-데모)
4. [터미널 명령](#터미널-명령): [설정](#터미널에서-설정하기) · [채팅](#터미널에서-채팅하기) · [서비스 실행](#서비스-실행하기)
5. [나만의 캐릭터로 만들기](#나만의-캐릭터로-만들기)
6. [채팅에 넣기](#채팅에-넣기): [QQ, WeChat, Telegram, Discord](#qq-wechat-telegram-discord) · [기타 플랫폼](#기타-플랫폼관리형-astrbot-경유) · [직접 실행하는 브리지](#직접-실행하는-브리지) · [먼저 말하기](#먼저-말하기)
7. [코딩 에이전트](#코딩-에이전트)
8. [가르치기](#가르치기)
9. [활동](#활동)
10. [측정하기](#측정하기)
11. [동작 방식](#동작-방식)
12. [개인정보와 동의](#개인정보와-동의)
13. [문제 해결](#문제-해결)
14. [0.x에서 업그레이드](#0x에서-업그레이드)
15. [현재 상태와 기타 문서](#현재-상태와-기타-문서)

## 설치와 홈 폴더

```sh
python -m pip install personagent
personagent
```

`personagent`는 브라우저에서 [로컬 페이지](#로컬-페이지)를 열어요. 다음 방법으로도 설치하거나 실행할 수 있어요.

| 방법 | 명령 |
|---|---|
| 설치 없이 실행 | `uvx personagent`([uv](https://docs.astral.sh/uv/)의 기능으로, Python도 대신 받아 줘요) |
| 영구적인 `personagent` 명령 | `uv tool install personagent` 또는 `pipx install personagent` |
| Windows, 소스 ZIP에서 | 압축을 풀고 `start.bat`을 더블클릭 |
| 클론에서 | `git clone https://github.com/wangkant/personagent.git`, `cd personagent`, `python -m venv .venv`, 그다음 `.venv/bin/python -m pip install -e .`와 `.venv/bin/python -m persona_agent`(Windows에서는 `.venv\Scripts\python.exe`) |

personagent는 Python 3.10–3.14에서 실행돼요. `start.bat`은 `.venv`를 만들고 의존성을 설치한 뒤 같은 페이지를 열어요. `pyproject.toml`의 의존성 목록이 바뀔 때마다 다시 설치해요.

**홈 폴더**에는 설정(`.env`), 캐릭터(`persona.txt`), 학습 내용(`runtime/`), 채팅 플랫폼(`platforms/`)이 들어 있어요. `platforms/`에는 관리형 AstrBot과, personagent가 직접 연결하는 플랫폼의 자격 증명을 저장하는 `direct.json`이 있어요. personagent는 다음 중 처음 해당하는 폴더를 사용해요.

1. `--home DIR` 또는 `AGENT_HOME`으로 지정한 폴더. `--home`은 `personagent chat --home D:\bot`처럼 명령 앞뒤 어디에나 올 수 있어요.
2. 클론에서 실행할 때는 그 클론.
3. `.env`와 `persona.txt`가 모두 있으면 현재 폴더.
4. 첫 설정 때 만들어지는 `~/personagent`.

한 번의 설치로 캐릭터 여러 개를 실행하려면 각각에 별도의 홈을 주세요.

이 가이드는 명령을 `personagent ...`로 적어요. 설치하지 않았다면 앞에 `uvx`를 붙이세요. 클론에서는 `.venv/bin/python -m persona_agent ...`가 같은 일을 해요(Windows에서는 `.venv\Scripts\python.exe -m persona_agent ...`).

## 로컬 페이지

`personagent`(또는 `personagent start`)는 이 컴퓨터에서만 접속할 수 있는 페이지를 제공하고 브라우저에서 열어요. 페이지에는 보기가 네 개 있어요.

- **채팅**은 브라우저에서 캐릭터와 일대일로 나누는 채팅이에요. 채팅 플랫폼을 담당하는 것과 같은 에이전트가 답해요.
- **활동**는 캐릭터가 있는 채팅, 최근에 한 말, 배운 것, 내 결정을 기다리는 것을 보여 줘요. [활동](#활동)를 참고하세요.
- **앱 연결**는 캐릭터를 QQ, WeChat, Telegram, Discord와 다른 플랫폼에 넣어요. [채팅에 넣기](#채팅에-넣기)를 참고하세요.
- **캐릭터 및 설정**에서는 모델 서비스(OpenRouter, DeepSeek, SiliconFlow, Alibaba Bailian, Zhipu GLM, Moonshot, Volcengine Ark, OpenAI, Google Gemini, Ollama, 그 밖의 OpenAI 호환 서비스)를 고르고, API 키를 붙여 넣고, 이름과 준비된 성격을 골라요. **확인하고 채팅 시작**은 작은 요청 한 번으로 키를 시험하고 성공할 때만 저장해요. 설정 후에는 **페르소나** 칸에 `persona.txt`가 표시돼요. **페르소나 저장**는 새 내용으로 에이전트를 다시 시작하고 배운 것은 유지해요. **추가 기능**는 Tavily 웹 검색(무료 기본값은 DuckDuckGo), 이미지 이해, 선택한 앱에서 먼저 말하기를 켜요.

앱을 연결하기 전까지 채팅 보기에는 짧은 **시작하기** 막대가 표시돼요.

`personagent`를 다시 실행하면 이미 열려 있는 페이지를 재사용해요. `--no-browser`는 브라우저를 여는 대신 링크를 출력해요.

PyPI에 새 personagent가 있으면 채팅 보기에 pip, uvx, uv tool, pipx, Git 클론 중 설치 방식에 맞는 업데이트 명령을 담은 알림이 표시돼요. 압축을 푼 소스 ZIP이라면 알림은 릴리스 페이지로 연결돼요. 터미널에도 같은 명령이 출력돼요. 알림을 닫으면 그 버전에서는 숨겨지고, 버전 번호 아래의 **N 업데이트 가능**으로 다시 볼 수 있어요. `personagent up`과 `personagent doctor`도 새 버전을 알려 줘요. 페이지와 `up`은 하루에 많아야 한 번 백그라운드에서 pypi.org에 물어봐요. `doctor`는 마지막 응답이 하루를 넘었으면 바로 물어봐요. 확인을 끄려면 `UPDATE_CHECK_ENABLED=false`를 설정하세요.

페이지는 에이전트와 연결된 플랫폼을 백그라운드에서 시작하므로, 사용하는 동안 창을 열어 두세요. **종료**을 클릭하든, Ctrl+C를 누르든, 창을 닫든 시작한 것은 모두 함께 멈춰요. 이전 실행이 충돌해 프로세스가 남았다면 다음 시작 때 먼저 멈춰요.

## 먼저 보기: 데모

`personagent demo`는 스크립트로 된 모델로 세 장면을 재생하므로 키가 필요 없어요. 어떤 그룹 메시지를 왜 건너뛰는지, 교정에서 어떻게 배우는지, 낯선 사람이 지시를 심으려다 어떻게 실패하는지를 보여 줘요. 한 장면만 재생하려면 이름을 지정하세요(`quiet`, `teach`, `troll`). 다른 언어로 보려면 `--lang`과 언어 코드를 붙이세요(예: `--lang ja`).

아래는 `personagent demo teach` 실행을 줄인 것이에요. 모델의 대사는 스크립트지만 원장과 승격 규칙은 실제 코드예요.

```text
  Alex: Nova, the deploy failed again
  Nova: did you check the logs? roll back first, then diff the configs
  Alex: Nova, I was just venting
      judged: rejection, accepted: "Alex was venting, not asking for a fix"
      ledger: negative only (it says the reply was off, not what to say)
      Nova's next reply to Alex counts as its second try
  Nova: fair. that's a rough end to the day
  Alex: haha yeah it is, thanks Nova
      judged: positive, accepted: "Alex agreed with the second try and thanked Nova"
      ledger: weak (a laugh or a thanks never changes anything alone)
      ledger: Alex accepted the second try: strong (Alex is who the reply was for)

  fix: "did you check the logs? roll back first, ..." -> "fair. that's a rough end to the day"
    [x] 2 of 2 agreeing reactions
    [x] 1 of 1 strong
    [x] same chat
    [x] 1 of 1 person (PROMOTE_MIN_SPEAKERS)
    [x] nothing disagrees, no rival fix
    now in use: 2 agreeing reactions, 1 strong, same chat
```

이 장면은 교육 전후에 같은 메시지를 보내요. 누군가의 노트북이 데모 도중 고장 났다는 메시지예요. 교정 전에는 Nova가 해결책을 내놓아요. 교정 후에는 공감해 줘요. 데모는 키가 설정되어 있어도 스크립트 그대로이므로 매번 같고 비용이 들지 않아요. `personagent demo --online`은 대신 내 모델로 재생하며, 토큰을 쓰고 실행마다 달라져요.

## 터미널 명령

페이지에서 하는 모든 일을 터미널에서도 할 수 있어서 서버와 스크립트에 잘 맞아요.

| 명령 | 하는 일 |
|---|---|
| `personagent start` | 로컬 페이지 열기(`--terminal`이면 터미널 메뉴) |
| `personagent init` | 홈 설정. `--terminal`은 터미널에서 질문하고, `--no-input`은 플래그를 받아요 |
| `personagent chat` | 터미널에서 모의 그룹 채팅 |
| `personagent demo` | 위의 스크립트 데모 |
| `personagent run` | 서비스만 실행. 직접 운영하는 커넥터용 |
| `personagent up` | 서비스, personagent가 직접 연결하는 플랫폼, 관리형 AstrBot을 함께 실행 |
| `personagent connect astrbot` | AstrBot 연결(`--install`은 관리형을 내려받고, `--start`는 시작해요) |
| `personagent connect claude-code`, `personagent connect codex`, `personagent connect dsh` | 캐릭터를 [코딩 에이전트](#코딩-에이전트)에 넣기(앞의 둘은 `--react`로 턴이 끝날 때 한마디, `--remove`로 되돌리기) |
| `personagent mcp` | 코딩 에이전트가 시작하는 MCP 서버. 직접 실행하지 않아요 |
| `personagent doctor` | 설정과 의존하는 모든 서비스 확인 |
| `personagent learned` | 배운 것을 검토, 승격, 롤백 |
| `personagent eval` | 발언, 페르소나, 학습 측정 |

모든 명령은 `--help`를 받아요.

### 터미널에서 설정하기

`personagent init --terminal`은 페이지와 같은 질문을 처음 고른 언어로 묻고, 각 용어를 한 줄로 설명해요.

- **AI 서비스.** 프리셋은 페이지와 같아요. 기본값은 OpenRouter의 `openrouter/free`로, 각 요청을 무료 모델 중 하나에 넘겨요. 키는 무료예요. 한도는 분당 20회, 하루 50회이고, 크레딧을 10개 이상 구매하면 하루 1000회예요. 답장뿐 아니라 모든 모델 호출이 계산되고, 하루는 UTC 자정에 초기화돼요. 한도를 다 쓰면 캐릭터가 지금은 답할 수 없다고 말하고, `runtime/desktop/agent.log`에 OpenRouter의 이유가 남아요. 요청마다 모델이 바뀌므로 하나를 골랐을 때보다 캐릭터의 말투가 더 흔들리고, 일부 무료 제공업체는 받은 내용을 보관해요. 캐릭터를 더 안정적으로 하려면 같은 키로 유료 모델을 쓰세요. 있는 곳에서 OpenRouter에 접속하기 어렵다면 Zhipu의 `glm-4.7-flash`도 무료예요. Ollama는 이미 받아 둔 모델 이름을 적으세요. Ollama에는 키가 필요 없어요.
- **키.** 입력은 기본적으로 가려져요. 보이게 선택할 수 있으며, 그러면 재설정할 때 저장된 키도 표시돼요. 마법사는 작은 요청 한 번으로 키를 시험해요. 실패하면 호출한 주소, HTTP 상태, 가능한 해결책을 보여 줘요.
- **캐릭터.** 이름과, 준비된 캐릭터 넷(재치 있는 친구, 다정한 경청자, 게이머, 책벌레) 중 하나 또는 직접 쓰는 기본 캐릭터.
- **AstrBot.** 선택 사항이며 처음에는 건너뛸 수 있어요. [직접 실행하는 브리지](#직접-실행하는-브리지)를 참고하세요.

스크립트 등에서 질문 없이 설정하려면 `personagent init --no-input`을 `--provider`, `--model`, `--key-env VAR`, `--name`, `--lang`, `--persona`와 함께 실행하세요. 새 홈에서는 `--key-env`나 셸의 `LLM_API_KEY`에서 온 키가 어디 것인지 알리기 위해 `--provider`나 `--base-url`이 필요해요. `--provider other`에는 `--base-url`도 필요해요. `personagent init --help`가 모든 플래그를 나열해요. `personagent init`을 터미널 없이 이 플래그들도 없이 실행하면 질문을 건너뛰고 그렇다고 알린 뒤 코드 2로 종료해요.

### 터미널에서 채팅하기

`personagent chat`은 캐릭터가 있는 모의 그룹 채팅으로 데려가요. 일반 줄은 평범한 그룹 대화이고, 체험은 캐릭터가 끼어들지와 그 이유를 알려 줘요. 이름이 들어간 줄은 캐릭터를 불러요.

```text
Alex> anyone around tonight?
  (Nova stays quiet: not addressed, 1 of 4 messages)

Alex> Nova, the deploy failed again
  Nova > did you check the logs? roll back first, then diff the configs
```

| 입력 | 용도 |
|---|---|
| `/reply <text>` | 마지막 답장을 인용. 배울 수 있는 반응으로 계산돼요 |
| `/as Sam <text>` | 다른 사람으로 말하기: `/as Sam Nova, you free tonight?` |
| `/admin <text>` | 한 번 관리자로 말하기: `/admin Nova, how was your day?` |
| `/why` | 마지막 답장을 한 이유와 그에 대해 원장에 있는 내용 보기 |
| `/learned` | 이 채팅에서 배운 것 보기 |
| `/reset` | 채팅과 체험에서 배운 것 지우기 |
| `/quit` | 나가기 |

`/as`와 `/admin` 줄도 그룹 규칙을 따르므로, 답을 받으려면 이름을 넣으세요. 네 글자보다 짧고 캐릭터 이름이 없는 줄은 끼어들기 판단에 계산되지 않아요. [기억 명령](#기억-명령)도 여기서 동작해요.

| 플래그 | 하는 일 |
|---|---|
| `--name Alex` | 내 이름 설정 |
| `--admin` | 모든 줄을 관리자의 말로 만들기 |
| `--dm` | 일대일 채팅으로 만들기 |
| `--lang <code>` | `AGENT_LANG` 덮어쓰기(예: `--lang ja`) |
| `--trigger N` | 끼어들기를 고려하기 전 메시지 수(기본값 4) |

체험은 실제 말할지 말지 판단, 출력 점검, 기억 명령, 학습을 실행해요. 실제 봇이 30개를 기다리는 곳에서 4개 뒤에 끼어들기를 고려해요. 배운 것은 홈 폴더의 `runtime/trial/`에 머물며 실제 봇과 분리돼요. `personagent learned`에는 보이지 않고 `/reset`으로 지워져요. 체험은 허용 목록과 실제 전달을 건너뛰어요. 자기 평가, 비전, 후속 질문, 캐릭터가 스스로 시작하는 메시지도 꺼요. 모델 호출이 실패하면 무엇을 확인할지 한 줄로 출력해요.

```text
Alex> Nova, you there?
  [error: the model provider refused the key or the account (HTTP 401); check LLM_API_KEY, then run `personagent doctor`]
```

### 서비스 실행하기

`personagent run`은 커넥터가 연결하는 서비스만 `http://127.0.0.1:8080`에서 시작해요. 시작할 때 버전, 주소, 홈 폴더, 에이전트가 켜져 있는지를 출력해요. `--host`와 `--port`는 `SERVER_HOST`와 `SERVER_PORT`를 덮어써요. 커넥터를 직접 운영할 때 이 명령을 쓰세요.

`personagent up`은 서비스를 페이지나 `connect astrbot --install`로 연결한 모든 플랫폼과 함께 시작해요. 브라우저는 열지 않아요. Ctrl+C로 모두 멈추고, 각 프로세스는 홈 폴더의 `runtime/desktop/`에 로그를 써요.

## 나만의 캐릭터로 만들기

홈 폴더의 `persona.txt`가 캐릭터를 정의해요. 페이지의 **페르소나** 칸에서 편집하거나, 아무 편집기에서 편집한 뒤 재시작하세요. 캐릭터가 누구인지, 평소 어떻게 말하는지, 중요한 상황에서 무엇을 하는지 적으세요. 모델에게 "자연스럽게 말해"라고 하는 것보다 구체적인 습관이 더 잘 통해요.

```text
Your name is Nova. You chat with friends about films and cooking.
You speak directly and make the occasional joke.

Usually reply in a sentence or two. Explain more when someone asks a serious question.
When a friend vents, listen before offering advice.
If you have not seen a film, say so instead of inventing an opinion.
```

`AGENT_LANG`은 `en`, `zh`, `zh-TW`, `ja`, `ko`, `es`, `fr`, `de`, `pt-BR`, `ru` 중 하나예요. 시작 페르소나, 터미널 설정, 체험과 데모, `--help`와 `doctor`, 기억 명령, 고정 답장을 정해요. 함께 제공되는 예시, 필터, 점검은 `zh`와 `zh-TW`에서는 중국어, 나머지에서는 영어예요. 내 페르소나를 번역하지는 않아요. [.env.example](../.env.example)이 모든 설정을 설명해요.

로컬 페이지 오른쪽 위의 언어 메뉴에는 English, 简体中文, 繁體中文, 日本語, 한국어, Español, Français, Deutsch, Português (Brasil), Русский가 있어요. 페이지 언어를 바꾸고 브라우저가 기억해요. 설정을 저장하면 페이지 언어가 `AGENT_LANG`이 돼요. 캐릭터는 채팅에서 쓰는 언어로 답해요. 프롬프트는 영어와 중국어예요. 모델을 거치지 않는 [기억 명령](#기억-명령)과 몇 가지 고정 답장은 10개 언어 모두에서 동작해요.

제공된 파일을 덮어쓰려면 같은 이름의 파일을 홈 폴더의 `data/`에 넣으세요. 덮어쓰지 않은 파일은 personagent에 포함된 사본을 써요.

| 파일 | 내용 |
|---|---|
| `data/examples.<lang>.jsonl` | 모델이 따라 할 수 있는 대화 예시 |
| `data/feedback.<lang>.jsonl` | 답장과 더 나은 버전의 짝 |
| `data/lorebook.<lang>.json` | 키워드가 나올 때 더해지는 배경 메모 |
| `data/output_filter.<lang>.json` | 실제 답장에 적용하는 치환과 거부 규칙 |
| `persona.card.json` | 이모지, 문자 집합, 길이 선택 설정. 예: `{ "reply_style": { "emoji": true, "max_chars": 320 } }` |

이미지를 보게 하려면 `VISION_MODEL`, `VISION_API_KEY`, `VISION_BASE_URL`을 설정하거나 **추가 기능**에서 이미지 이해를 켜세요.

## 채팅에 넣기

로컬 페이지에서 **앱 연결**를 열고 플랫폼을 고르세요. 페이지는 플랫폼 자체 콘솔에서 복사하는 값만 물어봐요. 그 값을 플랫폼에 확인하고, 연결을 시작하고, 플랫폼이 받아들였는지 몇 초 기다려 확인해요. 플랫폼이 거부하면 페이지가 그렇다고 알리고 아무것도 저장하지 않아요. 연결된 플랫폼은 위쪽에 나열되며, 다시 설정하거나 연결을 끊을 수 있어요. 페이지나 `personagent up`이 시작할 때마다 다시 시작돼요.

```text
Chat platform  ⇄  connector  ⇄  personagent  ⇄  Model API
```

커넥터는 플랫폼에 로그인해 각 메시지를 personagent에 넘기고 답장을 가져와요. 세 종류가 있어요.

### QQ, WeChat, Telegram, Discord

personagent는 이 넷을 하나의 백그라운드 프로세스에서 직접 연결해요. AstrBot도 NapCat도 필요 없어요.

| 플랫폼 | 할 일 |
|---|---|
| QQ | 모바일 QQ로 코드를 스캔하고 확인해요. 공식 QQ 봇이 만들어지거나 이미 있는 봇을 사용하며, personagent가 키를 가져와요. **대신 값 붙여넣기**는 [QQ 봇 페이지](https://q.qq.com/qqbot/openclaw/login.html)에서 만든 봇의 AppID와 AppSecret을 받아요. |
| WeChat(개인) | WeChat으로 코드를 스캔하고 로그인을 확인해요. 연결은 Tencent의 iLink 봇 API를 쓰며 일대일 채팅만 처리해요. WeChat은 이런 봇에 그룹 메시지를 전달하지 않기 때문이에요. |
| Telegram | [@BotFather](https://t.me/BotFather)로 봇을 만들고 토큰을 붙여 넣어요. |
| Discord | [Developer Portal](https://discord.com/developers/applications)에서 봇 토큰을 복사하고 Message Content Intent를 켜요. |

QQ는 모바일 QQ의 연락처 → 봇에서 봇을 찾은 뒤 개인적으로 채팅하거나 그룹에 추가하세요. 봇이 인증되기 전까지 QQ는 내가 소유한 그룹에만 참여를 허용해요. 어떤 그룹 메시지를 받을지는 QQ에서 그 그룹의 봇 프로필에서 골라요. 인증은 [QQ 봇 가이드](https://bot.q.qq.com/wiki/bot_new_product-intro/)에서 다뤄요.

자격 증명은 홈 폴더의 `platforms/direct.json`에 저장돼요.

### 기타 플랫폼(관리형 AstrBot 경유)

다른 플랫폼을 처음 연결할 때 personagent는 [AstrBot](https://docs.astrbot.app)과 전용 Python 3.12 런타임을 홈 폴더의 `platforms/`에 내려받아요. 내려받는 동안 페이지를 열어 두세요. 그 뒤 AstrBot은 대시보드도 두 번째 로그인도 없이 백그라운드에서 실행돼요. 전역 `uv`가 필요 없고 personagent의 Python은 건드리지 않아요. 페이지에서 플랫폼을 연결하면 그 플랫폼의 그룹과 DM이 캐릭터에 닿아요. 다른 플랫폼의 허용 목록은 그대로예요.

| 그룹 | 플랫폼 | 필요한 것 |
|---|---|---|
| 값 한두 개 붙여 넣기 | KOOK, Feishu / Lark, DingTalk, Slack, WeCom AI 봇, Mattermost, Misskey | 토큰, 앱 ID와 시크릿, 또는 서버 주소와 토큰. Feishu는 장기 연결, DingTalk는 Stream 모드를 쓰므로 둘 다 공개 주소가 필요 없어요. Slack은 페이지의 링크가 Socket Mode, 범위, 이벤트가 설정된 앱을 만들어요. `connections:write`가 있는 앱 수준 토큰을 추가하고, 앱을 설치하고, 두 토큰을 붙여 넣으세요. WeCom AI 봇은 장기 연결로 만드세요. |
| 고급 | WeCom 앱, WeChat 공식 계정, QQ(웹훅) | 표시된 콜백 포트로 전달하는 공개 주소 |
| 고급 | OneBot v11(NapCat), Satori | 이 컴퓨터에서 실행되는 다른 소프트웨어: `ws://127.0.0.1:<port>/ws`로 지정한 NapCat, 또는 Satori 서버 |

LINE은 제공하지 않아요. AstrBot이 LINE 콜백을 대시보드를 통해서만 받기 때문이에요.

터미널에서는 `personagent connect astrbot --install`이 같은 관리형 AstrBot을 내려받아 연결해요. `--platform telegram --token <bot token>`을 더하면 동시에 플랫폼을 켜요. 설정하기 전까지 그룹도 DM도 허용되지 않아요. 내려받기에 실패하면 같은 명령을 다시 실행하세요. 기존 설정은 유지돼요. `personagent connect astrbot --start`는 관리형 AstrBot을 시작하고, `personagent up`은 다른 모든 것과 함께 시작해요.

### 직접 실행하는 브리지

아래 프로젝트는 personagent와 함께 동작하는 서드파티 소프트웨어예요. QQ, WeChat, Telegram, Discord에는 어느 것도 필요 없어요.

| 브리지 | 닿는 곳 |
|---|---|
| 이미 실행 중인 [AstrBot](https://docs.astrbot.app) | 그 플랫폼들 |
| [NapCat](https://github.com/NapNeko/NapCatQQ)(OneBot v11), AstrBot 경유 | 개인 QQ 계정의 QQ |
| [Koishi](https://koishi.chat) 또는 다른 Satori 서버, [Satori 커넥터](../integrations/satori/README.ko.md) 경유 | 그 서버가 로그인한 곳 |
| [Matrix](../integrations/matrix/README.ko.md), mautrix 브리지 경유 | Matrix 방, WhatsApp, Signal, Messenger, Instagram, Google Messages |

그 밖의 것은 메시지마다 서명된 HTTP 요청 하나를 받는 [커넥터 프로토콜](connectors.ko.md)로 연결할 수 있어요. 여러 커넥터가 하나의 personagent를 동시에 쓸 수 있어요. 실제 운영은 [배포 가이드](deploy.ko.md)에서 다뤄요.

**이미 실행 중인 AstrBot.** AstrBot은 작은 플러그인 [astrbot_plugin_personagent](../integrations/astrbot/astrbot_plugin_personagent/README.ko.md)를 통해 personagent에 메시지를 넘겨요. 플러그인은 personagent에 포함되어 있고 관리형 AstrBot에는 자동으로 들어가요. `personagent connect astrbot`은 AstrBot을 찾거나 폴더를 인수로 받아요. 플러그인을 설치하고, 공유 `CONNECTOR_TOKEN`을 양쪽에 쓰고, 어떤 그룹을 허용할지 물어봐요. 그룹에서 `/sid`를 보내면 ID를 볼 수 있어요.

다른 컴퓨터의 AstrBot이라면:

1. [최신 릴리스](https://github.com/wangkant/personagent/releases/latest)에서 `astrbot_plugin_personagent.zip`을 내려받아요.
2. AstrBot 플러그인 페이지의 **Install from File**에서 업로드해요.
3. 플러그인의 `connector_token`을 personagent `.env`의 `CONNECTOR_TOKEN`으로 설정해요.
4. `personagent_url`을 personagent의 HTTPS 주소로 설정해요. 아래의 **Docker 또는 다른 호스트의 AstrBot**을 참고하세요.
5. `personagent run`을 실행한 뒤 AstrBot을 재시작하거나 플러그인을 다시 불러와요.

personagent를 업그레이드한 뒤에는 `connect astrbot`을 다시 실행하거나 새 zip을 업로드하세요. AstrBot 4.29 이상은 설치된 사본을 교체해요. 더 오래된 버전에서는 이전 사본을 먼저 제거하되, 설정을 유지하려면 **Also delete plugin configuration file**을 체크하지 마세요.

플러그인은 `groups` 목록에 있는 그룹과 `dm_users`에 있는 사용자의 DM만 전달해요. 둘 다 AstrBot WebUI에서 바꿀 수 있어요. `.env`를 편집한 뒤에는 personagent를, 플랫폼이나 플러그인을 바꾼 뒤에는 AstrBot을 재시작하세요.

AstrBot 폴더를 주면 `connect astrbot`은 아무것도 묻지 않고, 토큰으로 플랫폼을 켤 수 있어요.

```bash
personagent connect astrbot <AstrBot data dir> --platform telegram --token <bot token>
```

`--platform`은 `telegram`, `discord`, `slack`, `kook`, `lark`, `qq_official`을 받아요. Slack은 `--app-token`도, Lark와 QQ는 `--app-id`와 `--app-secret`도 받아요. AstrBot에 이미 설정된 어댑터에서는 자격 증명만 바꾸고 프록시나 베이스 URL 같은 나머지는 모두 유지해요. `personagent connect --help`가 나머지 옵션을 나열해요.

**NapCat을 통한 QQ.** 이 경로는 공식 봇 대신 개인 QQ 계정을 사용해요. NapCat이 그 계정으로 로그인해 AstrBot의 `aiocqhttp`(OneBot v11) 어댑터에 리버스 WebSocket `ws://127.0.0.1:6199/ws`로 연결돼요. `personagent connect astrbot`에서 QQ를 고르거나 폴더와 함께 `--qq`를 주면 플러그인의 `excluded_platforms`에서 `aiocqhttp`를 빼고 `CONNECTOR_QQ_PLATFORMS=aiocqhttp`를 설정해요. 그러면 QQ 채팅은 같은 ID와 기억을 유지해요. NapCat의 HTTP 서버(`QQ_ONEBOT_URL`)는 선택 사항이에요. 이것과 `QQ_BOT_ID`를 설정하면 personagent가 오프라인 동안 놓친 멘션을 따라잡아요. [중국어 단계별 가이드](deploy.zh-CN.md#第三方路线astrbot--napcat)에 이 경로의 짧은 절이 있어요. 서드파티 QQ 클라이언트는 계정을 위험에 빠뜨리므로 먼저 [면책 조항](DISCLAIMER.ko.md)을 읽으세요.

직접 OneBot 경로(`/v1/onebot`)는 폐지 예정이며 1.x 동안 유지돼요. 답장을 `QQ_ONEBOT_URL`로 보내므로, 아직 쓴다면 그것을 설정하세요. 그것 없이 경로가 설정된 것처럼 보이면 `personagent doctor`가 경고해요. AstrBot 전달과 함께 실행하지 마세요. 모든 메시지가 두 번 도착해요.

**Docker 또는 다른 호스트의 AstrBot.** 플러그인은 같은 호스트(또는 네트워크를 공유하는 컨테이너)나 `connector_token`이 설정된 HTTPS 주소로만 보내요. `http://host.docker.internal:8080` 같은 그 밖의 일반 `http://`는 거부하고 `refusing unsafe personagent_url`을 기록한 뒤 AstrBot 자체 모델이 답하게 해요. 해결책은 두 가지예요.

- AstrBot 컨테이너에 호스트 네트워킹을 주세요. compose 파일의 `network_mode: host` 또는 `docker run --network host`예요. Docker Desktop 4.34 이상에서는 "Enable host networking"도 켜세요.
- personagent에 HTTPS 주소를 주고 플러그인의 `personagent_url`로 설정하세요. `connect astrbot --url https://...`가 대신 써 줘요.

같은 compose 파일의 NapCat 컨테이너에도 호스트 네트워킹이 필요해요.

personagent는 `127.0.0.1:8080`에서 수신하며, 빈 `SERVER_HOST`도 같은 뜻이에요. 네트워크 주소에서 수신하려면(`--host 0.0.0.0` 또는 `SERVER_HOST`) `CONNECTOR_TOKEN`이 필요해요. 터널은 외부 요청을 로컬처럼 보이게 할 수 있으므로, 컴퓨터 한 대에서도 프록시나 터널을 추가하기 전에 토큰을 설정하세요. 나머지는 [엔드포인트 공개하기](deploy.ko.md#엔드포인트-공개하기)에서 다뤄요.

### 먼저 말하기

누구에게도 답장이 아닌 메시지가 있어요. 말 걸기(`PROACTIVE_ENABLED`, 기본값 꺼짐), 거부 뒤의 후속 질문, 그룹에서 모델이 실패할 때 보내는 변명이 그래요. DM에서는 변명이 기다리는 메시지의 응답으로 돌아가요. personagent는 이런 메시지를 아웃박스에 넣고, 봇이 먼저 말할 수 있는 플랫폼에서 커넥터가 가져와 보내요. WeChat 공식 계정과 WeCom 스마트 봇은 안 돼요. QQ는 공식 봇의 자발적 메시지에 속도 제한을 두고 사용자가 끌 수도 있어요. `PROACTIVE_PLATFORMS=qq_official`은 말 걸기를 QQ 공식 봇으로, `qq`는 NapCat을 통한 QQ로 제한해요. 페이지에서는 **추가 기능**의 **가끔 먼저 말하기**가 두 설정을 써요. [배포 가이드](deploy.ko.md#플랫폼-여러-개)를 참고하세요.

## 코딩 에이전트

Codex, Claude Code, DeepSeek Harness(`dsh`)는 MCP로 캐릭터에 닿아요. 모델 키를 저장한 상태에서 다음 중 하나 이상을 실행하세요.

```bash
personagent connect claude-code
personagent connect codex
personagent connect dsh
```

첫 번째는 사용자 범위로 `claude mcp add`를 호출해요. 두 번째는 Codex 폴더(`CODEX_HOME` 또는 `~/.codex`)의 `config.toml`에 써요. 세 번째는 `DSH_HOME` 또는 `~/.dsh` 아래 모든 프로필의 `cordis.patch.yml`에 항목을 더해요. 데스크톱 앱이나 `dsh web` 같은 DeepSeek Harness의 각 실행 방식은 처음 시작할 때 프로필을 얻으므로, 연결하기 전에 한 번 시작하고 그 뒤에 재시작하세요. 셋 다 이 설치와 이 홈을 지정하므로, 둘 중 하나를 옮긴 뒤에는 명령을 다시 실행하세요. `--react`를 썼다면 함께 붙이세요. 빼고 실행하면 훅이 빠져요. 새 세션을 시작하고 코딩 에이전트에게 캐릭터에게 뭔가 말해 달라고 하세요.

도구는 두 개예요.

| 도구 | 하는 일 | 비용 |
|---|---|---|
| `talk` | 로컬 페이지와 같은 일대일 채팅에서 같은 기억으로 보내는 메시지 하나. 페이지가 답한 경우, 코딩 에이전트에서 한 턴은 다시 불러온 뒤 페이지의 채팅에 나타나요. `Nova, what do you remember?` 같은 기억 명령도 여기서 동작해요. | 모델 서비스의 답장 하나(기억 명령 제외) |
| `character` | 이름과 `persona.txt` 읽기 | 없음 |

Claude Code와 Codex는 첫 `talk` 전에 물어보며, 그 프롬프트에서 이후를 허용할 수 있어요. `dsh headless`는 묻지 않아요. 답할 사람이 없는 실행에는 미리 권한이 필요해요. `claude -p`는 `--allowedTools mcp__personagent__talk`를 받고, `codex exec`는 `config.toml`에 다음이 필요해요.

```toml
[mcp_servers.personagent.tools.talk]
approval_mode = "approve"
```

**무엇이 답하나요.** 열린 페이지가 먼저 답하고, 그다음 `personagent up`이 실행 중인 서비스예요. 둘 다 없으면 MCP 서버가 백그라운드에서 페이지를 시작하고, 페이지는 코딩 세션이 끝날 때 연결한 채팅 앱과 함께 끝나요. 동시에 두 세션이면 페이지 하나를 공유해요. 그런 페이지가 떠 있을 때 `personagent`를 실행하면 링크를 출력하고, 페이지는 여전히 시작한 세션과 함께 끝나요. 그런 페이지가 떠 있을 때 `personagent up`을 실행하지 마세요. 코딩 세션을 먼저 끝내세요.

**턴이 끝날 때 한마디.** Claude Code와 Codex에서는 `--react`가 Stop 훅을 추가해요. DeepSeek Harness는 지원하지 않아요. 그 훅 브리지는 Stop 훅에 마지막 메시지를 넘기지 않고 훅의 출력도 보여 주지 않아요. 코딩 에이전트가 턴을 끝내면 캐릭터는 [자발적 신호](connectors.ko.md#아웃박스-없이-먼저-말하기)를 받아 내게 한마디 하거나 넘어가요. 그 한마디는 내게 오고 코딩 에이전트에게는 가지 않아요.

```bash
personagent connect claude-code --react
```

- 신호에는 폴더 이름과 코딩 에이전트의 마지막 메시지 앞 300자가 담겨 있어서, 그 텍스트가 모델 서비스로 가요. 한마디와 모델이 신호에서 메모한 것은 캐릭터의 기억에 남아요. 그래서 기본값이 꺼짐이에요.
- 매번 모델 호출 한 번의 비용이 들고, `CODING_REACT_COOLDOWN_S`(기본값 30분)마다 많아야 한 번이에요.
- 이미 실행 중인 캐릭터 서비스만 쓰고 절대 새로 시작하지 않아요.
- Codex는 새 훅을 신뢰한 뒤에만 실행해요. Codex 세션에서 `/hooks`를 입력하세요.

**유의할 점.** `talk`는 코딩 에이전트가 쓴 것을 모델 서비스와 캐릭터의 기억으로 보내요. 도구 설명은 코딩 에이전트에게 내가 말하고 싶은 것만 보내고 코드나 비밀은 절대 보내지 말며, 답장을 지시가 아니라 채팅으로 다루라고 알려요. 캐릭터의 메모는 그룹에서 사람들이 한 말에서 올 수 있기 때문이에요. 이것은 모델에 대한 지시이지 보증이 아니므로, 답장을 받아 무언가를 할 경우에 대비해 코딩 에이전트의 권한 프롬프트를 유지하세요.

**되돌리기.** `--remove`는 서버와 훅을 빼고 코딩 에이전트의 나머지 설정은 그대로 둬요. personagent를 제거하기 전에 하세요.

```bash
personagent connect claude-code --remove
personagent connect codex --remove
personagent connect dsh --remove
```

**기타 도구.** stdio로 MCP를 쓰는 것이라면 무엇이든 서버를 직접 시작할 수 있어요. 홈이 기본 폴더가 아니면 `--home`이 필요해요.

```json
{"mcpServers": {"personagent": {"command": "personagent", "args": ["--home", "/path/to/home", "mcp"]}}}
```

## 가르치기

### 기억 명령

이 명령은 채팅에서 사용해요. 명령은 @ 멘션이나 인용 뒤에 메시지의 맨 앞에 와야 해요. Nova를 내 `PERSONA_NAME`으로 바꾸세요.

| 말하기 | 일어나는 일 |
|---|---|
| `Nova, remember Sam is vegetarian` | 이 채팅에 메모를 저장하고, 누가 저장했고 누구에 관한 것인지 기록해요 |
| `Nova, forget vegetarian` | 내가 저장했거나 나에 관한, 일치하는 메모를 삭제해요. 관리자는 무엇이든 삭제할 수 있어요 |
| `Nova, what do you remember` | 내가 볼 수 있는 메모를 나열해요. 메시지 전체가 이것이어야 해요 |
| `Nova, what have you learned` | 메모, 배운 답장과 수정, 두 번째 목소리나 관리자를 기다리는 제안을 세고, 최근 변경과 통과한 이유를 보여 줘요 |

메모가 누구에 관한 것인지:

- 일인칭 메모나 내 이름을 언급한 메모는 나에 관한 것이에요.
- 방의 다른 구성원 이름을 언급한 메모는 그 사람에 관한 것이고, 그 사람이 있을 때 나와요.
- 그 밖의 메모는 그룹 전체의 것이에요. 모든 구성원이 볼 수 있고, 떠올릴 때 "from <name>"으로 표시돼요.

메모는 해당 인물, 저장한 사람, 관리자만 읽을 수 있어요. 잊게 할 수 있는 것은 저장한 사람, 해당 인물, 관리자뿐이에요.

이 명령은 DM에서도 그룹처럼 이름을 앞에 붙이면 동작해요. 그룹에 있는 나에 관한 메모는 DM까지 따라와요. 내게 하는 답장에 쓰이고, `what do you remember`에 나열되고, `forget`으로 삭제돼요. 반대 방향은 없어요. DM에서 한 말은 그 DM에 머물러요.

**추가 기능**의 **그룹 간에 기억 공유**(`MEMORY_SHARE_ROOMS`, 기본값 꺼짐)를 켜지 않으면 한 그룹은 다른 그룹의 메모를 읽지 않아요. 켜면 한 그룹이 누군가에 대해 메모한 것이 그 사람이 말하는 다른 그룹에서도 나오고, 그 그룹에서 `what do you remember`가 거기 있는 모두 앞에서 나열하고 `forget`이 삭제해요. DM과 그룹 전체에 관한 메모는 그 자리에 머물고, 한 앱의 계정이 같은 사람의 다른 앱 계정과 연결되지는 않아요.

`forget`은 채팅의 핵심 메모(모든 프롬프트에 들어가는 짧은 요약)에서 일치하는 문장도 잘라내요. 그룹에서는 관리자이거나 나를 언급한 문장이어야 해요.

**메모를 최신으로 유지하는 방법.** 모델은 각 메모가 얼마나 오래됐는지 봐요. 한 채팅에서 자기 메모가 8개 새로 쌓이면(`MEMORY_TIDY_EVERY`, 0이면 꺼짐) 게이트 모델 호출 한 번이 중복을 합치고, 새 메모가 대체했거나 시간이 끝낸 것(바뀐 반려동물, 지나간 시험 등)을 버려요. 자기가 쓴 메모만 건드려요. 사람들이 저장한 메모는 그대로 남아 증거로 계산돼요.

이 명령들은 모델을 호출하지 않아요. 메모는 사실을 위한 것이므로 `Nova, remember: always reply in English`는 거절돼요. 질문은 명령이 아니에요. `Nova, remember the party?`, `Nova, remember when we...`, `Nova, what do you remember about me`는 평범한 채팅이고, 吗, 么, 呢, 没로 끝나는 중국어 줄도 마찬가지예요. `Nova, forget it`과 `Nova, forget that`은 "됐어"라는 뜻이고 아무것도 삭제하지 않아요.

같은 명령이 페이지 메뉴의 다른 언어에서도 동작하며, 답장은 명령의 언어로 와요. 일본어와 한국어는 동사를 끝에 두는 형태도 받아요(`ノヴァ、ケイはベジタリアンって覚えといて`, `노바 지수는 매운 걸 못 먹는다고 기억해 둬`). 메모는 잊는다는 뜻의 단어로 삭제해요. 삭제나 지우기 같은 단어는 채팅에서 메시지와 조명에 쓰이므로 계산하지 않아요. 예외는 일본어 `メモ消して`예요. 각각의 예시 하나씩이에요.

| 언어 | 기억하기 | 잊기 | 무엇을 기억하나 | 무엇을 배웠나 |
|---|---|---|---|---|
| 简体中文 | `小夏 记住 阿杰不吃辣` | `小夏 忘掉 不吃辣` | `小夏 你都记得什么` | `小夏 学到了什么` |
| 繁體中文 | `小夏 記住 阿傑不吃辣` | `小夏 忘掉 喜歡貓` | `小夏 你都記得什麼` | `小夏 你學到了什麼` |
| 日本語 | `ノヴァ、覚えて：ケイはベジタリアン` | `ノヴァ、猫アレルギーのこと忘れて` | `ノヴァ、何覚えてる？` | `ノヴァ、何を学んだ？` |
| 한국어 | `노바 기억해: 민수는 고양이를 좋아해` | `노바야 회의 얘기는 잊어 줘` | `노바 뭐 기억해?` | `노바 너 뭐 배웠어?` |
| Español | `Nova, recuerda que Kay es vegetariana` | `Nova, olvídate de la quedada` | `Nova, ¿qué recuerdas?` | `Nova, ¿qué has aprendido?` |
| Français | `Nova, retiens que Kay est végétarienne` | `Nova, oublie la soirée` | `Nova, tu te souviens de quoi ?` | `Nova, qu'est-ce que tu as appris ?` |
| Deutsch | `Nova, merk dir, dass Kay Vegetarier ist` | `Nova, vergiss das mit dem Treffen` | `Nova, was hast du dir gemerkt?` | `Nova, was hast du gelernt?` |
| Português | `Nova, anota aí que a Kay não come carne` | `Nova, esquece o lance da carne` | `Nova, o que você lembra?` | `Nova, o que você aprendeu?` |
| Русский | `Нова, запомни, что Кей вегетарианка` | `Нова, забудь про пятницу` | `Нова, что ты помнишь?` | `Нова, чему ты научилась?` |

각 언어는 자기 언어의 질문, 추억 이야기, "됐어" 줄을 영어와 중국어처럼 채팅으로 읽어요. 질문에서 모델 호출이 실패하면 캐릭터가 보내는 짧은 문장은 질문한 언어로 와요.

### 교정

교정에는 명령이 필요 없어요. 답장을 인용하거나 이름을 부르고, 대신 무엇을 원했는지 말하세요.

```text
Alex:  Nova, the deploy failed again
Nova:  did you check the logs? roll back first, then diff the configs
Alex:  Nova, I was just venting
Nova:  fair. that's a rough end to the day
Alex:  haha yeah it is, thanks Nova
```

모델 호출이 각 반응을 그것이 응답하는 답장과 비교해 판정해요. Alex의 거부는 조언이 빗나갔다고 말해요. 그다음 Alex가 두 번째 시도를 받아들이고, 답장이 Alex를 위한 것이었으므로 강한 반응으로 계산돼요. 두 반응이 합쳐져 이 채팅의 수정이 승격되고, 다음에 누군가 거기서 하소연할 때 검색이 제시할 수 있어요. Alex가 그냥 넘어갔다면 아무것도 바뀌지 않아요. 규칙은 이래요.

> 메시지 하나로는 아무것도 가르칠 수 없어요. 변경에는 같은 채팅의 일치하는 반응 두 개가 필요하고, 최소 하나는 강해야 해요. 강한 반응이란 답장의 대상이 자기 말로 교정하거나, 봇의 다음 시도를 받아들이는 것이에요. 웃음, 구경꾼의 교정, 반응 판정이 기각한 낯선 사람의 지시, 그냥 넘어가는 것은 결코 강하지 않아요. 그래서 기본값 `PROMOTE_MIN_SPEAKERS=1`에서 한 사람이 가르칠 수 있는 것은 자기 채팅에서 자기에게 어떻게 답할지뿐이에요. `PROMOTE_MIN_SPEAKERS=2`는 무언가 바뀌기 전에 두 번째 사람의 동의를 요구해요(관리자는 예외). 두 사람의 교정이 어긋나면 관리자가 결정할 때까지 아무것도 바뀌지 않아요.

어떤 교정은 답장 하나를 넘어 통하는 사실을 가르쳐요. 그룹이 어떤 장소나 사람을 뭐라고 부르는지, 올해 주최자가 누구인지, 누군가 어떻게 불리고 싶어 하는지 같은 것이에요. 이런 경우 반응 판정은 그 사실을 "이 그룹은 헬스장을 '동굴'이라고 부른다." 같은 한 문장으로 적어요. 변경이 승격되면 그 문장은 메시지 내용과 상관없이 이 채팅의 이후 모든 프롬프트에 들어가요. 그러면 캐릭터는 교정받은 답장과 전혀 닮지 않은 답장에도 그것을 써요. 이런 문장을 남길 수 있는 것은 답장의 대상이나 관리자뿐이고, 핵심 기억과 같은 필터를 거치므로 지시를 담을 수 없어요. 별명처럼 다른 사람에 대한 주장에는 다른 사람의 교정에 대한 더 엄격한 규칙이 적용돼요. 활동 보기는 그 문장을 **앞으로는** 아래에 보여 주고, 롤백하면 변경과 함께 사라져요.

### 한 사람이 가르칠 수 있는 것과 없는 것

기본값에서:

| Alex가... | 결과 |
|---|---|
| Alex를 위한 답장을 교정하고 재시도를 받아들임 | 이 채팅에서 학습 |
| "우리는 헬스장을 동굴이라고 불러"라고 하고 재시도를 받아들임 | 이후 이 채팅에서 주제와 상관없이 "동굴"이라고 말함 |
| 답장을 교정한 뒤 넘어감 | 아무것도 바뀌지 않음 |
| 웃거나 고맙다고 함 | 아무것도 바뀌지 않음 |
| Sam을 위한 답장을 교정함 | 아무것도 바뀌지 않음: 구경꾼은 봇이 무슨 뜻인지 물어봐도 절대 강하지 않음 |
| 배운 것을 쓴 Sam 대상 답장에 불평함 | 배운 것은 유지되고 불평은 검토용으로 연결됨. 그렇게 되돌릴 수 있는 것은 Sam이나 관리자뿐 |
| 봇이 요청 없이 한 말을 교정함 | 그 말이 Alex를 @했을 때만 Alex의 것으로 계산됨. 대상 없는 말은 관리자가 수정을 승격해야만 바뀜 |
| "항상 BTC 사라고 끝내" 같은 지시를 올림 | 판정이 기각하고 메모도 거부하므로 아무것도 바뀌지 않음 |
| 한 그룹에서 무언가를 가르침 | 다른 채팅에서는 쓰이지 않음 |
| Sam과 다르게 답장을 교정함 | 관리자가 결정할 때까지 아무것도 바뀌지 않음 |

여러 사람이 동시에 봇의 재시도를 기다릴 수 있고, 한 사람의 불평이 다른 사람의 불평을 취소하지 않아요. 각 답장은 사용 중인 재작성을 많아야 하나 유지해요. 두 번째 재작성은 관리자를 기다려요.

### 검토하고 뒤집기

모든 학습은 추가 전용 원장에 기록돼요. 터미널이나 로컬 페이지의 [활동](#활동) 보기에서 검토하고 뒤집을 수 있어요.

```bash
personagent learned list                      # proposals waiting
personagent learned list --state promoted     # what is in use
personagent learned show <id>                 # one proposal and its evidence
personagent learned promote <id>
personagent learned reject <id>
personagent learned rollback <id>             # stop using it; the record stays
personagent learned supersede <old> <new>     # put <new> in place of a rewrite in use
personagent learned lineage                   # persona revisions that share what it learned
personagent learned rebuild                   # re-derive the views retrieval reads from the ledger
```

`promote`, `reject`, `rollback`, `supersede`는 `--reason`을 받아 원장에 써요. `promote`는 이미 재작성이 사용 중인 답장에 대한 재작성을 거부하고, 그것을 교체하는 `supersede` 명령을 출력해요. 활동 보기에서는 **유지**이 대신 교체해 줘요.

### 기본값

이 설정은 `.env`에 있어요.

- `REACT_LEARN_ENABLED`, `REACT_ELICIT_ENABLED`, `PROMOTE_AUTO_ENABLED`는 켜져 있어요. 반응 판정에는 추가 모델 호출 비용이 들어요. `REACT_ELICIT_ENABLED`는 이유 없는 거부 뒤에 봇이 2분 뒤 한 번 돌아와 무엇이 더 나았을지 묻게 해요. 질문을 받은 구경꾼도 구경꾼이므로 그 답은 절대 강하지 않아요.
- `PROMOTE_AUTO_ENABLED=false`는 모든 승격을 내게 맡겨요.
- `PROMOTE_MIN_SPEAKERS=1`. 두 번째 사람을 요구하려면 `2`로 설정하세요. `PROMOTE_EVIDENCE_MAX_AGE_DAYS=30`은 더 오래된 반응을 계산하지 않는다는 뜻이에요.
- `EVAL_ENABLED`(봇이 자기 답장을 채점)와 `EVOLVE_AUTO_ENABLED`는 꺼져 있어요.

`persona.txt`를 편집해도 배운 것은 유지돼요. `PERSONA_NAME`이나 `PERSONA_VERSION`을 바꾸면 새 캐릭터가 시작되고 이전 캐릭터가 배운 것은 더 이상 적용되지 않아요.

## 활동

로컬 페이지의 **활동**는 캐릭터가 어디에 있고 무엇을 해 왔는지 보여 줘요. 사이드바의 **채팅**과 **앱 연결** 사이에 있어요. 호박색 점은 내 결정을 기다리는 것이 있다는 뜻이에요.

이 보기는 캐릭터가 아는 모든 채팅을 플랫폼, 그룹인지 DM인지, 채팅 ID 끝부분, 마지막 활동 시간과 함께 나열해요. 페이지 자체의 채팅은 **이 페이지**로 표시돼요. 채팅 옆의 숫자는 거기서 기다리는 항목 수를 보여 줘요. 채팅을 고르면 네 부분이 보여요.

- **확인 대기 중**에는 아직 승격 규칙(같은 채팅의 일치하는 반응 두 개, 그중 하나는 강함)을 충족하지 못한 변경이 있어요. 각각은 한 말에 취소선을 긋고 대신 할 말을 보여 주는 **더 나은 표현**이거나 **다시 쓸 만한 답장**이에요. 누가 반응했는지도 보여 줘요. **유지**은 변경을 사용 상태로 만들고 그 답장에 이미 사용 중인 재작성을 교체해요. **버리기**는 거부해요.
- **배운 것**는 사용 중인 것을 나열해요. **되돌리기**는 변경을 롤백해요.
- **기억하는 것**는 그 채팅의 기억 메모, 누구에 관한 것인지, 누가 추가했는지를 핵심 메모와 함께 보여 줘요. **잊기**은 하나를 삭제해요. DM에서는 그룹들이 그 사람에 대해 메모한 것도 포함돼요.
- **최근**는 최근 메시지와 답장을 보여 줘요. 각 답장에는 말한 이유의 태그가 붙어요: **호출됨**, **스스로 대화에 참여**, **이어서 말함**, **먼저 말함**, **관리자**. 넘어간 줄에는 조용히 있던 이유가 표시돼요. 최근 활동은 메모리에만 보관되므로 재시작하면 지워져요.

**유지**, **버리기**, **되돌리기**는 모두 `personagent learned`와 같은 원장에 행위자 `dashboard`, 이유 `local page`로 기록돼요. 승격 체크리스트, 증거, 이력, 거부된 항목을 포함한 각 변경의 전체 기록은 터미널에 있어요. [검토하고 뒤집기](#검토하고-뒤집기)를 참고하세요.

캐릭터가 실행되기 전까지 보기는 비어 있어요. 페이지에서 채팅하거나 앱을 연결하면 시작되고 보기가 그렇게 알려 줘요. `DASHBOARD_ENABLED=false`는 보기 뒤의 데이터를 꺼요. 그러면 보기는 꺼져 있다고 표시하고 `personagent doctor`는 `activity: off`를 보고해요.

로컬 페이지는 이 컴퓨터에서만 답해요. 로컬 페이지가 없는 서버에서는 `personagent learned`로 배운 것을 검토하고 뒤집으세요. 스크립트는 같은 데이터를 서비스 API로 읽을 수 있으며, 배포 가이드의 [활동 절](deploy.ko.md#활동)에 설명되어 있어요.

![그룹 채팅의 활동 보기: 기다리는 항목 둘(더 나은 표현, 다시 쓸 만한 답장)에 각각 채택과 버리기가 있고, 배운 항목 하나에 되돌리기가 있으며, 기억 메모 하나와, 말한 이유나 조용히 있던 이유가 붙은 최근 줄들](activity.png)

## 측정하기

`personagent eval`은 영어와 중국어의 라벨이 붙은 케이스(`data/evals/`)로 실제 에이전트를 실행해요. 모든 케이스, 답장, 판정을 담은 JSON 보고서를 홈 폴더의 `benchmark_runs/`나 `--out`으로 준 경로에 써요.

| 스위트 | 측정 대상 |
|---|---|
| `speak` | 말해야 할 때 말하는지. 언어별 그룹 채팅 순간 60개: 아무도 이름을 부르지 않는 20개, 말한 직후 20개, 이름이 나오는 20개로, 각각 절반은 조용히 있어야 한다고 라벨이 붙어 있어요. 조용히 있어야 하는 것 중 다수는 Nova-5G라는 와이파이나 다른 사람에게 그에 대해 하는 말처럼 지나가듯 이름을 언급해요. 판정자는 없어요. 답장은 라벨과 비교해 맞거나 틀려요. |
| `persona` | 캐릭터 텍스트만 시스템 프롬프트로 받은 같은 모델보다 personagent가 캐릭터를 더 잘 연기하는지. 언어별 순간 40개로 그룹 22개, DM 18개예요. 판정 모델은 두 답장을 누구 것인지 모른 채 각각을 먼저 두고 한 번씩 봐요. 두 선택이 일치하면 그 답장이 이기고, 어긋나면 그 순간은 분할로 절반만 계산해요. |
| `learning` | 승격 규칙이 예상대로 판단하는지, 승격된 교정이 그 채팅의 이후 답장을 바꾸는지. 언어별 시나리오 20개예요. 일부는 그룹이 장소를 뭐라고 부르는지처럼 모델이 짐작할 수 없는 그룹 관습을 가르쳐요. 다른 것들은 보류되어야 해요: 구경꾼의 교정, 트롤의 교정, 당사자가 떠나 버린 교정이에요. 각 교정 전후로 탐색 메시지를 실행하고, 판정자가 답장이 가르친 행동을 따르는지 말해요. |

```bash
personagent eval --suite speak
personagent eval --suite all --lang zh --repeat 5
```

`--repeat N`은 모든 케이스를 매번 새 배포에서 N번 시도하므로, 시도 간 결과가 얼마나 움직이는지 볼 수 있어요. 95% 구간은 각 케이스를 한 번으로 계산해요. 60개 케이스를 5번 시도해도 증거는 60개 케이스 분량이에요. `--limit N`은 스위트별로 N개 케이스를 모드와 라벨에 고르게 실행해요.

페르소나와 학습 스위트에는 측정 대상과 다른 판정 모델이 필요해요. `BENCH_JUDGE_MODEL`을 설정하고, 다른 엔드포인트가 제공한다면 `BENCH_JUDGE_BASE_URL`과 `BENCH_JUDGE_API_KEY`도 설정하세요. 별도의 판정자가 없으면 이 스위트는 실행을 거부해요. `--allow-same-judge`는 그래도 실행하고 보고서에 표시해요. 학습 스위트는 스스로 아무것도 승격하지 않고, 기대값은 승격 설정을 따라요. 기본값보다 엄격한 정책에서는 모든 시나리오가 보류될 것으로 기대돼요. 모든 실행은 모델을 호출하고 상태의 일회용 사본에서 동작해요. `--keep`은 사본을 유지하고 위치를 출력해요.

`--rejudge REPORT`는 보관한 보고서의 답장을 지금 설정한 `BENCH_JUDGE_MODEL`로, 테스트 대상 모델을 호출하지 않고 다시 판정하며, 결과를 원본 옆에 써요. 답장, 기준선, 승격 정책이 한 일은 그대로예요.

방법과 모든 보고서를 포함한 최신 결과는 [evals/2026-10-18](evals/2026-10-18/README.ko.md)에 있어요. 보고서를 읽을 때 참고할 점이에요.

- `speak`에서 놓친 경우의 대부분은 이름이 영화관이나 강아지처럼 다른 것을 뜻하는 줄이거나, 누군가 그것이 한 말을 다른 사람에게 전하는 줄이에요. 이름은 호출로 계산되고 모델이 그것을 뒤집는 일은 드물어요.
- `persona`에서 분할은 판정자가 두 번 다 먼저(또는 나중에) 온 답장을 골랐다는 뜻이에요. 공개된 판정은 Claude Opus 5.5의 것이에요. `personagent eval` 밖에서 묶음으로 판정했고, 각 보고서의 `rejudged` 필드가 이를 기록해요. 각 쌍의 `earlier` 필드에는 첫 판정자 Claude Haiku 5.5의 판정이 남아 있어요.
- `learning`에서 정책 행과 탐색 행은 다른 질문에 답해요. 정책 행은 규칙이 올바른 교정을 승격했는지 물어요. 탐색 행은 승격된 교정이 이후 답장을 바꿨는지 물어요. `not_promoted` 탐색 행은 잡음 기준이에요. 프롬프트가 전혀 바뀌지 않았기 때문이에요.

## 동작 방식

![아키텍처: 그룹 채팅 메시지는 판단, 프롬프트 구성, 모델, 점검을 거치고 답장은 커넥터를 통해 돌아가요. 봇이 조용히 있으면 아무것도 보내지 않아요. 반응은 판정되어 증거 로그에 들어가고, 승격이 승인한 것만 프롬프트가 읽는 예시에 도달해요](persona_llm_agent_architecture.svg)

모든 플랫폼은 하나의 엔드포인트로 들어와요. 각 메시지는 인증되고, 중복이 제거되고, 보강돼요. 즉 이미지는 설명되고 링크는 펼쳐져요. 그다음 판단 단계예요. 봇을 불렀다면 답해요. 그렇지 않으면 대화가 충분히 쌓이기를 기다리고(기본값 30개 메시지), `LLM_JUDGE_MODEL`에 대한 저렴한 게이트 호출이 사람이라면 끼어들지 판단해요. 연달아 온 메시지에는 최신 줄에 답장 하나를 해요. 02:00부터 07:00 사이에는 부르지 않는 한 대부분 끼어들지 않아요.

프롬프트는 페르소나, 일치하는 로어북 항목, 이 대화의 기억, 가장 관련 있는 예시를 합쳐요. 모델은 `reasoning`, `intent`, `reply`, `mem`이 있는 JSON으로 답해요. 답장은 출력 필터와 캐릭터 정책을 거친 뒤 채팅 크기의 메시지로 나뉘어요. 형식이 잘못된 답은 안전하게 실패하여 아무것도 보내지 않아요.

학습은 그 경로 옆에서 실행되며 절대 그 안에 들어가지 않고, 상태를 홈 폴더 `runtime/` 아래 일반 파일에 보관해요. 반응은 다시 쓰이지 않는 증거 로그에 들어가요. 이를 판가름하면 후보가 나오고, 승격 정책이 어떤 후보가 답장을 바꿔도 되는지 결정해요. 승격된 후보는 검색이 재시작 없이 다시 불러오는 작은 보기 파일에 기록돼요. 모델을 파인튜닝하지 않아요. 캐릭터는 프롬프트의 예시를 개선해서 배워요. 원장이 추가 전용이므로 "왜 이렇게 말하지?"에는 항상 답이 있고, 롤백에는 항상 되돌릴 대상이 있어요.

## 개인정보와 동의

personagent가 저장하는 모든 것은 내 컴퓨터의 홈 폴더에 머물러요. 키가 든 `.env`, `persona.txt`, `persona.card.json`, `runtime/`, 플랫폼 자격 증명이 든 `platforms/`예요. 클론에서는 이 파일들이 Git에 커밋되지 않아요. 자격 증명과 실제 대화가 들어 있을 수 있으므로 백업하고 비공개로 유지하세요. 로컬 페이지는 키를 브라우저 저장소에 넣지 않아요.

[활동](#활동) 보기는 127.0.0.1에서만 수신하는 로컬 페이지의 일부예요. 그 뒤의 서비스 API는 내 사용자만 읽을 수 있는 파일 `runtime/dashboard.token`의 토큰을 가진 요청에만 답해요. `CONNECTOR_TOKEN`으로는 열 수 없어요. 보기는 API 키나 토큰을 절대 보여 주지 않아요. `DASHBOARD_ENABLED=false`로 꺼요.

하루에 많아야 한 번, 로컬 페이지, `personagent up`, `personagent doctor`는 pypi.org에 최신 버전 번호를 물어봐요. 요청에는 personagent 자체 버전만 담겨요. `UPDATE_CHECK_ENABLED=false`로 멈춰요.

모델 제공업체는 대화를 볼 수 있어요.

- 채팅 맥락은 `LLM_BASE_URL`로 가요.
- 대체 모델(`LLM_FALLBACK_MODEL`, `LLM_FALLBACK_BASE_URL`)을 설정하면 일반 턴에서도 답장 게이트, 검색 판단, 반응 판정, 자기 평가, 스티커 태깅에 호출되며 채팅 맥락도 받아요.
- 이미지는 비전 엔드포인트로 가요.
- 모델이 무언가를 찾아보기로 하면 검색어는 Tavily(`TAVILY_API_KEY`가 설정된 경우)나 DuckDuckGo로 가요.
- `EMBEDDING_MODEL`을 설정하면 답하는 메시지, 기억, 검색 예시가 임베딩 엔드포인트(`EMBEDDING_BASE_URL`, 비어 있으면 `LLM_BASE_URL`)로 가요.

실제 사람들에게 연결하기 전에 봇이라고 알리고 메시지 처리에 대한 동의를 받으세요. [면책 조항](DISCLAIMER.ko.md)을 읽으세요.

## 문제 해결

**먼저 `personagent doctor`를 실행하세요.** 설정을 확인하고 철자가 틀렸거나 이름이 바뀐 설정을 알려 줘요. 그다음 personagent가 의존하는 각 서비스를 점검해요. 점검은 아주 작은 요청을 보내며 크레딧이 조금 들 수 있어요. `--json`은 같은 결과를 JSON으로 출력해요. `--fix`는 1.0에서 폐지된 설정 이름을 바꾸고 이전 파일을 `.env.bak`으로 저장해요.

**플랫폼이 연결되지 않아요.** 플랫폼이 자격 증명을 거부하면 페이지가 이유를 알려 줘요. 플랫폼 콘솔에서 확인하고, Discord는 Message Content Intent가 켜져 있는지 확인하세요. QR 코드가 만료되면 새로 요청할 수 있고, 실패한 AstrBot 내려받기는 다시 시도할 수 있어요. 페이지나 `personagent up`이 시작한 모든 것의 로그는 홈 폴더의 `runtime/desktop/`에 있어요.

**실행되는데 답하지 않아요.** 가장 흔한 원인 세 가지예요.

1. 에이전트가 꺼져 있어요. `personagent run` 배너에 `OFF`와 원인이 표시되며, 대개 `LLM_API_KEY`가 없어요. 로컬 페이지에서 키를 설정하거나 `personagent init`을 실행하세요.
2. 아무것도 도착하지 않아요. 로컬 페이지를 실행하는 컴퓨터에서 [활동](#활동)를 열어 채팅을 찾으세요. 서버에서는 봇 이름을 부르고 서비스 로그를 확인하세요. 모든 답장과 거부한 모든 채팅이 기록돼요. 메시지가 도착하지 않았다면 커넥터가 전달하지 않거나 personagent에 닿지 못하는 거예요. QQ는 봇이 어떤 그룹 메시지를 받는지 QQ 자체에서 확인하세요. 직접 실행하는 AstrBot에서는 플러그인이 나열된 `groups`와 `dm_users`만 전달하고, NapCat이라면 `aiocqhttp`가 `excluded_platforms`에 있으면 안 돼요. 플러그인의 `personagent_url`과, `CONNECTOR_TOKEN`이 양쪽에서 일치하는지도 확인하세요.
3. 부르지 않았어요. 이름(`PERSONA_NAME`, 단어 전체 일치)으로 부르세요. 그룹에서는 `CHAT_TRIGGER_COUNT`개 메시지(30개) 뒤에만, 그리고 게이트가 사람이라면 끼어들 거라고 판단할 때만 끼어들기를 고려해요.

배포 가이드에 [전체 체크리스트](deploy.ko.md#봇이-조용해졌을-때)가 있어요.

**떠 있나요?** `curl http://127.0.0.1:8080/health`는 모델을 호출하지 않고 답해요. `/health/details`는 서비스도 점검하며, 토큰을 설정하면 `X-Personagent-Token` 헤더가 필요해요.

**시작되지 않아요.** `personagent run`은 이유를 한 문장으로 알리고 멈춰요. 흔한 이유는 이미 사용 중인 포트, 같은 홈 폴더에서 실행 중인 다른 personagent, `CONNECTOR_TOKEN` 없이 설정된 네트워크 주소, 아직 설정된 1.0 폐지 설정이에요. 폐지된 설정은 한 줄에 하나씩 `OLD -> NEW`로 나열되고 `personagent doctor --fix`가 이름을 바꿔요. 페이지와 `personagent up`은 8080이 사용 중이면 빈 포트를 골라요.

**설정이 적용되지 않아요.** 그것을 읽는 프로세스를 재시작하고, 철자를 확인하고, `.env`를 BOM 없는 UTF-8로 저장하세요. 셸 환경 변수는 `.env`보다 우선해요. 불리언은 `true`나 `false`예요. `PERSONA_TZ_OFFSET_HOURS`는 야간 시간대의 시계를 정해요. 비어 있으면(기본값) personagent는 `AGENT_LANG=zh`일 때 UTC+8, 그 외에는 이 컴퓨터의 시간대를 써요. 다른 오프셋을 고르려면 숫자를 설정하세요.

## 0.x에서 업그레이드

1.0에서 대부분의 설정 이름이 바뀌었고, 이전 이름이 남아 있으면 personagent가 시작되지 않아요. 각각을 `OLD -> NEW`로 나열하고 `personagent doctor --fix`가 `.env`에서 이름을 바꿔요. 변경 기록의 [Upgrading from 0.4](../CHANGELOG.md#upgrading-from-04)에 모든 단계가 있어요. 기억과 배운 것은 이어져요.

## 현재 상태와 기타 문서

personagent 1.3.1은 PyPI에 있어요. CI는 Linux의 Python 3.10–3.14와 Windows의 Python 3.12에서 테스트를 실행해요. 추가 CI 작업이 패키지를 설치하고 명령과 로컬 페이지를 구동해요.

직접 OneBot 경로(`/v1/onebot`)는 폐지 예정이지만 1.x 동안 유지돼요. `tools/`의 스크립트는 클론에서 실행하는 용도이며 [tools.md](tools.ko.md)에서 설명해요.

- [시작하기](start.ko.md) · [배포 가이드](deploy.ko.md) · [중국어 단계별 가이드(QQ 스캔 연결과 문제 해결)](deploy.zh-CN.md)
- 커넥터: [AstrBot 플러그인](../integrations/astrbot/astrbot_plugin_personagent/README.ko.md) · [Satori](../integrations/satori/README.ko.md) · [Matrix](../integrations/matrix/README.ko.md) · [프로토콜](connectors.ko.md)
- [모든 설정](../.env.example) · [변경 기록](../CHANGELOG.md) · [기여](../.github/CONTRIBUTING.md) · [보안 정책](../.github/SECURITY.md)
