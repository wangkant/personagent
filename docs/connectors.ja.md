# コネクタープロトコル

[English](connectors.md) · [简体中文](connectors.zh-CN.md) · [繁體中文](connectors.zh-TW.md) · 日本語 · [한국어](connectors.ko.md) · [Español](connectors.es.md) · [Français](connectors.fr.md) · [Deutsch](connectors.de.md) · [Português (Brasil)](connectors.pt-BR.md) · [Русский](connectors.ru.md)

エージェント自身がチャットプラットフォームと話すことはありません。それはコネクターの仕事です。コネクターは 1 つのプラットフォーム、または多くのプラットフォームを扱うフレームワークにログインし、受信した各メッセージを中立的なイベントに変えて personagent に送り、返ってきたものを届けます。プラットフォーム固有のものはすべてコネクターに留まるので、エージェントはどのプラットフォームからも同じ形式を受け取ります。

このリポジトリには 4 つのコネクターが含まれています。

| コネクター | つながる先 | パス |
|---|---|---|
| 直接接続 | QQ 公式ボット、個人の WeChat（iLink）、Telegram、Discord。ほかのソフトウェアは不要です。ローカルページと `personagent up` は 1 つのプロセス `python -m persona_agent.direct` として動かします。 | `persona_agent/direct/` |
| AstrBot プラグイン | サードパーティのブリッジ AstrBot のプラットフォーム。KOOK、Feishu/Lark、DingTalk、Slack、WeCom、Mattermost、Misskey、OneBot v11 などのために personagent が管理する AstrBot には、プラグインが自動で入ります。すでに動かしている AstrBot には `personagent connect astrbot` で設定します。GitHub Release の `astrbot_plugin_personagent.zip` を AstrBot の「ファイルからインストール」でアップロードし、`connector_token` を自分で設定することもできます。 | `integrations/astrbot/` |
| Satori | すべての Satori 実装（Koishi などサードパーティ）：QQ、Telegram、Discord、KOOK、Lark、DingTalk、LINE、WhatsApp、Matrix、Zulip、メールなど。 | `integrations/satori/` |
| Matrix | Matrix のルーム。さらにサードパーティの mautrix ブリッジ経由で WhatsApp、Signal、Messenger、Instagram、Google Messages など。 | `integrations/matrix/` |

コーディングエージェントはチャットプラットフォームではないので、専用の経路があります。MCP サーバー `personagent mcp` で、[ユーザーガイド](guide.md#coding-agents)で説明しています。

4 つとも、このページで説明するプロトコルを話します。新しいコネクターを書くのに必要なのは、このページと HTTP クライアントです。`integrations/sdk/personagent_connector.py` の Python ヘルパーは、リクエストの署名とアウトボックスのループを代わりに行います。ベース URL、トークン、コネクターの `connector_id` を受け取り、`httpx` が必要です。

## 設定

ローカルページは直接接続のコネクターを設定します。ほかの 3 つは同じ名前を使うので、1 つの設定はどれでも同じ意味です。

| 意味 | Satori | Matrix | AstrBot プラグインのキー |
|---|---|---|---|
| personagent のベース URL（例：`http://127.0.0.1:8080`）。コネクターが `/v1/events` と `/v1/outbox` を付け足します。 | `PERSONAGENT_URL` | `PERSONAGENT_URL` | `personagent_url` |
| 共有トークン。エージェントの `CONNECTOR_TOKEN` と同じ値 | `CONNECTOR_TOKEN` | `CONNECTOR_TOKEN` | `connector_token` |
| このコネクターの ID（後述の `connector_id`） | `SATORI_CONNECTOR_ID` | `MATRIX_CONNECTOR_ID` | `connector_id` |
| 1 回のリクエストにかけてよい秒数 | `SATORI_TIMEOUT_S` | `MATRIX_TIMEOUT_S` | `timeout_s` |
| アウトボックスを取得する | `SATORI_OUTBOX_ENABLED` | `MATRIX_OUTBOX_ENABLED` | `outbox_enabled` |
| 転送するグループ | `SATORI_GROUPS` | `MATRIX_GROUPS` | `groups` |
| DM を転送する相手 | `SATORI_DM_USERS` | `MATRIX_DM_USERS` | `dm_users` |
| プラットフォームのサーバー | `SATORI_URL` | `MATRIX_URL` | AstrBot 自身の設定 |

グループや DM のリストが空なら、その種類は何も転送しません。`*` はその種類をすべて転送し、イベントに `"prefiltered": false` を付けて、判断をエージェントの `ACCESS_GROUPS` と `ACCESS_DM_USERS` に任せます。残りの設定は各コネクターの README にあります。

## アドレス

personagent はすべての ID を `<platform>:<id>` として保存します。たとえばグループなら `telegram:-1001234`、ユーザーなら `discord:4242` です。`platform` はコネクターが付けたプラットフォーム名で、小文字で `:` を含みません。

QQ は唯一の例外で、互換性のために残しています。ID はそのまま（`123456`）保存され、どの設定でも `qq:123456` は同じ意味です。コネクターが QQ を扱い、学習状態を既存の QQ デプロイと揃えたい場合は、そのプラットフォーム名を `CONNECTOR_QQ_PLATFORMS` に書きます。AstrBot プラグインの QQ アダプターは `aiocqhttp` です。そこに挙げたプラットフォームの ID もそのまま保存されます。

## 認証

以下の 2 つのエンドポイントは同じ方式を使います。エージェントに `CONNECTOR_TOKEN` が設定されていると、すべてのリクエストに 4 つのヘッダーが付きます。

- `X-Personagent-Token`：トークン。
- `X-Personagent-Timestamp`：unix 秒。エージェントの時計と 5 分以上ずれた値は拒否されます。
- `X-Personagent-Nonce`：新しいランダム値。再利用された nonce は拒否されます。
- `X-Personagent-Signature`：`sha256=` に続けて、トークンを鍵とした `timestamp + "." + nonce + "." + body` の 16 進 HMAC-SHA256。

本文は正規化した JSON です。UTF-8、キーはソート、区切りは詰め、非 ASCII はエスケープしません。トークンは署名鍵でもあるので、ログに残さないでください。

トークンがない場合、エージェントは `127.0.0.1` か `localhost` を直接呼ぶローカルプログラムだけを受け付けます。コネクターは、ループバック URL か、トークン付きの HTTPS URL 以外への送信を拒否しなければなりません。

## 受信：`POST /v1/events`

各リクエストは 1 つのメッセージを運び、それへの返信を返します。

```json
{
  "platform": "telegram",
  "conversation_type": "group",
  "conversation_id": "-1001234",
  "sender_id": "42",
  "sender_name": "Alex",
  "bot_id": "7000",
  "message_id": "881",
  "sent_at": 1790320000,
  "addressed": true,
  "text": "Nova, how was your day?",
  "segments": [
    {"type": "text", "text": "Nova, how was your day?"}
  ],
  "connector_id": "astrbot-7f3c",
  "reply_handle": "tg-bot:GroupMessage:-1001234",
  "capabilities": ["outbox", "quote_text"]
}
```

必須フィールドは `platform`、`conversation_type`（`group` か `dm`）、`sender_id`、`message_id`、`sent_at` で、グループではさらに `conversation_id` が必要です。`sent_at` はプラットフォームがメッセージに付けた時刻で、unix 秒です。プラットフォームの生の ID を送ってください。接頭辞はエージェントが付けます。

`addressed` はコネクターが設定します。メッセージがボットにメンションしている、ボットのメッセージに返信している、またはプラットフォーム独自のルールでボット宛てである場合に true です。エージェントはテキスト内の自分の名前にも自分で気づきます。自分のメッセージの引用やボットへの @ は学習できるリアクションとして読むので、ボットへの返信には `addressed` を設定してください。ほかのメンバーのメッセージの引用は、ボットへのリアクションにはなりません。

`sender_id` が `bot_id` と等しいイベントは、ボット自身のメッセージのエコーです。エージェントは読まずに捨てて `{"handled": false, "owned": true, "replies": []}` と答えるので、コネクター自身のボットロジックも静かなままです。こうしたイベントはコネクターでスキップしてください。

セグメントは順番に並びます。

| 種類 | フィールド | 備考 |
|---|---|---|
| `text` | `text` | |
| `mention` | `user_id`, `name` | 誰かへのメンション。`user_id` が `bot_id` と等しければボットへのメンションです。 |
| `image` | `url` または `b64`、`sticker`（真偽値） | `sticker` は画像として送られたスタンプを示します。 |
| `emoji` | `name`, `id` | エージェントには見えないプラットフォームのスタンプやカスタム絵文字。`name` は人が呼ぶときの名前です。 |
| `reply` | `message_id`, `text`, `sender_id`, `sender_name` | このメッセージが引用するメッセージ。プラットフォームが提供するなら必ず `text` を送ってください。 |

それ以外は `(sent a voice message)` や `(sent a file: deck.pdf)` のように、`text` セグメントとして言葉で説明してください。エージェントは未知の種類のセグメントを捨てます。

次の任意フィールドで、エージェントの機能がさらに使えます。

| フィールド | 意味 |
|---|---|
| `connector_id` | このコネクターインスタンスの安定した ID。アウトボックスには必須です。 |
| `reply_handle` | 受信メッセージなしで後からこの会話に届くためにコネクターが必要とするもの。AstrBot の `unified_msg_origin`、Matrix のルーム ID、Satori のログインとチャンネル ID などです。エージェントは中身を解釈せず、会話ごとに保存して、アウトボックスの配信で返します。 |
| `capabilities` | コネクターができること。`outbox` はアウトボックスをポーリングし、自発的に送れることを意味します。`quote_text` は返信セグメントに引用テキストが含まれることを意味します。 |
| `prefiltered` | コネクターが独自の許可リストを適用した場合は `true`（既定）。`false` にするとエージェントのリストが唯一のフィルターになります。 |
| `proactive` | DM イベントを、本人の言葉ではなくコネクターが書いた合図として示します。「アウトボックスなしで先に話す」を参照してください。 |

レスポンスは次のようになります。

```json
{"handled": true, "owned": true, "replies": [
  {"type": "text", "text": "not bad, rained all afternoon", "mention_user_id": "telegram:42"},
  {"type": "image", "b64": "..."}
]}
```

- `replies`：順番に、それぞれ別のメッセージとして送ってください。`mention_user_id` があれば、それはメンションする接頭辞付きの ID です。メンションはプラットフォームのやり方で表示してください。
- `owned`：エージェントがこの会話を引き受けました。true のときは、`replies` が空でもほかのボットロジックに答えさせないでください。ペルソナが黙ることを選んだからです。false のときは、そのメッセージはあなたが扱います。会話がエージェントの許可リストにないか、エージェントがまったく答えられない（`LLM_API_KEY` がない、または `AGENT_ENABLED=false`）かのどちらかです。後者の場合、エージェントのログに原因を示す ERROR 行が 1 行残ります。
- リクエストはそのターンの間続きます。短いデバウンスとすべてのモデル呼び出しの合計です。少なくとも `LLM_TIMEOUT_S × (1 + LLM_MAX_RETRIES)` 秒は待ってください。

## アウトボックス：`POST /v1/outbox`

リクエストへの答えではないメッセージもあります。予定された話しかけ、拒否の後の追加質問、グループでモデルが落ちているときの言い訳などです。エージェントはこれらを会話ごとにキューに入れ、`outbox` を宣言したコネクターが取得します。NAT やファイアウォールの内側のコネクターでも同じように動きます。接頭辞なしの QQ ID で保存された会話（「アドレス」を参照）も、そのコネクターが取得している間はアウトボックスを使います。そうでなければ、`QQ_ONEBOT_URL` が設定されているときに NapCat の HTTP API を通ります。

リクエスト：

```json
{
  "kind": "outbox.pull",
  "connector_id": "astrbot-7f3c",
  "wait_s": 25,
  "max_deliveries": 10,
  "acks": [
    {"delivery_id": "d_5c1f...", "status": "sent", "sent_items": 2}
  ]
}
```

エージェントはキューに何か入るまでリクエストを最大 `wait_s` 秒（上限 30）保持し、それから答えます。

```json
{
  "deliveries": [
    {
      "delivery_id": "d_9a07...",
      "conversation_key": "telegram:-1001234",
      "reply_handle": "tg-bot:GroupMessage:-1001234",
      "platform": "telegram",
      "conversation_type": "group",
      "conversation_id": "-1001234",
      "reason": "proactive",
      "expires_in_s": 300,
      "items": [{"type": "text", "text": "anyone still up?"}]
    }
  ],
  "next_wait_s": 25
}
```

`items` は `replies` と同じ形です。`reason` は `proactive`、`follow_up`、`excuse` のいずれかで、`conversation_type` は `group` か `dm` です。`conversation_key` はエージェントが会話を保存するキーで、DM なら `private:telegram:42` のようになります。`conversation_id` はイベントが運んだ生の ID で、DM ではユーザー ID です。エージェントは各会話で最後に受け入れたイベントの `reply_handle`、`connector_id`、`capabilities` を覚えているので、会話は 1 通送れば到達可能になります。

次の取得の `acks` で各配信を報告してください。

| `status` | 意味 |
|---|---|
| `sent` | すべての項目を送りました。 |
| `partial` | 最初の `sent_items` 項目を送りました。 |
| `failed` | 何も送れませんでした。 |
| `expired` | `expires_in_s` 以内に送信を始められませんでした。 |
| `refused` | コネクターがこの会話をもう許可していません。 |
| `unsupported` | プラットフォームがこの会話に自発的に送れません。 |

ルール：

- **多くても 1 回。** ack がどうなっても、エージェントは配信を 1 回だけ渡し、二度と渡しません。直近の数百の `delivery_id` を保持し、同じものを 2 回送らないでください。
- **順番どおり。** 1 つの会話の配信は受け取った順に送ってください。別の会話は並行して送ってかまいません。
- **ack された配信だけが数えられます。** エージェントは ack のない配信を未送信として扱い、ack されたものだけを送信済みとして記録します。ack は次の取得まで待ちますが、配信を渡してから最大 `expires_in_s` に 60 秒を足した時間までです。バッチを送り終えてから次を取得してください。
- **生存確認。** 90 秒取得していないコネクターはいなくなったとみなされます。再び取得するまでその会話には何もキューに入らず、そのためにキューに入ったものや ack なしで渡されたものは未送信で終わります。バッチを届けたらすぐ再取得してください。その取得でバッチの ack も運びます。
- **`unsupported` は持続します。** この ack の後、イベントが別の `reply_handle` を運んでくるまで、エージェントはその会話のキューへの追加をやめます。
- **本文の種類。** 署名は URL パスを含みません。そのためエージェントは、アウトボックスのエンドポイントへのイベント本文と、イベントのエンドポイントへの `outbox.pull` 本文を、`400` とコード `invalid_schema` で拒否します。イベントは `"kind": "event"` を持てます。それ以外の `kind` を持つイベントは拒否されます。

`code` のない 404 は、エージェントがアウトボックスを提供していないことを意味します。コード `outbox_disabled` の `404` は、運用者が `CONNECTOR_OUTBOX_ENABLED` でオフにしたことを意味します。どちらの場合も、次の取得まで長く待ってください。

## アウトボックスなしで先に話す

ポーリングできないコネクターでも DM を始められます。AstrBot プラグインのタスクや cron のような独自のスケジューラーが、`"proactive": true` を付けた普通の DM イベントを `/v1/events` に送ります。エージェントはテキストをペルソナへの合図（「1 日静かだった。今朝が試験だった」）として読み、500 文字で切り、本人の言葉としては決して保存しません。ターンを決めるのは引き続きエンジンの自発発言の指示で、ペルソナを黙らせることもあります。ペルソナが話せば、返信はレスポンスで返り、スケジューラーが中継します。

このイベントには、コネクターの通常のイベントが持つものがすべて必要です。署名ヘッダー、すべての必須フィールド、その人に対してコネクターが送るのと同じ `platform` と生の `sender_id`、空でないテキスト、毎回新しい `message_id` です。`message_id` が重複したイベントは黙って捨てられます。合図はエージェント自身の話しかけと同じ DM クールダウン（`PROACTIVE_DM_COOLDOWN_S`）に数えられ、本人の活動には数えられません。

必ずこのフラグを設定してください。ないと、エージェントは合図を本人の言葉として保存します。このフラグの付いたグループイベントは引き受けられ（`owned: true` なのでコネクターは自分のボットを静かにします）、読まずに捨てられます。

## 機能と、欠けたときの影響

| 欠けているもの | 影響 |
|---|---|
| `outbox` | 予定された話しかけも追加質問も、グループでのモデル呼び出し失敗時の言い訳もありません。QQ ID は、`QQ_ONEBOT_URL` が設定されて到達可能なら NapCat を通じて受け取ります。DM の言い訳はレスポンスの `replies` で返るので、アウトボックスは不要です。 |
| `quote_text` | エージェントが引用メッセージを理解できるのは、自分でそのメッセージを見た場合だけです。 |
| `reply_handle` | `outbox` がない場合と同じです。 |
| `addressed` の誤り | ペルソナが自分宛てのメッセージを背景の雑談として扱います。 |

## コネクターを書く

1. プラットフォームからメッセージを受け取ります。ボット自身のメッセージと、メッセージではないイベント（参加、取り消し、つつく）はスキップします。
2. 上で説明したイベントを組み立てます。`addressed` はプラットフォーム独自のメンションと返信のルールから設定します。
3. イベントに署名して送ります。`replies` を順番に送り、`owned` が true ならほかのボットロジックを静かにします。
4. プラットフォームが自発的に送れるなら、`connector_id`、`reply_handle`、`capabilities: ["outbox"]` を加え、取得ループを動かします。取得し、各配信を `reply_handle` で届け、次の取得で ack します。

`integrations/sdk/personagent_connector.py` がステップ 3 と 4 を処理します。
