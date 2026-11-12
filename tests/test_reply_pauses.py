"""A full stop, an ellipsis and a long dash are not sent by the default style;
what they separated must still read as separate."""
from __future__ import annotations

import pytest

from persona_agent.textproc import MAX_REPLY_MESSAGES, ReplyStyle
from persona_agent.textproc import TextProcessing as TP


def test_both_style_guides_ask_for_text_that_reads_easily():
    from persona_agent import prompts

    for guide in (prompts.STYLE_GUIDE, prompts.dm_style_guide(prompts.PersonaStyle())):
        assert prompts._EASY_TO_READ in guide
        # After the length rule it refines, before the scenes it applies to.
        assert (guide.index("[LENGTH HAS RHYTHM]") < guide.index("[EASY TO READ")
                < guide.index("[EMOTIONAL SCENES"))
        # The quoted examples are moves, not wording: stated where the language is chosen.
        assert guide.index("[LANGUAGE]") < guide.index(prompts._OWN_WORDS_LINE) < guide.index("[FORMAT")
    # The stock replies other rules tell it to send stay allowed.
    assert "'mhm'" in prompts._OWN_WORDS_LINE and "catchphrases" in prompts._OWN_WORDS_LINE


def messages(raw: str, lang: str = "zh") -> list[str]:
    clean = TP._sanitize_reply(raw, lang)
    return [value for _kind, value in
            TP._delivery_units(TP._parse_sticker_markers(clean), MAX_REPLY_MESSAGES)]


def test_long_sentences_that_ended_in_a_full_stop_are_not_run_into_one_message():
    assert messages("复利就是利滚利。比如你存了一万块，年利率百分之五，第一年利息是五百，第二年按一万零五百算。"
                    "时间越长，差距越大，所以大家都说要早点开始存钱。") == [
        "复利就是利滚利",
        "比如你存了一万块，年利率百分之五，第一年利息是五百，第二年按一万零五百算",
        "时间越长，差距越大，所以大家都说要早点开始存钱"]


def test_short_sentences_still_share_a_line():
    assert messages("好。那就这样。") == ["好 那就这样"]
    assert messages("这部我看过。节奏比较慢，但后劲很大。你要是喜欢安静的片子可以试试。") == [
        "这部我看过 节奏比较慢，但后劲很大 你要是喜欢安静的片子可以试试"]
    assert messages("それは大変でしたね。今日はゆっくり休んでください。明日また話しましょう。", "ja") == [
        "それは大変でしたね 今日はゆっくり休んでください 明日また話しましょう"]


def test_a_reply_gains_three_lines_at_most_from_its_full_stops():
    sentence = "这是一句长度正好超过二十个字的普通句子用来凑数"
    one = "。".join(f"{sentence}{n}号" for n in range(9)) + "。"
    clean = TP._sanitize_reply(one, "zh")
    lines = clean.split("\n")
    assert len(lines) == 4
    # The sentences past the fourth are folded into it, none is lost.
    assert all(f"{n}号" in clean for n in range(9))
    assert lines[3].count(sentence) == 6
    # The limit is for the whole reply: three paragraphs are three lines to begin with.
    paragraphs = "\n".join("。".join(f"{sentence}{p}{n}号" for n in range(4)) + "。" for p in "甲乙丙")
    assert len(TP._sanitize_reply(paragraphs, "zh").split("\n")) == 6


@pytest.mark.parametrize("raw, want", [
    # A closing mark stays with the sentence it closes.
    ("他说“好。”然后就走了，头也没回，我在原地站了很久很久很久，直到天都黑了才回去。",
     '他说"好 "然后就走了，头也没回，我在原地站了很久很久很久，直到天都黑了才回去'),
    # A decimal written with the full stop is a number.
    ("圆周率是3。14左右", "圆周率是3。14左右"),
    # The author's own line breaks are kept as they are.
    ("在呢。\n刚在厨房切菜。", "在呢\n刚在厨房切菜"),
])
def test_what_is_not_a_sentence_end_is_left_alone(raw, want):
    assert TP._sanitize_reply(raw, "zh") == want


@pytest.mark.parametrize("raw, lang, want", [
    ("这也太惨了吧……不过没事，下次肯定行！", "zh", "这也太惨了吧，不过没事，下次肯定行！"),
    ("真的吗……？", "zh", "真的吗？"),
    # Before a sticker, an emoji or a bracket there is no word to pause for.
    ("嗯…[STICKER:哭]你别这样", "zh", "嗯[STICKER:哭]你别这样"),
    ("唉……😢", "zh", "唉"),
    ("うーん…😅", "ja", "うーん"),
    ("好吧，…然后呢", "zh", "好吧，然后呢"),
    # Kanji with no kana beside it is still Japanese in a Japanese chat.
    ("日本語…English", "ja", "日本語、English"),
    ("算了……", "zh", "算了"),
    # Japanese pauses with its own comma, Korean and Latin text with three dots.
    ("そうだね…でも明日にしよう", "ja", "そうだね、でも明日にしよう"),
    ("本当…でも行く", "ja", "本当、でも行く"),
    ("그래… 알겠어", "ko", "그래... 알겠어"),
    ("음…", "ko", "음..."),
    ("well… I guess so", "en", "well... I guess so"),
    ("idk…", "en", "idk..."),
])
def test_an_ellipsis_between_words_stays_a_pause(raw, lang, want):
    assert TP._sanitize_reply(raw, lang) == want


def test_a_persona_that_keeps_the_ellipsis_keeps_it_between_words_too():
    keeps = ReplyStyle(charsets=frozenset({"ellipsis"}))
    assert TP._sanitize_reply("这也太惨了吧……不过没事", "zh", keeps) == "这也太惨了吧……不过没事"


@pytest.mark.parametrize("raw, lang, want", [
    ("I'd take it — Berlin is great", "en", "I'd take it, Berlin is great"),
    ("我觉得比第一部好看——尤其是沙虫那场戏", "zh", "我觉得比第一部好看，尤其是沙虫那场戏"),
    ("再想想——超时和重试要不要拆开", "zh", "再想想，超时和重试要不要拆开"),
    ("それは——違う", "ja", "それは、違う"),
    ("그건 — 아니야", "ko", "그건, 아니야"),
    # One tight dash between Chinese words is a route or a range, not a pause.
    ("北京—上海的高铁很快", "zh", "北京 上海的高铁很快"),
    # Between numbers it is a range.
    ("1949—2024年的变化", "zh", "1949-2024年的变化"),
    ("pages 3—5", "en", "pages 3-5"),
    # Elsewhere one tight dash is a pause only in the Latin scripts.
    ("sit down—soup is ready", "en", "sit down, soup is ready"),
    ("서울—부산", "ko", "서울 부산"),
    ("Москва—Петербург", "ru", "Москва Петербург"),
    ("ладно — посмотрим", "ru", "ладно, посмотрим"),
    ("東京——大阪", "ja", "東京、大阪"),
    # Before a sticker or an emoji it separates nothing.
    ("等一下——[STICKER:惊]", "zh", "等一下 [STICKER:惊]"),
    ("我——😳", "zh", "我"),
    # At the end of a line it separates nothing.
    ("你这个——", "zh", "你这个"),
    # Beside another mark it adds nothing.
    ("wait, — what", "en", "wait, what"),
])
def test_a_long_dash_between_words_becomes_the_pause_it_was(raw, lang, want):
    assert TP._sanitize_reply(raw, lang) == want


def test_the_new_pauses_change_nothing_on_a_second_pass():
    for raw, lang in (("复利就是利滚利。比如你存了一万块，年利率百分之五，第一年利息是五百，第二年按一万零五百算。", "zh"),
                      ("そうだね…でも明日にしよう。それは——違う。", "ja"),
                      ("well… I'd take it — Berlin is great", "en")):
        once = TP._sanitize_reply(raw, lang)
        assert TP._sanitize_reply(once, lang) == once
