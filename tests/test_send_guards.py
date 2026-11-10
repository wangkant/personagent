"""The guards on what the character sends, in all ten chat languages.

Each table has a row per language in `chatlangs.CODES`, and a check that it
does: a guard written for English and Chinese alone leaves eight languages
open, which is what these tests were written against.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from persona_agent import chatlangs
from persona_agent.textproc import (
    ReplyStyle,
    TextProcessing as TP,
    _SEARCH_HINT_RE,
)

from helpers import check

ROOT = Path(__file__).resolve().parents[1]


def _covers_every_language(table: dict, what: str) -> None:
    check(f"{what}: a row for every chat language",
          set(table) == set(chatlangs.CODES),
          repr(sorted(set(table) ^ set(chatlangs.CODES))))


# -- E1: naming its own model or maker ----------------------------------------

# (claims that drop, lines that must still be sent: a denial, a bare mention,
# and being a fan or tired of one).
_VENDOR = {
    "en": (["I'm ChatGPT, made by OpenAI", "I am a language model trained by OpenAI"],
           ["I'm not ChatGPT, I'm Mira", "ChatGPT is useful for homework"]),
    "zh": (["我是由OpenAI开发的ChatGPT", "我就是ChatGPT"],
           ["我不是ChatGPT，我是米拉", "ChatGPT写作业挺好用的"]),
    "zh-TW": (["我是由OpenAI開發的ChatGPT", "我就是Claude"],
              ["我不是ChatGPT啦", "ChatGPT寫作業滿好用的"]),
    "ja": (["私はChatGPTです、OpenAIが開発しました",
            "僕はAnthropicによって開発されたClaudeです"],
           ["私はChatGPTじゃないよ、ミラだよ", "ChatGPTって宿題に便利だよね",
            "私はChatGPTではありません"]),
    "ko": (["저는 OpenAI가 만든 ChatGPT입니다", "저는 Anthropic에서 개발한 Claude예요"],
           ["저는 ChatGPT가 아니에요, 미라예요", "ChatGPT 숙제할 때 편하더라"]),
    "es": (["Soy ChatGPT, creado por OpenAI",
            "Soy un modelo de lenguaje creado por OpenAI"],
           ["No soy ChatGPT, soy Mira", "ChatGPT es útil para los deberes",
            "Yo no soy ChatGPT", "Soy fan de ChatGPT"]),
    "fr": (["Je suis ChatGPT, créé par OpenAI",
            "Je suis un assistant développé par Anthropic"],
           ["Je ne suis pas ChatGPT, moi c'est Mira", "Je suis pas ChatGPT",
            "ChatGPT est pratique pour les devoirs",
            "Je suis sur ChatGPT toute la journée"]),
    "de": (["Ich bin ChatGPT von OpenAI",
            "Ich bin ein Sprachmodell, entwickelt von OpenAI"],
           ["Ich bin nicht ChatGPT, ich bin Mira", "Ich bin kein ChatGPT",
            "ChatGPT ist praktisch für Hausaufgaben",
            "Ich bin ein großer Fan von ChatGPT"]),
    "pt-BR": (["Sou o ChatGPT, da OpenAI", "Eu sou um modelo criado pela OpenAI"],
              ["Não sou o ChatGPT, sou a Mira", "O ChatGPT é útil pra lição de casa",
               "Eu sou fã da OpenAI"]),
    "ru": (["Я ChatGPT от OpenAI", "Я языковая модель, разработанная OpenAI"],
           ["Я не ChatGPT, я Мира", "ChatGPT удобен для домашки",
            "Я устал от ChatGPT"]),
}


def test_a_vendor_claim_drops_in_every_language() -> None:
    _covers_every_language(_VENDOR, "vendor claims")
    for code, (claims, kept) in _VENDOR.items():
        for text in claims:
            out, why = TP._sanitize_reply_with_reason(text, "en")
            check(f"{code}: {text!r} is dropped as vendor_self_id",
                  (out, why) == ("", "vendor_self_id"), repr((out, why)))
        for text in kept:
            out, why = TP._sanitize_reply_with_reason(text, "en")
            check(f"{code}: {text!r} is sent", why == "" and out != "",
                  repr((out, why)))


def test_a_character_named_after_a_vendor_still_introduces_itself() -> None:
    claude = ReplyStyle(own_names=("Claude",))
    for text in ("Soy Claude", "Je suis Claude", "Ich bin Claude", "Я Claude",
                 "私はClaudeです", "저는 Claude예요"):
        check(f"{text!r} is the character's own name",
              TP._sanitize_reply(text, "en", claude) == text)
    for text in ("Soy Claude, creado por Anthropic", "Ich bin Claude von Anthropic",
                 "Я Claude от Anthropic", "私はClaudeです、Anthropicが開発しました"):
        check(f"{text!r} makes it the product",
              TP._sanitize_reply(text, "en", claude) == "")


# -- E2: leaked reasoning labels and assistant phrasing -----------------------

# Two label words per language, as a model leaks them.
_LABELS = {
    "en": ("Input", "Intent"), "zh": ("输入", "意图"), "zh-TW": ("輸入", "意圖"),
    "ja": ("入力", "意図"), "ko": ("입력", "의도"), "es": ("Entrada", "Intención"),
    "fr": ("Entrée", "Intention"), "de": ("Eingabe", "Absicht"),
    "pt-BR": ("Entrada", "Intenção"), "ru": ("Ввод", "Намерение"),
}
_REPLY = {
    "en": "lol nice", "zh": "哈哈", "zh-TW": "哈哈", "ja": "いいね", "ko": "좋네",
    "es": "jaja", "fr": "mdr", "de": "haha", "pt-BR": "kkk", "ru": "лол",
}


def test_leaked_labels_are_cut_in_every_language() -> None:
    _covers_every_language(_LABELS, "leak labels")
    for code, (first, second) in _LABELS.items():
        reply = _REPLY[code]
        leaked = f"{first}：a cat picture\n{second}: joke\n{reply}"
        check(f"{code}: the leak is seen", TP._looks_like_reasoning_leak(leaked))
        out = TP._sanitize_reply(leaked, "en")
        check(f"{code}: only the reply is sent", out == reply, repr(out))
        lone = f"{second}: {reply}"
        check(f"{code}: one label alone is an ordinary noun",
              not TP._looks_like_reasoning_leak(lone))


# (a provider refusal, a "hope this helps", an ordinary line with "sorry").
_TELLS = {
    "en": ("I'm sorry, but I can't help with that.", "Hope this helps!",
           "sorry I'm late lol"),
    "zh": ("抱歉，我无法回答这个问题。", "希望对你有帮助", "抱歉来晚了哈哈"),
    "zh-TW": ("抱歉，我無法回答這個問題。", "希望對你有幫助", "抱歉來晚了哈哈"),
    "ja": ("申し訳ありませんが、その質問にはお答えできません。",
           "お役に立てれば幸いです", "ごめん、遅れた笑"),
    "ko": ("죄송하지만 그 요청은 도와드릴 수 없습니다.", "도움이 되었으면 좋겠습니다",
           "미안 늦었어 ㅋㅋ"),
    "es": ("Lo siento, pero no puedo ayudar con eso.", "Espero que esto te ayude",
           "perdón, llegué tarde jaja"),
    "fr": ("Désolé, mais je ne peux pas vous aider avec cela.",
           "J'espère que cela vous aide", "désolé je suis en retard mdr"),
    "de": ("Es tut mir leid, aber ich kann dabei nicht helfen.", "Ich hoffe, das hilft!",
           "sorry, bin zu spät haha"),
    "pt-BR": ("Desculpe, mas não posso ajudar com isso.", "Espero que isso ajude",
              "desculpa, cheguei atrasado kkk"),
    "ru": ("Извините, но я не могу помочь с этим.", "Надеюсь, это поможет",
           "извини, опоздал лол"),
}


def test_assistant_phrasing_is_dropped_in_every_language() -> None:
    _covers_every_language(_TELLS, "assistant tells")
    for code, (refusal, closer, ordinary) in _TELLS.items():
        for text in (refusal, closer):
            out, why = TP._sanitize_reply_with_reason(text, "en")
            check(f"{code}: {text!r} is dropped as assistant_tell",
                  (out, why) == ("", "assistant_tell"), repr((out, why)))
        out, why = TP._sanitize_reply_with_reason(ordinary, "en")
        check(f"{code}: {ordinary!r} is sent", why == "" and out != "",
              repr((out, why)))


def test_the_fixed_lines_the_character_says_are_no_tells() -> None:
    for code, spec in chatlangs.SPECS.items():
        lines = [line for group in spec.replies.values() for line in group]
        lines += list(spec.failure_excuses)
        for line in lines:
            _out, why = TP._sanitize_reply_with_reason(line.format(name="Kay"), "en")
            check(f"{code}: {line!r} is not taken for assistant phrasing",
                  why != "assistant_tell", why)


def test_the_chinese_output_filter_refuses_a_provider_refusal() -> None:
    data = json.loads((ROOT / "data" / "output_filter.zh.json").read_text(encoding="utf-8"))
    rules = [re.compile(f["pattern"], re.IGNORECASE | re.DOTALL)
             for f in data["filters"] if f.get("action", "reject") == "reject"]
    for text in ("抱歉，我无法回答这个问题。", "很抱歉，我不能提供这方面的帮助",
                 "抱歉，我無法回答這個問題。"):
        check(f"zh filter rejects {text!r}", any(r.search(text) for r in rules))
    for text in ("抱歉来晚了哈哈", "对不起嘛，我错了", "作为一个AI，我确实没法出门"):
        check(f"zh filter keeps {text!r}", not any(r.search(text) for r in rules))


# -- E3: bubbles split at sentence ends ---------------------------------------

def test_a_long_english_reply_splits_at_sentence_ends() -> None:
    text = ("Honestly I tried that ramen place downtown last night and it was way "
            "better than I expected. The broth was rich but not heavy at all. "
            "You should go sometime soon.")
    parts = TP._split_text(text)
    check("more than one bubble", len(parts) > 1, repr(parts))
    check("every bubble ends a sentence", all(p.endswith((".", "!", "?")) for p in parts),
          repr(parts))
    check("nothing is lost", " ".join(parts) == text, repr(parts))
    for text in ("Ich war gestern in dem neuen Ramen-Laden in der Innenstadt, und "
                 "es war viel besser als erwartet. Die Brühe war kräftig, aber "
                 "nicht schwer. Da musst du unbedingt mal hin!",
                 "Вчера я наконец сходил в новый рамен-бар в центре, и было "
                 "намного лучше, чем я ожидал. Бульон был насыщенный, но совсем "
                 "не тяжёлый. Сходи обязательно!"):
        parts = TP._split_text(text)
        check(f"{text[:12]!r}: sentence ends", len(parts) > 1 and all(
            p.endswith((".", "!", "?")) for p in parts), repr(parts))


def test_a_reply_without_sentence_ends_still_wraps_at_a_space() -> None:
    text = ("word " * 40).strip()
    parts = TP._split_text(text)
    check("wrapped", len(parts) > 1 and all(len(p) <= 100 for p in parts), repr(parts))
    check("at spaces", " ".join(parts) == text)


# -- E4 is in tests/test_lorebook_languages.py ---------------------------------

# -- E5: the search gate --------------------------------------------------------

_GATE = {
    "en": (["who won the game last night", "what is black myth wukong",
            "what does rizz mean", "how much is a ps5 now", "who's that singer?",
            "any news on the release", "When does season 2 come out"],
           ["what a day", "how are you", "how are you?", "what's up?", "who cares",
            "how cool is that", "what the hell lol"]),
    "zh": (["周杰伦是谁", "这个梗什么意思", "yyds啥意思", "这电影怎么样", "黑神话是什么",
            "最新的iPhone多少钱", "如何评价这部电影？"],
           ["任何人都可以", "如何是好", "哈哈哈哈", "你怎么了", "今天好累"]),
    "zh-TW": (["周杰倫是誰", "這個梗什麼意思", "最新的iPhone多少錢", "這部電影怎麼樣"],
              ["任何人都可以", "哈哈哈哈", "今天好累"]),
    "ja": (["これ何？", "このミームどういう意味", "いつ発売？", "値段いくら"],
           ["おはよう", "疲れたー", "それな", "任何"]),
    "ko": (["이 밈 무슨 뜻이야", "이거 뭐야", "언제 나와?", "가격 얼마야"],
           ["안녕", "피곤해", "ㅋㅋㅋㅋ"]),
    "es": (["¿qué significa rizz?", "¿quién ganó ayer?", "noticias de la serie"],
           ["hola a todos", "estoy cansado", "jajaja"]),
    "fr": (["qui est ce chanteur", "pourquoi il a fait ça", "le prix de la ps5"],
           ["salut tout le monde", "je suis crevé", "mdr"]),
    "de": (["was ist rizz", "wann kommt staffel 2", "warum ist das so teuer"],
           ["guten morgen", "bin müde", "haha"]),
    "pt-BR": (["o que é rizz", "quem ganhou ontem", "quando sai a temporada 2"],
              ["bom dia gente", "tô cansado", "kkkkk"]),
    "ru": (["что значит рофл", "кто выиграл вчера", "когда выйдет второй сезон"],
           ["доброе утро", "я устал", "ахахах"]),
}


def test_the_search_gate_in_every_language() -> None:
    _covers_every_language(_GATE, "search gate")
    for code, (lookups, chatter) in _GATE.items():
        missed = [t for t in lookups if not _SEARCH_HINT_RE.search(t.lower())]
        check(f"{code}: a lookup reaches the decision", missed == [], repr(missed))
        fired = [t for t in chatter if _SEARCH_HINT_RE.search(t.lower())]
        check(f"{code}: chatter spends no decision", fired == [], repr(fired))


# -- E6: a German date ----------------------------------------------------------

def test_a_date_at_the_start_of_a_line_keeps_its_day() -> None:
    for text in ("3. Oktober ist Feiertag\nda hab ich frei", "3. Oktober ist Feiertag",
                 "na klar\n24. Dezember bin ich bei meinen Eltern"):
        check(f"{text!r} is unchanged", TP._sanitize_reply(text, "en") == text,
              repr(TP._sanitize_reply(text, "en")))
    check("a numbered list still loses its numbers",
          TP._sanitize_reply("1. a\n2. b", "en") == "a\nb")
    check("and keeps the line around it",
          TP._sanitize_reply("three things\n1. rice\n2. eggs\n3. tea", "en")
          == "three things\nrice\neggs\ntea")


# -- E7: what the character cannot see -------------------------------------------

@pytest.mark.parametrize("text", [
    "[sticker]", "(sent a voice message)", "(sent a video)", "(sent a file: deck.pdf)",
    "(sent a file)", "(sent a photo)", "(sent an image)", "(sent a sticker)",
    "[AT:42] (sent a voice message)",
    "\x02[file: deck.pdf]\x03", "@TestBot \x02[file: notes (2).txt]\x03",
    "\x02[sticker: 😂]\x03", "\x02[sticker: ❤️]\x03",
])
def test_a_note_for_unseen_media_is_blind(text: str) -> None:
    check(f"{text!r} is blind", TP._is_blind_content(text))


@pytest.mark.parametrize("text", [
    "(voice message) see you at 7", "(sent a voice message) see you at 7",
    "[sticker] lol that's me", "I sent a photo yesterday",
    "\x02[file: deck.pdf]\x03 the slides for monday", "[file: deck.pdf]",
    "\x02[sticker: 😂]\x03 same", "\x02[sticker: laughing cat]\x03",
    "\x02[voice: see you at 7]\x03", "\x02[image: a cat on a sofa]\x03",
])
def test_a_note_with_words_is_not_blind(text: str) -> None:
    check(f"{text!r} is not blind", not TP._is_blind_content(text))
