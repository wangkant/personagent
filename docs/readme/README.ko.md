<p align="center">
  <img src="https://raw.githubusercontent.com/wangkant/personagent/main/assets/personagent-cover.webp" alt="personagent" width="100%">
</p>

<h3 align="center">언제 조용히 있어야 할지 알고, 지적받으면 배우는 그룹 채팅 캐릭터.</h3>

<p align="center">
  <a href="https://pypi.org/project/personagent/"><img src="https://img.shields.io/pypi/v/personagent?color=3776AB&label=PyPI&cacheSeconds=3600" alt="PyPI"></a>
  <a href="https://github.com/wangkant/personagent/actions/workflows/ci.yml"><img src="https://github.com/wangkant/personagent/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/Python-3.10%E2%80%933.14-3776AB?logo=python&logoColor=white" alt="Python 3.10–3.14"></a>
  <a href="https://github.com/wangkant/personagent/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-2f855a.svg" alt="라이선스: MIT"></a>
</p>

<p align="center"><a href="https://github.com/wangkant/personagent/blob/main/README.md">English</a> · <a href="https://github.com/wangkant/personagent/blob/main/README.zh-CN.md">简体中文</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.zh-TW.md">繁體中文</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.ja.md">日本語</a> · <strong>한국어</strong> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.es.md">Español</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.fr.md">Français</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.de.md">Deutsch</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.pt-BR.md">Português</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.ru.md">Русский</a></p>

*이 문서는 영어 README를 번역한 것입니다. 기준이 되는 영어 README가 더 최신일 수 있습니다.*

personagent는 그룹 채팅에 들어가는 캐릭터입니다. 준비된 캐릭터를 고르거나 직접 써서, OpenAI 호환 모델이라면 어떤 모델로든 실행할 수 있습니다. 먼저 브라우저에서 이야기해 보고, 같은 로컬 페이지에서 QQ, WeChat, Telegram, Discord와 그 밖의 십여 개 앱으로 데려가세요.

<p align="center">
  <img src="https://raw.githubusercontent.com/wangkant/personagent/main/docs/welcome.jpg" alt="로컬 페이지의 앱 연결 화면. 참여할 수 있는 모든 플랫폼이 표시되어 있습니다" width="960">
</p>

<p align="center"><em>앱 연결 화면은 설정, 캐릭터 채팅과 같은 로컬 페이지에 있습니다.</em></p>

## 왜 personagent인가

<table>
<tr>
<td width="220" valign="top"><strong>언제 조용히 있어야 할지 압니다.</strong></td>
<td valign="top">
부르면 답합니다. 그 밖에는 사람이라면 끼어들었을지를 모델이 판단합니다.<br>
메시지가 몰려와도 한 번만 답합니다.
</td>
</tr>
<tr>
<td width="220" valign="top"><strong>믿을 만한 지적에서 배웁니다.</strong></td>
<td valign="top">
그룹에서 헬스장을 뭐라고 부르는지처럼 지적에서 배운 내용은 그 대화의 이후 모든 답장에 반영됩니다.<br>
변경이 적용되려면 같은 대화에서 일치하는 반응이 두 번 필요하고, 그중 하나는 강한 반응이어야 합니다.<br>
장난꾼이나 구경꾼이 다시 길들일 수는 없습니다.<br>
모든 변경은 기록되며, 어느 것이든 되돌릴 수 있습니다.
</td>
</tr>
<tr>
<td width="220" valign="top"><strong>시작하기 쉽고, 그룹이 있는 곳에서 지냅니다.</strong></td>
<td valign="top">
명령 하나로 브라우저에 로컬 페이지가 열리며, 영어, 중국어 또는 다른 8개 언어로 볼 수 있습니다.<br>
모델 키 하나만 붙여 넣으면 채팅할 수 있습니다. 모델 서비스 10개가 프리셋으로 들어 있고, 그 밖의 OpenAI 호환 서비스도 쓸 수 있습니다.<br>
앱은 휴대폰 스캔 한 번이나 값 한두 개를 붙여 넣어 연결합니다. 캐릭터가 거기서 무엇을 했는지는 활동 화면에서 볼 수 있습니다.
</td>
</tr>
<tr>
<td width="220" valign="top"><strong>준비된 캐릭터를 고르거나 직접 만들 수 있습니다.</strong></td>
<td valign="top">
준비된 성격은 7가지입니다. 그중 셋은 커뮤니티에서 이미 그려 온 캐릭터인 DeepSeek 고래 소녀, GPT 드래곤 소녀, Claude 아가씨로, 초상화가 눈을 깜빡이고, 답장을 기다리는 동안 생각하고, 답장이 오면 말합니다.<br>
페르소나는 언제든 다시 쓸 수 있습니다. 캐릭터가 배운 것은 그대로 남습니다.
</td>
</tr>
</table>

- 대화마다 기억이 따로 있고, 잊으라고 하면 잊습니다. `노바 기억해: 민수는 채식주의자야`, `노바 잊어: 채식`, `노바 뭐 기억해?`([기억 명령](https://github.com/wangkant/personagent/blob/main/docs/guide.ko.md#기억-명령)). 그룹에서 어떤 사람에 대해 기록한 내용은 그 사람과의 1:1 대화로도 이어지지만, 반대로는 이어지지 않습니다.
- 채팅에서 쓰는 언어로 답합니다. 시작용 페르소나는 페이지의 10개 언어로 모두 준비되어 있고, 함께 제공되는 예시, 필터, 프롬프트는 영어와 중국어입니다.
- 측정됩니다. `personagent eval`은 말할 때를 잘 고르는지, 캐릭터를 유지하는지, 지적이 남는지를 채점합니다([결과](https://github.com/wangkant/personagent/blob/main/docs/readme/README.ko.md#측정-결과)).

## 시작하기

```sh
python -m pip install personagent
personagent
```

[uv](https://docs.astral.sh/uv/)가 있다면 `uvx personagent`로 별도 설치 없이 실행할 수 있습니다. Windows에서는 소스 ZIP을 내려받아 `start.bat`을 더블클릭해도 됩니다. personagent는 Linux의 Python 3.10–3.14와 Windows의 Python 3.12에서 테스트합니다.

브라우저에서 로컬 페이지가 열립니다. 모델 API 키를 붙여 넣고 **확인하고 채팅 시작**을 누르면, 작은 요청 하나로 키를 확인합니다. 아직 키가 없나요? OpenRouter의 무료 모델이 미리 선택되어 있고, 그 키는 무료입니다. 키를 받기 전에 먼저 구경하고 싶다면 `personagent demo`가 대본이 있는 장면 세 개를 무료로 보여 줍니다. [시작 가이드](https://github.com/wangkant/personagent/blob/main/docs/start.ko.md)가 페이지를 화면별로 안내합니다.

## 비용

personagent는 무료입니다. 비용은 선택한 모델 서비스에, 그 서비스의 요금대로 냅니다.

- **무료로 시작.** OpenRouter의 무료 모델은 하루 50회까지 요청할 수 있습니다. 요청마다 모델이 바뀔 수 있고, 일부 무료 제공자는 받은 내용을 보관합니다. Zhipu의 `glm-4.7-flash`도 무료이고, Ollama는 키 없이 내 컴퓨터에서 모델을 실행합니다.
- **모델을 호출하는 것.** 모든 답장과 작은 단계 두 가지입니다. 아무도 부르지 않았을 때 끼어들지 정하는 판단, 그리고 답장에 사람들이 보인 반응에 대한 판정입니다. `personagent doctor`와 `personagent eval`도 요청을 보냅니다. 나머지는 [배포 가이드](https://github.com/wangkant/personagent/blob/main/docs/deploy.ko.md#비용)에 있습니다.
- **절대 호출하지 않는 것.** `personagent demo`와 기억 명령입니다.

## 그룹에 넣기

로컬 페이지에서 **앱 연결**을 여세요. 앱은 다음과 같이 묶여 있습니다.

| 페이지 표시 | 앱 | 필요한 것 |
|---|---|---|
| 스캔해서 연결 | QQ, 개인 WeChat | 휴대폰. WeChat 봇은 1:1 대화만 가능 |
| 값 한두 개 붙여넣기 | Telegram, Discord, KOOK, Feishu/Lark, DingTalk, Slack, WeCom AI 봇, Mattermost, Misskey | 앱 콘솔에서 얻는 값. 어떤 값인지 페이지에 표시 |
| 고급 | WeCom 앱, WeChat 공식 계정, QQ 웹훅, OneBot v11 (NapCat), Satori | 공개 주소, 또는 이 컴퓨터의 다른 소프트웨어 |

인증 정보는 저장하기 전에 확인하며, 연결된 앱은 personagent가 시작될 때마다 함께 다시 시작됩니다. 스캔해서 연결하는 앱과 Telegram, Discord는 personagent가 직접 연결하고, 나머지는 personagent가 내려받아 백그라운드에서 실행하는 [AstrBot](https://github.com/AstrBotDevs/AstrBot)을 거치므로 따로 열어야 할 것이 없습니다. 서버에서는 `personagent up`으로 브라우저 없이 캐릭터와 연결된 모든 앱을 시작합니다. 앱별 설정 방법은 [사용자 가이드](https://github.com/wangkant/personagent/blob/main/docs/guide.ko.md#채팅에-넣기)에, QQ를 처음부터 한 단계씩 연결하는 방법은 [중국어 배포 가이드](https://github.com/wangkant/personagent/blob/main/docs/deploy.zh-CN.md)에 있습니다.

이미 브리지를 운영 중인가요?

- **AstrBot**: `personagent connect astrbot`이 플러그인과 공유 토큰을 설치합니다. 다른 컴퓨터의 AstrBot은 [가이드](https://github.com/wangkant/personagent/blob/main/docs/guide.ko.md#직접-실행하는-브리지)에서 다룹니다.
- **[Koishi](https://koishi.chat)** 또는 다른 Satori 서버: [Satori 커넥터](https://github.com/wangkant/personagent/blob/main/integrations/satori/README.ko.md)를 쓰세요.
- **[Matrix](https://matrix.org)**(mautrix 브리지 뒤의 WhatsApp과 Signal 포함): [Matrix 커넥터](https://github.com/wangkant/personagent/blob/main/integrations/matrix/README.ko.md)를 쓰세요.

## 코딩 에이전트

**설정을 맡기기.** 컴퓨터에서 명령을 실행할 수 있는 코딩 에이전트에게 아래 한 줄을 전달하세요. 에이전트는 원하는 것을 물어본 뒤 personagent를 설치하고 로컬 페이지를 시작합니다. 모델 키는 직접 그 페이지에 붙여 넣으므로, 키가 에이전트를 거치지 않습니다.

```text
https://raw.githubusercontent.com/wangkant/personagent/main/docs/setup-for-agents.md 를 읽고 personagent를 설정해 줘.
```

**작업하면서 캐릭터와 이야기하기.** 모델 키를 설정하고 나면 Claude Code, Codex, DeepSeek Harness(`dsh`)에서 캐릭터를 부를 수 있습니다.

```bash
personagent connect claude-code
personagent connect codex
personagent connect dsh
```

그쪽에서 새 세션을 열고(DeepSeek Harness는 먼저 다시 시작하세요) 캐릭터에게 말을 전해 달라고 하세요. 로컬 페이지와 같은 일대일 대화이고 기억도 같습니다. Claude Code와 Codex에서는 `--react`를 붙이면 턴이 끝날 때 캐릭터가 한마디 할 수 있습니다. `--remove`는 모든 것을 다시 걷어 냅니다. 권한, `--react`가 모델 서비스로 보내는 내용, 다른 MCP 도구는 [가이드](https://github.com/wangkant/personagent/blob/main/docs/guide.ko.md#코딩-에이전트)에서 다룹니다.

## 측정 결과

`personagent eval`은 레이블이 붙은 대화 장면들에 실제 에이전트를 돌려 봅니다. 2026-10-18의 최신 실행은 1.3.0에서 측정했습니다. 기본 제공 캐릭터를 OpenRouter를 통해 두 모델에서 실행하고, 모든 사례를 세 번씩 시도했으며, Claude Opus 5.5가 블라인드로 판정했습니다. 영어 / 중국어:

| | deepseek-v4.1-flash | gpt-6-luna |
|---|---|---|
| 말할 때를 맞게 판단 (60개 장면) | 83% / 80% | 93% / 91% |
| 같은 모델에 프롬프트만 준 경우보다 캐릭터를 더 잘 연기 (40개 장면) | 63% / 58% | 75% / 53% |
| 지적에서 배운 내용을 나중에 다르게 표현된 메시지에서 활용 | 76% / 56% | 71% / 67% |

- 자신을 향한 메시지를 무시하는 일은 드뭅니다. 틀린 경우는 대부분 이름이 영화관이나 강아지처럼 다른 것을 가리킬 때였습니다.
- 장난꾼, 구경꾼, 자리를 뜬 사람의 지적 84건은 하나도 통과하지 못했습니다.

[전체 결과](https://github.com/wangkant/personagent/blob/main/docs/evals/2026-10-18/README.ko.md)에는 신뢰 구간, 유형별 실패, 방법, 그리고 모든 보고서가 있습니다.

## 다른 프로젝트와 비교

흔히 함께 비교하는 프로젝트들입니다(2026년 11월 기준).

- **AstrBot**(AGPL-3.0)은 십여 개가 넘는 플랫폼을 지원하는 봇 프레임워크로, WebUI와 큰 플러그인 마켓이 있습니다. 부르지 않아도 무작위로 답할 수 있으며(10% 확률, 기본값은 꺼짐), 학습은 플러그인에 맡깁니다.
- **MaiBot**(GPL-3.0)은 NapCat을 통해 QQ에서 동작하는 캐릭터 봇으로, WebUI와 원클릭 런처가 있습니다. 플래너 모델이 얼마나 자주 말할지 정하고, 대화에서 표현과 은어를 익힙니다.
- Koishi용 **ChatLuna의 캐릭터 플러그인**(AGPL-3.0)은 정해진 간격, 대화가 얼마나 활발한지, 얼마나 오래 조용했는지 같은 규칙에 따라 대화에 참여합니다.
- **ElizaOS**(MIT)는 Discord, Telegram, Slack 등을 위한 TypeScript 에이전트 프레임워크로, 응답할지를 모델이 정합니다.

personagent에 내장된 것은 이렇습니다. 사람들이 답장에 보인 반응(지적, 거절, 받아들여진 재시도)에서 배우고, 모든 변경을 기록해 되돌릴 수 있게 하며, 어떻게 동작하는지 측정한 평가를 공개합니다.

다른 프로젝트가 앞선 부분은 모든 설정을 WebUI에서 다루는 데스크톱 앱, 큰 플러그인 생태계, 그리고 은어, 스티커 팩, 이미지 기억입니다. 이미 AstrBot이나 Koishi를 쓰고 있다면 둘 중 하나를 고를 필요가 없습니다. personagent를 그 뒤에서 캐릭터로 실행할 수 있습니다.

## 업데이트와 제거

PyPI에 새 버전이 올라오면 페이지에 알림이 뜨고, 설치한 방식에 맞는 업데이트 명령을 보여 줍니다. pip라면 `python -m pip install -U personagent`입니다. 홈 폴더는 그대로 이어집니다. 설정, 캐릭터, 배운 것, 연결된 앱이 모두 남습니다.

제거하려면 먼저 연결해 둔 코딩 에이전트에서 빼세요(`personagent connect claude-code --remove`, `codex`나 `dsh`도 같은 방식입니다). 그다음 personagent를 종료하고 `python -m pip uninstall personagent`를 실행합니다. 마지막으로 홈 폴더를 삭제합니다. PyPI에서 설치했다면 다른 위치를 고르지 않은 한 `~/personagent`입니다. 여기에는 키, 캐릭터, 배운 모든 것이 들어 있으므로 삭제하면 되돌릴 수 없습니다. uv, pipx의 경우와 폐기해야 할 것은 [전체 절차](https://github.com/wangkant/personagent/blob/main/docs/setup-for-agents.md#undoing-it)(영어)에 있습니다.

## 개인정보

personagent가 저장하는 모든 것은 내 컴퓨터의 홈 폴더 하나에 남습니다. 키가 담긴 `.env`, `persona.txt`, `runtime/`, 그리고 관리되는 AstrBot과 직접 연결의 인증 정보가 담긴 `platforms/`입니다. 선택한 모델 제공자는 자신이 답하는 대화를 보게 되며, personagent는 하루에 한 번 pypi.org에 새 버전이 나왔는지 묻습니다(`UPDATE_CHECK_ENABLED=false`로 끌 수 있습니다). 실제 사람들과 연결하기 전에 봇이라는 사실을 알리고 동의를 받으세요. 무엇이 어디로 가는지는 [가이드](https://github.com/wangkant/personagent/blob/main/docs/guide.ko.md#개인정보와-동의)에 나와 있습니다.

## 문서

- [사용자 가이드](https://github.com/wangkant/personagent/blob/main/docs/guide.ko.md): 설치, 설정, 터미널 채팅, 커넥터, 가르치기, 활동 화면, 문제 해결.
- [배포 가이드](https://github.com/wangkant/personagent/blob/main/docs/deploy.ko.md): 실제 운영하기. 커넥터, QQ, 엔드포인트 공개, 비용, 봇이 조용해졌을 때 확인할 것.
- [커넥터 프로토콜](https://github.com/wangkant/personagent/blob/main/docs/connectors.ko.md): 메시지마다 서명된 HTTP 요청 하나. 직접 커넥터를 만들 때 참고하세요.
- [도구](https://github.com/wangkant/personagent/blob/main/docs/tools.ko.md): 클론한 저장소에서 실행하는 `tools/`의 스크립트.
- [변경 기록](https://github.com/wangkant/personagent/blob/main/CHANGELOG.md) · [기여하기](https://github.com/wangkant/personagent/blob/main/.github/CONTRIBUTING.md) · [보안 정책](https://github.com/wangkant/personagent/blob/main/.github/SECURITY.md) · [면책 조항](https://github.com/wangkant/personagent/blob/main/docs/DISCLAIMER.ko.md)

## 라이선스

코드는 [MIT](https://github.com/wangkant/personagent/blob/main/LICENSE) © 2026 Qiankang (Kant) Wang입니다. 캐릭터 초상화 세 장은 CC BY-NC-SA 4.0으로 라이선스되며, 크레딧은 [persona_agent/static/characters/LICENSE.md](https://github.com/wangkant/personagent/blob/main/persona_agent/static/characters/LICENSE.md)에 있습니다.

## 감사의 말

- 다른 채팅 플랫폼에는 [AstrBot](https://github.com/AstrBotDevs/AstrBot), [NapCat](https://github.com/NapNeko/NapCatQQ), [satori-python](https://github.com/RF-Tar-Railt/satori-python)을 사용하는 [Koishi](https://koishi.chat), 그리고 [mautrix 브리지](https://docs.mau.fi/bridges/)를 사용하는 [matrix-nio](https://github.com/matrix-nio/matrix-nio)를 통해 연결합니다. WeChat 연결은 Tencent의 [openclaw-weixin 프로토콜 노트](https://github.com/Tencent/openclaw-weixin/blob/main/docs/protocol.md)를 따릅니다.
- 반응에서 배우는 방식은 [Self-Feeding Chatbot](https://arxiv.org/abs/1901.05415), [Alexa self-learning](https://arxiv.org/abs/1911.02557), [BlenderBot 3x](https://arxiv.org/abs/2306.04707)를 참고했으며, 로어북은 [SillyTavern](https://github.com/SillyTavern/SillyTavern)의 World Info를 따릅니다.
