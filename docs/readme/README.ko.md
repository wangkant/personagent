<p align="center">
  <img src="https://raw.githubusercontent.com/wangkant/personagent/main/assets/personagent-cover.webp" alt="personagent: 일러스트로 그린 대화 장면" width="100%">
</p>

<h3 align="center">언제 조용히 있어야 할지 알고, 지적받으면 배우는 그룹 채팅 캐릭터.</h3>

<p align="center">
  <a href="https://pypi.org/project/personagent/"><img src="https://img.shields.io/pypi/v/personagent?color=3776AB&label=PyPI&cacheSeconds=3600" alt="PyPI"></a>
  <a href="https://github.com/wangkant/personagent/actions/workflows/ci.yml"><img src="https://github.com/wangkant/personagent/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/Python-3.10%E2%80%933.14-3776AB?logo=python&logoColor=white" alt="Python 3.10–3.14"></a>
  <a href="https://github.com/wangkant/personagent/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-2f855a.svg" alt="라이선스: MIT"></a>
</p>

<p align="center"><a href="https://github.com/wangkant/personagent/blob/main/README.md">English</a> · <a href="https://github.com/wangkant/personagent/blob/main/README.zh-CN.md">简体中文</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.zh-TW.md">繁體中文</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.ja.md">日本語</a> · <strong>한국어</strong> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.es.md">Español</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.fr.md">Français</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.de.md">Deutsch</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.pt-BR.md">Português</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.ru.md">Русский</a></p>

*이 문서는 영어 README를 번역한 것입니다. 기준이 되는 영어 README가 더 최신일 수 있으며, 이 문서에서 링크하는 가이드는 영어로 되어 있습니다.*

personagent는 그룹 채팅에 들어가는 캐릭터입니다. 캐릭터를 고르거나 직접 작성해서, OpenAI 호환 모델이라면 어떤 모델로든 실행할 수 있습니다. QQ, WeChat, Telegram, Discord에는 직접 연결하고, KOOK, Feishu, DingTalk, Slack, WeCom, Mattermost, Misskey에도 같은 페이지에서 연결할 수 있습니다.

먼저 로컬 브라우저 채팅에서 시작하세요. 모델 키 하나만 추가하고 인사를 건네면 됩니다. 캐릭터를 그룹에 넣고 싶어지면, 휴대폰 스캔 한 번이나 값 한두 개로 앱을 연결하세요.

<p align="center">
  <img src="https://raw.githubusercontent.com/wangkant/personagent/main/docs/welcome.jpg" alt="로컬 페이지의 앱 연결 화면. 참여할 수 있는 모든 플랫폼이 표시되어 있습니다" width="960">
</p>

<p align="center"><em>앱 연결 화면은 설정, 캐릭터 채팅과 같은 로컬 페이지에 있습니다. 로컬 테스트 모델을 쓴 임시 환경에서 찍은 스크린샷입니다.</em></p>

## 시작하기

PyPI에서 설치하고 실행하세요.

```sh
python -m pip install personagent
personagent
```

[uv](https://docs.astral.sh/uv/)가 있다면 `uvx personagent`로 별도 설치 없이 실행할 수 있습니다.

브라우저에서 로컬 페이지가 열리며, **채팅**, **앱 연결**, **캐릭터 및 설정**의 세 화면이 있습니다. 모델 API 키를 붙여 넣고 **확인하고 채팅 시작**을 누르면, 작은 요청 하나로 키를 확인합니다. 모델 서비스 프리셋 10개와 그 밖의 OpenAI 호환 서비스를 쓸 수 있고, 캐릭터의 이름과 성격 프리셋도 있습니다. **페르소나** 상자에는 `persona.txt`의 내용이 들어 있으며, 저장하면 에이전트가 다시 시작되고 배운 것은 그대로 유지됩니다. **추가 기능**에서는 웹 검색, 이미지 이해, 먼저 말하기를 켤 수 있습니다. `personagent`를 다시 실행하면 이미 열려 있는 페이지를 그대로 씁니다. 오른쪽 위 메뉴에서 페이지를 영어, 중국어 또는 다른 8개 언어로 볼 수 있습니다. 캐릭터는 채팅에서 쓰는 언어로 답합니다. 다만 내장된 프롬프트와 데이터는 영어와 중국어뿐이라, 다른 언어에서 얼마나 자연스러운지는 모델에 달려 있습니다.

Windows에서는 소스 ZIP을 내려받아 `start.bat`을 더블클릭해도 됩니다. Python 3.10–3.14를 지원합니다. [간단한 시작 가이드](https://github.com/wangkant/personagent/blob/main/docs/start.md)를 참고하세요. 터미널 명령과 커넥터는 [전체 가이드](https://github.com/wangkant/personagent/blob/main/docs/guide.md)에 있습니다.

## 코딩 에이전트에게 설정 맡기기

컴퓨터에서 명령을 실행할 수 있는 코딩 에이전트라면 personagent 설치와 설정을 대신 해 줄 수 있습니다. 이렇게 전달하세요.

```text
https://raw.githubusercontent.com/wangkant/personagent/main/docs/setup-for-agents.md 를 읽고 personagent를 설정해 줘.
```

에이전트는 캐릭터의 언어, 이름, 성격과 모델 서비스, 사용하려는 채팅 앱을 물어본 뒤, personagent를 설치하고 홈 폴더를 만들고 로컬 페이지를 시작합니다. 모델 키는 직접 그 페이지에 붙여 넣으므로, 키가 에이전트를 거치지 않습니다. 에이전트가 따르는 [지침](https://github.com/wangkant/personagent/blob/main/docs/setup-for-agents.md)은 평범한 Markdown이라 직접 읽어 볼 수도 있습니다.

## 왜 personagent인가

<table>
<tr>
<td width="220" valign="top"><img src="https://raw.githubusercontent.com/wangkant/personagent/main/persona_agent/static/listening.webp" alt="" width="220"></td>
<td valign="top">
<strong>언제 조용히 있어야 할지 압니다.</strong><br>
부르면 답합니다. 그 밖에는 사람이라면 끼어들었을지를 모델이 판단합니다. 주사위를 굴리지 않습니다.<br>
메시지가 몰려와도 하나하나 답하지 않고 한 번만 답합니다.
</td>
</tr>
<tr>
<td width="220" valign="top"><img src="https://raw.githubusercontent.com/wangkant/personagent/main/persona_agent/static/learned-notebook.webp" alt="" width="220"></td>
<td valign="top">
<strong>믿을 만한 지적에서 배웁니다.</strong><br>
그룹에서 헬스장을 뭐라고 부르는지처럼 지적에서 배운 내용은 그 대화의 이후 모든 답장에 반영됩니다.<br>
변경이 적용되려면 같은 대화에서 일치하는 반응이 두 번 필요하고, 그중 하나는 강한 반응이어야 합니다.<br>
장난꾼이나 구경꾼이 다시 길들일 수는 없습니다.<br>
모든 변경은 기록되며, 어느 것이든 되돌릴 수 있습니다.
</td>
</tr>
<tr>
<td width="220" valign="top"><img src="https://raw.githubusercontent.com/wangkant/personagent/main/persona_agent/static/empty-chats.webp" alt="" width="220"></td>
<td valign="top">
<strong>시작하기 쉽고, 그룹이 있는 곳에서 지냅니다.</strong><br>
브라우저에서 설정하고 채팅하며, 영어, 중국어 또는 다른 8개 언어를 지원합니다. 모델 서비스 11개와 선택형 고급 설정이 있습니다.<br>
QQ, WeChat, Telegram, Discord에는 직접 참여하고, 그 밖의 여러 앱에도 같은 페이지에서 참여합니다. 활동 화면에서 무엇을 했는지 볼 수 있습니다.
</td>
</tr>
</table>

- 대화마다 기억이 따로 있습니다.
- 캐릭터를 수정해도 배운 것은 유지됩니다.
- 측정됩니다. `personagent eval`은 말할 때를 잘 고르는지, 캐릭터를 유지하는지, 지적이 남는지를 채점합니다([결과](https://github.com/wangkant/personagent#measured)).

## 그룹에 넣기

로컬 페이지에서 **앱 연결**을 여세요. 앱은 다음과 같이 묶여 있습니다.

| 페이지 표시 | 앱 | 필요한 것 |
|---|---|---|
| 스캔해서 연결 | QQ, 개인 WeChat | 휴대폰. WeChat 봇은 1:1 대화만 가능 |
| 값 한두 개 붙여넣기 | Telegram, Discord, KOOK, Feishu/Lark, DingTalk, Slack, WeCom AI 봇, Mattermost, Misskey | 앱 콘솔에서 얻는 값. 어떤 값인지 페이지에 표시 |
| 고급 | WeCom 앱, WeChat 공식 계정, QQ 웹훅, OneBot v11 (NapCat), Satori | 공개 주소, 또는 이 컴퓨터의 다른 소프트웨어 |

인증 정보는 저장하기 전에 확인하며, 연결된 앱은 personagent가 시작될 때마다 함께 다시 시작됩니다. QQ, WeChat, Telegram, Discord는 personagent가 직접 연결하고, 나머지는 personagent가 내려받아 백그라운드에서 실행하는 [AstrBot](https://github.com/AstrBotDevs/AstrBot)을 거치므로 따로 열어야 할 것이 없습니다. 서버에서는 `personagent up`으로 브라우저 없이 캐릭터와 연결된 모든 앱을 시작합니다.

**이미 AstrBot, Koishi, Matrix를 운영 중인가요?** 이 컴퓨터의 AstrBot이라면 `personagent connect astrbot`이 플러그인과 공유 토큰을 설치합니다. 다른 컴퓨터의 AstrBot이라면 [최신 릴리스](https://github.com/wangkant/personagent/releases/latest)의 `astrbot_plugin_personagent.zip`을 플러그인 페이지의 **Install from File**로 업로드한 다음, 아래 가이드대로 토큰과 personagent의 HTTPS 주소를 설정하세요. [Koishi](https://koishi.chat)는 [Satori 커넥터](https://github.com/wangkant/personagent/blob/main/integrations/satori/README.md)로, mautrix 브리지 뒤의 WhatsApp과 Signal을 포함한 [Matrix](https://matrix.org)는 [Matrix 커넥터](https://github.com/wangkant/personagent/blob/main/integrations/matrix/README.md)로 연결합니다.

각 앱의 설정 방법은 [사용자 가이드](https://github.com/wangkant/personagent/blob/main/docs/guide.md#put-it-in-a-chat)와 [배포 가이드](https://github.com/wangkant/personagent/blob/main/docs/deploy.md)에 있으며, [중국어 단계별 가이드](https://github.com/wangkant/personagent/blob/main/docs/deploy.zh-CN.md)는 QQ를 처음부터 다룹니다.

## 다른 프로젝트와 비교

사람들이 흔히 함께 비교하는 프로젝트들입니다. 2026년 10월 기준 각 프로젝트의 문서를 바탕으로 했습니다.

- **AstrBot**(AGPL-3.0)은 18개 이상의 플랫폼을 지원하는 봇 프레임워크로, WebUI와 큰 플러그인 마켓이 있습니다. 부르지 않아도 무작위로 답할 수 있으며(10% 확률, 기본값은 꺼짐), 학습은 플러그인에 맡깁니다.
- **MaiBot**(GPL-3.0)은 NapCat을 통해 QQ에서 동작하는 캐릭터 봇으로, WebUI와 원클릭 런처가 있습니다. 플래너 모델이 얼마나 자주 말할지 정하고, 대화에서 표현과 은어를 익힙니다.
- Koishi용 **ChatLuna의 캐릭터 플러그인**(AGPL-3.0)은 정해진 간격, 대화가 얼마나 활발한지, 얼마나 오래 조용했는지 같은 규칙에 따라 대화에 참여합니다.
- **ElizaOS**(MIT)는 Discord, Telegram, Slack 등을 위한 TypeScript 에이전트 프레임워크로, 응답할지를 모델이 정합니다.

다른 프로젝트들이 플러그인에 맡기거나 설명하지 않는 부분 중 personagent에 내장된 것은 다음과 같습니다. 사람들이 답장에 보인 반응(지적, 거절, 받아들여진 재시도)에서 배웁니다. 변경이 적용되려면 같은 대화에서 일치하는 반응이 두 번 필요하고, 그중 하나는 강한 반응이어야 합니다. 모든 변경은 기록되며 되돌릴 수 있습니다. 그리고 동작 방식을 공개된 평가로 측정합니다([아래](https://github.com/wangkant/personagent#measured)).

다른 프로젝트가 앞선 부분은 모든 설정을 WebUI에서 다루는 데스크톱 앱, 큰 플러그인 생태계, 그리고 은어, 스티커 팩, 이미지 기억입니다. 이미 AstrBot이나 Koishi를 쓰고 있다면 둘 중 하나를 고를 필요가 없습니다. personagent를 그 뒤에서 캐릭터로 실행할 수 있습니다.

## 측정 결과

`personagent eval`은 레이블이 붙은 대화 장면들에 실제 에이전트를 돌려 봅니다. 2026-10-18의 최신 실행에서는 기본 제공 캐릭터를 OpenRouter를 통해 두 모델에서 실행하고, 모든 사례를 세 번씩 시도했으며, Claude Opus 5.5가 블라인드로 판정했습니다. 영어 / 중국어:

| | deepseek-v4.1-flash | gpt-6-luna |
|---|---|---|
| 말할 때를 맞게 판단 (60개 장면) | 83% / 80% | 93% / 91% |
| 같은 모델에 프롬프트만 준 경우보다 캐릭터를 더 잘 연기 (40개 장면) | 63% / 58% | 75% / 53% |
| 지적에서 배운 내용을 나중에 다르게 표현된 메시지에서 활용 | 76% / 56% | 71% / 67% |

- 자신을 향한 메시지를 무시하는 일은 드뭅니다. 틀린 경우는 대부분 이름이 영화관이나 강아지처럼 다른 것을 가리킬 때였습니다.
- 중국어에서는 프롬프트만 준 경우에 대한 우위가 오차 범위 안에 있습니다.
- 지적에서 배운 내용이 유지되도록 고치기 전(그날 첫 실행 뒤에 수정됨)에는 이후 메시지 58개 중 2개만 그 내용을 활용했습니다.
- 장난꾼, 구경꾼, 자리를 뜬 사람의 지적은 84번의 시도에서 한 번도 통과하지 못했습니다.

[전체 결과](https://github.com/wangkant/personagent/tree/main/docs/evals/2026-10-18)에는 신뢰 구간, 유형별 실패, 방법, 수치가 보여 주지 않는 것, 그리고 모든 보고서가 있습니다.

## 문서

- [사용자 가이드](https://github.com/wangkant/personagent/blob/main/docs/guide.md) ([중국어](https://github.com/wangkant/personagent/blob/main/docs/guide.zh-CN.md)): 설치, 설정, 터미널 채팅, 커넥터, 가르치기, 활동 화면, 문제 해결.
- [배포 가이드](https://github.com/wangkant/personagent/blob/main/docs/deploy.md): 실제 운영하기. 커넥터, QQ, 엔드포인트 공개, 비용, 봇이 조용해졌을 때 확인할 것.
- [중국어 배포 튜토리얼](https://github.com/wangkant/personagent/blob/main/docs/deploy.zh-CN.md): QQ를 처음부터 단계별로.
- [커넥터 프로토콜](https://github.com/wangkant/personagent/blob/main/docs/connectors.md): 메시지마다 서명된 HTTP 요청 하나. 직접 커넥터를 만들 때 참고하세요.
- [도구](https://github.com/wangkant/personagent/blob/main/docs/tools.md): 클론한 저장소에서 실행하는 `tools/`의 스크립트.
- [변경 기록](https://github.com/wangkant/personagent/blob/main/CHANGELOG.md), [0.4에서 업그레이드하기](https://github.com/wangkant/personagent/blob/main/CHANGELOG.md#upgrading-from-04) 포함.
- [기여하기](https://github.com/wangkant/personagent/blob/main/.github/CONTRIBUTING.md) · [보안 정책](https://github.com/wangkant/personagent/blob/main/.github/SECURITY.md) · [면책 조항](https://github.com/wangkant/personagent/blob/main/docs/DISCLAIMER.md)

## 개인정보

personagent가 저장하는 모든 것은 내 컴퓨터의 홈 폴더 하나에 남습니다. 키가 담긴 `.env`, `persona.txt`, `runtime/`, 그리고 관리되는 AstrBot과 직접 연결의 인증 정보가 담긴 `platforms/`입니다. 선택한 모델 제공자는 자신이 답하는 대화를 보게 되며, personagent는 하루에 한 번 pypi.org에 새 버전이 나왔는지 묻습니다(`UPDATE_CHECK_ENABLED=false`로 끌 수 있습니다). 실제 사람들과 연결하기 전에 봇이라는 사실을 알리고 동의를 받으세요. 무엇이 어디로 가는지는 [가이드](https://github.com/wangkant/personagent/blob/main/docs/guide.md#privacy-and-consent)에 정확히 나와 있습니다.

## 상태

1.3.1이 2026-10-26에 PyPI에 릴리스되었습니다. 가장 많이 검증된 플랫폼은 QQ로, 1.0에서는 AstrBot을 통해, 1.1부터는 직접 연결합니다. WeChat, Telegram, Discord 연결은 저장 전에 실제 서비스에 인증 정보를 확인하며, 그 외에는 대역 서비스로 테스트합니다. Satori와 Matrix 커넥터도 대역 서비스로 테스트합니다. CI는 Linux에서 Python 3.10–3.14, Windows에서 Python 3.12로 테스트를 실행하고, 패키지를 설치해 명령과 로컬 페이지를 직접 구동하는 작업도 함께 돌립니다.

## 라이선스

[MIT](https://github.com/wangkant/personagent/blob/main/LICENSE) © 2026 Qiankang (Kant) Wang.

## 감사의 말

- 다른 채팅 플랫폼에는 [AstrBot](https://github.com/AstrBotDevs/AstrBot), [NapCat](https://github.com/NapNeko/NapCatQQ), [satori-python](https://github.com/RF-Tar-Railt/satori-python)을 사용하는 [Koishi](https://koishi.chat), 그리고 [mautrix 브리지](https://docs.mau.fi/bridges/)를 사용하는 [matrix-nio](https://github.com/matrix-nio/matrix-nio)를 통해 연결합니다. WeChat 연결은 Tencent의 [openclaw-weixin 프로토콜 노트](https://github.com/Tencent/openclaw-weixin/blob/main/docs/protocol.md)를 따릅니다.
- 반응에서 배우는 방식은 [Self-Feeding Chatbot](https://arxiv.org/abs/1901.05415), [Alexa self-learning](https://arxiv.org/abs/1911.02557), [BlenderBot 3x](https://arxiv.org/abs/2306.04707)를 참고했으며, 로어북은 [SillyTavern](https://github.com/SillyTavern/SillyTavern)의 World Info를 따릅니다.
