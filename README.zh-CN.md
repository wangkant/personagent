<div align="center">

# personagent

<p><strong>一个像群里的人、而不是侧边栏助手的聊天机器人。</strong></p>

你用一个文本文件描述一个角色，personagent 就让这个角色住进你的群聊和私聊——<br>
有话说的时候说，没话说的时候闭嘴，说错了被纠正之后会改。

[English](README.md) · [**简体中文**](README.zh-CN.md)

[![CI](https://github.com/wangkant/personagent/actions/workflows/ci.yml/badge.svg)](https://github.com/wangkant/personagent/actions/workflows/ci.yml)
[![最新版本](https://img.shields.io/github/v/release/wangkant/personagent?display_name=tag&sort=semver&color=6f42c1)](https://github.com/wangkant/personagent/releases)
[![Python 3.10–3.12](https://img.shields.io/badge/Python-3.10%E2%80%933.12-3776AB?logo=python&logoColor=white)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-2f855a.svg)](LICENSE)

[**这是什么？**](#这是什么) · [5 分钟试一下](#5-分钟试一下) · [写你的角色](#写你的角色) · [接到真实聊天里](#接到真实聊天里) · [它怎么学](#它怎么学) · [配置](#配置) · [排查](#日常运维) · [文档](#文档)

</div>

<a href="#5-分钟试一下">
  <img src="assets/demo.svg" alt="personagent 读群聊之后，选择回复、记一条记忆，或者保持沉默（示意图为英文）" width="100%">
</a>

## 这是什么？

personagent 是一个你自己跑在自己机器上的 Python 程序。它给一个虚构角色配一个聊天账号，让这个角色像群里任何一个普通成员那样待着。

整个想法用一个例子就说清楚了。朋友在群里发：

> **sam：** 搞了三个小时，一个 ctrl+z 全没了

| 普通助手机器人会说 | personagent 会说 |
|---|---|
| 「很遗憾听到这个！你可以试试编辑器的本地历史记录。如果需要更多恢复未保存文件的建议，随时告诉我～」 | 「凉了。先歇会儿再回去弄」 |

而当接下来三条消息是 `哈哈`、`同`、`D . e` 的时候，它**什么都不说**——在真实群聊里，这通常才是正确答案。**决定不说话在这里是正常结果，不是故障。**

### 你需要准备

| 你要准备 | 为什么 |
|---|---|
| **一个角色**——你自己写的几句话，放在 `persona.txt` 里 | 这就是机器人的全部性格。初始文件会帮你复制好。 |
| **一个 API Key**，任意 OpenAI 兼容模型——DeepSeek、Kimi、OpenAI、智谱、Together，或者**本地 Ollama** | 每条回复是一到两次模型调用，算在你自己账上。没有 personagent 服务；唯一免费的选项是把模型跑在本地。 |
| **一条通向聊天平台的路**——[AstrBot](https://github.com/AstrBotDevs/AstrBot)，一个你自己另外装的程序 | personagent 自己不登录 QQ / Telegram / Discord。本地试用不需要它。 |

### 技术上它到底是什么

- **一个你自己跑的小型 Web 服务**，不是一个库。`python main.py` 会在 `127.0.0.1:8080` 启动 FastAPI。AstrBot 负责连接聊天平台，把每条消息 POST 过来；personagent 在同一个 HTTP 响应里返回回复，或者返回「没什么可说的」。
- **要 clone，不要 `pip install`。** `main.py`、`try_chat.py`、`quickstart.py` 都是仓库根目录的入口，`data/` 里的种子数据必须挨着包放。装 wheel 只能拿到用于测试的管线，跑不起一个机器人。
- **靠纯 HTTP 做到不绑供应商。** 所有模型调用——写回复、给图片配文字、以及那个负责决定「要不要开口」的便宜小模型——都是 POST 到 OpenAI 兼容的 chat-completions 接口，不装任何厂商 SDK。
- **数据在你手里。** 它记住和学到的一切都是你磁盘上 `runtime/` 里的 JSON。离开你机器的只有你预期中的那部分：每次模型请求里的聊天上下文，发给你自己配的那个供应商。

### 它和普通机器人不一样的地方

- **会闭嘴。** 群聊里模型可以回 `PASS` 而不是文本；而且大部分沉默比这还便宜——没人搭理它的群，要积累约 30 条消息它才会考虑开口。*（一对一私聊里没有 PASS：角色总是回，只是长短不同。）*
- **不说客服腔。** 提示词直接禁止助手语气，最后还有一层正则过滤，把漏出来的「作为一个 AI……」「您好，请问有什么可以帮您」整条丢掉。
- **像人一样打字。** 回复是分行写的，每一行作为一条单独的消息发出，中间带打字停顿——所以稍长的一段会变成两三条气泡，而不是一整段。大多数回复本来就是一句话，那就只发一条。
- **按会话记忆。** 每个会话各自的短笔记，绝不跨会话、跨平台串。
- **不只读文字。** 图片会被转成描述，表情包会被认出来并复用，B 站 / YouTube / 网页链接会被展开成标题和简介，QQ 分享卡片会被拆开。语音、视频、聊天记录转发会变成诚实的占位符，并明确告诉模型不许瞎编。
- **听得进纠正。** 告诉它哪句说错了、你本来想要什么；等到第二个佐证信号出现，这条纠正就会开始影响后面的回复。见[它怎么学](#它怎么学)。

**适合谁：** 想让一个特定角色住在自己群里的人。**不适合谁：** 想做客服助手的人——这个项目全部的力气都花在**不**当助手上。

## 5 分钟试一下

不需要聊天账号，不需要 AstrBot，不需要配平台。你只需要 Git 和 Python 3.10–3.12。

```bash
git clone https://github.com/wangkant/personagent.git
cd personagent
python quickstart.py
```

它会先创建 `.venv/`、装好依赖、把 `.env.example` 复制一份就位，然后问八个小问题——用哪家模型和哪个模型名、key、机器人叫什么、语言、要不要连 AstrBot（先答不要）、要不要用一次极小的调用测试 key、要不要马上开聊。你的回答写进 `.env`，再复制一份初始 `persona.txt`，最后把你丢进终端对话。

**想零成本试？** 先装好 [Ollama](https://ollama.com) 并把模型拉下来（`ollama pull qwen3`），然后在第一个问题选 **4) Ollama (local)**，key 那一步直接回车——它预填了一个占位值，因为本地 Ollama 根本不校验。如果向导的测试调用在这条路上失败，基本都是 Ollama 没在跑或者模型没拉，而不是 key 有问题。

之后重新打开终端试用，不用激活虚拟环境：

```bash
.venv/bin/python try_chat.py              # macOS / Linux
```
```powershell
.venv\Scripts\python.exe try_chat.py      # Windows
```

试用里的命令：`/owner <消息>` 以**主人**的身份说话——主人是你指定的那一个账号，机器人跟他最亲近（用 `OWNER_QQ` 设置，其他平台用 `GATEWAY_OWNER_IDS`），语气更松，也只有他能管理机器人的记忆。`/as <名字> <消息>` 以会话里另一个人的身份说话，`/reset` 清空对话，`/quit` 退出。参数：`--owner` 全程以主人身份说话，`--name Alex` 设置你自己的显示名，`--lang zh` 切换的是**种子数据**（示例、反馈、世界书、输出过滤器）和回复校验器的语言——你的 `persona.txt` 两种情况下都按原样使用，所以想要哪种语言就用哪种语言写它。

> **`(stays quiet)` 不是 bug。** 角色觉得没什么可补充的时候就会打印这个。再试一句，或者说点它真能接的话。

<details>
<summary><b>终端试用覆盖了什么，没覆盖什么</b></summary>

试用走的是真实回复链路——你的人设、示例检索、结构化输出约定、字符白名单校验——所以你看到的和群里会看到的很接近。有三处刻意的差别：

- **自评分和图片理解默认关着**，免得第一次运行就花钱。
- **输出过滤器不跑。** 一条在生产里会因为太像助手而被丢掉的回复，在这里照样会打印出来。
- **模型之前的那几道沉默闸门被跳过了。** 因为你永远是在直接跟它说话，白名单、「有没有在叫我」的判断、约 30 条消息的门槛都不会触发。但模型自己的 `PASS` 判断仍然生效，所以 `(stays quiet)` 照样可能出现。

</details>

<details>
<summary><b>第一次运行会在你磁盘上创建什么</b></summary>

| 路径 | 是什么 |
|---|---|
| `.venv/` | 虚拟环境，装着七个声明的依赖以及它们带进来的一堆传递依赖（约 25 个包）。不会往全局装任何东西。 |
| `.env` | 你的配置，**包含 API Key**。以 `chmod 600` 创建，已被 gitignore。 |
| `persona.txt` | 你的角色，从 `data/persona.example.<lang>.txt` 复制而来。已被 gitignore——你真正的人设永远不会被提交。 |
| `runtime/` | 机器人记住和学到的一切，JSON 格式。已被 gitignore。上线之后里面会有真实聊天片段。 |

重复运行 `python quickstart.py` 不会动已有的 `persona.txt`，也不会把 `.env` 覆盖掉。它确实会在重跑向导前问你一句——但前提是 `LLM_API_KEY` 已经有值；而一旦你答了「是」，向导会用**它自己的默认值**、而不是你现有的值，重写 `LLM_API_KEY`、`LLM_BASE_URL`、`LLM_MODEL`、`BOT_NAME`、`AGENT_LANG` 这五项。所以请逐项重新输入，别一路回车：`BOT_NAME` 一变，就等于换了一个角色，之前学到的东西全部对不上号。

`python quickstart.py --no-input` 完全跳过向导（在 CI 里或 stdin 被管道接管时也会自动走这条路）。

</details>

## 写你的角色

`persona.txt` 就是全部性格，大白话写就行。没有 schema，没有 YAML——你是在描述一个人。

```text
你叫 Nova。在一个群里跟群友闲聊，目标是发消息像真人而不是 AI 助手。

气质：
- 冷静、毒舌、爱玩梗，常年泡在网上，梗永远能在对的时候甩出来

风格守则：
- 不当客服，不主动总结，不喊"亲"，不发"希望对你有帮助"
- 阴阳/调侃要含蓄留台阶，不要直白讽刺让人下不来台
- 不熟的梗不要硬编，承认不懂就行
- 跟上群里的节奏：斗图时就短，认真聊时给个真观点
```

quickstart 复制进来的那份是**模板**：里面还留着 `{bot_name}`、`{owner_name}`、`{owner_relationship}` 这些占位符，以及末尾一段写给你自己的说明。没有任何东西会替你填上去——这个文件是原封不动交给模型的——所以正式用之前请把它们替换掉。

`persona.txt` 只在启动时读一次，所以改完要重启 `python main.py` 才生效。改它**不会**丢掉已经学到的东西。

`data/` 下另外四个小文件和它一起决定行为，而且和 `persona.txt` 不同，这四个在运行期间**会**被重新读取：

| 文件 | 作用 |
|---|---|
| `examples.<lang>.jsonl` | 好的回复。按相关度检索出来，作为 few-shot 示例给模型看。 |
| `feedback.<lang>.jsonl` | 「你说了 X，其实该说 Y」的成对样本——和学习回路产出的形状一致。 |
| `lorebook.<lang>.json` | 关键词触发的片段，只有命中关键词时才注入。自带六条：三条诚实护栏（怎么回答「你是不是机器人」、别装看过那部剧、别编造共同回忆），外加「别跟着一起损主人」、一份网络黑话词表，以及分享链接时别把 URL 复读一遍的规则。 |
| `output_filter.<lang>.json` | 作用在成品回复上的正则。每条要么改写，要么整条丢弃。「作为一个 AI……」「您好，请问有什么可以帮您」就是被它杀掉的。 |

<details>
<summary><b>可选：风格开关</b></summary>

人设文档末尾可以带一个 `[style]` 块，引擎会读它、并在正文送进模型之前把它摘掉：

| 开关 | 取值 | 含义 |
|---|---|---|
| `length` | short / medium / long | 默认回复长度。 |
| `vent` | hold / ask / solve | 有人倒苦水时：陪着、追问，还是给方案。 |
| `recs` | ask_back / offer | 被要求推荐时：先反问缩小范围，还是直接给一个。 |
| `good_news` | cheer / deadpan | 听到好消息的反应。 |
| `particles` | capped / free / none | 语气词和口头禅。 |
| `fatigue` | stock / own | 当它前两条回复都用了同一种「反转吐槽」腔调时，第三条必须换一种——用固定的备选说法（`stock`），还是用角色自己的话（`own`）。 |

另外，`persona.card.json` 是一个小配置文件（不是给模型读的正文），控制 emoji 和回复长度：

```json
{ "reply_style": { "emoji": true, "charsets": ["music"], "max_chars": 320 } }
```

两者都是选配；不写的话角色拿到的是收紧的默认值——不用 emoji，不用可选字符集。

</details>

## 接到真实聊天里

personagent 不连接任何聊天平台。**连接平台的是 [AstrBot](https://github.com/AstrBotDevs/AstrBot)**——一个你自己安装并运行的独立聊天机器人框架，它本身已经支持 QQ、Telegram、Discord、Slack、飞书、KOOK 等等。本仓库提供一个给它用的小插件，负责把每条消息转发给 personagent，再把回复发回去。

```text
   QQ / Telegram / Discord / Slack / 飞书 / KOOK / …
                        │
                        ▼
              AstrBot  +  转发插件                  ← 你自己安装的另一个程序
                        │  HTTP POST
                        ▼
            personagent  /webhook/gateway           ← 本仓库，python main.py
```

两个进程，单向调用：AstrBot 调 personagent，反过来不会。所以改平台凭证或插件配置之后重启 **AstrBot**；改 `.env` 之后重启 **personagent**。

**步骤**

1. **先装好并启动 AstrBot**，在它自己的 WebUI 里至少配好一个平台。本仓库不会帮你安装它。
2. **把两边接起来**——运行 `python quickstart.py`，在「连接 AstrBot」那一步选是。它会把[转发插件](integrations/astrbot/astrbot_plugin_llm_persona_gateway/README.md)复制到 AstrBot 的 `data/plugins/`，生成共享的 `GATEWAY_TOKEN` 并写入两边，还能用一个 bot token 直接开启某个平台适配器。无交互写法：
   ```bash
   python quickstart.py --astrbot <AstrBot data 目录> [--qq] [--platform telegram --token <bot token>]
   ```
   Telegram、Discord、KOOK 只要一个 bot token；**Slack 需要 `--token` 和 `--app-token` 两个**；**飞书则改用 `--app-id` 和 `--app-secret`**。
3. **填白名单**，在 AstrBot WebUI 里插件自己的配置页。填之前插件**什么都不转发**——`group_whitelist` 和 `private_whitelist` 初始都是空的，私聊默认关闭。新装之后看起来像死了，绝大多数就是这个原因。
4. **重启 AstrBot**，然后启动 Agent：
   ```bash
   .venv/bin/python main.py              # macOS / Linux
   ```
   ```powershell
   .venv\Scripts\python.exe main.py      # Windows
   ```
   也可以用 `./start.sh` / `.\start.ps1`，它们在虚拟环境或依赖缺失时会自己创建和安装。两种方式都要在仓库根目录下运行。

**在 `.env` 里设好 `BOT_NAME` 和 `BOT_QQ`**（quickstart 已经把这个文件写在仓库根目录）：

```ini
BOT_NAME=Nova
BOT_QQ=10001
```

别被名字骗了，`BOT_QQ` 在**所有平台**上都是关键项：它一为空，@ 检测就永远判定为「没人叫我」，于是机器人从不响应任何一次单纯的 @。但它照样会应自己的名字、照样回私聊、偶尔还会自己开口——这正是这个问题难以察觉的原因。没有 QQ 账号的话，填一个稳定的数字即可。`BOT_NAME` 为空时，机器人只认显式 @，不认自己的名字。

<details>
<summary><b>专门说 QQ</b></summary>

QQ 比别的平台多不少东西，而且都不在这个仓库里：一个小号（别用你自己的）、QQ NT 桌面客户端，以及一个登录在该号上的 OneBot v11 实现，比如 [NapCat](https://github.com/NapNeko/NapCatQQ)。然后由 AstrBot 的 `aiocqhttp` 适配器去连 NapCat——这一步在 AstrBot 里配，向导不管。

**是两处设置，不是一处。** 一要把 `aiocqhttp` 从插件的 `excluded_platforms` 里移除（它默认就在排除列表里，所以 QQ 消息在白名单被读到之前就已经被丢掉了），二要在 Agent 这边设 `GATEWAY_NATIVE_PLATFORMS=aiocqhttp`。`--qq` 参数两件事都会做。漏掉第二处，每个 QQ 会话都会以一个全新的带命名空间的 id 进来，这些会话已有的记忆和学习成果就全部对不上号了——而且事后改字段也救不回来。

**即使 QQ 消息改走 AstrBot，也要让 NapCat 的 HTTP 接口保持可达**（`NAPCAT_API`，默认 `http://127.0.0.1:3000`）。有两件事仍然直接从它出去：主动发消息，以及补发离线期间漏掉的 @。关掉它，这两项会静默失效。（走转发路径时，引用消息改为在 Agent 自己的近期消息索引里查，OCR 则完全跳过——这两件事只有在已废弃的直连路径上才会去问 NapCat。）

两件只有 QQ 才有的事：在转发平台上机器人**无法主动开口**（没有可以写入的通道——回复只能搭着带消息进来的那次请求回去）；表情包学习和 OCR 也是 QQ 路径专属。

旧的直连方式——OneBot 客户端直接 POST 到 `/webhook/qq`——**自 0.3.0 起废弃**。仍然能用，首次使用会警告一次。不要同时开两个 QQ 入口，否则每条消息都会到达两次。仓库根目录的 `launch.vbs` 属于那条旧路径，同样已废弃。

</details>

<details>
<summary><b>跨机器部署</b></summary>

默认是只监听回环、完全不鉴权的服务，AstrBot 和 personagent 在同一台机器上时这是对的。一旦不在同一台：

- 设 `HOST=0.0.0.0`，并且 **`GATEWAY_TOKEN` 和 `WEBHOOK_SECRET` 两个都要设**。非回环绑定时缺任何一个都会拒绝启动——哪怕你根本不用 `WEBHOOK_SECRET` 保护的那个 QQ 路由。
- **personagent 只提供纯 HTTP。** 「用 HTTPS」的意思是在它前面放一个反向代理或私有隧道。
- 那个代理必须**逐字节**原样透传请求体。每个请求都带有对精确字节的 HMAC 签名，任何会重新序列化 JSON 的中间件都会让所有请求变成 403。
- 两台机器的时钟要在 5 分钟内对齐，原因同上。

服务一共暴露四个路由——`GET /health`、`GET /health/details`、`POST /webhook/gateway`，以及已废弃的 `POST /webhook/qq`——外加 FastAPI 默认的 `/docs`、`/redoc` 和 `/openapi.json`，这三个**没有**被关掉。绑定公网接口之前值得知道这一点。

</details>

## 一条消息是怎么变成回复的

![personagent 架构](docs/persona_llm_agent_architecture.zh-CN.svg)

1. **进来**——鉴权、去重、查白名单，然后等约 2.5 秒，好让连发的一串消息合成一轮。
2. **翻译**——图片变描述，表情包变含义，链接变标题，引用变「谁说了什么」。全部用不可信文本的围栏包起来，并告诉模型这里面可能有注入。
3. **决定**——这是在跟我说话吗？关我什么事吗？有什么可说的吗？大多数沉默根本不会碰到模型。自己起意的那种回合，会先用一次便宜的模型调用只回答「说还是不说」，然后才轮到贵的。
4. **写并校验**——一次模型调用返回一个 JSON 对象，四个字段：`reasoning`、`intent`、`reply`、`mem`。格式不对就整条丢弃，什么都不发。`reply: "PASS"` 表示保持沉默；`mem` 是值得记住的一条事实。
5. **投递**——过输出过滤器、去掉人设没有开启的 emoji 和符号集、拆成短消息、发出去。
6. **观察**——把接下来发生的事记成证据，不阻塞这次回复。

**记忆**是两样小东西，都按会话隔离，都存在 `runtime/`：每个会话最多 50 条短笔记（由模型写，或者你用 `Nova 记住 <事实>` 写），以及每个会话一条更长的常驻笔记，模型会随着情况变化整条改写。两者都会拒绝任何形如指令的内容，所以没人能把「以后都用法语回复」当成「事实」存进去。滚动的消息缓冲只在内存里，重启就没了。

## 它怎么学

这里没有任何微调，模型权重一点没变。所谓「学习」，就是往后续回合的提示词里多贴几条示例——而且前面有一道闸门。

**你要做的：** 对着机器人的某条消息回复——引用它、@ 它，或者叫它的名字——然后告诉它那句说错了，最好顺便说出你本来想要什么。在群里，一条既不引用也不点名的反应，无论多明显是冲它来的，学习链路都看不见。（只有一个例外：如果机器人刚问过你「你刚才是什么意思」，那么几分钟之内你的下一条消息不需要引用或 @ 也会被算上。）

**会发生什么：** 机器人对自己发出的每条回复，会等 15 分钟看有没有反应。一个便宜的模型读你的反应并给它分类。判定结果被追加进一个永不改写的日志，并提出一个**候选项**——在被晋升之前它什么都不做。晋升需要**两个相互兼容的信号、其中至少一个是强信号**，来自同一个会话、30 天以内。「强信号」有两种形态，而且都要求是那句回复本来说给的那个人：他指出这句不对**并且**说出本该怎么说，或者他接受了机器人的第二次尝试。旁观者的纠正永远不算强信号，主人也不算。有互相矛盾的证据时会直接拒绝晋升，留给你自己判断。

实际用起来，**你自己纠正它两次**就是标准的教法——先否定再澄清，或者先纠正、再接受它的第二次尝试。

**两件让人意外的事：**

- **好的回复永远不会被自动学会。** 五个人对着一条回复笑，什么都不会发生。「这句真好，以后多这样」只有你手动晋升才会生效。
- **这个功能默认开着，而且花钱。** 每匹配到一次反应就是一次额外的模型调用。另外，如果你只说了「这句不对」却没说想要什么，它可能在大约两分钟后主动发一句「等等，你刚才是什么意思？」（每个会话每小时最多一次）。用 `REACT_LEARN=false` / `REACT_ELICIT=false` 关掉。默认**关着**的是自评分（`EVAL_ENABLE`）和无人值守自诊断（`EVOLVE_AUTO`）。

**怎么查看和撤销：**

```bash
python tools/candidates_admin.py list                   # 还在等待的提议——不是它已经学会的东西
python tools/candidates_admin.py list --state promoted  # 当前真正在影响回复的
python tools/candidates_admin.py show <id>              # 某个提议，以及它背后的每一条证据
python tools/candidates_admin.py promote <id>           # 手动批准（好回复只有这一条路）
python tools/candidates_admin.py rollback <id>          # 撤销一个已晋升的；下一轮生效
```

或者干脆在聊天里告诉它错了——一次被采纳的纠正会自动撤销教出那句话的所有内容。什么都不会被真正删除，只是被剥夺效力；日志留着是为了可审计，这也意味着里面保留着真实消息的原文。真正的删除只有一种：你自己去删 `runtime/` 下的文件。

**改 `persona.txt` 不会丢失已学内容。** 改 `PERSONA_VERSION`——或者改 `BOT_NAME`——则是换了一个角色，旧角色学到的东西从此被拒绝。对 `PERSONA_VERSION` 来说这是刻意设计；对 `BOT_NAME` 来说，这一点常常让人措手不及。

## 配置

`.env.example` 是完整且带注释的权威参考，而且有测试保证它不撒谎——代码读取的每一个设置都在里面。一共 91 项。

**其中只有一项是必填的：`LLM_API_KEY`。** 另外 90 项都有默认值。模板里写的是随仓库发布的那份 `.env` 所用的值，个别设置和代码内置的兜底值并不一致——所以请改值，不要整行删掉。要跑真机器人，再加上 `BOT_NAME` 和 `BOT_QQ`，它才知道什么时候有人在跟它说话。

| 你想做什么 | 相关设置 |
|---|---|
| 选模型 | `LLM_API_KEY`、`LLM_BASE_URL`、`LLM_MODEL`——任意 OpenAI 兼容 `/v1` 接口。`PRIVATE_MODEL`、`FALLBACK_MODEL`、`JUDGE_MODEL` 是**同一个接口和 key 上的另一个模型名**。 |
| 给角色起名 | `BOT_NAME`、`PERSONA_FILE`、`PERSONA_CARD_FILE`。 |
| 切换语言 | `AGENT_LANG=en` 或 `zh`——决定种子示例、世界书和过滤器，并且每种语言各有一套独立的学习历史。你自己的 `persona.txt` 按原样使用。 |
| 接平台 | `GATEWAY_TOKEN`（与插件共享）、`GATEWAY_OWNER_IDS`（形如 `telegram:12345`）、`GATEWAY_NATIVE_PLATFORMS`；QQ 还要 `BOT_QQ`、`OWNER_QQ`、`NAPCAT_API`。 |
| 控制学习 | `REACT_LEARN` 和 `REACT_ELICIT`（都**默认开**）、`PROMOTE_AUTO`（开）、`EVAL_ENABLE` 和 `EVOLVE_AUTO`（都关）。 |
| 读图片 | `VISION_MODEL` 加上 `GLM_API_KEY` 和 `GLM_BASE_URL`——视觉**永远走这第二套凭证**，不用你的主 key。`VISION_MODEL` 留空，图片理解就不会生效。 |
| 挪动状态目录 | `AGENT_HOME`（部署根目录——想用一份代码跑多个角色，就给每个角色一个）、`AGENT_RUNTIME_DIR`（必须在 `AGENT_HOME` **之下**，否则启动失败）。 |

几个会咬人的细节，最好提前知道：

- **拼错的设置是静默的**——值被忽略，用默认值。启动时会把 `.env.example` 不认识的 key 全部记进日志，但只检查 `.env` **文件**；通过 Docker 或 systemd 注入的变量完全不查。两者都不会阻止启动。
- **shell 变量优先于 `.env`。** 加载时不覆盖已有环境变量，所以一个过期的 `export` 会悄悄盖住你刚改好的文件。
- **布尔值写法不统一。** `PROACTIVE_ENABLE=1` 会被当成 **false**；有几个开关只认字面量 `true`。统一用 `true`/`false`。
- **`TZ_OFFSET_HOURS` 默认是 8（UTC+8）**，它还决定了一个 02:00–07:00 的时段，期间机器人基本不主动说话。不在这个时区就改掉它，否则它会在你意想不到的时间段里几乎不吭声。
- **从 0.1.x 升上来？** `DEEPSEEK_API_KEY` / `_BASE_URL` / `_MODEL` 在 0.2.0 改名为 `LLM_*`，旧名字**不再被读取**。

## 日常运维

下面这些命令用的是虚拟环境里的 Python——没有激活虚拟环境的话，请加上 `.venv/bin/python` 前缀（Windows 上是 `.venv\Scripts\python.exe`）。

```bash
curl http://127.0.0.1:8080/health                     # 存活探针；免费，不调模型
.venv/bin/python tools/healthcheck.py                 # 完整诊断——配置、账本体积，然后是实时探测
.venv/bin/python tools/candidates_admin.py list       # 它正提议学什么
.venv/bin/python -m pip install -e ".[dev]"           # pytest 不是运行时依赖，要先装
.venv/bin/python -m pytest -q                         # 回归测试；离线、免费、不需要 API key
```

改完配置就跑 `tools/healthcheck.py`——它的第一段就是启动时那套预检，不花钱。后面的探测**会消耗额度**，`GET /health/details` 也一样（缓存 60 秒），所以别拿它当监控探针。

在角色所在的任意群里，说它的**名字**加上下面任意一句——四个命令都免费，都不调模型：

| 你说 | 得到 |
|---|---|
| `Nova 学到了什么` | 这个会话的记忆条数、当前正在影响回复的内容、还在等第二个信号的提议数。 |
| `Nova 记得什么` | 它为这个会话保存的笔记。 |
| `Nova 记住 <事实>` | 存一条笔记。形如指令的内容会被拒绝。 |
| `Nova 忘了 <关键词>` | 删除匹配的笔记。除非你是主人，否则只能删你自己存的那些。 |

名字必须出现在消息正文里——只 @ 是不够的。英文说法（`what have you learned`、`what do you remember`、`remember …`、`forget …`）在中文部署里同样可用。这几个命令只在群聊里生效。

**备份 `runtime/` 的同时，也要备份 `.env`、`persona.txt` 和 `persona.card.json`**——人设文件在部署根目录，不在 `runtime/` 里面。它们全都被 gitignore，所以不在任何仓库备份里；少了 `.env` 恢复出来就是一个没有 API key 的机器人。

<details>
<summary><b>如果它正常启动却从不回话</b></summary>

按可能性从高到低：

1. **插件白名单还是空的。** 它什么都不转发，也不打日志。先去 AstrBot 的 WebUI 看。
2. **QQ 场景：`aiocqhttp` 还留在插件的 `excluded_platforms` 里。** 消息在白名单被读到之前就已经被丢掉了。
3. **`BOT_QQ` 没设**，于是所有平台上的 @ 都识别不出来。
4. **某个设置拼错了**，或者 **`.env` 带了 UTF-8 BOM**——BOM 会粘在第一个 key 的名字上，而文件在任何编辑器里看都完全正常。`tools/healthcheck.py` 两者都能查出来。
5. **token 不一致、时钟偏差，或者代理改写了请求体**——三者表现完全一样：每个网关请求都 403。
6. **没人跟它说话。** 没被搭理的群，要积累约 30 条消息（第一次约 10 条）它才会考虑主动开口。
7. **`BOT_NAME` 或 `PERSONA_VERSION` 改过了**，于是旧角色学到的一切现在都被拒绝。

完整清单（包括怎么分别验证两个方向）见[部署指南](docs/deploy.md#when-the-bot-goes-quiet)（英文）。

</details>

## 你可以期待什么

**成本。** 每条回复至少一次模型调用，经常是两次——自己起意的回复会先过一次便宜的「说还是不说」判定。此外：`REACT_LEARN` 开着时每个反应一次调用，配了视觉的话每张图一次，每次联网搜索一次。判定用便宜模型、写作用贵模型，是设计时的预期用法。

**成熟度。** 版本 0.3.0，beta，单人作者，MIT。测试是认真的——17 个套件约 1000 条断言，完全离线，不花钱——CI 在 Linux 上跑 Python 3.10–3.12，在 Windows 上跑 3.12。没有 macOS 任务，3.13 未经测试。`main` 通常领先于最新的 tag。

**平台。** 真正在跑、被实际验证的是 QQ。其他平台都通过 AstrBot 进来、共用同一条管线，但没有任何平台做过端到端集成测试。在任何转发平台上，机器人无法主动开口，只能应答。

**实验性的部分。** `tools/dspy_tune.py` 自己的文档字符串就写着 "SCAFFOLD ONLY"。`tools/evolution_benchmark.py` 跑在 64 条合成的英文场景上，并且明说它的数字**不**衡量真实部署能自己学到多少。致谢里的论文是思路来源，不是对本实现的验证。

## 负责任地使用

把这东西接到 QQ 之前，请先读 [DISCLAIMER.md](DISCLAIMER.md)。简版：

- **QQ 协议客户端未经腾讯授权**，运行它可能导致账号被冻结、限制或**永久封禁**——从云服务器或境外 IP 跑尤其容易触发。请用小号，不要用你自己的号，并且从家庭宽带跑。
- **告诉别人这是机器人。** 把账号标注清楚。不要部署在它的行为会误导他人的场合，也不要未经本人同意去模仿真实的人。
- **处理他人消息前先取得同意。** `runtime/` 里最终会保存真实对话的原文，而且日志按设计是只追加的。
- **你的模型供应商能看到每次请求里的聊天上下文**，有些供应商在你不主动关闭的情况下会拿它训练。

## 文档

- [部署指南](docs/deploy.md)（英文）——那些真正关键的细节，以及完整的「机器人沉默」排查清单
- [AstrBot 转发插件](integrations/astrbot/astrbot_plugin_llm_persona_gateway/README.md)
- [配置参考](.env.example)——全部 91 项，带注释
- [更新日志](CHANGELOG.md) · [贡献指南](CONTRIBUTING.md) · [免责声明](DISCLAIMER.md)

## 许可证

[MIT](LICENSE) © 2026 Qiankang Wang。

## 致谢

基于 [OneBot v11](https://github.com/botuniverse/onebot-11) 事件模型、[NapCat](https://github.com/NapNeko/NapCatQQ)、[AstrBot](https://github.com/AstrBotDevs/AstrBot)、[FastAPI](https://github.com/fastapi/fastapi) 和 [httpx](https://github.com/encode/httpx) 构建，思路借鉴 [Self-Feeding Chatbot](https://arxiv.org/abs/1901.05415)、[Alexa self-learning](https://arxiv.org/abs/1911.02557) 和 [BlenderBot 3x](https://arxiv.org/abs/2306.04707)。世界书与输出过滤器的模型参考了 SillyTavern 的 World Info 与正则扩展。
