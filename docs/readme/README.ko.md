<p align="center">
  <img src="https://raw.githubusercontent.com/wangkant/personagent/main/assets/personagent-cover.webp" alt="personagent" width="100%">
</p>

<h3 align="center">사용하는 모든 플랫폼에서 사람처럼 행동하는 에이전트입니다.<br>고유한 캐릭터를 지니고, 기억하며, 대화 상대에게서 배우고, 언제 말할지 스스로 판단합니다.</h3>

<p align="center">
  <a href="https://pypi.org/project/personagent/"><img src="https://img.shields.io/pypi/v/personagent?style=flat-square&label=PyPI&labelColor=24292f&color=0969da&cacheSeconds=3600" alt="PyPI"></a>
  <a href="https://github.com/wangkant/personagent/actions/workflows/ci.yml"><img src="https://img.shields.io/github/actions/workflow/status/wangkant/personagent/ci.yml?branch=main&style=flat-square&label=CI&labelColor=24292f" alt="CI"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/Python-3.10%E2%80%933.14-0969da?style=flat-square&labelColor=24292f" alt="Python 3.10–3.14"></a>
  <a href="https://github.com/wangkant/personagent/blob/main/LICENSE"><img src="https://img.shields.io/badge/License-PolyForm%20Noncommercial-0969da?style=flat-square&labelColor=24292f" alt="라이선스: PolyForm Noncommercial"></a>
</p>

<p align="center"><a href="https://github.com/wangkant/personagent/blob/main/README.md">English</a> · <a href="https://github.com/wangkant/personagent/blob/main/README.zh-CN.md">简体中文</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.zh-TW.md">繁體中文</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.ja.md">日本語</a> · <strong>한국어</strong> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.es.md">Español</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.fr.md">Français</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.de.md">Deutsch</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.pt-BR.md">Português</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.ru.md">Русский</a></p>

*이 문서는 영어 README를 번역한 것입니다. 기준이 되는 영어 README가 더 최신일 수 있습니다.*

personagent는 사람처럼 행동하는 에이전트입니다. 고유한 캐릭터를 지니고, 기억하며, 대화 상대에게서 배우고, 언제 말할지 스스로 판단합니다. QQ, WeChat, Telegram, Discord와 그 밖의 18개 플랫폼의 그룹 채팅과 개인 채팅, 사용자의 컴퓨터에 있는 창, Claude Code, Codex 같은 코딩 어시스턴트 등 사용하는 모든 곳에서 작동합니다. 캐릭터는 직접 고르거나 쓸 수 있으며, OpenAI 호환 모델이라면 어떤 모델로든 실행됩니다.

<p align="center">
  <img src="https://raw.githubusercontent.com/wangkant/personagent/main/docs/welcome.jpg" alt="로컬 페이지의 플랫폼 연결 화면. 스캔하거나 값 한두 개를 붙여넣어 연결하는 플랫폼, 접힌 고급 플랫폼, 참여할 수 있는 코딩 어시스턴트가 표시되어 있습니다" width="960">
</p>

<p align="center"><em>플랫폼 연결 화면은 설정, 캐릭터 채팅과 같은 로컬 페이지에 있습니다.</em></p>

## 왜 personagent인가

<table>
<tr>
<td width="220" valign="top"><strong>고유한 캐릭터를 지닙니다.</strong></td>
<td valign="top">
준비된 성격은 7가지입니다. 그중 셋은 커뮤니티에서 이미 그려 온 캐릭터인 DeepSeek 고래 소녀, GPT 드래곤 소녀, Claude 아가씨로, 초상화가 눈을 깜빡이고, 생각하고, 말합니다.<br>
페르소나는 언제든 다시 쓸 수 있습니다. 캐릭터가 배운 것은 그대로 남습니다.
</td>
</tr>
<tr>
<td width="220" valign="top"><strong>사람처럼 말합니다.</strong></td>
<td valign="top">
사람이 채팅에서 쓰듯이 씁니다. 대화에 쓰이는 언어로 짧고 쉬운 문장을 쓰며, 목록이나 제목, 상담원식 문구는 쓰지 않습니다. 모르는 것은 모른다고 말합니다.<br>
대부분의 플랫폼에서 답장은 짧은 메시지 여러 개로 나뉘어, 입력하는 데 걸릴 만한 간격을 두고 전송됩니다. Telegram, Discord, Matrix에서는 입력 중 표시도 나타납니다.<br>
사람들이 보낸 스티커를 모아 두었다가 어울리는 순간에 사용하며, 심야에는 부르지 않는 한 대화에 거의 끼어들지 않습니다.<br>
기능을 켜 두면 오랫동안 조용한 뒤 먼저 말을 걸고, 사람들이 이야기했던 계획을 나중에 다시 물어봅니다.
</td>
</tr>
<tr>
<td width="220" valign="top"><strong>기억합니다.</strong></td>
<td valign="top">
대화마다 기억이 따로 있습니다. 다시 시작해도 남는 최근 메시지, 이전 대화 요약, 날짜가 붙은 사건, 사람에 관한 사실이며, 스스로 최신 상태로 유지합니다.<br>
기억하는 모든 것은 활동 보기에 표시되며, 그 안의 어떤 항목이든 삭제하거나 복원할 수 있습니다.
</td>
</tr>
<tr>
<td width="220" valign="top"><strong>믿을 만한 지적에서 배웁니다.</strong></td>
<td valign="top">
그룹에서 헬스장을 뭐라고 부르는지처럼 지적에서 배운 내용은 그 대화의 이후 모든 답장에 반영됩니다.<br>
장난꾼이나 구경꾼이 다시 길들일 수는 없습니다.<br>
반응으로 결정할 수 없는 변경은 캐릭터가 스스로 결정하고 그 이유를 기록하므로, 누구도 승인할 필요가 없습니다.<br>
모든 변경은 기록되며, 어느 것이든 되돌릴 수 있습니다.
</td>
</tr>
<tr>
<td width="220" valign="top"><strong>언제 조용히 있어야 할지 압니다.</strong></td>
<td valign="top">
그룹에서는 부르면 답합니다. 그 밖에는 사람이라면 끼어들었을지를 모델이 판단합니다.<br>
메시지가 몰려와도 한 번만 답합니다.
</td>
</tr>
<tr>
<td width="220" valign="top"><strong>모든 플랫폼에 연결됩니다.</strong></td>
<td valign="top">
채팅 플랫폼 22개를 한 페이지에서 휴대폰 스캔 한 번이나 값 한두 개를 붙여 넣어 연결합니다. 대부분은 그룹 채팅과 개인 채팅을 모두 지원합니다.<br>
같은 에이전트가 사용자의 컴퓨터에 있는 창에서도, Claude Code, Codex, DeepSeek Harness 안에서도 답합니다.<br>
그 밖의 플랫폼은 AstrBot, Koishi, Matrix 브리지 또는 직접 작성한 커넥터를 통해 추가할 수 있습니다.
</td>
</tr>
<tr>
<td width="220" valign="top"><strong>지금 가진 환경에서 작동합니다.</strong></td>
<td valign="top">
OpenAI 호환 모델이라면 무엇이든 사용할 수 있습니다. OpenRouter의 무료 모델, 유료 서비스, 또는 Ollama로 사용자의 컴퓨터에서 실행하는 모델입니다.<br>
명령 하나로 열리며 영어, 중국어 또는 다른 8개 언어로 볼 수 있고, 모델 키 하나만 붙여 넣으면 채팅을 시작합니다.
</td>
</tr>
</table>

채팅에서 부탁하면 기억하거나 잊기도 합니다. `노바 기억해: 민수는 채식주의자야`, `노바 잊어: 채식`([기억 명령](https://github.com/wangkant/personagent/blob/main/docs/guide.ko.md#기억-명령)). 무엇을 얼마 동안 보관하는지는 가이드의 [기억](https://github.com/wangkant/personagent/blob/main/docs/guide.ko.md#기억) 절에 나와 있습니다.

## 시작하기

```sh
python -m pip install personagent
personagent
```

[uv](https://docs.astral.sh/uv/)가 있다면 `uvx personagent`로 별도 설치 없이 실행할 수 있습니다. Windows에서는 소스 ZIP을 내려받아 `start.bat`을 더블클릭해도 됩니다.

Windows에서는 전용 창에서 열리고, macOS와 Linux에서는 브라우저에서 열립니다. 모델 API 키를 붙여 넣고 **확인 후 채팅 시작**을 누르십시오. 아직 키가 없습니까? OpenRouter의 무료 모델이 미리 선택되어 있고, 그 키는 무료입니다. `personagent demo`는 키 없이 대본이 있는 장면 세 개를 보여 줍니다. [시작 가이드](https://github.com/wangkant/personagent/blob/main/docs/start.ko.md)가 페이지를 화면별로 안내합니다.

personagent는 무료입니다. 비용은 선택한 모델 서비스에, 그 서비스의 요금대로 냅니다. OpenRouter의 무료 모델은 하루 50회까지 요청할 수 있고, 일부 무료 제공자는 받은 내용을 보관합니다. Ollama는 키 없이 사용자의 컴퓨터에서 모델을 실행합니다.

## 플랫폼 연결하기

로컬 페이지에서 **플랫폼 연결**을 여십시오.

| 페이지 표시 | 플랫폼 | 필요한 것 |
|---|---|---|
| 스캔하여 연결 | QQ, 개인 WeChat | 휴대폰. WeChat 봇은 1:1 대화만 가능 |
| 값 한두 개 붙여넣기 | Telegram, Discord, Matrix, Twitch, IRC, Zulip, VK, Stoat, KOOK, Feishu/Lark, DingTalk, Slack, WeCom AI 봇, Mattermost, Misskey | 앱 콘솔에서 얻는 값. 어떤 값인지 페이지에 표시 |
| 고급 | WeCom 앱, WeChat 공식 계정, QQ 웹훅, OneBot v11 (NapCat), Satori | 공개 주소, 또는 이 컴퓨터의 다른 소프트웨어 |

연결된 플랫폼은 personagent가 시작될 때마다 함께 다시 시작됩니다. 스캔하여 연결하는 플랫폼과 Telegram, Discord, Matrix, Twitch, IRC, Zulip, VK, Stoat는 personagent가 직접 연결하고, 나머지는 personagent가 내려받아 백그라운드에서 실행하는 [AstrBot](https://github.com/AstrBotDevs/AstrBot)을 거칩니다. 디스플레이가 없는 서버에서는 personagent가 직접 연결하는 이 플랫폼들을 터미널에서 `personagent connect <platform>`으로 페이지와 같은 단계와 확인을 거쳐 연결할 수 있고, `personagent up`으로 브라우저 없이 모든 것을 시작합니다. 플랫폼별 설정 방법은 [사용자 가이드](https://github.com/wangkant/personagent/blob/main/docs/guide.ko.md#채팅에-넣기)에, QQ를 처음부터 연결하는 방법은 [중국어 배포 가이드](https://github.com/wangkant/personagent/blob/main/docs/deploy.zh-CN.md)에 있습니다.

이미 AstrBot, Koishi, Matrix를 운영 중입니까? personagent를 그 뒤에서 에이전트로 실행할 수 있습니다. [직접 실행하는 브리지](https://github.com/wangkant/personagent/blob/main/docs/guide.ko.md#직접-실행하는-브리지), [Satori 커넥터](https://github.com/wangkant/personagent/blob/main/integrations/satori/README.ko.md), [Matrix 커넥터](https://github.com/wangkant/personagent/blob/main/integrations/matrix/README.ko.md)를 참고하십시오.

## 코딩 어시스턴트

**설정을 맡기기.** 컴퓨터에서 명령을 실행할 수 있는 코딩 어시스턴트에게 아래 한 줄을 전달하십시오. 모델 키는 직접 로컬 페이지에 붙여 넣으므로, 키가 에이전트를 거치지 않습니다.

```text
https://raw.githubusercontent.com/wangkant/personagent/main/docs/setup-for-agents.md 를 읽고 personagent를 설정해 줘.
```

**작업하면서 캐릭터와 이야기하기.** Claude Code, Codex, DeepSeek Harness(`dsh`)에서 로컬 페이지와 같은 대화와 기억으로 캐릭터를 부를 수 있습니다.

```bash
personagent connect claude-code
personagent connect codex
personagent connect dsh
```

`--remove`는 연결을 다시 해제하며, **플랫폼 연결** 아래의 **코딩 어시스턴트**에서 페이지로 연결과 해제를 모두 할 수 있습니다. 권한, 그리고 턴이 끝날 때 캐릭터가 한마디 하게 하는 `--react`는 [가이드](https://github.com/wangkant/personagent/blob/main/docs/guide.ko.md#코딩-어시스턴트)에서 다룹니다.

## 업데이트와 제거

PyPI에 새 버전이 올라오면 페이지에 알림과 업데이트 명령이 표시됩니다. pip라면 `python -m pip install -U personagent`입니다. 대부분의 설치 방식에서는 페이지의 앱 보기에 있는 **업데이트 후 다시 열기**가 이 명령을 대신 실행합니다. 설정, 캐릭터, 배운 것, 연결된 플랫폼이 모두 남습니다. 제거하려면 [제거 절차](https://github.com/wangkant/personagent/blob/main/docs/setup-for-agents.md#undoing-it)(영어)를 따르십시오.

## 개인정보

personagent가 저장하는 모든 것은 사용자 컴퓨터의 홈 폴더 하나에 남습니다. 선택한 모델 제공자는 자신이 답하는 대화를 보게 되며, personagent는 하루에 한 번 pypi.org에 새 버전이 나왔는지 묻습니다(`UPDATE_CHECK_ENABLED=false`로 끌 수 있습니다). 실제 사람들과 연결하기 전에 봇이라는 사실을 알리고 동의를 받으십시오. 무엇이 어디로 가는지는 [가이드](https://github.com/wangkant/personagent/blob/main/docs/guide.ko.md#개인정보와-동의)에 나와 있습니다.

## 문서

- [사용자 가이드](https://github.com/wangkant/personagent/blob/main/docs/guide.ko.md): 설정, 커넥터, 가르치기, 활동 화면, 문제 해결.
- [배포 가이드](https://github.com/wangkant/personagent/blob/main/docs/deploy.ko.md): 실제 운영하기, 비용, 봇이 조용해졌을 때 확인할 것.
- [커넥터 프로토콜](https://github.com/wangkant/personagent/blob/main/docs/connectors.ko.md): 직접 커넥터를 만들 때 참고하십시오.
- [도구](https://github.com/wangkant/personagent/blob/main/docs/tools.ko.md): 클론한 저장소에서 실행하는 `tools/`의 스크립트.
- [변경 기록](https://github.com/wangkant/personagent/blob/main/CHANGELOG.md) · [기여하기](https://github.com/wangkant/personagent/blob/main/.github/CONTRIBUTING.md) · [보안 정책](https://github.com/wangkant/personagent/blob/main/.github/SECURITY.md) · [면책 조항](https://github.com/wangkant/personagent/blob/main/docs/DISCLAIMER.ko.md)

## 라이선스

personagent는 [PolyForm Noncommercial License 1.0.0](https://github.com/wangkant/personagent/blob/main/LICENSE)으로 배포됩니다(© 2026 Qiankang (Kant) Wang). 비상업적 목적이라면 무료로 사용, 수정, 공유할 수 있으며 상업적 목적으로는 사용할 수 없습니다. `integrations/` 아래의 커넥터와 1.4.0 이하 버전은 계속 MIT 라이선스를 따릅니다. 캐릭터 초상화 세 장은 CC BY-NC-SA 4.0으로 라이선스되며, 크레딧은 [persona_agent/static/characters/LICENSE.md](https://github.com/wangkant/personagent/blob/main/persona_agent/static/characters/LICENSE.md)에 있습니다.

## 감사의 말

- 다른 채팅 플랫폼에는 [AstrBot](https://github.com/AstrBotDevs/AstrBot), [NapCat](https://github.com/NapNeko/NapCatQQ), [satori-python](https://github.com/RF-Tar-Railt/satori-python)을 사용하는 [Koishi](https://koishi.chat), 그리고 [mautrix 브리지](https://docs.mau.fi/bridges/)를 사용하는 [matrix-nio](https://github.com/matrix-nio/matrix-nio)를 통해 연결합니다. WeChat 연결은 Tencent의 [openclaw-weixin 프로토콜 노트](https://github.com/Tencent/openclaw-weixin/blob/main/docs/protocol.md)를 따릅니다.
- 반응에서 배우는 방식은 [Self-Feeding Chatbot](https://arxiv.org/abs/1901.05415), [Alexa self-learning](https://arxiv.org/abs/1911.02557), [BlenderBot 3x](https://arxiv.org/abs/2306.04707)를 참고했으며, 로어북은 [SillyTavern](https://github.com/SillyTavern/SillyTavern)의 World Info를 따릅니다.
