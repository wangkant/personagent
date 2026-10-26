"""Brazilian Portuguese."""
from . import Spec

SPEC = Spec(
    code="pt-BR",
    # "anota aí", "lembra que", "lembre-se de que", "não esquece que". No
    # "grave" (English) and no "memoriza"/"memorize" (Spanish, English).
    remember=(r"(?:n[ãa]o\s+esque[cç][ae]|lembr[ae](?:-se)?|anot[ae](?:\s+a[ií])?"
              r"|guard[ae](?:\s+a[ií])?|grava(?:\s+a[ií])?)(?![\w-])"),
    # "lembra quando...", "lembra da festa", "lembra que a gente...": reminiscing.
    not_a_note=(r"(?!\s*[,:]?\s*(?:quando|como|onde|quem|qual|se|o\s+que|aquel[ae]s?"
                r"|aquilo|daquel[ae]s?|daquilo|disso|disto|de\s+mim|me|segredo|sil[êe]ncio"
                r"|(?:isso\s+)?pra\s+(?:voc[êe]|vc|ti)"
                r"|que\s+(?:a\s+gente|n[óo]s|voc[êe]|vc)|d[aoe]s?(?!\s+que\b))\b)"),
    forget=r"(?:esque[cç][ae])\b",
    # "esquece isso", "esquece aí", "esquece, deixa pra lá": never mind.
    not_a_delete=(r"(?!\s*[,.!]?\s*(?:isso|isto|aquilo(?!\s+(?:de|sobre)\b)|disso|a[ií]|l[áa]|deixa"
                  r"|pra\s+l[áa]|tudo\s+isso)\b)"),
    recall=(r"(?:o|do)\s+que\s+(?:voc[êe]|vc|tu)\s+(?:se\s+)?lembra(?:\s+de\s+mim)?"
            r"|o\s+que\s+(?:tem|t[áa])\s+na\s+(?:sua|tua)\s+mem[óo]ria"
            r"|o\s+que\s+(?:voc[êe]|vc|tu)\s+(?:guardou|anotou)"),
    recall_tail=r"a[ií]|hein|ent[ãa]o",
    # Anchored: "o que você aprendeu na escola" is chat, not the summary.
    learned=(r"(?:o\s+)?que\s+(?:voc[êe]|vc|tu)\s+(?:j[áa]\s+)?aprendeu"
             r"(?:\s+(?:at[ée]\s+agora|comigo|com\s+a\s+gente|a[ií]))?"
             r"\s*[?!.~]*$"),
    # Questions often drop the mark and end on a tag: "né", "não é", "lembra".
    question_end=(r"[?？][\s?？!！.。~～]*$"
                  r"|\b(?:n[ée]|n[ãa]o\s+[ée]|sabe|lembra|certo|hein)[\s!.~]*$"),
    asking=r"\b(?:como|por\s*qu[eê]|pq|onde|qual|quais|quem|o\s+que|e\s+se|ser[áa]\s+que)\b",
    note_lead=(r"^(?:(?:de\s+que|que|a[ií]|isso|isto|l[áa]|pra\s+mim|por\s+favor|pfv)"
               r"(?:\s*[:,]\s*|\s+|$))+"),
    query_lead=(r"^(?:(?:o\s+lance\s+d[aoe]s?|a\s+parte\s+d[aoe]s?|aquilo\s+(?:de|sobre)"
                r"|a\s+d[aoe]s?|o\s+d[aoe]s?|sobre|d[aoe]s?|que|as|os|a|o)\s+)+"),
    deictic=frozenset({"isso", "isto", "aquilo", "disso", "disto", "daquilo",
                       "esse", "essa", "este", "esta", "isso aí", "isso ai",
                       "esse aí", "essa aí", "aquilo lá", "ele", "ela"}),
    everything=frozenset({"tudo", "tudo isso", "tudinho", "todas", "todos",
                          "tudo que você sabe", "tudo que vc sabe"}),
    first_person=r"(?<![\w'])(?:eu|me|mim|comigo|meu|meus|minha|minhas)(?![\w'])",
    replies={
        "remember_what": ("lembrar o quê? você não falou nada", "fala aí, anotar o quê",
                          "anotar o quê kkk"),
        "not_instructions": ("eu guardo fatos, não instruções",),
        "noted": ("anotado", "beleza, guardei", "tá anotado", "fechou", "ok"),
        "forget_what": ("esquecer o quê? fala direito", "qual delas? explica melhor"),
        "nothing_to_forget": ("hm, nunca anotei isso", "não lembro disso não",
                              "não achei nada pra esquecer"),
        "forgotten": ("esqueci", "apagado", "já era", "foi"),
        "empty": ("cabeça vazia", "não tem nada aqui", "tudo em branco"),
        "recall_head": ("Olha o que eu lembro:",),
        "about": ("sobre {name}: ",),
        "from": ("de {name}: ",),
    },
    failure_excuses=("pera, travei aqui",
                     "calma, a conexão tá zoada",
                     "sinal ruim agora, me dá um minuto"),
    # "label: {n}" throughout, so no count needs singular or plural.
    learned_text={
        "head": ("memórias: {memories}, respostas aprendidas: {examples}, "
                 "correções: {fixes}, esperando outra pessoa confirmar: {voice}, "
                 "esperando o admin: {admin}"),
        "score": ", última autoavaliação {score}/5",
        "pair": "antes: {was}, agora: {better}",
        "someone_else": "alguém em outro chat",
        "someone": "alguém",
        "retry": "{who} aceitou a nova resposta",
        "self_review": "revisão própria",
        "self_eval": "autoavaliação nota máxima",
        "corrected": "{who} corrigiu",
        "missed": "{who} disse que errei",
        "liked": "{who} curtiu",
        "by_admin": "aprovado pelo admin",
        "passed": "provas: {events}, fortes: {strong}, passou",
        "why": "motivo: {steps}",
        "sep": ", ",
    },
    stopwords=frozenset({
        "não", "nao", "você", "voce", "vc", "tá", "ta", "tô", "né", "pra", "tenho",
        "isso", "muito", "também", "tambem", "tbm", "agora", "aqui", "gente",
        "eu", "ela", "uma", "meu", "minha", "então", "ainda", "já", "só",
        "hoje", "amanhã", "ontem", "vou", "vai", "estou", "quero", "tudo", "kkk",
        "kkkk", "rs", "beleza", "valeu", "obrigado", "obrigada", "pq", "nem",
        "acho", "aí", "bem",
    }),
    letters="ãõ",
)
