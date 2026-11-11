# astrbot_plugin_personagent

[English](README.md) · [简体中文](README.zh-CN.md) · [繁體中文](README.zh-TW.md) · 日本語 · [한국어](README.ko.md) · [Español](README.es.md) · [Français](README.fr.md) · [Deutsch](README.de.md) · [Português (Brasil)](README.pt-BR.md) · [Русский](README.ru.md)


この [AstrBot](https://github.com/AstrBotDevs/AstrBot) プラグインは、AstrBot を [personagent](https://github.com/wangkant/personagent) につなぎます。許可されたメッセージをエージェントへ転送し、エージェントの返信をチャットへ返します。

## 必要ですか？

QQ、WeChat、Telegram、Discord、Matrix、Twitch、IRC、Zulip、VK、Stoat には必要ありません。personagent が AstrBot なしで直接つなぎます。`personagent` を実行してローカルページを開き、**プラットフォーム連携** で追加するか、ターミナルで `personagent connect <platform>` を実行してください。

このプラグインが必要なのは、AstrBot が会話を運ぶときです。次の 2 つの場合があります。

- **personagent のページで別のプラットフォームを追加する。** KOOK、Feishu/Lark、DingTalk、Slack、WeCom AI ボット、Mattermost、Misskey、**上級** にあるプラットフォームはすべて AstrBot を通ります。ページが AstrBot をダウンロードして実行し、このプラグインも入れるので、ここですることはありません。
- **すでに AstrBot を動かしていて**、独自のプラットフォームやプラグインがある場合。下の手順でプラグインをインストールしてください。

## 何をするか

- AstrBot のすべてのプラットフォームアダプター（Telegram、Discord、Slack、QQ など）からグループメッセージと DM を受け取ります。`excluded_platforms` にあるものは除きます。
- 許可リストのグループと送信者のメッセージを、プラットフォームに依存しないイベントとしてエージェントの `POST /v1/events` へ転送します。誰宛てか、何を引用したか、スタンプ、画像、音声メッセージ、プラットフォームが示す送信時刻など、各プラットフォームをアダプターが届ける形のまま読みます。
- エージェントの返信を、各プラットフォームが求める形で AstrBot 経由で返します。返信にはテキストと画像を含められ、グループチャットではエージェントが求めたときにメンションも付きます。
- エージェントのアウトボックスを取得し、予定された話しかけ、追加の質問、モデルが落ちているときにグループへ投稿する言い訳など、自分から話す内容を届けます。[アウトボックス](#アウトボックス)を参照してください。
- エージェントが会話を引き受けると AstrBot 自身のパイプラインを止めます（`block_default`）。これで AstrBot 内蔵のモデルがペルソナの代わりに答えることはありません。

ペルソナ、記憶、デバウンス、タイピングの再現はすべてエージェント側で動きます。このプラグインは、エージェントの [`docs/connectors.md`](https://github.com/wangkant/personagent/blob/main/docs/connectors.ja.md) が定めるコネクターです。

## 自分の AstrBot にインストールする

AstrBot（データフォルダーができるよう一度は起動したもの）と personagent（`python -m pip install personagent`。README を参照）が必要です。

### personagent のセットアップで

```bash
personagent connect astrbot
```

このコマンドはまず AstrBot のデータフォルダー、つまり `cmd_config.json`、`plugins/`、`config/` があるフォルダーを探します。見つからなければ AstrBot のダウンロードを提案します。次に、AstrBot が Docker で動くか、ボットが参加するチャットプラットフォーム（AstrBot がまだ必要とする場合はそのプラットフォームのトークンも）、グループ、管理者、ボットに DM できる人を尋ねます。NapCat 経由の QQ ではボットアカウントの番号も尋ねます。最後にこのプラグインをコピーし、共有トークンを生成して両側に書き込み、許可リストを書き込みます。`personagent init --terminal` も最後に同じ手順を提案します。

質問を省くにはデータフォルダーを渡します。

```bash
personagent connect astrbot <AstrBot data dir>        # add --qq to route QQ (NapCat) as well
```

この方法だと、初回接続の許可リストは**空**のままで、プラグインの設定で入力します。`personagent connect astrbot --help` には、AstrBot のプラットフォームも有効にするフラグが一覧されています。

このコマンドはいつでも再実行できます。許可リスト、ほかの除外プラットフォーム、プラグインが受け付ける `personagent_url` は保たれます（[エージェントを動かせる場所](#エージェントを動かせる場所)を参照）。プラグインが拒否する `personagent_url` はループバックの既定値に置き換えられます。QQ の経路が変わるのは `--qq` か `--no-qq` を渡したときだけで、エージェントの `CONNECTOR_QQ_PLATFORMS` もそれに従います。質問されたときは現在の許可リストが既定値です。Enter で保持し、`-` を入力すると消去します。

その後 AstrBot を再起動し、エージェントを起動します（[動作を確認する](#動作を確認する)を参照）。

### AstrBot の WebUI から

1. [personagent の最新リリース](https://github.com/wangkant/personagent/releases/latest)から `astrbot_plugin_personagent.zip` をダウンロードします。
2. AstrBot のプラグインページの **Install from File** でアップロードします。
3. `connector_token` を personagent の `.env` の `CONNECTOR_TOKEN` に設定し、下の説明に従って許可リストを入力します。
4. AstrBot が personagent と別のコンピューターで動くなら、`personagent_url` を HTTPS のアドレスにします（[エージェントを動かせる場所](#エージェントを動かせる場所)を参照）。

更新するには、新しいリリースの zip を同じようにアップロードします。AstrBot 4.29 以降はインストール済みのものを置き換えます。それより古いバージョンでは先にプラグインをアンインストールし、**Also delete plugin configuration file** のチェックは外したままにしてください。

### 手作業で

1. このフォルダーを `<AstrBot data dir>/plugins/astrbot_plugin_personagent/` にコピーします。
2. AstrBot を再起動するか、WebUI でプラグインを再読み込みします。AstrBot は `httpx` だけを記した `requirements.txt` をインストールします。
3. WebUI でプラグインの設定を開きます。設定は `<AstrBot data dir>/config/astrbot_plugin_personagent_config.json` に保存されます。
   - ペルソナが参加してよいグループ ID を `groups` に追加します。
   - DM に答えてよい送信者 ID を `dm_users` に追加します。
   - エージェントの `.env` が `CONNECTOR_TOKEN` を設定しているなら、同じ値を `connector_token` に入れます。エージェントが別のホストにあるときは必須です。
   - エージェントが同じホストで既定の `SERVER_PORT=8080` で動くなら、`personagent_url` は既定のままにします。

プラグインは**既定で拒否**です。許可リストが空なら何も転送せず、AstrBot はプラグインがないかのように動きます。ID は AstrBot の表示どおりに書いてください。チャットで `/sid` を送ると確認できます。プレフィックスのない ID はすべてのアダプターに一致します。`qq_official:ID` はそのアダプターだけに一致し、`qq_official:*` はそのアダプターの同じ種類の会話をすべて転送します。

`groups` か `dm_users` の単独の `*` は、すべてのアダプターの同じ種類の会話をすべて転送し、`prefiltered: false` と印を付けます。その場合はエージェント自身の `ACCESS_GROUPS` と `ACCESS_DM_USERS` だけが決めます。そこに項目のないプラットフォームをエージェントは拒否しますが、QQ グループは例外で、`ACCESS_GROUPS` に QQ グループがなければ答えます。

### 動作を確認する

1. `personagent run` でエージェントを起動します。これはサーバーだけを起動します。バナーに `agent: on` と出るはずです。
2. 許可されたグループでボットの名前（エージェントの `PERSONA_NAME`）を呼びます。

返信がなければ、AstrBot のログで `personagent:` の行を探し、次に `personagent run` がバナーの後に出力した内容を読み、[トラブルシューティング](#トラブルシューティング)を参照してください。

## 設定

| キー | 型 | 既定値 | 説明 |
| --- | --- | --- | --- |
| `personagent_url` | string | `http://127.0.0.1:8080` | エージェントのベース URL。プラグインが `/v1/events` と `/v1/outbox` を付けます。ループバックか、`connector_token` を設定した HTTPS でなければなりません。 |
| `connector_token` | string | `""` | 共有シークレット。エージェントの `CONNECTOR_TOKEN` と一致が必要です。ループバック以外の `personagent_url` では必須です。 |
| `timeout_s` | int | `420` | 各試行で待つ秒数。[タイムアウト](#タイムアウト)を参照してください。 |
| `excluded_platforms` | list | `["aiocqhttp"]` | 決して転送しないアダプター名。`aiocqhttp` を除くと QQ（NapCat）がこのプラグインを通ります。[NapCat 経由の QQ](#napcat-経由の-qq) を参照してください。 |
| `groups` | list | `[]` | 転送するグループ ID。空ならどのグループも転送しません。`adapter:ID` か `adapter:*` で項目を 1 つのアダプターに限定します。単独の `*` はすべてのグループをフィルターなしで転送します。 |
| `dm_users` | list | `[]` | DM を転送する送信者 ID。空なら DM を転送しません。`adapter:ID` か `adapter:*` で項目を 1 つのアダプターに限定します。単独の `*` はすべての DM をフィルターなしで転送します。 |
| `block_default` | bool | `true` | エージェントが会話を引き受けたら AstrBot のパイプラインを止めます。 |
| `forward_quoted_text` | bool | `true` | プラットフォームが提供する場合、引用メッセージの本文と作者を id と一緒に送ります。これがオンで `quote_max_chars` が 0 より大きい間、すべてのイベントが `quote_text` 機能を宣言します。 |
| `quote_max_chars` | int | `200` | 送る引用文の最大長。長い引用は切り詰めます。 |
| `max_inline_image_bytes` | int | `4000000` | インラインで送る画像の最大サイズ。エージェントが自分で取得できない画像（Telegram、ローカルファイル、プライベートアドレス）はインラインで送ります。これより大きい画像は `(sent an image)` というメモとして届きます。エージェントの `VISION_MAX_IMAGE_BYTES` より小さくしてください。 |
| `outbox_enabled` | bool | `true` | エージェントのアウトボックスを取得して届けます。[アウトボックス](#アウトボックス)を参照してください。 |
| `outbox_wait_s` | int | `25` | 1 回のアウトボックス取得がエージェント側で待てる時間。最大 30。 |
| `connector_id` | string | `""` | エージェントから見たこの AstrBot の名前。空なら一度生成して保持します。2 台の AstrBot ホストには別々の名前が必要です。 |

### エージェントを動かせる場所

- **同じホスト**、またはホストのネットワーク名前空間を共有するかホストネットワークを使うコンテナー：既定のループバック `personagent_url` のままにします。
- **別のコンテナーやホスト**：HTTPS の `personagent_url` を使い、`connector_token` とエージェントの `CONNECTOR_TOKEN` に同じ空でないシークレットを設定します。AstrBot から見えるループバック URL で終わるプライベートトンネルも使えます。その場合も両側に同じトークンを設定してください。エージェントはプロキシ経由で届いたトークンなしのリクエストを拒否するからです。

プラグインはループバック以外への平文 `http://`（`http://host.docker.internal:8080` など）を、トークンがあっても拒否します。その場合メッセージごとに `refusing unsafe personagent_url` と記録され、AstrBot 自身のモデルが代わりに答えます。

**Docker の AstrBot。** コンテナーの中では `127.0.0.1` はコンテナー自身なので、既定の `personagent_url` はどこにも届きません。選択肢は 2 つです。

- AstrBot にホストネットワークを与える：compose ファイルに `network_mode: host`、または `docker run --network host`。Docker Desktop ではバージョン 4.34 以降で「Enable host networking」を有効にする必要があります。同じ compose ファイルの NapCat コンテナーにもホストネットワークが必要です。
- エージェントを HTTPS の後ろに置き、そのアドレスを `personagent_url` にします（`personagent connect astrbot <dir> --url https://...`）。

エージェントは既定で `127.0.0.1:8080` で待ち受けます。`SERVER_HOST` をループバック以外にすると、`CONNECTOR_TOKEN` がなければ起動を拒否します。エージェントの前にプロキシやトンネルを置く前にトークンを設定してください。1 台のホストでも同じです。

### タイムアウト

各リクエストはエージェントのターンが終わるまで続きます。ターンは短いデバウンスと、すべてのモデル呼び出しと再試行からなります。`timeout_s` が尽きても、エージェントはターンを終えて学んだことを保持しますが、返信は失われ、AstrBot 自身のモデルが代わりにそのメッセージに答えます。

エージェントの 3 × `LLM_TIMEOUT_S` は `timeout_s` より小さく保ってください。1 ターンのモデル呼び出しは再試行も含めて 1.5 × `LLM_TIMEOUT_S` を分け合い、メッセージはまず、届いたときに考えていたターンが終わるのを待ちます。エージェントの既定値（`LLM_TIMEOUT_S=120`）では 360 秒で、既定の `timeout_s` の 420 で足ります。エージェント側で `LLM_TIMEOUT_S` を上げたら `timeout_s` も上げてください。

署名済みリクエストが新しいうちは、プラグインはエージェントの 429 または 500 を最大 2 回再試行し、429 では `Retry-After` に従います。

### `block_default` と会話の所有

エージェントが会話を自分のものと報告すると（`owned: true`）、返信したかどうかに関係なく、プラグインは AstrBot のパイプラインを止めます。これでペルソナが黙るターンに AstrBot 内蔵のモデルが割り込むことはありません。

通信エラー、無効な応答、エージェントが断った会話は AstrBot の通常のパイプラインへ進みます。エージェントの応答に `owned` がなければ、プラグインは代わりに `handled` を使います。

## NapCat 経由の QQ

QQ 公式ボットは personagent が AstrBot なしで直接つなぎます。この節は、NapCat（または別の OneBot v11 実装）で動かす QQ アカウントを AstrBot の `aiocqhttp` アダプターの後ろで使う場合だけを扱います。personagent 自身のページで OneBot v11 を追加すると、`excluded_platforms` から `aiocqhttp` を除き、`CONNECTOR_QQ_PLATFORMS` を設定します。

1. `excluded_platforms` から `aiocqhttp` を除き、QQ グループを `groups` に追加します。
2. エージェントの `.env` に `CONNECTOR_QQ_PLATFORMS=aiocqhttp` と `QQ_BOT_ID`（ボットアカウントの番号）を設定します。
3. 任意：エージェントの `QQ_ONEBOT_URL` を NapCat の HTTP サーバーに設定します。これで取りこぼしたメンションを拾う処理が有効になります。これにも `QQ_BOT_ID` が必要です。自発的なメッセージ、拒否された後の追加の質問、モデルが失敗したときのグループの言い訳は、プラグインが取得している間はこのプラグインの[アウトボックス](#アウトボックス)を通ります。そうでなければ、その URL が設定されている場合に NapCat を直接通ります。
4. NapCat がエージェントの `/v1/onebot` にも投稿しているなら、それを止めてください。この経路は非推奨で、両方動かすとメッセージが 2 回届きます。

`personagent connect astrbot <data dir> --qq` は `excluded_platforms` から `aiocqhttp` を除き、`CONNECTOR_QQ_PLATFORMS` を設定します。フォルダーなしで実行すると `QQ_BOT_ID` も尋ねます。デプロイガイドもこの経路を扱っています：[docs/deploy.md](https://github.com/wangkant/personagent/blob/main/docs/deploy.ja.md#napcatonebot経由の-qq)。

`CONNECTOR_QQ_PLATFORMS=aiocqhttp` を省かないでください。これがないとエージェントは QQ のチャットを `aiocqhttp:` 付きの ID で記録し、プレフィックスなしの QQ ID で学んだことが一致しなくなり、学習記録を後から付け替えることもできません。

QQ の ID はプレフィックスなしのままなので、エージェント自身の QQ 設定がそのまま適用されます。`ACCESS_GROUPS` の QQ の項目がグループを制限し（項目がなければすべての QQ グループ）、DM は `ADMIN_IDS` の管理者か `ACCESS_DM_USERS` の人にだけ答えます。ウィザードは指定された QQ グループをエージェントの `.env` に書き込みます。後で QQ グループを追加するときは `groups` と `ACCESS_GROUPS` の両方に加えるか、`ACCESS_GROUPS` に QQ グループを一切書かないでください。

AstrBot に活発な QQ グループを任せる前に、AstrBot の 2 つの設定を確認してください。どちらもプラグインのハンドラーより先に動きます。

- `platform_settings.rate_limit` は既定で 60 秒に 30 メッセージです。超えたメッセージは捨てられず遅延します。上限を上げるか無効にしてください。
- `content_safety.internal_keywords` は既定でオンで、キーワード一覧に一致するメッセージを捨てます。ペルソナが答えるはずだったものも含みます。一覧を確認してください。

## プラットフォーム

エージェントは 1 つの中立な形式で話し、プラグインは境界で各プラットフォーム自身の仕組みを使って変換します。下の表は AstrBot 4.25.5 のアダプターと照合したものです。

すべてのプラットフォームで：

- 転送するのは人が書いたメッセージだけです。QQ の通知（つつく、取り消し、参加）とリクエスト、Slack の参加やトピック変更はターンになりません。
- 動画、ファイル、音声メッセージは、`(sent a video)`、`(sent a file: deck.pdf)`、`(sent a voice message)` のように、ペルソナが反応できるメモとして届きます。プラットフォームに書き起こしがあれば添えます。
- 引用メッセージは、プラットフォームが提供する場合に本文と作者を伴います（`forward_quoted_text`）。
- アダプターが保持している場合、メッセージの時刻は AstrBot が受け取った時刻ではなくプラットフォーム自身の時刻です。
- 返信はプラットフォームの長さ制限より短く分割し、メンションとエスケープはプラットフォームの数え方で数えます。テキストの画像化は決して行わず、人の呼び方はプラットフォームに合わせます。
- アウトボックスは、プラットフォームが自発的に送れる場合だけ使います。

| プラットフォーム（アダプター） | 動くもの | プラットフォーム自体にできないこと |
| --- | --- | --- |
| OneBot 経由の QQ（`aiocqhttp`） | グループと DM。@ とボットへの返信。アダプターが @ を解決できなかった場合も含みます。顔文字名、ストアスタンプ（`mface`）、スタンプとされた画像。本物の QQ @ と続く半角スペース 1 つでのメンション。長い返信は AstrBot の `forward_threshold` 未満に分割し、まとめ転送カードになりません。アウトボックス。 | Markdown は入力したまま表示されます。 |
| QQ 公式（`qq_official`、`qq_official_webhook`） | ボットを @ したグループメッセージと DM。顔文字は `[表情:name]` になります。返信はアダプターの markdown ではなくプレーンテキストを要求します。 | グループはボットを @ したメッセージしか届けないので、ペルソナは会話を追えません。引用なし、名前なし（openid のみ）、返信でのメンションなし。返信はメッセージから 5 分以内だけ可能なので、アウトボックスはありません。 |
| Telegram（`telegram`） | グループ、トピック（`<chat>#<thread>`）、DM。あらゆる種類のメッセージへのボット宛て返信。アダプターの `/@bot` ウェイクプレフィックスは除きます。スタンプの絵文字と、静止スタンプでは画像。画像はアダプターのボット経由で取得するので、ボットトークンは AstrBot の外に出ません。メンションされたユーザー名は、その人が発言した後は数値 id になります。返信はユーザー名で、ユーザー名のない人には `tg://user` リンクでメンションし、`*` や `_` などは入力したまま表示されます。アウトボックス。 | BotFather のプライバシーモードがオン（既定）だと、グループはコマンド、@メンション、ボットへの返信しか届けません。ペルソナが会話を追えるようオフにしてください。アニメーションと動画のスタンプは見られません。 |
| Discord（`discord`） | チャンネルとスレッドをグループとして、および DM。先頭の `@bot`（アダプターが除く）、ボットのロールへの ping、ボットへの返信はすべてボット宛てです。本文付きの引用。スタンプ。音声と動画の添付はメモとして。メンションは `<@id>` で、`@everyone` と `@here` は無効のままです。返信は 2000 文字で分割します。DM を含むアウトボックス。 | Message Content インテントが必要です。 |
| Slack（`slack`） | チャンネルと DM。ボットのメッセージの下のスレッド返信はボット宛てです。リンクを展開します。メッセージ id は Slack の `ts` です。メンションは `<@id>`。`&`、`<`、`>` をエスケープし、テキストがチャンネルに通知できないようにします。返信は 3000 文字で分割します。アウトボックス。 | スレッド返信に親の本文は付きません。ボットに入力中表示はありません。答えはスレッドではなくチャンネルに出ます（アダプター）。 |
| KOOK（`kook`） | チャンネルと DM。@ とボットが持つロールへの ping。KOOK が含める場合の引用。`(emj)` 絵文字と実際の送信時刻。メンションはテキスト内に置き、ペルソナの文中の `(met)` 形式のタグは無効のままです。アダプターは JPEG base64 しかアップロードしないので、画像はファイルとして送ります。アウトボックス。 | AstrBot のアダプターは、プラグインが見る前に単純な画像、ファイル、音声、動画のメッセージを（カードを除き）捨てます。入力中表示はありません。 |
| Lark / Feishu（`lark`） | グループと DM。@ とボットへの返信（Lark はアプリを送信者とします）。本文付きの引用。スタンプは絵文字として。アウトボックス。 | 「グループの全メッセージを読む」権限がないと @ メッセージしか届きません。返信はすべて答える相手のメッセージを引用し、markdown は描画されます（アダプター）。名前は id のプレフィックスです。 |
| DingTalk（`dingtalk`） | グループと DM。アダプターがローカルファイルとして渡す画像はインラインで送ります。動画はメモとして。アウトボックス。DM はボットに書いた人に届きます。 | グループはボットを @ したメッセージしか届けません。引用なし、返信でのメンションや引用返信もなし。返信はすべて「AstrBot」という題の markdown です（アダプター）。 |
| LINE（`line`） | グループ、ルーム、DM。ボットへの @。引用 id。スタンプのキーワード。1 ターンの吹き出しを 1 回の呼び出しで 5 つずつ送るので、無料の reply token で足ります。アウトボックスはプッシュの枠を消費します。 | LINE は引用本文を送りません。返信でのメンションなし（アダプター）。送信画像には公開 HTTPS の `callback_api_base` が必要です。名前は id のプレフィックスです。 |
| Mattermost（`mattermost`） | チャンネルと DM。ボットへの @。スレッドのルートを引用とします。画像はインライン。その人が発言した後はユーザー名でメンションします。`@channel`、`@all`、`@here` は無効のままです。返信は 4000 文字で分割します。アウトボックス。 | 引用本文にはプラグインが行わない照会が必要です。入力中表示はありません。 |
| Misskey（`misskey`） | チャットの DM とルーム。ルームのメッセージのどこにあっても `@bot` を認識します。その人が発言した後は `@user@host` でメンションし、ペルソナの文中のほかの `@` は無効のままです。返信は 3000 文字で分割します。チャットとルームのアウトボックス。 | ノート（公開投稿）は転送しません。AstrBot がシステムイベントとして扱い、返信が公開されるからです。`unique_session` はルームを壊します（アダプター）。 |
| Satori（`satori`） | Satori バックエンドがブリッジするもの：グループ、DM、@、ボットへの返信、本文付きの引用。ミリ秒のタイムスタンプは秒として読みます。アウトボックス。 | グループ id はギルドなので、ギルドのチャンネルは 1 つの会話を共有します。ブリッジ先のプラットフォームの制限が適用されます。 |
| WebChat（`webchat`） | ダッシュボードのチャットを DM として。引用と画像。アウトボックスはライブで表示するか会話に保存します。 | 1 対 1 のみです。 |
| WeCom アプリ（`wecom`） | DM、画像、書き起こし付きの音声。カスタマーサービスモードは顧客のメッセージだけを実際の送信時刻で転送します。返信はバイト数で分割します。アプリモードのアウトボックスは、AstrBot の起動後に誰かが書いてから使えます。 | DM のみ、引用なし。カスタマーサービスモードは自発的に送れません。Markdown は入力したまま表示されます。 |
| WeCom AI ボット（`wecom_ai_bot`） | グループ（WeCom はボットが @ されたときだけグループメッセージを届けます）と DM。音声、ファイル、動画のメモ。1 ターンを 1 つのストリーミング回答として送ります。 | メッセージへの回答の中でしか返信できないので、アウトボックスもメンションもありません。回答は markdown として描画されます。「@bot」が本文から除かれるよう AstrBot で `wecom_ai_bot_name` を設定してください。 |
| WeChat 公式アカウント（`weixin_official_account`） | DM と書き起こし付きの音声。1 ターンを 1 通のメッセージとして送ります。 | パッシブモードはユーザーのメッセージごとに 1 件の返信を、WeChat の 5 秒の枠内で届けます。残りはユーザーの次のメッセージを待ち、ペルソナが黙るターンではユーザーは待たされます（アダプター）。画像はアクティブモードのみ。アウトボックスなし。 |
| 個人 WeChat（`weixin_oc`） | DM。本文付きの引用。画像はインライン。書き起こし付きの音声。入力中表示。アウトボックス。 | グループなし。再ログイン後は、相手がまた書くまで誰にも届きません。 |
| その他のアダプター | AstrBot が届けるまま転送します。メンションは At として。 | アウトボックスは宣言しません。 |

## アウトボックス

何にも答えていないメッセージがあります。予定された話しかけ、拒否された後の追加の質問、モデルが落ちたときのグループの言い訳です。（DM の言い訳はイベント自体の応答で返ります。）エージェントはこれらをキューに入れ、このプラグインがイベントと同じ署名で `POST <personagent_url>/v1/outbox` から取得するので、エージェントが AstrBot にアクセスする必要はありません。アウトボックスは既定でオンです（`outbox_enabled`）。

- 配信はそれぞれ会話自身の AstrBot セッションを通じて順番に送られ、各メッセージは最大 1 回送られます。
- 配信先は、プラグイン自身が同じ会話のメッセージから得たセッションだけです。これらのセッションは AstrBot のプラグインストアに保存されるので、再読み込みしても残ります。エージェントにイベントを投稿する他のものがアウトボックスを別のチャットへ向けることはできず、プラグインはそうした配信を拒否します。
- プラグインは送信時に許可リストと `excluded_platforms` を再確認し、その後除かれた会話を拒否します。
- 先に話しかけられないプラットフォーム（表を参照）にアウトボックスのメッセージは届きません。プラグインがその会話にアウトボックスを宣言しないからです。
- アウトボックスのないエージェントは 404 を返します。プラグインは 10 分ごとに再度尋ねます。

エージェントはこの AstrBot を `connector_id` で識別します。プラグインが一度生成して保持します。1 つのエージェントと話す 2 台の AstrBot ホストには別々の id が必要です。

## リクエストの認証

`connector_token` を設定すると、すべてのリクエストに 4 つのヘッダーが付きます。

- `X-Personagent-Token`：トークン。
- `X-Personagent-Timestamp`：Unix 秒。
- `X-Personagent-Nonce`：新しいランダム値。
- `X-Personagent-Signature`：`sha256=` に続けて、トークンを鍵とした `timestamp + "." + nonce + "." + body` の 16 進 HMAC-SHA256。

本文は正規化 JSON です。UTF-8、キーはソート、コンパクトな区切り、非 ASCII 文字はエスケープなしです。署名はこの正確なバイト列を対象とするので、プロキシは本文を書き換えてはいけません。エージェントは不正な署名、再利用された nonce、自身の時計と 5 分より離れたタイムスタンプを拒否します。2 つの時計を合わせておいてください。

本文にはアダプター自身のメッセージ時刻も `sent_at` として含まれます。エージェントはこれを別途 `CONNECTOR_MAX_EVENT_AGE_S`（既定 24 時間）と照合するので、新しい署名で再送された古いイベントも拒否されます。アダプターが有効なタイムスタンプを示さないメッセージをプラグインは転送せず、AstrBot が通常どおり処理します。キャラクターは各メッセージをこの時刻とともに受け取ります。AstrBot が再起動後に届ける未処理分のように、届いた時点で 10 分以上前のグループメッセージは、文脈として保持されますが、返信はされません。

## エージェント側の ID

エージェントは転送された各 id に `<platform>:<raw id>`（例：`telegram:12345`）の形でプラットフォームを付けるので、異なるプラットフォームの id が衝突することはありません。`CONNECTOR_QQ_PLATFORMS` のプラットフォームはプレフィックスなしの id のままです。エージェントの `ADMIN_IDS`、`ACCESS_GROUPS`、`ACCESS_DM_USERS` は同じ形式の id を取ります。たとえば `ADMIN_IDS=telegram:12345` は、そのアカウントを Telegram のグループと DM で管理者にします。`ACCESS_GROUPS` か `ACCESS_DM_USERS` に項目があるプラットフォームは、このプラグインの許可リストに加えてエージェントでも制限されます。

## トラブルシューティング

AstrBot のログでプラグインの行は `personagent:` で始まります。

| ログメッセージ | すること |
| --- | --- |
| `refusing unsafe personagent_url` | `personagent_url` が別のホストへの平文 HTTP か、`connector_token` のない HTTPS です。[エージェントを動かせる場所](#エージェントを動かせる場所)を参照してください。 |
| `agent refused the request (403): invalid, stale, or replayed request envelope` | `connector_token` が空かエージェントの `CONNECTOR_TOKEN` と一致しない、2 つの時計が 5 分より離れている、またはプロキシが本文を変更しました。エージェントのログに `connector replay guard full` とあれば、空くのを待ってください。 |
| `agent refused the request (403): stale or invalid sent_at` | メッセージがエージェントの `CONNECTOR_MAX_EVENT_AGE_S` より古いです。通常は AstrBot が溜まった分を届けた後に起きます。 |
| `agent refused the request (403): authentication required` または `... only local requests accepted` | エージェントに `CONNECTOR_TOKEN` がなく、リクエストがローカルではありません。両側に同じトークンを設定してください。 |
| `agent at capacity (429)` | エージェントがすでに `CONNECTOR_MAX_INFLIGHT` 個のターンを実行中で、再試行後もメッセージを断ったので、AstrBot 自身のモデルが答えました。頻繁に起きるなら `CONNECTOR_MAX_INFLIGHT` を上げてください。 |
| `agent rejected the body as too large (413)` | 通常は大きなインライン画像です。エージェントの `SERVER_MAX_BODY_BYTES` を上げてください。 |
| `agent rejected the event schema (400)` | イベントにメッセージ id か送信者 id がない（省くアダプターがあります）か、このプラグインのバグです。ログの行を添えて報告してください。 |
| `timed out waiting for the agent` | [タイムアウト](#タイムアウト)を参照してください。 |
| `dropping event without a valid time the platform sent it` | アダプターがタイムスタンプを示しませんでした。AstrBot がそのメッセージを自分で処理します。 |
| `agent request failed: ...` または `agent request failed (<status>)` | 通常はエージェントが動いていないか `personagent_url` の誤りです。404 はパスの誤りです。`personagent_url` は `/v1/events` なしのベース URL です。500 はエージェントの失敗なので、そのログを確認してください。 |
| `outbox off: ...` | アウトボックスはイベントと同じ `personagent_url` の規則に従います。最初の行を参照してください。 |
| `outbox: agent has no outbox (turned off, or an older version); retrying in 10 minutes` | エージェントの `CONNECTOR_OUTBOX_ENABLED` がオフです。 |
| `outbox: outbox pull refused (403)` または `outbox pull failed: ...` | 原因はイベントと同じです。トークン、時計、またはエージェントが動いていないことです。プラグインは試行の間隔を最大 1 分まで延ばします。 |
| `outbox: no running platform '<id>'` | AstrBot で無効にされたか名前を変えたアダプター宛ての配信です。プラグインはエージェントに失敗として報告します。 |
| `could not store connector_id` | AstrBot のプラグインストアが失敗しました。`connector_id` を自分で設定してください。そうしないと、エージェントには再起動のたびに新しい AstrBot が見えます。 |

AstrBot 自身のモデルが突然別の口調で答えたら、プラグインがエージェントに届いていないか、エージェントが会話を引き受けていません。上の表を確認し、`personagent doctor` を実行してください。ローカルページがエージェントを起動したなら、ページの **アクティビティ** を開き、メッセージが届いたか、ペルソナがなぜ黙ったかを確認します。`personagent run` で起動したならターミナルを読んでください。

エージェント自身のログに、コネクターが `X-Personagent-Token` を送っているのに `CONNECTOR_TOKEN` が空だと出たら、エージェントはトークンを無視しています。エージェントの `.env` に同じ値を設定してください。

QQ、Telegram、Discord、KOOK、QQ 公式、Misskey では、メッセージの時刻は AstrBot が受け取った時刻ではなくプラットフォーム自身の時刻です。AstrBot がエージェントの `CONNECTOR_MAX_EVENT_AGE_S` より長く止まっていると、エージェントは AstrBot が届ける溜まった分を古いものとして拒否します。

## 既知の制限：Telegram のメンション

AstrBot の Telegram アダプターは送信者を数値のユーザー id（`telegram:<numeric id>`）で識別しますが、メッセージ内の `@username` メンションはユーザー名でしか識別しません。プラグインは、その人が AstrBot の起動後に発言していれば、メンションされたユーザー名をその人の数値 id に書き換えます。それまではメンションはユーザー名のままエージェントに届きます。

返信はユーザー名で、ユーザー名のない人には `tg://user` リンクでメンションします。AstrBot の起動後に見ていない人をプラグインはメンションしません。
