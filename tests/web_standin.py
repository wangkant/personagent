"""A small site with a sign-in, an inbox drawn inside a shadow root and a
thread with reply boxes, for the browser-worked platforms' tests. Its layout,
an overlay and a verification wall are switched from the test."""
from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

PAGE = """<!doctype html><html><head><meta charset="utf-8"><title>%(title)s</title>
<style>.cover{position:fixed;inset:0;background:rgba(0,0,0,.4);z-index:9}</style></head>
<body>%(body)s</body></html>"""

INBOX = """<inbox-list></inbox-list><script>
customElements.define('inbox-list', class extends HTMLElement {
  async connectedCallback() {
    const root = this.attachShadow({mode: 'open'});
    const items = await (await fetch('/api/inbox')).json();
    root.innerHTML = items.map(i => `<div class="item" data-id="${i.id}" data-thread="${i.thread}"
      data-from="${i.from_id}" data-kind="${i.kind}"><b class="who"></b><span class="said"></span></div>`).join('');
    items.forEach((i, n) => { const el = root.children[n];
      el.querySelector('.who').textContent = i.from_name; el.querySelector('.said').textContent = i.text; });
    this.setAttribute('ready', '');
  }});
</script>"""

THREAD = """<div id="thread" data-thread="%(thread)s"></div><script>
const REPLY = %(reply_class)s, EDITOR = %(editor_class)s;
async function draw() {
  const comments = await (await fetch('/api/thread?id=%(thread)s')).json();
  const root = document.getElementById('thread');
  root.innerHTML = '';
  for (const c of comments) {
    const row = document.createElement('div');
    row.className = 'comment'; row.dataset.id = c.id;
    const said = document.createElement('p'); said.className = 'said'; said.textContent = c.text;
    const reply = document.createElement('button'); reply.className = REPLY; reply.textContent = 'Reply';
    reply.onclick = () => {
      if (row.querySelector('.' + EDITOR)) return;
      const box = document.createElement('div'); box.className = EDITOR; box.contentEditable = 'true';
      box.setAttribute('aria-label', 'Write a reply');
      const send = document.createElement('button'); send.className = 'send'; send.textContent = 'Send';
      send.onclick = async () => {
        await fetch('/api/reply', {method: 'POST', body: JSON.stringify(
          {thread: '%(thread)s', parent: c.id, text: box.innerText})});
        draw();
      };
      row.append(box, send);
    };
    row.append(said, reply); root.append(row);
  }
}
draw();
%(cover)s
</script>"""

COVER = """const cover = document.createElement('div'); cover.className = 'cover'; document.body.append(cover);
document.addEventListener('keydown', e => { if (e.key === 'Escape') cover.remove(); });"""


class Site:
    def __init__(self) -> None:
        self.accounts = {"42": "Robin"}
        self.inbox: list[dict] = []
        self.threads: dict[str, list[dict]] = {}
        self.replies: list[dict] = []
        self.layout = 1
        self.cover = False
        self.wall = False
        self.signed_out = False
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), self._handler())
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def close(self) -> None:
        self.server.shutdown()
        self.server.server_close()

    def say(self, ident: str, text: str, *, thread: str = "t1", kind: str = "reply",
            from_id: str = "7", from_name: str = "Kim") -> None:
        """Someone writes to the account: a comment in a thread, and the inbox item for it."""
        self.threads.setdefault(thread, []).append({"id": ident, "text": text})
        self.inbox.append({"id": ident, "thread": thread, "kind": kind, "from_id": from_id,
                           "from_name": from_name, "text": text})

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
                    if name == "sid" and value in site.accounts:
                        return value
                return ""

            def _send(self, body: str, kind: str = "text/html; charset=utf-8", headers: dict | None = None) -> None:
                raw = body.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", kind)
                self.send_header("Content-Length", str(len(raw)))
                for name, value in (headers or {}).items():
                    self.send_header(name, value)
                self.end_headers()
                self.wfile.write(raw)

            def _page(self, title: str, body: str) -> None:
                if site.wall:
                    body = '<div id="verify">Prove you are a person</div>'
                self._send(PAGE % {"title": title, "body": body})

            def do_GET(self) -> None:
                url = urlsplit(self.path)
                query = parse_qs(url.query)
                who = self._who()
                if url.path == "/login":
                    account = (query.get("as") or [""])[0]
                    self._send(PAGE % {"title": "Sign in", "body": "Signed in"},
                               headers={"Set-Cookie": f"sid={account}; Path=/; Max-Age=86400"})
                elif url.path == "/api/inbox":
                    self._send(json.dumps(site.inbox if who else []), "application/json")
                elif url.path == "/api/thread":
                    self._send(json.dumps(site.threads.get((query.get("id") or [""])[0], [])), "application/json")
                elif url.path == "/inbox":
                    self._page("Inbox", INBOX if who else '<a href="/login">Sign in</a>')
                elif url.path.startswith("/thread/"):
                    thread = url.path.rsplit("/", 1)[-1]
                    names = {1: ("reply-v1", "editor-v1"), 2: ("respond-x9", "field-q4")}[site.layout]
                    self._page("Thread", THREAD % {
                        "thread": thread, "reply_class": json.dumps(names[0]),
                        "editor_class": json.dumps(names[1]), "cover": COVER if site.cover else ""})
                else:
                    me = f'<div id="me" data-id="{who}">{site.accounts[who]}</div>' if who else \
                        '<a href="/login">Sign in</a>'
                    self._page("Home", me)

            def do_POST(self) -> None:
                length = int(self.headers.get("Content-Length") or 0)
                body = json.loads(self.rfile.read(length) or b"{}")
                if self.path == "/api/reply" and self._who():
                    site.replies.append(body)
                    site.threads.setdefault(body["thread"], []).append(
                        {"id": f"r{len(site.replies)}", "text": body["text"]})
                self._send("{}", "application/json")
        return Handler
