# コネクタープロトコル

[English](connectors.md) · [简体中文](connectors.zh-CN.md) · [繁體中文](connectors.zh-TW.md) · 日本語 · [한국어](connectors.ko.md) · [Español](connectors.es.md) · [Français](connectors.fr.md) · [Deutsch](connectors.de.md) · [Português (Brasil)](connectors.pt-BR.md) · [Русский](connectors.ru.md)

エージェント自身がチャットプラットフォームと話すことはありません。それはコネクターの仕事です。コネクターは 1 つのプラットフォーム、または多くのプラットフォームを扱うフレームワークにログインし、受信した各メッセージを中立的なイベントに変えて personagent に送り、返ってきたものを届けます。プラットフォーム固有のものはすべてコネクターに留まるので、エージェントはどのプラットフォームからも同じ形式を受け取ります。

このリポジトリには 4 つのコネクターが含まれています。

| コネクター | つながる先 | パス |
|---|---|---|
| 直接接続 | QQ 公式ボット、個人の WeChat（iLink）、Telegram、Discord、Matrix、Twitch、IRC、Zulip、VK、Stoat。ほかのソフトウェアは不要です。ローカルページと `personagent up` は 1 つのプロセス `python -m persona_agent.direct` として動かします。 | `persona_agent/direct/` |
| AstrBot プラグイン | サードパーティのブリッジ AstrBot のプラットフォーム。KOOK、Feishu/Lark、DingTalk、Slack、WeCom、Mattermost、Misskey、OneBot v11 などのために personagent が管理する AstrBot には、プラグインが自動で入ります。すでに動かしている AstrBot には `personagent connect astrbot` で設定します。GitHub Release の `astrbot_plugin_personagent.zip` を AstrBot の **Install from File** でアップロードし、`connector_token` を自分で設定することもできます。 | `integrations/astrbot/` |
| Satori | すべての Satori 実装（Koishi などサードパーティ）：QQ、Telegram、Discord、KOOK、Lark、DingTalk、LINE、WhatsApp、Matrix、Zulip、メールなど。 | `integrations/satori/` |
| Matrix | Matrix のルーム。さらにサードパーティの mautrix ブリッジ経由で WhatsApp、Signal、Messenger、Instagram、Google Messages など。 | `integrations/matrix/` |

コーディングアシスタントはチャットプラットフォームではないため、専用の経路を使います。MCP サーバー `personagent mcp` で、[ユーザーガイド](guide.ja.md#コーディングアシスタント)で説明しています。

4 つとも、このページで説明するプロトコルを話します。新しいコネクターを書くのに必要なのは、このページと HTTP クライアントです。`integrations/sdk/personagent_connector.py` の Python ヘルパーは、リクエストの署名とアウトボックスのループを代わりに行います。ベース URL、トークン、コネクターの `connector_id` を受け取り、`httpx` が必要です。完全な例はその [README](../integrations/sdk/README.ja.md) にあります。

## 手元のマシンで試す

```
personagent run --port 8080
curl http://127.0.0.1:8080/health
```

`personagent run` は、下で説明する 2 つのエンドポイントを `127.0.0.1` で提供します。`CONNECTOR_TOKEN` は、起動時のバナーに表示されるホームフォルダーの `.env` から読みます。別のフォルダーを使うには `--home DIR` を指定します。

- `CONNECTOR_TOKEN` が空のとき、エージェントは同じマシン上で `127.0.0.1` か `localhost` を呼ぶプログラムだけを受け付け、それらは認証ヘッダーを送りません。`personagent init` はこれを設定しません。ローカルページ、`personagent up`、`personagent connect astrbot` は、空のときにランダムな値を書き込みます。
- 設定するには、十分に長いランダムな値を `.env` に書きます。たとえば `python -c "import secrets; print(secrets.token_urlsafe(32))"` の出力です。コネクターにも同じ値を渡し、エージェントを再起動してください。
- `GET /health` は `{"status": "ok", "agent_enabled": true}` を返し、費用はかかりません。`"agent_enabled": false` はエージェントが答えられない（`LLM_API_KEY` がない、または `AGENT_ENABLED=false`）ことを意味し、どのイベントにも `owned: false` が返ります。`GET /health/details` はモデルやほかのサービスも確認するため、わずかに費用がかかることがあります。トークンが設定されていれば `X-Personagent-Token` ヘッダーが、設定されていなければ同じマシンからのリクエストであることが必要です。それ以外には `403` とコード `forbidden` が返ります。

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

署名は実際に送られた本文のバイト列を対象とするため、UTF-8 の有効な JSON であれば通ります。正規化した JSON（キーはソート、区切りは詰め、非 ASCII はエスケープしない）を推奨し、同梱のコネクターもそれを送りますが、エージェントは必須としていません。トークンは署名鍵でもあるので、ログに残さないでください。

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

必須フィールドは `platform`、`conversation_type`（`group` か `dm`）、`sender_id`、`message_id`、`sent_at` で、グループではさらに `conversation_id` が必要です。`sent_at` はプラットフォームがメッセージに付けた時刻で、整数の unix 秒です（数字だけの文字列も受け付けます）。キャラクターは各メッセージをこの時刻とともに受け取ります。エージェントの起動後、そのプラットフォームの最初のメッセージから 2 分以内に届いたグループメッセージのうち、届いた時点で 10 分以上前のものは、再起動後に配信された未処理分とみなされ、文脈として保持されますが、返信はされません。その 2 分を過ぎると、古い `sent_at` によってメッセージが差し止められることはないため、時計が遅れているコネクターにも返信します。プラットフォームの生の ID を送ってください。接頭辞はエージェントが付けます。

`addressed` はコネクターが設定します。メッセージがボットにメンションしている、ボットのメッセージに返信している、またはプラットフォーム独自のルールでボット宛てである場合に true です。エージェントはテキスト内の自分の名前にも自分で気づきます。自分のメッセージの引用やボットへの @ は学習できるリアクションとして読むので、ボットへの返信には `addressed` を設定してください。ほかのメンバーのメッセージの引用は、ボットへのリアクションにはなりません。転送されたメッセージの中にあるボットへのメンションはボット宛てではないため、その場合は `addressed` を設定しないでください。

`sender_id` が `bot_id` と等しいイベントは、ボット自身のメッセージのエコーです。エージェントは読まずに捨てて `{"handled": false, "owned": true, "replies": []}` と答えるので、コネクター自身のボットロジックも静かなままです。こうしたイベントはコネクターでスキップしてください。

セグメントは順番に並びます。

| 種類 | フィールド | 備考 |
|---|---|---|
| `text` | `text` | |
| `mention` | `user_id`, `name` | 誰かへのメンション。`user_id` が `bot_id` と等しければボットへのメンションです。キャラクターは ID の代わりに `name` を読むため、`name` を送ってください。`name` は送信者が書いたものではない名前として印が付けられてモデルに届くため、キャラクターを呼ぶことも、コマンドになることもありません。`forward` セグメントの後にあるボットへのメンションは、呼びかけになりません。 |
| `image` | `url` または `b64`、`sticker`（真偽値） | `sticker` は画像として送られたスタンプを示します。`b64` で送られたグループの画像、または `sticker` の印が付いた画像は、スタンプのライブラリーに収集されることがあります。`url` だけで送られた写真は収集されません。 |
| `emoji` | `name`, `id` | エージェントには見えないプラットフォームのスタンプやカスタム絵文字。`name` は人が呼ぶときの名前です。 |
| `media` | `kind`, `name`, `transcript`, `emoji` | エージェントには見えないもの。`kind` は `voice`、`video`、`file`、`photo`（取得できなかった画像）、`sticker` のいずれかです。ファイルには `name` を、プラットフォームが文字起こしした音声メッセージには `transcript` を、スタンプには `emoji` を加えてください。 |
| `forward` | `name` | これより後のセグメントは `name` から転送されたもので、送信者が書いたものではありません。`name` は空でも構いません。そのテキストは転送元の人の言葉として読まれるため、名前で誰かを呼ぶことも、記憶コマンドを実行することもありません。送信者自身のコメントは、`forward` セグメントの前に置くか、別のメッセージとして送ってください。 |
| `reply` | `message_id`, `text`, `sender_id`, `sender_name` | このメッセージが引用するメッセージ。プラットフォームが提供するなら必ず `text` を送ってください。 |

メディアは `media` セグメントとして送り、`(sent a voice message)` のような言葉では送らないでください。言葉で送ると、キャラクターはそれを送信者が入力したものとして読みます。エージェントは未知の種類のセグメントを捨てます。

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

- `replies`：順番に、それぞれ別のメッセージとして送ってください。`mention_user_id` があれば、それはメンションする接頭辞付きの ID です。メンションはプラットフォームのやり方で表示してください。`"reason": "excuse"` が付いた項目は、モデルが失敗したときにキャラクターが DM で送る短いメッセージで、返信ではありません。ほかの項目と同じように送るか、エラーとして扱ってください。
- `owned`：エージェントがこのメッセージを引き受けました。メッセージがエージェントの許可リストを通ったという意味で、その後ペルソナがどう応じるかには関係しません。true のときは、`replies` が空でもほかのボットロジックに答えさせないでください。ペルソナが黙ることを選んだのかもしれないからです。false のときは、エージェントはそのメッセージに関わっていません。会話がエージェントの許可リストにない、またはエージェントがまったく答えられない（`LLM_API_KEY` がない、または `AGENT_ENABLED=false`）のいずれかです。エージェントが答えられない場合、そのログに原因を示す ERROR 行が 1 行残ります。重複した `message_id` は、エージェントが引き受けたものとして扱われます（下の「重複したメッセージ」を参照）。
- `handled`：このリクエスト自身のターンが何かを届けたとき、つまり返信か記憶コマンドの答えを返したときに true です。ログと統計のためのものです。判断は `owned` で行い、`handled` の値にかかわらず `replies` にあるものはすべて送ってください。たとえば excuse は `handled: false` とともに届きます。

コネクターが出会う組み合わせ：

| レスポンス | 状況 | コネクターがすること |
|---|---|---|
| `handled: true`、`owned: true`、返信あり | 通常の返信。 | `replies` を送り、ほかのボットロジックは黙らせます。 |
| `handled: false`、`owned: true`、`replies: []` | ペルソナが黙った。イベントがボット自身のエコーだった。メッセージが後のメッセージのターンにまとめられた（「続けて届いたメッセージ」を参照）。記憶コマンドの答えが後でアウトボックスから届く。`proactive` 付きのグループイベント。`message_id` が重複している（再配信）。 | 何も送らず、ほかのボットロジックは黙らせます。 |
| `handled: false`、`owned: true`、`"reason": "excuse"` 付きの返信が 1 つ | DM でモデルが失敗した。 | それを送るか、エラーとして扱います。 |
| `handled: false`、`owned: false`、`replies: []` | 会話が許可リストにない、またはエージェントが答えられない。 | そのメッセージはあなたが扱います。 |

そのほかのルール：

- **重複したメッセージ。** エージェントは、受け入れた直近 2,000 件のメッセージを、会話を問わず覚えています。キーは `platform`、会話（グループなら `conversation_id`、DM なら `sender_id`）、`message_id` の組で、`CONNECTOR_QQ_PLATFORMS` のプラットフォームでは接頭辞なしの `message_id` です。この一覧はホームフォルダーの `runtime/` に随時、また終了時に保存されるので、再起動後も有効です。もう一度送られたメッセージ（プラットフォームの再配信や、タイムアウト後の再試行など）には、最初のリクエストがまだ処理中でも、すぐに `{"handled": false, "owned": true, "replies": []}` が返ります。これには何も送らないでください。返信は最初のレスポンスにしか入りません。呼び出し側があきらめてもターンは続くので、タイムアウトした場合その返信は失われます。再試行するのではなく、十分な時間を取ってください。許可リストに拒否されたメッセージは覚えられず、もう一度送られると改めて判断されます。
- **続けて届いたメッセージ。** 同じ会話のメッセージが短いデバウンス（2.5 秒。グループでペルソナの名前を呼ぶだけのメッセージの後は 5 秒）のうちに届くと、1 つのターンにまとめられ、まとめて答えられます。進行中のターンの後ろで待っていたメッセージも、同じように次のターンに読み込まれます。返信が入るのは最も新しいメッセージのリクエストだけで、それより前のリクエストはそれぞれ `{"handled": false, "owned": true, "replies": []}` を返します。グループでは、返信の `mention_user_id` はペルソナが答える相手を指します。その人が送ったのは、返信を運ぶリクエストのメッセージではなく、それより前のメッセージかもしれません。記憶コマンドはまとめられません。最後の項目を参照してください。
- リクエストはそのターンが終わるまで続きます。短いデバウンスとモデルにかかる時間の合計です。1 ターンのモデル呼び出しは、グループでも DM でも、再試行も含めて 1.5 × `LLM_TIMEOUT_S` という 1 つの時間枠を分け合います。同じ会話の前のターンがまだ考えている間に届いたメッセージは、そのターンが終わるのを待ってから自分のターンに入ります。少なくとも 3 × `LLM_TIMEOUT_S` 秒（既定では 360 秒）は待ってください。
- 会話のターンがまだ考えている間に届いた記憶コマンド（「remember ...」など）には、そのターンの後で答えます。`outbox` を宣言したコネクターには、すぐに `{"handled": false, "owned": true, "replies": []}` が返り、答えは後で `follow_up` の配信として届きます。`outbox` がなければ、答えはレスポンスで届きます。そのリクエスト自身のレスポンスか、同じ会話で待っている別のリクエストのレスポンスです。そのため、レスポンスにはイベントの送信者以外の人をメンションする返信が含まれることがあります。

## アウトボックス：`POST /v1/outbox`

リクエストへの答えではないメッセージもあります。予定された話しかけ、拒否の後の追加質問、ターンの後ろで待っていた記憶コマンドへの答え、グループでモデルが落ちているときの言い訳などです。エージェントはこれらを会話ごとにキューに入れ、`outbox` を宣言したコネクターが取得します。NAT やファイアウォールの内側のコネクターでも同じように動きます。接頭辞なしの QQ ID で保存された会話（「アドレス」を参照）も、そのコネクターが取得している間はアウトボックスを使います。そうでなければ、`QQ_ONEBOT_URL` が設定されているときに NapCat の HTTP API を通ります。

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

`items` は `replies` と同じ形です。`reason` は `proactive`、`follow_up`、`excuse` のいずれかで、`conversation_type` は `group` か `dm` です。`conversation_key` はエージェントが会話を保存するキーで、DM なら `private:telegram:42` のようになります。`conversation_id` はイベントが運んだ生の ID で、DM ではユーザー ID です。エージェントは各会話で最後に受け入れたイベントの `reply_handle`、`connector_id`、`capabilities` を覚えているので、会話は 1 通送れば到達可能になります。ただし、取得するコネクターを維持するための例外が 1 つあります。`outbox` 機能を持たないコネクターからのイベントは、その機能を持つ別のコネクターが同じ会話について保存した値を置き換えません。したがって、アウトボックスを取得するコネクターは、コーディングアシスタントなどの別のプログラムがその会話で発言した後も、その会話に到達し続けます。同じコネクターからのイベント、または `outbox` を宣言しているコネクターからのイベントは、これまでどおり保存された値を置き換えます。

ローカルページ自体も、`connector_id` が `local-welcome` のアウトボックスコネクターです。ページ自身のチャット宛ての配信だけを受け取り、それをチャットビューに表示します。

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

## エラー

エラーは `{"error": "...", "code": "..."}` で返ります。`code` は変わらないので、分岐にはこれを使ってください。`error` はログを読む人のための文で、表現は変わることがあります。

| ステータス | `code` | エンドポイント | 原因 |
|---|---|---|---|
| 400 | `invalid_schema` | 両方 | 本文が JSON オブジェクトでない。必須フィールドがない、または空。`conversation_type` が `group` でも `dm` でもない。`segments` がリストでない。本文の種類が違う（「本文の種類」を参照）。取得リクエストに使える `connector_id`（128 文字まで）がない、`wait_s` か `max_deliveries` が数値でない、または ack が 1,000 件を超える。 |
| 400 | `client_disconnected` | 両方 | 呼び出し側が本文の送信中に切断した。 |
| 403 | `unauthenticated` | 両方 | `CONNECTOR_TOKEN` がなく、呼び出し側がエージェントと同じマシンにいない。 |
| 403 | `non_local_request` | 両方 | `CONNECTOR_TOKEN` がなく、ローカルのプログラムが送らないヘッダーがリクエストに付いている。`Origin`、`none` 以外の `Sec-Fetch-Site`、`localhost`・`127.0.0.1`・`::1` 以外の `Host`、`X-Forwarded-For` などのプロキシのヘッダーです。 |
| 403 | `invalid_envelope` | 両方 | `CONNECTOR_TOKEN` が設定されていて、トークンかヘッダーがない、または誤っている、署名が一致しない、タイムスタンプが 5 分以上ずれている、nonce が使用済み、またはリプレイ防止の記録が満杯。 |
| 403 | `stale_event` | events | `sent_at` が整数の秒でない、またはエージェントの時計と前後どちらかに `CONNECTOR_MAX_EVENT_AGE_S`（24 時間）を超えてずれている。ミリ秒の値は遠い未来になります。 |
| 404 | `outbox_disabled` | outbox | `CONNECTOR_OUTBOX_ENABLED=false`、またはエージェントが止まっている（`AGENT_ENABLED=false`）。 |
| 408 | `body_timeout` | 両方 | 本文が届くまでに 30 秒を超えた。 |
| 413 | `body_too_large` | 両方 | 本文が `SERVER_MAX_BODY_BYTES`（8,000,000 バイト）より大きい。たいていはインライン画像が原因です。 |
| 429 | `capacity_exceeded` | 両方 | 同時のリクエストが多すぎる。イベントのエンドポイントで `CONNECTOR_MAX_INFLIGHT`（既定 64）を超えるターン、またはアウトボックスで 16 を超える取得。`Retry-After` ヘッダーが待つ秒数を示します。3 秒、アウトボックスでは 5 秒です。 |

パスが違うと `404 {"detail": "Not Found"}`、`GET /v1/events` のようにメソッドが違うと `405 {"detail": "Method Not Allowed"}` が返ります。これらは Web フレームワークが返すもので、`code` はありません。

## アウトボックスなしで先に話す

ポーリングできないコネクターでも DM を始められます。AstrBot プラグインのタスクや cron のような独自のスケジューラーが、`"proactive": true` を付けた普通の DM イベントを `/v1/events` に送ります。エージェントはテキストをペルソナへの合図（「1 日静かだった。今朝が試験だった」）として読み、500 文字で切り、本人の言葉としては決して保存しません。ターンを決めるのは引き続きエンジンの自発発言の指示で、ペルソナを黙らせることもあります。ペルソナが話せば、返信はレスポンスで返り、スケジューラーが中継します。

このイベントには、コネクターの通常のイベントが持つものがすべて必要です。署名ヘッダー、すべての必須フィールド、その人に対してコネクターが送るのと同じ `platform` と生の `sender_id`、空でないテキスト、毎回新しい `message_id` です。`message_id` が重複したイベントは再び処理されず、返信なしの `owned: true` が返ります。合図はエージェント自身の話しかけと同じ DM クールダウン（`PROACTIVE_DM_COOLDOWN_S`）に数えられ、本人の活動には数えられません。

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

`integrations/sdk/personagent_connector.py` がステップ 3 と 4 を処理します。その [README](../integrations/sdk/README.ja.md) では、この 2 つを短いプログラム 1 つで示しています。
