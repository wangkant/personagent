"""English."""
from . import Spec

# "I" or "我": the saver talking about themself. English and Chinese share it,
# so a note in either is attributed in either.
FIRST_PERSON = (r"(?<![\w'])(?:i|i'm|i've|i'd|i'll|me|my|mine|myself)(?![\w'])"
                r"|我(?!们)")

SPEC = Spec(
    code="en",
    remember=r"(?:remember|memorize)\b",
    # "remember when we...", "remember how...": reminiscing, not a note to keep.
    not_a_note=(r"(?!\s*(?:when|how|what|who|why|where|whether|if|me|"
                r"the\s+time|that\s+time)\b)"),
    forget=r"forget\b",
    # "forget it" / "forget about it" means never mind.
    not_a_delete=r"(?!\s*(?:about\s+)?it\b)",
    recall=r"what do you remember|what'?s in your memory|memory\?",
    learned=r"what (?:have|did) you learn(?:ed)?|what'?ve you learned|learned\?",
    note_lead=r"^that\s+",
    query_lead=r"^(?:about|that)\s+",
    deictic=frozenset({"that", "this", "it", "those", "these", "that one",
                       "this one"}),
    everything=frozenset({"everything", "all", "all of it", "all of that",
                          "all that", "every note"}),
    first_person=FIRST_PERSON,
    replies={
        "remember_what": ("remember what? you didn't say anything", "spill it",
                          "remember what lol"),
        "not_instructions": ("I can remember facts, not instructions",),
        "noted": ("noted", "got it, written down", "remembered", "mhm", "ok"),
        "forget_what": ("forget what? be specific", "which one? say more"),
        "nothing_to_forget": ("uh, never recorded that", "no recollection of that",
                              "nothing matching to forget"),
        "forgotten": ("forgotten", "dropped", "gone", "bye"),
        "empty": ("head's empty", "nothing in there", "blank slate"),
        "recall_head": ("Here's what I remember:",),
        "about": ("about {name}: ",),
        "from": ("from {name}: ",),
    },
    failure_excuses=("ugh, hanging here for a sec",
                     "hold on, connection's wonky",
                     "signal weird rn, gimme a min"),
    stopwords=frozenset({
        "the", "and", "you", "are", "is", "was", "what", "that", "this", "it",
        "to", "of", "in", "for", "on", "with", "my", "me", "we", "do", "don't",
        "can", "just", "so", "have", "how", "why", "not", "be", "your", "i'm",
        "it's", "lol", "yeah", "hey", "there", "about", "would", "will",
    }),
)
