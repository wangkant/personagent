"""A stand-in for YouTube, YouTube Studio and Google's sign-in, for the YouTube
platform's tests. The public parts (the top bar signed out, a video's page
opened at a comment, the comment rows and the data the page loads them from)
copy the real pages' element names, nesting, attributes and words; the parts
behind a sign-in (the bell, the account menu, the reply box, Studio) follow
how the signed-in site is built."""
from __future__ import annotations

import base64
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, quote, urlsplit

WORDS = {
    "zh": {"lang": "zh-Hans-CN", "hl": "zh-CN", "reply": "回复", "box": "添加回复…", "cancel": "取消",
           "bell": "通知", "avatar": "帐号菜单", "sign_in": "登录", "settings": "设置",
           "linked": "所要查看的评论", "linked_reply": "所要查看的回复", "ago": "1 分钟前",
           "join": "想要加入对话？", "join_more": "登录后才能继续", "replies": "条回复", "your_channel": "你的频道", "empty": "你的通知会显示在这里"},
    "en": {"lang": "en", "hl": "en", "reply": "Reply", "box": "Add a reply…", "cancel": "Cancel",
           "bell": "Notifications", "avatar": "Account menu", "sign_in": "Sign in", "settings": "Settings",
           "linked": "Highlighted comment", "linked_reply": "Highlighted reply", "ago": "1 minute ago",
           "join": "Want to join the conversation?", "join_more": "Sign in to continue", "replies": "replies",
           "your_channel": "Your channel", "empty": "Your notifications live here"},
}

SHELL = """<!doctype html><html lang="%(lang)s"><head><meta charset="utf-8"><title>%(title)s</title>
<style>
ytd-app, ytd-app div, ytd-masthead, ytd-popup-container, tp-yt-iron-dropdown, ytd-multi-page-menu-renderer,
ytd-notification-renderer, ytd-comments, ytd-item-section-renderer, ytd-comment-thread-renderer,
ytd-comment-view-model, ytd-comment-replies-renderer, yt-sub-thread, ytd-expander, ytd-comment-engagement-bar,
ytd-comment-reply-dialog-renderer, ytd-commentbox, ytd-watch-metadata, ytcp-app, ytcp-comment-thread,
ytcp-comment { display: block; }
[hidden] { display: none !important; }
#player { height: 1400px; background: #111; }
tp-yt-iron-dropdown { position: fixed; top: 56px; right: 16px; background: #fff; z-index: 5; padding: 8px; }
[contenteditable] { min-height: 24px; border-bottom: 1px solid #888; }
</style></head><body>%(body)s
<script>window.ytcfg = {data_: %(cfg)s, get(k) { return this.data_[k]; }};</script>
<script>%(script)s</script></body></html>"""

MASTHEAD_OUT = """<ytd-masthead><div id="end" class="style-scope ytd-masthead"><div id="buttons" class="style-scope ytd-masthead">
<ytd-topbar-menu-button-renderer class="style-scope ytd-masthead style-default"><div id="button"><a class="yt-simple-endpoint" tabindex="-1">
<yt-icon-button id="button"><button id="button" class="style-scope yt-icon-button" aria-label="%(settings)s">&#9881;</button></yt-icon-button></a></div></ytd-topbar-menu-button-renderer>
<ytd-button-renderer class="style-scope ytd-masthead" button-renderer="" button-next=""><yt-button-shape>
<a href="%(accounts)s/ServiceLogin?service=youtube&amp;uilel=3&amp;passive=true&amp;hl=%(hl)s&amp;ec=65620" rel="nofollow" class="ytSpecButtonShapeNextHost" aria-label="%(sign_in)s">
<div class="ytSpecButtonShapeNextButtonTextContent"><span class="ytAttributedStringHost" role="text">%(sign_in)s</span></div></a>
</yt-button-shape></ytd-button-renderer></div></div></ytd-masthead>"""

MASTHEAD_IN = """<ytd-masthead><div id="end" class="style-scope ytd-masthead"><div id="buttons" class="style-scope ytd-masthead">
<ytd-notification-topbar-button-renderer class="style-scope ytd-masthead"><yt-icon-button id="button">
<button id="button" class="style-scope yt-icon-button" aria-label="%(bell)s">&#128276;</button></yt-icon-button></ytd-notification-topbar-button-renderer>
<ytd-topbar-menu-button-renderer class="style-scope ytd-masthead style-default"><button id="avatar-btn" aria-label="%(avatar)s" aria-haspopup="true">R</button></ytd-topbar-menu-button-renderer>
</div></div></ytd-masthead>"""

POPUP = """<ytd-popup-container><tp-yt-iron-dropdown aria-hidden="true" hidden><div id="contentWrapper"></div></tp-yt-iron-dropdown></ytd-popup-container>"""

TOP_SCRIPT = r"""
const W = %(words)s;
const drop = document.querySelector('ytd-popup-container tp-yt-iron-dropdown');
function closeDrop() { drop.hidden = true; drop.setAttribute('aria-hidden', 'true'); drop.firstElementChild.innerHTML = ''; }
function openDrop(html) { drop.firstElementChild.innerHTML = html; drop.hidden = false; drop.removeAttribute('aria-hidden'); }
document.addEventListener('keydown', e => { if (e.key === 'Escape') closeDrop(); });
async function post(path, body) {
  return (await fetch(path, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body || {})})).json();
}
function text(v) { return v ? (v.simpleText || (v.runs || []).map(r => r.text).join('') || v.content || '') : ''; }
const bell = document.querySelector('ytd-notification-topbar-button-renderer button');
if (bell) bell.onclick = async () => {
  const data = await post('/youtubei/v1/notification/get_notification_menu', {notificationsMenuRequestType: 'NOTIFICATIONS_MENU_REQUEST_TYPE_INBOX'});
  const items = data.actions[0].openPopupAction.popup.multiPageMenuRenderer.sections[0].multiPageMenuNotificationSectionRenderer.items;
  const menu = document.createElement('ytd-multi-page-menu-renderer');
  for (const it of items) {
    const n = it.notificationRenderer; if (!n) continue;
    const row = document.createElement('ytd-notification-renderer');
    const a = document.createElement('a'); a.className = 'yt-simple-endpoint';
    a.href = n.navigationEndpoint.commandMetadata.webCommandMetadata.url;
    const msg = document.createElement('yt-formatted-string'); msg.className = 'message'; msg.textContent = text(n.shortMessage);
    a.append(msg); row.append(a); menu.append(row);
  }
  if (!menu.children.length) menu.innerHTML = '<div id="empty">' + W.empty + '</div>';
  openDrop(''); drop.firstElementChild.append(menu);
};
const avatar = document.querySelector('#avatar-btn');
if (avatar) avatar.onclick = async () => {
  const data = await post('/youtubei/v1/account/account_menu', {});
  const h = data.actions[0].openPopupAction.popup.multiPageMenuRenderer.header.activeAccountHeaderRenderer;
  openDrop(''); const menu = document.createElement('ytd-multi-page-menu-renderer');
  menu.innerHTML = '<ytd-active-account-header-renderer><yt-formatted-string id="account-name"></yt-formatted-string></ytd-active-account-header-renderer>';
  menu.querySelector('#account-name').textContent = text(h.accountName);
  drop.firstElementChild.append(menu);
};
"""

WATCH_BODY = """<ytd-app>%(masthead)s%(popup)s<div id="player"></div>
<ytd-watch-metadata><div id="title"><h1 class="style-scope ytd-watch-metadata"><yt-formatted-string>%(title)s</yt-formatted-string></h1></div></ytd-watch-metadata>
<ytd-comments id="comments" class="style-scope ytd-watch-flexy"><ytd-item-section-renderer id="sections"><div id="header"></div><div id="contents"></div></ytd-item-section-renderer></ytd-comments>
<div style="height:1600px"></div></ytd-app>"""

WATCH_SCRIPT = r"""
const VIDEO = %(video)s, LINKED = %(lc)s, SIGNED_IN = %(signed_in)s, LAYOUT = %(layout)s;
function rowHtml(c, linked) {
  const badge = linked ? `<ytd-badge-supported-renderer><yt-badge-supported-renderer class="ytBadgeSupportedRendererHost"><div class="badge-shape"><yt-metadata-badge-renderer><badge-shape class="ytBadgeShapeHost" role="img" aria-label="${c.replyLevel ? W.linked_reply : W.linked}"><div class="ytBadgeShapeText" aria-hidden="true">${c.replyLevel ? W.linked_reply : W.linked}</div></badge-shape></yt-metadata-badge-renderer></div></yt-badge-supported-renderer></ytd-badge-supported-renderer>` : '';
  const reply = LAYOUT !== 2
    ? `<ytd-button-renderer id="${LAYOUT === 1 ? 'reply-button-end' : 'reply-action'}" force-icon-button="true" class="style-scope ytd-comment-engagement-bar" button-renderer="" button-next=""><yt-button-shape><button class="ytSpecButtonShapeNextHost ytSpecButtonShapeNextText" title="" aria-label="${W.reply}"><div class="ytSpecButtonShapeNextButtonTextContent"><span class="ytAttributedStringHost" role="text">${W.reply}</span></div></button></yt-button-shape></ytd-button-renderer>`
    : `<ytd-button-renderer id="respond-end" class="style-scope ytd-comment-engagement-bar"><yt-button-shape><button class="ytSpecButtonShapeNextHost" aria-label="Write back"><div class="ytSpecButtonShapeNextButtonTextContent"><span role="text">Write back</span></div></button></yt-button-shape></ytd-button-renderer>`;
  return `<div id="paid-comment-background" class="style-scope ytd-comment-view-model"></div>
<div id="linked-comment-badge" class="style-scope ytd-comment-view-model">${badge}</div>
<div id="body" class="style-scope ytd-comment-view-model"><div id="author-thumbnail"><button id="author-thumbnail-button" aria-label=""></button></div>
<div id="main" class="style-scope ytd-comment-view-model"><div id="header"><div id="pinned-comment-badge"></div><div id="header-author">
<h3><a class="yt-simple-endpoint style-scope ytd-comment-view-model" id="author-text" href=""><span></span></a></h3>
<span dir="auto" id="published-time-text" class="style-scope ytd-comment-view-model"><a class="yt-simple-endpoint style-scope ytd-comment-view-model" href="/watch?v=${VIDEO}&lc=${c.id}">${c.publishedTime}</a></span></div></div>
<ytd-expander id="expander" max-number-of-lines="4" class="style-scope ytd-comment-view-model"><div id="content" class="style-scope ytd-expander"><yt-attributed-string slot="content" id="content-text" class="style-scope ytd-comment-view-model"><span class="ytAttributedStringHost ytAttributedStringWhiteSpacePreWrap" dir="auto" role="text"></span></yt-attributed-string></div></ytd-expander>
<ytd-comment-engagement-bar id="action-buttons" class="style-scope ytd-comment-view-model"><div id="toolbar" class="style-scope ytd-comment-engagement-bar">
<ytd-toggle-button-renderer id="like-button"><yt-button-shape><button aria-pressed="false" aria-label="like"></button></yt-button-shape></ytd-toggle-button-renderer>
<span id="vote-count-middle"></span><div id="creator-heart"></div>${reply}</div>
<div id="reply-dialog" class="style-scope ytd-comment-engagement-bar"></div></ytd-comment-engagement-bar></div></div>`;
}
function makeRow(c, linked) {
  const m = document.createElement('ytd-comment-view-model');
  if (!c.replyLevel) m.id = 'comment';
  m.className = 'style-scope ytd-comment-thread-renderer';
  for (const a of ['use-small-avatars', 'comment-threading-enabled', 'web-watch-compact-comments']) m.setAttribute(a, '');
  if (linked) m.setAttribute('linked', '');
  if (c.replyLevel) m.setAttribute('is-reply', '');
  m.innerHTML = rowHtml(c, linked);
  m.querySelector('#author-text').setAttribute('href', c.authorUrl);
  m.querySelector('#author-text span').textContent = ' ' + c.author + ' ';
  m.querySelector('#author-thumbnail-button').setAttribute('aria-label', c.author);
  m.querySelector('#content-text span').textContent = c.text;
  const open = m.querySelector('ytd-comment-engagement-bar ytd-button-renderer button');
  open.onclick = () => openReply(m, c);
  return m;
}
function openReply(m, c) {
  if (!SIGNED_IN) { openDrop(`<div>${W.join}</div><div>${W.join_more}</div><a href="/accounts/ServiceLogin">${W.sign_in}</a>`); return; }
  const dialog = m.querySelector('#reply-dialog');
  if (dialog.querySelector('ytd-commentbox')) return;
  const editor = LAYOUT !== 2
    ?`<div id="contenteditable-root" contenteditable="true" class="style-scope yt-formatted-string" aria-label="${W.box}" role="textbox" aria-multiline="true"></div>`
    : `<div id="editor-q" contenteditable="true" aria-label="Your answer" role="textbox"></div>`;
  dialog.innerHTML = `<ytd-comment-reply-dialog-renderer><ytd-commentbox id="commentbox" class="style-scope ytd-comment-reply-dialog-renderer">
<div id="main"><div id="creation-box"><yt-formatted-string id="contenteditable-textarea">${editor}</yt-formatted-string></div>
<div id="footer"><div id="buttons">
<ytd-button-renderer id="cancel-button"><yt-button-shape><button aria-label="${W.cancel}"><span role="text">${W.cancel}</span></button></yt-button-shape></ytd-button-renderer>
<ytd-button-renderer id="submit-button"><yt-button-shape><button aria-label="${W.reply}" aria-disabled="true" disabled><span role="text">${W.reply}</span></button></yt-button-shape></ytd-button-renderer>
</div></div></div></ytd-commentbox></ytd-comment-reply-dialog-renderer>`;
  const box = dialog.querySelector('[contenteditable]');
  const send = dialog.querySelector('#submit-button button');
  if (c.replyLevel) box.textContent = c.author + ' ';
  box.addEventListener('input', () => { const empty = !box.innerText.trim(); send.disabled = empty; send.setAttribute('aria-disabled', String(empty)); });
  dialog.querySelector('#cancel-button button').onclick = () => { dialog.innerHTML = ''; };
  send.onclick = async () => {
    if (send.disabled) return;
    const top = c.id.split('.')[0];
    const made = await post('/youtubei/v1/comment/create_comment_reply', {videoId: VIDEO, parent: c.id, commentText: box.innerText});
    dialog.innerHTML = '';
    const thread = m.closest('ytd-comment-thread-renderer');
    const host = thread.querySelector('#expanded-threads') || thread;
    host.append(makeRow(made.comment, false));
  };
}
function thread(top, replies, linkedId) {
  const t = document.createElement('ytd-comment-thread-renderer');
  t.className = 'style-scope ytd-item-section-renderer';
  t.innerHTML = '<div id="comment-container" class="style-scope ytd-comment-thread-renderer"></div><div id="replies" class="style-scope ytd-comment-thread-renderer"><ytd-comment-replies-renderer modern="" comment-threading-enabled=""><div id="expander" hidden></div><div id="teaser-replies" hidden></div><div id="collapsed-threads" hidden></div><div id="expanded-threads"></div></ytd-comment-replies-renderer></div>';
  t.querySelector('#comment-container').append(makeRow(top, top.id === linkedId));
  for (const r of replies) {
    const sub = document.createElement('yt-sub-thread');
    const inner = document.createElement('ytd-comment-thread-renderer');
    inner.innerHTML = '<div id="comment-container"></div>';
    inner.firstElementChild.append(makeRow(r, r.id === linkedId));
    sub.append(inner); t.querySelector('#expanded-threads').append(sub);
  }
  return t;
}
let loaded = false;
const watcher = new IntersectionObserver(async (seen) => {
  if (loaded || !seen.some(e => e.isIntersecting)) return;
  loaded = true;
  const data = await post('/youtubei/v1/next', {continuation: 'comments-section', videoId: VIDEO, lc: LINKED});
  const byId = {};
  for (const m of data.frameworkUpdates.entityBatchUpdate.mutations) {
    const p = m.payload.commentEntityPayload; if (!p) continue;
    byId[p.properties.commentId] = {id: p.properties.commentId, text: p.properties.content.content, replyLevel: p.properties.replyLevel,
      publishedTime: p.properties.publishedTime, author: p.author.displayName,
      authorUrl: p.author.channelCommand.innertubeCommand.commandMetadata.webCommandMetadata.url};
  }
  const contents = document.querySelector('ytd-comments #contents');
  for (const e of data.onResponseReceivedEndpoints) {
    const items = (e.reloadContinuationItemsCommand || e.appendContinuationItemsAction || {}).continuationItems || [];
    for (const it of items) {
      const tr = it.commentThreadRenderer; if (!tr) continue;
      const top = byId[tr.commentViewModel.commentViewModel.commentId];
      const shown = (tr.shownReplies || []).map(id => byId[id]);
      contents.append(thread(top, shown, LINKED));
    }
  }
}, {rootMargin: '0px'});
watcher.observe(document.querySelector('ytd-comments'));
"""

STUDIO_BODY = """<ytcp-app><div id="main"><ytcp-comments-section><div id="threads"></div></ytcp-comments-section></div></ytcp-app>"""

STUDIO_SCRIPT = r"""
(async () => {
  const data = await (await fetch('/youtubei/v1/comment/get_comments?alt=json', {method: 'POST', body: '{}'})).json();
  const host = document.querySelector('#threads');
  for (const c of data.comments || []) {
    const t = document.createElement('ytcp-comment-thread');
    t.innerHTML = '<ytcp-comment><div id="header"><a id="name" class="author"></a><a id="published-time-text"></a></div><yt-formatted-string id="content-text"></yt-formatted-string></ytcp-comment>';
    t.querySelector('#name').textContent = c.authorText.simpleText;
    t.querySelector('#published-time-text').href = %(www)s + '/watch?v=' + c.videoId + '&lc=' + c.commentId;
    t.querySelector('#published-time-text').textContent = W.ago;
    t.querySelector('#content-text').textContent = c.content.runs[0].text;
    host.append(t);
  }
})();
"""


def packed(comment: str) -> str:
    """A watch link's `params` pointing at `comment`, packed as the real page packs it."""
    raw = bytes([0x7A, len(comment)]) + comment.encode() + bytes.fromhex("a20203c00100")
    return quote(base64.urlsafe_b64encode(raw).decode(), safe="")


class Site:
    def __init__(self, lang: str = "zh") -> None:
        self.lang = lang
        self.accounts = {"UCrobin0000000000000000": ("Robin", "@robin")}
        self.videos: dict[str, dict] = {}
        self.comments: dict[str, dict] = {}
        self.notifications: list[dict] = []
        self.replies: list[dict] = []
        self.layout = 1
        self.wall = False
        self.signed_out = False
        self.seq = 0
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), self._handler())
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def close(self) -> None:
        self.server.shutdown()
        self.server.server_close()

    # -- what happens on the site

    def video(self, ident: str, title: str, owner: str = "UCrobin0000000000000000") -> None:
        self.videos[ident] = {"title": title, "owner": owner}

    def _id(self) -> str:
        self.seq += 1
        return f"UgzStandin{self.seq:04d}xYz4AaABAg"

    def comment(self, video: str, text: str, *, by: str = "UCkim00000000000000000", name: str = "@kim",
                notify: bool = True) -> str:
        """A top-level comment; one on the account's own video shows in Studio and as a notification."""
        ident = self._id()
        self.comments[ident] = {"id": ident, "video": video, "text": text, "by": by, "name": name, "parent": ""}
        if notify and self.videos[video]["owner"] in self.accounts and by not in self.accounts:
            self.notifications.insert(0, {"video": video, "comment": ident, "message": f"{name} 发表了评论：{text}",
                                          "packed_only": False})
        return ident

    def reply(self, parent: str, text: str, *, by: str = "UCkim00000000000000000", name: str = "@kim",
              notify: bool = True, packed_only: bool = False) -> str:
        """A reply in `parent`'s thread; a notification for the account when it is the parent's author."""
        top = parent.split(".")[0]
        ident = f"{top}.{self._id()[2:20]}"
        self.comments[ident] = {"id": ident, "video": self.comments[top]["video"], "text": text, "by": by,
                                "name": name, "parent": top}
        if notify:
            self.notifications.insert(0, {"video": self.comments[top]["video"], "comment": ident,
                                          "message": f"{name} 回复了：{text}", "packed_only": packed_only})
        return ident

    def upload(self, video: str, title: str) -> None:
        """A new video from a subscription: a notification that is no comment."""
        self.video(video, title, owner="UCother00000000000000000")
        self.notifications.insert(0, {"video": video, "comment": "", "message": f"新视频：{title}"})

    # -- the data the pages load

    def _entity(self, c: dict, me: str) -> dict:
        key = base64.b64encode(c["id"].encode()).decode()
        return {"entityKey": key, "type": "ENTITY_MUTATION_TYPE_REPLACE", "payload": {"commentEntityPayload": {
            "key": key,
            "properties": {"commentId": c["id"], "content": {"content": c["text"]},
                           "publishedTime": WORDS[self.lang]["ago"], "replyLevel": 1 if c["parent"] else 0,
                           "authorButtonA11y": c["name"]},
            "author": {"channelId": c["by"], "displayName": c["name"], "isVerified": False,
                       "isCurrentUser": c["by"] == me,
                       "isCreator": c["by"] == self.videos[c["video"]]["owner"],
                       "channelCommand": {"innertubeCommand": {"commandMetadata": {"webCommandMetadata": {
                           "url": f"/{c['name']}", "webPageType": "WEB_PAGE_TYPE_CHANNEL",
                           "apiUrl": "/youtubei/v1/browse"}},
                           "browseEndpoint": {"browseId": c["by"], "canonicalBaseUrl": f"/{c['name']}"}}}}}}}

    def next_data(self, video: str, linked: str, me: str) -> dict:
        tops = [c for c in self.comments.values() if c["video"] == video and not c["parent"]]
        tops.sort(key=lambda c: c["id"], reverse=True)
        linked_top = linked.split(".")[0]
        tops.sort(key=lambda c: c["id"] != linked_top)
        threads, mutations = [], []
        for top in tops:
            shown = [linked] if top["id"] == linked_top and "." in linked else []
            shown += [c["id"] for c in self.comments.values() if c["parent"] == top["id"] and c["by"] == me
                      and c["id"] not in shown]
            mutations.append(self._entity(top, me))
            mutations += [self._entity(self.comments[i], me) for i in shown if i in self.comments]
            threads.append({"commentThreadRenderer": {"commentViewModel": {"commentViewModel": {
                "commentKey": base64.b64encode(top["id"].encode()).decode(), "commentId": top["id"]}},
                "shownReplies": [i for i in shown if i in self.comments]}})
        return {"responseContext": {}, "trackingParams": "x",
                "onResponseReceivedEndpoints": [{"reloadContinuationItemsCommand": {
                    "targetId": "comments-section", "continuationItems": threads}}],
                "frameworkUpdates": {"entityBatchUpdate": {"mutations": mutations}}}

    def notification_data(self) -> dict:
        items = []
        for n in self.notifications:
            url = f"/watch?v={n['video']}" + (f"&lc={n['comment']}" if n["comment"] and not n.get("packed_only") else "")
            endpoint = {"commandMetadata": {"webCommandMetadata": {"url": url, "webPageType": "WEB_PAGE_TYPE_WATCH"}},
                        "watchEndpoint": {"videoId": n["video"],
                                          **({"params": packed(n["comment"])} if n["comment"] else {})}}
            items.append({"notificationRenderer": {
                "thumbnail": {"thumbnails": []}, "shortMessage": {"simpleText": n["message"]},
                "sentTimeText": {"simpleText": WORDS[self.lang]["ago"]}, "navigationEndpoint": endpoint,
                "read": False, "notificationId": str(len(items) + 1)}})
        return {"actions": [{"openPopupAction": {"popup": {"multiPageMenuRenderer": {"sections": [
            {"multiPageMenuNotificationSectionRenderer": {"items": items}}]}}, "popupType": "DROPDOWN"}}]}

    def account_menu(self, me: str) -> dict:
        name, handle = self.accounts[me]
        return {"actions": [{"openPopupAction": {"popup": {"multiPageMenuRenderer": {
            "header": {"activeAccountHeaderRenderer": {"accountName": {"simpleText": name},
                                                       "channelHandle": {"simpleText": handle}}},
            "sections": [{"multiPageMenuSectionRenderer": {"items": [{"compactLinkRenderer": {
                "title": {"simpleText": WORDS[self.lang]["your_channel"]},
                "navigationEndpoint": {"commandMetadata": {"webCommandMetadata": {"url": f"/{handle}"}},
                                       "browseEndpoint": {"browseId": me, "canonicalBaseUrl": f"/{handle}"}}}}]}}]}}}}]}

    def studio_data(self, me: str) -> dict:
        mine = [c for c in self.comments.values() if not c["parent"] and self.videos[c["video"]]["owner"] == me]
        mine.sort(key=lambda c: c["id"], reverse=True)
        return {"comments": [{"commentId": c["id"], "videoId": c["video"], "authorText": {"simpleText": c["name"]},
                              "content": {"runs": [{"text": c["text"]}]}} for c in mine]}

    def _handler(self):
        site = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args) -> None:
                pass

            def _who(self) -> str:
                if site.signed_out:
                    return ""
                for part in (self.headers.get("Cookie") or "").split(";"):
                    name, _, value = part.strip().partition("=")
                    if name == "SID" and value in site.accounts:
                        return value
                return ""

            def _send(self, body: str, kind: str = "text/html; charset=utf-8", status: int = 200,
                      headers: dict | None = None) -> None:
                raw = body.encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", kind)
                self.send_header("Content-Length", str(len(raw)))
                for name, value in (headers or {}).items():
                    self.send_header(name, value)
                self.end_headers()
                self.wfile.write(raw)

            def _go(self, where: str) -> None:
                self._send("", status=302, headers={"Location": where})

            def _shell(self, title: str, body: str, script: str = "", **extra) -> None:
                who = self._who()
                words = WORDS[site.lang]
                cfg = {"LOGGED_IN": bool(who), "HL": words["hl"], "GL": "JP"}
                self._send(SHELL % {"lang": words["lang"], "title": title, "body": body, "cfg": json.dumps(cfg),
                                    "script": (TOP_SCRIPT % {"words": json.dumps(words, ensure_ascii=False)})
                                    + script})

            def _masthead(self) -> str:
                words = {**WORDS[site.lang], "accounts": site.url + "/accounts"}
                return (MASTHEAD_IN if self._who() else MASTHEAD_OUT) % words

            def do_GET(self) -> None:
                url = urlsplit(self.path)
                query = {k: v[0] for k, v in parse_qs(url.query).items()}
                who = self._who()
                if url.path.startswith("/accounts/"):
                    if url.path == "/accounts/login":
                        self._send("<p>signed in</p>", headers={
                            "Set-Cookie": f"SID={query.get('as', '')}; Path=/; Max-Age=86400"})
                    else:
                        self._send('<!doctype html><title>YouTube</title><form><input type="email" '
                                   'aria-label="Email or phone"><input type="password"></form>')
                    return
                if url.path.startswith("/sorry/"):
                    self._send('<!doctype html><form id="captcha-form"><div id="recaptcha"></div></form>')
                    return
                if site.wall and (url.path.startswith("/yt") or url.path.startswith("/studio")):
                    self._go("/sorry/index?continue=" + quote(self.path, safe=""))
                    return
                if url.path.startswith("/studio"):
                    if not who:
                        self._go("/accounts/v3/signin/identifier?service=youtube")
                    elif url.path in ("/studio", "/studio/"):
                        self._go(f"/studio/channel/{who}")
                    elif url.path.endswith("/comments/inbox"):
                        self._shell("Channel comments - YouTube Studio", STUDIO_BODY,
                                    STUDIO_SCRIPT % {"www": json.dumps(site.url + "/yt")})
                    else:
                        self._shell("Channel dashboard - YouTube Studio", STUDIO_BODY.replace("threads", "dash"))
                    return
                if url.path == "/yt/watch":
                    video = query.get("v", "")
                    title = site.videos.get(video, {}).get("title", "")
                    body = WATCH_BODY % {"masthead": self._masthead(), "popup": POPUP, "title": title}
                    script = WATCH_SCRIPT % {"video": json.dumps(video), "lc": json.dumps(query.get("lc", "")),
                                             "signed_in": json.dumps(bool(who)), "layout": site.layout}
                    self._shell(f"{title} - YouTube", body, script)
                    return
                if url.path.startswith("/yt"):
                    self._shell("YouTube", f"<ytd-app>{self._masthead()}{POPUP}</ytd-app>")
                    return
                self._send("", status=404)

            def do_POST(self) -> None:
                length = int(self.headers.get("Content-Length") or 0)
                body = json.loads(self.rfile.read(length) or b"{}")
                who = self._who()
                path = urlsplit(self.path).path
                answer: dict = {}
                if path == "/youtubei/v1/next":
                    answer = site.next_data(body.get("videoId", ""), body.get("lc", ""), who)
                elif path == "/youtubei/v1/notification/get_notification_menu" and who:
                    answer = site.notification_data()
                elif path == "/youtubei/v1/account/account_menu" and who:
                    answer = site.account_menu(who)
                elif path == "/youtubei/v1/comment/get_comments" and who:
                    answer = site.studio_data(who)
                elif path == "/youtubei/v1/comment/create_comment_reply" and who:
                    parent = body["parent"]
                    ident = site.reply(parent, body["commentText"], by=who, name=site.accounts[who][1],
                                       notify=False)
                    site.replies.append({"video": body["videoId"], "parent": parent, "text": body["commentText"]})
                    c = site.comments[ident]
                    answer = {"comment": {"id": ident, "text": c["text"], "replyLevel": 1,
                                          "publishedTime": WORDS[site.lang]["ago"], "author": c["name"],
                                          "authorUrl": "/" + c["name"]}}
                else:
                    self._send("{}", "application/json", status=401 if not who else 404)
                    return
                self._send(json.dumps(answer, ensure_ascii=False), "application/json")
        return Handler
