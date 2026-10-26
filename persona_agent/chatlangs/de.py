"""German."""
from . import Spec

# A German word character, for word edges ("merk" not "merkwürdig").
_W = r"[\wäöüß']"
# Fillers people drop into a question about its memory.
_FILL = r"(?:\s+(?:denn|so|eigentlich|alles|bisher|schon))*"

SPEC = Spec(
    code="de",
    # The du imperative: "merk dir", "merk's dir", "notier", "speicher",
    # "schreib dir auf", each with an optional "bitte" or "mal".
    remember=(r"(?:bitte\s+)?(?:merk(?:e|'?s)?(?:\s+mal)?\s+dir"
              r"|notier(?:e|'?s)?(?:\s+mal)?(?:\s+dir)?"
              r"|speicher(?:e|'?s)?(?:\s+mal)?(?:\s+dir)?"
              r"|schreib(?:e|'?s)?(?:\s+mal)?\s+dir\s+auf)"
              rf"(?!{_W})"),
    # "merk dir das", "merk dir mal was": nothing named to keep.
    not_a_note=r"(?!\s*(?:das|dies|es|mal\s+was|was)\s*[!.~]*$)",
    forget=rf"(?:bitte\s+)?(?:vergiss|vergiß)(?:\s+mal)?(?!{_W})",
    # "vergiss es" is never mind; "vergiss nicht, ..." and "vergiss mich
    # nicht" ask it to remember, not to delete.
    not_a_delete=r"(?!\s*(?:es|'s|nicht|nich|mich|uns)(?![\wäöüß]))",
    # A German question can end in a tag instead of a question mark.
    question_end=(r"(?:[?？]|(?<![\wäöüß])(?:oder|oder\s+nicht|ne|gell|nicht\s+wahr|"
                  r"woll|wa)\s*)[\s?？!！.~]*$"),
    # "vergiss, was ich gesagt hab" waves it off; "wie vergess ich..." asks.
    asking=(r"(?<![\wäöüß])(?:was|wie|warum|wieso|weshalb|wer|wo|wann|ob|"
            r"welche[rsnm]?)(?![\wäöüß])"),
    note_lead=(r"^(?:(?:bitte|mal)(?:\s*[,:]\s*|\s+))*(?:(?:das|dies|folgendes)\s*:\s*)?"
               r"(?:(?:(?:doch|kurz|noch|eben)\s+)*(?:,\s*)?(?:dass|daß)\s+)?"),
    query_lead=(r"^(?:(?:bitte|mal|doch)\s+)*"
                r"(?:(?:das|die\s+sache)\s+mit\s+(?:(?:dem|der|den|die|das)\s+)?"
                r"|(?:alles\s+)?(?:über|von|wegen)\s+(?:(?:dem|der|den|die|das)\s+)?"
                r"|(?:dass|daß)\s+)?"),
    # Whole questions about its memory only: "weißt du noch, als..." reminisces.
    recall=(rf"was\s+(?:hast\s+du{_FILL}\s+dir{_FILL}\s+gemerkt"
            rf"|hast\s+du{_FILL}\s+(?:gespeichert|notiert)"
            rf"|merkst\s+du\s+dir{_FILL}"
            rf"|wei(?:ß|ss)t\s+du{_FILL}\s+(?:noch|über\s+uns))"
            rf"|woran\s+erinnerst\s+du\s+dich{_FILL}"
            r"|was\s+ist\s+in\s+deinem\s+(?:gedächtnis|kopf|speicher)"),
    recall_tail=r"(?:so|denn|eigentlich|alles)",
    learned=(rf"was\s+hast\s+du{_FILL}(?:\s+(?:neues|dazu))?\s+(?:dazu)?gelernt"
             rf"(?!{_W})"),
    deictic=frozenset({"das", "dies", "dieses", "diese", "den", "die", "es",
                       "das da", "das hier", "das eben", "das gerade",
                       "das einfach", "den da", "die da", "das von eben",
                       "das von gerade"}),
    everything=frozenset({"alles", "alle", "alles davon", "einfach alles",
                          "komplett alles", "alle notizen", "alles was du weißt"}),
    # Whole words: "mir" and "mich", never inside "Mirabellen" or "Michael".
    first_person=(r"(?<![\wäöüß'])(?:ich|mich|mir|mein(?:e[mnrs]?)?|meins)"
                  r"(?![\wäöüß'])"),
    replies={
        "remember_what": ("was soll ich mir merken? du hast nix gesagt",
                          "na sag schon", "merken, was denn"),
        "not_instructions": ("ich merk mir Fakten, keine Anweisungen",),
        "noted": ("notiert", "okay, gemerkt", "hab ich mir gemerkt", "jo", "ok"),
        "forget_what": ("was soll ich vergessen? sag genauer",
                        "welches denn? sag mehr"),
        "nothing_to_forget": ("äh, hab ich mir nie gemerkt", "davon weiß ich nix",
                              "nichts Passendes zum Vergessen"),
        "forgotten": ("vergessen", "weg damit", "gelöscht", "tschüss"),
        "empty": ("Kopf ist leer", "da ist nix drin", "komplett leer"),
        "recall_head": ("Das weiß ich noch:",),
        "about": ("über {name}: ",),
        "from": ("von {name}: ",),
    },
    failure_excuses=("ugh, häng kurz fest",
                     "Moment, Verbindung spinnt",
                     "Netz ist grad komisch, gib mir ne Minute"),
    # "label: n" throughout, so no count has to agree with a noun.
    learned_text={
        "head": ("Erinnerungen: {memories}, gelernte Antworten: {examples}, "
                 "Korrekturen: {fixes}, warten auf eine zweite Stimme: {voice}, "
                 "warten auf den Admin: {admin}"),
        "score": ", letzte Selbstbewertung {score}/5",
        "pair": "vorher: {was}, besser: {better}",
        "someone_else": "jemand in einem anderen Chat",
        "someone": "jemand",
        "retry": "{who} hat die neue Antwort genommen",
        "self_review": "eigene Nachbetrachtung",
        "self_eval": "Selbstbewertung mit voller Punktzahl",
        "corrected": "{who} hat korrigiert",
        "missed": "{who} meinte, das war daneben",
        "liked": "{who} fand's gut",
        "by_admin": "vom Admin freigegeben",
        "passed": "Belege: {events}, davon stark: {strong}, bestanden",
        "why": "Grund: {steps}",
        "sep": ", ",
    },
    # Frequent in German, not in English, Spanish, French or Portuguese
    # ("das", "die", "was", "war", "will", "so" are left out).
    stopwords=frozenset({
        "ich", "du", "nicht", "und", "ist", "der", "den", "auch", "noch", "schon",
        "eben", "doch", "ja", "wir", "sie", "mit", "auf", "für", "ein", "eine",
        "kein", "wie", "wenn", "aber", "oder", "heute", "bist", "hast", "habe",
        "haben", "sind", "geht", "nur", "jetzt", "nichts", "dir", "mir", "mich",
        "dich", "nein", "bitte", "danke", "echt", "denn", "gerade",
    }),
    letters="ßäöü",
)
