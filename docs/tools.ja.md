# `tools/` のスクリプト

[English](tools.md) · [简体中文](tools.zh-CN.md) · [繁體中文](tools.zh-TW.md) · 日本語 · [한국어](tools.ko.md) · [Español](tools.es.md) · [Français](tools.fr.md) · [Deutsch](tools.de.md) · [Português (Brasil)](tools.pt-BR.md) · [Русский](tools.ru.md)

`tools/` のスクリプトは、personagent をクローンから動かす人のためのものです。パッケージと一緒にはインストールされず、クローンの `.env` と `runtime/` を読みます。クローンのインタープリターで、リポジトリのルートから実行します。

```bash
.venv/bin/python tools/<script>.py --help     # Windows: .venv\Scripts\python.exe
```

日常の作業はスクリプトではなく `personagent` のサブコマンドで行います。`personagent doctor`、`personagent learned`、`personagent eval` です。プロンプトの変更を試すには `personagent chat`、測るには `personagent eval` を使います。`personagent eval --suite memory` はスクリプト化された整理の回答を使ってオフラインで実行され、言語ごとに 21 のケースがあり、キーは要りません。このバージョンでは、すべてのケースが期待どおりに動作します。ほかのスイートはモデルを呼び出します。

| スクリプト | 内容 | 必要なもの | モデル呼び出し | 状態 |
|---|---|---|---|---|
| `import_stickers_folder.py` | 画像のフォルダーをスタンプライブラリに取り込み、1 枚ずつタグを付けます。新しいライブラリが空から始まらずに済みます。`--dry-run` は件数を表示し、`--no-tag` はファイルをコピーするだけです | 画像のフォルダー。タグ付けには `VISION_MODEL`、`VISION_API_KEY`、`VISION_BASE_URL` も必要 | あり。画像 1 枚につきビジョン呼び出し 1 回。`--dry-run` か `--no-tag` なら呼びません | サポート対象 |
| `bootstrap_from_history.py` | 新しいデプロイを QQ グループの履歴から一度だけ立ち上げます。管理者のスタンプとメッセージ長のプロファイルを作り、見つけたスタンプをライブラリに保存します | サードパーティの QQ クライアント NapCat の HTTP サーバー（`QQ_ONEBOT_URL`、必須）と、`ACCESS_GROUPS` か `--group` の QQ グループ | なし。保存したスタンプには、動作中のボットのビジョンモデルが後でタグを付けます | 実験的。QQ と NapCat のみ |
| `sticker_holdout_eval.py` | 手でラベルを付けたスタンプに対して、スタンプ承認ゲートの安定性と精度を測ります | `runtime/holdout.jsonl`（形式は `tools/holdout.example.jsonl`）と 3 つの `VISION_*` 設定 | あり。画像数 × `--runs`（既定 5）回のビジョン呼び出し。30 枚で約 150 回 | 実験的 |
| `package_smoke.py` | インストール済みの `personagent` コマンドを端から端まで確認します。バージョン、`init --no-input`、`chat`、`/health` 付きの `run`、`doctor --json` です | インストール済みの `personagent`（`--personagent PATH`）だけ | なし。代役のサーバーが応答します | サポート対象。CI が Linux と Windows で実行します |
| `welcome_smoke.py` | インストール済みのローカルページを端から端まで確認します。`start --no-browser`、キーの保存、本物のキャラクターとの 1 回のチャット、ページを再利用する 2 回目の起動、きれいな終了です | インストール済みの `personagent`（`--personagent PATH`）だけ | なし。同じ代役のサーバーが応答します | サポート対象。CI が Linux と Windows で実行します |
| `window_smoke.py` | 一時的なホームで実際のアプリウィンドウを開き、ウィンドウ内でページをセットアップしてチャットしてから、ウィンドウを閉じます | macOS と Linux では、app エクストラ付きでインストールした `personagent`（`pip install "personagent[app]"`）。Linux ではさらに `xvfb-run` などのディスプレイ | なし。同じ代役のサーバーが応答します | サポート対象。CI が Linux、macOS、Windows で実行します |
| `release_notes.py` | リリースタグを `pyproject.toml` と照合し、そのバージョンの CHANGELOG の節を出力します | `v1.1.0` のようなタグ | なし | サポート対象。リリースワークフローが実行します |
| `locale_gaps.py` | `persona_agent/locales/` の言語ごとに、セットアップウィザード、ターミナルのチャット、デモの文のうち翻訳済みの数を出力します。`ja` のような言語コードを付けると、まだ翻訳がなく英語で表示される文を出力します | なし | なし | サポート対象。不足があると `tests/test_locales.py` が失敗します |

実験的なスクリプトは研究と保守のための補助で、廃止予告なしに変更または削除されることがあります。モデルを呼ぶスクリプトは `.env` のアカウントのクレジットを消費します。まず `--help` を読み、`--dry-run` があれば試してください。
