"""The vendor self-identification guard, per chat language: what it catches
and the ordinary replies it must let through (star signs, names that only
contain a vendor, sentences about a product someone else made)."""
from __future__ import annotations

import pytest

from persona_agent import chatlangs
from persona_agent.textproc import TextProcessing as TP, _names_its_own_vendor

_HARMLESS = {
    "en": ["I'm a Gemini, so yeah, two moods", "I'm trying to grok this",
           "I'm talking to ChatGPT about it", "I'm on ChatGPT all day",
           "I'm using Claude for my essay", "I'm a big fan of OpenAI",
           "I'm a little tired of ChatGPT", "I'm Kimiko, nice to meet you",
           "as a kid ChatGPT didn't exist", "I'm a ChatGPT user myself",
           "I'm not ChatGPT, I'm Mira"],
    "zh": ["我是觉得ChatGPT挺好用的", "我叫Kimi帮我查了一下", "我是ChatGPT的重度用户",
           "我是从Kimi那看到的", "我是昨天才开始用Gemini的", "我是双子座，所以善变",
           "我是Kimiko的朋友", "我昨天看了由OpenAI开发的Sora", "我是说deepseek那个接口挺好用的"],
    "zh-TW": ["我是覺得ChatGPT挺好用的", "我叫Kimi幫我查了一下", "我是ChatGPT的重度用戶",
              "我是從Kimi那看到的", "我是雙子座，所以善變", "我是Kimiko的朋友",
              "我昨天看了由OpenAI開發的Sora", "我是說deepseek那個介面很好用"],
    "ja": ["私はOpenAIが開発したSoraを使ってみた", "私はGoogle製のGemini使ってる",
           "私はChatGPTを毎日使う", "私はClaudeが好きです", "私はKimikoです",
           "私はOpenAIが作ったアプリが好きです", "私は双子座です",
           "僕はGeminiよりClaude派", "私はChatGPTじゃないよ"],
    "ko": ["난 OpenAI가 만든 소라 써봤어", "나는 ChatGPT를 매일 써", "저는 Claude가 더 좋아요",
           "난 쌍둥이자리야", "나는 OpenAI 뉴스를 봤어", "저는 ChatGPT가 아니에요",
           "내가 Gemini한테 물어봤어", "전 Kimiko예요", "난 OpenAI가 만든 소라가 최고야"],
    "es": ["Soy geminiano, ya sabes cómo somos", "Soy llamativa, lo sé",
           "Soy de Madrid y uso un modelo creado por Mistral", "Soy fan de ChatGPT",
           "No soy ChatGPT, soy Mira", "Soy géminis, así que cambio de idea",
           "Soy usuaria de Claude desde hace un año", "Soy muy de usar ChatGPT para todo",
           "Soy grokero total"],
    "pt-BR": ["Sou geminiana, então mudo de ideia toda hora", "Sou grokeira? kkk",
              "Eu sou fã da OpenAI", "Não sou o ChatGPT, sou a Mira",
              "Sou de São Paulo e uso um modelo criado pela OpenAI",
              "Sou viciada no ChatGPT", "Sou usuário do Claude faz tempo",
              "Sou mais Gemini do que ChatGPT", "Sou kimiana de carteirinha"],
    "fr": ["Je suis fan de Mistral, créé par des Français", "Je suis pas ChatGPT",
           "Je suis sur ChatGPT toute la journée", "Je suis Gémeaux, donc lunatique",
           "Je suis mistralienne de cœur", "Je suis allé voir un modèle créé par OpenAI",
           "Je suis utilisatrice de Claude", "Je suis grokophile", "Je suis Kimiko"],
    "de": ["Ich bin Kimis Schwester",
           "Ich bin gespannt auf das neue Modell, entwickelt von OpenAI",
           "Ich bin nicht ChatGPT, ich bin Mira", "Ich bin ein großer Fan von ChatGPT",
           "Ich bin Zwilling, also launisch", "Ich bin Mistral-Fan seit Tag eins",
           "Ich bin heute mit ChatGPT fertig geworden", "Ich bin Nutzerin von Claude",
           "Ich bin Kimiko"],
    "ru": ["Я читал про модель, созданную OpenAI", "Я — Мистраль? нет, я Мира",
           "Я не ChatGPT, я Мира", "Я устал от ChatGPT", "Я фанат Claude",
           "Я пользователь Gemini уже год", "Я спросил у ChatGPT",
           "Я близнец по гороскопу", "Я гуглю всё в ChatGPT"],
}

_CLAIMS = {
    "en": ["I'm ChatGPT, made by OpenAI", "I am a language model trained by OpenAI",
           "I'm actually Claude", "I am DeepSeek-V3", "I'm an AI assistant from Anthropic",
           "As a DeepSeek model, I can't do that"],
    "zh": ["我是ChatGPT", "我就是Claude", "我是一个由OpenAI开发的语言模型",
           "我叫Kimi，很高兴认识你", "我是基于GPT-4的AI助手",
           "作为DeepSeek训练的语言模型，我可以回答"],
    "zh-TW": ["我是ChatGPT", "我就是Claude", "我是一個由OpenAI開發的語言模型",
              "我是基於GPT-4的AI助手"],
    "ja": ["私はChatGPTです", "僕はAnthropicによって開発されたClaudeです",
           "私はOpenAI製のAIです", "私はClaudeと申します",
           "私はOpenAIが開発した言語モデルです"],
    "ko": ["저는 OpenAI가 만든 ChatGPT입니다", "저는 Anthropic에서 개발한 Claude예요",
           "나는 ChatGPT야", "저는 Claude입니다"],
    "es": ["Soy ChatGPT, creado por OpenAI", "Soy un modelo de lenguaje creado por OpenAI",
           "Soy un asistente de OpenAI", "Yo soy Claude",
           "Soy una IA desarrollada por Anthropic"],
    "pt-BR": ["Sou o ChatGPT, da OpenAI", "Eu sou um modelo criado pela OpenAI",
              "Sou uma IA desenvolvida pela Anthropic", "Eu sou o Claude",
              "Sou um assistente da OpenAI"],
    "fr": ["Je suis ChatGPT, créé par OpenAI", "Je suis un assistant développé par Anthropic",
           "Je suis un modèle d'OpenAI", "Je suis Claude", "Je suis une IA créée par Mistral"],
    "de": ["Ich bin ChatGPT von OpenAI", "Ich bin ein Sprachmodell, entwickelt von OpenAI",
           "Ich bin Claude", "Ich bin ein KI-Assistent von Anthropic",
           "Ich bin ein Modell von Mistral"],
    "ru": ["Я ChatGPT от OpenAI", "Я языковая модель, разработанная OpenAI", "Я Claude",
           "Я ассистент от Anthropic", "Я нейросеть, созданная OpenAI"],
}


def test_every_language_has_both_lists() -> None:
    assert set(_HARMLESS) == set(chatlangs.CODES) == set(_CLAIMS)
    assert all(len(v) >= 8 for v in _HARMLESS.values())
    assert all(len(v) >= 4 for v in _CLAIMS.values())


@pytest.mark.parametrize("code,text", [(c, t) for c, ts in _HARMLESS.items() for t in ts])
def test_an_ordinary_reply_is_sent(code: str, text: str) -> None:
    assert not _names_its_own_vendor(text), f"{code}: {text!r}"
    out, why = TP._sanitize_reply_with_reason(text, "en")
    assert why != "vendor_self_id", f"{code}: {text!r}"


@pytest.mark.parametrize("code,text", [(c, t) for c, ts in _CLAIMS.items() for t in ts])
def test_a_self_identification_is_caught(code: str, text: str) -> None:
    assert _names_its_own_vendor(text), f"{code}: {text!r}"
