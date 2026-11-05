# `tools/` 스크립트

[English](tools.md) · [简体中文](tools.zh-CN.md) · [繁體中文](tools.zh-TW.md) · [日本語](tools.ja.md) · 한국어 · [Español](tools.es.md) · [Français](tools.fr.md) · [Deutsch](tools.de.md) · [Português (Brasil)](tools.pt-BR.md) · [Русский](tools.ru.md)

`tools/`의 스크립트는 personagent를 클론에서 실행하는 사람을 위한 거예요. 패키지와 함께 설치되지 않고, 클론의 `.env`와 `runtime/`을 읽어요. 클론의 인터프리터로 저장소 루트에서 실행하세요.

```bash
.venv/bin/python tools/<script>.py --help     # Windows: .venv\Scripts\python.exe
```

일상적인 작업은 스크립트가 아니라 `personagent` 하위 명령으로 해요. `personagent doctor`, `personagent learned`, `personagent eval`이에요. 프롬프트 변경을 시험하려면 `personagent chat`, 측정하려면 `personagent eval`을 쓰세요.

| 스크립트 | 하는 일 | 필요한 것 | 모델 호출 | 상태 |
|---|---|---|---|---|
| `import_stickers_folder.py` | 이미지 폴더를 스티커 라이브러리로 가져와 하나씩 태그를 달아요. 새 라이브러리가 비어 있는 채로 시작하지 않아요. `--dry-run`은 개수를 보여 주고 `--no-tag`는 파일만 복사해요 | 이미지 폴더, 태그를 달려면 `VISION_MODEL`, `VISION_API_KEY`, `VISION_BASE_URL`도 | 예, 이미지마다 비전 호출 한 번. `--dry-run`이나 `--no-tag`를 주면 호출하지 않아요 | 지원 |
| `bootstrap_from_history.py` | 새 배포를 QQ 그룹 기록으로 한 번 시작해 줘요. 관리자의 스티커와 메시지 길이 프로필을 만들고, 본 스티커를 라이브러리에 저장해요 | 서드파티 QQ 클라이언트 NapCat의 HTTP 서버(`QQ_ONEBOT_URL`, 필수)와 `ACCESS_GROUPS` 또는 `--group`의 QQ 그룹 | 아니요. 저장한 스티커에는 실행 중인 봇의 비전 모델이 나중에 태그를 달아요 | 실험적, QQ와 NapCat 전용 |
| `auto_reviewer.py` | `runtime/eval.jsonl`에서 낮은 자기 평가 점수를 읽어 모델이 각각을 수정 전후 쌍으로 만들게 해요. `--apply`를 주면 쌍마다 공유 피드백 풀에 추가할지 물어봐요 | 점수가 쌓이도록 한동안 `EVAL_ENABLED=true` | 예, 검토 항목마다 한 번(`--limit`, 기본 20). `--dry-run`은 호출하지 않아요 | 실험적. `--apply`는 모든 채팅이 쓰는 풀에 기록해요. 한 채팅에만 수정을 승인하려면 `personagent learned`를 쓰세요 |
| `evolution_benchmark.py` | `data/benchmark/`의 시나리오로 실제 에이전트를 여러 라운드 실행해요. 자기 개선 루프를 켜고 한 번, 끄고 한 번 돌려 둘을 비교해요. `run`이 실행하고 `ingest`가 판정 점수를 읽어 와요 | `LLM_API_KEY`와 시험 대상이 아닌 판정 모델(`--judge export`, `openai` 또는 `anthropic`, `BENCH_JUDGE_MODEL`과 함께) | 예, 아주 많이. 시나리오, 라운드, 조건마다 호출해요 | 실험적 |
| `scenario_probe.py` | 벤치마크 시나리오 후보를 실제 모델로 시험해 벤치마크에 필요한 실패를 드러내는 것을 알려 줘요 | `LLM_API_KEY`, `data/benchmark/scenarios.train.en.jsonl` 형식의 후보 시나리오 파일, 판정용 `--judge-model` | 예, 시나리오마다 답변, 자기 평가, 판정 호출 | 실험적, 벤치마크 제작용 |
| `sticker_holdout_eval.py` | 직접 라벨을 단 스티커로 스티커 승인 게이트의 안정성과 정확도를 측정해요 | `runtime/holdout.jsonl`(형식은 `tools/holdout.example.jsonl`)과 `VISION_*` 설정 세 개 | 예, 이미지 수 × `--runs`(기본 5)번의 비전 호출. 이미지 30개면 약 150번 | 실험적 |
| `package_smoke.py` | 설치된 `personagent` 명령을 처음부터 끝까지 확인해요. 버전, `init --no-input`, `chat`, `/health`를 포함한 `run`, `doctor --json`이에요 | 설치된 `personagent`(`--personagent PATH`)만 | 아니요, 대역 서버가 응답해요 | 지원. CI가 Linux와 Windows에서 실행해요 |
| `welcome_smoke.py` | 설치된 로컬 페이지를 처음부터 끝까지 확인해요. `start --no-browser`, 키 저장, 실제 캐릭터와 한 번 채팅, 페이지를 재사용하는 두 번째 실행, 깨끗한 종료예요 | 설치된 `personagent`(`--personagent PATH`)만 | 아니요, 같은 대역 서버가 응답해요 | 지원. CI가 Linux와 Windows에서 실행해요 |
| `release_notes.py` | 릴리스 태그를 `pyproject.toml`과 대조하고 그 버전의 CHANGELOG 절을 출력해요 | `v1.1.0` 같은 태그 | 아니요 | 지원. 릴리스 워크플로가 실행해요 |

실험적 스크립트는 연구와 유지 보수를 위한 보조 도구이며, 지원 중단 기간 없이 바뀌거나 삭제될 수 있어요. 모델을 호출하는 스크립트는 `.env`에 있는 계정의 크레딧을 써요. 먼저 `--help`를 읽고, `--dry-run`이 있으면 시험해 보세요.
