"""A stand-in of the parts of Bilibili the bilibili platform works: the
message centre (replies to me, @ me, private messages), a video page whose
comment section is the site's tree of web components with open shadow
roots, the sign-in redirect and a verification panel. Element names,
nesting, ids, classes and words follow the real pages; the data answers
follow the shapes the real pages load."""
from __future__ import annotations

import itertools
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

PAGE = """<!doctype html><html><head><meta charset="utf-8"><title>%(title)s</title>
<style>
body{margin:0;font:14px sans-serif}
.geetest_panel{position:fixed;inset:0;background:rgba(0,0,0,.6);z-index:99}
.geetest_panel_box{width:340px;height:380px;margin:80px auto;background:#fff}
.bili-mini-mask{position:fixed;inset:0;background:rgba(0,0,0,.5);z-index:50}
.bili-mini-content-wp{width:820px;height:430px;margin:80px auto;background:#fff}
.interaction-item{display:flex;padding:12px;border-bottom:1px solid #eee}
.brt-editor{min-height:32px;border:1px solid #ccc}
</style></head><body>%(body)s<script>const CONFIG = %(config)s;</script>%(script)s</body></html>"""

WALL = """<div class="geetest_panel geetest_wind"><div class="geetest_panel_box"><div class="geetest_widget">
<div class="geetest_head">请完成安全验证</div></div></div></div>"""

LOGIN_MASK = """<div class="bili-mini-content-wp"><div class="bili-mini-close-icon"></div>
<div class="bili-mini-customer-title">登录参与社区互动</div><div class="login-scan-wp">
<div class="login-scan-title">扫描二维码登录</div></div><div class="bili-mini-line"></div>
<div class="bili-mini-login-right-wp"><div class="login-tab-wp"><div class="login-tab-item active-tab">密码登录</div>
<div class="login-tab-item">短信登录</div></div><div class="login-pwd-wp"><form class="tab__form">
<div class="form__item"><div class="form_info">账号</div><input placeholder="请输入账号" type="text"></div>
<div class="form__item"><div class="form_info">密码</div><input placeholder="请输入密码" type="password"></div>
</form><div class="btn_wp"><div class="btn_other">注册</div><div class="btn_primary disabled">登录</div></div>
</div></div></div>"""

# The message centre: a hash-routed page whose lists come from the feed addresses.
CENTRE = r"""<script>
const app = document.getElementById('app-main');
async function json(url) { return await (await fetch(url, {credentials: 'include'})).json(); }
const Q = 'platform=web&build=0&mobi_app=web';
function row(item, section) {
  // The rows keep their data the way the real list's components do.
  const it = item.item, el = document.createElement('div');
  el.className = 'interaction-item';
  const data = {id: String(item.id), users: [{...item.user, mid: String(item.user.mid)}],
    actionText: section === 'at' ? '在评论中@了我' : (it.business === '评论' ? '回复了我的评论' : '对我的视频发表了评论'),
    msgNodes: [{type: 'text', text: it.source_content}], time: item.reply_time || item.at_time,
    action: {reply: it.hide_reply_button ? null : {params: {type: it.business_id, oid: it.subject_id,
      root: it.root_id || it.source_id, parent: it.source_id, target: it.target_id ? item.user.nickname : ''}}},
    cover: {type: 'text', text: it.title}, url: it.uri ? it.uri + '#reply' + it.source_id : ''};
  if (it.target_reply_content) data.reference = CONFIG.uname + ' : ' + it.target_reply_content;
  el.__vue__ = {data};
  el.innerHTML = `<div class="interaction-item__left"><div class="interaction-item__avatar"></div></div>
    <div class="interaction-item__right"><div class="interaction-item__content">
    <div class="interaction-item__title"><span class="interaction-item__uname"></span>
    <span class="interaction-item__action"></span></div><div class="interaction-item__msg bili-ellipsis"></div>
    <div class="interaction-item__reference"></div><div class="interaction-item__metadata">
    <span class="interaction-item__time"></span><span class="interaction-item__btn reply">回复</span>
    <span class="interaction-item__btn like">点赞</span></div></div></div>`;
  el.querySelector('.interaction-item__uname').textContent = item.user.nickname;
  el.querySelector('.interaction-item__action').textContent = data.actionText;
  el.querySelector('.interaction-item__msg').textContent = it.source_content;
  el.querySelector('.interaction-item__reference').textContent = data.reference || '';
  return el;
}
async function feed(section) {
  const path = CONFIG.feed_moved ? '/x/msgfeed/v2/' : '/x/msgfeed/';
  const answer = await json(path + section + '?' + Q);
  app.innerHTML = `<div class="${section}"><div class="message-header message-box-shadow">
    <div class="message-header__title">${section === 'at' ? '@ 我的' : '回复我的'}</div></div>
    <div class="${section}-layout"><div class="${section}-list"></div></div></div>`;
  const list = app.querySelector('.' + section + '-list');
  for (const item of (answer.data && answer.data.items) || []) list.append(row(item, section));
}
async function sessions() {
  const answer = await json('/session_svr/v1/session_svr/get_sessions?session_type=1&group_fold=1&unfollow_fold=0&sort_rule=2&build=0&mobi_app=web');
  const list = (answer.data && answer.data.session_list) || [];
  await json('/x/polymer/pc-electron/v1/user/cards?uids=' + list.map(s => s.talker_id).join(',') + '&build=0&mobi_app=web');
  app.innerHTML = '<div class="im-container"><div class="_ChatList__Sessions_1wgzt_6"></div></div>';
  for (const s of list) {
    const el = document.createElement('div'); el.className = '_SessionItem_dnmx0_1';
    el.innerHTML = '<div class="_SessionItem__Name_dnmx0_80"></div><div class="_SessionItem__Message_dnmx0_101"></div>';
    el.firstChild.textContent = CONFIG.names[s.talker_id] || s.talker_id;
    el.onclick = () => { location.hash = '#/whisper/mid' + s.talker_id; };
    app.firstChild.firstChild.append(el);
  }
}
async function conversation(talker) {
  await json('/x/polymer/pc-electron/v1/user/cards?uids=' + talker + '&build=0&mobi_app=web');
  const answer = await json('/svr_sync/v1/svr_sync/fetch_session_msgs?talker_id=' + talker +
    '&session_type=1&size=20&sender_device_id=1&build=0&mobi_app=web');
  app.innerHTML = `<div class="im-container"><div class="_ChatWindow_1n8sa_1"><div class="_Msgs_v1v4w_1"></div>
    <div class="_MessageSendBox_1izxa_1"><div class="_MessageSendBox__Toolbar_1izxa_6">
    <button class="_MessageSendBox__ToolBtn_1izxa_13">图片</button></div>
    <div class="_MessageSendBox__Textarea_1izxa_42 msb-textarea" style="--brt-editor-padding-hrz:16px">
    <div class="brt-root"><div class="brt-placeholder">请输入消息内容</div>
    <div class="brt-editor" contenteditable="true"></div></div></div>
    <div class="_MessageSendBox__Send_1izxa_60"><div class="_MessageSendBox__Indicator_1izxa_91">
    <span class="_MessageSendBox__IndicatorValue_1izxa_96">0</span>/500</div>
    ${CONFIG.layout === 2 ? '<div role="button" tabindex="0" class="_SendBox__Go_9zz_1" aria-label="发送消息">➤</div>'
                          : '<button class="_MessageSendBox__SendBtn_1izxa_69">发送</button>'}</div></div></div></div>`;
  const msgs = app.querySelector('._Msgs_v1v4w_1');
  for (const m of [...((answer.data && answer.data.messages) || [])].reverse()) {
    const el = document.createElement('div'); el.className = '_Msg_7ixmd_1';
    el.innerHTML = '<div class="_Msg__Main_7ixmd_38"><div class="_MsgText__Content_1qqpe_1"></div></div>';
    try { el.querySelector('div div').textContent = JSON.parse(m.content).content || ''; } catch (e) {}
    msgs.append(el);
  }
  const editor = app.querySelector('.brt-editor');
  editor.addEventListener('input', () => {
    app.querySelector('.brt-placeholder').style.display = editor.innerText.trim() ? 'none' : '';
  });
  const send = app.querySelector('._MessageSendBox__Send_1izxa_60 > :last-child');
  send.addEventListener('click', async () => {
    const text = editor.innerText.trim();
    if (!text) return;
    const body = new URLSearchParams({'msg[sender_uid]': CONFIG.mid, 'msg[receiver_type]': '1',
      'msg[receiver_id]': talker, 'msg[msg_type]': '1', 'msg[content]': JSON.stringify({content: text}),
      from_firework: '0', build: '0', mobi_app: 'web'});
    const answer = await (await fetch('/web_im/v1/web_im/send_msg?w_sender_uid=' + CONFIG.mid +
      '&w_receiver_id=' + talker, {method: 'POST', body, credentials: 'include'})).json();
    if (answer.code === 0) { editor.innerText = ''; }
  });
}
async function route() {
  const hash = location.hash.replace(/^#\/?/, '');
  if (hash.startsWith('whisper/mid')) return conversation(hash.slice('whisper/mid'.length));
  if (hash.startsWith('whisper')) return sessions();
  if (hash.startsWith('at')) return feed('at');
  return feed('reply');
}
(async () => {
  const nav = await json('/x/web-interface/nav?web_location=333.1228');
  if (!nav.data || !nav.data.isLogin) {
    location.replace('/passport/login?gourl=' + encodeURIComponent(location.href));
    return;
  }
  window.addEventListener('hashchange', route);
  route();
})();
</script>"""

# The comment section: the real one's elements, each a web component with an open shadow root.
COMMENTS = r"""<script>
const esc = (s) => String(s == null ? '' : s).replace(/[&<>"]/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c]));
function make(tag, data, extra) { const el = document.createElement(tag); el.data = data; Object.assign(el, extra || {}); return el; }
class Base extends HTMLElement {
  connectedCallback() { if (!this.shadowRoot) { this.attachShadow({mode: 'open'}); this.draw(); } }
}
customElements.define('bili-rich-text', class extends Base {
  draw() { this.shadowRoot.innerHTML = '<style>:host{--bili-rich-text-display:block}</style><p id="contents"><span></span></p>';
           this.shadowRoot.querySelector('span').textContent = this.text || ''; }
});
customElements.define('bili-comment-user-info', class extends Base {
  draw() { const m = this.data.member; this.shadowRoot.innerHTML = `<div id="info"><slot></slot>
    <div id="user-name" data-user-profile-id="${esc(m.mid)}"><a target="_blank" href="//space.bilibili.com/${esc(m.mid)}">${esc(m.uname)}</a></div>
    <div id="user-level"></div></div>`; }
});
customElements.define('bili-comment-action-buttons-renderer', class extends Base {
  draw() {
    const reply = CONFIG.layout === 2
      ? '<div id="respond"><span role="button" tabindex="0" aria-label="回复这条评论">回应</span></div>'
      : '<div id="reply"><button>回复</button></div>';
    this.shadowRoot.innerHTML = `<style>button,span[role]{min-width:24px;min-height:16px;display:inline-block}</style>
      <div id="pubdate">${new Date(this.data.ctime * 1000).toISOString().slice(0, 16).replace('T', ' ')}</div>
      <div id="like"><button><span id="count">${this.data.like || 0}</span></button></div>
      <div id="dislike"><button> </button></div>${reply}<div id="more"><button> </button></div>`;
    const control = this.shadowRoot.querySelector('#reply button, #respond span');
    control.addEventListener('click', () => this.dispatchEvent(new CustomEvent('pa-reply',
      {detail: this.data, bubbles: true, composed: true})));
    control.addEventListener('keydown', (e) => { if (e.key === 'Enter') control.click(); });
  }
});
customElements.define('bili-comment-renderer', class extends Base {
  draw() { const d = this.data; this.shadowRoot.innerHTML = `<div id="body" class=" light ">
    <a id="user-avatar" target="_blank" href="//space.bilibili.com/${esc(d.mid)}" data-user-profile-id="${esc(d.mid)}"></a>
    <div id="main"><div id="header"></div><div id="content"></div><div id="footer"></div></div></div>`;
    const r = this.shadowRoot;
    r.querySelector('#header').append(make('bili-comment-user-info', d));
    r.querySelector('#content').append(make('bili-rich-text', d, {text: d.content.message}));
    r.querySelector('#footer').append(make('bili-comment-action-buttons-renderer', d)); }
});
customElements.define('bili-comment-reply-renderer', class extends Base {
  draw() { const d = this.data; this.shadowRoot.innerHTML = '<div id="body"><div id="main"></div><div id="footer"></div></div>';
    const main = this.shadowRoot.querySelector('#main');
    main.append(make('bili-comment-user-info', d));
    main.append(make('bili-rich-text', d, {text: d.content.message}));
    this.shadowRoot.querySelector('#footer').append(make('bili-comment-action-buttons-renderer', d)); }
});
customElements.define('bili-comment-replies-renderer', class extends Base {
  draw() { this.shadowRoot.innerHTML = '<div id="expander"><div id="expander-contents"></div><div id="expander-footer"></div></div>';
    for (const r of this.data.replies || []) this.add(r); }
  add(reply) { this.shadowRoot.querySelector('#expander-contents').append(make('bili-comment-reply-renderer', reply)); }
});
customElements.define('bili-comment-rich-textarea', class extends Base {
  draw() { this.shadowRoot.innerHTML = `<style>.brt-editor{min-height:32px;border:1px solid #ccc}</style><div id="input" class="  ">
    <div class="brt-root"><div class="brt-placeholder">${esc(this.placeholder || '请输入内容')}</div>
    <div class="brt-editor" contenteditable="true"></div></div></div>`;
    const editor = this.shadowRoot.querySelector('.brt-editor');
    editor.addEventListener('focus', () => this.dispatchEvent(new CustomEvent('pa-focus', {bubbles: true, composed: true})));
    editor.addEventListener('input', () => { this.shadowRoot.querySelector('.brt-placeholder').style.display =
      editor.innerText.trim() ? 'none' : ''; }); }
  get value() { return this.shadowRoot.querySelector('.brt-editor').innerText; }
});
customElements.define('bili-checkbox', class extends Base {
  draw() { this.shadowRoot.innerHTML = `<span id="input"><input type="checkbox" value="sync"><span id="inner"></span></span>
    <slot><span id="label">${esc(this.getAttribute('label'))}</span></slot>`; }
});
customElements.define('bili-comment-box', class extends Base {
  draw() {
    const pub = CONFIG.layout === 2 ? '<div id="publish"><span role="button" tabindex="0">提交</span></div>'
                                    : '<div id="pub"><button class="  "> 发布 </button></div>';
    this.shadowRoot.innerHTML = `<style>#footer.hidden{display:none}.tool-btn{width:24px;height:24px}
      #pub button,#publish span{display:inline-block;padding:4px 12px}</style>
      <div id="user-avatar"></div><div id="comment-area"><div id="emoji-popover"></div><div id="body">
      <div id="editor" class=""></div></div><div id="footer" class=" hidden ">
      <button class="tool-btn emoji"> </button><button class="tool-btn mention"> </button><button class=" tool-btn "> </button>
      <div id="optional"><bili-checkbox value="sync" checked="false" label="同时转发到我的动态"></bili-checkbox></div>${pub}</div></div>`;
    const area = make('bili-comment-rich-textarea', null, {placeholder: this.target ? '回复 @' + this.target.member.uname + ' :' : '请输入内容'});
    this.shadowRoot.querySelector('#editor').append(area);
    this.addEventListener('pa-focus', () => this.shadowRoot.querySelector('#footer').className = '');
    const press = this.shadowRoot.querySelector('#pub button, #publish span');
    press.addEventListener('click', async () => {
      const message = area.value.trim();
      if (!message) return;
      const body = new URLSearchParams({oid: CONFIG.oid, type: '1', message, plat: '1'});
      if (this.target) { body.set('root', this.target.root_str === '0' ? this.target.rpid_str : this.target.root_str);
                         body.set('parent', this.target.rpid_str); }
      const answer = await (await fetch('/x/v2/reply/add', {method: 'POST', body, credentials: 'include'})).json();
      if (answer.code === 0) this.dispatchEvent(new CustomEvent('pa-sent', {detail: answer.data.reply, bubbles: true, composed: true}));
    });
  }
});
customElements.define('bili-comment-thread-renderer', class extends Base {
  draw() { const d = this.data; const r = this.shadowRoot;
    r.innerHTML = '<div id="replies"></div><div id="reply-container"></div><div id="div"></div>';
    r.prepend(make('bili-comment-renderer', d, {id: 'comment'}));
    this.replies = make('bili-comment-replies-renderer', d);
    r.querySelector('#replies').append(this.replies);
    this.addEventListener('pa-reply', (e) => {
      if (!CONFIG.mid) { document.querySelector('.bili-mini-mask').style.display = 'block'; return; }
      const holder = r.querySelector('#reply-container');
      holder.innerHTML = '';
      holder.append(make('bili-comment-box', null, {target: e.detail}));
    });
    this.addEventListener('pa-sent', (e) => { r.querySelector('#reply-container').innerHTML = '';
      this.replies.add(e.detail); }); }
});
customElements.define('bili-comments-header-renderer', class extends Base {
  draw() { this.shadowRoot.innerHTML = `<div id="navbar"><div id="title"><h2>评论</h2><div id="count">${this.data.count}</div></div></div>
    <div id="commentbox">${CONFIG.mid ? '' : '<div id="disabled-commentbox"><div id="user-avatar"></div><div id="edit"><div>请先</div><button>登录</button><div>后发表评论 (・ω・)</div></div></div>'}</div>`;
    if (CONFIG.mid) this.shadowRoot.querySelector('#commentbox').append(make('bili-comment-box', null)); }
});
customElements.define('bili-comments', class extends Base {
  async draw() {
    const r = this.shadowRoot;
    r.innerHTML = '<div id="header"></div><div id="contents"><div id="new"></div><div id="feed"></div></div>';
    const seek = (location.hash.match(/^#reply(\d+)/) || [])[1] || '';
    const answer = await (await fetch(`/x/v2/reply/wbi/main?oid=${CONFIG.oid}&type=1&mode=3&pagination_str=%7B%22offset%22:%22%22%7D&plat=1&seek_rpid=${seek}&web_location=1315875`, {credentials: 'include'})).json();
    r.querySelector('#header').append(make('bili-comments-header-renderer', {count: answer.data.cursor.all_count}));
    for (const thread of answer.data.replies) r.querySelector('#feed').append(make('bili-comment-thread-renderer', thread));
  }
});
</script>"""


class Bilibili:
    """The stand-in site. The owner's account is 1001 "Robin"; videos are his."""

    def __init__(self) -> None:
        self.accounts = {"1001": "Robin"}
        self.names = {"1001": "Robin", "2002": "Kim", "3003": "Lee"}
        self.videos = {"880001": {"bvid": "BV1xx411c7aa", "title": "A walk by the river", "owner": "1001"}}
        self.comments: dict[str, list[dict]] = {"880001": []}
        self.replies_feed: list[dict] = []
        self.mentions_feed: list[dict] = []
        self.messages: dict[str, list[dict]] = {}
        self.sent_comments: list[dict] = []
        self.sent_messages: list[dict] = []
        self.layout = 1
        self.wall = False
        self.signed_out = False
        self.feed_moved = False
        self.page_size = 2
        self.hits: list[str] = []
        self._ids = itertools.count(5_000_000_001)
        self._seqno = itertools.count(1)
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), self._handler())
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def close(self) -> None:
        self.server.shutdown()
        self.server.server_close()

    # ------------------------------------------------------------ what people do

    def _comment(self, oid: str, mid: str, text: str, *, root: str = "0", parent: str = "0") -> dict:
        rpid = str(next(self._ids))
        made = {"rpid": int(rpid), "rpid_str": rpid, "oid": int(oid), "oid_str": oid, "type": 1, "mid": int(mid),
                "mid_str": mid, "root": int(root), "root_str": root, "parent": int(parent), "parent_str": parent,
                "ctime": int(time.time()), "like": 0, "rcount": 0,
                "member": {"mid": mid, "uname": self.names.get(mid, mid)}, "content": {"message": text},
                "replies": []}
        if root == "0":
            self.comments[oid].append(made)
        else:
            thread = next(c for c in self.comments[oid] if c["rpid_str"] == root)
            thread["replies"].append(made)
            thread["rcount"] += 1
        return made

    def _feed_item(self, made: dict, *, kind: str, business: str, target: dict | None = None) -> dict:
        video = self.videos[made["oid_str"]]
        return {"id": next(self._ids), "user": {"mid": int(made["mid_str"]), "fans": 0,
                                                "nickname": made["member"]["uname"], "avatar": "", "follow": False},
                "item": {"subject_id": int(made["oid_str"]), "root_id": int(made["root_str"]),
                         "source_id": int(made["rpid_str"]), "target_id": int(target["rpid_str"]) if target else 0,
                         "type": kind, "business_id": 1, "business": business, "title": video["title"],
                         "desc": "", "image": "", "uri": f"{self.url}/video/{video['bvid']}",
                         "native_uri": f"bilibili://video/{made['oid_str']}", "detail_title": "",
                         "root_reply_content": "", "source_content": made["content"]["message"],
                         "target_reply_content": target["content"]["message"] if target else "",
                         "at_details": [], "topic_details": [], "hide_reply_button": False,
                         "hide_like_button": False, "like_state": 0, "danmu": None, "message": ""},
                "counts": 1, "is_multi": 0, "reply_time": made["ctime"]}

    def own_comment(self, text: str, oid: str = "880001") -> dict:
        return self._comment(oid, "1001", text)

    def comment_on_video(self, mid: str, text: str, oid: str = "880001") -> dict:
        made = self._comment(oid, mid, text)
        self.replies_feed.insert(0, self._feed_item(made, kind="video", business="视频"))
        return made

    def reply_to(self, comment: dict, mid: str, text: str) -> dict:
        root = comment["rpid_str"] if comment["root_str"] == "0" else comment["root_str"]
        made = self._comment(comment["oid_str"], mid, text, root=root, parent=comment["rpid_str"])
        if comment["mid_str"] == "1001":
            self.replies_feed.insert(0, self._feed_item(made, kind="reply", business="评论", target=comment))
        return made

    def mention(self, mid: str, text: str, oid: str = "880001") -> dict:
        made = self._comment(oid, mid, f"@Robin {text}")
        item = self._feed_item(made, kind="reply", business="评论")
        item["at_time"] = item.pop("reply_time")
        item["item"]["at_details"] = [{"mid": 1001, "nickname": "Robin"}]
        self.mentions_feed.insert(0, item)
        return made

    def danmu_reply(self, mid: str, text: str) -> None:
        item = self._feed_item(self._comment("880001", mid, text), kind="danmu", business="弹幕")
        item["item"]["danmu"] = {"aid": 880001, "progress": 12}
        self.replies_feed.insert(0, item)

    def whisper(self, sender: str, receiver: str, text: str) -> dict:
        talker = receiver if sender == "1001" else sender
        message = {"sender_uid": int(sender), "receiver_type": 1, "receiver_id": int(receiver), "msg_type": 1,
                   "content": json.dumps({"content": text}, ensure_ascii=False), "msg_seqno": next(self._seqno),
                   "timestamp": int(time.time()), "at_uids": None, "msg_key": next(self._ids), "msg_status": 0,
                   "notify_code": "", "new_face_version": 0}
        self.messages.setdefault(talker, []).append(message)
        return message

    # ------------------------------------------------------------ the site

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
                    if name == "SESSDATA" and value in site.accounts:
                        return value
                return ""

            def _send(self, body: str, kind: str = "text/html; charset=utf-8", headers: dict | None = None,
                      status: int = 200) -> None:
                raw = body.encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", kind)
                self.send_header("Content-Length", str(len(raw)))
                for name, value in (headers or {}).items():
                    self.send_header(name, value)
                self.end_headers()
                self.wfile.write(raw)

            def _json(self, value: dict) -> None:
                self._send(json.dumps(value, ensure_ascii=False), "application/json; charset=utf-8")

            def _page(self, title: str, body: str, script: str, config: dict) -> None:
                if site.wall:
                    body += WALL
                self._send(PAGE % {"title": title, "body": body, "script": script,
                                   "config": json.dumps(config, ensure_ascii=False)})

            def _risky(self) -> bool:
                if site.wall:
                    self._json({"code": -352, "message": "风控校验失败", "ttl": 1})
                return site.wall

            def do_GET(self) -> None:
                url = urlsplit(self.path)
                query = {k: v[0] for k, v in parse_qs(url.query).items()}
                who = self._who()
                site.hits.append(url.path)
                path = url.path
                if path == "/login":
                    self._send("Signed in", headers={"Set-Cookie": f"SESSDATA={query.get('as', '')}; Path=/; Max-Age=86400"})
                elif path.startswith("/passport/login"):
                    self._send(PAGE % {"title": "哔哩哔哩 (゜-゜)つロ 干杯~-bilibili", "config": "{}", "script": "",
                                       "body": '<div id="app"><div class="login_wp"><div class="login__main">'
                                               '<div class="tab_active">密码登录</div></div></div></div>'})
                elif path == "/x/web-interface/nav":
                    if who:
                        self._json({"code": 0, "message": "0", "ttl": 1, "data": {
                            "isLogin": True, "mid": int(who), "uname": site.accounts[who], "face": "",
                            "wbi_img": {"img_url": "", "sub_url": ""}}})
                    else:
                        self._json({"code": -101, "message": "账号未登录", "ttl": 1,
                                    "data": {"isLogin": False, "wbi_img": {"img_url": "", "sub_url": ""}}})
                elif path in ("/x/msgfeed/reply", "/x/msgfeed/at", "/x/msgfeed/v2/reply", "/x/msgfeed/v2/at"):
                    if self._risky():
                        return
                    if not who:
                        self._json({"code": -101, "message": "账号未登录", "ttl": 1})
                        return
                    items = site.replies_feed if path.endswith("reply") else site.mentions_feed
                    self._json({"code": 0, "message": "0", "ttl": 1, "data": {
                        "cursor": {"is_end": True, "id": 0, "time": 0}, "items": items,
                        "last_view_at": int(time.time())}})
                elif path == "/session_svr/v1/session_svr/get_sessions":
                    if self._risky():
                        return
                    sessions = []
                    for talker, messages in site.messages.items():
                        last = messages[-1]
                        sessions.append({"talker_id": int(talker), "session_type": 1, "at_seqno": 0, "top_ts": 0,
                                         "group_name": "", "group_cover": "", "is_follow": 1, "is_dnd": 0,
                                         "ack_seqno": 0, "ack_ts": 0, "session_ts": last["timestamp"] * 1_000_000,
                                         "unread_count": 1, "last_msg": last, "group_type": 0, "can_fold": 0,
                                         "status": 0, "max_seqno": last["msg_seqno"], "new_push_msg": 0,
                                         "setting": 0, "is_guardian": 0, "is_intercept": 0, "is_trust": 0,
                                         "system_msg_type": 0, "account_info": None})
                    sessions.sort(key=lambda s: -s["session_ts"])
                    self._json({"code": 0, "msg": "0", "message": "0", "ttl": 1,
                                "data": {"session_list": sessions, "has_more": 0, "anti_disturb_cleaning": False,
                                         "is_address_list_empty": 0, "system_msg": {}, "show_level": False}})
                elif path == "/x/polymer/pc-electron/v1/user/cards":
                    uids = [u for u in query.get("uids", "").split(",") if u]
                    self._json({"code": 0, "message": "0", "ttl": 1, "data": {
                        u: {"mid": u, "name": site.names.get(u, u), "face": ""} for u in uids}})
                elif path == "/svr_sync/v1/svr_sync/fetch_session_msgs":
                    if self._risky():
                        return
                    messages = site.messages.get(query.get("talker_id", ""), [])
                    self._json({"code": 0, "msg": "0", "message": "0", "ttl": 1, "data": {
                        "messages": list(reversed(messages[-20:])), "has_more": 0,
                        "min_seqno": messages[0]["msg_seqno"] if messages else 0,
                        "max_seqno": messages[-1]["msg_seqno"] if messages else 0, "e_infos": []}})
                elif path == "/x/v2/reply/wbi/main":
                    oid = query.get("oid", "")
                    threads = list(reversed(site.comments.get(oid, [])))
                    seek = query.get("seek_rpid", "")
                    if seek:
                        # The sought comment, or the thread holding it, comes first.
                        first = [t for t in threads if t["rpid_str"] == seek
                                 or any(r["rpid_str"] == seek for r in t["replies"])]
                        threads = first + [t for t in threads if t not in first]
                    # A short first page, so a comment is only found by seeking it.
                    threads = threads[:site.page_size]
                    self._json({"code": 0, "message": "0", "ttl": 1, "data": {
                        "cursor": {"is_begin": True, "prev": 0, "next": 2, "is_end": True, "mode": 3,
                                   "all_count": sum(1 + len(t["replies"]) for t in threads)},
                        "replies": threads, "top_replies": [], "upper": {"mid": 1001},
                        "control": {"input_disable": False, "root_input_text": "", "child_input_text": ""}}})
                elif path.startswith("/video/"):
                    bvid = path.strip("/").split("/")[1]
                    oid = next((k for k, v in site.videos.items() if v["bvid"] == bvid), "")
                    body = ('<div class="bili-header"><div class="right-entry">'
                            + ('<div class="header-entry-mini"></div>' if who else
                               '<div class="header-avatar-unlogin-entry">登录</div>')
                            + f'</div></div><h1 class="video-title">{site.videos[oid]["title"]}</h1>'
                            '<div id="commentapp"><bili-comments></bili-comments></div>'
                            f'<div class="bili-mini-mask" style="display:none">{LOGIN_MASK}</div>')
                    self._page(site.videos[oid]["title"] + "_哔哩哔哩_bilibili", body, COMMENTS,
                               {"oid": oid, "mid": who, "layout": site.layout})
                elif path == "/":
                    self._page("消息中心 - 哔哩哔哩弹幕视频网", '<div id="app"><div class="message-layout">'
                               '<div class="message-sidebar"></div><div id="app-main" class="message-main"></div>'
                               '</div></div>', CENTRE,
                               {"mid": who, "uname": site.accounts.get(who, ""), "layout": site.layout,
                                "feed_moved": site.feed_moved, "names": site.names})
                else:
                    self._send("not found", status=404)

            def do_POST(self) -> None:
                url = urlsplit(self.path)
                length = int(self.headers.get("Content-Length") or 0)
                form = {k: v[0] for k, v in parse_qs(self.rfile.read(length).decode("utf-8")).items()}
                who = self._who()
                if not who:
                    self._json({"code": -101, "message": "账号未登录", "ttl": 1})
                    return
                if url.path == "/x/v2/reply/add":
                    site.sent_comments.append(form)
                    root, parent = form.get("root", "0"), form.get("parent", "0")
                    oid = form["oid"]
                    if root != "0":
                        made = site._comment(oid, who, form["message"], root=root, parent=parent)
                    else:
                        made = site._comment(oid, who, form["message"])
                    self._json({"code": 0, "message": "0", "ttl": 1, "data": {
                        "rpid": made["rpid"], "rpid_str": made["rpid_str"], "reply": made,
                        "success_toast": "发送成功"}})
                elif url.path == "/web_im/v1/web_im/send_msg":
                    site.sent_messages.append(form)
                    content = json.loads(form["msg[content]"])["content"]
                    made = site.whisper(who, form["msg[receiver_id]"], content)
                    self._json({"code": 0, "msg": "0", "message": "0", "ttl": 1, "data": {
                        "msg_key": made["msg_key"], "msg_content": form["msg[content]"], "key_hit_infos": {}}})
                else:
                    self._json({"code": -404, "message": "啥都木有", "ttl": 1})
        return Handler
