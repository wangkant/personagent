# personagent のデプロイ

[English](deploy.md) · [简体中文](deploy.zh-CN.md) · [繁體中文](deploy.zh-TW.md) · 日本語 · [한국어](deploy.ko.md) · [Español](deploy.es.md) · [Français](deploy.fr.md) · [Deutsch](deploy.de.md) · [Português (Brasil)](deploy.pt-BR.md) · [Русский](deploy.ru.md)

[はじめに](start.ja.md)と[ユーザーガイド](guide.ja.md)で、最初のチャットまで進めることができます。インストール、[personagent フォルダー](guide.ja.md#インストールと-personagent-フォルダー)、ローカルページでの設定、プラットフォームの接続を扱っています。このガイドでは、本番運用に必要なことと、ボットが黙ったときに確認することを説明します。

## 動く最短の設定

ローカルページ（`personagent`、ターミナルのウィザードなら `personagent init --terminal`）は小さなリクエスト 1 回でキーを確認し、personagent フォルダーに `.env` を書き込みます。チャットにはキーが必要で、`.env.example` は OpenRouter の無料モデルから始めます。

```
LLM_API_KEY=...
LLM_BASE_URL=https://openrouter.ai/api/v1
LLM_MODEL=openrouter/free
```

この 2 行は省略できません。キーだけを設定した `.env` では、コードの既定値である DeepSeek の `https://api.deepseek.com` と `deepseek-flash` が使われ、OpenRouter にはなりません。ホスト型でもローカル（Ollama、llama.cpp）でも、OpenAI 互換のエンドポイントを指定できます。API アドレスはプロバイダーの文書どおりに貼り付けてください。ルートでも、`.../v1` や `.../api/paas/v4` のようなバージョン付きのベースでもかまいません。`persona.txt` を書くまでは、同梱の `data/persona.example.<lang>.txt` が代わりになります。`PERSONA_NAME` が設定されるまで（セットアップで設定されます）、キャラクターの名前は「bot」です。

ページは `PERSONA_NAME`、`AGENT_LANG`、`CONNECTOR_TOKEN` も書き込みます。ページで連携したプラットフォームには、`.env` にこれ以上何も要りません。認証情報は `<home>/platforms/` に入ります。`direct.json` には personagent が自分でつなぐプラットフォームが、残りは管理下の AstrBot の設定に保存されます。任意の追加項目：

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

ローカルページと `personagent up` は、新しい personagent が出ていないかを多くても 1 日 1 回 pypi.org に尋ねます。出ていれば、チャットビューとターミナルにこのインストールを更新するコマンドが表示されます。リクエストに含まれるのはバージョン番号だけで、`UPDATE_CHECK_ENABLED=false` で確認をオフにできます。

`personagent run` はエージェントだけを起動します。[サービスを実行する](guide.ja.md#サービスを実行する)で説明しています。自分のコネクター（自分で動かす AstrBot、Satori、Matrix）が話しかける場合に使います。`personagent doctor` は設定を確認し、すべての上流サービスを調べます。

**1.0 で名前が変わった設定。** 1.0 で廃止された設定名が残っていると、起動は終了コード 2 で拒否され、それぞれを `OLD -> NEW` と一覧にします。`personagent doctor --fix` は `<home>/.env` の中で名前を変えます。値とコメントは保ち、古いファイルを `.env.bak` に保存し、新しい名前がすでに設定されている古い行はコメントアウトします。`.env` ではなく環境に設定された廃止名は、設定した場所で変更してください。`personagent doctor` は残っている間は 1 で終了し、`--json` は `retired_settings` の下に一覧にします。`HOST`、`PORT`、`LOG_FILE` は `.env` に書かれている場合だけ数えます。

### アクティビティ

[アクティビティ](guide.ja.md#アクティビティ)はローカルページのビューの 1 つです。追加のインストールは不要で、インターネットから何も読み込まず、キーやトークンを表示しません。ローカルページが起動したエージェントサービスの JSON API を読みます。`personagent run` だけの場合は、サービスのログを読み、代わりに `personagent learned` と `personagent memory` を使ってください。`DASHBOARD_ENABLED=false` は API をオフにします。するとビューにその旨が表示され、`personagent doctor` は `activity: off (...)` と出力します。

API はエージェントサービスの `/api/dashboard/` の下にあります。

- `GET conversations` と `GET conversation?id=<chat id>` は、サービスが把握しているチャットと、1 つのチャットの詳細を読みます。`conversations` の各チャットには、`learned`、`observing`（観察中の項目の数）、`latest`（最後に何かが使用され始めた時刻）が含まれます。`conversation` は `learned` と `observing` のリストを返します。観察中の項目には `standing`（段階、まだ足りないもの、キャラクターの理由、除外される日付）が含まれ、使用中の項目には `by`（`reactions`、`character`、`person` のいずれか）と `why` が含まれます。`conversation` は、そのチャットが記憶している内容として、`memories`、`core_note` と `core_at`、`thread`、`episodes`、`removed`、`memory_status` も返します。
- `POST candidates/<id>/promote`、`replace`、`reject`、`rollback`、`restore` は、学習内容に対して人が任意で行う操作です。各操作は `personagent learned` と同じ学習記録に、アクター `dashboard` で記録されます。`restore` は、キャラクターまたは期限によって除外されたもの、およびキャラクターまたは規則によって使用が止められたものを戻します。人が取り消したものや除外したもの、内容の規則が破棄したものはそのままです。`promote` は、ロールバックされた項目を戻しません。
- `POST memory/forget` は、本文 `{"conv": "<chat id>", "kind": "note", "id": "<id>"}` で項目を 1 つ削除し、`tid` を返します。`POST memory/restore`（`{"tid": "<tid>"}`）にこの `tid` を渡すと、項目を戻せます。`kind` は `note`、`episode`、`thread`、`core` のいずれかです。以前の本文 `{"conv": "<chat id>", "note": "<note id>"}` も引き続き使用でき、`note` がなければ、そのチャットの常に保持するメモを削除します。
- `POST memory/forget_chat` は、`{"conv": "<chat id>"}` で、そのチャットが記憶しているすべての内容を削除します。この操作は元に戻せません。
- `GET memory/list?conv=<chat id>` は、各チャットが記憶している内容と、まだ復元できる内容を一覧にします。サービスの実行中は、`personagent memory` がこれを読み取ります。
- `GET memory/evidence?conv=<chat id>&kind=note|episode&id=<id>` は、1 件のメモまたは出来事の根拠となったチャットの記録の行（`lines`。各行に `seq`、`t`、`name`、`self`、`text`）、引用している行の数（`refs`）、記録が有効かどうか（`on`）を返します。`conversation` と `memory/list` では、各メモに `refs` と `checked`（照合で当てはまると確認された最新の日時。未照合は `0`）、各出来事に `refs`、各チャットに `log`（`on`、`days`、`lines`、`first_at`）も含まれます。

すべての呼び出しには、ランタイムフォルダー（`AGENT_RUNTIME_DIR` で移さない限り `<home>/runtime/`）の `dashboard.token` にあるトークンを、ヘッダー `X-Personagent-Dashboard-Token` に入れる必要があります。このファイルを読めるのはサービスを実行しているユーザーだけで、サービスは起動時に作成します。ヘッダーのない呼び出しは 401（`dashboard_token`）、誤ったトークンは 403（`wrong_token`）になります。`CONNECTOR_TOKEN` と `X-Personagent-Token` では開けません。これらはコネクターと `/health/details` 専用です。

- 書き込みにはさらに `X-Personagent-Dashboard: 1` と `Content-Type: application/json` が必要です。リクエストが `Origin` を送る場合は、サービス自身のものでなければなりません。
- ブラウザーのクロスサイトリクエストは拒否されます。
- レスポンスではすべての認証情報が `***` に置き換えられます。起動時チェックの URL は、ユーザー名、パスワード、クエリも伏せられます。
- 同じコンピューター上のスクリプトは、ローカルページと同じ方法で API を呼べます。

サービスはページを提供しません。`GET /` はローカルページと `personagent learned` を案内する短い文を返します。古い `?token=` リンクを開いても今はこれが表示されます。ローカルページは 127.0.0.1 にのみバインドします。ローカルページのないサーバーでは、`personagent learned` で、キャラクターが学習した内容と、観察している内容とその理由を確認できます。また、項目を使用状態にする、除外する、取り消す、キャラクターまたは期限によって除外されたものやキャラクターまたは規則によって使用が止められたものを戻す、といった操作ができます。`personagent memory` は、記憶している内容を一覧にし、項目を削除または復元します。

## サーバー、NAS、Docker で動かす

personagent はディスプレイのないマシンでもよく動きます。それを支えるのは次の 3 つです。ページがパスワードの背後で他のデバイスに応答すること、`personagent service install` で再起動後も動き続けること、そしてイメージで Docker の中ですべてを動かせることです。

### サーバーにゼロから

1. サーバーに personagent をインストールします（[インストールと personagent フォルダー](guide.ja.md#インストールと-personagent-フォルダー)を参照。1 行のインストーラーは SSH 越しでも使えます）。
2. ページのパスワードを設定します。パスワードは 2 回入力し、表示されません。`.env` にはハッシュだけが保存されます。

   ```
   personagent page password
   ```

   キーボードの前に誰もいないサーバーでは、`personagent page password --random` でパスワードを作成し、一度だけ表示できます。
3. 他のデバイスからページにアクセスできるようにします。`<home>/.env` に次を追加します。

   ```
   PAGE_HOST=0.0.0.0
   ```

4. 起動します：`personagent up`。このコンピューター用のリンクと、他のデバイス用のアドレスが表示されます。ポートは `PAGE_PORT` で指定しない限り 8090 です。スマートフォンや別のコンピューターでそのアドレスを開き、サインインして、モデルのキーを貼り付け、プラットフォームを連携します。プラットフォームの QR コードはページに表示されます。キーを保存するとすぐにキャラクターが起動します。
5. 動かし続けます：`personagent service install`。

### 別のデバイスからページを開く

| 設定 | 意味 |
|---|---|
| `PAGE_HOST` | ページが待ち受ける場所。空欄または `127.0.0.1`：これまでどおり、トークン付きのリンクでこのコンピューターからのみ。`0.0.0.0` または `::`：他のデバイスからも。このコンピューターの特定のアドレスも使えます。その場合、ページはリンク用に `127.0.0.1` でも待ち受けます。 |
| `PAGE_PORT` | ページのポート。空欄の場合、ループバックでは空いているポート、それ以外では 8090。 |
| `PAGE_PASSWORD` | 他のデバイスがサインインに使うもの：12 文字以上で、そのうち 5 種類以上が異なる文字。`personagent page password` はハッシュを保存します。環境変数（Docker）からの平文の値も使えます。 |
| `PAGE_ALLOWED_HOSTS` | ページが応答するホスト名（`nas.local` や Tailscale の名前など）。数字で入力したアドレスと、このコンピューター自身の名前は常に使えます。 |

ほかの設定と同様に、環境変数は `.env` より優先されます。`PAGE_HOST`、`PAGE_PORT`、`PAGE_PASSWORD` のいずれかを設定すると、`personagent up` はページも提供します。`personagent up --page` はそれらがなくてもページを提供します。`personagent start --no-browser` の意味は変わりません。リンクを表示して何も開かず、`up` がページを提供している間はそのページのリンクを表示します。

**起動しない場合。** ループバック以外では、パスワードがないか弱すぎるとページは起動しません。どの設定をどう直せばよいかが示され、`personagent doctor` とページのアプリビューにも同じ内容が表示されます。`doctor` にはページの行があり、どこで待ち受けているか、パスワードで保護されているかを示します。

**サインイン。** このコンピューター以外のデバイスにはサインインページが表示されます。正しいパスワードを入力すると、セッション Cookie（HttpOnly、SameSite=Strict、HTTPS の背後では Secure）が発行されます。有効期間は 7 日で、ページ上部の **サインアウト**、パスワードの変更、personagent の再起動のいずれかで終了します。パスワードを誤るたびに 1 秒待たされ、同じアドレスから 15 分以内に 5 回誤ると、そのアドレスは 15 分間締め出されます。パスワードは一定時間で比較され、ログに記録されたり表示されたりすることはありません。ページの API は、ページ自身のヘッダーが付いたセッションだけを受け付け、別のサイトからのリクエスト（`Origin`、`Sec-Fetch-Site`）や許可されていないホスト名へのリクエストを拒否します。そのため、Web ページがセッションを利用したり、独自の名前でページにアクセスしたりすることはできません。

**このコンピューターでは何も変わりません。** ここでトークン付きのリンクを開いたブラウザーは、パスワードなしで入れます。プロキシ経由のリクエストは、このコンピューターからであっても別のデバイスとして扱われます。

**別のデバイスからできないこと。** フォルダーを開く、デスクトップアイコン、サインイン時の起動、アプリのウィンドウのボタン、終了、ページからの更新は、personagent が動作しているコンピューターに対して働くため、別のデバイスではページに表示されず、API も拒否します。バックアップ、復元、リセットは使え、そのファイルはそのコンピューターに保存されます。

### ページに安全にアクセスする

ページは暗号化されていない HTTP で通信します。自分で管理していないネットワークでは、パスワードとセッションが通信途中で読み取られるおそれがあるため、次のいずれかを使ってください。

- **SSH トンネル。** `PAGE_HOST` は空欄のまま、`PAGE_PORT=8090` を設定して `personagent up` を実行します。自分のコンピューターから次を実行します。

  ```
  ssh -L 8090:127.0.0.1:8090 you@server
  ```

  そのうえで、`personagent up` が表示したリンク（`#token=` 付き）を開くか、サーバーで `personagent start --no-browser` を実行してもう一度表示させます。パスワードは不要です。ページから見ると、トンネルはこのコンピューターです。
- **Tailscale または ZeroTier。** どちらもデバイス間の通信を暗号化します。`PAGE_HOST=0.0.0.0`（またはサーバーの Tailscale アドレス）とページのパスワードを設定し、サーバーの Tailscale 名を使う場合はそれを `PAGE_ALLOWED_HOSTS` に追加します。
- **HTTPS のリバースプロキシ**（Caddy、nginx、NAS 独自のもの）。`PAGE_HOST=127.0.0.1` のままにし、ページのパスワードを設定して、公開名を `PAGE_ALLOWED_HOSTS` に記載します。こうすると、プロキシ経由のリクエストにはサインインページが表示され、サーバー自身でのリンクは引き続き使えます。Caddy の場合：

  ```
  personagent.example.com {
      reverse_proxy 127.0.0.1:8090
  }
  ```

  nginx の場合は、ホストとスキームを引き渡します。

  ```
  location / {
      proxy_pass http://127.0.0.1:8090;
      proxy_set_header Host $http_host;
      proxy_set_header X-Forwarded-For $remote_addr;
      proxy_set_header X-Forwarded-Proto $scheme;
  }
  ```

  この場合、すべての呼び出し元がプロキシのアドレスから来ることになるため、誰かがパスワードを 5 回誤ると、全員のサインインが 15 分間停止します。

personagent 自身は TLS の終端もトンネルの作成も行いません。

### 動かし続ける：`personagent service`

```
personagent service install     # サービスを書き込んで起動
personagent service status
personagent service restart     # 更新の後に
personagent service remove
```

`--dry-run` を付けると、実行せずにファイルとコマンドを表示します。サービスは、このインストール自身の Python でこの personagent フォルダーの `personagent up` を実行し、失敗したら再起動して、出力をあなたのユーザーだけが読める `<home>/runtime/desktop/service.log` に書き込みます。`up` が動き続けられない状況ではインストールされません。セットアップが完了していない場合（ページが別のデバイス向けに設定されている場合を除く）、パスワードのないページの場合、コピーが一時的な uvx の下で動いている場合です。

- **Linux：** systemd のユーザーユニット `~/.config/systemd/user/personagent.service`（別の personagent フォルダーでは接尾辞が付きます）で、`systemctl --user enable --now` で有効にします。ユーザーのサービスは、lingering がオンでない限り、ログアウトすると停止し、ログイン時にのみ起動します。`install` は `loginctl enable-linger` を実行し、それが許可されない場合は実行すべき `sudo` コマンドを表示します。lingering がオンなら、サービスは起動時に開始します。終了コード 2（セットアップ未完了、パスワードのないページ、この personagent フォルダーで別の personagent が動作中）の場合は再起動しません。システム全体のサービスはありません。ユーザーユニットはあなたとして動作し、そのほうが安全です。
- **macOS：** LaunchAgent `~/Library/LaunchAgents/com.github.wangkant.personagent.plist` で、`launchctl bootstrap gui/<uid>` で読み込みます。ログインしている間に動作するため、他の人にサービスを提供する Mac では自動ログインをオンにしてください。
- **Windows：** アプリ自身のサインイン時の起動（アプリビューと同じスイッチ）です。サインインすると、personagent が通知領域のアイコンの裏で開きます。失敗しても再起動されず、`restart` は使えません。

### Docker

```
docker compose up -d
docker compose logs personagent      # 初回起動時に作成されたページのパスワード
```

リポジトリの `compose.yaml` は `ghcr.io/wangkant/personagent` を実行し、ページはポート 8090、personagent フォルダーはボリューム `personagent-data`（`/data` にマウント）に置かれます。Compose を使わない場合：

```
docker run -d --name personagent --init --restart unless-stopped \
  -p 8090:8090 -v personagent-data:/data ghcr.io/wangkant/personagent
```

初回の実行：`http://<server>:8090/` を開き、ログに表示されたパスワードでサインインし、モデルのキーを貼り付けてプラットフォームを連携します。QR コードはページに表示されます。イメージは、`PAGE_HOST=0.0.0.0` と `PAGE_PORT=8090` を設定したうえで、特権のないユーザーとして `personagent up` を実行します。自分でパスワードを決めるには、環境変数で `PAGE_PASSWORD` を指定してください。指定しない場合、初回起動時にパスワードが作成され、ハッシュだけが `/data/.env` に保存されて、一度だけ表示されます。ほかの設定も環境変数で指定できます。`docker exec -it personagent personagent page password` でパスワードを変更し、`docker exec personagent personagent doctor` でセットアップを確認します。ポートを `127.0.0.1:8090:8090` とマッピングすると、ページは SSH トンネルか同じホスト上のプロキシからのみ使えるようになります。バインドマウントは、ユーザー 1000 が書き込めるものでなければなりません。

Windows と macOS の Docker Desktop は、公開したポートへのすべての接続を 1 つのゲートウェイアドレスからコンテナーに渡すため、ページからはすべてのデバイスが 1 つに見えます。どのデバイスからでもパスワードを 5 回誤ると、すべてのデバイスのサインインが 15 分間停止します。Linux では、各デバイスが自分のアドレスを保ちます。Docker Desktop では、信頼できないネットワークにポートを出さないでください。`127.0.0.1:8090:8090` として公開して SSH トンネルを使うか、Tailscale 経由でアクセスしてください。

コンテナーにないもの：

- **アプリのウィンドウ、通知領域のアイコン、デスクトップアイコン。** ディスプレイがないため、すべてページで行います。
- **ページからの更新。** イメージは新しいものを取得して更新します：`docker compose pull && docker compose up -d`。更新の通知にもそう表示されます。
- **管理下の AstrBot** は動作します。glibc（イメージは Debian ベース）、書き込み可能な personagent フォルダー（`/data`）、PyPI と GitHub、またはそのミラー（`PERSONAGENT_MIRROR`）への外向きの接続が必要です。ボリュームに数百 MB ダウンロードされます。
- **タイムゾーン。** コンテナーの時計は UTC です。`compose.yaml` または `-e` で `PERSONA_TZ_OFFSET_HOURS`（UTC から進んでいる時間数。`8` や `-5` など）を設定してください。設定しない場合、キャラクターは UTC で時刻を伝え、夜間の静かな時間帯も UTC で判断します。

イメージのヘルスチェックは、ページの `/health` に問い合わせます。イメージはリリースごとに amd64 と arm64 向けに公開され、バージョンと `latest` のタグが付きます。

## ホストに必要なもの

1. **書き込めるホーム。** 起動時に `runtime/` の外の `<home>/.personagent.instance.lock` でロックを取ります。読み取り専用のホームでは起動に失敗します。
2. **ホームごとに 1 プロセス。** 同じホームで 2 つ目の `personagent run` を実行すると、その旨を 1 文で伝えて終了します。
3. **空いているポート。** 使用中または禁止されたポートでも 1 文で終了します。`--port` か `SERVER_PORT` で別のポートを選んでください。

`AGENT_RUNTIME_DIR` はホームの下に解決されなければならず、そうでなければ起動に失敗します。相対パスの `PERSONA_FILE` や `PERSONA_CARD_FILE` もホームの下に解決されるので、別の場所に置くペルソナには絶対パスが必要です。

`memory.json`、`core_memory.json`、`episodes.json` のいずれかが破損している場合、起動は終了コード 2 で止まり、そのファイルと、代わりに置く `.bak` コピーを示す 1 文が表示されます。破損したファイルには手を加えません。

## プラットフォームと連携する

ローカルページの **プラットフォーム連携** でプラットフォームを追加します。personagent は何かを保存する前に、認証情報をプラットフォームに確認します。プラットフォームが拒否すると、ページに拒否内容が表示され、何も残りません。

ディスプレイのないサーバーでは、personagent が直接連携するプラットフォームを、ターミナルから `personagent connect <platform>`（たとえば `personagent connect telegram`）で連携します。このコマンドはページと同じ手順と確認を行い、値を同じ形式で保存します。QQ と WeChat はターミナルに QR コードを表示し、Twitch はリンクとコードを表示します。`--no-input` を付け、すべての値をオプションで指定すると、コマンドは何も尋ねず、必須の値がない場合はコード 2 で終了します。その後、`personagent up` が personagent を接続済みのプラットフォームとともに起動します。[コマンドとそのオプション](guide.ja.md#ターミナルでプラットフォームと連携する)はユーザーガイドで説明しています。

**personagent が直接連携するもの。** QQ、個人の WeChat、Telegram、Discord、Matrix、Twitch、IRC、Zulip、VK、Stoat は 1 つの「direct」プロセスで動き、AstrBot も NapCat も要りません。読み込めないプラットフォームはスキップされ、ほかのプラットフォームは起動します。表は最初の 4 つを扱います。ほかの 6 つに必要なものと制限は、ユーザーガイドの[一覧](guide.ja.md#personagent-が直接連携するプラットフォーム)にあります。

| プラットフォーム | すること | 制限 |
|---|---|---|
| QQ（公式ボット） | モバイル版 QQ で QR コードをスキャンします。QQ がボットを作成するか、作成済みのものを選びます。AppID と AppSecret の貼り付けは代替手段です。 | ボットが認証されるまで、QQ が参加を許すのは自分が所有するグループだけです。グループのオーナーがそのグループのボットのプロフィールですべてのメッセージの受信をオンにしない限り、グループでは自分を @ したメッセージだけを受け取ります。それまでは自分から会話に加わることはできません。 |
| 個人の WeChat | WeChat でスキャンします（Tencent の iLink ボット API）。 | DM のみ。WeChat はこの種のボットにグループメッセージを渡しません。 |
| Telegram | @BotFather のトークンを貼り付けます。 | |
| Discord | ボットトークンを貼り付けます。Message Content Intent をオンにしておきます。 | |

**管理下の AstrBot 経由。** ほかのプラットフォームはすべて、personagent が専用の Python 3.12 ランタイムと一緒にダウンロードしてヘッドレスで動かす AstrBot を経由します。ダッシュボードはなく、2 回目のログインも要りません。KOOK、Feishu/Lark（長時間接続）、DingTalk（Stream モード）、Slack（Socket Mode。ガイドのリンクがアプリを事前入力します）、WeCom AI ボット（長時間接続）、Mattermost、Misskey は値を 1 つか 2 つ尋ねます。上級グループには公開アドレスか別のソフトウェアが必要です。WeCom アプリ、WeChat 公式アカウント、QQ Webhook、OneBot v11（NapCat）、Satori です。LINE は提供していません。

どちらの経路でも、ページまたは `personagent connect <platform>` で連携したプラットフォームでは、新しいチャットに承認が必要です。キャラクターは管理者と、管理者が承認した人とグループに答えます。それ以外の人には短いコードを含む決まったメッセージが 1 通届き、**プラットフォーム連携** または `personagent access` で承認を待ちます（[キャラクターを管理する](#キャラクターを管理する)を参照）。このバージョンより前にセットアップした personagent フォルダーや、**新しいチャットに承認なしで返信** に切り替えたプラットフォームでは、プラットフォームがボットに届けるすべてのグループと DM に答えます。範囲を絞るには、ページの **返信するグループを限定** を使います。ページはこれを `ACCESS_GROUPS` として保存し、DM には `ACCESS_DM_USERS` が同じ働きをします。どちらかにそのプラットフォームの項目が 1 つでもあると、そのプラットフォームでは列挙した相手にしか返信しません（[personagent 自身の許可リスト](#すでに動かしている-astrbot-を通す)を参照）。ID は `<platform>:<id>` の形で届きます。たとえば `qq_official:<openid>`、`weixin_oc:<id>`、`telegram:<id>`、`discord:<id>` です。QQ 公式ボットに見えるのは QQ 番号ではなく openid です。プラットフォームを直接つなぐと、同じプラットフォームの AstrBot 接続は削除されます。

## キャラクターを管理する

以下はすべてローカルページで行います。設定は **キャラクターと設定** → **詳細設定** にあり、**詳細設定を保存** をクリックすると反映されます。括弧内は `.env` での設定名です。`.env` を直接変更した場合は、personagent を再起動すると反映されます。

- **新しいチャットを承認する。** `ACCESS_APPROVAL_PLATFORMS` に記載されたプラットフォーム（このバージョン以降に連携したすべてのプラットフォーム）では、下の 2 つの一覧のどちらにもないチャットにはモデルが返信しません。DM には 6 文字のコードを含む決まった 1 行が、1 日に多くても 1 回届きます。承認されていないグループでは、誰かがキャラクターに話しかけたときにだけ、1 日に多くても 1 行届きます。申請は **プラットフォーム連携** で待機し、**承認**、**拒否**、DM の場合は **自分です** を選べます。**自分です** では、自分のチャットに届いたコードを入力すると、そのアカウントが管理者になります。サーバーでは、`personagent access` が申請を一覧表示し、`personagent access approve CODE`（または `decline`、`admin`）で 1 件を処理します。承認したチャットと拒否したチャットはランタイムフォルダーの `approvals.json` に保存され、実行中のサービスがすぐに読み込みます。これらは `ADMIN_IDS`、`ACCESS_DM_USERS`、`ACCESS_GROUPS` が `.env` と環境変数のどちらから来ていても、それらに追加して扱われ、それらを変更することはありません。拒否したチャットには、どちらのルールでも返信しません。申請は 3 日で期限切れになり、待機できるのはプラットフォームごとに DM が最大 20 件、グループが最大 10 件です。承認を求めるのは、初めて連携し、決定の記録もチャットもまだないプラットフォームだけです。`personagent access policy <platform> open`（またはページの **新しいチャットに承認なしで返信**）で、プラットフォームの承認をオフにできます。
- **自分を管理者にする。** キャラクターに DM で一度メッセージを送り、**返信、管理者とアクセス** で **最近のチャットから選択** をクリックし、自分のアカウントの横の **自分です** (`ADMIN_IDS`) をクリックします。QQ 公式ボットには QQ 番号ではなく openid が見えるため、この方法を使います。
- **一部のグループでだけ返信させる。** 同じ一覧で、残すグループごとに **このグループで返信** にチェックを入れるか、**返信するグループを限定** (`ACCESS_GROUPS`) に ID を入力します。あるプラットフォームのグループを 1 つでも列挙すると、そのプラットフォームのほかのグループでは返信しなくなります。QR コードで連携した QQ 公式ボットのグループの ID は `qq_official:<id>` の形で、QQ 上では確認できません。そのグループで一度ボットにメンションしてから、**最近のチャットから選択** で選んでください。
- **すべての返信を止める。** **返信、管理者とアクセス** の最初の項目 **メッセージに返信** (`AGENT_ENABLED`) をオフにします。保存の前に確認が表示されます。キャラクターは接続を保ったまま、オンに戻すまでどのメッセージにも返信しません。
- **一部のグループでだけ止める。** 同じ一覧でそのグループの **このグループでは返信を停止** にチェックを入れるか、**返信を停止するグループ** (`ACCESS_PAUSED_GROUPS`) に ID を入力します。キャラクターはそのグループでは呼びかけられても返信せず、プラットフォーム側のボットも応答しません。ほかの場所では通常どおり返信します。停止中のグループのメッセージは保持されず、学習にも使われません。一覧から外すと再開します。
- **呼びかけられたときだけ返信させる。** **発言と返信のスタイル** の **グループでは呼びかけられたときのみ返信** (`CHAT_ONLY_WHEN_CALLED`) をオンにします。グループでは、名前を呼ばれたとき、メンションされたとき、または自分のメッセージに返信されたときにのみ返信し、自分から会話に加わったり始めたりしません。DM には影響しません。
- **あなただけが教えられるようにする。** **学習** の **管理者の訂正からのみ学習** (`REACT_LEARN_ADMIN_ONLY`) をオンにします。**あなたのアカウント** に含まれない人の反応も記録されますが、その提案は使用されません。先にアカウントを登録してください。登録がない場合は、このページの **チャット** での訂正のみが学習に使われます。
- **学習したことを取り消す。** **アクティビティ** でチャットを選び、項目の横の **取り消し** をクリックするか、`personagent learned rollback <id>` を実行します。
- **グループから外す。** プラットフォーム側でボットをグループから削除します。**プラットフォーム連携** で連携を解除しても personagent の接続が終わるだけで、ボットはグループのメンバーのままです。
- **外されたとき、制限されたとき。** ボットを外したグループからは何も届かなくなるだけで、再接続は要りません。プラットフォームがボットを禁止したりオフラインにしたりすると、personagent が直接連携するプラットフォームでは接続が止まり、**プラットフォーム連携** に理由が表示されます。

## すでに動かしている AstrBot を通す

AstrBot、NapCat（OneBot）、Koishi（[Satori コネクター](../integrations/satori/README.ja.md)経由）、Matrix（[Matrix コネクター](../integrations/matrix/README.ja.md)と mautrix ブリッジ経由）は、personagent と連携するサードパーティのブリッジです。personagent が直接連携するプラットフォームには、どれも必要ありません。

AstrBot は `integrations/astrbot/astrbot_plugin_personagent/` のプラグインを通じて personagent にメッセージを渡します。プラグインは各メッセージを `POST /v1/events` に送り、レスポンスの返信を中継します。personagent のアウトボックスも取得するので（`outbox_enabled`、既定でオン）、プラットフォームがボットに許す場所ではペルソナが自分から話しかけられます。表はプラグインの README にあります。管理下の AstrBot にはプラグインが自動で入ります。自分の AstrBot の場合は、一度起動してデータフォルダー（`cmd_config.json`、`plugins/`、`config/` があるフォルダー）を作らせてから、次を実行します。

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

プラグインの既定は拒否です。AstrBot の WebUI で `groups` と、DM 用に `dm_users` を埋めるか、`connect` の質問に答えてください。DM は `dm_users` が空でなくなると転送されます。[プラグインの README](../integrations/astrbot/astrbot_plugin_personagent/README.ja.md)にすべてのキーがあります。管理下の AstrBot は、連携した各プラットフォームを `<platform>:*` で開きます。プラグインをインストールしたら、AstrBot を再起動するか WebUI でプラグインを再読み込みしてください。personagent 側では：

- `CONNECTOR_TOKEN` は各リクエストを認証します。リクエストは `X-Personagent-Token` ヘッダーと、トークンを鍵とした `timestamp.nonce.body` の HMAC-SHA256 を運び、リプレイ防止が再利用された nonce を拒否します。傍受したリクエストを再送したり改ざんしたりはできません。トークンは署名鍵でもあるので、ログに残さず、漏れたら交換してください。1 台のホストでは任意、ホストをまたぐ場合は必須です。
- `ADMIN_IDS` は管理者のアカウントを `<platform>:<id>`（`telegram:12345`、`discord:4242`）で一覧にします。ID だけ、または `qq:<id>` は QQ 番号です。`ADMIN_NAME` は管理者の名前を設定します。一覧のアカウントはすべて 1 人の人物のもので、グループと DM でより親しいペルソナを受け取り、ボットがグループについて覚えていることを管理でき、1 人で教えることができます。AstrBot 経由では、プラットフォームは AstrBot が表示するアダプター名で、チャットで `/sid` を使うと ID が表示されます。
- `ACCESS_GROUPS` と `ACCESS_DM_USERS` は、同じ `<platform>:<id>` の形で personagent 自身にプラットフォームを制限させます。プラットフォームごとに別々に制限されます。項目のないプラットフォームはコネクターに任され、項目が 1 つでもあればそのプラットフォームは項目だけに制限されます。personagent が拒否したターンは引き受けられずに戻るので、AstrBot 自身のモデルが答えることがあります。
- `ACCESS_APPROVAL_PLATFORMS` は、そのプラットフォームの項目がなくても 2 つの一覧を適用するプラットフォームを指定します（ここでは AstrBot のアダプター名）。どちらにもないチャットは管理者の承認待ちとして保留され、引き受けられるので、AstrBot 自身のモデルも答えません。何が personagent に届くかは、引き続きプラグインの `groups` と `dm_users` が先に決めます。

Docker や別のホストの AstrBot については[ユーザーガイド](guide.ja.md#自分で動かすブリッジ)を参照してください。

### NapCat（OneBot）経由の QQ

この経路は公式ボットではなく個人の QQ アカウントを使います。対象のグループには、自分のものではない 2 つ目の QQ アカウントが必要です（[DISCLAIMER.md](DISCLAIMER.ja.md) を参照）。通常は QR コードで、再起動後も続くセッションとして、AstrBot の `aiocqhttp` アダプターにつながった OneBot v11 実装にログインします。[NapCat](https://github.com/NapNeko/NapCatQQ) はテスト済みで、QQ NT デスクトップクライアントに接続します。LLOneBot と Lagrange も OneBot v11 の実装です。そのアカウントは自分で各グループに参加させてください。メンバーになるまでは、グループのメッセージはキャラクターに届きません。

管理下の AstrBot では、ローカルページで **上級** の **OneBot v11（NapCat）** を追加し、NapCat を `ws://127.0.0.1:6199/ws` に向けます。[中国語のガイド](deploy.zh-CN.md)に手順があります。自分の AstrBot では、プラグインの `excluded_platforms` から `aiocqhttp` を外し、`CONNECTOR_QQ_PLATFORMS=aiocqhttp` を設定し（`--qq` で両方できます）、`QQ_BOT_ID` を設定します（`personagent connect astrbot` が尋ねます）。

**ここでは `CONNECTOR_QQ_PLATFORMS` が必須です。** ないと QQ の ID が名前空間付き（`aiocqhttp:123456`）で届き、すべての会話が新しく見えます。記憶、履歴、学習した例は接頭辞なしの ID をキーにしており、学習記録は会話 ID から行 ID を導くので、分かれたものは後から修復できません。

接頭辞なしの ID は QQ の権限を持つので、`ADMIN_IDS`、`ACCESS_GROUPS`、`ACCESS_DM_USERS` の QQ の項目はプラグインの許可リストに重ねて適用されます。QQ の DM は `dm_users` に含まれ、*かつ*管理者か `ACCESS_DM_USERS` の項目からのものでなければなりません。`ACCESS_GROUPS` に QQ グループがあれば、QQ グループは両方に含まれている必要があります。その権限をコネクターに任せられる場合だけ、プラットフォームを `CONNECTOR_QQ_PLATFORMS` に入れてください。

**NapCat の HTTP サーバー**（`QQ_ONEBOT_URL`、既定は空）は、この経路では任意です。personagent は自分からもメッセージを送ります。

- 自分から話しかけるメッセージ（`PROACTIVE_ENABLED`、既定でオフ）
- 否定の 2 分後に尋ねる質問（`REACT_ELICIT_ENABLED`）
- モデル呼び出しが失敗したときにグループに送る言い訳

これらは、プラグインが取得している間はプラグインのアウトボックスを通って戻ります。取得していないときは、URL が設定されていれば `QQ_ONEBOT_URL` に送られます。サーバーが必要なのは、オフライン中に見逃した @ メンションの掃引だけで、`QQ_BOT_ID` も一緒に必要です。掃引は起動時とその後 30 分ごとに動きます。`ACCESS_GROUPS` の QQ グループと前回の再起動以降に動きのあったグループを対象に、1 時間以内の @ メンションを再生します。URL が空なら、`personagent doctor` は OneBot ブリッジを「not configured」と表示します。

**すべてのコネクター経路で失われるもの**（直接接続、AstrBot、その他のコネクター）。戻す設定はありません。

- ビジョンモデルが説明しなかった画像の OCR フォールバック
- NapCat を通じた引用の検索。引用は personagent 自身の最近のメッセージの索引と、コネクターが引用と一緒に送る引用テキストから解決します

新しいスタンプは、QQ と同じくすべての経路で収集されます。対象は、グループに投稿された画像のうち、インラインで届いたもの、またはスタンプとして印が付いたものです。コネクターがリンクとしてだけ送る写真は収集されません。

## 複数のプラットフォーム

各コネクターがプラットフォーム名を付けるので（`telegram:-1001234`、`matrix:!room:example.org`）、複数のコネクターを 1 つの personagent に対して並行して動かせます。direct プロセス、AstrBot、Satori、Matrix はすべて同時に動かせます。1 つのチャットを 2 つのコネクターから入れないでください。すべてのメッセージが 2 回届きます。名前空間付きの ID は接頭辞なしの QQ 番号と衝突しません。

誰も頼んでいないメッセージは、personagent のアウトボックスを取得するコネクターを通じてプラットフォームに届きます。自分からの話しかけ、否定の後に尋ねる質問、グループでモデル呼び出しが失敗したときの言い訳です。DM の言い訳は、メッセージを運んだリクエストへのレスポンスで返ります。

direct プロセスとここにある 3 つのコネクターは、ボットから話しかけることを許すプラットフォームでアウトボックスを取得します。QQ は公式ボットの自発的なメッセージにレート制限をかけ、相手がオフにすることもできます。自作のコネクターは、イベントと一緒に `connector_id`、`reply_handle`、`"capabilities": ["outbox"]` を送り、`/v1/outbox` をロングポーリングします（[コネクタープロトコル](connectors.ja.md)を参照）。そのようなコネクターがなければ、personagent が話すのはメッセージを運んだリクエストの中だけです。自発ループはその会話を飛ばし、質問と言い訳は送られません。

ローカルページもアウトボックスを取得しますが、対象はページ自身のチャットだけです。アウトボックスを取得しないプログラム（チャットで発言するコーディングアシスタントなど）からのイベントによって、アウトボックスを取得するコネクターがそのチャットを失うことはありません（[コネクタープロトコル](connectors.ja.md#アウトボックスpost-v1outbox)を参照）。

`PROACTIVE_PLATFORMS` は自分から話しかける処理が使える場所を制限します。`PROACTIVE_PLATFORMS=qq_official` は QQ 公式ボットに、`qq` は NapCat 経由の QQ に限定します。`CONNECTOR_OUTBOX_ENABLED=false` はアウトボックスを完全にオフにします。

アウトボックスなしで DM で自分から話しかけるには、自分のスケジューラー（AstrBot プラグインのタスク、cron の項目）が `"proactive": true` を付けた DM イベントを送れます。[アウトボックスなしで自分から話しかける](connectors.ja.md#アウトボックスなしで自分から話しかける)を参照してください。

## エンドポイントを公開する

コネクターと personagent が同じマシンにあるなら、`SERVER_HOST=127.0.0.1` のままにしてください。コンテナが同じマシンとみなされるのは、ホストのネットワーク名前空間かホストネットワークを使う場合だけです。ローカルページまたは `personagent up` が起動したエージェントは常に `127.0.0.1` にバインドします。ページ自体は `PAGE_HOST` に従います（[別のデバイスからページを開く](#別のデバイスからページを開く)）。それ以外の場合：

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

- **調査はクレジットを消費します。** `personagent doctor` と `/health/details` は、エージェントが処理を送る各モデルに小さなチャット補完を 1 回送ります。対象は、グループと DM の返信、ウェブ検索の判断、反応の判定（`REACT_LEARN_ENABLED` がオンの間）、自己評価（`EVAL_ENABLED` がオンの間）、ビジョンです。`EMBEDDING_MODEL` があれば埋め込みを 1 回、`TAVILY_API_KEY` があれば Tavily 検索を 1 回送ります。`/health` と設定や学習記録の確認は無料です。
- **モデルの使用量は集計されます。** すべてのモデルへのリクエストは、プロバイダーが報告する使用量をもとに、モデルごと、日ごとに集計されます。プロバイダーが費用を報告する場合は費用も集計されます。`personagent doctor` は本日と過去 7 日間の値を出力し、ローカルページのアプリビューにも同じ値が表示されます。集計ファイルはバックグラウンドで書き込まれます。書き込みは多くても 1 分に 1 回で、終了時にもう 1 回行います。リクエストは 1 回のモデル呼び出しで、1 件のメッセージから通常は複数発生します。アプリビューでは本日のリクエストを用途別にも示します。強制終了すると最後の 1 分間の集計が失われることがあります。
- **学習と記憶。** キャラクター自身による学習の判断は、1 回ごとに `PROMOTE_JUDGE_MODEL` の呼び出しを 1 回消費し、`PROMOTE_JUDGE_INTERVAL_S` ごとに最大 `PROMOTE_JUDGE_BATCH` 回です。記憶の整理は、チャットの 1 区間ごとに `LLM_JUDGE_MODEL` の呼び出しを 1 回消費し、1 日あたりチャットごとに最大 16 回、すべてのチャットを合わせて `MEMORY_CALLS_PER_DAY`（40）回までです。`PROMOTE_JUDGE_ENABLED=false` と `MEMORY_CALLS_PER_DAY=0` でそれぞれオフになります。
- **`tools/` のスクリプト**はさまざまです。無料のものもモデルを呼ぶものもあります。[tools.md](tools.ja.md) の表に書かれています。
- **`personagent eval`** はケースごとにモデルを呼びます。ただし `memory` スイートは例外で、あらかじめ用意した回答を使ってオフラインで実行されます。ペルソナと学習のスイートには、判定用の 2 つ目のモデル（`BENCH_JUDGE_MODEL`）も必要です。
- **メモリ。** 名前空間付き（QQ 以外）の会話が 256 を超えると、最も長く動きのないアイドル会話がメモリから外され、保留中の反応を失います。その会話のまだ整理されていないメッセージは先に整理され、最近のメッセージは、`MEMORY_KEEP_RECENT=false` でない限り `runtime/recent.json` に 72 時間残ります。事実、出来事、常に保持するメモ、学習記録は残ります。リクエストの途中の会話は追い出されません。長期記憶は起動時にディスクから読み込まれ、この上限の対象外です。
- **ディスク。** `runtime/` の学習記録（証拠ログと候補ログ）は追記専用で、切り詰められません。`personagent doctor` はどちらかが 50 MB を超えると警告します（`LEDGER_EVIDENCE_WARN_BYTES`、`LEDGER_CANDIDATES_WARN_BYTES`）。記憶のファイルは小さいままです。`recent.json` は直近 72 時間に動きのあったチャットだけを保持し、`memory_trash.jsonl` は削除された項目を最大 30 日間保持します。毎日最初の変更の前に、`memory.json`、`core_memory.json`、`episodes.json` は、同じ名前の末尾に `.bak` を付けたファイルにコピーされます。また、このバージョンの初回起動時には、古い記憶ファイルが `memory.json.pre-v2` として保持されます。**このチャットの記憶を削除** またはチャットで依頼された削除の後は、`.bak` のコピーが現在のファイルから書き直され、`memory.json.pre-v2` からも忘れた内容が取り除かれるため、記憶ファイルのどのコピーにもその内容は残りません。ただし、それ以前に作成したバックアップには残り、このページ自身のチャット（`runtime/desktop/browser-chat.json`）にも、そのチャットで依頼した削除が取り除いた部分を除き、**新しいチャット** または **このページのチャットの記憶を削除** まで残ります。ボットが学んだことと記憶していることのすべてが入っているので、`runtime/` をバックアップしてください。
- **チャットの記録。** `runtime/log/` にある各チャットの記録は、行を `MEMORY_LOG_DAYS`（30）日間、最大 5,000 行保持し、1 日 1 回整理されます。`.bak` のコピーはなく、バックアップにも含まれず、どの削除も記録に及びます。記録とのメモの照合は記憶の整理の呼び出しに含まれ、静かなチャットでの照合だけの呼び出しは 1 日 1 回までで、`MEMORY_CALLS_PER_DAY` の範囲内です。ただし、バックアップには最近のチャットの本文を保持する `recent.json` と `pending_reactions.json` が含まれます。

## ボットが黙ったとき

原因は多いものから順に挙げています。ローカルページがエージェントを動かしているなら、[アクティビティ](guide.ja.md#アクティビティ)でメッセージが届いているか、なぜ黙ったかがわかります。サーバーではサービスのログを読み、学習内容には `personagent learned` を使ってください。

1. **何も届いていない。** ローカルページでプラットフォームが連携済みとして表示されているか確認し、`runtime/desktop/direct.log` か `astrbot.log` を読んでください。QQ 公式ボットはグループにいる必要があり、どのグループメッセージを受け取るかは QQ が決めます。個人の WeChat ボットはグループを受け取りません。自分で動かす AstrBot では、プラグインの `groups`（DM には `dm_users` も）を埋め、NapCat なら `excluded_platforms` から `aiocqhttp` を外してください。Satori と Matrix のコネクターには `.env` に独自の許可リストがあります。それぞれの README を参照してください。この場合、チャットはアクティビティに現れません。
2. **エージェントがオフ。** `personagent run` のバナーに `agent: OFF` と理由と対処が表示されます。`LLM_API_KEY` がなければ、ローカルページでキーを追加して（または `LLM_API_KEY` を設定して）再起動してください。`AGENT_ENABLED=false` なら `<home>/.env` で `true` にして再起動してください。それまですべてのイベントは `owned: false` を受け取り、最初のイベントで同じ助言の ERROR 行が 1 行記録されます。
3. **代わりに AstrBot 自身のモデルが答える。** リクエストが失敗した、personagent がメッセージを断った（項目 5）、またはエージェントがオフ（項目 2）のためにプラグインがフォールバックしました。AstrBot のログには `refusing unsafe personagent_url`、`agent refused the request (403): <message>`（または別のステータス。下の表を参照）、`timed out waiting for the agent` が出ます。`timeout_s` はデバウンスとターン内のモデル呼び出しに加え、メッセージが届いたときに考えていたターンの分もカバーする必要があります。1 ターンのモデル呼び出しは、グループでも DM でも合わせて 1.5 × `LLM_TIMEOUT_S` までなので、3 × `LLM_TIMEOUT_S` をそれ未満に保ってください。既定値（420）はエージェントの既定値（3 × 120 = 360 秒）をカバーします。`LLM_TIMEOUT_S` を上げるなら、これも上げてください。
4. **呼ばれていない。** グループでは名前（`PERSONA_NAME`）か @ に答えます。そうでなければ会話がたまるのを待ち（`CHAT_TRIGGER_COUNT`、既定は 30 メッセージ）、それでも見送ることがあります。タイムゾーンの 02:00 から 07:00 までは、呼ばれていないチャットにはほとんど入りません。タイムゾーンは `PERSONA_TZ_OFFSET_HOURS` です。空の場合、`AGENT_LANG` が `zh` か `zh-TW` なら UTC+8、それ以外はこのマシンのオフセットです。起動後、そのプラットフォームの最初のメッセージから 2 分以内に届いたグループメッセージのうち、送信から 10 分以上たって届いたものは未処理分とみなされ、文脈として保持されますが、返信はされません。その旨はサービスのログに記録されます。アクティビティに最近の各ターンの理由が表示されます。同じ判断をオフラインで見るには `personagent chat --trigger 4` を実行してください。
5. **personagent の許可リスト。** `ACCESS_GROUPS` と `ACCESS_DM_USERS` はすべての経路で適用され、接頭辞なし ID の QQ DM にはさらに管理者か項目が必要です。これらが断ったメッセージは引き受けられずに戻るので、AstrBot 経由ならそのモデルが答えることがあります。personagent は拒否した各会話を、拒否した設定とともに INFO で一度記録します。`ACCESS_APPROVAL_PLATFORMS` に記載されたプラットフォームでは、どちらの一覧にもないチャットは代わりに承認を待ちます。`personagent access` に一覧表示され、ログには「waiting for the admin's approval」と記録されます。
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
| 403 | `invalid_envelope` | invalid request envelope: … | トークン、ヘッダー、署名の欠落や誤り、5 分を超える時計のずれ、再利用された nonce、またはリプレイ防止の満杯（エージェントのログに `connector replay guard full`） |
| 403 | `stale_event` | stale or invalid sent_at | `sent_at` が現在と `CONNECTOR_MAX_EVENT_AGE_S`（24 時間）を超えて異なります。未来の時刻やミリ秒単位のタイムスタンプも該当します |
| 400 | `invalid_schema` | invalid event schema: … | 必須フィールドの欠落：`platform`、`conversation_type`、`sender_id`、`message_id`、`sent_at`、グループでは `conversation_id` |
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
