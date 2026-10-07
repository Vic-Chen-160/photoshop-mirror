#!/usr/bin/env python3
"""photoshop-mirror server: serves one or more Photoshop Image Assets folders to a phone.

Usage: serve.py <port> [--token=XXX] [--local] [--depth=N] <path> [<path> ...]

Each path is resolved like this:
  · an *-assets folder (or a folder that directly holds images) → one source
  · any other folder → every *-assets folder found below it

A background thread rescans the sources every 3 seconds, so when you open another
PSD and Generator creates a new -assets folder, it shows up on the phone without a
restart. Scanning runs in the background so a slow walk over a network drive never
blocks HTTP requests.

When a token is set, everything lives under /<token>/ and any other path is a 404.
Anyone on the same Wi-Fi can reach the port; the token keeps unreleased work private.
"""
import email.utils, hashlib, hmac, http.server, io, json, mimetypes, os, socketserver
import subprocess, sys, tempfile, threading, time, urllib.parse

HERE     = os.path.dirname(os.path.abspath(__file__))
PORT     = int(sys.argv[1])
_args    = sys.argv[2:]
_opt     = lambda k: next((a.split("=", 1)[1] for a in _args if a.startswith(k + "=")), None)
TOKEN    = _opt("--token") or ""
LOCALIZE = "--local" in _args          # redirect cross-filesystem -assets to local disk
MAXDEPTH = int(_opt("--depth") or 3)   # how deep to look for *-assets
SPECS    = [os.path.abspath(p) for p in _args if not p.startswith("--")]
TEMPLATE = os.path.join(HERE, "preview.html")
EXT      = (".png", ".jpg", ".jpeg", ".gif", ".webp")
PAGE     = ("/", "/index.html")
RESCAN   = 3.0        # seconds; backs off automatically when a scan is slow (see scanner)

_manifest = {"sources": []}   # sent to the page
_lookup   = {}                # slug -> real folder path
_lock     = threading.Lock()


def slug_of(path):
    return hashlib.sha1(path.encode("utf-8")).hexdigest()[:10]


def label_of(path):
    # Localized folders carry a hash suffix (v4-75f4691a). Show the original PSD name
    # instead, which localize.py recorded in .psmirror-source.
    try:
        with open(os.path.join(path, ".psmirror-source")) as fh:
            path = fh.read().strip() or path
    except OSError:
        pass
    b = os.path.basename(path)
    return b[:-7] if b.endswith("-assets") else b


def images_in(d):
    try:
        return sorted(
            f for f in os.listdir(d)
            if f.lower().endswith(EXT) and not f.startswith(".")
        )
    except OSError:
        return []


def find_sources(spec):
    """Expand one spec into the list of source folders."""
    if not os.path.isdir(spec):
        return []
    if spec.endswith("-assets") or images_in(spec):
        return [spec]
    # Walk down looking for *-assets.
    #
    # Not os.walk: it trusts scandir's d_type, and on SMB mounts a symlink is
    # reported as is_dir()=False and is_symlink()=False, so localized -assets
    # folders get skipped. os.path.isdir really stats, which is correct.
    found, stack = [], [(spec, 0)]
    while stack:
        cur, depth = stack.pop()
        try:
            entries = os.listdir(cur)
        except OSError:
            continue
        for name in entries:
            if name.startswith("."):
                continue
            full = os.path.join(cur, name)
            if not os.path.isdir(full):
                continue
            if name.endswith("-assets"):
                found.append(full)          # don't descend into it
            elif depth + 1 < MAXDEPTH:
                stack.append((full, depth + 1))
    return sorted(found)


def localize(d):
    """Swap a cross-filesystem -assets folder for a symlink to local disk; return the path to watch.

    Save As (v3 → v4) makes Generator create a brand-new -assets folder and EXDEV comes
    back. Handling it during the background scan means every new version just works.
    """
    if not LOCALIZE or os.path.islink(d):
        return os.path.realpath(d)
    try:
        if os.stat(d).st_dev == os.stat(tempfile.gettempdir()).st_dev:
            return d                            # already on local disk
    except OSError:
        return d
    try:
        r = subprocess.run(
            [sys.executable, os.path.join(HERE, "localize.py"), d, "--apply"],
            capture_output=True, text=True, timeout=60)
        if r.stdout.strip():
            print(r.stdout.rstrip(), flush=True)
    except Exception as e:
        print(f"  ⚠️  Could not redirect {d}: {e}", flush=True)
    return os.path.realpath(d)


def rescan():
    sources, lookup, seen = [], {}, set()
    for spec in SPECS:
        for d in find_sources(spec):
            d = localize(d)
            if d in seen:
                continue
            seen.add(d)
            files = images_in(d)
            if not files:
                continue
            s = slug_of(d)
            lookup[s] = d
            sources.append({"slug": s, "label": label_of(d), "files": files})
    sources.sort(key=lambda s: s["label"])
    with _lock:
        _manifest["sources"] = sources
        # Shown on the page when there are no images, so "can't connect" and
        # "connected but nothing to show" look different.
        _manifest["watching"] = [p.replace(os.path.expanduser("~"), "~", 1) for p in SPECS]
        _manifest["scanned"] = time.strftime("%H:%M:%S")
        _lookup.clear()
        _lookup.update(lookup)


def scanner():
    """Background rescan. A deep walk over a network drive can take seconds, and
    hitting the NAS every 3 seconds regardless is rude, so back off by actual cost."""
    while True:
        t0 = time.perf_counter()
        try:
            rescan()
        except Exception:
            pass
        elapsed = time.perf_counter() - t0
        time.sleep(max(RESCAN, elapsed * 4))


class Handler(http.server.BaseHTTPRequestHandler):
    def _bytes(self, body, ctype):
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store, must-revalidate")
        self.end_headers()
        return io.BytesIO(body)

    def _file(self, path):
        """/f/<slug>/<name> → the image. Only a single-level file name is allowed."""
        parts = path.split("/", 3)          # ['', 'f', slug, name]
        if len(parts) != 4:
            self.send_error(404); return None
        slug, name = parts[2], urllib.parse.unquote(parts[3])
        if "/" in name or name.startswith(".") or not name.lower().endswith(EXT):
            self.send_error(403); return None
        with _lock:
            d = _lookup.get(slug)
        if not d:
            self.send_error(404); return None
        full = os.path.join(d, name)
        if os.path.dirname(os.path.abspath(full)) != os.path.abspath(d):
            self.send_error(403); return None
        try:
            f = open(full, "rb")
            st = os.fstat(f.fileno())
        except OSError:
            self.send_error(404); return None
        self.send_response(200)
        self.send_header("Content-Type", mimetypes.guess_type(name)[0] or "application/octet-stream")
        self.send_header("Content-Length", str(st.st_size))
        self.send_header("Last-Modified", email.utils.formatdate(st.st_mtime, usegmt=True))
        self.send_header("Cache-Control", "no-store, must-revalidate")
        self.end_headers()
        return f

    def _route(self):
        path = urllib.parse.urlparse(self.path).path
        if TOKEN:
            prefix = "/" + TOKEN
            head, _, rest = path[1:].partition("/")
            if not hmac.compare_digest(head, TOKEN):
                self.send_error(404); return None
            if path == prefix:                      # /<token> → /<token>/
                self.send_response(301)
                self.send_header("Location", prefix + "/")
                self.send_header("Content-Length", "0")
                self.end_headers()
                return None
            path = "/" + rest
        if path in PAGE:
            try:
                with open(TEMPLATE, "rb") as f:
                    return self._bytes(f.read(), "text/html; charset=utf-8")
            except OSError:
                self.send_error(500, "preview.html missing"); return None
        if path == "/__list":
            with _lock:
                body = json.dumps(_manifest, ensure_ascii=False).encode()
            return self._bytes(body, "application/json")
        if path.startswith("/f/"):
            return self._file(path)
        self.send_error(404)
        return None

    def do_GET(self):
        f = self._route()
        if f:
            try:
                while chunk := f.read(64 * 1024):
                    self.wfile.write(chunk)
            except (BrokenPipeError, ConnectionResetError):
                pass
            finally:
                f.close()

    def do_HEAD(self):
        f = self._route()
        if f:
            f.close()

    def log_message(self, fmt, *args):
        pass


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


if __name__ == "__main__":
    rescan()                                        # first scan up front so the page loads instantly
    threading.Thread(target=scanner, daemon=True).start()
    try:
        Server(("0.0.0.0", PORT), Handler).serve_forever()
    except KeyboardInterrupt:
        print("\n  Stopped\n")
