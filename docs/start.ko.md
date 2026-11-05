# personagent 시작하기

[English](start.md) · [简体中文](start.zh-CN.md) · [繁體中文](start.zh-TW.md) · [日本語](start.ja.md) · 한국어 · [Español](start.es.md) · [Français](start.fr.md) · [Deutsch](start.de.md) · [Português (Brasil)](start.pt-BR.md) · [Русский](start.ru.md) · [전체 가이드](guide.ko.md)

## 열기

PyPI에서 personagent를 설치하고 엽니다.

```sh
python -m pip install personagent
personagent
```

[uv](https://docs.astral.sh/uv/)가 있으면 `uvx personagent`로 따로 설치하지 않고 실행할 수 있어요.

코딩 에이전트에게 설정을 맡길 수도 있어요. [setup-for-agents.md](setup-for-agents.md)를 읽고 personagent를 설정해 달라고 요청하세요.

Windows에서는 소스 ZIP을 내려받아 압축을 풀고 `start.bat`을 더블 클릭해도 돼요. 폴더 안에 전용 Python 환경을 만들고 같은 페이지를 엽니다.

클론에서 실행하려면 전용 venv를 만드세요. `python -m venv .venv`를 실행한 다음 `.venv/bin/python -m pip install -e .`와 `.venv/bin/python -m persona_agent`를 실행합니다. Windows의 인터프리터는 `.venv\Scripts\python.exe`이고, `start.bat`을 더블 클릭해도 돼요.

## 키를 넣고 채팅하기

모델 서비스를 고르고 API 키를 붙여 넣은 뒤 **확인하고 채팅 시작**을 클릭하세요. 처음에는 OpenRouter의 무료 모델과 따뜻한 경청자 캐릭터가 선택되어 있어요. 키는 무료이고 한도는 하루 50회 요청이에요. **고급 설정**에는 모델 이름과 API 주소가, **이름이나 성격 고르기**에는 캐릭터의 이름과 성격이 있어요.

키는 내 컴퓨터에만 있어요. 확인하려면 **보기**를 클릭하세요. 채팅 메시지는 선택한 모델 서비스로 전송되고, 해당 서비스의 일반 요금이 적용돼요.

캐릭터는 페이지 안에서 답해요. 설정이 저장되므로 다음 실행부터는 바로 채팅으로 들어가요.

설정이 끝나면 **캐릭터 및 설정**에 **페르소나** 칸이 생기고, 캐릭터의 바탕이 되는 글이 들어 있어요. 캐릭터가 어떤 사람이고 어떻게 말하는지 고쳐 쓴 뒤 **페르소나 저장**을 클릭하세요. 변경은 바로 적용되고, 캐릭터가 배운 내용은 유지돼요.

그 아래 **추가 기능**에서 웹 검색, 이미지 이해, 먼저 말 걸기를 켤 수 있어요. 검색은 기본적으로 DuckDuckGo를 쓰고, Tavily 키가 있으면 더 안정적이에요. 앱을 연결하기 전까지 **채팅** 화면에는 짧은 시작 안내 표시줄이 나타나요.

## 다른 앱으로 데려가기

1. **앱 연결**을 클릭하고 앱을 고르세요. 연결하면 캐릭터가 그 앱의 그룹 채팅과 DM에 답해요.
   - **스캔해서 연결**: QQ와 개인 WeChat. **QR 코드 받기**를 클릭하고 휴대폰에서 확인하세요.
     - QQ: 모바일 QQ로 스캔하세요. QQ가 봇을 만들거나 이미 있는 봇을 고르게 해 주고, personagent가 그 키를 가져와요. [QQ 봇 페이지](https://q.qq.com/qqbot/openclaw/login.html)에서 직접 봇을 만들었다면 **대신 값 붙여넣기**를 클릭하고 AppID와 AppSecret을 입력하세요.
     - WeChat: WeChat으로 스캔하세요. WeChat이 이런 봇에는 그룹 메시지를 넘기지 않기 때문에 봇은 일대일 채팅만 해요.
   - **값 한두 개 붙여넣기**: Telegram(@BotFather의 토큰), Discord(봇 토큰, Message Content Intent를 켜 두세요), KOOK, Feishu, DingTalk, Slack, WeCom AI 봇, Mattermost, Misskey. 앱 콘솔에서 어떤 값을 복사할지는 페이지가 알려 줘요. 나머지는 기본값을 써요.
   - **고급**: WeCom 앱, WeChat 공식 계정, QQ 웹훅에는 콜백 포트로 전달하는 공개 주소가 필요해요. OneBot v11(NapCat)과 Satori에는 이 컴퓨터에서 실행되는 다른 소프트웨어가 필요해요.
2. personagent는 QQ, WeChat, Telegram, Discord에 직접 연결해요. 다른 앱은 서드파티 브리지인 AstrBot을 거쳐요. 그중 하나를 처음 연결할 때 personagent가 AstrBot과 별도의 Python 3.12 런타임을 내려받으니, 끝날 때까지 페이지를 열어 두세요. 그 뒤 AstrBot은 백그라운드에서 실행되고, 로그인할 대시보드는 없어요.
3. personagent는 저장하기 전에 앱에 자격 증명을 확인해요. 앱이 거부하면 페이지에 알려 주고 아무것도 저장하지 않아요.
4. 연결된 앱은 **앱 연결** 맨 위에 표시되고, 거기서 다시 설정하거나 연결을 끊을 수 있어요.

QQ 봇을 찾으려면 모바일 QQ에서 연락처 → 봇으로 가세요. 일대일로 채팅하거나 내가 소유한 그룹에 추가하면 돼요. 이 방법은 QQ 공식 봇 플랫폼을 쓰므로 개인 QQ 계정도 추가 소프트웨어도 필요 없어요. 봇이 어디에 갈 수 있는지는 QQ가 정해요. 봇이 인증되기 전에는 관리자가 소유한 그룹에만 들어갈 수 있고, 따로 설정할 샌드박스는 없어요. 그룹 소유자가 그 그룹에 있는 봇의 프로필에서 모든 메시지 받기를 켜지 않으면, 그룹에서는 봇을 @한 메시지만 보여요. 인증을 비롯한 계정 쪽 내용은 [QQ 봇 가이드](https://bot.q.qq.com/wiki/bot_new_product-intro/)에 있어요.

QR 코드가 만료되면 새로 요청하세요. 다운로드가 실패하면 모델 설정을 반복하지 않고 다시 시도할 수 있어요. 앱을 연결해도 캐릭터에게 열리는 것은 그 앱의 그룹과 DM뿐이고, 다른 어댑터의 허용 목록은 그대로예요. LINE은 제공하지 않아요. AstrBot은 대시보드를 통해서만 LINE 콜백을 받는데, personagent는 대시보드를 실행하지 않기 때문이에요.

## 다음에 쓸 때

personagent를 다시 여세요. 설정은 그대로 있고, 연결된 앱은 자동으로 다시 시작돼요. 이미 실행 중이면 다시 열어도 실행 중인 페이지를 다시 사용해요. 쓰는 동안에는 실행 창을 열어 두세요. **종료**를 클릭하든 창을 닫든 시작한 프로세스는 함께 멈추고, 충돌로 남은 것은 다음 시작 때 정리돼요.

PyPI에 새 버전이 나오면 **채팅** 화면에 릴리스 노트 링크와, 이 사본을 설치한 방식에 맞는 업데이트 명령이 표시돼요. 소스 ZIP에서 푼 사본에는 대신 릴리스 페이지에서 새 소스를 내려받는 링크가 나와요. personagent는 pypi.org에 많아야 하루 한 번 물어보고, 요청에는 버전 번호만 담겨요. 확인을 끄려면 `.env`에 `UPDATE_CHECK_ENABLED=false`를 설정하세요.

명령줄이 더 좋다면 `personagent start --terminal`, `personagent init --terminal`, `personagent up`, 또는 `chat`, `demo`(키 불필요), `run`, `connect` 명령을 쓰세요. 기존 `.env`, 수정한 페르소나, 학습한 기억은 유지돼요. 다른 플랫폼은 [전체 가이드](guide.ko.md)에서 다뤄요.
