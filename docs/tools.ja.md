# `tools/` のスクリプト

[English](tools.md) · [简体中文](tools.zh-CN.md) · [繁體中文](tools.zh-TW.md) · 日本語 · [한국어](tools.ko.md) · [Español](tools.es.md) · [Français](tools.fr.md) · [Deutsch](tools.de.md) · [Português (Brasil)](tools.pt-BR.md) · [Русский](tools.ru.md)

`tools/` のスクリプトは、personagent をクローンから動かす人のためのものです。パッケージと一緒にはインストールされず、クローンの `.env` と `runtime/` を読みます。クローンのインタープリターで、リポジトリのルートから実行します。

```bash
.venv/bin/python tools/<script>.py --help     # Windows: .venv\Scripts\python.exe
```

日常の作業はスクリプトではなく `personagent` のサブコマンドで行います。`personagent doctor`、`personagent learned`、`personagent eval` です。プロンプトの変更を試すには `personagent chat`、測るには `personagent eval` を使います。

| スクリプト | 内容 | 必要なもの | モデル呼び出し | 状態 |
|---|---|---|---|---|
| `import_stickers_folder.py` | 画像のフォルダーをスタンプライブラリに取り込み、1 枚ずつタグを付けます。新しいライブラリが空から始まらずに済みます。`--dry-run` は件数を表示し、`--no-tag` はファイルをコピーするだけです | 画像のフォルダー。タグ付けには `VISION_MODEL`、`VISION_API_KEY`、`VISION_BASE_URL` も必要 | あり。画像 1 枚につきビジョン呼び出し 1 回。`--dry-run` か `--no-tag` なら呼びません | サポート対象 |
| `bootstrap_from_history.py` | 新しいデプロイを QQ グループの履歴から一度だけ立ち上げます。管理者のスタンプとメッセージ長のプロファイルを作り、見つけたスタンプをライブラリに保存します | サードパーティの QQ クライアント NapCat の HTTP サーバー（`QQ_ONEBOT_URL`、必須）と、`ACCESS_GROUPS` か `--group` の QQ グループ | なし。保存したスタンプには、動作中のボットのビジョンモデルが後でタグを付けます | 実験的。QQ と NapCat のみ |
| `auto_reviewer.py` | `runtime/eval.jsonl` の低い自己評価を読み、モデルにそれぞれを修正前後のペアにさせます。`--apply` を付けると、共有フィードバックプールに追加するかをペアごとに尋ねます | スコアがたまるよう、しばらく `EVAL_ENABLED=true` にしておくこと | あり。確認する項目ごとに 1 回（`--limit`、既定 20）。`--dry-run` は呼びません | 実験的。`--apply` はすべてのチャットが使うプールに書き込みます。1 つのチャットだけで修正を承認するには `personagent learned` を使います |
| `evolution_benchmark.py` | `data/benchmark/` のシナリオで本物のエージェントを数ラウンド動かし、自己改善ループをオンとオフで 1 回ずつ実行して比較します。`run` が実行し、`ingest` が判定スコアを読み戻します | `LLM_API_KEY` と、テスト対象ではない判定モデル（`--judge export`、`openai`、`anthropic` と `BENCH_JUDGE_MODEL`） | あり、大量に。シナリオ、ラウンド、条件のすべてで呼びます | 実験的 |
| `scenario_probe.py` | ベンチマークシナリオの候補を本物のモデルで試し、ベンチマークに必要な失敗を引き出すものを報告します | `LLM_API_KEY`、`data/benchmark/scenarios.train.en.jsonl` の形式の候補シナリオファイル、判定用の `--judge-model` | あり。シナリオごとに返信、自己評価、判定の呼び出し | 実験的。ベンチマーク作成用 |
| `sticker_holdout_eval.py` | 手でラベルを付けたスタンプに対して、スタンプ承認ゲートの安定性と精度を測ります | `runtime/holdout.jsonl`（形式は `tools/holdout.example.jsonl`）と 3 つの `VISION_*` 設定 | あり。画像数 × `--runs`（既定 5）回のビジョン呼び出し。30 枚で約 150 回 | 実験的 |
| `package_smoke.py` | インストール済みの `personagent` コマンドを端から端まで確認します。バージョン、`init --no-input`、`chat`、`/health` 付きの `run`、`doctor --json` です | インストール済みの `personagent`（`--personagent PATH`）だけ | なし。代役のサーバーが応答します | サポート対象。CI が Linux と Windows で実行します |
| `welcome_smoke.py` | インストール済みのローカルページを端から端まで確認します。`start --no-browser`、キーの保存、本物のキャラクターとの 1 回のチャット、ページを再利用する 2 回目の起動、きれいな終了です | インストール済みの `personagent`（`--personagent PATH`）だけ | なし。同じ代役のサーバーが応答します | サポート対象。CI が Linux と Windows で実行します |
| `window_smoke.py` | 一時的なホームで実際のアプリウィンドウを開き、ウィンドウ内でページをセットアップしてチャットしてから、ウィンドウを閉じます | macOS と Linux では、app エクストラ付きでインストールした `personagent`（`pip install "personagent[app]"`）。Linux ではさらに `xvfb-run` などのディスプレイ | なし。同じ代役のサーバーが応答します | サポート対象。CI が Linux、macOS、Windows で実行します |
| `release_notes.py` | リリースタグを `pyproject.toml` と照合し、そのバージョンの CHANGELOG の節を出力します | `v1.1.0` のようなタグ | なし | サポート対象。リリースワークフローが実行します |
| `locale_gaps.py` | `persona_agent/locales/` の言語ごとに、セットアップウィザード、ターミナルのチャット、デモの文のうち翻訳済みの数を出力します。`ja` のような言語コードを付けると、まだ翻訳がなく英語で表示される文を出力します | なし | なし | サポート対象。不足があると `tests/test_locales.py` が失敗します |

実験的なスクリプトは研究と保守のための補助で、廃止予告なしに変更または削除されることがあります。モデルを呼ぶスクリプトは `.env` のアカウントのクレジットを消費します。まず `--help` を読み、`--dry-run` があれば試してください。
