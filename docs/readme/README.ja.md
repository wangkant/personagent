<p align="center">
  <img src="https://raw.githubusercontent.com/wangkant/personagent/main/assets/personagent-cover.webp" alt="personagent：イラストで描いた会話の様子" width="100%">
</p>

<h3 align="center">黙るべきときを心得ていて、訂正されると学ぶ、グループチャットのためのキャラクター。</h3>

<p align="center">
  <a href="https://pypi.org/project/personagent/"><img src="https://img.shields.io/pypi/v/personagent?color=3776AB&label=PyPI&cacheSeconds=3600" alt="PyPI"></a>
  <a href="https://github.com/wangkant/personagent/actions/workflows/ci.yml"><img src="https://github.com/wangkant/personagent/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/Python-3.10%E2%80%933.14-3776AB?logo=python&logoColor=white" alt="Python 3.10–3.14"></a>
  <a href="https://github.com/wangkant/personagent/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-2f855a.svg" alt="ライセンス：MIT"></a>
</p>

<p align="center"><a href="https://github.com/wangkant/personagent/blob/main/README.md">English</a> · <a href="https://github.com/wangkant/personagent/blob/main/README.zh-CN.md">简体中文</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.zh-TW.md">繁體中文</a> · <strong>日本語</strong> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.ko.md">한국어</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.es.md">Español</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.fr.md">Français</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.de.md">Deutsch</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.pt-BR.md">Português</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.ru.md">Русский</a></p>

*これは英語版 README の翻訳です。基準となるのは英語版で、こちらより新しい場合があります。リンク先のガイドは英語です。*

personagent はグループチャットのためのキャラクターです。用意されたものから選ぶか自分で書き、OpenAI 互換の任意のモデルで動かせます。QQ、WeChat、Telegram、Discord には自力で接続し、KOOK、Feishu、DingTalk、Slack、WeCom、Mattermost、Misskey にも同じページから接続できます。

まずはローカルのブラウザーチャットから始めます。モデルのキーを 1 つ追加して、あいさつするだけです。キャラクターをグループに参加させたくなったら、スマートフォンでのスキャンか、値を 1〜2 個入力してアプリを連携します。

<p align="center">
  <img src="https://raw.githubusercontent.com/wangkant/personagent/main/docs/welcome.jpg" alt="ローカルページの「アプリ連携」画面。参加できるすべてのプラットフォームが並んでいる" width="960">
</p>

<p align="center"><em>「アプリ連携」は、設定やキャラクターとのチャットと同じローカルページにあります。スクリーンショットは、ローカルのテスト用モデルを使った使い捨ての環境で撮影したものです。</em></p>

## はじめに

PyPI からインストールして起動します。

```sh
python -m pip install personagent
personagent
```

[uv](https://docs.astral.sh/uv/) があれば、`uvx personagent` で個別のインストールなしに実行できます。

ブラウザーでローカルページが開き、**チャット**、**アプリ連携**、**キャラクターと設定** の 3 つのビューが表示されます。モデルの API キーを貼り付けて **確認してチャット開始 →** をクリックすると、小さなリクエストを 1 回送ってキーを確認します。モデルサービスのプリセットは 10 種類あり、そのほかの OpenAI 互換サービスも使えます。キャラクターの名前と性格にもプリセットがあります。**ペルソナ** 欄の内容は `persona.txt` に保存され、保存するとエージェントが再起動し、学んだことはそのまま残ります。**その他の機能** では、ウェブ検索、画像の理解、自分から話しかける機能をオンにできます。`personagent` をもう一度実行すると、すでに開いているページを再利用します。右上のメニューで、ページを英語、中国語、またはほか 8 つの言語で表示できます。キャラクターに組み込まれたプロンプトは英語か中国語で、それ以外の言語で答えるかどうかはモデル次第です。

Windows では、ソースの ZIP をダウンロードして `start.bat` をダブルクリックする方法もあります。対応する Python は 3.10–3.14 です。[簡単なスタートガイド](https://github.com/wangkant/personagent/blob/main/docs/start.md)を参照してください。ターミナルでのコマンドとコネクターについては[詳しいガイド](https://github.com/wangkant/personagent/blob/main/docs/guide.md)にあります。

## コーディングエージェントにセットアップを任せる

あなたのコンピューターでコマンドを実行できるコーディングエージェントなら、personagent のインストールとセットアップを代わりに行えます。次のように指示してください。

```text
https://raw.githubusercontent.com/wangkant/personagent/main/docs/setup-for-agents.md を読んで、personagent をセットアップしてください。
```

エージェントは、キャラクターの言語・名前・性格、使うモデルサービス、つなぎたいチャットアプリを尋ねたうえで、personagent をインストールし、ホームフォルダーを作成してローカルページを起動します。モデルのキーはそのページにあなた自身が貼り付けるので、キーがエージェントを経由することはありません。エージェントが従う[手順書](https://github.com/wangkant/personagent/blob/main/docs/setup-for-agents.md)は、あなたも読めるプレーンな Markdown です。

## personagent を選ぶ理由

<table>
<tr>
<td width="220" valign="top"><img src="https://raw.githubusercontent.com/wangkant/personagent/main/persona_agent/static/listening.webp" alt="" width="220"></td>
<td valign="top">
<strong>黙るべきときを心得ています。</strong><br>
呼ばれれば答えます。それ以外のときは、人ならここで口を挟むかをモデルが判断します。サイコロ任せではありません。<br>
メッセージが立て続けに届いても、1 件ずつではなくまとめて 1 回返信します。
</td>
</tr>
<tr>
<td width="220" valign="top"><img src="https://raw.githubusercontent.com/wangkant/personagent/main/persona_agent/static/learned-notebook.webp" alt="" width="220"></td>
<td valign="top">
<strong>確かな訂正から学びます。</strong><br>
訂正で教わったこと（たとえば、グループでジムを何と呼んでいるか）は、そのチャットでのその後のすべての返信に反映されます。<br>
変更には、同じチャットからの一致する反応が 2 つ必要で、そのうち 1 つは強い反応でなければなりません。<br>
荒らしや通りすがりの人が学習し直させることはできません。<br>
すべての変更は記録され、どれでも元に戻せます。
</td>
</tr>
<tr>
<td width="220" valign="top"><img src="https://raw.githubusercontent.com/wangkant/personagent/main/persona_agent/static/empty-chats.webp" alt="" width="220"></td>
<td valign="top">
<strong>始めるのが簡単で、グループのいる場所で暮らします。</strong><br>
ブラウザーでの設定とチャットは英語、中国語、ほか 8 つの言語に対応し、モデルサービスは 11 種類、必要なら詳細設定も使えます。<br>
QQ、WeChat、Telegram、Discord には自力で参加し、さらに十数個のアプリにも同じページから参加できます。何をしたかは「アクティビティ」ビューで確認できます。
</td>
</tr>
</table>

- チャットごとに独立した記憶を持ちます。
- キャラクターを編集しても、学んだことは残ります。
- 振る舞いは測定されています。`personagent eval` は、話すタイミング、キャラクターを保てているか、訂正が定着するかを採点します（[結果](https://github.com/wangkant/personagent#measured)）。

## グループに参加させる

ローカルページで **アプリ連携** を開きます。アプリは次のように分類されています。

| ページ上の表示 | アプリ | 必要なもの |
|---|---|---|
| スキャンで連携 | QQ、個人 WeChat | スマートフォン。WeChat のボットは 1 対 1 のチャットのみ |
| 値を 1〜2 個貼り付け | Telegram、Discord、KOOK、Feishu/Lark、DingTalk、Slack、WeCom AI ボット、Mattermost、Misskey | アプリのコンソールで取得する値。どの値かはページに表示されます |
| 上級 | WeCom アプリ、WeChat 公式アカウント、QQ Webhook、OneBot v11 (NapCat)、Satori | 公開アドレス、またはこのコンピューター上の他のソフトウェア |

認証情報は保存前に確認され、連携済みのアプリは personagent を起動するたびに再び起動します。QQ、WeChat、Telegram、Discord には personagent が自分で接続し、それ以外は personagent がダウンロードしてバックグラウンドで動かす [AstrBot](https://github.com/AstrBotDevs/AstrBot) を経由します。ほかに何かを開く必要はありません。サーバーでは、`personagent up` でキャラクターと連携済みのすべてのアプリをブラウザーなしで起動できます。

**すでに AstrBot、Koishi、Matrix を運用していますか？** このコンピューター上の AstrBot なら、`personagent connect astrbot` でプラグインと共有トークンをインストールできます。別のマシン上の AstrBot なら、[最新リリース](https://github.com/wangkant/personagent/releases/latest)の `astrbot_plugin_personagent.zip` をそのプラグインページの **Install from File** からアップロードし、以下のガイドに従ってトークンと personagent の HTTPS アドレスを設定してください。[Koishi](https://koishi.chat) は [Satori コネクター](https://github.com/wangkant/personagent/blob/main/integrations/satori/README.md)で参加でき、[Matrix](https://matrix.org)（mautrix ブリッジ経由の WhatsApp と Signal を含む）は [Matrix コネクター](https://github.com/wangkant/personagent/blob/main/integrations/matrix/README.md)で参加できます。

それぞれの設定方法は[ユーザーガイド](https://github.com/wangkant/personagent/blob/main/docs/guide.md#put-it-in-a-chat)と[デプロイガイド](https://github.com/wangkant/personagent/blob/main/docs/deploy.md)にあります。[中国語のステップバイステップガイド](https://github.com/wangkant/personagent/blob/main/docs/deploy.zh-CN.md)では、QQ をゼロから設定する手順を説明しています。

## 他のプロジェクトとの比較

よく比較されるプロジェクトを、2026 年 10 月時点の各ドキュメントに基づいてまとめます。

- **AstrBot**（AGPL-3.0）は 18 以上のプラットフォームに対応したボットフレームワークで、WebUI と大きなプラグインマーケットがあります。呼ばれていなくてもランダムに返信でき（確率 10%、初期設定ではオフ）、学習はプラグインに任せています。
- **MaiBot**（GPL-3.0）は NapCat を通じて QQ で動くキャラクターボットで、WebUI とワンクリックのランチャーがあります。プランナーモデルが発言の頻度を決め、チャットから言い回しやスラングを覚えます。
- Koishi 向けの **ChatLuna のキャラクタープラグイン**（AGPL-3.0）は、一定の間隔、チャットの活発さ、静かになってからの時間といったルールに基づいて会話に加わります。
- **ElizaOS**（MIT）は Discord、Telegram、Slack などに対応した TypeScript 製のエージェントフレームワークで、返答するかどうかはモデルが決めます。

ほかのプロジェクトがプラグインに任せているか、説明していない点で、personagent に組み込まれているもの：返信への人々の反応（訂正、拒否、受け入れられた言い直し）から学ぶこと。変更には同じチャットからの一致する反応が 2 つ必要で、そのうち 1 つは強い反応であること。すべての変更が記録され、元に戻せること。そして振る舞いが公開された評価で測定されていること（[後述](https://github.com/wangkant/personagent#measured)）。

ほかのプロジェクトが優れている点：すべての設定を WebUI で扱えるデスクトップアプリ、大きなプラグインエコシステム、スラング・スタンプパック・画像の記憶。すでに AstrBot や Koishi を運用しているなら、どちらかを選ぶ必要はありません。personagent はどちらの背後でもキャラクターとして動かせます。

## 測定結果

`personagent eval` は、ラベル付けされたチャットの場面を使って実際のエージェントを動かします。2026-10-18 の最新の実行では、同梱のキャラクターを OpenRouter 経由で 2 つのモデルで動かし、各ケースを 3 回ずつ試し、Claude Opus 5.5 がブラインドで判定しました。英語 / 中国語の結果です。

| | deepseek-v4.1-flash | gpt-6-luna |
|---|---|---|
| 話すべきタイミングの判断が正しい（60 場面） | 83% / 80% | 93% / 91% |
| 同じモデルにプロンプトだけを与えた場合よりキャラクターをうまく演じる（40 場面） | 63% / 58% | 75% / 53% |
| 訂正で教わったことを、言い方の異なる後のメッセージで生かす | 76% / 56% | 71% / 67% |

- 自分宛てのメッセージを無視することはまれです。誤りの多くは、映画館や子犬など、別のものを指して名前が使われたケースです。
- 中国語では、プロンプトだけの場合に対する優位は誤差の範囲内です。
- 訂正の教訓が保持されるようになる前（同日の最初の実行後に修正）は、後のメッセージ 58 件のうち、それを生かせたのは 2 件だけでした。
- 荒らし、通りすがり、途中で去った人による訂正は、84 回の試行で 1 つも通りませんでした。

[詳しい結果](https://github.com/wangkant/personagent/tree/main/docs/evals/2026-10-18)には、信頼区間、種類別の誤り、手法、数値からわからないこと、すべてのレポートが含まれています。

## ドキュメント

- [ユーザーガイド](https://github.com/wangkant/personagent/blob/main/docs/guide.md)（[中文](https://github.com/wangkant/personagent/blob/main/docs/guide.zh-CN.md)）：インストール、設定、ターミナルでのチャット、コネクター、教え方、アクティビティビュー、トラブルシューティング。
- [デプロイガイド](https://github.com/wangkant/personagent/blob/main/docs/deploy.md)：本番運用について。コネクター、QQ、エンドポイントの公開、コスト、ボットが黙ってしまったときの確認事項。
- [中文部署教程](https://github.com/wangkant/personagent/blob/main/docs/deploy.zh-CN.md)：QQ をゼロから設定するステップバイステップの中国語ガイド。
- [コネクタープロトコル](https://github.com/wangkant/personagent/blob/main/docs/connectors.md)：1 メッセージにつき署名付き HTTP リクエスト 1 回。独自のコネクターを書くためのものです。
- [ツール](https://github.com/wangkant/personagent/blob/main/docs/tools.md)：`tools/` 内のスクリプト。クローンから実行するためのものです。
- [変更履歴](https://github.com/wangkant/personagent/blob/main/CHANGELOG.md)（[0.4 からのアップグレード](https://github.com/wangkant/personagent/blob/main/CHANGELOG.md#upgrading-from-04)を含む）。
- [コントリビューション](https://github.com/wangkant/personagent/blob/main/.github/CONTRIBUTING.md) · [セキュリティポリシー](https://github.com/wangkant/personagent/blob/main/.github/SECURITY.md) · [免責事項](https://github.com/wangkant/personagent/blob/main/docs/DISCLAIMER.md)

## プライバシー

personagent が保存するものはすべて、あなたのマシン上の 1 つのホームフォルダーに置かれます。キーを含む `.env`、`persona.txt`、`runtime/`、そして管理対象の AstrBot と直接接続の認証情報を含む `platforms/` です。選んだモデルプロバイダーは、自分が応答する会話を見ることになります。また personagent は 1 日に 1 回、新しいバージョンが出ていないか pypi.org に問い合わせます（`UPDATE_CHECK_ENABLED=false` で止められます）。実在の人々とつなぐ前に、ボットであることを伝えて同意を得てください。何がどこに送られるかは[ガイド](https://github.com/wangkant/personagent/blob/main/docs/guide.md#privacy-and-consent)に正確に記載しています。

## ステータス

1.3.0 は 2026-10-18 にリリースされ、PyPI で公開されています。最も多く使われてきたプラットフォームは QQ で、1.0 では AstrBot 経由、1.1 以降は直接接続しています。WeChat、Telegram、Discord の接続は、保存前に実際のサービスで認証情報を確認し、それ以外は代替環境でテストしています。Satori と Matrix のコネクターも代替環境でテストしています。CI は Linux の Python 3.10–3.14 と Windows の Python 3.12 でテストを実行し、さらにパッケージをインストールしてコマンドとローカルページを動かすジョブも実行します。

## ライセンス

[MIT](https://github.com/wangkant/personagent/blob/main/LICENSE) © 2026 Qiankang (Kant) Wang.

## 謝辞

- ほかのチャットプラットフォームへは、[AstrBot](https://github.com/AstrBotDevs/AstrBot)、[NapCat](https://github.com/NapNeko/NapCatQQ)、[Koishi](https://koishi.chat) と [satori-python](https://github.com/RF-Tar-Railt/satori-python)、そして [matrix-nio](https://github.com/matrix-nio/matrix-nio) と [mautrix ブリッジ](https://docs.mau.fi/bridges/)を通じて接続しています。WeChat との接続は Tencent の [openclaw-weixin プロトコルノート](https://github.com/Tencent/openclaw-weixin/blob/main/docs/protocol.md)に従っています。
- 反応からの学習は [Self-Feeding Chatbot](https://arxiv.org/abs/1901.05415)、[Alexa self-learning](https://arxiv.org/abs/1911.02557)、[BlenderBot 3x](https://arxiv.org/abs/2306.04707) を参考にしています。ロアブックは [SillyTavern](https://github.com/SillyTavern/SillyTavern) の World Info にならっています。
