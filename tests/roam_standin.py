"""Small sites for the walks' tests: pages describing themselves in the
standard ways (or not at all), walls, a redirect and a subrequest to an
internal address, and pages shaped like Bilibili's and YouTube's lists."""
from __future__ import annotations

import io
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

ARTICLE = "<p>" + "</p><p>".join(
    f"Paragraph {n} of the story about tide pools, long enough to count as reading matter for anyone."
    for n in range(20)) + "</p>"
NAV = "<nav>" + " ".join(f"<a href='/n{n}'>Menu entry {n}</a>" for n in range(30)) + "</nav>"


def picture(width: int = 1600, height: int = 900) -> bytes:
    from PIL import Image
    out = io.BytesIO()
    Image.new("RGB", (width, height), (40, 120, 200)).save(out, "PNG")
    return out.getvalue()


def ld(value: dict) -> str:
    return f'<script type="application/ld+json">{json.dumps(value)}</script>'


class Recorder:
    """A server on another loopback address that only notes who reached it."""

    def __init__(self, host: str = "127.0.0.2") -> None:
        self.hits: list[str] = []
        hits = self.hits

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args) -> None:
                pass

            def do_GET(self) -> None:
                hits.append(self.path)
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                self.wfile.write(b"<title>secret</title><p>internal</p>")

        self.server = ThreadingHTTPServer((host, 0), Handler)
        self.url = f"http://{host}:{self.server.server_address[1]}"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def close(self) -> None:
        self.server.shutdown()
        self.server.server_close()


class Site:
    def __init__(self, inside: str = "") -> None:
        self.inside = inside
        self.loads: list[str] = []
        self.cover = picture()
        self.videos = {f"BV1aa41167{n:02d}": f"Stand-in video {n}" for n in range(10)}
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), self._handler())
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def close(self) -> None:
        self.server.shutdown()
        self.server.server_close()

    def page(self, path: str, query: dict) -> tuple[int, str, str, dict]:
        """(status, content type, body, headers) for a GET."""
        html = "text/html; charset=utf-8"
        cover = f'<meta property="og:image" content="{self.url}/cover.png">'
        if path == "/og":
            return 200, html, (
                "<html><head><title>Tab title</title>"
                '<meta property="og:title" content="Tide pools at dawn">'
                '<meta property="og:site_name" content="Shore Notes">'
                '<meta property="og:type" content="article">'
                '<meta property="og:description" content="What lives in a tide pool.">'
                f"{cover}</head><body>{NAV}<article><h1>Tide pools</h1>{ARTICLE}</article></body></html>"), {}
        if path == "/ld":
            return 200, html, ("<html><head><title>A clip</title>" + ld({
                "@context": "https://schema.org", "@type": "VideoObject", "name": "Making bread by hand",
                "description": "Flour, water, time.", "thumbnailUrl": [f"{self.url}/cover.png"],
                "duration": "PT3M20S", "uploadDate": "2026-11-01", "author": {"@type": "Person", "name": "Ana"},
                "embedUrl": "https://player.vimeo.com/video/123"}) + "</head><body><main><p>Short.</p></main>"
                "</body></html>"), {}
        if path == "/both":
            return 200, html, (
                '<html><head><title>x</title><meta property="og:title" content="Harbour reopens">'
                '<meta property="og:site_name" content="Port Daily">' + ld({"@graph": [
                    {"@type": "WebSite", "name": "ignored"},
                    {"@type": "NewsArticle", "headline": "Harbour reopens after storm",
                     "author": [{"name": "Lee Chen"}], "datePublished": "2026-11-17T08:00:00Z",
                     "publisher": {"@type": "Organization", "name": "Port Daily Group"}}]})
                + f"</head><body><article>{ARTICLE}</article></body></html>"), {}
        if path == "/none":
            return 200, html, (
                f"<html><head><title>Plain page</title></head><body>{NAV}<div id='x'>{ARTICLE}</div>"
                "<footer><p>Copyright and many links in the footer that are not the reading.</p></footer>"
                "</body></html>"), {}
        if path == "/redirect":
            return 302, html, "", {"Location": f"{self.inside}/secret"}
        if path == "/hop":
            return 302, html, "", {"Location": "/og"}
        if path == "/sub":
            return 200, html, (
                f'<html><head><title>With a picture</title></head><body><p>Hello.</p>'
                f'<img src="{self.inside}/pixel.png"></body></html>'), {}
        if path == "/login":
            return 200, html, ('<html><head><title>Sign in</title></head><body><form>'
                               '<input type="password"></form></body></html>'), {}
        if path == "/check":
            return 200, html, ('<html><head><title>Just a moment...</title></head><body>'
                               '<iframe src="https://challenges.cloudflare.com/x"></iframe></body></html>'), {}
        if path == "/paid":
            return 200, html, ('<html><head><meta property="og:title" content="Members only">' + ld(
                {"@type": "NewsArticle", "headline": "Members only", "isAccessibleForFree": False})
                + "</head><body><p>Subscribe.</p></body></html>"), {}
        if path == "/file":
            return 200, "application/zip", "PK", {"Content-Disposition": "attachment; filename=a.zip"}
        # Bilibili-shaped pages
        if path == "/v/popular/all":
            return 200, html, ("<html><head><title>Popular</title></head><body><div id='list'></div><script>"
                               "fetch('/x/web-interface/popular?ps=20&pn=1').then(r => r.json()).then(d => {"
                               "document.getElementById('list').textContent = d.data.list.length; });"
                               "</script></body></html>"), {}
        if path == "/all":
            words = (query.get("keyword") or [""])[0]
            cards = "".join(f'<div class="video-card"><a href="//127.0.0.1:{self.server.server_address[1]}'
                            f'/video/{bv}/"><img></a><h3 title="{words} {title}">{words} {title}</h3></div>'
                            for bv, title in list(self.videos.items())[:6])
            return 200, html, f"<html><head><title>search</title></head><body>{cards}</body></html>", {}
        if path.startswith("/video/BV"):
            bv = path.split("/")[2]
            state = {"videoData": {"bvid": bv, "title": self.videos.get(bv, "?"), "desc": "A video description.",
                                   "pic": f"{self.url}/cover.png", "duration": 125, "pubdate": 1763000000,
                                   "owner": {"name": "Uploader A", "mid": 99}}}
            return 200, html, (f'<html><head><title>{self.videos.get(bv, "?")}_bilibili</title>'
                               f'<meta property="og:title" content="{self.videos.get(bv, "?")}">'
                               f"<script>window.__INITIAL_STATE__ = {json.dumps(state)};</script></head>"
                               "<body><p>video page</p></body></html>"), {}
        # YouTube-shaped pages
        if path == "/results":
            items = [{"videoRenderer": {"videoId": f"abcdefghij{n}", "title": {"runs": [{"text": f"Clip {n}"}]}}}
                     for n in range(5)]
            data = {"contents": {"sectionListRenderer": {"contents": [{"itemSectionRenderer": {"contents": items}}]}}}
            return 200, html, (f"<html><head><title>results</title><script>var ytInitialData = "
                               f"{json.dumps(data)};</script></head><body></body></html>"), {}
        if path == "/watch":
            ident = (query.get("v") or [""])[0]
            player = {"videoDetails": {"videoId": ident, "title": f"Clip {ident[-1]}", "author": "Channel B",
                                       "lengthSeconds": "61", "shortDescription": "About the clip.",
                                       "thumbnail": {"thumbnails": [{"url": f"{self.url}/cover.png"}]}},
                      "microformat": {"playerMicroformatRenderer": {"publishDate": "2026-10-02"}}}
            if ident == "walledvideo":
                player = {"playabilityStatus": {"status": "LOGIN_REQUIRED", "reason": "Sign in to confirm"}}
            return 200, html, (f"<html><head><title>Clip - YouTube</title><script>var ytInitialPlayerResponse = "
                               f"{json.dumps(player)};</script></head><body><p>watch</p></body></html>"), {}
        return 404, html, "<title>gone</title>", {}

    def _handler(self):
        site = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args) -> None:
                pass

            def do_GET(self) -> None:
                url = urlsplit(self.path)
                site.loads.append(url.path)
                if url.path == "/cover.png":
                    return self._send(200, "image/png", site.cover)
                if url.path == "/x/web-interface/popular":
                    rows = [{"bvid": bv, "title": title} for bv, title in site.videos.items()]
                    return self._send(200, "application/json",
                                      json.dumps({"code": 0, "data": {"list": rows}}).encode())
                status, kind, body, headers = site.page(url.path, parse_qs(url.query))
                self._send(status, kind, body.encode("utf-8"), headers)

            def _send(self, status: int, kind: str, body: bytes, headers: dict | None = None) -> None:
                self.send_response(status)
                self.send_header("Content-Type", kind)
                self.send_header("Content-Length", str(len(body)))
                for name, value in (headers or {}).items():
                    self.send_header(name, value)
                self.end_headers()
                self.wfile.write(body)

        return Handler
