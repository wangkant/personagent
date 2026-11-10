<p align="center">
  <img src="https://raw.githubusercontent.com/wangkant/personagent/main/assets/personagent-cover.webp" alt="personagent" width="100%">
</p>

<h3 align="center">黙るべきときを心得ていて、訂正されると学ぶ、グループチャットのためのキャラクター。</h3>

<p align="center">
  <a href="https://pypi.org/project/personagent/"><img src="https://img.shields.io/pypi/v/personagent?style=flat-square&label=PyPI&labelColor=24292f&color=0969da&cacheSeconds=3600" alt="PyPI"></a>
  <a href="https://github.com/wangkant/personagent/actions/workflows/ci.yml"><img src="https://img.shields.io/github/actions/workflow/status/wangkant/personagent/ci.yml?branch=main&style=flat-square&label=CI&labelColor=24292f" alt="CI"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/Python-3.10%E2%80%933.14-0969da?style=flat-square&labelColor=24292f" alt="Python 3.10–3.14"></a>
  <a href="https://github.com/wangkant/personagent/blob/main/LICENSE"><img src="https://img.shields.io/badge/License-MIT-0969da?style=flat-square&labelColor=24292f" alt="ライセンス：MIT"></a>
</p>

<p align="center"><a href="https://github.com/wangkant/personagent/blob/main/README.md">English</a> · <a href="https://github.com/wangkant/personagent/blob/main/README.zh-CN.md">简体中文</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.zh-TW.md">繁體中文</a> · <strong>日本語</strong> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.ko.md">한국어</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.es.md">Español</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.fr.md">Français</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.de.md">Deutsch</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.pt-BR.md">Português</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.ru.md">Русский</a></p>

*これは英語版 README の翻訳です。基準となるのは英語版で、こちらより新しい場合があります。*

personagent はグループチャットのためのキャラクターです。用意されたものから選ぶか自分で書き、OpenAI 互換の任意のモデルで動かせます。まずは自分のパソコンで話してみて、そのあと同じローカルページから QQ、WeChat、Telegram、Discord、さらに十数個のアプリへ連れていけます。

<p align="center">
  <img src="https://raw.githubusercontent.com/wangkant/personagent/main/docs/welcome.jpg" alt="ローカルページの「アプリ連携」画面。参加できるすべてのプラットフォームが並んでいる" width="960">
</p>

<p align="center"><em>「アプリ連携」は、設定やキャラクターとのチャットと同じローカルページにあります。</em></p>

## personagent を選ぶ理由

<table>
<tr>
<td width="220" valign="top"><strong>黙るべきときを心得ています。</strong></td>
<td valign="top">
呼ばれれば答えます。それ以外のときは、人ならここで口を挟むかをモデルが判断します。<br>
メッセージが立て続けに届いても、返信は 1 回です。
</td>
</tr>
<tr>
<td width="220" valign="top"><strong>確かな訂正から学びます。</strong></td>
<td valign="top">
訂正で教わったこと（たとえば、グループでジムを何と呼んでいるか）は、そのチャットでのその後のすべての返信に反映されます。<br>
変更には、同じチャットからの一致する反応が 2 つ必要で、そのうち 1 つは強い反応でなければなりません。<br>
荒らしや通りすがりの人が学習し直させることはできません。<br>
すべての変更は記録され、どれでも元に戻せます。
</td>
</tr>
<tr>
<td width="220" valign="top"><strong>始めるのが簡単で、グループのいる場所で暮らします。</strong></td>
<td valign="top">
コマンド 1 つで自分のパソコンに開きます。表示は英語、中国語、ほか 8 つの言語から選べます。<br>
モデルのキーを 1 つ貼り付ければチャットできます。10 種類のモデルサービスがプリセットされていて、そのほかの OpenAI 互換サービスも使えます。<br>
アプリの連携は、スマートフォンでのスキャンか、値を 1〜2 個貼り付けるだけです。キャラクターがそこで何をしたかは「アクティビティ」ビューで確認できます。
</td>
</tr>
<tr>
<td width="220" valign="top"><strong>既成のキャラクターにも、自分だけのキャラクターにもできます。</strong></td>
<td valign="top">
既成の性格は 7 つ。そのうち 3 つは、コミュニティですでに描かれてきたキャラクター、DeepSeek クジラ娘、GPT ドラゴン娘、Claude お嬢様です。立ち絵はまばたきし、返信を待つあいだは考え、返信が届くと話します。<br>
ペルソナはいつでも書き直せます。キャラクターが学んだことは残ります。
</td>
</tr>
</table>

- チャットごとに独立した記憶を持ち、頼めば忘れます：`ノヴァ、覚えて：ケイはベジタリアン`、`ノヴァ、忘れて、ベジタリアンのこと`、`ノヴァ、何覚えてる？`（[記憶コマンド](https://github.com/wangkant/personagent/blob/main/docs/guide.ja.md#記憶コマンド)）。グループで誰かについて記録されたことは、その人との DM にも引き継がれますが、逆はありません。
- チャットで使われている言語で返事をします。最初に選べるペルソナは、ページの 10 言語すべてに用意されています。同梱の例、フィルター、プロンプトは英語と中国語です。
- 振る舞いは測定されています。`personagent eval` は、話すタイミング、キャラクターを保てているか、訂正が定着するかを採点します（[結果](https://github.com/wangkant/personagent/blob/main/docs/readme/README.ja.md#測定結果)）。

## はじめに

```sh
python -m pip install personagent
personagent
```

[uv](https://docs.astral.sh/uv/) があれば、`uvx personagent` で個別のインストールなしに実行できます。Windows では、ソースの ZIP をダウンロードして `start.bat` をダブルクリックする方法もあります。デスクトップに personagent のアイコンも置かれます。personagent は Linux の Python 3.10–3.14 と Windows の Python 3.12 でテストされています。

Windows では専用のウィンドウで開きます。macOS と Linux ではブラウザーで開き、`pip install "personagent[app]"` を入れればウィンドウでも開けます。モデルの API キーを貼り付けて **確認してチャット開始** をクリックすると、小さなリクエストを 1 回送ってキーを確認します。まだキーがない場合も、最初から OpenRouter の無料モデルが選ばれていて、そのキーは無料で取得できます。キーを取る前に様子を見たいなら、`personagent demo` が台本のある 3 つの場面を無料で再生します。[スタートガイド](https://github.com/wangkant/personagent/blob/main/docs/start.ja.md)では、ページを画面ごとに説明しています。

## かかる費用

personagent 自体は無料です。料金は、選んだモデルサービスに、そのサービスの料金で支払います。

- **無料で始められます。** OpenRouter の無料モデルは 1 日 50 リクエストまで使えます。リクエストごとにモデルが変わることがあり、無料のプロバイダーの中には受け取った内容を保持するところもあります。Zhipu の `glm-4.7-flash` も無料で、Ollama ならキーなしで自分のコンピューター上でモデルを動かせます。
- **モデルを呼び出すもの。** すべての返信と、2 つの小さなステップです。呼ばれていないときに会話に加わるかどうかの判断と、返信に対する人々の反応の判定です。`personagent doctor` と `personagent eval` もリクエストを送ります。そのほかは[デプロイガイド](https://github.com/wangkant/personagent/blob/main/docs/deploy.ja.md#コスト)にあります。
- **決して呼び出さないもの。** `personagent demo` と記憶コマンドです。

## グループに参加させる

ローカルページで **アプリ連携** を開きます。アプリは次のように分類されています。

| ページ上の表示 | アプリ | 必要なもの |
|---|---|---|
| スキャンで連携 | QQ、個人 WeChat | スマートフォン。WeChat のボットは 1 対 1 のチャットのみ |
| 値を 1〜2 個貼り付け | Telegram、Discord、KOOK、Feishu/Lark、DingTalk、Slack、WeCom AI ボット、Mattermost、Misskey | アプリのコンソールで取得する値。どの値かはページに表示されます |
| 上級 | WeCom アプリ、WeChat 公式アカウント、QQ Webhook、OneBot v11 (NapCat)、Satori | 公開アドレス、またはこのコンピューター上の他のソフトウェア |

認証情報は保存前に確認され、連携済みのアプリは personagent を起動するたびに再び起動します。スキャンで連携するアプリと Telegram、Discord には personagent が自分で接続し、それ以外は personagent がダウンロードしてバックグラウンドで動かす [AstrBot](https://github.com/AstrBotDevs/AstrBot) を経由します。ほかに何かを開く必要はありません。サーバーでは、`personagent up` でキャラクターと連携済みのすべてのアプリをブラウザーなしで起動できます。アプリごとの設定方法は[ユーザーガイド](https://github.com/wangkant/personagent/blob/main/docs/guide.ja.md#チャットに入れる)に、QQ をゼロから一歩ずつつなぐ手順は[中国語のデプロイガイド](https://github.com/wangkant/personagent/blob/main/docs/deploy.zh-CN.md)にあります。

すでにブリッジを運用していますか？

- **AstrBot**：`personagent connect astrbot` でプラグインと共有トークンをインストールします。別のマシン上の AstrBot については[ガイド](https://github.com/wangkant/personagent/blob/main/docs/guide.ja.md#自分で動かすブリッジ)で説明しています。
- **[Koishi](https://koishi.chat)**、またはほかの Satori サーバー：[Satori コネクター](https://github.com/wangkant/personagent/blob/main/integrations/satori/README.ja.md)を使います。
- **[Matrix](https://matrix.org)**（mautrix ブリッジ経由の WhatsApp と Signal を含む）：[Matrix コネクター](https://github.com/wangkant/personagent/blob/main/integrations/matrix/README.ja.md)を使います。

## コーディングエージェント

**セットアップを任せる。** あなたのコンピューターでコマンドを実行できるコーディングエージェントに、下の 1 行を渡してください。エージェントは希望を尋ねたうえで、personagent をインストールしてローカルページを起動します。モデルのキーはそのページにあなた自身が貼り付けるので、キーがエージェントを経由することはありません。

```text
https://raw.githubusercontent.com/wangkant/personagent/main/docs/setup-for-agents.md を読んで、personagent をセットアップしてください。
```

**作業しながらキャラクターと話す。** モデルのキーを設定したら、Claude Code、Codex、DeepSeek Harness（`dsh`）からキャラクターに話しかけられます。

```bash
personagent connect claude-code
personagent connect codex
personagent connect dsh
```

そちらで新しいセッションを開き（DeepSeek Harness は先に再起動してください）、キャラクターに何か言うよう頼んでください。ローカルページと同じ一対一のチャットと記憶です。Claude Code と Codex では、`--react` を付けるとターンの終わりにキャラクターが一言話せるようになります。`--remove` ですべて元に戻せます。権限、`--react` がモデルサービスに送る内容、そのほかの MCP ツールについては[ガイド](https://github.com/wangkant/personagent/blob/main/docs/guide.ja.md#コーディングエージェント)にあります。

## 測定結果

`personagent eval` は、ラベル付けされたチャットの場面を使って実際のエージェントを動かします。2026-10-18 の最新の実行は 1.3.0 で測定しました。同梱のキャラクターを OpenRouter 経由で 2 つのモデルで動かし、各ケースを 3 回ずつ試し、Claude Opus 5.5 がブラインドで判定しています。英語 / 中国語の結果です。

| | deepseek-v4.1-flash | gpt-6-luna |
|---|---|---|
| 話すべきタイミングの判断が正しい（60 場面） | 83% / 80% | 93% / 91% |
| 同じモデルにプロンプトだけを与えた場合よりキャラクターをうまく演じる（40 場面） | 63% / 58% | 75% / 53% |
| 訂正で教わったことを、言い方の異なる後のメッセージで生かす | 76% / 56% | 71% / 67% |

- 自分宛てのメッセージを無視することはまれです。誤りの多くは、映画館や子犬など、別のものを指して名前が使われたケースです。
- 荒らし、通りすがり、途中で去った人による 84 件の訂正は、1 つも通りませんでした。

[詳しい結果](https://github.com/wangkant/personagent/blob/main/docs/evals/2026-10-18/README.ja.md)には、信頼区間、種類別の誤り、手法、すべてのレポートが含まれています。

## 他のプロジェクトとの比較

よく比較されるプロジェクト（2026 年 11 月時点）：

- **AstrBot**（AGPL-3.0）は十数種類を超えるプラットフォームに対応したボットフレームワークで、WebUI と大きなプラグインマーケットがあります。呼ばれていなくてもランダムに返信でき（確率 10%、初期設定ではオフ）、学習はプラグインに任せています。
- **MaiBot**（GPL-3.0）は NapCat を通じて QQ で動くキャラクターボットで、WebUI とワンクリックのランチャーがあります。プランナーモデルが発言の頻度を決め、チャットから言い回しやスラングを覚えます。
- Koishi 向けの **ChatLuna のキャラクタープラグイン**（AGPL-3.0）は、一定の間隔、チャットの活発さ、静かになってからの時間といったルールに基づいて会話に加わります。
- **ElizaOS**（MIT）は Discord、Telegram、Slack などに対応した TypeScript 製のエージェントフレームワークで、返答するかどうかはモデルが決めます。

personagent に組み込まれているもの：返信への人々の反応（訂正、拒否、受け入れられた言い直し）から学ぶこと、すべての変更を記録して元に戻せるようにしていること、そして振る舞いの評価を公開していること。

ほかのプロジェクトが優れている点：すべての設定を WebUI で扱えるデスクトップアプリ、大きなプラグインエコシステム、そしてスラング、スタンプパック、画像の記憶。すでに AstrBot や Koishi を運用しているなら、どちらかを選ぶ必要はありません。personagent はどちらの背後でもキャラクターとして動かせます。

## アップデートとアンインストール

PyPI に新しいバージョンが出ると、ページに通知が表示され、インストール方法に合ったアップデートコマンドが示されます。pip の場合は `python -m pip install -U personagent` です。ホームフォルダーの中身、つまり設定、キャラクター、学んだこと、連携済みのアプリはそのまま引き継がれます。

削除するには、まず接続したコーディングエージェントから取り外します（`personagent connect claude-code --remove`。`codex` と `dsh` も同様です）。次に personagent を終了して `python -m pip uninstall personagent` を実行します。最後にホームフォルダーを削除します。PyPI からインストールした場合、別の場所を選んでいなければ `~/personagent` です。ここにはキー、キャラクター、学んだことのすべてが入っているので、削除すると元に戻せません。uv や pipx の場合と、無効化しておくべきものは[詳しい手順](https://github.com/wangkant/personagent/blob/main/docs/setup-for-agents.md#undoing-it)（英語）にあります。

## プライバシー

personagent が保存するものはすべて、あなたのマシン上の 1 つのホームフォルダーに置かれます。キーを含む `.env`、`persona.txt`、`runtime/`、そして管理対象の AstrBot と直接接続の認証情報を含む `platforms/` です。選んだモデルプロバイダーは、自分が応答する会話を見ることになります。また personagent は 1 日に 1 回、新しいバージョンが出ていないか pypi.org に問い合わせます（`UPDATE_CHECK_ENABLED=false` で止められます）。実在の人々とつなぐ前に、ボットであることを伝えて同意を得てください。何がどこに送られるかは[ガイド](https://github.com/wangkant/personagent/blob/main/docs/guide.ja.md#プライバシーと同意)に記載しています。

## ドキュメント

- [ユーザーガイド](https://github.com/wangkant/personagent/blob/main/docs/guide.ja.md)：インストール、設定、ターミナルでのチャット、コネクター、教え方、アクティビティビュー、トラブルシューティング。
- [デプロイガイド](https://github.com/wangkant/personagent/blob/main/docs/deploy.ja.md)：本番運用について。コネクター、QQ、エンドポイントの公開、コスト、ボットが黙ってしまったときの確認事項。
- [コネクタープロトコル](https://github.com/wangkant/personagent/blob/main/docs/connectors.ja.md)：1 メッセージにつき署名付き HTTP リクエスト 1 回。独自のコネクターを書くためのものです。
- [ツール](https://github.com/wangkant/personagent/blob/main/docs/tools.ja.md)：`tools/` 内のスクリプト。クローンから実行するためのものです。
- [変更履歴](https://github.com/wangkant/personagent/blob/main/CHANGELOG.md) · [コントリビューション](https://github.com/wangkant/personagent/blob/main/.github/CONTRIBUTING.md) · [セキュリティポリシー](https://github.com/wangkant/personagent/blob/main/.github/SECURITY.md) · [免責事項](https://github.com/wangkant/personagent/blob/main/docs/DISCLAIMER.ja.md)

## ライセンス

コードは [MIT](https://github.com/wangkant/personagent/blob/main/LICENSE) © 2026 Qiankang (Kant) Wang です。3 枚のキャラクターの立ち絵は CC BY-NC-SA 4.0 でライセンスされており、クレジットは [persona_agent/static/characters/LICENSE.md](https://github.com/wangkant/personagent/blob/main/persona_agent/static/characters/LICENSE.md) にあります。

## 謝辞

- ほかのチャットプラットフォームへは、[AstrBot](https://github.com/AstrBotDevs/AstrBot)、[NapCat](https://github.com/NapNeko/NapCatQQ)、[Koishi](https://koishi.chat) と [satori-python](https://github.com/RF-Tar-Railt/satori-python)、そして [matrix-nio](https://github.com/matrix-nio/matrix-nio) と [mautrix ブリッジ](https://docs.mau.fi/bridges/)を通じて接続しています。WeChat との接続は Tencent の [openclaw-weixin プロトコルノート](https://github.com/Tencent/openclaw-weixin/blob/main/docs/protocol.md)に従っています。
- 反応からの学習は [Self-Feeding Chatbot](https://arxiv.org/abs/1901.05415)、[Alexa self-learning](https://arxiv.org/abs/1911.02557)、[BlenderBot 3x](https://arxiv.org/abs/2306.04707) を参考にしています。ロアブックは [SillyTavern](https://github.com/SillyTavern/SillyTavern) の World Info にならっています。
