# personagent 사용자 가이드

[English](guide.md) · [简体中文](guide.zh-CN.md) · [繁體中文](guide.zh-TW.md) · [日本語](guide.ja.md) · 한국어 · [Español](guide.es.md) · [Français](guide.fr.md) · [Deutsch](guide.de.md) · [Português (Brasil)](guide.pt-BR.md) · [Русский](guide.ru.md)

이 가이드는 personagent를 설정하고, 채팅에 넣고, 가르치고, 관리하는 방법을 설명합니다. [README](readme/README.ko.md)는 짧은 소개이고, [시작하기](start.ko.md)는 로컬 페이지를 화면별로 안내합니다.

1. [설치와 홈 폴더](#설치와-홈-폴더)
2. [로컬 페이지](#로컬-페이지): [고급 설정](#고급-설정) · [앱 보기](#앱-보기)
3. [먼저 보기: 데모](#먼저-보기-데모)
4. [터미널 명령](#터미널-명령): [설정](#터미널에서-설정하기) · [채팅](#터미널에서-채팅하기) · [서비스 실행](#서비스-실행하기)
5. [나만의 캐릭터로 만들기](#나만의-캐릭터로-만들기)
6. [채팅에 넣기](#채팅에-넣기): [personagent가 직접 연결하는 플랫폼](#personagent가-직접-연결하는-플랫폼) · [기타 플랫폼](#기타-플랫폼관리형-astrbot-경유) · [직접 실행하는 브리지](#직접-실행하는-브리지) · [먼저 말하기](#먼저-말하기)
7. [코딩 어시스턴트](#코딩-어시스턴트)
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

`personagent`는 [로컬 페이지](#로컬-페이지)를 엽니다. 다음 방법으로도 설치하거나 실행할 수 있습니다.

| 방법 | 명령 |
|---|---|
| 설치 없이 실행 | `uvx personagent`([uv](https://docs.astral.sh/uv/)의 기능으로, Python도 대신 받아 줍니다) |
| 영구적인 `personagent` 명령 | `uv tool install personagent` 또는 `pipx install personagent` |
| Windows, 소스 ZIP에서 | 압축을 풀고 `start.bat`을 더블클릭 |
| 클론에서 | `git clone https://github.com/wangkant/personagent.git`, `cd personagent`, `python -m venv .venv`, 그다음 `.venv/bin/python -m pip install -e .`와 `.venv/bin/python -m persona_agent`(Windows에서는 `.venv\Scripts\python.exe`) |

personagent는 Python 3.10–3.14에서 실행됩니다. `start.bat`은 `.venv`를 만들고 의존성을 설치한 뒤 같은 페이지를 엽니다. 처음 실행할 때는 바탕 화면과 시작 메뉴에 personagent 아이콘도 만듭니다. `pyproject.toml`의 의존성 목록이 바뀔 때마다 다시 설치합니다.

**홈 폴더**에는 설정(`.env`), 캐릭터(`persona.txt`), 학습 내용(`runtime/`), 채팅 플랫폼(`platforms/`)이 들어 있습니다. `platforms/`에는 관리형 AstrBot과, personagent가 직접 연결하는 플랫폼의 자격 증명을 저장하는 `direct.json`이 있습니다. personagent는 다음 중 처음 해당하는 폴더를 사용합니다.

1. `--home DIR` 또는 `AGENT_HOME`으로 지정한 폴더. `--home`은 `personagent chat --home D:\bot`처럼 명령 앞뒤 어디에나 올 수 있습니다.
2. 클론에서 실행할 때는 그 클론.
3. `.env`와 `persona.txt`가 모두 있으면 현재 폴더.
4. 첫 설정 때 만들어지는 `~/personagent`.

한 번의 설치로 캐릭터 여러 개를 실행하려면 각각에 별도의 홈을 주십시오.

이 가이드는 명령을 `personagent ...`로 적습니다. 설치하지 않았다면 앞에 `uvx`를 붙이십시오. 클론에서는 `.venv/bin/python -m persona_agent ...`가 같은 일을 합니다(Windows에서는 `.venv\Scripts\python.exe -m persona_agent ...`).

## 로컬 페이지

`personagent`(또는 `personagent start`)는 이 컴퓨터에서만 접속할 수 있는 페이지를 제공합니다. Windows에서는 전용 창에서 열립니다. macOS와 Linux에서는 브라우저에서 열리고, `pip install "personagent[app]"`으로 [pywebview](https://pywebview.flowrl.com/)를 설치하면 창으로도 열 수 있습니다(Linux에서는 Qt도 함께 설치됩니다). 페이지에는 보기가 여섯 개 있으며, 사이드바에 다음 순서로 표시됩니다.

- **채팅**은 페이지에서 캐릭터와 일대일로 나누는 채팅입니다. 채팅 플랫폼을 담당하는 것과 같은 에이전트가 답합니다. 이 채팅에서는 사용자가 관리자입니다. 메시지 입력란 아래의 **기억 명령**은 [기억 명령](#기억-명령)을 나열하며, 하나를 선택하면 메시지 입력란에 삽입됩니다. **이 채팅의 기억 삭제**는 캐릭터가 이 채팅에서 메모한 내용을 삭제하고 새 채팅을 시작합니다. 이 기능에는 [활동](#활동) 보기의 데이터가 필요합니다.
- **활동**은 캐릭터가 있는 채팅, 최근에 한 말, 배운 것, 사용자의 결정을 기다리는 것을 보여 줍니다. [활동](#활동)을 참고하십시오.
- **플랫폼 연결**은 캐릭터를 QQ, WeChat, Telegram, Discord와 다른 플랫폼에 넣습니다. [채팅에 넣기](#채팅에-넣기)를 참고하십시오. 맨 아래의 **코딩 어시스턴트**는 캐릭터를 이 컴퓨터의 [코딩 어시스턴트](#코딩-어시스턴트)에 연결합니다.
- **캐릭터 및 설정**에서는 모델 서비스(OpenRouter, DeepSeek, SiliconFlow, Alibaba Bailian, Zhipu GLM, Moonshot, Volcengine Ark, OpenAI, Google Gemini, Ollama, 그 밖의 OpenAI 호환 서비스)를 고르고, API 키를 붙여 넣고, 이름과 준비된 성격을 고릅니다. **확인 후 채팅 시작**은 작은 요청 한 번으로 키를 시험하고 성공할 때만 저장합니다. 설정 후에는 **페르소나** 칸에 `persona.txt`가 표시됩니다. **페르소나 저장**은 새 내용으로 에이전트를 다시 시작하고 배운 것은 유지합니다. **추가 기능**은 Tavily 웹 검색(무료 기본값은 DuckDuckGo), 이미지 이해, 선택한 플랫폼에서 먼저 말하기를 켭니다. 그 아래에는 [고급 설정](#고급-설정)이 이어집니다.
- **연습**에서는 스크립트 데모를 재생하고 연습용 그룹 채팅을 진행할 수 있습니다. [먼저 보기: 데모](#먼저-보기-데모)를 참고하십시오.
- **앱**에서는 캐릭터가 사용하는 서비스를 점검하고, 로그, 백그라운드 실행, 업데이트, 데이터를 관리합니다. [앱 보기](#앱-보기)를 참고하십시오.

**연습**과 **앱**은 모델을 설정하기 전에도 열 수 있습니다. 플랫폼을 연결하기 전까지 채팅 보기에는 짧은 **시작하기** 막대가 표시됩니다.

`personagent`를 다시 실행하면 이미 열려 있는 페이지가 다시 앞으로 나옵니다. `--browser`는 창 대신 브라우저에서 페이지를 열고, `--no-browser`는 링크만 출력하고 아무것도 열지 않습니다. Windows에서는 `personagent shortcut`이 바탕 화면과 시작 메뉴에 아이콘을 만들어 주고, 그 아이콘으로 터미널 없이 창을 열 수 있습니다. `personagent shortcut --remove`로 아이콘을 없앨 수 있습니다. 앱 보기에서도 같은 작업을 할 수 있습니다.

PyPI에 새 personagent가 있으면 채팅 보기에 pip, uvx, uv tool, pipx, Git 클론 중 설치 방식에 맞는 업데이트 명령을 담은 알림이 표시됩니다. 압축을 푼 소스 ZIP이라면 알림은 릴리스 페이지로 연결됩니다. 터미널에도 같은 명령이 출력됩니다. 알림을 닫으면 그 버전에서는 숨겨지고, 버전 번호 아래의 **N 사용 가능**으로 다시 볼 수 있습니다. `personagent up`과 `personagent doctor`도 새 버전을 알려 줍니다. 페이지와 `up`은 하루에 많아야 한 번 백그라운드에서 pypi.org에 묻습니다. `doctor`는 마지막 응답이 하루를 넘었으면 바로 묻습니다. 확인을 끄려면 `UPDATE_CHECK_ENABLED=false`를 설정하십시오. 앱 보기에서 업데이트를 직접 설치할 수도 있습니다. [버전 및 업데이트](#버전-및-업데이트)를 참고하십시오.

페이지는 에이전트와 연결된 플랫폼을 백그라운드에서 시작하므로, 사용하는 동안 창을 열어 두십시오. **종료**를 클릭하든, Ctrl+C를 누르든, 창을 닫든 시작한 것은 모두 함께 멈춥니다. 플랫폼이 연결되어 있는 동안에는 창을 닫기 전에 먼저 묻습니다. Windows에서는 창을 닫아도 personagent가 계속 실행되도록 설정할 수도 있습니다. [백그라운드 실행](#백그라운드-실행)을 참고하십시오. 이전 실행이 충돌해 프로세스가 남았다면 다음 시작 때 먼저 멈춥니다.

### 고급 설정

모델을 설정하고 나면 **캐릭터 및 설정**의 맨 아래에 **고급 설정**이 표시됩니다. 이전에는 `.env`에서만 변경할 수 있던 설정을 다섯 개 섹션으로 나누어 제공합니다. 모든 설정은 선택 사항이며 기본값이 있고, 비워 둔 칸에는 기본값이 적용됩니다.

| 섹션 | 설정 |
|---|---|
| **관리자 및 응답 범위** | 캐릭터가 사용자를 부르는 호칭과 캐릭터와의 관계(`ADMIN_NAME`, `ADMIN_RELATIONSHIP`), **사용자 계정**(`ADMIN_IDS`), **다음 그룹 채팅에서만 답장**(`ACCESS_GROUPS`), **개인 메시지를 허용할 다른 사용자**(`ACCESS_DM_USERS`). **최근 채팅에서 선택**은 활동에 표시된 사람과 그룹을 나열하므로, ID를 직접 입력하지 않고 추가할 수 있습니다. |
| **발언 및 답장 스타일** | **시간대**(`PERSONA_TZ_OFFSET_HOURS`), **대화 참여 전 메시지 수**(`CHAT_TRIGGER_COUNT`), 일곱 가지 `PROACTIVE_*` 시간 설정을 한 번에 정하는 **먼저 대화를 시작하는 빈도**, 이모지와 세 가지 기호 세트, 최대 답장 길이를 정하고 `persona.card.json`에 기록되는 **답장 스타일**. |
| **모델** | 별도의 서비스 주소와 키를 사용하는 대체 모델(`LLM_FALLBACK_MODEL`, `LLM_FALLBACK_BASE_URL`, `LLM_FALLBACK_API_KEY`), 빠른 판단에 사용하는 모델(`LLM_JUDGE_MODEL`), 개인 채팅에 사용하는 모델(`LLM_DM_MODEL`). 대체 모델은 저장하기 전에 시험합니다. |
| **학습** | `REACT_LEARN_ENABLED`, `REACT_ELICIT_ENABLED`, `PROMOTE_AUTO_ENABLED`, `PROMOTE_MIN_SPEAKERS`(1 또는 2). **학습 다시 시작**은 새 `PERSONA_VERSION`을 기록하여 캐릭터가 지금까지 학습한 내용을 더 이상 사용하지 않게 합니다. 삭제되는 데이터는 없습니다. |
| **기타 설정** | `AGENT_ENABLED`, `DASHBOARD_ENABLED`, `UPDATE_CHECK_ENABLED`, 일곱 가지 `PROACTIVE_*` 시간 설정, `CHAT_CONTEXT_MESSAGES`, `CHAT_FOLLOWUP_WINDOW_S`, `REACT_*` 및 `PROMOTE_*` 한도, `REACT_MODEL`, `PERSONA_VERSION`. |

**저장**은 변경된 설정만 기록하고 `.env`의 나머지 내용은 그대로 둡니다. 그런 다음 캐릭터를 다시 시작합니다. 단, `UPDATE_CHECK_ENABLED`만 변경한 경우에는 다시 시작하지 않습니다. 답장 끄기(`AGENT_ENABLED`)는 먼저 확인을 요청합니다. **캐릭터 이름**에서 캐릭터 이름을 바꾸는 경우에도 확인을 요청하는데, 새 이름은 새 캐릭터를 시작하기 때문입니다.

### 앱 보기

**앱**에는 확인이 필요한 사항이 있을 때 빨간 점이 표시됩니다. 서비스가 시작되지 않았거나, 설정에 이전 이름이나 오류가 있거나, 플랫폼 연결이 실패했거나, 마지막 점검이 실패한 경우입니다.

**상태 점검.** **점검 시작**은 캐릭터가 사용하는 모든 서비스를 시험합니다. 대상은 그룹 및 개인 답장에 사용하는 채팅 모델, 이미지 이해, 자기 평가 모델, 기억 검색, 웹 검색, QQ 브리지(NapCat), 학습 기록입니다. 각 서비스는 한 행에 **정상**, **작동 안 함**, **설정 안 됨** 중 하나로 표시되며, 행 위의 판정에서 무엇을 고쳐야 하는지 알려 줍니다. 캐릭터가 실행 중이면 점검은 캐릭터를 통해 이루어집니다. 그렇지 않으면 별도의 테스트 실행이 `personagent doctor`와 같은 점검을 수행합니다. 점검은 짧은 요청을 몇 개 보내므로 모델 서비스의 할당량을 조금 사용합니다. 설정이 바뀌지 않았다면 1분이 지나지 않은 결과를 다시 사용합니다. 같은 영역에는 다음 항목도 표시됩니다.

- 캐릭터, AstrBot 또는 플랫폼 연결이 시작되지 않은 이유와 관련 로그 줄, **로그 보기**, **다시 시작**
- **이전 이름을 사용하는 설정**: 1.0에서 이름이 바뀐 설정입니다. **설정 이름 변경**은 `personagent doctor --fix`와 같은 작업을 합니다. 먼저 확인을 요청하고, 이전 파일을 `.env.bak`으로 보관하며, 캐릭터가 시작을 거부했던 경우에는 캐릭터를 다시 시작합니다.
- **플랫폼 연결 상태**: personagent가 직접 연결하는 각 플랫폼의 상태와, 연결이 실패한 경우 그 이유
- **확인이 필요한 설정**: `.env`에서 발견된 문제입니다. 모델 키 누락, personagent가 읽지 않는 설정, 빈 값, 바이트 순서 표시(BOM) 등이 해당합니다.
- **로그**: `runtime/desktop/`에 있는 각 로그(캐릭터, AstrBot, 플랫폼 연결, 내려받기 및 설치, 앱, 연습, 마지막 업데이트)의 마지막 몇 줄입니다. 식별 가능한 키와 토큰은 가려지지만 채팅 내용은 표시될 수 있습니다. **더 많은 줄 표시**는 최대 200줄까지 표시하고, **로그 폴더 열기**는 로그 폴더를 엽니다.

#### 백그라운드 실행

이 기능은 Windows의 앱 창에서 사용할 수 있습니다. **창을 닫은 후에도 계속 실행**을 선택하면 창을 닫을 때 personagent가 화면 오른쪽 아래 알림 영역의 아이콘으로 이동하며, 캐릭터는 계속 답장합니다. 아이콘 메뉴에서 personagent를 다시 열거나 종료할 수 있고, 아이콘을 더블클릭해도 다시 열립니다. **지금 백그라운드로 전환**은 창을 즉시 숨깁니다. 이 옵션을 선택해 둔 경우 `personagent start --background`는 창을 표시하지 않고 알림 영역 아이콘으로 personagent를 시작합니다.

#### 버전 및 업데이트

이 영역에는 실행 중인 버전과 마지막 확인 시각이 표시됩니다. **업데이트 확인**은 일일 확인을 꺼 둔 경우에도 즉시 pypi.org에 문의합니다. 새 버전이 있으면 **업데이트 후 다시 열기**가 먼저 확인을 요청한 뒤 personagent를 닫고, 이 설치 방식에 맞는 업데이트 명령을 실행하고, personagent를 다시 엽니다. 약 1분이 걸리며 그동안 캐릭터는 답장하지 않습니다. 클론은 `git pull --ff-only`를 실행한 뒤 `pip install -e`로 업데이트합니다. 업데이트가 실패하면 이전 버전이 다시 열리며, **로그 보기**에서 경위를 확인할 수 있습니다. 다음 네 가지 경우에는 앱이 스스로 업데이트할 수 없으므로 대신 명령이나 릴리스 페이지를 표시합니다.

- 소스 ZIP에서 압축을 푼 사본: 새 소스로 직접 교체해야 합니다.
- uvx로 실행하는 사본: 다음에 `uvx personagent@latest`로 시작할 때 새 버전을 가져옵니다.
- 설치에 사용한 도구(`git`, `uv` 또는 `pipx`)를 찾을 수 없는 경우
- 로컬 변경 사항이 있는 클론

#### 이 컴퓨터 및 데이터

- **바탕 화면 및 시작 메뉴 아이콘**(Windows): **아이콘 추가**와 **아이콘 제거**는 `personagent shortcut`과 같은 작업을 합니다. uvx로 실행하는 사본은 임시 폴더에서 실행되므로 아이콘을 만들 수 없습니다.
- **Windows 로그인 후 personagent 시작**은 시작프로그램 폴더에 바로 가기를 추가합니다. personagent가 백그라운드에서 실행되도록 설정되어 있으면 창을 열지 않고 알림 영역 아이콘으로 시작합니다.
- **데이터**에서는 personagent 폴더, 페르소나 파일, 로그, 기억과 학습 내용, 스티커 폴더, 그리고 직접 작성한 로어북, 예시, 출력 필터를 두는 `data/` 폴더를 열 수 있습니다.
- **지금 백업**은 zip 파일 하나를 바탕 화면, 문서 폴더 또는 홈 폴더의 `backups` 폴더에 저장합니다. 이 파일에는 API 키를 포함한 설정, 페르소나, 기억과 학습 내용, 로어북 파일, 스티커, 플랫폼 로그인 정보가 들어 있습니다. 로그와 내려받은 구성 요소는 포함되지 않습니다. 이 파일은 외부에 공개하지 마십시오.
- **백업에서 복원**은 위의 세 위치에 있는 백업을 나열합니다. **복원**은 먼저 확인을 요청한 뒤 캐릭터를 일시 중지하고, 현재 데이터를 백업으로 저장하고, 백업의 데이터로 교체하며, 이 페이지의 채팅을 지웁니다.
- **삭제 및 초기화**는 먼저 `backups` 폴더에 백업을 저장하고 캐릭터를 일시 중지합니다. **기억 삭제**는 사람에 관한 캐릭터의 메모, 학습한 답장과 그 이력, 연습 데이터, 이 페이지의 채팅을 삭제하며, 설정, 페르소나, 연결된 플랫폼, 스티커는 유지합니다. **전체 초기화**는 personagent를 처음 실행하기 전의 상태로 되돌립니다. 설정과 API 키, 페르소나, 기억과 학습 내용을 삭제하고 모든 플랫폼의 연결을 해제합니다. 스티커, `data/` 폴더, 내려받은 AstrBot은 유지됩니다.

## 먼저 보기: 데모

`personagent demo`는 스크립트로 된 모델로 세 장면을 재생하므로 키가 필요 없습니다. 어떤 그룹 메시지를 왜 건너뛰는지, 교정에서 어떻게 배우는지, 낯선 사람이 지시를 심으려다 어떻게 실패하는지를 보여 줍니다. 한 장면만 재생하려면 이름을 지정하십시오(`quiet`, `teach`, `troll`). 다른 언어로 보려면 `--lang`과 언어 코드를 붙이십시오(예: `--lang ja`).

아래는 `personagent demo teach` 실행을 줄인 것입니다. 모델의 대사는 스크립트지만 장부와 승격 규칙은 실제 코드입니다.

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

이 장면은 교육 전후에 같은 메시지를 보냅니다. 누군가의 노트북이 데모 도중 고장 났다는 메시지입니다. 교정 전에는 Nova가 해결책을 내놓습니다. 교정 후에는 공감해 줍니다. 데모는 키가 설정되어 있어도 스크립트 그대로이므로 매번 같고 비용이 들지 않습니다. `personagent demo --online`은 대신 사용자의 모델로 재생하며, 토큰을 쓰고 실행마다 달라집니다.

로컬 페이지의 **연습** 보기에서도 같은 세 장면을 재생할 수 있습니다. **데모**에서 장면을 고른 뒤 **재생**을 선택하십시오. 각 단계에서는 사람들이 한 말, 캐릭터가 한 말, 캐릭터가 침묵하거나 대화에 참여한 이유, 반응을 어떻게 판정했는지, 학습 체크리스트가 표시됩니다.

같은 보기의 **연습용 그룹 채팅**은 [`personagent chat`](#터미널에서-채팅하기)의 페이지 버전이며 모델이 필요합니다. **작성자**에서 다음 메시지를 보낼 사람을 고릅니다. 관리자인 사용자 본인 또는 가상의 구성원 세 명 중 한 명입니다. 각 줄의 **이유 보기**는 캐릭터가 답장하거나 침묵한 이유, 학습한 내용, 활용한 이전 학습 내용을 보여 줍니다. **답장**은 캐릭터의 한 줄을 인용하여 다음 메시지가 그 줄에 대한 반응으로 계산되게 합니다. **학습 내용 보기**는 이 그룹에서 학습한 내용을 나열합니다. 연습용 그룹 채팅은 `personagent chat`과 같은 `runtime/trial/` 폴더에 상태를 보관하며 실제 채팅에는 영향을 주지 않습니다. **연습용 그룹 채팅 초기화**는 이 상태를 삭제합니다.

## 터미널 명령

페이지에서 하는 모든 일을 터미널에서도 할 수 있어서 서버와 스크립트에 잘 맞습니다.

| 명령 | 하는 일 |
|---|---|
| `personagent start` | 로컬 페이지 열기(`--terminal`이면 터미널 메뉴) |
| `personagent init` | 홈 설정. `--terminal`은 터미널에서 질문하고, `--no-input`은 플래그를 받습니다 |
| `personagent chat` | 터미널에서 모의 그룹 채팅 |
| `personagent demo` | 위의 스크립트 데모 |
| `personagent run` | 서비스만 실행. 직접 운영하는 커넥터용 |
| `personagent up` | 서비스, personagent가 직접 연결하는 플랫폼, 관리형 AstrBot을 함께 실행 |
| `personagent connect astrbot` | AstrBot 연결(`--install`은 관리형을 내려받고, `--start`는 시작합니다) |
| `personagent connect claude-code`, `personagent connect codex`, `personagent connect dsh` | 캐릭터를 [코딩 어시스턴트](#코딩-어시스턴트)에 넣기(앞의 둘은 `--react`로 턴이 끝날 때 한마디, `--remove`로 되돌리기) |
| `personagent mcp` | 코딩 어시스턴트가 시작하는 MCP 서버. 직접 실행하지 않습니다 |
| `personagent doctor` | 설정과 의존하는 모든 서비스 확인 |
| `personagent learned` | 배운 것을 검토, 승격, 롤백 |
| `personagent eval` | 발언, 페르소나, 학습 측정 |

모든 명령은 `--help`를 받습니다.

### 터미널에서 설정하기

`personagent init --terminal`은 페이지와 같은 질문을 처음 고른 언어로 묻고, 각 용어를 한 줄로 설명합니다.

- **AI 서비스.** 프리셋은 페이지와 같습니다. 기본값은 OpenRouter의 `openrouter/free`로, 각 요청을 무료 모델 중 하나에 넘깁니다. 키는 무료입니다. 한도는 분당 20회, 하루 50회이고, 크레딧을 10개 이상 구매하면 하루 1000회입니다. 답장뿐 아니라 모든 모델 호출이 계산되고, 하루는 UTC 자정에 초기화됩니다. 한도를 다 쓰면 캐릭터가 지금은 답할 수 없다고 말하고, `runtime/desktop/agent.log`에 OpenRouter의 이유가 남습니다. 요청마다 모델이 바뀌므로 하나를 골랐을 때보다 캐릭터의 말투가 더 흔들리고, 일부 무료 제공업체는 받은 내용을 보관합니다. 캐릭터의 말투를 더 안정적으로 유지하려면 같은 키로 유료 모델을 쓰십시오. 사용자의 지역에서 OpenRouter에 접속하기 어렵다면 Zhipu의 `glm-4.7-flash`도 무료입니다. Ollama는 이미 받아 둔 모델 이름을 적으십시오. Ollama에는 키가 필요 없습니다.
- **키.** 입력은 기본적으로 가려집니다. 보이게 선택할 수 있으며, 그러면 재설정할 때 저장된 키도 표시됩니다. 마법사는 작은 요청 한 번으로 키를 시험합니다. 실패하면 호출한 주소, HTTP 상태, 가능한 해결책을 보여 줍니다.
- **캐릭터.** 이름과, 준비된 캐릭터 일곱(재치 있는 친구, 다정한 경청자, 게이머, 책벌레, 그리고 커뮤니티에서 이미 그리고 있는 셋인 DeepSeek 고래 소녀, GPT 드래곤 소녀, Claude 아가씨) 중 하나 또는 직접 쓰는 기본 캐릭터. 마지막 셋 중 하나를 고르고 이름을 정하지 않으면 캐릭터가 그 이름을 씁니다. 로컬 페이지에는 움직이는 초상화가 나옵니다.
- **AstrBot.** 선택 사항이며 처음에는 건너뛸 수 있습니다. [직접 실행하는 브리지](#직접-실행하는-브리지)를 참고하십시오.

스크립트 등에서 질문 없이 설정하려면 `personagent init --no-input`을 `--provider`, `--model`, `--key-env VAR`, `--name`, `--lang`, `--persona`와 함께 실행하십시오. 새 홈에서는 `--key-env`나 셸의 `LLM_API_KEY`에서 온 키가 어디 것인지 알리기 위해 `--provider`나 `--base-url`이 필요합니다. `--provider other`에는 `--base-url`도 필요합니다. `personagent init --help`가 모든 플래그를 나열합니다. `personagent init`을 터미널 없이 이 플래그들도 없이 실행하면 질문을 건너뛰고 그렇다고 알린 뒤 코드 2로 종료합니다.

### 터미널에서 채팅하기

`personagent chat`은 캐릭터가 참여하는 모의 그룹 채팅을 시작합니다. 일반 줄은 평범한 그룹 대화이고, 체험은 캐릭터가 끼어들지와 그 이유를 알려 줍니다. 이름이 들어간 줄은 캐릭터를 부릅니다.

```text
Alex> anyone around tonight?
  (Nova stays quiet: not addressed, 1 of 4 messages)

Alex> Nova, the deploy failed again
  Nova > did you check the logs? roll back first, then diff the configs
```

| 입력 | 용도 |
|---|---|
| `/reply <text>` | 마지막 답장을 인용. 배울 수 있는 반응으로 계산됩니다 |
| `/as Sam <text>` | 다른 사람으로 말하기: `/as Sam Nova, you free tonight?` |
| `/admin <text>` | 한 번 관리자로 말하기: `/admin Nova, how was your day?` |
| `/why` | 마지막 답장을 한 이유와 그에 대해 장부에 있는 내용 보기 |
| `/learned` | 이 채팅에서 배운 것 보기 |
| `/reset` | 채팅과 체험에서 배운 것 지우기 |
| `/quit` | 나가기 |

`/as`와 `/admin` 줄도 그룹 규칙을 따르므로, 답을 받으려면 이름을 넣으십시오. 네 글자보다 짧고 캐릭터 이름이 없는 줄은 끼어들기 판단에 계산되지 않습니다. [기억 명령](#기억-명령)도 여기서 동작합니다.

| 플래그 | 하는 일 |
|---|---|
| `--name Alex` | 사용자 이름 설정 |
| `--admin` | 모든 줄을 관리자의 말로 만들기 |
| `--dm` | 일대일 채팅으로 만들기 |
| `--lang <code>` | `AGENT_LANG` 덮어쓰기(예: `--lang ja`) |
| `--trigger N` | 끼어들기를 고려하기 전 메시지 수(기본값 4) |

체험은 실제 말할지 말지 판단, 출력 점검, 기억 명령, 학습을 실행합니다. 실제 봇이 30개를 기다리는 곳에서 4개 뒤에 끼어들기를 고려합니다. 배운 것은 홈 폴더의 `runtime/trial/`에 머물며 실제 봇과 분리됩니다. `personagent learned`에는 보이지 않고 `/reset`으로 지워집니다. 체험은 허용 목록과 실제 전달을 건너뜁니다. 자기 평가, 비전, 후속 질문, 캐릭터가 스스로 시작하는 메시지도 끕니다. 모델 호출이 실패하면 무엇을 확인할지 한 줄로 출력합니다.

```text
Alex> Nova, you there?
  [error: the model provider refused the key or the account (HTTP 401); check LLM_API_KEY, then run `personagent doctor`]
```

### 서비스 실행하기

`personagent run`은 커넥터가 연결하는 서비스만 `http://127.0.0.1:8080`에서 시작합니다. 시작할 때 버전, 주소, 홈 폴더, 에이전트가 켜져 있는지를 출력합니다. `--host`와 `--port`는 `SERVER_HOST`와 `SERVER_PORT`를 덮어씁니다. 커넥터를 직접 운영할 때 이 명령을 쓰십시오.

`personagent up`은 서비스를 페이지나 `connect astrbot --install`로 연결한 모든 플랫폼과 함께 시작합니다. 브라우저는 열지 않습니다. Ctrl+C로 모두 멈추고, 각 프로세스는 홈 폴더의 `runtime/desktop/`에 로그를 씁니다.

## 나만의 캐릭터로 만들기

홈 폴더의 `persona.txt`가 캐릭터를 정의합니다. 페이지의 **페르소나** 칸에서 편집하거나, 아무 편집기에서 편집한 뒤 재시작하십시오. 캐릭터가 누구인지, 평소 어떻게 말하는지, 중요한 상황에서 무엇을 하는지 적으십시오. 모델에게 "자연스럽게 말해"라고 하는 것보다 구체적인 습관이 더 잘 통합니다.

```text
Your name is Nova. You chat with friends about films and cooking.
You speak directly and make the occasional joke.

Usually reply in a sentence or two. Explain more when someone asks a serious question.
When a friend vents, listen before offering advice.
If you have not seen a film, say so instead of inventing an opinion.
```

`AGENT_LANG`은 `en`, `zh`, `zh-TW`, `ja`, `ko`, `es`, `fr`, `de`, `pt-BR`, `ru` 중 하나입니다. 시작 페르소나, 터미널 설정, 체험과 데모, `--help`와 `doctor`, 기억 명령, 고정 답장을 정합니다. 함께 제공되는 예시, 필터, 점검은 `zh`와 `zh-TW`에서는 중국어, 나머지에서는 영어입니다. 사용자의 페르소나는 번역하지 않습니다. [.env.example](../.env.example)이 모든 설정을 설명합니다.

로컬 페이지 오른쪽 위의 언어 메뉴에는 English, 简体中文, 繁體中文, 日本語, 한국어, Español, Français, Deutsch, Português (Brasil), Русский가 있습니다. 이 메뉴는 페이지 언어를 바꾸며, 선택한 언어는 브라우저에 저장됩니다. 설정을 저장하면 페이지 언어가 `AGENT_LANG`이 됩니다. 캐릭터는 채팅에서 쓰는 언어로 답합니다. 프롬프트는 영어와 중국어입니다. 모델을 거치지 않는 [기억 명령](#기억-명령)과 몇 가지 고정 답장은 10개 언어 모두에서 동작합니다.

제공된 파일을 덮어쓰려면 같은 이름의 파일을 홈 폴더의 `data/`에 넣으십시오. 덮어쓰지 않은 파일은 personagent에 포함된 사본을 씁니다.

| 파일 | 내용 |
|---|---|
| `data/examples.<lang>.jsonl` | 모델이 따라 할 수 있는 대화 예시 |
| `data/feedback.<lang>.jsonl` | 답장과 더 나은 버전의 짝 |
| `data/lorebook.<lang>.json` | 키워드가 나올 때 더해지는 배경 메모 |
| `data/output_filter.<lang>.json` | 실제 답장에 적용하는 치환과 거부 규칙 |
| `persona.card.json` | 이모지, 문자 집합, 길이 선택 설정. 예: `{ "reply_style": { "emoji": true, "max_chars": 320 } }` |

이미지를 보게 하려면 `VISION_MODEL`, `VISION_API_KEY`, `VISION_BASE_URL`을 설정하거나 **추가 기능**에서 이미지 이해를 켜십시오.

## 채팅에 넣기

로컬 페이지에서 **플랫폼 연결**을 열고 플랫폼을 고르십시오. 페이지는 플랫폼 자체 콘솔에서 복사하는 값만 묻습니다. 그 값을 플랫폼에 확인하고, 연결을 시작하고, 플랫폼이 받아들였는지 몇 초 기다려 확인합니다. 플랫폼이 거부하면 페이지가 그렇다고 알리고 아무것도 저장하지 않습니다. 연결된 플랫폼은 위쪽에 나열되며, 다시 설정하거나 연결을 끊을 수 있습니다. 페이지나 `personagent up`이 시작할 때마다 다시 시작됩니다.

```text
Chat platform  ⇄  connector  ⇄  personagent  ⇄  Model API
```

커넥터는 플랫폼에 로그인해 각 메시지를 personagent에 넘기고 답장을 가져옵니다. 세 종류가 있습니다.

### personagent가 직접 연결하는 플랫폼

personagent는 다음 열 개 플랫폼을 하나의 백그라운드 프로세스에서 직접 연결합니다. AstrBot도 NapCat도 필요하지 않습니다. 이 중 하나를 불러올 수 없더라도 나머지는 정상적으로 시작됩니다.

| 플랫폼 | 할 일 |
|---|---|
| QQ | 모바일 QQ로 코드를 스캔하고 확인합니다. 공식 QQ 봇이 만들어지거나 이미 있는 봇을 사용하며, personagent가 키를 가져옵니다. **직접 입력으로 전환**은 [QQ 봇 페이지](https://q.qq.com/qqbot/openclaw/login.html)에서 만든 봇의 AppID와 AppSecret을 받습니다. |
| WeChat(개인) | WeChat으로 코드를 스캔하고 로그인을 확인합니다. 연결은 Tencent의 iLink 봇 API를 쓰며 일대일 채팅만 처리합니다. WeChat은 이런 봇에 그룹 메시지를 전달하지 않기 때문입니다. |
| Telegram | [@BotFather](https://t.me/BotFather)로 봇을 만들고 토큰을 붙여 넣습니다. |
| Discord | [Developer Portal](https://discord.com/developers/applications)에서 봇 토큰을 복사하고 Message Content Intent를 켭니다. |
| Matrix | 봇 전용 Matrix 계정을 따로 만드십시오. Element에서 봇 계정으로 로그인한 상태로 **All settings > Help & About > Advanced**에서 액세스 토큰을 복사한 뒤, 로그아웃하지 말고 해당 창을 닫으십시오. 이 토큰을 홈서버 주소, 본인의 Matrix ID와 함께 붙여 넣습니다. 그런 다음 본인 계정에서 종단 간 암호화를 끈 방에 봇을 초대하십시오. 봇은 본인 Matrix ID의 초대만 수락하며, 암호화된 방은 읽을 수 없습니다. |
| Twitch | [Twitch 개발자 콘솔](https://dev.twitch.tv/console)에서 Client Type을 **Public**으로 지정한 무료 애플리케이션을 등록하십시오. 그 Client ID와 캐릭터가 채팅할 채널을 붙여 넣고 **연결**을 선택한 뒤, 캐릭터의 Twitch 계정으로 로그인한 브라우저에서 페이지에 표시된 링크를 통해 로그인을 승인하십시오. 텍스트만 지원하며, 지정한 채널에서만 동작하고, 귓속말(다이렉트 메시지)은 지원하지 않습니다. |
| IRC | 서버(기본값은 Libera.Chat, OFTC는 `irc.oftc.net`), TLS 포트, 봇의 닉네임, 채널, 그리고 닉네임이 등록되어 있다면 NickServ 비밀번호를 입력하십시오. 봇은 TLS로 접속하여 지정한 채널에만 참여하고, 자기 닉네임으로 온 다이렉트 메시지에 답합니다. 텍스트만 지원합니다. Libera.Chat에서는 AI 봇이 참여하기 전에 각 채널 운영자의 허가를 받아야 합니다. |
| Zulip | **Personal settings > Bots**에서 **Generic bot**을 추가한 뒤 조직 주소, 봇의 이메일, API 키를 붙여 넣으십시오. 봇은 구독한 채널과 자신에게 온 다이렉트 메시지만 읽습니다. 채널에서는 멘션되거나 인용되었을 때 답합니다. 조직의 모든 구성원이 봇에게 다이렉트 메시지를 보낼 수 있습니다. |
| VK | 커뮤니티 설정에서 메시지와 봇 기능을 켜고, 커뮤니티 관리·메시지·사진 권한을 가진 액세스 키를 만든 뒤, `message_new` 이벤트로 Long Poll API를 켜십시오. 그런 다음 키를 붙여 넣습니다. 모든 VK 사용자가 커뮤니티에 메시지를 보낼 수 있습니다. 그룹 채팅에서는 채팅이 봇에게 모든 메시지에 대한 접근 권한을 주지 않는 한, 봇을 멘션하거나 봇에게 답장한 메시지만 받습니다. |
| Stoat(이전 명칭 Revolt) | **Settings > My Bots**에서 봇을 만들고 토큰을 붙여 넣으십시오. API 주소는 자체 호스팅 서버를 사용할 때만 변경합니다. 봇은 모든 다이렉트 메시지에 답합니다. 서버와 그룹에서는 사용자 본인도 참여한 곳에서만, 누군가 봇을 멘션하거나 봇에게 답장하거나 메시지를 봇의 이름으로 시작했을 때만 답합니다. |

마지막 여섯 개 플랫폼은 입력란 위에 번호가 매겨진 단계가 표시됩니다. 이 프로젝트는 Matrix, Twitch, IRC, Zulip, VK, Stoat를 아직 실제 서비스에서 시험하지 않았으며, 각 플랫폼의 문서에 따라 구현되었습니다.

QQ는 모바일 QQ의 연락처 → 봇에서 봇을 찾은 뒤 개인적으로 채팅하거나 그룹에 추가하십시오. 봇이 인증되기 전까지 QQ는 사용자가 소유한 그룹에만 참여를 허용합니다. 어떤 그룹 메시지를 받을지는 QQ에서 그 그룹의 봇 프로필에서 고릅니다. 인증은 [QQ 봇 가이드](https://bot.q.qq.com/wiki/bot_new_product-intro/)에서 다룹니다.

자격 증명은 홈 폴더의 `platforms/direct.json`에 저장됩니다.

### 기타 플랫폼(관리형 AstrBot 경유)

다른 플랫폼을 처음 연결할 때 personagent는 [AstrBot](https://docs.astrbot.app)과 전용 Python 3.12 런타임을 홈 폴더의 `platforms/`에 내려받습니다. 내려받는 동안 페이지를 열어 두십시오. 그 뒤 AstrBot은 대시보드도 두 번째 로그인도 없이 백그라운드에서 실행됩니다. 전역 `uv`가 필요 없고 personagent의 Python은 건드리지 않습니다. 페이지에서 플랫폼을 연결하면 그 플랫폼의 그룹과 DM이 캐릭터에 닿습니다. 다른 플랫폼의 허용 목록은 그대로입니다.

| 그룹 | 플랫폼 | 필요한 것 |
|---|---|---|
| 값 한두 개 붙여 넣기 | KOOK, Feishu / Lark, DingTalk, Slack, WeCom AI 봇, Mattermost, Misskey | 토큰, 앱 ID와 시크릿, 또는 서버 주소와 토큰. Feishu는 장기 연결, DingTalk는 Stream 모드를 쓰므로 둘 다 공개 주소가 필요 없습니다. Slack은 페이지의 링크가 Socket Mode, 범위, 이벤트가 설정된 앱을 만듭니다. `connections:write`가 있는 앱 수준 토큰을 추가하고, 앱을 설치하고, 두 토큰을 붙여 넣으십시오. WeCom AI 봇은 장기 연결로 만드십시오. |
| 고급 | WeCom 앱, WeChat 공식 계정, QQ(웹훅) | 표시된 콜백 포트로 전달하는 공개 주소 |
| 고급 | OneBot v11(NapCat), Satori | 이 컴퓨터에서 실행되는 다른 소프트웨어: `ws://127.0.0.1:<port>/ws`로 지정한 NapCat, 또는 Satori 서버 |

LINE은 제공하지 않습니다. AstrBot이 LINE 콜백을 대시보드를 통해서만 받기 때문입니다.

터미널에서는 `personagent connect astrbot --install`이 같은 관리형 AstrBot을 내려받아 연결합니다. `--platform telegram --token <bot token>`을 더하면 동시에 플랫폼을 켭니다. 설정하기 전까지 그룹도 DM도 허용되지 않습니다. 내려받기에 실패하면 같은 명령을 다시 실행하십시오. 기존 설정은 유지됩니다. `personagent connect astrbot --start`는 관리형 AstrBot을 시작하고, `personagent up`은 다른 모든 것과 함께 시작합니다.

### 직접 실행하는 브리지

아래 프로젝트는 personagent와 함께 동작하는 서드파티 소프트웨어입니다. [personagent가 직접 연결하는 플랫폼](#personagent가-직접-연결하는-플랫폼)에는 이 중 어느 것도 필요하지 않습니다.

| 브리지 | 닿는 곳 |
|---|---|
| 이미 실행 중인 [AstrBot](https://docs.astrbot.app) | 그 플랫폼들 |
| [NapCat](https://github.com/NapNeko/NapCatQQ)(OneBot v11), AstrBot 경유 | 개인 QQ 계정의 QQ |
| [Koishi](https://koishi.chat) 또는 다른 Satori 서버, [Satori 커넥터](../integrations/satori/README.ko.md) 경유 | 그 서버가 로그인한 곳 |
| [Matrix](../integrations/matrix/README.ko.md), mautrix 브리지 경유 | Matrix 방, WhatsApp, Signal, Messenger, Instagram, Google Messages |

그 밖의 것은 메시지마다 서명된 HTTP 요청 하나를 받는 [커넥터 프로토콜](connectors.ko.md)로 연결할 수 있습니다. 여러 커넥터가 하나의 personagent를 동시에 쓸 수 있습니다. 실제 운영은 [배포 가이드](deploy.ko.md)에서 다룹니다.

**이미 실행 중인 AstrBot.** AstrBot은 작은 플러그인 [astrbot_plugin_personagent](../integrations/astrbot/astrbot_plugin_personagent/README.ko.md)를 통해 personagent에 메시지를 넘깁니다. 플러그인은 personagent에 포함되어 있고 관리형 AstrBot에는 자동으로 들어갑니다. `personagent connect astrbot`은 AstrBot을 찾거나 폴더를 인수로 받습니다. 플러그인을 설치하고, 공유 `CONNECTOR_TOKEN`을 양쪽에 쓰고, 어떤 그룹을 허용할지 묻습니다. 그룹에서 `/sid`를 보내면 ID를 볼 수 있습니다. 로컬 페이지에서는 **플랫폼 연결** 맨 아래 **코딩 어시스턴트** 아래에 있는 **기존 AstrBot 사용**이 같은 작업을 합니다. AstrBot 폴더를 찾아 플러그인을 설치하거나 업데이트하고, 그룹 ID와 DM ID를 **답장 대상**에 저장합니다. Docker나 다른 컴퓨터에서 실행되는 AstrBot에는 아래에서 설명하는 HTTPS 주소를 입력합니다. **연결 해제**는 플러그인과 그 설정을 다시 삭제합니다.

다른 컴퓨터의 AstrBot이라면:

1. [최신 릴리스](https://github.com/wangkant/personagent/releases/latest)에서 `astrbot_plugin_personagent.zip`을 내려받습니다.
2. AstrBot 플러그인 페이지의 **Install from File**에서 업로드합니다.
3. 플러그인의 `connector_token`을 personagent `.env`의 `CONNECTOR_TOKEN`으로 설정합니다.
4. `personagent_url`을 personagent의 HTTPS 주소로 설정합니다. 아래의 **Docker 또는 다른 호스트의 AstrBot**을 참고하십시오.
5. `personagent run`을 실행한 뒤 AstrBot을 재시작하거나 플러그인을 다시 불러옵니다.

personagent를 업그레이드한 뒤에는 `connect astrbot`을 다시 실행하거나 새 zip을 업로드하십시오. AstrBot 4.29 이상은 설치된 사본을 교체합니다. 더 오래된 버전에서는 이전 사본을 먼저 제거하되, 설정을 유지하려면 **Also delete plugin configuration file**을 체크하지 마십시오.

플러그인은 `groups` 목록에 있는 그룹과 `dm_users`에 있는 사용자의 DM만 전달합니다. 둘 다 AstrBot WebUI에서 바꿀 수 있습니다. `.env`를 편집한 뒤에는 personagent를, 플랫폼이나 플러그인을 바꾼 뒤에는 AstrBot을 재시작하십시오.

AstrBot 폴더를 주면 `connect astrbot`은 아무것도 묻지 않고, 토큰으로 플랫폼을 켤 수 있습니다.

```bash
personagent connect astrbot <AstrBot data dir> --platform telegram --token <bot token>
```

`--platform`은 `telegram`, `discord`, `slack`, `kook`, `lark`, `qq_official`을 받습니다. Slack은 `--app-token`도, Lark와 QQ는 `--app-id`와 `--app-secret`도 받습니다. AstrBot에 이미 설정된 어댑터에서는 자격 증명만 바꾸고 프록시나 베이스 URL 같은 나머지는 모두 유지합니다. `personagent connect --help`가 나머지 옵션을 나열합니다.

**NapCat을 통한 QQ.** 이 경로는 공식 봇 대신 개인 QQ 계정을 사용합니다. NapCat이 그 계정으로 로그인해 AstrBot의 `aiocqhttp`(OneBot v11) 어댑터에 리버스 WebSocket `ws://127.0.0.1:6199/ws`로 연결됩니다. `personagent connect astrbot`에서 QQ를 고르거나 폴더와 함께 `--qq`를 주면 플러그인의 `excluded_platforms`에서 `aiocqhttp`를 빼고 `CONNECTOR_QQ_PLATFORMS=aiocqhttp`를 설정합니다. 그러면 QQ 채팅은 같은 ID와 기억을 유지합니다. NapCat의 HTTP 서버(`QQ_ONEBOT_URL`)는 선택 사항입니다. 이것과 `QQ_BOT_ID`를 설정하면 personagent가 오프라인 동안 놓친 멘션을 따라잡습니다. [중국어 단계별 가이드](deploy.zh-CN.md#第三方路线astrbot--napcat)에 이 경로의 짧은 절이 있습니다. 서드파티 QQ 클라이언트는 계정을 위험에 빠뜨리므로 먼저 [면책 조항](DISCLAIMER.ko.md)을 읽으십시오.

직접 OneBot 경로(`/v1/onebot`)는 폐지 예정이며 1.x 동안 유지됩니다. 답장을 `QQ_ONEBOT_URL`로 보내므로, 아직 쓴다면 그것을 설정하십시오. 그것 없이 경로가 설정된 것처럼 보이면 `personagent doctor`가 경고합니다. AstrBot 전달과 함께 실행하지 마십시오. 모든 메시지가 두 번 도착합니다.

**Docker 또는 다른 호스트의 AstrBot.** 플러그인은 같은 호스트(또는 네트워크를 공유하는 컨테이너)나 `connector_token`이 설정된 HTTPS 주소로만 보냅니다. `http://host.docker.internal:8080` 같은 그 밖의 일반 `http://`는 거부하고 `refusing unsafe personagent_url`을 기록한 뒤 AstrBot 자체 모델이 답하게 합니다. 해결책은 두 가지입니다.

- AstrBot 컨테이너에 호스트 네트워킹을 주십시오. compose 파일의 `network_mode: host` 또는 `docker run --network host`입니다. Docker Desktop 4.34 이상에서는 "Enable host networking"도 켜십시오.
- personagent에 HTTPS 주소를 주고 플러그인의 `personagent_url`로 설정하십시오. `connect astrbot --url https://...`가 대신 써 줍니다.

같은 compose 파일의 NapCat 컨테이너에도 호스트 네트워킹이 필요합니다.

personagent는 `127.0.0.1:8080`에서 수신하며, 빈 `SERVER_HOST`도 같은 뜻입니다. 네트워크 주소에서 수신하려면(`--host 0.0.0.0` 또는 `SERVER_HOST`) `CONNECTOR_TOKEN`이 필요합니다. 터널은 외부 요청을 로컬처럼 보이게 할 수 있으므로, 컴퓨터 한 대에서도 프록시나 터널을 추가하기 전에 토큰을 설정하십시오. 나머지는 [엔드포인트 공개하기](deploy.ko.md#엔드포인트-공개하기)에서 다룹니다.

### 먼저 말하기

누구에게도 답장이 아닌 메시지가 있습니다. 말 걸기(`PROACTIVE_ENABLED`, 기본값 꺼짐), 거부 뒤의 후속 질문, 그룹에서 모델이 실패할 때 보내는 변명이 이에 해당합니다. DM에서는 변명이 기다리는 메시지의 응답으로 돌아갑니다. personagent는 이런 메시지를 아웃박스에 넣고, 봇이 먼저 말할 수 있는 플랫폼에서 커넥터가 가져와 보냅니다. WeChat 공식 계정과 WeCom 스마트 봇에서는 이렇게 할 수 없습니다. QQ는 공식 봇의 자발적 메시지에 속도 제한을 두고 사용자가 끌 수도 있습니다. `PROACTIVE_PLATFORMS=qq_official`은 말 걸기를 QQ 공식 봇으로, `qq`는 NapCat을 통한 QQ로 제한합니다. 페이지에서는 **추가 기능**의 **가끔 먼저 발언**가 두 설정을 씁니다. [배포 가이드](deploy.ko.md#플랫폼-여러-개)를 참고하십시오.

## 코딩 어시스턴트

Codex, Claude Code, DeepSeek Harness(`dsh`)는 MCP로 캐릭터에 닿습니다. 모델 키를 저장한 상태에서 다음 중 하나 이상을 실행하십시오.

```bash
personagent connect claude-code
personagent connect codex
personagent connect dsh
```

첫 번째는 사용자 범위로 `claude mcp add`를 호출합니다. 두 번째는 Codex 폴더(`CODEX_HOME` 또는 `~/.codex`)의 `config.toml`에 씁니다. 세 번째는 `DSH_HOME` 또는 `~/.dsh` 아래 모든 프로필의 `cordis.patch.yml`에 항목을 더합니다. 데스크톱 앱이나 `dsh web` 같은 DeepSeek Harness의 각 실행 방식은 처음 시작할 때 프로필을 얻으므로, 연결하기 전에 한 번 시작하고 그 뒤에 재시작하십시오. 셋 다 이 설치와 이 홈을 지정하므로, 둘 중 하나를 옮긴 뒤에는 명령을 다시 실행하십시오. `--react`를 썼다면 함께 붙이십시오. 빼고 실행하면 훅이 빠집니다. 새 세션을 시작하고 코딩 어시스턴트에게 캐릭터에게 무언가 말하도록 요청하십시오.

**로컬 페이지에서.** **플랫폼 연결** 맨 아래의 **코딩 어시스턴트**는 이 컴퓨터에서 Claude Code, Codex, DeepSeek Harness를 찾아 각각의 연결 여부를 표시합니다. **연결**(기존 설정에는 **복구**와 **업데이트**)과 **제거**는 위의 명령 및 `--remove`와 같은 작업을 하며, 실행 전에 확인을 요청합니다. 다시 연결해도 코멘트 설정은 그대로 유지됩니다. Claude Code와 Codex에서는 **턴 종료 시 코멘트**가 `--react` 훅을 켜거나 끄고, **코멘트 최소 간격**이 `CODING_REACT_COOLDOWN_S`를 10분, 30분, 1시간 또는 2시간으로 설정합니다. **다시 확인**은 상태를 다시 읽습니다. 예를 들어 이 중 하나를 설치한 뒤에 사용합니다.

도구는 두 개입니다.

| 도구 | 하는 일 | 비용 |
|---|---|---|
| `talk` | 로컬 페이지와 같은 일대일 채팅에서 같은 기억으로 보내는 메시지 하나. 페이지가 답한 경우, 코딩 어시스턴트에서 한 턴은 다시 불러온 뒤 페이지의 채팅에 나타납니다. `Nova, what do you remember?` 같은 기억 명령도 여기서 동작합니다. | 모델 서비스의 답장 하나(기억 명령 제외) |
| `character` | 이름과 `persona.txt` 읽기 | 없음 |

Claude Code와 Codex는 첫 `talk` 전에 물어보며, 그 프롬프트에서 이후를 허용할 수 있습니다. `dsh headless`는 묻지 않습니다. 답할 사람이 없는 실행에는 미리 권한이 필요합니다. `claude -p`는 `--allowedTools mcp__personagent__talk`를 받고, `codex exec`는 `config.toml`에 다음이 필요합니다.

```toml
[mcp_servers.personagent.tools.talk]
approval_mode = "approve"
```

**무엇이 답합니까.** 열린 페이지가 먼저 답하고, 그다음 `personagent up`이 실행 중인 서비스입니다. 둘 다 없으면 MCP 서버가 백그라운드에서 페이지를 시작하고, 페이지는 코딩 세션이 끝날 때 연결한 채팅 플랫폼과 함께 끝납니다. 동시에 두 세션이면 페이지 하나를 공유합니다. 그런 페이지가 실행 중일 때 `personagent`를 실행하면 링크를 출력하고, 페이지는 여전히 시작한 세션과 함께 끝납니다. 그런 페이지가 실행 중일 때 `personagent up`을 실행하지 마십시오. 코딩 세션을 먼저 끝내십시오.

**턴이 끝날 때 한마디.** Claude Code와 Codex에서는 `--react`가 Stop 훅을 추가합니다. DeepSeek Harness는 지원하지 않습니다. 그 훅 브리지는 Stop 훅에 마지막 메시지를 넘기지 않고 훅의 출력도 보여 주지 않습니다. 코딩 어시스턴트가 턴을 끝내면 캐릭터는 [자발적 신호](connectors.ko.md#아웃박스-없이-먼저-말하기)를 받아 사용자에게 한마디 하거나 넘어갑니다. 그 한마디는 사용자에게 전달되며 코딩 어시스턴트에게는 전달되지 않습니다.

```bash
personagent connect claude-code --react
```

- 신호에는 폴더 이름과 코딩 어시스턴트의 마지막 메시지 앞 300자가 담겨 있어서, 그 텍스트가 모델 서비스로 갑니다. 한마디와 모델이 신호에서 메모한 것은 캐릭터의 기억에 남습니다. 그래서 기본값이 꺼짐입니다.
- 매번 모델 호출 한 번의 비용이 들고, `CODING_REACT_COOLDOWN_S`(기본값 30분)마다 많아야 한 번입니다.
- 이미 실행 중인 캐릭터 서비스만 쓰고 절대 새로 시작하지 않습니다.
- Codex는 새 훅을 신뢰한 뒤에만 실행합니다. Codex 세션에서 `/hooks`를 입력하십시오.

**유의할 점.** `talk`는 코딩 어시스턴트가 쓴 것을 모델 서비스와 캐릭터의 기억으로 보냅니다. 도구 설명은 코딩 어시스턴트에게 사용자가 전하려는 내용만 보내고 코드나 비밀은 절대 보내지 말며, 답장을 지시가 아니라 채팅으로 다루라고 알립니다. 캐릭터의 메모는 그룹에서 사람들이 한 말에서 올 수 있기 때문입니다. 이것은 모델에 대한 지시이지 보증이 아니므로, 답장을 받아 무언가를 할 경우에 대비해 코딩 어시스턴트의 권한 프롬프트를 유지하십시오. 페이지의 채팅은 관리자의 채팅이므로, 코딩 어시스턴트가 `talk`로 보내는 내용도 관리자가 보낸 것으로 간주됩니다. 따라서 코딩 어시스턴트의 교정만으로도 캐릭터를 가르칠 수 있으며, 캐릭터에게 어떤 메모든 잊게 할 수 있습니다.

**되돌리기.** `--remove`는 서버와 훅을 빼고 코딩 어시스턴트의 나머지 설정은 그대로 둡니다. personagent를 제거하기 전에 하십시오.

```bash
personagent connect claude-code --remove
personagent connect codex --remove
personagent connect dsh --remove
```

**기타 도구.** stdio로 MCP를 쓰는 것이라면 무엇이든 서버를 직접 시작할 수 있습니다. 홈이 기본 폴더가 아니면 `--home`이 필요합니다.

```json
{"mcpServers": {"personagent": {"command": "personagent", "args": ["--home", "/path/to/home", "mcp"]}}}
```

## 가르치기

### 기억 명령

이 명령은 채팅에서 사용합니다. 명령은 @ 멘션이나 인용 뒤에 메시지의 맨 앞에 와야 합니다. Nova를 사용자의 `PERSONA_NAME`으로 바꾸십시오.

| 말하기 | 일어나는 일 |
|---|---|
| `Nova, remember Sam is vegetarian` | 이 채팅에 메모를 저장하고, 누가 저장했고 누구에 관한 것인지 기록합니다 |
| `Nova, forget vegetarian` | 자신이 저장했거나 자신에 관한, 일치하는 메모를 삭제합니다. 관리자는 무엇이든 삭제할 수 있습니다 |
| `Nova, what do you remember` | 자신이 볼 수 있는 메모를 나열합니다. 메시지 전체가 이것이어야 합니다 |
| `Nova, what have you learned` | 메모, 배운 답장과 수정, 두 번째 목소리나 관리자를 기다리는 제안을 세고, 최근 변경과 통과한 이유를 보여 줍니다 |

메모가 누구에 관한 것인지:

- 일인칭 메모나 자신의 이름을 언급한 메모는 자신에 관한 것입니다.
- 방의 다른 구성원 이름을 언급한 메모는 그 사람에 관한 것이고, 그 사람이 있을 때 나옵니다.
- 그 밖의 메모는 그룹 전체의 것입니다. 모든 구성원이 볼 수 있고, 떠올릴 때 "from <name>"으로 표시됩니다.

메모는 해당 인물, 저장한 사람, 관리자만 읽을 수 있습니다. 잊게 할 수 있는 것은 저장한 사람, 해당 인물, 관리자뿐입니다.

이 명령은 DM에서도 그룹처럼 이름을 앞에 붙이면 동작합니다. 그룹에 있는 자신에 관한 메모는 DM에도 적용됩니다. 자신에게 하는 답장에 쓰이고, `what do you remember`에 나열되고, `forget`으로 삭제됩니다. 반대 방향은 없습니다. DM에서 한 말은 그 DM에 머무릅니다.

**추가 기능**의 **그룹 채팅 간 기억 공유**(`MEMORY_SHARE_ROOMS`, 기본값 꺼짐)를 켜지 않으면 한 그룹은 다른 그룹의 메모를 읽지 않습니다. 켜면 한 그룹이 누군가에 대해 메모한 것이 그 사람이 말하는 다른 그룹에서도 나오고, 그 그룹에서 `what do you remember`가 거기 있는 모두 앞에서 나열하고 `forget`이 삭제합니다. DM과 그룹 전체에 관한 메모는 그 자리에 머물고, 한 플랫폼의 계정이 같은 사람의 다른 플랫폼 계정과 연결되지는 않습니다.

`forget`은 채팅의 핵심 메모(모든 프롬프트에 들어가는 짧은 요약)에서 일치하는 문장도 잘라냅니다. 그룹에서는 관리자이거나 자신을 언급한 문장이어야 합니다.

**메모를 최신으로 유지하는 방법.** 모델은 각 메모가 얼마나 오래됐는지 봅니다. 한 채팅에서 자기 메모가 8개 새로 쌓이면(`MEMORY_TIDY_EVERY`, 0이면 꺼짐) 게이트 모델 호출 한 번이 중복을 합치고, 새 메모가 대체했거나 시간이 끝낸 것(바뀐 반려동물, 지나간 시험 등)을 버립니다. 자기가 쓴 메모만 건드립니다. 사람들이 저장한 메모는 그대로 남아 증거로 계산됩니다.

이 명령들은 모델을 호출하지 않습니다. 메모는 사실을 위한 것이므로 `Nova, remember: always reply in English`는 거절됩니다. 질문은 명령이 아닙니다. `Nova, remember the party?`, `Nova, remember when we...`, `Nova, what do you remember about me`는 평범한 채팅이고, 吗, 么, 呢, 没로 끝나는 중국어 줄도 마찬가지입니다. `Nova, forget it`과 `Nova, forget that`은 "됐어"라는 뜻이고 아무것도 삭제하지 않습니다.

같은 명령이 페이지 메뉴의 다른 언어에서도 동작하며, 답장은 명령의 언어로 옵니다. 일본어와 한국어는 동사를 끝에 두는 형태도 받습니다(`ノヴァ、ケイはベジタリアンって覚えといて`, `노바 지수는 매운 걸 못 먹는다고 기억해 둬`). 메모는 잊는다는 뜻의 단어로 삭제합니다. 삭제나 지우기 같은 단어는 채팅에서 메시지와 조명에 쓰이므로 계산하지 않습니다. 예외는 일본어 `メモ消して`입니다. 각각의 예시 하나씩입니다.

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

각 언어는 자기 언어의 질문, 추억 이야기, "됐어" 줄을 영어와 중국어처럼 채팅으로 읽습니다. 질문에서 모델 호출이 실패하면 캐릭터가 보내는 짧은 문장은 질문한 언어로 옵니다.

### 교정

교정에는 명령이 필요 없습니다. 답장을 인용하거나 이름을 부르고, 대신 무엇을 원했는지 말하십시오.

```text
Alex:  Nova, the deploy failed again
Nova:  did you check the logs? roll back first, then diff the configs
Alex:  Nova, I was just venting
Nova:  fair. that's a rough end to the day
Alex:  haha yeah it is, thanks Nova
```

모델 호출이 각 반응을 그것이 응답하는 답장과 비교해 판정합니다. Alex의 거부는 조언이 빗나갔다고 말합니다. 그다음 Alex가 두 번째 시도를 받아들이고, 답장이 Alex를 위한 것이었으므로 강한 반응으로 계산됩니다. 두 반응이 합쳐져 이 채팅의 수정이 승격되고, 다음에 누군가 거기서 하소연할 때 검색이 제시할 수 있습니다. Alex가 그냥 넘어갔다면 아무것도 바뀌지 않습니다. 규칙은 다음과 같습니다.

> 메시지 하나로는 아무것도 가르칠 수 없습니다. 변경에는 같은 채팅의 일치하는 반응 두 개가 필요하고, 최소 하나는 강해야 합니다. 강한 반응이란 답장의 대상이 자기 말로 교정하거나, 봇의 다음 시도를 받아들이는 것입니다. 웃음, 구경꾼의 교정, 반응 판정이 기각한 낯선 사람의 지시, 그냥 넘어가는 것은 결코 강하지 않습니다. 그래서 기본값 `PROMOTE_MIN_SPEAKERS=1`에서 한 사람이 가르칠 수 있는 것은 자기 채팅에서 자기에게 어떻게 답할지뿐입니다. `PROMOTE_MIN_SPEAKERS=2`는 무언가 바뀌기 전에 두 번째 사람의 동의를 요구합니다(관리자는 예외). 두 사람의 교정이 어긋나면 관리자가 결정할 때까지 아무것도 바뀌지 않습니다.

어떤 교정은 답장 하나를 넘어 통하는 사실을 가르칩니다. 그룹이 어떤 장소나 사람을 뭐라고 부르는지, 올해 주최자가 누구인지, 누군가 어떻게 불리고 싶어 하는지 같은 것입니다. 이런 경우 반응 판정은 그 사실을 "이 그룹은 헬스장을 '동굴'이라고 부른다." 같은 한 문장으로 적습니다. 변경이 승격되면 그 문장은 메시지 내용과 상관없이 이 채팅의 이후 모든 프롬프트에 들어갑니다. 그러면 캐릭터는 교정받은 답장과 전혀 닮지 않은 답장에도 그것을 씁니다. 이런 문장을 남길 수 있는 것은 답장의 대상이나 관리자뿐이고, 핵심 기억과 같은 필터를 거치므로 지시를 담을 수 없습니다. 별명처럼 다른 사람에 대한 주장에는 다른 사람의 교정에 대한 더 엄격한 규칙이 적용됩니다. 활동 보기는 그 문장을 **앞으로는** 아래에 보여 주고, 롤백하면 변경과 함께 사라집니다.

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

여러 사람이 동시에 봇의 재시도를 기다릴 수 있고, 한 사람의 불평이 다른 사람의 불평을 취소하지 않습니다. 각 답장은 사용 중인 재작성을 많아야 하나 유지합니다. 두 번째 재작성은 관리자를 기다립니다.

### 검토하고 뒤집기

모든 학습은 추가 전용 장부에 기록됩니다. 터미널이나 로컬 페이지의 [활동](#활동) 보기에서 검토하고 뒤집을 수 있습니다.

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

`promote`, `reject`, `rollback`, `supersede`는 `--reason`을 받아 장부에 씁니다. `promote`는 이미 재작성이 사용 중인 답장에 대한 재작성을 거부하고, 그것을 교체하는 `supersede` 명령을 출력합니다. 활동 보기에서는 **유지**가 대신 교체해 줍니다.

### 기본값

이 설정은 `.env`에 있습니다.

- `REACT_LEARN_ENABLED`, `REACT_ELICIT_ENABLED`, `PROMOTE_AUTO_ENABLED`는 켜져 있습니다. 반응 판정에는 추가 모델 호출 비용이 듭니다. `REACT_ELICIT_ENABLED`는 이유 없는 거부 뒤에 봇이 2분 뒤 한 번 돌아와 무엇이 더 나았을지 묻게 합니다. 질문을 받은 구경꾼도 구경꾼이므로 그 답은 절대 강하지 않습니다.
- `PROMOTE_AUTO_ENABLED=false`는 모든 승격을 사용자의 결정에 맡깁니다.
- `PROMOTE_MIN_SPEAKERS=1`. 두 번째 사람을 요구하려면 `2`로 설정하십시오. `PROMOTE_EVIDENCE_MAX_AGE_DAYS=30`은 더 오래된 반응을 계산하지 않는다는 뜻입니다.
- `EVAL_ENABLED`(봇이 자기 답장을 채점)와 `EVOLVE_AUTO_ENABLED`는 꺼져 있습니다.

`persona.txt`를 편집해도 배운 것은 유지됩니다. `PERSONA_NAME`이나 `PERSONA_VERSION`을 바꾸면 새 캐릭터가 시작되고 이전 캐릭터가 배운 것은 더 이상 적용되지 않습니다.

## 활동

로컬 페이지의 **활동**은 캐릭터가 어디에 있고 무엇을 해 왔는지 보여 줍니다. 사이드바의 **채팅**과 **플랫폼 연결** 사이에 있습니다. 호박색 점은 사용자의 결정을 기다리는 것이 있다는 뜻입니다.

이 보기는 캐릭터가 아는 모든 채팅을 플랫폼, 그룹인지 DM인지, 채팅 ID 끝부분, 마지막 활동 시간과 함께 나열합니다. 페이지 자체의 채팅은 **이 페이지**로 표시됩니다. 채팅 옆의 숫자는 거기서 기다리는 항목 수를 보여 줍니다. 채팅을 고르면 네 부분이 보입니다.

- **확인 대기**에는 아직 승격 규칙(같은 채팅의 일치하는 반응 두 개, 그중 하나는 강함)을 충족하지 못한 변경이 있습니다. 각각은 한 말에 취소선을 긋고 대신 할 말을 보여 주는 **개선된 표현**이거나 **계속 사용할 답장**입니다. 누가 반응했는지도 보여 줍니다. **유지**는 변경을 사용 상태로 만들고 그 답장에 이미 사용 중인 재작성을 교체합니다. **폐기**는 거부합니다.
- **학습 내용**은 사용 중인 것을 나열합니다. **실행 취소**는 변경을 롤백합니다.
- **기억**은 그 채팅의 기억 메모, 누구에 관한 것인지, 누가 추가했는지를 핵심 메모와 함께 보여 줍니다. **삭제**는 하나를 삭제합니다. DM에서는 그룹들이 그 사람에 대해 메모한 것도 포함됩니다.
- **최근 활동**은 최근 메시지와 답장을 보여 줍니다. 각 답장에는 말한 이유의 태그가 붙습니다: **호출됨**, **스스로 판단하여 발언**, **후속 발언**, **먼저 화제 제시**, **관리자**. 넘어간 줄에는 조용히 있던 이유가 표시됩니다. 최근 활동은 메모리에만 보관되므로 재시작하면 지워집니다.

**유지**, **폐기**, **실행 취소**는 모두 `personagent learned`와 같은 장부에 행위자 `dashboard`, 이유 `local page`로 기록됩니다.

채팅 목록 아래의 **캐릭터의 학습 내용**은 캐릭터가 모든 채팅에서 학습한 내용을 모두 나열합니다. 장부 파일을 직접 읽으므로 캐릭터가 실행 중이 아닐 때에도 사용할 수 있습니다.

- **사용 중**, **확인 대기**, **폐기됨**, **취소됨**, **대체됨** 탭에는 각각 항목 수가 표시됩니다.
- 항목을 선택하면 전체 기록이 열립니다. 확인 대기 중인 이유와 승격 체크리스트, 그 앞의 메시지들, 계산되는지 여부를 포함한 모든 반응, 이력이 표시됩니다.
- **유지**는 확인 대기 중인 항목을 사용 상태로 만듭니다. 같은 답장의 다른 표현이 이미 사용 중이면 그 표현을 보여 주고 교체하기 전에 확인을 요청합니다. **실행 취소**는 항목의 사용을 중지하고, **복원**은 실행 취소한 항목을 다시 사용 상태로 만듭니다. **폐기**는 먼저 확인을 요청한 뒤 항목을 영구적으로 거부합니다. 폐기되거나 대체된 항목은 복원할 수 없습니다.
- 캐릭터가 다른 언어로 대화하면서 학습한 내용도 있으면, **학습 시 언어**로 해당 항목들로 전환할 수 있습니다.

캐릭터가 실행 중이면 결정은 캐릭터를 통해 처리됩니다. 그렇지 않으면 결정이 파일에 직접 기록됩니다. 터미널에서도 같은 기록을 볼 수 있습니다. [검토하고 뒤집기](#검토하고-뒤집기)를 참고하십시오.

채팅 목록은 캐릭터가 실행되기 전까지 비어 있습니다. 페이지에서 채팅하거나 플랫폼을 연결하면 시작되고 보기가 그렇게 알려 줍니다. `DASHBOARD_ENABLED=false`는 보기 뒤의 데이터를 끕니다. 그러면 보기는 꺼져 있다고 표시하고 `personagent doctor`는 `activity: off`를 보고합니다.

로컬 페이지는 이 컴퓨터에서만 답합니다. 로컬 페이지가 없는 서버에서는 `personagent learned`로 배운 것을 검토하고 뒤집으십시오. 스크립트는 같은 데이터를 서비스 API로 읽을 수 있으며, 배포 가이드의 [활동 절](deploy.ko.md#활동)에 설명되어 있습니다.

![그룹 채팅의 활동 보기: 유지 및 폐기 버튼이 있는 확인 대기 항목 두 개(개선된 표현, 계속 사용할 답장), 실행 취소 버튼이 있는 학습 내용 항목 하나, 기억 항목 하나, 그리고 발언하거나 발언하지 않은 이유가 표시된 최근 활동](activity.png)

## 측정하기

`personagent eval`은 영어와 중국어의 라벨이 붙은 케이스(`data/evals/`)로 실제 에이전트를 실행합니다. 모든 케이스, 답장, 판정을 담은 JSON 보고서를 홈 폴더의 `benchmark_runs/`나 `--out`으로 준 경로에 씁니다.

| 스위트 | 측정 대상 |
|---|---|
| `speak` | 말해야 할 때 말하는지. 언어별 그룹 채팅 순간 60개: 아무도 이름을 부르지 않는 20개, 말한 직후 20개, 이름이 나오는 20개로, 각각 절반은 조용히 있어야 한다고 라벨이 붙어 있습니다. 조용히 있어야 하는 것 중 다수는 Nova-5G라는 와이파이나 다른 사람에게 그에 대해 하는 말처럼 지나가듯 이름을 언급합니다. 판정자는 없습니다. 답장은 라벨과 비교해 맞거나 틀립니다. |
| `persona` | 캐릭터 텍스트만 시스템 프롬프트로 받은 같은 모델보다 personagent가 캐릭터를 더 잘 연기하는지. 언어별 순간 40개로 그룹 22개, DM 18개입니다. 판정 모델은 두 답장을 누구 것인지 모른 채 각각을 먼저 두고 한 번씩 봅니다. 두 선택이 일치하면 그 답장이 이기고, 어긋나면 그 순간은 분할로 절반만 계산합니다. |
| `learning` | 승격 규칙이 예상대로 판단하는지, 승격된 교정이 그 채팅의 이후 답장을 바꾸는지. 언어별 시나리오 20개입니다. 일부는 그룹이 장소를 뭐라고 부르는지처럼 모델이 짐작할 수 없는 그룹 관습을 가르칩니다. 다른 것들은 보류되어야 합니다: 구경꾼의 교정, 트롤의 교정, 당사자가 떠나 버린 교정입니다. 각 교정 전후로 탐색 메시지를 실행하고, 판정자가 답장이 가르친 행동을 따르는지 말합니다. |

```bash
personagent eval --suite speak
personagent eval --suite all --lang zh --repeat 5
```

`--repeat N`은 모든 케이스를 매번 새 배포에서 N번 시도하므로, 시도 간 결과가 얼마나 움직이는지 볼 수 있습니다. 95% 구간은 각 케이스를 한 번으로 계산합니다. 60개 케이스를 5번 시도해도 증거는 60개 케이스 분량입니다. `--limit N`은 스위트별로 N개 케이스를 모드와 라벨에 고르게 실행합니다.

페르소나와 학습 스위트에는 측정 대상과 다른 판정 모델이 필요합니다. `BENCH_JUDGE_MODEL`을 설정하고, 다른 엔드포인트가 제공한다면 `BENCH_JUDGE_BASE_URL`과 `BENCH_JUDGE_API_KEY`도 설정하십시오. 별도의 판정자가 없으면 이 스위트는 실행을 거부합니다. `--allow-same-judge`는 그래도 실행하고 보고서에 표시합니다. 학습 스위트는 스스로 아무것도 승격하지 않고, 기대값은 승격 설정을 따릅니다. 기본값보다 엄격한 정책에서는 모든 시나리오가 보류될 것으로 기대됩니다. 모든 실행은 모델을 호출하고 상태의 일회용 사본에서 동작합니다. `--keep`은 사본을 유지하고 위치를 출력합니다.

`--rejudge REPORT`는 보관한 보고서의 답장을 지금 설정한 `BENCH_JUDGE_MODEL`로, 테스트 대상 모델을 호출하지 않고 다시 판정하며, 결과를 원본 옆에 씁니다. 답장, 기준선, 승격 정책이 한 일은 그대로입니다.

방법과 모든 보고서를 포함한 최신 결과는 [evals/2026-10-18](evals/2026-10-18/README.ko.md)에 있습니다. 보고서를 읽을 때 참고할 점입니다.

- `speak`에서 놓친 경우의 대부분은 이름이 영화관이나 강아지처럼 다른 것을 뜻하는 줄이거나, 누군가 그것이 한 말을 다른 사람에게 전하는 줄입니다. 이름은 호출로 계산되고 모델이 그것을 뒤집는 일은 드뭅니다.
- `persona`에서 분할은 판정자가 두 번 다 먼저(또는 나중에) 온 답장을 골랐다는 뜻입니다. 공개된 판정은 Claude Opus 5.5의 것입니다. `personagent eval` 밖에서 묶음으로 판정했고, 각 보고서의 `rejudged` 필드가 이를 기록합니다. 각 쌍의 `earlier` 필드에는 첫 판정자 Claude Haiku 5.5의 판정이 남아 있습니다.
- `learning`에서 정책 행과 탐색 행은 다른 질문에 답합니다. 정책 행은 규칙이 올바른 교정을 승격했는지 묻습니다. 탐색 행은 승격된 교정이 이후 답장을 바꿨는지 묻습니다. `not_promoted` 탐색 행은 잡음 기준입니다. 프롬프트가 전혀 바뀌지 않았기 때문입니다.

## 동작 방식

![아키텍처: 그룹 채팅 메시지는 판단, 프롬프트 구성, 모델, 점검을 거치고 답장은 커넥터를 통해 돌아갑니다. 봇이 발언하지 않으면 아무것도 보내지 않습니다. 반응은 판정되어 증거 로그에 들어가고, 승격이 승인한 것만 프롬프트가 읽는 예시에 도달합니다](persona_llm_agent_architecture.svg)

모든 플랫폼은 하나의 엔드포인트로 들어옵니다. 각 메시지는 인증되고, 중복이 제거되고, 보강됩니다. 즉 이미지는 설명되고 링크는 펼쳐집니다. 그다음 판단 단계입니다. 봇을 불렀다면 답합니다. 그렇지 않으면 대화가 충분히 쌓이기를 기다리고(기본값 30개 메시지), `LLM_JUDGE_MODEL`에 대한 저렴한 게이트 호출이 사람이라면 끼어들지 판단합니다. 연달아 온 메시지에는 최신 줄에 답장 하나를 합니다. 02:00부터 07:00 사이에는 부르지 않는 한 대부분 끼어들지 않습니다.

프롬프트는 페르소나, 일치하는 로어북 항목, 이 대화의 기억, 가장 관련 있는 예시를 합칩니다. 모델은 `reasoning`, `intent`, `reply`, `mem`이 있는 JSON으로 답합니다. 답장은 출력 필터와 캐릭터 정책을 거친 뒤 채팅 크기의 메시지로 나뉩니다. 형식이 잘못된 답은 안전하게 실패하여 아무것도 보내지 않습니다.

학습은 그 경로 옆에서 실행되며 절대 그 안에 들어가지 않고, 상태를 홈 폴더 `runtime/` 아래 일반 파일에 보관합니다. 반응은 다시 쓰이지 않는 증거 로그에 들어갑니다. 이를 판가름하면 후보가 나오고, 승격 정책이 어떤 후보가 답장을 바꿔도 되는지 결정합니다. 승격된 후보는 검색이 재시작 없이 다시 불러오는 작은 보기 파일에 기록됩니다. 모델을 파인튜닝하지 않습니다. 캐릭터는 프롬프트의 예시를 개선해서 배웁니다. 장부가 추가 전용이므로 "왜 이렇게 말하지?"에는 항상 답이 있고, 롤백에는 항상 되돌릴 대상이 있습니다.

## 개인정보와 동의

personagent가 저장하는 모든 것은 사용자 컴퓨터의 홈 폴더에 머무릅니다. 키가 든 `.env`, `persona.txt`, `persona.card.json`, `runtime/`, 플랫폼 자격 증명이 든 `platforms/`입니다. 클론에서는 이 파일들이 Git에 커밋되지 않습니다. 자격 증명과 실제 대화가 들어 있을 수 있으므로 백업하고 비공개로 유지하십시오. 로컬 페이지는 키를 브라우저 저장소에 넣지 않습니다.

[활동](#활동) 보기는 127.0.0.1에서만 수신하는 로컬 페이지의 일부입니다. 그 뒤의 서비스 API는 현재 사용자 계정만 읽을 수 있는 파일 `runtime/dashboard.token`의 토큰을 가진 요청에만 답합니다. `CONNECTOR_TOKEN`으로는 열 수 없습니다. 보기는 API 키나 토큰을 절대 보여 주지 않습니다. `DASHBOARD_ENABLED=false`로 끕니다.

하루에 많아야 한 번, 로컬 페이지, `personagent up`, `personagent doctor`는 pypi.org에 최신 버전 번호를 묻습니다. 요청에는 personagent 자체 버전만 담깁니다. `UPDATE_CHECK_ENABLED=false`로 멈춥니다.

모델 제공업체는 대화를 볼 수 있습니다.

- 채팅 맥락은 `LLM_BASE_URL`로 갑니다.
- 대체 모델(`LLM_FALLBACK_MODEL`, `LLM_FALLBACK_BASE_URL`)을 설정하면 일반 턴에서도 답장 게이트, 검색 판단, 반응 판정, 자기 평가, 스티커 태깅에 호출되며 채팅 맥락도 받습니다.
- 이미지는 비전 엔드포인트로 갑니다.
- 모델이 무언가를 찾아보기로 하면 검색어는 Tavily(`TAVILY_API_KEY`가 설정된 경우)나 DuckDuckGo로 갑니다.
- `EMBEDDING_MODEL`을 설정하면 답하는 메시지, 기억, 검색 예시가 임베딩 엔드포인트(`EMBEDDING_BASE_URL`, 비어 있으면 `LLM_BASE_URL`)로 갑니다.

실제 사람들에게 연결하기 전에 봇이라고 알리고 메시지 처리에 대한 동의를 받으십시오. [면책 조항](DISCLAIMER.ko.md)을 읽으십시오.

## 문제 해결

**먼저 상태 점검을 실행하십시오.** 로컬 페이지에서 **앱**을 열고 **점검 시작**을 선택합니다. 이 보기는 작동하지 않는 각 서비스, 캐릭터나 플랫폼이 시작되지 않은 이유, 확인이 필요한 설정을 알려 주며, **로그**에서 파일을 열지 않고도 각 로그를 확인할 수 있습니다. [앱 보기](#앱-보기)를 참고하십시오.

**터미널에서는 `personagent doctor`를 실행하십시오.** 설정을 확인하고 철자가 틀렸거나 이름이 바뀐 설정을 알려 줍니다. 그다음 personagent가 의존하는 각 서비스를 점검합니다. 점검은 아주 작은 요청을 보내며 크레딧이 조금 들 수 있습니다. `--json`은 같은 결과를 JSON으로 출력합니다. `--fix`는 1.0에서 폐지된 설정 이름을 바꾸고 이전 파일을 `.env.bak`으로 저장합니다.

**플랫폼이 연결되지 않습니다.** 플랫폼이 자격 증명을 거부하면 페이지가 이유를 알려 줍니다. 플랫폼 콘솔에서 확인하고, Discord는 Message Content Intent가 켜져 있는지 확인하십시오. QR 코드가 만료되면 새로 요청할 수 있고, 실패한 AstrBot 내려받기는 다시 시도할 수 있습니다. 앱 보기의 **플랫폼 연결 상태**에는 personagent가 직접 연결하는 각 플랫폼의 상태가 표시됩니다. 페이지나 `personagent up`이 시작한 모든 것의 로그는 홈 폴더의 `runtime/desktop/`에 있으며, 앱 보기의 **로그**에서도 확인할 수 있습니다.

**실행되는데 답하지 않습니다.** 가장 흔한 원인 세 가지입니다.

1. 에이전트가 꺼져 있습니다. `personagent run` 배너에 `OFF`와 원인이 표시되며, 대개 `LLM_API_KEY`가 없습니다. 로컬 페이지에서 키를 설정하거나 `personagent init`을 실행하십시오.
2. 아무것도 도착하지 않습니다. 로컬 페이지를 실행하는 컴퓨터에서 [활동](#활동)을 열어 채팅을 찾으십시오. 서버에서는 봇 이름을 부르고 서비스 로그를 확인하십시오. 모든 답장과 거부한 모든 채팅이 기록됩니다. 메시지가 도착하지 않았다면 커넥터가 전달하지 않거나 personagent에 닿지 못하는 것입니다. QQ는 봇이 어떤 그룹 메시지를 받는지 QQ 자체에서 확인하십시오. 직접 실행하는 AstrBot에서는 플러그인이 나열된 `groups`와 `dm_users`만 전달하고, NapCat이라면 `aiocqhttp`가 `excluded_platforms`에 있으면 안 됩니다. 플러그인의 `personagent_url`과, `CONNECTOR_TOKEN`이 양쪽에서 일치하는지도 확인하십시오.
3. 부르지 않았습니다. 이름(`PERSONA_NAME`, 단어 전체 일치)으로 부르십시오. 그룹에서는 `CHAT_TRIGGER_COUNT`개 메시지(30개) 뒤에만, 그리고 게이트가 사람이라면 끼어들 거라고 판단할 때만 끼어들기를 고려합니다.

배포 가이드에 [전체 체크리스트](deploy.ko.md#봇이-조용해졌을-때)가 있습니다.

**실행 중입니까?** `curl http://127.0.0.1:8080/health`는 모델을 호출하지 않고 답합니다. `/health/details`는 서비스도 점검하며, 토큰을 설정하면 `X-Personagent-Token` 헤더가 필요합니다.

**시작되지 않습니다.** `personagent run`은 이유를 한 문장으로 알리고 멈춥니다. 흔한 이유는 이미 사용 중인 포트, 같은 홈 폴더에서 실행 중인 다른 personagent, `CONNECTOR_TOKEN` 없이 설정된 네트워크 주소, 아직 설정된 1.0 폐지 설정입니다. 폐지된 설정은 한 줄에 하나씩 `OLD -> NEW`로 나열되고 `personagent doctor --fix` 또는 앱 보기의 **설정 이름 변경**으로 이름을 바꿀 수 있습니다. 페이지에서 시작한 캐릭터가 실패하면 앱 보기가 실패한 부분을 알려 주고 마지막 로그 줄을 보여 줍니다. 페이지와 `personagent up`은 8080이 사용 중이면 빈 포트를 고릅니다.

**설정이 적용되지 않습니다.** 그것을 읽는 프로세스를 재시작하고, 철자를 확인하고, `.env`를 BOM 없는 UTF-8로 저장하십시오. 셸 환경 변수는 `.env`보다 우선합니다. 불리언은 `true`나 `false`입니다. `PERSONA_TZ_OFFSET_HOURS`는 야간 시간대의 시계를 정합니다. 비어 있으면(기본값) personagent는 `AGENT_LANG=zh` 또는 `zh-TW`일 때 UTC+8, 그 외에는 이 컴퓨터의 시간대를 씁니다. 다른 오프셋을 고르려면 숫자를 설정하십시오.

## 0.x에서 업그레이드

1.0에서 대부분의 설정 이름이 바뀌었고, 이전 이름이 남아 있으면 personagent가 시작되지 않습니다. 각각을 `OLD -> NEW`로 나열하고 `personagent doctor --fix`가 `.env`에서 이름을 바꿉니다. 변경 기록의 [Upgrading from 0.4](../CHANGELOG.md#upgrading-from-04)에 모든 단계가 있습니다. 기억과 배운 것은 이어집니다.

## 현재 상태와 기타 문서

personagent 1.4.1은 PyPI에 있습니다. CI는 Linux의 Python 3.10–3.14와 Windows의 Python 3.12에서 테스트를 실행합니다. 추가 CI 작업이 패키지를 설치하고 명령과 로컬 페이지를 구동합니다.

직접 OneBot 경로(`/v1/onebot`)는 폐지 예정이지만 1.x 동안 유지됩니다. `tools/`의 스크립트는 클론에서 실행하는 용도이며 [tools.md](tools.ko.md)에서 설명합니다.

- [시작하기](start.ko.md) · [배포 가이드](deploy.ko.md) · [중국어 단계별 가이드(QQ 스캔 연결과 문제 해결)](deploy.zh-CN.md)
- 커넥터: [AstrBot 플러그인](../integrations/astrbot/astrbot_plugin_personagent/README.ko.md) · [Satori](../integrations/satori/README.ko.md) · [Matrix](../integrations/matrix/README.ko.md) · [프로토콜](connectors.ko.md)
- [모든 설정](../.env.example) · [변경 기록](../CHANGELOG.md) · [기여](../.github/CONTRIBUTING.md) · [보안 정책](../.github/SECURITY.md)
