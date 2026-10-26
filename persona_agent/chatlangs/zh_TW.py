"""Traditional Chinese (Taiwan)."""
from . import Spec
from .en import FIRST_PERSON

SPEC = Spec(
    code="zh-TW",
    remember=r"(?:幫我|帮我)?記(?:住|一下|下來|下)",
    # 忘了 and 忘掉 are also Simplified: both specs read them and detection
    # picks, so what keeps a forget conversation below covers both scripts.
    forget=r"忘(?:了|記|掉)",
    # "忘了吧", "忘了它啦": never mind, not a delete.
    not_a_delete=(r"(?![\s，,]*(?:它|這個|那個|这个|那个)?(?:吧|啦|算了)[\s!！。.~～]*$)"
                  r"(?!說|讲|講|说|帶|带|拿|告訴|告诉|問|问|買|买|關|关|鎖|锁|交|寫|写)"),
    # Recall must be the whole message: "小夏 記憶力真好" is a compliment.
    recall=(r"(?:你\s*)?(?:都\s*)?(?:還\s*)?(?:記得(?:什麼|啥|哪些)|記了(?:什麼|啥|哪些)"
            r"|記憶|有什麼記憶|腦袋裡有什麼)"),
    learned=r"(?:你)?(?:學到|學會|學了)(?:了)?(?:什麼|啥|哪些)",
    # The question mark is often dropped: "記住了嗎", "記下來沒", "忘記了呢".
    question_end=r"(?:[?？]|嗎|麼|呢|沒有?)[\s?？!！。.~～]*$",
    # Judged on a forget only: "忘了帶傘怎麼辦" asks, it does not delete.
    asking=(r"怎麼|怎樣|為什麼|為啥|幹嘛|什麼|啥|哪|多少|是不是|有沒有|能不能|可不可以"
            r"|怎么|怎样|为什么|为啥|干嘛|什么|有没有"),
    # A particle where the note should start ("記住喔，..."), or "一件事：".
    note_lead=(r"^(?:(?:了|啊|呀|喔|哦|嘛|啦|哈|吧|唷|齁)+(?=[\s，,。:：!！~～]|$)"
               r"|(?:一件事|這件事)(?=[\s，,:：]))[\s，,。:：!！~～]*"),
    query_lead=r"^(?:關於|有關)\s*",
    recall_tail=r"呢|呀|啊|嗎|嘛|咧",
    deictic=frozenset({"這個", "那個", "這", "那", "這件事", "那件事", "這條", "那條",
                       "它", "剛剛那個", "剛才那個", "剛剛的", "剛剛說的", "剛才說的",
                       "这个", "那个", "这", "这件事", "那件事", "这条", "那条",
                       "刚才那个", "刚才的", "刚才说的"}),
    everything=frozenset({"全部", "所有", "一切", "全部的", "所有的", "所有事",
                          "全部記憶", "所有記憶", "全部记忆", "所有记忆"}),
    # en's 我 excludes 们 only; here 我們 is not the saver either.
    first_person=FIRST_PERSON.replace("我(?!们)", "我(?![們们])"),
    replies={
        "remember_what": ("記什麼？你什麼都沒說", "說啊，要記啥", "要我記什麼"),
        "not_instructions": ("我只記事實，不記指令",),
        "noted": ("記下來了", "好，記住了", "嗯，記著呢", "收到"),
        "forget_what": ("忘掉什麼？講清楚一點", "哪一條？再說清楚點"),
        "nothing_to_forget": ("呃，沒記過這個", "沒什麼印象耶", "沒有對得上的可以忘"),
        "forgotten": ("忘掉了", "刪掉了", "沒了"),
        "empty": ("腦袋空空的", "什麼都沒記", "一片空白"),
        "recall_head": ("我記得這些：",),
        "about": ("關於{name}：",),
        "from": ("來自{name}：",),
    },
    failure_excuses=("等我一下，網路有點卡",
                     "訊號不太好，稍等",
                     "卡住了，等等再聊"),
    learned_text={
        "head": ("記憶 {memories} 條，學到 {examples} 條回覆和 {fixes} 組糾正，"
                 "{voice} 條等第二個人佐證，{admin} 條等管理員處理"),
        "score": "，最近自評 {score}/5",
        "pair": "原本：{was}，改成：{better}",
        "someone_else": "另一個聊天裡有人",
        "someone": "有人",
        "retry": "{who} 接受了重答",
        "self_review": "自我檢討",
        "self_eval": "自評滿分",
        "corrected": "{who} 糾正了",
        "missed": "{who} 說沒答對",
        "liked": "{who} 覺得不錯",
        "by_admin": "管理員通過",
        "passed": "{events} 條證據其中 {strong} 條強，通過",
        "why": "原因：{steps}",
        "sep": "，",
    },
)
