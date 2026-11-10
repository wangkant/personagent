# Satori コネクター

[English](README.md) · [简体中文](README.zh-CN.md) · [繁體中文](README.zh-TW.md) · 日本語 · [한국어](README.ko.md) · [Español](README.es.md) · [Français](README.fr.md) · [Deutsch](README.de.md) · [Português (Brasil)](README.pt-BR.md) · [Русский](README.ru.md)


このコネクターは [personagent](https://github.com/wangkant/personagent) を [Satori](https://satori.chat) サーバーにつなぎます。Satori はクロスプラットフォームのチャットプロトコルです。[Koishi](https://koishi.chat)（`server-satori` プラグイン付き）、Chronocat、LLOneBot などのサーバーがチャットプラットフォームにログインし、このようなクライアントは 1 本の websocket ですべてのログインのすべてのメッセージを受け取ります。そのため、1 つのコネクタープロセスで、サーバーにアダプターがあるすべてのプラットフォームにペルソナを置けます。

Satori と Koishi はサードパーティのソフトウェアです。personagent が自分で接続する QQ、WeChat、Telegram、Discord、Matrix、Twitch、IRC、Zulip、VK、Stoat や、ローカルページが AstrBot 経由で設定するプラットフォームには必要ありません。すでに Koishi を動かしている場合や、Koishi でしか届かないプラットフォームを使いたい場合に、このコネクターを使ってください。

コネクターは許可された各メッセージを中立イベントとしてエージェントの `POST /v1/events` に転送し（[docs/connectors.md](../../docs/connectors.ja.md)）、返信を Satori 経由で送り返します。エージェントのアウトボックスも取得するので、予定された話しかけ、追加の質問、言い訳もチャットに届きます。

[satori-python](https://github.com/RF-Tar-Railt/satori-python) が Satori 側（websocket、ログイン一覧、HTTP API）を担当します。このコネクターは Satori と personagent のイベント形式を変換し、署名とアウトボックスのループには [`integrations/sdk/personagent_connector.py`](../sdk/personagent_connector.py) を使います。

## セットアップ（Koishi の場合）

1. **Koishi。** デスクトップランチャーまたは `npm init koishi@latest` で Koishi をインストールします。コンソールで `adapter-telegram` や `adapter-discord` などプラットフォームのアダプターを追加して設定し、ボットがオンラインであることを確認します。`server` と `server-satori` プラグインを有効にします。すると Koishi は `http://127.0.0.1:5140/satori` で Satori を提供します。このマシン以外からそのポートに届く場合は、`server-satori` に `token` を設定してください。

   Koishi はほかのプラグインも動かし続けます。チャットモデルや返信プラグインなど、メッセージに答えるものがあると、ペルソナと一緒に返信し、コネクターではそれを止められません。そのプラグインを無効にするか、転送する会話の対象外にしてください。

2. **エージェント。** personagent を実行します（`personagent run`、README を参照）。コネクターとエージェントが別のホストにある場合は、エージェントの `.env` に `CONNECTOR_TOKEN` を設定し、エージェントを HTTPS の背後に置きます。1 台のホストでも、プロキシやトンネルを追加する前にトークンを設定してください。

3. **コネクター。** コネクターはこのリポジトリのスクリプトなので、リポジトリのコピー（クローンまたは GitHub の ZIP）と専用の Python 環境が必要です。`satori-python` は personagent の依存関係ではないためです。personagent の `.venv` があるクローンでは、その環境にインストールします。

   ```bash
   .venv/bin/python -m pip install -r integrations/satori/requirements.txt
   ```

   PyPI から pip で personagent をインストールした場合や uvx で実行している場合は、コピーの隣に別の venv を作ります。

   ```bash
   python -m venv connector-venv
   connector-venv/bin/python -m pip install -r integrations/satori/requirements.txt
   ```

   Windows のインタープリターは `.venv\Scripts\python.exe` または `connector-venv\Scripts\python.exe` です。次に設定ファイルをコピーします。

   ```bash
   cp integrations/satori/.env.example integrations/satori/.env
   ```

   `integrations/satori/.env` に、Satori サーバーの URL とトークン、エージェントのベース URL と `CONNECTOR_TOKEN`、転送する会話（[許可リスト](#許可リスト)を参照）を設定します。そして同じインタープリターでコネクターを起動します。

   ```bash
   .venv/bin/python integrations/satori/satori_connector.py
   ```

   `--config FILE` で別の設定ファイルを読みます。どの設定も環境変数で指定でき、環境変数はファイルより優先されます。

4. **動作の確認。** サーバーにある各ボットについて、ログに `Satori login telegram:7000 is ONLINE` のような行が出ます。転送するグループでボットをメンションします。エージェントのログにそのターンが出て、返信がチャットに現れます。何も起きなければ `SATORI_LOG_LEVEL=DEBUG` を設定してください。

## 設定

| 設定 | デフォルト | 意味 |
|---|---|---|
| `SATORI_URL` | `http://127.0.0.1:5140/satori` | Satori サーバー。末尾の `/v1` は省略できます。 |
| `SATORI_TOKEN` | | サーバーのトークン（Koishi では `server-satori` → `token`）。 |
| `PERSONAGENT_URL` | `http://127.0.0.1:8080` | エージェントのベース URL。`/v1/events` と `/v1/outbox` が付加されます。 |
| `CONNECTOR_TOKEN` | | エージェントの `CONNECTOR_TOKEN`。 |
| `SATORI_GROUPS` | | 転送するグループ。チャンネル ID またはギルド ID で、`platform:id` も可。空なら転送なし、`*` ならすべて転送します。 |
| `SATORI_DM_USERS` | | DM を転送する相手。ユーザー ID で、`platform:id` も可。空なら転送なし、`*` ならすべて転送します。 |
| `SATORI_PLATFORMS` | すべて | コネクターをこれらの Satori プラットフォームに限定します。 |
| `SATORI_PLATFORM_NAMES` | `qq=qqbot` | エージェントから見たプラットフォーム名を変更します：`satori_name=name, ...` |
| `SATORI_OUTBOX_ENABLED` | `true` | エージェントのアウトボックスを取得します。 |
| `SATORI_CONNECTOR_ID` | `SATORI_URL` から生成 | エージェント側でのこのコネクターの ID。変えないでください。 |
| `SATORI_TIMEOUT_S` | `420` | 1 ターンにかけられる時間。エージェントの 3 × `LLM_TIMEOUT_S` より大きくしてください。 |
| `SATORI_INLINE_IMAGES_ENABLED` | `false` | URL をエージェントに渡さず、公開画像の URL をコネクターでダウンロードします。 |
| `SATORI_LOG_LEVEL` | `INFO` | |

エージェントの URL はループバックアドレスか、`CONNECTOR_TOKEN` を設定した HTTPS でなければなりません。それ以外ではコネクターは起動を拒否します。`SATORI_TOKEN` が平文の `http` で別のホストに送られる場合、コネクターは警告をログに出します。

## 許可リスト

コネクターはデフォルトで拒否します。リストが空なら何も転送しません。

- グループは Satori のチャンネルです。チャンネル ID またはギルド ID が `SATORI_GROUPS` にあるときに転送されます。そのため Discord や KOOK では、1 つのギルド ID でそのギルドの全チャンネルが許可され、各チャンネルは別々の会話のままです。
- DM は、送信者のユーザー ID が `SATORI_DM_USERS` にあるときに転送されます。
- エントリーには `telegram:-1001234` や `discord:4242` のようにプラットフォームを書け、その場合はそのプラットフォームでのみ一致します。何も付けないエントリーはすべてのプラットフォームで一致します。
- `*` はすべてのグループ（またはすべての DM）を転送し、イベントに `prefiltered: false` を付けます。すると判断はエージェント自身の `ACCESS_GROUPS` と `ACCESS_DM_USERS` に委ねられ、そこにエントリーのないプラットフォームは拒否されます。

Koishi の `inspect` プラグインは、メッセージのプラットフォーム、チャンネル、ギルド、ユーザーの ID を表示します。

## プラットフォーム名と QQ

personagent は ID を `<platform>:<id>` として保存します。プラットフォームは Satori ログインのプラットフォーム（`telegram`、`discord`、`onebot` など）です。手順 4 のログ行に表示されます。特別なケースが 2 つあります。

- **OneBot 経由の QQ**（Koishi の `adapter-onebot`、背後に NapCat や LLOneBot）は QQ 番号を ID に使います。既存の QQ デプロイでエージェントが学んだことを残すには、エージェントの `CONNECTOR_QQ_PLATFORMS` にプラットフォームを追加します（`CONNECTOR_QQ_PLATFORMS=onebot`）。すると ID は NapCat の QQ 番号と同じくそのまま保存され、`ACCESS_GROUPS` と `ACCESS_DM_USERS` の QQ エントリーが適用されます。ID が本当に QQ 番号であるプラットフォームだけにしてください。
- **QQ 公式ボット API**（Koishi の `adapter-qq`）はプラットフォームを `qq` と呼びますが、ID は QQ 番号ではなく openid です。コネクターはプラットフォームを `qqbot` に変更します。`SATORI_PLATFORM_NAMES` でこの変更を上書きできます。personagent は Koishi なしで QQ 公式ボットに自分で接続することもできます。

## 動作するもの

| 機能 | 状況 |
|---|---|
| グループチャットと DM | 対応。DM は `DIRECT` チャンネル、またはギルドのないメッセージです。 |
| 呼びかけの検出（`addressed`） | ボットへの `<at>`（ID で、サーバーが ID を出さないときはボットの名前で）と、ボットのメッセージへの返信。`@all` はメンションではなくテキストとして扱います。 |
| 引用メッセージ | 引用のテキスト、送信者、ID を `<quote>` 要素または `message.quote` から取得します。 |
| 受信画像 | `data:` と `internal:` の画像、および Satori サーバー上の画像はインライン化します。公開 URL はエージェントが取得するよう渡します。プライベートネットワークの URL は `(sent an image)` と記述します。ダウンロードは 1 メッセージ最大 4 枚、各 4 MB です。 |
| スタンプと絵文字 | `<emoji>` と QQ の `<face>` は絵文字として届き、ペルソナはそれが見えないことを知っています。 |
| 音声、動画、ファイル | 言葉で記述します：`(sent a voice message)`、`(sent a video)`、`(sent a file: deck.pdf)`。 |
| 返信 | テキストと `data:` URI の画像を、それぞれ別のメッセージとして少し間を空けて送ります。グループでは、エージェントが求めるメンションは `<at>` になります。 |
| パッシブ返信のプラットフォーム | 返信にはイベントの `referrer` が付きます。QQ 公式ボット API がメッセージに答えるのに必要です。 |
| アウトボックス | 予定された話しかけ、追加の質問、言い訳は、その会話を受け取ったログインを通じてチャンネルに届きます。コネクターは `SATORI_TOKEN` と `CONNECTOR_TOKEN` から導いた鍵で各返信ハンドルに署名し、自分が署名したハンドルにだけ送ります。どちらかのトークンを変えると、会話は次にメッセージを送ってから再び届くようになります。`CONNECTOR_OUTBOX_ENABLED=false` のエージェントは 404 を返し、コネクターは 10 分ごとに再試行します。 |
| 入力中の表示 | なし。Satori には入力中の API がありません。 |
| `owned` | 尊重します：コネクターはほかに何も送りません。Koishi のほかのプラグインは止められません（手順 1 を参照）。 |

プラットフォームの規則は引き続き適用されます。たとえば QQ 公式ボット API はボットが自発的に送れるメッセージを厳しく制限しているので、そこでのアウトボックス配信は `failed` で返ることがあります。

## テスト

`tests/test_satori_connector.py` は satori-python もネットワークもなしで動きます。要素オブジェクト、アカウント、エージェントを模擬します。
