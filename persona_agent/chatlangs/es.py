"""Spanish."""
from . import Spec

SPEC = Spec(
    code="es",
    # tú imperatives. "guarda" only before "esto"/"que": "guarda silencio" is
    # not a note. "apúntate" means "join in", so it is left out.
    remember=(r"(?:recuerda|acu[eé]rdate(?:\s+de)?|apunta|anota|memoriza"
              r"|no\s+olvides|guarda(?=\s+(?:esto|que)\b))\b"),
    # "recuerda cuando...", "acuérdate de aquella vez": reminiscing. "Nova
    # recuerda todo / muy bien / a mi gato" reads as the third person.
    not_a_note=(r"(?!\s*(?:de\s+)?(?:cuando|cuándo|c[oó]mo|qué|cu[aá]l|qui[eé]n"
                r"|d[oó]nde|si|aquel|aquella|aquello|la\s+vez|el\s+d[ií]a"
                r"|lo\s+que|lo\s+de|todo|siempre|muy|bien|mejor|mucho|nada"
                r"|perfectamente|al?)\b)"),
    forget=r"(?:olv[ií]date(?:\s+de)?|olvida)\b",
    # "olvídalo" never matches the keyword; "olvida eso" is in `deictic`.
    not_a_delete=r"(?!\s*(?:lo|eso|esto|ello)\s*$)",
    # Spanish opens a question with ¿, and tags one with "verdad", "no".
    question_end=(r"¿|(?:[?？]|\b(?:verdad|cierto|o\s+no|no\s+crees|né)\b)"
                  r"[\s?？!！.。~～]*$"),
    asking=r"(?:qué|cómo|cuándo|dónde|cuánto|quién|cuál|por\s*qu[eé])\b|¿",
    recall=(r"¿?\s*(?:qu[eé]\s+(?:te\s+)?recuerdas"
            r"|qu[eé]\s+(?:cosas\s+)?(?:tienes\s+)?(?:guardad|apuntad|anotad)[oa]s?"
            r"|qu[eé]\s+(?:hay|tienes)\s+en\s+(?:tu\s+)?memoria)"),
    recall_tail=r"t[uú]",
    learned=(r"¿?\s*qu[eé]\s+(?:has\s+aprendido|aprendiste)"
             r"(?:\s+(?:hasta\s+ahora|[uú]ltimamente))?(?=[\s?？!！.。~～]*$)"),
    # "recuerda esto: ...", "recuerda que ...", "acuérdate de que ...".
    note_lead=r"^(?:(?:esto|eso)\s*(?:[:,]\s*|[.!~]*$))?(?:de\s+que\s+|que\s+)?",
    query_lead=(r"^(?:lo\s+que\s+(?:te\s+)?(?:dije|cont[eé])\s+)?"
                r"(?:(?:lo\s+)?(?:del?|sobre|acerca\s+de)\s+|que\s+)"),
    deictic=frozenset({"eso", "esto", "ello", "lo", "aquello", "eso que dije",
                       "lo que dije", "lo que te dije", "lo anterior", "lo de antes",
                       "tema", "el tema", "ese tema", "este tema"}),
    everything=frozenset({"todo", "todo eso", "todo lo que sabes", "todas",
                          "todos", "toda tu memoria", "todas las notas"}),
    # Spanish drops the subject, so a few first-person verbs count too.
    first_person=(r"(?<!\w)(?:yo|me|mi|mis|mí|mío|mía|míos|mías|conmigo|soy|estoy"
                  r"|tengo|quiero|prefiero|necesito|odio|detesto|adoro)(?!\w)"),
    replies={
        "remember_what": ("¿recordar qué? no dijiste nada", "venga, suéltalo",
                          "¿qué apunto?"),
        "not_instructions": ("puedo recordar datos, no instrucciones",),
        "noted": ("apuntado", "vale, anotado", "listo, me lo quedo", "ok"),
        "forget_what": ("¿olvidar qué? dime cuál", "¿cuál? explícate un poco"),
        "nothing_to_forget": ("eh, eso nunca lo apunté", "no me suena de nada",
                              "no hay nada así que olvidar"),
        "forgotten": ("olvidado", "borrado", "fuera", "chao"),
        "empty": ("tengo la cabeza vacía", "ahí no hay nada", "en blanco"),
        "recall_head": ("Esto es lo que recuerdo:",),
        "about": ("sobre {name}: ",),
        "from": ("de {name}: ",),
    },
    failure_excuses=("uf, se me colgó todo un segundo",
                     "espera, la conexión va fatal",
                     "la señal va rara, dame un minuto"),
    learned_text={
        "head": ("notas: {memories}, respuestas aprendidas: {examples}, "
                 "correcciones: {fixes}, esperando a otra persona: {voice}, "
                 "esperando al admin: {admin}"),
        "score": ", autoevaluación reciente: {score}/5",
        "pair": "antes: {was}, ahora: {better}",
        "someone_else": "alguien en otro chat",
        "someone": "alguien",
        "retry": "{who} aceptó la nueva respuesta",
        "self_review": "autorrevisión",
        "self_eval": "autoevaluación perfecta",
        "corrected": "{who} corrigió",
        "missed": "{who} dijo que no acerté",
        "liked": "a {who} le gustó",
        "by_admin": "aprobado por el admin",
        "passed": "pruebas: {events}, fuertes: {strong}, aprobado",
        "why": "motivo: {steps}",
        "sep": ", ",
    },
    stopwords=frozenset({
        "el", "los", "las", "del", "lo", "una", "qué", "cómo", "dónde", "pero",
        "muy", "eso", "esto", "hay", "yo", "tú", "también", "bueno", "pues",
        "cuando", "ahora", "aquí", "hoy", "tengo", "quiero", "tiene", "estoy",
        "eres", "puedo", "creo", "verdad", "siempre", "mucho", "ella", "hola",
        "gracias", "sí", "jaja", "jajaja",
    }),
    letters="ñ¿¡",
)
