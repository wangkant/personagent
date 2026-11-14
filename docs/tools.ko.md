# `tools/` 스크립트

[English](tools.md) · [简体中文](tools.zh-CN.md) · [繁體中文](tools.zh-TW.md) · [日本語](tools.ja.md) · 한국어 · [Español](tools.es.md) · [Français](tools.fr.md) · [Deutsch](tools.de.md) · [Português (Brasil)](tools.pt-BR.md) · [Русский](tools.ru.md)

`tools/`의 스크립트는 personagent를 클론에서 실행하는 사용자를 위한 것입니다. 패키지와 함께 설치되지 않으며, 클론의 `.env`와 `runtime/`을 읽습니다. 클론의 인터프리터로 저장소 루트에서 실행하십시오.

```bash
.venv/bin/python tools/<script>.py --help     # Windows: .venv\Scripts\python.exe
```

일상적인 작업은 스크립트가 아니라 `personagent` 하위 명령으로 수행합니다. 해당 명령은 `personagent doctor`, `personagent learned`, `personagent eval`입니다. 프롬프트 변경을 시험하려면 `personagent chat`을, 측정하려면 `personagent eval`을 사용하십시오. `personagent eval --suite memory`는 미리 작성된 통합 답으로 오프라인에서 실행되며, 언어별 케이스는 21개이고 키가 필요 없습니다. 이 버전에서는 모든 케이스가 통과합니다. 다른 스위트는 모델을 호출합니다.

| 스크립트 | 기능 | 필요한 것 | 모델 호출 | 상태 |
|---|---|---|---|---|
| `import_stickers_folder.py` | 이미지 폴더를 스티커 라이브러리로 가져와 하나씩 태그를 붙입니다. 새 라이브러리가 빈 상태로 시작하지 않게 합니다. `--dry-run`은 개수를 표시하고 `--no-tag`는 파일만 복사합니다 | 이미지 폴더. 태그를 붙이려면 `VISION_MODEL`, `VISION_API_KEY`, `VISION_BASE_URL`도 필요 | 예. 이미지마다 비전 호출 한 번. `--dry-run` 또는 `--no-tag`를 지정하면 호출하지 않습니다 | 지원 |
| `bootstrap_from_history.py` | 새 배포를 QQ 그룹 기록으로 한 번 초기화합니다. 관리자의 스티커와 메시지 길이 프로필을 만들고, 확인한 스티커를 라이브러리에 저장합니다 | 서드파티 QQ 클라이언트 NapCat의 HTTP 서버(`QQ_ONEBOT_URL`, 필수)와 `ACCESS_GROUPS` 또는 `--group`의 QQ 그룹 | 아니요. 저장한 스티커에는 실행 중인 봇의 비전 모델이 나중에 태그를 붙입니다 | 실험적, QQ와 NapCat 전용 |
| `sticker_holdout_eval.py` | 직접 레이블을 붙인 스티커로 스티커 승인 게이트의 안정성과 정확도를 측정합니다 | `runtime/holdout.jsonl`(형식은 `tools/holdout.example.jsonl`)과 `VISION_*` 설정 세 개 | 예. 이미지 수 × `--runs`(기본값 5)회의 비전 호출. 이미지 30개이면 약 150회 | 실험적 |
| `package_smoke.py` | 설치된 `personagent` 명령을 처음부터 끝까지 확인합니다. 대상은 버전, `init --no-input`, `chat`, `/health`를 포함한 `run`, `doctor --json`입니다 | 설치된 `personagent`(`--personagent PATH`)만 | 아니요. 대역 서버가 응답합니다 | 지원. CI가 Linux와 Windows에서 실행합니다 |
| `welcome_smoke.py` | 설치된 로컬 페이지를 처음부터 끝까지 확인합니다. 대상은 `start --no-browser`, 키 저장, 실제 캐릭터와의 채팅 한 번, 페이지를 재사용하는 두 번째 실행, 정상 종료입니다 | 설치된 `personagent`(`--personagent PATH`)만 | 아니요. 같은 대역 서버가 응답합니다 | 지원. CI가 Linux와 Windows에서 실행합니다 |
| `window_smoke.py` | 임시 홈에서 실제 앱 창을 열고, 창 안에서 페이지를 설정해 채팅한 뒤 창을 닫습니다 | macOS와 Linux에서는 app 추가 기능으로 설치한 `personagent`(`pip install "personagent[app]"`). Linux에서는 `xvfb-run` 같은 디스플레이도 필요 | 아니요. 같은 대역 서버가 응답합니다 | 지원. CI가 Linux, macOS, Windows에서 실행합니다 |
| `release_notes.py` | 릴리스 태그를 `pyproject.toml`과 대조하고 해당 버전의 CHANGELOG 절을 출력합니다 | `v1.1.0` 같은 태그 | 아니요 | 지원. 릴리스 워크플로가 실행합니다 |
| `locale_gaps.py` | `persona_agent/locales/`의 언어마다 설정 마법사, 터미널 채팅, 데모의 문장 중 번역된 문장 수를 출력합니다. `ja` 같은 언어 코드를 지정하면 아직 번역되지 않아 영어로 표시되는 문장을 출력합니다 | 없음 | 아니요 | 지원. 누락된 문장이 있으면 `tests/test_locales.py`가 실패합니다 |

실험적 스크립트는 연구와 유지 보수를 위한 보조 도구이며, 지원 중단 기간 없이 변경되거나 삭제될 수 있습니다. 모델을 호출하는 스크립트는 `.env`에 설정된 계정의 크레딧을 사용합니다. 먼저 `--help`를 읽고, `--dry-run`이 있으면 이를 사용해 시험하십시오.
