"""What the character perceives of media, forwards and mentions from each
direct platform: the platform event, through the connector, to the text the
model reads. No network, no accounts."""
from __future__ import annotations

import asyncio
import time

import httpx
import pytest

from helpers import isolated_agent
from persona_agent.connector import synthesize_onebot_payload
from persona_agent.direct import discord, matrix, qq, stoat, telegram, vk, weixin, zulip
from persona_agent.textproc import TextProcessing, _strip_web_desc


def run(coro):
    return asyncio.run(coro) if asyncio.iscoroutine(coro) else coro


def down() -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(500)))


@pytest.fixture(scope="module")
def agent(tmp_path_factory):
    return isolated_agent(tmp_path_factory.mktemp("perceive"))


def perceived(agent, platform: str, event: dict, bot_id: str = "7000") -> str:
    payload = synthesize_onebot_payload(
        {"platform": platform, "bot_id": bot_id, **event}, agent._self_mention_id())
    return asyncio.run(agent._extract_text(payload))


# ---------------------------------------------------------------- fixtures

def tg(**fields) -> dict:
    bot = telegram.Telegram({"telegram_token": "t"}, client=down())
    bot.bot_id, bot.username = "7000", "NovaBot"
    message = {"message_id": 9, "date": 1790000000, "chat": {"id": 42, "type": "private"},
               "from": {"id": 42, "first_name": "Alex"}}
    message.update(fields)
    return run(bot.event(message))


def dc(**fields) -> dict:
    bot = discord.Discord({"discord_token": "t"}, client=down())
    bot.bot_id = "900"
    data = {"id": "55", "channel_id": "300", "content": "", "author": {"id": "42", "username": "alex"},
            "timestamp": "2026-10-14T10:00:00+00:00"}
    data.update(fields)
    return bot.event(data)


def st(**fields) -> dict:
    bot = stoat.Stoat({"stoat_token": "t"}, client=down())
    bot.bot_id = "01BOT"
    bot.channels["C1"] = {"channel_type": "DirectMessage"}
    bot.users["01ALEX"] = {"_id": "01ALEX", "username": "alex"}
    bot.users["01SAM"] = {"_id": "01SAM", "username": "sam", "display_name": "Sam"}
    message = {"_id": "01KDVDNA00" + "0" * 16, "channel": "C1", "author": "01ALEX", "content": ""}
    message.update(fields)
    found = run(bot.event(message))
    return found[0] if found else None


def zl(content: str) -> dict:
    bot = zulip.Zulip({"zulip_site": "https://chat.example.org/", "zulip_email": "b@x",
                       "zulip_api_key": "k"}, client=down())
    bot.bot_id, bot.full_name = "900", "Nova"
    message = {"id": 55, "type": "stream", "stream_id": 12, "subject": "lunch", "sender_id": 42,
               "sender_full_name": "Alex", "timestamp": 1790000000, "content": content,
               "display_recipient": "general"}
    return run(bot.event(message, []))


def vkm(*attachments, **fields) -> dict:
    bot = vk.VK({"vk_token": "t"}, client=down())
    bot.group_id, bot.bot_id = 77, "-77"
    bot.names["42"] = "Alex"
    message = {"id": 0, "conversation_message_id": 31, "date": 1790000000, "peer_id": 42,
               "from_id": 42, "text": "", "attachments": list(attachments), "fwd_messages": []}
    message.update(fields)
    return run(bot.event(message))


def mx(**content) -> dict:
    bot = matrix.Matrix({"matrix_homeserver": "https://example.org", "matrix_token": "t",
                         "matrix_owner": "@kant:example.org"}, client=down())
    bot.bot_id = "@nova:example.org"
    bot.direct.add("!dm:example.org")
    bot.names[("!dm:example.org", "@alex:example.org")] = "Alex"
    source = {"type": "m.room.message", "event_id": "$1", "sender": "@alex:example.org",
              "origin_server_ts": int(time.time() * 1000), "content": content}
    return run(bot.event("!dm:example.org", source))


def wx(tmp_path, *items) -> dict:
    bot = weixin.Weixin({"weixin_oc_token": "bt"}, state=tmp_path / "s.json", client=down())
    return bot.event({"from_user_id": "u1", "message_id": 5, "item_list": list(items)})


def qqm(*attachments) -> dict:
    bot = qq.QQ({"appid": "1", "secret": "s"}, client=down())
    event, _ = bot.event("C2C_MESSAGE_CREATE", {
        "id": "m1", "author": {"user_openid": "U1"}, "content": "", "attachments": list(attachments),
        "timestamp": "2026-10-14T10:00:00+00:00"})
    return event


VOICE_VIDEO = {
    "telegram voice": ("telegram", lambda tmp: tg(voice={"file_id": "v", "duration": 3})),
    "telegram video": ("telegram", lambda tmp: tg(video={"file_id": "v"})),
    "discord voice": ("discord", lambda tmp: dc(flags=8192, attachments=[
        {"filename": "voice-message.ogg", "content_type": "audio/ogg", "duration_secs": 3.1,
         "waveform": "AAA=", "url": "https://cdn.example/v.ogg"}])),
    "discord video": ("discord", lambda tmp: dc(attachments=[
        {"filename": "clip.mp4", "content_type": "video/mp4", "url": "https://cdn.example/c.mp4"}])),
    "stoat video": ("stoat", lambda tmp: st(attachments=[
        {"filename": "clip.mp4", "content_type": "video/mp4", "metadata": {"type": "Video"}}])),
    "zulip video": ("zulip", lambda tmp: zl("[clip.mp4](/user_uploads/2/ab/cd/clip.mp4)")),
    "vk voice": ("vk", lambda tmp: vkm({"type": "audio_message", "audio_message": {"duration": 2}})),
    "vk video": ("vk", lambda tmp: vkm({"type": "video", "video": {"title": "x"}})),
    "matrix voice": ("matrix", lambda tmp: mx(msgtype="m.audio", body="Voice message",
                                              **{"org.matrix.msc3245.voice": {}})),
    "matrix video": ("matrix", lambda tmp: mx(msgtype="m.video", body="clip.mp4", filename="clip.mp4")),
    "weixin voice": ("weixin_oc", lambda tmp: wx(tmp, {"type": 3, "voice_item": {}})),
    "weixin video": ("weixin_oc", lambda tmp: wx(tmp, {"type": 5, "video_item": {}})),
    "qq voice": ("qq_official", lambda tmp: qqm({"content_type": "voice", "filename": "a.silk",
                                                 "url": "https://x.example/a.silk"})),
    "qq video": ("qq_official", lambda tmp: qqm({"content_type": "video/mp4", "filename": "c.mp4",
                                                 "url": "https://x.example/c.mp4"})),
}

FILES = {
    "telegram file": ("telegram", lambda tmp: tg(document={"file_id": "d", "file_name": "deck.pdf"})),
    "discord file": ("discord", lambda tmp: dc(attachments=[
        {"filename": "deck.pdf", "content_type": "application/pdf", "url": "https://cdn.example/d.pdf"}])),
    "stoat file": ("stoat", lambda tmp: st(attachments=[
        {"filename": "deck.pdf", "content_type": "application/pdf", "metadata": {"type": "File"}}])),
    "zulip file": ("zulip", lambda tmp: zl("[deck.pdf](/user_uploads/2/ab/cd/deck.pdf)")),
    "vk file": ("vk", lambda tmp: vkm({"type": "doc", "doc": {"title": "deck.pdf"}})),
    "matrix file": ("matrix", lambda tmp: mx(msgtype="m.file", body="deck.pdf", filename="deck.pdf")),
    "weixin file": ("weixin_oc", lambda tmp: wx(tmp, {"type": 4, "file_item": {"file_name": "deck.pdf"}})),
    "qq file": ("qq_official", lambda tmp: qqm({"content_type": "file", "filename": "deck.pdf",
                                                "url": "https://x.example/d.pdf"})),
}


@pytest.mark.parametrize("case", sorted(VOICE_VIDEO))
def test_voice_and_video_reach_the_model_as_something_it_cannot_see(case, agent, tmp_path):
    platform, make = VOICE_VIDEO[case]
    event = make(tmp_path)
    assert event, f"{case}: the platform event was dropped"
    text = perceived(agent, platform, event)
    assert "(sent" not in text, text
    assert TextProcessing._is_blind_content(text), f"{case}: {text!r}"


@pytest.mark.parametrize("case", sorted(FILES))
def test_a_file_reaches_the_model_by_name_never_as_typed_words(case, agent, tmp_path):
    platform, make = FILES[case]
    event = make(tmp_path)
    assert event, f"{case}: the platform event was dropped"
    text = perceived(agent, platform, event)
    assert "(sent" not in text, text
    assert "[file: deck.pdf]" in text, f"{case}: {text!r}"
    # Fenced: the sender did not type the name.
    assert "deck.pdf" not in _strip_web_desc(text), text


def test_a_nameless_file_and_a_failed_photo_are_blind(agent, tmp_path):
    for platform, event in (("vk", vkm({"type": "doc", "doc": {}})),
                            ("telegram", tg(photo=[{"file_id": "p", "file_size": 10}])),
                            ("weixin_oc", wx(tmp_path, {"type": 2, "image_item": {}}))):
        text = perceived(agent, platform, event)
        assert TextProcessing._is_blind_content(text), (platform, text)


def test_a_transcript_and_a_sticker_emoji_are_fenced_descriptions(agent, tmp_path):
    voice = perceived(agent, "weixin_oc", wx(tmp_path, {"type": 3, "voice_item": {"text": "see you at 7"}}))
    assert "[voice: see you at 7]" in voice and "see you" not in _strip_web_desc(voice), voice
    assert not TextProcessing._is_blind_content(voice)
    vk_voice = perceived(agent, "vk", vkm({"type": "audio_message",
                                           "audio_message": {"transcript": "running late"}}))
    assert "[voice: running late]" in vk_voice, vk_voice
    sticker = perceived(agent, "telegram", tg(sticker={"file_id": "s", "emoji": "😂"}))
    assert "[sticker: 😂]" in sticker and "(sent" not in sticker, sticker


def test_a_forward_is_marked_as_someone_elses_words(agent):
    """A forwarded "I quit" is not the sender quitting, and a Discord forward,
    whose words live in a snapshot, is not dropped."""
    event = tg(text="I quit", forward_origin={"type": "user", "date": 1, "sender_user": {
        "id": 5, "first_name": "Dana"}})
    text = perceived(agent, "telegram", event)
    assert "[forwarded from Dana]" in text and "I quit" in text, text
    assert text.index("[forwarded from Dana]") < text.index("I quit"), text
    hidden = perceived(agent, "telegram", tg(text="hi", forward_origin={
        "type": "hidden_user", "date": 1, "sender_user_name": "Lee"}))
    assert "[forwarded from Lee]" in hidden, hidden
    channel = perceived(agent, "telegram", tg(text="news", forward_origin={
        "type": "channel", "date": 1, "chat": {"id": -1, "title": "Daily"}, "message_id": 3}))
    assert "[forwarded from Daily]" in channel, channel

    event = dc(message_reference={"type": 1, "message_id": "9"}, message_snapshots=[
        {"message": {"content": "I quit", "attachments": [
            {"filename": "deck.pdf", "content_type": "application/pdf", "url": "https://cdn.example/d"}]}}])
    assert event, "a Discord forward was dropped"
    text = perceived(agent, "discord", event, bot_id="900")
    assert "[forwarded]" in text and "I quit" in text and "[file: deck.pdf]" in text, text


def test_mentions_of_other_people_reach_the_model_by_name(agent):
    event = dc(content="<@900> <@81234> what do you think of <#5> and <@&6>", guild_id="1",
               mentions=[{"id": "900", "username": "nova"},
                         {"id": "81234", "username": "sam", "global_name": "Sam",
                          "member": {"nick": "Sammy"}}])
    mention = next(s for s in event["segments"] if s["type"] == "mention" and s["user_id"] == "81234")
    assert mention["name"] == "Sammy", event["segments"]
    text = perceived(agent, "discord", {**event, "conversation_id": "300"}, bot_id="900")
    # Fenced: the mentioned person chose the name, not the sender.
    assert "\x02@Sammy\x03 what do you think of #channel and @role" in text, text
    assert "<@" not in text and "81234" not in text, text

    stoat_event = st(content="ask <@01SAM> about it")
    assert {"type": "mention", "user_id": "01SAM", "name": "Sam"} in stoat_event["segments"]
    assert "ask \x02@Sam\x03 about it" in perceived(agent, "stoat", stoat_event, bot_id="01BOT")


def test_a_named_mention_renders_by_name_and_counts_the_person_present(agent):
    event = {"conversation_type": "group", "conversation_id": "g1", "sender_id": "1",
             "sender_name": "Alex", "message_id": "m1",
             "segments": [{"type": "mention", "user_id": "55", "name": "Sam"},
                          {"type": "text", "text": "you there?"}]}
    assert perceived(agent, "telegram", event) == "\x02@Sam\x03 you there?"
    assert ("telegram:55", "Sam") in agent.active_users["telegram:g1"]
    nameless = dict(event, segments=[{"type": "mention", "user_id": "56"}])
    assert perceived(agent, "telegram", nameless) == "@telegram:56"
    # Another member named after the character is not a call to it.
    namesake = dict(event, segments=[{"type": "mention", "user_id": "57", "name": "TestBot fan"}])
    assert perceived(agent, "telegram", namesake) == "@telegram:57"


def test_a_quote_keeps_two_hundred_characters(agent):
    quoted = "".join(f"w{i:03d} " for i in range(60))      # 300 characters
    event = {"conversation_type": "group", "conversation_id": "g2", "sender_id": "1",
             "sender_name": "Alex", "message_id": "m2",
             "segments": [{"type": "reply", "message_id": "q9", "text": quoted, "sender_name": "Eve"},
                          {"type": "text", "text": " agreed"}]}
    text = perceived(agent, "telegram", event)
    assert f"Eve: {quoted.strip()[:200]}" in text and quoted.strip()[:201] not in text, text


def test_a_quote_fetched_from_napcat_keeps_two_hundred_characters(agent, monkeypatch):
    raw = "x" * 300

    class Reply:
        def json(self):
            return {"data": {"sender": {"nickname": "Eve"}, "raw_message": raw}}

    class Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def post(self, url, json):
            return Reply()
    monkeypatch.setattr(agent, "qq_onebot_url", "http://127.0.0.1:9")
    monkeypatch.setattr(agent, "_local_http", lambda timeout: Client())
    assert asyncio.run(agent._resolve_quote("12345")) == "Eve: " + "x" * 200


def test_a_caption_still_reads_as_the_senders_words(agent):
    text = perceived(agent, "telegram", tg(video={"file_id": "v"}, caption="look at this"))
    assert "look at this" in _strip_web_desc(text) and "[video]" in text, text
