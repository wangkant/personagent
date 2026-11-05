# personagent ユーザーガイド

[English](guide.md) · [简体中文](guide.zh-CN.md) · [繁體中文](guide.zh-TW.md) · 日本語 · [한국어](guide.ko.md) · [Español](guide.es.md) · [Français](guide.fr.md) · [Deutsch](guide.de.md) · [Português (Brasil)](guide.pt-BR.md) · [Русский](guide.ru.md)

このガイドでは、personagent のセットアップ、チャットへの参加、教え方、日々の管理を説明します。[README](readme/README.ja.md) は短い紹介で、[はじめに](start.ja.md) はローカルページを画面ごとに案内します。

1. [インストールとホームフォルダー](#インストールとホームフォルダー)
2. [ローカルページ](#ローカルページ)
3. [まず見てみる：デモ](#まず見てみるデモ)
4. [ターミナルコマンド](#ターミナルコマンド)：[セットアップ](#ターミナルでセットアップする) · [チャット](#ターミナルでチャットする) · [サービスの実行](#サービスを実行する)
5. [自分のキャラクターにする](#自分のキャラクターにする)
6. [チャットに入れる](#チャットに入れる)：[QQ、WeChat、Telegram、Discord](#qqwechattelegramdiscord) · [その他のプラットフォーム](#その他のプラットフォーム管理下の-astrbot-経由) · [自分で動かすブリッジ](#自分で動かすブリッジ) · [先に話す](#先に話す)
7. [コーディングエージェント](#コーディングエージェント)
8. [教える](#教える)
9. [アクティビティ](#アクティビティ)
10. [測定する](#測定する)
11. [仕組み](#仕組み)
12. [プライバシーと同意](#プライバシーと同意)
13. [トラブルシューティング](#トラブルシューティング)
14. [0.x からのアップグレード](#0x-からのアップグレード)
15. [現状とその他の文書](#現状とその他の文書)

## インストールとホームフォルダー

```sh
python -m pip install personagent
personagent
```

`personagent` はブラウザーで[ローカルページ](#ローカルページ)を開きます。次の方法でもインストールや実行ができます。

| 方法 | コマンド |
|---|---|
| インストールせずに実行 | `uvx personagent`（[uv](https://docs.astral.sh/uv/) の機能で、Python も取得してくれます） |
| 常設の `personagent` コマンド | `uv tool install personagent` または `pipx install personagent` |
| Windows、ソース ZIP から | 展開して `start.bat` をダブルクリック |
| クローンから | `git clone https://github.com/wangkant/personagent.git`、`cd personagent`、`python -m venv .venv`、続けて `.venv/bin/python -m pip install -e .` と `.venv/bin/python -m persona_agent`（Windows では `.venv\Scripts\python.exe`） |

personagent は Python 3.10–3.14 で動きます。`start.bat` は `.venv` を作り、依存パッケージをインストールして同じページを開きます。`pyproject.toml` の依存リストが変わると、そのたびに再インストールします。

**ホームフォルダー**には、設定（`.env`）、キャラクター（`persona.txt`）、学習内容（`runtime/`）、チャットプラットフォーム（`platforms/`）が入ります。`platforms/` には管理下の AstrBot と、personagent 自身がつなぐプラットフォームの認証情報を保存する `direct.json` があります。personagent は次のうち最初に当てはまるフォルダーを使います。

1. `--home DIR` または `AGENT_HOME` で指定したフォルダー。`--home` は `personagent chat --home D:\bot` のように、コマンドの前後どちらにも置けます。
2. クローンから実行している場合はそのクローン。
3. `.env` と `persona.txt` の両方があれば現在のフォルダー。
4. 初回セットアップで作られる `~/personagent`。

1 つのインストールで複数のキャラクターを動かすには、それぞれに別のホームを与えてください。

このガイドではコマンドを `personagent ...` と書きます。インストールしていない場合は前に `uvx` を付けてください。クローンでは `.venv/bin/python -m persona_agent ...` が同じ働きをします（Windows では `.venv\Scripts\python.exe -m persona_agent ...`）。

## ローカルページ

`personagent`（または `personagent start`）は、このコンピューターからだけ開けるページを提供し、ブラウザーで開きます。ページには 4 つのビューがあります。

- **チャット** はブラウザーでキャラクターと 1 対 1 で話すチャットです。チャットプラットフォームに応答しているのと同じエージェントが答えます。
- **アクティビティ** はキャラクターがいるチャット、最近の発言、学んだこと、あなたの判断を待っていることを表示します。[アクティビティ](#アクティビティ)を参照してください。
- **アプリ連携** はキャラクターを QQ、WeChat、Telegram、Discord などのプラットフォームに入れます。[チャットに入れる](#チャットに入れる)を参照してください。
- **キャラクターと設定** では、モデルサービス（OpenRouter、DeepSeek、SiliconFlow、Alibaba Bailian、Zhipu GLM、Moonshot、Volcengine Ark、OpenAI、Google Gemini、Ollama、その他の OpenAI 互換サービス）を選び、API キーを貼り付け、名前と既成の性格を選びます。**確認してチャット開始** は小さなリクエスト 1 回でキーを試し、成功した場合だけ保存します。セットアップ後は **ペルソナ** 欄に `persona.txt` が表示されます。**ペルソナを保存** は新しい文章でエージェントを再起動し、学んだことは保ちます。**その他の機能** では Tavily によるウェブ検索（無料の既定は DuckDuckGo）、画像の理解、選んだアプリで先に話す機能をオンにできます。

アプリをつなぐまで、チャットビューには短い **はじめに** バーが表示されます。

`personagent` をもう一度実行すると、すでに開いているページを再利用します。`--no-browser` はブラウザーを開かずにリンクを出力します。

PyPI に新しい personagent があると、チャットビューに、pip、uvx、uv tool、pipx、Git クローンのどれで入れたかに応じた更新コマンドの通知が表示されます。展開したソース ZIP の場合、通知はリリースページへのリンクになります。ターミナルにも同じコマンドが出力されます。通知を閉じるとそのバージョンでは非表示になり、バージョン番号の下の **N が利用可能** で再表示できます。`personagent up` と `personagent doctor` も新しいバージョンを報告します。ページと `up` は多くても 1 日 1 回、バックグラウンドで pypi.org に尋ねます。`doctor` は前回の回答から 1 日を超えていればすぐに尋ねます。確認をオフにするには `UPDATE_CHECK_ENABLED=false` を設定してください。

ページはエージェントと接続済みのプラットフォームをバックグラウンドで起動するので、使っている間はウィンドウを開いたままにしてください。**終了** をクリックしても、Ctrl+C を押しても、ウィンドウを閉じても、起動したものはすべて一緒に止まります。以前の実行がクラッシュしてプロセスが残っていれば、次の起動時に先に止めます。

## まず見てみる：デモ

`personagent demo` はスクリプト化されたモデルで 3 つの場面を再生するので、キーは要りません。どのグループメッセージをなぜ見送るか、訂正からどう学ぶか、見知らぬ人が指示を仕込もうとしてどう失敗するかを見せます。1 つの場面だけを再生するには名前を指定します（`quiet`、`teach`、`troll`）。別の言語にするには `--lang` と言語コードを付けます（`--lang ja` など）。

以下は `personagent demo teach` の実行を短くしたものです。モデルのせりふはスクリプトですが、台帳と昇格ルールは本物のコードです。

```text
  Alex: Nova, the deploy failed again
  Nova: did you check the logs? roll back first, then diff the configs
  Alex: Nova, I was just venting
      judged: rejection, accepted: "Alex was venting, not asking for a fix"
      ledger: negative only (it says the reply was off, not what to say)
      Nova's next reply to Alex counts as its second try
  Nova: fair. that's a rough end to the day
  Alex: haha yeah it is, thanks Nova
      judged: positive, accepted: "Alex agreed with the second try and thanked Nova"
      ledger: weak (a laugh or a thanks never changes anything alone)
      ledger: Alex accepted the second try: strong (Alex is who the reply was for)

  fix: "did you check the logs? roll back first, ..." -> "fair. that's a rough end to the day"
    [x] 2 of 2 agreeing reactions
    [x] 1 of 1 strong
    [x] same chat
    [x] 1 of 1 person (PROMOTE_MIN_SPEAKERS)
    [x] nothing disagrees, no rival fix
    now in use: 2 agreeing reactions, 1 strong, same chat
```

この場面では、誰かのノートパソコンがデモの途中で壊れたという同じメッセージを、教える前後で送ります。訂正の前は、Nova は解決策を出します。訂正の後は、同情します。デモはキーが設定されていてもスクリプトのままなので、毎回同じで費用もかかりません。`personagent demo --online` は代わりに自分のモデルで再生します。トークンを消費し、実行ごとに変わります。

## ターミナルコマンド

ページでできることはすべてターミナルからもできるので、サーバーやスクリプトに向いています。

| コマンド | 働き |
|---|---|
| `personagent start` | ローカルページを開く（`--terminal` でターミナルのメニューにする） |
| `personagent init` | ホームをセットアップする。`--terminal` はターミナルで質問し、`--no-input` はフラグで受け取る |
| `personagent chat` | ターミナルで模擬グループチャット |
| `personagent demo` | 上のスクリプト化されたデモ |
| `personagent run` | サービスだけを起動。自分で動かすコネクター向け |
| `personagent up` | サービス、personagent 自身がつなぐプラットフォーム、管理下の AstrBot をまとめて起動 |
| `personagent connect astrbot` | AstrBot をつなぐ（`--install` で管理下のものをダウンロード、`--start` で起動） |
| `personagent connect claude-code`、`personagent connect codex`、`personagent connect dsh` | キャラクターを[コーディングエージェント](#コーディングエージェント)に入れる（最初の 2 つは `--react` でターン終了時のひとことを追加、`--remove` で元に戻す） |
| `personagent mcp` | コーディングエージェントが起動する MCP サーバー。自分で実行するものではありません |
| `personagent doctor` | セットアップと依存するすべてのサービスを確認 |
| `personagent learned` | 学んだことを確認、昇格、ロールバック |
| `personagent eval` | 発言、ペルソナ、学習を測定 |

すべてのコマンドは `--help` を受け付けます。

### ターミナルでセットアップする

`personagent init --terminal` はページと同じ質問を、最初に選んだ言語で尋ね、各用語を 1 行で説明します。

- **AI サービス。** プリセットはページと同じです。既定は OpenRouter の `openrouter/free` で、各リクエストを無料モデルのどれかに渡します。キーは無料です。上限は 1 分あたり 20 リクエストと 1 日 50 リクエストで、10 クレジット以上購入すると 1 日 1000 になります。返信だけでなくすべてのモデル呼び出しが数えられ、日付は UTC の午前 0 時に切り替わります。上限に達するとキャラクターは今は答えられないと言い、`runtime/desktop/agent.log` に OpenRouter の理由が残ります。リクエストごとにモデルが変わるので、1 つのモデルを選んだときよりキャラクターの声はぶれやすく、無料プロバイダーの中には受け取った内容を保存するものもあります。キャラクターを安定させるには、同じキーで有料モデルを使ってください。OpenRouter につながりにくい地域では、Zhipu の `glm-4.7-flash` も無料です。Ollama では、すでに取得済みのモデルを指定してください。Ollama にキーは要りません。
- **キー。** 入力は既定で隠されます。表示を選ぶこともでき、その場合は再設定時に保存済みのキーも見えます。ウィザードは小さなリクエスト 1 回でキーを試します。失敗すると、呼び出したアドレス、HTTP ステータス、考えられる対処を表示します。
- **キャラクター。** 名前と、4 つの既成キャラクター（皮肉屋の友人、聞き上手、ゲーマー、本好き）のどれか、または自分で書くプレーンなものを選びます。
- **AstrBot。** 任意で、初回は飛ばせます。[自分で動かすブリッジ](#自分で動かすブリッジ)を参照してください。

スクリプトなどで質問なしにセットアップするには、`personagent init --no-input` を `--provider`、`--model`、`--key-env VAR`、`--name`、`--lang`、`--persona` と一緒に実行します。新しいホームでは、`--key-env` やシェルの `LLM_API_KEY` のキーがどこのものかを示すために `--provider` か `--base-url` が必要です。`--provider other` には `--base-url` も必要です。`personagent init --help` がすべてのフラグを一覧にします。`personagent init` をターミナルなしで、これらのフラグも付けずに実行すると、質問を飛ばしてその旨を伝え、コード 2 で終了します。

### ターミナルでチャットする

`personagent chat` は、キャラクターのいる模擬グループチャットに入れます。普通の行は通常のグループの会話で、試用版はキャラクターが加わるかどうかとその理由を教えてくれます。名前を含む行はキャラクターを呼びます。

```text
Alex> anyone around tonight?
  (Nova stays quiet: not addressed, 1 of 4 messages)

Alex> Nova, the deploy failed again
  Nova > did you check the logs? roll back first, then diff the configs
```

| 入力 | 目的 |
|---|---|
| `/reply <text>` | 最後の返信を引用する。学習できるリアクションとして数えられます |
| `/as Sam <text>` | 別の人として話す：`/as Sam Nova, you free tonight?` |
| `/admin <text>` | 一度だけ管理者として話す：`/admin Nova, how was your day?` |
| `/why` | 最後の返信の理由と、それについて台帳にある内容を見る |
| `/learned` | このチャットで学んだことを見る |
| `/reset` | チャットと試用版で学んだことを消す |
| `/quit` | 終了する |

`/as` と `/admin` の行もグループのルールに従うので、返信が欲しければ名前を入れてください。4 文字未満でキャラクターの名前を含まない行は、参加の判断に数えられません。[記憶コマンド](#記憶コマンド)もここで使えます。

| フラグ | 働き |
|---|---|
| `--name Alex` | 自分の名前を設定する |
| `--admin` | すべての行を管理者の発言にする |
| `--dm` | 1 対 1 のチャットにする |
| `--lang <code>` | `AGENT_LANG` を上書きする（`--lang ja` など） |
| `--trigger N` | 参加を検討するまでのメッセージ数（既定は 4） |

試用版は本物の「話すか黙るか」の判断、出力チェック、記憶コマンド、学習を実行します。稼働中のボットが 30 メッセージ待つところを、4 メッセージで参加を検討します。学んだことはホームフォルダーの `runtime/trial/` に留まり、稼働中のボットとは別です。`personagent learned` には表示されず、`/reset` で消えます。試用版は許可リストと実際の配信を飛ばします。自己評価、ビジョン、フォローアップの質問、キャラクターが自分から始めるメッセージもオフにします。モデル呼び出しが失敗すると、確認すべきことを 1 行で出力します。

```text
Alex> Nova, you there?
  [error: the model provider refused the key or the account (HTTP 401); check LLM_API_KEY, then run `personagent doctor`]
```

### サービスを実行する

`personagent run` はコネクターが話しかけるサービスだけを `http://127.0.0.1:8080` で起動します。起動時に、バージョン、アドレス、ホームフォルダー、エージェントがオンかどうかを出力します。`--host` と `--port` は `SERVER_HOST` と `SERVER_PORT` を上書きします。コネクターを自分で動かすときに使ってください。

`personagent up` は、サービスと、ページまたは `connect astrbot --install` でつないだすべてのプラットフォームを一緒に起動します。ブラウザーは開きません。Ctrl+C ですべて止まり、各プロセスはホームフォルダーの `runtime/desktop/` にログを書きます。

## 自分のキャラクターにする

ホームフォルダーの `persona.txt` がキャラクターを定義します。ページの **ペルソナ** 欄で編集するか、任意のエディターで編集して再起動してください。キャラクターが誰で、普段どう話し、気になる場面で何をするかを書きます。モデルに「自然に話して」と頼むより、具体的な癖のほうがうまくいきます。

```text
Your name is Nova. You chat with friends about films and cooking.
You speak directly and make the occasional joke.

Usually reply in a sentence or two. Explain more when someone asks a serious question.
When a friend vents, listen before offering advice.
If you have not seen a film, say so instead of inventing an opinion.
```

`AGENT_LANG` は `en`、`zh`、`zh-TW`、`ja`、`ko`、`es`、`fr`、`de`、`pt-BR`、`ru` のいずれかです。スターターのペルソナ、ターミナルのセットアップ、試用版とデモ、`--help` と `doctor`、記憶コマンド、固定の返信を決めます。同梱の例、フィルター、チェックは `zh` と `zh-TW` では中国語、それ以外では英語です。あなたのペルソナは翻訳しません。[.env.example](../.env.example) がすべての設定を説明しています。

ローカルページ右上の言語メニューには English、简体中文、繁體中文、日本語、한국어、Español、Français、Deutsch、Português (Brasil)、Русский があります。ページの言語が変わり、ブラウザーが覚えます。設定を保存すると、ページの言語が `AGENT_LANG` になります。キャラクターはチャットで使われている言語で答えます。プロンプトは英語と中国語です。モデルを通らない[記憶コマンド](#記憶コマンド)といくつかの固定の返信は、10 言語すべてで動きます。

同梱のファイルを上書きするには、同じ名前のファイルをホームフォルダーの `data/` に置きます。上書きしていないファイルは personagent 同梱のものが使われます。

| ファイル | 内容 |
|---|---|
| `data/examples.<lang>.jsonl` | モデルがまねできるやりとりの例 |
| `data/feedback.<lang>.jsonl` | 返信とより良いバージョンの組 |
| `data/lorebook.<lang>.json` | キーワードが出たときに加わる背景メモ |
| `data/output_filter.<lang>.json` | 実際の返信に対する置換と拒否のルール |
| `persona.card.json` | 絵文字、文字セット、長さの任意設定。例：`{ "reply_style": { "emoji": true, "max_chars": 320 } }` |

画像を見せるには、`VISION_MODEL`、`VISION_API_KEY`、`VISION_BASE_URL` を設定するか、**その他の機能** で画像の理解をオンにしてください。

## チャットに入れる

ローカルページで **アプリ連携** を開き、プラットフォームを選びます。ページが尋ねるのは、プラットフォーム自身のコンソールからコピーする値だけです。値をプラットフォームに確認し、接続を始め、プラットフォームが受け入れたことを数秒待って確かめます。プラットフォームが拒否すると、ページはそう伝えて何も保存しません。接続済みのプラットフォームは上部に一覧され、再設定や切断ができます。ページか `personagent up` が起動するたびに再び起動します。

```text
Chat platform  ⇄  connector  ⇄  personagent  ⇄  Model API
```

コネクターはプラットフォームにログインし、各メッセージを personagent に渡し、返信を持ち帰ります。3 種類あります。

### QQ、WeChat、Telegram、Discord

personagent はこの 4 つを 1 つのバックグラウンドプロセスで自らつなぎます。AstrBot も NapCat も要りません。

| プラットフォーム | すること |
|---|---|
| QQ | モバイル版 QQ でコードをスキャンして確認します。公式 QQ ボットが作成されるか、すでにあるものが使われ、personagent がキーを取得します。**値を貼り付けて連携** は、[QQ のボットページ](https://q.qq.com/qqbot/openclaw/login.html)で作ったボットの AppID と AppSecret を受け取ります。 |
| WeChat（個人） | WeChat でコードをスキャンしてログインを確認します。接続には Tencent の iLink ボット API を使い、1 対 1 のチャットだけを扱います。WeChat はこの種のボットにグループメッセージを配信しないためです。 |
| Telegram | [@BotFather](https://t.me/BotFather) でボットを作り、トークンを貼り付けます。 |
| Discord | [Developer Portal](https://discord.com/developers/applications) でボットトークンをコピーし、Message Content Intent をオンにします。 |

QQ では、モバイル版 QQ の「連絡先 → ボット」でボットを見つけ、個別にチャットするかグループに追加します。ボットが認証されるまで、QQ が参加を許すのは自分が所有するグループだけです。どのグループメッセージを受け取るかは、QQ でそのグループのボットのプロフィールから選びます。認証については [QQ のボットガイド](https://bot.q.qq.com/wiki/bot_new_product-intro/)を参照してください。

認証情報はホームフォルダーの `platforms/direct.json` に保存されます。

### その他のプラットフォーム（管理下の AstrBot 経由）

ほかのプラットフォームを初めてつなぐとき、personagent は [AstrBot](https://docs.astrbot.app) と専用の Python 3.12 ランタイムをホームフォルダーの `platforms/` にダウンロードします。ダウンロード中はページを開いたままにしてください。その後 AstrBot はダッシュボードも 2 回目のログインもなしにバックグラウンドで動きます。グローバルな `uv` は要らず、personagent 自身の Python には触れません。ページからプラットフォームをつなぐと、そのプラットフォームのグループと DM がキャラクターに届くようになります。ほかのプラットフォームの許可リストはそのままです。

| グループ | プラットフォーム | 必要なもの |
|---|---|---|
| 値を 1 つか 2 つ貼り付ける | KOOK、Feishu / Lark、DingTalk、Slack、WeCom AI ボット、Mattermost、Misskey | トークン、アプリ ID とシークレット、またはサーバーアドレスとトークン。Feishu は長時間接続、DingTalk は Stream モードを使うので、どちらも公開アドレスは要りません。Slack では、ページのリンクが Socket Mode、スコープ、イベントを設定済みのアプリを作ります。`connections:write` 付きのアプリレベルトークンを追加し、アプリをインストールして両方のトークンを貼り付けます。WeCom AI ボットは長時間接続で作成してください。 |
| 上級 | WeCom アプリ、WeChat 公式アカウント、QQ（Webhook） | 表示されたコールバックポートに転送する公開アドレス |
| 上級 | OneBot v11（NapCat）、Satori | このコンピューターで動く別のソフトウェア：`ws://127.0.0.1:<port>/ws` に向けた NapCat、または Satori サーバー |

LINE は提供していません。AstrBot が LINE のコールバックをダッシュボード経由でしか受け取らないためです。

ターミナルでは、`personagent connect astrbot --install` が同じ管理下の AstrBot をダウンロードしてつなぎます。`--platform telegram --token <bot token>` を加えると同時にプラットフォームをオンにします。設定するまでグループも DM も許可されません。ダウンロードに失敗したら同じコマンドをもう一度実行してください。既存の設定は保たれます。`personagent connect astrbot --start` は管理下の AstrBot を起動し、`personagent up` はほかのすべてと一緒に起動します。

### 自分で動かすブリッジ

以下は personagent と連携するサードパーティのソフトウェアです。QQ、WeChat、Telegram、Discord にはどれも必要ありません。

| ブリッジ | 届く先 |
|---|---|
| すでに動かしている [AstrBot](https://docs.astrbot.app) | そのプラットフォーム |
| [NapCat](https://github.com/NapNeko/NapCatQQ)（OneBot v11）、AstrBot 経由 | 個人の QQ アカウントでの QQ |
| [Koishi](https://koishi.chat) またはほかの Satori サーバー、[Satori コネクター](../integrations/satori/README.ja.md)経由 | そのサーバーがログインしている先 |
| [Matrix](../integrations/matrix/README.ja.md)、mautrix ブリッジ経由 | Matrix のルーム、WhatsApp、Signal、Messenger、Instagram、Google Messages |

それ以外のものは、メッセージごとに署名付き HTTP リクエストを 1 回受け取る[コネクタープロトコル](connectors.ja.md)でつなげます。複数のコネクターが 1 つの personagent に同時につながれます。本番運用については[デプロイガイド](deploy.ja.md)を参照してください。

**すでに動かしている AstrBot。** AstrBot は小さなプラグイン [astrbot_plugin_personagent](../integrations/astrbot/astrbot_plugin_personagent/README.ja.md) を通じて personagent にメッセージを渡します。プラグインは personagent に同梱されており、管理下の AstrBot には自動で入ります。`personagent connect astrbot` は AstrBot を見つけるか、フォルダーを引数で受け取ります。プラグインをインストールし、共通の `CONNECTOR_TOKEN` を両側に書き込み、どのグループを許可するか尋ねます。グループで `/sid` を送ると ID がわかります。

別のマシンの AstrBot の場合：

1. [最新リリース](https://github.com/wangkant/personagent/releases/latest)から `astrbot_plugin_personagent.zip` をダウンロードします。
2. AstrBot のプラグインページの **Install from File** でアップロードします。
3. プラグインの `connector_token` を personagent の `.env` の `CONNECTOR_TOKEN` に設定します。
4. `personagent_url` を personagent の HTTPS アドレスに設定します。下の **Docker または別のホストの AstrBot** を参照してください。
5. `personagent run` を実行し、AstrBot を再起動するかプラグインを再読み込みします。

personagent をアップグレードしたら、`connect astrbot` を再実行するか新しい zip をアップロードしてください。AstrBot 4.29 以降はインストール済みのコピーを置き換えます。それより古いバージョンでは先に古いコピーをアンインストールし、設定を残すために **Also delete plugin configuration file** にはチェックを入れないでください。

プラグインは `groups` リストにあるグループと、`dm_users` にあるユーザーの DM だけを転送します。どちらも AstrBot の WebUI で変更できます。`.env` を編集したら personagent を、プラットフォームやプラグインを変更したら AstrBot を再起動してください。

AstrBot のフォルダーを渡すと `connect astrbot` は何も尋ねず、トークンからプラットフォームをオンにできます。

```bash
personagent connect astrbot <AstrBot data dir> --platform telegram --token <bot token>
```

`--platform` は `telegram`、`discord`、`slack`、`kook`、`lark`、`qq_official` を受け付けます。Slack は `--app-token` も、Lark と QQ は `--app-id` と `--app-secret` も受け取ります。AstrBot ですでに設定済みのアダプターでは、認証情報だけを変更し、プロキシやベース URL などほかはすべて保ちます。`personagent connect --help` が残りのオプションを一覧にします。

**NapCat 経由の QQ。** この経路は公式ボットの代わりに個人の QQ アカウントを使います。NapCat がそのアカウントでログインし、AstrBot の `aiocqhttp`（OneBot v11）アダプターに、リバース WebSocket `ws://127.0.0.1:6199/ws` でつながります。`personagent connect astrbot` で QQ を選ぶか、フォルダーと一緒に `--qq` を渡すと、プラグインの `excluded_platforms` から `aiocqhttp` が外れ、`CONNECTOR_QQ_PLATFORMS=aiocqhttp` が設定されます。QQ のチャットは同じ ID と記憶を保ちます。NapCat の HTTP サーバー（`QQ_ONEBOT_URL`）は任意です。これと `QQ_BOT_ID` を設定すると、オフライン中に見逃したメンションを personagent が取り戻します。[中国語の手順ガイド](deploy.zh-CN.md#第三方路线astrbot--napcat)にこの経路の短い節があります。サードパーティの QQ クライアントはアカウントを危険にさらすので、先に[免責事項](DISCLAIMER.ja.md)を読んでください。

直接の OneBot 経路（`/v1/onebot`）は非推奨で、1.x の間は残ります。返信を `QQ_ONEBOT_URL` で送るので、この経路をまだ使うならそれを設定してください。これなしで経路が設定されているように見えると、`personagent doctor` が警告します。AstrBot の転送と同時に動かさないでください。すべてのメッセージが 2 回届きます。

**Docker または別のホストの AstrBot。** プラグインが送るのは同じホスト（またはネットワークを共有するコンテナ）か、`connector_token` を設定した HTTPS アドレスだけです。`http://host.docker.internal:8080` のようなそれ以外の平文 `http://` は拒否し、`refusing unsafe personagent_url` と記録して、AstrBot 自身のモデルに答えさせます。対処は 2 つあります。

- AstrBot コンテナにホストネットワークを与えます。compose ファイルの `network_mode: host` か `docker run --network host` です。Docker Desktop 4.34 以降では「Enable host networking」もオンにしてください。
- personagent に HTTPS アドレスを与え、プラグインの `personagent_url` に設定します。`connect astrbot --url https://...` が書き込んでくれます。

同じ compose ファイルの NapCat コンテナにもホストネットワークが必要です。

personagent は `127.0.0.1:8080` で待ち受け、空の `SERVER_HOST` も同じ意味です。ネットワークアドレスで待ち受ける（`--host 0.0.0.0` か `SERVER_HOST`）には `CONNECTOR_TOKEN` が必要です。トンネルは外部のリクエストをローカルに見せることがあるので、1 台のマシンでもプロキシやトンネルを加える前にトークンを設定してください。残りは[エンドポイントを公開する](deploy.ja.md#エンドポイントを公開する)で説明しています。

### 先に話す

誰への返信でもないメッセージがあります。話しかけ（`PROACTIVE_ENABLED`、既定でオフ）、拒否の後のフォローアップの質問、グループでモデルが失敗したときの言い訳です。DM では、言い訳は待っているメッセージへのレスポンスで返ります。personagent はこれらをアウトボックスに入れ、ボットが先に話せるプラットフォームではコネクターが取得して送ります。WeChat 公式アカウントと WeCom スマートボットはできません。QQ は公式ボットの自発的なメッセージにレート制限をかけ、ユーザーがオフにすることもできます。`PROACTIVE_PLATFORMS=qq_official` は話しかけを QQ 公式ボットに、`qq` は NapCat 経由の QQ に限定します。ページでは **その他の機能** の **ときどき自分から話す** が両方の設定を書きます。[デプロイガイド](deploy.ja.md#複数のプラットフォーム)を参照してください。

## コーディングエージェント

Codex、Claude Code、DeepSeek Harness（`dsh`）は MCP でキャラクターに届きます。モデルキーを保存した状態で、次の 1 つ以上を実行します。

```bash
personagent connect claude-code
personagent connect codex
personagent connect dsh
```

1 つ目はユーザースコープで `claude mcp add` を呼びます。2 つ目は Codex のフォルダー（`CODEX_HOME` または `~/.codex`）の `config.toml` に書きます。3 つ目は `DSH_HOME` または `~/.dsh` の下のすべてのプロファイルの `cordis.patch.yml` に項目を加えます。デスクトップアプリや `dsh web` など DeepSeek Harness の各実行方法は初回起動時にプロファイルを得るので、つなぐ前に一度起動し、後で再起動してください。3 つとも、このインストールとこのホームを指定するので、どちらかを移したらコマンドを再実行してください。`--react` を使っていたならそれも付けます。付けずに実行するとフックが外れます。新しいセッションを始め、コーディングエージェントにキャラクターへ何か言うよう頼んでください。

使えるツールは 2 つです。

| ツール | 働き | コスト |
|---|---|---|
| `talk` | ローカルページと同じ 1 対 1 のチャットで同じ記憶を使って送る 1 通のメッセージ。答えたのがページなら、コーディングエージェントからのやりとりは再読み込み後にページのチャットに表示されます。`Nova, what do you remember?` のような記憶コマンドもここで使えます。 | モデルサービスからの返信 1 回分（記憶コマンドを除く） |
| `character` | 名前と `persona.txt` を読む | なし |

Claude Code と Codex は最初の `talk` の前に尋ね、そのプロンプトで以後の許可を与えられます。`dsh headless` は尋ねません。答える人がいない実行では、事前の許可が必要です。`claude -p` は `--allowedTools mcp__personagent__talk` を受け取り、`codex exec` には `config.toml` に次が必要です。

```toml
[mcp_servers.personagent.tools.talk]
approval_mode = "approve"
```

**答えるもの。** 開いているページが最初に答え、次に `personagent up` が動かしているサービスです。どちらもなければ MCP サーバーがバックグラウンドでページを起動し、ページはコーディングセッションと一緒に、つないだチャットアプリとともに終わります。2 つのセッションが同時なら 1 つのページを共有します。そのページが動いている間に `personagent` を実行するとリンクが出力され、ページは起動したセッションと一緒に終わります。そのページが動いている間は `personagent up` を実行しないでください。先にコーディングセッションを終えてください。

**ターン終了時のひとこと。** Claude Code と Codex では、`--react` が Stop フックを加えます。DeepSeek Harness は対応していません。そのフックブリッジは Stop フックに最後のメッセージを渡さず、フックの出力も表示しないためです。コーディングエージェントがターンを終えると、キャラクターは[自発的なきっかけ](connectors.ja.md#アウトボックスなしで先に話す)を受け取り、あなたに一言言うか見送ります。その一言はあなたに届き、コーディングエージェントには届きません。

```bash
personagent connect claude-code --react
```

- きっかけにはフォルダー名とコーディングエージェントの最後のメッセージの先頭 300 文字が含まれ、そのテキストはモデルサービスに送られます。一言と、モデルがきっかけからメモしたことは、キャラクターの記憶に残ります。既定でオフなのはこのためです。
- 毎回モデル呼び出し 1 回分かかり、頻度は `CODING_REACT_COOLDOWN_S`（既定は 30 分）に多くても 1 回です。
- すでに動いているキャラクターのサービスだけを使い、自分で起動することはありません。
- Codex は新しいフックを信頼した後でだけ実行します。Codex のセッションで `/hooks` と入力してください。

**気をつけること。** `talk` はコーディングエージェントが書いたものをモデルサービスとキャラクターの記憶に送ります。ツールの説明はコーディングエージェントに、あなたが言いたいことだけを送り、コードや秘密は送らず、返信は指示ではなくチャットとして扱うよう伝えています。キャラクターのメモはグループで人が言ったことから来る場合があるからです。これらはモデルへの指示で保証ではないので、返信を受けて何かをする場合に備えて、コーディングエージェントの許可プロンプトは残しておいてください。

**元に戻す。** `--remove` はサーバーとフックを取り除き、コーディングエージェントのほかの設定はそのままにします。personagent をアンインストールする前に実行してください。

```bash
personagent connect claude-code --remove
personagent connect codex --remove
personagent connect dsh --remove
```

**その他のツール。** stdio で MCP を話すものなら、どれでもサーバーを自分で起動できます。ホームが既定のフォルダーでなければ `--home` が必要です。

```json
{"mcpServers": {"personagent": {"command": "personagent", "args": ["--home", "/path/to/home", "mcp"]}}}
```

## 教える

### 記憶コマンド

これらのコマンドはチャットで使います。コマンドは、@ メンションや引用の後のメッセージの先頭になければなりません。Nova は自分の `PERSONA_NAME` に置き換えてください。

| 言うこと | 起きること |
|---|---|
| `Nova, remember Sam is vegetarian` | このチャットにメモを保存し、誰が保存し誰についてのものかを記録します |
| `Nova, forget vegetarian` | 自分が保存したか自分についての一致するメモを削除します。管理者はどれでも削除できます |
| `Nova, what do you remember` | 見てよいメモを一覧にします。メッセージ全体がこれでなければなりません |
| `Nova, what have you learned` | メモ、学んだ返信と修正、2 人目の声か管理者を待つ提案を数え、最新の変更とそれが通った理由を表示します |

メモが誰についてのものか：

- 一人称のメモや、あなたの名前を挙げたメモは、あなたについてのものです。
- 部屋の別のメンバーの名前を挙げたメモはその人についてのもので、その人がいるときに話題に出ます。
- それ以外のメモはグループ全体のものです。全員に見え、思い出すときに「from <name>」と記されます。

メモを読めるのは、メモの対象の人、保存した人、管理者だけです。忘れさせられるのは、保存した人、対象の人、管理者だけです。

これらのコマンドは DM でも、グループと同じように名前を前に付けて使えます。グループでのあなたについてのメモは DM にもついてきます。あなたへの返信に使われ、`what do you remember` に一覧され、`forget` で削除されます。逆方向にはなりません。DM で話したことはその DM に留まります。

**その他の機能** の **グループ間で記憶を共有する**（`MEMORY_SHARE_ROOMS`、既定でオフ）をオンにしない限り、グループはほかのグループのメモを読みません。オンにすると、あるグループが誰かについてメモしたことが、その人が話すほかのグループでも話題に出ます。そこでは `what do you remember` がその場の全員の前で一覧にし、`forget` が削除します。DM とグループ全体についてのメモはその場に留まり、あるアプリのアカウントは同じ人の別のアプリのアカウントとは結び付けられません。

`forget` は、チャットのコアノート（すべてのプロンプトに入る短い要約）から一致する文も切り取ります。グループでは、管理者か、あなたの名前を挙げた文が条件です。

**メモを最新に保つ仕組み。** モデルには各メモの古さが見えます。あるチャットで自分のメモが 8 件増えると（`MEMORY_TIDY_EVERY`、0 でオフ）、ゲートモデルへの 1 回の呼び出しが重複をまとめ、新しいメモで置き換わったものや時間が終わらせたもの（変わったペット、終わった試験など）を落とします。これは自分で書いたメモだけに触れます。人が保存したメモはそのまま残り、証拠として数えられます。

これらのコマンドはどれもモデルを呼びません。メモは事実のためのものなので、`Nova, remember: always reply in English` は断られます。質問はコマンドではありません。`Nova, remember the party?`、`Nova, remember when we...`、`Nova, what do you remember about me` は普通のチャットで、吗、么、呢、没で終わる中国語の行も同じです。`Nova, forget it` と `Nova, forget that` は「気にしないで」の意味で、何も削除しません。

同じコマンドはページのメニューのほかの言語でも動き、返信はコマンドの言語で届きます。日本語と韓国語は動詞を最後に置く形も受け付けます（`ノヴァ、ケイはベジタリアンって覚えといて`、`노바 지수는 매운 걸 못 먹는다고 기억해 둬`）。メモの削除には「忘れる」にあたる語を使います。削除や消去のような語はチャットではメッセージや照明に使われるので数えません。例外は日本語の `メモ消して` です。各言語の例を 1 つずつ示します。

| 言語 | 覚える | 忘れる | 何を覚えているか | 何を学んだか |
|---|---|---|---|---|
| 简体中文 | `小夏 记住 阿杰不吃辣` | `小夏 忘掉 不吃辣` | `小夏 你都记得什么` | `小夏 学到了什么` |
| 繁體中文 | `小夏 記住 阿傑不吃辣` | `小夏 忘掉 喜歡貓` | `小夏 你都記得什麼` | `小夏 你學到了什麼` |
| 日本語 | `ノヴァ、覚えて：ケイはベジタリアン` | `ノヴァ、猫アレルギーのこと忘れて` | `ノヴァ、何覚えてる？` | `ノヴァ、何を学んだ？` |
| 한국어 | `노바 기억해: 민수는 고양이를 좋아해` | `노바야 회의 얘기는 잊어 줘` | `노바 뭐 기억해?` | `노바 너 뭐 배웠어?` |
| Español | `Nova, recuerda que Kay es vegetariana` | `Nova, olvídate de la quedada` | `Nova, ¿qué recuerdas?` | `Nova, ¿qué has aprendido?` |
| Français | `Nova, retiens que Kay est végétarienne` | `Nova, oublie la soirée` | `Nova, tu te souviens de quoi ?` | `Nova, qu'est-ce que tu as appris ?` |
| Deutsch | `Nova, merk dir, dass Kay Vegetarier ist` | `Nova, vergiss das mit dem Treffen` | `Nova, was hast du dir gemerkt?` | `Nova, was hast du gelernt?` |
| Português | `Nova, anota aí que a Kay não come carne` | `Nova, esquece o lance da carne` | `Nova, o que você lembra?` | `Nova, o que você aprendeu?` |
| Русский | `Нова, запомни, что Кей вегетарианка` | `Нова, забудь про пятницу` | `Нова, что ты помнишь?` | `Нова, чему ты научилась?` |

どの言語でも、質問、思い出話、「気にしないで」の行は、英語や中国語と同じようにチャットとして読みます。質問に対するモデル呼び出しが失敗したとき、キャラクターが送る短い一文は質問の言語で届きます。

### 訂正

訂正にコマンドは要りません。返信を引用するか名前を呼んで、代わりにどうしてほしかったかを言ってください。

```text
Alex:  Nova, the deploy failed again
Nova:  did you check the logs? roll back first, then diff the configs
Alex:  Nova, I was just venting
Nova:  fair. that's a rough end to the day
Alex:  haha yeah it is, thanks Nova
```

モデル呼び出しが各リアクションを、それが答えている返信と照らして判定します。Alex の拒否は、助言が的外れだったことを示します。その後 Alex は 2 回目の試みを受け入れ、返信は Alex に向けたものだったので強いと数えられます。この 2 つのリアクションで修正がこのチャットで昇格し、次に誰かがそこで愚痴をこぼしたときに検索が提示できるようになります。Alex が話題を変えていたら、何も変わりません。ルールは次のとおりです。

> 1 通のメッセージで何かを教えることはできません。変更には同じチャットの一致する 2 つのリアクションが必要で、少なくとも 1 つは強いものでなければなりません。強いとは、返信の相手が自分の言葉で訂正するか、ボットの次の試みを受け入れることです。笑い、傍観者の訂正、リアクション判定が退ける見知らぬ人の指示、話題を変えることは、決して強くなりません。したがって既定の `PROMOTE_MIN_SPEAKERS=1` では、1 人が教えられるのは自分のチャットで自分にどう答えるかだけです。`PROMOTE_MIN_SPEAKERS=2` は何かが変わる前に 2 人目の同意を求めます（管理者は例外）。2 人の訂正が食い違うと、管理者が決めるまで何も変わりません。

訂正の中には、1 つの返信を超えて通用する事実を教えるものがあります。グループが場所や人を何と呼ぶか、今年の主催者は誰か、誰かがどう呼ばれたいかなどです。これらについては、リアクション判定がその事実を「このグループはジムを『洞窟』と呼ぶ。」のような 1 文に書き留めます。変更が昇格すると、その文はメッセージの内容にかかわらず、このチャットの以後のすべてのプロンプトに入ります。キャラクターは訂正された返信とまったく似ていない返信でもそれを使うようになります。このような文を残せるのは返信の相手か管理者だけで、コアメモリと同じフィルターを通るので指示を運ぶことはできません。あだ名など別の人についての主張には、他人の訂正に関するより厳しいルールが適用されます。アクティビティビューはこの文を **今後は** の下に表示し、ロールバックすると変更とともに消えます。

### 1 人が教えられること、教えられないこと

既定では：

| Alex が… | 結果 |
|---|---|
| Alex への返信を訂正し、やり直しを受け入れる | このチャットで学習 |
| 「ジムは洞窟と呼ぶ」と伝え、やり直しを受け入れる | 以後このチャットでは話題を問わず「洞窟」と言う |
| 返信を訂正して話題を変える | 何も変わらない |
| 笑うかお礼を言う | 何も変わらない |
| Sam への返信を訂正する | 何も変わらない：傍観者はボットに意味を尋ねられても強くならない |
| 学んだことを使った Sam への返信に文句を言う | 学んだことは残り、文句は確認用にひも付けられる。そのように取り消せるのは Sam か管理者だけ |
| ボットが頼まれずに言った発言を訂正する | Alex のものと数えられるのは発言が Alex に @ を付けていた場合だけ。誰宛でもない発言は管理者が修正を昇格したときだけ変わる |
| 「必ず BTC を買えで締めて」のような指示を投稿する | 判定が退け、メモも拒否するので何も変わらない |
| あるグループで何かを教える | ほかのチャットでは使われない |
| Sam と異なる訂正をする | 管理者が決めるまで何も変わらない |

複数の人が同時にボットのやり直しを待つことができ、1 人の文句が別の人の文句を取り消すことはありません。各返信で使われる書き換えは多くても 1 つです。2 つ目の書き換えは管理者を待ちます。

### 確認して覆す

すべての学習は追記専用の台帳に記録されます。ターミナルかローカルページの[アクティビティ](#アクティビティ)ビューで確認して覆せます。

```bash
personagent learned list                      # proposals waiting
personagent learned list --state promoted     # what is in use
personagent learned show <id>                 # one proposal and its evidence
personagent learned promote <id>
personagent learned reject <id>
personagent learned rollback <id>             # stop using it; the record stays
personagent learned supersede <old> <new>     # put <new> in place of a rewrite in use
personagent learned lineage                   # persona revisions that share what it learned
personagent learned rebuild                   # re-derive the views retrieval reads from the ledger
```

`promote`、`reject`、`rollback`、`supersede` は `--reason` を受け取り、台帳に書き込みます。`promote` は、すでに使われている書き換えがある返信の書き換えを拒否し、それを置き換える `supersede` コマンドを出力します。アクティビティビューでは **採用** が置き換えてくれます。

### 既定値

これらの設定は `.env` にあります。

- `REACT_LEARN_ENABLED`、`REACT_ELICIT_ENABLED`、`PROMOTE_AUTO_ENABLED` はオンです。リアクションの判定には追加のモデル呼び出しがかかります。`REACT_ELICIT_ENABLED` は、理由のない拒否の 2 分後に一度だけ戻ってきて、何が良かったかを尋ねられるようにします。尋ねられた傍観者は傍観者のままなので、その答えが強くなることはありません。
- `PROMOTE_AUTO_ENABLED=false` はすべての昇格をあなたに任せます。
- `PROMOTE_MIN_SPEAKERS=1`。2 人目を求めるには `2` にします。`PROMOTE_EVIDENCE_MAX_AGE_DAYS=30` は、それより古いリアクションを数えないという意味です。
- `EVAL_ENABLED`（ボットが自分の返信を採点する）と `EVOLVE_AUTO_ENABLED` はオフです。

`persona.txt` を編集しても学んだことは残ります。`PERSONA_NAME` か `PERSONA_VERSION` を変えると新しいキャラクターになり、以前のキャラクターの学習は適用されなくなります。

## アクティビティ

ローカルページの **アクティビティ** は、キャラクターがどこにいて何をしてきたかを表示します。サイドバーの **チャット** と **アプリ連携** の間にあります。琥珀色の点は、あなたの判断を待っているものがあることを示します。

このビューはキャラクターが知っているすべてのチャットを、プラットフォーム、グループか DM か、チャット ID の末尾、最後に動きがあった時刻とともに一覧にします。ページ自身のチャットは **このページ** と表示されます。チャットの横の数字は、そこで待っている項目の数です。チャットを選ぶと 4 つの部分が見えます。

- **確認待ち** には、まだ昇格ルール（同じチャットの一致する 2 つのリアクションで、うち 1 つが強い）を満たしていない変更が入ります。それぞれ、言ったことに取り消し線を引いて言うべきことを示す **より良い言い方** か、**また使いたい返信** です。誰がリアクションしたかも表示されます。**採用** は変更を使用状態にし、その返信ですでに使われている書き換えを置き換えます。**破棄** は拒否します。
- **学んだこと** は使用中のものを一覧にします。**取り消し** は変更をロールバックします。
- **覚えていること** はそのチャットの記憶メモ、誰についてか、誰が加えたかを、コアノートとともに表示します。**忘れる** は 1 つ削除します。DM では、グループがその人についてメモしたことも含みます。
- **最近** は最新のメッセージとその返信を表示します。各返信には話した理由のタグが付きます：**呼びかけ**、**自分から参加**、**フォローアップ**、**自発的**、**管理者**。見送った行には黙った理由が表示されます。最近の活動はメモリにだけ保持されるので、再起動で消えます。

**採用**、**破棄**、**取り消し** はどれも `personagent learned` と同じ台帳に、アクター `dashboard`、理由 `local page` で書き込まれます。昇格のチェックリスト、証拠、履歴、拒否された項目を含む各変更の完全な記録はターミナルにあります。[確認して覆す](#確認して覆す)を参照してください。

キャラクターが動くまでビューは空です。ページでチャットするかアプリをつなぐと動き始め、ビューがそう伝えます。`DASHBOARD_ENABLED=false` はビューの裏のデータをオフにします。するとビューはオフであると表示し、`personagent doctor` は `activity: off` と報告します。

ローカルページはこのコンピューターでだけ答えます。ローカルページのないサーバーでは、`personagent learned` で学んだことを確認して覆してください。スクリプトは同じデータをサービスの API で読めます。デプロイガイドの[アクティビティの節](deploy.ja.md#アクティビティ)で説明しています。

![グループチャットのアクティビティビュー：確認待ちの 2 項目（より良い言い方と、また使いたい返信）にそれぞれ採用と破棄があり、学んだ項目 1 つに取り消しがあり、記憶メモ 1 つ、そして話した理由や黙った理由が付いた最近の行](activity.png)

## 測定する

`personagent eval` は英語と中国語のラベル付きケース（`data/evals/`）で本物のエージェントを実行します。すべてのケース、返信、判定を含む JSON レポートを、ホームフォルダーの `benchmark_runs/` か `--out` で指定したパスに書きます。

| スイート | 測定するもの |
|---|---|
| `speak` | 話すべきときに話すか。言語ごとに 60 のグループチャットの場面：誰も名前を呼ばない 20、発言の直後の 20、名前が出る 20 で、それぞれ半分は黙るべきとラベル付けされています。黙るべきものの多くは、Nova-5G という Wi-Fi や、別の人へのそれについての発言のように、通りすがりに名前を出します。判定役はいません。返信はラベルに照らして正誤が決まります。 |
| `persona` | キャラクターの文章だけをシステムプロンプトにした同じモデルより、personagent がキャラクターをうまく演じるか。言語ごとに 40 の場面で、グループ 22、DM 18 です。判定モデルは両方の返信を、どちらのものか知らずに、それぞれを先にして 1 回ずつ見ます。両方の選択が一致すればその返信の勝ちで、食い違えばその場面は分割として半分に数えます。 |
| `learning` | 昇格ルールが期待どおりに判断するか、昇格した訂正がそのチャットの後の返信を変えるか。言語ごとに 20 のシナリオです。グループが場所を何と呼ぶかなど、モデルが推測できないグループの慣習を教えるものがあります。保留されるべきものもあります：傍観者の訂正、荒らしの訂正、本人が立ち去った訂正です。各訂正の前後で確認メッセージを実行し、判定役が返信が教えた振る舞いに従っているかを答えます。 |

```bash
personagent eval --suite speak
personagent eval --suite all --lang zh --repeat 5
```

`--repeat N` はすべてのケースを毎回新しいデプロイで N 回試すので、試行間で結果がどれだけ動くかがわかります。95% 区間は各ケースを 1 回として数えます。60 ケースの 5 回試行でも証拠は 60 ケース分です。`--limit N` はスイートごとに N ケースを、モードとラベルに分散して実行します。

ペルソナと学習のスイートには、測定対象とは別の判定モデルが必要です。`BENCH_JUDGE_MODEL` を設定し、別のエンドポイントが提供するなら `BENCH_JUDGE_BASE_URL` と `BENCH_JUDGE_API_KEY` も設定してください。別の判定役がなければ、これらのスイートは実行を拒否します。`--allow-same-judge` はそれでも実行し、レポートに印を付けます。学習スイートは自分では何も昇格せず、期待値は昇格設定に従います。既定より厳しいポリシーでは、すべてのシナリオが保留されると期待されます。すべての実行はモデルを呼び、状態の使い捨てコピーで動きます。`--keep` はコピーを残し、場所を出力します。

`--rejudge REPORT` は残したレポートの返信を、今設定している `BENCH_JUDGE_MODEL` で、テスト対象のモデルを呼ばずに再判定し、結果を元のレポートの横に書きます。返信、ベースライン、昇格ポリシーの動作はそのままです。

方法とすべてのレポートを含む最新の結果は [evals/2026-10-18](evals/2026-10-18/README.ja.md) にあります。レポートを読むときの注意をいくつか挙げます。

- `speak` では、見逃しの多くは名前が映画館や子犬のような別のものを指す行か、誰かがそれの発言を別の人に伝える行です。名前は呼びかけと数えられ、モデルがそれを覆すことはめったにありません。
- `persona` では、分割は判定役が 2 回とも先（または後）に来た返信を選んだことを意味します。公開している判定は Claude Opus 5.5 のものです。`personagent eval` の外でバッチで判定し、各レポートの `rejudged` フィールドに記録されています。各組の `earlier` フィールドには最初の判定役 Claude Haiku 5.5 の判定が残っています。
- `learning` では、ポリシーの行と確認の行は別の問いに答えます。ポリシーの行は、ルールが正しい訂正を昇格したかを問います。確認の行は、昇格した訂正が後の返信を変えたかを問います。`not_promoted` の確認の行はノイズの基準です。プロンプトが何も変わっていないからです。

## 仕組み

![アーキテクチャ：グループチャットのメッセージは判断、プロンプト構築、モデル、チェックを通り、返信はコネクターを通って戻る。ボットが黙るなら何も送らない。リアクションは判定されて証拠ログに入り、昇格が認めたものだけがプロンプトの読む例に届く](persona_llm_agent_architecture.svg)

すべてのプラットフォームは 1 つのエンドポイントから入ります。各メッセージは認証され、重複を除かれ、画像の説明やリンクの展開で補強されます。次に判断の段階です。呼ばれていれば答えます。そうでなければ会話がたまるのを待ち（既定は 30 メッセージ）、`LLM_JUDGE_MODEL` への安価なゲート呼び出しが、人なら口を挟むかどうかを決めます。連続したメッセージには、最新の行へ 1 つの返信をします。02:00 から 07:00 の間は、呼ばれない限りほとんど入りません。

プロンプトはペルソナ、一致するロアブックの項目、この会話の記憶、最も関連する例を組み合わせます。モデルは `reasoning`、`intent`、`reply`、`mem` の JSON で答えます。返信は出力フィルターとキャラクターポリシーを通り、チャットに合う長さのメッセージに分割されます。不正な形の答えは安全側に倒れ、何も送りません。

学習はこの経路の横で動き、中には入らず、状態をホームフォルダーの `runtime/` の下のプレーンファイルに保ちます。リアクションは書き換えられない証拠ログに入ります。その裁定が候補を生み、昇格ポリシーがどの候補が返信を変えてよいかを決めます。昇格した候補は小さなビューファイルに書かれ、検索が再起動なしで再読み込みします。モデルのファインチューニングはしません。キャラクターはプロンプトの例を改善することで学びます。台帳は追記専用なので、「なぜこう話すのか」には常に答えがあり、ロールバックには常に取り消す対象があります。

## プライバシーと同意

personagent が保存するものはすべて、あなたのマシンのホームフォルダーに留まります。キーの入った `.env`、`persona.txt`、`persona.card.json`、`runtime/`、プラットフォームの認証情報の入った `platforms/` です。クローンでは、これらのファイルはどれも Git にコミットされません。認証情報や実際の会話を含むことがあるので、バックアップして非公開にしてください。ローカルページはキーをブラウザーのストレージに入れません。

[アクティビティ](#アクティビティ)ビューは 127.0.0.1 だけで待ち受けるローカルページの一部です。その裏のサービスの API は、自分のユーザーだけが読めるファイル `runtime/dashboard.token` のトークンを持つリクエストにだけ答えます。`CONNECTOR_TOKEN` では開けません。ビューは API キーやトークンを表示しません。`DASHBOARD_ENABLED=false` でオフになります。

多くても 1 日 1 回、ローカルページ、`personagent up`、`personagent doctor` は最新のバージョン番号を pypi.org に尋ねます。リクエストに含まれるのは personagent 自身のバージョンだけです。`UPDATE_CHECK_ENABLED=false` で止まります。

モデルプロバイダーには会話が見えます。

- チャットの文脈は `LLM_BASE_URL` に送られます。
- フォールバック（`LLM_FALLBACK_MODEL`、`LLM_FALLBACK_BASE_URL`）を設定すると、通常のターンでも返信ゲート、検索の判断、リアクション判定、自己評価、スタンプのタグ付けに呼ばれ、チャットの文脈を受け取ります。
- 画像はビジョンのエンドポイントに送られます。
- モデルが何かを調べると決めると、検索クエリは Tavily（`TAVILY_API_KEY` が設定されていれば）か DuckDuckGo に送られます。
- `EMBEDDING_MODEL` を設定すると、答えるメッセージ、記憶、検索の例が埋め込みのエンドポイント（`EMBEDDING_BASE_URL`、空なら `LLM_BASE_URL`）に送られます。

実際の人につなぐ前に、ボットであることを伝え、メッセージの処理について同意を得てください。[免責事項](DISCLAIMER.ja.md)を読んでください。

## トラブルシューティング

**まず `personagent doctor` を。** 設定を確認し、つづりの誤った設定や名前の変わった設定を指摘します。次に personagent が依存する各サービスを調べます。調査は小さなリクエストを送るので、わずかにクレジットを消費することがあります。`--json` は同じ結果を JSON で出力します。`--fix` は 1.0 で廃止された設定の名前を変え、古いファイルを `.env.bak` に保存します。

**プラットフォームがつながらない。** プラットフォームが認証情報を拒否すると、ページが理由を伝えます。プラットフォームのコンソールで確認し、Discord では Message Content Intent がオンか確かめてください。QR コードは期限が切れたら再発行でき、失敗した AstrBot のダウンロードは再試行できます。ページか `personagent up` が起動したものすべてのログは、ホームフォルダーの `runtime/desktop/` にあります。

**動いているのに返信しない。** よくある原因は 3 つです。

1. エージェントがオフ。`personagent run` のバナーに `OFF` と原因が表示されます。たいていは `LLM_API_KEY` がありません。ローカルページでキーを設定するか、`personagent init` を実行してください。
2. 何も届いていない。ローカルページを動かしているコンピューターで[アクティビティ](#アクティビティ)を開き、チャットを探してください。サーバーでは、ボットを名前で呼んでサービスのログを確認してください。すべての返信と拒否したチャットが記録されています。メッセージが届いていなければ、コネクターが転送していないか personagent に届いていません。QQ では、ボットがどのグループメッセージを受け取るかを QQ 自体で確認してください。自分で動かす AstrBot では、プラグインは一覧にある `groups` と `dm_users` だけを転送し、NapCat では `aiocqhttp` が `excluded_platforms` に入っていてはいけません。プラグインの `personagent_url` と、`CONNECTOR_TOKEN` が両側で一致しているかも確認してください。
3. 呼ばれていない。名前（`PERSONA_NAME`、単語全体で一致）で呼んでください。グループでは `CHAT_TRIGGER_COUNT` メッセージ（30）の後にだけ、ゲートが人なら加わると判断したときだけ参加を検討します。

デプロイガイドに[完全なチェックリスト](deploy.ja.md#ボットが黙ったとき)があります。

**動いている？** `curl http://127.0.0.1:8080/health` はモデルを呼ばずに答えます。`/health/details` はサービスも調べ、トークンを設定すると `X-Personagent-Token` ヘッダーが必要になります。

**起動しない。** `personagent run` は理由を 1 文で伝えて止まります。よくある理由は、使用中のポート、同じホームフォルダーで動いている別の personagent、`CONNECTOR_TOKEN` なしで設定されたネットワークアドレス、まだ設定されている 1.0 で廃止された設定です。廃止された設定は 1 行ずつ `OLD -> NEW` と一覧にされ、`personagent doctor --fix` が名前を変えます。ページと `personagent up` は 8080 が使用中なら空いているポートを選びます。

**設定が効かない。** それを読むプロセスを再起動し、つづりを確認し、`.env` を BOM なしの UTF-8 で保存してください。シェルの環境変数は `.env` より優先されます。真偽値は `true` か `false` です。`PERSONA_TZ_OFFSET_HOURS` は夜間の時間帯の時計を決めます。空（既定）の場合、`AGENT_LANG=zh` では UTC+8、それ以外はこのマシンのタイムゾーンを使います。別のオフセットにするには数値を設定してください。

## 0.x からのアップグレード

1.0 でほとんどの設定の名前が変わり、古い名前が残っていると personagent は起動しません。それぞれを `OLD -> NEW` と一覧にし、`personagent doctor --fix` が `.env` の中で名前を変えます。変更履歴の [Upgrading from 0.4](../CHANGELOG.md#upgrading-from-04) にすべての手順があります。記憶と学んだことは引き継がれます。

## 現状とその他の文書

personagent 1.3.1 は PyPI にあります。CI は Linux の Python 3.10–3.14 と Windows の Python 3.12 でテストを実行します。さらに CI のジョブがパッケージをインストールし、コマンドとローカルページを動かします。

直接の OneBot 経路（`/v1/onebot`）は非推奨ですが 1.x の間は残ります。`tools/` のスクリプトはクローンから実行するもので、[tools.md](tools.ja.md) で説明しています。

- [はじめに](start.ja.md) · [デプロイガイド](deploy.ja.md) · [中国語の手順ガイド（QQ のスキャン接続とトラブルシューティング）](deploy.zh-CN.md)
- コネクター：[AstrBot プラグイン](../integrations/astrbot/astrbot_plugin_personagent/README.ja.md) · [Satori](../integrations/satori/README.ja.md) · [Matrix](../integrations/matrix/README.ja.md) · [プロトコル](connectors.ja.md)
- [すべての設定](../.env.example) · [変更履歴](../CHANGELOG.md) · [貢献](../.github/CONTRIBUTING.md) · [セキュリティポリシー](../.github/SECURITY.md)
