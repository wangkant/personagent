"""Korean."""
from . import Spec

# Syllables with no final consonant: 를/는/라고 follow these, 을/은 the rest.
_OPEN = "".join(chr(0xAC00 + 28 * i) for i in range(399))
_H = "가-힣"
# A request ending: "기억해 줘", "적어 둬요", "기억해 주세요".
_SOFT = r"(?:\s*(?:주세요|줘요|둬요|놔요|줘|둬|놔|줄래))?(?:요)?"
_REMEMBER = rf"(?:좀\s*)?(?:(?:기억|메모)\s*(?:좀\s*)?해|(?:적어|외워)){_SOFT}"
_FORGET = r"(?:잊어\s*버려(?:\s*줘)?|잊어\s*줘|잊어)(?:요)?"

SPEC = Spec(
    code="ko",
    vocative=r"야|아|씨",
    remember=rf"{_REMEMBER}(?![{_H}])",
    # "기억해? 우리 그때...", "기억해 둔 거 있어": a question or a statement.
    not_a_note=(rf"(?!\s*[?？])(?!\s*(?:우리|그때|그\s*때|저번에|예전에|옛날에|어릴\s*때"
                rf"|둔|뒀|놨|놓은|준|줬|주는|두는|둘|줄)(?![{_H}]))"),
    # The verb last: "...라고 기억해 줘", "...을 기억해 둬", "...잊지 마".
    # A note ending in 때 or 던 거 ("그때 기억해") is reminiscing.
    remember_last=(rf"(?<!때)(?<!때 )(?<!던 거)(?<!던 거 )(?<!던거)(?<!던거 )"
                   rf"(?<!그거)(?<!그거 )"
                   rf"[,，:：]?\s*(?:(?<=다)고|(?<=\d[일월시분원명번개살])이라고|라고|(?<=[{_OPEN}])를|(?<![{_OPEN}\s])을)?\s*"
                   rf"(?:{_REMEMBER}|잊지\s*마(?:요|라)?)"),
    forget=rf"{_FORGET}(?![{_H}])",
    # "잊어 그냥", "잊어버려 됐어": never mind.
    not_a_delete=rf"(?!\s*(?:그냥|됐어|됐다|괜찮아)(?![{_H}]))",
    forget_last=rf"[,，:：]?\s*{_FORGET}",
    # No question mark needed after an unambiguous question ending; a casual
    # "좋아해" is both a statement and a question, so that one needs it.
    question_end=(r"(?:[?？]|(?:(?<!언)(?<!머)니|냐|(?<!니)까요?|나요|가요|는지|던가"
                  r"|[었았했였]나|뭐|뭘|뭐뭐)(?=[\s!！.。~～]*$))[\s?？!！.。~～]*$"),
    # Judged on a forget only: "우산 잊으면 어떡해" asks, it does not delete.
    asking=r"어떡|어떻게|어쩌|왜|뭐|뭘|무슨|언제|어디|누구|누가|몇|얼마|할까|될까",
    # "기억해 둬 이거: ...", "기억해 줘, 있잖아 ...": not part of the note.
    note_lead=(rf"^(?:이거도|이것도|이거|이것|그러니까|있잖아|줘|둬|놔|요)(?![{_H}])"
               r"[\s:：,，]*"),
    # Korean puts "about" after the query: "민수에 대한 거", "회의 얘기를".
    query_lead=(rf"(?:\s*(?:에\s*대한|에\s*관한|에\s*대해서?|관련된?|얘기|이야기)?"
                rf"\s*(?:거|것|건|내용|메모)?"
                rf"(?:(?<=[{_OPEN}])(?:는|를)|(?<![{_OPEN}\s])(?:은|을))?)$"),
    recall=(r"(?:너\s*)?(?:뭐|뭘|무엇을|무슨\s*거)\s*(?:다\s*)?기억(?:해|하고\s*있어|하니|하냐)"
            r"|(?:너\s*)?기억하는\s*(?:거|게)\s*(?:뭐|뭐가)\s*(?:있어|있니|있냐|야)?"),
    recall_tail=r"요",
    learned=(r"(?:(?:너\s*)?(?:뭐|뭘|무엇을)\s*(?:좀\s*)?(?:배웠|익혔)(?:어요|어|니|냐|나)?"
             r"|(?:너\s*)?배운\s*(?:거|게)\s*(?:뭐|뭐가)\s*(?:있어|있니|있냐|야)?)"
             r"(?=[\s?？!！.。~～]*$)"),
    deictic=frozenset({"", "그거", "이거", "저거", "그것", "이것", "그건", "이건", "그",
                       "이", "그냥", "됐어", "그 얘기", "그 일", "그거 그냥",
                       "방금 그거", "아까 그거", "아까 말한 거"}),
    everything=frozenset({"전부", "다", "모두", "전부 다", "다 전부", "모든 것",
                          "모든 거", "기억 전부", "기억 다"}),
    # Whole words only: 내일, 저녁, 나라, 제주 are not "I"; bare 저 is "that"
    # and bare 전 "before", so those count only with a particle.
    first_person=(rf"(?<![{_H}])(?:나(?:는|도|를|랑|한테|에게|만)?|내(?:가|꺼|거)?|난"
                  rf"|저(?:는|도|를|랑|한테|에게|만)|제(?:가)?)(?![{_H}])"),
    replies={
        "remember_what": ("뭘 기억하라고? 아무 말도 안 했잖아", "말을 해야 기억하지",
                          "뭐를 기억해"),
        "not_instructions": ("사실은 기억해도 지시는 안 받아",),
        "noted": ("기억해 둘게", "알았어, 적어 놨어", "오케이 기억함", "응 접수",
                  "메모 완료"),
        "forget_what": ("뭘 잊으라고? 구체적으로 말해 줘", "어떤 거? 좀 더 자세히"),
        "nothing_to_forget": ("음, 그런 건 적어 둔 적 없는데", "그런 기억 없어",
                              "지울 만한 게 없네"),
        "forgotten": ("잊었어", "지웠어", "삭제 완료", "없던 일로 할게"),
        "empty": ("머릿속 텅 비었어", "기억해 둔 게 하나도 없어", "백지 상태야"),
        "recall_head": ("내가 기억하는 거:",),
        "about": ("{name} 관련: ",),
        "from": ("출처 {name}: ",),
    },
    failure_excuses=("잠깐만, 렉 걸렸어",
                     "어 잠시만, 인터넷이 이상해",
                     "신호가 안 좋네, 조금만 기다려"),
    # 의 and labels, so no particle has to agree with a name or a number.
    learned_text={
        "head": ("기억 {memories}개, 배운 답변 {examples}개, 고친 것 {fixes}개, "
                 "두 번째 확인 대기 {voice}개, 관리자 확인 대기 {admin}개"),
        "score": ", 최근 자체 평가 {score}/5",
        "pair": "원래: {was}, 고친 거: {better}",
        "someone_else": "다른 채팅방의 누군가",
        "someone": "누군가",
        "retry": "다시 한 답을 {who} 쪽에서 수락",
        "self_review": "스스로 돌아봄",
        "self_eval": "자체 평가 만점",
        "corrected": "{who}의 지적으로 수정",
        "missed": "{who}의 틀렸다는 말",
        "liked": "{who}의 좋다는 말",
        "by_admin": "관리자 승인",
        "passed": "근거 {events}개 중 강한 근거 {strong}개, 통과",
        "why": "이유: {steps}",
        "sep": ", ",
    },
)
