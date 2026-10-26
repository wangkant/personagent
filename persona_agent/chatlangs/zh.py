"""Simplified Chinese."""
from . import Spec
from .en import FIRST_PERSON

SPEC = Spec(
    code="zh",
    remember=r"(?:帮我|幫我)?记(?:住|一下|下来|下)",
    forget=r"忘(?:了|记|掉)",
    not_a_delete=(r"(?![\s，,]*(?:它|这个|那个|這個|那個)?(?:吧|啦|算了)[\s!！。.~～]*$)"
                  r"(?!說|讲|講|说|帶|带|拿|告訴|告诉|問|问|買|买|關|关|鎖|锁|交|寫|写)"),
    # Recall must be the whole message: "小夏 记忆力真好" is a compliment.
    recall=r"(?:你\s*)?(?:都\s*)?(?:记得(?:什么|啥)|记忆|有什么记忆|脑子里有啥)",
    learned=r"(?:你)?(?:学到|学会|学了)(?:了)?(?:什么|啥)",
    # Chinese drops the question mark: "记住了吗", "记下来没", "忘记我说的话了吗".
    question_end=r"(?:[?？]|吗|么|呢|没有?)[\s?？!！。.~～]*$",
    # Judged on a forget only: "忘了带伞怎么办" asks, it does not delete.
    asking=r"怎么|怎样|咋|为什么|为啥|什么|啥|哪|多少|是不是|有没有|能不能",
    # A particle or aspect marker where the note should start: "记住了，...".
    note_lead=r"^(?:了|啊|呀|哦|喔|嘛|啦|哈|吧|呗)+(?=[\s，,。:：!！~～]|$)[\s，,。:：!！~～]*",
    recall_tail=r"呢|呀|啊|吗|嘛",
    deictic=frozenset({"这个", "那个", "这", "那", "这事", "那事", "这件事", "那件事",
                       "這個", "那個", "這", "這件事", "剛才那個", "剛剛那個",
                       "这条", "那条", "它", "刚才那个", "刚才的", "刚才说的"}),
    everything=frozenset({"全部", "所有", "一切", "全部的", "所有的", "所有事",
                          "全部记忆", "所有记忆"}),
    first_person=FIRST_PERSON,
    replies={
        "remember_what": ("记什么？你啥也没说", "说呀，记啥", "要我记啥"),
        "not_instructions": ("我只记事实，不记指令",),
        "noted": ("记下了", "好，记住了", "嗯，记着呢", "收到"),
        "forget_what": ("忘掉什么？说具体点", "哪条？再说清楚点"),
        "nothing_to_forget": ("呃，没记过这个", "没这印象啊", "没有对得上的可以忘"),
        "forgotten": ("忘掉了", "删了", "没了"),
        "empty": ("脑子里空空的", "啥也没记", "一片空白"),
        "recall_head": ("我记得这些：",),
        "about": ("关于{name}：",),
        "from": ("来自{name}：",),
    },
    failure_excuses=("等我一下，网有点卡",
                     "信号不太好，稍等",
                     "卡住了，等会儿再聊"),
    learned_text={
        "head": ("记忆 {memories} 条，学到 {examples} 条回复和 {fixes} 组纠正，"
                 "{voice} 条等第二个人佐证，{admin} 条等管理员处理"),
        "score": "，最近自评 {score}/5",
        "pair": "原来：{was}，改成：{better}",
        "someone_else": "另一个聊天里有人",
        "someone": "有人",
        "retry": "{who} 接受了重答",
        "self_review": "自我复盘",
        "self_eval": "自评满分",
        "corrected": "{who} 纠正了",
        "missed": "{who} 说没答对",
        "liked": "{who} 觉得好",
        "by_admin": "管理员通过",
        "passed": "{events} 条证据其中 {strong} 条强，通过",
        "why": "原因：{steps}",
        "sep": "，",
    },
)
