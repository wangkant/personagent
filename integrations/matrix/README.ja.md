# Matrix コネクター

[English](README.md) · [简体中文](README.zh-CN.md) · [繁體中文](README.zh-TW.md) · 日本語 · [한국어](README.ko.md) · [Español](README.es.md) · [Français](README.fr.md) · [Deutsch](README.de.md) · [Português (Brasil)](README.pt-BR.md) · [Русский](README.ru.md)


このコネクターは [personagent](https://github.com/wangkant/personagent) を Matrix のルームに、さらに [mautrix ブリッジ](https://docs.mau.fi/bridges/)を通じて WhatsApp、Signal、Messenger、Instagram、Google Messages などのネットワークに置きます。Matrix とブリッジはサードパーティのソフトウェアで、自分で運用します。personagent がローカルページから接続するプラットフォームには必要ありません。

コネクターは [matrix-nio](https://github.com/matrix-nio/matrix-nio) で作られた小さな独立プロセスで、libolm なしでエンドツーエンド暗号化に対応します。普通の Matrix ユーザーとしてホームサーバーにログインし、許可されたルームの各メッセージをプラットフォーム中立のイベントとしてエージェントの `POST /v1/events` に転送し（[docs/connectors.md](../../docs/connectors.ja.md)）、エージェントの返信をルームに投稿します。エージェントのアウトボックスもポーリングするので、予定された話しかけ、追加の質問、言い訳も Matrix に届きます。

## 何をするか

受信時、許可されたルームの各メッセージについて：

- イベントはプラットフォーム `matrix` と生の Matrix ID を使うので、エージェントは `matrix:@alex:example.org` と `matrix:!room:example.org` を保存します。
- ボットの `m.direct` に載っているルーム、またはボットと `MATRIX_IGNORE_USERS` のユーザーを除いてメンバーがちょうど 1 人のルームはダイレクトチャットとして扱います。ダイレクトチャットは人ごと、グループはルームごとに区別します。`MATRIX_GROUPS` に ID で書いたルームは常にグループです。
- メッセージがボットをメンションするかボットのメッセージに返信すると、`addressed` は true です。メンションとは `m.mentions`、または `m.mentions` を送れない古いクライアントからのピルやテキスト内のボットのユーザー ID です。
- 返信には引用されたメッセージの送信者とテキストが付きます。コネクターは最近のイベントのキャッシュから取るか、親イベントを取得します。古いクライアントが先頭に付ける返信のフォールバック（`> <@alex:example.org> ...`）は取り除くので、エージェントがほかの人の言葉を送信者の言葉として読むことはありません。
- 4 MB までの画像とスタンプはダウンロードされ、暗号化ルームでは復号されて、バイト列としてエージェントに送られます。音声メッセージ、動画、ファイルは言葉で記述します。
- ルームのメッセージは送信順にエージェントに届きます。画像の後に送られたメッセージは、画像のダウンロードが終わるまで待ちます。エージェントは複数のターンを同時に処理できます。
- タイムスタンプはホームサーバーの `origin_server_ts` です。
- コネクターは、ボット自身のメッセージ、`m.notice` メッセージ（ボットが送る種類）、編集、リアクション、`MATRIX_IGNORE_USERS` からのメッセージ、起動時の最初の同期が返すバックログ、`MATRIX_MAX_EVENT_AGE_S` より古いもの（ブリッジが新しいルームに埋め戻す履歴など）をスキップします。

送信時：

- テキストの返信は `m.text` です。エージェントがグループで誰かをメンションするよう求めると、返信はピルで始まり、その人を `m.mentions` に載せます。ほかの返信はすべて空の `m.mentions` を持つので、どのクライアントもテキスト内の名前を通知に変えません。
- 画像の返信はアップロードされ、暗号化ルームでは暗号化されます。
- エージェントがターンを処理している間は入力中の通知が出ます。
- スレッド内のメッセージにはそのスレッドで答えます。
- エージェントが会話を引き受けると、ボットはメッセージを既読にします（`MATRIX_READ_RECEIPTS_ENABLED`）。ブリッジ経由では、相手のネットワークで既読マークとして表示されます。
- アウトボックスの配信は、会話が最後に来たルームに届きます。イベントの `reply_handle` がルーム ID です。

## インストール

動いている personagent と、ボット用の Matrix アカウントが必要です。人と共有せず、専用のアカウントを作ってください。

コネクターはこのリポジトリのスクリプトなので、リポジトリのコピー（クローンまたは GitHub の ZIP）と専用の Python 環境が必要です。`matrix-nio` は personagent の依存関係ではないためです。personagent の `.venv` があるクローンでは、その環境にインストールします。

```bash
.venv/bin/python -m pip install -r integrations/matrix/requirements.txt
```

PyPI から pip で personagent をインストールした場合や uvx で実行している場合は、コピーの隣に別の venv を作ります。

```bash
python -m venv connector-venv
connector-venv/bin/python -m pip install -r integrations/matrix/requirements.txt
```

Windows のインタープリターは `.venv\Scripts\python.exe` または `connector-venv\Scripts\python.exe` です。次に設定ファイルをコピーします。

```bash
cp integrations/matrix/.env.example integrations/matrix/.env
```

`integrations/matrix/.env` を編集します。

```ini
MATRIX_URL=https://matrix.example.org
MATRIX_USER_ID=@nova:example.org
MATRIX_PASSWORD=...
MATRIX_GROUPS=!AbCdEf:example.org
MATRIX_DM_USERS=@alex:example.org
PERSONAGENT_URL=http://127.0.0.1:8080
```

そして同じインタープリターで、エージェントの隣でコネクターを起動します。

```bash
.venv/bin/python integrations/matrix/matrix_connector.py
# or: .venv/bin/python integrations/matrix/matrix_connector.py --config /path/to/matrix.env
```

`MATRIX_GROUPS` に載っているルームにボットを招待すると参加します。Element では、ルーム ID はルーム設定の詳細にあります。

### ログイン

パスワードログインが最も簡単な始め方です。コネクターは得たセッション（ユーザー ID、デバイス ID、アクセストークン）を `MATRIX_STORE_DIR/session.json` に保存して次の起動で再利用するので、再起動で新しいデバイスは作られません。そのファイルを削除すると再度ログインします。

既存のアクセストークンを使うには `MATRIX_ACCESS_TOKEN` を設定します。コネクターはホームサーバーにトークンのアカウントを問い合わせます。自分で使っているセッションのトークンは使わないでください。そのセッションからログアウトするとボットもログアウトします。

ホームサーバーがボットをログアウトさせると（`M_UNKNOWN_TOKEN`）、コネクターはその旨のエラーで停止します。パスワードログインなら、再度起動すればログインし直します。`MATRIX_ACCESS_TOKEN` の場合は、先に新しいトークンを設定してください。ほかの同期失敗は、最大 1 分まで倍々に延びる遅延の後に再試行します。

### エージェントを動かせる場所

規則はプロトコルで決まっています。`PERSONAGENT_URL` はループバックアドレスか、`CONNECTOR_TOKEN` をエージェントの `CONNECTOR_TOKEN` に設定した HTTPS でなければなりません。それ以外ではコネクターは起動を拒否します。1 台のホストでも、エージェントの前にプロキシやトンネルを置く前に、両側でトークンを設定してください。

## 設定

[.env.example](.env.example) にすべての設定があります。リストはカンマ区切りでグロブを使えるので、`@*:example.org` はサーバー全体に一致します。空のリストは誰にも答えません。単独の `*` は全員に一致し、イベントに `prefiltered: false` を付けます。すると判断はエージェント自身の `ACCESS_GROUPS` / `ACCESS_DM_USERS` だけに委ねられ、そこにエントリーのないプラットフォームは拒否されます。

| 設定 | 意味 |
|---|---|
| `MATRIX_GROUPS` | 答えるグループルームのルーム ID。`*` はボットが参加しているすべてのルームです。 |
| `MATRIX_DM_USERS` | ダイレクトチャットでボットと話せる人。`*` は全員です。 |
| `MATRIX_INVITE_FROM` | ボットが招待を受ける相手。`MATRIX_GROUPS` のルームへの招待と `MATRIX_DM_USERS` からのダイレクトチャットの招待は常に受けます。ほかの招待は保留のままです。 |
| `MATRIX_IGNORE_USERS` | 決して答えず、ダイレクトチャットとグループを見分けるときのメンバーにも数えません。 |
| `MATRIX_E2EE_ENABLED` | エンドツーエンド暗号化。下記を参照してください。 |
| `MATRIX_TIMEOUT_S` | 1 ターンにかけられる時間。エージェントの 3 × `LLM_TIMEOUT_S` より大きくしてください。 |
| `MATRIX_OUTBOX_ENABLED` | エージェントのアウトボックスをポーリングします。 |

## ブリッジ：WhatsApp、Signal、Messenger、Instagram など

mautrix ブリッジは別のネットワークにそのネットワークのアカウントとしてログインし、チャットをポータルと呼ばれる Matrix ルームにミラーします。向こう側の全員が `@whatsapp_4912345:example.org` のようなゴーストユーザーとして Matrix に現れます。ブリッジにログインしているのがボットの Matrix アカウントなら、ペルソナはそのネットワークに住むことになります。WhatsApp の連絡先がペルソナの番号に書き込むと、ブリッジがメッセージをポータルルームに投稿し、このコネクターが転送し、返信は同じ道を戻ります。

| ネットワーク | ブリッジ |
|---|---|
| WhatsApp | [mautrix-whatsapp](https://github.com/mautrix/whatsapp) |
| Signal | [mautrix-signal](https://github.com/mautrix/signal) |
| Facebook Messenger、Instagram の DM | [mautrix-meta](https://github.com/mautrix/meta) |
| Google Messages（Android スマートフォン経由の RCS と SMS） | [mautrix-gmessages](https://github.com/mautrix/gmessages) |
| Google Voice、LinkedIn、Twitter/X の DM、Bluesky の DM、Google Chat、Zulip、IRC、iMessage | ほかの [mautrix ブリッジ](https://github.com/mautrix) |
| Telegram、Discord、Slack | mautrix ブリッジはありますが、これらのネットワークには公式のボット API があります。personagent は Telegram と Discord に自分で接続し、Slack にはローカルページが動かす AstrBot 経由で接続します。 |

セットアップ手順：

1. 自分で管理するホームサーバー（Synapse、またはアプリケーションサービスに対応した別のサーバー）を動かし、[そのドキュメント](https://docs.mau.fi/bridges/)に従ってブリッジをインストールします。ブリッジの `permissions` でボットのアカウントに `user` 権限レベルを与えます。
2. ボットとして Element にサインインし、ブリッジボット（たとえば `@whatsappbot:example.org`）とのチャットを開いて `login` を送ります。ペルソナが使うネットワークアカウントをリンクします。WhatsApp、Signal、Google Messages ではペルソナのスマートフォンで QR コードをスキャンします。Messenger と Instagram では Meta のログイン情報を渡します。[ブリッジの使い方](https://docs.mau.fi/bridges/general/using-bridges.html)を参照してください。
3. コネクターをポータルに参加させ、ブリッジ自身のメッセージを除外します。

   ```ini
   MATRIX_INVITE_FROM=@whatsappbot:example.org
   MATRIX_IGNORE_USERS=@whatsappbot:example.org,@whatsapp_4900000000:example.org
   MATRIX_DM_USERS=@whatsapp_*:example.org
   MATRIX_GROUPS=!groupPortal:example.org
   ```

   `MATRIX_IGNORE_USERS` の 2 番目のエントリーは、ペルソナ自身の番号のブリッジ上のゴーストです。[ダブルパペッティング](https://docs.mau.fi/bridges/general/double-puppeting.html)がないと、ペルソナのスマートフォンで打ったメッセージがそのゴーストから Matrix に届き、ボットが自分に答えてしまいます。`MATRIX_GROUPS=*` はボットがいるすべてのグループポータルを転送し、personagent は `ACCESS_GROUPS` に `matrix:!room:server` として載っているルームだけで答えます。ここにルーム ID を書けば、コネクター側でルームを選べます。

### パペッティング

- ブリッジはそのネットワークの非公式クライアントで、普通のユーザーアカウント（リンクされたデバイスや Web セッション）としてログインします。ボット API は使わず、ネットワーク上でアカウントがボットと示されることもありません。
- ペルソナには専用のアカウントが必要で、普通は専用の電話番号を持ち、スマートフォンは接続可能でなければなりません。WhatsApp はスマートフォンが約 2 週間オフラインだとリンクされたデバイスを切断し、Google Messages は Android スマートフォンがオンラインの間だけ動きます。
- グループチャットでは、ペルソナのアカウントはほかのメンバーと同じに見えます。相手がボットであることを伝えてください。
- リアクション、編集、削除、投票、通話はエージェントに転送されません。

### 各ネットワークの規約

接続する前に各ネットワークの規約を読んでください。

- [WhatsApp](https://www.whatsapp.com/legal/terms-of-service) は自動メッセージ送信を許可されない通信に挙げ、許可していない非個人的な利用を禁じ、いずれかを行うアカウントを停止できます。認められた自動化の手段は WhatsApp Business Platform で、ブリッジはこれを使いません。
- [Signal](https://signal.org/legal/) も自動メッセージ送信を許可されないものに挙げています。
- [Facebook](https://www.facebook.com/terms.php) と [Instagram](https://help.instagram.com/581066165581870) は Meta の許可のない自動アクセスを禁じており、Meta は認識しないクライアントからログインしたアカウントをロックすることがあります。
- Google Messages は [Google の規約](https://policies.google.com/terms)と、SMS と RCS に関する携帯電話会社の規約の対象で、自動メッセージに料金や制限が課される場合があります。

失っても構わない専用のアカウントを使い、相手がボットだと知っている会話でのみ使い、[DISCLAIMER.md](../../docs/DISCLAIMER.ja.md) を読んでください。

## エンドツーエンド暗号化

`MATRIX_E2EE_ENABLED=false`（デフォルト）では、ボットは暗号化されていないルームだけを読みます。暗号化ルームでは復号できないとログに記録し、そこに平文の返信を送ることはありません。

`MATRIX_E2EE_ENABLED=true` では：

- `MATRIX_STORE_DIR`（デフォルトはスクリプトの隣の `runtime/` で、git は無視します）がデバイスの鍵と同期トークンを保持します。このディレクトリは残してください。失うと、ボットは新しいデバイスになり、それ以前の暗号化された内容を読めません。
- デバイスは再起動の前後で同じでなければなりません。パスワードログインは保存されたセッションで維持します。アクセストークンの場合は、`MATRIX_DEVICE_ID` をトークンのデバイスに設定します。
- ボットは検証の有無にかかわらず、ルームのすべてのデバイスと鍵を共有します。対話的に自己検証できないので、ほかの人にはデバイスが未検証と表示されます。鍵のバックアップもクロス署名もありません。
- 鍵が届いていないメッセージはログに記録してスキップし、再試行しません。
- mautrix ブリッジはポータルを暗号化できます（[エンドツーブリッジ暗号化](https://docs.mau.fi/bridges/general/end-to-bridge-encryption.html)）。ブリッジはその鍵をあなたのサーバーに保持するので、保護はそこで終わり、相手のネットワークは独自の暗号化でメッセージを運びます。ブリッジがポータルを暗号化するなら、`MATRIX_E2EE_ENABLED` をオンにしてください。

## テスト

`tests/test_matrix_connector.py` は Matrix クライアントとエージェントを模擬するので、matrix-nio もネットワークもなしで動きます。

```bash
python -m pytest tests/test_matrix_connector.py
```
