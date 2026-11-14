# personagent のデプロイ

[English](deploy.md) · [简体中文](deploy.zh-CN.md) · [繁體中文](deploy.zh-TW.md) · 日本語 · [한국어](deploy.ko.md) · [Español](deploy.es.md) · [Français](deploy.fr.md) · [Deutsch](deploy.de.md) · [Português (Brasil)](deploy.pt-BR.md) · [Русский](deploy.ru.md)

[はじめに](start.ja.md)と[ユーザーガイド](guide.ja.md)で、最初のチャットまで進めることができます。インストール、[ホームフォルダー](guide.ja.md#インストールとホームフォルダー)、ローカルページでの設定、プラットフォームの接続を扱っています。このガイドでは、本番運用に必要なことと、ボットが黙ったときに確認することを説明します。

## 動く最短の設定

ローカルページ（`personagent`、ターミナルのウィザードなら `personagent init --terminal`）は小さなリクエスト 1 回でキーを確認し、ホームフォルダーに `.env` を書き込みます。チャットにはキーが必要で、`.env.example` は OpenRouter の無料モデルから始めます。

```
LLM_API_KEY=...
LLM_BASE_URL=https://openrouter.ai/api/v1
LLM_MODEL=openrouter/free
```

キーだけを設定した `.env` は `https://api.deepseek.com` と `deepseek-flash` を意味します。ホスト型でもローカル（Ollama、llama.cpp）でも、OpenAI 互換のエンドポイントを指定できます。API アドレスはプロバイダーの文書どおりに貼り付けてください。ルートでも、`.../v1` や `.../api/paas/v4` のようなバージョン付きのベースでもかまいません。`persona.txt` を書くまでは、同梱の `data/persona.example.<lang>.txt` が代わりになります。`PERSONA_NAME` が設定されるまで（セットアップで設定されます）、キャラクターの名前は「bot」です。

ページは `PERSONA_NAME`、`AGENT_LANG`、`CONNECTOR_TOKEN` も書き込みます。ページからつないだプラットフォームには、`.env` にこれ以上何も要りません。認証情報は `<home>/platforms/` に入ります。`direct.json` には personagent が自分でつなぐプラットフォームが、残りは管理下の AstrBot の設定に保存されます。任意の追加項目：

```
ADMIN_IDS=telegram:12345             # the admin's accounts, <platform>:<id>
# QQ through NapCat (OneBot) only
QQ_BOT_ID=...                        # the bot account's number
CONNECTOR_QQ_PLATFORMS=aiocqhttp
```

キーはこのマシンに留まります。選んだモデルプロバイダーには会話が見えます。`.env.example` のそれ以外の項目には動作する既定値があります。`SERVER_HOST` と `SERVER_PORT` は `127.0.0.1:8080`、`QQ_ONEBOT_URL` は空（NapCat の HTTP サーバーなし）で、`ACCESS_GROUPS` が空ならすべてのグループをコネクターに任せます。

## 実行する

`personagent` はローカルページを開きます。ページが開いている間は、エージェント、直接接続のプラットフォームを保持するプロセス、そしてインストールされていれば管理下の AstrBot を動かします。`personagent` をもう一度実行すると、開いているページを再利用します。`personagent up` はブラウザーなしで同じプロセスを起動します。

どちらの場合も、どのように終わっても、それらのプロセスは一緒に終わります。以前にクラッシュして残ったものは次の起動時に止められます。各プロセスのログは `<home>/runtime/desktop/`（`agent.log`、`direct.log`、`astrbot.log`）に書かれます。

ローカルページと `personagent up` は、新しい personagent が出ていないかを多くても 1 日 1 回 pypi.org に尋ねます。出ていれば、チャットビューとターミナルにこのコピーを更新するコマンドが表示されます。リクエストに含まれるのはバージョン番号だけで、`UPDATE_CHECK_ENABLED=false` で確認をオフにできます。

`personagent run` はエージェントだけを起動します。[サービスを実行する](guide.ja.md#サービスを実行する)で説明しています。自分のコネクター（自分で動かす AstrBot、Satori、Matrix）が話しかける場合に使います。`personagent doctor` は設定を確認し、すべての上流サービスを調べます。

**1.0 で名前が変わった設定。** 1.0 で廃止された設定名が残っていると、起動は終了コード 2 で拒否され、それぞれを `OLD -> NEW` と一覧にします。`personagent doctor --fix` は `<home>/.env` の中で名前を変えます。値とコメントは保ち、古いファイルを `.env.bak` に保存し、新しい名前がすでに設定されている古い行はコメントアウトします。`.env` ではなく環境に設定された廃止名は、設定した場所で変更してください。`personagent doctor` は残っている間は 1 で終了し、`--json` は `retired_settings` の下に一覧にします。`HOST`、`PORT`、`LOG_FILE` は `.env` に書かれている場合だけ数えます。

### アクティビティ

[アクティビティ](guide.ja.md#アクティビティ)はローカルページのビューの 1 つです。追加のインストールは不要で、インターネットから何も読み込まず、キーやトークンを表示しません。ローカルページが起動したエージェントサービスの JSON API を読みます。`personagent run` だけの場合は、サービスのログを読み、代わりに `personagent learned` と `personagent memory` を使ってください。`DASHBOARD_ENABLED=false` は API をオフにします。するとビューにその旨が表示され、`personagent doctor` は `activity: off (...)` と出力します。

API はエージェントサービスの `/api/dashboard/` の下にあります。

- `GET conversations` と `GET conversation?id=<chat id>` は、サービスが把握しているチャットと、1 つのチャットの詳細を読みます。`conversations` の各チャットには、`learned`、`observing`（観察中の項目の数）、`latest`（最後に何かが使用され始めた時刻）が含まれます。`conversation` は `learned` と `observing` のリストを返します。観察中の項目には `standing`（段階、まだ足りないもの、キャラクターの理由、除外される日付）が含まれ、使用中の項目には `by`（`reactions`、`character`、`person` のいずれか）と `why` が含まれます。`conversation` は、そのチャットが記憶している内容として、`memories`、`core_note` と `core_at`、`thread`、`episodes`、`removed`、`memory_status` も返します。
- `POST candidates/<id>/promote`、`replace`、`reject`、`rollback`、`restore` は、学習内容に対して人が任意で行う操作です。各操作は `personagent learned` と同じ学習記録に、アクター `dashboard` で記録されます。`restore` は、キャラクターまたは期限によって除外されたもの、およびキャラクターまたは規則によって使用が止められたものを戻します。人が取り消したものや除外したもの、内容の規則が破棄したものはそのままです。`promote` は、ロールバックされた項目を戻しません。
- `POST memory/forget` は、本文 `{"conv": "<chat id>", "kind": "note", "id": "<id>"}` で項目を 1 つ削除し、`tid` を返します。`POST memory/restore`（`{"tid": "<tid>"}`）にこの `tid` を渡すと、項目を戻せます。`kind` は `note`、`episode`、`thread`、`core` のいずれかです。以前の本文 `{"conv": "<chat id>", "note": "<note id>"}` も引き続き使用でき、`note` がなければ、そのチャットのコアノートを削除します。
- `POST memory/forget_chat` は、`{"conv": "<chat id>"}` で、そのチャットが記憶しているすべての内容を削除します。この操作は元に戻せません。
- `GET memory/list?conv=<chat id>` は、各チャットが記憶している内容と、まだ復元できる内容を一覧にします。サービスの実行中は、`personagent memory` がこれを読み取ります。

すべての呼び出しには、ランタイムフォルダー（`AGENT_RUNTIME_DIR` で移さない限り `<home>/runtime/`）の `dashboard.token` にあるトークンを、ヘッダー `X-Personagent-Dashboard-Token` に入れる必要があります。このファイルを読めるのはサービスを実行しているユーザーだけで、サービスは起動時に作成します。ヘッダーのない呼び出しは 401（`dashboard_token`）、誤ったトークンは 403（`wrong_token`）になります。`CONNECTOR_TOKEN` と `X-Personagent-Token` では開けません。これらはコネクターと `/health/details` 専用です。

- 書き込みにはさらに `X-Personagent-Dashboard: 1` と `Content-Type: application/json` が必要です。リクエストが `Origin` を送る場合は、サービス自身のものでなければなりません。
- ブラウザーのクロスサイトリクエストは拒否されます。
- レスポンスではすべての認証情報が `***` に置き換えられます。起動時チェックの URL は、ユーザー名、パスワード、クエリも伏せられます。
- 同じコンピューター上のスクリプトは、ローカルページと同じ方法で API を呼べます。

サービスはページを提供しません。`GET /` はローカルページと `personagent learned` を案内する短い文を返します。古い `?token=` リンクを開いても今はこれが表示されます。ローカルページは 127.0.0.1 にのみバインドします。ローカルページのないサーバーでは、`personagent learned` で、キャラクターが学習した内容と、観察している内容とその理由を確認できます。また、項目を使用状態にする、除外する、取り消す、キャラクターまたは期限によって除外されたものやキャラクターまたは規則によって使用が止められたものを戻す、といった操作ができます。`personagent memory` は、記憶している内容を一覧にし、項目を削除または復元します。

## ホストに必要なもの

1. **書き込めるホーム。** 起動時に `runtime/` の外の `<home>/.personagent.instance.lock` でロックを取ります。読み取り専用のホームでは起動に失敗します。
2. **ホームごとに 1 プロセス。** 同じホームで 2 つ目の `personagent run` を実行すると、その旨を 1 文で伝えて終了します。
3. **空いているポート。** 使用中または禁止されたポートでも 1 文で終了します。`--port` か `SERVER_PORT` で別のポートを選んでください。

`AGENT_RUNTIME_DIR` はホームの下に解決されなければならず、そうでなければ起動に失敗します。相対パスの `PERSONA_FILE` や `PERSONA_CARD_FILE` もホームの下に解決されるので、別の場所に置くペルソナには絶対パスが必要です。

`memory.json`、`core_memory.json`、`episodes.json` のいずれかが破損している場合、起動は終了コード 2 で止まり、そのファイルと、代わりに置く `.bak` コピーを示す 1 文が表示されます。破損したファイルには手を加えません。

## プラットフォームをつなぐ

ローカルページの **プラットフォーム連携** でプラットフォームを追加します。personagent は何かを保存する前に、認証情報をプラットフォームに確認します。プラットフォームが拒否すると、ページに拒否内容が表示され、何も残りません。

ディスプレイのないサーバーでは、personagent が自らつなぐプラットフォームを、ターミナルから `personagent connect <platform>`（たとえば `personagent connect telegram`）で接続します。このコマンドはページと同じ手順と確認を行い、値を同じ形式で保存します。QQ と WeChat はターミナルに QR コードを表示し、Twitch はリンクとコードを表示します。`--no-input` を付け、すべての値をオプションで指定すると、コマンドは何も尋ねず、必須の値がない場合はコード 2 で終了します。その後、`personagent up` が personagent を接続済みのプラットフォームとともに起動します。[コマンドとそのオプション](guide.ja.md#ターミナルでプラットフォームを接続する)はユーザーガイドで説明しています。

**personagent 自身がつなぐもの。** QQ、個人の WeChat、Telegram、Discord、Matrix、Twitch、IRC、Zulip、VK、Stoat は 1 つの「direct」プロセスで動き、AstrBot も NapCat も要りません。読み込めないプラットフォームはスキップされ、ほかのプラットフォームは起動します。表は最初の 4 つを扱います。ほかの 6 つに必要なものと制限は、ユーザーガイドの[一覧](guide.ja.md#personagent-が自らつなぐプラットフォーム)にあります。

| プラットフォーム | すること | 制限 |
|---|---|---|
| QQ（公式ボット） | モバイル版 QQ で QR コードをスキャンします。QQ がボットを作成するか、作成済みのものを選びます。AppID と AppSecret の貼り付けは代替手段です。 | ボットが認証されるまで、QQ が参加を許すのは自分が所有するグループだけです。グループのオーナーがそのグループのボットのプロフィールですべてのメッセージの受信をオンにしない限り、グループでは自分を @ したメッセージだけを受け取ります。それまでは自分から会話に加わることはできません。 |
| 個人の WeChat | WeChat でスキャンします（Tencent の iLink ボット API）。 | 1 対 1 のチャットのみ。WeChat はこの種のボットにグループメッセージを渡しません。 |
| Telegram | @BotFather のトークンを貼り付けます。 | |
| Discord | ボットトークンを貼り付けます。Message Content Intent をオンにしておきます。 | |

**管理下の AstrBot 経由。** ほかのプラットフォームはすべて、personagent が専用の Python 3.12 ランタイムと一緒にダウンロードしてヘッドレスで動かす AstrBot を経由します。ダッシュボードはなく、2 回目のログインも要りません。KOOK、Feishu/Lark（長時間接続）、DingTalk（Stream モード）、Slack（Socket Mode。ガイドのリンクがアプリを事前入力します）、WeCom AI ボット（長時間接続）、Mattermost、Misskey は値を 1 つか 2 つ尋ねます。上級グループには公開アドレスか別のソフトウェアが必要です。WeCom アプリ、WeChat 公式アカウント、QQ Webhook、OneBot v11（NapCat）、Satori です。LINE は提供していません。

どちらの経路でも、接続したプラットフォームは、プラットフォームがボットに届けるすべてのグループと DM に答えます。範囲を絞るには、ページの **返信するグループを限定** を使います（[キャラクターを管理する](#キャラクターを管理する)を参照）。ページはこれを `ACCESS_GROUPS` として保存し、個人チャットには `ACCESS_DM_USERS` が同じ働きをします。どちらかにそのプラットフォームの項目が 1 つでもあると、そのプラットフォームでは列挙した相手にしか返信しません（[personagent 自身の許可リスト](#すでに動かしている-astrbot-を通す)を参照）。ID は `<platform>:<id>` の形で届きます。たとえば `qq_official:<openid>`、`weixin_oc:<id>`、`telegram:<id>`、`discord:<id>` です。QQ 公式ボットに見えるのは QQ 番号ではなく openid です。プラットフォームを直接つなぐと、同じプラットフォームの AstrBot 接続は削除されます。

## キャラクターを管理する

以下はすべてローカルページで行います。設定は **キャラクターと設定** → **詳細設定** にあり、**保存** をクリックすると反映されます。

- **自分を管理者にする。** キャラクターに個人チャットで一度メッセージを送り、**管理者とアクセス** で **最近のチャットから選択** をクリックし、自分のアカウントの横の **自分です** をクリックします。QQ 公式ボットには QQ 番号ではなく openid が見えるため、この方法を使います。
- **一部のグループでだけ返信させる。** 同じ一覧で、残すグループごとに **このグループで返信** にチェックを入れるか、**返信するグループを限定** に ID を入力します。あるプラットフォームのグループを 1 つでも列挙すると、そのプラットフォームのほかのグループでは返信しなくなります。
- **すべての返信を止める。** **その他の設定** の **メッセージに返信** をオフにします。キャラクターは接続を保ったまま、オンに戻すまでどのメッセージにも返信しません。
- **学習したことを取り消す。** **アクティビティ** でチャットを選び、項目の横の **取り消し** をクリックするか、`personagent learned rollback <id>` を実行します。
- **グループから外す。** プラットフォーム側でボットをグループから削除します。**プラットフォーム連携** で切断しても personagent の接続が終わるだけで、ボットはグループのメンバーのままです。
- **外されたとき、制限されたとき。** ボットを外したグループからは何も届かなくなるだけで、再接続は要りません。プラットフォームがボットを禁止したりオフラインにしたりすると、personagent が自らつなぐプラットフォームでは接続が止まり、**プラットフォーム連携** に理由が表示されます。

## すでに動かしている AstrBot を通す

AstrBot、NapCat（OneBot）、Koishi（[Satori コネクター](../integrations/satori/README.ja.md)経由）、Matrix（[Matrix コネクター](../integrations/matrix/README.ja.md)と mautrix ブリッジ経由）は、personagent と連携するサードパーティのブリッジです。personagent が自らつなぐプラットフォームには、どれも必要ありません。

AstrBot は `integrations/astrbot/astrbot_plugin_personagent/` のプラグインを通じて personagent にメッセージを渡します。プラグインは各メッセージを `POST /v1/events` に送り、レスポンスの返信を中継します。personagent のアウトボックスも取得するので（`outbox_enabled`、既定でオン）、プラットフォームがボットに許す場所ではペルソナが先に話せます。表はプラグインの README にあります。管理下の AstrBot にはプラグインが自動で入ります。自分の AstrBot の場合は、一度起動してデータフォルダー（`cmd_config.json`、`plugins/`、`config/` があるフォルダー）を作らせてから、次を実行します。

```
personagent connect astrbot                       # asks, and finds AstrBot's folder itself
personagent connect astrbot <AstrBot data dir>    # asks nothing
```

このコマンドはプラグインを `<data dir>/plugins/` にコピーし、同じ `CONNECTOR_TOKEN` を `.env` とプラグインの設定の両方に書き込みます。プラグインに受け入れ可能な URL（ループバック URL。トンネルを含む。または HTTPS）がすでになければ、`personagent_url` を `http://127.0.0.1:<SERVER_PORT>` に設定します。

別のマシンの AstrBot には、[最新リリース](https://github.com/wangkant/personagent/releases/latest)から `astrbot_plugin_personagent.zip` をダウンロードし、AstrBot のプラグインページの **Install from File** でアップロードします。`connector_token` を personagent の `.env` の `CONNECTOR_TOKEN` に、`personagent_url` を personagent の HTTPS アドレスに設定します（[エンドポイントを公開する](#エンドポイントを公開する)を参照）。

personagent を更新したら、`connect astrbot` を再実行するか、新しい zip をアップロードしてください。AstrBot 4.29 以降はインストール済みのコピーを置き換えます。それより古いバージョンでは先にアンインストールし、**Also delete plugin configuration file** にチェックを入れないでください。

`connect astrbot` のオプション：

- `--qq` は `excluded_platforms` から `aiocqhttp` を外し、`--no-qq` は戻します。どちらもなければ QQ の経路はそのままです。`CONNECTOR_QQ_PLATFORMS` はプラグインの最終的な動作に従います。
- `--platform qq_official|telegram|discord|slack|kook|lark --token <token>` は AstrBot 自身の設定でそのアダプターもオンにします。Slack は `--app-token` も、Lark と QQ は `--app-id` と `--app-secret` も受け取ります。すでにあるアダプター項目はほかの設定（プロキシ、ベース URL、ポーリング）を保ち、新しい認証情報だけを受け取ります。
- `--url https://...` はプラグインの送信先の HTTPS アドレスを設定します。
- `--install` は代わりに管理下の AstrBot をダウンロードし、`--start` はそれを起動します。

初回の実行では許可リストは空のままです。再実行すると、ほかの除外プラットフォームとともに保たれます。

プラグインの既定は拒否です。AstrBot の WebUI で `groups` と、DM 用に `dm_users` を埋めるか、`connect` の質問に答えてください。DM は `dm_users` が空でなくなると転送されます。[プラグインの README](../integrations/astrbot/astrbot_plugin_personagent/README.ja.md)にすべてのキーがあります。管理下の AstrBot は、つないだ各プラットフォームを `<platform>:*` で開きます。プラグインをインストールしたら、AstrBot を再起動するか WebUI でプラグインを再読み込みしてください。personagent 側では：

- `CONNECTOR_TOKEN` は各リクエストを認証します。リクエストは `X-Personagent-Token` ヘッダーと、トークンを鍵とした `timestamp.nonce.body` の HMAC-SHA256 を運び、リプレイ防止が再利用された nonce を拒否します。傍受したリクエストを再送したり改ざんしたりはできません。トークンは署名鍵でもあるので、ログに残さず、漏れたら交換してください。1 台のホストでは任意、ホストをまたぐ場合は必須です。
- `ADMIN_IDS` は管理者のアカウントを `<platform>:<id>`（`telegram:12345`、`discord:4242`）で一覧にします。ID だけ、または `qq:<id>` は QQ 番号です。`ADMIN_NAME` は管理者の名前を設定します。一覧のアカウントはすべて 1 人の人物のもので、グループと DM でより親しいペルソナを受け取り、ボットがグループについて覚えていることを管理でき、1 人で教えることができます。AstrBot 経由では、プラットフォームは AstrBot が表示するアダプター名で、チャットで `/sid` を使うと ID が表示されます。
- `ACCESS_GROUPS` と `ACCESS_DM_USERS` は、同じ `<platform>:<id>` の形で personagent 自身にプラットフォームを制限させます。プラットフォームごとに別々に制限されます。項目のないプラットフォームはコネクターに任され、項目が 1 つでもあればそのプラットフォームは項目だけに制限されます。personagent が拒否したターンは引き受けられずに戻るので、AstrBot 自身のモデルが答えることがあります。

Docker や別のホストの AstrBot については[ユーザーガイド](guide.ja.md#自分で動かすブリッジ)を参照してください。

### NapCat（OneBot）経由の QQ

この経路は公式ボットではなく個人の QQ アカウントを使います。対象のグループには、自分のものではない 2 つ目の QQ アカウントが必要です（[DISCLAIMER.md](DISCLAIMER.ja.md) を参照）。通常は QR コードで、再起動後も続くセッションとして、AstrBot の `aiocqhttp` アダプターにつながった OneBot v11 実装にログインします。[NapCat](https://github.com/NapNeko/NapCatQQ) はテスト済みで、QQ NT デスクトップクライアントに接続します。LLOneBot と Lagrange も OneBot v11 の実装です。

管理下の AstrBot では、ローカルページで **上級** の **OneBot v11（NapCat）** を追加し、NapCat を `ws://127.0.0.1:6199/ws` に向けます。[中国語のガイド](deploy.zh-CN.md)に手順があります。自分の AstrBot では、プラグインの `excluded_platforms` から `aiocqhttp` を外し、`CONNECTOR_QQ_PLATFORMS=aiocqhttp` を設定し（`--qq` で両方できます）、`QQ_BOT_ID` を設定します（`personagent connect astrbot` が尋ねます）。

**ここでは `CONNECTOR_QQ_PLATFORMS` が必須です。** ないと QQ の ID が名前空間付き（`aiocqhttp:123456`）で届き、すべての会話が新しく見えます。記憶、履歴、学習した例は接頭辞なしの ID をキーにしており、学習記録は会話 ID から行 ID を導くので、分かれたものは後から修復できません。

接頭辞なしの ID は QQ の権限を持つので、`ADMIN_IDS`、`ACCESS_GROUPS`、`ACCESS_DM_USERS` の QQ の項目はプラグインの許可リストに重ねて適用されます。QQ の DM は `dm_users` に含まれ、*かつ*管理者か `ACCESS_DM_USERS` の項目からのものでなければなりません。`ACCESS_GROUPS` に QQ グループがあれば、QQ グループは両方に含まれている必要があります。その権限をコネクターに任せられる場合だけ、プラットフォームを `CONNECTOR_QQ_PLATFORMS` に入れてください。

**NapCat の HTTP サーバー**（`QQ_ONEBOT_URL`、既定は空）は、この経路では任意です。personagent は自分からもメッセージを送ります。

- 自発的なメッセージ（`PROACTIVE_ENABLED`、既定でオフ）
- 拒否の 2 分後に尋ねる質問（`REACT_ELICIT_ENABLED`）
- モデル呼び出しが失敗したときにグループに送る言い訳

これらは、プラグインが取得している間はプラグインのアウトボックスを通って戻ります。取得していないときは、URL が設定されていれば `QQ_ONEBOT_URL` に送られます。サーバーが必要なのは、オフライン中に見逃した @ メンションの掃引だけで、`QQ_BOT_ID` も一緒に必要です。掃引は起動時とその後 30 分ごとに動きます。`ACCESS_GROUPS` の QQ グループと前回の再起動以降に動きのあったグループを対象に、1 時間以内の @ メンションを再生します。URL が空なら、`personagent doctor` は OneBot ブリッジを「not configured」と表示します。

**すべてのコネクター経路で失われるもの**（直接接続、AstrBot、その他のコネクター）。戻す設定はありません。

- ビジョンモデルが説明しなかった画像の OCR フォールバック
- NapCat を通じた引用の検索。引用は personagent 自身の最近のメッセージの索引と、コネクターが引用と一緒に送る引用テキストから解決します

新しいスタンプは、QQ と同じくすべての経路で収集されます。対象は、グループに投稿された画像のうち、インラインで届いたもの、またはスタンプとして印が付いたものです。コネクターがリンクとしてだけ送る写真は収集されません。

## 複数のプラットフォーム

各コネクターがプラットフォーム名を付けるので（`telegram:-1001234`、`matrix:!room:example.org`）、複数のコネクターを 1 つの personagent に対して並行して動かせます。direct プロセス、AstrBot、Satori、Matrix はすべて同時に動かせます。1 つのチャットを 2 つのコネクターから入れないでください。すべてのメッセージが 2 回届きます。名前空間付きの ID は接頭辞なしの QQ 番号と衝突しません。

誰も頼んでいないメッセージは、personagent のアウトボックスを取得するコネクターを通じてプラットフォームに届きます。自発的な話しかけ、拒否の後に尋ねる質問、グループでモデル呼び出しが失敗したときの言い訳です。DM の言い訳は、メッセージを運んだリクエストへのレスポンスで返ります。

direct プロセスとここにある 3 つのコネクターは、ボットが先に送ることを許すプラットフォームでアウトボックスを取得します。QQ は公式ボットの自発的なメッセージにレート制限をかけ、相手がオフにすることもできます。自作のコネクターは、イベントと一緒に `connector_id`、`reply_handle`、`"capabilities": ["outbox"]` を送り、`/v1/outbox` をロングポーリングします（[コネクタープロトコル](connectors.ja.md)を参照）。そのようなコネクターがなければ、personagent が話すのはメッセージを運んだリクエストの中だけです。自発ループはその会話を飛ばし、質問と言い訳は送られません。

ローカルページもアウトボックスを取得しますが、対象はページ自身のチャットだけです。アウトボックスを取得しないプログラム（チャットで発言するコーディングアシスタントなど）からのイベントによって、アウトボックスを取得するコネクターがそのチャットを失うことはありません（[コネクタープロトコル](connectors.ja.md#アウトボックスpost-v1outbox)を参照）。

`PROACTIVE_PLATFORMS` は自発ループが先に話せる場所を制限します。`PROACTIVE_PLATFORMS=qq_official` は QQ 公式ボットに、`qq` は NapCat 経由の QQ に限定します。`CONNECTOR_OUTBOX_ENABLED=false` はアウトボックスを完全にオフにします。

アウトボックスなしで DM で先に話すには、自分のスケジューラー（AstrBot プラグインのタスク、cron の項目）が `"proactive": true` を付けた DM イベントを送れます。[アウトボックスなしで先に話す](connectors.ja.md#アウトボックスなしで先に話す)を参照してください。

## エンドポイントを公開する

コネクターと personagent が同じマシンにあるなら、`SERVER_HOST=127.0.0.1` のままにしてください。コンテナが同じマシンとみなされるのは、ホストのネットワーク名前空間かホストネットワークを使う場合だけです。ローカルページと `personagent up` は常に `127.0.0.1` にバインドします。それ以外の場合：

1. `SERVER_HOST=0.0.0.0`（または `--host 0.0.0.0`）と `CONNECTOR_TOKEN` を設定します。トークンなしのネットワークバインドは起動時に拒否されます。`QQ_ONEBOT_SECRET` は必須ではありませんが、なければ非推奨の `/v1/onebot` はネットワークバインドではオフになります。そこへのリクエストはすべて 403 `onebot_disabled` になり、ログに理由が一度記録されます。
2. 前段に HTTPS リバースプロキシかプライベートトンネルを置きます。ここにあるコネクターはすべて、ループバックか、トークンを設定した HTTPS にしか送りません。AstrBot プラグインはそれ以外を `refusing unsafe personagent_url` と記録し、Satori と Matrix のコネクターは起動を拒否します。
3. 署名が本文を含むので、本文を 1 バイトも変えないでください。時計のずれは 5 分以内に保ってください。

認証情報が空の場合、そのエンドポイントは `http://127.0.0.1` か `http://localhost` を直接呼ぶローカルプログラムだけに応じます。次のいずれかがあるリクエストは 403 `non_local_request` になります。

- `Origin` ヘッダー
- `none` 以外の `Sec-Fetch-Site`
- `localhost`、`127.0.0.1`、`::1` 以外の `Host`
- プロキシヘッダー：`X-Forwarded-For`、`Forwarded`、`X-Real-IP`、`CF-Connecting-IP`、`Via`、`X-Forwarded-Host`、`X-Forwarded-Proto`、`X-Forwarded-Port`、`True-Client-IP`、`X-Client-IP`、`X-Original-Forwarded-For`

同じホストのプロキシがこれらを 1 つも付けなければ、ローカルに見えます。1 台のホストでも、プロキシやトンネルを加える前に `CONNECTOR_TOKEN`（`/v1/onebot` を使うなら `QQ_ONEBOT_SECRET` も）を設定してください。

## ヘルスエンドポイント

- `GET /health` は無料で公開されており、何も呼びません。
- `GET /health/details` は上流サービスを調べます（60 秒キャッシュ）。`CONNECTOR_TOKEN` が空ならローカルのリクエストだけに答えます。トークンが設定されていれば、ループバックからでも、一致する `X-Personagent-Token` ヘッダーを持つリクエストに**だけ**答えます。重要な調査が失敗するか実行できないと 503 を返します。重要な調査はチャットモデルと、QQ が直接の OneBot 受信を使う場合（`QQ_BOT_ID` と `QQ_ONEBOT_URL` が設定され、`CONNECTOR_QQ_PLATFORMS` が未設定）の OneBot ブリッジです。
- `personagent doctor [--json]` は同じ調査に設定の確認を加えて実行し、同じ場合に 0 以外で終了します。最後の更新確認から 1 日たっていれば、pypi.org に最新バージョンも尋ねます（`UPDATE_CHECK_ENABLED=false` で省けます）。

## コスト

- **調査はクレジットを消費します。** `personagent doctor` と `/health/details` は、エージェントが処理を送る各モデルに小さなチャット補完を 1 回送ります。対象は、グループとプライベートの返信、ウェブ検索の判断、リアクションの判定（`REACT_LEARN_ENABLED` がオンの間）、自己評価（`EVAL_ENABLED` がオンの間）、ビジョンです。`EMBEDDING_MODEL` があれば埋め込みを 1 回、`TAVILY_API_KEY` があれば Tavily 検索を 1 回送ります。`/health` と設定や学習記録の確認は無料です。
- **モデルの使用量は集計されます。** すべてのモデルへのリクエストは、プロバイダーが報告する使用量をもとに、モデルごと、日ごとに集計されます。プロバイダーが費用を報告する場合は費用も集計されます。`personagent doctor` は本日と過去 7 日間の値を出力し、ローカルページのアプリビューにも同じ値が表示されます。集計ファイルはバックグラウンドで書き込まれます。書き込みは多くても 1 分に 1 回で、終了時にもう 1 回行います。
- **学習と記憶。** キャラクター自身による学習の判断は、1 回ごとに `PROMOTE_JUDGE_MODEL` の呼び出しを 1 回消費し、`PROMOTE_JUDGE_INTERVAL_S` ごとに最大 `PROMOTE_JUDGE_BATCH` 回です。記憶の整理は、チャットの 1 区間ごとに `LLM_JUDGE_MODEL` の呼び出しを 1 回消費し、1 日あたりチャットごとに最大 16 回、すべてのチャットを合わせて `MEMORY_CALLS_PER_DAY`（40）回までです。`PROMOTE_JUDGE_ENABLED=false` と `MEMORY_CALLS_PER_DAY=0` でそれぞれオフになります。
- **`tools/` のスクリプト**はさまざまです。無料のものもモデルを呼ぶものもあります。[tools.md](tools.ja.md) の表に書かれています。
- **`personagent eval`** はケースごとにモデルを呼びます。ただし `memory` スイートは例外で、あらかじめ用意した回答を使ってオフラインで実行されます。ペルソナと学習のスイートには、判定用の 2 つ目のモデル（`BENCH_JUDGE_MODEL`）も必要です。
- **メモリ。** 名前空間付き（QQ 以外）の会話が 256 を超えると、最も長く動きのないアイドル会話がメモリから外され、保留中のリアクションを失います。その会話のまだ整理されていないメッセージは先に整理され、最近のメッセージは、`MEMORY_KEEP_RECENT=false` でない限り `runtime/recent.json` に 72 時間残ります。事実、出来事、コアノート、学習記録は残ります。リクエストの途中の会話は追い出されません。長期記憶は起動時にディスクから読み込まれ、この上限の対象外です。
- **ディスク。** `runtime/` の学習記録（証拠ログと候補ログ）は追記専用で、切り詰められません。`personagent doctor` はどちらかが 50 MB を超えると警告します（`LEDGER_EVIDENCE_WARN_BYTES`、`LEDGER_CANDIDATES_WARN_BYTES`）。記憶のファイルは小さいままです。`recent.json` は直近 72 時間に動きのあったチャットだけを保持し、`memory_trash.jsonl` は削除された項目を最大 30 日間保持します。毎日最初の変更の前に、`memory.json`、`core_memory.json`、`episodes.json` は、同じ名前の末尾に `.bak` を付けたファイルにコピーされます。また、このバージョンの初回起動時には、古い記憶ファイルが `memory.json.pre-v2` として保持されます。**このチャットの記憶を削除** またはチャットで依頼された削除の後は、`.bak` のコピーが現在のファイルから書き直され、`memory.json.pre-v2` からも忘れた内容が取り除かれるため、`runtime/` のどのコピーにもその内容は残りません。ただし、それ以前に作成したバックアップには残ります。ボットが学んだことと記憶していることのすべてが入っているので、`runtime/` をバックアップしてください。

## ボットが黙ったとき

原因は多いものから順に挙げています。ローカルページがエージェントを動かしているなら、[アクティビティ](guide.ja.md#アクティビティ)でメッセージが届いているか、なぜ黙ったかがわかります。サーバーではサービスのログを読み、学習内容には `personagent learned` を使ってください。

1. **何も届いていない。** ローカルページでプラットフォームが接続済みとして表示されているか確認し、`runtime/desktop/direct.log` か `astrbot.log` を読んでください。QQ 公式ボットはグループにいる必要があり、どのグループメッセージを受け取るかは QQ が決めます。個人の WeChat ボットはグループを受け取りません。自分で動かす AstrBot では、プラグインの `groups`（DM には `dm_users` も）を埋め、NapCat なら `excluded_platforms` から `aiocqhttp` を外してください。Satori と Matrix のコネクターには `.env` に独自の許可リストがあります。それぞれの README を参照してください。この場合、チャットはアクティビティに現れません。
2. **エージェントがオフ。** `personagent run` のバナーに `agent: OFF` と理由と対処が表示されます。`LLM_API_KEY` がなければ、ローカルページでキーを追加して（または `LLM_API_KEY` を設定して）再起動してください。`AGENT_ENABLED=false` なら `<home>/.env` で `true` にして再起動してください。それまですべてのイベントは `owned: false` を受け取り、最初のイベントで同じ助言の ERROR 行が 1 行記録されます。
3. **代わりに AstrBot 自身のモデルが答える。** リクエストが失敗した、personagent がメッセージを断った（項目 5）、またはエージェントがオフ（項目 2）のためにプラグインがフォールバックしました。AstrBot のログには `refusing unsafe personagent_url`、`agent refused the request (403): <message>`（または別のステータス。下の表を参照）、`timed out waiting for the agent` が出ます。`timeout_s` はデバウンスとターン内のモデル呼び出しに加え、メッセージが届いたときに考えていたターンの分もカバーする必要があります。1 ターンのモデル呼び出しは、グループでも DM でも合わせて 1.5 × `LLM_TIMEOUT_S` までなので、3 × `LLM_TIMEOUT_S` をそれ未満に保ってください。既定値（420）はエージェントの既定値（3 × 120 = 360 秒）をカバーします。`LLM_TIMEOUT_S` を上げるなら、これも上げてください。
4. **呼ばれていない。** グループでは名前（`PERSONA_NAME`）か @ に答えます。そうでなければ会話がたまるのを待ち（`CHAT_TRIGGER_COUNT`、既定は 30 メッセージ）、それでも見送ることがあります。タイムゾーンの 02:00 から 07:00 までは、呼ばれていないチャットにはほとんど入りません。タイムゾーンは `PERSONA_TZ_OFFSET_HOURS` です。空の場合、`AGENT_LANG` が `zh` か `zh-TW` なら UTC+8、それ以外はこのマシンのオフセットです。起動後、そのプラットフォームの最初のメッセージから 2 分以内に届いたグループメッセージのうち、送信から 10 分以上たって届いたものは未処理分とみなされ、文脈として保持されますが、返信はされません。その旨はサービスのログに記録されます。アクティビティに最近の各ターンの理由が表示されます。同じ判断をオフラインで見るには `personagent chat --trigger 4` を実行してください。
5. **personagent の許可リスト。** `ACCESS_GROUPS` と `ACCESS_DM_USERS` はすべての経路で適用され、接頭辞なし ID の QQ DM にはさらに管理者か項目が必要です。これらが断ったメッセージは引き受けられずに戻るので、AstrBot 経由ならそのモデルが答えることがあります。personagent は拒否した各会話を、拒否した設定とともに INFO で一度記録します。
6. **モデル呼び出しが失敗する。** 拒否されたキー（401 か 403）や残高切れ（402 か割り当て超過）は、プロバイダーのホストと直すべき設定を示す ERROR 行を 1 行記録します。`personagent doctor` を実行してください。各モデルエンドポイントに小さなリクエストを送ってステータスを表示するので、誤った `LLM_BASE_URL` や `LLM_MODEL` もわかります。メインモデルがタイムアウトするか接続が切れ、`LLM_FALLBACK_MODEL` に別のモデルが指定されている場合、呼び出しはすぐに予備モデルに移るため、そのターンは制限時間内に答えられます。OpenRouter の上流での失敗のように、プロバイダーが通常のレスポンスの中で送るエラーは、対応する HTTP エラーと同じように扱われます。モデルが落ちている間、ペルソナは呼ばれるとキャラクターらしい短い言い訳を送ります。会話ごとに 5 分に 1 回までです。アクティビティでは、そのターンは「モデルからの応答なし」と表示されます。
7. **設定のつづり間違い。** 起動ログと `personagent doctor` は、`.env.example` が知らないすべてのキーと、`#` で始まる値を一覧にします。
8. **`.env` の BOM。** 最初の設定の名前に BOM が付いてプロセスに届きません。起動時と `personagent doctor` が報告します。BOM なしの UTF-8 で保存し直してください。
9. **NapCat で `QQ_BOT_ID` が未設定または誤り。** AstrBot 経由では @ メンションは動きますが、見逃したメンションの掃引はこれで照合します。直接の OneBot 受信では @ メンションが認識されません。ボットは問題なく起動し、何も記録せず、答えません。`personagent doctor` は `QQ_BOT_ID` が空でほかの QQ 設定がある場合に警告します。QQ 公式ボットはこれを使いません。
10. **答えるが、学んだことを忘れている。** NapCat の QQ が `CONNECTOR_QQ_PLATFORMS=aiocqhttp` なしで届いているか、`PERSONA_NAME` か `PERSONA_VERSION` が変わって新しいキャラクターになっています。古いキャラクターの昇格済みの内容が丸ごと拒否されるとログが警告します。`persona.txt` の編集は、ページのペルソナ欄でも、新しいキャラクターにはなりません。1 つの `PERSONA_VERSION` の下の改訂は学習の範囲を共有します（`runtime/persona_lineage.json`）。系譜にないペルソナハッシュの下で学んだ行を取り込むには、`personagent learned lineage adopt <hash>` のあと `personagent learned rebuild` を実行します。ハッシュは `personagent learned show <id>` の候補の範囲にあります。`AGENT_LANG` を中国語とほかの言語の間で動かすと、`runtime/` の別の学習ファイルにも切り替わります。

`/v1/events` のエラーを以下に示します。AstrBot プラグインはメッセージを記録し、`code` はクライアントが分岐に使える安定したフィールドです。

| ステータス | `code` | AstrBot のログのメッセージ | 原因 |
|---|---|---|---|
| 403 | `unauthenticated` | authentication required | `CONNECTOR_TOKEN` がなく、呼び出し元がこのマシン上にありません |
| 403 | `non_local_request` | no credential is configured; only local requests accepted | `CONNECTOR_TOKEN` がなく、リクエストがブラウザー、プロキシ、または別のホスト名を経由しています |
| 403 | `invalid_envelope` | invalid, stale, or replayed request envelope | トークン、ヘッダー、署名の欠落や誤り、5 分を超える時計のずれ、再利用された nonce、またはリプレイ防止の満杯（エージェントのログに `connector replay guard full`） |
| 403 | `stale_event` | stale or invalid sent_at | `sent_at` が現在と `CONNECTOR_MAX_EVENT_AGE_S`（24 時間）を超えて異なります。未来の時刻やミリ秒単位のタイムスタンプも該当します |
| 400 | `invalid_schema` | invalid event schema | 必須フィールドの欠落：`platform`、`conversation_type`、`sender_id`、`message_id`、`sent_at`、グループでは `conversation_id` |
| 400 | `client_disconnected` | client disconnected | 呼び出し元が送信中に切断しました |
| 408 | `body_timeout` | request body not received in time | 本文の到着に 30 秒を超えました |
| 413 | `body_too_large` | request body too large | `SERVER_MAX_BODY_BYTES`（8 MB）を超えています。多くの場合はインライン画像が原因です |
| 429 | `capacity_exceeded` | webhook capacity exceeded | 処理中のターンが `CONNECTOR_MAX_INFLIGHT` を超えました。3 秒後に再試行してください |

## 旧方式：直接の OneBot 受信

NapCat の Webhook は今でも `POST /v1/onebot` にイベントを送れ、personagent は `QQ_ONEBOT_URL` を通じて返信します。この経路は非推奨で、1.x の間は残ります。代わりに QQ 公式ボット接続か、`CONNECTOR_QQ_PLATFORMS=aiocqhttp` を付けた AstrBot 経由の NapCat を使ってください。この経路は初回使用時に一度警告し、すべてのレスポンスに `Deprecation: true` を付けます。

AstrBot 経由の NapCat に移るには、ローカルページで OneBot v11（NapCat）を追加するか、自分の AstrBot なら `personagent connect astrbot <AstrBot data dir> --qq` を実行して許可リストを埋めます。NapCat の WebSocket クライアントをそこに向け、NapCat の HTTP クライアントをオフにします（HTTP サーバーは残します）。`CONNECTOR_QQ_PLATFORMS` が ID を保つので、記憶と学習は引き継がれます。

旧方式をまだ動かしている場合：

- [NapCat の文書](https://napneko.github.io/)のとおりに両方向を設定します。送信用に `QQ_ONEBOT_URL` の **HTTP サーバー**と、`http://127.0.0.1:8080/v1/onebot`（`SERVER_HOST`、`SERVER_PORT`）に送る **HTTP クライアント**が必要です。`QQ_ONEBOT_URL` は既定で空なので、`.env` に書いてください。ないとボットは受信しても返信しません。プリフライトと `personagent doctor` は、この経路が設定されているように見え（`QQ_BOT_ID` か `QQ_ONEBOT_SECRET` が設定され、`CONNECTOR_QQ_PLATFORMS` が空）、`QQ_ONEBOT_URL` が空のときに警告します。
- NapCat が別のマシンにあるなら、`QQ_ONEBOT_SECRET` を HTTP クライアントの `secret` に設定してください。さもないと、ポートに届く人なら誰でもイベントを偽造できます。その場合、本文には `x-signature: sha1=<hex>` が必要で（403 `bad_signature`）、5 分を超えてずれたタイムスタンプのイベントは 403 `stale_event` になります。シークレットがなければ、この経路はこのホストのプログラムだけに答え、ネットワークバインドではオフです（403 `onebot_disabled`）。
- 同じアカウントで AstrBot を使うなら、`aiocqhttp` を `excluded_platforms` に残してください。さもないとすべてのメッセージが 2 回届きます。

送信は `curl http://127.0.0.1:3000/get_login_info` で確認します。受信は、グループでボットにメッセージを送りながら personagent のログを見て確認します。
