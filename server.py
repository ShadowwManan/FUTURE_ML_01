import http.server
import socketserver
import os
import json
import urllib.parse

PORT = int(os.environ.get("PORT", "3000"))
ROOT = os.path.dirname(os.path.abspath(__file__))
PUBLIC = os.path.join(ROOT, "public")
DATA = os.path.join(ROOT, "data")

try:
    with open(os.path.join(DATA, "faqs.json"), "r", encoding="utf-8") as f:
        FAQS = json.load(f)
except Exception:
    FAQS = []
TRAINED = []
try:
    with open(os.path.join(DATA, "trained_pairs.json"), "r", encoding="utf-8") as f:
        obj = json.load(f)
        TRAINED = obj.get("pairs", [])
except Exception:
    TRAINED = []
KB = list(FAQS) + list(TRAINED)

CONV = {}

def tokens(s):
    return [x for x in "".join([c.lower() if c.isalnum() else " " for c in s]).split() if x]

def jaccard(a, b):
    sa = set(a)
    sb = set(b)
    inter = len(sa.intersection(sb))
    union = len(sa.union(sb))
    return 0 if union == 0 else inter / union

def levenshtein(a, b):
    m = len(a)
    n = len(b)
    if m == 0:
        return n
    if n == 0:
        return m
    d = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(m + 1):
        d[i][0] = i
    for j in range(n + 1):
        d[0][j] = j
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            d[i][j] = min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + cost)
    return d[m][n]

def score(q, s):
    t1 = tokens(q)
    t2 = tokens(s)
    j = jaccard(t1, t2)
    l = levenshtein(q.lower(), s.lower())
    ln = l / max(len(q), len(s)) if max(len(q), len(s)) > 0 else 1
    return 0.7 * j + 0.3 * (1 - ln)

def best(s, k=3):
    scored = [{"item": x, "score": score(x["question"], s)} for x in KB]
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:k]

class Handler(http.server.BaseHTTPRequestHandler):
    def send_json(self, obj, code=200):
        data = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/faqs":
            self.send_json([{"question": x["question"]} for x in KB])
            return
        if parsed.path.startswith("/public/"):
            rel = parsed.path[len("/public/") :]
            fp = os.path.normpath(os.path.join(PUBLIC, rel))
            if not fp.startswith(PUBLIC):
                self.send_response(403)
                self.end_headers()
                return
            if not os.path.isfile(fp):
                self.send_response(404)
                self.end_headers()
                return
            ext = os.path.splitext(fp)[1].lower()
            types = {".html": "text/html", ".css": "text/css", ".js": "application/javascript", ".json": "application/json", ".png": "image/png", ".jpg": "image/jpeg", ".svg": "image/svg+xml"}
            ct = types.get(ext, "application/octet-stream")
            with open(fp, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", ct)
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
            return
        fp = os.path.join(PUBLIC, "index.html")
        with open(fp, "rb") as f:
            content = f.read()
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path != "/api/chat":
            self.send_response(404)
            self.end_headers()
            return
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length > 0 else b"{}"
        try:
            body = json.loads(raw.decode("utf-8"))
        except Exception:
            body = {}
        message = str(body.get("message", ""))
        cid = body.get("conversationId") or os.urandom(6).hex()
        conv = CONV.get(cid) or {"turns": [], "low": 0}
        conv["turns"].append({"role": "user", "content": message})
        matches = best(message)
        top = matches[0] if matches else None
        suggestions = [m["item"]["question"] for m in matches]
        handoff = False
        if top and top["score"] >= 0.6:
            reply = top["item"]["answer"]
            conv["low"] = 0
        else:
            conv["low"] = conv["low"] + 1
            reply = "I am not fully sure. Here are some related topics you can try."
            if conv["low"] >= 2:
                handoff = True
        conv["turns"].append({"role": "assistant", "content": reply})
        CONV[cid] = conv
        self.send_json({"reply": reply, "suggestions": suggestions, "handoff": handoff, "conversationId": cid})

def run():
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"Server listening on http://localhost:{PORT}")
        httpd.serve_forever()

if __name__ == "__main__":
    run()
