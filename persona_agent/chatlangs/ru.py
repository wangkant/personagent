"""Russian."""
from . import Spec

# Cyrillic word edges: \w covers it, the hyphen keeps "что-то" one word.
_W = r"(?<![\w-])"
_E = r"(?![\w-])"

SPEC = Spec(
    code="ru",
    # Imperatives, informal and polite. "заметь" is left out: "заметь, я был
    # прав" is rhetoric, not a note.
    remember=r"(?:запомни|запиши|сохрани)(?:те)?" + _E,
    # "запомни этот момент": sentiment, not a note.
    not_a_note=r"(?!\s*[,:]?\s*(?:этот|это|тот)\s+(?:момент|день|вечер)" + _E + ")",
    forget=r"забудь(?:те)?" + _E,
    # "забудь, проехали" / "забудь, неважно" means never mind.
    not_a_delete=(r"(?!\s*[,.!]?\s*(?:проехали|неважно|не\s+важно|забей|ладно|"
                  r"не\s+бери\s+в\s+голову)" + _E + ")"),
    recall=(r"что\s+(?:ты\s+)?(?:помнишь|запомнила?)|"
            r"что\s+у\s+тебя\s+в\s+памяти|покажи\s+(?:свою\s+)?память"),
    # Whole question only: "что ты узнала про Кей" is conversation.
    learned=(r"(?:чему\s+ты\s+(?:уже\s+)?научил(?:ась|ся)|"
             r"что\s+ты\s+(?:уже\s+)?(?:узнала?|выучила?)(?:\s+нового)?)"
             r"(?=[\s?？!.~]*$)"),
    # A bare question word is a question too: "запомни что".
    question_end=(r"[?？][\s?？!！.。~～]*$|"
                  r"^(?:что|чего|какое|какой|какую|о\s+ч[её]м|про\s+что)[\s!.~]*$"),
    asking=_W + r"(?:почему|зачем|разве|ли|можно|можешь|сможешь)" + _E,
    note_lead=(r"^(?:(?:что|мол|типа|короче|ну|пожалуйста|плиз|себе|на\s+будущее)(?:[\s,:]+|$))+"
               r"|^(?:это|вот\s+это)\s*[!.]*$"),
    query_lead=r"^(?:(?:заметку|запись)\s+)?(?:про|об?|обо|насч[её]т)\s+",
    recall_tail=r"вообще|сейчас",
    deictic=frozenset({"это", "этом", "этого", "то", "том", "того", "его", "её",
                       "ее", "их", "нём", "нем", "ней", "них", "всё это", "все это", "это всё", "это все"}),
    everything=frozenset({"всё", "все", "вообще всё", "всё подряд", "всю память",
                          "все заметки", "всё что помнишь"}),
    first_person=(_W + r"(?:я|меня|мне|мной|мною|мой|моя|моё|мое|мои|моего|моей|"
                  r"моему|моим|моих|моими|мою)" + _E),
    # Neutral forms where a verb would show the persona's gender. Each line
    # ends off a letter: the note follows it, and a Cyrillic letter glued to
    # a Latin one is refused by the character policy as a mixed-script token.
    replies={
        "remember_what": ("запомнить что?", "а что записать-то?", "что запомнить?"),
        "not_instructions": ("я запоминаю факты, а не команды!",),
        "noted": ("записано!", "принято!", "ок, есть!", "ага, запомнено!"),
        "forget_what": ("забыть что?", "что именно забыть?"),
        "nothing_to_forget": ("хм, такого не записано...", "не помню такого...",
                              "а такого и не было!"),
        "forgotten": ("забыто!", "стёрто!", "всё, нету!"),
        "empty": ("в голове пусто...", "ничего не записано...", "чистый лист!"),
        "recall_head": ("Вот что я помню:",),
        "about": ("про {name}: ",),
        "from": ("от {name}: ",),
    },
    failure_excuses=("секунду, что-то подвисает",
                     "погоди, связь барахлит",
                     "сигнал шалит, дай минутку"),
    # "label: n", so no word agrees with a count.
    learned_text={
        "head": ("заметок: {memories}, выученных ответов: {examples}, "
                 "исправлений: {fixes}, ждут второго голоса: {voice}, "
                 "ждут админа: {admin}"),
        "score": ", последняя самооценка {score}/5",
        "pair": "было: {was}, стало: {better}",
        "someone_else": "кто-то в другом чате",
        "someone": "кто-то",
        "retry": "{who} одобряет новый ответ",
        "self_review": "самопроверка",
        "self_eval": "самооценка на максимум",
        "corrected": "{who} поправляет",
        "missed": "{who} говорит, что мимо",
        "liked": "{who} хвалит",
        "by_admin": "одобрено админом",
        "passed": "доказательств: {events}, сильных: {strong}, принято",
        "why": "причина: {steps}",
        "sep": ", ",
    },
)
