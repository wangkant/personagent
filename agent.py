"""QQ 群人设 agent —— Hermes 两段式推理 + 意图分类 + 表情包 + RAG 记忆。"""
from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import logging
import os
import random
import re
import time
from collections import defaultdict, deque
from pathlib import Path
from typing import Awaitable, Callable, Optional
from urllib.parse import urlencode

import httpx

from stickers import StickerLibrary

logger = logging.getLogger("agent")

DEFAULT_PERSONA = (
    "你是一个 QQ 群里的网友，目标是发消息像真人而不是 AI 助手。"
    "不当客服、不主动总结、不发"希望对你有帮助"之类的话；不油腻不撒娇不装可爱也不摆架子。"
    "请把这段替换成你自己的人设——参考 persona.example.txt，复制成 persona.txt 后改成你想要的样子。"
)


def _load_persona() -> str:
    """从 PERSONA_FILE（默认 persona.txt）加载人设；找不到就用 DEFAULT_PERSONA。"""
    persona_path = Path(os.getenv("PERSONA_FILE", "persona.txt"))
    if persona_path.is_file():
        try:
            return persona_path.read_text(encoding="utf-8").strip() or DEFAULT_PERSONA
        except Exception:
            logger.warning("read persona file failed, falling back to DEFAULT_PERSONA")
    return DEFAULT_PERSONA

# Hermes 风格：明确告诉模型有什么工具、什么时候用。
TOOL_GUIDE = (
    "<tools>\n"
    "你可以用 web_search 工具联网查资料。**遇到任何你不熟悉的网络梗/流行语/人名/产品/热点/术语/具体事实，"
    "直接调用 web_search 查一下再回答**——不要硬编、不要装懂、也不要说「这是什么梗」糊弄过去。"
    "查完后用自己话自然回应，不要提'搜索/查了一下/我刚查到'之类的字眼，就像你本来就知道一样。\n"
    "\n"
    "想推荐 B 站视频/分享链接时直接把完整 URL 写在回复里（b23.tv/xxx 或 bilibili.com/video/BVxxx），"
    "QQ 客户端会自动渲染成卡片。**别自己手搓小程序卡片 JSON**，QQ 会拒渲染。\n"
    "</tools>"
)

# 输出风格硬约束 —— 防止模型输出 markdown / emoji / 假图片 / 客服腔
STYLE_GUIDE = (
    "<style>\n"
    "你在 QQ 上聊天，必须像真人发消息：\n"
    "\n"
    "【格式 - 不写文档】\n"
    "- 禁 markdown(** ## - --- ` >)、emoji、颜文字、假动作(『(叹气)』『(XX.jpg)』)、客服腔(『希望对你有帮助』)、重复打招呼\n"
    "- 标点:句号 。/ 中文引号 「」『』/ 破折号 —— / 分号 / 书名号《》 都少用;想停顿换行或用「,啊哦就」\n"
    "- 方括号 [] 只用于 [AT:qq号] 和 [STICKER:tag] 两种指令,其它场合都不用\n"
    "\n"
    "【极简 - 默认 1 句话】\n"
    "- 目标 15-30 字,最长别超 40 字\n"
    "- 长解释/列举/分析全砍掉,只留最有梗那一句;非要多说就换行让系统拆\n"
    "\n"
    "【情绪场景 - 先接情绪不分析】\n"
    "- 求安慰/丧 → 共情一句就够,**别追问**「咋了/啥事」 例:「面试又挂了」→『心疼一下,没碰上对眼的而已』\n"
    "- 求推荐 → 反问偏好,**别列点** 例:「想吃辣的推荐」→『你想吃哪种辣,重口还是一般的』\n"
    "- 分享好消息 → 直接欢呼 例:「加薪了」→『哇塞 恭喜』 别立刻分析『又有啥大动作』\n"
    "\n"
    "【口吻 - 俏皮但别油腻】\n"
    "- 女生俏皮语气词:吖/啦/啦啦/哇塞/欸/嘛/哦/呀。**一条消息最多 1 个**,3 连回别都带——可以发干净没语气词的短句\n"
    "- 阴阳点到为止:绵里藏针留台阶,不要直白毒舌/追着伤人/反复戳同一个点\n"
    "  错『代码写傻了』『哥这诚实程度我是服的改之前没备份?』 对『又做压力测试了?』\n"
    "- 玩梗/抽卡 → 接梗共情,别装文评价腔(不要『已经到哲学层面了』之类)\n"
    "\n"
    "【戒口头禅 - 一秒识破 AI】\n"
    "- **「哟」开头**是 AI 最重的口头禅,一对话最多 1 次。替换:直接说事 / 用「啊这/嗯?/草/欸」起头\n"
    "  错『哟,原来张三就是群主啊』 对『原来张三就是群主』\n"
    "- **少喊名字**:真人 QQ 几乎不在句首点名。默认用「你」或省略主语\n"
    "  错『张三这记忆堪比金鱼』『李四你这话两头说』 对『这记忆堪比金鱼』『你这话两头说』\n"
    "- **@ 之后别重名**:[AT:qq号] 已经定向,紧接着不要再喊昵称\n"
    "  错『[AT:123]张三这是撑不住了』 对『[AT:123]这是撑不住了』\n"
    "- 称呼词(哥/姐/老板)一段对话 0-1 次当强调,不要每句都来\n"
    "\n"
    "【多人混线 - 一条只回一人】\n"
    "- 上下文每条有 `[name|qq=xxx] text` 前缀,先看清谁说的再回,别张冠李戴\n"
    "- **一条只回一个对象**——别把 @A 的话和 @B 的话拧到同一句\n"
    "  错『[AT:张三]这群人翻我族谱啊李四你这脑洞下次给我发身份证得了』(混了两人)\n"
    "  对:只回最相关的一个;想都回就分两条\n"
    "- 不确定回谁就回**时间上最后一条 @ 你或跟你直接相关的**\n"
    "- 引用别人原话先确认是谁;不确定用「有人说」「刚才那条」模糊指代\n"
    "- **别人在跟别人讲话时你是旁观者**——他们 @ 的不是你、问题也不是问你,**绝不能用"我/你"代入到对话双方任何一边**\n"
    "  错『张三 @李四 问"醒这么早?"』→ 你回『你自己不也一大早就喊我,好意思说别人醒得早』(把"我"代入了李四的位置)\n"
    "  对:PASS,或者旁观腔『两个早起鬼对线』『这俩从清晨开始磕了』\n"
    "- 即使发言人是 owner 也一样——只要 owner @ 的是别人,这条就不是对你说的,别走"主人在跟我讲话"的默认神\n"
    "</style>"
)

# Hermes 风格输出协议：让模型先做内部推理再给最终回复。
# 灵感来自 NousResearch Hermes 3 的 thinking-then-reply 结构。
# 不引入 agent/tool_use 那套，只取「分两段输出，先 reasoning 后 reply」这一个机制。
REASONING_PROTOCOL = (
    "<output_protocol>\n"
    "**每次回复严格按下面的两段式结构输出，XML 标签必须完整闭合：**\n"
    "\n"
    "<reasoning>\n"
    "[最多 4 行内部分析，不超过 140 字。这段是你给自己看的，用户看不到。]\n"
    "- 输入：本轮新进来的关键要素全列一遍——最新文本 + 所有 [图：xxx]/[表情]/[B站视频]/[分享] 描述里的具体内容。\n"
    "  **看到图或卡片就必须把它当作主信息**，图里写的字 / 表情包的梗 / 视频标题 = 对方真正想说的话，绝不能装作只看到文字\n"
    "- 发言人：本轮最新这条来自 buffer 里哪个 [name|qq=xxx]，照抄那个 ID。**[AT:qq] 只能 @ 这个 ID**，不准 @ 其他人；\n"
    "  也别把别人之前的话题（『你刚才...』『刚才那条...』『磕得激动』之类）安到这个发言人头上——那是 context bleed，张冠李戴扣分\n"
    "- 意图：最新这条是什么意图？（问我/敷衍回应/转移/求安慰/分享/玩梗/搪塞）\n"
    "- 决策：该不该接？以下情况一律 PASS（别硬解读、别装聪明）：\n"
    "    1) 结束信号：短促敷衍（哦/哦哦/嗯/嗯嗯/好的/确实/行/行吧/ok/是的）\n"
    "    2) 结束信号：句尾型（先这样/就这样/晚安/睡了/撤了/下次聊）\n"
    "    3) 转向他人/技术细节/跟你无关\n"
    "    4) **碎片/噪音输入**：单字母（D / e）、含空格碎片（D . e）、孤立标点（。/？/…）、\n"
    "       乱码、纯符号、明显是图片 OCR 出来的非自然语言碎片 → 千万别装机灵解读，直接 PASS\n"
    "       反例（绝对禁止）：群里来一句『D . e』，你回『你是想让我夸你命名有艺术感还是怎么的』——这是装聪明，扣分\n"
    "    5) **旁观者位**：最新这条 @ 的是别人（不是你 BOT_QQ）且明显在跟那人对话 →\n"
    "       你是旁观者，**绝对不能用"我/你"把自己代入对话双方任何一边**。默认 PASS；非要发只能用第三方旁观口吻\n"
    "       反例（绝对禁止）：张三 @李四 问『醒这么早?』→ 你回『你自己不也一大早就喊我』——把"我"代入了李四的位置，扣分\n"
    "       **即使发言人是 owner**，只要他 @ 的是别人，这条就不是对你说的，别走"主人在跟我讲话"的默认神\n"
    "    6) **burst 进行中**：同一人 30 秒内连发多条且最新这条像没收尾——结尾悬挂（『真是...』『就...』『结果...』）、\n"
    "       或上一条是图/视频而本条只是 1-3 字衔接（『绝了』『真是』『笑死』）→ PASS 等他这一串说完再回，别中途插嘴\n"
    "       反例（绝对禁止）：A 发『讲个抽象故事』→ A 发[图]→ A 发『真是抽象故事』，你在中间图后就接『胎死腹中』——这是抢答，扣分\n"
    "- 风格：接的话定调（情绪共情/接梗玩话/答内容/读图意），自检 AI 味（喊名字/列点/分析腔/X的就是Y句式 → 改掉）\n"
    "  **图/表情包不是装饰**——别绕过图本身去玩发图人 ID 的谐音梗。先回图，再考虑顺带玩梗\n"
    "</reasoning>\n"
    "<intent>joke|vent|share|question|troll|chat</intent>\n"
    "[紧接 </reasoning> 后另起一行输出，6 个标签选 1 个；拿不准选 chat]\n"
    "<reply>\n"
    "不接 → 这里只写 PASS（大写，不加别的）\n"
    "接 → 最终回复内容，按上面 reasoning 定的语气和长度（默认 1 句、15-30 字）\n"
    "</reply>\n"
    "\n"
    "想记事的话在 </reply> 之后另起一行：MEM: 想记的内容\n"
    "</output_protocol>"
)

# 意图分类驱动的子风格——比 STYLE_GUIDE 通用约束更窄、更准。
# 模型先在 <intent> 选标签，对应规则就在这里查到，再写 <reply>。
INTENT_RULES = (
    "<intent_rules>\n"
    "**根据 reasoning 末尾 <intent> 的标签选对应风格——不同意图风格差很多：**\n"
    "- `joke` 玩梗/抽象/无厘头/谐音梗 → 直接接梗，禁分析腔（『有意思/这个梗挺/绷不住』全不要），不解释不追问\n"
    "- `vent` 吐槽/丧/抱怨/求安慰 → 短共情一句，**禁追问**（咋了/为啥/怎么了），**禁给方案**，让对方感觉被听到就行\n"
    "- `share` 分享视频/图/链接/B站 → 评论**具体内容**（图里啥/视频啥），别说『分享得好』『谢谢分享』\n"
    "- `question` 真问问题/求信息/求建议 → 直接答内容，别铺垫『这是个好问题』，别绕弯\n"
    "- `troll` 调戏/捧杀/装弱/挑事 → 高情商阴阳，绵里藏针留台阶，不接招不捧场\n"
    "- `chat` 默认闲聊 → 走 STYLE_GUIDE 基础风格\n"
    "</intent_rules>"
)


class Agent:
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.deepseek.com",
        model: str = "deepseek-chat",
        bot_qq: str = "",
        bot_name: str = "",
        anthropic_key: str = "",
        anthropic_base_url: str = "",
        anthropic_private_model: str = "",
        napcat_api: str = "http://127.0.0.1:3000",
        trigger_count: int = 30,
        context_len: int = 120,
        followup_window: int = 120,
        memory_file: str = "memory.json",
        memory_max_per_group: int = 50,
        owner_qq: str = "",
        owner_name: str = "",
        owner_relationship: str = "",
        persona: Optional[str] = None,
        on_reply: Optional[Callable[[str, str], Awaitable[None]]] = None,
        fallback_model: str = "",
        rate_window: int = 60,
        rate_threshold: int = 5,
        fallback_duration: int = 300,
        eval_enable: bool = True,
        eval_model: str = "",
        eval_file: str = "eval.jsonl",
        vision_model: str = "",
        glm_api_key: str = "",
        glm_base_url: str = "https://open.bigmodel.cn/api/paas/v4",
        stickers_dir: str = "stickers",
        stickers_file: str = "stickers.json",
        message_debounce_sec: float = 2.5,
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.fallback_model = fallback_model or model
        self.rate_window = rate_window
        self.rate_threshold = rate_threshold
        self.fallback_duration = fallback_duration
        self.model_calls: deque = deque()
        self._fallback_until: float = 0.0
        self.bot_qq = str(bot_qq)
        self.bot_name = bot_name
        self.anthropic_key = anthropic_key
        self.anthropic_base_url = anthropic_base_url.rstrip("/") if anthropic_base_url else ""
        self.anthropic_private_model = anthropic_private_model
        self.napcat_api = napcat_api.rstrip("/")
        self.trigger_count = trigger_count
        self.context_len = context_len
        self.followup_window = followup_window
        self.persona = persona if persona is not None else _load_persona()
        self.owner_relationship = owner_relationship
        self.on_reply = on_reply
        self.buffers: dict[str, deque] = defaultdict(lambda: deque(maxlen=context_len))
        self.counters: dict[str, int] = defaultdict(int)
        self.last_reply_at: dict[str, float] = defaultdict(float)
        self.locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
        self.active_users: dict[str, deque] = defaultdict(lambda: deque(maxlen=20))

        self.memory_file = Path(memory_file)
        if not self.memory_file.is_absolute():
            self.memory_file = Path(__file__).parent / self.memory_file
        self.memory_max = memory_max_per_group
        self.memories: dict[str, list[dict]] = self._load_memories()

        self.owner_qq = str(owner_qq) if owner_qq else ""
        self.owner_name = owner_name

        self.image_caption_cache: dict[str, str] = {}
        # B 站视频元信息缓存（key=qqdocurl，value={title,up,desc,summary}）
        # 同一视频在同群被多次分享只查一次 API
        self.bili_info_cache: dict[str, dict] = {}
        # WBI 签名密钥缓存（B 站 conclusion/get 等接口需要签名）
        # 24h 过期重拉；失败时为 ("","")，跳过 AI 总结
        self._wbi_keys: tuple[str, str] = ("", "")
        self._wbi_keys_ts: float = 0.0
        # 私聊：每个 user 存真实 OpenAI-format message 历史
        self.private_history: dict[str, list[dict]] = {}

        # Anthropic 异步客户端（缓存复用）
        self._anthropic_client = None

        # Self-eval: background scoring of every reply, written to eval.jsonl
        self.eval_enable = eval_enable
        self.eval_model = eval_model or self.fallback_model or self.model
        eval_path = Path(eval_file)
        if not eval_path.is_absolute():
            eval_path = Path(__file__).parent / eval_path
        self.eval_file = eval_path

        # Vision model for image understanding. Must be explicitly set to a vision-capable
        # model (e.g. claude-haiku, glm-4v). If empty, vision is disabled and we go straight
        # to OCR — avoids text-only models hallucinating image descriptions.
        # Routing by model-name prefix:
        #   "glm-*"    → 智谱 OpenAI-compat endpoint via GLM_API_KEY/GLM_BASE_URL
        #   "claude-*" → ANTHROPIC_BASE_URL (real Anthropic or deepseek anthropic-compat)
        self.vision_model = (vision_model or "").strip()
        self.glm_api_key = glm_api_key
        self.glm_base_url = glm_base_url.rstrip("/") if glm_base_url else ""

        # Sticker library — auto-steal + auto-tag, see stickers.py
        stickers_path = Path(stickers_dir)
        if not stickers_path.is_absolute():
            stickers_path = Path(__file__).parent / stickers_path
        stickers_json = Path(stickers_file)
        if not stickers_json.is_absolute():
            stickers_json = Path(__file__).parent / stickers_json
        self.stickers = StickerLibrary(
            stickers_dir=stickers_path,
            stickers_file=stickers_json,
            unknown_log=Path(__file__).parent / "unknown_stickers.jsonl",
            anthropic_caller=self._call_anthropic,
            tagger_model="deepseek-chat",
        )

        # Few-shot examples (curated by user via tools/prompt_lab.py)
        self.examples_file = Path(__file__).parent / "examples.jsonl"
        self._examples_cache: list = []
        self._examples_mtime: float = 0.0

        # Preference pairs (rejected/chosen) auto-extracted from feedback.jsonl
        # Hermes-style contrastive learning: stronger signal than chosen-only examples
        self.feedback_file = Path(__file__).parent / "feedback.jsonl"
        self._pairs_cache: list = []
        self._pairs_mtime: float = 0.0

        # Message debounce: short wait before responding so consecutive short
        # messages from the same user batch into one LLM call.
        # Implemented via per-group monotonic seq — only the latest message in
        # a burst triggers _think; older ones drop on seq mismatch.
        self.message_debounce_sec = max(0.0, message_debounce_sec)
        self._msg_seq: dict[str, int] = defaultdict(int)

        # Count of in-flight vision describes per group. When user A posts an
        # image and user B @s the bot almost simultaneously, B's phase 2 would
        # otherwise fire before vision finishes for A, leading to "看不到" reply.
        # Phase 2 entry waits briefly if vision is still pending in same group.
        self._vision_in_flight: dict[str, int] = defaultdict(int)

        # Sticky call marker: when an @/named-call comes in, remember it for a
        # short window so a follow-up image/text message in the same burst
        # (which loses seq race in debounce) still produces a `called` reply
        # @-ing the original caller. Without this, "<bot-name><image><image>" pattern
        # silently downgrades to followup/judge and loses the call context.
        self._sticky_call: dict[str, dict] = {}

        self.enabled = bool(api_key)
        if not self.enabled:
            logger.warning("[Agent] DEEPSEEK_API_KEY 未配置，%s 已禁用", bot_name)

    async def handle(self, payload: dict) -> bool:
        if not self.enabled:
            return False
        if payload.get("post_type") and payload.get("post_type") != "message":
            return False

        message_type = payload.get("message_type", "group")
        user_id = str(payload.get("user_id", ""))

        # 私聊：仅响应 owner
        if message_type == "private":
            if not self.owner_qq or user_id != self.owner_qq:
                return False
            return await self._handle_private(user_id, payload)

        group_id = str(payload.get("group_id", "")).strip()
        if not group_id:
            return False

        # Track vision in-flight per group so concurrent non-image messages can
        # wait for this group's vision to finish before processing (avoids
        # "图片看不到" replies when someone else's image is still being described).
        has_image = any(
            isinstance(seg, dict) and seg.get("type") == "image"
            for seg in payload.get("message", [])
        )
        if has_image:
            self._vision_in_flight[group_id] += 1
        try:
            text = await self._extract_text(payload)
        finally:
            if has_image:
                self._vision_in_flight[group_id] = max(0, self._vision_in_flight[group_id] - 1)
        if not text:
            return False

        sender = payload.get("sender", {})
        nickname = (sender.get("card") or sender.get("nickname") or "?")[:8]

        is_at = self._is_at_me(payload)
        is_called = self.bot_name in text
        # < 4 字的「嗯」「哦」「6」等噪音消息：进 buffer 但不计入触发计数
        is_noise = len(text.strip()) < 4 and not (is_at or is_called)

        is_owner_msg = bool(self.owner_qq) and user_id == self.owner_qq

        # === Phase 1: 吸收消息、处理立即指令、标记 seq ===
        async with self.locks[group_id]:
            self._append_buffer(group_id, nickname, text[:200], user_id)
            self.active_users[group_id].append((user_id, nickname))
            if not is_noise:
                self.counters[group_id] += 1

            # 显式记忆命令：立即回复，不走 debounce
            if is_called or is_at:
                mem_reply = self._handle_memory_command(group_id, text, user_id, nickname)
                if mem_reply is not None:
                    await self._send_qq(group_id, mem_reply, user_id if (is_at or is_called) else "")
                    self.last_reply_at[group_id] = time.time()
                    self._append_buffer(group_id, self.bot_name, mem_reply)
                    if self.on_reply:
                        try:
                            await self.on_reply(group_id, mem_reply)
                        except Exception as e:
                            logger.warning("[Agent] on_reply 回调失败: %s", e)
                    logger.info("[Agent] 记忆命令 (group=%s): %s", group_id, mem_reply[:60])
                    return True

            # Sticky-call：本条是 @ 或叫名字时把召唤者记下来。
            # 后续同 burst 内如果有人发图/补一句话抢走了 seq race，phase 2
            # 能凭这个记录把 mode 从 followup/judge 提升回 called，并 AT 原召唤者。
            if is_at or is_called:
                self._sticky_call[group_id] = {
                    "user_id": user_id,
                    "nickname": nickname,
                    "ts": time.time(),
                }

            # 标记本条 seq；其它消息后到时会让我变成"非最新"
            self._msg_seq[group_id] += 1
            my_seq = self._msg_seq[group_id]

        # === Debounce: lock 外短等，让连续消息聚合 ===
        # bare-call (光叫名字/@没实质内容) → 翻倍等，给追发的图/补文留时间，
        # 避免 "<bot>" → 5s → <image> 这种节奏首次回复错过图。
        bare_after_strip = (
            text.replace(f"@{self.bot_name}", "").replace(self.bot_name, "").strip()
        )
        is_bare_call = (is_at or is_called) and len(bare_after_strip) <= 4
        debounce_sec = 5.0 if is_bare_call else self.message_debounce_sec
        if debounce_sec > 0:
            try:
                await asyncio.sleep(debounce_sec)
            except asyncio.CancelledError:
                return False

        # Wait for any in-flight vision in this group (up to 4s extra).
        # Fixes the case where user A posts an image and user B @s the bot in
        # the same window — without this wait, B processes before A's vision
        # finishes and replies "图片看不到".
        vision_waited = 0.0
        while self._vision_in_flight.get(group_id, 0) > 0 and vision_waited < 4.0:
            await asyncio.sleep(0.3)
            vision_waited += 0.3
        if vision_waited > 0:
            logger.debug("[Agent] waited %.1fs for vision in group=%s", vision_waited, group_id)

        # === Phase 2: 重入 lock；只有最新那条消息往下走 LLM ===
        async with self.locks[group_id]:
            if self._msg_seq.get(group_id, 0) != my_seq:
                # 同 group 后面又来消息了 → 让最新那条触发，我直接跳过
                logger.debug("[Agent] debounce drop (group=%s seq=%d latest=%d)",
                             group_id, my_seq, self._msg_seq.get(group_id, 0))
                return False

            in_followup = (
                time.time() - self.last_reply_at[group_id] < self.followup_window
            )

            # Sticky-call inheritance: earlier @ in same group might still be warm.
            # Its original message lost the seq race, so unless we re-route here
            # the winning follow-up (image / "你看这个") drops to followup/judge
            # and loses the call context.
            sticky = self._sticky_call.get(group_id)
            sticky_ttl = self.message_debounce_sec + 5.0
            sticky_active = (
                sticky is not None
                and time.time() - sticky["ts"] < sticky_ttl
            )

            caller_override = None
            if is_owner_msg:
                mode = "owner"
            elif is_at or is_called:
                mode = "called"
            elif sticky_active:
                mode = "called"
                user_id = sticky["user_id"]
                nickname = sticky["nickname"]
                caller_override = (nickname, user_id)
                logger.info(
                    "[Agent] sticky-call upgrade (group=%s caller=%s nick=%s age=%.1fs)",
                    group_id, user_id, nickname, time.time() - sticky["ts"],
                )
            elif in_followup:
                mode = "followup"
            elif self.counters[group_id] >= self.trigger_count:
                mode = "judge"
            else:
                return False

            self.counters[group_id] = 0
            # Sticky 消费完或已无关，清掉避免污染后续 burst
            self._sticky_call.pop(group_id, None)

            try:
                reply = await self._think(group_id, mode, text, caller_override=caller_override)
            except Exception as e:
                logger.warning("[Agent] LLM 调用失败 (mode=%s): %s", mode, e)
                # called 模式被 @ 时静默会显得很冷；发一句简短兜底
                if mode == "called":
                    import random
                    fallback = random.choice([
                        "诶 我这会儿有点卡",
                        "稍等下 网炸了",
                        "信号不太对 等等",
                    ])
                    try:
                        await self._send_qq(group_id, fallback, user_id)
                        self.last_reply_at[group_id] = time.time()
                        self._append_buffer(group_id, self.bot_name, fallback)
                    except Exception:
                        pass
                return False

            # 抽出可选的 MEM 行（即使最后判 PASS，也允许保留记忆）
            reply, auto_mem = self._split_reply_and_mem(reply or "")

            if not reply or reply.strip().upper().startswith("PASS"):
                logger.info("[Agent] PASS (mode=%s, group=%s)", mode, group_id)
                if auto_mem:
                    self._save_auto_memory(group_id, auto_mem)
                # followup 模式下被 PASS：说明对话已经转向他人，立刻退出 followup
                # 避免后续每条消息都白白调 LLM 烧 token
                if mode == "followup":
                    self.last_reply_at[group_id] = 0.0
                return False

            reply = reply.strip().strip('"').strip("「」")
            # 解析模型输出的 [AT:qq号] 标记
            at_uid = ""
            at_match = re.search(r'\[AT:(\d+)\]', reply)
            if at_match:
                at_uid = at_match.group(1)
                reply = reply.replace(at_match.group(0), "").strip()
            if not at_uid and mode == "called":
                at_uid = user_id
            # reply length no longer truncated here; _send_qq handles splitting
            if auto_mem:
                self._save_auto_memory(group_id, auto_mem)
            await self._send_qq(group_id, reply, at_uid)
            self.last_reply_at[group_id] = time.time()
            # 记入 buffer 让下次上下文连贯，但不算入触发计数（避免自激）
            self._append_buffer(group_id, self.bot_name, reply)

            if self.on_reply:
                try:
                    await self.on_reply(group_id, reply)
                except Exception as e:
                    logger.warning("[Agent] on_reply 回调失败: %s", e)

            logger.info("[Agent] 回复 (mode=%s, group=%s): %s", mode, group_id, reply[:60])

            # Fire-and-forget self-evaluation (won't block, won't crash main flow)
            if self.eval_enable:
                asyncio.create_task(self._evaluate_reply(group_id, mode, text, reply))

            return True

    # -------- 私聊（owner 专属，无人设，直接对话） --------
    async def _handle_private(self, user_id: str, payload: dict) -> bool:
        text = await self._extract_text(payload)
        if not text:
            return False

        async with self.locks[f"private:{user_id}"]:
            history = self.private_history.setdefault(user_id, [])
            history.append({"role": "user", "content": text})
            # 最多保留 40 条（20 轮），超出时从头裁
            if len(history) > 40:
                self.private_history[user_id] = history[-40:]
                history = self.private_history[user_id]

            try:
                reply = await self._chat_private(history)
            except Exception as e:
                logger.warning("[Agent] 私聊 LLM 失败: %s", e)
                return False

            if not reply:
                return False

            history.append({"role": "assistant", "content": reply})
            await self._send_private_qq(user_id, reply)
            logger.info("[Agent] 私聊 (%s): %s", user_id, reply[:80])
            return True

    async def _chat_private(self, history: list[dict]) -> str:
        """Private chat with owner. Uses Anthropic SDK + DeepSeek anthropic endpoint."""
        last_user = next(
            (m.get("content", "") for m in reversed(history) if m.get("role") == "user"),
            "",
        )
        system = (
            f"<persona>\n{self.persona}\n"
            + (f"现在和你私聊的是 {self.owner_name}"
               + (f"（{self.owner_relationship}）" if self.owner_relationship else "")
               + "。私聊里说话可以更放松直接，但保持人设。\n"
               if self.owner_name else "")
            + "</persona>\n\n"
            f"{STYLE_GUIDE}\n\n"
            f"{INTENT_RULES}\n\n"
            f"{TOOL_GUIDE}"
            f"{self._sticker_guide_for_prompt()}"
            f"{self._examples_for_prompt(focus_text=last_user)}\n\n"
            f"<rules>\n"
            f"- 别透露自己是 AI、别说自己的模型名/版本号\n"
            f"- 哪怕回答信息量大，也要用聊天口吻一段段说，不要写文档\n"
            f"</rules>\n\n"
            f"[当前北京时间] {self._current_time_str()}\n\n"
            f"{REASONING_PROTOCOL}"
        )
        raw = await self._call_anthropic(
            system=system,
            messages=history,
            model=self.anthropic_private_model,
            max_tokens=2048,
            enable_search=True,
            max_search_uses=3,
        )
        reply, reasoning, intent = self._parse_hermes_output(raw)
        if reasoning:
            logger.info("[Agent] reasoning (private intent=%s): %s",
                        intent or "?", reasoning.replace("\n", " | ")[:240])
        return reply

    async def _send_private_qq(self, user_id: str, text: str) -> None:
        text = self._sanitize_reply(text)
        if not text:
            return
        try:
            chunks = self._split_text(text)
            for i, chunk in enumerate(chunks):
                if i > 0:
                    await asyncio.sleep(self._typing_delay(chunk))
                async with httpx.AsyncClient(timeout=10) as client:
                    r = await client.post(
                        f"{self.napcat_api}/send_private_msg",
                        json={"user_id": int(user_id), "message": chunk},
                    )
                    if r.status_code != 200:
                        logger.warning("[Agent] NapCat private reply %d: %s", r.status_code, r.text[:200])
        except Exception as e:
            logger.warning("[Agent] send private msg failed: %s", e)

    async def _extract_text(self, payload: dict) -> str:
        parts: list[str] = []
        group_id = str(payload.get("group_id", ""))
        sender_uid = str(payload.get("user_id", ""))
        for seg in payload.get("message", []):
            if not isinstance(seg, dict):
                continue
            t = seg.get("type")
            d = seg.get("data", {}) if isinstance(seg.get("data"), dict) else {}
            if t == "text":
                parts.append(d.get("text", ""))
            elif t == "at":
                qq = str(d.get("qq", ""))
                parts.append(f"@{self.bot_name}" if qq == self.bot_qq else f"@{qq}")
            elif t == "image":
                url = d.get("url") or d.get("file", "")
                file_field = d.get("file", "")
                if not url:
                    parts.append("[图片]")
                    continue
                # Sticker library: zero-cost md5 lookup via NapCat file field
                entry = self.stickers.lookup_by_file_field(file_field)
                if entry and entry.get("auto_tagged") and entry.get("meaning"):
                    parts.append(f"[表情包：{entry['meaning']}]")
                    # Background: record this new context sighting (no download)
                    asyncio.create_task(self._record_sticker_context(
                        entry["md5"], group_id, sender_uid,
                    ))
                    continue
                # Unknown or untagged — vision describe + background steal
                desc = await self._describe_image(url)
                parts.append(f"[图：{desc}]" if desc else "[图片]")
                if group_id and sender_uid != self.bot_qq:
                    asyncio.create_task(self._steal_image_async(
                        url=url,
                        sender_uid=sender_uid,
                        group_id=group_id,
                    ))
            elif t == "face":
                parts.append("[表情]")
            elif t == "reply":
                parts.append("[回复]")
            elif t == "json":
                raw_data = d.get("data", "")
                if raw_data:
                    desc = await self._describe_share(raw_data)
                    parts.append(desc if desc else "[分享卡]")
                else:
                    parts.append("[分享卡]")
        if parts:
            return "".join(parts).strip()
        return payload.get("raw_message", "").strip()

    async def _record_sticker_context(self, md5: str, group_id: str, sender_uid: str) -> None:
        """Lightweight: log another context sighting for a known sticker
        (skipping the byte download since md5 already matches the entry)."""
        if not md5 or not group_id:
            return
        entry = self.stickers.lookup_by_md5(md5)
        if not entry:
            return
        filename = self.stickers._md5_index.get(md5)
        if not filename:
            return
        entry["use_count"] = entry.get("use_count", 0) + 1
        ctx = self._sticker_context_lines(group_id)
        self.stickers._append_context(filename, sender_uid, ctx)

    async def _fetch_image_bytes(self, url: str) -> bytes | None:
        """Fetch image bytes. Handles file:// (local read for NapCat local-cache
        mode) and http(s) (httpx)."""
        if not url:
            return None
        if url.startswith("file://"):
            from urllib.parse import urlparse, unquote
            parsed = urlparse(url)
            local = unquote(parsed.path)
            # Windows: file:///C:/path → parsed.path is "/C:/path"; strip leading /
            if len(local) > 3 and local[0] == "/" and local[2] == ":":
                local = local[1:]
            try:
                return Path(local).read_bytes()
            except Exception as e:
                logger.debug("[Agent] file:// read failed (%s): %s", local, e)
                return None
        try:
            async with httpx.AsyncClient(timeout=15, follow_redirects=True) as c:
                r = await c.get(url, headers={"User-Agent": "Mozilla/5.0"})
                if r.status_code != 200:
                    return None
                return r.content
        except Exception as e:
            logger.debug("[Agent] http fetch failed (%s): %s", url, e)
            return None

    async def _steal_image_async(
        self,
        url: str,
        sender_uid: str,
        group_id: str,
    ) -> None:
        """Background download + steal + maybe-tag. Fire-and-forget."""
        try:
            img_bytes = await self._fetch_image_bytes(url)
            if not img_bytes:
                return
            ctx_lines = self._sticker_context_lines(group_id)
            md5 = await self.stickers.steal(
                image_bytes=img_bytes,
                url=url,
                src_user=sender_uid,
                src_group=group_id,
                context_before=ctx_lines,
            )
            if md5:
                await self.stickers.maybe_tag(md5)
        except Exception as e:
            logger.debug("[Agent] steal failed: %s: %s",
                         type(e).__name__, str(e) or "(no message)")

    def _sticker_context_lines(self, group_id: str, n: int = 6) -> list[str]:
        """Format the most recent buffer entries as 'name: text' lines for
        sticker context capture. Excludes bot's own messages."""
        buf = list(self.buffers.get(group_id, []))
        out: list[str] = []
        for m in buf[-n:]:
            if not m.get("user_id"):  # bot's own
                continue
            out.append(f"{m.get('name','?')}: {m.get('text','')[:80]}")
        return out

    async def _describe_share(self, raw_json: str) -> str:
        """Parse a QQ mini-app share-card JSON segment into a text line the LLM
        can read. Special-cases B站 video shares (resolves shortlink, fetches
        full title/up/desc via web-interface/view); other shares fall back to
        whatever title+desc the card already carries."""
        try:
            outer = json.loads(raw_json)
        except (TypeError, ValueError, json.JSONDecodeError):
            return ""
        if not isinstance(outer, dict):
            return ""

        prompt = outer.get("prompt", "") or ""
        meta = outer.get("meta") or {}
        if not isinstance(meta, dict):
            meta = {}
        detail = (
            meta.get("detail_1")
            or meta.get("news")
            or meta.get("music")
            or meta.get("video")
            or {}
        )
        if not isinstance(detail, dict):
            return prompt[:80]

        title_field = detail.get("title", "") or ""
        desc_field = detail.get("desc", "") or ""
        url = (
            detail.get("qqdocurl")
            or detail.get("jumpUrl")
            or detail.get("url")
            or ""
        )

        is_bili = (
            "哔哩哔哩" in prompt
            or "哔哩哔哩" in title_field
            or "bilibili" in url.lower()
            or "b23.tv" in url.lower()
        )
        if is_bili:
            info = await self._fetch_bili_info(url)
            if info:
                video_title = info.get("title") or desc_field
                up = info.get("up", "")
                video_desc = (info.get("desc", "") or "").strip().replace("\n", " ")[:80]
                summary = (info.get("summary", "") or "").strip().replace("\n", " ")
                line = f"[B站视频]《{video_title}》"
                if up:
                    line += f" — up主{up}"
                # AI 总结优先于自填简介——通常更紧凑、更贴近实际内容
                if summary:
                    line += f"，AI总结:{summary[:200]}"
                elif video_desc:
                    line += f"，简介:{video_desc}"
                return line
            return f"[B站视频]《{desc_field}》" if desc_field else "[B站视频]"

        if title_field and desc_field:
            return f"[分享|{title_field}]{desc_field[:80]}"
        return f"[分享|{title_field or '未知'}]"

    async def _fetch_bili_info(self, url: str) -> dict:
        """Resolve b23.tv shortlinks → real URL → BVid; then call Bilibili web
        view API for title/up/desc. Returns {} on any failure so callers can
        gracefully fall back to the share-card's own title/desc."""
        if not url:
            return {}

        if url in self.bili_info_cache:
            return self.bili_info_cache[url]

        real_url = url
        if "b23.tv" in url:
            try:
                async with httpx.AsyncClient(timeout=5, follow_redirects=True) as client:
                    r = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
                    real_url = str(r.url)
            except Exception as e:
                logger.debug("[Agent] b23.tv 解析失败 (%s): %s", url, e)

        m = re.search(r"BV[a-zA-Z0-9]{10}", real_url)
        if not m:
            self.bili_info_cache[url] = {}
            return {}
        bvid = m.group(0)

        info: dict = {}
        cid: int = 0
        up_mid: int = 0
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                r = await client.get(
                    "https://api.bilibili.com/x/web-interface/view",
                    params={"bvid": bvid},
                    headers={"User-Agent": "Mozilla/5.0"},
                )
                r.raise_for_status()
                data = r.json()
                if data.get("code") == 0:
                    d = data.get("data") or {}
                    cid = int(d.get("cid") or 0)
                    up_mid = int((d.get("owner") or {}).get("mid") or 0)
                    info = {
                        "title": (d.get("title") or "")[:80],
                        "up": ((d.get("owner") or {}).get("name") or "")[:30],
                        "desc": (d.get("desc") or "")[:200],
                    }
        except Exception as e:
            logger.debug("[Agent] Bili view API 失败 (%s): %s", bvid, e)

        # AI 总结：拿到了 cid + up_mid 就尝试调一次，失败/无总结 graceful skip
        if info and cid and up_mid:
            summary = await self._fetch_bili_summary(bvid, cid, up_mid)
            if summary:
                info["summary"] = summary

        self.bili_info_cache[url] = info
        if len(self.bili_info_cache) > 200:
            for k in list(self.bili_info_cache.keys())[:50]:
                self.bili_info_cache.pop(k, None)
        logger.info("[Agent] bili view %s: %s", bvid, (info.get("title") or "(空)")[:60])
        return info

    # WBI 签名置换表（B 站固定 64 项常量，sign 算法的一部分）
    _WBI_MIXIN_KEY_ENC_TAB = [
        46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35,
        27, 43, 5, 49, 33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13,
        37, 48, 7, 16, 24, 55, 40, 61, 26, 17, 0, 1, 60, 51, 30, 4,
        22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11, 36, 20, 34, 44, 52,
    ]

    async def _fetch_wbi_keys(self) -> tuple[str, str]:
        """Fetch (img_key, sub_key) used to sign WBI requests; cached 24h.
        Returns ('','') on failure — caller should skip WBI-protected calls."""
        now = time.time()
        if self._wbi_keys[0] and now - self._wbi_keys_ts < 86400:
            return self._wbi_keys
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                r = await client.get(
                    "https://api.bilibili.com/x/web-interface/nav",
                    headers={"User-Agent": "Mozilla/5.0"},
                )
                data = (r.json().get("data") or {})
                wbi_img = data.get("wbi_img") or {}
                img_url = wbi_img.get("img_url", "") or ""
                sub_url = wbi_img.get("sub_url", "") or ""
                img_key = img_url.rsplit("/", 1)[-1].split(".")[0]
                sub_key = sub_url.rsplit("/", 1)[-1].split(".")[0]
                if img_key and sub_key:
                    self._wbi_keys = (img_key, sub_key)
                    self._wbi_keys_ts = now
                    return self._wbi_keys
        except Exception as e:
            logger.debug("[Agent] WBI keys fetch failed: %s", e)
        return ("", "")

    def _wbi_sign_params(
        self, params: dict, img_key: str, sub_key: str
    ) -> dict:
        """Apply WBI signing: appends wts + w_rid. Returns a new params dict."""
        orig = img_key + sub_key
        mixin = "".join(orig[i] for i in self._WBI_MIXIN_KEY_ENC_TAB if i < len(orig))[:32]
        signed = dict(sorted({**params, "wts": int(time.time())}.items()))
        # 过滤 WBI 签名禁用字符
        signed = {
            k: "".join(c for c in str(v) if c not in "!'()*")
            for k, v in signed.items()
        }
        sign = hashlib.md5((urlencode(signed) + mixin).encode()).hexdigest()
        signed["w_rid"] = sign
        return signed

    async def _fetch_bili_summary(self, bvid: str, cid: int, up_mid: int) -> str:
        """Bilibili AI 总结：调 view/conclusion/get。失败/无总结返回空串。"""
        img_key, sub_key = await self._fetch_wbi_keys()
        if not img_key or not sub_key:
            return ""
        params = self._wbi_sign_params(
            {"bvid": bvid, "cid": cid, "up_mid": up_mid},
            img_key, sub_key,
        )
        try:
            async with httpx.AsyncClient(timeout=8) as client:
                r = await client.get(
                    "https://api.bilibili.com/x/web-interface/view/conclusion/get",
                    params=params,
                    headers={
                        "User-Agent": "Mozilla/5.0",
                        "Referer": f"https://www.bilibili.com/video/{bvid}",
                    },
                )
                r.raise_for_status()
                data = r.json()
                if data.get("code") != 0:
                    logger.debug("[Agent] bili summary %s: code=%s msg=%s",
                                 bvid, data.get("code"), data.get("message"))
                    return ""
                d = data.get("data") or {}
                mr = d.get("model_result") or {}
                # result_type: 0=无总结，1=只有大纲，2=summary+大纲
                if not mr.get("result_type"):
                    return ""
                summary = (mr.get("summary") or "").strip()
                outline = mr.get("outline") or []
                outline_titles: list[str] = []
                for sec in outline[:5]:
                    t = (sec.get("title") or "").strip()
                    if t:
                        outline_titles.append(t[:30])
                line = summary
                if outline_titles:
                    sep = " | 大纲:" if line else "大纲:"
                    line += sep + " / ".join(outline_titles)
                line = line[:300]
                if line:
                    logger.info("[Agent] bili summary %s: %s", bvid, line[:80])
                return line
        except Exception as e:
            logger.debug("[Agent] bili summary 失败 (%s): %s", bvid, e)
        return ""

    def _append_buffer(self, group_id: str, name: str, text: str, user_id: str = "") -> None:
        # 同人连续消息合并：减少 buffer 噪音 & 节省 token
        buf = self.buffers[group_id]
        if buf and buf[-1].get("name") == name and len(buf[-1].get("text", "")) < 300:
            buf[-1]["text"] = buf[-1]["text"] + " " + text
        else:
            buf.append({"name": name, "text": text, "user_id": user_id})

    def _is_at_me(self, payload: dict) -> bool:
        if not self.bot_qq:
            return False
        for seg in payload.get("message", []):
            if (
                isinstance(seg, dict)
                and seg.get("type") == "at"
                and str(seg.get("data", {}).get("qq")) == self.bot_qq
            ):
                return True
        return False

    def _get_anthropic_client(self):
        """惰性创建并缓存 anthropic AsyncClient。"""
        if self._anthropic_client is not None:
            return self._anthropic_client
        import anthropic as _anthropic
        kwargs: dict = {"api_key": self.anthropic_key or self.api_key}
        if self.anthropic_base_url:
            kwargs["base_url"] = self.anthropic_base_url
        elif self.base_url:
            kwargs["base_url"] = self.base_url + "/anthropic"
        self._anthropic_client = _anthropic.AsyncAnthropic(**kwargs)
        return self._anthropic_client

    async def _call_anthropic(
        self,
        system: str,
        messages: list[dict],
        model: str,
        max_tokens: int = 2048,
        enable_search: bool = True,
        max_search_uses: int = 2,
    ) -> str:
        """统一的 Anthropic 调用：自动带 web_search 工具、错误日志、空回复兜底。"""
        client = self._get_anthropic_client()
        kwargs: dict = {
            "model": model,
            "max_tokens": max_tokens,
            "system": system,
            "messages": messages,
        }
        if enable_search:
            kwargs["tools"] = [{
                "type": "web_search_20250305",
                "name": "web_search",
                "max_uses": max_search_uses,
            }]
        try:
            response = await client.messages.create(**kwargs)
        except Exception as e:
            logger.warning("[Agent] Anthropic API 调用失败 (model=%s): %s", model, e)
            raise
        text = "".join(
            getattr(b, "text", "") for b in response.content if getattr(b, "text", "")
        ).strip()
        if not text:
            logger.warning("[Agent] Anthropic 返回空文本 stop_reason=%s blocks=%s",
                           getattr(response, "stop_reason", "?"),
                           [type(b).__name__ for b in response.content])
        return text

    async def _evaluate_reply(
        self, group_id: str, mode: str, user_msg: str, reply: str
    ) -> None:
        """Background quality eval. Scores 1-5 via cheap model, appends to eval.jsonl.
        Never raises — eval failures must not affect main reply flow."""
        try:
            # Take last 5 buffer entries EXCLUDING the bot reply we just appended
            ctx_msgs = list(self.buffers[group_id])[-6:-1]
            ctx_text = "\n".join(f"{m['name']}: {m['text']}" for m in ctx_msgs)

            eval_prompt = (
                f"评估 QQ 群聊回复质量。1-5 打分，5=完美自然，4=不错有小瑕疵，"
                f"3=一般有点出戏，2=差明显不合适，1=灾难。\n\n"
                f"群聊上下文：\n---\n{ctx_text}\n---\n"
                f"{self.bot_name or 'bot'}的回复：「{reply}」\n\n"
                f"人设：{self.bot_name or 'bot'} 是 QQ 群里的普通群友，自然口语，有自己脾气，不油腻不客套，"
                f"该接梗接梗，该正经正经。\n"
                f"考察：1) 是否贴上下文 2) 是否符合人设 3) 是否自然不像 AI 4) 长度是否合理。\n"
                f'只输出 JSON：{{"score": 整数1-5, "reason": "一句话原因"}}'
            )

            async with httpx.AsyncClient(timeout=15) as client:
                r = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={
                        "model": self.eval_model,
                        "messages": [
                            {"role": "system", "content": "You are a strict reply quality evaluator. Output JSON only, no markdown."},
                            {"role": "user", "content": eval_prompt},
                        ],
                        "temperature": 0,
                        "max_tokens": 120,
                        "response_format": {"type": "json_object"},
                    },
                )
                r.raise_for_status()
                content = r.json()["choices"][0]["message"]["content"]

            data = json.loads(content)
            score = int(data.get("score", 0))
            reason = str(data.get("reason", ""))[:200]

            record = {
                "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "group_id": group_id,
                "mode": mode,
                "user_msg": user_msg[:200],
                "reply": reply[:300],
                "score": score,
                "reason": reason,
            }
            self._append_with_rotation(
                self.eval_file,
                json.dumps(record, ensure_ascii=False) + "\n",
            )

            if score <= 2:
                logger.warning("[Agent] LOW-SCORE reply (%d/5) mode=%s: %s | reason=%s",
                               score, mode, reply[:60], reason)
            else:
                logger.debug("[Agent] eval %d/5 mode=%s: %s", score, mode, reason)
        except Exception as e:
            logger.debug("[Agent] reply evaluation failed: %s: %s",
                         type(e).__name__, e)

    async def _think(
        self,
        group_id: str,
        mode: str,
        latest_text: str = "",
        caller_override: Optional[tuple] = None,
    ) -> str:
        # 不同模式用不同上下文长度省 token
        all_history = list(self.buffers[group_id])
        if mode == "followup":
            history = all_history[-30:]
        elif mode == "called":
            history = all_history[-30:]
        elif mode == "owner":
            history = all_history[-30:]
        else:
            history = all_history
        def _fmt_line(m: dict) -> str:
            uid = m.get("user_id", "")
            if uid:
                return f"[{m['name']}|qq={uid}] {m['text']}"
            return f"[{m['name']}] {m['text']}"  # bot self or anonymous
        history_text = "\n".join(_fmt_line(m) for m in history)

        # Identify the latest non-bot speaker for explicit framing in prompt.
        # When caller_override is set (sticky-call inheritance), trust that
        # instead of buffer order — the original @-er is the right "针对" target,
        # even if someone else slipped a message in between their @ and the
        # winning burst message.
        if caller_override:
            latest_nick, latest_uid = caller_override
        else:
            latest_nick, latest_uid = "", ""
            for m in reversed(history):
                if m.get("user_id"):  # bot's own entries have empty user_id
                    latest_nick = m["name"]
                    latest_uid = m["user_id"]
                    break

        # Time line is invisible metadata — used to ground the model's internal time sense
        # so it doesn't hallucinate "凌晨三点" at noon. NOT for the model to bring up in replies.
        time_line = (
            f"[元信息] 现在北京时间 {self._current_time_str()}。"
            f"**仅用于内部时间感知**——回复里别主动提时间/别拿时间当调侃点，除非对方问。"
            f"群聊上下文里如果出现别的时间数字，那是过去的事，不是现在。\n\n"
        )

        # 焦点抽取：扫最近 5 条找图/分享卡/B站视频描述，单独抽到顶部，避免模型在
        # 长 history 里漏掉视觉内容。模型默认看文字更敏感，需要主动提醒。
        focus_block = ""
        focus_items: list[str] = []
        focus_pat = re.compile(r"(\[图：[^\]]+\]|\[B站视频\][^\n\[]+|\[分享\|[^\]]+\][^\n\[]*)")
        for m in history[-5:]:
            for hit in focus_pat.findall(m.get("text", "")):
                if hit not in focus_items:
                    focus_items.append(hit.strip())
        if focus_items:
            focus_block = (
                "[本轮焦点内容]（必看，别漏，回复要扣这些）：\n"
                + "\n".join(f"- {item}" for item in focus_items[-4:])
                + "\n\n"
            )

        mem_instruction = (
            "\n\n[可选记忆抽取]\n"
            "如果群聊里出现了值得长期记住的事实（某人的真实身份/职业/爱好/外号/重要状态等），"
            "在回复后另起一行输出 `MEM:简短一句话`。例：\n"
            "MEM:张三是开发者\n"
            "MEM:李四养了一只猫叫橘子\n"
            "限制：仅记真实事实，不记当下情绪、玩笑话、临时状态。没什么好记的就不要输出 MEM 行。"
        )

        # Decision signals shared across modes
        signals = self._compute_chat_signals(group_id, history)

        decision_framework = (
            "判断要不要回，从下面这些信号综合判断（不要只看最新一条）：\n"
            f"- 话题热度：最近几条是不是围绕同一个话题 / 频率多高（{signals['热度']}）\n"
            f"- 话题类型：闲聊/吐槽/玩梗 → 倾向回；严肃讨论/工作细节/争吵/敏感 → 倾向 PASS（当前类型：{signals['类型']}）\n"
            f"- 活跃人数：多人在聊插话不突兀；只有 1 人独白要慎重（最近活跃：{signals['活跃人数']} 人）\n"
            f"- 你的最近发言：刚说完不久就别再硬插；很久没冒泡可以刷存在感（你上次发言：{signals['上次发言']}）\n"
            f"- 气氛：冷场可以适度破冰；激烈争论别插\n"
            "宁可不发也别尬聊。但**该接的地方一定要接住**，不要冷处理。\n"
        )

        speaker_hint = (
            f"（最后一条是 {latest_nick}（qq={latest_uid}）说的）"
            if latest_nick else ""
        )

        if mode == "called":
            user_prompt = (
                f"{time_line}"
                f"{focus_block}"
                f"以下是最近的群聊{speaker_hint}，点名/at 了你：\n"
                f"---\n{history_text}\n---\n"
                f"被点名了所以基本一定要回（除非纯粹是路过提了一嘴你名字，跟你完全无关）。\n"
                f"回复直接针对 {latest_nick or '点你的人'}，自然像真人。"
                f"{mem_instruction}"
            )
        elif mode == "owner":
            user_prompt = (
                f"{time_line}"
                f"{focus_block}"
                f"以下是最近的群聊（最后一条是你哥{self.owner_name}说的）：\n"
                f"---\n{history_text}\n---\n"
                f"{self.owner_name}是你哥，**默认倾向回他**——聊天/问问题/吐槽/分享心情都接。\n"
                f"在跟群里别人单线讨论工作/技术细节、跟你无关 → PASS。\n"
                f"按 protocol 的 PASS 信号判断（即使是哥，结束信号/碎片输入也照 PASS）。\n"
                f"{mem_instruction}"
            )
        elif mode == "followup":
            user_prompt = (
                f"{time_line}"
                f"{focus_block}"
                f"以下是最近的群聊{speaker_hint}，你刚刚发过言，现在群里有新消息：\n"
                f"---\n{history_text}\n---\n"
                f"判断这条新消息：在问你/接你的话/扩展话题 → 回；其它情况按 protocol 的 PASS 信号判断。\n"
                f"如果要回，针对 {latest_nick or '说话的人'} 一个对象回，别拧上别人的话。\n"
                f"**宁可 PASS 不要硬接**——粘人比冷漠扣分多。\n"
                f"{decision_framework}"
                f"{mem_instruction}"
            )
        else:
            active_text = self._active_users_for_prompt(group_id)
            at_hint = ""
            if active_text:
                at_hint = (
                    f"- 没特别想说的，也可以找活跃群友搭句话；想 @某人在句首加 [AT:对方QQ号]，比如 [AT:123456] 然后接话\n"
                )
            user_prompt = (
                f"{time_line}"
                f"{focus_block}"
                f"以下是最近的群聊：\n"
                f"---\n{history_text}\n---\n"
                f"你不被任何人点名，但累积了一段时间没说话，考虑要不要主动插话。\n"
                f"{decision_framework}"
                f"输出：\n"
                f"- PASS 或者你要说的话（不加引号前缀）\n"
                f"{at_hint}"
                f"{mem_instruction}"
            )
            if active_text:
                user_prompt += f"\n\n最近活跃群友：{active_text}"

        owner_block = ""
        if self.owner_qq:
            owner_block = (
                f"\n\n【特别的人】\n"
                f"{self.owner_name}在关系上是你哥哥，是你比较熟的人之一。"
                f"**就当熟人聊，少喊名字、少喊「哥」**——默认用「你」或者省略主语就好，"
                f"只有偶尔（一段对话里 0-1 次）才点一下「哥」当强调用，绝不要每句都喊。"
                f"相处自然就行——温柔开朗，比对其他人稍微上心一点、更倾向回他，但**不要过度亲昵、撒娇、黏他**。"
                f"他说错话或犯傻可以用高情商阴阳调侃一下（绵里藏针那种，留台阶），别变成直白的刻薄。"
                f"你是普通有个性的妹妹，不是恋爱脑、不是工具人。"
            )
        # Hermes 风格 system prompt：人设 + 风格硬约束 + 意图分流 + 工具能力 + 表情包 + few-shot 示例 + 关系 + 长期记忆 分段
        system_content = (
            f"<persona>\n{self.persona}\n</persona>\n\n"
            f"{STYLE_GUIDE}\n\n"
            f"{INTENT_RULES}\n\n"
            f"{TOOL_GUIDE}"
            f"{self._sticker_guide_for_prompt()}"
            f"{self._examples_for_prompt(focus_text=latest_text, mode=mode)}"
            f"{owner_block}"
            f"{self._memories_for_prompt(group_id, focus_text=latest_text)}\n\n"
            f"{REASONING_PROTOCOL}"
        )

        # owner 模式始终用主模型，不降级
        if mode == "owner":
            model_to_use = self.model
        else:
            model_to_use = self._pick_group_model()
        self.model_calls.append(time.time())

        # judge 模式只判断要不要插话，不联网；其它模式启用 web_search
        enable_search = mode in ("called", "owner", "followup")
        raw = await self._call_anthropic(
            system=system_content,
            messages=[{"role": "user", "content": user_prompt}],
            model=model_to_use,
            max_tokens=2048,
            enable_search=enable_search,
            max_search_uses=2,
        )
        reply, reasoning, intent = self._parse_hermes_output(raw)
        if reasoning:
            logger.info("[Agent] reasoning (mode=%s intent=%s): %s",
                        mode, intent or "?", reasoning.replace("\n", " | ")[:240])
        return reply

    @staticmethod
    def _append_with_rotation(path: Path, line: str, max_bytes: int = 5_000_000) -> None:
        """Append a line; rotate path to path.old when it would exceed max_bytes."""
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            sz = path.stat().st_size if path.exists() else 0
        except OSError:
            sz = 0
        if sz > max_bytes:
            old = path.with_suffix(path.suffix + ".old")
            try:
                if old.exists():
                    old.unlink()
                path.rename(old)
            except OSError as e:
                logger.warning("[Agent] log rotation failed for %s: %s", path, e)
        try:
            with path.open("a", encoding="utf-8") as f:
                f.write(line)
        except OSError as e:
            logger.warning("[Agent] log write failed for %s: %s", path, e)

    @staticmethod
    def _current_time_str() -> str:
        """北京时间 + 大致时段描述。给模型一个真实时间锚点，避免瞎编时间。"""
        from datetime import datetime, timezone, timedelta
        BJ = timezone(timedelta(hours=8))
        now = datetime.now(BJ)
        weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        h = now.hour
        if h < 5:
            part = "深夜"
        elif h < 7:
            part = "清晨"
        elif h < 11:
            part = "上午"
        elif h < 13:
            part = "中午"
        elif h < 18:
            part = "下午"
        elif h < 22:
            part = "晚上"
        else:
            part = "深夜"
        return f"{now.strftime('%Y-%m-%d %H:%M')} {weekdays[now.weekday()]} {part}"

    @staticmethod
    def _sanitize_reply(text: str) -> str:
        """Pre-flight regex strip catching what STYLE_GUIDE failed to suppress.
        Logs when it changes the text so prompt drift is observable."""
        if not text:
            return text
        original = text
        text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
        text = re.sub(r'(?<!\w)\*(.+?)\*(?!\w)', r'\1', text)
        text = re.sub(r'__(.+?)__', r'\1', text)
        text = re.sub(r'(?m)^#{1,6}\s+', '', text)
        text = re.sub(r'(?m)^[\-\*]\s+', '', text)
        text = re.sub(r'(?m)^\d+\.\s+', '', text)
        text = re.sub(r'`+([^`]+)`+', r'\1', text)
        text = re.sub(r'(?m)^>\s+', '', text)
        text = re.sub(r'(?m)^---+\s*$', '', text)
        text = text.translate(str.maketrans('', '', '「」『』《》【】'))
        text = re.sub(r'。+(?!\d)', ' ', text)
        text = text.replace('——', ' ').replace('—', ' ')
        text = text.replace('；', ',').replace(';', ',')
        text = re.sub(r'[（(][^（()）]{1,12}\.(?:jpg|png|gif|jpeg)[）)]', '', text, flags=re.IGNORECASE)
        text = re.sub(
            r'[（(](?:叹气|皱眉|笑哭|大笑|微笑|敲头|耸肩|摊手|无奈|尴尬|偷笑|捂脸|翻白眼|思考|沉思|惊讶|皱眉头)[）)]',
            '', text,
        )
        text = re.sub(
            r'['
            r'\U0001F300-\U0001F5FF'
            r'\U0001F600-\U0001F64F'
            r'\U0001F680-\U0001F6FF'
            r'\U0001F700-\U0001F77F'
            r'\U0001F780-\U0001F7FF'
            r'\U0001F900-\U0001F9FF'
            r'\U0001FA00-\U0001FA6F'
            r'\U0001FA70-\U0001FAFF'
            r'\U00002600-\U000026FF'
            r'\U00002700-\U000027BF'
            r']+',
            '', text,
        )
        text = re.sub(r'[ \t]+', ' ', text)
        text = re.sub(r' *\n *', '\n', text)
        text = text.strip()
        if text != original:
            logger.info("[Agent] sanitize: %r -> %r", original[:80], text[:80])
        return text

    @staticmethod
    def _split_text(text: str, max_len: int = 50) -> list[str]:
        """Split text on sentence punctuation to simulate human messaging."""
        parts = re.split(r'([。！？；\n]+)', text)
        chunks: list[str] = []
        cur = ""
        for part in parts:
            cur += part
            if len(cur) >= max_len or part.endswith(("\n", "。", "！", "？", "；")):
                chunks.append(cur.strip())
                cur = ""
        if cur.strip():
            chunks.append(cur.strip())

        # 合并过短的句子到上一条
        result: list[str] = []
        for c in chunks:
            if result and len(result[-1]) + len(c) < max_len:
                result[-1] += c
            else:
                result.append(c)
        return result or [text]

    @staticmethod
    def _typing_delay(chunk: str) -> float:
        """Simulate human typing speed: ~6-8 chars/sec + small pause. Capped at 7s."""
        chars_per_sec = random.uniform(6.0, 8.0)
        base = len(chunk) / chars_per_sec
        pause = random.uniform(0.4, 1.2)
        return min(base + pause, 7.0)

    @staticmethod
    def _parse_sticker_markers(text: str) -> list[tuple[str, str]]:
        """Split on [STICKER:tag] markers. Returns ordered (kind, value) where
        kind is 'text' or 'sticker'. Empty text segments dropped. Used by
        _send_qq to send mixed text/image messages."""
        out: list[tuple[str, str]] = []
        pattern = re.compile(r"\[STICKER:([^\]\s]+)\]")
        pos = 0
        for m in pattern.finditer(text):
            if m.start() > pos:
                seg = text[pos:m.start()].strip()
                if seg:
                    out.append(("text", seg))
            out.append(("sticker", m.group(1).strip()))
            pos = m.end()
        if pos < len(text):
            seg = text[pos:].strip()
            if seg:
                out.append(("text", seg))
        if not out and text.strip():
            out.append(("text", text.strip()))
        return out

    async def _napcat_send_group(self, group_id: str, message) -> None:
        """Single-shot send to NapCat. message: str or list of segments."""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.post(
                    f"{self.napcat_api}/send_group_msg",
                    json={"group_id": int(group_id), "message": message},
                )
                if r.status_code != 200:
                    logger.warning("[Agent] NapCat returned %d: %s",
                                   r.status_code, r.text[:200])
        except Exception as e:
            logger.warning("[Agent] send group msg failed: %s", e)

    async def _send_qq(self, group_id: str, text: str, at_user_id: str = "") -> None:
        text = self._sanitize_reply(text)
        if not text:
            return
        segments = self._parse_sticker_markers(text)
        is_first = True
        for kind, value in segments:
            if kind == "sticker":
                file_path = self.stickers.pick_by_tag(value)
                if not file_path or not file_path.exists():
                    logger.info("[Agent] sticker tag %r → no match, skipping", value)
                    continue
                # Brief delay before sticker too — simulates "finding the right one"
                await asyncio.sleep(random.uniform(0.6, 1.4))
                try:
                    img_b64 = base64.b64encode(file_path.read_bytes()).decode()
                except Exception as e:
                    logger.warning("[Agent] sticker read failed (%s): %s", file_path, e)
                    continue
                msg_segs: list = []
                if is_first and at_user_id:
                    msg_segs.append({"type": "at", "data": {"qq": str(at_user_id)}})
                msg_segs.append({"type": "image", "data": {"file": f"base64://{img_b64}"}})
                await self._napcat_send_group(group_id, msg_segs)
                is_first = False
                continue
            # text chunk — split for typing simulation
            chunks = self._split_text(value)
            for chunk in chunks:
                if not is_first:
                    await asyncio.sleep(self._typing_delay(chunk))
                if is_first and at_user_id:
                    message = [
                        {"type": "at", "data": {"qq": str(at_user_id)}},
                        {"type": "text", "data": {"text": chunk}},
                    ]
                else:
                    message = chunk
                await self._napcat_send_group(group_id, message)
                is_first = False

    async def check_missed_mentions(self) -> None:
        """启动后拉最近 10 条群消息，如有被 @/叫名字且未回复的，补处理 1 条。"""
        if not self.enabled:
            return
        fallback_groups = [g.strip() for g in os.getenv("QQ_GROUPS", "").split(",") if g.strip()]
        for group_id in list(self.buffers.keys()) or fallback_groups:
            try:
                async with httpx.AsyncClient(timeout=15) as client:
                    r = await client.post(
                        f"{self.napcat_api}/get_group_msg_history",
                        json={"group_id": int(group_id), "count": 10},
                    )
                    r.raise_for_status()
                    msgs = r.json().get("data", {}).get("messages", [])
                    for msg in reversed(msgs):
                        sender_id = str(msg.get("sender", {}).get("user_id", ""))
                        if sender_id == self.bot_qq:
                            continue
                        raw = msg.get("raw_message", "")
                        if self.bot_name in raw or f"@{self.bot_qq}" in raw:
                            logger.info("[Agent] 检测到离线未回复消息，补处理 (group=%s)", group_id)
                            await self.handle(msg)
                            break
            except Exception as e:
                logger.warning("[Agent] 检测离线消息失败 (group=%s): %s", group_id, e)

    async def probe_models(self) -> None:
        """启动时轻量探测，确认各端点实际返回的模型名。"""
        if not self.enabled:
            return

        # 群聊模型 (DeepSeek/OpenAI 格式)
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                r = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={
                        "model": self.model,
                        "messages": [{"role": "user", "content": "hi"}],
                        "max_tokens": 1,
                    },
                )
                r.raise_for_status()
                actual = r.json().get("model", "?")
                logger.info("[Agent] 群聊模型检测 OK: 配置=%s 实际=%s", self.model, actual)
        except Exception as e:
            logger.warning("[Agent] 群聊模型检测失败: %s", e)

        # 私聊模型 (Anthropic 兼容端点)
        if self.anthropic_key:
            try:
                import anthropic as _anthropic
                client_kwargs: dict = {"api_key": self.anthropic_key}
                if self.anthropic_base_url:
                    client_kwargs["base_url"] = self.anthropic_base_url
                client = _anthropic.AsyncAnthropic(**client_kwargs)
                response = await client.messages.create(
                    model=self.anthropic_private_model,
                    max_tokens=1,
                    messages=[{"role": "user", "content": "hi"}],
                )
                actual = getattr(response, "model", "?")
                logger.info("[Agent] 私聊模型检测 OK: 配置=%s 实际=%s", self.anthropic_private_model, actual)
            except Exception as e:
                logger.warning("[Agent] 私聊模型检测失败: %s", e)

    def _pick_group_model(self) -> str:
        """根据最近调用频率决定用主模型还是降级模型。"""
        now = time.time()
        # 清掉窗口期外的旧记录
        while self.model_calls and self.model_calls[0] < now - self.rate_window:
            self.model_calls.popleft()

        # 如果还在降级冷却期，继续用降级模型
        if self._fallback_until > now:
            return self.fallback_model

        # 频率超限 → 触发降级
        if len(self.model_calls) >= self.rate_threshold:
            self._fallback_until = now + self.fallback_duration
            logger.warning(
                "[Agent] 调用频繁 (%d/%ds)，降级到 %s (持续 %ds)",
                len(self.model_calls), self.rate_window,
                self.fallback_model, self.fallback_duration,
            )
            return self.fallback_model

        return self.model

    # -------- 图片 OCR --------
    # 表情包-aware prompt：把 vision 从「描述像素」改成「读懂含义」。
    # QQ 群里 80% 的图都是表情包（情绪符号），vision 直接描述会变成「一只柴犬坐桌前」
    # 这种没用的话。这个 prompt 强制模型给情绪/梗名，对真实照片也还能工作。
    VISION_PROMPT = (
        "这张图大概率是 QQ 群里的**表情包**（约定俗成的情绪符号，不是照片）。\n"
        "**任务：说出它表达的情绪/梗，最多 20 字。**\n"
        "\n"
        "硬规则：\n"
        "1. 看不清/打不开/全黑 → 回『看不到』，绝不瞎编\n"
        "2. **报含义不报像素**——错『一只柴犬坐桌前』 对『doge 笑/嘲讽』；错『一只熊猫』 对『无语熊猫/没语了』\n"
        "3. 图上**有文字必读出来 + 情绪**——例『字面「你说得对」，敷衍同意』『字面「我要骂人了」，假装生气』\n"
        "4. 著名表情包直接报名字：doge / 无语熊猫 / 摸鱼大鱼 / 流泪猫猫头 / 委屈鼠 / 旺仔牛奶 / 思考人生 等\n"
        "5. 真实照片（不是表情包）→ 简短主体描述也行，例『一只真猫蜷在沙发上』\n"
        "6. 不要『这张图/图中/图片显示』前缀，直接说"
    )

    _VISION_REJECT_TOKENS = (
        "不清楚", "不确定", "看不到", "看不了", "看不清", "打不开",
        "无法", "不存在", "无内容", "黑屏", "空白", "没看到",
        "图片为空", "加载失败", "无法访问", "无法识别",
    )

    def _accept_vision_caption(self, url: str, text: str, provider: str) -> str:
        text = (text or "").strip()[:150]
        hit = next((t for t in self._VISION_REJECT_TOKENS if t in text), "")
        too_long = len(text) > 80
        if text and len(text) >= 4 and not hit and not too_long:
            self.image_caption_cache[url] = text
            self._gc_image_cache()
            logger.info("[Agent] vision/%s (%s): %s", provider, url[:60], text[:60])
            return text
        logger.info(
            "[Agent] vision/%s rejected (%s, hit=%r, len=%d): %s",
            provider, url[:60], hit, len(text), text[:80],
        )
        return ""

    async def _describe_image_glm(self, url: str) -> str:
        """智谱 GLM-4V — fetch image, send as base64 data URL.
        Raw URLs trigger GLM error 1210 (图片输入格式/解析错误); base64 mandatory."""
        try:
            img_bytes = await self._fetch_image_bytes(url)
            if not img_bytes:
                return ""
            if len(img_bytes) < 200:
                logger.debug("[Agent] GLM image too small (%d bytes), skipping", len(img_bytes))
                return ""
            if len(img_bytes) > 5_000_000:
                logger.warning("[Agent] GLM image too large (%d bytes), skipping", len(img_bytes))
                return ""
            # MIME by magic bytes (no http response headers now that _fetch_image_bytes
            # handles file:// too)
            if img_bytes[:8] == b"\x89PNG\r\n\x1a\n":
                mime = "image/png"
            elif img_bytes[:3] == b"\xff\xd8\xff":
                mime = "image/jpeg"
            elif img_bytes[:4] == b"GIF8":
                mime = "image/gif"
            elif img_bytes[:4] == b"RIFF" and img_bytes[8:12] == b"WEBP":
                mime = "image/webp"
            else:
                mime = "image/jpeg"
            data_url = f"data:{mime};base64,{base64.b64encode(img_bytes).decode()}"

            async with httpx.AsyncClient(timeout=30) as c:
                r = await c.post(
                    f"{self.glm_base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self.glm_api_key}"},
                    json={
                        "model": self.vision_model,
                        "messages": [{
                            "role": "user",
                            "content": [
                                {"type": "text", "text": self.VISION_PROMPT},
                                {"type": "image_url", "image_url": {"url": data_url}},
                            ],
                        }],
                        "max_tokens": 120,
                        "temperature": 0.3,
                    },
                )
                if r.status_code != 200:
                    logger.warning("[Agent] GLM vision HTTP %d: %s",
                                   r.status_code, r.text[:200])
                    return ""
                data = r.json()
                text = (data.get("choices", [{}])[0]
                            .get("message", {})
                            .get("content", "") or "")
                return self._accept_vision_caption(url, text, "glm")
        except Exception as e:
            logger.debug("[Agent] GLM vision failed: %s: %s",
                         type(e).__name__, e)
            return ""

    async def _describe_image_anthropic(self, url: str) -> str:
        """Anthropic SDK vision call (claude-haiku / claude-sonnet / etc.)."""
        try:
            client = self._get_anthropic_client()
            response = await asyncio.wait_for(
                client.messages.create(
                    model=self.vision_model,
                    max_tokens=120,
                    messages=[{
                        "role": "user",
                        "content": [
                            {"type": "image", "source": {"type": "url", "url": url}},
                            {"type": "text", "text": self.VISION_PROMPT},
                        ],
                    }],
                ),
                timeout=20.0,
            )
            text = "".join(
                getattr(b, "text", "") for b in response.content if getattr(b, "text", "")
            )
            return self._accept_vision_caption(url, text, "anthropic")
        except Exception as e:
            logger.debug("[Agent] Anthropic vision failed: %s: %s",
                         type(e).__name__, e)
            return ""

    async def _describe_image(self, url: str) -> str:
        """Route to GLM or Anthropic by vision_model prefix; OCR fallback on miss.
        Filters garbage OCR (too short / single-char fragments)."""
        if not url:
            return ""
        if url in self.image_caption_cache:
            return self.image_caption_cache[url]

        caption = ""
        if self.vision_model.startswith("glm") and self.glm_api_key and self.glm_base_url:
            caption = await self._describe_image_glm(url)
        elif self.vision_model:
            caption = await self._describe_image_anthropic(url)
        if caption:
            return caption

        # Fallback: NapCat OCR
        ocr_text = await self._ocr_image(url)
        # Filter garbage: too short or fragmented single chars/symbols
        if ocr_text and len(ocr_text) >= 4:
            tokens = ocr_text.split()
            avg_token_len = sum(len(t) for t in tokens) / max(len(tokens), 1)
            if avg_token_len >= 2:
                return ocr_text
        return ""

    def _gc_image_cache(self) -> None:
        if len(self.image_caption_cache) > 200:
            for k in list(self.image_caption_cache.keys())[:50]:
                self.image_caption_cache.pop(k, None)

    async def _ocr_image(self, url: str) -> str:
        """调用 NapCat /ocr_image 提取图片文字；失败或无文字返回空串。"""
        if not url:
            return ""
        if url in self.image_caption_cache:
            return self.image_caption_cache[url]
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                r = await client.post(
                    f"{self.napcat_api}/ocr_image",
                    json={"image": url},
                )
                r.raise_for_status()
                data = r.json()
                items = data.get("data") or []
                text = " ".join(
                    it.get("text", "") for it in items if it.get("text")
                ).strip()[:120]
        except Exception as e:
            logger.warning("[Agent] NapCat OCR failed (%s): %s: %s",
                           url[:80], type(e).__name__, str(e) or "(no message)")
            return ""
        self.image_caption_cache[url] = text
        if len(self.image_caption_cache) > 200:
            for k in list(self.image_caption_cache.keys())[:50]:
                self.image_caption_cache.pop(k, None)
        logger.info("[Agent] OCR (%s): %s", url[:60], text[:60] or "(无文字)")
        return text

    # -------- 记忆 --------
    def _load_memories(self) -> dict:
        if not self.memory_file.exists():
            return {}
        try:
            return json.loads(self.memory_file.read_text(encoding="utf-8"))
        except Exception as e:
            logger.warning("[Agent] 记忆加载失败: %s", e)
            return {}

    def _save_memories(self) -> None:
        try:
            self.memory_file.write_text(
                json.dumps(self.memories, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as e:
            logger.warning("[Agent] 记忆保存失败: %s", e)

    def _reload_examples_if_stale(self) -> None:
        try:
            mtime = self.examples_file.stat().st_mtime
        except FileNotFoundError:
            self._examples_cache = []
            self._examples_mtime = 0.0
            return
        if mtime <= self._examples_mtime:
            return
        try:
            lines = self.examples_file.read_text(encoding="utf-8").splitlines()
            self._examples_cache = [json.loads(l) for l in lines if l.strip()]
            self._examples_mtime = mtime
        except Exception as e:
            logger.warning("[Agent] examples.jsonl reload failed: %s", e)

    def _reload_pairs_if_stale(self) -> None:
        """Load preference pairs from feedback.jsonl (rating=better only)."""
        try:
            mtime = self.feedback_file.stat().st_mtime
        except FileNotFoundError:
            self._pairs_cache = []
            self._pairs_mtime = 0.0
            return
        if mtime <= self._pairs_mtime:
            return
        try:
            lines = self.feedback_file.read_text(encoding="utf-8").splitlines()
            records = []
            for ln in lines:
                ln = ln.strip()
                if not ln:
                    continue
                try:
                    records.append(json.loads(ln))
                except json.JSONDecodeError:
                    pass
            # Only keep "better" rows where user provided a chosen alternative
            self._pairs_cache = [
                r for r in records
                if r.get("rating") == "better" and r.get("better") and r.get("reply")
            ]
            self._pairs_mtime = mtime
        except Exception as e:
            logger.warning("[Agent] feedback.jsonl reload failed: %s", e)

    def _examples_for_prompt(
        self,
        focus_text: str = "",
        mode: str = "",
        limit_pairs: int = 6,
        limit_good: int = 4,
    ) -> str:
        """Hermes-style: contrastive pairs first (stronger signal), then chosen-only goods.
        Dynamic retrieval: rank by relevance (scenario + context ngram overlap with
        focus_text, mode match) and fall back to recency. Pairs are auto-mined from
        feedback.jsonl entries the user rated 'better'."""
        self._reload_examples_if_stale()
        self._reload_pairs_if_stale()

        if not self._examples_cache and not self._pairs_cache:
            return ""

        # Same ngram tokenization as _memories_for_prompt — consistent matching
        focus_lc = focus_text.lower()
        chinese_chars = re.findall(r"[一-鿿]", focus_lc)
        chinese_ngrams = {
            "".join(chinese_chars[i:i+2])
            for i in range(max(0, len(chinese_chars) - 1))
        }
        ascii_tokens = set(re.findall(r"[a-z0-9]{3,}", focus_lc))
        focus_tokens = chinese_ngrams | ascii_tokens

        def _score(ex: dict) -> float:
            s = 0.0
            scenario_lc = ex.get("scenario", "").lower()
            ctx_lc = " ".join(ex.get("context", [])).lower()
            # Scenario hit is high signal (curated tag)
            for tok in focus_tokens:
                if tok in scenario_lc:
                    s += 1.0
                if tok in ctx_lc:
                    s += 0.3
            # Same-mode bonus (called/owner/followup/judge)
            if mode and ex.get("mode") == mode:
                s += 0.5
            # Mild recency tiebreaker: parse ts if present
            ts = ex.get("ts", "")
            if ts:
                # newer entries get a small bump; use last 6 chars as quick proxy
                s += len(ts) * 0.001  # all entries get ~0.02, breaks ties stably
            return s

        # Rank pairs (contrastive, stronger signal first). With no signal at
        # all (judge mode, no focus), fall back to last-N rather than letting
        # stable sort pick the *oldest* entries.
        have_signal = bool(focus_tokens or mode)
        if have_signal:
            pairs = sorted(self._pairs_cache, key=_score, reverse=True)[:limit_pairs]
        else:
            pairs = self._pairs_cache[-limit_pairs:]

        parts = ["\n\n<examples>"]

        if pairs:
            parts.append(
                "【对比学习】下面是同一情境的「错误回复 [BAD]」vs「正确回复 [OK]」对照——"
                "重点学 [OK] 那种说话风格，避免 [BAD] 那种 AI 味。"
            )
            for p in pairs:
                ctx = "\n".join(p.get("context", []))
                parts.append(
                    f"\n场景: {p.get('scenario','?')}\n"
                    f"群里:\n{ctx}\n"
                    f"[BAD] {p.get('reply','')}\n"
                    f"[OK]  {p.get('better','')}"
                )

        # Dedupe + rank goods (same fallback rule)
        pair_chosen_set = {p.get("better", "") for p in pairs}
        candidates = [e for e in self._examples_cache if e.get("reply", "") not in pair_chosen_set]
        if have_signal:
            goods = sorted(candidates, key=_score, reverse=True)[:limit_good]
        else:
            goods = candidates[-limit_good:]
        if goods:
            parts.append("\n【正面示范】这些回复都贴你的风格，学这种感觉：")
            for e in goods:
                ctx = "\n".join(e.get("context", []))
                parts.append(
                    f"\n场景: {e.get('scenario','?')}\n"
                    f"群里:\n{ctx}\n"
                    f"你的回复: {e.get('reply','')}"
                )

        parts.append("\n</examples>")
        return "\n".join(parts)

    def _sticker_guide_for_prompt(self) -> str:
        """Sticker guide. ALWAYS returns content — when library is empty, gives
        anti-confab rules (don't fabricate stickers you don't have); when populated,
        encourages frequent trailing stickers (default: every message + one)."""
        stats = self.stickers.stats()
        tags_summary = self.stickers.available_tags_summary(limit=20)
        if not tags_summary:
            return (
                "\n\n<sticker_guide>\n"
                "**你目前还没攒到任何表情包**——你刚加群，库里是空的。\n"
                f"（已观察到 {stats['total']} 张，但都还没攒够上下文理解含义，所以发不出去。）\n"
                "\n"
                "**被问『有什么表情包』『发个表情包』『让我看看你收藏的』时：**\n"
                "- **坦白没攒着**，禁止瞎编不存在的表情包名字（比如『猫猫无语脸』『熊猫摊手』之类的，你**根本没有**就别说有）\n"
                "- 自然回应：『刚来还没攒呢』『还没收藏多少』『让我先看你们都发啥再说』『我先观察一阵子』\n"
                "- 反向调侃也行：『你倒挺会蹭，自己先发几个让我学学』『想抄我作业是吧』\n"
                "\n"
                "**绝对不要使用 `[STICKER:xxx]` 标记**——库里没货发不出，会显得很傻\n"
                "（等库里攒够了你就会爱上每条消息后面跟一张——但现在不行）\n"
                "</sticker_guide>"
            )
        # If we have an analyzed owner profile, embed it as the frequency target
        owner_pattern = self._owner_sticker_pattern_block()
        return (
            "\n\n<sticker_guide>\n"
            f"**你也用表情包**——库里有 {stats['tagged']} 张 tagged。\n"
            "在 reply 里写 `[STICKER:<tag>]`，agent 自动从库里挑张匹配的发出去。\n"
            "\n"
            f"{owner_pattern}"
            "**何时发**（按 intent 自然就好，**别每条都带**）：\n"
            "- 表态/共情/玩梗/吐槽/敷衍承认 → 容易匹配到合适 sticker 就跟一张\n"
            "- 被 @ 没啥可说 / 接梗到位 / 笑场 → 单独发 sticker 也可以\n"
            "- 例：『确实牛』+ `[STICKER:嘲讽]` ；『心疼一下』+ `[STICKER:抱抱]`\n"
            "\n"
            "**不该带的场合**：\n"
            "- 答正经问题/给具体信息 → 不跟，正经回答带 sticker 显轻浮\n"
            "- 长解释超 50 字 → 不跟，冗余\n"
            "- 上一条刚发过 sticker → 这条歇一下\n"
            "- 找不到合适的 tag → **别硬凑**，正常打字就行\n"
            "\n"
            "**tag 怎么选**：\n"
            "- 按 intent 偏好：joke→[嘲讽/笑/玩梗]、vent→[无奈/共鸣/抱抱]、troll→[doge/翻白眼]、share→[绝/牛/震惊]\n"
            "- 只用下面列出的 tag——其它写了 agent 找不到\n"
            "\n"
            "当前库里可用 tag（按热度）：\n"
            f"{tags_summary}\n"
            "</sticker_guide>"
        )

    def _owner_sticker_pattern_block(self) -> str:
        """If owner_profile.json exists, embed measured frequency as the target.
        Otherwise return a placeholder telling model to use moderate frequency."""
        profile_file = Path(__file__).parent / "owner_profile.json"
        if not profile_file.exists():
            return (
                "**频率参考**：还没分析过 " + self.owner_name + " 的聊天风格，先按**中等频率**来——"
                "大约每 3-5 条文字消息穿插 1 张表情包，不强求。\n\n"
            )
        try:
            profile = json.loads(profile_file.read_text(encoding="utf-8"))
        except Exception:
            return ""
        total = profile.get("total_msgs", 0)
        with_sticker = profile.get("msgs_with_image", 0)
        sticker_only = profile.get("sticker_only_msgs", 0)
        if total < 20:
            return ""
        ratio = with_sticker / total
        every_n = max(2, round(total / max(with_sticker, 1)))
        return (
            f"**频率参考（按 {self.owner_name} 实际风格学的）**：\n"
            f"- 平均每 {every_n} 条消息发 1 张表情包（{int(ratio*100)}%）\n"
            f"- 其中 {int(sticker_only/max(with_sticker,1)*100)}% 是单发表情包不打字\n"
            f"- 你按这个节奏来，别比这频繁，也别完全不发\n"
            f"\n"
        )

    def _memories_for_prompt(self, group_id: str, focus_text: str = "") -> str:
        items = self.memories.get(group_id, [])
        if not items:
            return ""

        # 出场人物的 user_id 集合（只塞他们的私人记忆，省 token）
        present_uids = {
            m.get("user_id")
            for m in self.buffers.get(group_id, [])
            if m.get("user_id")
        }
        # owner 的记忆永远视为在场
        if self.owner_qq:
            present_uids.add(self.owner_qq)

        # Relevance scoring: 14-day linear recency decay + keyword overlap bonus.
        # Tokenize Chinese via 2-char sliding ngrams (greedy match grabs whole runs
        # which then fail substring lookup); ASCII via 3+ char words.
        # No embeddings — keeps cold-path zero-dependency; good enough at this scale.
        now = time.time()
        focus_lc = focus_text.lower()
        chinese_chars = re.findall(r"[一-鿿]", focus_lc)
        chinese_ngrams = {
            "".join(chinese_chars[i:i+2])
            for i in range(max(0, len(chinese_chars) - 1))
        }
        ascii_tokens = set(re.findall(r"[a-z0-9]{3,}", focus_lc))
        focus_tokens = chinese_ngrams | ascii_tokens

        def _score(it: dict) -> float:
            text_lc = it.get("text", "").lower()
            age_days = max(0.0, (now - it.get("time", now)) / 86400.0)
            s = max(0.0, 1.0 - age_days / 14.0)
            for tok in focus_tokens:
                if tok in text_lc:
                    s += 0.5
            return s

        group_level: list[dict] = []
        per_user: dict[str, list[dict]] = defaultdict(list)
        for it in items:
            uid = it.get("user_id")
            if not uid:
                group_level.append(it)
            elif uid in present_uids:
                name = it.get("user_name") or uid
                per_user[name].append(it)

        # Top-K per bucket to bound token cost. Group-level wider since they
        # apply to anyone; per-user narrower since each user may have many.
        group_level.sort(key=_score, reverse=True)
        group_level = group_level[:8]
        for name in list(per_user.keys()):
            per_user[name].sort(key=_score, reverse=True)
            per_user[name] = per_user[name][:5]

        parts: list[str] = []
        if group_level:
            parts.append("群里记下的事：\n" + "\n".join(f"- {it['text']}" for it in group_level))
        for name, lst in per_user.items():
            # 把存储里的 "我" 替换成名字，让 LLM 读起来不歧义
            texts = [re.sub(r"\b我\b", name, it["text"]) for it in lst]
            parts.append(f"关于 {name}：\n" + "\n".join(f"- {t}" for t in texts))
        if not parts:
            return ""
        return (
            "\n\n<memories>\n"
            "下面是之前记下的一些背景事实（已按相关性+新鲜度排序，只列 top）。"
            "**仅供参考——只在跟当前话题真的相关时才用**。\n"
            "不要硬塞记忆、不要为了用而用；跟当前对话无关就当不知道。\n"
            "记忆不等于当前正在发生的事，别把过去的事说成现在的。\n\n"
            + "\n\n".join(parts) +
            "\n</memories>\n"
        )

    def _active_users_for_prompt(self, group_id: str) -> str:
        """返回最近活跃的群友列表，用于 judge 模式 prompt。"""
        users = list(self.active_users.get(group_id, []))
        if not users:
            return ""
        seen = set()
        unique = []
        for uid, nick in reversed(users):
            if uid != self.bot_qq and uid not in seen:
                seen.add(uid)
                unique.append((uid, nick))
        if not unique:
            return ""
        return "、".join([f"{nick}({uid})" for uid, nick in unique[:5]])

    def _compute_chat_signals(self, group_id: str, history: list) -> dict:
        """Compute chat signals for prompt: topic heat / active count / time since bot spoke / topic type."""
        # Active distinct users in recent window (excluding bot)
        active_count = len({
            m.get("user_id") for m in history
            if m.get("user_id") and m.get("user_id") != self.bot_qq
        })

        # Topic heat: messages in last 30 entries treated as window
        heat = "热" if len(history) >= 15 else ("一般" if len(history) >= 5 else "冷清")

        # Time since bot last spoke
        last = self.last_reply_at.get(group_id, 0.0)
        if last == 0:
            since = "很久没说话"
        else:
            delta = time.time() - last
            if delta < 60:
                since = f"{int(delta)}秒前"
            elif delta < 600:
                since = f"{int(delta // 60)}分钟前"
            else:
                since = "10+ 分钟前"

        # Topic type: heuristic on recent messages
        recent_text = " ".join(m.get("text", "") for m in history[-8:])
        if any(k in recent_text for k in ["bug", "代码", "报错", "需求", "deadline", "项目", "工作"]):
            ttype = "工作/技术"
        elif any(k in recent_text for k in ["哈哈", "草", "笑死", "梗", "绷", "乐"]):
            ttype = "玩梗/吐槽"
        elif any(k in recent_text for k in ["？", "?"]):
            ttype = "提问/讨论"
        else:
            ttype = "闲聊"

        return {
            "热度": heat,
            "活跃人数": active_count,
            "上次发言": since,
            "类型": ttype,
        }

    def _handle_memory_command(
        self,
        group_id: str,
        text: str,
        user_id: str = "",
        user_name: str = "",
    ) -> Optional[str]:
        # 保存：「<bot>记住XX」「<bot>记一下XX」「<bot>记下XX」
        m = re.search(rf"{self.bot_name}\s*[，,]?\s*记(?:住|一下|下)\s*[：:，,]?\s*(.+)", text)
        if m:
            content = m.group(1).strip()
            if not content:
                return random.choice(["啊？记啥", "你说啊", "记啥呀，说嘛"])
            # 检测「我XX」「自己XX」→ 绑定到发言人
            bind_self = bool(re.match(r"^(?:我|自己)", content))
            item: dict = {"text": content[:200], "time": time.time()}
            if bind_self and user_id:
                item["user_id"] = user_id
                if user_name:
                    item["user_name"] = user_name
            items = self.memories.setdefault(group_id, [])
            items.append(item)
            if len(items) > self.memory_max:
                items.pop(0)
            self._save_memories()
            return random.choice(["嗯，记下了", "好的，记到小本本上了", "记住啦", "嗯嗯", "ok"])

        # 删除：「<bot>忘了XX」「<bot>忘记XX」「<bot>忘掉XX」
        m = re.search(rf"{self.bot_name}\s*[，,]?\s*忘(?:了|记|掉)\s*[：:，,]?\s*(.+)", text)
        if m:
            query = m.group(1).strip()
            items = self.memories.get(group_id, [])
            before = len(items)
            kept = [it for it in items if query not in it["text"] and it["text"] not in query]
            if len(kept) == before:
                return random.choice(["啊？没记过这个", "啥？我没印象", "什么呀，没记呢"])
            self.memories[group_id] = kept
            self._save_memories()
            return random.choice(["忘了", "好的，删了", "嗯，扔掉了", "拜拜"])

        # 列出：「<bot>记得什么」「<bot>记忆」「<bot>记得啥」「<bot>都记住了啥」
        if re.search(
            rf"{self.bot_name}\s*[，,]?\s*(?:都\s*)?(?:记得(?:什么|啥)|记忆|有什么记忆|脑子里有啥)",
            text,
        ):
            items = self.memories.get(group_id, [])
            if not items:
                return random.choice(["脑子里空空的", "啥都没记呢", "一片空白"])
            lines: list[str] = []
            for it in items:
                tag = f"[关于{it.get('user_name')}] " if it.get("user_name") else ""
                lines.append(f"· {tag}{it['text']}")
            return "我记得这些：\n" + "\n".join(lines)

        return None

    @staticmethod
    def _parse_hermes_output(raw: str) -> tuple[str, str, str]:
        """Parse Hermes-style structured output:
        <reasoning>...</reasoning> <intent>tag</intent> <reply>...</reply>

        Returns (reply_text, reasoning_text, intent). intent is "" when tag is
        missing/malformed. MEM lines after </reply> are appended to reply so
        downstream _split_reply_and_mem still works.
        """
        if not raw:
            return "", "", ""

        reasoning_m = re.search(r'<reasoning>(.*?)</reasoning>', raw, re.DOTALL | re.IGNORECASE)
        reasoning = reasoning_m.group(1).strip() if reasoning_m else ""

        intent_m = re.search(r'<intent>\s*([a-zA-Z_]+)\s*</intent>', raw, re.IGNORECASE)
        intent = intent_m.group(1).lower() if intent_m else ""

        reply_m = re.search(r'<reply>(.*?)</reply>', raw, re.DOTALL | re.IGNORECASE)
        if reply_m:
            reply_inner = reply_m.group(1).strip()
            tail = raw[reply_m.end():].strip()
            if tail:
                reply_inner = f"{reply_inner}\n{tail}" if reply_inner else tail
            return reply_inner, reasoning, intent

        # <reply> open tag without close — take everything after </reasoning> (or <intent>)
        anchor_end = max(
            reasoning_m.end() if reasoning_m else -1,
            intent_m.end() if intent_m else -1,
        )
        if anchor_end > 0:
            after = raw[anchor_end:].strip()
            after = re.sub(r'^\s*<\s*reply\s*>\s*', '', after, flags=re.IGNORECASE)
            after = re.sub(r'\s*<\s*/\s*reply\s*>\s*$', '', after, flags=re.IGNORECASE)
            return after, reasoning, intent

        # No protocol followed at all — treat the whole thing as reply (back-compat).
        return raw.strip(), "", intent

    def _split_reply_and_mem(self, raw: str) -> tuple[str, Optional[str]]:
        """从 LLM 输出里抽出 MEM 行；其余作为 reply。"""
        if not raw:
            return "", None
        # 匹配独占一行的 MEM:... 或 MEM：...
        mem_match = re.search(r"(?:^|\n)\s*MEM\s*[:：]\s*(.+?)\s*$", raw, re.DOTALL)
        if not mem_match:
            return raw.strip(), None
        mem = mem_match.group(1).strip()
        reply = raw[: mem_match.start()].strip()
        # 防止 LLM 复读 prompt 里的占位例子
        if mem.lower() in {"无", "none", "n/a", ""}:
            mem = ""
        return reply, mem or None

    def _save_auto_memory(self, group_id: str, text: str) -> None:
        text = text.strip()[:200]
        if not text:
            return
        items = self.memories.setdefault(group_id, [])
        # 简单去重：内容已存在就跳过
        if any(it["text"] == text for it in items):
            return
        item: dict = {"text": text, "time": time.time(), "auto": True}
        # Auto-tag subject by scanning text for known speaker names — lets
        # per-user retrieval find this entry when subject speaks again.
        name_to_uid: dict[str, str] = {}
        for m in self.buffers.get(group_id, []):
            nm = m.get("name", "")
            uid = m.get("user_id", "")
            if nm and len(nm) >= 2 and uid:
                name_to_uid.setdefault(nm, uid)
        if self.owner_qq and self.owner_name and len(self.owner_name) >= 2:
            name_to_uid.setdefault(self.owner_name, self.owner_qq)
        for nm, uid in name_to_uid.items():
            if nm in text:
                item["user_id"] = uid
                item["user_name"] = nm
                break
        items.append(item)
        if len(items) > self.memory_max:
            items.pop(0)
        self._save_memories()
        subj = f" (about={item.get('user_name','?')})" if "user_id" in item else ""
        logger.info("[Agent] 自动记忆 (group=%s)%s: %s", group_id, subj, text[:60])
