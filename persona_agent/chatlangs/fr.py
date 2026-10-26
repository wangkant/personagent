"""French."""
from . import Spec

# Typed apostrophes come straight or curly.
_A = "['’]"

SPEC = Spec(
    code="fr",
    # Imperatives, tu or vous. "note" is English, "rappelle" alone is "call
    # back", so only the reflexive "rappelle-toi"; "n'oublie pas" only with
    # "que", else it is a reminder to act ("n'oublie pas de manger").
    remember=(r"(?:retiens|retenez|mémorise|mémorisez|souviens[-\s]toi|souvenez[-\s]vous"
              r"|rappelle[-\s]toi|rappelez[-\s]vous"
              r"|gardez?\s+(?:bien\s+)?en\s+(?:tête|tete|mémoire|memoire)"
              rf"|(?:n{_A}\s*)?oubli(?:e|ez)\s+pas(?=\s+qu))(?![\w-])"),
    # "souviens-toi quand on...", "rappelle-toi de la fois où": reminiscing.
    not_a_note=(r"(?![\s,]*(?:bien\s+)?(?:(?:quand(?!\s+même)|comment|quoi|qui|pourquoi"
                r"|où|si|combien|lorsque|la\s+fois|cette\s+fois|le\s+jour|moi|de|du|des)"
                rf"(?![\w-])|d{_A}))"),
    forget=r"(?:oublie|oubliez)(?![\w-])",
    # "oublie ça", "oublie pas de..." (casual "don't forget"), "laisse tomber".
    not_a_delete=(r"(?![\s,]*(?:ça|ca|cela|pas|laisse|c{_A}est\s+pas\s+grave|tout\s+ça)"
                  r"(?![\w-]))").replace("{_A}", _A),
    recall=(rf"(?:qu{_A}est-ce\s+que\s+|que\s+)?(?:tu\s+te|vous\s+vous)\s+"
            r"(?:souviens|rappelles|souvenez|rappelez)\s+de\s+quoi"
            r"|de\s+quoi\s+(?:tu\s+te\s+(?:souviens|rappelles)|te\s+souviens-tu"
            r"|vous\s+vous\s+(?:souvenez|rappelez)|vous\s+souvenez-vous)"
            rf"|qu{_A}(?:est-ce\s+que\s+(?:tu\s+as|t{_A}\s*as|vous\s+avez)|as-tu|avez-vous)"
            r"\s+(?:retenu|en\s+mémoire)"
            rf"|(?:tu\s+as|t{_A}\s*as|vous\s+avez)\s+(?:retenu|quoi)\s+(?:quoi|en\s+mémoire)"
            r"|(?:ta|votre)\s+mémoire\s*\?"),
    recall_tail=r"(?:jusqu{_A}ici|pour\s+l{_A}instant|en\s+fait)".replace("{_A}", _A),
    learned=(rf"qu{_A}(?:est-ce\s+que\s+(?:tu\s+as|t{_A}\s*as|vous\s+avez)|as-tu|avez-vous)"
             rf"\s+appris|(?:tu\s+as|t{_A}\s*as|vous\s+avez)\s+appris\s+quoi|appris\s*\?"),
    # The question mark, a tag ("..., non", "hein") or an opening "est-ce que".
    question_end=(r"[?？][\s?？!！.~～]*$|(?:,\s*(?:non|nan|ou\s+pas|ou\s+quoi)|[\s,]hein)[\s!.~]*$"
                  rf"|^est-ce\s+qu"),
    asking=(rf"(?<![\w-])(?:comment|pourquoi|quoi|combien|où|est-ce|lequel|laquelle)"
            r"(?![\w-])"),
    # "retiens bien que...", "retiens ça : ...", "qu'il..." keeps "il...".
    note_lead=(r"^(?:bien\s+|quand\s+même\s+)?(?:(?:ça|ca|cela|ceci)(?:\s*[:,]\s*|\s*$))?"
               rf"(?:que\s+|qu{_A}\s*)?"),
    query_lead=(r"^(?:(?:tout\s+)?ce\s+que\s+(?:je\s+t{_A}ai|j{_A}ai)\s+dit\s+sur\s+"
                r"|à\s+propos\s+|au\s+sujet\s+|concernant\s+|le\s+truc\s+sur\s+)"
                rf"(?:(?:de|du|des)\s+|d{_A}\s*)?").replace("{_A}", _A),
    deictic=frozenset({"ça", "ca", "cela", "ceci", "ce truc", "ce truc-là", "ça là",
                       "celui-là", "celle-là", "le", "la", "les", "ce que j'ai dit",
                       "tout ça"}),
    everything=frozenset({"tout", "tous", "toutes", "tout le reste", "tout ce que tu sais",
                          "toute ta mémoire", "ta mémoire"}),
    first_person=(r"(?<![\w'’-])(?:je|moi|me|mon|ma|mes|mien|mienne|miens|miennes"
                  r"|moi-même)(?![\w'’-])|(?<![\w'’-])[jm]['’](?=\w)"),
    replies={
        "remember_what": ("retenir quoi ? t'as rien dit", "vas-y, dis",
                          "je retiens quoi lol"),
        "not_instructions": ("je retiens des faits, pas des consignes",),
        "noted": ("noté", "ok, c'est retenu", "retenu", "mhm", "ok"),
        "forget_what": ("oublier quoi ? sois plus précis", "laquelle ? dis-en plus"),
        "nothing_to_forget": ("euh, j'ai jamais noté ça", "ça me dit rien",
                              "rien de tel à oublier"),
        "forgotten": ("oublié", "effacé", "c'est oublié", "bye"),
        "empty": ("j'ai la tête vide", "y a rien là-dedans", "page blanche"),
        "recall_head": ("Voilà ce dont je me souviens :",),
        "about": ("sur {name} : ",),
        "from": ("de {name} : ",),
    },
    failure_excuses=("attends, ça rame un peu",
                     "deux secondes, la connexion fait des siennes",
                     "réseau bizarre là, laisse-moi une minute"),
    learned_text={
        "head": ("souvenirs : {memories}, réponses apprises : {examples}, "
                 "corrections : {fixes}, en attente d'un deuxième avis : {voice}, "
                 "en attente de l'admin : {admin}"),
        "score": ", dernière auto-éval : {score}/5",
        "pair": "avant : {was}, maintenant : {better}",
        "someone_else": "quelqu'un dans un autre chat",
        "someone": "quelqu'un",
        "retry": "{who} a accepté la nouvelle réponse",
        "self_review": "auto-bilan",
        "self_eval": "auto-éval au max",
        "corrected": "{who} a corrigé",
        "missed": "{who} a dit que c'était raté",
        "liked": "{who} a aimé",
        "by_admin": "validé par l'admin",
        "passed": "preuves : {events}, solides : {strong}, validé",
        "why": "pourquoi : {steps}",
        "sep": ", ",
    },
    # Frequent in French, rare in English, Spanish, German, Portuguese: so not
    # "que", "de", "le", "tu" (es/pt), "du"/"des" (de), "mais"/"ou" (pt), "on".
    stopwords=frozenset({
        "je", "il", "elle", "ils", "nous", "vous", "est", "suis", "sont", "pas",
        "c'est", "j'ai", "t'es", "ce", "ça", "cette", "avec", "dans", "sur", "qui",
        "au", "aux", "très", "demain", "trop", "aussi", "alors", "quoi", "oui",
        "ouais", "salut", "merci", "vraiment", "encore", "toujours", "rien", "ici",
        "moi", "toi", "peux", "veux", "sais", "fait", "faire", "être", "une",
    }),
    letters="èëîïûùœ",
)
