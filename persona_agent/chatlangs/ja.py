"""Japanese."""
from . import Spec

# Softening endings after a command verb: "覚えといてね", "メモしてください".
_SOFT = r"(?:ね|よ|な|ください|くれ|ちょうだい|ほしい|欲しい)*"
# Punctuation that may sit between parts of a command.
_PUNCT = r"[\s、,，:：。!！~～]"

SPEC = Spec(
    code="ja",
    vocative=r"さん|ちゃん|くん",
    # Keyword first: "覚えて：...", "メモして、...". The lookaheads keep the
    # verb from stopping short, so "覚えてる" and "覚えておいてくれる" are not
    # read as "覚えて" plus a note; a bare "メモ" needs a colon or comma.
    remember=(r"覚えて(?:おいて|て)?(?![るいたなおとま])|覚えといて|覚えとけ"
              r"|メモ(?:しておいて|しといて|っといて|して)(?![るいたおと])"
              r"|メモ(?=\s*[：:、,，])|記憶して(?:おいて)?(?![るいたおま])"),
    # Asking it to remember ("覚えてくれる？", "覚えてもらえる") is not the order.
    not_a_note=r"(?!\s*(?:くれ(?:る|ない|た|ます)|もらえ|られ))",
    # Verb last: "...って覚えといて", "...をメモしてね". The quotative or object
    # particle is not part of the note.
    remember_last=(r"[、,，]?\s*(?:ということ|ってこと|って|(?<!こ)と)?(?:を)?\s*"
                   r"(?:覚えて(?:おいて|て)?|覚えといて|覚えとけ"
                   r"|メモ(?:しておいて|しといて|っといて|して)|記憶して(?:おいて)?)"
                   + _SOFT),
    forget=r"忘れて(?:おいて)?(?![るいたなおとま])|忘れといて|忘れろ|忘れとけ",
    # "忘れて", "忘れてね", "忘れていいよ": never mind, with nothing to drop.
    not_a_delete=rf"(?!{_PUNCT}*{_SOFT}{_PUNCT}*$)",
    forget_last=(r"(?:(?:の)?(?:メモ|記憶)(?:から|を)?\s*(?:消して|削除して)"
                 r"|(?:のこと|について|って|は|を)?\s*"
                 r"(?:忘れて(?:おいて)?|忘れといて|忘れろ|忘れとけ))" + _SOFT),
    # Japanese drops the question mark: "覚えてるかな", "何だっけ". Not "とか".
    question_end=r"(?:[?？]|(?<!と)か|かな|かね|かい|っけ)[\s?？!！。.~～]*$",
    asking=r"どう|なんで|なぜ|何|なに|どこ|いつ|誰|だれ|どれ|どの|いくら",
    # A softener after the verb ("覚えといてね、..."), and a closing
    # complementizer on a keyword-first note ("...ってこと").
    note_lead=(rf"^(?:ね|よ|な|ください|くれ|ちょうだい)*(?={_PUNCT}|$){_PUNCT}*"
               r"|(?:ということ|ってこと)$|^(?:これ|それ|あれ|この話|その話)$"),
    # "about X" is "Xのこと" / "Xについて" in Japanese, after the query.
    query_lead=(rf"^(?:ね|よ|ください|くれ)*(?={_PUNCT}|$){_PUNCT}*"
                r"|(?:のこと|について)$"),
    # Recall and learned are whole questions about its memory.
    recall=(r"(?:何|なに)(?:を)?覚えて(?:る|いる|ます)|どんなこと(?:を)?覚えて(?:る|いる)"
            r"|(?:記憶|メモ)(?:に|には)?(?:何|なに)(?:が)?(?:ある|入って(?:る|いる))"),
    recall_tail=r"の|ん?ですか|か|かな|っけ",
    learned=(r"(?:何|なに)(?:を|か)?(?:学んだ|学習した|覚えた)"
             r"(?=\s*(?:の|ん?ですか|か|かな|っけ)?[\s?？!！。~～]*$)"),
    # "" too: "ノヴァ、忘れて" leaves only the comma as a verb-last query.
    deictic=frozenset({"", "それ", "これ", "あれ", "今の", "さっきの", "そのこと", "このこと",
                       "あのこと", "今のこと", "さっきのこと", "今の話", "さっきの話",
                       "その話", "なんでもない", "もう", "もういい", "もういいから"}),
    everything=frozenset({"全部", "すべて", "全て", "全部のこと", "何もかも",
                          "全部の記憶", "全部のメモ"}),
    # Singular only: 私たち / 僕ら are "we". The kana forms only open a phrase,
    # since "おれ" also hides in お礼, 倒れる.
    first_person=(r"私(?!たち|達|ども|立|服|鉄|有)|僕(?!たち|達|ら)|俺(?!たち|達|ら)"
                  r"|(?:^|(?<=[\s、。,，!！?？]))(?:わたし|あたし|ぼく|おれ|うち)"
                  r"(?!たち|達|ら)(?=[はがのもをにと、,\s]|$)"),
    replies={
        "remember_what": ("覚えるって何を？何も言ってないじゃん", "で、何を覚えればいい？",
                          "何を覚えるの"),
        "not_instructions": ("覚えられるのは事実だけ、指示は無理",),
        "noted": ("覚えた", "了解、メモった", "おっけー、覚えとく", "うん", "はーい"),
        "forget_what": ("何を忘れるの？はっきり言って", "どれのこと？もうちょい詳しく"),
        "nothing_to_forget": ("え、そんなの覚えてないよ", "記憶にないなあ",
                              "忘れるようなこと何もないけど"),
        "forgotten": ("忘れた", "消しといた", "もう覚えてない"),
        "empty": ("頭の中からっぽ", "何も覚えてないよ", "まっさら"),
        "recall_head": ("覚えてるのはこれ：",),
        "about": ("{name}について：",),
        "from": ("{name}から：",),
    },
    failure_excuses=("ごめん、ちょっと固まってる",
                     "待って、回線が変かも",
                     "電波悪いから少し待って"),
    learned_text={
        "head": ("記憶 {memories} 件、覚えた返事 {examples} 件、直し {fixes} 組、"
                 "二人目の確認待ち {voice} 件、管理者待ち {admin} 件"),
        "score": "、最近の自己評価 {score}/5",
        "pair": "前：{was}、直し：{better}",
        "someone_else": "別のチャットの誰か",
        "someone": "誰か",
        "retry": "{who} が答え直しを受け入れた",
        "self_review": "自分で振り返り",
        "self_eval": "自己評価で満点",
        "corrected": "{who} が直した",
        "missed": "{who} がハズレって言った",
        "liked": "{who} がいいって言った",
        "by_admin": "管理者が承認",
        "passed": "証拠 {events} 件、うち強いの {strong} 件で通過",
        "why": "理由：{steps}",
        "sep": "、",
    },
)
